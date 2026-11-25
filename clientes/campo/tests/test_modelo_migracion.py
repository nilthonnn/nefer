"""Almacén v2, esquema de proyectos y modelo de datos MANT.

Lo que se protege aquí es que un teléfono que ya tiene actas guardadas con la
app anterior —base IndexedDB versión 1, proyectos sin número de esquema— las
siga abriendo igual después de actualizar. Para eso se fabrica a mano, en el
mismo origen que la app, una base exactamente como la dejaba la versión 1, y
recién después se carga la app nueva encima.
"""

from __future__ import annotations

import base64
import io

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import App, _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


def _jpeg_b64(color) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), color).save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# La base tal como la creaba la versión 1 de la app: una sola tienda, con su
# índice, y registros sin `esquema`.
SEMBRAR_V1 = """async ({registros, fotos}) => {
  const blobs = fotos.map(b64 => {
    const bin = atob(b64), u = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return new Blob([u], {type: 'image/jpeg'});
  });
  const d = await new Promise((ok, mal) => {
    const p = indexedDB.open('campo', 1);
    p.onupgradeneeded = () => {
      const t = p.result.createObjectStore('proyectos', {keyPath: 'id'});
      t.createIndex('modificado', 'modificado');
    };
    p.onsuccess = () => ok(p.result);
    p.onerror = () => mal(p.error);
  });
  await new Promise((ok, mal) => {
    const tx = d.transaction('proyectos', 'readwrite');
    for (const r of registros) {
      const c = JSON.parse(JSON.stringify(r));
      for (const lista of ['fotos', 'antes']) {
        if (c.datos[lista]) c.datos[lista].forEach(f => { f.archivo = blobs[f.archivo]; });
      }
      tx.objectStore('proyectos').put(c);
    }
    tx.oncomplete = ok; tx.onerror = () => mal(tx.error);
  });
  d.close();
}"""

LEER_CRUDO = """async (id) => {
  const d = await new Promise((ok, mal) => {
    const p = indexedDB.open('campo');
    p.onsuccess = () => ok(p.result); p.onerror = () => mal(p.error);
  });
  const r = await new Promise(ok => {
    const g = d.transaction('proyectos').objectStore('proyectos').get(id);
    g.onsuccess = () => ok(g.result);
  });
  const out = {version: d.version, tiendas: Array.from(d.objectStoreNames).sort(),
               esquema: r ? (r.esquema === undefined ? null : r.esquema) : 'no existe',
               fotos: r ? (r.datos.fotos || []).length : 0};
  d.close();
  return out;
}"""

DESPACHO_V1 = {
    "id": "pviejo1", "nombre": "Despacho · GE-074 · acta vieja", "vista": "despacho",
    "estado": "borrador", "creado": 1767000000000, "modificado": 1767000000000,
    "datos": {
        "cat": "grupo_electrogeno",
        "campos": {"d-cliente": "MINERA DE PRUEBA S.A.C.", "d-equipo": "GE-074",
                   "d-modelo": "C100D6", "d-acta": "ACTA-0001",
                   "d-fecha": "2026-09-09", "d-horometro": "1548.7"},
        "extras": [], "accesorios": [],
        "casillas": [0, 1, None, None, None, None, None, None, None, None],
        "fotos": [
            {"nombre": "frontal.jpg", "archivo": 0, "fecha": None, "respaldo": 0},
            {"nombre": "posterior.jpg", "archivo": 1, "fecha": None, "respaldo": 0},
        ],
    },
}

RECEPCION_V1 = {
    "id": "pviejo2", "nombre": "Recepción · GE-074", "vista": "recepcion",
    "estado": "en proceso", "creado": 1767000001000, "modificado": 1767000001000,
    "datos": {"campos": {"r-acta": "ACTA-0002", "r-codigo_equipo": "GE-074",
                         "r-cliente": "MINERA DE PRUEBA S.A.C."}},
}


