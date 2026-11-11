"""Sincronismo: permisivo de cierre, reparto, estatismo, protecciones,
tendencias, guia de sintomas e informe."""

import datetime as dt
import json
from pathlib import Path

import pytest

from nefer.cli import main
from nefer.sincronismo import (diagnostico, informe, protecciones, reparto,
                               tendencias, verificacion)

RAIZ = Path(__file__).resolve().parent.parent
EJ = RAIZ / "ejemplos" / "sincronismo"


# --- verificacion (ANSI 25) -------------------------------------------------

def test_ventana_ieee1547_por_potencia():
    assert verificacion.ventana_por_potencia(300).delta_angulo_grados == 20
    assert verificacion.ventana_por_potencia(500).delta_f_hz == 0.3
    assert verificacion.ventana_por_potencia(501).delta_v_pct == 5
    assert verificacion.ventana_por_potencia(2000).delta_f_hz == 0.1


def _lectura(**kw):
    base = dict(v_barra=480, f_barra=60, v_gen=482, f_gen=60.1,
                angulo_grados=0, t_cierre_s=0.1)
    base.update(kw)
    return verificacion.Lectura(**base)


def test_cierre_permitido_y_angulo_en_el_contacto():
    v = verificacion.verificar(_lectura(), verificacion.ventana_por_potencia(625))
    assert v.permitido
    # 360 * 0.1 Hz * 0.1 s = 3.6 grados de adelanto
    assert v.angulo_adelanto == pytest.approx(3.6)
    assert v.angulo_contacto == pytest.approx(3.6)


def test_angulo_juzgado_en_el_contacto_no_en_la_orden():
    # La orden a 10° parece dentro de ±15°, pero el contacto llega a 17.2°.
    v = verificacion.verificar(_lectura(f_gen=60.2, angulo_grados=10),
                               verificacion.ventana_por_potencia(625))
    assert not v.permitido
    assert v.angulo_contacto == pytest.approx(17.2)
    assert v.espera_s is not None and v.espera_s > 0


def test_secuencia_distinta_bloquea_siempre():
    v = verificacion.verificar(_lectura(secuencia_gen="ACB"),
                               verificacion.ventana_por_potencia(625))
    assert not v.permitido
    assert any("Secuencia" in b for b in v.bloqueos)


def test_deslizamiento_negativo_avisa_potencia_inversa():
    v = verificacion.verificar(_lectura(f_gen=59.95),
                               verificacion.ventana_por_potencia(625))
    assert v.permitido
    assert any("32" in a for a in v.avisos)


def test_espera_hasta_ventana_con_deslizamiento_positivo():
    # Contacto a +30°, desliz +0.1 Hz: debe dar la vuelta hasta -15°: 315°/36°/s
    v = verificacion.verificar(_lectura(angulo_grados=26.4),
                               verificacion.ventana_por_potencia(625))
    assert v.espera_s == pytest.approx(315 / 36, abs=0.01)


def test_envolver_angulo():
    v = verificacion.verificar(_lectura(angulo_grados=359, f_gen=60.0),
                               verificacion.ventana_por_potencia(625))
    assert v.angulo_contacto == pytest.approx(-1)


# --- reparto ----------------------------------------------------------------

def test_reparto_por_unidad_de_placa_no_por_kw():
    us = [reparto.Unidad("A", 500, kw=250), reparto.Unidad("B", 1000, kw=500)]
    r = reparto.analizar_reparto(us)
    assert r.pu_kw_planta == 0.5
    assert all(abs(f.desvio_kw_pct) < 1e-9 for f in r.filas)
    assert not r.hallazgos


def test_reparto_detecta_motorizacion_y_circulante():
    us = [reparto.Unidad("A", 500, kw=600, kvar=200),
          reparto.Unidad("B", 500, kw=-20, kvar=-80)]
    r = reparto.analizar_reparto(us)
    textos = " ".join(h["texto"] for h in r.hallazgos)
    assert "motorizando" in textos
    assert "circulante" in textos
    assert any(h["severidad"] == "detiene" for h in r.hallazgos)


def test_reparto_exige_dos_unidades():
    with pytest.raises(ValueError):
        reparto.analizar_reparto([reparto.Unidad("A", 500, kw=100)])


