"""Sin nombre de empresa: identidad en Ajustes y migración del nombre anterior.

El repositorio no lleva razón social, logo ni marca de terceros. Cada
teléfono escribe la suya en Ajustes. Y quien ya tenía actas guardadas con la
versión anterior —que usaba otro nombre interno— las encuentra igual.
"""

from __future__ import annotations

import base64
import io
import re
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

RAIZ_REPO = Path(__file__).resolve().parents[3]
APP = Path(__file__).resolve().parents[1] / "docs" / "app" / "index.html"

# Los nombres que no pueden volver al repositorio, por motivos legales.
PROHIBIDOS = re.compile(r"rd[\s_-]?rent(?:a|al)|unimaq|ferreycorp|cat rental", re.I)
# La única excepción: la constante con la que la app migra el almacenamiento
# de los teléfonos que tenían la versión anterior. Está en la app y en sus
# copias generadas, en una sola línea cada una, y en esta prueba.
EXCEPCION = 'var LEGADO = "rdrenta";'


def test_ningun_archivo_del_repositorio_lleva_nombres_de_empresa():
    archivos = subprocess.run(["git", "ls-files"], cwd=RAIZ_REPO, capture_output=True,
                              text=True, check=True).stdout.split()
    hallados = []
    for nombre in archivos:
        if PROHIBIDOS.search(nombre):
            hallados.append(("ruta", nombre))
        ruta = RAIZ_REPO / nombre
        if ruta.suffix in {".png", ".jpg", ".woff2", ".jar", ".ico"} or not ruta.is_file():
            continue
        try:
            texto = ruta.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if ruta.name == "test_identidad.py":
            continue
        for i, linea in enumerate(texto.splitlines(), 1):
            if PROHIBIDOS.search(linea) and EXCEPCION not in linea:
                hallados.append((f"{nombre}:{i}", linea.strip()[:100]))
    assert hallados == []


pytestmark_nav = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


def _logo_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (900, 300), (20, 60, 140)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytestmark_nav
def test_identidad_en_ajustes_va_al_pdf_y_se_queda_en_el_telefono(pw, servidor, tmp_path):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.CAMPO && window.ENTREGABLE")
    # De fábrica: sin nombre, sin logo, código genérico.
    assert pg.inner_text("#marca-nombre").startswith("ACTAS DE CAMPO")
    assert pg.evaluate("() => ENTREGABLE.logo()") is None
    assert pg.evaluate("() => ENTREGABLE.control({}).codigo") == "FO-DR-001"

    pg.click("#ajustes-identidad summary")
    pg.fill("#id-empresa", "Mi Empresa S.A.C.")
    pg.fill("#id-codigo", "MI-FO-010")
    pg.fill("#id-version", "02")
    logo = tmp_path / "logo.png"
    logo.write_bytes(base64.b64decode(_logo_b64()))
    pg.set_input_files("#id-logo", str(logo))
    pg.wait_for_selector("#id-logo-ver:not([hidden])")

    assert pg.inner_text("#marca-nombre").startswith("MI EMPRESA S.A.C.")
    c = pg.evaluate("() => ENTREGABLE.control({})")
    assert (c["codigo"], c["version"]) == ("MI-FO-010", "02")
    lg = pg.evaluate("() => ENTREGABLE.logo()")
    assert lg["w"] <= 550 and lg["h"] <= 154 and abs(lg["w"] / lg["h"] - 3) < 0.05
    # Lo del acta manda sobre Ajustes.
    assert pg.evaluate("() => ENTREGABLE.control({codigo_formato: 'X-1'}).codigo") == "X-1"

    # Sobrevive a cerrar la app, y no sale del teléfono: está en localStorage.
    pg.reload()
    pg.wait_for_function("() => window.CAMPO")
    assert pg.evaluate("() => CAMPO.identidad.leer().empresa") == "Mi Empresa S.A.C."

    pg.click("#ajustes-identidad summary")
    pg.click("#id-logo-quitar")
    assert pg.evaluate("() => ENTREGABLE.logo()") is None
    nav.close()


