"""El clasificador de causas: lo que dice el historial entero.

Dos cosas se prueban aqui por encima de todo: que agrupe la misma causa
escrita de tres formas —si no, el historial queda partido en anecdotas— y
que se calle cuando no tiene con que hablar.
"""

import pytest

from nefer.fixmate import aprendizaje
from nefer.fixmate.aprendizaje import ClasificadorCausas, agrupar_causas, misma_causa

# Un historial pequeño pero con lo que importa: tres causas, varias formas de
# escribir cada una y sintomas que se solapan.
EJEMPLOS = [
    ("humo negro al tomar carga", "Filtro de aire colmatado"),
    ("perdida de potencia y humo negro en altura", "Filtro de aire colmatado por polvo de mina"),
    ("humo negro en pendiente con carga", "Filtro de aire colmatado; restriccion de admision"),
    ("el motor no levanta carga y humea", "Filtro de aire colmatado por polvo"),
    ("marcha inestable en frio", "Inyector con retorno excesivo"),
    ("cascabeleo y humo en ralenti", "Inyector con retorno excesivo por aguja desgastada"),
    ("falla de combustion en un cilindro", "Inyector con retorno excesivo"),
    ("ralenti irregular y olor a diesel", "Inyector con retorno excesivo por asiento gastado"),
    ("fuga de aceite hidraulico en el cilindro", "Sello del vastago cortado"),
    ("charco de aceite bajo la maquina", "Sello del vastago cortado por rebaba"),
    ("goteo en el cilindro del brazo", "Sello del vastago cortado en el brazo"),
    ("perdida de aceite por el vastago", "Sello del vastago cortado"),
    ("no arranca en la mañana", "Baterias sulfatadas"),
    ("el arranque gira lento", "Baterias sulfatadas por descargas profundas"),
]


def _entrenado() -> ClasificadorCausas:
    return ClasificadorCausas().entrenar(EJEMPLOS)


# ----------------------------------------------------------- agrupamiento

def test_la_misma_causa_escrita_larga_y_corta_es_la_misma():
    assert misma_causa("Filtro de aire colmatado",
                       "Filtro de aire colmatado por polvo de mina")


def test_la_misma_causa_con_detalles_distintos_es_la_misma():
    # Comparten dos palabras de diez: por conteo no se parecen, y son lo
    # mismo. Lo que las une es el sujeto con el que empiezan.
    assert misma_causa("Baterias sulfatadas con densidad por debajo de 1.220 en dos vasos",
                       "Baterias sulfatadas por descargas profundas en almacen")


def test_dos_causas_distintas_no_se_mezclan():
    assert not misma_causa("Filtro de aire colmatado", "Filtro de combustible tapado")
    assert not misma_causa("Sello del vastago cortado", "Baterias sulfatadas")


def test_una_palabra_suelta_no_se_lleva_por_delante_a_todo_lo_que_gotea():
    assert not misma_causa("Fuga", "Fuga de refrigerante por la bomba de agua")


def test_agrupar_deja_una_sola_forma_por_causa():
    mapa = agrupar_causas(c for _, c in EJEMPLOS)
    assert len(set(mapa.values())) == 4
    # El nombre del grupo es la forma mas frecuente y, a igualdad, la mas corta.
    assert mapa["Filtro de aire colmatado por polvo"] == "Filtro de aire colmatado"


# ---------------------------------------------------------- entrenamiento

def test_con_pocos_casos_se_declara_sin_entrenar():
    clasificador = ClasificadorCausas().entrenar(EJEMPLOS[:4])
    assert not clasificador.entrenado
    assert "casos" in clasificador.motivo
    assert clasificador.predecir("humo negro") == []


def test_con_una_sola_causa_tampoco_hay_clasificador():
    unos = [(t, "Filtro de aire colmatado") for t, _ in EJEMPLOS]
    clasificador = ClasificadorCausas().entrenar(unos)
    assert not clasificador.entrenado
    assert "causas distintas" in clasificador.motivo


def test_una_causa_con_un_solo_caso_no_entra_al_reparto():
    clasificador = _entrenado()
    conmas = ClasificadorCausas().entrenar(
        EJEMPLOS + [("el tablero no enciende", "Tarjeta de control quemada")])
    assert "Tarjeta de control quemada" not in conmas.casos_por_causa
    assert set(conmas.casos_por_causa) == set(clasificador.casos_por_causa)


# ------------------------------------------------------------- prediccion

def test_acierta_la_causa_de_un_sintoma_conocido():
    prediccion = _entrenado().predecir("sale humo negro y pierde fuerza en la subida")
    assert prediccion[0].causa == "Filtro de aire colmatado"
    assert prediccion[0].casos == 4


def test_las_probabilidades_suman_uno_y_bajan_en_orden():
    prediccion = _entrenado().predecir("fuga de aceite por el cilindro", limite=10)
    assert abs(sum(c.probabilidad for c in prediccion) - 1.0) < 0.01
    assert prediccion == sorted(prediccion, key=lambda c: -c.probabilidad)
    assert prediccion[0].causa == "Sello del vastago cortado"


def test_una_palabra_que_nunca_se_vio_no_inclina_nada():
    clasificador = _entrenado()
    con_ruido = clasificador.predecir("humo negro zzyzx qwertyuiop")
    sin_ruido = clasificador.predecir("humo negro")
    assert con_ruido[0].causa == sin_ruido[0].causa


def test_el_mismo_historial_da_la_misma_respuesta():
    uno = _entrenado().predecir("no arranca en la mañana")
    otro = _entrenado().predecir("no arranca en la mañana")
    assert [(c.causa, c.probabilidad) for c in uno] == [
        (c.causa, c.probabilidad) for c in otro]


# --------------------------------------------------------------- medicion

def test_se_mide_dejando_uno_fuera_y_se_publica_la_linea_base():
    medicion = _entrenado().evaluar()
    assert medicion is not None
    assert medicion.casos == len(EJEMPLOS)
    assert medicion.causas == 4
    assert 0.0 <= medicion.precision <= 1.0
    # La linea base es acertar siempre la causa mas comun: sin ella, un
    # porcentaje de acierto no significa nada.
    assert medicion.linea_base == pytest.approx(4 / 14, abs=0.01)
    assert "linea base" not in medicion.resumen()   # se dice en castellano
    assert "%" in medicion.resumen()


def test_sin_entrenar_no_hay_medicion():
    assert ClasificadorCausas().entrenar(EJEMPLOS[:3]).evaluar() is None


def test_aprende_de_lo_que_ya_esta_indexado():
    from nefer.fixmate.indice import Fragmento, Indice

    indice = Indice()
    indice.agregar([
        Fragmento(id=f"ot:{n}", tipo="informe", fuente="h.json", texto=falla,
                  metadatos={"codigo_ot": f"OT-{n}", "resumen_falla": falla,
                             "causa_raiz": causa})
        for n, (falla, causa) in enumerate(EJEMPLOS)])
    clasificador = aprendizaje.desde_indice(indice)
    assert clasificador.entrenado
    assert clasificador.predecir("humo negro al subir")[0].causa == \
        "Filtro de aire colmatado"
