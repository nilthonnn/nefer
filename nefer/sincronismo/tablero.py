"""Tablero de inicio: todo el modulo de sincronismo en una carpeta que se abre sin red.

`publicar()` regenera, desde los datos de la carpeta de ejemplos (o los de la
planta cuando existan), cada pagina y cada archivo —menu de fallas, flota,
laminas, diagramas, hojas de parametros, auditoria, AMEF y plan en CSV— y
arma un `index.html` que pone arriba lo que hay que mirar hoy:

- los indicadores de riesgo (NPR antes y despues del plan, prioridad alta);
- las alertas que detienen: controlador que no sirve para el modo, derivas
  ya sobre el limite, protecciones faltantes;
- lo predictivo: que variable cruza su limite y en que fecha;
- las acciones del plan que vencen en los proximos 30 dias.

La fecha de corte es la del analisis, no la del reloj: la misma entrada da la
misma pagina, y asi se puede comprobar que lo publicado esta al dia.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from xml.sax.saxutils import escape

from . import (auditoria, diagramas, flota, informe, laminas, menu_fallas, parametros,
               plan_accion, tendencias)

HERRAMIENTAS = (
    ("menu-fallas.html", "Menu de fallas", "RCM, arbol de decision, AMEF con NPR y plan de accion por falla"),
    ("flota.html", "Flota y despliegues", "Grupos solos y en sincronismo; que verificar al cambiar de modo"),
    ("lamina-sincronismo.html", "Lamina: sincronismo", "Conexiones por capas, como se verifica cada una y errores de campo"),
    ("lamina-tta.html", "Lamina: TTA", "Transferencia automatica por capas y su secuencia"),
    ("parametros-sincronismo.html", "Parametros de sincronismo", "Que se ajusta, como decidirlo y que pasa si queda mal"),
    ("parametros-tta.html", "Parametros de TTA", "Umbrales de red y temporizadores"),
    ("diagrama-sincronismo.svg", "Diagrama de sincronismo", "Unifilar de la planta en paralelo"),
    ("diagrama-tta.svg", "Diagrama de TTA", "Red, grupo y transferencia"),
    ("auditoria.html", "Auditoria", "Funcionalidad y normas: SAE JA1011, IEC 60812, ISO 14224, IEEE"),
    ("amef-completa.csv", "AMEF en Excel", "Todas las columnas IEC 60812 / AIAG-VDA"),
    ("plan-accion.csv", "Plan de accion en Excel", "Acciones priorizadas con responsable y fecha"),
)


def publicar(ejemplos: str | Path, destino: str | Path) -> list[Path]:
    """Genera todo en `destino` y devuelve los archivos escritos."""
    ej, dst = Path(ejemplos), Path(destino)
    dst.mkdir(parents=True, exist_ok=True)
    analisis = ej / "rcm-paralelo-tta.json"
    planta_dse = informe.cargar_planta(ej / "planta-dse-cat.json")
    fl = flota.cargar(ej / "flota.json")
    res_flota = flota.analizar(fl, analisis)
    filas = plan_accion.amef(analisis)
    fecha = json.loads(analisis.read_text(encoding="utf-8")).get("fecha")
    acciones = plan_accion.plan(filas, fecha)
    aud = auditoria.auditar(ej, analisis)

    archivos = {
        "menu-fallas.html": menu_fallas.pagina(analisis),
        "flota.html": flota.a_html(fl, res_flota),
        "lamina-sincronismo.html": laminas.lamina_html("sincronismo", planta_dse),
        "lamina-tta.html": laminas.lamina_html("tta", planta_dse),
        "parametros-sincronismo.html": parametros.hoja_html("sincronismo", planta_dse),
        "parametros-tta.html": parametros.hoja_html("tta", planta_dse),
        "diagrama-sincronismo.svg": diagramas.diagrama_sincronismo(planta_dse),
        "diagrama-tta.svg": diagramas.diagrama_tta(planta_dse),
        "auditoria.html": auditoria.a_html(aud),
        "amef-completa.csv": plan_accion.a_csv_amef(filas),
        "plan-accion.csv": plan_accion.a_csv_plan(acciones),
    }
    archivos["index.html"] = index(ej, fecha, filas, acciones, res_flota, aud)
    escritos = []
    for nombre, contenido in archivos.items():
        ruta = dst / nombre
        ruta.write_text(contenido, encoding="utf-8")
        escritos.append(ruta)
    return escritos


def _predictivo(ej: Path, hoy: _dt.date) -> tuple[list, list]:
    planta = informe.cargar_planta(ej / "planta.json")
    regs = tendencias.leer_csv(ej / "registro.csv")
    res = informe.analizar(planta, regs, hoy)
    tend = [t for t in res["secciones"].get("tendencias", []) if t["severidad"]]
    detiene = [h for h in res["hallazgos"] if h["severidad"] == "detiene"]
    return tend, detiene


def index(ej: Path, fecha: str, filas, acciones, res_flota, aud) -> str:
    hoy = _dt.date.fromisoformat(fecha)
    r = plan_accion.resumen(filas)
    tend, detiene_planta = _predictivo(ej, hoy)
    alertas = [(o["unidad"], f"{d['nombre']}: {o['texto']}") for d in res_flota
               for o in d["observaciones"] if o["severidad"] == "detiene"]
    alertas += [(h["unidad"], f"{h['origen']}: {h['texto']}") for h in detiene_planta]
    limite = (hoy + _dt.timedelta(days=30)).isoformat()
    proximas = sorted((a for a in acciones if a["fecha_objetivo"] and a["fecha_objetivo"] <= limite),
                      key=lambda a: (a["fecha_objetivo"], plan_accion.ORDEN_AP.get(a["prioridad"], 9)))

    kpis = [
        (str(r["modos"]), "Modos de falla analizados"),
        (f"{r['npr_total_inicial']} → {r['npr_total_residual']}", f"NPR total (−{r['reduccion_pct']} %)"),
        (f"{r['ap_inicial']['alta']} → {r['ap_residual']['alta']}", "Prioridad alta antes → despues"),
        (str(len(alertas)), "Alertas que detienen"),
        (f"{aud['conformidad_pct']} %", "Conformidad de la auditoria"),
    ]
    k_html = "".join(f"<div class='k'><b>{escape(v)}</b>{escape(t)}</div>" for v, t in kpis)
    a_html = "".join(f"<li><b>{escape(u)}</b> — {escape(t)}</li>" for u, t in alertas) or \
        "<li>Sin alertas que detengan.</li>"
    t_html = "".join(
        f"<li class='{t['severidad']}'><b>{escape(t['equipo'])}</b> · {escape(t['variable'])}: "
        f"{escape(t['texto'])}</li>" for t in tend) or "<li>Ninguna deriva proyectada.</li>"
    p_html = "".join(
        f"<tr><td>{escape(a['fecha_objetivo'])}</td><td><span class='chip {a['prioridad']}'>"
        f"{escape(a['prioridad'])}</span></td><td>{escape(a['accion'])}</td>"
        f"<td>{escape(a['modo_falla'])}</td><td>{escape(a['responsable'])}</td></tr>"
        for a in proximas)
    h_html = "".join(f"<a class='h' href='{escape(f)}'><b>{escape(n)}</b><span>{escape(d)}</span></a>"
                     for f, n, d in HERRAMIENTAS)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Tablero de sincronismo</title>
<style>
:root{{--fondo:#f4f6f8;--panel:#fff;--tinta:#111827;--suave:#4b5563;--borde:#d1d5db;--acento:#2563eb;
--alta:#b91c1c;--media:#b45309;--baja:#15803d}}
@media (prefers-color-scheme:dark){{:root{{--fondo:#0f172a;--panel:#1e293b;--tinta:#e5e7eb;--suave:#9ca3af;
--borde:#334155;--acento:#60a5fa;--alta:#f87171;--media:#fbbf24;--baja:#4ade80}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--fondo);color:var(--tinta);font:15px/1.45 system-ui,-apple-system,Arial,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:16px}}
h1{{margin:0 0 4px;font-size:1.5rem}}h2{{font-size:1.1rem;margin:22px 0 8px}}.sub{{color:var(--suave);margin:0}}
.ks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0}}
.k{{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:10px 12px}}
.k b{{display:block;font-size:1.45rem}}
.panel{{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:12px 16px}}
.alertas li{{color:var(--alta);margin:6px 0}}
li.detiene{{color:var(--alta)}}li.programable{{color:var(--media)}}
.hs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}}
a.h{{display:block;text-decoration:none;color:var(--tinta);background:var(--panel);border:1px solid var(--borde);
border-left:5px solid var(--acento);border-radius:10px;padding:10px 12px}}
a.h:hover{{border-color:var(--acento)}}a.h b{{display:block}}a.h span{{color:var(--suave);font-size:.88rem}}
.t{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:var(--panel)}}
td,th{{border-bottom:1px solid var(--borde);padding:7px;text-align:left;font-size:.9rem}}
.chip{{color:#fff;border-radius:999px;padding:1px 8px;font-size:.78rem}}
.chip.alta{{background:var(--alta)}}.chip.media{{background:var(--media)}}.chip.baja{{background:var(--baja)}}
code{{background:var(--panel);border:1px solid var(--borde);border-radius:4px;padding:1px 5px}}
</style></head><body><main>
<h1>Sincronismo y grupos electrogenos</h1>
<p class="sub">Tablero de inicio · fecha de corte {escape(fecha)} · datos de EJEMPLO hasta cargar los de la
planta. Abre sin conexion.</p>
<div class="ks">{k_html}</div>
<h2>Herramientas</h2>
<div class="hs">{h_html}</div>
<h2>Detiene la maquina ahora</h2>
<div class="panel"><ul class="alertas">{a_html}</ul></div>
<h2>Predictivo: derivas del registro</h2>
<div class="panel"><ul>{t_html}</ul></div>
<h2>Acciones que vencen en los proximos 30 dias ({len(proximas)})</h2>
<div class="t"><table><tr><th>Fecha</th><th>Prioridad</th><th>Accion</th><th>Falla</th><th>Responsable</th></tr>
{p_html}</table></div>
<h2>En campo, desde la terminal</h2>
<div class="panel"><ul>
<li><code>nefer sincronismo verificar --v-barra 380 --f-barra 60 --v-gen 382 --f-gen 60.1 --angulo -4 --kva 500</code> — ¿se puede cerrar?</li>
<li><code>nefer sincronismo codigo 168 17</code> — que significa un evento SPN/FMI (PowerWizard, ECM)</li>
<li><code>nefer sincronismo diagnostico "dispara por potencia inversa"</code> — causas en orden de descarte</li>
<li><code>nefer sincronismo publicar</code> — regenerar este tablero con los datos nuevos</li>
</ul></div>
</main></body></html>
"""
