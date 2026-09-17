"""De un solo original salen las dos formas en que se abre la app del camal.

`app-camal.cuerpo.html` tiene el título, los estilos, el marcado y el guion, y
nada más. De ahí salen:

  app-camal.html         el archivo que se guarda en el teléfono y se abre sin
                         señal, con su propio <head> y su viewport.
  artefacto-celular.html lo que se publica como enlace, sin envoltura, porque
                         el visor pone la suya y duplicarla la rompe.

Se generan en vez de mantenerse a mano porque dos copias de la misma app
divergen a la tercera corrección.

    python3 demos/camal/construir.py
"""

from __future__ import annotations

from pathlib import Path

AQUI = Path(__file__).resolve().parent
CUERPO = AQUI / "app-camal.cuerpo.html"

AVISO = (
    "<!-- Generado por construir.py desde app-camal.cuerpo.html. "
    "No editar a mano: se pisa. -->"
)

ENVOLTURA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#1A1E25">
{aviso}
{cabeza}
</head>
<body>
{cuerpo}
</body>
</html>
"""

MARCA = "<!-- CUERPO -->"


def construir() -> list[Path]:
    """Escribe las dos salidas y devuelve sus rutas."""
    original = CUERPO.read_text(encoding="utf-8")
    if MARCA not in original:
        raise SystemExit(f"falta {MARCA} en {CUERPO.name}: separa la cabeza del cuerpo")
    cabeza, cuerpo = original.split(MARCA, 1)

    autonomo = AQUI / "app-camal.html"
    autonomo.write_text(
        ENVOLTURA.format(aviso=AVISO, cabeza=cabeza.strip(), cuerpo=cuerpo.strip()),
        encoding="utf-8",
    )

    artefacto = AQUI / "artefacto-celular.html"
    artefacto.write_text(AVISO + "\n" + original, encoding="utf-8")

    return [autonomo, artefacto]


if __name__ == "__main__":
    for ruta in construir():
        print(ruta.relative_to(AQUI.parent.parent), ruta.stat().st_size, "bytes")
