"""Ilustraciones épicas dibujadas con código, para cuando no se puede descargar una pintura.

Cada función devuelve una imagen vertical (AW×AH) con cielo pintado, siluetas y luz cálida.
escenas.pintura() las usa si falta imagenes/<clave>.jpg.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from base import ruido

AW, AH = 1440, 2560


# ------------------------------------------------------------------ fondos
def cielo(arriba, medio, abajo, sol=None, semilla=1, nubes=0.5, horizonte=0.62):
    y = np.linspace(0, 1, AH)[:, None, None]
    a, m, b = (np.array(c, np.float32) for c in (arriba, medio, abajo))
    k1 = np.clip(y / horizonte, 0, 1)
    col = np.where(y < horizonte, a + (m - a) * k1, m + (b - m) * np.clip((y - horizonte) / (1 - horizonte), 0, 1))
    col = np.broadcast_to(col, (AH, AW, 3)).copy()
    if sol:
        sx, sy, r, c = sol
        yy, xx = np.mgrid[0:AH, 0:AW].astype(np.float32)
        d = np.sqrt((xx - sx * AW) ** 2 + (yy - sy * AH) ** 2)
        col += np.array(c, np.float32) * (np.exp(-d / (r * 4)) * 0.9 + (d < r) * 0.6)[..., None]
    if nubes:
        n = ruido(AW // 2, AH // 2, semilla, 6, 3, 0.6)
        n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((AW, AH), Image.BILINEAR)) / 255
        franja = np.exp(-((np.linspace(0, 1, AH) - 0.3) / 0.22) ** 2)[:, None]
        c = np.clip((n - 0.5) * 2.5, 0, 1) * franja * nubes
        col = col * (1 - c[..., None] * 0.55) + np.array(medio, np.float32) * 1.15 * c[..., None] * 0.55
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert("RGBA")


def textura(img, fuerza=18, semilla=5):
    """Textura de lienzo pintado."""
    n = ruido(AW // 2, AH // 2, semilla, 7, 8, 0.65)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((AW, AH), Image.BILINEAR)).astype(np.float32) / 255
    a = np.asarray(img.convert("RGB")).astype(np.float32) + (n[..., None] - 0.5) * fuerza * 2
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def colinas(d, base, amp, color, semilla, pasos=80):
    rng = np.random.default_rng(semilla)
    fases = rng.random(4) * 6
    pts = [(0, AH)]
    for i in range(pasos + 1):
        x = AW * i / pasos
        y = base - amp * (0.5 * math.sin(x / 260 + fases[0]) + 0.3 * math.sin(x / 110 + fases[1])
                          + 0.2 * math.sin(x / 47 + fases[2]))
        pts.append((x, y))
    pts.append((AW, AH))
    d.polygon(pts, fill=color)


def resplandor(img, x, y, r, color, alfa=120):
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).ellipse((x - r, y - r, x + r, y + r), fill=color + (alfa,))
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(r / 2)))


# ------------------------------------------------------------------ siluetas
def torre(d, x, base, ancho, alto, col, techo=True, almenas=False, ventana=None):
    d.rectangle((x - ancho / 2, base - alto, x + ancho / 2, base), fill=col)
    if techo:
        d.polygon([(x - ancho / 2 - 14, base - alto), (x + ancho / 2 + 14, base - alto), (x, base - alto - ancho * 1.5)], fill=col)
        d.line((x, base - alto - ancho * 1.5, x, base - alto - ancho * 1.5 - 60), fill=col, width=5)
        d.polygon([(x, base - alto - ancho * 1.5 - 60), (x + 50, base - alto - ancho * 1.5 - 48), (x, base - alto - ancho * 1.5 - 36)], fill=col)
    if almenas:
        n = max(3, int(ancho / 28))
        for k in range(n):
            if k % 2 == 0:
                xx = x - ancho / 2 + k * ancho / n
                d.rectangle((xx, base - alto - 30, xx + ancho / n, base - alto), fill=col)
    if ventana:
        for k in range(int(alto / 140)):
            yy = base - alto + 80 + k * 140
            d.rounded_rectangle((x - 9, yy, x + 9, yy + 38), 9, fill=ventana)


def castillo(d, cx, base, escala, col, ventana=(255, 190, 90, 255)):
    s = escala
    d.rectangle((cx - 380 * s, base - 260 * s, cx + 380 * s, base), fill=col)                 # muralla
    for k in range(16):
        if k % 2 == 0:
            xx = cx - 380 * s + k * 760 * s / 16
            d.rectangle((xx, base - 290 * s, xx + 760 * s / 16, base - 260 * s), fill=col)
    torre(d, cx - 380 * s, base, 120 * s, 420 * s, col, ventana=ventana)
    torre(d, cx + 380 * s, base, 120 * s, 420 * s, col, ventana=ventana)
    torre(d, cx - 150 * s, base, 140 * s, 640 * s, col, ventana=ventana)
    torre(d, cx + 160 * s, base, 110 * s, 540 * s, col, ventana=ventana)
    torre(d, cx, base, 190 * s, 860 * s, col, ventana=ventana)                                 # torre del homenaje
    d.pieslice((cx - 70 * s, base - 200 * s, cx + 70 * s, base - 60 * s), 180, 360, fill=(30, 20, 10, 255))
    d.rectangle((cx - 70 * s, base - 130 * s, cx + 70 * s, base), fill=(30, 20, 10, 255))


def caballero_pie(d, x, base, s, col, espada=True, escudo=(150, 30, 25, 255), flip=1):
    d.ellipse((x - 30 * s, base - 330 * s, x + 30 * s, base - 260 * s), fill=col)            # yelmo
    d.rectangle((x - 30 * s, base - 300 * s, x + 30 * s, base - 270 * s), fill=col)
    d.polygon([(x - 70 * s, base - 255 * s), (x + 70 * s, base - 255 * s), (x + 55 * s, base - 120 * s),
               (x - 55 * s, base - 120 * s)], fill=col)                                         # torso
    d.polygon([(x - 55 * s, base - 120 * s), (x + 55 * s, base - 120 * s), (x + 75 * s, base - 40 * s),
               (x - 75 * s, base - 40 * s)], fill=col)                                          # faldón
    d.rectangle((x - 45 * s, base - 50 * s, x - 15 * s, base), fill=col)
    d.rectangle((x + 15 * s, base - 50 * s, x + 45 * s, base), fill=col)
    if escudo:
        ex = x - 85 * s * flip
        d.polygon([(ex - 50 * s, base - 240 * s), (ex + 50 * s, base - 240 * s), (ex + 50 * s, base - 160 * s),
                   (ex, base - 90 * s), (ex - 50 * s, base - 160 * s)], fill=escudo)
        d.line((ex, base - 235 * s, ex, base - 110 * s), fill=(230, 190, 90, 255), width=max(2, int(8 * s)))
        d.line((ex - 40 * s, base - 200 * s, ex + 40 * s, base - 200 * s), fill=(230, 190, 90, 255), width=max(2, int(8 * s)))
    if espada:
        sx = x + 80 * s * flip
        d.line((sx, base - 120 * s, sx + 40 * s * flip, base - 440 * s), fill=(200, 200, 210, 255), width=max(3, int(10 * s)))
        d.line((sx - 30 * s, base - 140 * s, sx + 30 * s, base - 125 * s), fill=col, width=max(3, int(12 * s)))


def caballo(d, x, base, s, col, flip=1, galope=0.0):
    f = flip
    d.ellipse((x - 190 * s, base - 330 * s, x + 170 * s, base - 170 * s), fill=col)             # cuerpo
    d.polygon([(x + 120 * f * s, base - 300 * s), (x + 190 * f * s, base - 470 * s), (x + 250 * f * s, base - 450 * s),
               (x + 200 * f * s, base - 260 * s)], fill=col)                                     # cuello
    d.polygon([(x + 190 * f * s, base - 470 * s), (x + 300 * f * s, base - 400 * s), (x + 285 * f * s, base - 375 * s),
               (x + 215 * f * s, base - 410 * s)], fill=col)                                     # cabeza
    d.polygon([(x - 180 * f * s, base - 300 * s), (x - 260 * f * s, base - 200 * s), (x - 230 * f * s, base - 190 * s)], fill=col)  # cola
    for k, dx in enumerate((-140, -90, 90, 130)):
        ang = math.sin(galope + k * 1.7) * 0.35
        x0, y0 = x + dx * s, base - 200 * s
        x1, y1 = x0 + math.sin(ang) * 190 * s, y0 + math.cos(ang) * 190 * s
        d.line((x0, y0, x1, y1), fill=col, width=max(4, int(26 * s)))


def jinete(d, x, base, s, col, lanza=False, flip=1, estandarte=None, galope=0.0):
    caballo(d, x, base, s, col, flip, galope)
    caballero_pie(d, x - 10 * s * flip, base - 230 * s, s * 0.85, col, espada=not lanza, escudo=None, flip=flip)
    if lanza:
        d.line((x - 60 * s * flip, base - 330 * s, x + 520 * s * flip, base - 470 * s), fill=(210, 190, 150, 255),
               width=max(4, int(14 * s)))
    if estandarte:
        px = x - 40 * s * flip
        d.line((px, base - 300 * s, px, base - 780 * s), fill=col, width=max(3, int(10 * s)))
        d.polygon([(px, base - 780 * s), (px - 220 * s * flip, base - 740 * s), (px - 160 * s * flip, base - 700 * s),
                   (px - 220 * s * flip, base - 660 * s), (px, base - 640 * s)], fill=estandarte)


def rey_trono(d, x, base, s, col, oro=(235, 190, 80, 255)):
    d.rectangle((x - 230 * s, base - 900 * s, x + 230 * s, base), fill=(70, 20, 20, 255))         # respaldo
    d.polygon([(x - 230 * s, base - 900 * s), (x, base - 1050 * s), (x + 230 * s, base - 900 * s)], fill=(70, 20, 20, 255))
    d.rectangle((x - 210 * s, base - 880 * s, x + 210 * s, base), outline=oro, width=max(3, int(10 * s)))
    d.ellipse((x - 60 * s, base - 720 * s, x + 60 * s, base - 590 * s), fill=col)                  # cabeza
    d.polygon([(x - 65 * s, base - 700 * s), (x - 65 * s, base - 790 * s), (x - 35 * s, base - 740 * s), (x, base - 800 * s),
               (x + 35 * s, base - 740 * s), (x + 65 * s, base - 790 * s), (x + 65 * s, base - 700 * s)], fill=oro)   # corona
    d.polygon([(x - 200 * s, base - 590 * s), (x + 200 * s, base - 590 * s), (x + 260 * s, base), (x - 260 * s, base)], fill=col)  # manto
    d.polygon([(x - 200 * s, base - 590 * s), (x - 120 * s, base - 590 * s), (x - 170 * s, base), (x - 260 * s, base)], fill=(140, 25, 25, 255))
    d.polygon([(x + 200 * s, base - 590 * s), (x + 120 * s, base - 590 * s), (x + 170 * s, base), (x + 260 * s, base)], fill=(140, 25, 25, 255))
    d.line((x + 160 * s, base - 300 * s, x + 220 * s, base - 820 * s), fill=oro, width=max(3, int(14 * s)))   # cetro
    d.ellipse((x + 195 * s, base - 860 * s, x + 245 * s, base - 810 * s), fill=oro)


def campesino(d, x, base, s, col, herramienta=True, flip=1):
    d.ellipse((x - 26 * s, base - 260 * s, x + 26 * s, base - 208 * s), fill=col)
    d.polygon([(x - 46 * s, base - 270 * s), (x + 46 * s, base - 270 * s), (x, base - 300 * s)], fill=col)   # sombrero
    d.polygon([(x - 45 * s, base - 205 * s), (x + 45 * s, base - 205 * s), (x + 70 * s, base - 60 * s),
               (x - 70 * s, base - 60 * s)], fill=col)
    d.rectangle((x - 40 * s, base - 70 * s, x - 15 * s, base), fill=col)
    d.rectangle((x + 15 * s, base - 70 * s, x + 40 * s, base), fill=col)
    if herramienta:
        hx = x + 60 * s * flip
        d.line((hx, base - 230 * s, hx + 30 * s * flip, base - 20 * s), fill=col, width=max(3, int(9 * s)))
        d.arc((hx - 120 * s, base - 300 * s, hx + 40 * s, base - 160 * s), 180, 300, fill=col, width=max(3, int(8 * s)))


def catedral(d, cx, base, s, col, ventana=(255, 190, 90, 255)):
    for dx in (-200, 200):
        x = cx + dx * s
        d.rectangle((x - 110 * s, base - 1100 * s, x + 110 * s, base), fill=col)
        d.polygon([(x - 110 * s, base - 1100 * s), (x, base - 1600 * s), (x + 110 * s, base - 1100 * s)], fill=col)
        for k in range(4):
            d.pieslice((x - 40 * s, base - 1000 * s + k * 200 * s, x + 40 * s, base - 900 * s + k * 200 * s), 180, 360, fill=ventana)
            d.rectangle((x - 40 * s, base - 950 * s + k * 200 * s, x + 40 * s, base - 860 * s + k * 200 * s), fill=ventana)
    d.rectangle((cx - 120 * s, base - 820 * s, cx + 120 * s, base), fill=col)
    d.ellipse((cx - 90 * s, base - 760 * s, cx + 90 * s, base - 580 * s), fill=ventana)                 # rosetón
    for k in range(8):
        a = k * math.pi / 4
        d.line((cx, base - 670 * s, cx + math.cos(a) * 90 * s, base - 670 * s + math.sin(a) * 90 * s), fill=col, width=max(2, int(8 * s)))
    d.pieslice((cx - 80 * s, base - 420 * s, cx + 80 * s, base - 250 * s), 180, 360, fill=(40, 25, 15, 255))
    d.rectangle((cx - 80 * s, base - 340 * s, cx + 80 * s, base), fill=(40, 25, 15, 255))


def estandarte(d, x, y, alto, color, col_asta):
    d.line((x, y, x, y - alto), fill=col_asta, width=8)
    d.polygon([(x, y - alto), (x + 140, y - alto + 30), (x + 100, y - alto + 70), (x + 140, y - alto + 110),
               (x, y - alto + 120)], fill=color)


# ------------------------------------------------------------------ escenas
NEGRO = (14, 9, 6, 255)


def esc_regreso():
    img = cielo((40, 30, 60), (240, 140, 60), (60, 35, 25), sol=(0.5, 0.52, 90, (255, 170, 80)), semilla=11)
    d = ImageDraw.Draw(img)
    colinas(d, 1650, 120, (60, 35, 30, 255), 1)
    castillo(d, AW / 2, 1520, 0.95, (25, 16, 14, 255))
    colinas(d, 1900, 80, (30, 20, 14, 255), 2)
    for k, x in enumerate((260, 520, 800, 1080)):
        jinete(d, x, 2250 + (k % 2) * 40, 0.55, NEGRO, estandarte=(150, 25, 20, 255) if k % 2 == 0 else None, galope=k)
    colinas(d, 2350, 40, (12, 8, 5, 255), 3)
    resplandor(img, AW / 2, 1330, 300, (255, 160, 70), 90)
    return textura(img)


def esc_godspeed():
    img = cielo((70, 80, 110), (230, 170, 110), (90, 70, 50), sol=(0.75, 0.35, 70, (255, 200, 120)), semilla=12)
    d = ImageDraw.Draw(img)
    colinas(d, 1500, 140, (80, 70, 70, 255), 4)
    castillo(d, 1150, 1450, 0.4, (55, 45, 50, 255))
    colinas(d, 1800, 60, (45, 38, 30, 255), 5)
    jinete(d, 640, 2150, 1.25, NEGRO, estandarte=(170, 30, 25, 255), galope=0.6)
    colinas(d, 2300, 30, (12, 8, 5, 255), 6)
    return textura(img)


def esc_accolade():
    img = cielo((25, 18, 15), (90, 55, 30), (30, 20, 12), semilla=13, nubes=0)
    d = ImageDraw.Draw(img)
    for x in (230, 1210):                                                  # columnas del salón
        d.rectangle((x - 70, 300, x + 70, 2100), fill=(45, 30, 20, 255))
    for x in (520, 920):                                                   # vitrales
        d.pieslice((x - 120, 400, x + 120, 640), 180, 360, fill=(200, 140, 70, 255))
        d.rectangle((x - 120, 520, x + 120, 1100), fill=(200, 140, 70, 255))
    resplandor(img, AW / 2, 800, 500, (255, 170, 80), 80)
    d = ImageDraw.Draw(img)
    for k, x in enumerate((150, 1290)):
        estandarte(d, x, 1500, 900, (150, 25, 20, 255), (40, 25, 15, 255))
    d.rectangle((0, 2100, AW, AH), fill=(25, 15, 10, 255))
    rey_trono(d, 980, 2100, 0.95, NEGRO)
    # caballero arrodillado
    kx, kb = 470, 2100
    d.ellipse((kx - 45, kb - 520, kx + 45, kb - 420), fill=NEGRO)
    d.polygon([(kx - 90, kb - 420), (kx + 90, kb - 420), (kx + 70, kb - 200), (kx - 70, kb - 200)], fill=NEGRO)
    d.polygon([(kx - 70, kb - 200), (kx + 160, kb - 200), (kx + 160, kb - 120), (kx - 70, kb - 120)], fill=NEGRO)
    d.rectangle((kx + 120, kb - 200, kx + 170, kb), fill=NEGRO)
    d.rectangle((kx - 70, kb - 130, kx - 20, kb), fill=NEGRO)
    d.line((kx + 650, kb - 900, kx + 60, kb - 560), fill=(220, 220, 230, 255), width=14)   # espada del rey sobre el hombro
    return textura(img)


def esc_carlomagno():
    img = cielo((20, 12, 10), (110, 60, 25), (30, 18, 10), semilla=14, nubes=0)
    resplandor(img, AW / 2, 1100, 650, (255, 180, 80), 110)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 2050, AW, AH), fill=(35, 20, 12, 255))
    for k in range(5):
        d.rectangle((AW / 2 - 500 + k * 40, 2050 - k * 40, AW / 2 + 500 - k * 40, 2050 - k * 40 + 40), fill=(60 + k * 8, 35, 20, 255))
    estandarte(d, 230, 2000, 1100, (150, 25, 20, 255), (40, 25, 15, 255))
    estandarte(d, 1210, 2000, 1100, (150, 25, 20, 255), (40, 25, 15, 255))
    rey_trono(d, AW / 2, 1850, 1.3, NEGRO)
    return textura(img)


def esc_schinkel():
    img = cielo((50, 60, 100), (250, 170, 90), (40, 50, 70), sol=(0.35, 0.5, 80, (255, 190, 100)), semilla=15)
    d = ImageDraw.Draw(img)
    colinas(d, 1450, 260, (70, 60, 80, 255), 7)
    castillo(d, 760, 1150, 1.0, (30, 22, 28, 255))
    d.rectangle((0, 1560, AW, AH), fill=(40, 45, 60, 255))                        # río
    reflejo = img.crop((0, 400, AW, 1560)).transpose(Image.FLIP_TOP_BOTTOM).resize((AW, AH - 1560))
    reflejo = Image.blend(reflejo, Image.new("RGBA", reflejo.size, (30, 35, 55, 255)), 0.55)
    img.paste(reflejo, (0, 1560))
    d = ImageDraw.Draw(img)
    for k in range(40):
        y = 1580 + k * 24
        d.line((0, y, AW, y + 4), fill=(255, 190, 110, 25), width=2)
    colinas(d, 1600, 40, (25, 20, 22, 255), 8)
    return textura(img)


def esc_destruccion():
    img = cielo((30, 15, 12), (200, 80, 30), (40, 20, 12), sol=(0.5, 0.55, 120, (255, 120, 40)), semilla=16, nubes=0.9)
    d = ImageDraw.Draw(img)
    col = (20, 12, 10, 255)
    for k, x in enumerate(range(140, AW, 230)):                                   # columnas rotas
        alto = [900, 600, 1050, 400, 820, 700, 980][k % 7]
        d.rectangle((x - 50, 2000 - alto, x + 50, 2000), fill=col)
        d.rectangle((x - 70, 2000 - alto - 30, x + 70, 2000 - alto), fill=col)
        d.polygon([(x - 50, 2000 - alto), (x + 50, 2000 - alto - 60), (x + 50, 2000 - alto)], fill=(0, 0, 0, 0))
    d.polygon([(100, 1100), (AW - 100, 1100), (AW / 2, 850)], fill=col)          # frontón del templo
    d.rectangle((0, 2000, AW, AH), fill=(25, 14, 10, 255))
    for k in range(7):
        resplandor(img, 150 + k * 200, 1950 - (k % 3) * 120, 220, (255, 110, 30), 140)
    d = ImageDraw.Draw(img)
    for k in range(10):                                                          # humo
        x = 100 + k * 140
        d.ellipse((x - 160, 400 + (k % 4) * 120, x + 160, 760 + (k % 4) * 120), fill=(30, 20, 18, 70))
    return textura(img)


def esc_enero():
    img = cielo((25, 15, 10), (120, 70, 30), (35, 20, 12), semilla=17, nubes=0)
    d = ImageDraw.Draw(img)
    for x in (240, 720, 1200):                                                   # candelabros
        resplandor(img, x, 600, 260, (255, 180, 80), 120)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 1350, AW, 1500), fill=(120, 30, 25, 255))                  # mantel
    d.rectangle((0, 1490, AW, AH), fill=(40, 22, 14, 255))
    oro = (240, 195, 90, 255)
    for k, x in enumerate(range(140, AW, 230)):                                 # comensales
        y = 1350
        d.ellipse((x - 50, y - 420, x + 50, y - 320), fill=NEGRO)
        d.polygon([(x - 90, y - 320), (x + 90, y - 320), (x + 110, y), (x - 110, y)], fill=NEGRO)
        if k == 3:
            d.polygon([(x - 55, y - 400), (x - 55, y - 470), (x - 25, y - 430), (x, y - 480), (x + 25, y - 430), (x + 55, y - 470), (x + 55, y - 400)], fill=oro)
    for x in range(160, AW, 160):                                              # copas y platos dorados
        d.ellipse((x - 45, 1370, x + 45, 1400), fill=oro)
        d.polygon([(x + 50, 1300), (x + 90, 1300), (x + 80, 1350), (x + 60, 1350)], fill=oro)
    d.polygon([(560, 1340), (880, 1340), (820, 1240), (620, 1240)], fill=(170, 110, 50, 255))   # banquete
    return textura(img)


def esc_junio():
    img = cielo((90, 120, 170), (250, 200, 120), (180, 150, 70), sol=(0.8, 0.3, 90, (255, 220, 140)), semilla=18)
    d = ImageDraw.Draw(img)
    colinas(d, 1250, 100, (100, 110, 120, 255), 9)
    castillo(d, 1050, 1230, 0.35, (90, 90, 110, 255), ventana=None)
    colinas(d, 1450, 60, (180, 150, 60, 255), 10)
    rng = np.random.default_rng(3)
    for _ in range(1400):                                                       # trigo
        x, y = rng.random() * AW, 1450 + rng.random() * 1100
        h = 30 + (y - 1450) / 12
        d.line((x, y, x + rng.uniform(-6, 6), y - h), fill=(int(200 + rng.random() * 40), int(160 + rng.random() * 40), 60, 255), width=3)
    for k, x in enumerate((300, 640, 980, 1220)):
        campesino(d, x, 2200 + (k % 2) * 60, 1.4 - 0.15 * (k % 2), (40, 28, 18, 255), flip=1 if k % 2 else -1)
    return textura(img)


def esc_octubre():
    img = cielo((60, 80, 120), (230, 180, 120), (110, 90, 60), sol=(0.25, 0.4, 60, (255, 210, 140)), semilla=19)
    d = ImageDraw.Draw(img)
    colinas(d, 1400, 160, (70, 70, 90, 255), 11)
    castillo(d, AW / 2, 1300, 1.0, (45, 40, 50, 255))
    d.rectangle((AW / 2 - 450, 1300, AW / 2 + 450, 1380), fill=(60, 70, 90, 255))     # foso
    colinas(d, 1700, 50, (90, 75, 45, 255), 12)
    for k, x in enumerate((360, 1080)):
        caballero_pie(d, x, 2100, 1.1, NEGRO, flip=1 if k else -1)
    colinas(d, 2300, 30, (25, 18, 10, 255), 13)
    return textura(img)


def esc_torneo():
    img = cielo((90, 120, 170), (240, 200, 140), (120, 100, 60), semilla=20)
    d = ImageDraw.Draw(img)
    for k in range(12):                                                         # gradas con banderas
        x = k * 130
        d.rectangle((x, 1150, x + 120, 1450), fill=(110, 40, 30, 255) if k % 2 else (40, 50, 110, 255))
        d.polygon([(x + 60, 1050), (x + 120, 1150), (x, 1150)], fill=(200, 160, 70, 255))
    d.rectangle((0, 1450, AW, AH), fill=(140, 115, 70, 255))
    d.rectangle((0, 1700, AW, 1760), fill=(90, 50, 30, 255))                     # valla central
    jinete(d, 360, 2150, 0.95, NEGRO, lanza=True, flip=1, galope=0.4)
    jinete(d, 1080, 2000, 0.85, (35, 20, 15, 255), lanza=True, flip=-1, galope=2.0)
    return textura(img)


def esc_batalla():
    img = cielo((50, 30, 30), (210, 110, 50), (60, 35, 25), sol=(0.6, 0.45, 100, (255, 150, 60)), semilla=21, nubes=0.9)
    d = ImageDraw.Draw(img)
    colinas(d, 1500, 120, (60, 40, 35, 255), 14)
    for k in range(30):                                                         # lanzas del ejército
        x = 40 + k * 48
        d.line((x, 1700, x + 30, 1100 - (k % 5) * 40), fill=(30, 20, 15, 255), width=6)
    colinas(d, 1750, 60, (35, 22, 18, 255), 15)
    for k, x in enumerate((220, 520, 860, 1180)):
        estandarte(d, x, 1800, 700, (160, 25, 20, 255) if k % 2 else (30, 50, 120, 255), (25, 15, 10, 255))
    jinete(d, 420, 2250, 1.0, NEGRO, flip=1, galope=1.0)
    caballero_pie(d, 1050, 2300, 1.3, NEGRO, flip=-1)
    for k in range(8):
        resplandor(img, 100 + k * 180, 1650, 150, (255, 120, 40), 90)
    return textura(img)


def esc_ciudad():
    img = cielo((110, 150, 200), (250, 220, 170), (170, 140, 100), sol=(0.7, 0.25, 70, (255, 230, 160)), semilla=22)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    for k in range(9):                                                          # casas
        x = k * 165
        h = rng.integers(500, 900)
        col = (int(150 + rng.random() * 60), int(110 + rng.random() * 50), int(80 + rng.random() * 40), 255)
        d.rectangle((x, 1500 - h, x + 160, 1500), fill=col)
        d.polygon([(x - 10, 1500 - h), (x + 170, 1500 - h), (x + 80, 1500 - h - 160)], fill=(120, 50, 35, 255))
        for j in range(3):
            d.rectangle((x + 40, 1500 - h + 80 + j * 150, x + 80, 1500 - h + 150 + j * 150), fill=(60, 40, 30, 255))
    d.rectangle((0, 1500, AW, AH), fill=(150, 125, 95, 255))
    colores = [(180, 40, 30, 255), (40, 80, 150, 255), (200, 160, 50, 255), (40, 110, 60, 255)]
    for k, x in enumerate((180, 560, 940, 1300)):                               # puestos del mercado
        d.polygon([(x - 170, 1650), (x + 170, 1650), (x + 140, 1520), (x - 140, 1520)], fill=colores[k])
        d.rectangle((x - 150, 1650, x + 150, 1820), fill=(110, 75, 45, 255))
        for j in range(5):
            d.ellipse((x - 130 + j * 55, 1600, x - 90 + j * 55, 1640), fill=(220, 130 + j * 20, 40, 255))
    for k, x in enumerate((120, 330, 700, 820, 1100, 1350)):                   # gente
        campesino(d, x, 2250 + (k % 3) * 40, 1.15, (40 + k * 6, 28, 22, 255), herramienta=False)
    return textura(img)


def esc_universidad():
    img = cielo((30, 20, 14), (120, 80, 40), (40, 26, 16), semilla=23, nubes=0)
    d = ImageDraw.Draw(img)
    for x in (360, 1080):
        d.pieslice((x - 150, 300, x + 150, 600), 180, 360, fill=(220, 180, 110, 255))
        d.rectangle((x - 150, 450, x + 150, 1100), fill=(220, 180, 110, 255))
    resplandor(img, AW / 2, 800, 500, (255, 200, 120), 70)
    d = ImageDraw.Draw(img)
    d.rectangle((AW / 2 - 220, 1150, AW / 2 + 220, 1500), fill=(70, 40, 25, 255))     # cátedra
    caballero_pie(d, AW / 2, 1300, 0.9, NEGRO, espada=False, escudo=None)
    d.rectangle((AW / 2 - 120, 1080, AW / 2 + 40, 1120), fill=(235, 220, 180, 255))   # libro
    for fila in range(3):
        for k in range(5):
            x = 180 + k * 270 + (fila % 2) * 60
            campesino(d, x, 1950 + fila * 220, 1.0, (25 + fila * 5, 16, 10, 255), herramienta=False)
            d.rectangle((x - 80, 1950 + fila * 220 - 90, x + 80, 1950 + fila * 220 - 60), fill=(80, 50, 30, 255))
    return textura(img)


def esc_catedral():
    img = cielo((80, 110, 170), (250, 200, 140), (140, 110, 80), sol=(0.5, 0.3, 80, (255, 220, 150)), semilla=24)
    d = ImageDraw.Draw(img)
    catedral(d, AW / 2, 1950, 1.05, (70, 60, 65, 255))
    # andamios de la obra
    for x in (AW / 2 - 330, AW / 2 + 330):
        for k in range(6):
            d.line((x - 130, 1950 - k * 250, x + 130, 1950 - k * 250), fill=(110, 80, 50, 255), width=8)
        for dx in (-130, 0, 130):
            d.line((x + dx, 1950, x + dx, 500), fill=(110, 80, 50, 255), width=8)
    d.line((AW / 2 + 500, 1950, AW / 2 + 500, 300), fill=(90, 60, 40, 255), width=14)          # grúa
    d.line((AW / 2 + 500, 300, AW / 2 + 150, 420), fill=(90, 60, 40, 255), width=12)
    d.rectangle((0, 1950, AW, AH), fill=(120, 100, 75, 255))
    for k, x in enumerate((200, 520, 900, 1230)):
        campesino(d, x, 2300, 1.1, (45, 32, 22, 255), herramienta=k % 2 == 0)
    return textura(img)


def esc_kells():
    """Manuscrito iluminado (inspirado en el estilo insular), con letra capital y nudos dorados."""
    a = np.array([228, 205, 155], np.float32) * (0.85 + 0.25 * ruido(AW, AH, 25, 6, 4, 0.6))[..., None]
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    oro, rojo, azul, verde = (215, 165, 60, 255), (170, 40, 30, 255), (40, 70, 140, 255), (50, 110, 70, 255)
    d.rectangle((120, 160, AW - 120, AH - 160), outline=rojo, width=24)
    d.rectangle((170, 210, AW - 170, AH - 210), outline=oro, width=12)
    for k in range(60):                                                         # cenefa de nudos
        for x, y in ((150 + k * 20, 185), (150 + k * 20, AH - 185)):
            if x < AW - 150:
                d.arc((x - 12, y - 12, x + 12, y + 12), 0 if k % 2 else 180, 180 if k % 2 else 360, fill=azul, width=6)
    cx, cy = AW / 2, 1050
    for r, c in ((520, rojo), (470, oro), (420, azul), (360, verde)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=26)
    for k in range(12):
        ang = k * math.pi / 6
        d.line((cx, cy, cx + math.cos(ang) * 340, cy + math.sin(ang) * 340), fill=oro, width=14)
    d.ellipse((cx - 120, cy - 120, cx + 120, cy + 120), fill=rojo)
    d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), fill=oro)
    for k in range(14):                                                         # texto manuscrito ilegible
        y = 1750 + k * 48
        pts = [(260 + i * 6, y + 6 * math.sin(i * 0.9 + k)) for i in range(int((AW - 520) / 6))]
        d.line(pts, fill=(60, 40, 30, 200), width=3)
    return textura(img, 10)


ESCENAS = {
    "regreso": esc_regreso, "godspeed": esc_godspeed, "accolade": esc_accolade, "carlomagno": esc_carlomagno,
    "schinkel": esc_schinkel, "destruccion": esc_destruccion, "enero": esc_enero, "junio": esc_junio,
    "octubre": esc_octubre, "torneo": esc_torneo, "san_romano": esc_batalla, "ciudad": esc_ciudad,
    "universidad": esc_universidad, "catedral": esc_catedral, "kells": esc_kells, "partida": esc_regreso,
}