SEMBRAR_LEGADO = """async ({b64}) => {
  localStorage.setItem('rdrenta.sesion', JSON.stringify({id: 'pviejo', vista: 'despacho'}));
  localStorage.setItem('rdrenta.tema', 'oscuro');
  const bin = atob(b64), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  const d = await new Promise((ok, mal) => {
    const p = indexedDB.open('rdrenta', 2);
    p.onupgradeneeded = () => {
      const t = p.result.createObjectStore('proyectos', {keyPath: 'id'});
      t.createIndex('modificado', 'modificado');
      p.result.createObjectStore('equipos', {keyPath: 'tag'});
      p.result.createObjectStore('fotos', {keyPath: 'id'}).createIndex('proyecto', 'proyecto');
    };
    p.onsuccess = () => ok(p.result); p.onerror = () => mal(p.error);
  });
  await new Promise(ok => {
    const tx = d.transaction(['proyectos', 'equipos'], 'readwrite');
    tx.objectStore('proyectos').put({id: 'pviejo', nombre: 'Acta de antes', vista: 'despacho',
      estado: 'borrador', creado: 1, modificado: 1, esquema: 2,
      datos: {cat: 'grupo_electrogeno', campos: {'d-equipo': 'GE-074'}, extras: [], accesorios: [],
              casillas: [0], fotos: [{nombre: 'f.jpg', archivo: new Blob([u], {type: 'image/jpeg'}),
                                      fecha: null, respaldo: 0}]}});
    tx.objectStore('equipos').put({tag: '064', grupo: {modelo: 'C100D6'}});
    tx.oncomplete = ok;
  });
  d.close();
}"""


@pytestmark_nav
def test_lo_guardado_con_el_nombre_anterior_se_migra_sin_perder_nada(pw, servidor):
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (90, 90, 90)).save(buf, "JPEG")
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pg.route(servidor + "semilla.html", lambda r: r.fulfill(
        status=200, content_type="text/html", body="<!doctype html><title>s</title>"))
    pg.goto(servidor + "semilla.html")
    pg.evaluate(SEMBRAR_LEGADO, {"b64": base64.b64encode(buf.getvalue()).decode()})

    pg.goto(servidor)
    pg.wait_for_selector("#proy-recuperado", timeout=8000)    # la sesión vieja vuelve
    r = pg.evaluate("""async () => {
      const p = await CAMPO.almacen.leer('pviejo');
      const e = await CAMPO.almacen.equipos.leer('064');
      const bases = indexedDB.databases ? (await indexedDB.databases()).map(b => b.name) : null;
      return {nombre: p.nombre, fotos: p.datos.fotos.length, foto: p.datos.fotos[0].archivo.size > 0,
              equipo: e && e.grupo.modelo, bases,
              tema: localStorage.getItem('campo.tema'),
              viejas: Object.keys(localStorage).filter(k => k.startsWith('rdrenta.'))};
    }""")
    assert r["nombre"] == "Acta de antes" and r["fotos"] == 1 and r["foto"]
    assert r["equipo"] == "C100D6"
    assert r["tema"] == "oscuro"
    assert r["viejas"] == [], "las claves viejas se retiran"
    if r["bases"] is not None:
        assert "rdrenta" not in r["bases"], "la base vieja se borra tras copiarla"
    nav.close()


@pytestmark_nav
def test_sin_datos_viejos_no_se_crea_la_base_vieja(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.CAMPO")
    bases = pg.evaluate("""async () => { await CAMPO.almacen.listar();
      return indexedDB.databases ? (await indexedDB.databases()).map(b => b.name) : null; }""")
    if bases is not None:
        assert "rdrenta" not in bases and "campo" in bases
    nav.close()
