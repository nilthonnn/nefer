import pytest

from shortsfactory.audio import alineacion
from shortsfactory.models import Guion, Variacion

from conftest import guion_bueno, requiere_espeak, requiere_ffmpeg


def test_kokoro_fonemas_a_palabras():
    # "hola mundo" → fonemas "ola mundo" (3 + espacio + 5); 1 unidad = 25 ms
    fonemas = "ola mundo"
    pred = [5] + [4, 4, 4] + [6] + [4, 4, 4, 4, 4] + [3]
    p = alineacion.desde_fonemas("Hola mundo.", fonemas, pred)
    assert [w.texto for w in p] == ["Hola", "mundo."]
    assert p[0].inicio == pytest.approx(0.05) and p[0].fin == pytest.approx(0.35)
    assert p[1].inicio == pytest.approx(0.50) and p[1].fin == pytest.approx(1.00)


def test_kokoro_filtra_fonemas_fuera_del_vocabulario():
    # "ˈ" (acento) no está en el vocabulario: Kokoro lo descarta y pred_dur no lo trae.
    vocab = {c: i for i, c in enumerate("ola mundo")}
    pred = [5] + [4, 4, 4] + [6] + [4, 4, 4, 4, 4] + [3]
    p = alineacion.desde_fonemas("Hola mundo.", "ˈola ˈmundo", pred, vocab)
    assert [w.texto for w in p] == ["Hola", "mundo."] and p[1].inicio == pytest.approx(0.50)
    with pytest.raises(ValueError):
        alineacion.desde_fonemas("Hola mundo.", "ˈola ˈmundo", pred)  # sin filtrar no cuadra


def test_kokoro_desajuste_reparte_sin_salirse():
    # "2024" se pronuncia como varias palabras: no hay 1:1, se reparte el tramo real.
    fonemas = "en dos mil beinte"
    pred = [3] + [2] * len(fonemas) + [3]
    p = alineacion.desde_fonemas("en 2024", fonemas, pred)
    assert len(p) == 2 and p[0].inicio == pytest.approx(0.0) and p[-1].fin <= len(fonemas) * 0.05 + 1e-9
    with pytest.raises(ValueError):
        alineacion.desde_fonemas("x", "abc", [1, 2])


def test_edge_limites():
    p = alineacion.desde_limites_edge("Hola, mundo", [(0.1, 0.3, "Hola"), (0.5, 0.4, "mundo")])
    assert [(w.texto, w.inicio, w.fin) for w in p] == [("Hola,", 0.1, 0.4), ("mundo", 0.5, 0.9)]


def test_estimacion_monotona():
    p = alineacion.estimar("El PIB creció 2,5% en 2023.", 0.0, 3.0)
    assert all(a.fin <= b.inicio for a, b in zip(p, p[1:])) and p[-1].fin <= 3.0


@requiere_ffmpeg
@requiere_espeak
def test_narracion_completa_con_pausas_y_loudness(tmp_path, cfg):
    from shortsfactory.audio import mezcla
    from shortsfactory.audio.motores import Espeak
    from shortsfactory.proc import duracion
    from shortsfactory.visuals.variacion import elegir

    v = elegir(3, [])
    n = mezcla.narrar(guion_bueno(), Espeak(), v, cfg, tmp_path)
    assert n.duracion <= cfg.duracion_max + 0.05
    assert abs(duracion(n.audio) - n.duracion) < 0.01
    assert all(a.fin <= b.inicio + 1e-6 for a, b in zip(n.palabras, n.palabras[1:]))
    assert any(w.enfasis for w in n.palabras)  # "razón", "9,5%"...
    assert len(n.frases) == 5 and n.frases[1][0] > n.frases[0][1]  # pausa tras el gancho
