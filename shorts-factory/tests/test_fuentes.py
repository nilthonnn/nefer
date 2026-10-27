import pytest
import requests

from shortsfactory.errors import ErrorConfiguracion, ErrorContenido, ErrorTransitorio, ShortsError
from shortsfactory.core import retry
from shortsfactory.models import Tendencia
from shortsfactory.sources import tendencias, worldbank
from shortsfactory.sources.http import obtener_json


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)


@pytest.mark.parametrize("tema, indicador, pais", [
    ("La crisis de los semiconductores", "TX.VAL.TECH.MF.ZS", "WLD"),
    ("Inflación récord en Argentina", "FP.CPI.TOTL.ZG", "AR"),
    ("¿Se viene una recesión en Estados Unidos?", "NY.GDP.MKTP.KD.ZG", "US"),
    ("El desempleo en México no para de cambiar", "SL.UEM.TOTL.ZS", "MX"),
    ("La carrera por la inteligencia artificial", "GB.XPD.RSDV.GD.ZS", "WLD"),
    ("TSMC y Taiwán dominan los chips", "TX.VAL.TECH.MF.ZS", "WLD"),
])
def test_elige_indicador_y_pais(tema, indicador, pais):
    ind, p = worldbank.elegir(tema)
    assert (ind.id, p) == (indicador, pais)


def test_sin_coincidencias_rota_al_menos_usado():
    usados = [i.id for i in worldbank.CATALOGO[:3]]
    ind, _ = worldbank.elegir("Un tema cualquiera", usados)
    assert ind.id not in usados


def test_parsear_respuesta_del_banco_mundial():
    filas = [{"date": str(a), "value": v} for a, v in [(2020, 1.5), (2019, None), (2018, 2.0), (2017, 2.5), (2016, 1.0), (2015, 0.5), (2014, 1.1)]]
    s = worldbank.parsear([{"page": 1}, filas], worldbank.CATALOGO[0], "MX")
    assert [p.anio for p in s.puntos] == [2014, 2015, 2016, 2017, 2018, 2020] and s.pais_nombre == "México"
    with pytest.raises(ErrorContenido, match="no tiene"):
        worldbank.parsear([{"message": [{"value": "Invalid"}]}], worldbank.CATALOGO[0], "XX")


def test_tendencias_filtra_nicho_y_temas_cubiertos():
    c = [Tendencia(titulo="Receta de pan casero", puntaje=999),
         Tendencia(titulo="Nvidia presenta un nuevo chip para IA", puntaje=50),
         Tendencia(titulo="El banco central sube las tasas otra vez", puntaje=40)]
    assert tendencias.elegir(c, []).titulo.startswith("Nvidia")
    assert tendencias.elegir(c, ["Nvidia presenta un nuevo chip para IA"]).titulo.startswith("El banco")
    with pytest.raises(ShortsError):
        tendencias.elegir(c[:1], [])


class _Sesion:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)

    def get(self, url, **kw):
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        status, datos = r
        return type("R", (), {"status_code": status, "text": "x", "json": lambda self: datos})()


def test_http_reintenta_y_clasifica():
    assert obtener_json("https://api.x/y", sesion=_Sesion([(503, None), requests.ConnectionError(), (200, {"ok": 1})])) == {"ok": 1}
    with pytest.raises(ErrorConfiguracion):
        obtener_json("https://api.x/y", sesion=_Sesion([(401, None)]))
    with pytest.raises(ErrorTransitorio):
        obtener_json("https://api.x/y", sesion=_Sesion([(429, None)] * 4))
