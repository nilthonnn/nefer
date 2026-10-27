# documental: fábrica de documentales para YouTube

Convierte un guion (JSON o Markdown), o directamente un tema usando Claude, en
un documental 16:9 listo para subir: narración con **ElevenLabs** en español
latino, video de stock buscado con **MoneyPrinterTurbo**, infografías animadas
con **Remotion**, subtítulos dinámicos, música con *ducking* y todo el paquete
de publicación (miniatura, descripción con capítulos, SRT, metadatos y una
auditoría de monetización).

Es un proyecto independiente de `nefer`: no comparte código ni dependencias con él.

```
tema ──(Claude)──► guion.json ──► revisión humana
                                        │
       ┌────────────────────────────────┘
       ▼
  ┌─────────┐   ┌───────────────┐   ┌──────────────────────────────┐
  │ entrada │──►│ voz por escena│──►│ línea de tiempo (la voz manda)│
  └─────────┘   │  ElevenLabs   │   └──────────────┬───────────────┘
                │ +tiempos/palab│                  ▼
                └───────────────┘   ┌──────────────────────────────┐
                                    │ visual por escena (selector)  │
                                    │  stock ─► MoneyPrinterTurbo   │
                                    │  cifra/línea/comparativa/     │
                                    │  titular/final ─► Remotion    │
                                    │  respaldo ─► tarjetas Pillow  │
                                    └──────────────┬───────────────┘
                                                   ▼
   auditoría ◄── montaje ffmpeg: xfade + ASS + voz/música (-14 LUFS) ──► MP4
       │                                                                 │
       └──────► miniatura · descripción con capítulos · SRT · metadatos ◄┘
```

## Qué produce

`salidas/<slug>/`

| Archivo | Para qué |
|---|---|
| `<slug>.mp4` | H.264 High 1080p30 con AAC de 48 kHz y 384 kbps a −14 LUFS, con `faststart` (los parámetros que recomienda YouTube) |
| `miniatura.jpg` | 1280×720 y menos de 2 MB: fotograma de stock oscurecido con 2 a 4 palabras grandes |
| `descripcion.txt` | Descripción, capítulos (`00:00 …`), fuentes, créditos de stock y música, y hashtags |
| `subtitulos.srt` | Se sube como subtítulos en español (Latinoamérica); ayuda al SEO y a la accesibilidad |
| `metadatos.json` | Título, etiquetas (máximo 500 caracteres), capítulos y atribuciones |
| `auditoria.md` | Bloqueos y avisos de monetización (ver más abajo) |
| `render.log.jsonl` | Log completo, incluidos los comandos de ffmpeg (nivel DEBUG) |
| `trabajo/` | Intermedios con clave de contenido; permiten **reanudar** sin volver a pagar la voz |

## Requisitos

- Python 3.11 o superior, **ffmpeg/ffprobe** (con libass) y Node.js 18 o superior.
- Una cuenta de **ElevenLabs** con plan de pago (las licencias comerciales empiezan en el plan Starter).
- Claves gratuitas de **Pexels** y/o **Pixabay** para el video de stock.
- Opcional: `espeak-ng`, para vistas previas sin gastar créditos, y una clave de **Anthropic** para escribir guiones.

## Instalación

```bash
cd documental
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,guion]"

# MoneyPrinterTurbo (MIT): se usa como biblioteca, en el MISMO entorno
git clone https://github.com/harry0703/MoneyPrinterTurbo.git ../../MoneyPrinterTurbo
pip install -r ../../MoneyPrinterTurbo/requirements.txt

# Remotion (infografías animadas)
(cd remotion && npm install)

cp .env.example .env    # y rellénalo
python -m documental diagnostico
```

`diagnostico` muestra con ✔ o ✘ cada herramienta, clave y componente.

### Variables de entorno (`.env`)

| Variable | Obligatoria | Descripción |
|---|---|---|
| `ELEVENLABS_API_KEY` | para publicar | Clave de la API |
| `ELEVENLABS_VOICE_ID` | para publicar | Voz con acento latino (Voice Library → *Spanish* + *Latin American*) |
| `ELEVENLABS_MODEL` | no | `eleven_multilingual_v2` por defecto: la mejor prosodia para narración larga |
| `MPT_DIR` | para stock | Ruta al clon de MoneyPrinterTurbo |
| `PEXELS_API_KEY` / `PIXABAY_API_KEY` | para stock | Al menos una de las dos |
| `REMOTION_DIR` | no | Por defecto `documental/remotion` |
| `REMOTION_BROWSER` | no | Chrome headless propio (si no se indica, Remotion descarga el suyo) |
| `ANTHROPIC_API_KEY` | para `guion` | Escritura de guiones con Claude |
| `CLAUDE_MODEL` | no | `claude-opus-5-5` por defecto |
| `DOCUMENTAL_SALIDA` | no | Carpeta de salida (por defecto `./salidas`) |
| `DOCUMENTAL_LOG` | no | `DEBUG` muestra cada comando de ffmpeg |

La identidad del canal y los parámetros técnicos (resolución, ajustes de la
voz, LUFS, estilo de subtítulos, umbrales de monetización) están en
`config/canal.toml`. Ese archivo no contiene secretos.

## Tu primer video

```bash
# 1. Vista previa gratis: voz local robótica, solo sirve para revisar el ritmo y los cortes
python -m documental render ejemplos/historia-panel-solar.json --previa

# 2. Versión publicable con ElevenLabs (mismo comando, sin --previa)
python -m documental render ejemplos/historia-panel-solar.json
```

