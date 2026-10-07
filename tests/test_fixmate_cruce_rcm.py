"""La pantalla y la oficina tienen que decidir lo mismo sobre un modo de falla.

El árbol de decisión de RCM se recorre dos veces: en el JavaScript de
`docs/fixmate/rcm/index.html`, donde el equipo de análisis lo contesta en
vivo, y en `nefer/fixmate/decision.py`, que corre cuando el archivo vuelve a
la oficina y de ahí sale el plan, la matriz FMECA y el tablero.

Dos copias que se separan **no dan error en ninguna parte**: la pantalla dice
«operar hasta la falla» y la oficina dice «rediseño obligatorio» sobre el
mismo modo de falla de seguridad, las dos se ven razonables, y la que queda
firmada es la que alguien imprimió primero. Por eso aquí se recorren **las
729 combinaciones** de respuestas —tres estados en seis preguntas— por cada
clase de consecuencia, evidente y oculta, y se comparan dictamen por
dictamen: estrategia, motivo, camino completo, avisos y banderas.

El JavaScript se saca de la **pantalla publicada**, no de una copia: si
alguien lo edita ahí, esto lo mide.

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
APP = RAIZ / "docs" / "fixmate" / "rcm" / "index.html"
EJEMPLOS = RAIZ / "ejemplos" / "rcm-tpm"

from nefer.fixmate import cargador, decision, rcm  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="hace falta node para correr el JS de la pantalla")

TRI = (True, False, None)
CAMPOS = cargador.CAMPOS_DECISION


def reglas_js() -> str:
    """Las reglas tal como están en la pantalla publicada, entre sus marcas."""
    html = APP.read_text(encoding="utf-8")
    m = re.search(r"/\* rcm:reglas:inicio.*?\*/(.*?)/\* rcm:reglas:fin \*/",
                  html, re.S)
    assert m, ("no se encontraron las reglas en la pantalla: faltan las marcas "
               "rcm:reglas:inicio / rcm:reglas:fin")
    return m.group(1)


CONDUCTOR = """
%(reglas)s

var fs = require("fs");
var entrada = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

function plano(d) {
  return { estrategia: d.estrategia, rotulo: d.rotulo, motivo: d.motivo,
           por_defecto: d.por_defecto,
           bloqueado_por_seguridad: d.bloqueado_por_seguridad,
           incompleta: d.incompleta, avisos: d.avisos,
           camino: d.camino.map(function (p) {
             return { pregunta: p.pregunta, respuesta: p.respuesta,
                      consecuencia: p.consecuencia };
           }) };
}

