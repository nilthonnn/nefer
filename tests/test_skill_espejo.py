"""La skill «espejo» es un documento, y los documentos se quedan atrás.

La skill existe para que lo generado no envejezca en silencio. Si ella misma
nombra un generador que ya no está, o se olvida de uno nuevo, comete el
pecado que persigue — y nadie lo nota, porque una skill desactualizada sigue
leyéndose igual de bien.

Esto la vigila: que su frontmatter sea válido, que no se le hayan colado
permisos de escritura, que todo lo que nombra exista, y que su script
descubra los generadores mirando el disco en vez de una lista escrita a mano.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
SKILL = RAIZ / ".claude" / "skills" / "espejo" / "SKILL.md"
GUION = RAIZ / ".claude" / "skills" / "espejo" / "scripts" / "espejo.py"


@pytest.fixture(scope="module")
def frontmatter() -> dict:
    texto = SKILL.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert m, "la skill no abre con un frontmatter YAML"
    return yaml.safe_load(m.group(1))


@pytest.fixture(scope="module")
def cuerpo() -> str:
    return SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def modulo():
    spec = importlib.util.spec_from_file_location("espejo_guion", GUION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_el_frontmatter_es_yaml_valido_y_trae_lo_necesario(frontmatter):
    # La primera versión no parseaba: la descripción llevaba «: » sin
    # comillas. Un frontmatter roto no da error — la skill simplemente no
    # se carga, y nadie se entera.
    assert frontmatter["name"] == "espejo"
    assert frontmatter["description"].strip()
    assert "allowed-tools" in frontmatter


def test_la_skill_no_puede_escribir_archivos(frontmatter):
    """El guardrail vive en los permisos, no en la prosa.

    La regla es «no edites un archivo generado, regéneralo». Escrita sólo
    como texto depende de que el modelo se acuerde; quitada del whitelist,
    no depende de nadie.
    """
    herramientas = {t.strip() for t in frontmatter["allowed-tools"].split(",")}
    assert "Write" not in herramientas and "Edit" not in herramientas, herramientas
    assert "Bash" in herramientas


def test_la_descripción_dice_cuándo_dispararse(frontmatter):
    # Sin rutas concretas, una skill no se invoca sola: es el único
    # mecanismo que tiene Claude para saber que esto le toca.
    descripcion = frontmatter["description"]
    for ruta in ("herramientas/piel", "herramientas/rcm", "herramientas/ronda"):
        assert ruta in descripcion, f"la descripción no nombra {ruta}"


def test_el_guion_descubre_los_generadores_que_hay_hoy(modulo):
    """Mirando el disco, no una lista escrita a mano.

    Una lista se queda atrás el día que alguien agrega un generador, y la
    skill lo dejaría fuera del radar sin decir nada.
    """
    esperados = {p.name for p in (RAIZ / "herramientas").glob("espejo-*.py")}
    esperados.add("piel.py")
    assert {g.name for g in modulo.generadores()} == esperados


def test_la_piel_se_regenera_antes_que_las_pantallas(modulo):
    # La piel sale de la app y la copian las dos pantallas: al revés, se
    # regeneran con la piel vieja y hay que correrlo todo dos veces.
    nombres = [g.name for g in modulo.generadores()]
    assert nombres.index("piel.py") < nombres.index("espejo-ronda.py")
    assert nombres.index("piel.py") < nombres.index("espejo-rcm.py")


def test_un_generador_nuevo_se_corre_al_final_y_no_se_pierde(modulo, tmp_path):
    # No se adivina su orden —podría depender de otro— pero tampoco se
    # ignora: va al final y el informe lo señala.
    assert "espejo-inventado.py" not in modulo.ORDEN
    falso = RAIZ / "herramientas" / "espejo-zzz-prueba.py"
    falso.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    try:
        nombres = [g.name for g in modulo.generadores()]
        assert nombres[-1] == "espejo-zzz-prueba.py"
    finally:
        falso.unlink()


def test_todo_lo_que_la_skill_nombra_existe(cuerpo):
    """Una skill que manda correr un archivo que no está es peor que ninguna.

    Manda al modelo a un callejón y le hace inventar el camino de vuelta.
    """
    citados = set(re.findall(r"(?:tests|herramientas|\.claude)[\w/.\-]+\.(?:py|json)",
                             cuerpo))
    assert citados, "la skill no nombra ningún archivo"
    faltan = [c for c in sorted(citados) if not (RAIZ / c).exists()]
    assert not faltan, f"la skill nombra archivos que no existen: {faltan}"


def test_el_guion_corre_y_dice_que_el_arbol_esta_al_dia():
    """Y de paso vigila lo mismo que la skill: que lo publicado sea lo generado.

    En una copia recién clonada tiene que salir 0. Si sale 1, alguien
    commiteó una fuente sin regenerar.
    """
    salida = subprocess.run([sys.executable, str(GUION)], cwd=RAIZ,
                            capture_output=True, text=True)
    assert salida.returncode == 0, salida.stdout + salida.stderr
    for nombre in ("piel.py", "espejo-rcm.py", "espejo-ronda.py"):
        assert nombre in salida.stdout
