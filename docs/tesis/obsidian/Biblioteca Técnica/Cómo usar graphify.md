---
tags: [herramientas, claude-code]
---
# Cómo usar graphify
[graphify](https://github.com/Graphify-Labs/graphify) convierte una carpeta (notas, PDF, código) en un **grafo de conocimiento**: un mapa de conceptos y de cómo se conectan, que se puede abrir en el navegador (`graph.html`) y consultar desde Claude Code sin releer todas las notas.

## Instalar en tu PC (una sola vez)
1. Necesitas **Python 3.10 o más nuevo**. En la terminal de VS Code: `python --version`.
2. Instala la herramienta `uv` y luego graphify:
   ```
   pip install uv
   uv tool install graphifyy
   ```
   (Son dos «y» en `graphifyy`: así se llama el paquete oficial.)
3. La skill ya está en esta bóveda (`.claude/skills/graphify/`). No hace falta `graphify install`.

## Usar
En Claude Code, con la carpeta de la bóveda abierta:
- `/graphify .` → construye el grafo. Crea `graphify-out/` con:
  - `graph.html`: el mapa interactivo (ábrelo con doble clic);
  - `GRAPH_REPORT.md`: los conceptos centrales y conexiones sorprendentes;
  - `graph.json`: el grafo completo.
- Después, preguntas rápidas:
  - `graphify explain "Sincronismo"` → el concepto y todo lo que se conecta con él;
  - `graphify path "Phase Window" "NPR"` → cómo se une un tema con otro;
  - `graphify query "¿qué alarmas afectan la disponibilidad?"`.

## Para estudiar con TDAH
El `graph.html` es un **mapa visual** del curso: los temas centrales salen grandes y los grupos de colores muestran qué conceptos van juntos. Úsalo como repaso visual antes del «Repaso de hoy» del Aula ComAp.

## Avisos
- **Costo:** leer notas y PDF usa tokens de tu plan de Claude. Por eso `.graphifyignore` deja fuera `Archivos/` (los PDF de cientos de páginas). Hoy la bóveda tiene unas 9 000 palabras; el propio graphify dice que aún no es indispensable. Vale más cuando agregues más manuales.
- **No se instalaron los hooks** que trae graphify: sirven para proyectos de código y darían error si el programa no está instalado.
- Graphify ofrece una versión de pago en la nube (Graphify Cloud). **No la necesitas**: todo lo de esta nota es gratis y local.
