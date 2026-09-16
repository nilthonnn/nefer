"""Los dos motores tienen que dar lo mismo.

FixMate está escrito dos veces a propósito: en Python, donde están el Excel y
los PDF, y en JavaScript dentro de la app de campo, que es donde está el
mecánico y donde no hay señal. Dos implementaciones de la misma búsqueda se
separan solas —una corrección aquí que allá no se hace, un redondeo distinto—
y nadie lo nota hasta que el teléfono contesta otra cosa que la computadora.

Aquí se corren las mismas consultas sobre el mismo índice en los dos motores
y se comparan los rankings con sus puntajes, la causa, los pasos, los torques
y las probabilidades del clasificador. El motor de JavaScript se saca de la
propia app publicada, no de una copia: si alguien lo edita ahí, esto lo mide.

Sin `node` instalado la prueba se salta; en CI está.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "app" / "index.html"
EJEMPLOS = RAIZ / "ejemplos" / "fixmate"

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="hace falta node para el motor JS")

# Consultas de taller, no de laboratorio: como las escribiría el mecánico.
CONSULTAS = [
    ("gotea aceite por el cilindro del brazo toda la noche", None, None),
    ("sale humo negro y pierde fuerza en la subida", "P0300", None),
    ("no arranca en la mañana y el arranque gira lento", None, None),
    ("el mastil de la torre no sube", None, "TI09-04"),
    ("que apriete lleva el perno de la tapa del cilindro", None, None),
    ("manguera reventada en el brazo", None, None),
    ("el motor se calienta y para a las dos horas", None, None),
    # Una que no está en ningún antecedente: los dos tienen que negarse igual.
    ("tramites de aduana del contenedor en el puerto", None, None),
]


@pytest.fixture(scope="module")
def indice(tmp_path_factory):
    """Un índice de verdad, hecho con el corpus de ejemplo del repositorio."""
    from nefer.fixmate import Indice, Motor, actualizar

    indice = Indice()
    actualizar(indice, [EJEMPLOS])
    indice.medicion = Motor(indice).medicion()
    ruta = tmp_path_factory.mktemp("cruce") / "indice.json"
    indice.guardar(ruta)
    return ruta


def _respuesta_python(ruta_indice: Path) -> list[dict]:
    from nefer.fixmate import Indice, Motor
    from nefer.fixmate.motor import Consulta, SinEvidencia

    motor = Motor(Indice.cargar(ruta_indice))
    salida = []
    for texto, dtc, equipo in CONSULTAS:
        try:
            d = motor.consultar(Consulta(texto, codigo_dtc=dtc, codigo_equipo=equipo))
        except SinEvidencia:
            salida.append({"consulta": texto, "sin_evidencia": True})
            continue
        salida.append({
            "consulta": texto,
            "sin_evidencia": False,
            "evidencia": [[e.id, e.similitud] for e in d.evidencia_historica],
            "causa": d.causa_raiz_mas_probable,
            "pasos": d.pasos_recomendados,
            "herramientas": d.herramientas_y_repuestos,
            "torques": d.torques,
            "confianza": d.confianza,
            "causas_probables": [[c["causa"], c["probabilidad"], c["casos"]]
                                 for c in d.causas_probables],
            "avisos": len(d.avisos),
            "precauciones": [[c["texto"], c["origen"]] for c in d.precauciones],
        })
    return salida


def motor_js() -> str:
    """El motor tal como está en la app publicada, entre sus dos marcas."""
    html = APP.read_text(encoding="utf-8")
    m = re.search(r"/\* fixmate:motor:inicio.*?\*/(.*?)/\* fixmate:motor:fin \*/",
                  html, re.S)
    assert m, ("no se encontró el motor en la app: faltan las marcas "
               "fixmate:motor:inicio / fixmate:motor:fin")
    return m.group(1)


CONDUCTOR = """
%(motor)s

