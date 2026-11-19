"""Persistencia del historial del canal en una rama huérfana de git.

La caché de GitHub Actions caduca a los 7 días sin uso y puede desalojarse
antes: si se pierde, el canal "olvida" lo publicado y empieza a repetirse.
Por eso, tras cada publicación, ``historial.jsonl`` se versiona en la rama
``estado-produccion`` (huérfana: no comparte historia con ``main`` y no
ensucia sus PR). La caché queda como complemento (``cuota.json``).

- ``bajar``: trae el historial de la rama y lo FUSIONA con el local.
- ``subir``: fusiona local + remoto en un worktree temporal, hace commit y
  push. Si otro run empujó antes (push rechazado), vuelve a traer, fusiona
  y reintenta: ninguna fila se pierde porque la fusión es por ``run_id``.

Solo se toca ``historial.jsonl``; la rama no contiene nada más.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

from .errors import ShortsError
from .logs import obtener
from .memory import ARCHIVO, Memoria, escribir_jsonl, fusionar, leer_jsonl

log = obtener("estado")
RAMA = "estado-produccion"
AUTOR = ("shortsfactory-bot", "shortsfactory-bot@users.noreply.github.com")


class ErrorEstadoGit(ShortsError):
    pass


def _git(args: list[str], cwd: Path, comprobar: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=120)
    if comprobar and p.returncode != 0:
        raise ErrorEstadoGit(f"git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p


def _traer(repo: Path, remoto: str, rama: str) -> bool:
    """Actualiza ``<remoto>/<rama>``. False si la rama aún no existe."""
    p = _git(["fetch", "--quiet", remoto, f"+refs/heads/{rama}:refs/remotes/{remoto}/{rama}"], repo, comprobar=False)
    if p.returncode == 0:
        return True
    if "couldn't find remote ref" in p.stderr or "no se pudo encontrar" in p.stderr.lower():
        return False
    raise ErrorEstadoGit(f"git fetch {remoto} {rama}: {p.stderr.strip()}")


def _remoto(repo: Path, remoto: str, rama: str) -> list[dict]:
    p = _git(["show", f"refs/remotes/{remoto}/{rama}:{ARCHIVO}"], repo, comprobar=False)
    if p.returncode != 0:
        return []
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(p.stdout)
    try:
        return leer_jsonl(Path(f.name))
    finally:
        Path(f.name).unlink(missing_ok=True)


def bajar(dir_estado: Path, repo: Path, remoto: str = "origin", rama: str = RAMA) -> int:
    """Fusiona en el historial local el de la rama. Devuelve cuántas filas eran nuevas."""
    if not _traer(repo, remoto, rama):
        log.info("la rama %s aún no existe: se empieza con el historial local", rama)
        return 0
    nuevas = Memoria(dir_estado).fusionar_con(_remoto(repo, remoto, rama))
    log.info("historial: %d fila(s) nuevas desde %s", nuevas, rama)
    return nuevas


def subir(dir_estado: Path, repo: Path, mensaje: str, remoto: str = "origin", rama: str = RAMA,
          intentos: int = 4, dormir: Callable[[float], None] = time.sleep) -> bool:
    """Versiona el historial fusionado en la rama. False si no había nada nuevo."""
    local = leer_jsonl(dir_estado / ARCHIVO)
    if not local:
        log.info("historial vacío: nada que subir")
        return False
    for intento in range(1, intentos + 1):
        existe = _traer(repo, remoto, rama)
        remotas = _remoto(repo, remoto, rama) if existe else []
        unidas = fusionar(remotas, local)
        if existe and len(unidas) == len(remotas):
            log.info("la rama %s ya tiene todo el historial", rama)
            return False
        arbol = Path(tempfile.mkdtemp(prefix="estado-"))
        try:
            if existe:
                _git(["worktree", "add", "--detach", str(arbol), f"refs/remotes/{remoto}/{rama}"], repo)
            else:
                _git(["worktree", "add", "--detach", str(arbol)], repo)
                _git(["checkout", "--quiet", "--orphan", f"{rama}-nueva"], arbol)
                _git(["rm", "-rf", "--quiet", "."], arbol, comprobar=False)
                for sobrante in arbol.iterdir():
                    if sobrante.name != ".git":
                        shutil.rmtree(sobrante) if sobrante.is_dir() else sobrante.unlink()
            escribir_jsonl(arbol / ARCHIVO, unidas)
            _git(["add", ARCHIVO], arbol)
            _git(["-c", f"user.name={AUTOR[0]}", "-c", f"user.email={AUTOR[1]}", "commit", "--quiet", "-m", mensaje], arbol)
            p = _git(["push", "--quiet", remoto, f"HEAD:refs/heads/{rama}"], arbol, comprobar=False)
            if p.returncode == 0:
                log.info("historial versionado en %s (%d filas)", rama, len(unidas))
                escribir_jsonl(dir_estado / ARCHIVO, unidas)
                return True
            if intento == intentos:
                raise ErrorEstadoGit(f"git push a {rama} falló {intentos} veces: {p.stderr.strip()}")
            log.warning("push a %s rechazado (intento %d/%d): se vuelve a fusionar", rama, intento, intentos)
            dormir(2 ** intento)
        finally:
            _git(["worktree", "remove", "--force", str(arbol)], repo, comprobar=False)
            shutil.rmtree(arbol, ignore_errors=True)
    return False
