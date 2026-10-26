# Instrucciones para Claude Code en esta bóveda
Biblioteca de manuales técnicos (empezando por ComAp). Español técnico peruano.
- Enlaza con [[wikilinks]] y a páginas de PDF con [[archivo.pdf#page=N]]. Verifica el número de página en el PDF antes de escribirlo.
- Marca el origen: [D] dato del manual (con página), [I] explicación general, [F] pendiente.
- No inventes setpoints, rangos ni códigos: si no están en el manual, márcalos [F].
- Cada manual nuevo: PDF en Archivos/<Marca>/, nota en <Marca>/Manuales/ con la plantilla Manual, y enlace en el índice de la marca y en los temas.
- No modifiques .obsidian/ ni los PDF.
- En tablas, escapa el alias: [[archivo.pdf#page=N\|p. N]].

## Skills de esta bóveda
- `/agregar-manual <ruta.pdf>` — procesa un manual nuevo (mapa de páginas, nota, temas, revisión de enlaces).
- `/repasar [tema]` — simulacro de preguntas con calificación 1–5 y páginas para releer.
- `/tutor` — curso por capítulos estilo Harvard (≥ 80 % para avanzar); progreso en `Repasos/Progreso ComAp.md`.
- Revisión rápida de enlaces: `python .claude/skills/agregar-manual/scripts/revisar_enlaces.py`
- Los scripts necesitan `pip install pypdf`.

## graphify
- Skill instalada en `.claude/skills/graphify/` (requiere `uv tool install graphifyy` en la PC). Uso: `/graphify .` para construir el grafo de conceptos de la bóveda; luego `graphify query "<pregunta>"`, `graphify path "<A>" "<B>"` y `graphify explain "<concepto>"`.
- Cuando exista `graphify-out/graph.json`, consulta el grafo antes de leer muchas notas, y vuelve a la nota y a la página del PDF para citar datos.
- `.graphifyignore` excluye `Archivos/` (PDF) y `Repasos/`. Solo incluir PDF si el usuario lo pide: cuesta muchos tokens.
- No se instalaron los hooks de graphify (son para código y fallan si el programa no está instalado).
