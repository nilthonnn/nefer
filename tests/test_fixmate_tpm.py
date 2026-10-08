"""TPM · mantenimiento autónomo: la pauta que hace el operador.

Lo que importa fijar aquí son las tres defensas contra la forma concreta en
que una ronda CIL se degrada: deja de ejecutarse y empieza a firmarse.

1. Las clases tienen criterio verificable. «Detectar anomalías» no es una
   clase de punto, porque no hay criterio de aceptación posible para eso.
2. «No pude ver» es un resultado, y rompe la ronda completa.
3. El tiempo se mide, no se declara: una ronda demasiado rápida se detecta.
"""

from __future__ import annotations

import pytest

from nefer.fixmate.tpm import (CLASES, Checklist, Ejecucion, ErrorTPM,
                               FRACCION_SOSPECHOSA, cumplimiento, estado)


def _pauta() -> Checklist:
    c = Checklist("cl-ex220", "EX-220", "Ronda de arranque", frecuencia="diaria")
    c.agregar("limpiar", "Rejilla del radiador",
              "Sin costra que restrinja el aire", segundos=8,
              codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")
    c.agregar("inspeccionar", "Visor de nivel de aceite",
              "Entre mín y máx, aceite claro", segundos=5)
    c.agregar("lubricar", "Grasera del descanso LA",
              "Dos golpes de pistola, sin rebose", segundos=8)
    c.agregar("inspeccionar", "Guarda del acople", "Puesta y con sus pernos",
              alcance_operador=False, segundos=5)
    return c


def _ronda(c: Checklist, resultados, segundos=None) -> Ejecucion:
    e = Ejecucion("ej-1", c.id, c.activo_codigo, "J. Quispe", fecha="2026-03-02")
    for p, r in zip(c.puntos, resultados):
        e.registrar(p.id, r, segundos=(p.segundos if segundos is None else segundos))
    return e


# ------------------------------------------- las clases tienen criterio

def test_son_cinco_clases_y_detectar_anomalias_no_es_una():
    # No hay criterio de aceptación posible para «detectar anomalías»: en
    # campo se marca OK siempre. Es lo que PASA cuando un punto sale NOK.
    assert set(CLASES) == {"limpiar", "inspeccionar", "lubricar", "ajustar",
                           "verificar"}
    with pytest.raises(ErrorTPM, match="no es una clase de punto"):
        _pauta().agregar("detectar anomalias", "x", "y")


def test_un_punto_sin_criterio_se_rechaza():
    with pytest.raises(ErrorTPM, match="criterio de aceptacion"):
        _pauta().agregar("inspeccionar", "Radiador", "   ")


def test_un_punto_necesita_un_sitio_fisico():
    with pytest.raises(ErrorTPM, match="sitio fisico"):
        _pauta().agregar("inspeccionar", "", "Sin fugas")


def test_un_codigo_de_catalogo_inventado_se_rechaza():
    with pytest.raises(ErrorTPM, match="no esta en el catalogo"):
        _pauta().agregar("limpiar", "Radiador", "Limpio",
                         codigo_catalogo="TER.INVENTADO.XYZ")


def test_una_frecuencia_desconocida_se_rechaza():
    with pytest.raises(ErrorTPM, match="frecuencia"):
        Checklist("c", "EX-220", "x", frecuencia="cuando se acuerden")


def test_la_ejecucion_necesita_responsable():
    with pytest.raises(ErrorTPM, match="responsable"):
        Ejecucion("e", "cl", "EX-220", "  ")


# --------------------------------- «no pude ver» rompe la ronda completa

def test_una_ronda_entera_en_ok_esta_completa():
    c = _pauta()
    assert estado(_ronda(c, ["ok"] * 4), c).completa is True


def test_un_punto_sin_acceso_deja_la_ronda_incompleta_aunque_estén_los_cuatro():
    # La alternativa real a `sin_acceso` es un OK falso, y un OK falso
    # contamina la ronda entera.
    c = _pauta()
    s = estado(_ronda(c, ["ok", "ok", "ok", "sin_acceso"]), c)
    assert s.respondidos == 4
    assert s.sin_acceso == 1
    assert s.completa is False


def test_una_ronda_a_medias_lista_lo_que_falta():
    c = _pauta()
    e = Ejecucion("e", c.id, "EX-220", "J. Q.")
    e.registrar(c.puntos[0].id, "ok", segundos=8)
    s = estado(e, c)
    assert s.completa is False
    assert s.pendientes == tuple(p.id for p in c.puntos[1:])


def test_un_nok_no_impide_que_la_ronda_este_completa():
    # Encontrar algo es que la ronda funcionó, no que fallara.
    c = _pauta()
    s = estado(_ronda(c, ["nok", "ok", "ok", "ok"]), c)
    assert s.completa is True and s.nok == 1


def test_corregir_un_punto_reemplaza_en_su_sitio_y_no_altera_el_recorrido():
    # El orden de la pauta es el recorrido físico por la máquina.
    c = _pauta()
    e = _ronda(c, ["ok"] * 4)
    e.registrar(c.puntos[1].id, "nok", "Aceite lechoso", 9)
    assert len(e.items) == 4
    assert [i.punto_id for i in e.items] == [p.id for p in c.puntos]
    assert e.items[1].resultado == "nok"


# --------------------------------------- el tiempo se mide, no se declara

def test_una_ronda_despachada_en_un_segundo_por_punto_es_sospechosa():
    c = _pauta()                      # presupuesto 26 s
    s = estado(_ronda(c, ["ok"] * 4, segundos=1), c)
    assert s.segundos == 4
    assert s.segundos < s.presupuesto_seg * FRACCION_SOSPECHOSA
    assert s.sospechosa_de_firma is True


def test_una_ronda_ejecutada_a_conciencia_no_se_acusa():
    c = _pauta()
    assert estado(_ronda(c, ["ok"] * 4), c).sospechosa_de_firma is False


def test_una_ronda_a_medias_nunca_se_acusa_de_firma():
    # Siempre lleva menos tiempo que el presupuesto: acusarla sería delatar a
    # quien va por el segundo punto.
    c = _pauta()
    e = Ejecucion("e", c.id, "EX-220", "J. Q.")
    e.registrar(c.puntos[0].id, "ok", segundos=1)
    assert estado(e, c).sospechosa_de_firma is False


def test_sin_presupuesto_declarado_no_se_juzga_la_velocidad():
    # Si la pauta no dice cuánto debería costar, el sistema no lo supone.
    c = Checklist("c", "EX-220", "Sin presupuesto")
    c.agregar("inspeccionar", "Radiador", "Limpio")
    e = Ejecucion("e", c.id, "EX-220", "J. Q.")
    e.registrar(c.puntos[0].id, "ok", segundos=0)
    assert estado(e, c).sospechosa_de_firma is False


# --------------------------------------------- cumplimiento del pilar 1

def test_el_cumplimiento_cuenta_rondas_completas_no_rondas_hechas():
    c = _pauta()
    buena = _ronda(c, ["ok"] * 4)
    coja = _ronda(c, ["ok", "ok", "ok", "sin_acceso"])
    coja.id = "ej-2"
    r = cumplimiento([buena, coja], c)
    assert r.ejecuciones == 2 and r.completas == 1
    assert r.cumplimiento == 0.5


def test_sin_ejecuciones_el_cumplimiento_es_none_y_no_cero():
    # Cero se lee como «lo hicieron mal»; None se lee como «no hay dato».
    assert cumplimiento([], _pauta()).cumplimiento is None


def test_un_punto_que_nunca_se_pudo_ver_sale_a_la_luz():
    # No es descuido del operador: es un defecto de la máquina o de la pauta.
    c = _pauta()
    r1 = _ronda(c, ["ok", "ok", "ok", "sin_acceso"])
    r2 = _ronda(c, ["ok", "ok", "ok", "sin_acceso"])
    r2.id = "ej-2"
    assert cumplimiento([r1, r2], c).nunca_vistos == (c.puntos[3].id,)


def test_basta_una_ronda_que_si_lo_vio_para_que_deje_de_estar_nunca_visto():
    c = _pauta()
    coja = _ronda(c, ["ok", "ok", "ok", "sin_acceso"])
    buena = _ronda(c, ["ok"] * 4)
    buena.id = "ej-2"
    assert cumplimiento([coja, buena], c).nunca_vistos == ()


def test_el_cumplimiento_se_desglosa_por_clase():
    # Responde «¿se está lubricando de verdad?» por separado de «¿se está
    # inspeccionando?», que es la pregunta que el total esconde.
    c = _pauta()
    r = cumplimiento([_ronda(c, ["ok"] * 4)], c)
    assert r.por_clase["lubricar"] == 1
    assert r.por_clase["inspeccionar"] == 2
    assert r.por_clase["ajustar"] == 0


def test_lo_que_no_se_pudo_ver_no_cuenta_como_ejecutado_en_su_clase():
    c = _pauta()
    r = cumplimiento([_ronda(c, ["sin_acceso", "ok", "ok", "ok"])], c)
    assert r.por_clase["limpiar"] == 0


def test_una_ronda_con_fecha_ambigua_no_entra():
    # El teléfono siempre manda ISO 8601; una ejecución escrita a mano, no.
    # Y una ronda mal fechada no se puede cruzar con el historial después.
    with pytest.raises(ErrorTPM, match="ISO 8601"):
        Ejecucion(id="r1", checklist_id="c1", activo_codigo="EX-220",
                  operador="J. Quispe", fecha="16/03/2026")
