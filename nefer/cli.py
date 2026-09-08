"""Interfaz de linea de comandos de nefer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, build, extract, layout, pdf, schema


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


# Formatos que Excel sabe incrustar, y los que la gente trae de todos modos.
EXT_VALIDAS = build.FORMATOS_IMAGEN
EXT_PROBLEMA = {".heic", ".heif", ".tiff", ".tif", ".webp", ".dng", ".raw"}


def cmd_fotos(args) -> int:
    """Arma el bloque `registro_fotografico` a partir de una carpeta de fotos.

    Las fotos se emparejan con los rotulos de la categoria en el orden en que
    aparecen ordenadas por nombre, que es el orden de la rejilla del formato.
    """
    carpeta = Path(args.carpeta)
    if not carpeta.is_dir():
        print(f"No existe la carpeta {carpeta}", file=sys.stderr)
        return 1

    manifiesto = None
    if args.manifiesto:
        ruta_m = Path(args.manifiesto)
        try:
            with ruta_m.open(encoding="utf-8") as fh:
                manifiesto = json.load(fh)
        except FileNotFoundError:
            print(f"No existe el manifiesto {ruta_m}", file=sys.stderr)
            return 1
        except json.JSONDecodeError as exc:
            print(f"{ruta_m}: no es JSON valido (linea {exc.lineno}).", file=sys.stderr)
            return 1

    categoria = args.categoria
    if not categoria and manifiesto:
        categoria = manifiesto.get("encabezado", {}).get("categoria")
    categoria = categoria or "generico"
    if categoria not in layout.VISTAS_POR_CATEGORIA:
        print(f"Categoria desconocida: {categoria!r}. Use una de "
              f"{sorted(layout.VISTAS_POR_CATEGORIA)}.", file=sys.stderr)
        return 1

    archivos = sorted(p for p in carpeta.iterdir()
                      if p.is_file() and p.suffix.lower() in EXT_VALIDAS)
    rechazadas = sorted(p for p in carpeta.iterdir()
                        if p.is_file() and p.suffix.lower() in EXT_PROBLEMA)

    if rechazadas:
        print(f"  aviso: {len(rechazadas)} archivo(s) que Excel no puede incrustar: "
              + ", ".join(p.name for p in rechazadas[:4])
              + ("…" if len(rechazadas) > 4 else ""), file=sys.stderr)
        print("  aviso: conviertalos a JPG antes de continuar. En el iPhone, "
              "Ajustes > Camara > Formatos > 'Mas compatible' evita el problema "
              "de raiz.", file=sys.stderr)
    if not archivos:
        print(f"No hay imagenes utilizables en {carpeta}", file=sys.stderr)
        return 1

    base = Path(args.manifiesto).parent if args.manifiesto else Path(".")
    vistas = layout.VISTAS_POR_CATEGORIA[categoria]

    # Primero las fotos cuyo nombre delata la vista; el resto rellena los huecos
    # en orden alfabetico, que es el orden en que se numeraron en campo.
    asignadas: dict[int, Path] = {}
    sueltas: list[Path] = []
    for archivo in archivos:
        vista = layout.vista_sugerida(archivo.name)
        i = vistas.index(vista) if vista in vistas else -1
        if i >= 0 and i not in asignadas:
            asignadas[i] = archivo
        else:
            sueltas.append(archivo)
    for archivo in sueltas:
        hueco = next((i for i in range(len(vistas)) if i not in asignadas), None)
        if hueco is None:
            hueco = max(asignadas) + 1 if asignadas else 0
        asignadas[hueco] = archivo

    registro = []
    for n, i in enumerate(sorted(asignadas)):
        archivo = asignadas[i]
        try:
            relativa = archivo.resolve().relative_to(base.resolve())
        except ValueError:
            relativa = archivo
        registro.append({
            "foto_id": n + 1,
            "descripcion": vistas[i] if i < len(vistas) else "",
            "archivo": relativa.as_posix(),
        })

    if len(archivos) > len(vistas):
        print(f"  aviso: hay {len(archivos)} fotos y solo {len(vistas)} rotulos "
              f"para '{categoria}'; complete a mano las ultimas descripciones.",
              file=sys.stderr)

    if manifiesto is None:
        print(json.dumps({"registro_fotografico": registro},
                         ensure_ascii=False, indent=2))
        return 0

    manifiesto["registro_fotografico"] = registro
    Path(args.manifiesto).write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(registro)} fotos escritas en {args.manifiesto}")
    for foto in registro:
        print(f"  {foto['foto_id']:>2}. {foto['descripcion'] or '(sin rotulo)':<26} "
              f"{foto['archivo']}")
    print("\nRevise que cada rotulo corresponda a su foto antes de construir.")
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

    f = sub.add_parser("fotos",
                       help="carpeta de fotos -> bloque registro_fotografico")
    f.add_argument("carpeta")
    f.add_argument("-m", "--manifiesto",
                   help="escribir el bloque dentro de este acta.json")
    f.add_argument("-c", "--categoria",
                   help="familia del equipo; por defecto, la del manifiesto")
    f.set_defaults(func=cmd_fotos)

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
