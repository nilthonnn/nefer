from pathlib import Path

from documental import entrada
from documental.config import Config
from documental.modelos import Atribucion, ClipEscena, Locucion, Palabra, Tramo
from documental.monetizacion import auditar, informe, similitud
from documental.publicacion import capitulos, descripcion, etiquetas, marca_tiempo, problemas_capitulos

from conftest import guion_minimo


def _tramos(guion, duracion=12.0, ppm=150):
    tramos, t = [], 0.0
    for c in guion.capitulos:
        for e in c.escenas:
            n = int(duracion * ppm / 60)
            loc = Locucion(Path("x"), duracion, [Palabra("p", 0, 0.1)] * n)
            tramos.append(Tramo(e, c.titulo, t, duracion, loc))
            t += duracion
    return tramos


def test_marca_tiempo():
    assert marca_tiempo(0) == "00:00"
    assert marca_tiempo(75.9) == "01:15"
    assert marca_tiempo(3725) == "1:02:05"


def test_capitulos_y_reglas_de_youtube():
    datos = guion_minimo()
    datos["capitulos"] += [
        {"titulo": "Dos", "escenas": [{"narracion": "x", "visual": {"tipo": "titular", "datos": {"titulo": "t"}}}]},
        {"titulo": "Tres", "escenas": [{"narracion": "y", "visual": {"tipo": "titular", "datos": {"titulo": "t"}}}]},
    ]
    g = entrada.desde_dict(datos)
    caps = capitulos(_tramos(g))
    assert [c for _, c in caps] == ["Uno", "Dos", "Tres"] and caps[0][0] == 0
    assert problemas_capitulos(caps, 48) == []
    assert problemas_capitulos(caps[:2], 30)  # menos de 3
    assert problemas_capitulos([(0, "a"), (5, "b"), (20, "c")], 40)  # uno de 5 s


def test_etiquetas_no_superan_500():
    lista = [f"etiqueta numero {i}" for i in range(100)]
    salida = etiquetas(lista)
    assert sum(len(e) + 3 for e in salida) <= 500 and len(salida) < 100


def test_descripcion_incluye_capitulos_fuentes_y_creditos():
    g = entrada.desde_dict(guion_minimo(fuentes=["IRENA 2023"], etiquetas=["energía solar", "off grid"]))
    texto = descripcion(g, [(0, "Uno"), (30, "Dos")], [Atribucion("pexels", "Ana", "https://p/1"), Atribucion("pexels", "Ana", "https://p/1")], "Música: X", True)
    assert "00:00 Uno" in texto and "00:30 Dos" in texto
    assert "IRENA 2023" in texto
    assert texto.count("Ana") == 1  # créditos sin duplicar
    assert "#EnergíaSolar #OffGrid" in texto


def test_similitud():
    assert similitud("el sol es energía libre", "el sol es energía libre") == 1.0
    assert similitud("el sol es energía libre", "las baterías de litio duran años") == 0.0


def test_auditoria_bloqueos_y_avisos():
    g = entrada.desde_dict(guion_minimo())
    tramos = _tramos(g)
    clips = {
        "c01e01": ClipEscena(Path("a"), False, ids_stock=["abc"]),
        "c01e02": ClipEscena(Path("b"), False, ids_stock=["abc"]),
    }
    historial = [{"slug": "otro", "titulo": "Otro", "narracion": " ".join(e.narracion for e in g.escenas)}]
    h = auditar(g, tramos, clips, {}, voz_comercial=False, historial=historial, cfg=Config())
    bloqueos = [x.mensaje for x in h if x.nivel == "bloqueo"]
    assert any("vista previa" in m for m in bloqueos)
    assert any("se repite" in m for m in bloqueos)
    assert any("se parece" in m for m in bloqueos)
    avisos = " ".join(x.mensaje for x in h if x.nivel == "aviso")
    assert "anuncios a mitad" in avisos and "visual propio" in avisos and "fuentes" in avisos
    assert "Bloqueos" in informe(h)


def test_auditoria_limpia():
    g = entrada.desde_dict(guion_minimo(fuentes=["F"]))
    datos = guion_minimo(fuentes=["F"])
    tramos = _tramos(g, duracion=250)
    clips = {"c01e01": ClipEscena(Path("a"), False, ids_stock=["1"]), "c01e02": ClipEscena(Path("b"), True)}
    h = auditar(g, tramos, clips, {}, True, [], Config())
    # Solo queda el aviso de capítulos (el guion mínimo tiene uno).
    assert [x.nivel for x in h] == ["aviso"] and "Capítulos" in h[0].mensaje
