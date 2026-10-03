"""La app de estados financieros para MYPE, conducida en un navegador de verdad.

Se prueban las cuentas, que es lo que no puede fallar: el ejemplo cuadra en
los dos ejercicios, cada régimen calcula su impuesto, el RUC se valida con su
dígito verificador y lo pegado desde Excel suma las subcuentas en su cuenta.
Y se prueba la pantalla: lo que se escribe aparece en los estados, sobrevive a
una recarga y la página entra en un teléfono sin desbordarse.

Se salta entera sin Playwright o sin Chromium.
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from navegador import HAY_CHROMIUM, opciones  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "eeff"

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def url():
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(APP))
    manejador.log_message = lambda *a, **k: None

    class Servidor(socketserver.TCPServer):
        allow_reuse_address = True

    servidor = Servidor(("127.0.0.1", 0), manejador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}/"
    servidor.shutdown()


@pytest.fixture(scope="module")
def navegador():
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        yield nav
        nav.close()


@pytest.fixture
def pg(navegador, url):
    contexto = navegador.new_context(viewport={"width": 390, "height": 844})
    pagina = contexto.new_page()
    errores = []
    pagina.on("pageerror", lambda e: errores.append(str(e)))
    pagina.on("dialog", lambda d: d.accept())
    pagina.goto(url)
    yield pagina
    assert not errores, errores
    contexto.close()


def calcular(pg, saldos: dict, empresa: dict | None = None, **ejercicio) -> dict:
    """Corre el cálculo de la app sobre un balance armado aquí.

    `saldos` va con signo: positivo deudor, negativo acreedor.
    """
    emp = {"regimen": "RMT", "actividad": "comercio", "trabajadores": 5}
    emp.update(empresa or {})
    ej = {"corte": "2026-12-31", "uit": 5500, "lp": 0, "pv": 0, "adiciones": 0,
          "deducciones": 0, "perdidas": 0, "pagos": 0}
    ej.update(ejercicio)
    ej["saldos"] = {c: ({"d": v, "a": 0} if v >= 0 else {"d": 0, "a": -v}) for c, v in saldos.items()}
    return pg.evaluate(
        """([j, e]) => { const r = EEFF.calcular(j, e);
             return {er: r.er, esf: r.esf, dif: r.diferencia, fuera: r.fuera,
                     imp: r.trib.impuesto, part: r.trib.participacion, renta: r.trib.renta,
                     categoria: r.trib.categoria, alertas: r.trib.alertas.map(a => a[1])}; }""",
        [ej, emp])


# --------------------------------------------------------------- el ejemplo

def test_el_ejemplo_cuadra_en_los_dos_ejercicios(pg):
    pg.click("#b-ejemplo")
    r = pg.evaluate("""() => { const E = EEFF.estado();
        return ['2025','2026'].map(a => { const r = EEFF.calcular(E.ejercicios[a], E.empresa);
          return {dif: r.diferencia, debe: r.debe, haber: r.haber, neta: r.er.neta, ir: r.er.ir,
                  est: r.er.estimado, destino: r.er.destino, activo: r.esf.activo, fuera: r.fuera}; }); }""")
    r25, r26 = r
    for x in r:
        assert abs(x["dif"]) < 0.01
        assert abs(x["debe"] - x["haber"]) < 0.01
        assert x["fuera"] == []

    # 2026: cuentas por función, sin cuenta 88: el IR se estima en el RMT.
    assert r26["destino"] and r26["est"]
    assert r26["ir"] == pytest.approx(7300)        # 10 % de 73,000
    assert r26["neta"] == pytest.approx(65700)
    assert r26["activo"] == pytest.approx(311850)

    # 2025: sólo naturaleza, con el IR ya registrado en la 88.
    assert not r25["destino"] and not r25["est"]
    assert r25["ir"] == pytest.approx(5450)
    assert r25["neta"] == pytest.approx(49050)

    # En pantalla: los dos años lado a lado y el aviso de que cuadra.
    pg.click("nav button[data-ir='situacion']")
    assert pg.is_visible("#rep-esf .aviso.bien")
    cab = pg.text_content("#rep-esf thead")
    assert "2026" in cab and "2025" in cab
    assert "311,850.00" in pg.text_content("#rep-esf tr[data-k='activo']")
    pg.click("nav button[data-ir='resultados']")
    assert "65,700.00" in pg.text_content("#rep-er tr[data-k='neta']")
    assert "49,050.00" in pg.text_content("#rep-er tr[data-k='neta']")


# ---------------------------------------------------------------- tributos

def test_rmt_cobra_diez_por_ciento_hasta_15_uit_y_29_5_el_exceso(pg):
    r = calcular(pg, {"10": 150000, "70": -200000, "69": 50000})
    assert r["er"]["uai"] == pytest.approx(150000)
    tramo = 15 * 5500
    assert r["imp"] == pytest.approx(tramo * 0.10 + (150000 - tramo) * 0.295)
    assert abs(r["dif"]) < 0.01, "el IR estimado entra como pasivo y el balance sigue cuadrando"


def test_regimen_general_con_participacion_de_trabajadores(pg):
    r = calcular(pg, {"10": 100000, "70": -100000},
                 {"regimen": "RG", "actividad": "comercio", "trabajadores": 25})
    assert r["part"] == pytest.approx(8000)              # comercio: 8 %
    assert r["imp"] == pytest.approx(92000 * 0.295)
    assert r["er"]["neta"] == pytest.approx(100000 - 8000 - 27140)
    assert r["esf"]["partEst"] == pytest.approx(8000)
    assert abs(r["dif"]) < 0.01


def test_sin_mas_de_20_trabajadores_no_hay_participacion(pg):
    r = calcular(pg, {"10": 100000, "70": -100000},
                 {"regimen": "RG", "actividad": "industria", "trabajadores": 20})
    assert r["part"] == 0


def test_rer_paga_uno_y_medio_por_ciento_de_los_ingresos(pg):
    r = calcular(pg, {"10": 600000, "70": -600000}, {"regimen": "RER"})
    assert r["imp"] == pytest.approx(9000)
    assert any("525,000" in a for a in r["alertas"]), "pasa el tope del RER y tiene que avisarlo"


def test_ajustes_tributarios_y_perdidas_compensables(pg):
    r = calcular(pg, {"10": 50000, "70": -50000}, adiciones=5000, deducciones=1000, perdidas=20000)
    assert r["renta"] == pytest.approx(34000)
    assert r["imp"] == pytest.approx(3400)


def test_con_perdida_no_hay_impuesto(pg):
    r = calcular(pg, {"10": -10000, "70": -20000, "69": 30000})
    assert r["er"]["uai"] == pytest.approx(-10000)
    assert r["imp"] == 0
    assert r["esf"]["obligCP"] == pytest.approx(10000), "caja en negativo es sobregiro: va al pasivo"


def test_categoria_mype_por_ventas_en_uit(pg):
    assert calcular(pg, {"70": -150 * 5500})["categoria"] == "Microempresa"
    assert calcular(pg, {"70": -151 * 5500})["categoria"] == "Pequeña empresa"


def test_gastos_por_naturaleza_se_reparten_con_el_porcentaje_de_ventas(pg):
    r = calcular(pg, {"10": 0, "70": -100000, "62": 30000, "63": 10000, "67": 2000}, pv=25)
    assert r["er"]["gVen"] == pytest.approx(10000)
    assert r["er"]["gAdm"] == pytest.approx(30000)
    assert r["er"]["gFin"] == pytest.approx(2000)


def test_cuentas_que_no_se_saldaron_se_senalan(pg):
    # Con 94/95 en uso, una 62 sin su 79 deja el balance descuadrado: hay que decir cuál.
    r = calcular(pg, {"10": 0, "70": -1000, "94": 1000, "62": 500, "42": -500})
    assert [f["cta"] for f in r["fuera"]] == ["62 a 79"]
    assert r["fuera"][0]["saldo"] == pytest.approx(500)
    assert abs(r["dif"]) > 1


# ------------------------------------------------------------ RUC y números

def test_ruc(pg):
    v = pg.evaluate("""() => ['20000000001','20000000002','2000000000','30000000001']
                         .map(r => EEFF.validarRuc(r).ok)""")
    assert v == [True, False, False, False]


def test_numeros_como_los_escriben(pg):
    casos = {"1,234.56": 1234.56, "1.234,56": 1234.56, "1234,5": 1234.5, "(500)": -500,
             "S/ 2,000": 2000, "1,000,000": 1000000, "1.000.000": 1000000, "-75.5": -75.5, "": 0}
    for texto, esperado in casos.items():
        assert pg.evaluate("t => EEFF.num(t)", texto) == pytest.approx(esperado), texto


def test_pegar_desde_excel_suma_subcuentas(pg):
    texto = ("Cuenta\tNombre\tDeudor\tAcreedor\n"
             "101\tCaja\t1,500.00\t\n"
             "1041\tBanco\t8,500.00\t0.00\n"
             "4011\tIGV\t\t1,200.00\n"
             "50\tCapital\t\t8,800.00\n"
             "TOTALES\t\t10,000.00\t10,000.00\n")
    pg.click("nav button[data-ir='datos']")
    pg.click("#m-pcge")
    pg.fill("#pegado", texto)
    pg.click("#b-importar")
    s = pg.evaluate("() => EEFF.estado().ejercicios[EEFF.estado().actual].saldos")
    assert s["10"] == {"d": 10000, "a": 0}
    assert s["40"] == {"d": 0, "a": 1200}
    assert s["50"] == {"d": 0, "a": 8800}
    assert "omitidas" in pg.text_content("#import-ayuda")
    assert "Cuadra" in pg.text_content("#cuadre")


# ----------------------------------------------------------------- pantalla

def test_ingreso_rapido_llega_a_los_estados_y_sobrevive_a_recargar(pg):
    pg.fill("#e-razon", "BODEGA DOÑA ROSA E.I.R.L.")
    pg.fill("#e-ruc", "20000000002")
    assert "verificador" in pg.text_content("#ruc-ayuda")
    pg.fill("#e-ruc", "20000000001")
    assert "válido" in pg.text_content("#ruc-ayuda")

    pg.click("nav button[data-ir='datos']")
    pg.click("#m-simple")
    pg.fill(".monto-simple[data-c='10']", "30000")
    pg.fill(".monto-simple[data-c='50']", "20000")
    pg.fill(".monto-simple[data-c='70']", "50,000.00")
    pg.fill(".monto-simple[data-c='69']", "40000")
    # Caja 30,000 = capital 20,000 + utilidad neta 9,000 + IR estimado por
    # pagar 1,000: el impuesto lo pone la app y con él el balance cuadra.
    assert "Cuadra" in pg.text_content("#cuadre")

    pg.click("nav button[data-ir='resultados']")
    assert "9,000.00" in pg.text_content("#rep-er tr[data-k='neta']")
    assert "BODEGA DOÑA ROSA" in pg.text_content("#rep-er .membrete")

    pg.wait_for_timeout(400)
    pg.reload()
    pg.click("nav button[data-ir='resultados']")
    assert "9,000.00" in pg.text_content("#rep-er tr[data-k='neta']")
    assert pg.input_value("#e-razon") == "BODEGA DOÑA ROSA E.I.R.L."


def test_cabe_en_un_telefono_sin_desbordarse(pg):
    pg.click("#b-ejemplo")
    for vista in ("empresa", "datos", "resultados", "situacion", "tributos"):
        pg.click(f"nav button[data-ir='{vista}']")
        ancho = pg.evaluate("() => document.documentElement.scrollWidth")
        assert ancho <= 390, f"{vista}: la página mide {ancho}px de ancho"


def test_al_imprimir_salen_los_estados_y_no_los_formularios(pg):
    pg.click("#b-ejemplo")
    pg.emulate_media(media="print")
    assert pg.is_visible("#rep-er") and pg.is_visible("#rep-esf") and pg.is_visible("#rep-ind")
    assert not pg.is_visible("#e-razon")
    assert not pg.is_visible("#b-imprimir")
    assert pg.is_visible("#rep-esf .firmas")


def test_exporta_csv_con_los_dos_estados(pg):
    pg.click("#b-ejemplo")
    with pg.expect_download() as bajada:
        pg.click("#b-csv")
    texto = Path(bajada.value.path()).read_text(encoding="utf-8-sig")
    assert "ESTADO DE RESULTADOS,2026,2025" in texto
    assert "Total activo,311850.00" in texto
    assert "Resultado neto del ejercicio,65700.00,49050.00" in texto


# ------------------------------------------- lo que ahorra tiempo (Musk, paso 4 y 5)

BALANCE_10_COLUMNAS = [
    ["BALANCE DE COMPROBACIÓN AL 31/12/2026"],
    ["Cuenta", "Denominación", "Sumas Debe", "Sumas Haber", "Saldos Deudor", "Saldos Acreedor",
     "Inventario Activo", "Inventario Pasivo", "Resultados Pérdidas", "Resultados Ganancias"],
    ["10", "EFECTIVO", 50000, 20000, 30000, None, 30000, None, None, None],
    ["101", "Caja", 10000, 5000, 5000, None, 5000, None, None, None],
    ["1041", "Banco", 40000, 15000, 25000, None, 25000, None, None, None],
    ["50", "CAPITAL", None, 20000, None, 20000, None, 20000, None, None],
    ["70", "VENTAS", None, 50000, None, 50000, None, None, None, 50000],
    ["69", "COSTO DE VENTAS", 40000, None, 40000, None, None, None, 40000, None],
    ["", "TOTALES", 130000, 130000, 70000, 70000, None, None, None, None],
]


def test_formato_de_diez_columnas_toma_los_saldos_y_no_duplica_subcuentas(pg):
    texto = "\n".join("\t".join("" if v is None else str(v) for v in fila) for fila in BALANCE_10_COLUMNAS)
    r = pg.evaluate("t => EEFF.importar(t)", texto)
    s = pg.evaluate("() => EEFF.estado().ejercicios[EEFF.estado().actual].saldos")
    # La 10 viene como resumen de la 101 y la 1041: cuenta sólo una vez.
    assert s["10"] == {"d": 30000, "a": 0}
    assert s["50"] == {"d": 0, "a": 20000}
    assert s["69"] == {"d": 40000, "a": 0}
    assert r["cuentas"] == 4


def test_sube_el_excel_del_contador_desde_el_arranque(pg, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Balance"
    for fila in BALANCE_10_COLUMNAS:
        hoja.append(fila)
    archivo = tmp_path / "balance-2026.xlsx"
    libro.save(archivo)

    assert pg.is_visible("#inicio"), "sin datos, lo primero que se ve es cómo empezar"
    with pg.expect_file_chooser() as elegido:
        pg.click("label[for='f-archivo-inicio']")
    elegido.value.set_files(str(archivo))
    pg.wait_for_selector("section[data-vista='resultados']:not([hidden])", timeout=5000)

    assert "9,000.00" in pg.text_content("#rep-er tr[data-k='neta']")   # 10,000 − IR 10 %
    assert "Cuadra" in pg.text_content("#cuadre")
    pg.click("nav button[data-ir='empresa']")
    assert not pg.is_visible("#inicio"), "con datos, el arranque estorba"


def test_el_informe_se_escribe_solo(pg):
    pg.click("#b-ejemplo")
    pg.click("nav button[data-ir='informe']")
    texto = pg.text_content("#rep-informe")
    assert "vendió S/ 606,000.00" in texto
    assert "22.4 % más que en 2025" in texto
    assert "Ganó S/ 65,700.00" in texto
    assert "Separe S/ 1,240.00" in texto         # IR 7,300 − pagos a cuenta 6,060
    assert "Qué hacer" in texto

    wa = pg.get_attribute("#b-whatsapp", "href")
    assert wa.startswith("https://wa.me/?text=") and "606%2C000.00" in wa

    ia = pg.input_value("#prompt-ia")
    assert "Ventas netas (ingresos operacionales): 606,000.00 | 495,000.00" in ia
    assert "20000000001" not in ia and "COMERCIAL EJEMPLO" not in ia, "a la IA no van ni el RUC ni el nombre"


def test_el_informe_avisa_cuando_hay_perdida_y_poca_liquidez(pg):
    pg.evaluate("""() => { const E = EEFF.estado(); const j = E.ejercicios[E.actual];
        j.saldos = {"10": {d: 1000, a: 0}, "42": {d: 0, a: 9000}, "50": {d: 0, a: 2000},
                    "70": {d: 0, a: 10000}, "69": {d: 12000, a: 0}, "94": {d: 8000, a: 0}}; }""")
    pg.click("nav button[data-ir='datos']")
    pg.click("#m-pcge")  # cualquier acción que vuelva a pintar
    pg.click("nav button[data-ir='informe']")
    texto = pg.text_content("#rep-informe")
    assert "Perdió S/ 10,000.00" in texto
    assert "Liquidez en riesgo" in texto
    assert "Está perdiendo" in texto
