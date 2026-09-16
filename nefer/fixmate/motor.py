"""El motor de diagnostico: consulta -> evidencia -> procedimiento.

Dos redactores, y el orden importa.

El **extractivo** no llama a nadie: arma el diagnostico recortando y ordenando
lo que dicen los antecedentes recuperados. Es el que corre en campo, es
determinista y no puede inventarse un torque porque solo sabe copiar. Es
tambien el que responde cuando el LLM no esta, no contesta o devuelve algo que
no se puede leer.

El **LLM** redacta mejor, junta tres informes en una explicacion sola y ordena
los pasos como los diria un instructor. Se usa cuando hay red y clave, y
siempre sobre la misma evidencia recuperada: si el modelo se cae, la respuesta
sigue saliendo por el otro camino en vez de devolver un 500 al tecnico que
esta parado al lado de la maquina.

Ninguno de los dos responde sin evidencia. Un diagnostico sin antecedente es
una conjetura, y una conjetura firmada por una herramienta se lee como un
dato.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field

from . import aprendizaje, texto as _texto
from .indice import Coincidencia, Indice

# Por debajo de esto, lo recuperado se parece mas al ruido del corpus que a la
# consulta: se responde igual, pero avisando de que hay poco donde sostenerse.
UMBRAL_CONFIANZA = 0.30

# Y por debajo de esto no se responde. Medido contra el corpus de ejemplo: una
# consulta de taller de verdad puntua entre 0.42 y 0.56, y una ajena al oficio
# —tramites de aduana, una receta— no pasa de 0.12. El hueco entre las dos es
# donde va la linea.
UMBRAL_MINIMO = 0.20

# Cuando el clasificador apunta a una causa con al menos esta probabilidad y
# la busqueda no trajo ningun antecedente de esa causa, se va a buscar uno.
APOYO_ESTADISTICO_MINIMO = 0.35

# Pero por encima de esto la busqueda ya encontro el antecedente bueno y la
# estadistica no manda. Es el caso de la falla nueva: el informe que se
# registro ayer describe exactamente esto, y el clasificador —que aprendio de
# las averias viejas— no puede saberlo todavia. La evidencia fuerte gana.
UMBRAL_EVIDENCIA_FUERTE = 0.50

AVISO_TORQUE = ("Contraste cada par de apriete con el manual OEM del equipo "
                "antes de aplicarlo.")
AVISO_SIN_FILTRO = ("Ningun antecedente cita ese codigo de falla; lo que sigue "
                    "se encontro por la descripcion de la falla.")
AVISO_POCA_EVIDENCIA = ("Evidencia debil: ningun antecedente se parece lo "
                        "suficiente. Trate esto como una pista, no como un "
                        "diagnostico.")
AVISO_LLM = ("El redactor con modelo de lenguaje no respondio; el diagnostico "
             "se armo con el historial recuperado, sin redaccion asistida.")
AVISO_SIN_PROCEDIMIENTO = ("Ningun antecedente trae un procedimiento escrito. Lea "
                           "el extracto de la evidencia: ahi esta lo que hay.")
AVISO_APOYO = ("La busqueda por palabras y el historial completo apuntaban a "
               "causas distintas. Se añadio a la evidencia el antecedente de la "
               "causa que respalda el historial; compare los dos antes de "
               "desarmar nada.")


class SinEvidencia(LookupError):
    """No hay antecedentes que respalden una respuesta."""


class ErrorRedactor(RuntimeError):
    """El redactor no devolvio algo utilizable."""


@dataclass
class Consulta:
    """Lo que el tecnico pregunta, dictado o escrito."""

    texto: str
    codigo_dtc: str | None = None
    codigo_equipo: str | None = None
    categoria: str | None = None
    limite: int = 3

    def __post_init__(self):
        if not str(self.texto).strip():
            raise ValueError("la consulta no puede estar vacia.")
        self.limite = max(1, min(int(self.limite), 10))
        if self.codigo_dtc:
            self.codigo_dtc = _texto.normalizar_dtc(self.codigo_dtc)

    def filtros(self) -> dict:
        """Lo que descarta: solo el codigo de falla, que o esta o no esta."""
        return {"codigos_dtc": self.codigo_dtc}

    def preferencias(self) -> dict:
        """Lo que solo empuja hacia arriba: el equipo y su familia."""
        return {"codigo_equipo": self.codigo_equipo, "categoria": self.categoria}


@dataclass
class Evidencia:
    """Un antecedente citado en la respuesta, con de donde salio."""

    id: str
    tipo: str
    fuente: str
    similitud: float
    codigo_ot: str = ""
    resumen_falla: str = ""
    causa_raiz: str = ""
    solucion_aplicada: str = ""
    extracto: str = ""

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Diagnostico:
    """La respuesta completa: que pasa, por que, que hacer y con que."""

    diagnostico_probabilistico: str
    causa_raiz_mas_probable: str
    pasos_recomendados: list[str] = field(default_factory=list)
    herramientas_y_repuestos: list[str] = field(default_factory=list)
    torques: list[str] = field(default_factory=list)
    evidencia_historica: list[Evidencia] = field(default_factory=list)
    confianza: str = "media"
    redactor: str = "extractivo"
    avisos: list[str] = field(default_factory=list)
    # Lo que dice el historial entero, no solo el informe mas parecido.
    causas_probables: list[dict] = field(default_factory=list)
    precision_medida: dict | None = None
    # Lo que el motor entendio que se le pregunto. Importa cuando la consulta
    # llego dictada: el tecnico tiene que poder leer que oyo la maquina.
    consulta_interpretada: str = ""

    def a_dict(self) -> dict:
        d = asdict(self)
        d["evidencia_historica"] = [e.a_dict() for e in self.evidencia_historica]
        return d


# ------------------------------------------------------------- evidencia

def _evidencia(coincidencia: Coincidencia) -> Evidencia:
    fragmento = coincidencia.fragmento
    meta = fragmento.metadatos
    return Evidencia(
        id=fragmento.id,
        tipo=fragmento.tipo,
        fuente=fragmento.fuente,
        similitud=round(coincidencia.puntaje, 4),
        codigo_ot=str(meta.get("codigo_ot") or meta.get("n_acta") or ""),
        resumen_falla=str(meta.get("resumen_falla") or meta.get("item") or ""),
        causa_raiz=str(meta.get("causa_raiz") or ""),
        solucion_aplicada=str(meta.get("solucion_aplicada") or ""),
        extracto=_recortar(fragmento.texto, 400),
    )


def _recortar(texto: str, largo: int) -> str:
    limpio = re.sub(r"\s+", " ", str(texto)).strip()
    return limpio if len(limpio) <= largo else limpio[:largo - 1].rstrip() + "…"


def contexto(coincidencias: list[Coincidencia]) -> str:
    """El bloque de evidencia que se le pasa al modelo, ya rotulado."""
    bloques = []
    for c in coincidencias:
        meta = c.fragmento.metadatos
        titulo = (meta.get("codigo_ot") or meta.get("seccion")
                  or meta.get("n_acta") or c.fragmento.id)
        bloques.append(
            f"--- {c.fragmento.tipo.upper()} {titulo} "
            f"(parecido {c.puntaje * 100:.0f}%, fuente {c.fragmento.fuente or 'n/d'}) ---\n"
            f"{c.fragmento.texto}")
    return "\n\n".join(bloques)


# ------------------------------------------------------ redactor sin LLM

def _unicos(valores) -> list[str]:
    """Quita repetidos ignorando mayusculas y tildes, conservando el orden."""
    vistos, salida = set(), []
    for valor in valores:
        limpio = str(valor).strip(" .;-")
        clave = _texto.normalizar(limpio)
        if limpio and clave not in vistos:
            vistos.add(clave)
            salida.append(limpio)
    return salida


def _frase_estadistica(causas_probables, medicion) -> str:
    """Lo que dice el historial completo, con el respaldo que tiene.

    Va siempre con el numero de casos y con el acierto medido. Un 62% sin
    esos dos numeros al lado es un adorno.
    """
    if not causas_probables:
        return ""
    mejor = causas_probables[0]
    frase = (f" En todo el historial, las descripciones parecidas a esta "
             f"terminaron en «{mejor['causa']}» el {mejor['probabilidad'] * 100:.0f}% "
             f"de las veces ({mejor['casos']} casos registrados)")
    if medicion:
        frase += (f"; el clasificador acierta el {medicion['precision'] * 100:.0f}% "
                  f"midiendolo contra sus propios {medicion['casos']} casos, y "
                  f"contestar siempre la causa mas comun acertaria el "
                  f"{medicion['linea_base'] * 100:.0f}%")
    return frase + "."


def _pasos_de(coincidencia: Coincidencia) -> list[str]:
    """Los pasos de un antecedente: los declarados o los de su solucion.

    Y nada mas. Partir en frases la prosa de un manual produce una lista que
    se lee como un procedimiento numerado sin serlo —el titulo de la seccion
    de paso 1, la advertencia de portada de paso 2—, y en campo eso se
    ejecuta. Cuando no hay procedimiento escrito se dice que no lo hay y se
    deja el extracto a la vista.
    """
    meta = coincidencia.fragmento.metadatos
    if meta.get("pasos"):
        return list(meta["pasos"])
    if meta.get("solucion_aplicada"):
        return _texto.frases(meta["solucion_aplicada"])
    return []


def _procedimiento_para(coincidencias: list[Coincidencia], causa: str):
    """Un antecedente con pasos que sirvan para la causa que se esta dando.

    El primero que traiga pasos no sirve: el orden es por parecido de
    palabras, y «humo negro» recupera igual el informe del filtro de aire y
    el del inyector. Tomando los pasos del que tuviera, se respondia «filtro
    de aire colmatado, segun OT-1» y debajo el procedimiento de cambiar un
    inyector, con su par de apriete, atribuido a OT-1. El tecnico aprieta a
    ese valor un perno que no es ese.

    Sirven: el antecedente de la misma causa, y el manual —una seccion de
    manual es un procedimiento, no una causa que compita—. Si no hay
    ninguno, no hay procedimiento, y eso se dice.
    """
    for c in coincidencias:
        if not _pasos_de(c):
            continue
        suya = str(c.fragmento.metadatos.get("causa_raiz") or "").strip()
        if c.fragmento.tipo == "manual" or not suya:
            return c
        if causa and aprendizaje.misma_causa(suya, causa):
            return c
    return None


def _con_causa(coincidencias: list[Coincidencia]) -> list[Coincidencia]:
    return [c for c in coincidencias if str(c.fragmento.metadatos.get("causa_raiz") or "").strip()]


def _respaldado(coincidencias: list[Coincidencia], causas_probables):
    """El antecedente cuya causa respalda todo el historial, si lo hay.

    Recuperar ordena por parecido de palabras, y la falla mas parecida no
    siempre es la misma averia: «humo negro y pierde fuerza» se parece tanto
    al informe del filtro de aire como al de un cilindro que perdia fuerza
    por otra cosa. Cuando el clasificador, que ha visto el historial entero,
    apunta a una causa y hay un antecedente recuperado con esa causa, se
    responde con ese. Sigue siendo evidencia recuperada: no se inventa nada,
    se elige mejor entre lo que ya salio.
    """
    con_causa = _con_causa(coincidencias)
    if not causas_probables or not con_causa:
        return None
    # La busqueda ya trajo un antecedente que encaja de sobra: se responde con
    # ese aunque el historial viejo apunte a otra cosa.
    if con_causa[0].puntaje >= UMBRAL_EVIDENCIA_FUERTE:
        return None
    esperada = causas_probables[0]["causa"]
    for coincidencia in con_causa:
        if aprendizaje.misma_causa(coincidencia.fragmento.metadatos["causa_raiz"],
                                   esperada):
            return coincidencia
    return None


def _referencia_de(coincidencia: Coincidencia) -> str:
    meta = coincidencia.fragmento.metadatos
    return str(meta.get("codigo_ot") or meta.get("n_acta") or meta.get("seccion")
               or coincidencia.fragmento.fuente or coincidencia.fragmento.id)


def _detalle_de(coincidencia: Coincidencia) -> str:
    meta = coincidencia.fragmento.metadatos
    item = str(meta.get("item") or "").strip()
    estado = str(meta.get("estado") or "").strip()
    return str(meta.get("resumen_falla") or meta.get("observacion")
               or (f"{item} ({estado})" if item and estado else item)
               or _recortar(coincidencia.fragmento.texto, 220))


def _causa_no_confirmada(coincidencia: Coincidencia) -> str:
    """Que decir cuando lo recuperado no confirma ninguna causa."""
    meta = coincidencia.fragmento.metadatos
    donde = str(meta.get("seccion") or meta.get("item") or "").strip()
    if coincidencia.fragmento.tipo == "manual":
        return ("No consta una causa raiz confirmada en el historial; lo "
                f"recuperado es documentacion del manual («{donde}»)." if donde else
                "No consta una causa raiz confirmada en el historial; lo "
                "recuperado es documentacion del manual.")
    return ("No consta una causa raiz confirmada; el antecedente solo registra "
            f"el hecho («{donde}»)." if donde else
            "No consta una causa raiz confirmada en el historial.")


def redactar_extractivo(consulta: Consulta, coincidencias: list[Coincidencia],
                        causas_probables=None, medicion=None) -> dict:
    """Arma el diagnostico recortando la evidencia. Sin red y sin invenciones."""
    mejor = coincidencias[0]

    # De donde sale la respuesta: el antecedente que el historial respalda si
    # lo hay, y si no el primero que traiga una causa confirmada.
    respaldado = _respaldado(coincidencias, causas_probables)
    con_causa = _con_causa(coincidencias)
    origen = respaldado or (con_causa[0] if con_causa else mejor)
    causa = str(origen.fragmento.metadatos.get("causa_raiz") or "").strip()
    if not causa:
        causa = _causa_no_confirmada(mejor)

    diagnostico = (
        f"{len(coincidencias)} antecedente(s) —historial y manuales— coinciden "
        f"con «{consulta.texto}». "
        f"El mas parecido ({_referencia_de(mejor)}, {mejor.puntaje * 100:.0f}%) "
        f"registra: {_detalle_de(mejor)}")

    iguales = [c for c in coincidencias if c is not origen and
               str(c.fragmento.metadatos.get("causa_raiz") or "").strip()
               and aprendizaje.misma_causa(c.fragmento.metadatos["causa_raiz"], causa)]
    if iguales:
        diagnostico += (f" Otros {len(iguales)} antecedente(s) terminaron en la "
                        f"misma causa, lo que la refuerza.")
    otras = [c for c in con_causa
             if c is not origen and c is not mejor and c not in iguales]
    if otras:
        referencias = ", ".join(_referencia_de(c) for c in otras)
        diagnostico += (f" Otros antecedentes ({referencias}) terminaron en otra "
                        f"causa; estan en la evidencia, con su propio procedimiento.")
    if consulta.codigo_dtc:
        diagnostico += f" Filtrado por el codigo {consulta.codigo_dtc}."
    diagnostico += _frase_estadistica(causas_probables, medicion)
    if respaldado is not None and respaldado is not mejor:
        diagnostico += (f" La causa sale de {_referencia_de(respaldado)}, que "
                        f"es el antecedente recuperado que coincide con esa "
                        f"estadistica.")

    # Los pasos salen de UN antecedente: el que da la causa, si trae
    # procedimiento. Encadenar el de dos causas distintas produce una lista
    # que se lee como un solo trabajo y no lo es.
    fuente = origen if _pasos_de(origen) else _procedimiento_para(coincidencias, causa)
    pasos = _pasos_de(fuente) if fuente is not None else []
    # Y se dice de donde salieron: un procedimiento prestado de otro
    # antecedente se cita como tal, o no se puede saber a que se refiere el
    # par de apriete que viene debajo.
    if fuente is not None and fuente is not origen:
        diagnostico += (f" El procedimiento y sus valores salen de "
                        f"{_referencia_de(fuente)}.")

    # Las herramientas y los torques acompañan al procedimiento: son de la
    # misma intervencion, no de la que dio el nombre de la causa.
    base = fuente if fuente is not None else origen
    herramientas = list(base.fragmento.metadatos.get("herramientas") or [])
    herramientas += list(base.fragmento.metadatos.get("repuestos") or [])
    # Las herramientas que nombra el manual valen para cualquier antecedente.
    for c in coincidencias:
        if c.fragmento.tipo == "manual":
            herramientas.extend(c.fragmento.metadatos.get("herramientas") or [])

    torques = list(base.fragmento.metadatos.get("torques") or [])
    torques += _texto.torques(base.fragmento.texto)
    for c in coincidencias:
        if c.fragmento.tipo == "manual":
            torques.extend(c.fragmento.metadatos.get("torques") or [])

    return {
        "diagnostico_probabilistico": diagnostico,
        "causa_raiz_mas_probable": causa or "No consta en el historial recuperado.",
        "pasos_recomendados": _unicos(pasos)[:10],
        "herramientas_y_repuestos": _unicos(herramientas),
        "torques": _unicos(torques),
    }


# ------------------------------------------------------ redactor con LLM

PROMPT_SISTEMA = """\
Eres FixMate AI, asistente de diagnostico de maquinaria pesada. Guias a un
tecnico que esta parado junto a la maquina, con las manos sucias y sin tiempo.

