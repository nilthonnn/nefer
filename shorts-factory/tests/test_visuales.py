import random

from shortsfactory.models import PalabraT
from shortsfactory.visuals import variacion
from shortsfactory.visuals.subtitulos import paginar


def test_paletas_legibles():
    for nombre, c in variacion.PALETAS.items():
        for fondo in ("fondo1", "fondo2"):
            assert variacion.contraste(c["texto"], c[fondo]) >= 4.5, (nombre, fondo)


def test_sorteo_reproducible_y_distinto_de_lo_reciente():
    a, b = variacion.elegir(42, []), variacion.elegir(42, [])
    assert a == b
    recientes = [variacion.elegir(s, []).firma() for s in range(8)]
    nueva = variacion.elegir(999, recientes)
    assert min(variacion.distancia(nueva.firma(), r) for r in recientes) >= 3


def test_cien_shorts_no_repiten_combinacion_consecutiva():
    recientes: list[dict] = []
    for s in range(100):
        v = variacion.elegir(s, recientes[-12:])
        assert v.firma() not in recientes[-12:]
        recientes.append(v.firma())


def test_paginas_sin_solapes_y_cortes_en_puntuacion():
    palabras = [PalabraT(texto=t, inicio=i * 0.3, fin=i * 0.3 + 0.29) for i, t in enumerate("Uno dos tres. Cuatro cinco seis siete".split())]
    pags = paginar(palabras, 3)
    assert [[w.texto for w in p.palabras] for p in pags] == [["Uno", "dos", "tres."], ["Cuatro", "cinco", "seis"], ["siete"]]
    assert all(a.fin <= b.inicio for a, b in zip(pags, pags[1:]))
