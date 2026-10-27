"""Adaptador de MoneyPrinterTurbo: búsqueda y descarga de video de stock.

Se reutiliza su capa de material (``app.services.material``) porque ya
resuelve lo difícil: filtrar por orientación y resolución, descargar con
validación, caché por URL y registrar el autor de cada clip (que necesitamos
para atribuir en la descripción de YouTube).

MoneyPrinterTurbo se importa desde ``MPT_DIR`` y sus claves se inyectan en
memoria: no se escribe nada en su ``config.toml``.
"""

from __future__ import annotations

import hashlib
import sys
import threading
from pathlib import Path
from typing import Any

from ..config import Config
from ..errores import ErrorConfiguracion, ErrorVisual
from ..modelos import Atribucion, ClipEscena, Escena
from ..multimedia.ffmpeg import ffmpeg, medir, verificar
from ..registro import de_escena, obtener
from .base import normalizar_video

log = obtener("visual.mpt")
_importacion = threading.Lock()


def _importar_mpt(mpt_dir: str) -> tuple[Any, Any, Any]:
    """Importa los módulos de MoneyPrinterTurbo; error claro si faltan dependencias."""
    if not mpt_dir:
        raise ErrorConfiguracion("Falta MPT_DIR (ruta al clon de MoneyPrinterTurbo) en .env")
    raiz = Path(mpt_dir).expanduser().resolve()
    if not (raiz / "app" / "services" / "material.py").is_file():
        raise ErrorConfiguracion(f"MPT_DIR no apunta a MoneyPrinterTurbo: {raiz}")
    with _importacion:
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        try:
            from app.config import config as mpt_config  # type: ignore[import-not-found]
            from app.models.schema import VideoAspect  # type: ignore[import-not-found]
            from app.services import material  # type: ignore[import-not-found]
        except ImportError as e:
            raise ErrorConfiguracion(
                f"No se pudo importar MoneyPrinterTurbo ({e}). Instala sus dependencias en este entorno: "
                f"pip install -r {raiz / 'requirements.txt'}"
            ) from e
    return mpt_config, material, VideoAspect


