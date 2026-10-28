# ShortsFactory-Enterprise

Shorts verticales de **≤ 15 s** sobre tecnología y economía, de punta a punta y sin
intervención: tendencia → dato real → guion → voz → video → control de calidad → YouTube.

Cada Short se ancla en una **serie real del Banco Mundial**. El gráfico se dibuja con esos
números y el guion no puede decir ninguna cifra que no salga de ahí. Eso es lo que aporta valor
propio y lo que separa este sistema de una granja de clips.

```
--topic / --auto-trend (GDELT + Hacker News)
        │
        ▼
 ┌───────────────── FSM persistente (runs/<id>/estado.json) ─────────────────┐
 │ TENDENCIA → DATOS (Banco Mundial) → GUION (Claude/OpenAI + heurísticas)   │
 │   → VOZ (Kokoro/Edge, tiempos por palabra) → VISUALES (Pexels opcional)   │
 │   → RENDER (Remotion 1080×1920, 30/60 fps) → QA (ffprobe, -14 LUFS)       │
 │   → PUBLICACION (YouTube Data API v3, OAuth2, cuota) → COMPLETADO         │
 └──────── reintentos solo en errores transitorios · reanudable ─────────────┘
```

## Qué hace cada pieza

| Requisito | Implementación |
|---|---|
| Orquestación con FSM | `core/fsm.py`: transiciones validadas, estado atómico en disco y una política de reintentos por etapa. `reanudar` continúa en la etapa que falló. |
| Ganchos de 0–3 s, bucles abiertos y loop | `scripts/heuristicas.py`: gancho de 10 palabras o menos con cifra, pregunta o contraste; promesa en las 2 primeras frases; última frase abierta que enlaza con el gancho. El fondo animado es periódico, así que el último fotograma coincide con el primero. |
| LLM | Claude (tool use) u OpenAI (JSON Schema estricto). Si el guion no pasa las heurísticas, se le devuelve al modelo con los problemas, hasta 2 rondas. |
| Voz con timestamps | Kokoro (Apache-2.0): en español reconstruyo los tiempos por palabra a partir de la duración de cada **fonema** (Kokoro solo los da por palabra en inglés). Edge TTS: eventos `WordBoundary`. |
| Subtítulos estilo Hormozi | De 1 a 3 palabras, con la palabra activa en caja, *pop* o subrayado, y las palabras de énfasis (las elige el LLM) en color de acento. |
| Variabilidad generativa | `visuals/variacion.py`: 10 paletas con contraste WCAG ≥ 4,5, 6 tipografías, 3 estilos de subtítulos, 3 fondos, 2 gráficos, 3 transiciones, intensidad de movimiento, velocidad de voz y pausas. Se elige la combinación más distinta de las 12 anteriores. |
| Gráficos de mercado | Línea que se dibuja o barras que crecen con la serie real, y una cifra protagonista que cuenta desde cero. |
| Publicador | OAuth2 con refresco automático, contabilidad de cuota en hora del Pacífico, subida reanudable con *backoff*, SEO con límites de YouTube y `containsSyntheticMedia`. |
| CI/CD | `.github/workflows/autopilot.yml`: cada 6 h o a mano. Ejecuta las pruebas, produce, sube y guarda la memoria del canal y los artefactos de auditoría. |

## Lo que conviene saber antes de automatizar la publicación

- **Ningún sistema garantiza un 85 % de VTR.** Este aplica las prácticas con efecto conocido
  (gancho, densidad, loop, cambio de plano en cada frase, subtítulos), pero el VTR real solo se
  mide en YouTube Analytics. Mídelo y ajusta las heurísticas con tus datos.
- **El YPP lo decide una persona.** Las políticas de contenido «no auténtico»
  (producido en masa o repetitivo) miran el canal en conjunto. Que la paleta o la
  tipografía cambien no hace original un video: lo que lo hace original es el dato y el
  ángulo. Por eso aquí hay memoria anti-repetición de temas, textos, indicadores, diseños y
  b-roll, y se rechaza cualquier cifra inventada.
- **Por defecto se sube como privado.** Te recomiendo revisar cada Short en YouTube Studio
  antes de publicarlo, al menos al principio. Cambiarlo es una decisión tuya
  (variable `SF_PUBLICAR`).
- **Proyectos de API sin auditar:** YouTube deja como privados los videos subidos por
  proyectos que no pasaron la auditoría de la API, aunque pidas `public`.
- **Cuota:** con la cuota por defecto (10 000 unidades) y 1600 por subida caben 6 subidas al
  día. El cron de cada 6 h usa 4. Usar varios proyectos para esquivar la cuota está prohibido.
- **Voz:** Kokoro tiene licencia Apache-2.0 y es apta para monetizar. Edge TTS usa un
  servicio sin licencia comercial explícita, así que revisa sus términos.
- **No es asesoría financiera:** el validador bloquea «compra», «invierte», «ganancias
  seguras», etc., y la descripción lo aclara.

## Instalación local

