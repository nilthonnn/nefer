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

    with TestClient(crear_app(ruta_indice=ruta)) as c:
        assert c.get("/salud").json()["fragmentos"] == 1
        respuesta = c.post("/search-report-rag",
                           json={"consulta_texto": "humo negro y marcha inestable"})
        assert respuesta.status_code == 200


# ------------------------------------------------------- motor ya montado

@pytest.fixture
def cliente(tmp_path):
    """Un motor de verdad sobre un indice de una sola orden."""
    indice = Indice()
    indice.agregar([INFORME])
    app = crear_app(m.Motor(indice), ruta_indice=tmp_path / "indice.json",
                    ruta_historial=tmp_path / "historial.json")
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------ cerrar el circulo

def test_registrar_una_falla_resuelta_la_deja_buscable(cliente):
    nuevo = {
        "resumen_falla": "El ventilador no gira y el motor sube de temperatura",
        "causa_raiz": "Correa del ventilador partida",
        "solucion_aplicada": "Se cambio la correa y se tenso a especificacion",
        "codigo_equipo": "GE074-01",
    }
    creado = cliente.post("/informes", json=nuevo)
    assert creado.status_code == 201
    assert creado.json()["codigo_ot"].startswith("OT-")

    # Sin reindexar nada, la consulta siguiente ya lo encuentra.
    respuesta = cliente.post(
        "/search-report-rag",
        json={"consulta_texto": "el ventilador no gira y sube la temperatura"})
    assert respuesta.status_code == 200
    assert "Correa" in respuesta.json()["causa_raiz_mas_probable"]


def test_un_informe_incompleto_se_rechaza_con_400_y_no_con_500(cliente):
    respuesta = cliente.post("/informes", json={
        "resumen_falla": "algo anda mal", "causa_raiz": "no se",
        "solucion_aplicada": "nada", "codigo_ot": "OT-1"})
    assert respuesta.status_code == 201        # esto si vale: hay las tres cosas

    repetido = cliente.post("/informes", json={
        "resumen_falla": "otra vez", "causa_raiz": "otra", "solucion_aplicada": "otra",
        "codigo_ot": "OT-1"})
    assert repetido.status_code == 400
    assert "ya esta" in repetido.json()["detail"]


def test_el_esquema_exige_falla_causa_y_solucion(cliente):
    assert cliente.post("/informes", json={
        "resumen_falla": "el mastil no sube"}).status_code == 422


# ------------------------------------------------------------ prediccion

def test_la_prediccion_de_un_equipo_sale_por_su_ruta(cliente):
    cuerpo = cliente.get("/prediccion/GE074-02").json()
    assert cuerpo["equipo"] == "GE074-02"
    assert "reincidencias" in cuerpo and "avisos" in cuerpo


def test_un_equipo_desconocido_lo_dice_en_vez_de_inventar(cliente):
    cuerpo = cliente.get("/prediccion/NO-EXISTE-01").json()
    assert cuerpo["eventos"] == 0
    assert any("No hay nada fechado" in a for a in cuerpo["avisos"])


def test_la_flota_se_consulta_sin_nombrar_equipo(cliente):
    cuerpo = cliente.get("/prediccion").json()
    assert "equipos" in cuerpo and "causas" in cuerpo


def test_salud_dice_tambien_que_aprendio(cliente):
    cuerpo = cliente.get("/salud").json()
    assert "clasificador" in cuerpo
    assert cuerpo["archivos"] >= 0


# ═══════════════ RCM y TPM por HTTP (fase 12) ═══════════════
#
# Son endpoints de LECTURA. Crear o aprobar un análisis RCM por HTTP
# exigiría autenticación y control de versiones, y FixMate no tiene ninguna
# de las dos: un endpoint de escritura sin eso deja que cualquiera en la red
# del taller reescriba el plan de mantenimiento sin dejar rastro.

