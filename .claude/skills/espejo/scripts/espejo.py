#!/usr/bin/env python3
"""Lo generado de este repositorio: que esta atrasado y como ponerlo al dia.

Esto es la parte DETERMINISTA del trabajo —descubrir los generadores,
ordenarlos, correrlos, informar— y por eso es un script y no una lista de
comandos en la skill. Una lista escrita a mano se queda atras el dia que
alguien agrega un generador, que es exactamente el fallo que la skill existe
para evitar: seria la skill cometiendo su propio pecado.

    python3 .claude/skills/espejo/scripts/espejo.py            # que falta
    python3 .claude/skills/espejo/scripts/espejo.py --regenerar # ponerlo al dia

Codigos de salida, para poder encadenarlo:
    0  todo al dia / todo regenerado sin fallos
    1  hay algo atrasado (solo al comprobar)
    2  un generador reviento, o hay uno que no se puede comprobar
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
HERRAMIENTAS = RAIZ / "herramientas"

# El orden NO es alfabetico y no puede serlo: la piel sale de la app de
# diagnostico y la copian las dos pantallas, asi que si se regeneran antes
# que ella se llevan la piel vieja y hay que correrlo todo dos veces.
# Un generador que aparezca y no este aqui se corre AL FINAL y se avisa: es
# mejor un aviso que un orden adivinado.
ORDEN = ("piel.py", "espejo-catalogo.py", "espejo-ronda.py", "espejo-rcm.py",
         "espejo-armar.py")


def generadores() -> list[Path]:
    """Los que hay hoy, no los que habia cuando se escribio esto."""
    hallados = sorted(HERRAMIENTAS.glob("espejo-*.py"))
    piel = HERRAMIENTAS / "piel.py"
    if piel.exists():
        hallados.append(piel)

    def clave(ruta: Path) -> tuple[int, str]:
        try:
            return (ORDEN.index(ruta.name), "")
        except ValueError:
            return (len(ORDEN), ruta.name)      # los nuevos, al final

    return sorted(hallados, key=clave)


def _correr(ruta: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ruta), *args],
                          cwd=RAIZ, capture_output=True, text=True)


def comprobar(ruta: Path) -> tuple[str, str]:
    """(estado, detalle). Estado: «al dia», «atrasado» o «sin comprobar»."""
    salida = _correr(ruta, "--revisar")
    texto = (salida.stdout + salida.stderr).strip().splitlines()
    detalle = texto[-1] if texto else ""
    if "unrecognized arguments" in detalle or "--revisar" in detalle and salida.returncode == 2:
        # Un generador sin modo de comprobacion no se puede vigilar, y
        # callarlo lo deja fuera del radar para siempre.
        return "sin comprobar", "no acepta --revisar"
    if salida.returncode == 0:
        return "al dia", detalle
    return "atrasado", detalle


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--regenerar", action="store_true",
                   help="correr los generadores atrasados, en el orden correcto")
    args = p.parse_args(argv)

    encontrados = generadores()
    if not encontrados:
        print("No hay generadores en herramientas/. ¿Es este el repositorio?",
              file=sys.stderr)
        return 2

    nuevos = [g.name for g in encontrados if g.name not in ORDEN]
    estados: list[tuple[Path, str, str]] = []
    for ruta in encontrados:
        estado, detalle = comprobar(ruta)
        estados.append((ruta, estado, detalle))

    atrasados = [r for r, e, _ in estados if e == "atrasado"]
    ciegos = [r for r, e, _ in estados if e == "sin comprobar"]

    ancho = max(len(r.name) for r in encontrados)
    print(f"ESPEJO · {len(encontrados)} generador(es)\n")
    for ruta, estado, detalle in estados:
        marca = {"al dia": "✓ al día   ", "atrasado": "↻ atrasado ",
                 "sin comprobar": "? sin ver  "}[estado]
        print(f"  {marca} {ruta.name:{ancho}}  {detalle}")

    if nuevos:
        print(f"\n  ▲ sin orden declarado: {', '.join(nuevos)}. Se corren al "
              "final; si dependen de otro, declararlos en ORDEN.")
    if ciegos:
        print(f"\n  ▲ no se pueden comprobar: "
              f"{', '.join(r.name for r in ciegos)}. Lo que generan hay que "
              "mirarlo a mano o darles un --revisar.")

    if not args.regenerar:
        if atrasados:
            print(f"\n{len(atrasados)} atrasado(s). Para ponerlo al día:\n"
                  "  python3 .claude/skills/espejo/scripts/espejo.py --regenerar")
        return 1 if atrasados else (2 if ciegos else 0)

    if not atrasados:
        print("\nNada que regenerar.")
        return 2 if ciegos else 0

    print(f"\nRegenerando {len(atrasados)}, en orden de dependencia:")
    fallo = False
    for ruta in atrasados:
        salida = _correr(ruta)
        linea = (salida.stdout.strip().splitlines() or [""])[-1]
        if salida.returncode == 0:
            print(f"  ↻ {ruta.name:{ancho}}  {linea}")
        else:
            fallo = True
            print(f"  ✗ {ruta.name:{ancho}}  {salida.stderr.strip()[:200]}")
    return 2 if fallo else 0


if __name__ == "__main__":
    raise SystemExit(main())
