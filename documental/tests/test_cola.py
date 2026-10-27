from pathlib import Path

from documental.cola import Cola
from documental.errores import ErrorEntrada, ErrorTransitorio


def test_flujo_completo(tmp_path):
    cola = Cola(tmp_path / "t")
    guion = tmp_path / "g.json"
    guion.write_text("{}")
    ids = [cola.agregar(guion) for _ in range(3)]
    resultados = iter([{"video": "v.mp4"}, ErrorEntrada("roto"), ErrorTransitorio("red")])

    def ejecutar(ruta: Path) -> dict:
        r = next(resultados)
        if isinstance(r, Exception):
            raise r
        return r

    assert cola.procesar(ejecutar, maximo=3) == 1
    estado = cola.estado()
    assert [t["id"] for t in estado["hecho"]] == [ids[0]]
    assert estado["fallido"][0]["error"].startswith("ErrorEntrada")
    # El transitorio vuelve a pendiente con su contador.
    assert estado["pendiente"][0]["id"] == ids[2] and estado["pendiente"][0]["reencolados"] == 1
    assert not estado["en_curso"]


def test_transitorio_acaba_en_fallido(tmp_path):
    cola = Cola(tmp_path / "t")
    (tmp_path / "g.json").write_text("{}")
    cola.agregar(tmp_path / "g.json")

    def falla(ruta):
        raise ErrorTransitorio("siempre")

    cola.procesar(falla)
    assert len(cola.estado()["fallido"]) == 1
    assert cola.reintentar_fallidos() == 1 and len(cola.estado()["pendiente"]) == 1


def test_tomar_es_exclusivo(tmp_path):
    cola = Cola(tmp_path / "t")
    (tmp_path / "g.json").write_text("{}")
    cola.agregar(tmp_path / "g.json")
    assert cola.tomar() is not None
    assert cola.tomar() is None