def _app_con_rcm():
    from fastapi.testclient import TestClient

    from nefer.fixmate import api as _api, embeddings, indexado, ingesta
    from nefer.fixmate.activos import Activo
    from nefer.fixmate.anomalia import Anomalia
    from nefer.fixmate.decision import Decisiones, Respuestas
    from nefer.fixmate.indice import Indice
    from nefer.fixmate.motor import Motor
    from nefer.fixmate.rcm import Analisis, Consecuencia, Efecto

    a = Analisis(Activo("EX-220", "Excavadora", categoria="excavadora"))
    f = a.agregar_funcion("Refrigerar", "80-95 °C con carga continua")
    ff = a.agregar_falla(f.id, "Supera 95 °C")
    m = a.agregar_modo(ff.id, "Radiador obstruido",
                       codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR")
    m.efecto = Efecto(local="Sube la temperatura")
    m.consecuencias = (Consecuencia("produccion"),)
    d = Decisiones()
    d.registrar(m, Respuestas(detectable=True, viable=True))

    informe = {"codigo_ot": "OT-1", "codigo_equipo": "EX-220",
               "fecha": "2026-01-02", "resumen_falla": "radiador tapado",
               "causa_raiz": "Radiador obstruido por tierra",
               "solucion_aplicada": "Lavado"}
    idx = Indice(embeddings.EmbebedorLocal())
    idx.agregar(ingesta.de_historial({"informes": [informe]}, "h.json"))
    indexado.indexar(idx, indexado.de_analisis(a, d))
    indexado.indexar(idx, [indexado.de_anomalia(
        Anomalia("an-1", "EX-220", "Panal tapado con tierra",
                 codigo_catalogo="TER.SOBRECALENTAMIENTO.RADIADOR"))])
    return TestClient(_api.crear_app(Motor(idx)))


def test_get_rcm_lista_los_modos_con_su_estrategia():
    r = _app_con_rcm().get("/rcm").json()
    assert r["total"] == 1
    assert r["modos"][0]["estrategia"] == "cbm"
    assert r["modos"][0]["estrategia_rotulo"] == "Mantenimiento segun condicion"


def test_get_rcm_filtra_por_equipo():
    c = _app_con_rcm()
    assert c.get("/rcm", params={"equipo": "EX-220"}).json()["total"] == 1
    assert c.get("/rcm", params={"equipo": "CA-310"}).json()["total"] == 0


def test_get_rcm_modos_por_codigo_de_catalogo():
    # Es la llave que cose el diagnóstico con el análisis.
    r = _app_con_rcm().get("/rcm/modos/TER.SOBRECALENTAMIENTO.RADIADOR").json()
    assert r["total"] == 1
    r2 = _app_con_rcm().get("/rcm/modos/ADM.RESTRICCION.FILTRO").json()
    assert r2["total"] == 0


def test_get_tpm_anomalias_filtra_abiertas_por_defecto():
    r = _app_con_rcm().get("/tpm/anomalias").json()
    assert r["total"] == 1 and r["filtro"] == "abiertas"


def test_get_tablero_no_inventa_mttr_ni_disponibilidad():
    r = _app_con_rcm().get("/tablero").json()
    assert r["mttr_horas"] is None and r["disponibilidad"] is None
    assert "no cuanto duro la reparacion" in r["nota"]


def test_el_diagnostico_devuelve_el_contexto_rcm():
    r = _app_con_rcm().post("/search-report-rag",
                            json={"consulta_texto": "radiador tapado con tierra"})
    assert r.status_code == 200
    assert any(x["origen"] == "analisis RCM" for x in r.json()["contexto_rcm"])


def test_el_contexto_rcm_esta_aunque_este_vacio():
    # El campo está y dice que no hay, en vez de faltar.
    from fastapi.testclient import TestClient

    from nefer.fixmate import api as _api, embeddings, ingesta
    from nefer.fixmate.indice import Indice
    from nefer.fixmate.motor import Motor

    idx = Indice(embeddings.EmbebedorLocal())
    idx.agregar(ingesta.de_historial({"informes": [
        {"codigo_ot": "OT-1", "resumen_falla": "radiador tapado",
         "causa_raiz": "Radiador obstruido", "solucion_aplicada": "Lavado"}]},
        "h.json"))
    r = TestClient(_api.crear_app(Motor(idx))).post(
        "/search-report-rag", json={"consulta_texto": "radiador tapado"})
    assert r.json()["contexto_rcm"] == []


def test_el_informe_acepta_la_trazabilidad_rcm_sin_exigirla(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from nefer.fixmate import api as _api, embeddings
    from nefer.fixmate.indice import Indice
    from nefer.fixmate.motor import Motor

    historial = tmp_path / "h.json"
    monkeypatch.setenv("FIXMATE_HISTORIAL", str(historial))
    c = TestClient(_api.crear_app(Motor(Indice(embeddings.EmbebedorLocal()))))
    base = {"resumen_falla": "Se recalienta", "causa_raiz": "Radiador obstruido",
            "solucion_aplicada": "Lavado del panal"}
    assert c.post("/informes", json=base).status_code in (200, 201)
    conysn = {**base, "codigo_ot": "OT-X", "modo_falla_id": "F1.1.1",
              "anomalia_id": "an-1"}
    assert c.post("/informes", json=conysn).status_code in (200, 201)
