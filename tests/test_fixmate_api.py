"""La API HTTP: los codigos de estado que el tecnico acaba leyendo en pantalla.

La diferencia entre un 404 y un 500 no es de protocolo. "No hay antecedentes
de esa falla" le dice al tecnico que siga por su cuenta y registre el caso;
"error del servidor" le dice que la herramienta esta rota. Un `except
Exception` que envuelve al `HTTPException` convierte lo primero en lo segundo,
y por eso hay una prueba dedicada a ello.

Sin FastAPI instalado estas pruebas se saltan solas: la API es un extra.
"""

import pytest

fastapi = pytest.importorskip("fastapi", reason="la API de FixMate es un extra")
pytest.importorskip("httpx", reason="el cliente de pruebas de FastAPI usa httpx")

from fastapi.testclient import TestClient            # noqa: E402

from nefer.fixmate import motor as m                 # noqa: E402
from nefer.fixmate.api import crear_app              # noqa: E402
from nefer.fixmate.indice import Fragmento, Indice   # noqa: E402

INFORME = Fragmento(
    id="ot:OT-455", tipo="informe", fuente="historial.json",
    texto="ORDEN DE TRABAJO OT-455\nFalla: humo negro y marcha inestable.\n"
          "Causa: inyector con retorno excesivo. Apretar el prisionero a 30 N·m.",
    metadatos={"codigo_ot": "OT-455", "codigos_dtc": ["P0300"],
               "codigo_equipo": "GE074-02",
               "resumen_falla": "Humo negro y marcha inestable en frio.",
               "causa_raiz": "Inyector del cilindro 3 con retorno excesivo.",
               "solucion_aplicada": "Se reemplazo el inyector.",
               "pasos": ["Medir el retorno de inyectores."],
               "herramientas": ["Juego de probetas"], "torques": ["30 N·m"]})


@pytest.fixture
def cliente():
    indice = Indice()
    indice.agregar([INFORME])
    with TestClient(crear_app(m.Motor(indice))) as c:
        yield c


def test_salud_dice_con_que_indice_esta_trabajando(cliente):
    cuerpo = cliente.get("/salud").json()
    assert cuerpo["estado"] == "listo"
    assert cuerpo["fragmentos"] == 1
    assert cuerpo["redactor"] == "extractivo"


def test_una_consulta_devuelve_el_diagnostico_con_su_evidencia(cliente):
    respuesta = cliente.post("/search-report-rag", json={
        "consulta_texto": "humo negro y marcha inestable en frio",
        "codigo_dtc": "P0300"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "Inyector" in cuerpo["causa_raiz_mas_probable"]
    assert cuerpo["pasos_recomendados"]
    assert cuerpo["evidencia_historica"][0]["codigo_ot"] == "OT-455"
    assert cuerpo["torques"] == ["30 N·m"]
    assert cuerpo["confianza"] in ("alta", "media", "baja")


def test_sin_antecedentes_se_responde_404_y_no_500(cliente):
    respuesta = cliente.post("/search-report-rag", json={
        "consulta_texto": "tramites de aduana del contenedor en el puerto"})

    assert respuesta.status_code == 404
    assert "antecedentes" in respuesta.json()["detail"]


def test_un_fallo_interno_no_le_cuenta_al_cliente_donde_vive_el_servidor(cliente,
                                                                        monkeypatch):
    def reventar(consulta):
        raise RuntimeError("password=secreto host=/srv/interno/indice.json")

    monkeypatch.setattr(m.Motor, "consultar", lambda self, c: reventar(c))
    respuesta = cliente.post("/search-report-rag",
                             json={"consulta_texto": "humo negro"})

    assert respuesta.status_code == 500
    assert respuesta.json()["detail"] == "Error interno al resolver la consulta."
    assert "secreto" not in respuesta.text


def test_una_consulta_vacia_la_rechaza_el_esquema(cliente):
    assert cliente.post("/search-report-rag", json={"consulta_texto": ""}).status_code == 422
    assert cliente.post("/search-report-rag", json={
        "consulta_texto": "humo negro", "limite_resultados": 99}).status_code == 422


def test_sin_indice_la_api_arranca_igual_y_lo_dice(tmp_path):
    # Arrancar y morir deja al tecnico sin saber que pasa; arrancar y avisar
    # le dice exactamente que falta.
    with TestClient(crear_app(ruta_indice=tmp_path / "no-esta.json")) as c:
        assert c.get("/salud").json()["estado"] == "sin indice"
        respuesta = c.post("/search-report-rag", json={"consulta_texto": "humo negro"})
        assert respuesta.status_code == 503
        assert "indexar" in respuesta.json()["detail"]


def test_la_api_lee_el_indice_del_disco(tmp_path):
    indice = Indice()
    indice.agregar([INFORME])
    ruta = indice.guardar(tmp_path / "indice.json")

    with TestClient(crear_app(ruta_indice=ruta, con_llm=False)) as c:
        assert c.get("/salud").json()["fragmentos"] == 1
        respuesta = c.post("/search-report-rag",
                           json={"consulta_texto": "humo negro y marcha inestable"})
        assert respuesta.status_code == 200
