"""La página publicada de FixMate no puede quedarse atrás de la demo.

Una página de demo envejece en silencio: el producto cambia, las cifras se
quedan viejas y el que la enseña se entera delante del cliente. Aquí se corre
la demo de verdad y se comprueba que cada número que la página afirma siga
saliendo de ella.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PAGINA = RAIZ / "docs" / "fixmate" / "index.html"
QR = RAIZ / "docs" / "fixmate" / "qr-fixmate.svg"
DIRECCION = "https://nilthonnn.github.io/nefer/fixmate/"


@pytest.fixture(scope="module")
def html() -> str:
    return PAGINA.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def salida_demo(tmp_path_factory) -> str:
    """La demo corrida entera, que es la fuente de todo lo que la página dice."""
    import contextlib
    import io

    ruta = RAIZ / "herramientas" / "demo-fixmate.py"
    spec = importlib.util.spec_from_file_location("demo_fixmate_pub", ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["demo_fixmate_pub"] = modulo
    spec.loader.exec_module(modulo)

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        assert modulo.main(["--dir", str(tmp_path_factory.mktemp("taller"))]) == 0
    return buffer.getvalue()


# Lo que la página afirma, y que tiene que seguir saliendo de la demo.
CIFRAS = [
    ("31 fragmentos", "el tamaño del índice"),
    ("sin cambios: 5 archivos", "la segunda indexación no relee nada"),
    ("OT-2026-0501", "el antecedente de la fuga"),
    ("210 N·m", "el torque citado, copiado de la fuente"),
    ("Filtro de aire colmatado por polvo de mina", "la causa que corrige a la búsqueda"),
    ("OT-2026-0412", "el antecedente que respalda la estadística"),
    ("5.71 h/dia", "el ritmo de uso"),
    ("2026-09-25", "la fecha del próximo servicio"),
    ("119 dias", "el MTBF"),
    ("Correa del ventilador partida por polea desalineada", "la falla nueva"),
    ("OT-2026-0001", "la orden que abre el cierre del círculo"),
    ("P533781", "el repuesto sugerido"),
]


@pytest.mark.parametrize("cifra,porque", CIFRAS, ids=[c for c, _ in CIFRAS])
def test_lo_que_la_pagina_afirma_lo_sigue_diciendo_la_demo(cifra, porque, html,
                                                           salida_demo):
    assert cifra in html, f"la página ya no cita {porque}"
    assert cifra in salida_demo, (
        f"la página dice «{cifra}» ({porque}) y la demo ya no lo produce. "
        "Vuelva a correr `python3 herramientas/demo-fixmate.py` y actualice "
        "docs/fixmate/index.html.")


def test_los_porcentajes_del_clasificador_son_los_medidos(html, salida_demo):
    """Los dos números que sostienen la parte de aprendizaje.

    No van escritos aquí a mano: se sacan de la demo y se busca **esos** en
    la página. Escritos a mano, esta prueba se rompía cada vez que el motor
    mejoraba y había que venir a cambiarle el número, que es justo lo que
    hace que una prueba deje de vigilar y empiece a estorbar.
    """
    import re

    medido = re.search(r"(\d+)% de acierto sobre (\d+) casos", salida_demo)
    assert medido, "la demo ya no publica su acierto medido"
    base = re.search(r"daria (\d+)%", salida_demo)
    assert base, "la demo ya no publica su línea base"

    acierto, linea_base = medido.group(1), base.group(1)
    assert f"{acierto}&nbsp;%" in html, (
        f"la demo mide {acierto}% y la página no lo dice. Vuelva a correr "
        "`python3 herramientas/demo-fixmate.py` y actualice "
        "docs/fixmate/index.html.")
    assert f"{linea_base}&nbsp;%" in html, (
        f"la demo da una línea base de {linea_base}% y la página no lo dice.")
    # Y el acierto sin la línea base al lado no significa nada.
    assert acierto != linea_base or "línea base" in html


def test_la_pagina_dice_lo_que_todavia_no_hace(html):
    # Es lo que la hace creible delante de un cliente, y lo primero que se
    # cae cuando alguien "mejora" la pagina.
    for limite in ("La foto no diagnostica", "OCR", "telemetría"):
        assert limite in html


def test_el_qr_apunta_a_esta_pagina():
    dentro = re.search(r"<title>([^<]+)</title>", QR.read_text(encoding="utf-8"))
    assert dentro and dentro.group(1) == DIRECCION


def test_la_pagina_declara_la_direccion_que_el_qr_codifica(html):
    assert DIRECCION in html


def test_la_pagina_de_descarga_lleva_a_la_demo():
    indice = (RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
    assert 'href="fixmate/"' in indice


def test_la_pagina_no_pide_nada_a_un_tercero(html):
    # La misma regla que la app: ninguna llamada fuera. Aquí no es por la
    # señal, es porque cada visita le contaría a un tercero quién la mira.
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    permitidos = {"https://github.com/nilthonnn/nefer"}
    assert not (set(externos) - permitidos), f"llama fuera: {externos}"


def test_el_fixmate_descargable_no_puede_envejecer(tmp_path):
    """`docs/fixmate-app.html` es la app entera en un archivo.

    Si alguien cambia la app y se olvida de rehacerlo, quien lo descargue se
    lleva una versión vieja sin enterarse — y es justo lo que hace imposible
    saber por qué «sigue fallando».
    """
    import subprocess
    import sys

    raiz = Path(__file__).resolve().parents[1]
    descargable = raiz / "docs" / "fixmate-app.html"
    assert descargable.exists(), "falta docs/fixmate-app.html"

    recien = tmp_path / "recien.html"
    herramienta = raiz / "herramientas" / "empaquetar-fixmate.py"
    subprocess.run([sys.executable, str(herramienta), str(recien)],
                   check=True, capture_output=True)
    assert descargable.read_bytes() == recien.read_bytes(), (
        "docs/fixmate-app.html no coincide con la app: rehacerlo con "
        "`python herramientas/empaquetar-fixmate.py`")


def test_la_pagina_publicada_manda_a_fixmate_y_no_a_la_app_de_actas():
    """Mandaba a la app de actas, que es otro producto.

    Quien llega a la página de FixMate viene por el diagnóstico; darle la
    app de levantar actas fotográficas es perderlo en la puerta.
    """
    raiz = Path(__file__).resolve().parents[1]
    pagina = (raiz / "docs" / "fixmate" / "index.html").read_text(encoding="utf-8")
    assert 'href="../fixmate-app.html"' in pagina
    assert 'href="app/"' in pagina
