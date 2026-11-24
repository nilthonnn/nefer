"""Revisa que todos los [[enlaces]] de la bóveda existan y que las páginas de PDF no pasen del total.

Uso (desde la carpeta de la bóveda):  python .claude/skills/agregar-manual/scripts/revisar_enlaces.py
"""
import glob, os, re, sys
try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("Falta pypdf. Instálalo con:  pip install pypdf")

V = sys.argv[1] if len(sys.argv) > 1 else "."
notas = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f"{V}/**/*.md", recursive=True)}
pdfs = {os.path.basename(p): p for p in glob.glob(f"{V}/**/*.pdf", recursive=True)}
paginas = {}
EJEMPLOS = {"archivo.pdf", "wikilinks"}
malos = 0
for f in glob.glob(f"{V}/**/*.md", recursive=True):
    if os.sep + ".claude" + os.sep in f or "/.claude/" in f:
        continue
    for m in re.finditer(r"\[\[([^\]]+?)\]\]", open(f, encoding="utf-8").read()):
        destino = m.group(1).replace("\\|", "|").split("|")[0]
        nombre, _, pag = destino.partition("#page=")
        if nombre.split("#")[0] in EJEMPLOS:
            continue
        if nombre.lower().endswith(".pdf"):
            if nombre not in pdfs:
                print(f"FALTA PDF   {f}: {destino}"); malos += 1; continue
            if nombre not in paginas:
                paginas[nombre] = len(PdfReader(pdfs[nombre]).pages)
            if pag and not (1 <= int(pag) <= paginas[nombre]):
                print(f"PÁGINA MALA {f}: {destino} (el PDF tiene {paginas[nombre]})"); malos += 1
        elif nombre.split("#")[0] not in notas:
            print(f"FALTA NOTA  {f}: {destino}"); malos += 1
print(f"{'OK' if not malos else 'Revisar'}: {malos} enlaces con problemas.")
