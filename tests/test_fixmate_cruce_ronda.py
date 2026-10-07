"""El teléfono y la oficina tienen que decir lo mismo de una ronda.

La ronda CIL se decide dos veces: en el JavaScript de
`docs/fixmate/ronda/index.html`, que corre en el teléfono del operador sin
red, y en `nefer/fixmate/tpm.py`, que corre en la oficina cuando llega el
archivo. Dos copias que se separan **no dan error en ninguna parte**: el
teléfono dice que la ronda está completa, la oficina dice que no, las dos
pantallas se ven razonables, y nadie se entera.

Aquí se corren las mismas rondas en los dos y se comparan las respuestas. El
JavaScript se saca de la **app publicada**, no de una copia: si alguien lo
edita ahí, esto lo mide.

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
sys.path.insert(0, str(RAIZ))
APP = RAIZ / "docs" / "fixmate" / "ronda" / "index.html"
EJEMPLOS = RAIZ / "ejemplos" / "rcm-tpm"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="hace falta node para correr el JS de la app")


def reglas_js() -> str:
    """Las reglas tal como están en la app publicada, entre sus dos marcas."""
    html = APP.read_text(encoding="utf-8")
    m = re.search(r"/\* ronda:reglas:inicio.*?\*/(.*?)/\* ronda:reglas:fin \*/",
                  html, re.S)
    assert m, ("no se encontraron las reglas en la app: faltan las marcas "
               "ronda:reglas:inicio / ronda:reglas:fin")
    return m.group(1)


CONDUCTOR = """
%(reglas)s

