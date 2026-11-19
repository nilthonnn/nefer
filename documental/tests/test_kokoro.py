import pytest

from documental.voz.kokoro import palabras_desde_fonemas


def test_fonemas_a_palabras():
    # "ola mundo": 3 fonemas, espacio, 5 fonemas; 1 unidad = 25 ms
    pred = [5] + [4, 4, 4] + [6] + [4, 4, 4, 4, 4] + [3]
    p = palabras_desde_fonemas("Hola mundo.", "ola mundo", pred)
    assert [w.texto for w in p] == ["Hola", "mundo."]
    assert p[0].inicio == pytest.approx(0.05) and p[0].fin == pytest.approx(0.35)
    assert p[1].inicio == pytest.approx(0.50) and p[1].fin == pytest.approx(1.00)


def test_filtra_fonemas_fuera_del_vocabulario():
    vocab = {c: i for i, c in enumerate("ola mundo")}
    pred = [5] + [4, 4, 4] + [6] + [4, 4, 4, 4, 4] + [3]
    p = palabras_desde_fonemas("Hola mundo.", "ˈola ˈmundo", pred, vocab)
    assert [w.texto for w in p] == ["Hola", "mundo."]
    with pytest.raises(ValueError):
        palabras_desde_fonemas("Hola mundo.", "ˈola ˈmundo", pred)


def test_desajuste_reparte_dentro_del_tramo_real():
    fonemas = "en dos mil beinte"
    pred = [3] + [2] * len(fonemas) + [3]
    p = palabras_desde_fonemas("en 2024", fonemas, pred)
    assert len(p) == 2 and all(a.fin <= b.inicio for a, b in zip(p, p[1:]))
    assert p[-1].fin <= len(fonemas) * 0.05 + 1e-9
