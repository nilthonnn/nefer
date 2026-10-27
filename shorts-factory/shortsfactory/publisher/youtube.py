"""Subida a YouTube (Data API v3) reanudable y con reintentos.

- Subida por trozos (resumable): un corte de red reanuda desde el último
  trozo confirmado, no desde cero.
- Reintentos con espera exponencial ante 500/502/503/504 y errores de red
  (el patrón que recomienda Google para ``videos.insert``).
- 403 quotaExceeded/uploadLimitExceeded → ErrorCuota (no se reintenta hoy).
- 401 → ErrorAutenticacion.

Nota: los proyectos de API sin auditar suben los videos BLOQUEADOS como
privados aunque se pida "public". Para publicar directo hay que pasar la
auditoría de la YouTube API Services; mientras tanto, se publican a mano.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any, Callable

from ..errors import ErrorAutenticacion, ErrorCuota, ErrorTransitorio, ShortsError
from ..logs import obtener
from ..models import ResultadoSubida
from ..settings import Settings

log = obtener("youtube")
REINTENTABLES = {500, 502, 503, 504}
TROZO = 8 * 1024 * 1024


def servicio(cfg: Settings) -> Any:
    from googleapiclient.discovery import build

    from .auth import credenciales

    return build("youtube", "v3", credentials=credenciales(cfg), cache_discovery=False)


def cuerpo(cfg: Settings, titulo: str, descripcion: str, etiquetas: list[str], privacidad: str) -> dict:
    return {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion[:5000],
            "tags": etiquetas,
            "categoryId": cfg.youtube_categoria,
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {
            "privacyStatus": privacidad,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": cfg.youtube_contenido_sintetico,
        },
    }


def subir(
    cfg: Settings,
    video: Path,
    metadatos: dict,
    yt: Any = None,
    intentos: int = 8,
    dormir: Callable[[float], None] = time.sleep,
) -> ResultadoSubida:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = yt or servicio(cfg)
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=TROZO, resumable=True)
    peticion = yt.videos().insert(part="snippet,status", body=metadatos, media_body=media)
    respuesta, fallos = None, 0
    while respuesta is None:
        try:
            estado, respuesta = peticion.next_chunk()
            if estado is not None:
                log.info("subida %.0f %%", estado.progress() * 100)
        except HttpError as e:
            codigo = int(getattr(e.resp, "status", 0))
            texto = f"{e} {(getattr(e, 'content', b'') or b'').decode('utf-8', 'ignore')}"
            if codigo in REINTENTABLES:
                error: ShortsError = ErrorTransitorio(f"YouTube respondió {codigo}")
            elif codigo == 403 and ("quotaExceeded" in texto or "uploadLimitExceeded" in texto):
                raise ErrorCuota(f"YouTube rechazó la subida por cuota/límite: {texto[:200]}") from e
            elif codigo == 401:
                raise ErrorAutenticacion("YouTube rechazó las credenciales (401)") from e
            else:
                raise ShortsError(f"YouTube rechazó la subida ({codigo}): {texto[:300]}") from e
        except (ConnectionError, TimeoutError, OSError) as e:
            error = ErrorTransitorio(f"red: {type(e).__name__}: {e}")
        else:
            continue
        fallos += 1
        if fallos >= intentos:
            raise error
        espera = min(64.0, 2 ** fallos) + random.uniform(0, 1)
        log.warning("subida: %s; reintento %d/%d en %.1f s", error, fallos, intentos, espera)
        dormir(espera)

    if "id" not in respuesta:
        raise ShortsError(f"Respuesta de subida inesperada: {respuesta}")
    vid = respuesta["id"]
    return ResultadoSubida(
        video_id=vid,
        url=f"https://youtube.com/shorts/{vid}",
        privacidad=respuesta.get("status", {}).get("privacyStatus", metadatos["status"]["privacyStatus"]),
        titulo=metadatos["snippet"]["title"],
        unidades_cuota=cfg.youtube_costo_subida,
    )
