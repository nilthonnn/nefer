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


def test_control_por_categoria_de_equipo():
    diesel = [c["consumible"] for c in textos.control_consumibles_vacio("maquinaria_amarilla")]
    electrica = [c["consumible"] for c in textos.control_consumibles_vacio("plataforma_elevacion")]
    assert "Combustible diésel" in diesel
    assert "Combustible diésel" not in electrica  # es electrica: no lleva diesel
