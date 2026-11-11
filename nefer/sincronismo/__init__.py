"""Sincronismo y grupos electrogenos en paralelo.

Lo que un tecnico de sincronismo hace todos los dias, convertido en calculo
que se puede repetir y en avisos que llegan antes que la falla:

- `verificacion`  permisivo de cierre (ANSI 25): diferencia de tension, de
                  frecuencia y de angulo, con el angulo evaluado en el
                  instante en que los contactos tocan, no en el que se da la
                  orden.
- `reparto`       reparto de kW y kVAr entre las unidades en paralelo, y la
                  prediccion del reparto por estatismo antes de tocar la
                  planta: que frecuencia queda y que carga toma cada una.
- `protecciones`  revision de los ajustes de las funciones que el paralelo
                  exige (25, 32, 40, 27/59, 81O/U, 46, 51V).
- `tendencias`    lo predictivo: la deriva del tiempo de sincronizacion o del
                  desbalance, y cuando cruza el limite, en fecha.
- `diagnostico`   guia de sintomas del paralelo, con sus comprobaciones.
- `informe`       todo lo anterior junto, ordenado por lo que obliga a hacer.

Tres reglas, las mismas del resto de nefer:

- Ningun limite sale de la nada: cada uno dice de donde viene, y los que
  son criterio de taller se rotulan como tales y se pueden cambiar.
- Una tendencia con menos puntos de los necesarios no se proyecta. Se dice
  cuantos hay y cuantos faltan.
- La guia de diagnostico es referencia, no antecedente: no confirma una causa
  en un equipo concreto. Lo que se confirme se cierra en FixMate.
"""

from .verificacion import LIMITES_IEEE1547, Lectura, Veredicto, verificar
from .reparto import Unidad, analizar_reparto, predecir_estatismo

__all__ = [
    "LIMITES_IEEE1547", "Lectura", "Veredicto", "verificar",
    "Unidad", "analizar_reparto", "predecir_estatismo",
]
