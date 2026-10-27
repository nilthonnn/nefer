import json
from pathlib import Path

import pytest

from documental import entrada
from documental.errores import ErrorEntrada

from conftest import guion_minimo

EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos"


def test_ejemplos_del_repositorio_son_validos():
    for ruta in EJEMPLOS.iterdir():
        if ruta.suffix in (".json", ".md"):
            g = entrada.cargar(ruta)
            assert g.escenas, ruta


def test_ids_automaticos_y_slug():
    g = entrada.desde_dict(guion_minimo(titulo="¿Cómo vivir Off-Grid?"))
    assert [e.id for e in g.escenas] == ["c01e01", "c01e02"]
    assert g.slug == "como-vivir-off-grid"


@pytest.mark.parametrize(
    "mutar, fragmento",
    [
        (lambda d: d["capitulos"][0]["escenas"][0].update(narracion=""), "narracion"),
        (lambda d: d["capitulos"][0]["escenas"][0]["visual"].update(tipo="gif"), "visual.tipo"),
        (lambda d: d["capitulos"][0]["escenas"][0]["visual"].update(busqueda=[]), "busqueda"),
        (lambda d: d["capitulos"][0]["escenas"][1]["visual"].update(datos={"valor": 1}), "etiqueta"),
        (lambda d: d["capitulos"][0]["escenas"][1].update(pausa=9), "pausa"),
        (lambda d: d.update(capitulos=[]), "capitulos"),
    ],
)
def test_errores_dicen_donde(mutar, fragmento):
    datos = guion_minimo()
    mutar(datos)
    with pytest.raises(ErrorEntrada, match=fragmento):
        entrada.desde_dict(datos)


def test_id_repetido():
    datos = guion_minimo()
    for e in datos["capitulos"][0]["escenas"]:
        e["id"] = "x"
    with pytest.raises(ErrorEntrada, match="repetido"):
        entrada.desde_dict(datos)


def test_json_invalido_indica_linea(tmp_path):
    ruta = tmp_path / "g.json"
    ruta.write_text('{"titulo": "x",\n "capitulos": [}', encoding="utf-8")
    with pytest.raises(ErrorEntrada, match="línea 2"):
        entrada.cargar(ruta)


def test_markdown(tmp_path):
    ruta = tmp_path / "g.md"
    ruta.write_text(
        "---\ntitulo: Título MD\netiquetas: a, b\nfuentes:\n- F1\n- F2\n---\n\n"
        "## Cap 1\n> stock: sun, solar farm\nPrimera frase\nque sigue.\n\n"
        '> cifra: {"valor": 5, "etiqueta": "x"}\nSegunda.\n',
        encoding="utf-8",
    )
    g = entrada.cargar(ruta)
    assert g.titulo == "Título MD"
    assert g.etiquetas == ["a", "b"] and g.fuentes == ["F1", "F2"]
    assert [e.narracion for e in g.escenas] == ["Primera frase que sigue.", "Segunda."]
    assert g.escenas[0].visual.busqueda == ["sun", "solar farm"]
    assert g.escenas[1].visual.datos == {"valor": 5, "etiqueta": "x"}


def test_markdown_parrafo_sin_visual(tmp_path):
    ruta = tmp_path / "g.md"
    ruta.write_text("---\ntitulo: T\n---\n## C\nSin visual.\n", encoding="utf-8")
    with pytest.raises(ErrorEntrada, match="> tipo"):
        entrada.cargar(ruta)


def test_imagen_relativa_al_guion(tmp_path):
    (tmp_path / "foto.jpg").write_bytes(b"x")
    datos = guion_minimo()
    datos["capitulos"][0]["escenas"][0]["visual"] = {"tipo": "imagen", "ruta": "foto.jpg"}
    ruta = tmp_path / "g.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    g = entrada.cargar(ruta)
    assert Path(g.escenas[0].visual.ruta) == tmp_path / "foto.jpg"
