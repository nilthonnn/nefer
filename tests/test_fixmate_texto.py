"""Lo que el motor entiende de una frase dictada en el patio.

Aqui se fija el contrato del que dependen el indice y el diagnostico: que
codigos de falla se reconocen, que cuenta como par de apriete y que no, y que
un documento largo se parte sin romper un procedimiento por la mitad.
"""

from nefer.fixmate import texto


def test_normalizar_quita_tildes_y_espacios():
    assert texto.normalizar("  Fugas   HIDRÁULICAS\n") == "fugas hidraulicas"


def test_tokenizar_deja_fuera_las_vacias_y_conserva_los_numeros():
    tokens = texto.tokenizar("El motor pierde potencia a 4000 msnm con el 35% de carga")
    assert "el" not in tokens and "de" not in tokens
    assert "motor" in tokens and "4000" in tokens and "35" in tokens


def test_ngramas_emparejan_singular_y_plural():
    comunes = set(texto.ngramas("inyector")) & set(texto.ngramas("inyectores"))
    assert len(comunes) >= 4, "sin trozos comunes no hay tolerancia a plurales"


def test_codigos_dtc_de_los_tres_dialectos_del_taller():
    encontrados = texto.codigos_dtc(
        "Tablero con P0300, el bus da SPN 157 y FMI 3; la CAT marca CID 0168 y E360.2")
    assert "P0300" in encontrados
    assert "SPN157" in encontrados      # 'SPN 157' y 'SPN-157' son el mismo codigo
    assert "FMI3" in encontrados
    assert "CID168" in encontrados      # sin el cero a la izquierda
    assert "E360.2" in encontrados


def test_normalizar_dtc_unifica_la_forma_de_escribirlo():
    assert texto.normalizar_dtc("spn-157") == texto.normalizar_dtc("SPN 157") == "SPN157"


def test_torques_se_copian_tal_cual_sin_convertir():
    valores = texto.torques("Apriete la tapa a 210 N·m, el borne a 8 kgf-m y la "
                            "brida a 120 lb-pie")
    assert valores == ["210 N·m", "8 kgf-m", "120 lb-pie"]


def test_torques_con_rango_conservan_el_rango():
    assert texto.torques("Apriete de 45 a 50 Nm") == ["45-50 Nm"]


def test_la_capacidad_de_la_herramienta_no_es_un_par_de_apriete():
    # "Torquimetro de 5 a 60 N·m" describe la llave, no el apriete. Ofrecerlo
    # como torque es ofrecer un numero que nadie escribio para eso.
    assert texto.torques("Herramientas: Torquímetro de 5 a 60 N·m, llave de 13 mm") == []
    assert texto.torques("Apretar a 30 N·m con torquímetro de 5 a 60 N·m") == ["30 N·m"]


def test_frases_parte_una_solucion_en_pasos():
    assert texto.frases("Se cambio el filtro. Se purgo el sistema; se probo en vacio") == [
        "Se cambio el filtro", "Se purgo el sistema", "se probo en vacio"]


def test_trocear_respeta_los_parrafos_cortos():
    documento = "Primer parrafo.\n\n" + "x" * 200 + "\n\n" + "y" * 200
    trozos = texto.trocear(documento, maximo=250)
    assert len(trozos) == 2
    assert trozos[0].startswith("Primer parrafo")   # el corto se pego al siguiente


def test_trocear_parte_un_parrafo_interminable_por_frases():
    largo = " ".join(f"Frase numero {i} del procedimiento." for i in range(60))
    trozos = texto.trocear(largo, maximo=300)
    assert len(trozos) > 1
    assert all(len(t) <= 320 for t in trozos)
    # Nada se pierde al partir: los trozos contienen todas las frases.
    assert "Frase numero 59" in " ".join(trozos)
