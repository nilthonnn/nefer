"""El catálogo de causas: de texto libre a un código estable.

Lo que se prueba aquí, por encima de todo, son dos cosas opuestas: que
reconozca la misma causa escrita de cinco formas, y que **se niegue** cuando
el texto no alcanza. La segunda importa más. Un código equivocado se suma
con los demás y ensucia la cuenta de toda la flota; uno que falta se ve.
"""

from __future__ import annotations

import json

import pytest

from nefer.fixmate import catalogo
from nefer.fixmate.catalogo import POR_DEFECTO, Catalogo, Entrada, cargar


# ------------------------------------------------- reconocer lo que ya está

@pytest.mark.parametrize("texto, codigo", [
    # El caso que motivó todo: tres formas, un código.
    ("Filtro de aire colmatado", "ADM.RESTRICCION.FILTRO"),
    ("filtro aire tapado", "ADM.RESTRICCION.FILTRO"),
    ("FILTROS DE AIRE OBSTRUIDOS", "ADM.RESTRICCION.FILTRO"),
    # Plural y femenino: el tokenizador no lematiza, y las pistas son raíces.
    ("Baterías sulfatadas", "ELE.NO_ARRANCA.BORNES"),
    ("bornes flojos y sulfatados", "ELE.NO_ARRANCA.BORNES"),
    ("Sello del vástago vencido", "HID.FUGA.SELLO"),
    ("sellos goteando en el cilindro del brazo", "HID.FUGA.SELLO"),
    ("mangueras picadas rozando el chasis", "HID.FUGA.MANGUERA"),
    ("Inyector con retorno excesivo", "COM.COMBUSTION.INYECTOR"),
    ("inyectores goteando", "COM.COMBUSTION.INYECTOR"),
    ("Termostato trabado abierto", "TER.SOBRECALENTAMIENTO.TERMOSTATO"),
    ("radiadores obstruidos con tierra", "TER.SOBRECALENTAMIENTO.RADIADOR"),
    ("cadena del tren de rodaje fuera de tolerancia", "EST.DESGASTE.TREN_RODAJE"),
    ("dientes del cucharón gastados", "EST.DESGASTE.DIENTES"),
    ("embrague patinando", "TRA.PATINA.EMBRAGUE"),
    ("fisura en la soldadura del chasis", "EST.FISURA.SOLDADURA"),
])
def test_reconoce_la_causa_escrita_como_la_escribe_el_taller(texto, codigo):
    entrada = POR_DEFECTO.clasificar(texto)
    assert entrada is not None, f"no reconoció «{texto}»"
    assert entrada.codigo == codigo


def test_la_misma_causa_escrita_de_tres_formas_da_un_solo_codigo():
    formas = ["Filtro de aire colmatado", "filtro aire tapado",
              "FILTRO DE AIRE OBSTRUIDO", "filtros de admisión saturados"]
    codigos = {POR_DEFECTO.clasificar(f).codigo for f in formas}
    assert len(codigos) == 1, codigos


# ------------------------------------------------------ negarse a adivinar

@pytest.mark.parametrize("texto", [
    "bomba",                    # ¿la hidráulica, la de inyección, la de agua?
    "fuga",                     # ¿de qué?
    "se rompió",
    "falla",
    "trámites de aduana del contenedor en el puerto",
    "corrosión galvánica en el soporte del tanque de urea",
])
def test_lo_que_no_alcanza_se_queda_sin_codigo(texto):
    assert POR_DEFECTO.clasificar(texto) is None


def test_no_existe_el_codigo_otro():
    """Es la recomendación explícita de la norma, y la razón es empírica:
    «Otro» termina siendo el código más usado de toda base mal llevada, y a
    partir de ahí los datos no sirven para nada."""
    codigos = {e.codigo.upper() for e in POR_DEFECTO.entradas}
    assert not any("OTRO" in c or "VARIOS" in c or "GENERAL" in c for c in codigos)
    causas = {e.causa.lower() for e in POR_DEFECTO.entradas}
    assert "otro" not in causas and "otros" not in causas


def test_un_empate_no_se_resuelve_a_la_suerte():
    """Dos entradas igual de defendibles quieren decir que el texto no
    alcanza para decidir."""
    catalogo_falso = Catalogo([
        Entrada("A.B.C", "x", "m", "k", "causa A", ("valvula", "fuga")),
        Entrada("D.E.F", "x", "m", "k", "causa B", ("valvula", "fuga")),
    ])
    assert catalogo_falso.clasificar("válvula con fuga") is None


# ------------------------------- un servicio planificado no es una falla

@pytest.mark.parametrize("texto", [
    "cambio de aceite de motor programado",
    "mantenimiento preventivo de 500 horas",
    "servicio de 250 horas",
    "cambio de filtros según plan",
])
def test_el_mantenimiento_cumplido_no_se_codifica_como_averia(texto):
    """La norma separa lo correctivo de lo preventivo. Mezclarlos infla el
    MTBF y llena de cambios de aceite la lista de lo que le vuelve a pasar
    a la máquina."""
    assert POR_DEFECTO.clasificar(texto) is None


