import pytest

from shortsfactory.memory import Memoria
from shortsfactory.scripts.heuristicas import evaluar, numeros

from conftest import guion_bueno


def _ev(g, serie, tendencia, memoria=None):
    return evaluar(g, serie, tendencia, 15.0, memoria)


def test_guion_bueno_pasa(serie, tendencia):
    ev = _ev(guion_bueno(), serie, tendencia)
    assert ev.ok, ev.errores


def test_numeros_en_formato_espanol():
    assert numeros("Subió de 3,1% a 9,5% entre 2014 y 2022; 12.500 dólares") == [3.1, 9.5, 2014, 2022, 12500]


def _con_frase(i, **cambios):
    g = guion_bueno()
    frases = [f.model_dump() for f in g.frases]
    frases[i].update(cambios)
    return guion_bueno(frases=frases)


@pytest.mark.parametrize("guion, fragmento", [
    (_con_frase(0, texto="Hola amigos, hoy veremos la inflación 4,4%"), "gastada"),
    (_con_frase(0, texto="La inflación del país de prueba"), "detonante"),
    (_con_frase(0, texto="Este dato de inflación cambió muchísimo durante los últimos años, 4,4%"), "10 o menos"),
    (_con_frase(1, texto="Este es el gráfico."), "bucle abierto"),
    (_con_frase(4, texto="Eso es todo."), "loop"),
    (_con_frase(2, texto="En 2014 estaba en 3,1%. En 2022 llegó a 12%."), "no salen de los datos"),
    (_con_frase(3, texto="Compra dólares antes de que suba."), "inversión"),
    (_con_frase(1, texto="Suscríbete para la razón."), "suscripción"),
    (_con_frase(3, broll_busqueda=""), "broll_busqueda"),
])
def test_errores_explicables(guion, fragmento, serie, tendencia):
    ev = _ev(guion, serie, tendencia)
    assert any(fragmento in e for e in ev.errores), ev.errores


def test_demasiado_largo(serie, tendencia):
    larga = " ".join(["palabra"] * 40)
    ev = _ev(_con_frase(3, texto=larga), serie, tendencia)
    assert any("Recorta" in e for e in ev.errores)


def test_sin_visual_de_datos(serie, tendencia):
    g = guion_bueno()
    frases = [{**f.model_dump(), "visual": "texto"} for f in g.frases]
    ev = _ev(guion_bueno(frases=frases), serie, tendencia)
    assert any("valor propio" in e for e in ev.errores)


def test_variaciones_calculadas_son_citables(serie, tendencia):
    # 3,1 → 4,4 es +41,9 %: una variación calculada de la serie se permite.
    ev = _ev(_con_frase(3, texto="Subió un 41,9% en diez años."), serie, tendencia)
    assert not any("no salen" in e for e in ev.errores), ev.errores


def test_bloquea_repetir_un_short_del_canal(tmp_path, serie, tendencia):
    memoria = Memoria(tmp_path)
    memoria.registrar(titulo="Anterior", narracion=guion_bueno().texto)
    ev = _ev(guion_bueno(), serie, tendencia, memoria)
    assert any("Se parece" in e for e in ev.errores)