class VisualStockMPT:
    nombre = "moneyprinterturbo"

    def __init__(self, config: Config, cache: Path, prohibidos: set[str] | None = None) -> None:
        s = config.secretos
        if not (s.pexels_api_key or s.pixabay_api_key):
            raise ErrorConfiguracion("El stock necesita PEXELS_API_KEY o PIXABAY_API_KEY en .env")
        self._cfg = config
        self._cache = cache
        self._mpt_config, self._material, self._aspecto = _importar_mpt(s.mpt_dir)
        # Claves solo en memoria del proceso.
        if s.pexels_api_key:
            self._mpt_config.app["pexels_api_keys"] = [s.pexels_api_key]
        if s.pixabay_api_key:
            self._mpt_config.app["pixabay_api_keys"] = [s.pixabay_api_key]
        self._fuentes = [("pexels", self._material.search_videos_pexels)] if s.pexels_api_key else []
        if s.pixabay_api_key:
            self._fuentes.append(("pixabay", self._material.search_videos_pixabay))
        # Huellas de los clips ya usados en este video (ver huella()): repetir
        # un clip es la señal más obvia de "contenido reutilizado".
        self.usados: set[str] = set()
        # Clips que ya salieron en OTROS videos del canal: no se reutilizan.
        self.prohibidos: set[str] = set(prohibidos or ())

    def puede(self, escena: Escena) -> bool:
        return escena.visual.tipo == "stock"

    def generar(self, escena: Escena, duracion: float, destino: Path) -> ClipEscena:
        slog = de_escena(log, escena.id)
        candidatos = self._buscar(escena, slog)
        if not candidatos:
            raise ErrorVisual(
                f"Sin material de stock para {escena.visual.busqueda} "
                "(sin resultados, o MoneyPrinterTurbo registró un error de red/clave en su log)"
            )

        # Se juntan clips distintos hasta cubrir la escena; cada uno aporta como
        # máximo ~6 s para que el plano cambie al ritmo de un documental.
        piezas: list[Path] = []
        atribuciones: list[Atribucion] = []
        ids: list[str] = []
        cubierto = 0.0
        for item in candidatos:
            if cubierto >= duracion:
                break
            try:
                local = Path(self._material.save_video(item.url, str(self._cache)))
            except Exception as e:  # su descarga puede lanzar varios tipos
                slog.warning("descarga fallida (%s), pruebo el siguiente clip", e)
                continue
            if not local.is_file():
                continue
            tramo = min(6.0, max(2.5, duracion - cubierto), medir(local).duracion)
            pieza = destino.with_name(f"{destino.stem}.p{len(piezas)}.mp4")
            # Movimiento alterno entre planos: acercar, alejar, acercar...
            movimiento = "acercar" if (len(piezas) + len(self.usados)) % 2 == 0 else "alejar"
            normalizar_video(local, pieza, tramo, self._cfg, movimiento=movimiento)
            piezas.append(pieza)
            cubierto += tramo
            self.usados.add(huella(item.url))
            ids.append(huella(item.url))
            atribuciones.append(_atribucion(item, escena.id))

        if not piezas:
            raise ErrorVisual(f"No se pudo descargar ningún clip para {escena.visual.busqueda}")
        _concatenar(piezas, destino, duracion, self._cfg)
        for p in piezas:
            p.unlink(missing_ok=True)
        slog.info("stock: %d clip(s) de %s", len(piezas), ", ".join(sorted({a.proveedor for a in atribuciones})))
        return ClipEscena(ruta=destino, propio=False, atribuciones=atribuciones, ids_stock=ids)

    def _buscar(self, escena: Escena, slog) -> list[Any]:
        encontrados: list[Any] = []
        for termino in escena.visual.busqueda:
            for nombre, buscar in self._fuentes:
                try:
                    items = buscar(termino, 3, self._aspecto.landscape)
                except Exception as e:
                    slog.warning("%s falló buscando %r: %s", nombre, termino, e)
                    continue
                ya = self.usados | self.prohibidos | {huella(e.url) for e in encontrados}
                nuevos = [i for i in items if huella(i.url) not in ya]
                slog.debug("%s %r: %d resultados, %d nuevos", nombre, termino, len(items), len(nuevos))
                encontrados.extend(nuevos[:4])
        return encontrados


def huella(url: str) -> str:
    """Identificador corto y estable de un clip de stock.

    Se conserva la query: en algunos proveedores identifica el archivo
    (``download?file_id=...``) y quitarla haría pasar clips distintos por iguales.
    """
    return hashlib.sha1(url.split("#", 1)[0].encode()).hexdigest()[:12]


def _atribucion(item: Any, escena: str) -> Atribucion:
    info = getattr(item, "source_info", None) or {}
    creador = info.get("creator") or {}
    return Atribucion(
        proveedor=str(info.get("provider") or getattr(item, "provider", "stock")),
        autor=str(creador.get("name", "")),
        url=str(info.get("source_page") or ""),
        licencia={"pexels": "Licencia Pexels", "pixabay": "Licencia de contenido Pixabay"}.get(str(info.get("provider")), ""),
        escena=escena,
    )


def _concatenar(piezas: list[Path], destino: Path, duracion: float, cfg: Config) -> None:
    """Une piezas ya normalizadas y fija la duración exacta (repitiendo si faltara)."""
    if len(piezas) == 1:
        normalizar_video(piezas[0], destino, duracion, cfg)
        return
    lista = destino.with_suffix(".lista.txt")
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in piezas), encoding="utf-8")
    unido = destino.with_suffix(".unido.mp4")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(unido)], "unir piezas de stock")
    normalizar_video(unido, destino, duracion, cfg)
    verificar(destino, duracion=duracion, video=True, tolerancia=0.15)
    lista.unlink(missing_ok=True)
    unido.unlink(missing_ok=True)
