"""La geometria debe coincidir con las actas reales llenadas a mano."""

from nefer import layout


def test_primer_bloque_fotografico():
    assert layout.bloque_foto(0) == {
        "fila_imagen_inicio": 11, "fila_imagen_fin": 24, "fila_rotulo": 25,
    }


def test_bloques_fotograficos_cada_quince_filas():
    for i in range(6):
        assert layout.bloque_foto(i)["fila_imagen_inicio"] == 11 + 15 * i


def test_observaciones_tras_cinco_bloques():
    # Acta de referencia: cinco filas de fotos y OBSERVACION en la fila 86.
    assert layout.fila_titulo_observaciones(5) == 86


def test_bloques_de_consumible_de_diecisiete_filas():
    # Acta de referencia: primer bloque en 87, segundo en 104.
    primero = layout.bloque_consumible(0, 5)
    assert primero == {
        "fila_encabezado": 87, "fila_imagen_inicio": 88, "fila_imagen_fin": 101,
        "fila_rotulo": 102, "fila_recuperacion": 103,
    }
    assert layout.bloque_consumible(1, 5)["fila_encabezado"] == 104


def test_paneles_de_ancho_comparable():
    izq = layout.ancho_panel_px(layout.PANEL_IZQ)
    der = layout.ancho_panel_px(layout.PANEL_DER)
    assert abs(izq - der) < 60, "los dos paneles deben verse simetricos al imprimir"