@pytest.mark.parametrize("texto", [
    "intervalo de cambio de aceite atrasado 180 horas",
    "aceite vencido, sobrepasado el intervalo",
])
def test_el_mantenimiento_que_no_se_hizo_si_es_un_hallazgo(texto):
    entrada = POR_DEFECTO.clasificar(texto)
    assert entrada is not None and entrada.codigo == "LUB.VENCIDO.INTERVALO"


# ------------------------------------------- los tres niveles de la norma

def test_cada_entrada_trae_modo_mecanismo_y_causa():
    """Confundir los tres es el error de datos más común del rubro: el modo
    es lo que se observa, el mecanismo el proceso físico y la causa la
    condición raíz."""
    for e in POR_DEFECTO.entradas:
        assert e.modo and e.mecanismo and e.causa, e.codigo
        assert e.sistema
        assert len(e.pistas) >= catalogo.MINIMO_PISTAS, e.codigo


def test_los_codigos_no_se_repiten():
    codigos = [e.codigo for e in POR_DEFECTO.entradas]
    assert len(codigos) == len(set(codigos))


def test_ninguna_pista_es_una_palabra_vacia():
    """Una palabra vacía nunca llega como token: la pista sería peso muerto
    que además engaña al que lee el catálogo."""
    from nefer.fixmate import texto as _texto

    for e in POR_DEFECTO.entradas:
        for pista in e.pistas:
            assert _texto.tokenizar(pista), f"{e.codigo}: «{pista}» no tokeniza"


# ----------------------------------------------------------- la cobertura

def test_la_cobertura_dice_que_falta_y_no_solo_cuanto_acierta():
    """El número que importa no es el de aciertos: es la lista de lo que no
    se pudo codificar, porque eso es lo que hay que agregarle al catálogo."""
    historial = (["Filtro de aire colmatado"] * 4 +
                 ["corrosión galvánica en el tanque de urea"] * 3 +
                 ["se rompió el perno"])
    c = POR_DEFECTO.cobertura(historial)

    assert c["total"] == 8
    assert c["codificadas"] == 4
    assert c["sin_codigo"] == 4
    assert c["cobertura"] == 0.5
    # Lo más repetido primero: es lo que más rinde agregar.
    assert c["faltantes"][0] == "corrosión galvánica en el tanque de urea"


# ------------------------------------------- el taller agrega las suyas

def test_el_taller_puede_agregar_sus_causas(tmp_path):
    """Un catálogo que no se puede ampliar obliga a elegir la entrada
    equivocada, que es volver al problema de «Otro» por otro camino."""
    propio = tmp_path / "catalogo-taller.json"
    propio.write_text(json.dumps([{
        "codigo": "QUI.CORROSION.UREA", "sistema": "postratamiento",
        "modo": "Corrosión", "mecanismo": "Ataque químico",
        "causa": "Corrosión galvánica en el soporte del tanque de urea",
        "pistas": ["urea", "corrosion", "galvanica", "soporte"],
    }]), encoding="utf-8")

    ampliado = cargar(propio)
    assert len(ampliado) == len(POR_DEFECTO) + 1
    entrada = ampliado.clasificar("corrosión galvánica en el tanque de urea")
    assert entrada is not None and entrada.codigo == "QUI.CORROSION.UREA"
    # Y el de fábrica no se toca.
    assert POR_DEFECTO.clasificar("corrosión galvánica en el tanque de urea") is None


def test_una_entrada_a_la_que_le_falta_un_nivel_se_rechaza(tmp_path):
    malo = tmp_path / "malo.json"
    malo.write_text(json.dumps([{"codigo": "X.Y.Z", "sistema": "x",
                                 "causa": "algo", "pistas": ["a", "b"]}]),
                    encoding="utf-8")
    with pytest.raises(ValueError, match="modo"):
        cargar(malo)


def test_una_entrada_con_una_sola_pista_se_rechaza(tmp_path):
    """Con una sola, la entrada se lleva por delante todo lo que la
    mencione: «bomba» capturaría la hidráulica, la de inyección y la de
    agua."""
    malo = tmp_path / "malo.json"
    malo.write_text(json.dumps([{"codigo": "X.Y.Z", "sistema": "x", "modo": "m",
                                 "mecanismo": "k", "causa": "c",
                                 "pistas": ["bomba"]}]), encoding="utf-8")
    with pytest.raises(ValueError, match="pistas"):
        cargar(malo)


# ------------------------------------- lo que cambia aguas abajo: agrupar

def test_agrupar_usa_el_catalogo_y_no_mezcla_lo_que_no_reconoce():
    from nefer.fixmate.aprendizaje import agrupar_causas

    mapa = agrupar_causas([
        "Filtro de aire colmatado", "filtro aire tapado",
        "FILTRO DE AIRE OBSTRUIDO",
        "corrosión galvánica en el tanque de urea",
        "corrosión galvánica del tanque de urea",
    ])
    grupos = set(mapa.values())
    assert len(grupos) == 2
    # Las tres del catálogo llevan el nombre canónico, no el más tecleado.
    assert mapa["filtro aire tapado"] == "Filtro de aire colmatado"
    # Y lo no codificado se agrupa por parecido, aparte.
    assert (mapa["corrosión galvánica en el tanque de urea"] ==
            mapa["corrosión galvánica del tanque de urea"])
    assert mapa["corrosión galvánica en el tanque de urea"] not in {
        e.causa for e in POR_DEFECTO.entradas}
