#!/bin/bash
# Instala todo lo necesario para editar y crear videos (videos-edicion/).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# FFmpeg y fuentes que usan los generadores de video
faltan=()
command -v ffmpeg >/dev/null 2>&1 || faltan+=(ffmpeg)
fc-list 2>/dev/null | grep -qi "Inter" || faltan+=(fonts-inter)
fc-list 2>/dev/null | grep -qi "Caladea" || faltan+=(fonts-crosextra-caladea)
fc-list 2>/dev/null | grep -qi "FreeSerif" || faltan+=(fonts-freefont-ttf)
fc-list 2>/dev/null | grep -qi "Noto Color Emoji" || faltan+=(fonts-noto-color-emoji)
if [ ${#faltan[@]} -gt 0 ]; then
  (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${faltan[@]}") \
    || echo "Aviso: no se pudieron instalar con apt: ${faltan[*]}" >&2
fi

# Paquetes de Python
pip install -q --break-system-packages -r videos-edicion/requirements.txt 2>/dev/null \
  || pip install -q -r videos-edicion/requirements.txt

# Voz de Piper en español (respaldo gratuito cuando no se usa ElevenLabs)
voz=videos-edicion/proyectos/bolivar/voz
if [ ! -f "$voz/es-carlfm-x-low.onnx" ]; then
  mkdir -p "$voz"
  tmp=$(mktemp -d)
  if curl -fsSL -o "$tmp/voz.tgz" https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-es-carlfm-x-low.tar.gz; then
    tar xzf "$tmp/voz.tgz" -C "$voz"
  else
    echo "Aviso: no se pudo descargar la voz de Piper" >&2
  fi
  rm -rf "$tmp"
fi
