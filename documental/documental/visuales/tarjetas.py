"""Visuales propios dibujados con Pillow: respaldo de Remotion y de stock.

No tienen animación interna (solo el acercamiento lento de ``imagen_a_clip``),
pero mantienen la misma paleta que Remotion para que un video con escenas de
respaldo no se vea "roto". También convierte en clip las imágenes propias.
"""

from __future__ import annotations

import subprocess
import textwrap
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import Config
from ..modelos import ClipEscena, Escena
from .base import imagen_a_clip

FONDO = (11, 17, 23)
FONDO_SUAVE = (20, 28, 37)
TEXTO = (242, 244, 245)
TENUE = (154, 167, 179)
ACENTO = (245, 179, 1)
ACENTO2 = (46, 194, 126)

TIPOS = ("titular", "cifra", "linea_tiempo", "comparativa", "final", "imagen", "frase")


@lru_cache(maxsize=8)
def ruta_fuente(familia: str = "Inter", grosor: str = "bold") -> str:
    """Busca la fuente con fontconfig; cae a DejaVu si no está la pedida."""
    for patron in (f"{familia}:style={grosor}", f"{familia}", f"DejaVu Sans:style={grosor}", "DejaVu Sans"):
        try:
            ruta = subprocess.run(["fc-match", "-f", "%{file}", patron], capture_output=True, text=True, timeout=10).stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            break
        if ruta and Path(ruta).is_file():
            return ruta
    return "DejaVuSans-Bold.ttf"  # Pillow la trae incluida en la mayoría de instalaciones


def fuente(tamano: int, grosor: str = "bold") -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(ruta_fuente("Inter", grosor), tamano)
    except OSError:
        return ImageFont.load_default(tamano)


def _lienzo(cfg: Config) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (cfg.video.ancho, cfg.video.alto), FONDO)
    return img, ImageDraw.Draw(img)


def _parrafo(d: ImageDraw.ImageDraw, texto: str, xy: tuple[int, int], tam: int, color, ancho_car: int, grosor="bold") -> int:
    """Dibuja texto envuelto y devuelve la y final."""
    f = fuente(tam, grosor)
    x, y = xy
    for linea in textwrap.wrap(texto, ancho_car) or [""]:
        d.text((x, y), linea, font=f, fill=color)
        y += int(tam * 1.2)
    return y


def _pie_fuente(d: ImageDraw.ImageDraw, cfg: Config, texto: str) -> None:
    if texto:
        f = fuente(30, "regular")
        ancho = d.textlength(f"Fuente: {texto}", font=f)
        d.text((cfg.video.ancho - 80 - ancho, cfg.video.alto - 90), f"Fuente: {texto}", font=f, fill=TENUE)


