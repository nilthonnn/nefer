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

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

try:
    from fastapi import Depends, FastAPI, HTTPException, status
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - depende del entorno
    raise ImportError(
        "la API de FixMate necesita FastAPI: pip install nefer[fixmate-api]"
    ) from exc

from . import motor as _motor
from .indice import ErrorIndice, Indice

registro = logging.getLogger("nefer.fixmate")

RUTA_INDICE = os.getenv("FIXMATE_INDICE", "indice-fixmate.json")


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


class Salud(BaseModel):
    estado: str
    fragmentos: int
    embebedor: str
    redactor: str
    indice: str


def crear_app(motor_diagnostico: _motor.Motor | None = None,
              ruta_indice: str | Path | None = None,
              con_llm: bool | None = None) -> FastAPI:
    """Arma la aplicacion. El motor se puede inyectar ya hecho (y asi se prueba)."""
    ruta = Path(ruta_indice or RUTA_INDICE)
    estado: dict = {"motor": motor_diagnostico, "error": None}

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
            indice = Indice.cargar(ruta)
        except ErrorIndice as exc:
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
        return Salud(
            estado="listo",
            fragmentos=len(activo.indice),
            embebedor=getattr(activo.indice.embebedor, "nombre", "?"),
            redactor=getattr(activo.redactor, "nombre", "extractivo"),
            indice=str(ruta),
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

    return app


app = crear_app()