def test_estatismo_iguales_reparten_parejo():
    us = [reparto.Unidad("A", 500, f_vacio=62.4, estatismo_pct=4),
          reparto.Unidad("B", 1000, f_vacio=62.4, estatismo_pct=4)]
    p = reparto.predecir_estatismo(us, 1500, 60)
    assert p.referencia == pytest.approx(60.0)
    assert p.toma == {"A": 500.0, "B": 1000.0}
    p = reparto.predecir_estatismo(us, 750, 60)
    assert p.referencia == pytest.approx(61.2)
    assert p.pu["A"] == pytest.approx(0.5)


def test_estatismo_consigna_baja_toma_menos_y_se_sugiere():
    us = [reparto.Unidad("A", 500, f_vacio=62.4, estatismo_pct=4),
          reparto.Unidad("B", 500, f_vacio=62.0, estatismo_pct=4)]
    p = reparto.predecir_estatismo(us, 1000, 60)
    assert p.toma["A"] > p.toma["B"]
    assert p.consigna_sugerida["B"] == pytest.approx(62.4)
    assert any(h["unidad"] == "A" for h in p.hallazgos)


def test_isocrona_toma_el_resto():
    us = [reparto.Unidad("ISO", 1000, modo="isocrono"),
          reparto.Unidad("D", 500, f_vacio=61.2, estatismo_pct=4)]
    p = reparto.predecir_estatismo(us, 800, 60)
    assert p.referencia == 60
    assert p.toma["D"] == pytest.approx(250)
    assert p.toma["ISO"] == pytest.approx(550)


def test_dos_isocronas_sin_lineas_se_marcan():
    us = [reparto.Unidad("A", 500, modo="isocrono"),
          reparto.Unidad("B", 500, modo="isocrono")]
    p = reparto.predecir_estatismo(us, 500, 60)
    assert any("isocrono" in h["texto"] and h["severidad"] == "detiene"
               for h in p.hallazgos)


def test_estatismo_reactivo():
    us = [reparto.Unidad("A", 400, kva_nominal=500, v_vacio=494.4, estatismo_v_pct=3),
          reparto.Unidad("B", 400, kva_nominal=500, v_vacio=494.4, estatismo_v_pct=3)]
    p = reparto.predecir_estatismo_reactivo(us, 600, 480)
    assert p.referencia == pytest.approx(480)
    assert p.toma["A"] == pytest.approx(300)


# --- protecciones -----------------------------------------------------------

def test_protecciones_faltantes_y_fuera_de_rango():
    obs = protecciones.revisar("GE", {"25": {}, "32": {"pickup_pct": 2,
                                                       "retardo_s": 3}})
    por_funcion = {(o.funcion, o.severidad) for o in obs}
    assert ("40", "detiene") in por_funcion
    assert ("32", "programable") in por_funcion
    assert not any(o.funcion == "46" for o in obs)  # opcional, no se exige


def test_proteccion_deshabilitada_cuenta_como_faltante():
    obs = protecciones.revisar("GE", {"32": {"habilitada": False}})
    assert any(o.funcion == "32" and o.severidad == "detiene" for o in obs)


# --- tendencias -------------------------------------------------------------

def _regs(valores, variable="tiempo_sincronizacion_s", equipo="GE"):
    d0 = dt.date(2026, 1, 1)
    return [tendencias.Registro(d0 + dt.timedelta(days=10 * i), equipo, variable,
                                str(v)) for i, v in enumerate(valores)]


def test_tendencia_proyecta_cruce_en_fecha():
    regs = _regs([10, 12, 14, 16, 18])  # +0.2 por dia, cruza 30 en el dia 100
    t, = tendencias.proyectar(regs, hoy=dt.date(2026, 2, 10))
    assert t.cruza_el == "2026-04-11"
    assert t.dias_restantes == 60
    assert t.severidad == "oportunidad"


def test_tendencia_no_proyecta_con_pocos_puntos():
    t, = tendencias.proyectar(_regs([10, 20, 25]))
    assert t.cruza_el is None and "hacen falta" in t.texto


def test_tendencia_no_proyecta_ruido():
    t, = tendencias.proyectar(_regs([10, 25, 9, 24, 11, 23, 10]))
    assert t.cruza_el is None and "Dispersion" in t.texto


