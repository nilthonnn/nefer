"""Mapa de un PDF para crear su nota en la bóveda.

Uso:
  python mapa_pdf.py "Archivos/ComAp/manual.pdf"              -> datos, marcadores y desfase de páginas
  python mapa_pdf.py "Archivos/ComAp/manual.pdf" --buscar "Sync Timeout|Dwell Time"
  python mapa_pdf.py "Archivos/ComAp/manual.pdf" --pagina 94   -> texto de una página
Requiere: pip install pypdf
"""
import argparse, re, sys
try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("Falta pypdf. Instálalo con:  pip install pypdf")

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("--buscar")
ap.add_argument("--pagina", type=int)
a = ap.parse_args()
r = PdfReader(a.pdf)
n = len(r.pages)
texto = lambda i: r.pages[i - 1].extract_text() or ""

if a.pagina:
    print(f"=== Página {a.pagina} de {n}\n{texto(a.pagina)}")
    sys.exit()

if a.buscar:
    pat = re.compile(a.buscar, re.I)
    for i in range(1, n + 1):
        for linea in texto(i).splitlines():
            if pat.search(linea):
                print(f"p. {i:>4} | {linea.strip()[:110]}")
    sys.exit()

m = r.metadata or {}
print(f"Archivo: {a.pdf}\nPáginas del PDF: {n}\nTítulo: {m.get('/Title', '')}\n")

def marcadores(items, nivel=0):
    for it in items:
        if isinstance(it, list):
            marcadores(it, nivel + 1)
        else:
            try:
                print(f"p. {r.get_destination_page_number(it) + 1:>4} | {'  ' * nivel}{it.title}")
            except Exception:
                pass
if r.outline:
    print("Marcadores (página real del PDF):")
    marcadores(r.outline)
else:
    print("El PDF no tiene marcadores: usa el índice impreso y --buscar para hallar la página real.")

# Desfase: compara el número impreso al pie con la página del PDF
desfases = {}
for i in range(5, min(n, 60) + 1, 5):
    lineas = [l.strip() for l in texto(i).splitlines() if l.strip()]
    for l in lineas[-3:] + lineas[:2]:
        mm = re.search(r"(\d{1,4})\s*$", l)
        if mm and abs(int(mm.group(1)) - i) < 40:
            desfases[i - int(mm.group(1))] = desfases.get(i - int(mm.group(1)), 0) + 1
            break
if desfases:
    d = max(desfases, key=desfases.get)
    print(f"\nDesfase estimado: página del PDF = página impresa {'+' if d >= 0 else '-'} {abs(d)}"
          + ("  (coinciden)" if d == 0 else "") + "  -> verifica con --pagina antes de enlazar.")
