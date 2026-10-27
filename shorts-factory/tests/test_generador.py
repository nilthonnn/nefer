import random
import types

import pytest

from shortsfactory.errors import ErrorConfiguracion, ErrorContenido, ErrorTransitorio
from shortsfactory.memory import Memoria
from shortsfactory.scripts import generador
from shortsfactory.scripts.heuristicas import evaluar
from shortsfactory.settings import Settings

from conftest import guion_bueno


class _Anthropic:
    """Doble del SDK: entrega guiones en orden y registra lo que recibe."""

    def __init__(self, entregas):
        self.entregas = list(entregas)
        self.llamadas = []
        self.messages = self

    def create(self, **kw):
        self.llamadas.append({**kw, "messages": list(kw["messages"])})
        e = self.entregas.pop(0)
        if isinstance(e, Exception):
            raise e
        bloque = types.SimpleNamespace(type="tool_use", id=f"t{len(self.llamadas)}", input=e)
        return types.SimpleNamespace(content=[bloque], stop_reason="tool_use")


def _cfg(tmp_path, **kw):
    return Settings(_env_file=None, anthropic_api_key="k", dir_estado=tmp_path, **kw)


def test_autocorrige_con_las_heuristicas(tmp_path, serie, tendencia):
    malo = guion_bueno().model_dump()
    malo["frases"][2]["texto"] = "En 2014 estaba en 3,1%. En 2022 llegó a 15%."  # cifra inventada
    bueno = guion_bueno().model_dump()
    cliente = _Anthropic([malo, bueno])
    proveedor = generador.ProveedorAnthropic(_cfg(tmp_path), cliente)
    g, ev = generador.escribir(_cfg(tmp_path), tendencia, serie, Memoria(tmp_path), proveedor)
    assert ev.ok and g.generador == "llm" and len(cliente.llamadas) == 2
    primera = cliente.llamadas[0]
    assert primera["model"] == "claude-opus-5-5"
    assert primera["tool_choice"] == {"type": "tool", "name": "entregar_guion"}
    assert "2024: 4,40" in primera["messages"][0]["content"]  # recibe la serie real
    correccion = cliente.llamadas[1]["messages"][-1]["content"][0]
    assert correccion["type"] == "tool_result" and "15" in correccion["content"]


def test_se_rinde_tras_las_correcciones(tmp_path, serie, tendencia):
    malo = guion_bueno().model_dump()
    malo["frases"][0]["texto"] = "Hola, en este video"
    cliente = _Anthropic([malo] * 3)
    proveedor = generador.ProveedorAnthropic(_cfg(tmp_path), cliente)
    with pytest.raises(ErrorContenido, match="tras las correcciones"):
        generador.escribir(_cfg(tmp_path), tendencia, serie, Memoria(tmp_path), proveedor)
    assert len(cliente.llamadas) == 3


def test_esquema_invalido_se_devuelve_al_modelo(tmp_path, serie, tendencia):
    cliente = _Anthropic([{"titulo": "x"}, guion_bueno().model_dump()])
    proveedor = generador.ProveedorAnthropic(_cfg(tmp_path), cliente)
    g, _ = generador.escribir(_cfg(tmp_path), tendencia, serie, Memoria(tmp_path), proveedor)
    assert "esquema" in cliente.llamadas[1]["messages"][-1]["content"][0]["content"]


def test_errores_del_sdk_se_clasifican():
    e = type("RateLimitError", (Exception,), {"status_code": 429})()
    assert isinstance(generador._clasificar(e), ErrorTransitorio)
    e = type("AuthenticationError", (Exception,), {"status_code": 401})()
    assert isinstance(generador._clasificar(e), ErrorConfiguracion)


def test_openai_con_json_schema(tmp_path, serie, tendencia):
    import json

    llamadas = []

    def create(**kw):
        llamadas.append(kw)
        msg = types.SimpleNamespace(content=json.dumps(guion_bueno().model_dump(exclude={"generador"})))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    cliente = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    cfg = Settings(_env_file=None, llm_proveedor="openai", llm_modelo="modelo-x", openai_api_key="k", dir_estado=tmp_path)
    g, ev = generador.escribir(cfg, tendencia, serie, Memoria(tmp_path), generador.ProveedorOpenAI(cfg, cliente))
    assert ev.ok and llamadas[0]["response_format"]["json_schema"]["strict"] is True


def test_plantilla_es_valida_pero_no_publicable(serie, tendencia):
    for semilla in range(5):
        g = generador.plantilla(tendencia, serie, random.Random(semilla))
        assert g.generador == "plantilla"
        assert evaluar(g, serie, tendencia, 15.0).ok
