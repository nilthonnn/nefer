"""Lo que la pantalla de «Armar» deja bajar, el resto de FixMate lo tiene que leer.

De `docs/fixmate/armar/index.html` sale el archivo que abren las otras dos
pantallas y que leen `cargador.checklist_de_dict` y
`cargador.analisis_de_dict`. Si el editor acepta algo que el cargador
rechaza, el error aparece **con la pauta ya bajada y el operador ya frente a
la máquina**, a 4.200 m y sin señal, que es el peor sitio posible para
descubrir que falta un criterio de aceptación. Y si el editor rechaza algo
que el cargador acepta, el planificador se queda trabado por un campo que al
producto no le hace falta.

Así que aquí se corren los dos juicios —el del JavaScript publicado y el de
Python— sobre los mismos borradores, y se comparan **verdicto por verdicto**.
No se comparan los mensajes: cada lenguaje reporta en su orden y uno puede
juntar varios errores donde el otro se detiene en el primero. Lo que no
puede diferir es *si pasa o no pasa*, que es lo único que cambia lo que le
ocurre al usuario.

El JavaScript se saca de la **pantalla publicada**, no de las partes: si
alguien la edita ahí a mano, esto lo mide.

Sin `node` instalado la prueba se salta; en CI está.
"""

from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
APP = RAIZ / "docs" / "fixmate" / "armar" / "index.html"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="hace falta node para correr el JS de la app")


def reglas_js() -> str:
    """Las reglas tal como están en la pantalla publicada, entre sus marcas."""
    html = APP.read_text(encoding="utf-8")
    m = re.search(r"/\* armar:reglas:inicio.*?\*/(.*?)/\* armar:reglas:fin \*/",
                  html, re.S)
    assert m, ("no se encontraron las reglas en la pantalla: faltan las marcas "
               "armar:reglas:inicio / armar:reglas:fin")
    # Los datos generados viven dentro de ese mismo tramo, así que vienen con
    # él: las constantes que compara esto son las que de verdad tiene la app.
    return m.group(1)


CONDUCTOR = """
%(reglas)s

var fs = require("fs");
var casos = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(casos.map(function (c) {
  var datos = armarJSON(c.tipo, c.borrador);
  return {
    nombre: c.nombre,
    archivo: datos,
    errores: erroresDeCarga(c.tipo, datos),
    avisos: avisosDeCalidad(c.tipo, datos)
  };
})));
"""


@pytest.fixture(scope="module")
def correr(tmp_path_factory):
    """Un solo arranque de node para toda la batería: arrancarlo por caso
    costaba más que todas las comparaciones juntas."""
    carpeta = tmp_path_factory.mktemp("cruce-armar")
    guion = carpeta / "cruce-armar.js"
    guion.write_text(CONDUCTOR % {"reglas": reglas_js()}, encoding="utf-8")

    def _correr(casos: list[dict]) -> list[dict]:
        entrada = carpeta / "casos.json"
        entrada.write_text(json.dumps(casos), encoding="utf-8")
        salida = subprocess.run(["node", str(guion), str(entrada)],
                                capture_output=True, text=True)
        assert salida.returncode == 0, salida.stderr
        return json.loads(salida.stdout)

    return _correr


def _python_rechaza(tipo: str, datos: dict) -> str:
    """El motivo por el que Python rechaza el archivo, o «» si lo acepta."""
    from nefer.fixmate import cargador

    try:
        if tipo == "pauta":
            cargador.checklist_de_dict(datos)
        else:
            cargador.analisis_de_dict(datos)
    except cargador.ErrorCargador as exc:
        return str(exc)
    return ""


# --------------------------------------------------------------- los casos

PUNTO_OK = {"clase": "inspeccionar", "punto": "visor de nivel del reductor",
            "criterio": "el nivel queda entre las dos marcas", "segundos": 30,
            "alcance_operador": True, "codigo_catalogo": "", "modo_falla_id": ""}


def pauta(**kw) -> dict:
    base = {"id": "", "activo_codigo": "EX-220-03", "nombre": "Ronda de arranque",
            "frecuencia": "por_turno", "origen": "manual OEM",
            "puntos": [dict(PUNTO_OK)]}
    base.update(kw)
    return base


MODO_OK = {"descripcion": "Corona de giro con desgaste en los dientes",
           "ubicacion": {"sistema": "giro", "subsistema": "", "componente": "corona"},
           "codigo_catalogo": "", "causa": "", "mecanismo": "", "evidente": "si",
           "efecto": {"local": "el giro se detiene", "observa_operador": "",
                      "parametro": "", "alarma": "", "componente_afectado": "",
                      "como_detectarlo": ""},
           "consecuencias": [{"clase": "operacional", "descripcion": "para el frente"}],
           "evidencia": [], "estado": "propuesto"}

