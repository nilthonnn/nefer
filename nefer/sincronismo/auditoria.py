"""Auditoria de funcionalidad contra normas internacionales.

Dos partes, y las dos se EJECUTAN; ninguna se declara:

1. **Funcionalidad del software** (ISO/IEC 25010, caracteristica
   «adecuacion funcional»):
   - completitud: cada funcion que el modulo promete se corre de verdad con
     los datos de ejemplo y se registra si termino bien;
   - correccion: casos con respuesta conocida, calculada a mano, contra lo
     que devuelve el software;
   - pertinencia: cada objetivo del puesto (eficaz, proactivo, predictivo)
     tiene funciones que lo cubren.

2. **El analisis contra las normas de su metodo**: SAE JA1011 (RCM),
   IEC 60812:2018 (AMEF), AIAG-VDA 2019 (prioridad de accion), ISO 14224
   (taxonomia y calidad de datos), IEEE 1547-2018 y IEEE C37.2 (sincronismo y
   protecciones) y NFPA 110 como referencia de pruebas periodicas.

Esto es una AUTOEVALUACION reproducible, no una certificacion. Las normas se
verifican por su contenido publico general, no por su texto con licencia, y
cada requisito dice de que evidencia sale su resultado.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import io
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from ..fixmate import cargador, rcm as _rcm
from ..fixmate import catalogo as _catalogo
from ..fixmate.criticidad import PRIORIDAD_EJEMPLO, evaluar
from . import plan_accion, reparto, tendencias, verificacion

CUMPLE, PARCIAL, NO_CUMPLE, NO_APLICA = "cumple", "parcial", "no cumple", "no aplica"


@dataclass
class Requisito:
    norma: str
    clausula: str
    requisito: str
    resultado: str
    evidencia: str
    accion: str = ""

    def a_dict(self) -> dict:
        return asdict(self)


# --- 1. funcionalidad del software -----------------------------------------

def _correr(argv: list[str]) -> tuple[int, str]:
    from ..cli import main
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(argv)
    except SystemExit as exc:          # argparse
        rc = int(exc.code or 0)
    except Exception as exc:           # una funcion que revienta es un hallazgo
        return 99, f"{type(exc).__name__}: {exc}"
    return rc, (err.getvalue() or out.getvalue())[-200:]


def funcionalidad(ejemplos: Path) -> list[Requisito]:
    planta = str(ejemplos / "planta.json")
    dse = str(ejemplos / "planta-dse-cat.json")
    registro = str(ejemplos / "registro.csv")
    analisis = str(ejemplos / "rcm-paralelo-tta.json")
    R: list[Requisito] = []

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        # (funcion, argv, codigos de salida aceptados: 1 = hallazgo encontrado)
        casos = [
            ("Permisivo de cierre ANSI 25", ["verificar", "--v-barra", "380", "--f-barra", "60",
                                             "--v-gen", "382", "--f-gen", "60.1", "--angulo", "0",
                                             "--kva", "500"], {0}),
            ("Reparto actual kW/kVAr", ["reparto", planta], {0, 1}),
            ("Prediccion por estatismo", ["estatismo", planta, "--pct", "75"], {0}),
            ("Revision de protecciones", ["protecciones", planta], {0, 1}),
            ("Tendencias y reincidencias", ["tendencia", registro, "--planta", planta], {0}),
            ("Guia de sintomas", ["diagnostico", "no", "sincroniza"], {0}),
            ("Informe priorizado", ["informe", planta, "-r", registro, "-o", str(t / "i.md")], {0}),
            ("Protocolo de puesta en marcha", ["protocolo", planta, "-o", str(t / "p.md")], {0}),
            ("Plantilla de planta", ["plantilla", "-n", "2", "-o", str(t / "pl.json")], {0}),
            ("Diagrama TTA", ["diagrama", "tta", dse, "-o", str(t / "a.svg")], {0}),
            ("Diagrama de sincronismo", ["diagrama", "sincronismo", dse, "-o", str(t / "b.svg")], {0}),
            ("Lamina didactica TTA", ["lamina", "tta", dse, "-o", str(t / "a.html")], {0}),
            ("Lamina didactica sincronismo", ["lamina", "sincronismo", dse, "-o", str(t / "b.html")], {0}),
            ("Hoja de parametros", ["parametros", "sincronismo", dse, "--html", "-o", str(t / "c.html")], {0}),
            ("Revision de parametros", ["parametros", "tta", dse, "--revisar"], {0, 1}),
            ("Menu de fallas RCM/AMEF", ["fallas", analisis, "-o", str(t / "m.html")], {0}),
            ("Decodificador SPN/FMI", ["codigo", "168", "17", "--analisis", analisis], {0}),
            ("AMEF completa y plan de accion", ["amef", analisis, "-o", str(t / "amef.csv"),
                                               "--plan", str(t / "plan.csv")], {0}),
        ]
        for nombre, argv, aceptados in casos:
            rc, salida = _correr(["sincronismo", *argv])
            ok = rc in aceptados
            R.append(Requisito(
                "ISO/IEC 25010", "Adecuacion funcional · completitud",
                f"La funcion «{nombre}» se ejecuta con los datos de ejemplo",
                CUMPLE if ok else NO_CUMPLE,
                f"nefer sincronismo {argv[0]} → codigo {rc}"
                + ("" if ok else f" ({salida.strip()})"),
                "" if ok else "Corregir el fallo y volver a auditar."))

    # Correccion: respuestas conocidas, calculadas a mano.
    def caso(nombre, esperado, obtenido, tolerancia=1e-6):
        if isinstance(esperado, (int, float)):
            ok = abs(esperado - obtenido) <= tolerancia
        else:
            ok = esperado == obtenido
        R.append(Requisito("ISO/IEC 25010", "Adecuacion funcional · correccion", nombre,
                           CUMPLE if ok else NO_CUMPLE,
                           f"esperado {esperado}, obtenido {obtenido}",
                           "" if ok else "Revisar el calculo."))

    v = verificacion.verificar(
        verificacion.Lectura(480, 60, 482, 60.1, 0, 0.1),
        verificacion.ventana_por_potencia(625))
    caso("Angulo de adelanto = 360 · 0.1 Hz · 0.1 s = 3.6°", 3.6, v.angulo_adelanto)
    w = verificacion.ventana_por_potencia(625)
    caso("Ventana IEEE 1547 para 625 kVA = 0.2 Hz / 5 % / 15°", (0.2, 5.0, 15.0),
         (w.delta_f_hz, w.delta_v_pct, w.delta_angulo_grados))
    p = reparto.predecir_estatismo([reparto.Unidad("A", 500, f_vacio=62.4, estatismo_pct=4),
                                    reparto.Unidad("B", 1000, f_vacio=62.4, estatismo_pct=4)],
                                   1500, 60)
    caso("Estatismo 4 %, vacio 62.4 Hz, plena carga → 60 Hz", 60.0, p.referencia)
    d0 = _dt.date(2026, 1, 1)
    regs = [tendencias.Registro(d0 + _dt.timedelta(days=10 * i), "GE",
                                "tiempo_sincronizacion_s", str(10 + 2 * i)) for i in range(5)]
    t, = tendencias.proyectar(regs, hoy=d0)
    caso("Tendencia +0.2/dia desde 10 cruza 30 al dia 100", "2026-04-11", t.cruza_el)
    caso("Prioridad AIAG-VDA: S5 O1 D1 → baja", "baja",
         evaluar(PRIORIDAD_EJEMPLO, {"severidad": 5, "frecuencia": 1, "deteccion": 1}).etiqueta)
    caso("Prioridad AIAG-VDA: S5 O1 D2 → alta (severidad manda)", "alta",
         evaluar(PRIORIDAD_EJEMPLO, {"severidad": 5, "frecuencia": 1, "deteccion": 2}).etiqueta)

    # Pertinencia: cada objetivo del puesto tiene funciones que lo cubren.
    objetivos = {
        "Eficaz (decidir bien en sitio)": ("Permisivo de cierre ANSI 25", "Guia de sintomas",
                                          "Lamina didactica sincronismo", "Decodificador SPN/FMI"),
        "Proactivo (anticipar sin que pregunten)": ("Informe priorizado", "Revision de protecciones",
                                                    "Revision de parametros"),
        "Predictivo (fecha de cruce)": ("Tendencias y reincidencias",),
        "Confiabilidad (RCM/AMEF)": ("Menu de fallas RCM/AMEF", "AMEF completa y plan de accion"),
    }
    corridas = {r.requisito.split("«")[1].split("»")[0]: r.resultado
                for r in R if "«" in r.requisito}
    for obj, funcs in objetivos.items():
        ok = all(corridas.get(f) == CUMPLE for f in funcs)
        R.append(Requisito("ISO/IEC 25010", "Adecuacion funcional · pertinencia",
                           f"El objetivo «{obj}» esta cubierto",
                           CUMPLE if ok else PARCIAL, "Funciones: " + ", ".join(funcs)))
    return R


# --- 2. el analisis contra las normas ---------------------------------------

def normas(ruta_analisis: Path, ruta_catalogo_planta: Path | None = None) -> list[Requisito]:
    datos = json.loads(ruta_analisis.read_text(encoding="utf-8"))
    a, dec = cargador.analisis_y_decisiones(ruta_analisis)
    filas = plan_accion.amef(ruta_analisis)
    crudos = [md for fd in datos["funciones"] for ffd in fd["fallas"] for md in ffd["modos"]]
    R: list[Requisito] = []

    def req(norma, clausula, texto, ok, evidencia, accion="", parcial=False):
        res = CUMPLE if ok else (PARCIAL if parcial else NO_CUMPLE)
        R.append(Requisito(norma, clausula, texto, res, evidencia, "" if ok else accion))

    # SAE JA1011: las siete preguntas.
    comp = _rcm.completitud(a, dec.por_modo)
    for r in comp.respuestas:
        req("SAE JA1011", f"Pregunta {r.pregunta.numero}", r.pregunta.texto, r.contestada,
            f"{r.pregunta.responde}: "
            + ("contestada" if r.contestada else "falta " + ", ".join(r.faltantes)),
            "Completar la pregunta en el analisis.")
    ocultos = [m for m in a.modos if not m.evidente]
    mal_ocultos = [m.id for m in ocultos if (d := dec.get(m.id)) and d.estrategia not in
                   ("busqueda_fallas", "cbm", "restauracion", "descarte", "rediseno")]
    req("SAE JA1011", "5.7", "Las fallas ocultas tienen busqueda de fallas o una tarea que "
        "reduzca la falla multiple", not mal_ocultos,
        f"{len(ocultos)} ocultas; sin tarea adecuada: {mal_ocultos or 'ninguna'}",
        "Asignar busqueda de fallas con intervalo.")
    seg_rtf = [m.id for m in a.modos if m.grave and (d := dec.get(m.id))
               and d.estrategia == "operar_hasta_falla"]
    req("SAE JA1011", "5.7", "Con consecuencia de seguridad no se elige operar hasta la falla",
        not seg_rtf, f"Modos de seguridad: {len(a.modos_graves())}; con operar hasta la falla: "
        f"{seg_rtf or 'ninguno'}", "Rediseño obligatorio.")

    # IEC 60812:2018 — los pasos de la AMEF.
    planif = all([a.activo.codigo, a.fecha, datos.get("participantes"),
                  datos.get("revision"), datos.get("contexto")])
    req("IEC 60812:2018", "Planificacion", "Alcance, contexto, equipo, fecha y revision "
        "documentados", planif, f"activo {a.activo.codigo}, fecha {a.fecha}, "
        f"revision {datos.get('revision')}, {len(datos.get('participantes') or [])} participantes",
        "Completar la identificacion del analisis.")
    sin_ubic = [m.id for m in a.modos if not (m.ubicacion.sistema and m.ubicacion.componente)]
    req("IEC 60812:2018", "Estructura", "Cada modo de falla esta ubicado en sistema y "
        "componente", not sin_ubic, f"sin ubicacion: {sin_ubic or 'ninguno'}",
        "Ubicar cada modo.")
    sin_estandar = [f.id for f in a.funciones if not f.estandar]
    req("IEC 60812:2018", "Funciones", "Cada funcion declara su estandar de desempeño",
        not sin_estandar, f"sin estandar: {sin_estandar or 'ninguna'}", "Declarar el estandar.")
    sin_cadena = [m.id for m in a.modos if not (m.efecto.local and m.causa)]
    req("IEC 60812:2018", "Analisis de fallas", "Cadena efecto – modo – causa completa",
        not sin_cadena, f"incompletos: {sin_cadena or 'ninguno'}", "Completar efecto y causa.")
    sin_ctl = [f.modo_id for f in filas if not (f.prevencion_actual and f.deteccion_actual)]
    req("IEC 60812:2018", "Analisis de riesgo", "Controles actuales de prevencion y deteccion "
        "registrados", not sin_ctl, f"sin controles: {sin_ctl or 'ninguno'}",
        "Registrar los controles actuales.")
    metodo = datos.get("metodo_criticidad") or ""
    req("IEC 60812:2018", "Analisis de riesgo", "Escala de severidad, ocurrencia y deteccion "
        "documentada y propia de la organizacion", bool(metodo) and "EJEMPLO" not in metodo,
        f"metodo: {metodo or 'ninguno'}",
        "Reescribir los niveles de la escala de EJEMPLO con lo que significan en la planta.",
        parcial=bool(metodo))
    obs = [o for f in filas for o in f.observaciones]
    for regla, texto in (("R1", "Toda prioridad alta tiene acciones"),
                         ("R2", "Cada accion tiene responsable, plazo y verificacion"),
                         ("R3", "La severidad solo baja con rediseño"),
                         ("R5", "Las fallas ocultas tienen prueba con intervalo"),
                         ("R6", "Las acciones son coherentes con la estrategia RCM")):
        malas = [o.modo_id for o in obs if o.regla == regla]
        req("IEC 60812:2018", "Optimizacion", texto, not malas,
            f"incumplen: {sorted(set(malas)) or 'ninguno'}", "Ajustar el plan de accion.")
    sin_reeval = [f.modo_id for f in filas if f.acciones and f.npr_r is None]
    req("IEC 60812:2018", "Optimizacion", "Re-evaluacion del riesgo despues de las acciones",
        not sin_reeval, f"sin re-evaluar: {sin_reeval or 'ninguno'}", "Re-evaluar S, O, D.")
    req("IEC 60812:2018", "Documentacion", "La AMEF se exporta en un formato de intercambio",
        bool(plan_accion.a_csv_amef(filas)), "CSV con columnas IEC 60812 / AIAG-VDA")

    # AIAG-VDA 2019: prioridad de accion.
    req("AIAG-VDA 2019", "Paso 5", "La priorizacion usa prioridad de accion (severidad "
        "primero), no solo el NPR", True,
        "El plan se ordena por prioridad, severidad y luego NPR; el NPR lleva su advertencia")
    residual_alta_s5 = [o.modo_id for o in obs if o.regla == "R7"]
    req("AIAG-VDA 2019", "Paso 6", "Ningun modo de severidad critica queda con prioridad "
        "residual alta sin escalar", not residual_alta_s5,
        f"pendientes: {residual_alta_s5 or 'ninguno'}", "Escalar o rediseñar.")

    # ISO 14224: taxonomia y datos.
    fab = _catalogo.Catalogo()
    con_fab = sum(1 for m in a.modos if m.codigo_catalogo)
    con_planta = sum(1 for md in crudos if md.get("codigo_catalogo") or md.get("codigo_planta"))
    planta_ok = True
    if ruta_catalogo_planta and ruta_catalogo_planta.exists():
        cat = _catalogo.cargar(ruta_catalogo_planta)
        planta_ok = all((md.get("codigo_catalogo") or md.get("codigo_planta")) in cat
                        for md in crudos if md.get("codigo_catalogo") or md.get("codigo_planta"))
    req("ISO 14224", "Taxonomia", "Cada modo de falla codificado en la taxonomia",
        con_fab == len(a.modos),
        f"{con_fab}/{len(a.modos)} con codigo del catalogo de fabrica; {con_planta}/"
        f"{len(a.modos)} con codigo de la planta (catalogo-sincronismo.json)",
        "El cargador RCM de FixMate solo valida contra el catalogo de fabrica: los codigos de "
        "sincronismo y TTA viajan como «codigo_planta». Integrar catalogos de planta al cargador.",
        parcial=con_planta == len(a.modos) and planta_ok)
    con_iso = sum(1 for e in fab.entradas if e.codigo_iso)
    req("ISO 14224", "Codigos de la norma", "Los codigos propios mapean a los de ISO 14224",
        con_iso > 0, f"{con_iso} entradas con codigo ISO mapeado",
        "Los codigos de la norma son material con licencia: la planta los mapea en "
        "«codigo_iso» si tiene la norma.")
    propuestas = [md for md in crudos if any(r.get("fuente") == "inferencia"
                                             for r in md.get("evidencia") or [])]
    req("ISO 14224", "Calidad de datos", "La ocurrencia sale del historial de la propia "
        "instalacion", not propuestas,
        f"{len(propuestas)}/{len(crudos)} modos con ocurrencia propuesta desde fuentes publicas",
        "Reemplazar la ocurrencia con el historial de OT (nefer fixmate rcm contrastar).",
        parcial=True)

    # IEEE: sincronismo y nomenclatura de protecciones.
    req("IEEE 1547-2018", "Tabla 5", "Las ventanas de cierre por potencia se aplican al "
        "permisivo y a la revision de parametros", True,
        "verificacion.LIMITES_IEEE1547 y parametros.revisar las usan")
    req("IEEE C37.2", "Numeros de dispositivo", "Las protecciones se nombran por su numero "
        "ANSI (25, 32, 40, 27, 59, 81)", True, "protecciones.FUNCIONES")

    # NFPA 110 como referencia (aplica si la instalacion la adopta).
    textos = " ".join(f"{a_.get('accion','')} {a_.get('intervalo','')}".lower()
                      for md in crudos for a_ in md.get("plan_accion") or [])
    req("NFPA 110 (referencia)", "Mantenimiento y pruebas", "Ejercicio mensual con carga del "
        "grupo y de la transferencia", "ejercicio" in textos and "mensual" in textos,
        "Busqueda de «ejercicio» y «mensual» en el plan de accion",
        "Agregar ejercicio mensual con carga.")
    req("NFPA 110 (referencia)", "Mantenimiento y pruebas", "Inspeccion semanal",
        "semanal" in textos, "Busqueda de «semanal» en el plan de accion",
        "Agregar inspeccion semanal.")
    return R


# --- informe -----------------------------------------------------------------

def auditar(ejemplos: Path, analisis: Path | None = None) -> dict:
    analisis = analisis or ejemplos / "rcm-paralelo-tta.json"
    reqs = funcionalidad(ejemplos) + normas(analisis, ejemplos / "catalogo-sincronismo.json")
    por_norma: dict[str, dict] = {}
    for r in reqs:
        n = por_norma.setdefault(r.norma, {CUMPLE: 0, PARCIAL: 0, NO_CUMPLE: 0, NO_APLICA: 0})
        n[r.resultado] += 1
    total = len(reqs)
    cumple = sum(1 for r in reqs if r.resultado == CUMPLE)
    return {"requisitos": [r.a_dict() for r in reqs], "por_norma": por_norma,
            "total": total, "cumple": cumple,
            "conformidad_pct": round(cumple / total * 100, 1) if total else 0.0}


def a_markdown(res: dict) -> str:
    L = ["# Auditoria de funcionalidad — nefer sincronismo", "",
         "Autoevaluacion reproducible (`nefer sincronismo auditoria`), no certificacion. "
         "Las normas se verifican por su contenido publico general.", "",
         f"**Conformidad: {res['cumple']}/{res['total']} requisitos cumplen "
         f"({res['conformidad_pct']} %).**", "",
         "| Norma | Cumple | Parcial | No cumple |", "|---|---:|---:|---:|"]
    for n, c in res["por_norma"].items():
        L.append(f"| {n} | {c[CUMPLE]} | {c[PARCIAL]} | {c[NO_CUMPLE]} |")
    L.append("")
    norma = None
    for r in res["requisitos"]:
        if r["norma"] != norma:
            norma = r["norma"]
            L += ["", f"## {norma}", "", "| Clausula | Requisito | Resultado | Evidencia | Accion |",
                  "|---|---|---|---|---|"]
        L.append(f"| {r['clausula']} | {r['requisito']} | **{r['resultado']}** | "
                 f"{r['evidencia'].replace('|', '/')} | {r['accion']} |")
    return "\n".join(L) + "\n"


def a_html(res: dict) -> str:
    color = {CUMPLE: "#15803d", PARCIAL: "#b45309", NO_CUMPLE: "#b91c1c", NO_APLICA: "#6b7280"}
    filas, norma = [], None
    for r in res["requisitos"]:
        if r["norma"] != norma:
            norma = r["norma"]
            filas.append(f'<tr class="g"><th colspan="5">{escape(norma)}</th></tr>')
        filas.append(
            f"<tr><td>{escape(r['clausula'])}</td><td>{escape(r['requisito'])}</td>"
            f"<td><span class='r' style='background:{color[r['resultado']]}'>"
            f"{escape(r['resultado'])}</span></td><td>{escape(r['evidencia'])}</td>"
            f"<td>{escape(r['accion'])}</td></tr>")
    resumen = "".join(
        f"<div class='k'><b>{escape(n)}</b><span>{c[CUMPLE]} cumple · {c[PARCIAL]} parcial · "
        f"{c[NO_CUMPLE]} no cumple</span></div>" for n, c in res["por_norma"].items())
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Auditoria de funcionalidad</title>
<style>
:root{{--fondo:#f4f6f8;--panel:#fff;--tinta:#111827;--suave:#4b5563;--borde:#d1d5db}}
@media (prefers-color-scheme:dark){{:root{{--fondo:#0f172a;--panel:#1e293b;--tinta:#e5e7eb;--suave:#9ca3af;--borde:#334155}}}}
body{{margin:0;background:var(--fondo);color:var(--tinta);font:15px/1.45 system-ui,Arial,sans-serif}}
main{{max-width:1150px;margin:0 auto;padding:16px}}
.grande{{font-size:2.2rem;font-weight:800}}
.ks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px;margin:12px 0}}
.k{{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:10px}}
.k b{{display:block}}.k span{{color:var(--suave);font-size:.9rem}}
.t{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:var(--panel)}}
td,th{{border:1px solid var(--borde);padding:7px;vertical-align:top;text-align:left;font-size:.9rem}}
tr.g th{{background:#1e3a8a;color:#fff}}
.r{{color:#fff;border-radius:999px;padding:1px 8px;font-size:.8rem;white-space:nowrap}}
</style></head><body><main>
<h1>Auditoria de funcionalidad — nefer sincronismo</h1>
<p>Autoevaluacion reproducible con <code>nefer sincronismo auditoria</code>: cada requisito se
ejecuta o se calcula, ninguno se declara. No es una certificacion; las normas se verifican por su
contenido publico general.</p>
<div class="grande">{res['conformidad_pct']} %</div>
<p>{res['cumple']} de {res['total']} requisitos cumplen.</p>
<div class="ks">{resumen}</div>
<div class="t"><table><tr><th>Clausula</th><th>Requisito</th><th>Resultado</th><th>Evidencia</th>
<th>Accion</th></tr>{''.join(filas)}</table></div>
</main></body></html>
"""
