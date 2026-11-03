"""Dibuja pantallas de radar (imágenes propias) para las partes sobre señales y contacto perdido.

Uso: python3 dibujar_radar.py imagenes/
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2400, 1350
F = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def radar(ruta, semilla, ecos, perdido=False):
    rng = np.random.default_rng(semilla)
    im = Image.new("RGB", (W, H), (2, 10, 14))
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    cx, cy, r = W / 2, H / 2, 600
    col = (90, 255, 200)
    for k in range(1, 6):
        rr = r * k / 5
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col + (110,), width=2)
    for a in range(0, 360, 30):
        x, y = cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))
        d.line([(cx, cy), (x, y)], fill=col + (60,), width=1)
    ang = rng.uniform(0, 2 * math.pi)
    for k in range(60):
        a = ang - k * 0.012
        d.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], fill=col + (int(190 * (1 - k / 60)),), width=4)
    for _ in range(ecos):
        a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0.2, 0.9) * r
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(255, 220, 120, 230))
    # ruido de pantalla
    for _ in range(900):
        a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0, 1) * r
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        d.point((x, y), fill=col + (int(rng.uniform(30, 120)),))
    glow = capa.filter(ImageFilter.GaussianBlur(5))
    im.paste(glow, (0, 0), glow)
    im.paste(capa, (0, 0), capa)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(F, 34)
    d.text((140, 120), "RADAR · ATLÁNTICO OCCIDENTAL", font=f, fill=col)
    d.text((140, 170), f"ECOS: {ecos:02d}", font=f, fill=col)
    if perdido:
        d.text((W - 640, 120), "SIN SEÑAL", font=ImageFont.truetype(F, 60), fill=(255, 80, 70))
    im.save(ruta)


destino = Path(sys.argv[1])
radar(destino / "radar_0.png", 1, 5)
radar(destino / "radar_1.png", 2, 0, perdido=True)
radar(destino / "radar_2.png", 3, 2)
print("radares listos")
