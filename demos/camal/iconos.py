"""Los iconos de la app, dibujados en vez de guardados.

Son una balanza de dos platillos: lo que el operario ve en la playa de faenado
y lo único que hace la app. Se generan aquí para que el día que cambie el
color de la marca no haya que abrir un editor de imágenes.

    python3 demos/camal/iconos.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
DESTINO = AQUI.parent.parent / "docs" / "camal"

FONDO = (26, 30, 37)        # el mismo gris de la app
VERDE = (0, 168, 107)
CLARO = (0, 255, 149)


def dibujar(lado: int) -> Image.Image:
    """La balanza, en un lienzo cuadrado de `lado` píxeles."""
    # Se dibuja al cuádruple y se reduce: así los bordes salen suaves sin
    # depender de que la librería sepa suavizar.
    escala = 4
    p = lado * escala
    lienzo = Image.new("RGB", (p, p), FONDO)
    d = ImageDraw.Draw(lienzo)

    u = p / 100.0                      # una unidad = 1% del lado
    medio = p / 2
    grueso = max(2, int(3.2 * u))

    # Mástil y base
    d.line([(medio, 24 * u), (medio, 74 * u)], fill=VERDE, width=grueso)
    d.line([(34 * u, 76 * u), (66 * u, 76 * u)], fill=VERDE, width=grueso)
    d.line([(42 * u, 76 * u), (58 * u, 76 * u)], fill=VERDE, width=int(grueso * 1.6))

    # Brazo
    d.line([(20 * u, 30 * u), (80 * u, 30 * u)], fill=CLARO, width=grueso)
    d.ellipse([medio - 4 * u, 26 * u, medio + 4 * u, 34 * u], fill=CLARO)

    # Los dos platillos, colgados del brazo
    for x in (20 * u, 80 * u):
        d.line([(x, 30 * u), (x, 44 * u)], fill=VERDE, width=max(1, int(1.6 * u)))
        d.arc([x - 14 * u, 36 * u, x + 14 * u, 58 * u], start=0, end=180,
              fill=CLARO, width=grueso)
        d.line([(x - 14 * u, 46 * u), (x + 14 * u, 46 * u)], fill=CLARO, width=grueso)

    return lienzo.resize((lado, lado), Image.LANCZOS)


def generar() -> list[Path]:
    DESTINO.mkdir(parents=True, exist_ok=True)
    escritos = []
    for nombre, lado in (("icono-192.png", 192), ("icono-512.png", 512),
                         ("apple-touch-icon.png", 180)):
        ruta = DESTINO / nombre
        dibujar(lado).save(ruta, "PNG", optimize=True)
        escritos.append(ruta)
    return escritos


if __name__ == "__main__":
    for ruta in generar():
        print(ruta.relative_to(AQUI.parent.parent), ruta.stat().st_size, "bytes")
