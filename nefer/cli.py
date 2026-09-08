"""Interfaz de linea de comandos de nefer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, build, extract, pdf, schema


def _imprimir_avisos(avisos: list[str]) -> None:
    for aviso in avisos:
        print(f"  aviso: {aviso}", file=sys.stderr)


def _cargar(ruta: Path, validar_rutas: bool = True):
    """Lee y valida un manifiesto, o imprime el motivo y devuelve None."""
    try:
        return schema.cargar(ruta, validar_rutas=validar_rutas)
    except schema.ErrorManifiesto as exc:
        print(str(exc), file=sys.stderr)
        return None


def cmd_validar(args) -> int:
    ruta = Path(args.manifiesto)
    if _cargar(ruta, validar_rutas=not args.sin_verificar_fotos) is None:
        return 1
    print(f"{ruta}: manifiesto valido.")
    return 0


def cmd_construir(args) -> int:
    ruta = Path(args.manifiesto)
    manifiesto = _cargar(ruta)
    if manifiesto is None:
        return 1

    salida = Path(args.salida) if args.salida else ruta.with_suffix(".xlsx")
    xlsx, avisos = build.construir(
        manifiesto, salida, raiz=ruta.parent, con_guias=not args.sin_guias
    )
    _imprimir_avisos(avisos)
    print(f"Excel generado: {xlsx}")

    if args.pdf:
        destino = Path(args.pdf) if isinstance(args.pdf, str) else xlsx.with_suffix(".pdf")
        try:
            print(f"PDF generado:   {pdf.convertir(xlsx, destino)}")
        except pdf.ErrorPDF as exc:
            print(str(exc), file=sys.stderr)
            return 2
    return 0


def cmd_extraer(args) -> int:
    manifiesto = extract.extraer(args.xlsx, args.fotos)
    salida = json.dumps(manifiesto, ensure_ascii=False, indent=2)
    if args.salida:
        Path(args.salida).write_text(salida + "\n", encoding="utf-8")
        print(f"Manifiesto escrito: {args.salida}")
    else:
        print(salida)
    return 0


def cmd_pdf(args) -> int:
    try:
        print(f"PDF generado: {pdf.convertir(args.xlsx, args.salida)}")
    except pdf.ErrorPDF as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _a_markdown(lineas) -> str:
    partes = []
    for nivel, texto in lineas:
        if not texto:
            partes.append("")
        elif nivel == "t":
            partes.append(f"# {texto}\n")
        elif nivel == "s":
            partes.append(f"## {texto}\n")
        else:
            partes.append(texto + "\n")
    return "\n".join(partes).rstrip() + "\n"


def cmd_guias(args) -> int:
    """Exporta las guias impresas (las mismas que van dentro de cada acta)."""
    from . import textos

    manifiesto = {"encabezado": {}}
    if args.manifiesto:
        with open(args.manifiesto, encoding="utf-8") as fh:
            manifiesto = json.load(fh)

    destino = Path(args.salida or ".")
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, lineas in (
        ("GUIA-OPERADOR.md", textos.guia_operador(manifiesto)),
        ("GUIA-CLIENTE.md", textos.guia_cliente(manifiesto)),
    ):
        ruta = destino / nombre
        ruta.write_text(_a_markdown(lineas), encoding="utf-8")
        print(f"Guia escrita: {ruta}")
    return 0


def cmd_plantilla(args) -> int:
    salida = json.dumps(schema.PLANTILLA_MANIFIESTO, ensure_ascii=False, indent=2)
    if args.salida:
        Path(args.salida).write_text(salida + "\n", encoding="utf-8")
        print(f"Plantilla escrita: {args.salida}")
    else:
        print(salida)
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nefer",
        description="Automatiza el reporte fotografico de despacho y recepcion "
                    "de maquinaria.",
    )
    p.add_argument("--version", action="version", version=f"nefer {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    c = sub.add_parser("construir", help="manifiesto JSON + fotos -> Excel (y PDF)")
    c.add_argument("manifiesto")
    c.add_argument("-o", "--salida", help="ruta del .xlsx de salida")
    c.add_argument("--pdf", nargs="?", const=True, default=False,
                   help="exportar tambien a PDF (opcionalmente indique la ruta)")
    c.add_argument("--sin-guias", action="store_true",
                   help="no incluir las hojas GUIA OPERADOR y GUIA CLIENTE")
    c.set_defaults(func=cmd_construir)

    v = sub.add_parser("validar", help="verificar un manifiesto contra el esquema")
    v.add_argument("manifiesto")
    v.add_argument("--sin-verificar-fotos", action="store_true",
                   help="no comprobar que exista cada archivo de imagen "
                        "(por defecto si se comprueba, igual que al construir)")
    v.set_defaults(func=cmd_validar)

    e = sub.add_parser("extraer", help="Excel llenado -> manifiesto JSON")
    e.add_argument("xlsx")
    e.add_argument("-o", "--salida", help="ruta del .json de salida")
    e.add_argument("--fotos", help="carpeta donde volcar las imagenes incrustadas")
    e.set_defaults(func=cmd_extraer)

    d = sub.add_parser("pdf", help="Excel -> PDF")
    d.add_argument("xlsx")
    d.add_argument("-o", "--salida")
    d.set_defaults(func=cmd_pdf)

    g = sub.add_parser("guias", help="exportar las guias de operador y cliente en Markdown")
    g.add_argument("-o", "--salida", help="carpeta de destino (por defecto, la actual)")
    g.add_argument("-m", "--manifiesto",
                   help="acta de la que tomar equipo y cliente para encabezar la guia")
    g.set_defaults(func=cmd_guias)

    t = sub.add_parser("plantilla", help="imprimir un manifiesto JSON en blanco")
    t.add_argument("-o", "--salida")
    t.set_defaults(func=cmd_plantilla)

    return p


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    return args.func(args)
