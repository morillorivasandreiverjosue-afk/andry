#!/usr/bin/env bash
# Instalador de herramientas de edición de video para macOS (usa Homebrew)
# Uso: abre Terminal en esta carpeta y ejecuta:  bash instalar-mac.sh
set -u

if ! command -v brew >/dev/null 2>&1; then
  echo "==> Instalando Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

echo "==> Instalando FFmpeg y Python..."
brew install ffmpeg python

for app in shotcut kdenlive obs audacity handbrake vlc gimp; do
  echo "==> Instalando $app..."
  brew install --cask "$app" || echo "   (no se pudo instalar $app, sigue con el resto)"
done

echo "==> Instalando librerías de Python..."
python3 -m pip install --user -r "$(dirname "$0")/requirements.txt"

echo
echo "Listo. Opcional: DaVinci Resolve (editor profesional gratis):"
echo "  https://www.blackmagicdesign.com/products/davinciresolve"
