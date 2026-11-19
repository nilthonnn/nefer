"""Render por tramos: corte de la línea de tiempo y unión sin recodificar."""

from pathlib import Path

import pytest

from documental import entrada
from documental.modelos import Escena, Locucion, Tramo, Visual
from documental.multimedia.ffmpeg import verificar
from documental.pipeline import Opciones, cantidad_de_tramos, ensamblar, partir, preparar, renderizar_tramo

from conftest import guion_minimo, requiere_espeak, requiere_ffmpeg


def _tramos(duraciones: list[float], capitulos: list[str]) -> list[Tramo]:
    salida, t = [], 0.0
    for i, (d, c) in enumerate(zip(duraciones, capitulos)):
        e = Escena(id=f"e{i}", narracion="x", visual=Visual(tipo="titular", datos={}))
        salida.append(Tramo(escena=e, capitulo=c, inicio=t, duracion=d, locucion=Locucion(Path("a.wav"), d, [])))
        t += d
    return salida


def test_partir_cubre_todas_las_escenas_sin_huecos():
    tramos = _tramos([10] * 23, ["a"] * 23)
    for n in (1, 2, 3, 5, 23, 40):
        partes = partir(tramos, n)
        assert partes[0][0] == 0 and partes[-1][1] == len(tramos)
        assert all(a < b for a, b in partes)
        assert all(partes[k][1] == partes[k + 1][0] for k in range(len(partes) - 1))
        assert len(partes) == min(n, len(tramos))


def test_partir_prefiere_el_inicio_de_un_capitulo():
    # 10 escenas de 10 s; el capítulo cambia en la escena 6 (60 s), el ideal es 50 s.
    tramos = _tramos([10] * 10, ["a"] * 6 + ["b"] * 4)
    assert partir(tramos, 2) == [(0, 6), (6, 10)]


def test_partir_ignora_capitulos_lejanos_del_ideal():
    tramos = _tramos([10] * 10, ["a"] * 9 + ["b"])
    assert partir(tramos, 2) == [(0, 5), (5, 10)]


@pytest.mark.parametrize("total,maximo,esperado", [(60, 8, 1), (900, 8, 5), (900, 3, 3), (3600, 8, 8), (181, 8, 2)])
def test_cantidad_de_tramos(total, maximo, esperado):
    assert cantidad_de_tramos(total, maximo) == esperado


@requiere_ffmpeg
@requiere_espeak
def test_dos_tramos_dan_el_mismo_video_que_uno(tmp_path, cfg):
    datos = guion_minimo(fuentes=["F"])
    datos["capitulos"].append({"titulo": "Dos", "escenas": [
        {"narracion": "Una línea de tiempo.", "visual": {"tipo": "linea_tiempo", "datos": {"titulo": "T", "hitos": [{"anio": "1954", "texto": "Bell"}]}}},
        {"narracion": "Y una frase más para cerrar.", "visual": {"tipo": "titular", "datos": {"titulo": "Cierre"}}},
    ]})
    g = entrada.desde_dict(datos)
    from documental.voz.espeak import VozEspeak

    opciones = Opciones(usar_remotion=False, usar_stock=False)
    plan = preparar(g, cfg, VozEspeak(), opciones, partes=2)
    assert len(plan.partes) == 2
    # Cada tramo puede correr en otra máquina: aquí, en orden inverso a propósito.
    for k in reversed(range(2)):
        renderizar_tramo(g, cfg, plan, k, opciones)
    r = ensamblar(g, cfg, plan, opciones)
    m = verificar(r.video, video=True, audio=True)
    assert abs(m.duracion - plan.total) < 0.3
    assert (plan.carpeta / "subtitulos.srt").read_text(encoding="utf-8").strip()


@requiere_ffmpeg
@requiere_espeak
def test_ensamblar_sin_todos_los_tramos_falla_claro(tmp_path, cfg):
    g = entrada.desde_dict(guion_minimo(fuentes=["F"]))
    from documental.errores import ErrorMonetizacion
    from documental.voz.espeak import VozEspeak

    plan = preparar(g, cfg, VozEspeak(), Opciones(usar_remotion=False, usar_stock=False), partes=1)
    with pytest.raises(ErrorMonetizacion, match="faltan tramos"):
        ensamblar(g, cfg, plan, Opciones(usar_remotion=False, usar_stock=False))


@requiere_ffmpeg
@requiere_espeak
def test_cli_plan_tramo_ensamblar(tmp_path, cfg, monkeypatch, capsys):
    import json

    from documental import cli

    datos = guion_minimo(fuentes=["F"])
    ruta = tmp_path / "g.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(cli.m_config, "cargar", lambda *_: cfg)
    comunes = ["--previa", "--sin-remotion", "--sin-stock"]
    resumen = tmp_path / "plan.json"
    assert cli.main(["plan", str(ruta), "--segundos-por-parte", "1", "--partes-max", "2",
                     "--salida-json", str(resumen), *comunes]) == 0
    partes = json.loads(resumen.read_text(encoding="utf-8"))["partes"]
    assert partes == [0, 1]
    for k in partes:
        assert cli.main(["tramo", str(ruta), "--parte", str(k), *comunes]) == 0
    assert cli.main(["ensamblar", str(ruta), *comunes]) == 0
    assert "Video:" in capsys.readouterr().out
