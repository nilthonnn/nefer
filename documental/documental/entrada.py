"""Lectura y validación del guion (JSON o Markdown).

Toda la validación ocurre aquí, antes de gastar un céntimo en voz o una hora
de render: si algo falla, el mensaje dice el capítulo, la escena y el campo.

Formato Markdown (cómodo para escribir a mano)::

    ---
    titulo: Cómo vivir sin la red eléctrica
    miniatura: SIN CUENTA DE LUZ
    etiquetas: off grid, energía solar
    fuentes:
    - IRENA, Renewable Power Generation Costs 2023
    ---

    ## El gancho
    > stock: off grid cabin, solar panels snow
    Imagina no volver a pagar una cuenta de luz.

    > cifra: {"valor": 89, "sufijo": " %", "etiqueta": "bajó el panel solar", "fuente": "IRENA"}
    Desde 2010, el precio del panel solar cayó un ochenta y nueve por ciento.

Cada párrafo es una escena; la línea ``> tipo: ...`` justo encima define su
visual (``stock`` lleva términos separados por coma; el resto, JSON).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .errores import ErrorEntrada
from .modelos import TIPOS_VISUAL, Capitulo, Escena, Guion, Visual

# Campos mínimos de cada visual generado: sin ellos la composición sale vacía.
# Las cifras y comparativas exigen "fuente": un dato en pantalla sin respaldo
# es justo lo que hace que un revisor de YouTube dude de todo el video.
_REQUERIDOS: dict[str, tuple[str, ...]] = {
    "titular": ("titulo",),
    "cifra": ("valor", "etiqueta", "fuente"),
    "linea_tiempo": ("titulo", "hitos"),
    "comparativa": ("titulo", "barras", "fuente"),
    "final": (),
}


def slug(texto: str) -> str:
    """'¿Cómo vivir off-grid?' → 'como-vivir-off-grid'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")[:60] or "video"


def cargar(ruta: Path) -> Guion:
    """Lee un guion .json o .md y lo devuelve validado."""
    if not ruta.is_file():
        raise ErrorEntrada(f"No existe el guion: {ruta}")
    texto = ruta.read_text(encoding="utf-8")
    if ruta.suffix.lower() == ".json":
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErrorEntrada(f"{ruta}: JSON inválido (línea {e.lineno}): {e.msg}") from e
    elif ruta.suffix.lower() in (".md", ".markdown"):
        datos = _markdown_a_dict(texto, ruta)
    else:
        raise ErrorEntrada(f"{ruta}: formato no soportado (usa .json o .md)")
    guion = desde_dict(datos, origen=ruta)
    return guion


def desde_dict(datos: dict[str, Any], origen: Path | None = None) -> Guion:
    """Construye y valida un Guion desde un dict (también lo usa el guionista)."""
    if not isinstance(datos, dict):
        raise ErrorEntrada("El guion debe ser un objeto JSON")
    titulo = _texto(datos, "titulo", "guion")
    capitulos_crudos = datos.get("capitulos")
    if not isinstance(capitulos_crudos, list) or not capitulos_crudos:
        raise ErrorEntrada("guion.capitulos debe ser una lista no vacía")

    capitulos: list[Capitulo] = []
    vistos: set[str] = set()
    for ci, cap in enumerate(capitulos_crudos, 1):
        donde = f"capítulo {ci}"
        if not isinstance(cap, dict):
            raise ErrorEntrada(f"{donde}: debe ser un objeto")
        escenas_crudas = cap.get("escenas")
        if not isinstance(escenas_crudas, list) or not escenas_crudas:
            raise ErrorEntrada(f"{donde}: 'escenas' debe ser una lista no vacía")
        escenas = []
        for ei, esc in enumerate(escenas_crudas, 1):
            escena = _escena(esc, f"{donde}, escena {ei}", f"c{ci:02d}e{ei:02d}", origen)
            if escena.id in vistos:
                raise ErrorEntrada(f"{donde}, escena {ei}: id repetido '{escena.id}'")
            vistos.add(escena.id)
            escenas.append(escena)
        capitulos.append(Capitulo(titulo=_texto(cap, "titulo", donde), escenas=escenas))

    return Guion(
        titulo=titulo,
        slug=slug(str(datos.get("slug") or titulo)),
        capitulos=capitulos,
        descripcion=str(datos.get("descripcion", "")),
        etiquetas=_lista_texto(datos.get("etiquetas", []), "etiquetas"),
        fuentes=_lista_texto(datos.get("fuentes", []), "fuentes"),
        miniatura=str(datos.get("miniatura", "")),
        idioma=str(datos.get("idioma", "es-419")),
        estructura=str(datos.get("estructura", "")),
        origen=origen,
    )


def _texto(datos: dict, clave: str, donde: str) -> str:
    valor = datos.get(clave)
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorEntrada(f"{donde}: falta '{clave}' (texto no vacío)")
    return valor.strip()


def _lista_texto(valor: Any, nombre: str) -> list[str]:
    if isinstance(valor, str):
        valor = [v.strip() for v in valor.split(",")]
    if not isinstance(valor, list):
        raise ErrorEntrada(f"'{nombre}' debe ser una lista de textos")
    return [str(v).strip() for v in valor if str(v).strip()]


