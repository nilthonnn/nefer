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

from . import texto as _texto
from .indice import Coincidencia, Indice

# Por debajo de esto, lo recuperado se parece mas al ruido del corpus que a la
# consulta: se responde igual, pero avisando de que hay poco donde sostenerse.
UMBRAL_CONFIANZA = 0.30

# Y por debajo de esto no se responde. Medido contra el corpus de ejemplo: una
# consulta de taller de verdad puntua entre 0.42 y 0.56, y una ajena al oficio
# —tramites de aduana, una receta— no pasa de 0.12. El hueco entre las dos es
# donde va la linea.
UMBRAL_MINIMO = 0.20

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


def redactar_extractivo(consulta: Consulta, coincidencias: list[Coincidencia]) -> dict:
    """Arma el diagnostico recortando la evidencia. Sin red y sin invenciones."""
    mejor = coincidencias[0]
    meta = mejor.fragmento.metadatos

    causas = _unicos(c.fragmento.metadatos.get("causa_raiz", "") for c in coincidencias)
    causa = causas[0] if causas else ""
    if not causa:
        # Un manual no confirma causas: documenta. Devolver el titulo de la
        # seccion como "causa raiz" es dar por confirmado lo que nadie
        # confirmo.
        donde = str(meta.get("seccion") or meta.get("item") or "").strip()
        if mejor.fragmento.tipo == "manual":
            causa = ("No consta una causa raiz confirmada en el historial; lo "
                     f"recuperado es documentacion del manual («{donde}»)."
                     if donde else
                     "No consta una causa raiz confirmada en el historial; lo "
                     "recuperado es documentacion del manual.")
        else:
            causa = ("No consta una causa raiz confirmada; el antecedente solo "
                     f"registra el hecho («{donde}»)." if donde else
                     "No consta una causa raiz confirmada en el historial.")

    coinciden = sum(1 for c in coincidencias[1:]
                    if _texto.normalizar(str(c.fragmento.metadatos.get("causa_raiz", "")))
                    == _texto.normalizar(causa) and causa)

    referencia = (meta.get("codigo_ot") or meta.get("n_acta")
                  or meta.get("seccion") or mejor.fragmento.fuente or mejor.fragmento.id)
    item = str(meta.get("item") or "").strip()
    estado = str(meta.get("estado") or "").strip()
    detalle = str(meta.get("resumen_falla") or meta.get("observacion")
                  or (f"{item} ({estado})" if item and estado else item)
                  or _recortar(mejor.fragmento.texto, 220))

    diagnostico = (
        f"{len(coincidencias)} antecedente(s) —historial y manuales— coinciden "
        f"con «{consulta.texto}». "
        f"El mas parecido ({referencia}, {mejor.puntaje * 100:.0f}%) registra: {detalle}")
    if coinciden:
        diagnostico += (f" Otros {coinciden} antecedente(s) terminaron en la misma "
                        f"causa, lo que la refuerza.")
    otras = [c for c in coincidencias[1:]
             if c.fragmento.metadatos.get("causa_raiz")
             and _texto.normalizar(str(c.fragmento.metadatos["causa_raiz"])) != _texto.normalizar(causa)]
    if otras:
        referencias = ", ".join(
            str(c.fragmento.metadatos.get("codigo_ot") or c.fragmento.id) for c in otras)
        diagnostico += (f" Otros antecedentes ({referencias}) terminaron en otra causa; "
                        f"estan en la evidencia, con su propio procedimiento.")
    if consulta.codigo_dtc:
        diagnostico += f" Filtrado por el codigo {consulta.codigo_dtc}."

    # Los pasos salen de UN antecedente, el mejor que traiga alguno. Encadenar
    # el procedimiento de dos causas distintas produce una lista que se lee
    # como un solo trabajo y no lo es; el resto queda citado en la evidencia.
    origen = next((c for c in coincidencias if _pasos_de(c)), mejor)
    pasos = _pasos_de(origen)

    herramientas = list(origen.fragmento.metadatos.get("herramientas") or [])
    herramientas += list(origen.fragmento.metadatos.get("repuestos") or [])
    # Las herramientas que nombra el manual valen para cualquier antecedente.
    for c in coincidencias:
        if c.fragmento.tipo == "manual":
            herramientas.extend(c.fragmento.metadatos.get("herramientas") or [])

    torques = list(origen.fragmento.metadatos.get("torques") or [])
    torques += _texto.torques(origen.fragmento.texto)
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

    def __call__(self, consulta: Consulta, coincidencias: list[Coincidencia]) -> dict:
        cliente = self._obtener_cliente()
        usuario = (
            f"Consulta del tecnico en campo: {consulta.texto}\n"
            f"Codigo de falla: {consulta.codigo_dtc or 'no especificado'}\n"
            f"Equipo: {consulta.codigo_equipo or 'no especificado'}\n\n"
            f"Antecedentes recuperados del historial y de los manuales:\n"
            f"{contexto(coincidencias)}")
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
    """Une el indice con el redactor. Es lo que la API y la CLI llaman."""

    def __init__(self, indice: Indice, redactor=None, umbral: float = UMBRAL_MINIMO):
        self.indice = indice
        self.redactor = redactor
        self.umbral = umbral

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

    def consultar(self, consulta: Consulta) -> Diagnostico:
        coincidencias, avisos = self.recuperar(consulta)

        nombre_redactor = "extractivo"
        if self.redactor is not None:
            try:
                partes = self.redactor(consulta, coincidencias)
                nombre_redactor = getattr(self.redactor, "nombre", "llm")
            except ErrorRedactor as exc:
                avisos.append(f"{AVISO_LLM} ({exc})")
                partes = redactar_extractivo(consulta, coincidencias)
        else:
            partes = redactar_extractivo(consulta, coincidencias)

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
        )