var fs = require("fs");
var indice = new Indice(JSON.parse(fs.readFileSync(process.argv[2], "utf8")));
var motor = new Motor(indice);
var casos = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
var salida = casos.map(function (caso) {
  var d;
  try {
    d = motor.consultar({ texto: caso[0], codigo_dtc: caso[1], codigo_equipo: caso[2] });
  } catch (e) {
    if (e && e.sinEvidencia) return { consulta: caso[0], sin_evidencia: true };
    throw e;
  }
  return {
    consulta: caso[0],
    sin_evidencia: false,
    evidencia: d.evidencia_historica.map(function (e) { return [e.id, e.similitud]; }),
    causa: d.causa_raiz_mas_probable,
    pasos: d.pasos_recomendados,
    herramientas: d.herramientas_y_repuestos,
    torques: d.torques,
    confianza: d.confianza,
    causas_probables: d.causas_probables.map(function (c) {
      return [c.causa, c.probabilidad, c.casos];
    }),
    avisos: d.avisos.length,
    precauciones: (d.precauciones || []).map(function (c) {
      return [c.texto, c.origen];
    })
  };
});
process.stdout.write(JSON.stringify(salida));
"""


def _respuesta_js(ruta_indice: Path, tmp_path: Path) -> list[dict]:
    guion = tmp_path / "cruce.js"
    guion.write_text(CONDUCTOR % {"motor": motor_js()}, encoding="utf-8")
    casos = tmp_path / "casos.json"
    casos.write_text(json.dumps(CONSULTAS), encoding="utf-8")

    proceso = subprocess.run([NODE, str(guion), str(ruta_indice), str(casos)],
                             capture_output=True, text=True, timeout=120)
    if proceso.returncode != 0:
        pytest.fail("el motor JS no corrió:\n" + proceso.stderr[-2000:])
    return json.loads(proceso.stdout)


@pytest.fixture(scope="module")
def cruce(indice, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("js")
    return list(zip(_respuesta_python(indice), _respuesta_js(indice, tmp)))


def test_la_app_lleva_el_motor_entre_sus_marcas():
    # Si alguien las quita, esta suite dejaría de comparar nada y no se vería.
    codigo = motor_js()
    assert "function fnv1a" in codigo
    assert "Indice.prototype.buscar" in codigo


@pytest.mark.parametrize("n", range(len(CONSULTAS)),
                         ids=[c[0][:28] for c in CONSULTAS])
def test_los_dos_motores_recuperan_lo_mismo(cruce, n):
    py, js = cruce[n]
    assert py["consulta"] == js["consulta"]
    assert py["sin_evidencia"] == js["sin_evidencia"], (
        "uno responde y el otro no para: " + py["consulta"])
    if py["sin_evidencia"]:
        return
    # Los puntajes, a los cuatro decimales con que se publican.
    assert js["evidencia"] == py["evidencia"], (
        f"el ranking se separó en «{py['consulta']}»")


@pytest.mark.parametrize("n", range(len(CONSULTAS)),
                         ids=[c[0][:28] for c in CONSULTAS])
def test_los_dos_motores_redactan_lo_mismo(cruce, n):
    py, js = cruce[n]
    if py["sin_evidencia"]:
        return
    for campo in ("causa", "pasos", "herramientas", "torques", "confianza",
                  "causas_probables", "avisos", "precauciones"):
        assert js[campo] == py[campo], (
            f"«{campo}» se separó en «{py['consulta']}»:\n"
            f"  python: {py[campo]!r}\n  js:     {js[campo]!r}")


def test_el_telefono_tambien_se_niega_cuando_no_hay_antecedente(cruce):
    # La última consulta es de aduanas: ninguno de los dos debe contestarla.
    py, js = cruce[-1]
    assert py["sin_evidencia"] and js["sin_evidencia"]


def test_el_hash_da_el_mismo_numero_en_los_dos_lenguajes(tmp_path):
    from nefer.fixmate.embeddings import fnv1a

    guion = tmp_path / "hash.js"
    guion.write_text(motor_js() + """
