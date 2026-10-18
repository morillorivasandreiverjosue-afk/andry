"""Montaje final: dibuja los cuadros (~1:19 a 30 fps), añade subtítulos y une audio y video.

Uso:  python3 audio.py && python3 montaje.py [--procesos 4] [--prueba INICIO FIN]
Resultado: salida/Edad_Media_TikTok.mp4 (1080×1920, H.264) y salida/edad_media.srt
"""
import argparse
import math
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

from base import acabado, ease_out, fuente, texto
from escenas import ORO, PLANOS
from guion import CLAVE, DURACION, FPS, H, W, bloques_subtitulos

SALIDA = Path(__file__).parent / "salida"
SUBS = bloques_subtitulos()
FLASH = {3.6, 17.5, 20.0, 53.6, 57.8, 69.0, 75.6}     # cortes con destello


def plano_en(t):
    for k in range(len(PLANOS) - 1, -1, -1):
        if t >= PLANOS[k][0]:
            ini, f, fx = PLANOS[k]
            fin = PLANOS[k + 1][0] if k + 1 < len(PLANOS) else DURACION
            return ini, fin, f, fx


def subtitulo(img, t):
    for a, b, palabras in SUBS:
        if a <= t < b:
            break
    else:
        return
    k = ease_out((t - a) / 0.12)
    tam = int(78 * (0.8 + 0.2 * k))
    f = fuente("negra", tam)
    esp = f.getlength(" ")
    anchos = [f.getlength(p.upper()) for p in palabras]
    total = sum(anchos) + esp * (len(palabras) - 1)
    lineas = [palabras]
    if total > W - 160:          # en dos líneas si no cabe
        mitad = len(palabras) // 2 or 1
        lineas = [palabras[:mitad], palabras[mitad:]]
    y0 = 1430 - (len(lineas) - 1) * tam * 0.6
    for j, ln in enumerate(lineas):
        ws = [f.getlength(p.upper()) for p in ln]
        x = W / 2 - (sum(ws) + esp * (len(ln) - 1)) / 2
        for p, w in zip(ln, ws):
            limpio = p.strip("¿?¡!,.:…").lower()
            col = ORO if limpio in CLAVE else (255, 255, 255)
            texto(img, (x, y0 + j * tam * 1.15), p.upper(), f, fill=col, ancla="lm", sombra=8, borde=7,
                  color_borde=(0, 0, 0))
            x += w + esp


def cuadro(i):
    t = i / FPS
    ini, fin, f, fx = plano_en(t)
    tl = t - ini
    img = f(tl, fin - ini)
    # «punch-in» al empezar cada plano + leve sacudida
    z = 1 + 0.09 * (1 - ease_out(tl / 0.3))
    if z > 1.001:
        cw, ch = W / z, H / z
        img = img.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    if fx.get("sacudida") and tl < 1.2:          # golpe de cámara en la batalla
        s = (1 - tl / 1.2) * 18
        img = img.transform(img.size, Image.AFFINE, (1, 0, math.sin(t * 70) * s, 0, 1, math.cos(t * 53) * s),
                            resample=Image.BILINEAR)
    if fx.get("amanecer"):                        # de la oscuridad a la luz
        k = 0.3 + 0.7 * ease_out(tl / 2.4)
        img = Image.fromarray((np.asarray(img).astype(np.float32) * k).astype(np.uint8))
    img = acabado(img, i, grano=3.5, vin=0.55, tinte=(1.06, 0.99, 0.88))
    if ini in FLASH and tl < 0.15:
        a = np.asarray(img).astype(np.float32)
        a = a + (np.array([255, 230, 180]) - a) * (1 - tl / 0.15)
        img = Image.fromarray(a.astype(np.uint8))
    if t < 0.25:                                 # entrada desde negro
        img = Image.fromarray((np.asarray(img) * (t / 0.25)).astype(np.uint8))
    img = img.convert("RGBA")
    subtitulo(img, t)
    return np.asarray(img.convert("RGB")).tobytes()


def srt():
    def tc(x):
        h, r = divmod(x, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    lineas = []
    for k, (a, b, p) in enumerate(SUBS, 1):
        lineas += [str(k), f"{tc(a)} --> {tc(b)}", " ".join(p), ""]
    (SALIDA / "edad_media.srt").write_text("\n".join(lineas), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--prueba", nargs=2, type=float)
    args = ap.parse_args()
    a, b = args.prueba or (0, DURACION)
    cuadros = range(int(a * FPS), int(b * FPS))
    destino = SALIDA / ("prueba.mp4" if args.prueba else "Edad_Media_TikTok.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-ss", str(a), "-t", str(b - a), "-i", str(SALIDA / "mezcla.wav"),
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.0:LRA=9", "-ar", "44100",
         "-movflags", "+faststart", "-shortest", str(destino)], stdin=subprocess.PIPE)
    # se dibujan una vez antes de repartir el trabajo (los procesos los heredan)
    import escenas
    from base import granos
    for _, f, _ in PLANOS:
        f(0.0, 1.0)                               # carga las pinturas y fondos en memoria
    escenas.capa_niebla(), escenas.pergamino(), granos()
    with Pool(args.procesos) as pool:
        for n, datos in enumerate(pool.imap(cuadro, cuadros, chunksize=4)):
            ff.stdin.write(datos)
            if n % 150 == 0:
                print(f"cuadro {n}/{len(cuadros)}", flush=True)
    ff.stdin.close()
    ff.wait()
    srt()
    print("listo:", destino)


if __name__ == "__main__":
    main()
