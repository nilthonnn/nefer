"""Equipos de referencia de CLAUDE.md, para las pruebas de los formatos UNIMAQ.

Viven aquí y no en la app: la app se publica, y las series de los equipos de
un cliente no tienen por qué viajar en ella. Lo que CLAUDE.md no dice se deja
vacío, como lo dejaría el técnico; no se inventa. La frecuencia sí se pone en
los Cummins «D6»: el sufijo es el de 60 Hz, y el informe en papel del C450D6
dice 60 Hz y 1800 RPM.
"""

from __future__ import annotations


def _placa(marca="", modelo="", serie="", **extra):
    p = {"marca": marca, "modelo": modelo, "serie": serie, "spec": "", "extra": {}}
    p.update(extra)
    return p


EQUIPOS = {
    "064": {
        "tag": "064", "ubicacion": "T9 – Plataforma Generadores",
        "grupo": _placa("Cummins", "C100D6", "D19I420882"),
        "motor": _placa("Cummins", "6BTA5.9-G6", "84862783", cpl=""),
        "alternador": _placa("Stamford", "PI144E1", "", winding="311"),
        "controlador": "PowerStart", "controladorModelo": "PC1.2",
        "voltajeNominal": 380, "fases": 3, "frecuenciaHz": 60, "kva": None, "rpm": 1800,
        "bateria": {"marca": "", "modelo": "", "voltaje": 12, "ah": None, "cca": None,
                    "cantidad": None},
        "horometro": None,
    },
    "C450D6": {
        "tag": "C450D6", "ubicacion": "",
        "grupo": _placa("Cummins", "C450D6", "A18T042328"),
        "motor": _placa("Cummins", "QSX15-G9", "", cpl=""),
        "alternador": _placa("Stamford", "HCI534E1", "X17L492615", winding="311"),
        "controlador": "PowerCommand", "controladorModelo": "PC 2.3",
        "voltajeNominal": 380, "fases": 3, "frecuenciaHz": 60, "kva": None, "rpm": 1800,
        "horometro": None,
    },
    "C20D6": {
        "tag": "C20D6", "ubicacion": "",
        "grupo": _placa("Cummins", "C20D6", "G18I144268"),
        "motor": _placa("Cummins", "X2.5-G4", ""),
        "controlador": "PowerStart", "controladorModelo": "PS0500",
        "voltajeNominal": 220, "fases": None, "frecuenciaHz": 60, "rpm": 1800,
        "horometro": None,
    },
    "AAQ29": {
        "tag": "AAQ29", "ubicacion": "",
        "grupo": _placa("Luxtower", "LUX M3", "150200062"),
        "motor": _placa("Kubota", "D1105-BG-EF01", ""),
        "voltajeNominal": 220, "fases": 1, "frecuenciaHz": None,
        "horometro": None,
    },
}
