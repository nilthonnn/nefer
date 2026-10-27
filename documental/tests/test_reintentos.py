import pytest

from documental.errores import ErrorConfiguracion, ErrorTransitorio
from documental.reintentos import reintentar


def test_reintenta_hasta_exito():
    llamadas, esperas = [], []

    def f():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise ErrorTransitorio("pasajero")
        return "ok"

    assert reintentar(f, descripcion="x", dormir=esperas.append) == "ok"
    assert len(llamadas) == 3
    assert esperas[0] >= 2.0 and esperas[1] >= 4.0  # exponencial


def test_no_reintenta_errores_definitivos():
    llamadas = []

    def f():
        llamadas.append(1)
        raise ErrorConfiguracion("clave")

    with pytest.raises(ErrorConfiguracion):
        reintentar(f, descripcion="x", dormir=lambda s: None)
    assert len(llamadas) == 1


def test_agota_y_relanza():
    with pytest.raises(ErrorTransitorio):
        reintentar(lambda: (_ for _ in ()).throw(ErrorTransitorio("x")), descripcion="x", intentos=2, dormir=lambda s: None)
