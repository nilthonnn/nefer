"""Los dos motores tienen que dar lo mismo.

FixMate está escrito dos veces a propósito: en Python, donde están el Excel y
los PDF, y en JavaScript dentro de la app de campo, que es donde está el
mecánico y donde no hay señal. Dos implementaciones de la misma búsqueda se
separan solas —una corrección aquí que allá no se hace, un redondeo distinto—
y nadie lo nota hasta que el teléfono contesta otra cosa que la computadora.

Aquí se corren las mismas consultas sobre el mismo índice en los dos motores
y se comparan los rankings con sus puntajes, la causa, los pasos, los torques
y las probabilidades del clasificador. El motor de JavaScript se saca de la
propia app publicada, no de una copia: si alguien lo edita ahí, esto lo mide.

Sin `node` instalado la prueba se salta; en CI está.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "app" / "index.html"
EJEMPLOS = RAIZ / "ejemplos" / "fixmate"

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="hace falta node para el motor JS")

# Consultas de taller, no de laboratorio: como las escribiría el mecánico.
CONSULTAS = [
    ("gotea aceite por el cilindro del brazo toda la noche", None, None),
    ("sale humo negro y pierde fuerza en la subida", "P0300", None),
    ("no arranca en la mañana y el arranque gira lento", None, None),
    ("el mastil de la torre no sube", None, "TI09-04"),
    ("que apriete lleva el perno de la tapa del cilindro", None, None),
    ("manguera reventada en el brazo", None, None),
    ("el motor se calienta y para a las dos horas", None, None),
    # Una que no está en ningún antecedente: los dos tienen que negarse igual.
    ("tramites de aduana del contenedor en el puerto", None, None),
]


@pytest.fixture(scope="module")
def indice(tmp_path_factory):
    """Un índice de verdad, hecho con el corpus de ejemplo del repositorio."""
    from nefer.fixmate import Indice, Motor, actualizar

    indice = Indice()
    actualizar(indice, [EJEMPLOS])
    indice.medicion = Motor(indice).medicion()
    ruta = tmp_path_factory.mktemp("cruce") / "indice.json"
    indice.guardar(ruta)
    return ruta


def _respuesta_python(ruta_indice: Path) -> list[dict]:
    from nefer.fixmate import Indice, Motor
    from nefer.fixmate.motor import Consulta, SinEvidencia

    motor = Motor(Indice.cargar(ruta_indice))
    salida = []
    for texto, dtc, equipo in CONSULTAS:
        try:
            d = motor.consultar(Consulta(texto, codigo_dtc=dtc, codigo_equipo=equipo))
        except SinEvidencia:
            salida.append({"consulta": texto, "sin_evidencia": True})
            continue
        salida.append({
            "consulta": texto,
            "sin_evidencia": False,
            "evidencia": [[e.id, e.similitud] for e in d.evidencia_historica],
            "causa": d.causa_raiz_mas_probable,
            "pasos": d.pasos_recomendados,
            "herramientas": d.herramientas_y_repuestos,
            "torques": d.torques,
            "confianza": d.confianza,
            "causas_probables": [[c["causa"], c["probabilidad"], c["casos"]]
                                 for c in d.causas_probables],
            "avisos": len(d.avisos),
        })
    return salida


def motor_js() -> str:
    """El motor tal como está en la app publicada, entre sus dos marcas."""
    html = APP.read_text(encoding="utf-8")
    m = re.search(r"/\* fixmate:motor:inicio.*?\*/(.*?)/\* fixmate:motor:fin \*/",
                  html, re.S)
    assert m, ("no se encontró el motor en la app: faltan las marcas "
               "fixmate:motor:inicio / fixmate:motor:fin")
    return m.group(1)


CONDUCTOR = """
%(motor)s

