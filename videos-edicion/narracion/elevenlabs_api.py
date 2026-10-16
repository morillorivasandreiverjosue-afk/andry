#!/usr/bin/env python3
"""Genera la narración directamente con la API de ElevenLabs (para usar en TU computadora).

Necesita la variable de entorno ELEVENLABS_API_KEY. Usa siempre el voice_id de
voz.json (o el que pases con --voice-id) y nunca lo cambia por otro: si la voz no
existe o falla, se detiene con el error.

Uso:
  python3 narracion/preparar.py mi_guion.txt -o narracion/proyectos/mi-video
  python3 narracion/elevenlabs_api.py narracion/proyectos/mi-video
  python3 narracion/descargar.py narracion/proyectos/mi-video
"""
import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
API = "https://api.elevenlabs.io/v1"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("proyecto")
    p.add_argument("--voice-id", help="usar esta voz en lugar de la de voz.json (no se sustituye por otra)")
    args = p.parse_args()

    clave = os.environ.get("ELEVENLABS_API_KEY")
    if not clave:
        raise SystemExit("Falta la variable de entorno ELEVENLABS_API_KEY.")
    voz = json.loads((AQUI / "voz.json").read_text(encoding="utf-8"))
    proyecto = Path(args.proyecto)
    trabajo = json.loads((proyecto / "trabajo.json").read_text(encoding="utf-8"))
    voice_id = args.voice_id or trabajo["voice_id"]
    ajustes = voz["api_directa"]
    audio = proyecto / "audio"
    audio.mkdir(exist_ok=True)

    for pt in trabajo["partes"]:
        destino = audio / f"{pt['parte']}.mp3"
        if destino.exists():
            print(f"  {destino.name} ya existe, se omite")
            continue
        cuerpo = {"text": pt["texto"], "model_id": voz["modelo"], "voice_settings": ajustes["voice_settings"]}
        if voz.get("idioma"):
            cuerpo["language_code"] = voz["idioma"]
        req = urllib.request.Request(
            f"{API}/text-to-speech/{voice_id}?output_format={ajustes['formato']}",
            data=json.dumps(cuerpo).encode(), method="POST",
            headers={"xi-api-key": clave, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                destino.write_bytes(r.read())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"ElevenLabs rechazó {pt['parte']} (HTTP {e.code}): {e.read().decode(errors='replace')[:500]}")
        print(f"  {destino.name} generado con la voz {voice_id}")
    print("Ahora ejecuta descargar.py para unir las partes.")


if __name__ == "__main__":
    main()
