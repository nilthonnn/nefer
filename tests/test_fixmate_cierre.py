"""Cerrar el circulo: lo resuelto hoy tiene que responder mañana.

La prueba que importa es la ultima: se registra una falla que el indice no
tenia y, sin reindexar nada, la consulta siguiente la encuentra. Si eso se
rompe, el asistente envejece.
"""

import datetime as dt
import json

import pytest

from nefer.fixmate import cierre
from nefer.fixmate.indice import Indice
from nefer.fixmate.motor import Consulta, Motor

HOY = dt.date(2026, 9, 15)

RESUELTO = {
    "resumen_falla": "El mastil de la torre no sube y la bomba manual hace vacio",
    "causa_raiz": "Nivel de aceite por debajo de la toma, por fuga en el acople",
    "solucion_aplicada": "Se cambio el acople rapido, se relleno y se purgo la bomba",
    "codigo_equipo": "TI09-04",
    "repuestos": ["Acople rapido 1/4\""],
}


def test_un_informe_se_guarda_con_su_orden_y_su_fecha(tmp_path):
    historial = tmp_path / "historial.json"
    guardado = cierre.registrar(RESUELTO, historial, hoy=HOY)

    assert guardado["codigo_ot"] == "OT-2026-0001"
    assert guardado["fecha"] == "2026-09-15"
    datos = json.loads(historial.read_text(encoding="utf-8"))
    assert datos["informes"][0]["causa_raiz"].startswith("Nivel de aceite")


def test_la_orden_sigue_el_correlativo_del_año(tmp_path):
    historial = tmp_path / "historial.json"
    historial.write_text(json.dumps({"informes": [
        {"codigo_ot": "OT-2026-0007", "resumen_falla": "x"},
        {"codigo_ot": "OT-2025-0099", "resumen_falla": "y"}]}), encoding="utf-8")
    assert cierre.registrar(RESUELTO, historial, hoy=HOY)["codigo_ot"] == "OT-2026-0008"


def test_no_se_repite_una_orden_ya_registrada(tmp_path):
    historial = tmp_path / "historial.json"
    cierre.registrar(dict(RESUELTO, codigo_ot="OT-2026-0500"), historial, hoy=HOY)
    with pytest.raises(cierre.ErrorCierre, match="ya esta"):
        cierre.registrar(dict(RESUELTO, codigo_ot="OT-2026-0500"), historial, hoy=HOY)


def test_una_queja_no_es_un_antecedente(tmp_path):
    historial = tmp_path / "historial.json"
    with pytest.raises(cierre.ErrorCierre, match="causa ni solucion"):
        cierre.registrar({"resumen_falla": "la maquina anda mal"}, historial)
    assert not historial.exists(), "no se escribe nada si el informe no vale"


def test_sin_la_falla_como_se_describio_nadie_lo_va_a_encontrar(tmp_path):
    with pytest.raises(cierre.ErrorCierre, match="resumen_falla"):
        cierre.registrar({"causa_raiz": "Acople con fuga",
                          "solucion_aplicada": "Se cambio"}, tmp_path / "h.json")


def test_un_historial_que_no_es_historial_no_se_pisa(tmp_path):
    ruta = tmp_path / "otracosa.json"
    ruta.write_text('{"clientes": []}', encoding="utf-8")
    with pytest.raises(cierre.ErrorCierre, match="informes"):
        cierre.registrar(RESUELTO, ruta)
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"clientes": []}


def test_lo_registrado_responde_en_la_consulta_siguiente(tmp_path):
    indice = Indice()
    consulta = Consulta("el mastil de la torre no levanta")

    # Antes: el indice esta vacio y el motor lo dice en vez de inventar.
    with pytest.raises(Exception):
        Motor(indice).consultar(consulta)

    cierre.registrar(RESUELTO, tmp_path / "historial.json", indice, hoy=HOY)

    diagnostico = Motor(indice).consultar(consulta)
    assert "Nivel de aceite" in diagnostico.causa_raiz_mas_probable
    assert diagnostico.evidencia_historica[0].codigo_ot == "OT-2026-0001"


def test_el_indice_anota_el_historial_como_fuente_suya(tmp_path):
    # Si no, la siguiente reindexacion lo leeria entero otra vez.
    historial = tmp_path / "historial.json"
    indice = Indice()
    cierre.registrar(RESUELTO, historial, indice, hoy=HOY)
    assert str(historial) in indice.fuentes
    from nefer.fixmate.indice import firma_de
    assert indice.sin_cambios(str(historial), firma_de(historial))


def test_el_informe_se_puede_armar_desde_lo_ya_consultado():
    consulta = Consulta("humo negro y pierde fuerza", codigo_dtc="p0300",
                        codigo_equipo="GE074-01")

    class Falso:
        causa_raiz_mas_probable = "Filtro de aire colmatado"

    informe = cierre.desde_diagnostico(consulta, Falso(),
                                       solucion="Se cambio el filtro primario")
    assert informe["resumen_falla"] == "humo negro y pierde fuerza"
    assert informe["causa_raiz"] == "Filtro de aire colmatado"
    assert informe["codigos_dtc"] == ["P0300"]
    assert informe["codigo_equipo"] == "GE074-01"


def test_la_causa_se_puede_corregir_al_cerrar():
    # El tecnico desarmo y era otra cosa: lo que se registra es lo que
    # encontro, no lo que el motor supuso.
    consulta = Consulta("humo negro")

    class Falso:
        causa_raiz_mas_probable = "Filtro de aire colmatado"

    informe = cierre.desde_diagnostico(consulta, Falso(), solucion="Se cambio el turbo",
                                       causa="Turbo con juego axial")
    assert informe["causa_raiz"] == "Turbo con juego axial"
