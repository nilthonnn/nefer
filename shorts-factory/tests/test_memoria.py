"""Memoria del canal: deduplicación de temas, fusión y rama huérfana de estado."""

import shutil
import subprocess

import pytest

from shortsfactory import estado_git
from shortsfactory.core.fsm import Registro
from shortsfactory.core.pipeline import Pipeline
from shortsfactory.errors import ErrorContenido
from shortsfactory.memory import Memoria, fusionar, leer_jsonl, similitud_tema

requiere_git = pytest.mark.skipif(shutil.which("git") is None, reason="git no instalado")


@pytest.mark.parametrize("a,b", [
    ("La crisis de los semiconductores", "Crisis de semiconductor: ¿qué pasó?"),
    ("Inflación en Argentina 2024", "Argentina: la inflación vuelve a subir"),
    ("Nvidia supera a Apple en valor", "Apple pierde el primer puesto ante Nvidia"),
    ("Aranceles de EE.UU. a China", "Los nuevos aranceles de Trump a China"),
])
def test_temas_iguales_con_otras_palabras(a, b):
    assert similitud_tema(a, b) >= 0.6


@pytest.mark.parametrize("a,b", [
    ("La crisis de los semiconductores", "La inflación en Argentina"),
    ("El precio del dólar en México", "El precio del petróleo se dispara"),
    ("OpenAI lanza un nuevo modelo", "Google lanza un nuevo modelo de IA"),
    ("Desempleo juvenil en España", "Inteligencia artificial y empleo"),
])
def test_temas_distintos_no_se_bloquean(a, b):
    assert similitud_tema(a, b) < 0.6


def test_fusionar_no_duplica_y_ordena_por_fecha():
    a = [{"run_id": "1", "fecha": "2026-01-01"}, {"run_id": "3", "fecha": "2026-01-03"}]
    b = [{"run_id": "2", "fecha": "2026-01-02"}, {"run_id": "3", "fecha": "2026-01-03"}]
    assert [f["run_id"] for f in fusionar(a, b)] == ["1", "2", "3"]


def test_fusionar_con_escribe_solo_si_hay_novedades(tmp_path):
    m = Memoria(tmp_path)
    m.registrar(run_id="a", tema="x")
    assert m.fusionar_con([{"run_id": "a", "tema": "x", "fecha": "2026-01-01"}]) == 0
    assert m.fusionar_con([{"run_id": "b", "tema": "y", "fecha": "2020-01-01"}]) == 1
    assert [e["run_id"] for e in m.entradas()] == ["b", "a"]


def test_tema_mas_parecido_solo_mira_la_ventana(tmp_path):
    m = Memoria(tmp_path)
    m.registrar(run_id="viejo", tema="La crisis de los semiconductores", fecha="2025-01-01")
    for i in range(50):
        m.registrar(run_id=f"r{i}", tema=f"Tema distinto número {i}", fecha=f"2026-01-{i % 28 + 1:02d}")
    parecido, _ = m.tema_mas_parecido("Crisis de semiconductores", ultimas=50)
    assert parecido < 0.6  # el parecido quedó fuera de los últimos 50
    parecido, fila = m.tema_mas_parecido("Crisis de semiconductores", ultimas=60)
    assert parecido >= 0.6 and fila["run_id"] == "viejo"


def test_angulo_repetido_exige_mismo_indicador(tmp_path):
    m = Memoria(tmp_path)
    m.registrar(run_id="1", tema="Inflación en Argentina", indicador="FP.CPI.TOTL.ZG")
    assert m.angulo_repetido("La inflación argentina hoy", "FP.CPI.TOTL.ZG") is not None
    assert m.angulo_repetido("La inflación argentina hoy", "NY.GDP.MKTP.KD.ZG") is None


def test_pipeline_bloquea_tema_repetido_antes_del_guion(cfg):
    Memoria(cfg.dir_estado).registrar(run_id="1", tema="La crisis de los semiconductores", titulo="Chips")
    p = Pipeline(cfg)
    with pytest.raises(ErrorContenido, match="demasiado parecido"):
        p.tendencia(Registro(run_id="r", opciones={"tema": "Crisis de semiconductores en 2026"}))
    assert p.tendencia(Registro(run_id="r", opciones={"tema": "Crisis de semiconductores en 2026",
                                                     "permitir_repetido": True}))["tendencia"]


# --- rama huérfana ------------------------------------------------------------------


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repos(tmp_path):
    """Un remoto bare con main y dos clones (dos runs de CI que compiten)."""
    remoto = tmp_path / "remoto.git"
    _git("init", "--quiet", "--bare", "-b", "main", str(remoto), cwd=tmp_path)
    semilla = tmp_path / "semilla"
    _git("clone", "--quiet", str(remoto), str(semilla), cwd=tmp_path)
    (semilla / "README.md").write_text("main\n")
    _git("add", ".", cwd=semilla)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "main", cwd=semilla)
    _git("push", "--quiet", "origin", "main", cwd=semilla)
    clones = []
    for n in ("a", "b"):
        c = tmp_path / n
        _git("clone", "--quiet", str(remoto), str(c), cwd=tmp_path)
        clones.append(c)
    return remoto, clones


@requiere_git
def test_subir_crea_la_rama_huerfana_y_bajar_la_trae(repos, tmp_path):
    remoto, (a, b) = repos
    estado_a, estado_b = tmp_path / "ea", tmp_path / "eb"
    Memoria(estado_a).registrar(run_id="1", tema="uno")
    assert estado_git.subir(estado_a, a, "estado: 1") is True
    # Huérfana: no comparte historia con main y solo contiene el historial.
    archivos = _git("ls-tree", "--name-only", "refs/heads/estado-produccion", cwd=remoto).split()
    assert archivos == ["historial.jsonl"]
    assert _git("rev-list", "--count", "refs/heads/estado-produccion", cwd=remoto).strip() == "1"
    assert estado_git.bajar(estado_b, b) == 1
    assert [e["run_id"] for e in Memoria(estado_b).entradas()] == ["1"]
    assert estado_git.subir(estado_b, b, "sin cambios") is False


@requiere_git
def test_dos_runs_concurrentes_no_pierden_filas(repos, tmp_path):
    remoto, (a, b) = repos
    estado_a, estado_b = tmp_path / "ea", tmp_path / "eb"
    Memoria(estado_a).registrar(run_id="base", tema="base", fecha="2026-01-01")
    estado_git.subir(estado_a, a, "base")
    estado_git.bajar(estado_b, b)
    # Los dos runs publican a la vez a partir del mismo estado.
    Memoria(estado_a).registrar(run_id="a1", tema="a", fecha="2026-01-02")
    Memoria(estado_b).registrar(run_id="b1", tema="b", fecha="2026-01-03")
    assert estado_git.subir(estado_a, a, "a1", dormir=lambda s: None)
    assert estado_git.subir(estado_b, b, "b1", dormir=lambda s: None)
    final = _git("show", "refs/heads/estado-produccion:historial.jsonl", cwd=remoto)
    assert len([linea for linea in final.splitlines() if linea]) == 3
    assert {e["run_id"] for e in leer_jsonl(estado_b / "historial.jsonl")} == {"base", "a1", "b1"}
