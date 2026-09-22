"""Los iconos de la app, dibujados en vez de guardados.

Son una balanza de dos platillos: lo que el operario ve en la playa de faenado
y lo único que hace la app. Se generan aquí para que el día que cambie el
color de la marca no haya que abrir un editor de imágenes, y para que salgan
todos con el mismo margen: a ojo nunca salen iguales.

Salen los del sitio web y los del APK, que son otros tamaños y además llevan
un primer plano transparente —Android recorta el icono a la forma del lanzador
y lo que quede fuera del 60% central se pierde—.

    python3 demos/camal/iconos.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
DESTINO = RAIZ / "docs" / "camal"
ANDROID = RAIZ / "movil" / "android" / "app" / "src" / "main" / "res"

# Lo que pide Android, por densidad: el icono de siempre a 48 dp y el primer
# plano adaptable a 108 dp, del que sólo se ve con seguridad el 72 dp central.
DENSIDADES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

FONDO = (26, 30, 37)        # el mismo gris de la app
VERDE = (0, 168, 107)
CLARO = (0, 255, 149)


def dibujar(lado: int, fondo: bool = True, ocupacion: float = 1.0) -> Image.Image:
    """La balanza, en un lienzo cuadrado de `lado` píxeles.

    `ocupacion` es qué parte del lienzo ocupa el dibujo: en el icono adaptable
    vale 0.6, porque el lanzador recorta el resto.
    """
    # Se dibuja al cuádruple y se reduce: así los bordes salen suaves sin
    # depender de que la librería sepa suavizar.
    escala = 4
    p = lado * escala
    lienzo = (Image.new("RGB", (p, p), FONDO) if fondo
              else Image.new("RGBA", (p, p), (0, 0, 0, 0)))
    d = ImageDraw.Draw(lienzo)

    # La unidad se encoge con la ocupación, y el dibujo se centra solo.
    u = p * ocupacion / 100.0
    borde = p * (1 - ocupacion) / 2
    medio = p / 2
    grueso = max(2, int(3.2 * u))

    # Mástil y base
    d.line([(medio, borde + 24 * u), (medio, borde + 74 * u)], fill=VERDE, width=grueso)
    d.line([(borde + 34 * u, borde + 76 * u), (borde + 66 * u, borde + 76 * u)], fill=VERDE, width=grueso)
    d.line([(borde + 42 * u, borde + 76 * u), (borde + 58 * u, borde + 76 * u)], fill=VERDE, width=int(grueso * 1.6))

    # Brazo
    d.line([(borde + 20 * u, borde + 30 * u), (borde + 80 * u, borde + 30 * u)], fill=CLARO, width=grueso)
    d.ellipse([medio - 4 * u, borde + 26 * u, medio + 4 * u, borde + 34 * u], fill=CLARO)

    # Los dos platillos, colgados del brazo
    for x in (borde + 20 * u, borde + 80 * u):
        d.line([(x, borde + 30 * u), (x, borde + 44 * u)], fill=VERDE, width=max(1, int(1.6 * u)))
        d.arc([x - 14 * u, borde + 36 * u, x + 14 * u, borde + 58 * u], start=0, end=180,
              fill=CLARO, width=grueso)
        d.line([(x - 14 * u, borde + 46 * u), (x + 14 * u, borde + 46 * u)], fill=CLARO, width=grueso)

    return lienzo.resize((lado, lado), Image.LANCZOS)


def generar() -> list[Path]:
    """Los del sitio web y los del APK, de un solo dibujo."""
    escritos = []

    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, lado in (("icono-192.png", 192), ("icono-512.png", 512),
                         ("apple-touch-icon.png", 180)):
        ruta = DESTINO / nombre
        dibujar(lado).save(ruta, "PNG", optimize=True)
        escritos.append(ruta)

    if ANDROID.exists():
        for densidad, factor in DENSIDADES.items():
            carpeta = ANDROID / f"mipmap-{densidad}"
            carpeta.mkdir(parents=True, exist_ok=True)

            lado = int(48 * factor)
            clasico = dibujar(lado)
            for nombre in ("ic_launcher.png", "ic_launcher_round.png"):
                ruta = carpeta / nombre
                clasico.save(ruta, "PNG", optimize=True)
                escritos.append(ruta)

            # El adaptable: transparente y con el dibujo dentro del 60% central,
            # que es lo único que ningún lanzador recorta.
            ruta = carpeta / "ic_launcher_foreground.png"
            dibujar(int(108 * factor), fondo=False, ocupacion=0.6).save(
                ruta, "PNG", optimize=True)
            escritos.append(ruta)

    return escritos


if __name__ == "__main__":
    for ruta in generar():
        print(ruta.relative_to(AQUI.parent.parent), ruta.stat().st_size, "bytes")
