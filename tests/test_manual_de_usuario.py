"""El manual de usuario tiene que seguir siendo verdad.

`MANUAL_DE_USUARIO.md` no es documentación de cortesía: describe lo que el
sistema hace **y lo que no hace**, y en varias secciones lo segundo es lo más
importante. Un jefe de mantenimiento lee «FixMate no calcula MTTR» y organiza
su gestión alrededor de eso; lee «no hay autenticación» y decide no exponer la
API.

Un manual así falla de un modo particular: **envejece en silencio**. Alguien
implementa el MTTR en seis meses, nadie se acuerda del manual, y el documento
pasa de ser honesto a ser falso sin que ninguna prueba se ponga roja. La
versión vieja sigue circulando en PDF por el correo del cliente.

Esto lo vigila por los dos lados:

1. **Lo que el manual promete, existe.** Los comandos que documenta están en el
   parser de verdad, y los archivos que cita están en el repositorio.
2. **Lo que el manual declara ausente, sigue ausente.** Cada vacío declarado
   tiene aquí una prueba que se pone roja el día que la función aparezca,
   diciendo qué sección hay que corregir.

No se comprueba la redacción ni el tono: eso es juicio y no se automatiza. Se
comprueba lo que se puede medir.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
MANUAL = RAIZ / "MANUAL_DE_USUARIO.md"


def texto() -> str:
    return MANUAL.read_text(encoding="utf-8")


def _parser_de_fixmate() -> argparse.ArgumentParser:
    """El parser real, armado como lo arma `nefer`."""
    from nefer.fixmate import cli

    raiz = argparse.ArgumentParser(prog="nefer")
    cli.agregar_subcomando(raiz.add_subparsers(dest="orden"))
    return raiz


def _subcomandos() -> dict[str, set[str]]:
    """{"": {ordenes de fixmate}, "rcm": {...}, "tpm": {...}}."""
    raiz = _parser_de_fixmate()
    accion_raiz = next(a for a in raiz._subparsers._group_actions)
    fixmate = accion_raiz.choices["fixmate"]
    ordenes = next(a for a in fixmate._subparsers._group_actions)
    mapa: dict[str, set[str]] = {"": set(ordenes.choices)}
    for nombre in ("rcm", "tpm"):
        sub = ordenes.choices[nombre]
        acciones = next(a for a in sub._subparsers._group_actions)
        mapa[nombre] = set(acciones.choices)
    return mapa


# ------------------------------------------- 1. lo que promete, existe

def test_el_manual_existe_en_la_raiz():
    """En la raíz y no en `docs/`: es el documento de entrada al sistema."""
    assert MANUAL.exists(), "falta MANUAL_DE_USUARIO.md en la raíz del proyecto"


def test_documenta_todos_los_comandos_que_hay():
    """Un comando sin documentar es un comando que nadie usa.

    Y al revés de como suele fallar esto: no se comprueba que el manual sea
    corto, sino que no se haya quedado atrás cuando alguien agregó una orden.
    """
    t = texto()
    mapa = _subcomandos()
    faltan = sorted(o for o in mapa[""] if not re.search(rf"\b{re.escape(o)}\b", t))
    assert not faltan, (
        f"el manual no menciona estas órdenes de `fixmate`: {faltan}. "
        "Agréguelas al mapa de comandos de la sección 2.4.")
    for grupo in ("rcm", "tpm"):
        faltan = sorted(a for a in mapa[grupo]
                        if not re.search(rf"{grupo}\s+{re.escape(a)}\b", t))
        assert not faltan, (
            f"el manual no documenta `fixmate {grupo} {{{', '.join(faltan)}}}`.")


def _comandos_ejecutables() -> str:
    """Sólo lo de dentro de los bloques de código.

    En la prosa el manual NOMBRA comandos para decir que no existen —«no hay
    `fixmate activos crear`»—, y eso es justamente lo que tiene que poder
    seguir diciendo. Un comando dentro de un bloque de código es una promesa:
    alguien lo va a copiar y pegar. Uno en la prosa puede ser una negación.
    """
    return "\n".join(re.findall(r"```(?:bash)?\n(.*?)```", texto(), re.S))


def test_no_promete_comandos_que_no_existen():
    """Lo contrario de la prueba anterior, y peor: ofrecer lo que no está."""
    bloques = _comandos_ejecutables()
    mapa = _subcomandos()
    citados = set(re.findall(r"fixmate\s+(?:-i\s+\S+\s+)?([a-z_]+)", bloques))
    # Lo que aparece tras «fixmate» sin ser una orden suya.
    ruido = {"rcm", "tpm", "app", "ronda", "armar", "indice"}
    inventados = sorted(c for c in citados - mapa[""] - ruido)
    assert not inventados, (
        f"el manual ofrece para copiar y pegar órdenes que el parser no tiene: "
        f"{inventados}")

    for grupo in ("rcm", "tpm"):
        citados = set(re.findall(
            rf"fixmate\s+(?:-i\s+\S+\s+)?{grupo}\s+([a-z_]+)", bloques))
        inventados = sorted(c for c in citados - mapa[grupo])
        assert not inventados, (
            f"el manual ofrece `{grupo} {inventados}`, que no existe")


def test_los_archivos_que_cita_estan_en_el_repositorio():
    """Un enlace roto en un manual hace dudar del resto del manual."""
    t = texto()
    rutas = {r for r in re.findall(r"[\w./-]+\.(?:py|json|md|html|xml|toml|css|js)", t)
             if "/" in r and not r.startswith("http")}
    faltan = sorted(r for r in rutas if not (RAIZ / r).exists())
    assert not faltan, f"el manual cita archivos que no existen: {faltan}"


def test_los_enlaces_internos_llevan_a_una_seccion():
    t = texto()
    titulos = set()
    for linea in t.split("\n"):
        if linea.startswith("#"):
            s = linea.lstrip("#").strip().lower()
            titulos.add(re.sub(r"[^\w\s\-áéíóúñ]", "", s).replace(" ", "-"))
    anclas = re.findall(r"\]\(#([^)]+)\)", t)
    assert anclas, "la tabla de contenido perdió sus enlaces"
    rotos = sorted(a for a in anclas if a not in titulos)
    assert not rotos, f"enlaces internos rotos: {rotos}"


# ------------------------------- 2. lo que declara ausente, sigue ausente

def test_mttr_y_disponibilidad_siguen_sin_calcularse():
    """La sección 4.3 dice que no se calculan, y por qué.

    Si alguien los implementa, el manual pasa a ser falso en el indicador que
    un jefe de mantenimiento usa para dimensionar dotación y para prometer
    disponibilidad en un contrato. Esta prueba se pone roja antes.
    """
    from nefer.fixmate import tablero

    t = tablero.TableroConfiabilidad()
    assert t.mttr_horas is None and t.disponibilidad is None, (
        "MTTR o disponibilidad ya se calculan: corrija la sección 4.3 del "
        "MANUAL_DE_USUARIO.md, que hoy dice que no existen.")
    assert "sin dato" in texto().lower()


def test_sigue_sin_haber_entidad_de_orden_de_trabajo():
    """La sección 3.2 documenta que no existe, y qué usar en su lugar."""
    assert not (RAIZ / "nefer" / "fixmate" / "ot.py").exists(), (
        "apareció un módulo de órdenes de trabajo: corrija la sección 3.2 del "
        "MANUAL_DE_USUARIO.md, que hoy dice que no hay entidad de OT.")
    acciones = _subcomandos()["tpm"]
    nuevas = acciones - {"checklist", "ejecutar", "pendientes"}
    assert not nuevas, (
        f"`fixmate tpm` tiene órdenes nuevas ({sorted(nuevas)}): si alguna "
        "cierra o asigna una anomalía, la sección 3.2 del manual dejó de ser "
        "cierta.")


def test_la_api_sigue_sin_autenticacion_y_el_manual_lo_advierte():
    """La sección 6.3 dice que no la exponga. Vale en los dos sentidos.

    Si alguien agrega autenticación, el manual queda innecesariamente alarmista
    y hay que suavizarlo; si nadie la agrega, la advertencia tiene que seguir
    ahí.
    """
    api = (RAIZ / "nefer" / "fixmate" / "api.py").read_text(encoding="utf-8")
    hay_auth = any(p in api for p in
                   ("HTTPBearer", "APIKeyHeader", "OAuth2", "HTTPBasic"))
    t = texto()
    if hay_auth:
        raise AssertionError(
            "la API ya trae autenticación: corrija la sección 6 del "
            "MANUAL_DE_USUARIO.md, que hoy dice que no la tiene.")
    assert "no tiene autenticación" in t, (
        "la advertencia de la sección 6.3 desapareció del manual")


def test_el_manual_declara_los_tres_perfiles_y_los_vacios():
    """Lo que hace a este manual distinto de una lista de funciones."""
    t = texto()
    for perfil in ("Administrador", "Técnico", "Operador"):
        assert perfil in t, f"el manual perdió el perfil «{perfil}»"
    # Los recuadros de advertencia son donde viven los vacíos declarados.
    assert t.count("> [!WARNING]") >= 5, (
        "el manual tiene menos advertencias que vacíos declarados: compruebe "
        "que no se hayan borrado al editarlo")
