from pathlib import Path

from documental import entrada
from documental.config import Config
from documental.modelos import Atribucion, ClipEscena, Locucion, Palabra, Tramo
from dataclasses import replace

from documental.monetizacion import (
    auditar_guion,
    auditar_render,
    estimar_duracion,
    informe,
    proporcion_propia_estimada,
    similitud,
)
from documental.publicacion import capitulos, descripcion, etiquetas, marca_tiempo, pausas_publicitarias, problemas_capitulos

from conftest import guion_minimo
from test_adaptadores import guion_largo


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
        "c01e01": ClipEscena(Path("a"), False, ids_stock=["abc", "otro"]),
        "c01e02": ClipEscena(Path("b"), False, ids_stock=["abc"]),
    }
    historial = [{"slug": "otro", "titulo": "Otro", "narracion": " ".join(e.narracion for e in g.escenas)}]
    h = auditar_guion(g, historial, Config()) + auditar_render(
        g, tramos, clips, {}, (False, "voz local"), {"otro": "video-anterior"}, Config())
    bloqueos = " ".join(x.mensaje for x in h if x.nivel == "bloqueo")
    assert "licencia comercial" in bloqueos
    assert "se repite" in bloqueos
    assert "ya se usó en el video «video-anterior»" in bloqueos
    assert "se parece" in bloqueos
    assert "no cita ninguna fuente" in bloqueos  # hay una cifra (89) y fuentes = []
    avisos = " ".join(x.mensaje for x in h if x.nivel == "aviso")
    assert "anuncios a mitad" in avisos and "Duración estimada" in avisos
    assert "Bloqueos" in informe(h)


def test_licencia_no_verificada_es_aviso():
    g = entrada.desde_dict(guion_minimo(fuentes=["F"]))
    h = auditar_render(g, _tramos(g), {}, {}, (None, "sin red"), {}, Config())
    assert any(x.nivel == "aviso" and "sin red" in x.mensaje for x in h)


def test_fuente_que_no_esta_en_la_lista():
    g = entrada.desde_dict(guion_minimo(fuentes=["Agencia Internacional de Energía 2022"]))
    h = auditar_guion(g, [], Config())
    assert any("IRENA 2023" in x.mensaje and "no aparece" in x.mensaje for x in h)
    g = entrada.desde_dict(guion_minimo(fuentes=["IRENA, Renewable Power Generation Costs 2023"]))
    assert not any("no aparece" in x.mensaje for x in auditar_guion(g, [], Config()))


def test_terminos_de_stock_repetidos():
    datos = guion_minimo(fuentes=["IRENA 2023"])
    datos["capitulos"][0]["escenas"][1]["visual"] = {"tipo": "stock", "busqueda": ["SUN"]}
    h = auditar_guion(entrada.desde_dict(datos), [], Config())
    assert any("«SUN» se repite" in x.mensaje for x in h)


def test_proporcion_propia_por_tiempo_y_tarjetas():
    cfg = Config()
    datos = guion_minimo(fuentes=["F"])
    datos["capitulos"].append({"titulo": "Dos", "escenas": [{"narracion": "uno dos tres cuatro", "visual": {"tipo": "stock", "busqueda": ["x"]}}]})
    g = entrada.desde_dict(datos)
    # 3 s de tarjeta del capítulo "Dos" cuentan como propios.
    sin = proporcion_propia_estimada(g, replace(cfg, monetizacion=replace(cfg.monetizacion, tarjetas_capitulo=False)))
    con = proporcion_propia_estimada(g, cfg)
    assert con > sin
    palabras = sum(len(e.narracion.split()) for e in g.escenas)
    assert abs(estimar_duracion(g, cfg) - (palabras / 150 * 60 + 3 + 20)) < 0.01


def test_pausas_publicitarias():
    caps = [(0, "a"), (90, "b"), (130, "c"), (200, "d"), (300, "e"), (590, "f")]
    assert pausas_publicitarias(caps, 600) == [130, 300]


def test_auditoria_limpia():
    g = entrada.desde_dict(guion_largo())
    tramos = _tramos(g, duracion=40)
    clips = {e.id: ClipEscena(Path("a"), not e.visual.tipo == "stock", ids_stock=[e.id] if e.visual.tipo == "stock" else [])
             for e in g.escenas}
    h = auditar_guion(g, [], Config()) + auditar_render(g, tramos, clips, {}, (True, "plan creator"), {}, Config())
    assert h == []