var fs = require("fs");
var caso = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
var e = estadoRonda(caso.ejecucion, caso.pauta);
var anomalias = anomaliasDe(caso.ejecucion, caso.pauta);
process.stdout.write(JSON.stringify({
  estado: {
    total: e.total, respondidos: e.respondidos, ok: e.ok, nok: e.nok,
    sin_acceso: e.sin_acceso, pendientes: e.pendientes, segundos: e.segundos,
    presupuesto_seg: e.presupuesto_seg, completa: e.completa,
    sospechosa_de_firma: e.sospechosa_de_firma
  },
  anomalias: anomalias.map(function (a) {
    return [a.id, a.severidad, a.descripcion, a.componente,
            a.codigo_catalogo, a.modo_falla_id];
  })
}));
"""


def _js(pauta: dict, ejecucion: dict, tmp_path: Path) -> dict:
    guion = tmp_path / "cruce-ronda.js"
    guion.write_text(CONDUCTOR % {"reglas": reglas_js()}, encoding="utf-8")
    entrada = tmp_path / "caso.json"
    entrada.write_text(json.dumps({"pauta": pauta, "ejecucion": ejecucion}),
                       encoding="utf-8")
    salida = subprocess.run(["node", str(guion), str(entrada)],
                            capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


def _python(pauta_d: dict, ejecucion_d: dict) -> dict:
    from nefer.fixmate import cargador
    from nefer.fixmate.anomalia import desde_ejecucion
    from nefer.fixmate.tpm import estado

    pauta = cargador.checklist_de_dict(pauta_d)
    ejecucion = cargador.ejecucion_de_dict(ejecucion_d)
    e = estado(ejecucion, pauta)
    # Sin análisis: es la misma información que tiene el teléfono.
    anomalias = desde_ejecucion(ejecucion, pauta, None)
    return {
        "estado": e.a_dict(),
        "anomalias": [[a.id, a.severidad, a.descripcion, a.componente,
                       a.codigo_catalogo, a.modo_falla_id] for a in anomalias],
    }


def _pauta() -> dict:
    return json.loads((EJEMPLOS / "pauta-ex220.json").read_text(encoding="utf-8"))


def _ronda(nombre: str) -> dict:
    return json.loads((EJEMPLOS / nombre).read_text(encoding="utf-8"))


# ═══════════════════ el cruce ═══════════════════

@pytest.mark.parametrize("archivo", [
    "ronda-ex220-hallazgo.json",
    "ronda-ex220-firmada.json",
    "ronda-ex220-sin-enganche.json",
])
def test_los_dos_dicen_lo_mismo_de_las_rondas_de_ejemplo(archivo, tmp_path):
    # Con una excepción documentada y probada aparte: el código de catálogo,
    # que el teléfono no deduce. Ver el test del final del archivo.
    pauta, ronda = _pauta(), _ronda(archivo)
    js, py = _js(pauta, ronda, tmp_path), _python(pauta, ronda)
    assert js["estado"] == py["estado"]
    sin_codigo = lambda d: [a[:4] + a[5:] for a in d["anomalias"]]  # noqa: E731
    assert sin_codigo(js) == sin_codigo(py)


def test_los_dos_coinciden_en_que_un_punto_sin_ver_rompe_la_ronda(tmp_path):
    # Es la regla que más fácil se separa: un lenguaje la trata como «ronda
    # completa con una nota» y el otro como incompleta.
    pauta = _pauta()
    ronda = {"id": "r1", "checklist_id": pauta["id"], "activo_codigo": "EX-220",
             "operador": "x", "fecha": "2026-03-16",
             "items": [{"punto_id": p["id"] if "id" in p else f"{pauta['id']}.{i+1}",
                        "resultado": "sin_acceso" if i == 2 else "ok",
                        "observacion": "", "segundos": p.get("segundos", 5)}
                       for i, p in enumerate(pauta["puntos"])]}
    js, py = _js(pauta, ronda, tmp_path), _python(pauta, ronda)
    assert js == py
    assert js["estado"]["completa"] is False
    assert js["estado"]["respondidos"] == js["estado"]["total"]


def test_los_dos_coinciden_en_la_sospecha_de_firma(tmp_path):
    pauta = _pauta()

    def ronda_con(segundos):
        return {"id": "r", "checklist_id": pauta["id"], "activo_codigo": "EX-220",
                "operador": "x", "fecha": "2026-03-17",
                "items": [{"punto_id": f"{pauta['id']}.{i+1}", "resultado": "ok",
                           "observacion": "", "segundos": segundos}
                          for i in range(len(pauta["puntos"]))]}

    # Justo por debajo y justo por encima del umbral: donde los redondeos
    # separan dos implementaciones si se van a separar.
    for segundos in (1, 2, 3, 4, 8):
        r = ronda_con(segundos)
        assert _js(pauta, r, tmp_path) == _python(pauta, r), f"con {segundos} s/punto"


def _todos_nok(pauta: dict) -> dict:
    return {"id": "r", "checklist_id": pauta["id"], "activo_codigo": "EX-220",
            "operador": "x", "fecha": "2026-03-16",
            "items": [{"punto_id": f"{pauta['id']}.{i+1}", "resultado": "nok",
                       "observacion": f"algo en el punto {i+1}", "segundos": 9}
                      for i in range(len(pauta["puntos"]))]}


def test_los_dos_derivan_la_misma_severidad_del_alcance(tmp_path):
    # Fuera del alcance del operador → «detiene». Se decidió al escribir la
    # pauta, y los dos lenguajes tienen que leerlo igual.
    pauta = _pauta()
    ronda = _todos_nok(pauta)
    js, py = _js(pauta, ronda, tmp_path), _python(pauta, ronda)
    assert [a[1] for a in js["anomalias"]] == [a[1] for a in py["anomalias"]]
    severidades = [a[1] for a in js["anomalias"]]
    assert severidades.count("detiene") == 2       # freno y mangueras
    assert severidades.count("programable") == 3


# ═══════════ la única diferencia deliberada, fijada ═══════════

def test_el_telefono_NO_codifica_contra_el_catalogo_y_la_oficina_SI(tmp_path):
    """Es la única cosa en que los dos no coinciden, y es a propósito.

    El catálogo son 41 entradas con sus pistas y su ponderación; meterlo en
    la app de la ronda sería una tercera copia que mantener. El teléfono
    hereda el código sólo cuando la pauta lo declara. La oficina lo codifica
    al recibir el archivo, que es donde además está el análisis RCM.

    Si el teléfono empezara a codificar, o la oficina dejara de hacerlo,
    esta prueba se pone roja y hay que decidir a conciencia.
    """
    pauta = _pauta()
    ronda = _todos_nok(pauta)
    js, py = _js(pauta, ronda, tmp_path), _python(pauta, ronda)

    # Todo coincide salvo el código de catálogo (campo 4).
    sin_codigo = lambda d: [a[:4] + a[5:] for a in d["anomalias"]]  # noqa: E731
    assert sin_codigo(js) == sin_codigo(py)
    assert js["estado"] == py["estado"]

    codigos_js = [a[4] for a in js["anomalias"]]
    codigos_py = [a[4] for a in py["anomalias"]]
    # El punto 1 declara su código en la pauta: los dos lo heredan igual.
    assert codigos_js[0] == codigos_py[0] == "TER.SOBRECALENTAMIENTO.RADIADOR"
    # En los demás, el teléfono los deja vacíos y la oficina codifica lo que
    # el catálogo alcanza.
    assert all(c == "" for c in codigos_js[1:])
    assert any(c for c in codigos_py[1:]), (
        "la oficina debería codificar al menos uno de los textos libres")


def test_los_dos_coinciden_en_que_sin_acceso_no_genera_anomalia(tmp_path):
    pauta = _pauta()
    ronda = {"id": "r", "checklist_id": pauta["id"], "activo_codigo": "EX-220",
             "operador": "x", "fecha": "2026-03-16",
             "items": [{"punto_id": f"{pauta['id']}.{i+1}",
                        "resultado": "sin_acceso", "observacion": "guarda",
                        "segundos": 3} for i in range(len(pauta["puntos"]))]}
    js, py = _js(pauta, ronda, tmp_path), _python(pauta, ronda)
    assert js == py
    assert js["anomalias"] == []


def test_los_dos_usan_el_nombre_del_punto_cuando_no_hay_observacion(tmp_path):
    pauta = _pauta()
    ronda = {"id": "r", "checklist_id": pauta["id"], "activo_codigo": "EX-220",
             "operador": "x", "fecha": "2026-03-16",
             "items": [{"punto_id": f"{pauta['id']}.1", "resultado": "nok",
                        "observacion": "", "segundos": 9}]}
    js, py = _js(pauta, ronda, tmp_path), _python(pauta, ronda)
    assert js == py
    assert js["anomalias"][0][2] == pauta["puntos"][0]["punto"]


# ═══════════════ que el espejo esté al día ═══════════════

def test_la_app_publicada_es_la_que_sale_del_generador():
    # Si alguien edita la app a mano, o cambia una constante en Python y se
    # olvida de regenerar, esto se pone rojo. Es lo único que impide que las
    # dos copias se separen en silencio.
    import importlib.util

    ruta = RAIZ / "herramientas" / "espejo-ronda.py"
    spec = importlib.util.spec_from_file_location("espejo_ronda", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    esperado = modulo.construir(RAIZ / "herramientas" / "ronda")
    assert APP.read_text(encoding="utf-8") == esperado, (
        "docs/fixmate/ronda/index.html no está al día: corra "
        "`python herramientas/espejo-ronda.py`")


def test_las_constantes_del_javascript_son_las_de_python():
    from nefer.fixmate import anomalia as _an, tpm as _tpm

    html = APP.read_text(encoding="utf-8")
    for clase in _tpm.CLASES:
        assert f'"{clase}"' in html, f"falta la clase {clase} en la app"
    for sev in _an.SEVERIDADES:
        assert f'"{sev}"' in html, f"falta la severidad {sev} en la app"
    assert f"FRACCION_SOSPECHOSA = {_tpm.FRACCION_SOSPECHOSA}" in html


def test_el_ejemplo_del_telefono_es_lo_que_el_telefono_produce(tmp_path):
    """`ronda-ex220-telefono.json` es lo que sale del botón «Guardar», tal cual.

    Lo usa la pantalla de análisis RCM para cruzar la ronda con el análisis,
    y lo usa la guía de operación. Escrito a mano envejecería en silencio: si
    la app cambiara un campo, el ejemplo seguiría enseñando el formato viejo
    y el primero en descubrirlo sería un cliente.
    """
    import json as _json

    ejemplo = _json.loads((EJEMPLOS / "ronda-ex220-telefono.json")
                          .read_text(encoding="utf-8"))
    pauta, ejecucion = _pauta(), _ronda("ronda-ex220-hallazgo.json")
    js = _js(pauta, ejecucion, tmp_path)

    assert ejemplo["estado"] == js["estado"]
    resumen = [[a["id"], a["severidad"], a["descripcion"], a["componente"],
                a["codigo_catalogo"], a["modo_falla_id"]]
               for a in ejemplo["anomalias"]]
    assert resumen == js["anomalias"], (
        "el ejemplo del teléfono ya no coincide con lo que produce la app: "
        "vuelva a generarlo")
    # Y trae las tres partes que la oficina espera encontrar.
    assert set(ejemplo) == {"ejecucion", "anomalias", "estado"}