FUNCION_OK = {"descripcion": "Girar la superestructura 360°",
              "estandar": "a 9 rpm con carga nominal de 2,1 m³",
              "tipo": "principal", "condicion": "",
              "fallas": [{"descripcion": "No gira", "modos": [dict(MODO_OK)]}]}


def analisis(**kw) -> dict:
    base = {"activo": {"codigo": "EX-220-03", "nombre": "Excavadora hidráulica",
                       "marca": "", "modelo": "", "serie": "", "categoria": "",
                       "instalacion": "", "contexto": ""},
            "contexto": "turno continuo, interior mina", "facilitador": "",
            "participantes": "", "fecha": "2026-10-08", "revision": "",
            "aprobado_por": "", "proxima_revision": "",
            "funciones": [json.loads(json.dumps(FUNCION_OK))]}
    base.update(kw)
    return base


def _modo(**kw) -> dict:
    """Un análisis con un solo modo al que se le cambia lo que haga falta."""
    a = analisis()
    a["funciones"][0]["fallas"][0]["modos"][0].update(kw)
    return a


def _funcion(**kw) -> dict:
    a = analisis()
    a["funciones"][0].update(kw)
    return a


CASOS: list[tuple[str, str, dict]] = [
    # --- la pauta de la ronda
    ("pauta mínima válida", "pauta", pauta()),
    ("pauta sin puntos", "pauta", pauta(puntos=[])),
    ("pauta sin código de activo", "pauta", pauta(activo_codigo="")),
    ("pauta con id escrito a mano", "pauta", pauta(id="pauta-vieja-2024")),
    ("pauta con frecuencia inventada", "pauta", pauta(frecuencia="cada luna")),
    ("punto con clase inventada", "pauta",
     pauta(puntos=[dict(PUNTO_OK, clase="detectar anomalias")])),
    ("punto sin sitio", "pauta", pauta(puntos=[dict(PUNTO_OK, punto="")])),
    ("punto sin criterio", "pauta", pauta(puntos=[dict(PUNTO_OK, criterio="")])),
    ("punto con código de catálogo real", "pauta",
     pauta(puntos=[dict(PUNTO_OK, codigo_catalogo="ADM.RESTRICCION.FILTRO")])),
    ("punto con código de catálogo inventado", "pauta",
     pauta(puntos=[dict(PUNTO_OK, codigo_catalogo="TER.PRUEBA.1")])),
    ("punto con los segundos escritos con unidad", "pauta",
     pauta(puntos=[dict(PUNTO_OK, segundos="30 s")])),
    ("punto fuera del alcance del operador", "pauta",
     pauta(puntos=[dict(PUNTO_OK, alcance_operador=False)])),
    ("pauta de diez puntos", "pauta",
     pauta(puntos=[dict(PUNTO_OK, punto=f"punto {i}") for i in range(10)])),

    # --- el análisis RCM
    ("análisis mínimo válido", "analisis", analisis()),
    ("análisis sin funciones", "analisis", analisis(funciones=[])),
    ("análisis sin activo", "analisis", analisis(activo={})),
    ("activo sin código", "analisis",
     analisis(activo={"codigo": "", "nombre": "Excavadora"})),
    ("activo sin nombre", "analisis",
     analisis(activo={"codigo": "EX-220-03", "nombre": ""})),
    ("fecha a la peruana", "analisis", analisis(fecha="03/04/2026")),
    ("fecha que no existe", "analisis", analisis(fecha="2026-02-30")),
    ("fecha vacía", "analisis", analisis(fecha="")),
    ("próxima revisión ambigua", "analisis", analisis(proxima_revision="15-03-27")),
    ("próxima revisión en ISO", "analisis", analisis(proxima_revision="2027-10-08")),
    ("función sin descripción", "analisis", _funcion(descripcion="")),
    ("función sin estándar", "analisis", _funcion(estandar="")),
    ("función con tipo inventado", "analisis", _funcion(tipo="terciaria")),
    ("función secundaria", "analisis", _funcion(tipo="secundaria")),
    ("función sin fallas", "analisis", _funcion(fallas=[])),
    ("falla funcional sin descripción", "analisis",
     _funcion(fallas=[{"descripcion": "", "modos": [dict(MODO_OK)]}])),
    ("falla funcional sin modos", "analisis",
     _funcion(fallas=[{"descripcion": "No gira", "modos": []}])),
    ("modo sin descripción", "analisis", _modo(descripcion="")),
    ("modo oculto", "analisis", _modo(evidente="no")),
    ("«oculta» puesta como consecuencia", "analisis",
     _modo(consecuencias=[{"clase": "oculta", "descripcion": ""}])),
    ("consecuencia de seguridad", "analisis",
     _modo(consecuencias=[{"clase": "seguridad", "descripcion": "aplasta"}])),
    ("modo sin consecuencias", "analisis", _modo(consecuencias=[])),
    ("modo validado sin evidencia", "analisis", _modo(estado="validado")),
    ("modo validado con evidencia", "analisis",
     _modo(estado="validado",
           evidencia=[{"fuente": "historial", "referencia": "informe 2026-0412",
                       "nota": ""}])),
    ("modo con estado inventado", "analisis", _modo(estado="revisado")),
    ("evidencia con fuente inventada", "analisis",
     _modo(evidencia=[{"fuente": "rumor", "referencia": "x", "nota": ""}])),
    ("evidencia sin referencia", "analisis",
     _modo(evidencia=[{"fuente": "operador", "referencia": "", "nota": ""}])),
    ("modo con código de catálogo real", "analisis",
     _modo(codigo_catalogo="ADM.RESTRICCION.FILTRO")),
    ("modo con código de catálogo inventado", "analisis",
     _modo(codigo_catalogo="GIR.DESGASTE.CORONA")),
    ("participantes en una línea", "analisis",
     analisis(participantes="J. Quispe, M. Rojas; L. Ccahuana")),
]


