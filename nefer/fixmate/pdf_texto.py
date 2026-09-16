"""Texto de un PDF, con tres lectores y en este orden.

1. `pdftotext` de poppler, si esta instalado. Es el que mejor respeta la
   disposicion de la pagina, y este repositorio ya lo usa para comprobar sus
   propios entregables.
2. `pypdf`, si esta instalado.
3. El de aqui, de biblioteca estandar, para cuando no hay ninguno de los dos.

El tercero existe por el mismo motivo que `nefer/emf.py`: el manual esta en el
disco del taller y el tecnico no va a instalar poppler para leerlo. Lee lo que
lee un PDF generado por Word, LibreOffice o un navegador —flujos comprimidos
con Flate o ASCII85, texto en `Tj`/`TJ`, fuentes con `ToUnicode`— y no
pretende mas: no rasteriza, no hace OCR y no reordena columnas.

Un PDF escaneado no tiene capa de texto y ninguno de los tres saca nada de el.
Eso no se disimula devolviendo una cadena vacia: se dice, y se dice que hay
que pasarlo por OCR.
"""

from __future__ import annotations

import base64
import contextlib
import os
import re
import shutil
import subprocess
import zlib
from pathlib import Path

# Debajo de esto no hay capa de texto que valga: el PDF es una imagen
# escaneada, o su fuente no declara como se leen sus codigos. El umbral es
# bajo a proposito —una pagina puede traer una linea sola— porque el caso que
# importa distinguir es el de cero texto, no el de poco.
MINIMO_UTIL = 10


class ErrorPDFTexto(ValueError):
    """No se pudo sacar texto del PDF."""


