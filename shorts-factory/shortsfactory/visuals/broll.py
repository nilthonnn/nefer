"""B-roll vertical de Pexels (opcional, con PEXELS_API_KEY).

Busca clips verticales, elige la versión más liviana que cubra 1080×1920,
la descarga con tope de tamaño y la normaliza (recorte 9:16, fps del
proyecto, sin audio). Ningún clip se repite entre Shorts del canal.
Sin clave o sin resultados, la escena usa un fondo generativo.
"""

from __future__ import annotations

from pathlib import Path

import requests

from ..errors import ErrorTransitorio, ShortsError
from ..logs import obtener
from ..proc import ffmpeg
from ..sources.http import obtener_json

log = obtener("broll")
URL = "https://api.pexels.com/videos/search"
MAX_BYTES = 150 * 1024 * 1024


class BRoll:
    def __init__(self, clave: str, usados: set[str], sesion: requests.Session | None = None) -> None:
        self.clave = clave
        self.usados = set(usados)
        self.sesion = sesion or requests.Session()

    def buscar(self, consulta: str) -> tuple[str, str, str] | None:
        """(id, url_descarga, autor) del primer clip vertical no usado."""
        datos = obtener_json(URL, params={"query": consulta, "orientation": "portrait", "size": "medium", "per_page": 15},
                             headers={"Authorization": self.clave}, sesion=self.sesion)
        for v in datos.get("videos", []) if isinstance(datos, dict) else []:
            vid = f"pexels:{v.get('id')}"
            if vid in self.usados:
                continue
            archivos = [f for f in v.get("video_files", []) if f.get("height", 0) > f.get("width", 0)]
            buenos = sorted((f for f in archivos if f.get("height", 0) >= 1920), key=lambda f: f["height"]) \
                or sorted(archivos, key=lambda f: f.get("height", 0), reverse=True)
            if buenos and buenos[0].get("link"):
                return vid, buenos[0]["link"], str((v.get("user") or {}).get("name", ""))
        return None

    def obtener(self, consulta: str, destino: Path, segundos: float, fps: int) -> tuple[Path, str, str] | None:
        try:
            hallado = self.buscar(consulta)
        except ShortsError as e:
            log.warning("Pexels no disponible para %r: %s", consulta, e)
            return None
        if hallado is None:
            log.info("sin b-roll nuevo para %r", consulta)
            return None
        vid, url, autor = hallado
        crudo = destino.with_suffix(".crudo.mp4")
        self._descargar(url, crudo)
        ffmpeg(["-stream_loop", "-1", "-i", str(crudo), "-t", f"{segundos:.3f}", "-an",
                "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={fps},format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(destino)], f"normalizar b-roll {vid}")
        crudo.unlink(missing_ok=True)
        self.usados.add(vid)
        return destino, vid, autor

    def _descargar(self, url: str, destino: Path) -> None:
        try:
            with self.sesion.get(url, stream=True, timeout=(10, 120)) as r:
                if r.status_code != 200:
                    raise ErrorTransitorio(f"descarga de b-roll respondió {r.status_code}")
                total = 0
                with destino.open("wb") as f:
                    for trozo in r.iter_content(1 << 20):
                        total += len(trozo)
                        if total > MAX_BYTES:
                            raise ErrorTransitorio("b-roll demasiado grande")
                        f.write(trozo)
        except (requests.ConnectionError, requests.Timeout) as e:
            raise ErrorTransitorio(f"descarga de b-roll: {type(e).__name__}") from e
