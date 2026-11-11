"""Subcomandos `nefer sincronismo`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import diagnostico, informe, protecciones, reparto, tendencias, verificacion


def _salida(texto: str, ruta: str | None) -> None:
    if ruta:
        Path(ruta).write_text(texto, encoding="utf-8")
        print(f"Escrito: {ruta}")
    else:
        print(texto)


def cmd_verificar(a) -> int:
    if a.kva:
        ventana = verificacion.ventana_por_potencia(a.kva)
    else:
        ventana = verificacion.Ventana(a.df, a.dv, a.dangulo, "ventana declarada")
    for nombre, valor in (("--df", a.df), ("--dv", a.dv), ("--dangulo", a.dangulo)):
        if a.kva and valor is not None:
            campo = {"--df": "delta_f_hz", "--dv": "delta_v_pct",
                     "--dangulo": "delta_angulo_grados"}[nombre]
            setattr(ventana, campo, valor)
            ventana.fuente += f"; {nombre} declarado"
    if None in (ventana.delta_f_hz, ventana.delta_v_pct, ventana.delta_angulo_grados):
        print("Indique --kva, o las tres ventanas --df --dv --dangulo.", file=sys.stderr)
        return 2
    lectura = verificacion.Lectura(a.v_barra, a.f_barra, a.v_gen, a.f_gen, a.angulo,
                                   a.t_cierre, a.seq_barra, a.seq_gen, a.barra_muerta)
    v = verificacion.verificar(lectura, ventana)
    if a.json:
        print(json.dumps(v.a_dict(), ensure_ascii=False, indent=2))
        return 0 if v.permitido else 1
    print("CIERRE PERMITIDO" if v.permitido else "CIERRE BLOQUEADO")
    print(f"  ΔV {v.delta_v_pct:+.2f} %   desliz {v.deslizamiento_hz:+.3f} Hz   "
          f"angulo orden {v.angulo_orden:+.1f}° -> contacto {v.angulo_contacto:+.1f}° "
          f"(adelanto {v.angulo_adelanto:+.1f}°)")
    print(f"  ventana ±{ventana.delta_f_hz:g} Hz, ±{ventana.delta_v_pct:g} %, "
          f"±{ventana.delta_angulo_grados:g}°  [{ventana.fuente}]")
    for b in v.bloqueos:
        print(f"  BLOQUEO: {b}")
    for w in v.avisos:
        print(f"  aviso:   {w}")
    if v.espera_s:
        print(f"  El angulo entra en ventana en {v.espera_s:.1f} s.")
    return 0 if v.permitido else 1


def _unidades(planta):
    return [reparto.Unidad.desde_dict(u) for u in planta["unidades"]]


def cmd_reparto(a) -> int:
    planta = informe.cargar_planta(a.planta)
    r = reparto.analizar_reparto(_unidades(planta), a.limite_kw, a.limite_kvar)
    if a.json:
        print(json.dumps(r.a_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Planta al {r.pu_kw_planta*100:.0f} % de kW")
        for f in r.filas:
            q = "" if f.desvio_kvar_pct is None else f"   kVAr {f.desvio_kvar_pct:+.1f} %"
            print(f"  {f.id:8} {f.kw:7.0f} kW  {f.pu_kw*100:5.0f} %  "
                  f"desvio kW {f.desvio_kw_pct:+.1f} %{q}")
        for h in r.hallazgos:
            print(f"  [{h['severidad']}] {h['unidad']}: {h['texto']}")
    return 1 if any(h["severidad"] == "detiene" for h in r.hallazgos) else 0


def cmd_estatismo(a) -> int:
    planta = informe.cargar_planta(a.planta)
    unidades = _unidades(planta)
    f_nom = float(planta.get("f_nominal", 60.0))
    carga = a.kw if a.kw is not None else (
        sum(u.kw_nominal for u in unidades) * a.pct / 100)
    p = reparto.predecir_estatismo(unidades, carga, f_nom)
    if a.json:
        print(json.dumps(p.a_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"Carga {carga:.0f} kW -> barra en {p.referencia:.3f} Hz (nominal {f_nom:g})")
    for k, v in p.toma.items():
        sug = p.consigna_sugerida.get(k)
        extra = f"   consigna en vacio sugerida {sug:.2f} Hz" if sug else ""
        print(f"  {k:8} {v:7.0f} kW  {p.pu[k]*100:5.0f} %{extra}")
    for h in p.hallazgos:
        print(f"  [{h['severidad']}] {h['unidad']}: {h['texto']}")
    return 0


def cmd_tendencia(a) -> int:
    regs = tendencias.leer_csv(a.registro)
    limites = {}
    if a.planta:
        limites = informe.cargar_planta(a.planta).get("limites", {})
    tend = tendencias.proyectar(regs, limites)
    rein = tendencias.reincidencias(regs)
    if a.json:
        print(json.dumps({"tendencias": [t.a_dict() for t in tend],
                          "reincidencias": [r.a_dict() for r in rein]},
                         ensure_ascii=False, indent=2))
        return 0
    for t in tend:
        marca = f"[{t.severidad}] " if t.severidad else ""
        print(f"  {marca}{t.equipo} {t.variable}: {t.texto}")
    for r in rein:
        print(f"  [{r.severidad}] {r.equipo} alarma «{r.alarma}»: {r.texto}")
    return 0


def cmd_protecciones(a) -> int:
    planta = informe.cargar_planta(a.planta)
    obs = []
    for u in planta["unidades"]:
        obs += protecciones.revisar(u["id"], u.get("protecciones", {}))
    if a.json:
        print(json.dumps([o.a_dict() for o in obs], ensure_ascii=False, indent=2))
    else:
        print(f"Referencia: {protecciones.FUENTE}")
        for o in obs:
            print(f"  [{o.severidad}] {o.unidad} {o.texto}")
        if not obs:
            print("  Sin observaciones.")
    return 1 if any(o.severidad == "detiene" for o in obs) else 0


def cmd_diagnostico(a) -> int:
    hallados = diagnostico.buscar(" ".join(a.sintoma))
    if not hallados:
        print("Ningun sintoma de la guia coincide. Describa lo que ve "
              "(«no sincroniza», «dispara por potencia inversa», «oscila»...).")
        return 1
    print(diagnostico.ROTULO)
    for s, _ in hallados:
        print(f"\n{s.id}. {s.titulo}")
        for n, c in enumerate(s.causas, 1):
            print(f"  {n}. {c.causa}\n     -> {c.comprobacion}")
    return 0


def cmd_guia(a) -> int:
    _salida(diagnostico.exportar_markdown(), a.salida)
    return 0


def cmd_informe(a) -> int:
    planta = informe.cargar_planta(a.planta)
    regs = tendencias.leer_csv(a.registro) if a.registro else None
    res = informe.analizar(planta, regs)
    if a.json:
        _salida(json.dumps(res, ensure_ascii=False, indent=2), a.salida)
    else:
        _salida(informe.a_markdown(res), a.salida)
    return 0


def cmd_protocolo(a) -> int:
    planta = informe.cargar_planta(a.planta) if a.planta else None
    _salida(informe.protocolo_markdown(planta), a.salida)
    return 0


def cmd_plantilla(a) -> int:
    p = informe.plantilla(a.unidades, a.kw, a.kva, a.v, a.f, a.controlador,
                          a.modelo_controlador, a.motor, a.modelo_motor, a.modo)
    _salida(json.dumps(p, ensure_ascii=False, indent=2) + "\n", a.salida)
    return 0


def agregar_subcomando(sub) -> None:
    s = sub.add_parser("sincronismo",
                       help="grupos electrogenos en paralelo: cierre, reparto, "
                            "protecciones, tendencias e informe")
    o = s.add_subparsers(dest="orden", required=True)

    v = o.add_parser("verificar", help="permisivo de cierre ANSI 25")
    v.add_argument("--v-barra", type=float, required=True)
    v.add_argument("--f-barra", type=float, required=True)
    v.add_argument("--v-gen", type=float, required=True)
    v.add_argument("--f-gen", type=float, required=True)
    v.add_argument("--angulo", type=float, required=True,
                   help="angulo del generador respecto de la barra, grados")
    v.add_argument("--t-cierre", type=float, default=0.1,
                   help="tiempo de cierre del interruptor, s (por defecto 0.1)")
    v.add_argument("--kva", type=float, help="ventanas IEEE 1547 por potencia")
    v.add_argument("--df", type=float)
    v.add_argument("--dv", type=float)
    v.add_argument("--dangulo", type=float)
    v.add_argument("--seq-barra", default="ABC")
    v.add_argument("--seq-gen", default="ABC")
    v.add_argument("--barra-muerta", action="store_true")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_verificar)

    r = o.add_parser("reparto", help="reparto actual de kW y kVAr")
    r.add_argument("planta")
    r.add_argument("--limite-kw", type=float, default=reparto.LIMITE_KW_PCT)
    r.add_argument("--limite-kvar", type=float, default=reparto.LIMITE_KVAR_PCT)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_reparto)

    e = o.add_parser("estatismo", help="predecir el reparto por droop a una carga")
    e.add_argument("planta")
    g = e.add_mutually_exclusive_group()
    g.add_argument("--kw", type=float)
    g.add_argument("--pct", type=float, default=100.0)
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_estatismo)

    t = o.add_parser("tendencia", help="derivas y alarmas reincidentes de un registro CSV")
    t.add_argument("registro")
    t.add_argument("--planta", help="para tomar los limites declarados")
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=cmd_tendencia)

    p = o.add_parser("protecciones", help="revisar 25/32/40/27/59/81 de cada unidad")
    p.add_argument("planta")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_protecciones)

    d = o.add_parser("diagnostico", help="guia de sintomas del paralelo")
    d.add_argument("sintoma", nargs="+")
    d.set_defaults(func=cmd_diagnostico)

    gu = o.add_parser("guia", help="exportar la guia en Markdown para FixMate")
    gu.add_argument("-o", "--salida")
    gu.set_defaults(func=cmd_guia)

    i = o.add_parser("informe", help="informe priorizado de la planta")
    i.add_argument("planta")
    i.add_argument("-r", "--registro", help="CSV fecha,equipo,variable,valor")
    i.add_argument("-o", "--salida")
    i.add_argument("--json", action="store_true")
    i.set_defaults(func=cmd_informe)

    pl = o.add_parser("plantilla", help="planta.json en blanco para llenar")
    pl.add_argument("-n", "--unidades", type=int, default=2)
    pl.add_argument("--kw", type=float, help="potencia de placa, kW")
    pl.add_argument("--kva", type=float, help="potencia de placa, kVA")
    pl.add_argument("--v", type=float, default=380.0, help="tension nominal (380)")
    pl.add_argument("--f", type=float, default=60.0, help="frecuencia nominal (60)")
    pl.add_argument("--controlador", default="DSE")
    pl.add_argument("--modelo-controlador")
    pl.add_argument("--motor", default="CAT")
    pl.add_argument("--modelo-motor")
    pl.add_argument("--modo", default="isocrono_compartido",
                    choices=["isocrono_compartido", "droop", "isocrono"])
    pl.add_argument("-o", "--salida")
    pl.set_defaults(func=cmd_plantilla)

    pr = o.add_parser("protocolo", help="protocolo de puesta en marcha del paralelo")
    pr.add_argument("planta", nargs="?")
    pr.add_argument("-o", "--salida")
    pr.set_defaults(func=cmd_protocolo)
