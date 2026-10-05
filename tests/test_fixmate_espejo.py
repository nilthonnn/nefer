"""El catálogo del teléfono tiene que ser el mismo que el de la oficina.

FixMate clasifica en los dos lados: en Python, donde está el Excel, y en el
JavaScript de la app, que es donde está el mecánico y donde no hay señal. Dos
copias del catálogo que se separan no dan error en ninguna parte —el teléfono
agrupa una causa, la oficina la agrupa distinto, los dos informes se ven
razonables— y nadie se entera hasta que alguien compara dos listas que
tendrían que ser la misma.

Así que la del teléfono se genera desde la otra, y aquí se comprueban las dos
mitades del trato: que lo generado sea lo que está en el archivo, y que con
los mismos textos los dos den el mismo código.

    python herramientas/espejo-catalogo.py
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from nefer.fixmate.catalogo import POR_DEFECTO

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "fixmate" / "app" / "index.html"
NODE = shutil.which("node")


def _herramienta():
    ruta = RAIZ / "herramientas" / "espejo-catalogo.py"
    spec = importlib.util.spec_from_file_location("espejo_catalogo", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_espejo_del_catalogo_esta_al_dia():
    """Si esto falla, alguien tocó el catálogo y no rehizo el espejo."""
    espejo = _herramienta()
    assert espejo.bloque() in APP.read_text(encoding="utf-8"), (
        "el catálogo del teléfono quedó viejo. Correr "
        "«python herramientas/espejo-catalogo.py» y volver a commitear.")


def test_el_espejo_no_se_edita_a_mano_sin_que_se_note():
    """Las marcas son lo que hace que la herramienta sepa qué reemplazar."""
    html = APP.read_text(encoding="utf-8")
    espejo = _herramienta()
    assert html.count(espejo.ABRE) == 1 and html.count(espejo.CIERRA) == 1


# Textos de taller, escritos como los escribe el taller. Van los que el
# catálogo reconoce y los que tiene que rechazar: que los dos se nieguen
# igual importa tanto como que acierten igual.
TEXTOS = [
    "Filtro de aire colmatado",
    "filtro aire tapado",
    "FILTROS DE AIRE OBSTRUIDOS",
    "Baterías sulfatadas",
    "bornes flojos y sulfatados",
    "baterías sulfatadas con densidad baja en dos vasos",
    "Sello del vástago vencido",
    "sellos goteando en el cilindro del brazo",
    "mangueras picadas rozando el chasis",
    "nivel de aceite hidráulico bajo por fuga lenta en el acople rápido",
    "Inyector con retorno excesivo",
    "Termostato trabado abierto",
    "radiadores obstruidos con tierra",
    "cadena del tren de rodaje fuera de tolerancia",
    "dientes del cucharón gastados",
    "embrague patinando",
    "fisura en la soldadura del chasis",
    "Driver de focos LED dañado por vibración en el traslado.",
    "intervalo de cambio de aceite atrasado 180 horas",
    # Lo que no alcanza, y lo planificado, que no es una falla.
    "bomba", "fuga", "se rompió", "turbo", "inyector", "alternador",
    "trámites de aduana del contenedor en el puerto",
    "cambio de aceite de motor programado",
    "mantenimiento preventivo de 500 horas",
    "cambio de filtros según plan",
]


@pytest.mark.skipif(not NODE, reason="hace falta node para el motor JS")
def test_el_telefono_codifica_igual_que_la_oficina(tmp_path):
    """Los mismos textos, los dos clasificadores, el mismo código o ninguno.

    El JavaScript sale de la app publicada, no de una copia: si alguien lo
    edita ahí, esto lo mide.
    """
    from test_fixmate_cruce import motor_js

    guion = tmp_path / "codificar.js"
    guion.write_text(motor_js() + """
var fs = require("fs");
var textos = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(textos.map(function (t) {
  var e = catalogoClasificar(t);
  return e ? e[0] : null;
})));
""", encoding="utf-8")
    casos = tmp_path / "textos.json"
    casos.write_text(json.dumps(TEXTOS), encoding="utf-8")

    proceso = subprocess.run([NODE, str(guion), str(casos)],
                             capture_output=True, text=True, timeout=120)
    if proceso.returncode != 0:
        pytest.fail("el clasificador JS no corrió:\n" + proceso.stderr[-2000:])
    del_telefono = json.loads(proceso.stdout)

    de_la_oficina = []
    for t in TEXTOS:
        e = POR_DEFECTO.clasificar(t)
        de_la_oficina.append(e.codigo if e else None)

    separados = [(t, o, j) for t, o, j in zip(TEXTOS, de_la_oficina, del_telefono)
                 if o != j]
    assert not separados, "se separaron:\n" + "\n".join(
        f"  «{t}»: oficina {o!r}, teléfono {j!r}" for t, o, j in separados)


@pytest.mark.skipif(not NODE, reason="hace falta node para el motor JS")
def test_el_telefono_tampoco_codifica_con_una_sola_pista(tmp_path):
    """La regla de las dos pistas no sirve de nada si solo la cumple un lado."""
    from test_fixmate_cruce import motor_js

    pistas = sorted({p for e in POR_DEFECTO.entradas for p in e.pistas})
    guion = tmp_path / "solas.js"
    guion.write_text(motor_js() + """
var fs = require("fs");
var pistas = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(pistas.filter(function (p) {
  return catalogoClasificar(p) !== null;
})));
""", encoding="utf-8")
    casos = tmp_path / "pistas.json"
    casos.write_text(json.dumps(pistas), encoding="utf-8")

    proceso = subprocess.run([NODE, str(guion), str(casos)],
                             capture_output=True, text=True, timeout=120)
    if proceso.returncode != 0:
        pytest.fail("el clasificador JS no corrió:\n" + proceso.stderr[-2000:])
    assert json.loads(proceso.stdout) == [], "estas pistas codifican solas"
