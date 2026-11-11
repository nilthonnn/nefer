"""Flota mixta: grupos que trabajan solos, en sincronismo, o en los dos segun el trabajo.

La flota real no es una planta fija. Un grupo con PowerWizard trabaja siempre
solo; un grupo con DSE8610 trabaja en paralelo en un sitio y solo en el
siguiente. Lo que cambia con el modo:

- que fallas pueden ocurrir: un grupo solo no tiene reparto, ni cierre a una
  barra viva, ni corriente circulante entre unidades;
- que controlador sirve: uno de un solo grupo no puede ir a un despliegue en
  paralelo;
- que hay que revisar al cambiar de modo: el mismo grupo que ayer repartia
  por enlace hoy tiene que mantener 60 Hz solo, y lo que quedo configurado
  para el paralelo puede hacer que no cierre o que alarme.

`flota.json` declara las unidades (con su controlador) y los despliegues
(que unidades, en que modo, con o sin TTA). De ahi salen, por despliegue: la
revision de controladores, las fallas que aplican con su prioridad, y la
lista de verificacion de cada unidad que cambia de modo respecto del
despliegue anterior.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from . import codigos, plan_accion

MODOS = ("solo", "paralelo")

# Verificacion al cambiar de modo. Generica a proposito: los nombres de los
# parametros cambian por marca y version del controlador; lo que no cambia es
# que hay que mirarlos.
A_SOLO = (
    "Desconectar el enlace de reparto (MSC u otro) o retirar la unidad del grupo en la "
    "configuracion, para que no alarme por falla de enlace ni la cuenten como disponible.",
    "Modo de control de velocidad para un grupo solo (isocrono a la frecuencia nominal), "
    "sin polarizacion externa de velocidad ni de tension.",
    "Consignas de tension y frecuencia en la nominal del sitio ({v:g} V, {f:g} Hz) sin estatismo "
    "residual que deje la frecuencia baja con carga.",
    "Cierre del interruptor en barra muerta habilitado: solo no hay barra viva con que "
    "sincronizar.",
    "Arranque y parada por demanda deshabilitados (no hay otras unidades).",
    "Protecciones 27/59 y 81 ajustadas para el grupo solo; la 32 puede quedar activa.",
    "Prueba con carga: frecuencia y tension estables al tomar y soltar carga.",
)
A_PARALELO = (
    "Enlace de reparto conectado en cadena, terminacion en los dos extremos (unos 60 ohm "
    "entre H y L con todo apagado) y malla aterrada en un solo extremo.",
    "Identificador de unidad unico en el enlace, si el controlador lo pide.",
    "Modo de reparto acordado para todas las unidades (isocrono compartido o estatismo), "
    "igual en todas.",
    "Sensado de tension de barra conectado DESPUES del interruptor y en la misma fase de "
    "referencia; verificar con sincronoscopio externo.",
    "Secuencia de fases igual a ambos lados del interruptor de cada unidad.",
    "Funciones 25, 32 y 40 habilitadas; ventanas de sincronismo y nivel de apertura de rampa "
    "revisados (nefer sincronismo parametros --revisar).",
    "Arbitraje de barra muerta: con arranque simultaneo cierra una sola unidad.",
    "Primer cierre con el interruptor en prueba; despues, reparto al 25, 50, 75 y 100 %.",
)


def cargar(ruta: str | Path) -> dict:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    ids = [u["id"] for u in datos.get("unidades", [])]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError(f"{ruta}: las unidades necesitan un id unico")
    for d in datos.get("despliegues", []):
        if d.get("modo") not in MODOS:
            raise ValueError(f"{ruta}: despliegue «{d.get('nombre')}»: modo debe ser "
                             f"{' o '.join(MODOS)}")
        faltan = [u for u in d.get("unidades", []) if u not in ids]
        if faltan:
            raise ValueError(f"{ruta}: despliegue «{d.get('nombre')}»: unidades desconocidas "
                             f"{', '.join(faltan)}")
        if d["modo"] == "paralelo" and len(d["unidades"]) < 2:
            raise ValueError(f"{ruta}: despliegue «{d.get('nombre')}»: en paralelo hacen "
                             "falta al menos dos unidades")
    return datos


def aplica(modo_falla: dict, modo: str, con_tta: bool) -> bool:
    a = set(modo_falla.get("aplica") or ("solo", "paralelo"))
    return modo in a or (con_tta and "tta" in a)


def analizar(flota: dict, ruta_analisis: str | Path) -> list[dict]:
    datos = json.loads(Path(ruta_analisis).read_text(encoding="utf-8"))
    crudos = [md for fd in datos["funciones"] for ffd in fd["fallas"] for md in ffd["modos"]]
    filas = {f.modo_id: f for f in plan_accion.amef(ruta_analisis)}
    ids_modo = list(filas)          # mismo orden que los crudos
    unidades = {u["id"]: u for u in flota["unidades"]}
    ultimo_modo: dict[str, str] = {}
    salida = []

    for d in flota.get("despliegues", []):
        modo, tta = d["modo"], bool(d.get("tta"))
        planta = {"unidades": [{**unidades[i], "modo": "solo" if modo == "solo" else
                                unidades[i].get("modo_paralelo", "isocrono_compartido")}
                               for i in d["unidades"]]}
        obs = codigos.revisar_controladores(planta) if modo == "paralelo" else []
        for i in d["unidades"]:
            ctl = unidades[i].get("controlador") or {}
            if codigos.perfil(ctl.get("marca"), ctl.get("modelo")) is None:
                obs.append({"severidad": "oportunidad", "unidad": i,
                            "texto": "Controlador sin perfil conocido."})

        fallas = []
        for mid, md in zip(ids_modo, crudos):
            if aplica(md, modo, tta):
                f = filas[mid]
                fallas.append({"id": mid, "modo": f.modo_falla, "sistema": f.sistema,
                               "s": f.severidad, "npr": f.npr, "ap": f.ap,
                               "npr_r": f.npr_r, "ap_r": f.ap_r})
        fallas.sort(key=lambda x: (plan_accion.ORDEN_AP.get(x["ap"], 9), -x["s"], -x["npr"]))

        cambios = []
        for i in d["unidades"]:
            antes = ultimo_modo.get(i)
            if antes and antes != modo:
                v, fr = flota.get("v_nominal", 380), flota.get("f_nominal", 60)
                cambios.append({"unidad": i, "de": antes, "a": modo,
                                "verificar": [t.format(v=v, f=fr) for t in
                                              (A_SOLO if modo == "solo" else A_PARALELO)]})
            ultimo_modo[i] = modo

        salida.append({"nombre": d.get("nombre", ""), "sitio": d.get("sitio", ""),
                       "modo": modo, "tta": tta, "unidades": d["unidades"],
                       "observaciones": obs, "fallas": fallas, "cambios": cambios,
                       "npr_total": sum(x["npr"] for x in fallas),
                       "npr_total_r": sum(x["npr_r"] or 0 for x in fallas),
                       "alta": sum(1 for x in fallas if x["ap"] == "alta")})
    return salida


def a_markdown(flota: dict, res: list[dict], top: int = 8) -> str:
    L = [f"# Flota — {flota.get('nombre', 'flota')}", "",
         "| Unidad | Controlador | Motor | Puede ir en paralelo |", "|---|---|---|---|"]
    for u in flota["unidades"]:
        ctl = u.get("controlador") or {}
        p = codigos.perfil(ctl.get("marca"), ctl.get("modelo"))
        par = "—" if p is None else ("si" if p.paralelo else "no (un solo grupo)")
        mot = u.get("motor") or {}
        L.append(f"| {u['id']} | {ctl.get('marca', '')} {ctl.get('modelo', '')} | "
                 f"{mot.get('marca', '')} {mot.get('modelo') or ''} | {par} |")
    for d in res:
        L += ["", f"## {d['nombre']} — {'en paralelo' if d['modo'] == 'paralelo' else 'grupo solo'}"
              f"{' con TTA' if d['tta'] else ''}", "",
              f"Sitio: {d['sitio'] or '—'} · Unidades: {', '.join(d['unidades'])} · "
              f"{len(d['fallas'])} modos de falla aplican, {d['alta']} con prioridad alta · "
              f"NPR {d['npr_total']} → {d['npr_total_r']} con el plan.", ""]
        for o in d["observaciones"]:
            L.append(f"- **[{o['severidad']}] {o['unidad']}:** {o['texto']}")
        if d["observaciones"]:
            L.append("")
        for c in d["cambios"]:
            L += [f"### {c['unidad']} cambia de {c['de']} a {c['a']}: verificar antes de arrancar", ""]
            L += [f"- [ ] {v}" for v in c["verificar"]]
            L.append("")
        L += [f"Las {min(top, len(d['fallas']))} fallas a vigilar primero:", "",
              "| Prioridad | S | NPR | Falla | Sistema |", "|---|---:|---:|---|---|"]
        for x in d["fallas"][:top]:
            L.append(f"| {x['ap']} | {x['s']} | {x['npr']} | {x['modo']} | {x['sistema']} |")
    return "\n".join(L) + "\n"


def a_html(flota: dict, res: list[dict]) -> str:
    cuerpo = []
    for d in res:
        obs = "".join(f"<li class='{o['severidad']}'><b>{escape(o['unidad'])}</b> — "
                      f"{escape(o['texto'])}</li>" for o in d["observaciones"])
        cambios = "".join(
            f"<div class='cambio'><h4>{escape(c['unidad'])}: de {escape(c['de'])} a "
            f"{escape(c['a'])} — verificar antes de arrancar</h4><ul class='check'>"
            + "".join(f"<li><label><input type='checkbox'> {escape(v)}</label></li>"
                      for v in c["verificar"]) + "</ul></div>" for c in d["cambios"])
        filas = "".join(
            f"<tr><td><span class='chip {x['ap']}'>{escape(x['ap'])}</span></td><td>{x['s']}</td>"
            f"<td>{x['npr']}</td><td>{escape(x['modo'])}</td><td>{escape(x['sistema'])}</td>"
            f"<td>{x['npr_r'] if x['npr_r'] is not None else ''}</td></tr>" for x in d["fallas"])
        etiqueta = "En paralelo" if d["modo"] == "paralelo" else "Grupo solo"
        cuerpo.append(
            f"<section><h2>{escape(d['nombre'])} <span class='modo {d['modo']}'>{etiqueta}"
            f"{' + TTA' if d['tta'] else ''}</span></h2>"
            f"<p class='sub'>{escape(d['sitio'] or '')} · {', '.join(map(escape, d['unidades']))} · "
            f"{len(d['fallas'])} fallas aplican · {d['alta']} prioridad alta · NPR "
            f"{d['npr_total']} → {d['npr_total_r']}</p>"
            + (f"<ul class='obs'>{obs}</ul>" if obs else "") + cambios
            + "<details><summary>Fallas que aplican a este despliegue</summary><div class='t'>"
              "<table><tr><th>Prioridad</th><th>S</th><th>NPR</th><th>Falla</th><th>Sistema</th>"
              f"<th>NPR despues</th></tr>{filas}</table></div></details></section>")
    unidades = "".join(
        f"<tr><td>{escape(u['id'])}</td><td>{escape((u.get('controlador') or {}).get('marca', ''))} "
        f"{escape((u.get('controlador') or {}).get('modelo') or '')}</td>"
        f"<td>{escape((u.get('motor') or {}).get('marca', ''))}</td><td>"
        + (lambda p: "—" if p is None else ("si" if p.paralelo else "no, un solo grupo"))(
            codigos.perfil((u.get('controlador') or {}).get('marca'),
                           (u.get('controlador') or {}).get('modelo')))
        + "</td></tr>" for u in flota["unidades"])
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Flota y despliegues</title>
<style>
:root{{--fondo:#f4f6f8;--panel:#fff;--tinta:#111827;--suave:#4b5563;--borde:#d1d5db;
--alta:#b91c1c;--media:#b45309;--baja:#15803d}}
@media (prefers-color-scheme:dark){{:root{{--fondo:#0f172a;--panel:#1e293b;--tinta:#e5e7eb;
--suave:#9ca3af;--borde:#334155;--alta:#f87171;--media:#fbbf24;--baja:#4ade80}}}}
body{{margin:0;background:var(--fondo);color:var(--tinta);font:15px/1.45 system-ui,Arial,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:16px}}
section{{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:14px;margin:14px 0}}
h2{{margin:0;font-size:1.15rem}}.sub{{color:var(--suave)}}
.modo{{font-size:.8rem;border-radius:999px;padding:2px 10px;color:#fff;vertical-align:middle}}
.modo.paralelo{{background:#2563eb}}.modo.solo{{background:#059669}}
.t{{overflow-x:auto}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid var(--borde);padding:6px;text-align:left;font-size:.9rem}}
.chip{{color:#fff;border-radius:999px;padding:1px 8px;font-size:.8rem}}
.chip.alta{{background:var(--alta)}}.chip.media{{background:var(--media)}}.chip.baja{{background:var(--baja)}}
.obs li.detiene{{color:var(--alta);font-weight:600}}
.cambio{{border-left:4px solid #b45309;padding:4px 12px;margin:10px 0}}
.check{{list-style:none;padding:0}}.check li{{margin:6px 0}}
summary{{cursor:pointer;font-weight:600}}
</style></head><body><main>
<h1>Flota y despliegues — {escape(flota.get('nombre', ''))}</h1>
<p class="sub">Que fallas aplican segun el modo (solo, en paralelo, con TTA), si el controlador
de cada unidad sirve para ese modo, y que verificar cuando una unidad cambia de modo.
Generado por <code>nefer sincronismo flota</code>.</p>
<div class="t"><table><tr><th>Unidad</th><th>Controlador</th><th>Motor</th>
<th>Puede ir en paralelo</th></tr>{unidades}</table></div>
{''.join(cuerpo)}
</main></body></html>
"""
