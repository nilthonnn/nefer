"""Normalizacion del texto tecnico y extraccion de las señales que importan.

Todo lo de aqui es de biblioteca estandar y determinista: la misma frase
produce siempre los mismos tokens, los mismos codigos de falla y los mismos
torques. De eso depende que un indice construido hoy siga sirviendo mañana sin
volver a llamar a ningun servicio.
"""

from __future__ import annotations

import re
import unicodedata

# Palabras que aparecen en casi toda frase en español y no distinguen una falla
# de otra. Se quitan del indice lexico; el vector las ignora por lo mismo.
PALABRAS_VACIAS = {
    "a", "al", "ante", "con", "como", "cuando", "de", "del", "desde", "donde",
    "el", "ella", "ellos", "en", "entre", "era", "es", "esa", "ese", "eso",
    "esta", "estan", "este", "esto", "fue", "ha", "hace", "han", "hasta", "hay",
    "la", "las", "le", "les", "lo", "los", "mas", "me", "mi", "muy", "no",
    "para", "pero", "por", "porque", "que", "se", "segun", "ser", "si", "sin",
    "sobre", "solo", "son", "su", "sus", "tiene", "tras", "un", "una", "uno",
    "unos", "unas", "y", "ya",
}

# Codigos de falla que se ven en una maquina pesada. No hay uno solo: el
# tablero OBD da P0300, el bus J1939 da SPN/FMI y Caterpillar imprime CID/E.
_PATRONES_DTC = (
    re.compile(r"\b[PBCU][0-9]{4}\b", re.I),          # OBD-II: P0300
    re.compile(r"\bSPN[\s:-]*([0-9]{1,6})\b", re.I),  # J1939: SPN 157
    re.compile(r"\bFMI[\s:-]*([0-9]{1,2})\b", re.I),  # J1939: FMI 3
    re.compile(r"\bCID[\s:-]*([0-9]{2,4})\b", re.I),  # Caterpillar: CID 0168
    re.compile(r"\bE[0-9]{3}(?:[.-][0-9])?\b"),       # Caterpillar: E360.2
)

# "45 N.m", "45 Nm", "120 lb-pie", "30 lbf.ft", "8 kgf-m", y rangos "45-50 Nm".
_UNIDADES_TORQUE = r"(?:N[·\.\s-]?m|Nm|newton\s*metro?s?|lb[f]?[\s·\.-]*(?:pie|ft|pulg|in)|kgf?[\s·\.-]*m)"
_RE_TORQUE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:(?:a|-|–|\.\.\.)\s*(\d+(?:[.,]\d+)?)\s*)?(" + _UNIDADES_TORQUE + r")\b",
    re.I,
)

_RE_PALABRA = re.compile(r"[0-9a-z]+(?:[.\-/][0-9a-z]+)*")

# "Torquimetro de 5 a 60 N·m" no es un par de apriete: es el rango de la
# herramienta. Apretar a eso no significa nada.
_RE_NO_ES_TORQUE = re.compile(
    r"(torquimetro|llave de torque|torque wrench|capacidad|rango|escala)[^.;]{0,12}$",
    re.I)


def sin_tildes(texto: str) -> str:
    """Quita tildes y diereses. 'fugas hidráulicas' y 'fugas hidraulicas' son lo mismo."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Minusculas, sin tildes y con los espacios colapsados."""
    return re.sub(r"\s+", " ", sin_tildes(str(texto)).lower()).strip()


def tokenizar(texto: str, con_vacias: bool = False) -> list[str]:
    """Palabras utiles de una frase, ya normalizadas.

    Se conservan los numeros: '35%' de combustible y '4000' msnm distinguen un
    antecedente de otro tanto como las palabras.
    """
    tokens = _RE_PALABRA.findall(normalizar(texto))
    if con_vacias:
        return tokens
    return [t for t in tokens if t not in PALABRAS_VACIAS and len(t) > 1]


