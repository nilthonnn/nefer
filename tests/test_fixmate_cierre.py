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


# ------------------------------- lo que llega del campo, en un solo archivo

ENVIO = {
    "generado": "2026-09-16T11:20:00Z",
    "pendientes": [
        {"codigo_ot": "OT-CAMPO-20260916-1",
         "resumen_falla": "El ventilador no gira y el motor se calienta",
         "causa_raiz": "Correa del ventilador partida",
         "solucion_aplicada": "Se cambió la correa",
         "codigo_equipo": "GE074-03"},
        {"codigo_ot": "OT-CAMPO-20260916-2",
         "resumen_falla": "Fuga por el acople del mástil",
         "causa_raiz": "Acople rajado",
         "solucion_aplicada": "Se reemplazó el acople",
         "codigo_equipo": "TI09-04"},
    ],
}


def _envio(tmp_path, datos=None):
    ruta = tmp_path / "informes-de-campo.json"
    ruta.write_text(json.dumps(datos or ENVIO, ensure_ascii=False), encoding="utf-8")
    return ruta


def test_lo_cerrado_en_faena_entra_al_historial(tmp_path):
    historial = tmp_path / "historial.json"
    parte = cierre.recibir(_envio(tmp_path), historial, hoy=HOY)

    assert len(parte.nuevos) == 2 and not parte.rechazados
    guardados = json.loads(historial.read_text(encoding="utf-8"))["informes"]
    assert [i["codigo_ot"] for i in guardados] == ["OT-CAMPO-20260916-1",
                                                   "OT-CAMPO-20260916-2"]


def test_reenviar_el_mismo_archivo_no_duplica_nada(tmp_path):
    # Va a pasar: el técnico manda el archivo, no sabe si llegó, lo manda otra
    # vez. Tratarlo como error obligaría a alguien a elegir cuál valía.
    historial = tmp_path / "historial.json"
    envio = _envio(tmp_path)
    cierre.recibir(envio, historial, hoy=HOY)
    segunda = cierre.recibir(envio, historial, hoy=HOY)

    assert not segunda.nuevos
    assert segunda.repetidos == ["OT-CAMPO-20260916-1", "OT-CAMPO-20260916-2"]
    assert len(json.loads(historial.read_text(encoding="utf-8"))["informes"]) == 2


def test_un_informe_incompleto_se_rechaza_y_los_demas_entran(tmp_path):
    # Un envío con una fila mala no puede perder las buenas: el técnico no
    # tiene cómo rehacerlo desde el patio.
    datos = {"pendientes": [ENVIO["pendientes"][0],
                            {"resumen_falla": "algo raro"},
                            ENVIO["pendientes"][1]]}
    parte = cierre.recibir(_envio(tmp_path, datos), tmp_path / "h.json", hoy=HOY)

    assert len(parte.nuevos) == 2
    assert len(parte.rechazados) == 1
    assert "causa" in parte.rechazados[0][1]
    assert "2 nuevos" in parte.resumen()


def test_lo_recibido_queda_buscable_si_se_pasa_el_indice(tmp_path):
    indice = Indice()
    cierre.recibir(_envio(tmp_path), tmp_path / "h.json", indice, hoy=HOY)

    diagnostico = Motor(indice).consultar(
        Consulta("el ventilador no gira y el motor se calienta"))
    assert "Correa" in diagnostico.causa_raiz_mas_probable


def test_un_envio_que_no_es_un_envio_lo_dice(tmp_path):
    with pytest.raises(cierre.ErrorCierre, match="lista de informes"):
        cierre.recibir({"cualquier": "cosa"}, tmp_path / "h.json")
    with pytest.raises(cierre.ErrorCierre, match="no existe"):
        cierre.recibir(tmp_path / "fantasma.json", tmp_path / "h.json")


def test_tambien_acepta_una_lista_pelada(tmp_path):
    parte = cierre.recibir(ENVIO["pendientes"], tmp_path / "h.json", hoy=HOY)
    assert len(parte.nuevos) == 2


def test_reenviar_sin_numero_de_orden_tampoco_duplica(tmp_path):
    """El teléfono siempre pone OT, pero un envío a mano puede no traerla.

    Sin código, cada reenvío le inventaba un correlativo nuevo y lo metía
    otra vez: el mismo trabajo contado tres veces en el historial de la
    flota, que es de donde salen los promedios.
    """
    sin_ot = {"pendientes": [
        {"resumen_falla": "El mástil no sube", "causa_raiz": "Acople con fuga",
         "solucion_aplicada": "Se cambió el acople", "codigo_equipo": "TI09-04"}]}
    historial = tmp_path / "historial.json"
    envio = _envio(tmp_path, sin_ot)

    assert len(cierre.recibir(envio, historial, hoy=HOY).nuevos) == 1
    segunda = cierre.recibir(envio, historial, hoy=HOY)
    assert not segunda.nuevos and segunda.repetidos
    assert len(json.loads(historial.read_text(encoding="utf-8"))["informes"]) == 1


def test_dos_trabajos_parecidos_pero_distintos_si_entran_los_dos(tmp_path):
    # La firma mira falla, causa, solución, equipo y fecha: dos equipos con
    # la misma avería el mismo día son dos informes, no uno repetido.
    base = {"resumen_falla": "El mástil no sube", "causa_raiz": "Acople con fuga",
            "solucion_aplicada": "Se cambió el acople"}
    historial = tmp_path / "historial.json"
    parte = cierre.recibir([dict(base, codigo_equipo="TI09-04"),
                            dict(base, codigo_equipo="TI09-02")],
                           historial, hoy=HOY)
    assert len(parte.nuevos) == 2