def test_tendencia_sobre_el_limite_detiene():
    t, = tendencias.proyectar(_regs([10, 20, 31]))
    assert t.severidad == "detiene"


def test_reincidencias():
    regs = _regs(["32 potencia inversa"] * 3, variable="alarma")
    r, = tendencias.reincidencias(regs, hoy=dt.date(2026, 2, 15))
    assert r.veces == 3 and r.intervalo_medio_dias == 10
    assert r.vencida and r.severidad == "detiene"
    assert tendencias.reincidencias(regs[:1], hoy=dt.date(2026, 1, 5)) == []


def test_csv_con_fecha_ilegible(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text("fecha,equipo,variable,valor\n01/02/2026,GE,alarma,x\n")
    with pytest.raises(ValueError, match="AAAA-MM-DD"):
        tendencias.leer_csv(f)


# --- diagnostico ------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("el grupo no sincroniza, se queda buscando", "S1"),
    ("dispara por potencia inversa cuando cierra", "S2"),
    ("los dos grupos pendulean, se pasan la carga", "S3"),
    ("hay corriente circulante y uno absorbe reactivos", "S4"),
    ("se escucha un golpe al cerrar el interruptor", "S6"),
])
def test_diagnostico_encuentra_el_sintoma(texto, esperado):
    assert diagnostico.buscar(texto)[0][0].id == esperado


def test_diagnostico_sin_coincidencia():
    assert diagnostico.buscar("cambio de aceite") == []


def test_guia_publicada_sale_del_generador():
    publicada = (EJ / "guia-sintomas-paralelo.md").read_text(encoding="utf-8")
    assert publicada.rstrip("\n") == diagnostico.exportar_markdown().rstrip("\n"), (
        "la guia no esta al dia: python -m nefer sincronismo guia "
        "-o ejemplos/sincronismo/guia-sintomas-paralelo.md")


# --- informe y CLI ----------------------------------------------------------

def test_informe_del_ejemplo_prioriza():
    planta = informe.cargar_planta(EJ / "planta.json")
    regs = tendencias.leer_csv(EJ / "registro.csv")
    res = informe.analizar(planta, regs, hoy=dt.date(2026, 11, 11))
    sev = [h["severidad"] for h in res["hallazgos"]]
    assert sev == sorted(sev, key=informe.ORDEN.get)
    textos = " ".join(h["texto"] for h in res["hallazgos"])
    assert "40 Perdida de excitacion" in textos           # GE-02 sin 40
    assert "circulante" in textos                          # GE-03 absorbe kVAr
    assert "cruza 30" in textos                            # deriva de GE-02
    md = informe.a_markdown(res)
    assert md.startswith("# Informe de sincronismo")


def test_planta_con_ids_repetidos(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"unidades": [{"id": "A", "kw_nominal": 1},
                                          {"id": "A", "kw_nominal": 1}]}))
    with pytest.raises(ValueError, match="unico"):
        informe.cargar_planta(f)


def test_protocolo_tiene_columna_por_unidad():
    md = informe.protocolo_markdown(informe.cargar_planta(EJ / "planta.json"))
    assert "| Paso | GE-01 | GE-02 | GE-03 |" in md


def test_cli(capsys, tmp_path):
    assert main(["sincronismo", "verificar", "--v-barra", "480", "--f-barra", "60",
                 "--v-gen", "482", "--f-gen", "60.1", "--angulo", "0",
                 "--kva", "625"]) == 0
    assert "CIERRE PERMITIDO" in capsys.readouterr().out
    assert main(["sincronismo", "estatismo", str(EJ / "planta.json"),
                 "--pct", "50"]) == 0
    assert main(["sincronismo", "protecciones", str(EJ / "planta.json")]) == 1
    salida = tmp_path / "informe.md"
    assert main(["sincronismo", "informe", str(EJ / "planta.json"), "-r",
                 str(EJ / "registro.csv"), "-o", str(salida)]) == 0
    assert salida.read_text(encoding="utf-8").startswith("# Informe")
    assert main(["sincronismo", "diagnostico", "no", "sincroniza"]) == 0


# --- isocrono compartido (enlace DSE MSC) y plantilla -----------------------

