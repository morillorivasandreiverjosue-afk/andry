#!/bin/bash
# Instala las herramientas para crear y editar videos en las sesiones de Claude Code en la nube.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# ffmpeg (motor de audio y video)
if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq ffmpeg >/dev/null
fi

# Librerías de Python: edición rápida (moviepy) y generador de documentales (voz, sonido, mapas)
pip install -q --root-user-action=ignore \
  -r videos-edicion/requirements.txt \
  -r videos-edicion/proyectos/napoleon/requirements.txt

# Modelos de voz Kokoro (español), solo si no están ya descargados
MODELOS="videos-edicion/modelos"
URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
mkdir -p "$MODELOS"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ ! -s "$MODELOS/$f" ]; then
    curl -sSfL -o "$MODELOS/$f.tmp" "$URL/$f" && mv "$MODELOS/$f.tmp" "$MODELOS/$f"
  fi
done

echo "export KOKORO_MODELOS=\"$CLAUDE_PROJECT_DIR/$MODELOS\"" >> "${CLAUDE_ENV_FILE:-/dev/null}"
