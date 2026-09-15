"""FixMate AI — asistente de diagnostico para el tecnico en campo.

Pone en el bolsillo del mecanico lo que hoy esta repartido entre un archivador
de manuales OEM y la memoria del ingeniero que lleva veinte años en la flota:
el historial de fallas propio, buscable por como se describe la averia y no
por como se titula el capitulo.

    from nefer.fixmate import Consulta, Indice, Motor, indexar

    indice = indexar(["historial.json", "manuales/"])
    motor = Motor(indice)
    print(motor.consultar(Consulta("humo negro y perdida de potencia")).a_dict())

Nada de esto necesita red. El indice es un archivo JSON que se copia al
telefono, el embebedor por defecto no llama a ningun servicio y el redactor
extractivo arma la respuesta con lo recuperado. Con clave de OpenAI en el
entorno, el mismo motor redacta mejor y se apoya en la misma evidencia; si el
modelo no contesta, la respuesta sale igual por el camino local.

Lo que el motor no hace, por diseño: responder sin antecedente que lo
respalde, y estimar un par de apriete. Las dos cosas se leen igual de bien que
un dato y no lo son.
"""

from __future__ import annotations

from . import embeddings, ingesta, motor, texto
from .indice import Coincidencia, ErrorIndice, Fragmento, Indice
from .ingesta import ErrorIngesta
from .motor import (Consulta, Diagnostico, ErrorRedactor, Evidencia, Motor,
                    RedactorLLM, SinEvidencia, redactar_extractivo)

__all__ = [
    "Coincidencia", "Consulta", "Diagnostico", "ErrorIndice", "ErrorIngesta",
    "ErrorRedactor", "Evidencia", "Fragmento", "Indice", "Motor", "RedactorLLM",
    "SinEvidencia", "embeddings", "indexar", "ingesta", "motor",
    "redactar_extractivo", "texto",
]


def indexar(rutas, embebedor=None, indice: Indice | None = None) -> Indice:
    """Indexa archivos y carpetas: historiales, manuales y actas.

    Levanta `ErrorIngesta` en cuanto un documento no se puede leer. Indexar a
    medias y no decirlo deja un indice que responde, pero sin la mitad del
    historial: el tecnico no tiene como notar lo que no salio.
    """
    indice = indice or Indice(embebedor or embeddings.EmbebedorLocal())
    fragmentos = []
    for archivo in ingesta.recorrer(rutas):
        fragmentos.extend(ingesta.de_archivo(archivo))
    indice.agregar(fragmentos)
    return indice
