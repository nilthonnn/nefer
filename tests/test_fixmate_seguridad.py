"""La puerta que va entre el diagnóstico y las manos del técnico.

Un diagnóstico que termina en «desmontar el inyector 3» le está diciendo a
alguien que meta las manos en una máquina. Lo que se comprueba aquí es que
entre esa frase y el técnico haya algo, que ese algo diga de dónde sale, y
que no se pueda quitar sin que una prueba se ponga roja.
"""

from __future__ import annotations

import pytest

from nefer.fixmate import seguridad as s
from nefer.fixmate.indice import Coincidencia, Fragmento


def _textos(precauciones):
    return [p.texto for p in precauciones]


# ------------------------------------------------- la regla que va siempre

def test_si_hay_pasos_hay_precaucion_aunque_no_se_reconozca_el_sistema():
    """«No está escrito» no es «no aplica»."""
    ps = s.precauciones(["Revisar el tablero y anotar la lectura"])
    assert ps, "unos pasos sin ninguna precaución es la peor salida posible"
    assert "Bloquee" in ps[0].texto
    assert ps[0].origen == s.DE_LA_HERRAMIENTA


def test_sin_pasos_no_hay_precauciones():
    # No hay procedimiento que ejecutar: una advertencia suelta es ruido, y
    # el ruido es lo que hace que la siguiente no se lea.
    assert s.precauciones([]) == []
    assert s.precauciones(None) == []


# ------------------------------------- cada energía que el trabajo va a tocar

@pytest.mark.parametrize("pasos, causa, sistema, pista", [
    (["Cambiar el kit de sellos del cilindro del brazo"],
     "Sello del vástago vencido", "hidraulico", "presion hidraulica"),
    (["Limpieza de bornes y ajuste a 8 N·m"],
     "Bornes de batería sulfatados", "electrico", "borne negativo"),
    (["Desmontar el inyector 3 y medir el retorno"],
     "Inyector con retorno excesivo", "combustible", "riel de inyeccion"),
    (["Reemplazar el termostato"],
     "Termostato trabado abierto", "termico", "Deje enfriar"),
    (["Desmontar el aro y la llanta trasera"],
     "Llanta con pérdida", "neumatico", "aire comprimido"),
])
def test_la_energia_que_el_procedimiento_nombra_sale_advertida(pasos, causa,
                                                               sistema, pista):
    ps = s.precauciones(pasos, causa=causa)
    sistemas = [p.sistema for p in ps if p.sistema]
    assert sistema in sistemas, f"no advirtió de lo {sistema}: {sistemas}"
    assert any(pista in p.texto for p in ps)


def test_un_trabajo_que_toca_dos_energias_las_advierte_las_dos():
    ps = s.precauciones(["Bajar la pluma al suelo",
                         "Desconectar el arnés del sensor de presión"],
                        causa="Sensor de presión hidráulica en falla")
    sistemas = {p.sistema for p in ps if p.sistema}
    assert {"hidraulico", "electrico"} <= sistemas


def test_la_de_bloqueo_va_primera_y_no_se_repite():
    ps = s.precauciones(["Bajar el cilindro", "Soltar el borne"],
                        causa="Fuga hidráulica")
    assert "Bloquee" in ps[0].texto
    assert len([p for p in ps if "Bloquee" in p.texto]) == 1


# ------------------------------------------ lo que dice el manual, citado

def _manual(texto, seccion="Sistema hidráulico"):
    return Coincidencia(
        Fragmento(id="man:x:1", texto=texto, fuente="manual.pdf", tipo="manual",
                  metadatos={"seccion": seccion}),
        0.5, 0.5, 0.5)


