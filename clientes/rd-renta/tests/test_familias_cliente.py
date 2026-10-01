"""Las dos familias que RD RENTAL trajo con sus propias actas.

El rodillo vibrante y la motoniveladora caian en «maquinaria amarilla», cuya
rejilla no se parece a la suya: la del rodillo no tiene cucharon ni tren de
rodaje y si timon, rola y palanca de control; la de la motoniveladora
fotografia los seis neumaticos por eje y por lado y mide las piezas de
desgaste.

Los rotulos de aqui son los de las actas del cliente, copiados tal cual. Si
alguien los «arregla» de memoria, el acta que sale deja de poder compararse
con la plantilla del cliente, y esta prueba lo dice.

  · rodillo        RL19-04-01-010  (RODILLO VIBRANTE LISO DE 19000 KG)
  · motoniveladora MN15T-14-01-12  (MOTONIVELADORA)
"""

from __future__ import annotations

import pytest

from rdrenta import extract, layout, textos

# Transcripcion literal de la rejilla de cada acta, por franjas: cada par es
# una fila del formato, panel izquierdo y panel derecho.
RODILLO = [
    ("VISTA FRONTAL", "VISTA POSTERIOR"),
    ("VISTA IZQUIERDA", "VISTA DERECHA"),
    ("HORÓMETRO", "TIMÓN"),
    ("PALANCA DE CONTROL", "VISTO LATERAL DE LA ROLA"),
    ("VISTA IZQUIERDA DE MOTOR", "VISTA DERECHA DE MOTOR"),
    ("NEUMÁTICO IZQUIERDO", "NEUMÁTICO DERECHO"),
    ("LLAVE DE CONTACTO", "PICO Y LAMPA"),
    ("TACOS DE MADERA", "ACCESORIOS"),
]

MOTONIVELADORA = [
    ("VISTA FRONTAL", "VISTA POSTERIOR"),
    ("VISTA IZQUIERDA", "VISTA DERECHA"),
    ("HORÓMETRO", "PALA Y PICO + LLAVE DE CONTACTO"),
    ("ASIENTO DE OPERADOR", "MANDOS DE CONTROL"),
    ("NEUMÁTICO DELANTERO DERECHO", "NEUMÁTICO DELANTERO IZQUIERDO"),
    ("NEUMÁTICO POSTERIOR Y CENTRO DERECHO", "NEUMÁTICO POSTERIOR Y CENTRO IZQUIERDA"),
    ("VISTA SUPERIOR DE MOTOR", "VISTA FRONTAL DE MOTOR"),
    ("CUCHILLAS CON SUS MEDICIONES", "DESGARRADORES CON SUS MEDICIONES"),
    ("BATERÍAS", "MANDO Y BOTONES DE CONTROL"),
    ("TACOS", "ACCESORIOS"),
]


@pytest.mark.parametrize("familia,franjas", [
    ("rodillo", RODILLO),
    ("motoniveladora", MOTONIVELADORA),
])
def test_la_rejilla_es_la_del_acta_del_cliente(familia, franjas):
    esperadas = [rotulo for pareja in franjas for rotulo in pareja]
    assert layout.VISTAS_POR_CATEGORIA[familia] == esperadas


@pytest.mark.parametrize("familia,franjas", [
    ("rodillo", RODILLO),
    ("motoniveladora", MOTONIVELADORA),
])
def test_cada_franja_lleva_sus_dos_paneles(familia, franjas):
    """Una vista impar dejaria media fila vacia y el formato descuadrado."""
    vistas = layout.VISTAS_POR_CATEGORIA[familia]
    assert len(vistas) % 2 == 0, f"{familia} tiene {len(vistas)} vistas"
    assert len(vistas) // 2 == len(franjas)


