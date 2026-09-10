from nefer import textos


def test_rotulo_de_despacho():
    cons = {"cantidad": 2, "descripcion": 'CONOS DE 28"'}
    assert textos.texto_consumible(cons, "DESPACHO") == '02 CONOS DE 28" DESPACHADO'


def test_rotulo_de_recepcion_sin_retorno():
    cons = {"cantidad": 2, "descripcion": 'CONOS DE 28"', "estado_recepcion": "NO_RETORNA"}
    assert textos.texto_consumible(cons, "RECEPCIÓN") == 'EL EQUIPO RETORNÓ SIN 02 CONOS DE 28"'


def test_recuperacion_solo_cuando_hay_falta_o_dano():
    faltante = {"cantidad": 1, "descripcion": "EXTINTOR 6 KG", "estado_recepcion": "NO_RETORNA"}
    conforme = {"cantidad": 1, "descripcion": "EXTINTOR 6 KG", "estado_recepcion": "OK"}
    assert textos.texto_recuperacion(faltante, 3).startswith("RECUPERACIÓN N° 3")
    assert "SIN RECUPERACIÓN" in textos.texto_recuperacion(conforme, 3)


def test_recuperacion_manual_tiene_prioridad():
    cons = {"cantidad": 1, "descripcion": "X", "recuperacion": "TEXTO ACORDADO CON EL CLIENTE"}
    assert textos.texto_recuperacion(cons, 1) == "TEXTO ACORDADO CON EL CLIENTE"


def test_sin_estado_la_recepcion_no_afirma_nada():
    """Una observacion a medio llenar se imprime, pero no declara un retorno.

    El operador toma la foto y todavia no ha dicho si volvio o no volvio. El
    bloque sale igual —con su descripcion y su fotografia—, y la columna de
    recepcion queda vacia: decir "EL EQUIPO RETORNO CON" seria afirmar un
    hecho que nadie declaro, y "CONFORME" seria darlo por bueno sin revisarlo.
    """
    cons = {"cantidad": 1, "descripcion": "BARRA PUESTA A TIERRA"}
    assert textos.texto_consumible(cons, "DESPACHO") == "01 BARRA PUESTA A TIERRA DESPACHADO"
    assert textos.texto_consumible(cons, "RECEPCIÓN") == ""
    assert textos.cierres_consumible(cons) == []


def test_sin_estado_pero_con_texto_a_mano_la_franja_va():
    """Lo escrito a mano si es una declaracion: no se pierde."""
    cons = {"cantidad": 1, "descripcion": "X", "recuperacion": "ACORDADO CON EL CLIENTE"}
    cierres = textos.cierres_consumible(cons)
    assert len(cierres) == 1
    assert textos.texto_recuperacion(cons, 1) == "ACORDADO CON EL CLIENTE"


def test_sin_estado_pero_con_retorno_parcial_declarado_la_franja_va():
    """Declarar cuantas volvieron es declarar un hecho, y cierra el bloque."""
    cons = {"cantidad": 2, "descripcion": "GANCHOS", "cantidad_retorna": 1}
    cierres = textos.cierres_consumible(cons)
    assert [c["recupera"] for c in cierres] == [True, False]
    assert "01 DE 02 GANCHOS" in textos.texto_consumible(cons, "RECEPCIÓN")


def test_control_por_categoria_de_equipo():
    diesel = [c["consumible"] for c in textos.control_consumibles_vacio("maquinaria_amarilla")]
    electrica = [c["consumible"] for c in textos.control_consumibles_vacio("plataforma_elevacion")]
    assert "Combustible diésel" in diesel
    assert "Combustible diésel" not in electrica  # es electrica: no lleva diesel


def test_el_despacho_no_afirma_un_retorno():
    """Un acta de despacho no puede declarar hechos que aun no ocurrieron."""
    cons = {"cantidad": 1, "descripcion": "EXTINTOR 6 KG"}
    assert textos.texto_consumible(cons, "DESPACHO", "DESPACHO") == \
           "01 EXTINTOR 6 KG DESPACHADO"
    assert textos.texto_consumible(cons, "RECEPCIÓN", "DESPACHO") == ""
    assert textos.texto_recuperacion(cons, 1, "DESPACHO") == ""