Reglas, en orden:
1. Respondes EXCLUSIVAMENTE con lo que digan los antecedentes que se te pasan.
   Si algo no esta ahi, no esta.
2. No inventas ni estimas un par de apriete, una holgura, una presion ni un
   numero de parte. Un valor aproximado revienta un perno o parte una junta.
   Si el dato no consta, escribes que hay que verificarlo en el manual OEM.
3. Citas la orden de trabajo o la seccion de la que sacas cada afirmacion.
4. Los pasos van en el orden en que se ejecutan, empezando por la comprobacion
   mas barata y por el bloqueo de energia si hay riesgo.

Devuelves solo un objeto JSON valido, sin texto alrededor y sin cercas de
codigo, con estas llaves:
{
  "diagnostico_probabilistico": "que esta pasando, segun los antecedentes",
  "causa_raiz_mas_probable": "la causa que mas se repite en el historial",
  "pasos_recomendados": ["paso 1", "paso 2"],
  "herramientas_y_repuestos": ["herramienta o repuesto"],
  "torques": ["valor y unidad, tal como aparece en la fuente"]
}"""

LLAVES = ("diagnostico_probabilistico", "causa_raiz_mas_probable",
          "pasos_recomendados", "herramientas_y_repuestos", "torques")


def json_del_modelo(contenido: str) -> dict:
    """Lee el JSON de una respuesta de modelo, aunque venga envuelto.

    Los modelos devuelven el objeto pelado casi siempre, y casi siempre no es
    siempre: llega con ```json alrededor, o con una frase amable delante. Eso
    no es motivo para responderle un error al tecnico.
    """
    if isinstance(contenido, dict):
        crudo = contenido
    else:
        texto_plano = str(contenido).strip()
        cercado = re.search(r"```(?:json)?\s*(.+?)```", texto_plano, re.S)
        if cercado:
            texto_plano = cercado.group(1).strip()
        try:
            crudo = json.loads(texto_plano)
        except json.JSONDecodeError:
            llaves = re.search(r"\{.*\}", texto_plano, re.S)
            if not llaves:
                raise ErrorRedactor("el modelo no devolvio JSON.")
            try:
                crudo = json.loads(llaves.group(0))
            except json.JSONDecodeError as exc:
                raise ErrorRedactor(f"el JSON del modelo no se puede leer: {exc}") from exc

    if not isinstance(crudo, dict):
        raise ErrorRedactor("el modelo devolvio JSON que no es un objeto.")
    if not str(crudo.get("diagnostico_probabilistico") or "").strip():
        raise ErrorRedactor("el modelo no devolvio diagnostico.")

    limpio = {}
    for llave in LLAVES:
        valor = crudo.get(llave)
        if llave in ("pasos_recomendados", "herramientas_y_repuestos", "torques"):
            if isinstance(valor, str):
                valor = [valor]
            limpio[llave] = _unicos(valor or [])
        else:
            limpio[llave] = str(valor or "").strip()
    return limpio


class RedactorLLM:
    """Redacta con un modelo compatible con la API de OpenAI.

    Se le puede pasar cualquier `cliente` con
    `chat.completions.create(model=..., messages=[...])`, que es como se prueba
    aqui sin salir a la red.
    """

    def __init__(self, modelo: str = "gpt-4o-mini", clave: str | None = None,
                 temperatura: float = 0.2, cliente=None):
        self.modelo = modelo
        self.temperatura = temperatura
        self.nombre = f"llm:{modelo}"
        self._cliente = cliente
        self._clave = clave or os.getenv("OPENAI_API_KEY")

    def _obtener_cliente(self):
        if self._cliente is not None:
            return self._cliente
        if not self._clave:
            raise ErrorRedactor("falta OPENAI_API_KEY para el redactor con modelo.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ErrorRedactor("el redactor con modelo necesita el paquete "
                                "'openai': pip install nefer[fixmate-openai]") from exc
        self._cliente = OpenAI(api_key=self._clave)
        return self._cliente

    def __call__(self, consulta: Consulta, coincidencias: list[Coincidencia],
                 causas_probables=None, medicion=None) -> dict:
        cliente = self._obtener_cliente()
        estadistica = ""
        if causas_probables:
            renglones = "; ".join(
                f"{c['causa']}: {c['probabilidad'] * 100:.0f}% ({c['casos']} casos)"
                for c in causas_probables)
            estadistica = (f"\n\nLo que dice el historial completo para una "
                           f"descripcion asi: {renglones}.")
            if medicion:
                estadistica += (f" Ese clasificador acierta el "
                                f"{medicion['precision'] * 100:.0f}% medido sobre "
                                f"{medicion['casos']} casos.")
        usuario = (
            f"Consulta del tecnico en campo: {consulta.texto}\n"
            f"Codigo de falla: {consulta.codigo_dtc or 'no especificado'}\n"
            f"Equipo: {consulta.codigo_equipo or 'no especificado'}\n\n"
            f"Antecedentes recuperados del historial y de los manuales:\n"
            f"{contexto(coincidencias)}{estadistica}")
        try:
            respuesta = cliente.chat.completions.create(
                model=self.modelo,
                temperature=self.temperatura,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": PROMPT_SISTEMA},
                          {"role": "user", "content": usuario}],
            )
            contenido = respuesta.choices[0].message.content
        except ErrorRedactor:
            raise
        except Exception as exc:
            raise ErrorRedactor(f"el modelo no respondio: {exc}") from exc
        return json_del_modelo(contenido)


# ----------------------------------------------------------------- motor

class Motor:
    """Une el indice, el redactor y el clasificador. Lo que llaman API y CLI.

    Un redactor es cualquier invocable con la firma

        redactor(consulta, coincidencias, causas_probables=None, medicion=None)

    que devuelva el diccionario con las llaves de `LLAVES`, o levante
    `ErrorRedactor` para que la respuesta salga por el camino extractivo.
    """

    def __init__(self, indice: Indice, redactor=None, umbral: float = UMBRAL_MINIMO,
                 clasificador=None, aprender: bool = True):
        self.indice = indice
        self.redactor = redactor
        self.umbral = umbral
        # El clasificador se entrena al construir el motor: son milisegundos
        # sobre el indice que ya esta en memoria, y si no hay casos
        # suficientes se declara sin entrenar y no estorba.
        if clasificador is None and aprender:
            clasificador = aprendizaje.desde_indice(indice)
        self.clasificador = clasificador
        self._medicion = None
        self._medido = False

    def medicion(self) -> dict | None:
        """Que tan bien acierta el clasificador. Se mide una vez y se guarda."""
        if not self._medido:
            self._medido = True
            medida = (self.clasificador.evaluar()
                      if self.clasificador is not None
                      and getattr(self.clasificador, "entrenado", False) else None)
            self._medicion = medida.a_dict() if medida else None
        return self._medicion

    def recuperar(self, consulta: Consulta) -> tuple[list[Coincidencia], list[str]]:
        """Antecedentes para la consulta, y los avisos que deja la busqueda."""
        avisos: list[str] = []
        filtros = consulta.filtros()
        preferencias = consulta.preferencias()
        coincidencias = self.indice.buscar(consulta.texto, limite=consulta.limite,
                                           filtros=filtros, umbral=self.umbral,
                                           preferencias=preferencias)
        # Un filtro que no deja pasar nada esconde la respuesta en vez de
        # afinarla: se vuelve a buscar sin el, diciendolo.
        if not coincidencias and any(filtros.values()):
            coincidencias = self.indice.buscar(consulta.texto, limite=consulta.limite,
                                               umbral=self.umbral,
                                               preferencias=preferencias)
            if coincidencias:
                avisos.append(AVISO_SIN_FILTRO)
        if not coincidencias:
            raise SinEvidencia(
                "No hay antecedentes en el indice que respalden esa consulta. "
                "Registre el caso al cerrarlo y el proximo tecnico si los tendra.")
        return coincidencias, avisos

    def causas_probables(self, consulta: Consulta, limite: int = 3) -> list[dict]:
        """Lo que dice el historial entero sobre una descripcion asi."""
        if self.clasificador is None or not getattr(self.clasificador, "entrenado", False):
            return []
        return [c.a_dict() for c in self.clasificador.predecir(consulta.texto, limite)]

    def apoyo_estadistico(self, consulta: Consulta, coincidencias, causas):
        """Trae el antecedente de la causa que el historial respalda, si falta.

        Sin esto, una consulta puede recuperar por parecido de palabras tres
        antecedentes de otra averia y contestar con la causa del primero,
        mientras el historial entero apuntaba a otra cosa. El antecedente que
        se añade sale del mismo indice: no se inventa evidencia, se busca la
        que faltaba.
        """
        if not causas or causas[0]["probabilidad"] < APOYO_ESTADISTICO_MINIMO:
            return None
        con_causa = _con_causa(coincidencias)
        # Con un antecedente fuerte ya recuperado no hace falta ir a buscar
        # otro: la estadistica queda como segunda opinion, en el texto.
        if con_causa and con_causa[0].puntaje >= UMBRAL_EVIDENCIA_FUERTE:
            return None
        if _respaldado(coincidencias, causas) is not None:
            return None
        esperada = causas[0]["causa"]
        ya = {c.fragmento.id for c in coincidencias}
        extra = self.indice.buscar(
            consulta.texto, limite=1, umbral=0.0,
            acepta=lambda f: f.id not in ya and aprendizaje.misma_causa(
                str(f.metadatos.get("causa_raiz") or ""), esperada))
        return extra[0] if extra else None

    def consultar(self, consulta: Consulta) -> Diagnostico:
        coincidencias, avisos = self.recuperar(consulta)
        causas = self.causas_probables(consulta)
        medicion = self.medicion() if causas else None

        apoyo = self.apoyo_estadistico(consulta, coincidencias, causas)
        if apoyo is not None:
            coincidencias = coincidencias + [apoyo]
            avisos.append(AVISO_APOYO)

        nombre_redactor = "extractivo"
        if self.redactor is not None:
            try:
                partes = self.redactor(consulta, coincidencias, causas, medicion)
                nombre_redactor = getattr(self.redactor, "nombre", "llm")
            except ErrorRedactor as exc:
                avisos.append(f"{AVISO_LLM} ({exc})")
                partes = redactar_extractivo(consulta, coincidencias, causas, medicion)
        else:
            partes = redactar_extractivo(consulta, coincidencias, causas, medicion)

        mejor = coincidencias[0].puntaje
        confianza = "alta" if mejor >= 0.55 else "media" if mejor >= UMBRAL_CONFIANZA else "baja"
        if confianza == "baja":
            avisos.append(AVISO_POCA_EVIDENCIA)
        if not partes.get("pasos_recomendados"):
            avisos.append(AVISO_SIN_PROCEDIMIENTO)
        if partes.get("torques"):
            avisos.append(AVISO_TORQUE)

        return Diagnostico(
            diagnostico_probabilistico=partes["diagnostico_probabilistico"],
            causa_raiz_mas_probable=partes["causa_raiz_mas_probable"],
            pasos_recomendados=list(partes.get("pasos_recomendados") or []),
            herramientas_y_repuestos=list(partes.get("herramientas_y_repuestos") or []),
            torques=list(partes.get("torques") or []),
            evidencia_historica=[_evidencia(c) for c in coincidencias],
            confianza=confianza,
            redactor=nombre_redactor,
            avisos=avisos,
            causas_probables=causas,
            precision_medida=medicion,
            consulta_interpretada=consulta.texto,
        )
