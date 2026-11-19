# ShortsFactory-Enterprise — guía para Claude Code

Proyecto independiente dentro del repo `nefer` (no comparte código con `nefer/` ni con `documental/`).
Produce Shorts verticales de ≤ 15 s sobre tecnología y economía, anclados en una serie REAL del
Banco Mundial, y los sube a YouTube. Python 3.11+ (orquestación) + TypeScript/Remotion (render).

## Comandos

```bash
cd shorts-factory
pip install -e ".[dev,llm,youtube,edge]"          # + kokoro: pip install --extra-index-url https://download.pytorch.org/whl/cpu kokoro soundfile
(cd remotion && npm ci)                            # Remotion + zod + fuentes empaquetadas
python -m shortsfactory doctor                     # binarios, claves, Remotion
python -m pytest -q                                # suite rápida (~20 s, sin red)
SF_TEST_RENDER=1 python -m pytest -q -m render     # + render real (~1 min; necesita espeak-ng)
(cd remotion && npm test)                          # tsc + pruebas de lógica pura TS

# run local sin claves (guion de plantilla + voz espeak + serie sintética; NO publicable)
SF_LLM=plantilla SF_TTS=espeak python -m shortsfactory run --topic "Inflación" --serie ejemplos/serie-sintetica.json
python -m shortsfactory run --auto-trend --publicar private
python -m shortsfactory reanudar <run_id>          # continúa en la etapa que falló
python -m shortsfactory run --topic "..." --guion guiones/crisis-semiconductores.json --exigir-publicable
python -m shortsfactory humo                       # 150 fotogramas: Remotion compila y las props pasan Zod (lo que corre en cada PR)
python -m shortsfactory historial bajar|subir --repo ..   # memoria del canal en la rama huérfana estado-produccion
```

CI corre en la imagen `docker/produccion.Dockerfile` (GHCR, etiqueta = hash de Dockerfile + manifiestos;
`.github/workflows/imagen.yml`). Si cambias `requirements.txt` o un `package-lock.json`, la imagen se
reconstruye sola en el primer workflow que la pida.

En este contenedor de Claude Code: Chromium está en `/opt/pw-browsers/...`; pasa
`SF_REMOTION_BROWSER=/opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell`.
La red solo alcanza Anthropic, Google y npm/PyPI: Pexels, Hugging Face, Banco Mundial, GDELT y HN
se prueban con dobles (están en `tests/`), no en vivo.

## Arquitectura

| Ruta | Qué hace |
|---|---|
| `shortsfactory/core/fsm.py` | FSM persistente (`runs/<id>/estado.json`): INICIADO→TENDENCIA→DATOS→GUION→VOZ→VISUALES→RENDER→QA→PUBLICACION→COMPLETADO / FALLIDO. Reintenta solo `ErrorTransitorio`. |
| `shortsfactory/core/pipeline.py` | Un manejador por estado. Sin estado en memoria entre etapas (todo va por `artefactos`). |
| `shortsfactory/sources/` | `worldbank.py` (catálogo de indicadores + descarga), `tendencias.py` (GDELT + Hacker News). |
| `shortsfactory/scripts/` | `generador.py` (Anthropic structured outputs / OpenAI JSON Schema + autocorrección + auto-reparación contra Zod), `heuristicas.py` (reglas de retención y YPP). |
| `shortsfactory/audio/` | `motores.py` (Kokoro/Edge/espeak), `alineacion.py` (fonema→palabra), `mezcla.py` (pausas, ducking, -14 LUFS / -1 dBTP, síntesis concurrente salvo Kokoro). |
| `shortsfactory/visuals/` | `variacion.py` (diseño generativo anti-repetición), `subtitulos.py`, `broll.py` (Pexels), `render.py` (props → Remotion). |
| `shortsfactory/publisher/` | `auth.py` (OAuth2), `cuota.py`, `seo.py`, `youtube.py` (subida reanudable + `thumbnails().set`). |
| `shortsfactory/memory.py` | Historial del canal en `estado/historial.jsonl`: `similitud_tema`, fusión por `run_id`, deduplicación de los últimos 50. |
| `shortsfactory/estado_git.py` | Versiona el historial en la rama huérfana `estado-produccion` (fusiona y reintenta si otro run empujó antes). |
| `shortsfactory/scripts/rapido.py` | Modelo rápido (`claude-haiku-5-5`) con structured outputs: reparar JSON contra Zod y SEO. |
| `shortsfactory/visuals/validacion.py` | Ejecuta el Zod de `schema.ts` con node (`src/lib/validar-props.ts`) sobre props provisionales. |
| `shortsfactory/visuals/miniatura.py` | Miniatura 1280×720 (`remotion still`, composición `Miniatura`) con el dato del gancho. |
| `remotion/src/` | `schema.ts` (Zod = contrato de props), `Short.tsx`, `components/*`, `lib/geometria.ts` (puro, probado con node). |
| `../.github/workflows/autopilot.yml` | Cron cada 6 h (min 17) + manual; pruebas → producir → subir; historial a `estado-produccion`; artefactos 14 días. `modo=muestra` (manual): Short de prueba con guion editorial, sin publicar. |
| `../.github/workflows/pr-checks.yml` | En cada PR: `npm test`, pytest sin red y render de humo (150 fotogramas), en la imagen de GHCR. |

## Reglas para cambios

- **El contrato Python↔TS** es `visuals/render.py::props()` ↔ `remotion/src/schema.ts`. Cambia los dos a la vez
  y ejecuta `npm test` + la prueba de render.
- **Anthropic sin `tool_choice` forzado**: Claude Opus 5.5 lo rechaza con 400. Salida estructurada con
  `output_config.format` y `fallbacks="default"` (beta `server-side-fallback-2026-07-01`). Revisa
  `stop_reason == "refusal"` antes de leer el contenido (`rapido.texto_json`).
- **Ninguna cifra inventada**: el guion solo puede decir números de la serie (o variaciones calculadas).
  Si tocas `heuristicas.py`, añade el caso a `tests/test_heuristicas.py`.
- **Errores tipados** (`errors.py`): `ErrorTransitorio` solo para lo que puede resolverse solo (red, 429, 5xx,
  navegador caído). Un 401, una cuota agotada o un guion inválido NO se reintentan.
- **Nunca publicar** guiones `plantilla`, voz `espeak` ni datos sin fuente verificable (`qa` lo marca y
  `publicar` lo bloquea). Los guiones de `guiones/` deben pasar las heurísticas con la serie subiendo,
  bajando o estable (`tests/test_editorial.py`).
- **Longitud = palabras habladas** (`heuristicas.palabras_habladas`): las cifras cuentan como se pronuncian.
- **Privacidad por defecto `private`**. No cambies el default a `public`.
- No esquivar cuotas con varios proyectos de Google (prohibido por los ToS de la API).
- Secretos solo por entorno (`SecretStr`); nada de claves en el código, en logs ni en `estado.json`.
- Estilo: identificadores y comentarios en español, como el resto del repo; type hints en todo.

## Pruebas

- Todo lo externo tiene doble: SDK de Anthropic/OpenAI, `requests.Session`, cliente de YouTube, motor de voz.
- Las pruebas que necesitan ffmpeg/espeak/Remotion se saltan solas si faltan; en CI se ejecutan todas.
- `tests/conftest.py` limpia las variables `SF_*`, `YOUTUBE_*`, etc.: lee lo que necesites a nivel de módulo.
