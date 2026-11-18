# syntax=docker/dockerfile:1.7
# Imagen de producción y CI de shorts-factory y documental.
#
# Trae todo lo que antes se instalaba en cada job: Python con las
# dependencias de los dos proyectos, PyTorch CPU + Kokoro con sus pesos y dos
# voces, Node.js, los node_modules de los dos proyectos de Remotion, Chromium
# headless y FFmpeg. Los workflows la descargan de GHCR con una etiqueta que
# es el hash de este archivo y de los manifiestos de dependencias
# (.github/workflows/imagen.yml): si nada cambió, no se reconstruye.
#
# Contexto de build: la raíz del repositorio.
#   docker build -f docker/produccion.Dockerfile -t nefer-produccion .

ARG PYTHON_VERSION=3.12
ARG NODE_VERSION=22

# --- 1. node_modules de Remotion y navegador headless ---------------------------
FROM node:${NODE_VERSION}-bookworm-slim AS remotion
WORKDIR /opt/remotion
COPY shorts-factory/remotion/package.json shorts-factory/remotion/package-lock.json shorts-factory/
COPY documental/remotion/package.json documental/remotion/package-lock.json documental/
RUN cd shorts-factory && npm ci --no-audit --no-fund \
 && cd ../documental && npm ci --no-audit --no-fund
# Chrome headless shell de la misma versión que espera Remotion. Se deja en
# una ruta fija para no depender de dónde lo guarde cada versión.
RUN cd shorts-factory && npx --no-install remotion browser ensure \
 && binario="$(find node_modules/.remotion -type f -name chrome-headless-shell -perm -u+x | head -n1)" \
 && test -n "$binario" \
 && mkdir -p /opt/chrome \
 && cp -a "$(dirname "$binario")/." /opt/chrome/

# --- 2. Python: dependencias, PyTorch CPU y Kokoro ------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS python
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends espeak-ng \
 && rm -rf /var/lib/apt/lists/*
COPY shorts-factory/requirements.txt /tmp/sf-requirements.txt
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r /tmp/sf-requirements.txt \
 && /opt/venv/bin/pip install "pillow>=10.0" \
 && /opt/venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu "kokoro>=0.7.16" "soundfile>=0.12"
# Pesos del modelo y las dos voces (em_alex y la de contraste ef_dora) dentro
# de la imagen: ningún job vuelve a bajarlos de Hugging Face.
ENV HF_HOME=/opt/hf
RUN /opt/venv/bin/python - <<'PY'
from kokoro import KPipeline

pipe = KPipeline(lang_code="e", repo_id="hexgrad/Kokoro-82M")
for voz in ("em_alex", "ef_dora"):
    pipe.load_voice(voz)
    audio = next(iter(pipe("Prueba de voz.", voice=voz))).audio
    assert audio is not None and len(audio) > 0, f"Kokoro no generó audio con {voz}"
print("Kokoro listo")
PY

# --- 3. Imagen final --------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm
LABEL org.opencontainers.image.source="https://github.com/nilthonnn/nefer" \
      org.opencontainers.image.description="CI y producción de shorts-factory y documental"
# ffmpeg de Debian trae libass, freetype y libx264 (subtítulos, drawtext, H.264).
# Las bibliotecas de abajo son las que pide Chrome headless (lista de Remotion).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg espeak-ng git ca-certificates fontconfig fonts-dejavu-core fonts-inter \
      libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libgbm1 libasound2 libxrandr2 \
      libxkbcommon0 libxfixes3 libxcomposite1 libxdamage1 libpango-1.0-0 libcairo2 libcups2 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=remotion /usr/local/bin/node /usr/local/bin/node
COPY --from=remotion /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY --from=remotion /opt/remotion /opt/remotion
COPY --from=remotion /opt/chrome /opt/chrome
COPY --from=python /opt/venv /opt/venv
COPY --from=python /opt/hf /opt/hf
COPY docker/enlazar-node-modules.sh /usr/local/bin/enlazar-node-modules
RUN chmod +x /usr/local/bin/enlazar-node-modules
ENV PATH=/opt/venv/bin:$PATH \
    HF_HOME=/opt/hf \
    PYTHONUNBUFFERED=1 \
    SF_REMOTION_BROWSER=/opt/chrome/chrome-headless-shell \
    REMOTION_BROWSER=/opt/chrome/chrome-headless-shell
# Comprobación de humo de la imagen: si falta algo, el build falla aquí y no
# en mitad de un render.
RUN ffmpeg -hide_banner -filters | grep -qw subtitles \
 && ffmpeg -hide_banner -filters | grep -qw drawtext \
 && ffmpeg -hide_banner -encoders | grep -qw libx264 \
 && node --version && npx --version \
 && /opt/chrome/chrome-headless-shell --version \
 && python -c "import kokoro, soundfile, anthropic, googleapiclient, PIL"
