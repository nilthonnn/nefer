#!/usr/bin/env python3
"""Los iconos de FixMate, generados y no dibujados a mano.

Se generan por dos razones. Una es que un binario en el repositorio que
nadie sabe rehacer envejece y se queda: cuando cambia el color de marca,
alguien tiene que abrir un editor. La otra es que asi salen iguales las tres
veces —192, 512 y el de Apple— y con el mismo margen, que es lo que hace que
Android no lo recorte mal al ponerlo en la pantalla de inicio.

La marca es una llave sobre un disco: se reconoce a 48 px en una pantalla
sucia y con sol, que es donde se va a ver. Sin texto: «FixMate» escrito en
un icono de 48 px no se lee, ocupa el lugar de lo que si se ve y encima hay
que traducirlo.

Los colores son los de la casa: el fondo de la barra y el acento.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs" / "fixmate" / "app"

FONDO = (22, 25, 27)        # --barra
MARCA = (231, 236, 235)     # --barra-ink
ACENTO = (111, 168, 206)    # --accent del tema oscuro, que resalta sobre el fondo

# Android recorta el icono a un circulo, asi que la marca se dibuja dentro
# del 60% central: fuera de ahi, lo que se dibuje puede no verse.
SEGURO = 0.60


def dibujar(lado: int, maskable: bool = False) -> Image.Image:
    """Un icono cuadrado de `lado` px. `maskable` deja mas aire alrededor."""
    # Se dibuja al cuadruple y se reduce: los bordes salen suaves sin tener
    # que calcular el antialias a mano.
    escala = 4
    n = lado * escala
    img = Image.new("RGBA", (n, n), FONDO + (255,))
    d = ImageDraw.Draw(img)

    radio = n * (SEGURO if maskable else 0.72) / 2
    centro = n / 2

    # El disco: el cuerpo de la maquina.
    d.ellipse([centro - radio, centro - radio, centro + radio, centro + radio],
              outline=ACENTO, width=int(n * 0.055))

    # La llave: un trazo diagonal con la boca abierta arriba a la izquierda.
    grueso = int(n * 0.085)
    largo = radio * 1.05
    x0, y0 = centro - largo * 0.62, centro + largo * 0.62
    x1, y1 = centro + largo * 0.50, centro - largo * 0.50
    d.line([x0, y0, x1, y1], fill=MARCA, width=grueso)

    # La boca de la llave: un arco abierto en la punta de arriba.
    boca = grueso * 1.5
    d.arc([x1 - boca, y1 - boca, x1 + boca, y1 + boca],
          start=200, end=110, fill=MARCA, width=int(grueso * 0.8))

    # El punto del mango: cierra el trazo y da peso abajo.
    punta = grueso * 0.55
    d.ellipse([x0 - punta, y0 - punta, x0 + punta, y0 + punta], fill=MARCA)

    return img.resize((lado, lado), Image.LANCZOS)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    hechos = []
    for nombre, lado, maskable in [("icono-192.png", 192, False),
                                   ("icono-512.png", 512, False),
                                   ("icono-512-recortable.png", 512, True),
                                   ("apple-touch-icon.png", 180, False)]:
        ruta = DESTINO / nombre
        dibujar(lado, maskable).save(ruta, "PNG", optimize=True)
        hechos.append(f"{nombre} ({ruta.stat().st_size / 1024:.0f} KB)")
    print("  ·  ".join(hechos))


if __name__ == "__main__":
    main()
