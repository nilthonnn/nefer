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


# --------------------------------------------- la consulta dictada por voz

@pytest.fixture
def cliente_con_voz(tmp_path):
    """Un motor de verdad y un transcriptor falso: aqui no se prueba OpenAI."""
    indice = Indice()
    indice.agregar([INFORME])
    app = crear_app(m.Motor(indice), ruta_indice=tmp_path / "indice.json",
                    ruta_historial=tmp_path / "historial.json",
                    transcriptor=lambda audio, pistas="": "humo negro y marcha inestable")
    with TestClient(app) as c:
        yield c


def test_una_nota_de_voz_se_diagnostica_igual_que_un_texto(cliente_con_voz):
    respuesta = cliente_con_voz.post(
        "/search-report-rag-audio",
        files={"audio": ("nota.m4a", b"audio de mentira", "audio/m4a")},
        data={"codigo_equipo": "GE074-02"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "Inyector" in cuerpo["causa_raiz_mas_probable"]
    # Lo primero que el tecnico tiene que poder leer es que se entendio.
    assert cuerpo["consulta_interpretada"] == "humo negro y marcha inestable"


def test_un_audio_que_no_se_pudo_transcribir_no_es_un_error_del_servidor(tmp_path):
    from nefer.fixmate.transcripcion import ErrorTranscripcion

    def falla(audio, pistas=""):
        raise ErrorTranscripcion("la transcripcion salio vacia")

    indice = Indice()
    indice.agregar([INFORME])
    with TestClient(crear_app(m.Motor(indice), ruta_indice=tmp_path / "i.json",
                              transcriptor=falla)) as c:
        respuesta = c.post("/search-report-rag-audio",
                           files={"audio": ("n.m4a", b"x", "audio/m4a")})
    assert respuesta.status_code == 422
    assert "vacia" in respuesta.json()["detail"]


# ------------------------------------------------------ cerrar el circulo

def test_registrar_una_falla_resuelta_la_deja_buscable(cliente_con_voz):
    nuevo = {
        "resumen_falla": "El ventilador no gira y el motor sube de temperatura",
        "causa_raiz": "Correa del ventilador partida",
        "solucion_aplicada": "Se cambio la correa y se tenso a especificacion",
        "codigo_equipo": "GE074-01",
    }
    creado = cliente_con_voz.post("/informes", json=nuevo)
    assert creado.status_code == 201
    assert creado.json()["codigo_ot"].startswith("OT-")

    # Sin reindexar nada, la consulta siguiente ya lo encuentra.
    respuesta = cliente_con_voz.post(
        "/search-report-rag",
        json={"consulta_texto": "el ventilador no gira y sube la temperatura"})
    assert respuesta.status_code == 200
    assert "Correa" in respuesta.json()["causa_raiz_mas_probable"]


def test_un_informe_incompleto_se_rechaza_con_400_y_no_con_500(cliente_con_voz):
    respuesta = cliente_con_voz.post("/informes", json={
        "resumen_falla": "algo anda mal", "causa_raiz": "no se",
        "solucion_aplicada": "nada", "codigo_ot": "OT-1"})
    assert respuesta.status_code == 201        # esto si vale: hay las tres cosas

    repetido = cliente_con_voz.post("/informes", json={
        "resumen_falla": "otra vez", "causa_raiz": "otra", "solucion_aplicada": "otra",
        "codigo_ot": "OT-1"})
    assert repetido.status_code == 400
    assert "ya esta" in repetido.json()["detail"]


def test_el_esquema_exige_falla_causa_y_solucion(cliente_con_voz):
    assert cliente_con_voz.post("/informes", json={
        "resumen_falla": "el mastil no sube"}).status_code == 422


# ------------------------------------------------------------ prediccion

def test_la_prediccion_de_un_equipo_sale_por_su_ruta(cliente_con_voz):
    cuerpo = cliente_con_voz.get("/prediccion/GE074-02").json()
    assert cuerpo["equipo"] == "GE074-02"
    assert "reincidencias" in cuerpo and "avisos" in cuerpo


def test_un_equipo_desconocido_lo_dice_en_vez_de_inventar(cliente_con_voz):
    cuerpo = cliente_con_voz.get("/prediccion/NO-EXISTE-01").json()
    assert cuerpo["eventos"] == 0
    assert any("No hay nada fechado" in a for a in cuerpo["avisos"])


def test_la_flota_se_consulta_sin_nombrar_equipo(cliente_con_voz):
    cuerpo = cliente_con_voz.get("/prediccion").json()
    assert "equipos" in cuerpo and "causas" in cuerpo


def test_salud_dice_tambien_que_aprendio(cliente_con_voz):
    cuerpo = cliente_con_voz.get("/salud").json()
    assert "clasificador" in cuerpo
    assert cuerpo["archivos"] >= 0
