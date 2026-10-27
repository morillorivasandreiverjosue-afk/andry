"""Paso 3: graba los subtítulos en el video y lo parte en un video por capítulo.

Uso: python3 partir.py <carpeta_salida> [video] [--solo-partes]
El video de entrada por defecto es <salida>/Pompeya_documental.mp4 (el que deja montaje.py).
Crea <salida>/Pompeya_subtitulado.mp4 y <salida>/por_capitulos/Parte_01_….mp4 … Parte_09_….mp4
"""
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import montaje as M

ESTILO = ("FontName=Liberation Sans,Bold=1,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
          "BackColour=&H80000000,BorderStyle=1,Outline=1.6,Shadow=0.8,Alignment=2,MarginV=12")


def nombre_archivo(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")


def main():
    salida = Path(sys.argv[1]).resolve()
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    entrada = Path(args[0]).resolve() if args else salida / "Pompeya_documental.mp4"
    M.SALIDA = salida
    plan, total = M.linea_de_tiempo(salida)
    _, caps = M.leer_guion()
    M.srt(plan, caps)
    # cortes: la parte 1 incluye la portada y la última el cierre
    cortes = [p["inicio"] for p in plan[1:]]
    completo = salida / "Pompeya_subtitulado.mp4"
    srt = str(salida / "pompeya.srt").replace(":", r"\:").replace("'", r"\'")
    if "--solo-partes" not in sys.argv:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(entrada),
                        "-vf", f"subtitles='{srt}':force_style='{ESTILO}'",
                        "-c:v", "libx264", "-preset", "medium", "-b:v", "5300k", "-maxrate", "6500k",
                        "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                        str(completo)], check=True)
        print("Video completo con subtítulos:", completo, flush=True)
    carpeta = salida / "por_capitulos"
    carpeta.mkdir(exist_ok=True)
    limites = [0.0] + cortes + [total]
    # cada parte se vuelve a codificar para cortar en el fotograma exacto
    procesos = []
    for i, cap in enumerate(caps):
        destino = carpeta / f"Parte_{i + 1:02d}_{nombre_archivo(cap['titulo'])}.mp4"
        procesos.append(subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{limites[i]:.3f}", "-i", str(completo),
             "-t", f"{limites[i + 1] - limites[i]:.3f}", "-c:v", "libx264", "-preset", "medium",
             "-b:v", "6M", "-maxrate", "7M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
             "-af", "afade=t=in:d=0.05", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             str(destino)]))
        if len(procesos) == 3:
            procesos.pop(0).wait()
    for pr in procesos:
        pr.wait()
    print("Partes listas en", carpeta, flush=True)

if __name__ == "__main__":
    main()
