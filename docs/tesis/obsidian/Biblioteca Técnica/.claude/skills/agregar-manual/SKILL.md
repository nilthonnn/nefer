---
name: agregar-manual
description: Convierte un manual técnico en PDF (ComAp, Volvo Penta, Stamford, Caterpillar…) en notas de esta bóveda de Obsidian con enlaces a la página exacta. Úsala cuando el usuario diga «agrega este manual», «procesa este PDF», «/agregar-manual archivo.pdf» o deje un PDF nuevo en Archivos/.
---

# Agregar un manual a la Biblioteca Técnica

Entrada: la ruta de un PDF. Si está fuera de la bóveda, cópialo primero a `Archivos/<Marca>/` sin renombrarlo ni modificarlo.

## Pasos
1. **Mapa del PDF**
   `python .claude/skills/agregar-manual/scripts/mapa_pdf.py "Archivos/<Marca>/<archivo>.pdf"`
   Lee la cantidad de páginas, los marcadores y el **desfase** entre la página impresa y la del PDF.
   Los enlaces `#page=N` usan **siempre la página del PDF**, nunca la impresa.
2. **Ubicar los temas** del usuario (por defecto: control de potencia, sincronismo, alarmas, diagnóstico):
   `... mapa_pdf.py "<pdf>" --buscar "Synchron|Alarm|History|Troubleshoot"`
   Lee cada página candidata con `--pagina N` antes de citarla.
3. **Nota del manual** en `<Marca>/Manuales/<Nombre corto>.md`, siguiendo `Plantillas/Manual.md`:
   frontmatter completo (marca, familia, modelo, tipo, versión, año, idioma, páginas, pdf) y una tabla
   «Mapa del documento» con Pág. | Contenido | Tema.
4. **Temas:** agrega lo nuevo en `<Marca>/Temas/*.md` (crea el tema si no existe). Cada dato lleva su origen:
   `[D, [[archivo.pdf#page=N|XX p. N]]]` = del manual · `[I]` = explicación general · `[F]` = pendiente.
5. **Índices:** enlaza la nota nueva desde `<Marca>/00 <Marca>.md` (tabla de manuales) y, si es una marca nueva, desde `00 Índice.md`.
6. **Revisar enlaces:** `python .claude/skills/agregar-manual/scripts/revisar_enlaces.py` debe terminar en `OK: 0`.
7. **Resumen al usuario** en español sencillo: qué páginas son las clave para cada tema y qué quedó como [F].

## Reglas
- **Dentro de una tabla**, el `|` del alias va escapado: `[[archivo.pdf#page=94\|IC p. 94]]`. Fuera de tablas, sin escapar.
- No inventes setpoints, rangos, valores por defecto ni códigos. Si el manual da solo el rango, dilo.
- Si el manual es de otra versión o modelo que el equipo del usuario (su grupo usa InteliGen 200), avísalo en la nota.
- No modifiques los PDF ni `.obsidian/`.
- Escribe en español técnico peruano; deja los nombres de setpoints tal como están en el manual (en inglés).
- Si falta `pypdf`: pide al usuario ejecutar `pip install pypdf`.