var salida;
if (entrada.job === "arbol") {
  salida = entrada.casos.map(function (c) {
    return plano(decidir(c.modo, c.respuestas));
  });
} else if (entrada.job === "enlace") {
  salida = entrada.casos.map(function (c) {
    var a = normalizarAnalisis(c.analisis);
    return enlazarAnomalia(c.anomalia, a).modo_falla_id;
  });
} else {
  salida = entrada.casos.map(function (doc) {
    var a = normalizarAnalisis(doc);
    var decisiones = {};
    a.modos.forEach(function (m) {
      if (m.decision) decisiones[m.id] = decidir(m, m.decision);
    });
    return {
      ids: {
        funciones: a.funciones.map(function (f) { return f.id; }),
        fallas: a.fallas.map(function (f) { return f.id; }),
        modos: a.modos.map(function (m) { return m.id; })
      },
      completitud: completitud(a, decisiones),
      resumen: resumenRCM(a, decisiones),
      dictamenes: Object.keys(decisiones).map(function (mid) {
        return [mid, plano(decisiones[mid])];
      })
    };
  });
}
process.stdout.write(JSON.stringify(salida));
"""


def _node(job: str, casos: list, tmp_path: Path) -> list:
    guion = tmp_path / "cruce-rcm.js"
    guion.write_text(CONDUCTOR % {"reglas": reglas_js()}, encoding="utf-8")
    entrada = tmp_path / "casos.json"
    entrada.write_text(json.dumps({"job": job, "casos": casos},
                                  ensure_ascii=False), encoding="utf-8")
    salida = subprocess.run(["node", str(guion), str(entrada)],
                            capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


# ═══════════════════ el árbol, combinación por combinación ═══════════════════

def _modo(clases: tuple[str, ...], evidente: bool) -> rcm.ModoFalla:
    return rcm.ModoFalla(
        id="F1.1.1", falla_funcional_id="F1.1",
        descripcion="modo de prueba", evidente=evidente,
        consecuencias=tuple(rcm.Consecuencia(c) for c in clases))


# Las seis clases de la rama evidente, más el modo sin consecuencia
# clasificada: ese es el estado real de un análisis a medio hacer.
ESCENARIOS = [(c,) for c in rcm.CLASES_CONSECUENCIA] + [()]


def test_el_arbol_decide_lo_mismo_en_las_729_combinaciones(tmp_path):
    casos_js, esperado = [], []
    for clases, evidente in itertools.product(ESCENARIOS, (True, False)):
        modo = _modo(clases, evidente)
        modo_js = {"evidente": evidente,
                   "consecuencias": [{"clase": c} for c in clases]}
        for valores in itertools.product(TRI, repeat=len(CAMPOS)):
            r = dict(zip(CAMPOS, valores))
            casos_js.append({"modo": modo_js, "respuestas": r})
            esperado.append(decision.decidir(modo, decision.Respuestas(**r)).a_dict())

    assert len(casos_js) == len(ESCENARIOS) * 2 * 3 ** len(CAMPOS) == 14 * 729
    obtenido = _node("arbol", casos_js, tmp_path)

    # El primer desacuerdo se reporta con su caso, que es lo que hace falta
    # para arreglarlo: con 10.206 dictámenes, «no son iguales» no sirve.
    for caso, js, py in zip(casos_js, obtenido, esperado):
        assert js == py, (
            f"desacuerdo con evidente={caso['modo']['evidente']}, "
            f"consecuencias={caso['modo']['consecuencias']}, "
            f"respuestas={caso['respuestas']}\n  JS: {js}\n  PY: {py}")


def test_el_arbol_nunca_deja_operar_hasta_la_falla_una_falla_grave(tmp_path):
    """La guarda que no se negocia, comprobada en los dos lenguajes.

    No es una propiedad del código: es el motivo por el que existe el árbol.
    Un árbol que permita cerrar un modo de falla de seguridad con «operar
    hasta la falla» es peor que no tener árbol, porque firma la omisión.
    """
    casos_js, graves = [], []
    for clase in sorted(rcm.CONSECUENCIAS_GRAVES):
        modo = _modo((clase,), True)
        for valores in itertools.product(TRI, repeat=len(CAMPOS)):
            r = dict(zip(CAMPOS, valores))
            casos_js.append({"modo": {"evidente": True,
                                      "consecuencias": [{"clase": clase}]},
                             "respuestas": r})
            graves.append(decision.decidir(modo, decision.Respuestas(**r)))

    js = _node("arbol", casos_js, tmp_path)
    assert all(d.estrategia != "operar_hasta_falla" for d in graves)
    assert all(d["estrategia"] != "operar_hasta_falla" for d in js)
    # Y donde no hubo tarea proactiva, los dos dicen rediseño obligatorio.
    for caso, a, b in zip(casos_js, js, graves):
        assert a["bloqueado_por_seguridad"] == b.bloqueado_por_seguridad, caso
        if a["bloqueado_por_seguridad"]:
            assert a["estrategia"] == b.estrategia == "rediseno"


def test_los_dos_tratan_la_falla_oculta_antes_que_la_consecuencia(tmp_path):
    """Oculta es la primera bifurcación, no una categoría más.

    Con `probable=True`, un modo oculto sale a búsqueda de fallas sea cual
    sea su clase de consecuencia: el riesgo que se trata es la falla
    múltiple. Si un lenguaje empezara por la consecuencia, esto se separa.
    """
    casos_js, py = [], []
    for clases in ESCENARIOS:
        modo = _modo(clases, False)
        r = {"probable": True, "detectable": False, "intervalo_edad": False,
             "restaurable": False, "viable": True, "costo_efectiva": None}
        casos_js.append({"modo": {"evidente": False,
                                  "consecuencias": [{"clase": c} for c in clases]},
                         "respuestas": r})
        py.append(decision.decidir(modo, decision.Respuestas(**r)))

    js = _node("arbol", casos_js, tmp_path)
    assert all(d.estrategia == "busqueda_fallas" for d in py)
    assert all(d["estrategia"] == "busqueda_fallas" for d in js)
    assert all(d["camino"][0]["respuesta"] == "no" for d in js)
    assert all("falla multiple" in d["camino"][0]["consecuencia"] for d in js)


def test_los_dos_avisan_igual_cuando_no_hay_datos_economicos(tmp_path):
    # §18 de la misión: sin datos económicos no se declara ahorro, y el aviso
    # tiene que ser el mismo texto en los dos lados.
    modo = _modo(("economica",), True)
    r = {"detectable": True, "viable": True, "intervalo_edad": False,
         "restaurable": False, "probable": None, "costo_efectiva": None}
    js = _node("arbol", [{"modo": {"evidente": True,
                                   "consecuencias": [{"clase": "economica"}]},
                          "respuestas": r}], tmp_path)[0]
    py = decision.decidir(modo, decision.Respuestas(**r)).a_dict()
    assert js == py
    assert decision.SIN_DATOS_ECONOMICOS in js["avisos"]
    assert "no se declara ahorro" in decision.SIN_DATOS_ECONOMICOS


# ═══════════════════ el análisis completo y su completitud ═══════════════════

def _ejemplo() -> dict:
    return json.loads((EJEMPLOS / "analisis-ex220.json").read_text(encoding="utf-8"))


def _sin_decisiones(doc: dict) -> dict:
    for f in doc["funciones"]:
        for ff in f["fallas"]:
            for m in ff["modos"]:
                m.pop("decision", None)
    return doc


def _casos_analisis() -> list[dict]:
    """Un análisis completo y cinco maneras de que no lo esté.

    Cada una rompe una pregunta distinta de JA1011, que es donde las dos
    implementaciones del informe de completitud se pueden separar.
    """
    casos = [_ejemplo(), _sin_decisiones(_ejemplo())]

    sin_falla = _ejemplo()
    sin_falla["funciones"].append({
        "descripcion": "Señalizar su posición al resto del frente",
        "estandar": "Baliza visible a 50 m en polvo", "fallas": []})
    casos.append(sin_falla)

    sin_modo = _ejemplo()
    sin_modo["funciones"][0]["fallas"].append(
        {"descripcion": "La temperatura no llega a régimen", "modos": []})
    casos.append(sin_modo)

    sin_efecto = _ejemplo()
    sin_efecto["funciones"][0]["fallas"][0]["modos"][1]["efecto"] = {}
    casos.append(sin_efecto)

    sin_consec = _ejemplo()
    sin_consec["funciones"][0]["fallas"][0]["modos"][0]["consecuencias"] = []
    casos.append(sin_consec)

    return casos


def _python_analisis(doc: dict) -> dict:
    a = cargador.analisis_de_dict(doc)
    d = cargador.decisiones_de_dict(doc, a)
    return {
        "ids": {"funciones": [f.id for f in a.funciones],
                "fallas": [f.id for f in a.fallas],
                "modos": [m.id for m in a.modos]},
        "completitud": rcm.completitud(a, d.por_modo).a_dict(),
        "resumen": decision.resumen(a, d),
        "dictamenes": [[mid, dic.a_dict()] for mid, dic in d.por_modo.items()],
    }


@pytest.mark.parametrize("i", range(len(_casos_analisis())))
def test_los_dos_leen_el_mismo_analisis_igual(i, tmp_path):
    doc = _casos_analisis()[i]
    js = _node("analisis", [doc], tmp_path)[0]
    py = _python_analisis(doc)
    # Los ids se reconstruyen por posición en los dos lados: si se numeraran
    # distinto, las decisiones no casarían con sus modos al volver.
    assert js["ids"] == py["ids"]
    assert js["completitud"] == py["completitud"]
    assert js["resumen"] == py["resumen"]
    assert js["dictamenes"] == py["dictamenes"]


def test_el_ejemplo_no_esta_completo_y_los_dos_dicen_por_que(tmp_path):
    # El análisis de ejemplo tiene los cuatro modos decididos, así que las
    # siete quedan contestadas. Quitarle las decisiones deja Q6 y Q7 abiertas
    # —sin romper la cadena— y eso es lo que los dos tienen que informar.
    doc = _sin_decisiones(_ejemplo())
    js = _node("analisis", [doc], tmp_path)[0]["completitud"]
    py = rcm.completitud(cargador.analisis_de_dict(doc)).a_dict()
    assert js == py
    assert js["completo"] is False
    assert js["rompe_cadena"] is False
    pendientes = [r["numero"] for r in js["respuestas"] if not r["contestada"]]
    assert pendientes == [6, 7]


def test_el_analisis_de_ejemplo_si_esta_completo(tmp_path):
    doc = _ejemplo()
    js = _node("analisis", [doc], tmp_path)[0]
    assert js["completitud"]["completo"] is True
    assert js["completitud"]["contestadas"] == 7
    # Y reparte las cuatro estrategias que el ejemplo promete.
    assert js["resumen"]["reparto"]["cbm"] == 1
    assert js["resumen"]["reparto"]["descarte"] == 1
    assert js["resumen"]["reparto"]["busqueda_fallas"] == 1
    assert js["resumen"]["reparto"]["rediseno"] == 1
    assert js["resumen"]["rediseños_obligatorios"] == 1


# ═══════════ las diferencias deliberadas, fijadas ═══════════

def test_la_pantalla_NO_evalua_criticidad_ni_arma_la_matriz_FMECA():
    """Lo que la pantalla no hace, y está dicho en ella.

    Son decisiones de dónde vive cada cosa, no funciones a medio hacer:

      - La criticidad se evalúa con el método configurado de la planta, que
        vive en `criticidad.py` con sus matrices. Traerlo al navegador sería
        una segunda copia de una tabla que cada planta cambia.
      - La matriz FMECA tiene treinta columnas definidas en `fmeca.py` y sale
        del comando. Lo de la pantalla es un resumen para mirar.

    Si alguien implementara cualquiera de las dos en el JavaScript, esta
    prueba se pone roja y hay que decidirlo a conciencia.
    """
    from nefer.fixmate import criticidad as _crit, fmeca as _fmeca

    reglas = reglas_js()
    # Ni las etiquetas de los niveles ni las columnas de la matriz están ahí.
    for factor in _crit.PRIORIDAD_EJEMPLO.factores:
        for nivel in factor.niveles:
            assert nivel.etiqueta not in reglas, (
                f"la escala de criticidad «{nivel.etiqueta}» no debería estar "
                "en el JavaScript: la evalúa la oficina")
    # Ni las treinta columnas ni la cabecera del CSV están en la pantalla.
    # Se comprueba por la cabecera y no nombre por nombre: media docena de
    # esos nombres —«activo», «causa», «consecuencias»— son campos del modelo
    # y por supuesto aparecen; lo que no debe aparecer es la matriz.
    html = APP.read_text(encoding="utf-8")
    assert ";".join(_fmeca.COLUMNAS) not in html
    assert ",".join(_fmeca.COLUMNAS) not in html
    assert "COLUMNAS" not in reglas
    assert "csv" not in reglas.lower(), "el CSV lo escribe fmeca.py, no la pantalla"

    assert "No evalúa criticidad" in html
    assert "No arma la matriz FMECA" in html
    assert _crit.ADVERTENCIA_RPN in html, (
        "si el método declarado es RPN, la pantalla tiene que advertirlo")


def test_la_pantalla_no_trae_el_catalogo_iso_14224():
    from nefer.fixmate import catalogo as _cat

    reglas = reglas_js()
    entradas = _cat.DE_FABRICA
    presentes = [e.codigo for e in entradas if e.codigo in reglas]
    assert not presentes, (
        "el catálogo no va en el JavaScript: son 41 entradas con sus pistas y "
        f"su ponderación, y ya hay una copia en la app de diagnóstico {presentes}")


# ═══════════════ que el espejo esté al día ═══════════════

def test_la_pantalla_publicada_es_la_que_sale_del_generador():
    # Si alguien la edita a mano, o cambia una constante en Python y se olvida
    # de regenerar, esto se pone rojo. Es lo único que impide que las dos
    # copias se separen en silencio.
    import importlib.util

    ruta = RAIZ / "herramientas" / "espejo-rcm.py"
    spec = importlib.util.spec_from_file_location("espejo_rcm", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    esperado = modulo.construir(RAIZ / "herramientas" / "rcm")
    assert APP.read_text(encoding="utf-8") == esperado, (
        "docs/fixmate/rcm/index.html no está al día: corra "
        "`python herramientas/espejo-rcm.py`")


def test_las_constantes_del_javascript_son_las_de_python():
    html = APP.read_text(encoding="utf-8")
    for clave, rotulo in decision.ESTRATEGIAS.items():
        assert f'"{clave}": "{rotulo}"' in html, f"falta la estrategia {clave}"
    for clase in rcm.CLASES_CONSECUENCIA:
        assert f'"{clase}"' in html, f"falta la clase de consecuencia {clase}"
    for pregunta in rcm.PREGUNTAS:
        assert pregunta.texto in html, f"falta la Q{pregunta.numero} de JA1011"
    for aviso in (decision.SIN_DATOS_ECONOMICOS, decision.AVISO_SIN_EVALUAR,
                  decision.AVISO_89):
        assert aviso in html
    # Y «oculta» no es una clase de consecuencia en ninguno de los dos lados.
    assert "oculta" not in rcm.CLASES_CONSECUENCIA


# ═══════════ el enganche de la ronda con el análisis ═══════════

def _anomalia(**kw):
    base = {"id": "a1", "activo_codigo": "EX-220", "descripcion": "algo",
            "codigo_catalogo": "", "modo_falla_id": ""}
    base.update(kw)
    return base


def _casos_enlace() -> list[dict]:
    """Los cinco caminos del enganche, y los dos que no enganchan a propósito.

    Es la regla que decide si un hallazgo del operador cuenta como evidencia
    de un modo de falla. Enganchar al modo equivocado contamina la frecuencia
    por modo y la decisión de estrategia que sale de ahí, así que los dos
    lenguajes tienen que negarse en los mismos casos.
    """
    doc = _ejemplo()
    dos_veces = _ejemplo()
    # Dos modos con el mismo código: una ambigüedad del análisis.
    dos_veces["funciones"][0]["fallas"][0]["modos"][1]["codigo_catalogo"] = \
        "TER.SOBRECALENTAMIENTO.RADIADOR"
    return [
        # La pauta declaró el modo: no se toca.
        {"analisis": doc, "anomalia": _anomalia(modo_falla_id="F1.1.2",
                                                codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")},
        # Por código exacto, con un solo candidato.
        {"analisis": doc, "anomalia": _anomalia(codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")},
        # Sin código: el teléfono no clasifica texto libre.
        {"analisis": doc, "anomalia": _anomalia()},
        # Código que ningún modo declara.
        {"analisis": doc, "anomalia": _anomalia(codigo_catalogo="HID.FUGA.MANGUERA")},
        # Otro activo.
        {"analisis": doc, "anomalia": _anomalia(activo_codigo="EX-999",
                                                codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")},
        # Dos modos con el mismo código: no se elige.
        {"analisis": dos_veces, "anomalia": _anomalia(codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")},
    ]


def test_los_dos_enganchan_la_ronda_con_el_analisis_igual(tmp_path):
    from nefer.fixmate.anomalia import Anomalia, enlazar

    casos = _casos_enlace()
    js = _node("enlace", casos, tmp_path)
    py = []
    for caso in casos:
        a = Anomalia(**{k: v for k, v in caso["anomalia"].items()})
        py.append(enlazar(a, cargador.analisis_de_dict(caso["analisis"])).modo_falla_id)
    assert js == py
    # Y lo que tiene que salir: engancha por declaración y por código, y se
    # niega en los otros cuatro.
    assert py == ["F1.1.2", "F1.1.1", "", "", "", ""]


def test_la_pantalla_no_engancha_al_modo_mas_parecido(tmp_path):
    """La negativa que importa: dos modos con el mismo código no se resuelven
    a la suerte, y un código que nadie declara no se aproxima."""
    doc = _ejemplo()
    casi = _anomalia(codigo_catalogo="TER.SOBRECALENTAMIENTO.VENTILADOR")
    doc["funciones"][0]["fallas"][0]["modos"][1]["codigo_catalogo"] = ""
    js = _node("enlace", [{"analisis": doc, "anomalia": casi}], tmp_path)
    assert js == [""], "se enganchó con un modo que ya no declara ese código"
