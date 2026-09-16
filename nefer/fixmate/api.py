"""API HTTP de FixMate: el endpoint que consume la app de campo.

Es una capa fina. Todo lo que decide esta en `motor.py`, y por eso la API se
puede cambiar entera sin tocar el diagnostico.

    uvicorn nefer.fixmate.api:app --host 0.0.0.0 --port 8000

o, sin escribir la ruta del indice en ningun lado:

    FIXMATE_INDICE=indice.json nefer fixmate servir

Tres cosas que aqui se hacen distinto de como salen en un ejemplo de FastAPI:

- un 404 se devuelve como 404. Envuelto en un `except Exception` generico, el
  "no hay antecedentes" se convierte en un 500 y el tecnico lee "error del
  servidor" cuando lo que pasa es que nadie registro todavia esa falla;
- el detalle de una excepcion no viaja al cliente. Trae rutas, nombres de
  tablas y a veces la cadena de conexion;
- el indice se carga al arrancar, no en cada peticion.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

try:
    from fastapi import Depends, FastAPI, File, HTTPException, Form, UploadFile, status
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - depende del entorno
    raise ImportError(
        "la API de FixMate necesita FastAPI: pip install nefer[fixmate-api]"
    ) from exc

from . import cierre as _cierre, motor as _motor, prediccion as _prediccion
from . import transcripcion as _transcripcion
from .indice import Indice, firma_de

registro = logging.getLogger("nefer.fixmate")

RUTA_INDICE = os.getenv("FIXMATE_INDICE", "indice-fixmate.json")
RUTA_HISTORIAL = os.getenv("FIXMATE_HISTORIAL", "historial-fallas.json")
# Con esto en 'pg', la API busca en PostgreSQL en vez de en el archivo.
ALMACEN = os.getenv("FIXMATE_ALMACEN", "archivo")

# Subir un archivo en FastAPI necesita python-multipart. Si no esta, el resto
# de la API funciona igual y la ruta del audio lo dice en vez de tumbar el
# arranque entero por una dependencia que no todos necesitan.
HAY_MULTIPART = importlib.util.find_spec("multipart") is not None


class ConsultaDiagnostico(BaseModel):
    consulta_texto: str = Field(
        ..., min_length=3,
        json_schema_extra={"example": "Humo negro y perdida de potencia en "
                                      "pendiente a 4000 msnm"})
    codigo_dtc: Optional[str] = Field(None, json_schema_extra={"example": "P0300"})
    codigo_equipo: Optional[str] = Field(None, json_schema_extra={"example": "GE074-01"})
    categoria: Optional[str] = Field(None, json_schema_extra={"example": "grupo_electrogeno"})
    limite_resultados: int = Field(default=3, ge=1, le=10)


class EvidenciaSalida(BaseModel):
    id: str
    tipo: str
    fuente: str
    similitud: float
    codigo_ot: str = ""
    resumen_falla: str = ""
    causa_raiz: str = ""
    solucion_aplicada: str = ""
    extracto: str = ""


class CausaProbableSalida(BaseModel):
    causa: str
    probabilidad: float
    casos: int


class RespuestaDiagnostico(BaseModel):
    diagnostico_probabilistico: str
    causa_raiz_mas_probable: str
    pasos_recomendados: list[str]
    herramientas_y_repuestos: list[str]
    torques: list[str]
    evidencia_historica: list[EvidenciaSalida]
    confianza: str
    redactor: str
    avisos: list[str]
    causas_probables: list[CausaProbableSalida] = []
    precision_medida: Optional[dict] = None
    # Lo que el motor entendio. Con la consulta dictada, es lo primero que el
    # tecnico tiene que poder leer.
    consulta_interpretada: str = ""


class InformeEntrada(BaseModel):
    """Una falla resuelta, para que manana sea el antecedente de otro."""

    resumen_falla: str = Field(..., min_length=3)
    causa_raiz: str = Field(..., min_length=3)
    solucion_aplicada: str = Field(..., min_length=3)
    codigo_ot: Optional[str] = None
    codigo_equipo: Optional[str] = None
    categoria: Optional[str] = None
    codigos_dtc: list[str] = []
    pasos: list[str] = []
    herramientas: list[str] = []
    repuestos: list[str] = []
    horometro: Optional[float] = None
    horas_hombre: Optional[float] = None


class InformeGuardado(BaseModel):
    codigo_ot: str
    fecha: str
    historial: str
    indexado: bool
    fragmentos: int


class Salud(BaseModel):
    estado: str
    fragmentos: int
    embebedor: str
    redactor: str
    indice: str
    archivos: int = 0
    clasificador: str = "sin entrenar"
    precision_medida: Optional[dict] = None
    transcripcion: bool = False


def crear_app(motor_diagnostico: _motor.Motor | None = None,
              ruta_indice: str | Path | None = None,
              con_llm: bool | None = None,
              ruta_historial: str | Path | None = None,
              transcriptor=None,
              almacen: str | None = None) -> FastAPI:
    """Arma la aplicacion. El motor se puede inyectar ya hecho (y asi se prueba)."""
    ruta = Path(ruta_indice or RUTA_INDICE)
    en_pg = (almacen or ALMACEN) == "pg"
    estado: dict = {"motor": motor_diagnostico, "error": None,
                    "historial": Path(ruta_historial or RUTA_HISTORIAL),
                    "transcriptor": transcriptor}

    if con_llm is None:
        con_llm = bool(os.getenv("OPENAI_API_KEY"))

    @asynccontextmanager
    async def ciclo(_app: FastAPI):
        # El indice se lee una vez al arrancar, no en cada peticion: son
        # megabytes de vectores y el tecnico esta esperando.
        cargar_motor()
        yield

    app = FastAPI(
        title="FixMate AI — motor de diagnostico RAG",
        description="Diagnostico de maquinaria pesada sobre el historial de "
                    "fallas propio y los manuales del fabricante.",
        version="1.0.0",
        lifespan=ciclo,
    )

    def cargar_motor() -> None:
        if estado["motor"] is not None:
            return
        try:
            if en_pg:
                from .almacen_pg import AlmacenPgvector

                indice = AlmacenPgvector()
                len(indice)          # falla pronto si la base no contesta
            else:
                indice = Indice.cargar(ruta)
        except Exception as exc:
            # No se tumba el proceso: /salud tiene que poder decir que pasa.
            estado["error"] = str(exc)
            registro.error("FixMate sin indice: %s", exc)
            return
        redactor = _motor.RedactorLLM() if con_llm else None
        estado["motor"] = _motor.Motor(indice, redactor=redactor)
        registro.info("FixMate listo: %d fragmentos de %s", len(indice), ruta)

    def motor_actual() -> _motor.Motor:
        if estado["motor"] is None:
            cargar_motor()
        if estado["motor"] is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=estado["error"] or f"indice no disponible en {ruta}.")
        return estado["motor"]

    @app.get("/salud", response_model=Salud, summary="Estado del motor")
    def salud() -> Salud:
        if estado["motor"] is None:
            cargar_motor()
        activo = estado["motor"]
        if activo is None:
            return Salud(estado="sin indice", fragmentos=0, embebedor="-",
                         redactor="-", indice=str(ruta))
        clasificador = getattr(activo, "clasificador", None)
        return Salud(
            estado="listo",
            fragmentos=len(activo.indice),
            embebedor=getattr(activo.indice.embebedor, "nombre", "?"),
            redactor=getattr(activo.redactor, "nombre", "extractivo"),
            indice=str(getattr(activo.indice, "tabla", None) or ruta),
            archivos=len(getattr(activo.indice, "fuentes", {}) or {}),
            clasificador=getattr(clasificador, "motivo", "sin clasificador"),
            precision_medida=activo.medicion(),
            transcripcion=bool(os.getenv("OPENAI_API_KEY")) and HAY_MULTIPART,
        )

    @app.post("/search-report-rag", response_model=RespuestaDiagnostico,
              status_code=status.HTTP_200_OK,
              summary="Diagnostico a partir del historial de mantenimiento")
    def search_report_rag(peticion: ConsultaDiagnostico,
                          activo: _motor.Motor = Depends(motor_actual)
                          ) -> RespuestaDiagnostico:
        consulta = _motor.Consulta(
            texto=peticion.consulta_texto,
            codigo_dtc=peticion.codigo_dtc,
            codigo_equipo=peticion.codigo_equipo,
            categoria=peticion.categoria,
            limite=peticion.limite_resultados,
        )
        try:
            diagnostico = activo.consultar(consulta)
        except _motor.SinEvidencia as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=str(exc)) from exc
        except Exception as exc:
            # Se registra entero y se responde generico: el detalle de una
            # excepcion lleva rutas y credenciales dentro.
            registro.exception("fallo la consulta de diagnostico")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al resolver la consulta.") from exc
        return RespuestaDiagnostico(**diagnostico.a_dict())

    def _diagnosticar(activo: _motor.Motor, consulta: _motor.Consulta
                      ) -> RespuestaDiagnostico:
        try:
            return RespuestaDiagnostico(**activo.consultar(consulta).a_dict())
        except _motor.SinEvidencia as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=str(exc)) from exc
        except Exception as exc:
            registro.exception("fallo la consulta de diagnostico")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al resolver la consulta.") from exc

    if HAY_MULTIPART:
        @app.post("/search-report-rag-audio", response_model=RespuestaDiagnostico,
                  summary="Diagnostico a partir de una nota de voz")
        async def search_report_rag_audio(
                audio: UploadFile = File(..., description="nota de voz del tecnico"),
                codigo_dtc: Optional[str] = Form(None),
                codigo_equipo: Optional[str] = Form(None),
                categoria: Optional[str] = Form(None),
                limite_resultados: int = Form(3),
                activo: _motor.Motor = Depends(motor_actual)
        ) -> RespuestaDiagnostico:
            datos = await audio.read()
            transcriptor = estado.get("transcriptor") or _transcripcion.obtener("auto")
            try:
                texto = transcriptor(
                    (audio.filename or "nota.m4a", datos),
                    pistas=_transcripcion.pistas_de_indice(activo.indice))
            except _transcripcion.ErrorTranscripcion as exc:
                # 422: el audio llego, pero no se pudo convertir en consulta.
                # El numero va literal porque el nombre de la constante cambio
                # entre versiones de Starlette y no vale la pena atarse a eso.
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            return _diagnosticar(activo, _motor.Consulta(
                texto=texto, codigo_dtc=codigo_dtc, codigo_equipo=codigo_equipo,
                categoria=categoria, limite=limite_resultados))
    else:  # pragma: no cover - depende del entorno
        @app.post("/search-report-rag-audio", summary="No disponible sin multipart")
        def search_report_rag_audio_no():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="subir audio necesita python-multipart: "
                       "pip install 'nefer[fixmate-api]'")

    @app.post("/informes", response_model=InformeGuardado,
              status_code=status.HTTP_201_CREATED,
              summary="Registrar una falla resuelta (cierra el circulo)")
    def registrar_informe(informe: InformeEntrada,
                          activo: _motor.Motor = Depends(motor_actual)
                          ) -> InformeGuardado:
        historial = Path(estado.get("historial") or RUTA_HISTORIAL)
        try:
            guardado = _cierre.registrar(informe.model_dump(exclude_none=True),
                                         historial, activo.indice)
        except _cierre.ErrorCierre as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=str(exc)) from exc
        except OSError as exc:
            registro.exception("no se pudo escribir el historial")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo escribir el historial en disco.") from exc

        # El indice en memoria ya lo tiene; se deja tambien en disco para que
        # el proximo arranque no lo pierda.
        try:
            activo.indice.guardar(ruta)
            activo.indice.anotar_fuente(str(historial), firma_de(historial))
        except OSError:
            registro.warning("informe registrado pero el indice no se pudo guardar")
        # Lo aprendido cambia: el clasificador se vuelve a entrenar.
        estado["motor"] = _motor.Motor(activo.indice, redactor=activo.redactor)
        return InformeGuardado(
            codigo_ot=guardado["codigo_ot"], fecha=guardado["fecha"],
            historial=str(historial), indexado=True,
            fragmentos=len(activo.indice))

    @app.get("/prediccion", summary="Que falla mas en toda la flota")
    def prediccion_flota(limite: int = 5,
                         activo: _motor.Motor = Depends(motor_actual)) -> dict:
        return _prediccion.flota(activo.indice, limite=limite)

    @app.get("/prediccion/{equipo}", summary="Que le va a pasar a este equipo")
    def prediccion_equipo(equipo: str,
                          activo: _motor.Motor = Depends(motor_actual)) -> dict:
        return _prediccion.pronostico(activo.indice, equipo).a_dict()

    return app


app = crear_app()
