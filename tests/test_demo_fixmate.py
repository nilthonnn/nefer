"""La demo tiene que correr, y tiene que enseñar lo que dice que enseña.

Una demo rota se descubre delante del cliente. Aqui se corre entera, con los
mismos comandos de verdad que ejecuta cuando alguien la lanza, y se comprueba
que cada parte muestre lo suyo: que el PDF y el Word se lean, que la segunda
indexacion no relea nada, que el diagnostico salga con su evidencia y que lo
registrado al cerrar responda enseguida.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _demo():
    ruta = RAIZ / "herramientas" / "demo-fixmate.py"
    spec = importlib.util.spec_from_file_location("demo_fixmate", ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["demo_fixmate"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def demo():
    return _demo()


@pytest.fixture(scope="module")
def taller(demo, tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("taller")
    demo.montar_taller(carpeta)
    return carpeta


def test_el_taller_de_mentira_trae_los_cuatro_formatos(taller):
    nombres = {a.name for a in taller.iterdir()}
    assert "historial-2026.xlsx" in nombres        # el historial, en Excel
    assert "manual-hidraulica.docx" in nombres     # un manual, en Word
    assert "manual-electrico.pdf" in nombres       # otro, en PDF
    assert "acta-GE074-01.xlsx" in nombres         # un acta de nefer


def test_el_pdf_que_arma_la_demo_es_un_pdf_de_verdad(taller):
    from nefer.fixmate import pdf_texto

    texto = pdf_texto.extraer(taller / "manual-electrico.pdf")
    assert "Par de apriete de bornes de bateria: 8 N.m" in texto


def test_la_demo_entera_corre_y_cuenta_lo_que_promete(demo, tmp_path, capsys):
    assert demo.main(["--dir", str(tmp_path)]) == 0
    salida = capsys.readouterr().out

    # 1. los formatos se leen
    assert "manual-hidraulica.docx" in salida
    assert "# Cilindros hidráulicos" in salida
    # 2. la segunda pasada no relee nada
    assert "sin cambios: 5 archivos" in salida
    assert "Clasificador de causas: entrenado" in salida
    # 3 y 4. el diagnostico, con su evidencia y su estadistica
    assert "CAUSA RAIZ MAS PROBABLE" in salida
    assert "Sello del vástago cortado" in salida
    assert "LO QUE DICE EL HISTORIAL COMPLETO" in salida
    # 5. la prediccion
    assert "PROXIMO SERVICIO" in salida
    assert "VENCIDA" in salida
    # 6. el cierre del circulo
    assert "Registrado OT-2026-0001" in salida
    assert "Correa del ventilador partida" in salida


def test_cada_demo_corre_por_separado(demo, tmp_path):
    for nombre in demo.DEMOS:
        assert demo.main([nombre, "--dir", str(tmp_path)]) == 0, nombre


def test_una_demo_que_no_existe_lo_dice(demo, tmp_path, capsys):
    assert demo.main(["magia", "--dir", str(tmp_path)]) == 1
    assert "No conozco" in capsys.readouterr().err


def test_la_demo_no_deja_basura_si_no_se_lo_piden(demo):
    import tempfile

    antes = set(Path(tempfile.gettempdir()).glob("fixmate-demo-*"))
    demo.main(["formatos"])
    assert set(Path(tempfile.gettempdir()).glob("fixmate-demo-*")) == antes


# ═══════════ los ejemplos de RCM y TPM (fase 12) ═══════════
#
# El riesgo que cubren estas pruebas es concreto: `docs/CASOS-RCM-TPM-FIXMATE.md`
# manda correr comandos contra estos archivos. Si se renombran o se rompen,
# el manual de operación deja de funcionar y nadie se entera hasta que un
# cliente lo intenta.

import json as _json

EJEMPLOS_RCM = RAIZ / "ejemplos" / "rcm-tpm"


@pytest.mark.parametrize("nombre", [
    "analisis-ex220.json", "pauta-ex220.json",
    "ronda-ex220-hallazgo.json", "ronda-ex220-firmada.json",
    "historial-ex220.json",
])
def test_los_ejemplos_que_la_documentacion_promete_existen_y_son_json(nombre):
    ruta = EJEMPLOS_RCM / nombre
    assert ruta.exists(), f"{nombre} no está: el manual manda correrlo"
    _json.loads(ruta.read_text(encoding="utf-8"))


def test_el_analisis_de_ejemplo_contesta_las_siete_preguntas():
    # Si no las contestara, `rcm analizar` saldría con código 2 y el primer
    # caso del manual de operación fallaría.
    from nefer.fixmate import cargador
    from nefer.fixmate.rcm import completitud

    a, d = cargador.analisis_y_decisiones(EJEMPLOS_RCM / "analisis-ex220.json")
    assert completitud(a, d.por_modo).completo is True


def test_el_analisis_de_ejemplo_saca_las_cuatro_estrategias_que_promete():
    # Cada modo está puesto para salir por un camino distinto del árbol. Es
    # lo que el LEEME de los ejemplos afirma, y lo que hace útil la demo.
    from nefer.fixmate import cargador

    _, d = cargador.analisis_y_decisiones(EJEMPLOS_RCM / "analisis-ex220.json")
    reparto = {k: n for k, n in d.reparto().items() if n}
    assert reparto == {"cbm": 1, "descarte": 1, "busqueda_fallas": 1,
                       "rediseno": 1}


def test_el_ejemplo_tiene_un_rediseno_obligatorio_por_seguridad():
    from nefer.fixmate import cargador

    _, d = cargador.analisis_y_decisiones(EJEMPLOS_RCM / "analisis-ex220.json")
    bloqueados = [x for _, x in d if x.bloqueado_por_seguridad]
    assert len(bloqueados) == 1
    assert bloqueados[0].estrategia == "rediseno"


def test_el_historial_de_ejemplo_escribe_la_misma_causa_de_tres_formas():
    # Es lo que hace demostrable que `contrastar()` cruza por código de
    # catálogo y no por texto libre.
    from nefer.fixmate import cargador, embeddings, fmeca, ingesta
    from nefer.fixmate.indice import Indice

    datos = _json.loads((EJEMPLOS_RCM / "historial-ex220.json")
                        .read_text(encoding="utf-8"))
    indice = Indice(embeddings.EmbebedorLocal())
    indice.agregar(ingesta.de_historial(datos, "historial-ex220.json"))

    a, _ = cargador.analisis_y_decisiones(EJEMPLOS_RCM / "analisis-ex220.json")
    c = fmeca.contrastar(a, indice)
    assert c.frecuencias["F1.1.1"] == 3        # tres escrituras, un modo
    assert c.sin_cubrir == (("ADM.RESTRICCION.FILTRO", 1),)
    assert c.sin_codificar == 1                # «se escuchó algo suelto»


def test_la_ronda_con_hallazgo_queda_incompleta_y_engancha_con_rcm():
    from nefer.fixmate import cargador
    from nefer.fixmate.anomalia import desde_ejecucion
    from nefer.fixmate.tpm import estado

    pauta = cargador.checklist(EJEMPLOS_RCM / "pauta-ex220.json")
    ronda = cargador.ejecucion(EJEMPLOS_RCM / "ronda-ex220-hallazgo.json")
    a, _ = cargador.analisis_y_decisiones(EJEMPLOS_RCM / "analisis-ex220.json")

    e = estado(ronda, pauta)
    assert e.sin_acceso == 1 and e.completa is False
    anomalias = desde_ejecucion(ronda, pauta, a)
    assert len(anomalias) == 1
    assert anomalias[0].modo_falla_id == "F1.1.1"


def test_la_ronda_firmada_se_detecta_como_tal():
    from nefer.fixmate import cargador
    from nefer.fixmate.tpm import estado

    pauta = cargador.checklist(EJEMPLOS_RCM / "pauta-ex220.json")
    ronda = cargador.ejecucion(EJEMPLOS_RCM / "ronda-ex220-firmada.json")
    e = estado(ronda, pauta)
    assert e.completa is True            # todos respondidos, ninguno sin ver
    assert e.sospechosa_de_firma is True # 5 s sobre un presupuesto de 31


def test_la_pauta_de_ejemplo_marca_lo_que_es_del_tecnico():
    from nefer.fixmate import cargador

    pauta = cargador.checklist(EJEMPLOS_RCM / "pauta-ex220.json")
    assert pauta.presupuesto_seg == 31
    del_tecnico = [p.id for p in pauta.puntos if not p.alcance_operador]
    assert len(del_tecnico) == 2         # freno y mangueras


def test_la_ronda_sin_enganche_queda_sin_enlazar_y_se_ve():
    # Es la otra mitad del puente TPM → RCM, y la que el manual de operación
    # usa en la prueba 5b. El punto 5 no declara modo y el catálogo no puede
    # codificar «un chirrido raro al girar la pluma».
    from nefer.fixmate import cargador
    from nefer.fixmate.anomalia import desde_ejecucion

    pauta = cargador.checklist(EJEMPLOS_RCM / "pauta-ex220.json")
    ronda = cargador.ejecucion(EJEMPLOS_RCM / "ronda-ex220-sin-enganche.json")
    a, _ = cargador.analisis_y_decisiones(EJEMPLOS_RCM / "analisis-ex220.json")

    anomalias = desde_ejecucion(ronda, pauta, a)
    assert len(anomalias) == 1
    assert anomalias[0].codigo_catalogo == ""
    assert anomalias[0].enlazada is False


def test_el_hallazgo_engancha_aunque_no_se_pase_el_analisis():
    # Porque el punto 1 de la pauta DECLARA `modo_falla_id`. Quien escribió
    # la pauta ya dijo qué modo vigila ese punto, y eso es mejor dato que
    # adivinarlo del texto del operador. El manual lo dice en la nota de 5b.
    from nefer.fixmate import cargador
    from nefer.fixmate.anomalia import desde_ejecucion

    pauta = cargador.checklist(EJEMPLOS_RCM / "pauta-ex220.json")
    ronda = cargador.ejecucion(EJEMPLOS_RCM / "ronda-ex220-hallazgo.json")
    anomalias = desde_ejecucion(ronda, pauta, None)   # sin análisis
    assert anomalias[0].modo_falla_id == "F1.1.1"


@pytest.mark.parametrize("comando, espera", [
    (["rcm", "analizar", "{e}/analisis-ex220.json"],
     "siete preguntas de JA1011 estan contestadas"),
    (["rcm", "tareas", "{e}/analisis-ex220.json"],
     "4 tareas · 0 listas · 4 en borrador"),
    (["tpm", "checklist", "{e}/pauta-ex220.json"], "presupuesto 31 s"),
])
def test_los_comandos_del_manual_de_operacion_imprimen_lo_que_promete(
        comando, espera, capsys):
    # El manual dice «tiene que salir X». Si cambia la salida y nadie
    # actualiza el manual, el cliente lo descubre antes que nosotros.
    from nefer import cli as cli_nefer

    argv = ["fixmate", *[a.format(e=EJEMPLOS_RCM) for a in comando]]
    assert cli_nefer.main(argv) == 0
    assert espera in capsys.readouterr().out
