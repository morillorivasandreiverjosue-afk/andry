"""Paso 3: graba los subtítulos en el video y lo parte en un video por capítulo.

Uso: python3 partir.py <carpeta_salida> [video]
El video de entrada por defecto es <salida>/Pompeya_final.mp4 (el que deja montaje.py).
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
    entrada = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else salida / "Pompeya_final.mp4"
    M.SALIDA = salida
    plan, total = M.linea_de_tiempo(salida)
    _, caps = M.leer_guion()
    M.srt(plan, caps)
    # cortes: la parte 1 incluye la portada y la última el cierre
    cortes = [p["inicio"] for p in plan[1:]]
    completo = salida / "Pompeya_subtitulado.mp4"
    srt = str(salida / "pompeya.srt").replace(":", r"\:").replace("'", r"\'")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(entrada),
                    "-vf", f"subtitles='{srt}':force_style='{ESTILO}'",
                    "-c:v", "libx264", "-preset", "medium", "-b:v", "5300k", "-maxrate", "6500k", "-bufsize", "12M",
                    "-force_key_frames", ",".join(f"{c:.3f}" for c in cortes),
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(completo)], check=True)
    print("Video completo con subtítulos:", completo, flush=True)
    carpeta = salida / "por_capitulos"
    carpeta.mkdir(exist_ok=True)
    limites = [0.0] + cortes + [None]
    for i, cap in enumerate(caps):
        destino = carpeta / f"Parte_{i + 1:02d}_{nombre_archivo(cap['titulo'])}.mp4"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{limites[i]:.3f}", "-i", str(completo)]
        if limites[i + 1] is not None:
            cmd += ["-t", f"{limites[i + 1] - limites[i]:.3f}"]
        subprocess.run(cmd + ["-c", "copy", "-avoid_negative_ts", "make_zero", "-movflags", "+faststart",
                              str(destino)], check=True)
        print("Parte lista:", destino.name, flush=True)


if __name__ == "__main__":
    main()
