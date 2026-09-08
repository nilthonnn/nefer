"""Conversion del libro Excel a PDF mediante LibreOffice headless."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class ErrorPDF(RuntimeError):
    """LibreOffice no esta disponible o la conversion fallo."""


def _binario() -> str:
    for nombre in ("soffice", "libreoffice"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    raise ErrorPDF(
        "No se encontro LibreOffice (soffice). Instalelo para exportar a PDF:\n"
        "  Debian/Ubuntu: sudo apt-get install libreoffice-calc\n"
        "  macOS:         brew install --cask libreoffice"
    )


def convertir(xlsx: str | Path, salida_pdf: str | Path | None = None,
              timeout: int = 300) -> Path:
    """Exporta `xlsx` a PDF. Devuelve la ruta del PDF generado."""
    xlsx = Path(xlsx).resolve()
    if not xlsx.exists():
        raise ErrorPDF(f"No existe el libro {xlsx}")

    destino = Path(salida_pdf).resolve() if salida_pdf else xlsx.with_suffix(".pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="nefer-pdf-") as tmp:
        # -env:UserInstallation aisla el perfil: permite ejecuciones concurrentes.
        cmd = [
            _binario(), "--headless", "--norestore",
            f"-env:UserInstallation=file://{tmp}/perfil",
            "--convert-to", "pdf:calc_pdf_Export",
            "--outdir", tmp, str(xlsx),
        ]
        try:
            proceso = subprocess.run(cmd, capture_output=True, text=True,
                                     timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise ErrorPDF(
                f"LibreOffice no respondio en {timeout} s al convertir {xlsx.name}. "
                "Las actas con muchas fotos tardan mas: reintente con un timeout mayor."
            ) from exc
        generado = Path(tmp) / (xlsx.stem + ".pdf")
        if not generado.exists():
            raise ErrorPDF(
                "LibreOffice no genero el PDF.\n"
                f"stdout: {proceso.stdout.strip()}\nstderr: {proceso.stderr.strip()}"
            )
        shutil.move(str(generado), str(destino))

    return destino
