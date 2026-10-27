"""Paso 3: graba los subtítulos en el video y lo parte en clips de alrededor de un minuto.

Uso: python3 partir.py [--solo-partes]
Lee salida/EdadMedia_documental.mp4 (montaje.py) y salida/edad_media_sincronizado.srt (alinear.py).
Crea salida/EdadMedia_subtitulado.mp4 y salida/por_minuto/Parte_01.mp4, Parte_02.mp4…
Cada corte cae en la pausa entre dos subtítulos más cercana al minuto, para no partir ninguna frase.
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import montaje as M

ESTILO = ("FontName=Liberation Sans,Bold=1,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
          "BackColour=&H80000000,BorderStyle=1,Outline=1.6,Shadow=0.8,Alignment=2,MarginV=12")


DURACION = 60.0  # segundos por clip


def segundos(marca):
    h, m, s = marca.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def pausas_subtitulos(ruta):
    """Centros de los huecos entre subtítulos consecutivos."""
    tiempos = [tuple(segundos(x) for x in linea.split(" --> "))
               for linea in ruta.read_text(encoding="utf-8").splitlines() if " --> " in linea]
    return [(fin + ini) / 2 for (_, fin), (ini, _) in zip(tiempos, tiempos[1:])]


def puntos_de_corte(pausas, total):
    cortes, t = [], 0.0
    while total - t > DURACION * 1.4:
        objetivo = t + DURACION
        cerca = [p for p in pausas if abs(p - objetivo) <= 10]
        t = min(cerca, key=lambda p: abs(p - objetivo)) if cerca else objetivo
        cortes.append(t)
    return cortes


def main():
    salida = M.SALIDA
    plan, total = M.linea_de_tiempo()
    completo = salida / "EdadMedia_subtitulado.mp4"
    # los subtítulos sincronizados con la voz (alinear.py) si existen; si no, los aproximados de montaje.py
    archivo_srt = salida / "edad_media_sincronizado.srt"
    if not archivo_srt.exists():
        archivo_srt = salida / "edad_media.srt"
    srt = str(archivo_srt).replace(":", r"\:").replace("'", r"\'")
    if "--solo-partes" not in sys.argv:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(salida / "EdadMedia_documental.mp4"),
                        "-vf", f"subtitles='{srt}':force_style='{ESTILO}'",
                        "-c:v", "libx264", "-preset", "medium", "-b:v", "5M", "-maxrate", "6500k",
                        "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                        str(completo)], check=True)
        print("Video completo con subtítulos:", completo, flush=True)
    carpeta = salida / "por_minuto"
    carpeta.mkdir(exist_ok=True)
    limites = [0.0] + puntos_de_corte(pausas_subtitulos(archivo_srt), total) + [total]

    def cortar(i):
        destino = carpeta / f"Parte_{i + 1:02d}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{limites[i]:.3f}", "-i", str(completo),
                        "-t", f"{limites[i + 1] - limites[i]:.3f}", "-c:v", "libx264", "-preset", "medium",
                        "-b:v", "6M", "-maxrate", "7M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
                        "-af", "afade=t=in:d=0.05", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        str(destino)], check=True)

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(cortar, range(len(limites) - 1)))
    print("Partes listas en", carpeta, flush=True)


if __name__ == "__main__":
    main()