@pytest.mark.parametrize("nombre,familia", [
    ("RODILLO VIBRANTE LISO DE 19000 KG", "rodillo"),
    ("RODILLO LISO", "rodillo"),
    ("COMPACTADOR VIBRATORIO", "rodillo"),
    ("MOTONIVELADORA", "motoniveladora"),
    ("MOTONIVELADORA 140K", "motoniveladora"),
    # Las de siempre no se mueven: el cajon de sastre sigue donde estaba.
    ("EXCAVADORA SOBRE ORUGAS", "maquinaria_amarilla"),
    ("MINICARGADOR", "maquinaria_amarilla"),
])
def test_el_nombre_del_equipo_elige_la_rejilla(nombre, familia):
    assert extract._categoria(nombre) == familia


@pytest.mark.parametrize("familia", ["rodillo", "motoniveladora"])
def test_las_dos_llevan_hoja_de_consumibles(familia):
    """Son equipos autopropulsados: se despachan con combustible dentro."""
    assert familia in layout.CATEGORIAS_MOVILES
    control = textos.control_consumibles_vacio(familia)
    assert control, f"{familia} se queda sin tabla de consumibles"
    assert control is not textos.control_consumibles_vacio(familia), \
        "la tabla tiene que salir nueva cada vez, no compartida"


def test_el_rodillo_controla_el_agua_de_riego():
    """Vuelve con el tanque seco y la rola rayada, y nadie lo anotó.

    Es el consumible que el formato generico no tiene y que en un rodillo se
    discute: por eso esta familia existe aparte.
    """
    nombres = [c["consumible"] for c in textos.control_consumibles_vacio("rodillo")]
    assert "Agua del sistema de riego" in nombres
    assert "Rascadores de rola" in nombres


def test_la_motoniveladora_mide_las_piezas_de_desgaste():
    """La plantilla del cliente pide la foto «CON SUS MEDICIONES».

    La foto respalda un número, y el número es lo que se cobra al liquidar: si
    la tabla no lo pide, la foto se queda sin la cifra que la justifica.
    """
    control = {c["consumible"]: c["unidad"]
               for c in textos.control_consumibles_vacio("motoniveladora")}
    assert control.get("Cuchillas: alto remanente") == "mm"
    assert control.get("Desgarradores: puntas completas") == "und"

    vistas = layout.VISTAS_POR_CATEGORIA["motoniveladora"]
    assert "CUCHILLAS CON SUS MEDICIONES" in vistas
    assert "DESGARRADORES CON SUS MEDICIONES" in vistas


# ---------- la misma vista con otro nombre ----------

@pytest.mark.parametrize("archivo,familia,rotulo", [
    # El acta del rodillo dice «VISTA IZQUIERDA»; la pista del nombre de
    # archivo devuelve el rótulo largo, que en esta familia no existe.
    ("lateral-izquierda.jpg", "rodillo", "VISTA IZQUIERDA"),
    ("derecha.jpg", "rodillo", "VISTA DERECHA"),
    ("lateral-izquierda.jpg", "grupo_electrogeno", "VISTA LATERAL IZQUIERDA"),
    ("tacos.jpg", "rodillo", "TACOS DE MADERA"),
])
def test_una_foto_cae_en_su_hueco_aunque_la_familia_lo_llame_de_otro_modo(
        archivo, familia, rotulo):
    sugerida = layout.vista_sugerida(archivo)
    assert sugerida is not None, f"{archivo} no sugiere ninguna vista"

    vistas = layout.VISTAS_POR_CATEGORIA[familia]
    hueco = next((v for v in layout.equivalentes(sugerida) if v in vistas), None)
    assert hueco == rotulo


@pytest.mark.parametrize("archivo,rotulo", [
    ("timon.jpg", "TIMÓN"),
    ("rola.jpg", "VISTO LATERAL DE LA ROLA"),
    ("cuchillas.jpg", "CUCHILLAS CON SUS MEDICIONES"),
    ("desgarradores.jpg", "DESGARRADORES CON SUS MEDICIONES"),
    ("asiento.jpg", "ASIENTO DE OPERADOR"),
])
def test_las_vistas_nuevas_se_reconocen_por_el_nombre_del_archivo(archivo, rotulo):
    assert layout.vista_sugerida(archivo) == rotulo
