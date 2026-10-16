#!/usr/bin/env python3
"""Descarga los MP3 generados en ElevenLabs y los une en una sola narración.

Lee <proyecto>/trabajo.json (campo "url" de cada parte, que rellena Claude al generar
con el conector de ElevenLabs), descarga cada parte en <proyecto>/audio/parte-NN.mp3,
comprueba que sea un MP3 válido y crea <proyecto>/audio/narracion-completa.mp3.

Uso:
  python3 narracion/descargar.py narracion/proyectos/mi-video [--pausa 1.2]
"""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path


def duracion(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)],
                       capture_output=True, text=True)
    return float(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("proyecto")
    p.add_argument("--pausa", type=float, default=1.2, help="segundos de silencio entre partes")
    args = p.parse_args()

    proyecto = Path(args.proyecto)
    trabajo = json.loads((proyecto / "trabajo.json").read_text(encoding="utf-8"))
    audio = proyecto / "audio"
    audio.mkdir(exist_ok=True)
    faltan, listas = [], []
    for pt in trabajo["partes"]:
        destino = audio / f"{pt['parte']}.mp3"
        if not destino.exists():
            if not pt.get("url"):
                faltan.append(pt["parte"])
                continue
            urllib.request.urlretrieve(pt["url"], destino)
        d = duracion(destino)
        if not d:
            destino.unlink()
            raise SystemExit(f"{destino.name} no es un MP3 válido (¿enlace caducado?). Vuelve a pedir el enlace.")
        pt["duracion"] = round(d, 2)
        listas.append(destino)
        print(f"  {destino.name}  {d:6.1f} s")
    (proyecto / "trabajo.json").write_text(json.dumps(trabajo, ensure_ascii=False, indent=1), encoding="utf-8")
    if faltan:
        raise SystemExit(f"Faltan por generar: {', '.join(faltan)}")

    silencio = audio / "_silencio.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=mono", "-t", str(args.pausa), "-c:a", "libmp3lame", "-b:a", "128k",
                    str(silencio)], check=True)
    lista = audio / "_lista.txt"
    orden = []
    for i, f in enumerate(listas):
        orden.append(f)
        if i < len(listas) - 1:
            orden.append(silencio)
    lista.write_text("".join(f"file '{f.name}'\n" for f in orden))
    completa = audio / "narracion-completa.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    str(lista), "-c:a", "libmp3lame", "-b:a", "160k", str(completa)], check=True)
    lista.unlink()
    silencio.unlink()
    print(f"Listo: {completa} ({duracion(completa) / 60:.1f} min)")


if __name__ == "__main__":
    main()
