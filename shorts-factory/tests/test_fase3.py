"""SEO con modelo rápido, miniatura propia y síntesis concurrente."""

import threading
import time
import types
from pathlib import Path

import pytest

from shortsfactory.audio import mezcla
from shortsfactory.errors import ErrorTransitorio
from shortsfactory.models import Tendencia
from shortsfactory.publisher import seo, youtube
from shortsfactory.publisher.cuota import Cuota
from shortsfactory.settings import Settings
from shortsfactory.visuals import miniatura, variacion

from conftest import guion_bueno

# --- SEO ------------------------------------------------------------------------------


class _Rapido:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.llamadas = []

    def json(self, sistema, contenido, esquema, max_tokens=4000):
        self.llamadas.append(contenido)
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def _propuesta(**cambios):
    datos = {"titulo": "Por qué la inflación no vuelve al 3,1 %", "etiquetas": ["inflación", "precios", "economía"],
             "gancho": "En 2022 tocó 9,5 % y hoy sigue lejos de 2014."}
    datos.update(cambios)
    return datos


def test_seo_acepta_una_propuesta_con_cifras_reales(serie):
    p = seo.optimizar(guion_bueno(), serie, _Rapido(_propuesta()))
    assert p is not None and p["titulo"].startswith("Por qué")
    titulo, descripcion, etiquetas = seo.metadatos(guion_bueno(), serie, Tendencia(titulo="t"), [], p)
    assert titulo.endswith("#Shorts") and descripcion.startswith("En 2022 tocó")
    assert etiquetas[:3] == ["inflación", "precios", "economía"]
    assert "no es asesoría financiera" in descripcion  # las reglas fijas siguen aplicando


@pytest.mark.parametrize("cambios,motivo", [
    ({"titulo": "La inflación llegó al 25 % y nadie lo dijo"}, "cifras"),
    ({"titulo": "La inflación VIRAL que nadie vio"}, "mayúsculas"),
    ({"gancho": "Un dato viral sobre precios"}, "spam"),
    ({"titulo": "Corto"}, "caracteres"),
    ({"etiquetas": ["#inflacion"]}, "etiquetas"),
])
def test_seo_descarta_propuestas_que_rompen_reglas(serie, cambios, motivo):
    problemas = seo.revisar_propuesta(_propuesta(**cambios), guion_bueno(), serie)
    assert any(motivo in p for p in problemas)
    assert seo.optimizar(guion_bueno(), serie, _Rapido(_propuesta(**cambios))) is None


def test_seo_cae_a_reglas_fijas_si_el_modelo_falla(serie):
    assert seo.optimizar(guion_bueno(), serie, _Rapido(ErrorTransitorio("529"))) is None
    titulo, _, _ = seo.metadatos(guion_bueno(), serie, Tendencia(titulo="t"), [], None)
    assert titulo == seo.titulo(guion_bueno())


# --- miniatura ----------------------------------------------------------------------


def test_miniatura_usa_la_cifra_del_gancho(serie):
    valor, contexto = miniatura.dato_impactante(guion_bueno(), serie)
    assert valor == "4,4 %" and contexto.endswith("2024")


def test_miniatura_sin_cifras_en_el_guion_usa_el_ultimo_dato(serie):
    g = guion_bueno()
    g.frases[0].texto, g.frases[2].texto = "Nadie habla de esto", "Llegó muy alto."
    assert miniatura.dato_impactante(g, serie)[0] == "4,4 %"


def test_miniatura_props_pasan_el_contrato(serie):
    datos = miniatura.props(guion_bueno(), serie, variacion.elegir(5, []))
    assert set(datos) == {"titulo", "cifra", "contexto", "fuente", "colores", "tipografia"}
    assert len(datos["cifra"]) <= 16 and datos["fuente"].startswith("Fuente:")


class _Thumbnails:
    def __init__(self, guion):
        self.guion, self.llamadas = list(guion), []

    def set(self, videoId, media_body):
        self.llamadas.append(videoId)
        paso = self.guion.pop(0)

        class _Ejecutar:
            def execute(self_inner):
                if isinstance(paso, Exception):
                    raise paso
                return paso

        return _Ejecutar()


def _http_error(status):
    from googleapiclient.errors import HttpError

    return HttpError(type("Resp", (), {"status": status, "reason": "x"})(), b"")


@pytest.fixture
def jpg(tmp_path) -> Path:
    ruta = tmp_path / "m.jpg"
    ruta.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
    return ruta


def _yt(thumbs):
    return types.SimpleNamespace(thumbnails=lambda: thumbs)


def test_miniatura_se_sube_y_gasta_su_cuota(tmp_path, jpg):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None, dir_estado=tmp_path)
    thumbs = _Thumbnails([{"items": []}])
    assert youtube.subir_miniatura(cfg, "v1", jpg, yt=_yt(thumbs)) is True
    assert thumbs.llamadas == ["v1"] and Cuota(tmp_path, 10_000).usadas() == 50


def test_miniatura_403_no_rompe_la_publicacion(tmp_path, jpg):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None, dir_estado=tmp_path)
    assert youtube.subir_miniatura(cfg, "v1", jpg, yt=_yt(_Thumbnails([_http_error(403)]))) is False


def test_miniatura_reintenta_5xx(tmp_path, jpg):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None, dir_estado=tmp_path)
    esperas = []
    thumbs = _Thumbnails([_http_error(503), {"items": []}])
    assert youtube.subir_miniatura(cfg, "v1", jpg, yt=_yt(thumbs), dormir=esperas.append) is True
    assert len(esperas) == 1


def test_miniatura_sin_cuota_se_omite_en_silencio(tmp_path, jpg):
    pytest.importorskip("googleapiclient")
    cfg = Settings(_env_file=None, dir_estado=tmp_path, youtube_cuota_diaria=40)
    thumbs = _Thumbnails([{"items": []}])
    assert youtube.subir_miniatura(cfg, "v1", jpg, yt=_yt(thumbs)) is False and thumbs.llamadas == []


# --- síntesis concurrente --------------------------------------------------------------


class _Motor:
    def __init__(self, concurrente):
        self.concurrente = concurrente
        self.activos = self.maximo = 0
        self.cerrojo = threading.Lock()

    def sintetizar(self, texto, destino, velocidad):
        with self.cerrojo:
            self.activos += 1
            self.maximo = max(self.maximo, self.activos)
        time.sleep(0.05)
        with self.cerrojo:
            self.activos -= 1
        return destino, len(texto) / 10, [], True


def test_motor_concurrente_sintetiza_a_la_vez_y_conserva_el_orden(tmp_path):
    g = guion_bueno()
    motor = _Motor(concurrente=True)
    salida = mezcla.sintetizar_frases(g, motor, 1.0, tmp_path, hilos=4)
    assert [d for d, *_ in salida] == [tmp_path / f"frase{i:02d}" for i in range(len(g.frases))]
    assert motor.maximo > 1


def test_kokoro_sintetiza_en_serie(tmp_path):
    motor = _Motor(concurrente=False)
    mezcla.sintetizar_frases(guion_bueno(), motor, 1.0, tmp_path, hilos=4)
    assert motor.maximo == 1


def test_motores_declaran_si_admiten_concurrencia():
    from shortsfactory.audio import motores

    assert motores.Kokoro.concurrente is False
    assert motores.Edge.concurrente is True and motores.Espeak.concurrente is True