def _sembrar(pg, servidor, registros, sesion=None):
    """Carga una página vacía del mismo origen y deja ahí la base v1."""
    pg.route(servidor + "semilla.html",
             lambda r: r.fulfill(status=200, content_type="text/html",
                                 body="<!doctype html><title>semilla</title>"))
    pg.goto(servidor + "semilla.html")
    pg.evaluate(SEMBRAR_V1, {"registros": registros,
                             "fotos": [_jpeg_b64((90, 100, 120)), _jpeg_b64((120, 90, 80))]})
    if sesion:
        pg.evaluate("s => localStorage.setItem('campo.sesion', JSON.stringify(s))", sesion)


def _abrir_app(pg, servidor):
    pg.goto(servidor)
    pg.wait_for_function("() => window.CAMPO && window.MANT")
    pg.wait_for_timeout(600)


# --------------------------------------------------------------------------
# migración de la base y de los proyectos
# --------------------------------------------------------------------------

def test_una_base_v1_sube_a_v2_sin_tocar_las_actas(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True)
        pg = ctx.new_page()
        _sembrar(pg, servidor, [DESPACHO_V1, RECEPCION_V1])
        _abrir_app(pg, servidor)
        app = App(pg)

        lista = pg.evaluate("() => CAMPO.proyectos.listar()"
                            ".then(l => l.map(p => [p.id, p.esquema, p.vista]))")
        assert sorted(lista) == [["pviejo1", 2, "despacho"], ["pviejo2", 2, "recepcion"]]

        crudo = pg.evaluate(LEER_CRUDO, "pviejo1")
        assert crudo["version"] == 2
        assert crudo["tiendas"] == ["equipos", "fotos", "proyectos"]
        # Leer no escribe: el registro sigue como lo dejó la versión 1.
        assert crudo["esquema"] is None
        assert crudo["fotos"] == 2
        assert app.errores == []
        nav.close()


def test_el_despacho_viejo_se_abre_igual_y_al_guardar_queda_en_v2(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True)
        pg = ctx.new_page()
        pg.on("dialog", lambda d: d.accept())
        _sembrar(pg, servidor, [DESPACHO_V1])
        _abrir_app(pg, servidor)
        app = App(pg)

        pg.evaluate("() => CAMPO.proyectos.abrir('pviejo1')")
        app.despacho()
        pg.click("#d-datos summary")
        assert pg.input_value("#d-cliente") == "MINERA DE PRUEBA S.A.C."
        assert pg.input_value("#d-equipo") == "GE-074"
        assert pg.input_value("#d-horometro") == "1548.7"
        assert pg.input_value("#d-cat") == "grupo_electrogeno"
        assert app.llenas == 2, "las dos fotos de la versión 1 vuelven a su casilla"

        pg.evaluate("() => CAMPO.proyectos.guardar({})")
        pg.wait_for_timeout(300)
        crudo = pg.evaluate(LEER_CRUDO, "pviejo1")
        assert crudo["esquema"] == 2
        assert crudo["fotos"] == 2
        assert app.errores == []
        nav.close()


def test_la_recepcion_vieja_se_abre_igual(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True)
        pg = ctx.new_page()
        _sembrar(pg, servidor, [RECEPCION_V1])
        _abrir_app(pg, servidor)
        app = App(pg)
        pg.evaluate("() => CAMPO.proyectos.abrir('pviejo2')")
        pg.click("#tab-recepcion")
        pg.wait_for_timeout(300)
        assert pg.input_value("#r-acta") == "ACTA-0002"
        assert pg.input_value("#r-codigo_equipo") == "GE-074"
        assert app.errores == []
        nav.close()


def test_el_acta_a_medias_de_la_v1_se_recupera_sola(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True)
        pg = ctx.new_page()
        _sembrar(pg, servidor, [DESPACHO_V1], sesion={"id": "pviejo1", "vista": "despacho"})
        _abrir_app(pg, servidor)
        pg.wait_for_selector("#proy-recuperado", timeout=5000)
        assert "Se recuperó el acta que quedó a medias" in pg.inner_text("#proy-recuperado")
        assert App(pg).llenas == 2
        nav.close()


