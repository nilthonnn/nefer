"""OAuth2 de YouTube: refresh token → access token renovado automáticamente.

- ``autorizar`` (comando ``shortsfactory auth``) abre el navegador UNA vez y
  devuelve el refresh token para guardarlo como secreto (YOUTUBE_REFRESH_TOKEN).
- ``credenciales`` crea credenciales que google-auth renueva solas (el access
  token caduca cada hora; se rota sin intervención).
- ``invalid_grant`` = refresh token revocado o caducado. Ojo: si la app de
  OAuth está en modo "Testing" en Google Cloud, Google lo caduca a los 7 días;
  para CI hay que pasarla a "In production".
"""

from __future__ import annotations

import json
from typing import Any

from ..errors import ErrorAutenticacion, ErrorConfiguracion, ErrorTransitorio
from ..settings import Settings

ALCANCES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def config_cliente(cfg: Settings) -> dict[str, Any]:
    cfg.exigir("youtube_client_secret")
    try:
        datos = json.loads(Settings.secreto(cfg.youtube_client_secret))
    except json.JSONDecodeError as e:
        raise ErrorConfiguracion("YOUTUBE_CLIENT_SECRET debe ser el CONTENIDO JSON del client_secret") from e
    if not any(k in datos for k in ("installed", "web")):
        raise ErrorConfiguracion("YOUTUBE_CLIENT_SECRET no tiene la clave 'installed' ni 'web'")
    return datos


def credenciales(cfg: Settings) -> Any:
    cfg.exigir("youtube_client_secret", "youtube_refresh_token")
    from google.auth.exceptions import RefreshError, TransportError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    cliente = next(iter(config_cliente(cfg).values()))
    creds = Credentials(
        token=None,
        refresh_token=Settings.secreto(cfg.youtube_refresh_token),
        client_id=cliente["client_id"],
        client_secret=cliente["client_secret"],
        token_uri=cliente.get("token_uri", "https://oauth2.googleapis.com/token"),
        scopes=ALCANCES,
    )
    try:
        creds.refresh(Request())
    except RefreshError as e:
        if "invalid_grant" in str(e):
            raise ErrorAutenticacion(
                "El refresh token fue revocado o caducó. Ejecuta `shortsfactory auth` y actualiza "
                "YOUTUBE_REFRESH_TOKEN (si la app está en modo Testing, Google lo caduca a los 7 días)."
            ) from e
        raise ErrorAutenticacion(f"No se pudo renovar el acceso a YouTube: {e}") from e
    except TransportError as e:
        raise ErrorTransitorio(f"Sin conexión con Google OAuth: {e}") from e
    return creds


def autorizar(cfg: Settings) -> str:
    """Flujo interactivo (local, con navegador). Devuelve el refresh token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flujo = InstalledAppFlow.from_client_config(config_cliente(cfg), ALCANCES)
    creds = flujo.run_local_server(port=0, prompt="consent", access_type="offline")
    if not creds.refresh_token:
        raise ErrorAutenticacion("Google no devolvió refresh token; revoca el acceso de la app y repite")
    return creds.refresh_token
