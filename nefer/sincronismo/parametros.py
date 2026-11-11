"""Parametros que se configuran en sincronismo y en TTA, y su revision.

Dos cosas:

1. **El catalogo**: cada parametro con lo que hace, como se decide su valor,
   que pasa si queda mal y como se comprueba en campo. Sirve de hoja de
   configuracion: se imprime con la columna «valor ajustado» en blanco y se
   llena frente a DSE Configuration Suite.

2. **La revision**: si la planta declara los valores (`"parametros"` en
   planta.json), se comprueban las reglas que relacionan unos con otros.
   Un parametro suelto rara vez esta mal; lo que falla es la combinacion:
   una rampa que abre por debajo del pickup de la 32, un retorno de red mas
   corto que la confirmacion de falla, una ventana de angulo mas ancha que
   la norma.

Los nombres en DSE son los que aparecen en el manual de Configuration Suite
(DSE 057-238 para el 8610 MKII) y pueden variar con la version: se dan como
guia para encontrarlos, no como texto exacto. Ningun valor por defecto del
fabricante se presenta como recomendado. Las unicas cifras que se citan
llevan su fuente (IEEE 1547-2018 tabla 5; la guia DSE de paralelo).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from xml.sax.saxutils import escape

from . import verificacion


@dataclass
class Parametro:
    clave: str
    grupo: str
    nombre: str
    dse: str          # como buscarlo en DSE Configuration Suite
    unidad: str
    que_hace: str
    como_decidir: str
    si_queda_mal: str
    verificacion: str

    def a_dict(self) -> dict:
        return asdict(self)


P = Parametro

SINCRONISMO: tuple[Parametro, ...] = (
    # --- Sincronizador
    P("sync_df", "Sincronizador", "Ventana de frecuencia (deslizamiento)",
      "Synchroniser · Check sync · frequency / slip", "Hz",
      "Diferencia maxima de frecuencia entre generador y barra para permitir el cierre.",
      "IEEE 1547-2018 tabla 5: 0.3 Hz hasta 500 kVA, 0.2 Hz hasta 1500 kVA, 0.1 Hz "
      "por encima. Guia DSE de sincronismo 057-045 parte 1: 0.2 Hz en ediciones "
      "antiguas y 0.1 Hz en las posteriores, como valor con el que se parlela bien.",
      "Ancha: cierre con golpe y oscilacion de potencia. Estrecha: el gobernador no "
      "la sostiene y el grupo no sincroniza nunca.",
      "nefer sincronismo verificar con las lecturas del cierre; sincronoscopio externo."),
    P("sync_dv", "Sincronizador", "Ventana de tension",
      "Synchroniser · Check sync · voltage", "%",
      "Diferencia maxima de tension entre generador y barra para cerrar.",
      "IEEE 1547-2018: 10 % / 5 % / 3 % segun kVA. Guia DSE 057-045: 5 %.",
      "Ancha: al cerrar circulan reactivos y salta la 40 o la sobrecorriente.",
      "Medir V gen y V barra en el mismo instrumento antes del cierre."),
    P("sync_angulo", "Sincronizador", "Ventana de angulo de fase",
      "Synchroniser · Check sync · phase angle", "°",
      "Angulo maximo entre fasores al dar la orden de cierre.",
      "IEEE 1547-2018: 20° / 15° / 10° segun kVA. Guia DSE 057-045: 5°. Mas estrecho "
      "si el interruptor es lento.",
      "Ancha: par de choque en el acoplamiento y el devanado.",
      "Registrar el angulo del cierre en el historial del modulo."),
    P("sync_desliz_obj", "Sincronizador", "Deslizamiento objetivo / sentido",
      "Synchroniser · slip frequency", "Hz",
      "Con cuanto exceso de velocidad se acerca el generador a la barra.",
      "Levemente positivo (generador mas rapido) para entrar tomando carga, no "
      "absorbiendola. Menor que la ventana de frecuencia.",
      "Negativo: entra motorizado y dispara la 32. Grande: el angulo pasa rapido "
      "por la ventana y el cierre llega tarde.",
      "Observar el sincronoscopio: debe girar lento en sentido rapido."),
    P("t_cierre", "Sincronizador", "Tiempo de cierre del interruptor (compensacion)",
      "Breaker · close time / advance", "ms",
      "Lo que tarda el interruptor en juntar contactos; el modulo adelanta la orden.",
      "Medido con analizador de tiempos o de la placa del interruptor; no se estima.",
      "Sin compensar: el angulo en el contacto es mayor que el de la orden.",
      "Prueba de tiempos del interruptor; nefer sincronismo verificar --t-cierre."),
    P("sync_timeout", "Sincronizador", "Tiempo maximo de sincronizacion",
      "Synchroniser · fail to sync timer", "s",
      "Si no sincroniza en este tiempo, alarma.",
      "Mayor que el tiempo normal de sincronizacion medido, con margen. Vigilar su "
      "tendencia: subir es aviso de gobernador gastado.",
      "Corto: alarmas falsas. Muy largo: el grupo queda buscando y la carga espera.",
      "nefer sincronismo tendencia sobre tiempo_sincronizacion_s."),
    P("barra_muerta", "Sincronizador", "Cierre en barra muerta",
      "Bus · dead bus close / dead bus voltage", "on/off · V",
      "Permite a la primera unidad cerrar sobre la barra sin tension.",
      "Activo, con umbral de barra muerta bien por debajo de la nominal y "
      "arbitraje por MSC para que cierre una sola.",
      "Dos unidades cierran a la vez sobre la barra muerta, fuera de fase.",
      "Prueba de arranque simultaneo: debe cerrar una sola."),
    # --- Reparto
    P("modo_reparto", "Reparto de carga", "Modo: isocrono compartido / estatismo",
      "Load share · load sharing / droop active", "—",
      "Como reparten kW las unidades.",
      "Con MSC: isocrono compartido (frecuencia fija). Estatismo solo si no hay "
      "enlace o se trabaja con red.",
      "Mezcla sin coordinar: unidades que se disputan la carga.",
      "nefer sincronismo estatismo; ver el reparto a 25/50/75/100 %."),
    P("estatismo_kw", "Reparto de carga", "Estatismo de velocidad (si se usa)",
      "Governor · droop %", "%",
      "Cuanto cae la frecuencia de vacio a plena carga.",
      "Igual en todas las unidades. Con la consigna en vacio que da nefer "
      "estatismo para que repartan parejo.",
      "Distinto entre unidades: reparto desigual a toda carga.",
      "nefer sincronismo estatismo planta.json."),
    P("estatismo_kvar", "Reparto de carga", "Estatismo de tension / reparto de kVAr",
      "AVR · voltage droop / kvar share", "%",
      "Reparto de reactivos entre unidades.",
      "Igual en todas; con MSC, reparto de kVAr activo.",
      "Corriente reactiva circulante y disparos por 40.",
      "nefer sincronismo reparto (kvar por unidad)."),
    P("rampa_subida", "Reparto de carga", "Rampa de toma de carga",
      "Load control · ramp up rate", "%/s",
      "Velocidad con que la unidad toma su parte despues de cerrar.",
      "Lo que el motor acepta sin caida de frecuencia: el escalon de carga "
      "admisible del motor (ISO 8528-5 / dato del fabricante del motor).",
      "Rapida: caida de frecuencia y humo. Lenta: las demas cargan de mas un rato.",
      "Registrar f durante la toma de carga."),
    P("rampa_bajada", "Reparto de carga", "Rampa de descarga",
      "Load control · ramp down rate", "%/s",
      "Velocidad con que se descarga antes de abrir.",
      "Tal que las demas unidades absorban la carga sin sobrecargarse.",
      "Rapida: escalon a las demas. Lenta: retrasa la parada.",
      "Observar kW de las demas durante la descarga."),
    P("nivel_apertura", "Reparto de carga", "Nivel de apertura al final de la rampa",
      "Load control · ramp down / unload level", "% kW",
      "Carga a la que se abre el 52G al terminar la descarga.",
      "Por ENCIMA del pickup de potencia inversa: se abre antes de motorizar.",
      "Por debajo del pickup de la 32: cada parada termina en disparo por potencia inversa.",
      "Revision automatica de nefer (nivel_apertura > p32_pickup)."),
    P("arranque_demanda", "Reparto de carga", "Arranque / parada por demanda",
      "Load demand · start/stop levels", "% kW",
      "Niveles de carga a los que entra o sale una unidad.",
      "Nivel de parada claramente menor que el de arranque, para que no cicle.",
      "Niveles cercanos: unidades que arrancan y paran en ciclo.",
      "Contar arranques por dia en el historial."),
    # --- Protecciones del paralelo
    P("p32_pickup", "Protecciones", "Potencia inversa (32): pickup",
      "Generator protection · reverse power", "% kW",
      "Potencia absorbida a la que dispara.",
      "Segun estudio de coordinacion; referencia de taller diesel 5–15 %.",
      "Alto: el grupo se motoriza sin disparar. Bajo: dispara en cada transitorio.",
      "Prueba de 32 en la puesta en marcha."),
    P("p32_retardo", "Protecciones", "Potencia inversa (32): retardo",
      "Generator protection · reverse power delay", "s",
      "Tiempo sosteniendo potencia inversa antes de disparar.",
      "Mayor que la oscilacion del cierre; referencia 1–10 s.",
      "Corto: dispara al cerrar. Largo: el motor arrastrado se daña.",
      "Prueba de 32."),
    P("p40", "Protecciones", "Perdida de excitacion (40)",
      "Generator protection · loss of excitation / kvar negative", "kVAr · s",
      "Dispara la unidad que absorbe reactivos de la barra.",
      "Segun la curva de capacidad del alternador y el estudio.",
      "Deshabilitada: una unidad sin campo arrastra la tension de la barra.",
      "Revisar que este habilitada en todas."),
    P("p27_59", "Protecciones", "Sub y sobretension (27/59)",
      "Generator protection · under/over voltage", "% · s",
      "Limites de tension del generador.",
      "Segun la carga y el estudio; respecto de 380 V nominal.",
      "Estrechos: disparos en transitorios de toma de carga.",
      "Revisar umbrales contra la nominal declarada."),
    P("p81", "Protecciones", "Sub y sobrefrecuencia (81U/81O)",
      "Generator protection · under/over frequency", "% · s",
      "Limites de frecuencia del generador.",
      "En estatismo, 81O por encima de la frecuencia en vacio.",
      "81O por debajo de la f en vacio: disparo al quedar sin carga.",
      "Revision automatica de nefer (81O > f en vacio)."),
    P("msc_alarma", "Protecciones", "Falla del enlace MSC",
      "MSC · link failure action", "accion",
      "Que hace la unidad si pierde el enlace con las demas.",
      "Una accion definida (alarma, pasar a estatismo o descargar y abrir).",
      "Sin accion: unidades en isocrono sin enlace que se disputan la carga.",
      "Desconectar el MSC en prueba y observar."),
)

TTA: tuple[Parametro, ...] = (
    P("red_sub_v", "Deteccion de falla de red", "Subtension de red",
      "Mains · under voltage", "V o %",
      "Tension de red por debajo de la cual se considera falla.",
      "Por debajo del minimo que la carga tolera; respecto de 380 V entre fases.",
      "Alta: arranca por caidas normales de la red. Baja: la carga sufre antes de transferir.",
      "Bajar la tension con variac en prueba, o revisar el historial de eventos."),
    P("red_sobre_v", "Deteccion de falla de red", "Sobretension de red",
      "Mains · over voltage", "V o %",
      "Tension de red por encima de la cual se considera falla.",
      "Por encima del maximo normal de la red local.",
      "Baja: transferencias por sobretensiones normales.", "Historial de eventos."),
    P("red_f", "Deteccion de falla de red", "Sub y sobrefrecuencia de red",
      "Mains · under/over frequency", "Hz",
      "Frecuencia de red fuera de la cual se transfiere.",
      "Alrededor de 60 Hz segun la estabilidad de la red local.",
      "Estrecha: transferencias innecesarias.", "Historial de eventos."),
    P("red_secuencia", "Deteccion de falla de red", "Secuencia de fases de red",
      "Mains · phase rotation", "on/off",
      "Considera falla si la red llega con la secuencia invertida.",
      "Activa si hay motores en la carga.",
      "Inactiva: tras un trabajo en la red, los motores giran al reves.",
      "Secuencimetro."),
    P("t_transitorio", "Temporizadores", "Retardo de falla de red (transitorio)",
      "Timers · mains transient delay", "s",
      "Cuanto debe durar la falla para considerarla real.",
      "Mayor que las interrupciones breves de la red (recierres).",
      "Corto: arranca por parpadeos. Largo: la carga queda sin energia mas tiempo.",
      "Historial: arranques por falla de red de pocos segundos."),
    P("t_arranque", "Temporizadores", "Retardo de arranque",
      "Timers · start delay", "s",
      "Espera entre la falla confirmada y el arranque.",
      "Corto si la carga es critica.", "Largo: mas tiempo sin energia.",
      "Medir desde la falla hasta el arranque."),
    P("t_calentamiento", "Temporizadores", "Calentamiento antes de tomar carga",
      "Timers · warm up", "s",
      "Tiempo en vacio antes de cerrar KM2.",
      "Lo que pide el fabricante del motor; cero si la carga es de emergencia.",
      "Largo: carga sin energia. Cero en motor frio: humo y caida de f.",
      "Medir del arranque al cierre de KM2."),
    P("t_transferencia", "Temporizadores", "Tiempo muerto de transferencia",
      "Timers · transfer time / breaker interlock", "s",
      "Tiempo con ambos contactores abiertos al pasar de una fuente a otra.",
      "Mayor que cero y que el tiempo de apertura del contactor; mas si hay motores "
      "grandes (tension residual).",
      "Cero o menor que la apertura: red y grupo en paralelo un instante.",
      "Osciloscopio o registro en las bobinas KM1/KM2."),
    P("t_retorno", "Temporizadores", "Retardo de retorno de red",
      "Timers · mains return delay", "s",
      "Cuanto debe estar estable la red antes de retransferir.",
      "Mayor que el retardo de falla: confirmar que la red volvio de verdad.",
      "Corto: ida y vuelta varias veces si la red esta inestable.",
      "Historial: transferencias seguidas."),
    P("t_enfriamiento", "Temporizadores", "Enfriamiento",
      "Timers · cooling", "s",
      "Tiempo en vacio despues de retransferir, antes de parar.",
      "Lo que pide el fabricante del motor (turbo).",
      "Cero: el turbo se queda sin aceite caliente; dano al rodamiento.",
      "Medir de la retransferencia a la parada."),
    P("salida_red", "Salidas", "Salida «cerrar red» / «abrir red»",
      "Outputs · close mains output", "salida",
      "Que salida del modulo mueve KM1.",
      "La que este cableada al rele K1; con el contacto NC de KM2 en serie.",
      "Salida invertida (abrir en vez de cerrar): la carga queda sin red con red buena.",
      "Forzar la salida desde el modulo con la potencia aislada."),
    P("salida_grupo", "Salidas", "Salida «cerrar grupo» / «abrir grupo»",
      "Outputs · close generator output", "salida",
      "Que salida del modulo mueve KM2.",
      "La cableada al rele K2; con el NC de KM1 en serie.",
      "Igual que la anterior.", "Forzar la salida con la potencia aislada."),
    P("entradas_aux", "Entradas", "Auxiliares de KM1 y KM2",
      "Inputs · mains / generator closed auxiliary", "entrada",
      "Confirmacion al modulo de que cada contactor cerro.",
      "Activas si estan cableadas; dan alarma de falla de contactor.",
      "Sin ellas el modulo no detecta un contactor que no cerro.",
      "Abrir el contactor a mano: el modulo debe alarmar."),
    P("ejercicio", "Programacion", "Prueba programada (ejercicio)",
      "Scheduler · exercise", "dia/hora",
      "Arranque periodico del grupo, con o sin carga.",
      "Semanal o segun el plan de mantenimiento; con carga si es posible.",
      "Sin ejercicio: la falla del grupo aparece el dia del corte.",
      "Historial: ejercicios registrados."),
)

CATALOGOS = {"sincronismo": SINCRONISMO, "tta": TTA}


# --- revision de coherencia -------------------------------------------------

def revisar(tipo: str, valores: dict, planta: dict | None = None) -> list[dict]:
    """Reglas que relacionan unos parametros con otros.

    Solo opina sobre lo que esta declarado; lo que falta se lista como «sin
    declarar», no se supone.
    """
    planta = planta or {}
    valores = {k: v for k, v in (valores or {}).items() if v is not None}
    obs: list[dict] = []

    def add(sev, clave, texto):
        obs.append({"severidad": sev, "parametro": clave, "texto": texto})

    catalogo = CATALOGOS[tipo]
    faltan = [p.nombre for p in catalogo
              if not any(k == p.clave or k.startswith(p.clave + "_") for k in valores)]
    if faltan:
        add("oportunidad", "*", f"Sin declarar ({len(faltan)}): " + "; ".join(faltan) + ".")

    g = valores.get
    if tipo == "sincronismo":
        kva = max((u.get("kva_nominal") or 0) for u in planta.get("unidades", [{}])) or None
        if kva:
            v = verificacion.ventana_por_potencia(kva)
            for clave, tope, u in (("sync_df", v.delta_f_hz, "Hz"),
                                   ("sync_dv", v.delta_v_pct, "%"),
                                   ("sync_angulo", v.delta_angulo_grados, "°")):
                if g(clave) is not None and g(clave) > tope:
                    add("programable", clave,
                        f"{g(clave)} {u} supera {tope:g} {u} de {v.fuente}.")
        if g("sync_desliz_obj") is not None:
            if g("sync_desliz_obj") <= 0:
                add("detiene", "sync_desliz_obj",
                    "Deslizamiento objetivo nulo o negativo: el generador entra "
                    "absorbiendo potencia (32).")
            if g("sync_df") is not None and g("sync_desliz_obj") >= g("sync_df"):
                add("programable", "sync_desliz_obj",
                    "Deslizamiento objetivo igual o mayor que la ventana de "
                    "frecuencia: nunca queda dentro.")
        if g("t_cierre") is not None and g("sync_desliz_obj") and g("sync_angulo"):
            adelanto = 360 * g("sync_desliz_obj") * g("t_cierre") / 1000
            if adelanto > g("sync_angulo") / 2:
                add("programable", "t_cierre",
                    f"El interruptor consume {adelanto:.1f}° de la ventana de "
                    f"{g('sync_angulo')}°: compense el adelanto o baje el deslizamiento.")
        if g("nivel_apertura") is not None and g("p32_pickup") is not None:
            if g("nivel_apertura") <= g("p32_pickup"):
                add("detiene", "nivel_apertura",
                    f"La rampa abre al {g('nivel_apertura')} % y la 32 dispara al "
                    f"{g('p32_pickup')} %: abra por encima del pickup.")
        if g("estatismo_kw") == 0 and g("modo_reparto") == "droop":
            add("detiene", "estatismo_kw", "Modo estatismo con estatismo 0 %: es isocrono sin enlace.")
        if g("barra_muerta") is False:
            add("programable", "barra_muerta",
                "Sin cierre en barra muerta, ninguna unidad puede levantar la planta "
                "tras un apagon total.")
        f_nom = float(planta.get("f_nominal", 60))
        if g("p81_o_pct") is not None and g("modo_reparto") == "droop":
            for u in planta.get("unidades", []):
                if u.get("f_vacio") and f_nom * g("p81_o_pct") / 100 <= u["f_vacio"]:
                    add("detiene", "p81",
                        f"81O a {f_nom * g('p81_o_pct') / 100:.2f} Hz no supera la f en "
                        f"vacio de {u['id']} ({u['f_vacio']} Hz).")
        if g("arranque_demanda_arranque_pct") is not None and g("arranque_demanda_parada_pct") is not None:
            if g("arranque_demanda_parada_pct") >= g("arranque_demanda_arranque_pct") - 10:
                add("programable", "arranque_demanda",
                    "Niveles de arranque y parada por demanda muy cercanos: riesgo "
                    "de que las unidades ciclen.")
    else:
        if g("t_transferencia") is not None and g("t_transferencia") <= 0:
            add("detiene", "t_transferencia",
                "Tiempo muerto de transferencia nulo: red y grupo pueden quedar en "
                "paralelo un instante.")
        if g("t_retorno") is not None and g("t_transitorio") is not None:
            if g("t_retorno") <= g("t_transitorio"):
                add("programable", "t_retorno",
                    "El retorno de red es mas corto que la confirmacion de falla: con "
                    "red inestable, ida y vuelta.")
        if g("t_enfriamiento") == 0:
            add("programable", "t_enfriamiento", "Sin enfriamiento: dano al turbo.")
        if g("red_secuencia") is False:
            add("programable", "red_secuencia",
                "Sin vigilancia de secuencia de red: tras un trabajo en la red, los "
                "motores pueden girar al reves.")
        v = planta.get("v_nominal", 380)
        if g("red_sub_v") is not None and g("red_sobre_v") is not None:
            if not g("red_sub_v") < v < g("red_sobre_v"):
                add("detiene", "red_sub_v",
                    f"La nominal {v:g} V no queda entre sub ({g('red_sub_v')}) y sobre "
                    f"({g('red_sobre_v')}): el modulo veria falla con la red normal.")
    orden = {"detiene": 0, "programable": 1, "oportunidad": 2}
    obs.sort(key=lambda o: orden[o["severidad"]])
    return obs


# --- hoja de configuracion ---------------------------------------------------

def _fmt(v):
    if v is True:
        return "Si"
    if v is False:
        return "No"
    return str(v)


def hoja_markdown(tipo: str, planta: dict | None = None) -> str:
    planta = planta or {}
    valores = (planta.get("parametros") or {}).get(tipo, {})
    titulo = "Sincronismo" if tipo == "sincronismo" else "Transferencia automatica (TTA)"
    L = [f"# Hoja de configuracion — {titulo}", "",
         f"Planta: {planta.get('planta', '____')}  ·  Tension {planta.get('v_nominal', 380):g} V  "
         f"·  {planta.get('f_nominal', 60):g} Hz  ·  Fecha ____  ·  Tecnico ____", "",
         "Los nombres DSE orientan la busqueda en Configuration Suite y pueden variar "
         "con la version del modulo. Ningun valor por defecto del fabricante se toma "
         "como recomendado.", ""]
    grupo = None
    for p in CATALOGOS[tipo]:
        if p.grupo != grupo:
            grupo = p.grupo
            L += [f"## {grupo}", ""]
        val = valores.get(p.clave)
        L += [f"### {p.nombre}  ({p.unidad})", "",
              f"- **En DSE:** {p.dse}",
              f"- **Que hace:** {p.que_hace}",
              f"- **Como decidir:** {p.como_decidir}",
              f"- **Si queda mal:** {p.si_queda_mal}",
              f"- **Como se comprueba:** {p.verificacion}",
              f"- **Valor ajustado:** {_fmt(val) if val is not None else '________'}", ""]
    obs = revisar(tipo, valores, planta) if valores else []
    if obs:
        L += ["## Revision de coherencia", ""]
        L += [f"- [{o['severidad']}] {o['texto']}" for o in obs]
        L.append("")
    return "\n".join(L)


def hoja_html(tipo: str, planta: dict | None = None) -> str:
    planta = planta or {}
    valores = (planta.get("parametros") or {}).get(tipo, {})
    titulo = ("Parametros de sincronismo" if tipo == "sincronismo"
              else "Parametros de TTA")
    filas, grupo = [], None
    for p in CATALOGOS[tipo]:
        if p.grupo != grupo:
            grupo = p.grupo
            filas.append(f'<tr class="g"><th colspan="4">{escape(grupo)}</th></tr>')
        val = valores.get(p.clave)
        filas.append(
            f"<tr><td><b>{escape(p.nombre)}</b><br><small>{escape(p.dse)}</small></td>"
            f"<td>{escape(p.unidad)}</td>"
            f"<td>{escape(p.que_hace)}<details><summary>Como decidir · si queda mal · "
            f"como se comprueba</summary><p><b>Como decidir:</b> {escape(p.como_decidir)}</p>"
            f"<p><b>Si queda mal:</b> {escape(p.si_queda_mal)}</p>"
            f"<p><b>Como se comprueba:</b> {escape(p.verificacion)}</p></details></td>"
            f"<td class='v'>{escape(_fmt(val)) if val is not None else ''}</td></tr>")
    obs = revisar(tipo, valores, planta) if valores else []
    rev = ""
    if obs:
        rev = "<h2>Revision de coherencia</h2><ul>" + "".join(
            f"<li class='{o['severidad']}'><b>{o['severidad']}</b> — {escape(o['texto'])}</li>"
            for o in obs) + "</ul>"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{titulo}</title>
<style>
:root{{--fondo:#f4f6f8;--panel:#fff;--tinta:#111827;--suave:#4b5563;--borde:#d1d5db}}
@media (prefers-color-scheme:dark){{:root{{--fondo:#0f172a;--panel:#1e293b;--tinta:#e5e7eb;
--suave:#9ca3af;--borde:#334155}}}}
body{{margin:0;background:var(--fondo);color:var(--tinta);font:15px/1.45 system-ui,Arial,sans-serif}}
main{{max-width:1060px;margin:0 auto;padding:16px}}
.tabla{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:var(--panel)}}
td,th{{border:1px solid var(--borde);padding:8px;vertical-align:top;text-align:left}}
tr.g th{{background:#2563eb;color:#fff}}small{{color:var(--suave)}}
td.v{{min-width:90px}}details summary{{cursor:pointer;color:#2563eb;margin-top:4px}}
li.detiene{{color:#b91c1c}}li.programable{{color:#b45309}}
@media print{{details{{display:block}}details>summary{{display:none}}}}
</style></head><body><main>
<h1>{titulo}</h1>
<p>Planta: {escape(str(planta.get('planta', '____')))} · {planta.get('v_nominal', 380):g} V ·
{planta.get('f_nominal', 60):g} Hz. Los nombres DSE orientan la busqueda en Configuration
Suite (DSE 057-238) y pueden variar con la version. Ningun valor por defecto del fabricante
se toma como recomendado.</p>
<div class="tabla"><table><tr><th>Parametro</th><th>Unidad</th><th>Que hace</th>
<th>Valor ajustado</th></tr>{''.join(filas)}</table></div>{rev}
<p><small>Generado por nefer sincronismo parametros.</small></p>
</main></body></html>
"""
