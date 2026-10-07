"""El activo: la entidad que `codigo_equipo` siempre estuvo señalando.

Lo que importa probar aquí es la **compatibilidad**: declarar un activo no
migra nada, no reescribe ningún informe y no inventa fichas. Un historial
viejo sigue funcionando igual, y los activos que de él se deducen quedan con
todo lo no declarado en blanco — nunca con un valor supuesto.
"""

from __future__ import annotations

import pytest

from nefer.fixmate import embeddings, ingesta
from nefer.fixmate.activos import (SISTEMAS, Activo, ErrorActivo, Flota,
                                   Ubicacion, desde_indice)
from nefer.fixmate.indice import Indice


def test_el_activo_necesita_codigo_porque_es_lo_que_esta_pintado_en_la_maquina():
    with pytest.raises(ErrorActivo, match="codigo"):
        Activo("", "Excavadora")


def test_el_activo_necesita_nombre():
    with pytest.raises(ErrorActivo, match="nombre"):
        Activo("EX-220", "   ")


def test_la_criticidad_vacia_se_lee_como_no_evaluada():
    assert Activo("EX-220", "Excavadora").a_dict()["criticidad"] == "no evaluada"


def test_la_descripcion_arma_lo_que_se_ve_en_pantalla():
    a = Activo("EX-220", "Excavadora hidráulica", "Komatsu", "PC220-8")
    assert a.descripcion() == "EX-220 · Excavadora hidráulica · Komatsu PC220-8"
    sin_marca = Activo("VT-055", "Ventilador")
    assert sin_marca.descripcion() == "VT-055 · Ventilador"


def test_dos_activos_con_el_mismo_codigo_partirian_el_historial_en_dos():
    f = Flota()
    f.agregar(Activo("EX-220", "Excavadora"))
    with pytest.raises(ErrorActivo, match="ya esta declarado"):
        f.agregar(Activo("EX-220", "Otra excavadora"))


def test_la_flota_se_consulta_por_codigo():
    f = Flota()
    f.agregar(Activo("EX-220", "Excavadora"))
    assert "EX-220" in f and len(f) == 1
    assert f.get("EX-220").nombre == "Excavadora"
    assert f.get("NO-EXISTE") is None
    assert [a.codigo for a in f] == ["EX-220"]


def test_el_vocabulario_de_sistemas_no_es_una_lista_nueva():
    # Un sistema que estuviera aquí y no en el catálogo sería un sistema sobre
    # el que jamás se podría codificar una causa.
    from nefer.fixmate.catalogo import DE_FABRICA
    assert set(SISTEMAS) == {e.sistema for e in DE_FABRICA}
    assert "termico" in SISTEMAS


def test_la_ubicacion_se_lee_de_sistema_a_componente():
    assert str(Ubicacion("termico", "refrigeracion", "radiador")) == \
        "termico / refrigeracion / radiador"
    assert str(Ubicacion("termico")) == "termico"
    assert str(Ubicacion()) == ""


# ------------------------------------------- compatibilidad hacia atrás

def _indice_con_historial() -> Indice:
    informes = [
        {"codigo_ot": "OT-1", "fecha": "2025-03-01", "codigo_equipo": "EX-220",
         "modelo_equipo": "PC220-8", "categoria": "excavadora",
         "resumen_falla": "Se recalienta en pendiente",
         "causa_raiz": "Radiador obstruido por tierra",
         "solucion_aplicada": "Lavado del panal"},
        {"codigo_ot": "OT-2", "fecha": "2025-04-02", "codigo_equipo": "EX-220",
         "resumen_falla": "Humo negro", "causa_raiz": "Filtro de aire colmatado",
         "solucion_aplicada": "Cambio de filtro"},
        {"codigo_ot": "OT-3", "fecha": "2025-04-10", "codigo_equipo": "CA-310",
         "resumen_falla": "No arranca", "causa_raiz": "Bornes sulfatados",
         "solucion_aplicada": "Limpieza de bornes"},
    ]
    indice = Indice(embeddings.EmbebedorLocal())
    indice.agregar(ingesta.de_historial({"informes": informes}, "historial.json"))
    return indice


def test_los_activos_se_deducen_del_historial_que_ya_existe():
    # Es lo que permite arrancar un piloto sin cargar la flota primero.
    flota = desde_indice(_indice_con_historial())
    assert set(flota.activos) == {"EX-220", "CA-310"}


def test_lo_que_el_historial_no_dice_queda_vacio_y_no_supuesto():
    flota = desde_indice(_indice_con_historial())
    ex = flota.get("EX-220")
    assert ex.modelo == "PC220-8"          # esto sí estaba
    assert ex.categoria == "excavadora"
    assert ex.marca == ""                  # esto no: queda vacío
    assert ex.contexto == ""
    assert ex.criticidad == ""
    # Y el que ni modelo traía usa su propio código como nombre, sin inventar.
    assert flota.get("CA-310").nombre == "CA-310"
    assert flota.get("CA-310").modelo == ""


def test_deducir_la_flota_no_toca_el_indice():
    indice = _indice_con_historial()
    antes = len(indice.fragmentos)
    desde_indice(indice)
    assert len(indice.fragmentos) == antes


def test_el_codigo_del_activo_es_el_mismo_codigo_equipo_de_los_informes():
    # Esta es toda la historia de compatibilidad: no hay migración porque la
    # llave ya estaba ahí.
    indice = _indice_con_historial()
    flota = desde_indice(indice)
    codigos_en_informes = {f.metadatos.get("codigo_equipo")
                           for f in indice.fragmentos
                           if f.metadatos.get("codigo_equipo")}
    assert set(flota.activos) == codigos_en_informes


def test_de_dict_acepta_tanto_codigo_como_codigo_equipo():
    # Para poder reconstruir un activo desde los metadatos de un informe.
    assert Activo.de_dict({"codigo_equipo": "EX-220", "nombre": "x"}).codigo == "EX-220"
    assert Activo.de_dict({"codigo": "EX-220", "nombre": "x"}).codigo == "EX-220"