def _barrido() -> list[tuple[str, str, dict]]:
    """El barrido combinatorio: donde se cuelan las diferencias que un caso
    escrito a mano no toca, porque nadie escribe a mano «frecuencia semanal
    con clase inventada»."""
    casos = []
    clases = ["limpiar", "inspeccionar", "lubricar", "ajustar", "verificar",
              "detectar anomalias", ""]
    frecuencias = ["por_turno", "diaria", "semanal", "quincenal", "mensual",
                   "por_horas", "cada luna"]
    for clase, frecuencia in itertools.product(clases, frecuencias):
        casos.append((f"barrido pauta · {clase or '(vacía)'} · {frecuencia}",
                      "pauta",
                      pauta(frecuencia=frecuencia,
                            puntos=[dict(PUNTO_OK, clase=clase)])))

    consecuencias = ["seguridad", "ambiental", "operacional", "produccion",
                     "economica", "no-significativa", "oculta", ""]
    estados = ["propuesto", "validado", "descartado", "revisado"]
    for clase, estado, con_evidencia in itertools.product(
            consecuencias, estados, (False, True)):
        ev = [{"fuente": "manual", "referencia": "sección 4.2", "nota": ""}] \
            if con_evidencia else []
        casos.append((
            f"barrido modo · {clase or '(vacía)'} · {estado} · "
            f"{'con' if con_evidencia else 'sin'} evidencia",
            "analisis",
            _modo(consecuencias=[{"clase": clase, "descripcion": ""}],
                  estado=estado, evidencia=ev)))
    return casos


TODOS = CASOS + _barrido()


@pytest.fixture(scope="module")
def juicios(correr):
    casos = [{"nombre": n, "tipo": t, "borrador": _para_js(t, b)}
             for n, t, b in TODOS]
    return dict(zip([c["nombre"] for c in casos], correr(casos)))


def _para_js(tipo: str, borrador: dict) -> dict:
    """El borrador tal como lo tiene la pantalla. Para el análisis, la
    pantalla guarda `evidente` como «si»/«no» —sale de un desplegable— y los
    participantes en una sola línea; `armarJSON` los traduce. Aquí se le pasa
    en esa forma, que es la que de verdad va a recibir."""
    return json.loads(json.dumps(borrador))


def test_hay_casos():
    """Si el barrido se queda en nada, el resto de la prueba pasa sin medir."""
    assert len(TODOS) > 100, f"solo {len(TODOS)} casos"


@pytest.mark.parametrize("nombre,tipo,borrador", TODOS,
                         ids=[c[0] for c in TODOS])
