"""Montaje final: dibuja los 1800 cuadros (60 s a 30 fps), añade subtítulos y une audio y video.

Uso:  python3 audio.py && python3 montaje.py [--procesos 4] [--prueba INICIO FIN]
Resultado: salida/Esequibo_TikTok.mp4 (1080×1920, H.264) y salida/esequibo.srt
"""
import argparse
import math
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

from base import acabado, ease_out, fuente, texto
from escenas import AMARILLO, PLANOS
from guion import CLAVE, DURACION, FPS, H, W, bloques_subtitulos

SALIDA = Path(__file__).parent / "salida"
SUBS = bloques_subtitulos()
FLASH = {3.6, 12.4, 19.5, 31.4, 37.8, 55.4}       # cortes con destello blanco


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
            col = AMARILLO if limpio in CLAVE else (255, 255, 255)
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
    byn = fx.get("byn")
    img = acabado(img, i, grano=6 if fx.get("antiguo") else 2.5, vin=0.5, sepia=fx.get("sepia", 0),
                  parpadeo=0.08 if fx.get("antiguo") else 0, rayas=bool(fx.get("antiguo")))
    if byn:
        img = img.convert("L").convert("RGB")
    if ini in FLASH and tl < 0.12:
        a = np.asarray(img).astype(np.float32)
        a = a + (255 - a) * (1 - tl / 0.12)
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
    (SALIDA / "esequibo.srt").write_text("\n".join(lineas), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--prueba", nargs=2, type=float)
    args = ap.parse_args()
    a, b = args.prueba or (0, DURACION)
    cuadros = range(int(a * FPS), int(b * FPS))
    destino = SALIDA / ("prueba.mp4" if args.prueba else "Esequibo_TikTok.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-ss", str(a), "-t", str(b - a), "-i", str(SALIDA / "mezcla.wav"),
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.0:LRA=9", "-ar", "44100",
         "-movflags", "+faststart", "-shortest", str(destino)], stdin=subprocess.PIPE)
    # se dibujan una vez antes de repartir el trabajo (los procesos los heredan)
    import escenas
    from base import granos
    escenas.mapa(), escenas.fondo_selva(), escenas.fondo_tribunal(), escenas.palacio(), granos()
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
