"""Datos reales del Banco Mundial (API pública, sin clave).

Cada Short se ancla en una serie real: el gráfico se dibuja con estos
números y el validador rechaza cualquier cifra del guion que no salga de
aquí. Es la principal defensa contra la desinformación y lo que aporta
valor propio (no es un resumen de una noticia, es un dato verificable).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import requests

from ..errors import ErrorContenido
from ..models import Punto, Serie
from .http import obtener_json

URL = "https://api.worldbank.org/v2/country/{pais}/indicator/{indicador}"


@dataclass(frozen=True)
class Indicador:
    id: str
    nombre: str
    unidad: str
    claves: tuple[str, ...]  # palabras del tema que lo activan


CATALOGO: tuple[Indicador, ...] = (
    Indicador("FP.CPI.TOTL.ZG", "Inflación anual", "%", ("inflacion", "precios", "carestia", "ipc", "costo de vida")),
    Indicador("NY.GDP.MKTP.KD.ZG", "Crecimiento del PIB", "%", ("pib", "crecimiento", "recesion", "economia", "crisis")),
    Indicador("SL.UEM.TOTL.ZS", "Desempleo", "%", ("desempleo", "empleo", "trabajo", "paro", "despidos")),
    Indicador("NY.GDP.PCAP.CD", "PIB por persona", "USD", ("riqueza", "ingreso", "salario", "pobreza", "clase media")),
    Indicador("IT.NET.USER.ZS", "Personas que usan internet", "%", ("internet", "redes", "digital", "conectividad", "online")),
    Indicador("IT.CEL.SETS.P2", "Líneas móviles por cada 100 personas", "por 100", ("celular", "movil", "smartphone", "telefono", "5g")),
    Indicador("TX.VAL.TECH.MF.ZS", "Exportaciones de alta tecnología", "% de manufacturas",
              ("chips", "semiconductores", "alta tecnologia", "exportaciones", "manufactura", "fabricas")),
    Indicador("GB.XPD.RSDV.GD.ZS", "Inversión en investigación y desarrollo", "% del PIB",
              ("investigacion", "innovacion", "ia", "inteligencia artificial", "ciencia", "startups")),
    Indicador("EG.ELC.RNEW.ZS", "Electricidad renovable", "% del total", ("energia", "renovable", "solar", "eolica", "electricidad")),
    Indicador("GC.DOD.TOTL.GD.ZS", "Deuda del gobierno central", "% del PIB", ("deuda", "deficit", "gasto publico", "bonos", "default")),
    Indicador("NE.EXP.GNFS.ZS", "Exportaciones", "% del PIB", ("comercio", "aranceles", "exportar", "importaciones", "guerra comercial")),
)

PAISES: dict[str, tuple[str, tuple[str, ...]]] = {
    "WLD": ("el mundo", ()),
    "US": ("Estados Unidos", ("estados unidos", "ee uu", "eeuu", "usa", "fed", "wall street")),
    "CN": ("China", ("china", "pekin", "beijing")),
    "MX": ("México", ("mexico",)),
    "AR": ("Argentina", ("argentina", "milei")),
    "BR": ("Brasil", ("brasil",)),
    "CO": ("Colombia", ("colombia",)),
    "CL": ("Chile", ("chile",)),
    "PE": ("Perú", ("peru",)),
    "ES": ("España", ("espana",)),
    "DE": ("Alemania", ("alemania",)),
    "JP": ("Japón", ("japon",)),
    "KR": ("Corea del Sur", ("corea", "samsung")),
    "TW": ("Taiwán", ("taiwan", "tsmc")),
    "IN": ("India", ("india",)),
}


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", t)


def _contiene(texto: str, clave: str) -> bool:
    return re.search(rf"\b{re.escape(clave)}\b", texto) is not None


def elegir(tema: str, recientes: list[str] | None = None) -> tuple[Indicador, str]:
    """Indicador y país para un tema. Sin coincidencias, rota al menos usado."""
    t = normalizar(tema)
    pais = next((c for c, (_, claves) in PAISES.items() if any(_contiene(t, k) for k in claves)), "WLD")
    # Taiwán no está en el Banco Mundial: se usa el mundo para el dato.
    if pais == "TW":
        pais = "WLD"
    # Primero cuántas claves coinciden; a igualdad, la más específica (más
    # larga): "semiconductores" pesa más que "crisis".
    puntajes = [((sum(_contiene(t, k) for k in ind.claves), sum(len(k) for k in ind.claves if _contiene(t, k))), ind)
                for ind in CATALOGO]
    mejor = max(p for p, _ in puntajes)
    if mejor[0] > 0:
        return next(ind for p, ind in puntajes if p == mejor), pais
    usados = recientes or []
    return min(CATALOGO, key=lambda ind: (usados.count(ind.id), CATALOGO.index(ind))), pais


def descargar(indicador: Indicador, pais: str, desde: int = 2000, sesion: requests.Session | None = None) -> Serie:
    datos = obtener_json(
        URL.format(pais=pais, indicador=indicador.id),
        params={"format": "json", "per_page": 100, "date": f"{desde}:2100"},
        sesion=sesion,
    )
    return parsear(datos, indicador, pais)


def parsear(datos: object, indicador: Indicador, pais: str) -> Serie:
    if not isinstance(datos, list) or len(datos) < 2 or not isinstance(datos[1], list):
        mensaje = datos[0].get("message") if isinstance(datos, list) and datos and isinstance(datos[0], dict) else datos
        raise ErrorContenido(f"El Banco Mundial no tiene {indicador.id} para {pais}: {mensaje}")
    puntos = sorted(
        (Punto(anio=int(f["date"]), valor=float(f["value"])) for f in datos[1]
         if f.get("value") is not None and str(f.get("date", "")).isdigit()),
        key=lambda p: p.anio,
    )
    if len(puntos) < 5:
        raise ErrorContenido(f"Serie {indicador.id}/{pais} con muy pocos datos ({len(puntos)})")
    return Serie(
        indicador_id=indicador.id, indicador=indicador.nombre, unidad=indicador.unidad,
        pais=pais, pais_nombre=PAISES.get(pais, (pais,))[0], puntos=puntos[-25:],
        url=f"https://data.worldbank.org/indicator/{indicador.id}?locations={pais if pais != 'WLD' else '1W'}",
    )
