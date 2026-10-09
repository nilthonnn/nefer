"""Las cinco superficies de FixMate tienen que ser el mismo producto.

FixMate se usa desde cinco pantallas: la página de entrada, la app de
diagnóstico del técnico, la ronda CIL del operador y el análisis RCM de la
oficina. Hasta que esto existió había **dos paletas**: la de la app, clara y
oscura según el aparato, y una azul marino propia de las dos pantallas
nuevas, sin modo claro.

No es un asunto de gusto. Las tres personas hablan entre ellas de la misma
máquina: si cada pantalla parece de otro programa, la primera pregunta de
cada reunión es cuál de las tres tiene el dato bueno. Y el modo claro no es
decoración: a 4.200 m al sol, una pantalla oscura no se lee.

La fuente de verdad es la app, que es la superficie más mirada y la que más
tiempo lleva probada. De ahí se copia. Esto comprueba que la copia está al
día y que nadie metió una segunda paleta por el costado.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas"))

import piel  # noqa: E402

APP = RAIZ / "docs" / "fixmate" / "app" / "index.html"
PANTALLAS = {
    "la página de entrada": RAIZ / "docs" / "fixmate" / "index.html",
    "la ronda CIL": RAIZ / "docs" / "fixmate" / "ronda" / "index.html",
    "el análisis RCM": RAIZ / "docs" / "fixmate" / "rcm" / "index.html",
    "armar": RAIZ / "docs" / "fixmate" / "armar" / "index.html",
    "la app de diagnóstico": APP,
}
HERRAMIENTAS = ("la ronda CIL", "el análisis RCM", "armar",
                "la app de diagnóstico")
# La carpeta de cada herramienta, para poder decir a qué TIENE que enlazar
# cada barra. Contar enlaces no servía: el día que apareció la cuarta
# pantalla, la cuenta falló en las tres viejas sin decir qué faltaba.
#
# La app de diagnóstico entró después que las otras tres: ellas enlazaban a
# ella y ella no enlazaba a ninguna, así que desde el diagnóstico no había
# vuelta. Que esté en esta tabla es lo que impide que vuelva a quedarse
# fuera: cada barra tiene que llevar a la entrada y a TODAS las demás.
CARPETAS = {"la ronda CIL": "ronda", "el análisis RCM": "rcm", "armar": "armar",
            "la app de diagnóstico": "app"}


@pytest.mark.parametrize("nombre", list(PANTALLAS))
def test_todas_llevan_la_misma_piel_que_la_app(nombre):
    html = PANTALLAS[nombre].read_text(encoding="utf-8")
    assert piel.tokens() in html, (
        f"{nombre} no lleva los tokens de la app. Si cambió la paleta, corra "
        "`python herramientas/piel.py` y los `espejo-*.py` de las pantallas.")


def test_la_piel_sale_de_la_app_y_no_de_una_copia():
    # Si alguien borra las marcas de la app, la piel deja de tener origen y
    # cada pantalla vuelve a inventarse el color.
    html = APP.read_text(encoding="utf-8")
    assert piel.INICIO in html and piel.FIN in html
    assert "--paper:" in piel.tokens() and "--accent:" in piel.tokens()
    # Y los tres bloques: el claro, el del sistema y el forzado.
    assert piel.tokens().count("--paper:") == 3


def test_la_capa_comun_no_declara_un_solo_color():
    """`base.css` es forma, no color. Un `#hex` ahí sería una tercera paleta.

    Es la regla que impide que esto se degrade: mientras los componentes sólo
    hablen de `var(--…)`, cambiar la piel de la app cambia las cuatro
    pantallas y no hay nada que recordar.
    """
    hexes = re.findall(r"#[0-9A-Fa-f]{3,8}\b", piel.base())
    assert not hexes, f"la capa común empezó a declarar color: {hexes}"
    for prohibido in ("rgb(", "hsl(", "rgba("):
        assert prohibido not in piel.base()


@pytest.mark.parametrize("nombre", HERRAMIENTAS)
def test_las_pantallas_nuevas_dejaron_la_paleta_azul_marino(nombre):
    html = PANTALLAS[nombre].read_text(encoding="utf-8")
    for viejo in ("#0b1220", "#152033", "#2a3a55", "#3987e5", "#93a4bd"):
        assert viejo not in html, (
            f"{nombre} todavía trae {viejo}, de la paleta que tenía antes")


@pytest.mark.parametrize("nombre", HERRAMIENTAS)
def test_cada_herramienta_dice_de_que_producto_es_y_donde_esta(nombre):
    html = PANTALLAS[nombre].read_text(encoding="utf-8")
    assert '<div class="barra">' in html, f"{nombre} no tiene la barra del producto"
    assert "<b>FixMate</b>" in html
    # Y el nombre de la pantalla al lado, que es lo que dice dónde está uno.
    etiqueta = re.search(r"<b>FixMate</b><span>([^<]+)</span>", html)
    assert etiqueta and etiqueta.group(1).strip(), f"{nombre} no se nombra"


@pytest.mark.parametrize("nombre", HERRAMIENTAS)
def test_los_enlaces_entre_herramientas_van_a_algo_que_existe(nombre):
    ruta = PANTALLAS[nombre]
    html = ruta.read_text(encoding="utf-8")
    barra = re.search(r'<nav class="vinculos">(.*?)</nav>', html, re.S)
    assert barra, f"{nombre} no enlaza con las otras herramientas"
    destinos = re.findall(r'href="([^"]+)"', barra.group(1))
    # La entrada y todas las demás herramientas: todas, y sólo ésas. Desde
    # cualquier pantalla se llega a cualquier otra, sin pasar por la entrada.
    esperados = {"../"} | {
        f"../{c}/" for n, c in CARPETAS.items() if n != nombre}
    assert set(destinos) == esperados, destinos
    for destino in destinos:
        assert (ruta.parent / destino / "index.html").exists(), (
            f"{nombre} enlaza a «{destino}», que no existe")


@pytest.mark.parametrize("nombre", HERRAMIENTAS)
def test_los_enlaces_se_quitan_si_la_pantalla_viaja_suelta(nombre):
    # Descargada por WhatsApp, la pantalla se abre con `file://` y esas
    # carpetas no están. Un enlace roto en la barra hace dudar del resto.
    html = PANTALLAS[nombre].read_text(encoding="utf-8")
    assert 'location.protocol === "file:"' in html
    assert ".barra .vinculos" in html


def test_la_pagina_de_entrada_esta_al_dia():
    assert piel.main(["--revisar"]) == 0


def test_ninguna_pantalla_se_quedo_sin_modo_claro():
    # Lo que se arregló: las dos pantallas nuevas eran oscuras y punto.
    for nombre, ruta in PANTALLAS.items():
        html = ruta.read_text(encoding="utf-8")
        assert "prefers-color-scheme: dark" in html, (
            f"{nombre} no distingue claro de oscuro")
        assert "--paper:#F3F4F2" in html, f"{nombre} no tiene el tema claro"
