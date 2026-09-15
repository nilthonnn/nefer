#!/usr/bin/env python3
"""Demos de FixMate: un taller de mentira y los comandos de verdad.

Arma en una carpeta temporal lo que hay en la oficina de un taller —el
historial en Excel con su membrete, un manual en Word con sus titulos, otro en
PDF y un acta de nefer— y corre sobre eso **los mismos comandos** que correria
el usuario. Lo que sale en pantalla no es una imitacion de la salida: es la
salida.

    python3 herramientas/demo-fixmate.py                 # todas, una tras otra
    python3 herramientas/demo-fixmate.py formatos        # solo una
    python3 herramientas/demo-fixmate.py --lista         # cuales hay
    python3 herramientas/demo-fixmate.py --conservar     # deja la carpeta
    python3 herramientas/demo-fixmate.py servir          # levanta la API

Nada de esto necesita red ni clave de ningun servicio: es el camino local
completo, el mismo que corre en el patio.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import warnings
import shutil
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# Una demo no tiene por que ensenar los avisos de obsolescencia de las
# librerias de terceros: el que la mira esta mirando otra cosa.
warnings.filterwarnings("ignore")

from nefer import cli as cli_nefer                                  # noqa: E402

# Fecha fija: una demo que cambia de resultado cada dia no se puede ensenar
# dos veces ni comparar con la de ayer.
HOY = _dt.date(2026, 9, 15)

ANCHO = 74
W = "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\""


# --------------------------------------------------------------- pantalla

def titulo(texto: str) -> None:
    print(f"\n\n╔{'═' * (ANCHO - 2)}╗")
    print(f"║ {texto[:ANCHO - 4]:<{ANCHO - 4}} ║")
    print(f"╚{'═' * (ANCHO - 2)}╝")


def parrafo(texto: str) -> None:
    import textwrap

    print()
    for linea in textwrap.wrap(texto, ANCHO):
        print(linea)


def correr(orden: list[str], carpeta: Path) -> int:
    """Corre un comando de nefer de verdad y muestra lo que imprime."""
    import shlex

    argv = [str(a).format(d=carpeta) for a in orden]
    print(f"\n$ nefer {shlex.join(argv)}\n")
    try:
        return cli_nefer.main(argv)
    except SystemExit as exc:                     # argparse
        return int(exc.code or 0)


# ------------------------------------------------------------- el taller

def pdf_de(lineas: list[str]) -> bytes:
    """Un PDF de una pagina, del tamaño justo para que sea uno de verdad."""
    ordenes = [b"BT /F1 11 Tf 56 760 Td 14 TL"]
    for linea in lineas:
        escapada = (linea.replace("\\", r"\\").replace("(", r"\(")
                    .replace(")", r"\)")).encode("cp1252", "replace")
        ordenes.append(b"(" + escapada + b") Tj T*")
    ordenes.append(b"ET")
    contenido = zlib.compress(b"\n".join(ordenes))

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(contenido)
        + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida = bytearray(b"%PDF-1.4\n")
    for n, objeto in enumerate(objetos, 1):
        salida += b"%d 0 obj\n" % n + objeto + b"\nendobj\n"
    salida += b"trailer << /Root 1 0 R >>\n%%EOF\n"
    return bytes(salida)


def historial_xlsx(destino: Path) -> Path:
    """El historial como esta en la oficina: membrete arriba y una fila por OT."""
    from openpyxl import Workbook

    fuente = json.loads((RAIZ / "ejemplos" / "fixmate" / "historial-fallas.json")
                        .read_text(encoding="utf-8"))
    libro = Workbook()
    hoja = libro.active
    hoja.title = "HISTORIAL 2026"
    hoja.append(["MAQUINARIAS DEL SUR S.A.C."])
    hoja.append(["Historial de fallas — flota de alquiler"])
    hoja.append([])
    hoja.append(["N° OT", "Fecha", "Equipo", "Código de falla", "Falla reportada",
                 "Causa raíz", "Trabajo realizado", "Repuestos", "Técnico",
                 "Horómetro", "HH"])
    for informe in fuente["informes"]:
        hoja.append([
            informe["codigo_ot"], informe["fecha"], informe["codigo_equipo"],
            "; ".join(informe.get("codigos_dtc") or []), informe["resumen_falla"],
            informe["causa_raiz"], informe["solucion_aplicada"],
            "; ".join(informe.get("repuestos") or []), "J. Quispe",
            informe.get("horometro"), informe.get("horas_hombre"),
        ])
    ruta = destino / "historial-2026.xlsx"
    libro.save(ruta)
    return ruta


def manual_docx(destino: Path) -> Path:
    """Un manual en Word, con los titulos que le puso quien lo escribio."""
    cuerpo = (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        '<w:r><w:t>Cilindros hidráulicos</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Los pernos de la tapa del cilindro se aprietan a 210 N·m '
        'en cruz. El juego de sellos del vástago se cambia completo, nunca solo '
        'el sello que se ve dañado: el resto ya trabajó las mismas horas.'
        '</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Herramientas: torquímetro de 60 a 340 N·m, piedra de '
        'pulir fina.</w:t></w:r></w:p>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        '<w:r><w:t>Mangueras y tendido</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Toda manguera que roce el chasis termina reventando. '
        'Revise las abrazaderas del tendido en cada mantenimiento.</w:t></w:r></w:p>'
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Perno de tapa</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>210 N·m</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    ruta = destino / "manual-hidraulica.docx"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   f'<?xml version="1.0"?><w:document {W}><w:body>{cuerpo}'
                   f'</w:body></w:document>')
    return ruta


def manual_pdf(destino: Path) -> Path:
    """Y otro en PDF, que es como llega el del fabricante."""
    ruta = destino / "manual-electrico.pdf"
    ruta.write_bytes(pdf_de([
        "Sistema electrico y baterias",
        "",
        "El electrolito se verifica con el equipo frio. Una densidad por",
        "debajo de 1.220 en cualquier vaso condena la bateria, aunque el",
        "arranque todavia funcione.",
        "",
        "Par de apriete de bornes de bateria: 8 N.m. Un borne apretado de",
        "mas parte el plomo; uno flojo calienta y sulfata.",
        "",
        "Herramientas: densimetro, llave de 10 mm, cepillo de bornes.",
    ]))
    return ruta


def acta_xlsx(destino: Path) -> Path:
    """Un acta de nefer llenada: de ahi salen las recuperaciones."""
    from nefer import build

    manifiesto = json.loads(
        (RAIZ / "ejemplos" / "GE074-01-recepcion.json").read_text(encoding="utf-8"))
    manifiesto["registro_fotografico"] = []
    xlsx, _ = build.construir(manifiesto, destino / "acta-GE074-01.xlsx",
                              raiz=destino, con_guias=False)
    return xlsx


def montar_taller(carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    shutil.copy(RAIZ / "ejemplos" / "fixmate" / "manual-grupo-electrogeno.md", carpeta)
    for hacer in (historial_xlsx, manual_docx, manual_pdf, acta_xlsx):
        hacer(carpeta)


# ---------------------------------------------------------------- demos

def demo_formatos(carpeta: Path) -> None:
    """PDF, Word y Excel: lo que hay de verdad en la carpeta del taller."""
    titulo("1 · Los formatos que hay en la oficina")
    parrafo("El manual del fabricante no esta en Markdown: esta en PDF, en "
            "Word y en Excel. El historial tampoco esta en JSON: esta en un "
            "Excel con membrete y una fila por orden de trabajo. Esto es lo "
            "que hay en la carpeta del taller:")
    print()
    for archivo in sorted(carpeta.iterdir()):
        if archivo.is_file():
            print(f"  {archivo.name:<32} {archivo.stat().st_size / 1024:>7.1f} KB")

    from nefer.fixmate import documentos

    parrafo("Del Word salen los titulos como secciones, y del PDF sale el "
            "texto sin instalar nada: si no hay poppler ni pypdf, lo lee un "
            "lector de biblioteca estandar.")
    for nombre in ("manual-hidraulica.docx", "manual-electrico.pdf"):
        print(f"\n--- {nombre} " + "-" * (ANCHO - len(nombre) - 5))
        texto = documentos.leer(carpeta / nombre)
        for linea in texto.strip().splitlines()[:6]:
            print(f"  {linea}")

    parrafo("Y del Excel, cada fila se convierte en un antecedente con sus "
            "campos reconocidos —N° OT, Falla reportada, Causa raíz— sin "
            "renombrar una sola columna.")
    from nefer.fixmate import ingesta

    fragmento = ingesta.de_archivo(carpeta / "historial-2026.xlsx")[0]
    print()
    for linea in fragmento.texto.splitlines()[:7]:
        print(f"  {linea}")


def demo_indexar(carpeta: Path) -> None:
    """Indexar y reindexar sin releer lo que no cambio."""
    titulo("2 · Indexar, y volver a indexar sin releer nada")
    indexar = ["fixmate", "-i", "{d}/indice.json", "indexar", "{d}"]
    correr(indexar, carpeta)
    parrafo("La segunda pasada no vuelve a leer el manual de cuatrocientas "
            "paginas porque se anadio una orden de trabajo: cada archivo esta "
            "anotado con la huella de su contenido.")
    correr(indexar, carpeta)
    correr(["fixmate", "-i", "{d}/indice.json", "estado"], carpeta)


def demo_consultar(carpeta: Path) -> None:
    """Preguntar por una falla como la describe el mecanico."""
    titulo("3 · Preguntar como se pregunta en el patio")
    parrafo("La consulta no se escribe con las palabras del manual. Se "
            "escribe —o se dicta— como la diria el mecanico que tiene la "
            "maquina delante.")
    correr(["fixmate", "-i", "{d}/indice.json", "consultar",
            "gotea aceite por el cilindro del brazo toda la noche"], carpeta)


def demo_aprendizaje(carpeta: Path) -> None:
    """Cuando el historial entero corrige a la busqueda por palabras."""
    titulo("4 · Lo que dice el historial entero, no solo el mas parecido")
    parrafo("«Humo negro y pierde fuerza» se parece, palabra por palabra, al "
            "informe de un sello de vastago que tambien hacia perder fuerza. "
            "El clasificador ha visto el historial completo y apunta a otra "
            "causa; el motor vuelve al indice a buscar ese antecedente, lo "
            "anade a la evidencia y lo dice.")
    correr(["fixmate", "-i", "{d}/indice.json", "consultar",
            "sale humo negro y pierde fuerza en la subida",
            "--dtc", "P0300"], carpeta)


def demo_prediccion(carpeta: Path) -> None:
    """Ritmo de uso, proximo servicio y lo que le vuelve a pasar."""
    titulo("5 · Que le va a pasar a este equipo")
    parrafo("Sin sensores: con el horometro que el tecnico anota en cada acta "
            "y las fechas de las ordenes de trabajo.")
    correr(["fixmate", "-i", "{d}/indice.json", "predecir", "GE074-01",
            "--hoy", HOY.isoformat()], carpeta)
    correr(["fixmate", "-i", "{d}/indice.json", "predecir", "--flota",
            "--hoy", HOY.isoformat()], carpeta)


def demo_cierre(carpeta: Path) -> None:
    """Registrar la falla resuelta y encontrarla en el acto."""
    titulo("6 · Cerrar el circulo: lo de hoy responde manana")
    parrafo("El tecnico resolvio una falla que el indice no tenia. La "
            "registra desde la misma herramienta y queda buscable en el acto, "
            "sin reindexar: la encuentra el companero que pregunte dentro de "
            "un minuto.")
    correr(["fixmate", "-i", "{d}/indice.json", "cerrar",
            "--falla", "El ventilador no gira y el motor se calienta en dos horas",
            "--causa", "Correa del ventilador partida por polea desalineada",
            "--solucion", "Se cambio la correa y se alineo la polea del alternador",
            "--equipo", "GE074-03", "--repuesto", "Correa 8PK1230",
            "--historial", "{d}/historial-nuevo.json"], carpeta)
    parrafo("Y la falla nueva le gana a la estadistica: el clasificador "
            "aprendio de las averias viejas y no conoce esta todavia, asi que "
            "manda la evidencia recien registrada.")
    correr(["fixmate", "-i", "{d}/indice.json", "consultar",
            "el motor se calienta y el ventilador no gira"], carpeta)


def demo_api(carpeta: Path) -> None:
    """Las respuestas HTTP que consume la app de campo."""
    titulo("7 · La API que consume la app de campo")
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        parrafo("Sin FastAPI instalado esta demo no corre. Instalelo con: "
                "pip install -e \".[fixmate-api]\" y vuelva a intentarlo.")
        return

    from nefer.fixmate import Indice, Motor
    from nefer.fixmate.api import crear_app

    indice = Indice.cargar(carpeta / "indice.json")
    app = crear_app(Motor(indice), ruta_indice=carpeta / "indice.json",
                    ruta_historial=carpeta / "historial-api.json")
    parrafo("Se llama sin levantar servidor, con el cliente de pruebas de "
            "FastAPI. Lo que devuelve es lo mismo que devolveria por HTTP.")
    with TestClient(app) as cliente:
        for metodo, ruta, cuerpo in (
            ("GET", "/salud", None),
            ("POST", "/search-report-rag",
             {"consulta_texto": "fuga de aceite en el cilindro del brazo",
              "limite_resultados": 2}),
            ("GET", "/prediccion/GE074-01", None),
            ("POST", "/search-report-rag",
             {"consulta_texto": "tramites de aduana del contenedor"}),
        ):
            print(f"\n$ curl -X {metodo} localhost:8000{ruta}"
                  + (f" -d '{json.dumps(cuerpo, ensure_ascii=False)}'" if cuerpo else ""))
            respuesta = (cliente.get(ruta) if metodo == "GET"
                         else cliente.post(ruta, json=cuerpo))
            datos = respuesta.json()
            if isinstance(datos, dict):
                datos = {k: v for k, v in datos.items()
                         if k not in ("evidencia_historica", "reincidencias")}
            print(f"  {respuesta.status_code}")
            print("  " + json.dumps(datos, ensure_ascii=False, indent=2)[:700]
                  .replace("\n", "\n  "))
    parrafo("El 404 de la ultima no es una averia: es la respuesta. No hay "
            "antecedentes de eso, y decirlo vale mas que inventar uno.")


def demo_servir(carpeta: Path) -> None:
    titulo("La API, servida de verdad")
    parrafo(f"Indice en {carpeta / 'indice.json'}. Abra "
            "http://127.0.0.1:8000/docs para probarla desde el navegador. "
            "Ctrl-C para parar.")
    correr(["fixmate", "-i", "{d}/indice.json", "servir", "--puerto", "8000"],
           carpeta)


DEMOS = {
    "formatos": demo_formatos,
    "indexar": demo_indexar,
    "consultar": demo_consultar,
    "aprendizaje": demo_aprendizaje,
    "prediccion": demo_prediccion,
    "cierre": demo_cierre,
    "api": demo_api,
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="demo-fixmate",
        description="Demos de FixMate sobre un taller de mentira y comandos de verdad.")
    parser.add_argument("demos", nargs="*", default=[],
                        help=f"cuales correr ({', '.join(DEMOS)}, servir); "
                             "por defecto, todas")
    parser.add_argument("--dir", help="carpeta del taller (por defecto, temporal)")
    parser.add_argument("--conservar", action="store_true",
                        help="no borrar la carpeta al terminar")
    parser.add_argument("--lista", action="store_true", help="listar las demos")
    args = parser.parse_args(argv)

    if args.lista:
        for nombre, funcion in DEMOS.items():
            print(f"  {nombre:<12} {(funcion.__doc__ or '').strip()}")
        return 0

    pedidas = args.demos or list(DEMOS)
    desconocidas = [d for d in pedidas if d not in DEMOS and d != "servir"]
    if desconocidas:
        print(f"No conozco: {', '.join(desconocidas)}. Hay: "
              f"{', '.join(DEMOS)}, servir.", file=sys.stderr)
        return 1

    temporal = None
    if args.dir:
        carpeta = Path(args.dir)
    else:
        temporal = tempfile.mkdtemp(prefix="fixmate-demo-")
        carpeta = Path(temporal)

    try:
        print(f"Taller de mentira en: {carpeta}")
        montar_taller(carpeta)
        # La demo de indexar se encarga ella misma, y ver como lo hace es lo
        # que esa demo ensena. Las demas necesitan el indice ya hecho.
        necesitan = [x for x in pedidas if x not in ("formatos", "indexar")]
        if necesitan and "indexar" not in pedidas \
                and not (carpeta / "indice.json").exists():
            from nefer.fixmate import Indice, actualizar

            indice = Indice()
            actualizar(indice, [carpeta])
            indice.guardar(carpeta / "indice.json")

        for nombre in pedidas:
            if nombre == "servir":
                demo_servir(carpeta)
            else:
                DEMOS[nombre](carpeta)
        print("\n")
        if args.conservar or args.dir:
            print(f"El taller queda en {carpeta}. Pruebe sus propios comandos:")
            print(f"  python3 -m nefer fixmate -i {carpeta / 'indice.json'} "
                  "consultar \"su falla aqui\"")
        return 0
    finally:
        if temporal and not args.conservar:
            shutil.rmtree(temporal, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
