"""De un solo original salen las dos formas en que se abre la app del camal.

`app-camal.cuerpo.html` tiene el título, los estilos, el marcado y el guion, y
nada más. De ahí salen:

  app-camal.html         el archivo que se guarda en el teléfono y se abre sin
                         señal, con su propio <head> y su viewport.
  artefacto-celular.html lo que se publica como enlace, sin envoltura, porque
                         el visor pone la suya y duplicarla la rompe.
  docs/camal/index.html  la forma instalable en Android: manifiesto, icono y
                         trabajador de servicio. Pages sirve `docs/`.

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

# La forma instalable: la misma app, más lo que Android pide para tratarla como
# aplicación —manifiesto, icono y trabajador de servicio—. Se publica en
# `docs/camal/`, que es lo que GitHub Pages sirve.
ENVOLTURA_PWA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#1A1E25">
<meta name="description" content="Registro de faenamiento: lotes con correlativo, Excel y acta en PDF, sin conexión.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icono-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
{aviso}
{cabeza}
</head>
<body>
{cuerpo}
<script>
// Sin esto la app abre solo con señal, y en el camal no la hay.
if ("serviceWorker" in navigator) {{
  window.addEventListener("load", function () {{
    navigator.serviceWorker.register("./sw.js").catch(function () {{}});
  }});
}}
</script>
</body>
</html>
"""


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

    instalable = AQUI.parent.parent / "docs" / "camal" / "index.html"
    instalable.parent.mkdir(parents=True, exist_ok=True)
    instalable.write_text(
        ENVOLTURA_PWA.format(aviso=AVISO, cabeza=cabeza.strip(), cuerpo=cuerpo.strip()),
        encoding="utf-8",
    )

    return [autonomo, artefacto, instalable]


if __name__ == "__main__":
    for ruta in construir():
        print(ruta.relative_to(AQUI.parent.parent), ruta.stat().st_size, "bytes")
