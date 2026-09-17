"""Analitica de confiabilidad: lo que se puede decir, y lo que no.

Cada numero de aqui lo va a leer alguien que va a comprar un repuesto o a
sacar una maquina de faena. Por eso lo que mas se prueba no es que calcule,
sino que se calle cuando no hay datos: sin dos fechas no hay intervalo, y sin
dos horometros no hay ritmo.
"""

import datetime as dt

from nefer.fixmate import prediccion
from nefer.fixmate.indice import Fragmento, Indice

HOY = dt.date(2026, 9, 15)


def _acta(n, fecha, horas, equipo="GE074-01"):
    return Fragmento(id=f"acta:{n}", tipo="acta", fuente="actas.xlsx",
                     texto=f"acta {n}",
                     metadatos={"codigo_equipo": equipo, "fecha": fecha,
                                "horometro": horas, "n_acta": n})


def _ot(n, fecha, causa, equipo="GE074-01", repuestos=()):
    return Fragmento(id=f"ot:{n}", tipo="informe", fuente="historial.xlsx",
                     texto=f"orden {n}",
                     metadatos={"codigo_equipo": equipo, "fecha": fecha,
                                "causa_raiz": causa, "codigo_ot": n,
                                "repuestos": list(repuestos)})


def _indice(fragmentos) -> Indice:
    indice = Indice()
    indice.agregar(list(fragmentos))
    return indice


CON_HISTORIA = [
    _acta("A1", "2026-01-10", 1200.0),
    _acta("A2", "2026-03-11", 1750.0),
    _acta("A3", "2026-06-09", 2460.0),
    _ot("OT-1", "2026-01-20", "Filtro de aire colmatado por polvo de mina",
        repuestos=["Filtro P533781"]),
    _ot("OT-2", "2026-03-25", "Filtro de aire colmatado", repuestos=["Filtro P533781"]),
    _ot("OT-3", "2026-06-02", "Filtro de aire colmatado por polvo",
        repuestos=["Filtro P533781"]),
    _ot("OT-4", "2026-04-14", "Inyector con retorno excesivo",
        repuestos=["Inyector 0445110"]),
]


# ------------------------------------------------------------------- uso

def test_el_ritmo_sale_de_dos_horometros_con_fecha():
    uso = prediccion.uso_de(prediccion.eventos(_indice(CON_HISTORIA), "GE074-01"))
    assert uso.lecturas == 3
    assert uso.dias_observados == 150
    assert uso.ritmo_horas_dia == 8.4      # (2460 - 1200) / 150
    assert uso.horometro == 2460.0


def test_sin_dos_lecturas_no_hay_ritmo():
    solo_una = _indice([_acta("A1", "2026-01-10", 1200.0)])
    assert prediccion.uso_de(prediccion.eventos(solo_una, "GE074-01")) is None


def test_dos_lecturas_del_mismo_dia_no_son_dos_dias():
    # Despacho y recepcion del mismo dia: dan una sola lectura util.
    mismo = _indice([_acta("A1", "2026-01-10", 1200.0),
                     _acta("A2", "2026-01-10", 1208.0)])
    assert prediccion.uso_de(prediccion.eventos(mismo, "GE074-01")) is None


def test_el_proximo_servicio_se_dice_en_dias_y_en_fecha():
    # "Faltan 118 horas" no se puede poner en un calendario.
    uso = prediccion.uso_de(prediccion.eventos(_indice(CON_HISTORIA), "GE074-01"))
    servicio = prediccion.servicio_de(uso, HOY)
    assert servicio.proximo_intervalo_horas % 250 == 0
    assert servicio.horas_faltantes > 0
    assert servicio.fecha_estimada == (
        HOY + dt.timedelta(days=servicio.dias_estimados)).isoformat()


def test_sin_ritmo_no_se_estima_servicio():
    assert prediccion.servicio_de(None, HOY) is None


# ---------------------------------------------------------- reincidencia

def test_una_causa_que_volvio_tiene_intervalo_y_una_sola_vez_no():
    parte = prediccion.pronostico(_indice(CON_HISTORIA), "GE074-01", HOY)
    porcausa = {r.causa: r for r in parte.reincidencias}

    # El grupo lleva el nombre canónico del catálogo, no el que más se
    # tecleó: es el mismo código para las tres formas de escribirlo, y es
    # comparable entre equipos y entre años.
    filtro = porcausa["Filtro de aire colmatado"]
    assert filtro.casos == 3                    # las tres formas de escribirlo
    assert filtro.intervalo_medio_dias == 66    # (64 + 69) / 2, redondeado
    assert filtro.proxima_estimada == "2026-08-07"

    inyector = porcausa["Inyector con retorno excesivo o goteo"]
    assert inyector.casos == 1
    assert inyector.intervalo_medio_dias is None
    assert inyector.proxima_estimada is None


def test_lo_vencido_se_marca_y_se_pone_primero():
    parte = prediccion.pronostico(_indice(CON_HISTORIA), "GE074-01", HOY)
    assert parte.reincidencias[0].vencida
    assert parte.reincidencias[0].causa == "Filtro de aire colmatado"


def test_los_repuestos_sugeridos_son_los_de_lo_que_reincide():
    parte = prediccion.pronostico(_indice(CON_HISTORIA), "GE074-01", HOY)
    assert parte.repuestos_sugeridos == ["Filtro P533781"]
    assert "Inyector 0445110" not in parte.repuestos_sugeridos