def test_la_recepcion_si_declara_el_retorno():
    cons = {"cantidad": 1, "descripcion": "EXTINTOR 6 KG", "estado_recepcion": "OK"}
    assert "RETORNÓ" in textos.texto_consumible(cons, "RECEPCIÓN", "RECEPCION")
    assert textos.texto_recuperacion(cons, 1, "RECEPCION") != ""


# --------------------------------------------------------------------------
# retorno parcial: un bloque cierra con una franja por hecho declarado
# --------------------------------------------------------------------------

def _acc(**extra):
    base = {"descripcion": "GANCHOS DE IZAJE", "cantidad": 2,
            "estado_recepcion": "NO_RETORNA"}
    base.update(extra)
    return base


def test_sin_declarar_el_retorno_se_lee_como_antes():
    """Un acta anterior al campo tiene que dar exactamente lo mismo."""
    assert textos.reparto_consumible(_acc()) == (0, 2)
    assert textos.reparto_consumible(_acc(estado_recepcion="OK")) == (2, 0)
    assert textos.reparto_consumible(_acc(estado_recepcion="D")) == (2, 0)

    assert (textos.texto_consumible(_acc(), "RECEPCIÓN")
            == "EL EQUIPO RETORNÓ SIN 02 GANCHOS DE IZAJE")
    assert (textos.texto_recuperacion(_acc(), 1)
            == "RECUPERACIÓN N° 1 : 02 GANCHOS DE IZAJE")
    assert (textos.texto_recuperacion(_acc(estado_recepcion="OK"), 1)
            == "CONFORME N° 1 : 02 GANCHOS DE IZAJE — SIN RECUPERACIÓN")


def test_el_retorno_parcial_cierra_con_dos_franjas():
    """Salieron dos y vuelve uno: uno se cobra y el otro se da por conforme."""
    cons = _acc(cantidad_retorna=1)
    assert textos.reparto_consumible(cons) == (1, 1)

    cierres = textos.cierres_consumible(cons)
    assert [c["recupera"] for c in cierres] == [True, False]
    assert [c["cantidad"] for c in cierres] == [1, 1]

    assert (textos.texto_cierre(cons, cierres[0], 1, 0)
            == "RECUPERACIÓN N° 1 : 01 GANCHOS DE IZAJE")
    assert (textos.texto_cierre(cons, cierres[1], 1, 1)
            == "CONFORME N° 1 : 01 GANCHOS DE IZAJE — SIN RECUPERACIÓN")

    # Y la celda de recepcion dice cuantas de cuantas, no "sin" ni "con" a secas.
    assert (textos.texto_consumible(cons, "RECEPCIÓN")
            == "EL EQUIPO RETORNÓ CON 01 DE 02 GANCHOS DE IZAJE")


def test_lo_que_vuelve_danado_no_se_da_por_conforme():
    cons = _acc(estado_recepcion="D", cantidad_retorna=1)
    cierres = textos.cierres_consumible(cons)
    assert [c["recupera"] for c in cierres] == [True, True]
    assert (textos.texto_consumible(cons, "RECEPCIÓN")
            == "EL EQUIPO RETORNÓ CON 01 DE 02 GANCHOS DE IZAJE DAÑADO(A)")


def test_la_leyenda_escrita_a_mano_manda_sobre_la_automatica():
    cons = _acc(cantidad_retorna=1,
                recuperaciones=["RECUPERACIÓN N° 1 : 01 GANCHO — SE FACTURA"])
    cierres = textos.cierres_consumible(cons)
    assert (textos.texto_cierre(cons, cierres[0], 1, 0)
            == "RECUPERACIÓN N° 1 : 01 GANCHO — SE FACTURA")
    # La segunda no se escribio a mano: se redacta sola.
    assert (textos.texto_cierre(cons, cierres[1], 1, 1)
            == "CONFORME N° 1 : 01 GANCHOS DE IZAJE — SIN RECUPERACIÓN")


def test_un_despacho_no_cierra_nada():
    assert textos.cierres_consumible(_acc(), "DESPACHO") == []