def test_la_advertencia_del_manual_se_copia_literal_y_se_cita():
    manual = _manual("Sistema hidráulico\n"
                     "PELIGRO: el acumulador conserva presión durante 20 "
                     "minutos después de parar el motor.\n"
                     "El caudal nominal es de 180 l/min.")
    ps = s.precauciones(["Cambiar la manguera"], [manual], "Manguera picada")

    delm = [p for p in ps if p.origen == s.DEL_MANUAL]
    assert len(delm) == 1
    # Literal: ni resumida ni reescrita, igual que un par de apriete.
    assert delm[0].texto == ("PELIGRO: el acumulador conserva presión durante "
                             "20 minutos después de parar el motor.")
    assert delm[0].referencia == "Sistema hidráulico"
    # Y lo que no es advertencia no se cuela como si lo fuera.
    assert all("180 l/min" not in p.texto for p in ps)


def test_una_observacion_de_una_orden_no_es_una_regla_de_seguridad():
    """Lo que le pasó a una máquina no es una norma. Se cita como evidencia,
    no como precaución."""
    informe = Coincidencia(
        Fragmento(id="ot:OT-9", texto="CUIDADO que esta máquina viene con el "
                                      "freno flojo desde la faena anterior.",
                  fuente="historial.xlsx", tipo="informe",
                  metadatos={"codigo_ot": "OT-9"}),
        0.9, 0.9, 0.9)
    ps = s.precauciones(["Revisar el freno"], [informe], "Freno desajustado")
    assert all(p.origen == s.DE_LA_HERRAMIENTA for p in ps)


def test_toda_precaucion_dice_de_donde_sale():
    manual = _manual("ADVERTENCIA: no afloje la cañería con el motor caliente.")
    ps = s.precauciones(["Desmontar el inyector"], [manual], "Inyector")
    assert ps
    for p in ps:
        assert p.origen in (s.DE_LA_HERRAMIENTA, s.DEL_MANUAL)
        assert p.a_dict()["origen"] == p.origen
        if p.origen == s.DEL_MANUAL:
            assert p.a_dict()["referencia"]


# --------------------------------------------- y el motor no la puede saltar

def test_el_motor_pone_la_puerta_aunque_el_redactor_no_la_ponga():
    """La puerta está en el motor, no en el redactor: un redactor enchufado
    que devuelva pasos sin precauciones no puede dejar al técnico sin ellas."""
    from nefer.fixmate import Indice, Motor
    from nefer.fixmate.ingesta import de_informe
    from nefer.fixmate.motor import Consulta

    indice = Indice()
    indice.agregar([de_informe(
        {"codigo_ot": "OT-1",
         "resumen_falla": "gotea aceite por el cilindro del brazo",
         "causa_raiz": "Sello del vástago vencido",
         "solucion_aplicada": "Cambio de sellos",
         "pasos": ["Cambiar el kit de sellos del cilindro"]}, "h.json")])

    def redactor_descuidado(consulta, coincidencias, causas_probables=None,
                            medicion=None):
        return {"diagnostico_probabilistico": "x",
                "causa_raiz_mas_probable": "Sello del vástago vencido",
                "pasos_recomendados": ["Cambiar el kit de sellos del cilindro"],
                "herramientas_y_repuestos": [], "torques": []}

    d = Motor(indice, redactor=redactor_descuidado).consultar(
        Consulta("gotea aceite del brazo"))

    assert d.pasos_recomendados
    assert d.precauciones, "el redactor no las puso y el motor tampoco: nadie"
    assert any("hidraulica" in p["texto"] for p in d.precauciones)


def test_las_precauciones_viajan_en_el_json():
    from nefer.fixmate import Indice, Motor
    from nefer.fixmate.ingesta import de_informe
    from nefer.fixmate.motor import Consulta

    indice = Indice()
    indice.agregar([de_informe(
        {"codigo_ot": "OT-1", "resumen_falla": "no arranca, gira lento",
         "causa_raiz": "Bornes sulfatados", "solucion_aplicada": "Limpieza",
         "pasos": ["Limpiar los bornes de la batería"]}, "h.json")])
    d = Motor(indice).consultar(Consulta("no arranca gira lento"))
    crudo = d.a_dict()
    assert crudo["precauciones"]
    assert set(crudo["precauciones"][0]) >= {"texto", "origen"}
