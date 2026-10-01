"""La demo tiene que correr, y tiene que enseñar lo que dice que enseña.

Una demo rota se descubre delante del cliente. Aqui se corre entera, con los
mismos comandos de verdad que ejecuta cuando alguien la lanza, y se comprueba
que cada parte muestre lo suyo: que el PDF y el Word se lean, que la segunda
indexacion no relea nada, que el diagnostico salga con su evidencia y que lo
registrado al cerrar responda enseguida.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _demo():
    ruta = RAIZ / "herramientas" / "demo-fixmate.py"
    spec = importlib.util.spec_from_file_location("demo_fixmate", ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["demo_fixmate"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def demo():
    return _demo()


@pytest.fixture(scope="module")
def taller(demo, tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("taller")
    demo.montar_taller(carpeta)
    return carpeta


def test_el_taller_de_mentira_trae_los_cuatro_formatos(taller):
    nombres = {a.name for a in taller.iterdir()}
    assert "historial-2026.xlsx" in nombres        # el historial, en Excel
    assert "manual-hidraulica.docx" in nombres     # un manual, en Word
    assert "manual-electrico.pdf" in nombres       # otro, en PDF
    assert "acta-GE074-01.xlsx" in nombres         # un acta de nefer


def test_el_pdf_que_arma_la_demo_es_un_pdf_de_verdad(taller):
    from nefer.fixmate import pdf_texto

    texto = pdf_texto.extraer(taller / "manual-electrico.pdf")
    assert "Par de apriete de bornes de bateria: 8 N.m" in texto


def test_la_demo_entera_corre_y_cuenta_lo_que_promete(demo, tmp_path, capsys):
    assert demo.main(["--dir", str(tmp_path)]) == 0
    salida = capsys.readouterr().out

    # 1. los formatos se leen
    assert "manual-hidraulica.docx" in salida
    assert "# Cilindros hidráulicos" in salida
    # 2. la segunda pasada no relee nada
    assert "sin cambios: 5 archivos" in salida
    assert "Clasificador de causas: entrenado" in salida
    # 3 y 4. el diagnostico, con su evidencia y su estadistica
    assert "CAUSA RAIZ MAS PROBABLE" in salida
    assert "Sello del vástago cortado" in salida
    assert "LO QUE DICE EL HISTORIAL COMPLETO" in salida
    # 5. la prediccion
    assert "PROXIMO SERVICIO" in salida
    assert "VENCIDA" in salida
    # 6. el cierre del circulo
    assert "Registrado OT-2026-0001" in salida
    assert "Correa del ventilador partida" in salida


def test_cada_demo_corre_por_separado(demo, tmp_path):
    for nombre in demo.DEMOS:
        assert demo.main([nombre, "--dir", str(tmp_path)]) == 0, nombre


def test_una_demo_que_no_existe_lo_dice(demo, tmp_path, capsys):
    assert demo.main(["magia", "--dir", str(tmp_path)]) == 1
    assert "No conozco" in capsys.readouterr().err


def test_la_demo_no_deja_basura_si_no_se_lo_piden(demo):
    import tempfile

    antes = set(Path(tempfile.gettempdir()).glob("fixmate-demo-*"))
    demo.main(["formatos"])
    assert set(Path(tempfile.gettempdir()).glob("fixmate-demo-*")) == antes
