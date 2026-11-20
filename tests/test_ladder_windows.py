"""El instalador de LadderLab para Windows, sin Windows.

Compilarlo e instalarlo pasa en la integración (windows-ladderlab.yml), en
una máquina Windows de verdad. Aquí se vigila lo que se rompe editando: que
el script lleve los archivos que existen, que no pida administrador, que los
accesos abran la app con Edge en modo aplicación, y que el flujo de verdad
instale, abra y desinstale antes de publicar.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "escritorio" / "ladderlab-windows"
ISS = CARPETA / "LadderLab.iss"
FLUJO = RAIZ / ".github" / "workflows" / "windows-ladderlab.yml"


def _iss() -> str:
    return ISS.read_text(encoding="utf-8")


def test_lleva_archivos_que_existen():
    fuentes = re.findall(r'^Source: "([^"]+)"', _iss(), re.M)
    assert fuentes, "el instalador no lleva archivos"
    for f in fuentes:
        ruta = (CARPETA / f.replace("\\", "/")).resolve()
        assert ruta.is_file(), f"falta {f}"
    assert any(f.endswith("LadderLab.html") for f in fuentes), "debe llevar la app en un solo archivo"


def test_identidad_estable_y_sin_administrador():
    iss = _iss()
    assert re.search(r"^AppId=\{\{[0-9A-F-]{36}\}", iss, re.M), "AppId fija para instalar encima"
    assert "PrivilegesRequired=lowest" in iss
    assert r"DefaultDirName={localappdata}\Programs\LadderLab" in iss
    assert 'MessagesFile: "compiler:Languages\\Spanish.isl"' in iss


def test_los_accesos_abren_con_edge_en_modo_aplicacion():
    iss = _iss()
    assert r"\Microsoft\Edge\Application\msedge.exe" in iss
    assert "'--app=\"' + DireccionApp() + '\"'" in iss
    accesos = re.findall(r'^Name: "([^"]+)"; Filename: "\{code:Programa\}"; Parameters: "\{code:Parametros\}"', iss, re.M)
    assert "{group}\\LadderLab" in accesos and "{userdesktop}\\LadderLab" in accesos


def test_el_flujo_instala_abre_y_desinstala_antes_de_publicar():
    flujo = FLUJO.read_text(encoding="utf-8")
    orden = ["Compilar el instalador", "Instalar y revisar",
             "Abrir la app instalada con Edge y recorrerla", "Desinstalar y revisar",
             "Publicar para descargar"]
    posiciones = [flujo.index(f"name: {paso}") for paso in orden]
    assert posiciones == sorted(posiciones), "el instalador se publica solo después de probarlo"
    assert 'channel="msedge"' in flujo
    assert "runs-on: windows-latest" in flujo
