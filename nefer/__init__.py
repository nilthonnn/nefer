"""Automatizacion de informes de despacho y recepcion de maquinaria.

Genera el "Reporte fotografico de despacho y recepcion" a partir de un
manifiesto JSON. La identidad del formato (empresa, logo, codigo, version) es
configurable: el paquete no asume ninguna organizacion en particular.
"""

__version__ = "1.0.0"
__all__ = ["layout", "schema", "estilos", "build", "extract", "pdf"]
