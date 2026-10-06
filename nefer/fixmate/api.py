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

from . import cierre as _cierre, motor as _motor, prediccion as _prediccion
from .indice import Indice, firma_de

registro = logging.getLogger("nefer.fixmate")

RUTA_INDICE = os.getenv("FIXMATE_INDICE", "indice-fixmate.json")
RUTA_HISTORIAL = os.getenv("FIXMATE_HISTORIAL", "historial-fallas.json")
# Con esto en 'pg', la API busca en PostgreSQL en vez de en el archivo.
ALMACEN = os.getenv("FIXMATE_ALMACEN", "archivo")


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
    # Lo que aportan los analisis RCM y las pautas TPM que la busqueda
    # recupero. Lista vacia cuando no hay ninguno cargado — que es el estado
    # normal de un piloto recien empezado—, nunca ausente.
    contexto_rcm: list[dict] = []


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
    # Trazabilidad hacia RCM y TPM. Opcionales para siempre: un historial de
    # cinco años no los tiene, y exigirlos invalidaria cada informe viejo.
    modo_falla_id: Optional[str] = None
    codigo_catalogo: Optional[str] = None
    anomalia_id: Optional[str] = None


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


def crear_app(motor_diagnostico: _motor.Motor | None = None,
              ruta_indice: str | Path | None = None,
              ruta_historial: str | Path | None = None,
              almacen: str | None = None) -> FastAPI:
    """Arma la aplicacion. El motor se puede inyectar ya hecho (y asi se prueba)."""
    ruta = Path(ruta_indice or RUTA_INDICE)
    en_pg = (almacen or ALMACEN) == "pg"
    estado: dict = {"motor": motor_diagnostico, "error": None,
                    "historial": Path(ruta_historial or RUTA_HISTORIAL)}

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
        estado["motor"] = _motor.Motor(indice)
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

    # ------------------------------------------------------- RCM y TPM
    #
    # Son de LECTURA. Crear o aprobar un analisis RCM por HTTP exigiria
    # autenticacion y control de versiones, y FixMate no tiene ninguna de las
    # dos: un endpoint de escritura sin eso deja que cualquiera en la red del
    # taller reescriba el plan de mantenimiento sin dejar rastro. Los
    # analisis se cargan con la CLI, que corre con los permisos de quien la
    # ejecuta. Cuando haya autenticacion, esto se amplia.

    @app.get("/rcm", summary="Modos de falla analizados que hay en el indice")
    def rcm_listar(equipo: Optional[str] = None,
                   activo: _motor.Motor = Depends(motor_actual)) -> dict:
        from . import indexado as _indexado

        modos = [
            {"id": f.metadatos.get("modo_falla_id", ""),
             "codigo_equipo": f.metadatos.get("codigo_equipo", ""),
             "codigo_catalogo": f.metadatos.get("codigo_catalogo", ""),
             "sistema": f.metadatos.get("sistema", ""),
             "evidente": f.metadatos.get("evidente", True),
             "grave": f.metadatos.get("grave", False),
             "criticidad": f.metadatos.get("criticidad", ""),
             "estrategia": f.metadatos.get("estrategia", ""),
             "estrategia_rotulo": f.metadatos.get("estrategia_rotulo", ""),
             "estado_validacion": f.metadatos.get("estado_validacion", ""),
             "resumen_falla": f.metadatos.get("resumen_falla", "")}
            for f in activo.indice.fragmentos
            if f.tipo == _indexado.TIPO_RCM
            and (not equipo or f.metadatos.get("codigo_equipo") == equipo)]
        return {"modos": modos, "total": len(modos)}

    @app.get("/rcm/modos/{codigo_catalogo}",
             summary="Los modos de falla que declaran ese codigo de catalogo")
    def rcm_por_codigo(codigo_catalogo: str,
                       activo: _motor.Motor = Depends(motor_actual)) -> dict:
        from . import indexado as _indexado

        modos = [f.metadatos for f in activo.indice.fragmentos
                 if f.tipo == _indexado.TIPO_RCM
                 and f.metadatos.get("codigo_catalogo") == codigo_catalogo]
        return {"codigo_catalogo": codigo_catalogo, "modos": modos,
                "total": len(modos)}

    @app.get("/tpm/anomalias", summary="Anomalias registradas en el indice")
    def tpm_anomalias(abiertas: bool = True, equipo: Optional[str] = None,
                      activo: _motor.Motor = Depends(motor_actual)) -> dict:
        from . import indexado as _indexado

        salida = [f.metadatos for f in activo.indice.fragmentos
                  if f.tipo == _indexado.TIPO_ANOMALIA
                  and (not abiertas or f.metadatos.get("abierta"))
                  and (not equipo or f.metadatos.get("codigo_equipo") == equipo)]
        return {"anomalias": salida, "total": len(salida),
                "filtro": "abiertas" if abiertas else "todas"}

    @app.get("/tablero", summary="Indicadores de confiabilidad del historial")
    def tablero(activo: _motor.Motor = Depends(motor_actual)) -> dict:
        from . import tablero as _tablero

        datos = _tablero.confiabilidad(activo.indice).a_dict()
        datos["nota"] = (
            "MTTR y disponibilidad quedan en null a proposito: FixMate "
            "registra cuando ocurrio una falla, no cuanto duro la reparacion.")
        return datos

    return app


app = crear_app()
