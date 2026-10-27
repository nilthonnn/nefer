"""Paquete de publicación para YouTube: capítulos, descripción, etiquetas y miniatura.

Límites de YouTube que se respetan aquí:
- título ≤ 100 caracteres; descripción ≤ 5000; etiquetas ≤ 500 en total;
- capítulos: el primero en 00:00, al menos 3, cada uno de 10 s o más;
- miniatura 1280×720, JPG de menos de 2 MB.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .config import Config
from .modelos import Atribucion, Guion, Tramo
from .visuales.tarjetas import ACENTO, FONDO, TEXTO, fuente

MAX_TITULO = 100
MAX_DESCRIPCION = 5000
MAX_ETIQUETAS = 500


def marca_tiempo(segundos: float) -> str:
    s = int(segundos)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def capitulos(tramos: list[Tramo]) -> list[tuple[float, str]]:
    """Inicio de cada capítulo del guion en la línea de tiempo final."""
    salida: list[tuple[float, str]] = []
    for t in tramos:
        if not salida or salida[-1][1] != t.capitulo:
            salida.append((t.inicio, t.capitulo))
    return salida


def problemas_capitulos(caps: list[tuple[float, str]], total: float) -> list[str]:
    """Por qué YouTube no mostraría los capítulos (lista vacía = todo bien)."""
    problemas = []
    if len(caps) < 3:
        problemas.append(f"hay {len(caps)} capítulos; YouTube exige al menos 3")
    for i, (inicio, titulo) in enumerate(caps):
        fin = caps[i + 1][0] if i + 1 < len(caps) else total
        if fin - inicio < 10:
            problemas.append(f"el capítulo «{titulo}» dura {fin - inicio:.1f} s (mínimo 10 s)")
    return problemas


def etiquetas(lista: list[str]) -> list[str]:
    """Recorta la lista para no superar los 500 caracteres que admite YouTube."""
    salida, total = [], 0
    for e in lista:
        costo = len(e) + (2 if " " in e else 0) + 1  # comillas si tiene espacios, más la coma
        if total + costo > MAX_ETIQUETAS:
            break
        salida.append(e)
        total += costo
    return salida


def descripcion(guion: Guion, caps: list[tuple[float, str]], atribuciones: list[Atribucion], musica: str, sintetica: bool) -> str:
    partes = [guion.descripcion.strip()] if guion.descripcion.strip() else []
    partes.append("CAPÍTULOS\n" + "\n".join(f"{marca_tiempo(t)} {titulo}" for t, titulo in caps))
    if guion.fuentes:
        partes.append("FUENTES\n" + "\n".join(f"• {f}" for f in guion.fuentes))
    vistos = set()
    creditos = []
    for a in atribuciones:
        clave = (a.proveedor, a.autor, a.url)
        if clave in vistos:
            continue
        vistos.add(clave)
        autor = a.autor or "autor sin nombre"
        creditos.append(f"• {autor} ({a.proveedor.capitalize()}) {a.url}".rstrip())
    if creditos:
        partes.append("MATERIAL DE ARCHIVO\n" + "\n".join(creditos))
    if musica:
        partes.append("MÚSICA\n" + musica)
    if sintetica:
        partes.append("Narración generada con voz sintética a partir de un guion propio.")
    hashtags = " ".join("#" + "".join(p.capitalize() for p in e.split()) for e in guion.etiquetas[:3])
    if hashtags:
        partes.append(hashtags)
    texto = "\n\n".join(partes)
    return texto[:MAX_DESCRIPCION]


def miniatura(texto: str, fondo: Path | None, salida: Path, cfg: Config) -> None:
    """Miniatura 1280×720: fotograma oscurecido + 2–5 palabras enormes.

    La última palabra va en ámbar: un solo foco de color es lo que mejor se
    lee en el tamaño diminuto en que se ve una miniatura en el móvil.
    """
    W, H = 1280, 720
    if fondo is not None and fondo.is_file():
        img = Image.open(fondo).convert("RGB").resize((W, H))
        img = ImageEnhance.Brightness(img).enhance(0.55)
        img = ImageEnhance.Contrast(img).enhance(1.2)
    else:
        img = Image.new("RGB", (W, H), FONDO)
    # Degradado oscuro a la izquierda para que el texto siempre contraste.
    capa = Image.new("L", (W, H), 0)
    dc = ImageDraw.Draw(capa)
    for x in range(W):
        dc.line([(x, 0), (x, H)], fill=int(200 * max(0.0, 1 - x / (W * 0.75))))
    img = Image.composite(Image.new("RGB", (W, H), FONDO), img, capa.filter(ImageFilter.GaussianBlur(4)))

    d = ImageDraw.Draw(img)
    texto = (texto or "").upper().strip()
    lineas = textwrap.wrap(texto, 12)[:3] or [""]
    tam = 132 if len(lineas) <= 2 else 112
    f = fuente(tam)
    y = (H - len(lineas) * int(tam * 1.05)) // 2
    for i, linea in enumerate(lineas):
        color = ACENTO if i == len(lineas) - 1 else TEXTO
        d.text((70, y), linea, font=f, fill=color, stroke_width=6, stroke_fill=(0, 0, 0))
        y += int(tam * 1.05)
    img.save(salida, "JPEG", quality=90, optimize=True)
    if salida.stat().st_size > 2 * 1024 * 1024:
        img.save(salida, "JPEG", quality=75, optimize=True)


def pausas_publicitarias(caps: list[tuple[float, str]], total: float, separacion: float = 120.0) -> list[float]:
    """Inicios de capítulo aptos para anuncios a mitad del video.

    Un anuncio en un cambio de tema molesta menos que uno a mitad de frase,
    y YouTube permite elegir los puntos a mano. Se exigen 2 min desde el
    inicio y entre pausas, y ninguna en el último minuto.
    """
    pausas: list[float] = []
    for inicio, _ in caps:
        ultima = pausas[-1] if pausas else 0.0
        if inicio >= separacion and inicio - ultima >= separacion and inicio <= total - 60:
            pausas.append(inicio)
    return pausas


def escribir_paquete(
    carpeta: Path,
    guion: Guion,
    tramos: list[Tramo],
    atribuciones: list[Atribucion],
    musica: str,
    sintetica: bool,
    previa: bool = False,
) -> dict:
    """Escribe ``metadatos.json`` y ``descripcion.txt``; devuelve los metadatos."""
    total = tramos[-1].inicio + tramos[-1].duracion if tramos else 0.0
    caps = capitulos(tramos)
    texto = descripcion(guion, caps, atribuciones, musica, sintetica)
    datos = {
        "titulo": guion.titulo[:MAX_TITULO],
        "descripcion": texto,
        "etiquetas": etiquetas(guion.etiquetas),
        "idioma": guion.idioma,
        "categoria": "Ciencia y tecnología",
        "duracion_segundos": round(total, 2),
        "capitulos": [{"inicio": marca_tiempo(t), "titulo": c} for t, c in caps],
        "pausas_publicitarias": [marca_tiempo(t) for t in pausas_publicitarias(caps, total)],
        # Una vista previa (voz sin licencia comercial) nunca debe subirse.
        "previa": previa,
        "estructura": guion.estructura,
        "contenido_sintetico_realista": False,
        "atribuciones": [asdict(a) for a in atribuciones],
        "fuentes": guion.fuentes,
    }
    (carpeta / "metadatos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "descripcion.txt").write_text(texto + "\n", encoding="utf-8")
    return datos