def test_el_mismo_verdicto(juicios, nombre, tipo, borrador):
    """Lo que la pantalla deja bajar es exactamente lo que Python lee."""
    j = juicios[nombre]
    motivo = _python_rechaza(tipo, j["archivo"])
    js_rechaza = bool(j["errores"])
    if js_rechaza and not motivo:
        pytest.fail(
            f"«{nombre}»: la pantalla lo frena y Python lo acepta. El "
            f"planificador queda trabado por algo que al producto no le hace "
            f"falta.\n  pantalla: {j['errores']}")
    if motivo and not js_rechaza:
        pytest.fail(
            f"«{nombre}»: la pantalla lo deja bajar y Python lo rechaza. El "
            f"error aparecería con el archivo ya en el teléfono.\n"
            f"  python: {motivo}\n  archivo: {json.dumps(j['archivo'], ensure_ascii=False)[:400]}")


def test_la_pauta_valida_llega_entera(juicios):
    """No basta con que cargue: tiene que cargar con lo que se escribió."""
    from nefer.fixmate import cargador

    archivo = juicios["pauta mínima válida"]["archivo"]
    c = cargador.checklist_de_dict(archivo)
    assert c.activo_codigo == "EX-220-03"
    assert c.frecuencia == "por_turno"
    assert len(c.puntos) == 1
    assert c.puntos[0].clase == "inspeccionar"
    assert c.puntos[0].criterio == "el nivel queda entre las dos marcas"
    assert c.puntos[0].segundos == 30
    assert c.presupuesto_seg == 30
    # El id no se le pide al planificador: se deriva del activo y la
    # frecuencia, que es lo que lo hace único.
    assert c.id == "pauta-ex-220-03-por_turno"


def test_el_id_escrito_a_mano_gana(juicios):
    """Una pauta que ya existe tiene su id, y hay que poder conservarlo."""
    from nefer.fixmate import cargador

    c = cargador.checklist_de_dict(juicios["pauta con id escrito a mano"]["archivo"])
    assert c.id == "pauta-vieja-2024"
    assert c.puntos[0].id == "pauta-vieja-2024.1"


def test_el_analisis_valido_llega_entero(juicios):
    from nefer.fixmate import cargador

    a = cargador.analisis_de_dict(juicios["análisis mínimo válido"]["archivo"])
    assert a.activo.codigo == "EX-220-03"
    assert len(a.funciones) == 1 and len(a.fallas) == 1 and len(a.modos) == 1
    assert a.funciones[0].id == "F1"
    assert a.fallas[0].id == "F1.1"
    assert a.modos[0].id == "F1.1.1"
    assert a.modos[0].clases == ("operacional",)
    assert a.modos[0].evidente is True


def test_el_modo_oculto_llega_como_booleano(juicios):
    """La primera bifurcación de RCM no puede llegar como el texto «no»."""
    from nefer.fixmate import cargador

    a = cargador.analisis_de_dict(juicios["modo oculto"]["archivo"])
    assert a.modos[0].evidente is False
    assert a.modos_ocultos()


def test_los_participantes_salen_como_lista(juicios):
    from nefer.fixmate import cargador

    a = cargador.analisis_de_dict(juicios["participantes en una línea"]["archivo"])
    assert a.participantes == ("J. Quispe", "M. Rojas", "L. Ccahuana")


def test_la_herencia_del_catalogo_es_la_de_python(juicios):
    """`armarJSON` no inventa causa ni mecanismo: los deja vacíos y el
    cargador los hereda del catálogo, igual que `desde_catalogo()`."""
    from nefer.fixmate import cargador

    a = cargador.analisis_de_dict(
        juicios["modo con código de catálogo real"]["archivo"])
    assert a.modos[0].causa == "Filtro de aire colmatado"
    assert a.modos[0].mecanismo == "Obstruccion"


def test_oculta_como_consecuencia_se_frena_y_se_explica(juicios):
    """Es el error clásico, y el mensaje tiene que decir dónde va de verdad."""
    errores = juicios["«oculta» puesta como consecuencia"]["errores"]
    assert errores
    assert any("evidente" in e for e in errores), errores


def test_los_avisos_no_frenan_nada(juicios):
    """Un análisis sin revisión ni aprobación carga perfecto: es un hueco, no
    un error. Mezclarlos tiene las dos consecuencias malas."""
    j = juicios["análisis mínimo válido"]
    assert not j["errores"]
    assert j["avisos"], "un análisis sin revisión ni participantes tiene huecos"
    assert any("revision" in a or "revisión" in a for a in j["avisos"]), j["avisos"]


def test_la_pauta_sin_puntos_carga_pero_se_dice(juicios):
    """Python la acepta —es una pauta vacía, no un archivo roto— y por eso no
    puede ser un error de carga. Lo que no puede es pasar en silencio."""
    j = juicios["pauta sin puntos"]
    assert not j["errores"]
    assert any("ningun punto" in a or "ningún punto" in a for a in j["avisos"]), \
        j["avisos"]