def dibujar(tipo: str, datos: dict, cfg: Config, texto_escena: str = "") -> Image.Image:
    """Devuelve la imagen 16:9 del visual pedido."""
    img, d = _lienzo(cfg)
    W, H = cfg.video.ancho, cfg.video.alto
    if tipo == "titular":
        d.text((160, H // 2 - 180), str(datos.get("antetitulo", "")).upper(), font=fuente(44), fill=ACENTO)
        d.rectangle((160, H // 2 - 110, 420, H // 2 - 104), fill=ACENTO)
        _parrafo(d, str(datos["titulo"]), (160, H // 2 - 70), 100, TEXTO, 28)
    elif tipo == "cifra":
        dec = int(datos.get("decimales", 0))
        numero = f"{datos.get('prefijo', '')}{float(datos['valor']):,.{dec}f}{datos.get('sufijo', '')}"
        numero = numero.replace(",", " ")  # separador de miles fino, estilo es-419
        f = fuente(240)
        d.text(((W - d.textlength(numero, font=f)) / 2, H // 2 - 260), numero, font=f, fill=ACENTO)
        lineas = textwrap.wrap(str(datos["etiqueta"]), 42)
        y = H // 2 + 40
        for linea in lineas:
            fl = fuente(56, "regular")
            d.text(((W - d.textlength(linea, font=fl)) / 2, y), linea, font=fl, fill=TEXTO)
            y += 68
        _pie_fuente(d, cfg, str(datos.get("fuente", "")))
    elif tipo == "linea_tiempo":
        d.text((120, 110), str(datos["titulo"]), font=fuente(72), fill=TEXTO)
        hitos = list(datos.get("hitos", []))[:6] or [{"anio": "", "texto": ""}]
        d.rectangle((120, 557, W - 120, 563), fill=ACENTO)
        paso = (W - 240) / len(hitos)
        for i, h in enumerate(hitos):
            x = int(120 + paso * i)
            d.ellipse((x - 4, 548, x + 20, 572), fill=ACENTO)
            y = 300 if i % 2 == 0 else 610
            d.text((x, y), str(h.get("anio", "")), font=fuente(60), fill=ACENTO)
            _parrafo(d, str(h.get("texto", "")), (x, y + 76), 32, TEXTO, max(10, int(paso / 19)), "regular")
    elif tipo == "comparativa":
        d.text((120, 110), str(datos["titulo"]), font=fuente(72), fill=TEXTO)
        barras = list(datos.get("barras", []))[:6]
        maximo = max([float(b.get("valor", 0)) for b in barras] + [1.0])
        valores = [float(b.get("valor", 0)) for b in barras] or [0.0]
        ganador = min(valores) if datos.get("destacar") == "menor" else maximo
        y = 300
        for b in barras:
            valor = float(b.get("valor", 0))
            d.text((120, y + 10), str(b.get("etiqueta", "")), font=fuente(44, "regular"), fill=TEXTO)
            largo = int(1050 * valor / maximo)
            d.rounded_rectangle((560, y, 560 + max(8, largo), y + 72), 8, fill=ACENTO2 if valor == ganador else ACENTO)
            d.text((580 + largo, y + 10), f"{valor:,.0f} {datos.get('unidad', '')}".replace(",", " "), font=fuente(44), fill=TEXTO)
            y += 116
        _pie_fuente(d, cfg, str(datos.get("fuente", "")))
    elif tipo == "final":
        mensaje = str(datos.get("mensaje") or cfg.canal.llamado_final)
        f = fuente(70)
        d.text(((W - d.textlength(mensaje, font=f)) / 2, 110), mensaje, font=f, fill=TEXTO)
        canal = str(datos.get("canal") or cfg.canal.nombre)
        fc = fuente(40, "regular")
        d.text(((W - d.textlength(canal, font=fc)) / 2, 210), canal, font=fc, fill=ACENTO)
        # Huecos para los elementos de pantalla final de YouTube.
        d.rounded_rectangle((160, 420, 920, 848), 16, outline=FONDO_SUAVE, width=4)
        d.ellipse((W - 540, 520, W - 300, 760), outline=FONDO_SUAVE, width=4)
    elif tipo == "frase":
        # Respaldo de una escena de stock sin material: la idea clave en grande.
        # Máximo 3 líneas y por encima del tercio inferior: esa franja es de
        # los subtítulos quemados y no se debe tapar.
        frase = texto_escena.split(".")[0].strip() or texto_escena
        lineas = textwrap.wrap(frase, 36)
        if len(lineas) > 3:
            lineas = lineas[:3]
            lineas[-1] = lineas[-1].rstrip(" ,;") + "…"
        img = _degradado(cfg)
        d = ImageDraw.Draw(img)
        f = fuente(int(H * 0.07))
        y = int(H * 0.16)
        for linea in lineas:
            d.text((int(W * 0.083), y), linea, font=f, fill=TEXTO)
            y += int(H * 0.07 * 1.2)
    else:
        raise ValueError(f"tipo de tarjeta desconocido: {tipo}")
    return img


def _degradado(cfg: Config) -> Image.Image:
    img = Image.new("RGB", (cfg.video.ancho, cfg.video.alto), FONDO)
    d = ImageDraw.Draw(img)
    d.ellipse((-400, -300, 1100, 900), fill=FONDO_SUAVE)
    d.ellipse((1200, 500, 2300, 1500), fill=(40, 34, 14))
    return img.filter(ImageFilter.GaussianBlur(160))


class VisualTarjetas:
    nombre = "tarjetas"

    def __init__(self, config: Config) -> None:
        self._cfg = config

    def puede(self, escena: Escena) -> bool:
        return escena.visual.tipo in TIPOS

    def generar(self, escena: Escena, duracion: float, destino: Path, tipo: str | None = None) -> ClipEscena:
        tipo = tipo or escena.visual.tipo
        png = destino.with_suffix(".png")
        if tipo == "imagen":
            Image.open(escena.visual.ruta).convert("RGB").save(png)
        else:
            dibujar(tipo, escena.visual.datos, self._cfg, escena.narracion).save(png)
        # Las gráficas con texto pequeño no se acercan: el zoom recortaría bordes.
        imagen_a_clip(png, destino, duracion, self._cfg, acercar=tipo in ("imagen", "titular", "frase", "cifra"))
        return ClipEscena(ruta=destino, propio=True)
