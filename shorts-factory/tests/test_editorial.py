import json

import pytest

from shortsfactory.errors import ErrorContenido
from shortsfactory.scripts import editorial
from shortsfactory.scripts.heuristicas import evaluar

from conftest import RAIZ

GUIONES = sorted((RAIZ / "guiones").glob("*.json"))


@pytest.mark.parametrize("ruta", GUIONES, ids=[g.stem for g in GUIONES])
def test_guiones_del_repo_pasan_las_heuristicas_con_cualquier_tendencia(ruta, serie, tendencia):
    datos = editorial.leer(ruta)
    for factor in (1.0, 0.5, 2.0):  # la serie sube, baja o se mantiene: el texto debe valer igual
        s = serie.model_copy(update={"puntos": [p.model_copy(update={"valor": p.valor * (factor if i else 1)})
                                                for i, p in enumerate(serie.puntos)]})
        g = editorial.construir(datos, s)
        assert g.generador == "editorial" and "{" not in g.texto
        ev = evaluar(g, s, tendencia, 15.0)
        assert ev.ok, (factor, ev.errores)


def test_rellena_con_la_serie(serie):
    g = editorial.construir({"titulo": "Dato de {anio_ultimo}", "frases": [
        {"texto": "Hoy {ultimo}% en {pais}", "visual": "cifra"},
        {"texto": "Antes {primero}%, {verbo}.", "visual": "grafico"},
        {"texto": "Y por eso", "visual": "texto"}]}, serie)
    assert g.titulo == "Dato de 2024"
    assert g.frases[0].texto == "Hoy 4,4% en País de prueba" and g.frases[1].texto == "Antes 3,1%, subió."


def test_hueco_desconocido(serie, tmp_path):
    with pytest.raises(ErrorContenido, match="desconocidos"):
        editorial.construir({"titulo": "Título", "frases": [{"texto": "{inventado}", "visual": "texto"}] * 3}, serie)
    ruta = tmp_path / "g.json"
    ruta.write_text(json.dumps({"titulo": "x"}), encoding="utf-8")
    with pytest.raises(ErrorContenido, match="frases"):
        editorial.leer(ruta)