def test_mtbf_necesita_dos_fallas():
    assert prediccion.mtbf(prediccion.eventos(_indice(CON_HISTORIA), "GE074-01")) == 44
    una = _indice([_ot("OT-1", "2026-01-20", "Filtro de aire colmatado")])
    assert prediccion.mtbf(prediccion.eventos(una, "GE074-01")) is None


# ----------------------------------------------------------- honestidad

def test_de_un_equipo_sin_nada_no_se_inventa_un_pronostico():
    parte = prediccion.pronostico(_indice(CON_HISTORIA), "EX999-99", HOY)
    assert parte.eventos == 0
    assert parte.uso is None and parte.servicio is None
    assert any("No hay nada fechado" in a for a in parte.avisos)


def test_con_pocos_registros_se_avisa_de_que_la_señal_es_debil():
    flaco = _indice([_ot("OT-1", "2026-01-20", "Filtro de aire colmatado")])
    parte = prediccion.pronostico(flaco, "GE074-01", HOY)
    assert any("señal debil" in a for a in parte.avisos)
    assert any("se repitio" in a for a in parte.avisos)


def test_una_fecha_ilegible_no_tumba_el_pronostico():
    con_basura = _indice(CON_HISTORIA + [
        _ot("OT-X", "no es una fecha", "Filtro de aire colmatado")])
    parte = prediccion.pronostico(con_basura, "GE074-01", HOY)
    assert parte.eventos == 7      # la que no se pudo fechar queda fuera


def test_acepta_las_fechas_como_las_escribe_una_hoja_de_calculo():
    assert prediccion._fecha("14/03/2026") == dt.date(2026, 3, 14)
    assert prediccion._fecha("2026-03-14") == dt.date(2026, 3, 14)
    assert prediccion._fecha(dt.datetime(2026, 3, 14, 8, 30)) == dt.date(2026, 3, 14)
    assert prediccion._fecha("") is None


# ---------------------------------------------------------------- flota

def test_la_flota_ordena_por_lo_que_mas_trabajo_da():
    varios = _indice(CON_HISTORIA + [
        _ot("OT-9", "2026-05-05", "Manguera rozada", equipo="EX336-01")])
    resumen = prediccion.flota(varios, HOY)
    assert resumen["equipos"][0]["equipo"] == "GE074-01"
    assert resumen["causas"][0]["causa"] == "Filtro de aire colmatado"


def test_una_flota_vacia_lo_dice_en_vez_de_devolver_ceros():
    resumen = prediccion.flota(Indice(), HOY)
    assert resumen["equipos"] == [] and resumen["avisos"]


# ------------------------------- lo que no es una falla, y el dato torcido

def _consumible(n, fecha, descripcion, equipo="GE074-01"):
    return Fragmento(id=f"acta:{n}:c1", tipo="acta", fuente="acta.xlsx",
                     texto=f"CONSUMIBLE {descripcion}",
                     metadatos={"codigo_equipo": equipo, "fecha": fecha,
                                "item": descripcion, "estado": "NO_RETORNA",
                                "clase": "consumible", "n_acta": n})


def _componente(n, fecha, descripcion, equipo="GE074-01"):
    return Fragmento(id=f"acta:{n}:1", tipo="acta", fuente="acta.xlsx",
                     texto=f"COMPONENTE {descripcion}",
                     metadatos={"codigo_equipo": equipo, "fecha": fecha,
                                "item": descripcion, "estado": "D",
                                "clase": "componente", "n_acta": n})


def test_un_extintor_que_no_retorno_no_es_una_falla_del_equipo():
    # Es una recuperacion que se factura. Contarla como averia hincha el
    # MTBF y llena de extintores la lista de lo que le vuelve a pasar.
    indice = _indice(CON_HISTORIA + [
        _consumible("A9", "2026-08-26", "EXTINTOR DE 6 KG"),
        _consumible("A9b", "2026-08-26", "BARRA PUESTA A TIERRA")])
    parte = prediccion.pronostico(indice, "GE074-01", HOY)

    causas = [r.causa for r in parte.reincidencias]
    assert not any("EXTINTOR" in c for c in causas)
    assert not any("BARRA" in c for c in causas)


def test_un_componente_dañado_en_un_acta_si_es_una_falla():
    indice = _indice(CON_HISTORIA + [
        _componente("A9", "2026-08-26", "Barra de puesta a tierra")])
    causas = [r.causa for r in prediccion.pronostico(indice, "GE074-01", HOY).reincidencias]
    assert any("Barra de puesta a tierra" in c for c in causas)


def test_un_horometro_que_retrocede_se_dice_y_no_se_promedia():
    # Alguien anoto 1548 en agosto despues de haber anotado 2050 en julio.
    # Restar la primera de la ultima da un ritmo que no vivio ninguna maquina.
    indice = _indice([
        _acta("A1", "2026-01-10", 1200.0),
        _acta("A2", "2026-03-11", 1750.0),
        _acta("A3", "2026-04-20", 1548.7),      # mal anotada
    ])
    uso = prediccion.uso_de(prediccion.eventos(indice, "GE074-01"))

    assert uso.retrocesos == ["2026-03-11 → 2026-04-20"]
    assert uso.ritmo_horas_dia == 9.17          # (1750 - 1200) / 60 dias
    assert uso.horometro == 1750.0              # la mayor, con su propia fecha
    assert uso.fecha == "2026-03-11"

    parte = prediccion.pronostico(indice, "GE074-01", HOY)
    assert any("no desanda horas" in a for a in parte.avisos)