Si el proceso se interrumpe, vuelve a ejecutar el mismo comando: continúa
donde se quedó.

### Con un tema, usando Claude

```bash
python -m documental guion "La guerra de las corrientes: Tesla contra Edison" \
    -o guiones/guerra-corrientes.json --minutos 10 --notas mis-notas.txt
# REVISA el guion: comprueba los datos, ajusta el tono y añade tu experiencia
python -m documental validar guiones/guerra-corrientes.json
python -m documental render guiones/guerra-corrientes.json --estricto
```

### En lote (cola en disco)

```bash
python -m documental cola agregar guiones/*.json
python -m documental cola procesar          # hasta vaciar la cola
python -m documental cola estado
python -m documental cola reintentar        # devuelve los fallidos a pendiente
```

Los fallos transitorios (red, 429, 5xx, caída de Chrome) se reintentan dentro
de cada llamada con espera exponencial y, además, el trabajo vuelve a la cola
hasta 2 veces. Los fallos definitivos, como una clave inválida o un guion
roto, van directos a `fallido/` con el error y la traza completos.

## Formato del guion

Cada escena tiene una **narración** (lo que dice la voz) y un **visual**. La
duración de cada escena la decide la voz, nunca el guion.

| `visual.tipo` | Origen | Datos |
|---|---|---|
| `stock` | MoneyPrinterTurbo (Pexels/Pixabay) | `busqueda`: 2 o 3 términos **en inglés** y fáciles de filmar |
| `titular` | Remotion | `antetitulo`, `titulo` |
| `cifra` | Remotion | `valor`, `prefijo`, `sufijo`, `decimales`, `etiqueta`, `fuente` |
| `linea_tiempo` | Remotion | `titulo`, `hitos: [{anio, texto}]` |
| `comparativa` | Remotion | `titulo`, `unidad`, `barras: [{etiqueta, valor}]`, `fuente` |
| `imagen` | Foto o ilustración propia con efecto Ken Burns | `ruta` (relativa al guion) |
| `final` | Pantalla final de 20 s con huecos para los elementos de YouTube | se añade sola si falta |

Hay ejemplos en `ejemplos/`: uno en JSON y otro en Markdown, que es más cómodo
para escribir a mano.

## Pensado para monetizar

YouTube no monetiza el **contenido no auténtico**, es decir, el producido en
masa o repetitivo, ni el material reutilizado que no aporta nada propio. El
sistema está diseñado para aportar valor y para avisarte cuando no lo hace.
`auditoria.md` revisa lo siguiente:

- **Bloqueos.** Si la voz es de vista previa, si un clip de stock se repite o
  si el guion se parece más de un 45 % a otro video del canal. Con
  `--estricto`, el render se detiene.
- **Avisos.**
  - Duración menor de 8 minutos (sin anuncios a mitad del video).
  - Capítulos que YouTube no aceptaría (menos de 3, o alguno de menos de 10 s).
  - Menos del 25 % de las escenas con visual propio.
  - Escenas que usaron un visual de respaldo.
  - Guion sin fuentes.
  - Ritmo de narración fuera de 120 a 185 palabras por minuto.

Esto, además, va integrado en el producto:

- Subtítulos dinámicos con la palabra resaltada, sincronizados con los tiempos que devuelve ElevenLabs.
- Gancho al inicio, capítulos y pantalla final, ya contemplados en el prompt del guionista.
- Música atenuada automáticamente bajo la voz y sonoridad a −14 LUFS.
- Créditos de stock y de música en la descripción.

Antes de subir:
1. Revisa y personaliza el guion. Tu criterio es lo que lo hace auténtico.
2. Usa solo música con licencia, por ejemplo de la Biblioteca de audio de YouTube (ver `assets/musica/LEEME.md`).
3. Marca «Contenido alterado o sintético» solo si muestras personas o hechos realistas que no ocurrieron.

La auditoría no garantiza la aprobación: la decide una persona en YouTube.

## Decisiones de integración

- **MoneyPrinterTurbo** se importa como biblioteca desde `MPT_DIR` y aporta su
  capa de material: búsqueda filtrada por orientación y resolución, descargas
  validadas con caché y el autor de cada clip. Sus claves se inyectan en
  memoria y no se escribe nada en su `config.toml`.
- **La voz no pasa por MoneyPrinterTurbo**, porque su TTS de ElevenLabs no
  devuelve la alineación por palabra. Se usa directamente el endpoint
  `/with-timestamps`, enviando las frases vecinas (`previous_text`/`next_text`)
  para que la entonación sea continua.
- **Remotion** renderiza cada infografía por separado y ffmpeg las normaliza
  igual que el stock. Si Remotion no está instalado, se usan tarjetas Pillow
  con la misma paleta.
- **Sincronía:** la escena *i* empieza en la suma de los tramos anteriores. Su
  clip dura un tramo más el tiempo de la transición, que se solapa con la
  siguiente escena, así que los fundidos nunca desplazan la imagen respecto
  de la voz.

## Pruebas

```bash
pytest -q
```

Las pruebas de integración renderizan videos de verdad a 320×180 y se saltan
solas si faltan ffmpeg o espeak-ng. MoneyPrinterTurbo y Claude se prueban con
dobles, de modo que no hace falta red.

## Licencias

- MoneyPrinterTurbo tiene licencia MIT.
- Remotion es gratis para personas y empresas de hasta 3 empleados; por
  encima de eso requiere licencia de empresa (ver remotion.dev/license).
- Los clips de Pexels y Pixabay se pueden usar comercialmente; la atribución
  no es obligatoria, pero se incluye igualmente.
