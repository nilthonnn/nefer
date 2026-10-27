import re

from documental.config import Config
from documental.modelos import Palabra
from documental.multimedia.subtitulos import a_ass, a_srt, agrupar


def _palabras(texto, paso=0.4):
    return [Palabra(t, i * paso, i * paso + paso * 0.9) for i, t in enumerate(texto.split())]


def test_agrupa_por_puntuacion_y_largo():
    grupos = agrupar(_palabras("Uno dos. Tres cuatro cinco seis siete ocho nueve"), max_palabras=5)
    assert [" ".join(p.texto for p in g) for g in grupos] == ["Uno dos.", "Tres cuatro cinco seis siete", "ocho nueve"]


def test_agrupa_por_silencio():
    p = [Palabra("a", 0, 0.2), Palabra("b", 0.3, 0.5), Palabra("c", 2.0, 2.2)]
    assert len(agrupar(p)) == 2


def test_ass_resalta_una_palabra_por_evento():
    ass = a_ass(_palabras("Hola mundo solar."), Config())
    eventos = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert len(eventos) == 3
    assert all(e.count("\\c&H0001B3F5&") == 1 for e in eventos)
    assert eventos[0].startswith("Dialogue: 0,0:00:00.00,0:00:00.40")
    assert "PlayResX: 1920" in ass


def test_ass_escapa_llaves():
    ass = a_ass([Palabra("{malo}", 0, 1)], Config())
    assert "{malo}" not in ass


def test_srt_formato():
    srt = a_srt(_palabras("Primera frase. Segunda frase un poco más larga."))
    bloques = srt.strip().split("\n\n")
    assert len(bloques) == 2
    assert re.match(r"1\n00:00:00,000 --> 00:00:00,\d{3}\nPrimera frase\.", bloques[0])
