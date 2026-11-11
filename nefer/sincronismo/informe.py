"""El informe de la planta: todo junto, ordenado por lo que obliga a hacer.

Es la pieza proactiva. En vez de esperar a que alguien pregunte por una
unidad, revisa la planta entera —reparto actual, reparto previsto a cada
escalon de carga, protecciones, derivas del registro y alarmas que
reinciden— y pone arriba lo que detiene la maquina, despues lo que se
programa y al final lo que se hace cuando haya ocasion. Las mismas tres
severidades de la anomalia TPM de FixMate, por el mismo motivo: se
distinguen por lo que obligan a hacer, no por cuanto preocupan.

La planta se describe en un JSON (ver ejemplos/sincronismo/planta.json).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import protecciones as _prot
from . import reparto as _rep
from . import tendencias as _tend

ORDEN = {"detiene": 0, "programable": 1, "oportunidad": 2}
TITULOS = {
    "detiene": "Detiene la maquina ahora",
    "programable": "Se atiende en la proxima ventana",
    "oportunidad": "Cuando se abra una ocasion",
}


def cargar_planta(ruta: str | Path) -> dict:
    with open(ruta, encoding="utf-8") as fh:
        planta = json.load(fh)
    if not planta.get("unidades"):
        raise ValueError(f"{ruta}: la planta no declara unidades")
    ids = [u.get("id") for u in planta["unidades"]]
    if None in ids or len(set(ids)) != len(ids):
        raise ValueError(f"{ruta}: cada unidad necesita un id unico")
    return planta


def analizar(planta: dict, registros: list | None = None,
             hoy: _dt.date | None = None) -> dict:
    """Devuelve las secciones del informe y la lista de hallazgos priorizada."""
    hoy = hoy or _dt.date.today()
    unidades = [_rep.Unidad.desde_dict(u) for u in planta["unidades"]]
    f_nom = float(planta.get("f_nominal", 60.0))
    hallazgos: list[dict] = []
    secciones: dict = {}

    def agregar(origen, lista):
        for h in lista:
            hallazgos.append({**h, "origen": origen})

    # 1. Reparto actual.
    if sum(1 for u in unidades if u.kw is not None) >= 2:
        rep = _rep.analizar_reparto(unidades)
        secciones["reparto"] = rep.a_dict()
        agregar("reparto actual", rep.hallazgos)

    # 2. Reparto previsto por estatismo a cada escalon.
    if all(u.modo == "isocrono" or (u.f_vacio and u.estatismo_pct) for u in unidades):
        total = sum(u.kw_nominal for u in unidades)
        previstos = []
        # Un hallazgo por unidad y severidad: el del escalon mas alto, con la
        # lista de escalones donde aparece. Cuatro lineas que dicen lo mismo
        # con otro numero esconden las que dicen otra cosa.
        agrupados: dict[tuple, tuple] = {}
        for pct in planta.get("cargas_a_predecir_pct", (25, 50, 75, 100)):
            pred = _rep.predecir_estatismo(unidades, total * pct / 100, f_nom)
            previstos.append({"carga_pct": pct, **pred.a_dict()})
            for h in pred.hallazgos:
                clave = (h["unidad"], h["severidad"])
                pcts = agrupados.get(clave, (None, []))[1] + [pct]
                agrupados[clave] = (h, pcts)
        for h, pcts in agrupados.values():
            escalones = ", ".join(f"{p:g}" for p in pcts)
            agregar(f"reparto previsto ({escalones} %)",
                    [{**h, "texto": f"Al {pcts[-1]:g} %: {h['texto']}"}])
        secciones["estatismo"] = previstos

    # 3. Protecciones.
    prot = []
    for u in planta["unidades"]:
        if "protecciones" in u:
            prot.extend(o.a_dict() for o in _prot.revisar(u["id"], u["protecciones"]))
    if prot:
        secciones["protecciones"] = prot
        agregar("protecciones", [{"severidad": o["severidad"], "unidad": o["unidad"],
                                  "texto": o["texto"]} for o in prot])

    # 4. Registro: derivas y reincidencias.
    if registros:
        tend = _tend.proyectar(registros, planta.get("limites"), hoy)
        secciones["tendencias"] = [t.a_dict() for t in tend]
        agregar("tendencia", [{"severidad": t.severidad, "unidad": t.equipo,
                               "texto": f"{t.variable}: {t.texto}"}
                              for t in tend if t.severidad])
        rein = _tend.reincidencias(registros, hoy)
        secciones["reincidencias"] = [r.a_dict() for r in rein]
        agregar("alarma reincidente", [{"severidad": r.severidad, "unidad": r.equipo,
                                        "texto": f"{r.alarma}: {r.texto}"}
                                       for r in rein])

    hallazgos.sort(key=lambda h: (ORDEN.get(h["severidad"], 9), h["unidad"]))
    return {"planta": planta.get("planta", "planta"), "fecha": hoy.isoformat(),
            "hallazgos": hallazgos, "secciones": secciones}


def a_markdown(resultado: dict) -> str:
    L = [f"# Informe de sincronismo — {resultado['planta']}", "",
         f"Fecha: {resultado['fecha']}", ""]
    hall = resultado["hallazgos"]
    if not hall:
        L += ["Sin hallazgos. Nada que atender con los datos cargados.", ""]
    for sev in ORDEN:
        grupo = [h for h in hall if h["severidad"] == sev]
        if not grupo:
            continue
        L += [f"## {TITULOS[sev]} ({len(grupo)})", ""]
        for h in grupo:
            L.append(f"- **{h['unidad']}** · {h['origen']} — {h['texto']}")
        L.append("")

    sec = resultado["secciones"]
    if "reparto" in sec:
        r = sec["reparto"]
        L += ["## Reparto actual", "",
              f"Planta al {r['pu_kw_planta']*100:.0f} % de kW. Limites: "
              f"±{r['limite_kw_pct']:g} % kW, ±{r['limite_kvar_pct']:g} % kVAr "
              f"({r['fuente_limites']}).", "",
              "| Unidad | kW | % placa | desvio kW | kVAr | desvio kVAr |",
              "|---|---:|---:|---:|---:|---:|"]
        for f in r["filas"]:
            kvar = "—" if f["kvar"] is None else f"{f['kvar']:.0f}"
            dq = "—" if f["desvio_kvar_pct"] is None else f"{f['desvio_kvar_pct']:+.1f} %"
            L.append(f"| {f['id']} | {f['kw']:.0f} | {f['pu_kw']*100:.0f} % | "
                     f"{f['desvio_kw_pct']:+.1f} % | {kvar} | {dq} |")
        L.append("")
    if "estatismo" in sec:
        L += ["## Reparto previsto por estatismo", "",
              "| Carga | f barra (Hz) | " + " | ".join(sec["estatismo"][0]["toma"]) + " |",
              "|---:|---:|" + "---:|" * len(sec["estatismo"][0]["toma"])]
        for p in sec["estatismo"]:
            celdas = " | ".join(f"{v:.0f} kW ({p['pu'][k]*100:.0f} %)"
                                for k, v in p["toma"].items())
            L.append(f"| {p['carga_pct']} % | {p['referencia']:.2f} | {celdas} |")
        sug = sec["estatismo"][-1]["consigna_sugerida"]
        if sug:
            L += ["", "Consigna en vacio que deja la barra en nominal a plena carga "
                      "con reparto parejo: " +
                  ", ".join(f"{k} {v:.2f} Hz" for k, v in sug.items()) + "."]
        L.append("")
    if sec.get("tendencias"):
        L += ["## Tendencias del registro", "",
              "| Unidad | Variable | Lecturas | Ultimo | Limite | Lectura |",
              "|---|---|---:|---:|---:|---|"]
        for t in sec["tendencias"]:
            lim = "—" if t["limite"] is None else f"{t['limite']:g}"
            L.append(f"| {t['equipo']} | {t['variable']} | {t['puntos']} | "
                     f"{t['ultimo']:g} | {lim} | {t['texto']} |")
        L.append("")
    L += ["---", "",
          "Los limites de reparto y de tendencia son criterio de taller y se "
          "cambian en la planta. Las protecciones se comparan con referencia, "
          "no con el estudio de coordinacion. Lo que se confirme al revisar, "
          "cerrarlo en FixMate para que la flota lo aprenda.", ""]
    return "\n".join(L)


PROTOCOLO = (
    ("Antes de energizar", (
        "Secuencia de fases verificada a ambos lados de cada interruptor de generador",
        "Relacion y polaridad de TC y TP declaradas en cada controlador, comprobadas con inyeccion",
        "Tiempo de cierre de cada interruptor medido (ms) y cargado como angulo de adelanto",
        "Lineas de reparto / bus intercontrolador: continuidad, malla aterrada en un extremo",
        "Funciones 25, 32, 40, 27/59, 81O/U ajustadas segun estudio y probadas por inyeccion",
    )),
    ("Cada unidad sola", (
        "Estabilidad de frecuencia en vacio (pico a pico en 30 s): ____ Hz",
        "Estabilidad de tension en vacio: ____ V",
        "Consigna de velocidad en vacio y estatismo anotados: ____ Hz / ____ %",
        "Consigna de tension y estatismo del AVR anotados: ____ V / ____ %",
        "Toma de carga en escalones con banco resistivo: caida y recuperacion de f",
    )),
    ("Sincronizacion", (
        "Cierre en barra muerta con enclavamiento: solo una unidad cierra",
        "Sincronoscopio externo en paralelo: cero en el mismo instante que el controlador",
        "Primer cierre con interruptor en prueba (sin potencia): angulo en contacto ____ °",
        "Cierre real: deslizamiento ____ Hz, ΔV ____ %, angulo ____ °, sin golpe",
        "Prueba de 32: reducir combustible o consigna hasta disparo; pickup ____ % / ____ s",
    )),
    ("Reparto en paralelo", (
        "Reparto kW y kVAr al 25, 50, 75 y 100 %: desvio dentro de limites",
        "Comparar lo medido con nefer sincronismo estatismo para cada escalon",
        "Rechazo de carga del 50 % y 100 %: ninguna unidad dispara por 32 ni por 81O",
        "Perdida de una unidad bajo carga: las demas la toman sin disparar",
        "Descarga y apertura por rampa: abre antes de cruzar a potencia inversa",
    )),
)


def protocolo_markdown(planta: dict | None = None) -> str:
    nombre = (planta or {}).get("planta", "____________")
    ids = [u["id"] for u in (planta or {}).get("unidades", [])] or ["GE-__"]
    L = [f"# Protocolo de puesta en marcha del paralelo — {nombre}", "",
         "Fecha: ____  Tecnico: ____  Firma: ____", "",
         f"Unidades: {', '.join(ids)}", ""]
    for etapa, pasos in PROTOCOLO:
        L += [f"## {etapa}", "", "| Paso | " + " | ".join(ids) + " |",
              "|---|" + "---|" * len(ids)]
        for p in pasos:
            L.append(f"| {p} | " + " | ".join("☐" for _ in ids) + " |")
        L.append("")
    return "\n".join(L)
