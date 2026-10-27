"""Paso 3: graba los subtítulos en el video y lo parte en un video por capítulo.

Uso: python3 partir.py [--solo-partes]
Lee salida/EdadMedia_documental.mp4 y salida/edad_media.srt (los deja montaje.py).
Crea salida/EdadMedia_subtitulado.mp4 y salida/por_capitulos/Parte_01_….mp4 … Parte_12_….mp4
"""
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import montaje as M

ESTILO = ("FontName=Liberation Sans,Bold=1,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
          "BackColour=&H80000000,BorderStyle=1,Outline=1.6,Shadow=0.8,Alignment=2,MarginV=12")


def nombre_archivo(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")


def main():
    salida = M.SALIDA
    plan, total = M.linea_de_tiempo()
    _, caps = M.leer_guion()
    completo = salida / "EdadMedia_subtitulado.mp4"
    srt = str(salida / "edad_media.srt").replace(":", r"\:").replace("'", r"\'")
    if "--solo-partes" not in sys.argv:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(salida / "EdadMedia_documental.mp4"),
                        "-vf", f"subtitles='{srt}':force_style='{ESTILO}'",
                        "-c:v", "libx264", "-preset", "medium", "-b:v", "5M", "-maxrate", "6500k",
                        "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                        str(completo)], check=True)
        print("Video completo con subtítulos:", completo, flush=True)
    carpeta = salida / "por_capitulos"
    carpeta.mkdir(exist_ok=True)
    limites = [0.0] + [p["inicio"] for p in plan[1:]] + [total]

    def cortar(i):
        destino = carpeta / f"Parte_{i + 1:02d}_{nombre_archivo(caps[i]['titulo'])}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{limites[i]:.3f}", "-i", str(completo),
                        "-t", f"{limites[i + 1] - limites[i]:.3f}", "-c:v", "libx264", "-preset", "medium",
                        "-b:v", "6M", "-maxrate", "7M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
                        "-af", "afade=t=in:d=0.05", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        str(destino)], check=True)

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(cortar, range(len(caps))))
    print("Partes listas en", carpeta, flush=True)


if __name__ == "__main__":
    main()
