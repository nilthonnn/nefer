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

TRES HERRAMIENTAS, TRES MARCAS DENTRO DEL MISMO DISCO. En la pantalla de
inicio de un telefono las tres quedan juntas, y tres iconos identicos no se
eligen: se tantean. El disco y los colores son los mismos —es el mismo
producto— y dentro cambia el gesto: la llave del diagnostico, el recorrido
de la ronda, la bifurcacion del arbol de decision.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs" / "fixmate" / "app"
# Los del APK de la ronda: otros tamaños, por densidad, y con un primer plano
# transparente —Android recorta el icono a la forma del lanzador y lo que
# quede fuera del 60 % central se pierde—.
ANDROID = RAIZ / "movil" / "fixmate-ronda" / "android" / "app" / "src" / "main" / "res"
DENSIDADES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

FONDO = (22, 25, 27)        # --barra
MARCA = (231, 236, 235)     # --barra-ink
ACENTO = (111, 168, 206)    # --accent del tema oscuro, que resalta sobre el fondo

# Android recorta el icono a un circulo, asi que la marca se dibuja dentro
# del 60% central: fuera de ahi, lo que se dibuje puede no verse.
SEGURO = 0.60


def dibujar(lado: int, maskable: bool = False, marca: str = "llave",
            fondo: bool = True) -> Image.Image:
    """Un icono cuadrado de `lado` px. `maskable` deja mas aire alrededor.

    Sin `fondo` el lienzo sale transparente: es lo que pide el primer plano
    del icono adaptable de Android, que va encima de un color liso.
    """
    # Se dibuja al cuadruple y se reduce: los bordes salen suaves sin tener
    # que calcular el antialias a mano.
    escala = 4
    n = lado * escala
    img = Image.new("RGBA", (n, n), FONDO + (255,) if fondo else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    radio = n * (SEGURO if maskable else 0.72) / 2
    centro = n / 2

    # El disco: el cuerpo de la maquina.
    d.ellipse([centro - radio, centro - radio, centro + radio, centro + radio],
              outline=ACENTO, width=int(n * 0.055))

    grueso = int(n * 0.085)
    largo = radio * 1.05

    if marca == "llave":
        # El diagnostico: un trazo diagonal con la boca abierta arriba a la
        # izquierda.
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

    elif marca == "ronda":
        # La ronda: tres paradas unidas por un recorrido. Tres y no cinco
        # porque a 48 px, cinco puntos son una linea punteada.
        paradas = [(centro - largo * 0.55, centro + largo * 0.45),
                   (centro, centro - largo * 0.15),
                   (centro + largo * 0.55, centro + largo * 0.45)]
        d.line([paradas[0], paradas[1]], fill=MARCA, width=int(grueso * 0.7))
        d.line([paradas[1], paradas[2]], fill=MARCA, width=int(grueso * 0.7))
        r = grueso * 0.85
        for i, (x, y) in enumerate(paradas):
            caja = [x - r, y - r, x + r, y + r]
            # La primera va hueca: es donde se empieza.
            if i == 0:
                d.ellipse(caja, outline=MARCA, width=int(grueso * 0.55))
            else:
                d.ellipse(caja, fill=MARCA)

    elif marca == "rcm":
        # El analisis: un tronco que se bifurca. Es literalmente el arbol de
        # decision, y es lo unico que esta pantalla hace que las otras no.
        pie = (centro, centro + largo * 0.62)
        nudo = (centro, centro - largo * 0.02)
        d.line([pie, nudo], fill=MARCA, width=grueso)
        izq = (centro - largo * 0.52, centro - largo * 0.58)
        der = (centro + largo * 0.52, centro - largo * 0.58)
        d.line([nudo, izq], fill=MARCA, width=int(grueso * 0.8))
        d.line([nudo, der], fill=MARCA, width=int(grueso * 0.8))
        r = grueso * 0.8
        for x, y in (izq, der):
            d.ellipse([x - r, y - r, x + r, y + r], fill=MARCA)

    else:
        raise SystemExit(f"marca «{marca}» desconocida")

    return img.resize((lado, lado), Image.LANCZOS)


TAMANOS = [("icono-192.png", 192, False),
           ("icono-512.png", 512, False),
           ("icono-512-recortable.png", 512, True),
           ("apple-touch-icon.png", 180, False)]

# Cada herramienta instalable, con su marca. El diagnostico conserva la suya.
JUEGOS = [(DESTINO, "llave"),
          (RAIZ / "docs" / "fixmate" / "ronda", "ronda"),
          (RAIZ / "docs" / "fixmate" / "rcm", "rcm")]


def para_android(marca: str = "ronda") -> list:
    """Los del APK: el clasico por densidad y el primer plano adaptable."""
    if not ANDROID.exists():
        return []
    escritos = []
    for densidad, factor in DENSIDADES.items():
        carpeta = ANDROID / f"mipmap-{densidad}"
        carpeta.mkdir(parents=True, exist_ok=True)

        clasico = dibujar(int(48 * factor), marca=marca)
        for nombre in ("ic_launcher.png", "ic_launcher_round.png"):
            ruta = carpeta / nombre
            clasico.save(ruta, "PNG", optimize=True)
            escritos.append(ruta)

        ruta = carpeta / "ic_launcher_foreground.png"
        dibujar(int(108 * factor), maskable=True, marca=marca, fondo=False).save(
            ruta, "PNG", optimize=True)
        escritos.append(ruta)
    return escritos


def main() -> None:
    for carpeta, marca in JUEGOS:
        carpeta.mkdir(parents=True, exist_ok=True)
        hechos = []
        for nombre, lado, maskable in TAMANOS:
            ruta = carpeta / nombre
            dibujar(lado, maskable, marca).save(ruta, "PNG", optimize=True)
            hechos.append(f"{nombre} ({ruta.stat().st_size / 1024:.0f} KB)")
        print(f"{carpeta.relative_to(RAIZ)} · {marca}:  " + "  ·  ".join(hechos))

    android = para_android("ronda")
    if android:
        print(f"{ANDROID.relative_to(RAIZ)} · ronda:  {len(android)} archivos "
              f"en {len(DENSIDADES)} densidades")


if __name__ == "__main__":
    main()