def test_un_acta_de_una_version_mas_nueva_no_se_abre_ni_se_pisa(servidor):
    futuro = dict(DESPACHO_V1, id="pfuturo", esquema=99)
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True)
        pg = ctx.new_page()
        _sembrar(pg, servidor, [futuro])
        _abrir_app(pg, servidor)
        error = pg.evaluate("() => CAMPO.proyectos.abrir('pfuturo')"
                            ".then(() => null, e => e.message)")
        assert error and "versión más nueva" in error
        assert pg.evaluate(LEER_CRUDO, "pfuturo")["esquema"] == 99
        nav.close()


def test_migrar_proyecto_es_puro(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _abrir_app(pg, servidor)
        r = pg.evaluate("""() => {
          const viejo = {id: 'x', vista: 'despacho', datos: {campos: {a: 1}}};
          const nuevo = CAMPO.migrarProyecto(viejo);
          return {original: viejo.esquema === undefined, esquema: nuevo.esquema,
                  mismosDatos: nuevo.datos === viejo.datos,
                  idempotente: CAMPO.migrarProyecto(nuevo) === nuevo,
                  esquemaApp: CAMPO.ESQUEMA,
                  nuevoMarcado: CAMPO.demasiadoNuevo({esquema: 3}),
                  actualNo: CAMPO.demasiadoNuevo({esquema: 2})};
        }""")
        assert r == {"original": True, "esquema": 2, "mismosDatos": True,
                     "idempotente": True, "esquemaApp": 2,
                     "nuevoMarcado": True, "actualNo": False}
        nav.close()


def test_un_paquete_nefer_sin_esquema_se_importa(servidor):
    """Los `.nefer` exportados por la v1 no llevan `esquema`."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _abrir_app(pg, servidor)
        r = pg.evaluate("""async () => {
          const pj = {formato: 'nefer-proyecto/1', nombre: 'Viejo', vista: 'recepcion',
                      estado: 'borrador', datos: {campos: {'r-acta': 'A-9'}}};
          const zip = CAMPO.armarZip([{nombre: 'proyecto.json',
                        datos: new TextEncoder().encode(JSON.stringify(pj))}]);
          const p = await CAMPO.proyectos.importar(zip);
          return [p.esquema, p.nombre];
        }""")
        assert r == [2, "Viejo"]
        nav.close()


def test_tiendas_de_equipos_y_fotos_y_persistencia(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        pg.add_init_script("""
          window.__persist = 0;
          if (navigator.storage) navigator.storage.persist =
            () => { window.__persist++; return Promise.resolve(true); };
        """)
        _abrir_app(pg, servidor)
        r = pg.evaluate("""async () => {
          const A = CAMPO.almacen;
          await A.equipos.guardar(MANT.modelo.equipo('064'));
          const e = await A.equipos.leer('064');
          const b = new Blob([new Uint8Array([1, 2, 3])], {type: 'image/png'});
          await A.fotos.guardar({id: 'f1', proyecto: 'p1', archivo: b});
          await A.fotos.guardar({id: 'f2', proyecto: 'p2', archivo: b});
          const deP1 = await A.fotos.deProyecto('p1');
          const tam = (await A.fotos.leer('f1')).archivo.size;
          await A.fotos.borrar('f1');
          return {tag: e.tag, deP1: deP1.map(f => f.id), tam,
                  borrada: (await A.fotos.leer('f1')) === undefined,
                  persist: window.__persist};
        }""")
        assert r == {"tag": "064", "deP1": ["f1"], "tam": 3, "borrada": True, "persist": 1}
        nav.close()


# --------------------------------------------------------------------------
# modelo de mantenimiento
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def modelo(servidor):
    """Una página abierta para evaluar el modelo, que no toca el DOM."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _abrir_app(pg, servidor)
        yield lambda js, arg=None: pg.evaluate(js, arg)
        nav.close()


def test_formas_vacias(modelo):
    r = modelo("""() => {
      const M = MANT.modelo, m = M.mantenimiento(' aaq29 ');
      return {tag: m.tag, eqTag: m.equipo.tag, conf: m.placaConfirmada,
              ops: m.ot.operaciones.map(o => [o.numero, o.especialidad]),
              cargas: m.informe.pruebas.map(p => p.carga),
              motor: Object.keys(m.informe.motor).length,
              repuestos: Object.keys(m.informe.repuestos),
              horometro: m.ot.horometroSalida, crearAviso: m.ot.crearAviso,
              items: Object.keys(M.checklist().items).length,
              pa: M.ITEMS_BATERIA.PLOMO_ACIDO, lm: M.ITEMS_BATERIA.LIBRE_MANTENIMIENTO,
              frec: M.FRECUENCIAS.map(f => f.horas)};
    }""")
    assert r["tag"] == "AAQ29" and r["eqTag"] == "AAQ29"
    assert r["conf"] is None, "la placa no se da por confirmada sola"
    assert r["ops"] == [["0010", "ELECTRICO"], ["0020", "MECANICO"]]
    assert r["cargas"] == ["inicial", 0, 25, 50, 100]
    assert r["motor"] == 12
    assert r["repuestos"][0] == "5.1" and r["repuestos"][-1] == "5.14"
    assert r["horometro"] is None and r["crearAviso"] is None
    assert r["items"] == 19
    assert r["pa"] == list(range(1, 11)) and r["lm"] == list(range(11, 20))
    assert r["frec"] == [250, 500, 1000, 2000]


def test_el_tag_es_texto(modelo):
    assert modelo("() => MANT.modelo.tag(64)") == "64"
    assert modelo("() => MANT.modelo.tag(' 064 ')") == "064"


@pytest.mark.parametrize("entrada,esperado", [
    ("380", 380), ("380,5", 380.5), ("1.548,7", 1548.7), ("1548.7", 1548.7),
    ("", None), ("  ", None), ("abc", None), (None, None), (0, 0),
])
def test_numero_lee_lo_que_teclea_el_tecnico(modelo, entrada, esperado):
    assert modelo("x => MANT.modelo.numero(x)", entrada) == esperado


def test_normalizar_completa_un_registro_incompleto_y_conserva_lo_desconocido(modelo):
    r = modelo("""() => {
      const m = MANT.modelo.normalizar.mantenimiento({
        tag: '064', campoFuturo: 'se queda',
        ot: {ot: '4017300492', operaciones: [{numero: '0010', horasHombre: '1,5'}],
             horometroSalida: '6.240,3'},
        informe: {pruebas: [{carga: 50, voltajeLL: 384}]},
        baterias: [{tipo: 'PLOMO_ACIDO', items: {1: 'OK', 2: 'quizas'}}]
      });
      return {futuro: m.campoFuturo, ot: m.ot.ot, horo: m.ot.horometroSalida,
              op: [m.ot.operaciones[0].especialidad, m.ot.operaciones[0].horasHombre],
              demoras: m.ot.demoras.length, firmaTec: m.ot.firmas.tecnico.nombre,
              cargas: m.informe.pruebas.map(p => [p.carga, p.voltajeLL]),
              items: [m.baterias[0].items[1], m.baterias[0].items[2], m.baterias[0].items[19]],
              personal: m.baterias[0].personal.length};
    }""")
    assert r["futuro"] == "se queda"
    assert r["ot"] == "4017300492" and r["horo"] == 6240.3
    assert r["op"] == ["ELECTRICO", "1,5"]  # HH se guarda como se tecleó; el aviso compara
    assert r["demoras"] == 0 and r["firmaTec"] == ""
    assert r["cargas"] == [["inicial", None], [0, None], [25, None], [50, 384], [100, None]]
    assert r["items"] == ["OK", None, None]
    assert r["personal"] == 3, "el papel tiene tres renglones de personal"


def test_un_informe_es_un_tag(modelo):
    """Las piezas no guardan TAG propio: el del proyecto manda en todas."""
    r = modelo("""() => {
      const M = MANT.modelo;
      const m = M.normalizar.mantenimiento({
        tag: '064', equipo: {tag: 'C450D6', grupo: {modelo: 'C100D6'}},
        baterias: [{tipo: 'LIBRE_MANTENIMIENTO'}]
      });
      const k = M.aKit(m);
      return {eq: m.equipo.tag, ot: k.ot.equipoTag, inf: k.informe.equipoTag,
              bat: k.baterias[0].equipoTag, kitEq: k.equipo.tag,
              piezasSinTag: [m.ot, m.informe, m.baterias[0]].every(x => !('equipoTag' in x)),
              firmaVacia: k.ot.firmas.tecnico === undefined};
    }""")
    assert r == {"eq": "064", "ot": "064", "inf": "064", "bat": "064", "kitEq": "064",
                 "piezasSinTag": True, "firmaVacia": True}


def test_los_textos_son_los_del_papel(modelo):
    r = modelo("""() => {
      const F = MANT.modelo.FORMATO;
      return {motor: F.informe.motor.length, gen: MANT.modelo.ITEMS_GENERADOR,
              rep: F.informe.repuestos.length, par: F.informe.parametros.map(p => p[1]),
              col: F.informe.columnas.map(c => c[1]),
              items: Object.keys(F.baterias.items).length,
              i14: F.baterias.items[14],
              desv: F.ot.desviaciones.map(d => d[1].length),
              servicio: F.informe.servicio.map(s => s[1])};
    }""")
    assert r["motor"] == 12 and r["rep"] == 14 and r["items"] == 19
    assert r["gen"] == ["4.1.1", "4.1.2", "4.1.3", "4.1.4", "4.1.5", "4.1.6",
                        "4.2.1", "4.2.2", "4.2.3", "4.2.4", "4.2.5", "4.2.6"]
    assert r["par"] == ["Voltaje AC (Vac)", "Corriente (Amp)", "Potencia (kW)",
                        "Potencia (kVA)", "Frecuencia (Hz)", "Volt. Batería (Vcc)",
                        "Presión de Aceite (PSI)", "T° Refrigerante (°C)", "Velocidad (RPM)"]
    assert r["col"] == ["VALOR INICIAL", "VACIO", "25%", "50%", "100%"]
    assert r["i14"].startswith("Verificación de estados de alerta del indicador")
    assert r["desv"] == [6, 2, 6, 14]
    assert r["servicio"][3] == "Mantenimiento Correctivo"


def test_el_informe_lleva_dos_firmas_por_lado(modelo):
    r = modelo("""() => {
      const M = MANT.modelo;
      const vacio = M.informe();
      // La forma del kit traía una sola firma por lado: se completa a dos.
      const viejo = M.normalizar.informe({firmas: {empresa: {nombre: 'TÉCNICO A'}}});
      const k = M.aKit({tag: '064', informe: viejo});
      return {u: vacio.firmas.empresa.length, c: vacio.firmas.cliente.length,
              viejo: viejo.firmas.empresa.map(f => f.nombre),
              kit: k.informe.firmas.empresa.nombre,
              motor: M.normalizar.informe({motor: {'3.1': 'OK', '3.2': 'bien'}}).motor};
    }""")
    assert r["u"] == 2 and r["c"] == 2
    assert r["viejo"] == ["TÉCNICO A", ""]
    assert r["kit"] == "TÉCNICO A"
    assert r["motor"]["3.1"] == "OK" and r["motor"]["3.2"] is None
