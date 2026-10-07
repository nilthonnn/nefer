"""El activo: la entidad que `codigo_equipo` siempre estuvo señalando.

Hasta ahora FixMate no tenia activos. Tenia informes con un campo
`codigo_equipo` que era texto, y eso alcanzaba para filtrar y para preferir
antecedentes del mismo equipo. No alcanza para RCM: un analisis se hace
SOBRE un activo en un CONTEXTO, y sin la entidad no hay donde colgarlo.

La compatibilidad sale gratis y no es casualidad: el codigo del activo es el
mismo `codigo_equipo` que los informes ya traen. Declarar la excavadora
EX-220 no migra nada ni reescribe ningun informe — adopta de una vez todo el
historial que ya existe con ese codigo, con su MTBF y sus reincidencias ya
calculables por `prediccion`.

----------------------------------------------------------------------------
EL CONTEXTO OPERACIONAL NO ES UN COMENTARIO

Es la parte del modelo que mas se ignora y la que invalida mas analisis
copiados. Dos bombas identicas, mismo fabricante, mismo numero de parte: una
impulsa agua limpia en superficie y la otra lodo con solidos a 4.200 m. No
tienen la misma funcion —el estandar de desempeño es otro—, no tienen los
mismos modos de falla dominantes, y la consecuencia de que se detengan no se
parece.

Por eso `Analisis` queda amarrado a un contexto y `copiar_a()` obliga a
reconfirmarlo. Copiar un analisis sin mirar el contexto es el atajo con el
que un plan de mantenimiento se llena de tareas que no aplican.
----------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import catalogo as _catalogo

# El vocabulario de sistemas NO se inventa aqui: es el que el catalogo de
# causas ya usa. Un sistema nuevo en esta lista y no en el catalogo seria un
# sistema sobre el que nunca se podria codificar una causa.
SISTEMAS = tuple(sorted({e.sistema for e in _catalogo.DE_FABRICA}))


class ErrorActivo(ValueError):
    """El activo no se puede registrar tal como viene."""


@dataclass(frozen=True)
class Activo:
    """Una maquina de la flota.

    `codigo` es la llave y es el mismo que ya viaja en los informes. No se
    genera: lo pone el taller, porque es el que esta pintado en la maquina.
    """

    codigo: str
    nombre: str
    marca: str = ""
    modelo: str = ""
    serie: str = ""
    # La familia. Ya existe en FixMate como `categoria` y sirve para preferir
    # antecedentes de maquinas parecidas cuando no hay de la misma.
    categoria: str = ""
    # Donde y como trabaja. Texto libre a proposito: ningun enum captura
    # «turno continuo en interior mina, 4.200 m, con polvo de silice».
    contexto: str = ""
    criticidad: str = ""   # "" = no evaluada. Ver `criticidad.py`.

    def __post_init__(self):
        if not str(self.codigo).strip():
            raise ErrorActivo("el activo necesita codigo: es como lo llama el taller.")
        if not str(self.nombre).strip():
            raise ErrorActivo(f"{self.codigo}: falta el nombre del activo.")

    def a_dict(self) -> dict:
        return {"codigo": self.codigo, "nombre": self.nombre,
                "marca": self.marca, "modelo": self.modelo, "serie": self.serie,
                "categoria": self.categoria, "contexto": self.contexto,
                "criticidad": self.criticidad or "no evaluada"}

    @classmethod
    def de_dict(cls, d: dict) -> "Activo":
        return cls(
            codigo=str(d.get("codigo") or d.get("codigo_equipo") or ""),
            nombre=str(d.get("nombre") or ""),
            marca=str(d.get("marca") or ""),
            modelo=str(d.get("modelo") or d.get("modelo_equipo") or ""),
            serie=str(d.get("serie") or ""),
            categoria=str(d.get("categoria") or ""),
            contexto=str(d.get("contexto") or ""),
            criticidad=str(d.get("criticidad") or ""),
        )

    def descripcion(self) -> str:
        """Como se nombra en pantalla y en el texto indexable."""
        partes = [self.codigo, self.nombre]
        marca_modelo = " ".join(p for p in (self.marca, self.modelo) if p)
        if marca_modelo:
            partes.append(marca_modelo)
        return " · ".join(partes)


@dataclass(frozen=True)
class Ubicacion:
    """Donde esta el modo de falla dentro de la maquina.

    `sistema` sale del vocabulario del catalogo; `subsistema` y `componente`
    son libres porque bajar a ese nivel con un enum obliga a elegir el
    casillero equivocado, que es el problema que el catalogo resuelve no
    teniendo «Otro».
    """

    sistema: str = ""
    subsistema: str = ""
    componente: str = ""

    def a_dict(self) -> dict:
        return {"sistema": self.sistema, "subsistema": self.subsistema,
                "componente": self.componente}

    def __str__(self) -> str:
        return " / ".join(p for p in (self.sistema, self.subsistema,
                                      self.componente) if p)


@dataclass
class Flota:
    """Los activos declarados. Deliberadamente simple: es un indice por codigo.

    No persiste por su cuenta. Los activos viajan como fragmentos en el
    indice de FixMate, igual que todo lo demas, para no partir en dos el
    almacenamiento ni romper la copia al telefono.
    """

    activos: dict[str, Activo] = field(default_factory=dict)

    def agregar(self, activo: Activo) -> Activo:
        if activo.codigo in self.activos:
            raise ErrorActivo(
                f"el activo {activo.codigo} ya esta declarado. Dos activos con "
                "el mismo codigo parten su historial en dos.")
        self.activos[activo.codigo] = activo
        return activo

    def get(self, codigo: str) -> Activo | None:
        return self.activos.get(codigo)

    def __len__(self) -> int:
        return len(self.activos)

    def __contains__(self, codigo: str) -> bool:
        return codigo in self.activos

    def __iter__(self):
        return iter(self.activos.values())


def desde_indice(indice) -> Flota:
    """Los activos que el historial ya menciona, sin declararlos a mano.

    Esto NO inventa activos: lee los `codigo_equipo` que los informes ya
    traen y arma una ficha minima con lo que hay. Sirve para arrancar un
    piloto sin cargar la flota primero. Todo lo que no esta en el historial
    —marca, contexto, criticidad— queda vacio, y vacio se lee como «no
    declarado», nunca como un valor.
    """
    flota = Flota()
    for fragmento in getattr(indice, "fragmentos", []) or []:
        meta = getattr(fragmento, "metadatos", {}) or {}
        codigo = str(meta.get("codigo_equipo") or "").strip()
        if not codigo or codigo in flota:
            continue
        flota.agregar(Activo(
            codigo=codigo,
            nombre=str(meta.get("modelo_equipo") or codigo),
            modelo=str(meta.get("modelo_equipo") or ""),
            categoria=str(meta.get("categoria") or ""),
        ))
    return flota