def test_isocrono_compartido_reparte_por_placa_sin_alarma():
    us = [reparto.Unidad("A", 500, modo="isocrono_compartido"),
          reparto.Unidad("B", 1000, modo="isocrono_compartido")]
    p = reparto.predecir_estatismo(us, 900, 60)
    assert p.referencia == 60
    assert p.toma == {"A": 300.0, "B": 600.0}
    assert not p.hallazgos


def test_isocrono_suelto_junto_a_compartidas_se_marca():
    us = [reparto.Unidad("A", 500, modo="isocrono"),
          reparto.Unidad("B", 500, modo="isocrono_compartido")]
    p = reparto.predecir_estatismo(us, 500, 60)
    assert any(h["severidad"] == "detiene" for h in p.hallazgos)


def test_plantilla_380v_dse_cat(tmp_path):
    f = tmp_path / "planta.json"
    assert main(["sincronismo", "plantilla", "-n", "3", "-o", str(f)]) == 0
    p = json.loads(f.read_text(encoding="utf-8"))
    assert p["v_nominal"] == 380 and p["f_nominal"] == 60
    assert [u["id"] for u in p["unidades"]] == ["GE-01", "GE-02", "GE-03"]
    u = p["unidades"][0]
    assert u["controlador"]["marca"] == "DSE" and u["motor"]["marca"] == "CAT"
    assert u["modo"] == "isocrono_compartido"
    # Sin potencia de placa no se analiza nada: se pide, no se supone.
    with pytest.raises(ValueError, match="kw_nominal"):
        informe.cargar_planta(f)
    for u in p["unidades"]:
        u["kw_nominal"] = 400
    f.write_text(json.dumps(p), encoding="utf-8")
    obs = protecciones.revisar("GE-01", p["unidades"][0]["protecciones"])
    assert obs and all(o.severidad == "oportunidad" for o in obs)  # «falta anotar»


# --- diagramas --------------------------------------------------------------

import xml.etree.ElementTree as ET

from nefer.sincronismo import diagramas


def _planta_dse():
    p = informe.plantilla(3, kw=400, kva=500, modelo_controlador="8610 MKII",
                          modelo_motor="C15")
    p["planta"] = "Prueba"
    return p


def test_diagrama_sincronismo_una_columna_por_unidad():
    svg = diagramas.diagrama_sincronismo(_planta_dse())
    ET.fromstring(svg)                      # XML valido
    for n in (1, 2, 3):
        assert f"GE-0{n}" in svg and f"52G-{n}" in svg
    assert "V barra" in svg and "V gen" in svg and "Enlace MSC" in svg
    assert "380 V 60 Hz" in svg


def test_diagrama_no_inventa_bornes():
    p = _planta_dse()
    svg = diagramas.diagrama_sincronismo(p)
    assert "borne: 057-254" in svg          # remite al manual DSE 8610 MKII
    p["unidades"][0]["bornes"] = {"sensado_gen": "X1-X4"}
    assert "borne X1-X4" in diagramas.diagrama_sincronismo(p)


def test_diagrama_tta():
    p = _planta_dse()
    p["tta"] = {"modulo": "DSE7320 MKII", "polos": 4}
    svg = diagramas.diagrama_tta(p)
    ET.fromstring(svg)
    assert "KM1" in svg and "KM2" in svg and "enclavamiento" in svg
    assert "057-253" in svg


def test_diagramas_publicados_salen_del_generador():
    p = informe.cargar_planta(EJ / "planta-dse-cat.json")
    for nombre, svg in (("diagrama-tta.svg", diagramas.diagrama_tta(p)),
                        ("diagrama-sincronismo.svg", diagramas.diagrama_sincronismo(p))):
        assert (EJ / nombre).read_text(encoding="utf-8") == svg, (
            f"{nombre} no esta al dia: python -m nefer sincronismo diagrama ...")


def test_cli_diagrama(tmp_path):
    destino = tmp_path / "d.svg"
    assert main(["sincronismo", "diagrama", "tta", "-o", str(destino)]) == 0
    assert destino.read_text(encoding="utf-8").startswith("<svg")
    assert main(["sincronismo", "diagrama", "sincronismo"]) == 2