var palabras = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(palabras.map(function (p) {
  return fnv1a(p).toString();
})));
""", encoding="utf-8")
    palabras = ["fixmate:motor", "fixmate:hidráulico", "fixmate:^inye",
                "fixmate:P0300", "fixmate:niño"]
    proceso = subprocess.run([NODE, str(guion), json.dumps(palabras)],
                             capture_output=True, text=True, timeout=60)
    assert proceso.returncode == 0, proceso.stderr[-1000:]
    assert [int(x) for x in json.loads(proceso.stdout)] == [
        fnv1a(p.encode("utf-8")) for p in palabras]


# ------------------- lo que el teléfono cierra, la oficina lo indexa igual

INFORMES_DE_CAMPO = [
    {"codigo_ot": "OT-CAMPO-20260916-1",
     "fecha": "2026-09-16",
     "resumen_falla": "El ventilador no gira y el motor se calienta en dos horas",
     "causa_raiz": "Correa del ventilador partida por polea desalineada",
     "solucion_aplicada": "Se cambió la correa y se apretó el tensor a 30 N·m",
     "codigo_equipo": "GE074-03",
     "codigos_dtc": ["p0300"],
     "repuestos": ["Correa 8PK1230", "Tensor"]},
    # Sin nada opcional: el mínimo que la app deja registrar.
    {"codigo_ot": "OT-CAMPO-20260916-2",
     "fecha": "2026-09-16",
     "resumen_falla": "Fuga por el acople rápido del mástil",
     "causa_raiz": "Acople rajado",
     "solucion_aplicada": "Se reemplazó el acople",
     "codigo_equipo": "",
     "repuestos": []},
]


def test_el_informe_cerrado_en_faena_queda_igual_que_si_lo_hiciera_la_oficina(tmp_path):
    """El teléfono arma el fragmento; la oficina lo rehace al recibirlo.

    Si los dos no producen exactamente lo mismo —mismo texto, mismos
    metadatos, mismo vector— el índice cambiaría al sincronizar y las dos
    mitades dejarían de coincidir justo después de un cierre en campo, que es
    cuando nadie está mirando.
    """
    from nefer.fixmate import ingesta

    guion = tmp_path / "fragmentos.js"
    guion.write_text(motor_js() + """
var informes = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(informes.map(function (informe, n) {
  var f = fragmentoDeInforme(informe, "campo", n);
  return { id: f.id, texto: f.texto, tipo: f.tipo, fuente: f.fuente,
           metadatos: f.metadatos,
           vector: Array.prototype.map.call(f.vector, function (v) {
             return Math.round(v * 1e6) / 1e6;
           }) };
})));
""", encoding="utf-8")

    proceso = subprocess.run([NODE, str(guion), json.dumps(INFORMES_DE_CAMPO)],
                             capture_output=True, text=True, timeout=60)
    assert proceso.returncode == 0, proceso.stderr[-1500:]
    de_js = json.loads(proceso.stdout)

    for informe, js in zip(INFORMES_DE_CAMPO, de_js):
        py = ingesta.de_informe(informe, "campo", 0)
        assert js["id"] == py.id
        assert js["texto"] == py.texto, f"el texto difiere en {py.id}"
        assert js["tipo"] == py.tipo and js["fuente"] == py.fuente
        assert js["metadatos"] == {k: v for k, v in py.metadatos.items()
                                   if not k.startswith("_")}, \
            f"los metadatos difieren en {py.id}"
        esperado = [round(v, 6) for v in
                    __import__("nefer.fixmate.embeddings", fromlist=["x"])
                    .EmbebedorLocal().embeber([py.texto])[0]]
        assert js["vector"] == esperado, f"el vector difiere en {py.id}"


def test_el_telefono_y_la_oficina_encuentran_igual_lo_recien_cerrado(indice, tmp_path):
    """Registrado en el teléfono y recibido en la oficina: la misma respuesta."""
    from nefer.fixmate import Indice, Motor, cierre
    from nefer.fixmate.motor import Consulta

    informe = INFORMES_DE_CAMPO[0]
    consulta = "el ventilador no gira y sube la temperatura"

    # La oficina: lo recibe y consulta.
    oficina = Indice.cargar(indice)
    cierre.recibir({"pendientes": [informe]}, tmp_path / "historial.json", oficina)
    d = Motor(oficina).consultar(Consulta(consulta))

    # El teléfono: lo registra contra el mismo índice y consulta.
    guion = tmp_path / "telefono.js"
    guion.write_text(motor_js() + """
var fs = require("fs");
var indice = new Indice(JSON.parse(fs.readFileSync(process.argv[2], "utf8")));
indice.agregar(fragmentoDeInforme(JSON.parse(process.argv[3]), "historial.json", 0));
var d = new Motor(indice).consultar({ texto: process.argv[4] });
process.stdout.write(JSON.stringify({
  causa: d.causa_raiz_mas_probable,
  evidencia: d.evidencia_historica.map(function (e) { return [e.id, e.similitud]; })
}));
""", encoding="utf-8")
    proceso = subprocess.run(
        [NODE, str(guion), str(indice), json.dumps(informe), consulta],
        capture_output=True, text=True, timeout=60)
    assert proceso.returncode == 0, proceso.stderr[-1500:]
    js = json.loads(proceso.stdout)

    assert js["causa"] == d.causa_raiz_mas_probable
    assert js["evidencia"] == [[e.id, e.similitud] for e in d.evidencia_historica]
    assert "Correa" in js["causa"], "lo recién cerrado tiene que ser la respuesta"


# Palabras que un objeto de JavaScript trae puestas de fábrica. `{}` hereda
# "constructor", "toString", "valueOf" y "hasOwnProperty", así que una tabla
# indexada por token las daba por presentes sin que nadie las metiera: el
# teléfono las descartaba como palabras vacías y Python las conservaba, y la
# caché de posiciones devolvía una función donde esperaba un par de números.
HEREDADAS = ["constructor", "tostring", "valueof", "hasownproperty",
             "prototype", "__proto__"]


def test_el_tokenizador_no_hereda_palabras_del_lenguaje(tmp_path):
    """Los dos motores tienen que partir el mismo texto en los mismos tokens."""
    import subprocess

    guion = tmp_path / "tokens.js"
    guion.write_text(motor_js() + """
