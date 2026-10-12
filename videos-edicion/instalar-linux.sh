#!/usr/bin/env bash
# Instalador de herramientas de edición de video para Linux (Ubuntu/Debian/Mint)
# Uso: abre una terminal en esta carpeta y ejecuta:  bash instalar-linux.sh
set -u

sudo apt update
for pkg in ffmpeg shotcut kdenlive obs-studio audacity handbrake vlc gimp python3-pip python3-venv; do
  echo "==> Instalando $pkg..."
  sudo apt install -y "$pkg" || echo "   (no se pudo instalar $pkg, sigue con el resto)"
done

echo "==> Instalando librerías de Python en un entorno propio (.venv)..."
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

echo
echo "Listo. Activa el entorno con:  source .venv/bin/activate"
echo "Opcional: DaVinci Resolve (editor profesional gratis):"
echo "  https://www.blackmagicdesign.com/products/davinciresolve"
