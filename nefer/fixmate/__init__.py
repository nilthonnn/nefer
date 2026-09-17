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

from dataclasses import dataclass, field
from pathlib import Path

from . import embeddings, ingesta, motor, texto
from .indice import Coincidencia, ErrorIndice, Fragmento, Indice, firma_de
from .ingesta import ErrorIngesta
from .motor import (Consulta, Diagnostico, ErrorRedactor, Evidencia, Motor,
                    SinEvidencia, redactar_extractivo)

__all__ = [
    "Actualizacion", "Coincidencia", "Consulta", "Diagnostico", "ErrorIndice",
    "ErrorIngesta", "ErrorRedactor", "Evidencia", "Fragmento", "Indice", "Motor",
    "SinEvidencia", "actualizar", "embeddings", "indexar",
    "ingesta", "motor", "redactar_extractivo", "texto",
]


@dataclass
class Actualizacion:
    """Que cambio al reindexar. Lo imprime la CLI y lo devuelve la API."""

    nuevos: list[str] = field(default_factory=list)
    cambiados: list[str] = field(default_factory=list)
    iguales: list[str] = field(default_factory=list)
    eliminados: list[str] = field(default_factory=list)
    fragmentos: int = 0

    @property
    def hubo_cambios(self) -> bool:
        return bool(self.nuevos or self.cambiados or self.eliminados)

    def resumen(self) -> str:
        return (f"{len(self.nuevos)} nuevos, {len(self.cambiados)} actualizados, "
                f"{len(self.iguales)} sin cambios, {len(self.eliminados)} eliminados")


def actualizar(indice: Indice, rutas, podar: bool = True) -> Actualizacion:
    """Reindexa solo lo que cambio desde la ultima vez.

    Un manual de cuatrocientas paginas no cambia porque se haya añadido una
    orden de trabajo al historial, y volver a calcular sus vectores cuesta
    tiempo —y, con un servicio de embeddings de pago, dinero—. Se compara la
    huella del contenido de cada archivo con la que quedo anotada.

    `podar` quita del indice los archivos que ya no existen: un manual
    retirado no debe seguir respondiendo.
    """
    # Igual que arriba: con un generador, la poda de mas abajo no veria
    # ninguna ruta y se saltaria en silencio.
    rutas = list(rutas)
    parte = Actualizacion()
    vistos = set()
    for raiz, archivo in ingesta.recorrer_con_raiz(rutas):
        origen = str(archivo)
        vistos.add(origen)
        firma = firma_de(archivo)
        if indice.sin_cambios(origen, firma):
            parte.iguales.append(origen)
            continue
        era_conocido = origen in indice.fuentes
        indice.olvidar(origen)
        fragmentos = ingesta.de_archivo(archivo, raiz)
        indice.agregar(fragmentos)
        indice.anotar_fuente(origen, firma)
        parte.fragmentos += len(fragmentos)
        (parte.cambiados if era_conocido else parte.nuevos).append(origen)

    if podar:
        # Solo se poda lo que estaba bajo las rutas que se acaban de recorrer:
        # indexar la carpeta de manuales no puede borrar el historial.
        for origen in [o for o in list(indice.fuentes)
                       if o not in vistos and _esta_bajo(o, rutas)
                       and not Path(o).exists()]:
            indice.olvidar(origen)
            parte.eliminados.append(origen)
    return parte


def _esta_bajo(origen: str, rutas) -> bool:
    origen = Path(origen).resolve()
    for ruta in rutas:
        ruta = Path(ruta).resolve()
        if origen == ruta or ruta in origen.parents:
            return True
    return False


def indexar(rutas, embebedor=None, indice: Indice | None = None) -> Indice:
    """Indexa archivos y carpetas: historiales, manuales y actas.

    Levanta `ErrorIngesta` en cuanto un documento no se puede leer. Indexar a
    medias y no decirlo deja un indice que responde, pero sin la mitad del
    historial: el tecnico no tiene como notar lo que no salio.
    """
    indice = indice or Indice(embebedor or embeddings.EmbebedorLocal())
    actualizar(indice, rutas)
    return indice