var fs = require("fs");
var palabras = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
console.log(JSON.stringify(palabras.map(function (p) {
  return [tokenizar(p), Array.prototype.slice.call(vector(p))];
})));
""", encoding="utf-8")
    entrada = tmp_path / "palabras.json"
    entrada.write_text(json.dumps(HEREDADAS), encoding="utf-8")

    crudo = subprocess.run([NODE, str(guion), str(entrada)],
                           check=True, capture_output=True, text=True).stdout
    del_telefono = json.loads(crudo)

    from nefer.fixmate import embeddings, texto as _texto

    embebedor = embeddings.EmbebedorLocal()
    for palabra, (tokens_js, vector_js) in zip(HEREDADAS, del_telefono):
        assert tokens_js == _texto.tokenizar(palabra), (
            f"«{palabra}» se parte distinto en el teléfono")
        vector_py = embebedor.embeber([palabra])[0]
        assert [round(v, 9) for v in vector_js] == [round(v, 9) for v in vector_py], (
            f"«{palabra}» da otro vector en el teléfono")


def test_si_hay_pasos_hay_precauciones_en_los_dos_motores(cruce):
    """La puerta de seguridad no es opcional, y no depende del idioma.

    Un diagnóstico que termina en «desmontar el inyector 3» le está diciendo
    a alguien que meta las manos en una máquina. Que el teléfono entregue el
    procedimiento con una precaución menos que la oficina sería la peor forma
    de que los dos motores se separen, porque no se vería hasta que pasara
    algo.
    """
    con_pasos = 0
    for py, js in cruce:
        if py["sin_evidencia"]:
            continue
        if py["pasos"]:
            assert py["precauciones"], f"«{py['consulta']}» da pasos sin precauciones"
            assert js["precauciones"] == py["precauciones"]
            # La de bloqueo va siempre, y va primera.
            assert "Bloquee" in py["precauciones"][0][0]
            con_pasos += 1
        else:
            assert py["precauciones"] == [] == js["precauciones"]
    assert con_pasos, "ninguna consulta dio pasos: la prueba no comprobó nada"


# --------------------------- los mismos papeles, leídos por los dos motores

def _pdf_crudo(objetos):
    salida = bytearray(b"%PDF-1.4\n")
    for n, objeto in enumerate(objetos, 1):
        salida += b"%d 0 obj\n" % n + objeto + b"\nendobj\n"
    salida += b"trailer << /Root 1 0 R >>\n%%EOF\n"
    return bytes(salida)


def _flujo_pdf(contenido, comprimido=True):
    import zlib
    extra = b""
    if comprimido:
        contenido = zlib.compress(contenido)
        extra = b" /Filter /FlateDecode"
    return (b"<< /Length %d%s >>\nstream\n" % (len(contenido), extra)
            + contenido + b"\nendstream")


def _pdf_de_manual(comprimido=True):
    contenido = (b"BT /F1 12 Tf 72 720 Td (PELIGRO: el acumulador conserva presion.) Tj\n"
                 b"0 -16 Td (Par de apriete de la tapa del cilindro: 210 N.m) Tj\n"
                 b"0 -16 Td (El codigo P0300 aparece por combustion fallida.) Tj ET")
    return _pdf_crudo([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        _flujo_pdf(contenido, comprimido)])


def _en_el_navegador(guion, b64):
    """Corre un trozo del motor en Chromium. El PDF necesita DOMParser y
    DecompressionStream, que node no trae y el teléfono sí."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    from navegador import HAY_CHROMIUM, opciones
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium")

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        try:
            pg = nav.new_page()
            pg.goto("about:blank")
            return pg.evaluate(
                "async ([motor, b64]) => {\n"
                "  const api = {};\n"
                "  new Function('api', motor + '\\n" + guion + "')(api);\n"
                "  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));\n"
                "  try { return await api.correr(bin.buffer); }\n"
                "  catch (e) { return 'ERROR: ' + e.message; }\n"
                "}", [motor_js(), b64])
        finally:
            nav.close()