var fs = require("fs");
var indice = new Indice(JSON.parse(fs.readFileSync(process.argv[2], "utf8")));
var motor = new Motor(indice);
var casos = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
var salida = casos.map(function (caso) {
  var d;
  try {
    d = motor.consultar({ texto: caso[0], codigo_dtc: caso[1], codigo_equipo: caso[2] });
  } catch (e) {
    if (e && e.sinEvidencia) return { consulta: caso[0], sin_evidencia: true };
    throw e;
  }
  return {
    consulta: caso[0],
    sin_evidencia: false,
    evidencia: d.evidencia_historica.map(function (e) { return [e.id, e.similitud]; }),
    causa: d.causa_raiz_mas_probable,
    pasos: d.pasos_recomendados,
    herramientas: d.herramientas_y_repuestos,
    torques: d.torques,
    confianza: d.confianza,
    causas_probables: d.causas_probables.map(function (c) {
      return [c.causa, c.probabilidad, c.casos];
    }),
    avisos: d.avisos.length
  };
});
process.stdout.write(JSON.stringify(salida));
"""


def _respuesta_js(ruta_indice: Path, tmp_path: Path) -> list[dict]:
    guion = tmp_path / "cruce.js"
    guion.write_text(CONDUCTOR % {"motor": motor_js()}, encoding="utf-8")
    casos = tmp_path / "casos.json"
    casos.write_text(json.dumps(CONSULTAS), encoding="utf-8")

    proceso = subprocess.run([NODE, str(guion), str(ruta_indice), str(casos)],
                             capture_output=True, text=True, timeout=120)
    if proceso.returncode != 0:
        pytest.fail("el motor JS no corrió:\n" + proceso.stderr[-2000:])
    return json.loads(proceso.stdout)


@pytest.fixture(scope="module")
def cruce(indice, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("js")
    return list(zip(_respuesta_python(indice), _respuesta_js(indice, tmp)))


def test_la_app_lleva_el_motor_entre_sus_marcas():
    # Si alguien las quita, esta suite dejaría de comparar nada y no se vería.
    codigo = motor_js()
    assert "function fnv1a" in codigo
    assert "Indice.prototype.buscar" in codigo


@pytest.mark.parametrize("n", range(len(CONSULTAS)),
                         ids=[c[0][:28] for c in CONSULTAS])
def test_los_dos_motores_recuperan_lo_mismo(cruce, n):
    py, js = cruce[n]
    assert py["consulta"] == js["consulta"]
    assert py["sin_evidencia"] == js["sin_evidencia"], (
        "uno responde y el otro no para: " + py["consulta"])
    if py["sin_evidencia"]:
        return
    # Los puntajes, a los cuatro decimales con que se publican.
    assert js["evidencia"] == py["evidencia"], (
        f"el ranking se separó en «{py['consulta']}»")


@pytest.mark.parametrize("n", range(len(CONSULTAS)),
                         ids=[c[0][:28] for c in CONSULTAS])
def test_los_dos_motores_redactan_lo_mismo(cruce, n):
    py, js = cruce[n]
    if py["sin_evidencia"]:
        return
    for campo in ("causa", "pasos", "herramientas", "torques", "confianza",
                  "causas_probables", "avisos"):
        assert js[campo] == py[campo], (
            f"«{campo}» se separó en «{py['consulta']}»:\n"
            f"  python: {py[campo]!r}\n  js:     {js[campo]!r}")


def test_el_telefono_tambien_se_niega_cuando_no_hay_antecedente(cruce):
    # La última consulta es de aduanas: ninguno de los dos debe contestarla.
    py, js = cruce[-1]
    assert py["sin_evidencia"] and js["sin_evidencia"]


def test_el_hash_da_el_mismo_numero_en_los_dos_lenguajes(tmp_path):
    from nefer.fixmate.embeddings import fnv1a

    guion = tmp_path / "hash.js"
    guion.write_text(motor_js() + """
var palabras = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(palabras.map(function (p) {
  return fnv1a(p).toString();
})));
""", encoding="utf-8")
    palabras = ["fixmate:motor", "fixmate:hidráulico", "fixmate:^inye",
                "fixmate:P0300", "fixmate:niño"]
    proceso = subprocess.run([NODE, str(guion), json.dumps(palabras)],
                             capture_output=True, text=True, timeout=60)
    assert proceso.returncode == 0, proceso.stderr[-1000:]
    assert [int(x) for x in json.loads(proceso.stdout)] == [
        fnv1a(p.encode("utf-8")) for p in palabras]