def _escena(datos: Any, donde: str, id_defecto: str, origen: Path | None) -> Escena:
    if not isinstance(datos, dict):
        raise ErrorEntrada(f"{donde}: debe ser un objeto")
    narracion = _texto(datos, "narracion", donde)
    visual_crudo = datos.get("visual")
    if not isinstance(visual_crudo, dict):
        raise ErrorEntrada(f"{donde}: falta 'visual' (objeto con 'tipo')")
    tipo = visual_crudo.get("tipo")
    if tipo not in TIPOS_VISUAL:
        raise ErrorEntrada(f"{donde}: visual.tipo '{tipo}' no válido; usa uno de {', '.join(TIPOS_VISUAL)}")

    visual = Visual(
        tipo=tipo,
        busqueda=_lista_texto(visual_crudo.get("busqueda", []), f"{donde}.visual.busqueda"),
        datos=dict(visual_crudo.get("datos") or {}),
        ruta=str(visual_crudo.get("ruta", "")),
    )
    if tipo == "stock" and not visual.busqueda:
        raise ErrorEntrada(f"{donde}: un visual 'stock' necesita 'busqueda' (términos, mejor en inglés)")
    if tipo == "imagen":
        if not visual.ruta:
            raise ErrorEntrada(f"{donde}: un visual 'imagen' necesita 'ruta'")
        ruta = Path(visual.ruta)
        if not ruta.is_absolute() and origen is not None:
            ruta = origen.parent / ruta
        if not ruta.is_file():
            raise ErrorEntrada(f"{donde}: no existe la imagen {ruta}")
        visual.ruta = str(ruta)
    faltan = [c for c in _REQUERIDOS.get(tipo, ()) if c not in visual.datos or visual.datos[c] in ("", None, [])]
    if faltan:
        raise ErrorEntrada(f"{donde}: visual '{tipo}' necesita en 'datos': {', '.join(faltan)}")

    pausa = datos.get("pausa", 0.0)
    if not isinstance(pausa, (int, float)) or not 0 <= pausa <= 5:
        raise ErrorEntrada(f"{donde}: 'pausa' debe ser un número entre 0 y 5 segundos")
    return Escena(id=str(datos.get("id") or id_defecto), narracion=narracion, visual=visual, pausa=float(pausa))


# --- Markdown -------------------------------------------------------------------


def _frontmatter(texto: str) -> tuple[dict[str, Any], str]:
    if not texto.startswith("---"):
        return {}, texto
    partes = texto.split("\n---", 1)
    if len(partes) != 2:
        raise ErrorEntrada("Markdown: el bloque inicial '---' no está cerrado")
    cabecera, cuerpo = partes[0][3:], partes[1]
    datos: dict[str, Any] = {}
    clave_lista: str | None = None
    for linea in cabecera.splitlines():
        if not linea.strip():
            continue
        if linea.lstrip().startswith("- ") and clave_lista:
            datos[clave_lista].append(linea.lstrip()[2:].strip())
            continue
        if ":" not in linea:
            raise ErrorEntrada(f"Markdown: línea de cabecera no válida: {linea!r}")
        clave, valor = (p.strip() for p in linea.split(":", 1))
        if valor:
            datos[clave] = valor
            clave_lista = None
        else:
            datos[clave] = []
            clave_lista = clave
    return datos, cuerpo


def _markdown_a_dict(texto: str, ruta: Path) -> dict[str, Any]:
    datos, cuerpo = _frontmatter(texto)
    capitulos: list[dict[str, Any]] = []
    visual_pendiente: dict[str, Any] | None = None
    parrafo: list[str] = []

    def cerrar_parrafo(numero_linea: int) -> None:
        nonlocal visual_pendiente
        if not parrafo:
            return
        if not capitulos:
            raise ErrorEntrada(f"{ruta}:{numero_linea}: hay narración antes del primer '## capítulo'")
        if visual_pendiente is None:
            raise ErrorEntrada(f"{ruta}:{numero_linea}: el párrafo no tiene una línea '> tipo: ...' encima")
        capitulos[-1]["escenas"].append({"narracion": " ".join(parrafo), "visual": visual_pendiente})
        parrafo.clear()
        visual_pendiente = None

    for n, linea in enumerate(cuerpo.splitlines(), 1):
        s = linea.strip()
        if s.startswith("## "):
            cerrar_parrafo(n)
            capitulos.append({"titulo": s[3:].strip(), "escenas": []})
        elif s.startswith("# "):
            cerrar_parrafo(n)
            datos.setdefault("titulo", s[2:].strip())
        elif s.startswith(">"):
            cerrar_parrafo(n)
            visual_pendiente = _linea_visual(s[1:].strip(), f"{ruta}:{n}")
        elif not s:
            cerrar_parrafo(n)
        else:
            parrafo.append(s)
    cerrar_parrafo(len(cuerpo.splitlines()))
    datos["capitulos"] = capitulos
    return datos


def _linea_visual(texto: str, donde: str) -> dict[str, Any]:
    if ":" not in texto:
        raise ErrorEntrada(f"{donde}: se esperaba '> tipo: ...'")
    tipo, resto = (p.strip() for p in texto.split(":", 1))
    if tipo == "stock":
        return {"tipo": "stock", "busqueda": [t.strip() for t in resto.split(",") if t.strip()]}
    if tipo == "imagen":
        return {"tipo": "imagen", "ruta": resto}
    try:
        datos = json.loads(resto) if resto else {}
    except json.JSONDecodeError as e:
        raise ErrorEntrada(f"{donde}: JSON inválido en el visual '{tipo}': {e.msg}") from e
    return {"tipo": tipo, "datos": datos}
