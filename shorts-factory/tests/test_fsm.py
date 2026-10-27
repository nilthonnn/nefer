import pytest

from shortsfactory.core.fsm import ORDEN, Estado, MaquinaEstados, Politica, Registro, TransicionInvalida
from shortsfactory.errors import ErrorContenido, ErrorTransitorio


def _maquina(tmp_path, manejadores, **kw):
    esperas = []
    m = MaquinaEstados(tmp_path / "estado.json", manejadores, kw.get("politicas", {}), dormir=esperas.append)
    return m, esperas


def test_recorre_todas_las_etapas_en_orden(tmp_path):
    visitados = []
    manejadores = {e: (lambda r, e=e: visitados.append(e) or {e.value: True}) for e in ORDEN[:-1]}
    m, _ = _maquina(tmp_path, manejadores)
    r = m.ejecutar(Registro(run_id="x"))
    assert r.estado == Estado.COMPLETADO and visitados == ORDEN[:-1]
    assert MaquinaEstados.cargar(tmp_path / "estado.json").estado == Estado.COMPLETADO


def test_reintenta_transitorios(tmp_path):
    llamadas = []

    def voz(r):
        llamadas.append(1)
        if len(llamadas) < 3:
            raise ErrorTransitorio("503")
        return {"voz": "ok"}

    m, esperas = _maquina(tmp_path, {Estado.VOZ: voz}, politicas={Estado.VOZ: Politica(intentos=3, espera_inicial=1)})
    r = m.ejecutar(Registro(run_id="x"))
    assert r.estado == Estado.COMPLETADO and len(llamadas) == 3 and len(esperas) == 2
    assert esperas[1] >= 2  # exponencial
    assert [p.resultado for p in r.pasos if p.estado == Estado.VOZ] == ["reintento", "reintento", "ok"]


def test_falla_al_agotar_o_con_error_definitivo_y_reanuda(tmp_path):
    estado = {"romper": True}

    def guion(r):
        if estado["romper"]:
            raise ErrorContenido("guion malo")
        return {"guion": 1}

    m, _ = _maquina(tmp_path, {Estado.DATOS: lambda r: {"serie": [1, 2]}, Estado.GUION: guion})
    r = m.ejecutar(Registro(run_id="x"))
    assert r.estado == Estado.FALLIDO and r.estado_fallido == Estado.GUION and "guion malo" in r.error
    assert r.artefactos["serie"] == [1, 2]

    estado["romper"] = False
    r = m.ejecutar(m.reanudar(MaquinaEstados.cargar(tmp_path / "estado.json")))
    assert r.estado == Estado.COMPLETADO and r.artefactos == {"serie": [1, 2], "guion": 1} and not r.error


def test_transiciones_invalidas(tmp_path):
    m, _ = _maquina(tmp_path, {})
    r = Registro(run_id="x", estado=Estado.GUION)
    with pytest.raises(TransicionInvalida):
        m._mover(r, Estado.RENDER)
