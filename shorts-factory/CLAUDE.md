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
```

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
| `shortsfactory/scripts/` | `generador.py` (Anthropic tool-use / OpenAI JSON Schema + autocorrección), `heuristicas.py` (reglas de retención y YPP). |
| `shortsfactory/audio/` | `motores.py` (Kokoro/Edge/espeak), `alineacion.py` (fonema→palabra), `mezcla.py` (pausas, ducking, -14 LUFS). |
| `shortsfactory/visuals/` | `variacion.py` (diseño generativo anti-repetición), `subtitulos.py`, `broll.py` (Pexels), `render.py` (props → Remotion). |
| `shortsfactory/publisher/` | `auth.py` (OAuth2), `cuota.py`, `seo.py`, `youtube.py` (subida reanudable). |
| `shortsfactory/memory.py` | Historial del canal en `estado/historial.jsonl` (se persiste en CI con caché). |
| `remotion/src/` | `schema.ts` (Zod = contrato de props), `Short.tsx`, `components/*`, `lib/geometria.ts` (puro, probado con node). |
| `../.github/workflows/autopilot.yml` | Cron cada 6 h + manual; pruebas → producir → subir; artefactos de auditoría. |

## Reglas para cambios

- **El contrato Python↔TS** es `visuals/render.py::props()` ↔ `remotion/src/schema.ts`. Cambia los dos a la vez
  y ejecuta `npm test` + la prueba de render.
- **Ninguna cifra inventada**: el guion solo puede decir números de la serie (o variaciones calculadas).
  Si tocas `heuristicas.py`, añade el caso a `tests/test_heuristicas.py`.
- **Errores tipados** (`errors.py`): `ErrorTransitorio` solo para lo que puede resolverse solo (red, 429, 5xx,
  navegador caído). Un 401, una cuota agotada o un guion inválido NO se reintentan.
- **Nunca publicar** guiones `plantilla` ni voz `espeak` (`qa` lo marca y `publicar` lo bloquea).
- **Privacidad por defecto `private`**. No cambies el default a `public`.
- No esquivar cuotas con varios proyectos de Google (prohibido por los ToS de la API).
- Secretos solo por entorno (`SecretStr`); nada de claves en el código, en logs ni en `estado.json`.
- Estilo: identificadores y comentarios en español, como el resto del repo; type hints en todo.

## Pruebas

- Todo lo externo tiene doble: SDK de Anthropic/OpenAI, `requests.Session`, cliente de YouTube, motor de voz.
- Las pruebas que necesitan ffmpeg/espeak/Remotion se saltan solas si faltan; en CI se ejecutan todas.
- `tests/conftest.py` limpia las variables `SF_*`, `YOUTUBE_*`, etc.: lee lo que necesites a nivel de módulo.
