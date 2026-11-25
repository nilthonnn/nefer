"""Fotos de la inspección: cada foto en su casilla, dentro de la orden.

La misma idea que el despacho —la foto va bajo su rótulo— llevada a la
ventana de la orden: casillas del momento «inspección», carga directa en una
casilla, carga de varias con propuesta por el nombre del archivo, y las
fotos guardadas una por registro para que nada se pierda al cerrar la app.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def fotos(tmp_path_factory):
    d = tmp_path_factory.mktemp("fotos-insp")
    def jpg(nombre, color):
        r = d / nombre
        Image.new("RGB", (2400, 1800), color).save(r, "JPEG", quality=90)
        return r
    return {
        "patron": jpg("064_grupo_g04_vll_20261124-1031.jpg", (40, 60, 90)),
        "clave": jpg("IMG_horometro_final.jpg", (90, 60, 40)),
        "nada": jpg("IMG_20261124_103355.jpg", (60, 90, 40)),
        "directa": jpg("cualquiera.jpg", (120, 120, 120)),
        "otra": jpg("radiador_despues.jpg", (20, 120, 20)),
    }


def test_la_casilla_se_propone_por_el_nombre(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT")
    p = lambda n: pg.evaluate("n => MANT.modelo.proponerCasilla(n)", n)
    assert p("064_grupo_g04_vll_20261124-1031.jpg") == "g04"
    assert p("IMG_horometro.jpg") == "c06"
    assert p("placa_motor.jpg") == "c12", "la clave más larga gana a «placa»"
    assert p("placa.jpg") == "c05"
    assert p("foto_patio.jpg") is None, "sin claves cortas que adivinen de más"
    assert p("IMG_0001.jpg") is None
    n = pg.evaluate("() => MANT.modelo.nombreFoto('064', 'c06', new Date(2026, 10, 24, 10, 31))")
    assert n == "064_grupo_c06_horometro_20261124-1031.jpg"
    assert p(n) == "c06", "una foto tomada en la app se reconoce si vuelve a cargarse"
    nav.close()


def _orden(pg, servidor):
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION', '', '4017301000')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    return pg.evaluate("() => CAMPO.proyectos.actual().id")


def _datos(pg, pid):
    return pg.evaluate("id => CAMPO.almacen.leer(id).then(p => p.datos)", pid)


def _esperar_guardado(pg):
    pg.wait_for_timeout(300)
    pg.wait_for_function("() => /guardado/.test(document.querySelector('#m-o-guardado').textContent)")


def test_foto_directa_en_su_casilla_y_sobrevive_a_cerrar(pw, servidor, fotos):
    nav = _lanzar(pw)
    ctx = _contexto(nav, movil=True)
    pg = ctx.new_page()
    pid = _orden(pg, servidor)
    antes = pg.inner_text("#m-o-fotos-cuenta").lower()
    assert antes.startswith("faltan 25 de 25"), antes

    ctx.set_offline(True)
    pg.set_input_files("#m-o-foto-c06", str(fotos["directa"]))
    pg.wait_for_selector("[data-casilla=c06] img[data-foto]")
    assert pg.inner_text("#m-o-fotos-cuenta").lower().startswith("faltan 24 de 25")
    _esperar_guardado(pg)

    d = _datos(pg, pid)
    assert len(d["fotos"]) == 1
    f = d["fotos"][0]
    assert f["casilla"] == "c06" and f["propuesta"] is False
    assert f["nombre"].startswith("064_grupo_c06_horometro_")
    assert "archivo" not in f, "el proyecto guarda el id, no los bytes"
    reg = pg.evaluate("id => CAMPO.almacen.fotos.leer(id)", f["foto"])
    assert reg["proyecto"] == pid
    tam = pg.evaluate("id => CAMPO.almacen.fotos.leer(id).then(r => [r.archivo.size])", f["foto"])[0]
    assert 0 < tam < 1_500_000, "se reduce como en despacho"

    pg.close()
    pg = ctx.new_page()
    pg.goto(servidor)
    pg.wait_for_selector("#proy-recuperado", timeout=8000)
    pg.wait_for_function(
        "() => { const i = document.querySelector('[data-casilla=c06] img'); return i && i.naturalWidth > 0; }")
    nav.close()


def test_varias_fotos_se_proponen_y_el_tecnico_decide(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pg.on("dialog", lambda d: d.accept())
    pid = _orden(pg, servidor)
    pg.set_input_files("#m-o-fotos-varias", [str(fotos["patron"]), str(fotos["clave"]), str(fotos["nada"])])
    pg.wait_for_function("() => /3 fotos guardadas/.test(document.querySelector('#m-o-fotos-estado').textContent)")

    pg.evaluate("() => CAMPO.proyectos.volcar()")
    fotos_g = {f["nombre"]: f for f in _datos(pg, pid)["fotos"]}
    assert fotos_g["064_grupo_g04_vll_20261124-1031.jpg"]["casilla"] == "g04"
    assert fotos_g["064_grupo_g04_vll_20261124-1031.jpg"]["propuesta"] is True
    assert fotos_g["IMG_horometro_final.jpg"]["casilla"] == "c06"
    assert fotos_g["IMG_20261124_103355.jpg"]["casilla"] is None, "sin pista queda sin casilla"

    texto = pg.inner_text("#m-o-alertas")
    assert "sin confirmar" in texto and "sin casilla" in texto

    # La suelta se asigna a mano; las propuestas se confirman todas.
    i = [k for k, f in enumerate(_datos(pg, pid)["fotos"]) if f["casilla"] is None][0]
    pg.select_option(f"#m-o-mover-{i}", "c13")
    pg.click("[data-accion=fotos-confirmar]")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    l = _datos(pg, pid)["fotos"]
    assert sorted(f["casilla"] for f in l) == ["c06", "c13", "g04"]
    assert not any(f["propuesta"] for f in l)
    assert "sin confirmar" not in pg.inner_text("#m-o-alertas")

    # Una propuesta a una casilla ya llena no la pisa: queda suelta.
    pg.set_input_files("#m-o-fotos-varias", [str(fotos["clave"])])
    pg.wait_for_function("() => /1 foto guardada/.test(document.querySelector('#m-o-fotos-estado').textContent)")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    l = _datos(pg, pid)["fotos"]
    assert [f["casilla"] for f in l].count("c06") == 1 and [f["casilla"] for f in l].count(None) == 1

    # Quitar la borra de la tienda.
    quitada = [f for f in l if f["casilla"] is None][0]["foto"]
    k = [n for n, f in enumerate(l) if f["casilla"] is None][0]
    pg.click(f"[data-accion=foto-quitar][data-i='{k}']")
    pg.wait_for_timeout(300)
    assert pg.evaluate("id => CAMPO.almacen.fotos.leer(id)", quitada) is None
    nav.close()


def test_hallazgos_admite_varias_con_su_texto(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pid = _orden(pg, servidor)
    pg.set_input_files("#m-o-foto-c23", str(fotos["directa"]))
    pg.wait_for_selector("[data-casilla=c23] img")
    pg.set_input_files("#m-o-foto-c23", str(fotos["otra"]))
    pg.wait_for_function("() => document.querySelectorAll('[data-casilla=c23] img').length === 2")
    pg.fill("#m-o-fotos-1-texto", "Aislante quemado junto al escape")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    l = _datos(pg, pid)["fotos"]
    assert [f["casilla"] for f in l] == ["c23", "c23"]
    assert l[1]["texto"] == "Aislante quemado junto al escape"
    nav.close()


def test_las_fotos_viajan_en_el_paquete_y_se_van_al_eliminar(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pid = _orden(pg, servidor)
    pg.set_input_files("#m-o-foto-c01", str(fotos["directa"]))
    pg.wait_for_selector("[data-casilla=c01] img")
    pg.set_input_files("#m-o-foto-c06", str(fotos["clave"]))
    pg.wait_for_selector("[data-casilla=c06] img")
    pg.evaluate("() => CAMPO.proyectos.volcar()")

    r = pg.evaluate("""async (pid) => {
      const P = CAMPO.proyectos;
      const paquete = await P.empaquetar(pid);
      const nuevo = await P.importar(paquete.blob);
      await P.abrir(nuevo.id);
      await new Promise(r => setTimeout(r, 800));
      await P.volcar();
      const d = (await CAMPO.almacen.leer(nuevo.id)).datos;
      const regs = await CAMPO.almacen.fotos.deProyecto(nuevo.id);
      const copia = await P.duplicar(nuevo.id);
      const regsCopia = await CAMPO.almacen.fotos.deProyecto(copia.id);
      await P.borrar(pid);
      const quedan = await CAMPO.almacen.fotos.deProyecto(pid);
      return {casillas: d.fotos.map(f => f.casilla), sinBytes: d.fotos.every(f => !f.archivo && f.foto),
              regs: regs.length, tam: regs.every(x => x.archivo.size > 0),
              copia: regsCopia.length, idsDistintos: regsCopia.every(x => !regs.some(y => y.id === x.id)),
              quedan: quedan.length};
    }""", pid)
    assert r == {"casillas": ["c01", "c06"], "sinBytes": True, "regs": 2, "tam": True,
                 "copia": 2, "idsDistintos": True, "quedan": 0}
    nav.close()


def test_la_visita_tecnica_no_exige_fotos(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT")
    a = pg.evaluate("""() => {
      const M = MANT.modelo;
      const v = M.clasificar(M.mantenimiento('064'), 'VISITA', '');
      const i = M.clasificar(M.mantenimiento('064'), 'INSPECCION', '');
      const f = (m) => MANT.validaciones.validarMantenimiento(m, {}).filter(x => x.campo === 'fotos').length;
      return [f(v), f(i)];
    }""")
    assert a == [0, 1]
    nav.close()


def test_los_botones_principales_se_leen(pw, servidor, fotos):
    """Un botón principal dentro de una fila de botones tenía el texto del
    mismo color que el fondo: «Confirmar» y «Copiar» no se veían."""
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    _orden(pg, servidor)
    pg.set_input_files("#m-o-fotos-varias", [str(fotos["clave"])])
    pg.wait_for_selector("[data-accion=foto-confirmar]")
    for sel in ("[data-accion=foto-confirmar]", "[data-accion=wa-copiar]"):
        c = pg.eval_on_selector(sel, "n => { const s = getComputedStyle(n); return [s.color, s.backgroundColor]; }")
        assert c[0] != c[1], (sel, c)
    nav.close()


# --------------------------------------------------------------------------
# estado de cada componente, con el criterio del especialista a la vista
# --------------------------------------------------------------------------

def test_cada_casilla_trae_su_criterio(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT")
    r = pg.evaluate("""() => { const F = MANT.modelo.FORMATO;
      return F.fotos.map(c => [c[0], (F.criterios[c[0]] || []).length]); }""")
    assert all(n == 3 for _, n in r), r
    assert "entre las marcas L y H" in pg.evaluate("() => MANT.modelo.FORMATO.criterios.c13[0]")
    nav.close()


def test_falla_en_una_foto_pide_nota_aviso_y_sale_en_el_reporte(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pid = _orden(pg, servidor)
    pg.set_input_files("#m-o-foto-c17", str(fotos["directa"]))
    pg.wait_for_selector("[data-casilla=c17] img")
    pg.click("[data-casilla=c17] summary")
    assert "grietas transversales" in pg.inner_text("[data-casilla=c17] .m-criterio")

    pg.click("[data-estado-foto=c17][data-valor=FALLA]")
    assert "sin describir" in pg.inner_text("#m-o-alertas")
    pg.fill("#m-o-estados-c17-nota", "Faja del alternador con grietas transversales")
    texto = pg.inner_text("#m-o-alertas")
    assert "sin describir" not in texto
    assert "Falla en Fajas y ventilador" in texto and "crear aviso" in texto
    wa = pg.input_value("#m-o-wa")
    assert "• Falla · Fajas y ventilador: Faja del alternador con grietas transversales" in wa

    # Un estado sin foto que lo respalde queda anotado como dato.
    pg.click("[data-estado-foto=c13][data-valor=OK]")
    assert "Nivel de aceite (varilla): estado marcado sin foto" in pg.inner_text("#m-o-alertas")

    pg.evaluate("() => CAMPO.proyectos.volcar()")
    e = _datos(pg, pid)["estados"]
    assert e["c17"]["estado"] == "FALLA" and e["c17"]["hora"]
    assert e["c13"]["estado"] == "OK"
    # Tocar otra vez el marcado lo quita.
    pg.click("[data-estado-foto=c13][data-valor=OK]")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    assert "c13" not in _datos(pg, pid)["estados"]
    nav.close()