```bash
cd shorts-factory
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,llm,youtube,edge]"
pip install --extra-index-url https://download.pytorch.org/whl/cpu kokoro soundfile   # voz Kokoro
sudo apt-get install ffmpeg espeak-ng          # macOS: brew install ffmpeg espeak-ng
(cd remotion && npm ci)
cp .env.example .env                           # y rellénalo
python -m shortsfactory doctor
```

## Primer Short

```bash
# Sin ninguna clave (guion de plantilla, voz espeak y serie sintética). Sirve para comprobar
# la instalación; NO es publicable y el sistema lo bloquea.
SF_LLM=plantilla SF_TTS=espeak python -m shortsfactory run --topic "Inflación" --serie ejemplos/serie-sintetica.json

# Real, sin subir:
python -m shortsfactory run --topic "La crisis de los semiconductores"

# Guion EDITORIAL (escrito por una persona; las cifras las pone la serie real):
python -m shortsfactory run --topic "La crisis de los semiconductores" \
    --guion guiones/crisis-semiconductores.json --exigir-publicable

# Real, tendencia automática, subida como privado:
python -m shortsfactory run --auto-trend --publicar private
```

Cada run deja en `runs/<id>/`: `short.mp4`, `guion.json`, `estado.json` (la FSM con
artefactos y reintentos) y `auditoria.jsonl` (el log estructurado).

## El filtro de publicación

Un Short solo es **publicable** si cumple todo esto (si no, `PUBLICACION` lo bloquea y
`--exigir-publicable` sale con código 4):

| Regla | Por qué |
|---|---|
| Guion de LLM o **editorial** (nunca de plantilla) | Una plantilla repetida es justo el «contenido producido en masa» que YouTube no monetiza |
| Pasa todas las heurísticas (gancho, bucle, loop, cifras de la serie, sin consejos de inversión, sin parecerse a Shorts anteriores) | Retención y veracidad |
| Cabe en 15 s contando **palabras habladas** («18,5%» son 5) | Si la voz no cabe, se corta el loop o se acelera de forma artificial |
| Voz publicable (Kokoro o Edge; nunca espeak) | Calidad y licencia |
| Datos verificables: API del Banco Mundial o archivo con la URL de su fuente | Cualquiera debe poder comprobar el dato |
| QA del MP4: 1080×1920, fps, audio, ≤ 15 s y −14 LUFS ± 1,5 | Calidad técnica |

Los **guiones editoriales** (`guiones/*.json`) son la vía más sólida: el ángulo y las frases
son de autoría humana, y las cifras salen de la serie mediante huecos (`{ultimo}`,
`{anio_primero}`, `{verbo}`...), así nunca quedan mal copiadas. En cada PR, el job `muestra`
produce uno real (Kokoro + Banco Mundial) y falla si no sale publicable; el MP4 queda como
artefacto.

## YouTube: configuración (una vez)

1. En Google Cloud, crea un proyecto y habilita **YouTube Data API v3**.
2. En la pantalla de consentimiento OAuth, añade tu cuenta y **publícala en producción**.
   En modo *Testing* el refresh token caduca a los 7 días y el autopiloto deja de subir.
3. Crea credenciales **OAuth → App de escritorio** y descarga el JSON.
4. En local: `YOUTUBE_CLIENT_SECRET="$(cat client_secret.json)" python -m shortsfactory auth`
   y copia el refresh token que imprime.

## GitHub Actions

En *Settings → Secrets and variables → Actions*:

| Secreto | Valor |
|---|---|
| `ANTHROPIC_API_KEY` (u `OPENAI_API_KEY`) | Clave del LLM |
| `YOUTUBE_CLIENT_SECRET` | Contenido del JSON del cliente OAuth |
| `YOUTUBE_REFRESH_TOKEN` | El valor que imprimió `auth` |
| `PEXELS_API_KEY` | Opcional (b-roll) |

| Variable (opcional) | Por defecto |
|---|---|
| `SF_PUBLICAR` | `private` (`unlisted`, `public`, `no`) |
| `SF_LLM`, `SF_LLM_MODELO` | `anthropic`, `claude-opus-5-5` |
| `SF_TTS`, `SF_KOKORO_VOZ` | `kokoro`, `em_alex` |

Para generar un Short de prueba sin publicar nada: Actions → `shortsfactory-autopilot` →
**Run workflow** con `modo = muestra` (y, si quieres, otro `guion` editorial). Corre el mismo
job que en los PR: Kokoro, datos del Banco Mundial y `--exigir-publicable`; el MP4 queda como artefacto.

El workflow corre cada 6 h (minuto 17) o a mano, con tema y destino. Cada ejecución guarda la
memoria del canal en caché y sube como artefacto el video, el estado, el guion y los logs
(14 días). Si la cuota está agotada, termina con un aviso y no lo cuenta como fallo.

## Pruebas

```bash
python -m pytest -q                              # 71 pruebas, sin red (dobles para LLM, HTTP, YouTube y voz)
SF_TEST_RENDER=1 python -m pytest -q -m render   # render real de punta a punta
(cd remotion && npm test)                        # tipos + lógica pura en TypeScript
```