@pytest.mark.parametrize("comprimido", [True, False],
                         ids=["FlateDecode", "sin comprimir"])
def test_el_pdf_da_el_mismo_texto_en_la_oficina_y_en_el_telefono(comprimido):
    """El lector de PDF está escrito dos veces, y dos lectores se separan solos.

    Es el formato en el que vienen los manuales OEM, así que si el teléfono
    lee otra cosa que la oficina, responde otro manual.
    """
    import base64

    from nefer.fixmate import pdf_texto

    datos = _pdf_de_manual(comprimido)
    del_telefono = _en_el_navegador(
        "api.correr = textoDePdf;", base64.b64encode(datos).decode())
    assert del_telefono == pdf_texto.texto_de(datos)
    assert "210 N.m" in del_telefono


def test_un_pdf_escaneado_no_se_carga_vacio_en_el_telefono():
    """Una foto de una página no es un manual. Cargarla y después contestar
    «no hay antecedente» sería mentir con más pasos."""
    import base64

    datos = _pdf_crudo([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        _flujo_pdf(b"q 612 0 0 792 0 0 cm /Im0 Do Q")])
    salida = _en_el_navegador("api.correr = textoDePdf;",
                              base64.b64encode(datos).decode())
    assert salida.startswith("ERROR:")
    assert "OCR" in salida


def test_el_word_da_el_mismo_texto_en_la_oficina_y_en_el_telefono(tmp_path):
    import base64
    import io
    import zipfile

    from nefer.fixmate import documentos

    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    doc = ('<?xml version="1.0"?>\n'
           f'<w:document xmlns:w="{W}"><w:body>'
           '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
           '<w:r><w:t>Sistema hidraulico</w:t></w:r></w:p>'
           '<w:p><w:r><w:t>PELIGRO: el acumulador conserva presion.</w:t></w:r></w:p>'
           '<w:p><w:r><w:t>Par de apriete de la tapa: 210 N.m</w:t></w:r></w:p>'
           '<w:tbl><w:tr>'
           '<w:tc><w:p><w:r><w:t>P0300</w:t></w:r></w:p></w:tc>'
           '<w:tc><w:p><w:r><w:t>Combustion fallida</w:t></w:r></w:p></w:tc>'
           '</w:tr></w:tbl>'
           '</w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", doc)
    crudo = buf.getvalue()
    (tmp_path / "manual.docx").write_bytes(crudo)

    del_telefono = _en_el_navegador(
        "api.correr = async (b) => textoDeDocx("
        "await contenidoZip(b, entradasZip(b)[\\'word/document.xml\\']));",
        base64.b64encode(crudo).decode())
    assert del_telefono == documentos.leer_docx(tmp_path / "manual.docx")
    # El título de Word sale como título Markdown: así lo trocea la ingesta.
    assert del_telefono.startswith("# Sistema hidraulico")


def test_el_telefono_mide_su_clasificador_igual_que_la_oficina(indice, tmp_path):
    """El porcentaje que publica tiene que ser el mismo, o no vale nada.

    Cuando el índice lo arma el propio teléfono —cargando el Excel ahí
    mismo— nadie lo midió antes. Si el teléfono no supiera medirse,
    publicaría una causa probable sin decir cuánto acierta, que es
    justamente lo que esta herramienta promete no hacer.
    """
    import subprocess

    from nefer.fixmate import Indice, Motor

    de_la_oficina = Motor(Indice.cargar(indice)).medicion()
    assert de_la_oficina, "el ejemplo tiene que dar para medir"

    guion = tmp_path / "medir.js"
    guion.write_text(motor_js() + """
var fs = require("fs");
var datos = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
delete datos.medicion;            // como si lo hubiera armado el teléfono
var m = new Clasificador(new Indice(datos)).evaluar();
process.stdout.write(JSON.stringify(m));
""", encoding="utf-8")
    del_telefono = json.loads(subprocess.run(
        [NODE, str(guion), str(indice)],
        check=True, capture_output=True, text=True).stdout)

    for campo in ("casos", "causas", "aciertos"):
        assert del_telefono[campo] == de_la_oficina[campo], campo
    assert round(del_telefono["precision"], 9) == round(de_la_oficina["precision"], 9)
    assert round(del_telefono["linea_base"], 9) == round(de_la_oficina["linea_base"], 9)
