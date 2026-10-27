import base64

import pytest
import requests

from documental import reintentos
from documental.config import Config, Secretos
from documental.errores import ErrorConfiguracion, ErrorVoz, ErrorVozTransitorio
from documental.voz.base import estimar_palabras, palabras_desde_caracteres
from documental.voz.elevenlabs import VozElevenLabs


def test_caracteres_a_palabras():
    texto = "Hola  mundo."
    inicios = [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    fines = [t + 0.1 for t in inicios]
    p = palabras_desde_caracteres(list(texto), inicios, fines)
    assert [(x.texto, x.inicio, round(x.fin, 2)) for x in p] == [("Hola", 0.0, 0.4), ("mundo.", 0.5, 1.1)]


def test_caracteres_inconsistentes():
    with pytest.raises(ValueError):
        palabras_desde_caracteres(["a"], [0.0, 1.0], [1.0])


def test_estimacion_ordenada_y_dentro_del_audio():
    p = estimar_palabras("Uno, dos tres. Cuatro cinco seis siete.", 4.0)
    assert len(p) == 7
    assert all(a.inicio < a.fin <= b.inicio for a, b in zip(p, p[1:]))
    assert p[-1].fin <= 4.0


class _Respuesta:
    def __init__(self, status, datos=None, texto=""):
        self.status_code = status
        self._datos = datos
        self.text = texto

    def json(self):
        return self._datos


class _Sesion:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.cuerpos = []

    def post(self, url, **kw):
        self.cuerpos.append(kw["json"])
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _cfg():
    return Config(secretos=Secretos(elevenlabs_api_key="k", elevenlabs_voice_id="v"))


def _ok(mp3: bytes, texto="Hola mundo"):
    chars = list(texto)
    return _Respuesta(200, {
        "audio_base64": base64.b64encode(mp3).decode(),
        "alignment": {
            "characters": chars,
            "character_start_times_seconds": [i * 0.05 for i in range(len(chars))],
            "character_end_times_seconds": [i * 0.05 + 0.05 for i in range(len(chars))],
        },
    })


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    monkeypatch.setattr(reintentos.time, "sleep", lambda s: None)


def test_requiere_claves():
    with pytest.raises(ErrorConfiguracion):
        VozElevenLabs(Config())


def test_sintesis_con_contexto(tmp_path, mp3_corto):
    sesion = _Sesion([_ok(mp3_corto)])
    voz = VozElevenLabs(_cfg(), sesion=sesion)
    loc = voz.sintetizar("Hola mundo", tmp_path / "e1", anterior="Antes.", siguiente="Después.")
    assert loc.audio.suffix == ".mp3" and loc.audio.is_file()
    assert [p.texto for p in loc.palabras] == ["Hola", "mundo"]
    assert 0.9 < loc.duracion < 1.2
    assert sesion.cuerpos[0]["previous_text"] == "Antes." and sesion.cuerpos[0]["next_text"] == "Después."


def test_reintenta_5xx_y_429(tmp_path, mp3_corto):
    sesion = _Sesion([_Respuesta(503, texto="ocupado"), _Respuesta(429), _ok(mp3_corto)])
    VozElevenLabs(_cfg(), sesion=sesion).sintetizar("Hola mundo", tmp_path / "e1")
    assert len(sesion.cuerpos) == 3


def test_no_reintenta_clave_invalida(tmp_path):
    sesion = _Sesion([_Respuesta(401, texto="invalid api key")])
    with pytest.raises(ErrorVoz, match="401"):
        VozElevenLabs(_cfg(), sesion=sesion).sintetizar("Hola", tmp_path / "e1")
    assert len(sesion.cuerpos) == 1


def test_red_caida_agota_intentos(tmp_path):
    sesion = _Sesion([requests.ConnectionError("x")] * 4)
    with pytest.raises(ErrorVozTransitorio):
        VozElevenLabs(_cfg(), sesion=sesion).sintetizar("Hola", tmp_path / "e1")
    assert len(sesion.cuerpos) == 4


def test_huella_cambia_con_ajustes():
    a = VozElevenLabs(_cfg()).huella()
    b = VozElevenLabs(Config(secretos=Secretos(elevenlabs_api_key="k", elevenlabs_voice_id="otra"))).huella()
    assert a != b


class _SesionGet(_Sesion):
    def __init__(self, respuesta):
        super().__init__([])
        self.respuesta = respuesta

    def get(self, url, **kw):
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


@pytest.mark.parametrize(
    "respuesta, esperado",
    [
        (_Respuesta(200, {"tier": "free"}), False),
        (_Respuesta(200, {"tier": "creator"}), True),
        (_Respuesta(401, texto="no"), None),
        (requests.ConnectionError("x"), None),
    ],
)
def test_licencia_segun_plan(respuesta, esperado):
    comercial, detalle = VozElevenLabs(_cfg(), sesion=_SesionGet(respuesta)).licencia()
    assert comercial is esperado and detalle


def test_voz_inexistente_es_error_de_configuracion():
    with pytest.raises(ErrorConfiguracion, match="no existe"):
        VozElevenLabs(_cfg(), sesion=_SesionGet(_Respuesta(404))).describir_voz()
