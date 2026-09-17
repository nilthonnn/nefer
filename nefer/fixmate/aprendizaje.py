"""Lo que el historial completo dice, y no solo el informe mas parecido.

La busqueda contesta «esta orden de trabajo se parece a lo que me cuenta».
Esto contesta otra cosa: «de las 340 veces que alguien escribio algo parecido
a esto, el 62% termino en el filtro de aire». Son preguntas distintas y las
dos hacen falta: la primera trae el procedimiento, la segunda dice por donde
empezar.

Es un clasificador bayesiano ingenuo —multinomial, con suavizado de Laplace—
entrenado sobre las causas raiz confirmadas de la propia flota. Cabe en
doscientas lineas de biblioteca estandar, se entrena en milisegundos cada vez
que se carga el indice y no hay nada que descargar ni que servir.

Dos cosas que hace y que casi ningun ejemplo de clasificacion hace:

- **Agrupa las causas que son la misma escrita distinto.** «Filtro de aire
  colmatado» y «filtro de aire colmatado por polvo de mina» son una causa,
  no dos, y separarlas parte en dos la evidencia de las dos.
- **Se mide y publica lo que midio.** `evaluar()` hace validacion dejando uno
  fuera y devuelve el acierto junto a la linea base de acertar siempre la
  causa mas comun. Un 62% suena bien hasta que se ve que contestar siempre
  «filtro de aire» acierta el 58%.

Y una que no hace: predecir cuando no hay de donde. Con menos de
`MINIMO_CASOS` ejemplos, o con una sola causa en todo el historial, se
declara sin entrenar y no devuelve nada. Un porcentaje inventado sobre cuatro
informes es peor que ningun porcentaje, porque parece medido.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import texto as _texto

# Por debajo de esto no hay aprendizaje, hay memorizacion de anecdotas.
MINIMO_CASOS = 12
MINIMO_CAUSAS = 2
MINIMO_POR_CAUSA = 2

# Cuanto tienen que compartir dos causas para ser la misma escrita distinto.
# Se mide de tres formas porque en un taller la misma causa se escribe de tres
# formas: entera, resumida y con el detalle de esa maquina.
PARECIDO_CAUSAS = 0.6        # palabras compartidas sobre el total (Jaccard)
SOLAPE_CAUSAS = 0.8          # la corta esta casi entera dentro de la larga
PALABRAS_NUCLEO = 2          # "baterias sulfatadas ..." es siempre lo mismo

ALFA = 0.3          # suavizado de Laplace


@dataclass
class CausaProbable:
    """Una causa candidata, con su probabilidad y en cuantos casos se apoya."""

    causa: str
    probabilidad: float
    casos: int

    def a_dict(self) -> dict:
        return {"causa": self.causa, "probabilidad": self.probabilidad,
                "casos": self.casos}


@dataclass
class Medicion:
    """Lo que se midio del clasificador, para poder desconfiar con datos."""

    casos: int
    causas: int
    aciertos: int
    precision: float
    linea_base: float

    def a_dict(self) -> dict:
        return {"casos": self.casos, "causas": self.causas,
                "aciertos": self.aciertos, "precision": round(self.precision, 3),
                "linea_base": round(self.linea_base, 3)}

    def resumen(self) -> str:
        return (f"{self.precision * 100:.0f}% de acierto sobre {self.casos} casos "
                f"y {self.causas} causas (acertar siempre la mas comun daria "
                f"{self.linea_base * 100:.0f}%)")


def causas_del_indice(indice) -> list[tuple[str, str]]:
    """Pares (texto de la falla, causa confirmada) que hay en el indice."""
    ejemplos = []
    for fragmento in getattr(indice, "fragmentos", []):
        causa = str(fragmento.metadatos.get("causa_raiz") or "").strip()
        if not causa:
            continue
        falla = " ".join(str(fragmento.metadatos.get(clave) or "")
                         for clave in ("resumen_falla", "solucion_aplicada"))
        ejemplos.append(((falla.strip() or fragmento.texto), causa))
    return ejemplos


def _nucleo(tokens: list[str]) -> tuple[str, ...]:
    """Las primeras palabras con contenido: el sujeto de la causa."""
    return tuple(tokens[:PALABRAS_NUCLEO])


def misma_causa(a: str, b: str) -> bool:
    """Si dos causas escritas distinto son la misma.

    «Baterias sulfatadas con densidad por debajo de 1.220 en dos vasos» y
    «baterias sulfatadas por descargas profundas» comparten dos palabras de
    diez: por conteo no se parecen en nada, y son la misma causa. Lo que las
    une es como empiezan, que en español es donde va el sujeto de la averia.
    """
    ta, tb = _texto.tokenizar(a), _texto.tokenizar(b)
    if not ta or not tb:
        return False
    if _nucleo(ta) == _nucleo(tb):
        return True
    pa, pb = set(ta), set(tb)
    comunes = len(pa & pb)
    if not comunes:
        return False
    menor = min(len(pa), len(pb))
    if comunes / len(pa | pb) >= PARECIDO_CAUSAS:
        return True
    # La corta esta casi entera dentro de la larga: es la misma causa, escrita
    # con prisa. Se pide un minimo de palabras para que «fuga» no se lleve
    # por delante a todo lo que gotea.
    return menor >= 3 and comunes / menor >= SOLAPE_CAUSAS


def agrupar_causas(causas, catalogo=None) -> dict[str, str]:
    """De cada causa escrita como se escribio, a la forma que las agrupa.

    Primero el catalogo: si el texto casa con una entrada, el grupo es la
    causa canonica de esa entrada. Un codigo del catalogo es estable —no
    cambia porque este mes se escribio distinto— y es comparable entre
    equipos, entre talleres y entre años, que es para lo que existe.

    Lo que el catalogo no reconoce se agrupa como siempre, por parecido, y
    **no se mezcla con lo codificado**: meterlo en un grupo del catalogo
    seria adivinar, y un codigo equivocado ensucia la cuenta de la flota
    entera mientras que uno que falta se ve.

    Entre lo no codificado manda la mas frecuente: es como lo escribe la
    mayoria del taller.
    """
    from .catalogo import POR_DEFECTO

    catalogo = POR_DEFECTO if catalogo is None else catalogo

    frecuencia: dict[str, int] = {}
    for causa in causas:
        limpia = str(causa).strip()
        if limpia:
            frecuencia[limpia] = frecuencia.get(limpia, 0) + 1

    # Lo que el catalogo reconoce queda resuelto aqui y no entra al parecido.
    mapa_catalogo: dict[str, str] = {}
    for causa in list(frecuencia):
        entrada = catalogo.clasificar(causa)
        if entrada is not None:
            mapa_catalogo[causa] = entrada.causa
            del frecuencia[causa]

    # A igual frecuencia manda la mas corta: es la forma generica, y es
    # mejor nombre de grupo que el detalle de una maquina concreta.
    ordenadas = sorted(frecuencia, key=lambda c: (-frecuencia[c], len(c), c))
    representantes: list[str] = []
    mapa: dict[str, str] = {}
    for causa in ordenadas:
        for nombre in representantes:
            if misma_causa(causa, nombre):
                mapa[causa] = nombre
                break
        else:
            representantes.append(causa)
            mapa[causa] = causa
    mapa.update(mapa_catalogo)
    return mapa


class ClasificadorCausas:
    """Bayes ingenuo multinomial sobre las causas raiz del historial."""

    def __init__(self):
        self.entrenado = False
        self.motivo = "sin entrenar"
        self.casos_por_causa: dict[str, int] = {}
        self._vocabulario: set[str] = set()
        self._cuenta: dict[str, dict[str, int]] = {}
        self._total: dict[str, int] = {}
        self._ejemplos: list[tuple[list[str], str]] = []

    # ------------------------------------------------------- entrenamiento

    def entrenar(self, ejemplos) -> "ClasificadorCausas":
        """`ejemplos` son pares (texto de la falla, causa confirmada)."""
        pares = [(str(t), str(c).strip()) for t, c in ejemplos if str(c).strip()]
        mapa = agrupar_causas(c for _, c in pares)
        agrupados = [(_texto.tokenizar(t), mapa[c]) for t, c in pares if t.strip()]

        cuenta_causas: dict[str, int] = {}
        for _, causa in agrupados:
            cuenta_causas[causa] = cuenta_causas.get(causa, 0) + 1
        # Una causa con un solo caso no ensena nada y ensucia el reparto.
        utiles = {c for c, n in cuenta_causas.items() if n >= MINIMO_POR_CAUSA}
        agrupados = [(t, c) for t, c in agrupados if c in utiles]

        self._ejemplos = agrupados
        self.casos_por_causa = {c: n for c, n in cuenta_causas.items() if c in utiles}
        self._ajustar(agrupados)

        if len(agrupados) < MINIMO_CASOS:
            self.entrenado = False
            self.motivo = (f"hacen falta {MINIMO_CASOS} casos con causa confirmada "
                           f"y hay {len(agrupados)}")
        elif len(self.casos_por_causa) < MINIMO_CAUSAS:
            self.entrenado = False
            self.motivo = (f"hacen falta {MINIMO_CAUSAS} causas distintas y hay "
                           f"{len(self.casos_por_causa)}")
        else:
            self.entrenado = True
            self.motivo = "entrenado"
        return self

    def _ajustar(self, ejemplos) -> None:
        self._vocabulario = set()
        self._cuenta = {}
        self._total = {}
        for tokens, causa in ejemplos:
            porcausa = self._cuenta.setdefault(causa, {})
            for token in tokens:
                porcausa[token] = porcausa.get(token, 0) + 1
                self._vocabulario.add(token)
            self._total[causa] = self._total.get(causa, 0) + len(tokens)

    # ---------------------------------------------------------- prediccion

    def predecir(self, consulta: str, limite: int = 3) -> list[CausaProbable]:
        """Las causas mas probables para esa descripcion, de mayor a menor."""
        if not self.entrenado:
            return []
        return self._puntuar(_texto.tokenizar(consulta), self._cuenta,
                             self._total, self.casos_por_causa)[:max(1, limite)]

    def _puntuar(self, tokens, cuenta, total, casos) -> list[CausaProbable]:
        if not tokens or not casos:
            return []
        universo = len(self._vocabulario) or 1
        n = sum(casos.values())
        puntajes: dict[str, float] = {}
        for causa, veces in casos.items():
            log = math.log(veces / n)
            porcausa = cuenta.get(causa, {})
            denominador = total.get(causa, 0) + ALFA * universo
            for token in tokens:
                if token not in self._vocabulario:
                    continue    # palabra que nunca se vio: no inclina nada
                log += math.log((porcausa.get(token, 0) + ALFA) / denominador)
            puntajes[causa] = log
        if not puntajes:
            return []

        mayor = max(puntajes.values())
        pesos = {c: math.exp(v - mayor) for c, v in puntajes.items()}
        suma = sum(pesos.values()) or 1.0
        salida = [CausaProbable(c, round(p / suma, 4), casos[c])
                  for c, p in pesos.items()]
        salida.sort(key=lambda c: (-c.probabilidad, c.causa))
        return salida

    # ----------------------------------------------------------- medicion

    def evaluar(self) -> Medicion | None:
        """Validacion dejando uno fuera. None si no hay con que medir.

        Se le pregunta por cada caso habiendolo quitado antes: es la unica
        forma honesta de dar un porcentaje cuando el historial es pequeño.

        Quitar un caso es restarlo de las cuentas y volver a sumarlo despues,
        no rehacerlas: rehacerlas era cuadratico y con el historial de una
        corporacion —miles de ordenes— tardaba minutos en cada indexacion.
        El resultado es el mismo numero; solo cambia lo que cuesta.
        """
        if not self.entrenado or len(self._ejemplos) < MINIMO_CASOS:
            return None

        cuenta = {c: dict(t) for c, t in self._cuenta.items()}
        total = dict(self._total)
        casos = dict(self.casos_por_causa)

        aciertos = 0
        for tokens, causa in self._ejemplos:
            porcausa = cuenta[causa]
            for token in tokens:
                porcausa[token] -= 1
            total[causa] -= len(tokens)
            casos[causa] -= 1
            quitada = casos[causa] == 0
            if quitada:
                del casos[causa]

            prediccion = self._puntuar(tokens, cuenta, total, casos)
            if prediccion and prediccion[0].causa == causa:
                aciertos += 1

            if quitada:
                casos[causa] = 0
            casos[causa] += 1
            total[causa] += len(tokens)
            for token in tokens:
                porcausa[token] += 1

        casos_totales = len(self._ejemplos)
        mayor = max(self.casos_por_causa.values())
        return Medicion(
            casos=casos_totales,
            causas=len(self.casos_por_causa),
            aciertos=aciertos,
            precision=aciertos / casos_totales,
            linea_base=mayor / casos_totales,
        )


def desde_indice(indice) -> ClasificadorCausas:
    """Entrena con lo que ya esta indexado. Barato: se hace al cargar."""
    return ClasificadorCausas().entrenar(causas_del_indice(indice))