def extraer(ruta: str | Path, preferir: str = "auto") -> str:
    """Texto del PDF. `preferir` fuerza un lector: pdftotext, pypdf o propio."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ErrorPDFTexto(f"no existe el PDF {ruta}")

    lectores = {"pdftotext": _con_pdftotext, "pypdf": _con_pypdf,
                "propio": _con_lector_propio}
    if preferir != "auto":
        if preferir not in lectores:
            raise ValueError(f"lector desconocido: {preferir!r}")
        orden = [(preferir, lectores[preferir])]
    else:
        orden = list(lectores.items())

    intentos = []
    for nombre, lector in orden:
        try:
            texto = lector(ruta)
        except _SinLector as exc:
            intentos.append(f"{nombre}: {exc}")
            continue
        if texto and len(texto.strip()) >= MINIMO_UTIL:
            return texto
        intentos.append(f"{nombre}: recupero {len((texto or '').strip())} caracteres")

    raise ErrorPDFTexto(
        f"{ruta.name}: no se pudo sacar texto util ({'; '.join(intentos)}).\n"
        "Si el PDF es escaneado no tiene capa de texto: paselo antes por OCR "
        "(ocrmypdf entrada.pdf salida.pdf). Si no lo es, instale un lector:\n"
        "  sudo apt-get install poppler-utils    # pdftotext\n"
        "  pip install 'nefer[fixmate-docs]'     # pypdf")


class _SinLector(RuntimeError):
    """Ese lector no esta disponible en esta maquina."""


def _con_pdftotext(ruta: Path) -> str:
    binario = shutil.which("pdftotext")
    if not binario:
        raise _SinLector("no esta instalado")
    try:
        proceso = subprocess.run([binario, "-layout", "-enc", "UTF-8", str(ruta), "-"],
                                 capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise _SinLector("no respondio en 120 s") from exc
    if proceso.returncode != 0:
        raise _SinLector(proceso.stderr.decode("utf-8", "replace").strip()[:120])
    return proceso.stdout.decode("utf-8", "replace")


@contextlib.contextmanager
def _sin_ruido():
    """Tapa la salida de error del proceso mientras dura el bloque.

    Una extension nativa mal instalada no escribe su queja con `print`: la
    escribe en el descriptor 2 desde C o desde Rust, y eso no se atrapa con
    `try`. Aqui se tapa solo mientras se prueba pypdf, porque el fallo ya se
    recoge y se cuenta despues: sin esto, el tecnico ve un volcado de pila
    en pantalla antes de recibir su respuesta.
    """
    try:
        copia = os.dup(2)
    except OSError:
        yield
        return
    try:
        with open(os.devnull, "wb") as nulo:
            os.dup2(nulo.fileno(), 2)
        yield
    finally:
        os.dup2(copia, 2)
        os.close(copia)


def _con_pypdf(ruta: Path) -> str:
    # Se atrapa BaseException, que casi nunca esta bien y aqui si: una
    # extension nativa mal instalada no lanza una excepcion de Python, entra
    # en panico, y eso no puede tumbar la lectura de un manual cuando queda
    # otro lector por probar. Ctrl-C y la salida del proceso siguen pasando.
    with _sin_ruido():
        try:
            from pypdf import PdfReader
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise _SinLector(f"no utilizable ({type(exc).__name__})") from exc
        try:
            lector = PdfReader(str(ruta))
            return "\n\n".join((pagina.extract_text() or "")
                                 for pagina in lector.pages)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise _SinLector(f"fallo al leer ({type(exc).__name__}: {exc})") from exc


def _con_lector_propio(ruta: Path) -> str:
    return texto_de(ruta.read_bytes())


# --------------------------------------------------------------- el lector

_RE_OBJETO = re.compile(rb"(\d+)\s+\d+\s+obj\b(.*?)\bendobj", re.S)
_RE_FILTROS = re.compile(rb"/Filter\s*(\[[^\]]*\]|/\w+)")
_RE_REF = re.compile(rb"/%s\s+(\d+)\s+\d+\s+R")
_RE_FUENTES = re.compile(rb"/Font\s*<<(.*?)>>", re.S)
_RE_FUENTE = re.compile(rb"/([^\s/<>\[\]]+)\s+(\d+)\s+\d+\s+R")
_RE_HEX = re.compile(rb"<([0-9A-Fa-f\s]*)>")
_RE_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_RE_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)


def texto_de(datos: bytes) -> str:
    """Texto de un PDF ya leido en memoria."""
    objetos = _objetos(datos)
    paginas = _paginas(objetos)
    salida = []
    for numero in paginas:
        dic, _ = objetos[numero]
        fuentes = _fuentes_de_pagina(dic, objetos)
        for contenido in _contenidos(dic, objetos):
            pagina = _texto_de_contenido(contenido, fuentes)
            if pagina.strip():
                salida.append(pagina.strip())
    return "\n\n".join(salida)


def _objetos(datos: bytes) -> dict[int, tuple[bytes, bytes | None]]:
    """Todos los objetos del archivo: su diccionario y su flujo sin decodificar."""
    encontrados: dict[int, tuple[bytes, bytes | None]] = {}
    for m in _RE_OBJETO.finditer(datos):
        numero, cuerpo = int(m.group(1)), m.group(2)
        corte = cuerpo.find(b"stream")
        if corte < 0:
            encontrados[numero] = (cuerpo, None)
            continue
        dic = cuerpo[:corte]
        resto = cuerpo[corte + len(b"stream"):]
        # Tras 'stream' va un salto de linea, que no forma parte del flujo.
        if resto.startswith(b"\r\n"):
            resto = resto[2:]
        elif resto[:1] in (b"\n", b"\r"):
            resto = resto[1:]
        fin = resto.rfind(b"endstream")
        encontrados[numero] = (dic, resto[:fin] if fin >= 0 else resto)
    return encontrados


def _decodificar(dic: bytes, flujo: bytes | None) -> bytes | None:
    """Aplica la cadena de filtros del flujo. None si trae uno que no se sabe."""
    if flujo is None:
        return None
    m = _RE_FILTROS.search(dic)
    filtros = re.findall(rb"/(\w+)", m.group(1)) if m else []
    datos = flujo
    for filtro in filtros:
        try:
            if filtro == b"FlateDecode":
                datos = zlib.decompressobj().decompress(datos.strip(b"\r\n"))
            elif filtro == b"ASCII85Decode":
                datos = base64.a85decode(datos.strip(b"\r\n \t"), adobe=True)
            elif filtro == b"ASCIIHexDecode":
                limpio = re.sub(rb"[^0-9A-Fa-f]", b"", datos.split(b">")[0])
                datos = bytes.fromhex(limpio.decode() if len(limpio) % 2 == 0
                                      else limpio.decode() + "0")
            else:
                return None     # LZW, JPX, DCT: no es texto o no se sabe leer
        except Exception:
            return None
    return datos


def _referencia(dic: bytes, clave: bytes) -> int | None:
    m = re.search(rb"/" + clave + rb"\s+(\d+)\s+\d+\s+R", dic)
    return int(m.group(1)) if m else None


def _paginas(objetos: dict) -> list[int]:
    """Numeros de objeto de las paginas, en el orden del documento."""
    paginas = [n for n, (dic, _) in objetos.items() if b"/Type" in dic
               and re.search(rb"/Type\s*/Page\b", dic)]
    raiz = next((n for n, (dic, _) in objetos.items()
                 if re.search(rb"/Type\s*/Pages\b", dic)), None)
    if raiz is not None:
        orden = _kids(raiz, objetos, set())
        # Lo que el arbol no alcanza igual se lee: un PDF remendado a mano
        # deja paginas colgando y perderlas seria perder el manual.
        orden += [n for n in sorted(paginas) if n not in orden]
        return orden
    return sorted(paginas)


def _kids(numero: int, objetos: dict, vistos: set) -> list[int]:
    if numero in vistos or numero not in objetos:
        return []
    vistos.add(numero)
    dic, _ = objetos[numero]
    m = re.search(rb"/Kids\s*\[(.*?)\]", dic, re.S)
    if not m:
        return [numero] if re.search(rb"/Type\s*/Page\b", dic) else []
    salida: list[int] = []
    for hijo in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1)):
        salida.extend(_kids(int(hijo), objetos, vistos))
    return salida


def _recursos(dic: bytes, objetos: dict) -> bytes:
    """El bloque /Resources de una pagina, este en linea o referenciado."""
    referencia = _referencia(dic, b"Resources")
    if referencia is not None and referencia in objetos:
        return objetos[referencia][0]
    m = re.search(rb"/Resources\s*<<(.*)", dic, re.S)
    return m.group(1) if m else dic


def _fuentes_de_pagina(dic: bytes, objetos: dict) -> dict[bytes, dict]:
    """Por cada nombre de fuente de la pagina, como se convierten sus codigos."""
    recursos = _recursos(dic, objetos)
    m = _RE_FUENTES.search(recursos)
    if not m:
        return {}
    fuentes = {}
    for nombre, numero in _RE_FUENTE.findall(m.group(1)):
        objeto = objetos.get(int(numero))
        if not objeto:
            continue
        dic_fuente = objeto[0]
        cmap = {}
        unicode_ref = _referencia(dic_fuente, b"ToUnicode")
        if unicode_ref in objetos:
            bruto = _decodificar(*objetos[unicode_ref])
            if bruto:
                cmap = _cmap(bruto)
        fuentes[nombre] = {
            "cmap": cmap,
            "dos_bytes": bool(re.search(rb"/Subtype\s*/Type0\b", dic_fuente)),
        }
    return fuentes


def _hex_a_texto(crudo: bytes) -> str:
    limpio = re.sub(rb"\s", b"", crudo)
    if len(limpio) % 2:
        limpio += b"0"
    datos = bytes.fromhex(limpio.decode("ascii", "ignore"))
    try:
        return datos.decode("utf-16-be")
    except UnicodeDecodeError:
        return datos.decode("latin-1")


def _cmap(datos: bytes) -> dict[int, str]:
    """El ToUnicode de una fuente: de codigo a caracter."""
    mapa: dict[int, str] = {}
    for bloque in _RE_BFCHAR.findall(datos):
        partes = _RE_HEX.findall(bloque)
        for i in range(0, len(partes) - 1, 2):
            mapa[int(re.sub(rb"\s", b"", partes[i]) or b"0", 16)] = _hex_a_texto(partes[i + 1])
    for bloque in _RE_BFRANGE.findall(datos):
        partes = _RE_HEX.findall(bloque)
        for i in range(0, len(partes) - 2, 3):
            inicio = int(re.sub(rb"\s", b"", partes[i]) or b"0", 16)
            fin = int(re.sub(rb"\s", b"", partes[i + 1]) or b"0", 16)
            destino = _hex_a_texto(partes[i + 2])
            if not destino:
                continue
            for salto in range(0, min(fin - inicio, 1024) + 1):
                mapa[inicio + salto] = chr(ord(destino[0]) + salto)
    return mapa


def _contenidos(dic: bytes, objetos: dict) -> list[bytes]:
    """Los flujos de contenido de una pagina, ya decodificados."""
    numeros: list[int] = []
    referencia = _referencia(dic, b"Contents")
    if referencia is not None:
        numeros.append(referencia)
    else:
        m = re.search(rb"/Contents\s*\[(.*?)\]", dic, re.S)
        if m:
            numeros.extend(int(n) for n in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1)))
    flujos = []
    for numero in numeros:
        if numero in objetos:
            bruto = _decodificar(*objetos[numero])
            if bruto:
                flujos.append(bruto)
    return flujos


# Operadores que muestran texto, y los que mueven el cursor.
_RE_TOKEN = re.compile(rb"""
      \((?P<cadena>(?:\\.|[^\\()]|\((?:\\.|[^\\()])*\))*)\)
    | <(?P<hex>[0-9A-Fa-f\s]*)>
    | (?P<numero>[-+]?\d*\.?\d+)
    | /(?P<nombre>[^\s/<>\[\]()]+)
    | (?P<operador>[A-Za-z'"*]+)
    | (?P<abre>\[) | (?P<cierra>\])
""", re.X | re.S)

_ESCAPES = {b"n": "\n", b"r": "\r", b"t": "\t", b"b": "\b", b"f": "\f",
            b"(": "(", b")": ")", b"\\": "\\"}


def _cadena_literal(crudo: bytes) -> bytes:
    """Deshace los escapes de una cadena entre parentesis."""
    salida = bytearray()
    i = 0
    while i < len(crudo):
        c = crudo[i:i + 1]
        if c != b"\\":
            salida += c
            i += 1
            continue
        siguiente = crudo[i + 1:i + 2]
        if siguiente in _ESCAPES:
            salida += _ESCAPES[siguiente].encode("latin-1")
            i += 2
        elif b"0" <= siguiente <= b"7":
            # Solo del 0 al 7: `\8` y `\9` no son octal, y tratarlos como si
            # lo fueran dejaba la cuenta vacia y tumbaba la indexacion entera
            # con un ValueError por un PDF con una barra de mas.
            octal = crudo[i + 1:i + 4]
            digitos = bytes(d for d in octal if 48 <= d <= 55)
            salida.append(int(digitos, 8) & 0xFF)
            i += 1 + len(digitos)
        elif siguiente in (b"\n", b"\r"):
            i += 2      # continuacion de linea: no aporta caracter
        else:
            salida += siguiente
            i += 2
    return bytes(salida)


def _mostrar(crudo: bytes, fuente: dict | None) -> str:
    cmap = (fuente or {}).get("cmap") or {}
    if cmap:
        ancho = 2 if (fuente or {}).get("dos_bytes") or max(cmap) > 0xFF else 1
        salida = []
        for i in range(0, len(crudo) - (ancho - 1), ancho):
            codigo = int.from_bytes(crudo[i:i + ancho], "big")
            salida.append(cmap.get(codigo, ""))
        texto = "".join(salida)
        if texto.strip():
            return texto
    # Sin ToUnicode, el codigo es el byte: WinAnsi, que cp1252 reproduce.
    return crudo.decode("cp1252", "replace")


def _texto_de_contenido(contenido: bytes, fuentes: dict) -> str:
    salida: list[str] = []
    pila: list = []
    fuente = None
    y_actual = None
    for m in _RE_TOKEN.finditer(contenido):
        if m.group("cadena") is not None:
            pila.append(("cadena", _cadena_literal(m.group("cadena"))))
        elif m.group("hex") is not None:
            limpio = re.sub(rb"\s", b"", m.group("hex"))
            if len(limpio) % 2:
                limpio += b"0"
            pila.append(("cadena", bytes.fromhex(limpio.decode("ascii", "ignore"))))
        elif m.group("numero") is not None:
            pila.append(("numero", float(m.group("numero"))))
        elif m.group("nombre") is not None:
            pila.append(("nombre", m.group("nombre")))
        elif m.group("abre"):
            pila.append(("abre", None))
        elif m.group("cierra"):
            pila.append(("cierra", None))
        else:
            operador = m.group("operador")
            if operador == b"Tf":
                nombres = [v for t, v in pila if t == "nombre"]
                fuente = fuentes.get(nombres[-1]) if nombres else None
            elif operador in (b"Tj", b"'", b'"'):
                cadenas = [v for t, v in pila if t == "cadena"]
                if operador != b"Tj":
                    salida.append("\n")
                if cadenas:
                    salida.append(_mostrar(cadenas[-1], fuente))
            elif operador == b"TJ":
                for tipo, valor in pila:
                    if tipo == "cadena":
                        salida.append(_mostrar(valor, fuente))
                    elif tipo == "numero" and valor < -100:
                        # Un salto grande entre trozos es un espacio que la
                        # tipografia no escribio.
                        salida.append(" ")
            elif operador in (b"Td", b"TD"):
                numeros = [v for t, v in pila if t == "numero"]
                if len(numeros) >= 2 and numeros[-1] != 0:
                    salida.append("\n")
            elif operador == b"T*":
                salida.append("\n")
            elif operador == b"Tm":
                numeros = [v for t, v in pila if t == "numero"]
                if len(numeros) >= 6:
                    if y_actual is not None and abs(numeros[5] - y_actual) > 0.5:
                        salida.append("\n")
                    y_actual = numeros[5]
            elif operador in (b"BT", b"ET"):
                salida.append("\n")
            if operador not in (b"[", b"]"):
                pila = []
    texto = "".join(salida)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return "\n".join(linea.strip() for linea in texto.splitlines()).strip()