def ngramas(token: str, n: int = 4) -> list[str]:
    """Trozos de n caracteres de una palabra, con marcas de principio y fin.

    Es lo que permite que 'inyector' y 'inyectores' se parezcan sin mantener un
    diccionario de plurales ni un lematizador.
    """
    marcado = f"^{token}$"
    if len(marcado) <= n:
        return [marcado]
    return [marcado[i:i + n] for i in range(len(marcado) - n + 1)]


def codigos_dtc(texto: str) -> list[str]:
    """Codigos de falla citados en el texto, en mayusculas y sin repetir."""
    encontrados: list[str] = []
    for patron in _PATRONES_DTC:
        for coincidencia in patron.finditer(texto):
            codigo = normalizar_dtc(coincidencia.group(0))
            if codigo and codigo not in encontrados:
                encontrados.append(codigo)
    return encontrados


def normalizar_dtc(codigo: str) -> str:
    """Forma canonica de un codigo: 'spn 157' y 'SPN-157' se guardan 'SPN157'."""
    limpio = re.sub(r"[\s:_-]+", "", sin_tildes(str(codigo))).upper()
    return re.sub(r"^(SPN|FMI|CID)0+(?=\d)", r"\1", limpio)


def torques(texto: str) -> list[str]:
    """Pares de apriete citados en el texto, tal como se leen.

    Nunca se convierte ni se redondea un torque: un valor aproximado en un
    par de apriete es un perno reventado o una junta que sigue fugando.
    """
    valores: list[str] = []
    crudo = str(texto)
    for m in _RE_TORQUE.finditer(crudo):
        # Se quitan las tildes del trozo previo, no del texto entero: hacerlo
        # entero cambia las posiciones y el trozo deja de ser el de antes.
        previo = sin_tildes(crudo[max(0, m.start() - 60):m.start()])
        if _RE_NO_ES_TORQUE.search(previo):
            continue
        unidad = re.sub(r"\s+", " ", m.group(3)).strip()
        rango = f"{m.group(1)}-{m.group(2)}" if m.group(2) else m.group(1)
        valor = f"{rango} {unidad}"
        if valor not in valores:
            valores.append(valor)
    return valores


def frases(texto: str) -> list[str]:
    """Parte un parrafo en frases utilizables como pasos de un procedimiento."""
    crudas = re.split(r"(?<=[.;])\s+|\n+", str(texto))
    return [f.strip(" .;\t") for f in crudas if f.strip(" .;\t")]


def trocear(texto: str, maximo: int = 900, minimo: int = 120) -> list[str]:
    """Parte un documento largo en fragmentos indexables.

    Se corta por parrafos y solo dentro de un parrafo si excede `maximo`: un
    procedimiento partido a la mitad recupera la mitad del procedimiento.
    """
    trozos: list[str] = []
    acumulado = ""
    for parrafo in re.split(r"\n\s*\n", str(texto).strip()):
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        if len(parrafo) > maximo:
            if acumulado:
                trozos.append(acumulado)
                acumulado = ""
            trozos.extend(_partir_largo(parrafo, maximo))
            continue
        if acumulado and len(acumulado) + len(parrafo) + 2 > maximo:
            trozos.append(acumulado)
            acumulado = parrafo
        else:
            acumulado = f"{acumulado}\n\n{parrafo}" if acumulado else parrafo
    if acumulado:
        trozos.append(acumulado)

    # Un fragmento de dos lineas sueltas no dice nada por si solo; se pega al
    # anterior en vez de competir con el en la busqueda.
    fusionados: list[str] = []
    for trozo in trozos:
        if fusionados and len(trozo) < minimo and len(fusionados[-1]) + len(trozo) <= maximo:
            fusionados[-1] = f"{fusionados[-1]}\n\n{trozo}"
        else:
            fusionados.append(trozo)
    return fusionados


def _partir_largo(parrafo: str, maximo: int) -> list[str]:
    """Parte un parrafo interminable por frases, sin pasarse de `maximo`."""
    partes: list[str] = []
    actual = ""
    for frase in re.split(r"(?<=[.;])\s+", parrafo):
        if actual and len(actual) + len(frase) + 1 > maximo:
            partes.append(actual.strip())
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        partes.append(actual.strip())
    return partes
