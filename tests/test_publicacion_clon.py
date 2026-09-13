"""Lo publicado del clon tiene que ser lo que el clon dice.

GitHub Pages sirve `docs/` de la raiz y nada mas, asi que la app de RD RENTAL
se publica como copia en `docs/rd-rental/`. Una copia se queda atras sola: aqui
se comparan las dos carpetas, archivo por archivo y byte a byte.

Se rehace con `python3 herramientas/publicar-clon.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas"))


def _clones():
    import importlib.util

    ruta = RAIZ / "herramientas" / "publicar-clon.py"
    spec = importlib.util.spec_from_file_location("publicar_clon", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.CLONES


def _archivos(carpeta: Path) -> dict[Path, bytes]:
    return {a.relative_to(carpeta): a.read_bytes()
            for a in carpeta.rglob("*") if a.is_file()}


def test_lo_publicado_es_igual_a_lo_que_dice_el_clon():
    for origen, destino in _clones():
        o, d = RAIZ / origen, RAIZ / destino
        assert d.is_dir(), f"falta la carpeta publicada {destino}"

        del_clon, publicados = _archivos(o), _archivos(d)
        faltan = sorted(set(del_clon) - set(publicados))
        sobran = sorted(set(publicados) - set(del_clon))
        assert not faltan, f"sin publicar: {faltan[:5]}"
        assert not sobran, f"publicado de mas: {sobran[:5]}"

        distintos = sorted(r for r in del_clon if del_clon[r] != publicados[r])
        assert not distintos, (
            f"la copia publicada se quedo atras en: {distintos[:5]}. "
            "Rehagala con: python3 herramientas/publicar-clon.py")


def test_la_app_publicada_apunta_a_donde_de_verdad_queda():
    """La direccion que la app declara es la que tendra al publicarse.

    Si no coinciden, el aviso de la app manda al operador a una direccion que
    no existe, y el QR impreso en el taller tampoco lleva a ninguna parte.
    """
    for _, destino in _clones():
        app = RAIZ / destino / "app" / "index.html"
        assert app.is_file(), f"falta {app}"
        esperada = f"https://nilthonnn.github.io/nefer/{Path(destino).name}/app/"
        assert f'var DIRECCION_PUBLICADA = "{esperada}"' in app.read_text(encoding="utf-8")

        qr = RAIZ / destino / "qr-app.svg"
        assert esperada in qr.read_text(encoding="utf-8"), \
            "el QR apunta a otra direccion; rehagalo con herramientas/generar-qr.py"
