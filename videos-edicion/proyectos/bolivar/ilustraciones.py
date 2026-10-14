#!/usr/bin/env python3
"""Paso 2: dibuja las ilustraciones del documental (paisajes, batallas, documentos, retratos).

Todas se generan por código (no usan fotos de internet) y se guardan en build/img/<nombre>.png
a 2304x1296 (un poco más grandes que 1080p para poder hacer zoom lento "Ken Burns").

Si quieres usar una imagen real en lugar de una ilustración, pon un archivo con el mismo
nombre en proyectos/bolivar/imagenes/ (por ejemplo imagenes/retrato.jpg) y se usará esa.
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "build" / "img"
W0, H0 = 2304, 1296
SS = 2  # supersampling para siluetas suaves

F = {
    "serif": "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf",
    "serif_b": "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf",
    "serif_i": "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf",
    "serif_bi": "/usr/share/fonts/truetype/crosextra/Caladea-BoldItalic.ttf",
    "libre_i": "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
    "sans": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "sans_b": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
}


def fuente(clave, tam):
    try:
        return ImageFont.truetype(F[clave], int(tam))
    except OSError:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", int(tam))


# ======================= ruido y fondos =======================

def ruido2d(w, h, escala, octavas=4, semilla=0):
    rng = np.random.default_rng(semilla)
    total = np.zeros((h, w))
    amp, peso = 1.0, 0.0
    for o in range(octavas):
        gw, gh = max(2, int(w / escala * 2 ** o)), max(2, int(h / escala * 2 ** o))
        g = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8))
        total += amp * np.asarray(g.resize((w, h), Image.BICUBIC), float) / 255
        peso += amp
        amp *= 0.5
    return total / peso


def ruido1d(n, escala, octavas=5, semilla=0):
    rng = np.random.default_rng(semilla)
    x = np.arange(n)
    total = np.zeros(n)
    amp, peso = 1.0, 0.0
    for o in range(octavas):
        paso = max(2, escala / 2 ** o)
        pts = rng.random(int(n / paso) + 3)
        total += amp * np.interp(x / paso, np.arange(len(pts)), pts)
        peso += amp
        amp *= 0.5
    return total / peso


def gradiente(paradas, h=H0, w=W0):
    """paradas: [(posición 0..1, (r,g,b)), ...] de arriba a abajo."""
    y = np.linspace(0, 1, h)
    pos = [p for p, _ in paradas]
    canal = [np.interp(y, pos, [c[k] for _, c in paradas]) for k in range(3)]
    col = np.stack(canal, axis=-1)[:, None, :]
    return np.repeat(col, w, axis=1).astype(float)


def mezclar(img, color, alfa):
    """img HxWx3 float; alfa HxW (0..1) o escalar."""
    a = alfa[..., None] if np.ndim(alfa) == 2 else alfa
    return img * (1 - a) + np.array(color, float) * a


def nubes(img, y0, y1, color, densidad=0.5, semilla=1, escala=500, fuerza=0.85):
    h, w = img.shape[:2]
    n = ruido2d(w, h, escala, 5, semilla)
    n = np.clip((n - (1 - densidad) * 0.75) / 0.3, 0, 1) ** 1.5
    y = np.linspace(0, 1, h)[:, None]
    banda = np.clip((y - y0) / 0.08, 0, 1) * np.clip((y1 - y) / 0.12, 0, 1)
    return mezclar(img, color, n * banda * fuerza)


def resplandor(img, cx, cy, radio, color, fuerza=1.0):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radio
    a = np.exp(-d ** 2 * 1.6) * fuerza
    return np.clip(img + np.array(color, float) * a[..., None], 0, 255)


def disco(img, cx, cy, r, color):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    a = np.clip(r - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2), 0, 1.5) / 1.5
    return mezclar(img, color, a)


def estrellas(img, n=500, semilla=3, hasta=0.6):
    rng = np.random.default_rng(semilla)
    h, w = img.shape[:2]
    for _ in range(n):
        x, y = rng.integers(0, w), rng.integers(0, int(h * hasta))
        b = rng.random() ** 3
        img[y, x] = np.clip(img[y, x] + 255 * b, 0, 255)
        if b > 0.6 and 0 < x < w - 1 and 0 < y < h - 1:
            img[y - 1:y + 2, x] = np.clip(img[y - 1:y + 2, x] + 90 * b, 0, 255)
            img[y, x - 1:x + 2] = np.clip(img[y, x - 1:x + 2] + 90 * b, 0, 255)
    return img


def montes(img, base, amp, color, semilla, escala=500, nieve=None, filo=1.0):
    """Cordillera: base y amp en fracción de la altura."""
    h, w = img.shape[:2]
    r = ruido1d(w, escala, 6, semilla)
    r = (r - r.min()) / (r.max() - r.min() + 1e-9)
    r = r ** filo
    cresta = (base - amp * r) * h
    yy = np.arange(h)[:, None]
    a = np.clip(yy - cresta[None, :], 0, 1.5) / 1.5
    img = mezclar(img, color, a)
    if nieve is not None:
        alto = (base - amp * 0.62) * h
        prof = np.clip((yy - cresta[None, :]) / (h * amp * 0.12), 0, 1)
        m = a * (cresta[None, :] < alto) * (1 - prof) * 0.85
        m *= ruido2d(w, h, 60, 3, semilla + 9) > 0.45
        img = mezclar(img, nieve, m)
    return img


def niebla(img, y0, y1, color, fuerza=0.6):
    h = img.shape[0]
    y = np.linspace(0, 1, h)[:, None]
    a = np.clip((y - y0) / max(1e-6, (y1 - y0)), 0, 1)
    a = np.sin(a * math.pi) * fuerza
    return mezclar(img, color, np.broadcast_to(a, img.shape[:2]))


def suelo(img, y, color, color2=None):
    h, w = img.shape[:2]
    yy = np.linspace(0, 1, h)[:, None]
    a = np.broadcast_to(np.clip((yy - y) * h / 2, 0, 1), (h, w))
    img = mezclar(img, color, a)
    if color2 is not None:
        t = np.broadcast_to(np.clip((yy - y) / (1 - y), 0, 1), (h, w))
        img = mezclar(img, color2, a * t)
    return img


def agua(img, y, color, brillo_x=None, brillo_col=(255, 200, 120), semilla=4):
    h, w = img.shape[:2]
    yy = np.linspace(0, 1, h)[:, None]
    a = np.broadcast_to(np.clip((yy - y) * h / 2, 0, 1), (h, w)).copy()
    img = mezclar(img, color, a)
    estrecho = ruido2d(max(8, w // 14), h, 6, 3, semilla)
    olas = np.asarray(Image.fromarray((estrecho * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float) / 255
    olas = np.clip((olas - 0.5) * 4, 0, 1) * a
    img = mezclar(img, np.array(color) * 1.3 + 15, olas * 0.25)
    if brillo_x is not None:
        xx = np.arange(w)[None, :]
        prof = np.clip((yy - y) / (1 - y), 0, 1)
        ancho = 60 + 500 * prof
        cam = np.exp(-((xx - brillo_x) / ancho) ** 2) * a * (olas > 0.2)
        img = mezclar(img, brillo_col, cam * 0.8)
    return img


# ======================= siluetas (capa RGBA con supersampling) =======================

class Pincel:
    def __init__(self):
        self.img = Image.new("RGBA", (W0 * SS, H0 * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.color = (10, 8, 8, 255)

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, color=None):
        self.d.polygon(self._p(pts), fill=color or self.color)

    def linea(self, pts, ancho, color=None):
        self.d.line(self._p(pts), fill=color or self.color, width=max(1, int(ancho * SS)), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = ancho / 2
            self.d.ellipse(((x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS), fill=color or self.color)

    def elipse(self, cx, cy, rx, ry, color=None, borde=None, ancho=0):
        relleno = None if (borde is not None and color is None) else (color or self.color)
        self.d.ellipse(((cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS), fill=relleno,
                       outline=borde, width=int(ancho * SS))

    def rect(self, x0, y0, x1, y1, color=None):
        self.d.rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), fill=color or self.color)

    def texto(self, x, y, txt, f, color, anchor="mm"):
        f2 = ImageFont.truetype(f.path, f.size * SS)
        self.d.text((x * SS, y * SS), txt, font=f2, fill=color, anchor=anchor)

    def sobre(self, img_np, desenfoque=0):
        capa = self.img.resize((W0, H0), Image.LANCZOS)
        if desenfoque:
            capa = capa.filter(ImageFilter.GaussianBlur(desenfoque))
        base = Image.fromarray(np.clip(img_np, 0, 255).astype(np.uint8)).convert("RGBA")
        base.alpha_composite(capa)
        return np.asarray(base.convert("RGB"), float)


def soldado(p, x, y, h, fase=0.0, mira=1):
    u = h / 10
    s = mira
    p.linea([(x - 0.2 * u * s, y - 4.6 * u), (x + (-1.1 + fase) * u * s, y)], 0.75 * u)
    p.linea([(x + 0.2 * u * s, y - 4.6 * u), (x + (1.0 - fase) * u * s, y)], 0.75 * u)
    p.poly([(x - 0.95 * u, y - 4.4 * u), (x + 0.95 * u, y - 4.4 * u), (x + 0.8 * u, y - 7.7 * u), (x - 0.8 * u, y - 7.7 * u)])
    p.rect(min(x - 1.6 * u * s, x - 0.7 * u * s), y - 7.4 * u, max(x - 1.6 * u * s, x - 0.7 * u * s), y - 5.4 * u)
    p.elipse(x + 0.1 * u * s, y - 8.35 * u, 0.62 * u, 0.66 * u)
    p.poly([(x - 0.5 * u, y - 8.7 * u), (x + 0.6 * u, y - 8.7 * u), (x + 0.5 * u, y - 10.0 * u), (x - 0.45 * u, y - 10.0 * u)])
    p.elipse(x, y - 10.3 * u, 0.22 * u, 0.4 * u)
    p.linea([(x + 0.5 * u * s, y - 4.6 * u), (x + 1.4 * u * s, y - 11.6 * u)], 0.28 * u)
    p.linea([(x + 1.4 * u * s, y - 11.6 * u), (x + 1.55 * u * s, y - 12.9 * u)], 0.1 * u)
    p.linea([(x + 0.4 * u * s, y - 7.3 * u), (x + 0.95 * u * s, y - 6.0 * u), (x + 0.8 * u * s, y - 5.2 * u)], 0.45 * u)


def figura(p, x, y, h, mira=1, sombrero=True, falda=False, brazo=0.0):
    """Persona de pie con levita (o vestido si falda=True)."""
    u = h / 10
    s = mira
    if falda:
        p.poly([(x - 1.7 * u, y), (x + 1.7 * u, y), (x + 0.7 * u, y - 5.5 * u), (x - 0.7 * u, y - 5.5 * u)])
    else:
        p.linea([(x - 0.3 * u, y - 4.8 * u), (x - 0.5 * u, y)], 0.7 * u)
        p.linea([(x + 0.3 * u, y - 4.8 * u), (x + 0.5 * u, y)], 0.7 * u)
        p.poly([(x - 1.1 * u * s, y - 2.6 * u), (x - 0.2 * u * s, y - 4.6 * u), (x - 0.9 * u * s, y - 4.6 * u)])
    p.poly([(x - 0.9 * u, y - 4.4 * u), (x + 0.9 * u, y - 4.4 * u), (x + 0.85 * u, y - 7.8 * u), (x - 0.85 * u, y - 7.8 * u)])
    p.elipse(x - 0.95 * u, y - 7.6 * u, 0.35 * u, 0.3 * u)
    p.elipse(x + 0.95 * u, y - 7.6 * u, 0.35 * u, 0.3 * u)
    p.rect(x - 0.25 * u, y - 8.3 * u, x + 0.25 * u, y - 7.6 * u)
    p.elipse(x + 0.1 * u * s, y - 8.75 * u, 0.6 * u, 0.68 * u)
    if falda:
        p.elipse(x - 0.45 * u * s, y - 8.95 * u, 0.4 * u, 0.4 * u)
    if sombrero:
        p.elipse(x + 0.05 * u * s, y - 9.4 * u, 1.25 * u, 0.36 * u)
        p.elipse(x + 0.05 * u * s, y - 9.65 * u, 0.6 * u, 0.42 * u)
    ax, ay = x + 0.9 * u * s, y - 7.5 * u
    p.linea([(ax, ay), (ax + (0.3 + 1.6 * brazo) * u * s, ay + (2.6 - 3.4 * brazo) * u)], 0.42 * u)
    p.linea([(x - 0.9 * u * s, y - 7.5 * u), (x - 1.1 * u * s, y - 4.9 * u)], 0.42 * u)


def jinete(p, x, y, h, fase=0.0, lanza=True, mira=1):
    u = h / 10
    s = mira

    def X(v):
        return x + v * u * s

    p.elipse(x, y - 4.3 * u, 2.6 * u, 1.15 * u)
    p.poly([(X(1.4), y - 5.0 * u), (X(2.6), y - 7.3 * u), (X(3.3), y - 7.5 * u), (X(3.0), y - 4.3 * u)])
    p.poly([(X(2.5), y - 7.2 * u), (X(3.3), y - 7.9 * u), (X(4.4), y - 6.3 * u), (X(4.1), y - 5.9 * u), (X(3.0), y - 6.5 * u)])
    p.poly([(X(2.9), y - 7.7 * u), (X(3.1), y - 8.5 * u), (X(3.35), y - 7.75 * u)])
    p.poly([(X(-2.4), y - 4.9 * u), (X(-3.5), y - 3.2 * u), (X(-3.2), y - 2.6 * u), (X(-2.2), y - 4.1 * u)])
    a = math.sin(fase) * 0.8
    p.linea([(X(1.7), y - 3.8 * u), (X(2.6 + a), y - 2.0 * u), (X(3.4 + a), y - 1.4 * u)], 0.42 * u)
    p.linea([(X(1.3), y - 3.6 * u), (X(1.8 - a), y - 1.8 * u), (X(2.0 - a), y - 0.2 * u)], 0.42 * u)
    p.linea([(X(-1.7), y - 3.8 * u), (X(-2.5 - a), y - 2.0 * u), (X(-3.3 - a), y - 0.9 * u)], 0.42 * u)
    p.linea([(X(-1.3), y - 3.6 * u), (X(-1.0 + a), y - 1.9 * u), (X(-1.6 + a), y - 0.2 * u)], 0.42 * u)
    p.poly([(X(-0.6), y - 5.1 * u), (X(0.6), y - 5.1 * u), (X(0.55), y - 7.9 * u), (X(-0.3), y - 7.9 * u)])
    p.linea([(X(0.2), y - 5.2 * u), (X(0.5), y - 3.3 * u)], 0.5 * u)
    p.elipse(X(0.25), y - 8.5 * u, 0.55 * u, 0.6 * u)
    p.elipse(X(0.2), y - 9.05 * u, 1.05 * u, 0.32 * u)
    if lanza:
        p.linea([(X(-1.8), y - 5.6 * u), (X(5.8), y - 10.2 * u)], 0.17 * u)
        p.poly([(X(5.2), y - 9.85 * u), (X(4.4), y - 9.0 * u), (X(4.9), y - 9.6 * u)])


def bandera(p, x, y, h, colores, fase=0.0, mira=1):
    p.linea([(x, y), (x, y - h)], max(2, h * 0.018))
    fw, fh = h * 0.42 * mira, h * 0.27
    n = 16
    arriba = [(x + fw * i / n, y - h + math.sin(i * 0.55 + fase) * fh * 0.1 * i / n) for i in range(n + 1)]
    franjas = len(colores)
    for k, c in enumerate(colores):
        t0, t1 = fh * k / franjas, fh * (k + 1) / franjas
        pts = [(px, py + t0) for px, py in arriba] + [(px, py + t1) for px, py in reversed(arriba)]
        p.poly(pts, c)


def palmera(p, x, y, h, inclina=0.15, semilla=0):
    rng = random.Random(semilla)
    pts = [(x + inclina * h * (t ** 1.6), y - h * t) for t in np.linspace(0, 1, 12)]
    for i in range(len(pts) - 1):
        p.linea([pts[i], pts[i + 1]], h * 0.035 * (1.2 - i / 14))
    cx, cy = pts[-1]
    for k in range(9):
        ang = -math.pi / 2 + (k - 4) * 0.42 + rng.uniform(-0.1, 0.1)
        largo = h * rng.uniform(0.32, 0.42)
        hoja = []
        for t in np.linspace(0, 1, 10):
            hx = cx + math.cos(ang) * largo * t
            hy = cy + math.sin(ang) * largo * t + (largo * 0.55) * t * t
            hoja.append((hx, hy))
        for i in range(len(hoja) - 1):
            p.linea([hoja[i], hoja[i + 1]], h * 0.03 * (1 - i / 11))


def arbol(p, x, y, h, semilla=0):
    rng = random.Random(semilla)
    p.linea([(x, y), (x, y - h * 0.45)], h * 0.06)
    for _ in range(14):
        p.elipse(x + rng.uniform(-0.28, 0.28) * h, y - h * rng.uniform(0.5, 0.9), h * rng.uniform(0.12, 0.2),
                 h * rng.uniform(0.1, 0.16))


def casa(p, x, y, w, h, ventanas=True, luz=None):
    p.rect(x, y - h, x + w, y)
    p.poly([(x - w * 0.08, y - h), (x + w * 1.08, y - h), (x + w * 0.9, y - h - h * 0.35), (x + w * 0.1, y - h - h * 0.35)])
    if ventanas and luz:
        for i in range(int(w // 60)):
            vx = x + 25 + i * 60
            if (i * 7 + int(x)) % 3 == 0:
                p.rect(vx, y - h * 0.7, vx + 18, y - h * 0.4, luz)


def iglesia(p, x, y, w, h, luz=None):
    p.rect(x, y - h, x + w, y)
    p.poly([(x - 5, y - h), (x + w + 5, y - h), (x + w / 2, y - h - h * 0.35)])
    tw = w * 0.28
    for tx in (x - tw * 0.3, x + w - tw * 0.7):
        p.rect(tx, y - h * 1.75, tx + tw, y - h * 0.5)
        p.elipse(tx + tw / 2, y - h * 1.75, tw / 2, tw * 0.55)
        p.linea([(tx + tw / 2, y - h * 1.75 - tw * 0.5), (tx + tw / 2, y - h * 2.05)], 4)
        p.linea([(tx + tw / 2 - 14, y - h * 1.98), (tx + tw / 2 + 14, y - h * 1.98)], 4)
    if luz:
        p.elipse(x + w / 2, y - h * 0.62, w * 0.08, w * 0.08, luz)
        p.rect(x + w * 0.42, y - h * 0.32, x + w * 0.58, y, luz)


def barco(p, x, y, s, velas=(225, 210, 175, 255), mira=1, fase=0):
    """Velero de tres palos. s = escala (≈ largo/10)."""
    def X(v):
        return x + v * s * mira

    p.poly([(X(-5), y - 1.6 * s), (X(5.5), y - 1.9 * s), (X(4.6), y), (X(-4.2), y)])
    p.poly([(X(-5.2), y - 1.6 * s), (X(-4.6), y - 2.8 * s), (X(-3.2), y - 2.8 * s), (X(-3.3), y - 1.6 * s)])
    for i, (mx, alto) in enumerate(((-2.6, 10), (0.6, 12), (3.4, 9))):
        p.linea([(X(mx), y - 1.6 * s), (X(mx), y - alto * s)], 0.18 * s)
        for k in range(3):
            y0 = y - (alto - 0.6 - k * 2.6) * s
            y1 = y0 + 2.2 * s
            ancho = (1.6 + k * 0.35) * s
            curva = 0.4 * s * (1 + 0.2 * math.sin(fase + i))
            p.poly([(X(mx) - ancho, y0), (X(mx) + ancho, y0), (X(mx) + ancho + curva * mira, y1),
                    (X(mx) - ancho + curva * mira, y1)], velas)
    p.linea([(X(5.4), y - 1.9 * s), (X(8), y - 4 * s)], 0.12 * s)
    p.poly([(X(3.4), y - 9 * s), (X(7.6), y - 3.9 * s), (X(3.4), y - 3.6 * s)], velas)
    p.poly([(X(0.6), y - 12 * s), (X(1.6), y - 11.6 * s), (X(0.6), y - 11.2 * s)], (170, 30, 30, 255))


def canon(p, x, y, s, mira=1):
    p.elipse(x, y - s * 0.9, s * 0.9, s * 0.9)
    p.linea([(x - 1.6 * s * mira, y - 0.6 * s), (x + 2.6 * s * mira, y - 1.8 * s)], s * 0.55)


def fogata(img, p, x, y, s):
    img = resplandor(img, x, y - s, s * 10, (255, 120, 40), 0.55)
    p.poly([(x - s, y), (x + s, y), (x + 0.2 * s, y - 2.6 * s), (x - 0.3 * s, y - 1.6 * s)], (255, 170, 60, 255))
    p.poly([(x - 0.5 * s, y), (x + 0.5 * s, y), (x, y - 1.6 * s)], (255, 230, 150, 255))
    return img


def tienda(p, x, y, w, h):
    p.poly([(x - w / 2, y), (x + w / 2, y), (x, y - h)])


def humo(img, semilla, fuerza=0.55, color=(150, 140, 125), y0=0.35, y1=1.0):
    h, w = img.shape[:2]
    n = ruido2d(w, h, 280, 5, semilla)
    yy = np.linspace(0, 1, h)[:, None]
    banda = np.clip((yy - y0) / 0.2, 0, 1) * np.clip((y1 - yy) / 0.15, 0, 1)
    return mezclar(img, color, np.clip((n - 0.4) * 2.2, 0, 1) * banda * fuerza)


def lluvia(img, semilla=0, n=2500, color=(190, 200, 210)):
    rng = np.random.default_rng(semilla)
    capa = Image.new("L", (W0, H0), 0)
    d = ImageDraw.Draw(capa)
    for _ in range(n):
        x, y = rng.integers(-100, W0), rng.integers(-100, H0)
        lng = rng.integers(25, 60)
        d.line((x, y, x + lng * 0.25, y + lng), fill=int(rng.integers(40, 110)), width=2)
    a = np.asarray(capa, float) / 255
    return mezclar(img, color, a)


def rayo(img, x, semilla=0):
    rng = random.Random(semilla)
    capa = Image.new("L", (W0, H0), 0)
    d = ImageDraw.Draw(capa)
    pts, y, cx = [], 0, x
    while y < H0 * 0.62:
        pts.append((cx, y))
        y += rng.uniform(30, 70)
        cx += rng.uniform(-40, 40)
    d.line(pts, fill=255, width=5)
    capa = capa.filter(ImageFilter.GaussianBlur(1.5))
    glow = capa.filter(ImageFilter.GaussianBlur(25))
    a = np.clip(np.asarray(capa, float) / 255 + np.asarray(glow, float) / 255 * 1.5, 0, 1)
    return mezclar(img, (230, 235, 255), a)


# ======================= acabado pictórico =======================

_textura = None


def textura():
    global _textura
    if _textura is None:
        rng = np.random.default_rng(42)
        fino = rng.standard_normal((H0, W0))
        lienzo = (np.sin(np.arange(W0) * 1.9)[None, :] + np.sin(np.arange(H0) * 1.7)[:, None]) * 0.5
        trazo = ruido2d(W0, H0, 12, 2, 5) - 0.5
        _textura = fino * 3.5 + lienzo * 3 + trazo * 18
    return _textura


def acabado(img, calidez=0.12, contraste=1.05):
    img = np.clip(img, 0, 255)
    gris = img.mean(axis=2, keepdims=True)
    sepia = np.concatenate([gris * 1.07 + 12, gris * 0.95 + 4, gris * 0.78], axis=2)
    img = img * (1 - calidez) + sepia * calidez
    img = (img - 128) * contraste + 128
    img = img + textura()[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    im = im.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.UnsharpMask(2, 40, 2))
    return im


# ======================= escenas =======================

def sc_andes(marcha=False):
    img = gradiente([(0, (60, 78, 110)), (0.45, (190, 160, 140)), (0.62, (235, 190, 140))])
    img = nubes(img, 0.0, 0.45, (225, 215, 210), 0.55, 11)
    img = montes(img, 0.66, 0.42, (120, 125, 150), 21, 700, nieve=(235, 238, 245), filo=1.6)
    img = niebla(img, 0.45, 0.75, (215, 190, 170), 0.5)
    img = montes(img, 0.76, 0.3, (80, 82, 100), 22, 500, nieve=(200, 205, 215), filo=1.3)
    img = niebla(img, 0.6, 0.85, (190, 170, 160), 0.45)
    img = montes(img, 0.9, 0.22, (45, 42, 50), 23, 380)
    img = montes(img, 1.02, 0.18, (22, 20, 24), 24, 300)
    if marcha:
        p = Pincel()
        p.color = (18, 15, 18, 255)
        r = ruido1d(W0, 300, 6, 24)
        r = (r - r.min()) / (r.max() - r.min())
        for i in range(22):
            x = 200 + i * 92
            yb = (1.02 - 0.18 * r[min(W0 - 1, int(x))]) * H0 + 6
            soldado(p, x, yb, 120 + (i % 3) * 6, fase=(i % 2) * 0.6)
        jinete(p, 2140, (1.02 - 0.18 * r[2140]) * H0 + 8, 150, lanza=False)
        bandera(p, 640, (1.02 - 0.18 * r[640]) * H0 - 20, 260, [(200, 160, 30, 255), (30, 50, 120, 255), (160, 30, 35, 255)], 1)
        img = p.sobre(img)
        img = lluvia(img, 3, 1200, (200, 205, 215))
    return img


def sc_volcan():
    img = gradiente([(0, (70, 90, 130)), (0.5, (225, 170, 120)), (0.7, (240, 200, 150))])
    img = nubes(img, 0.05, 0.4, (240, 220, 205), 0.5, 31)
    h, w = img.shape[:2]
    xx = np.arange(w)
    cono = 0.72 - 0.5 * np.clip(1 - np.abs(xx - w * 0.55) / (w * 0.42), 0, 1) ** 1.3
    cono += (ruido1d(w, 80, 4, 3) - 0.5) * 0.03
    cono = np.maximum(cono, 0.26 + (ruido1d(w, 40, 3, 4) - 0.5) * 0.02)
    yy = np.arange(h)[:, None]
    a = np.clip(yy - cono[None, :] * h, 0, 1.5) / 1.5
    img = mezclar(img, (95, 85, 100), a)
    nieve = a * (yy < (0.36 * h)) * (ruido2d(w, h, 50, 3, 9) > 0.4)
    img = mezclar(img, (235, 235, 240), nieve * 0.85)
    img = niebla(img, 0.55, 0.85, (220, 180, 150), 0.5)
    img = montes(img, 0.95, 0.18, (40, 40, 45), 33, 300)
    p = Pincel()
    p.color = (20, 18, 20, 255)
    for i in range(14):
        soldado(p, 300 + i * 70, 0.93 * H0 + (i % 3) * 8, 95)
    bandera(p, 1300, 0.94 * H0, 240, [(200, 160, 30, 255), (30, 50, 120, 255), (160, 30, 35, 255)], 2)
    img = humo(img, 7, 0.35, (200, 180, 160), 0.6, 1.0)
    return p.sobre(img)


def sc_batalla(variante="noche"):
    if variante == "victoria":
        img = gradiente([(0, (40, 60, 100)), (0.45, (230, 150, 90)), (0.65, (255, 210, 140))])
        img = resplandor(img, W0 * 0.5, H0 * 0.62, 600, (255, 190, 100), 0.6)
        img = disco(img, W0 * 0.5, H0 * 0.6, 90, (255, 235, 190))
    else:
        img = gradiente([(0, (50, 40, 45)), (0.5, (170, 90, 50)), (0.68, (220, 130, 60))])
        img = resplandor(img, W0 * 0.3, H0 * 0.66, 700, (255, 120, 40), 0.5)
    img = nubes(img, 0.0, 0.5, (90, 70, 70), 0.6, 41)
    img = montes(img, 0.7, 0.18, (90, 70, 70), 42, 600)
    img = humo(img, 43, 0.6, (160, 130, 110), 0.3, 0.8)
    img = suelo(img, 0.82, (40, 30, 28), (25, 20, 18))
    p = Pincel()
    p.color = (16, 12, 12, 255)
    tri = [(210, 160, 30, 255), (30, 50, 130, 255), (170, 30, 35, 255)]
    if variante == "victoria":
        p.poly([(0, H0), (0, H0 * 0.84), (W0 * 0.35, H0 * 0.76), (W0 * 0.5, H0 * 0.74), (W0 * 0.7, H0 * 0.78), (W0, H0 * 0.86), (W0, H0)])
        bandera(p, W0 * 0.5, H0 * 0.745, 480, tri, 0.8)
        for i in range(-8, 9):
            if abs(i) < 1:
                continue
            x = W0 * 0.5 + i * 105
            yb = H0 * (0.745 + 0.0008 * i * i) + 20
            figura(p, x, yb, 150, mira=-1 if i > 0 else 1, sombrero=False, brazo=0.9 if i % 3 == 0 else 0)
        img = p.sobre(img)
        return img
    for i in range(28):
        x = 80 + i * 82
        soldado(p, x, H0 * 0.93 + (i % 2) * 14, 150, fase=(i % 3) * 0.4)
    for i in range(6):
        jinete(p, 400 + i * 330, H0 * 0.86 + (i % 2) * 20, 140, fase=i)
    bandera(p, 760, H0 * 0.92, 380, tri, 0.4)
    canon(p, 1900, H0 * 0.96, 36, -1)
    img = p.sobre(img)
    img = humo(img, 44, 0.45, (170, 150, 130), 0.6, 1.0)
    if variante == "humo":
        img = humo(img, 45, 0.6, (140, 120, 105), 0.2, 1.0)
    return img


def sc_caballeria():
    img = gradiente([(0, (70, 80, 110)), (0.55, (220, 170, 120)), (0.7, (240, 205, 160))])
    img = nubes(img, 0.0, 0.5, (230, 210, 200), 0.5, 51)
    img = montes(img, 0.66, 0.3, (110, 110, 135), 52, 700, nieve=(230, 232, 240), filo=1.5)
    img = niebla(img, 0.5, 0.8, (210, 180, 150), 0.5)
    img = suelo(img, 0.78, (70, 65, 45), (40, 35, 25))
    p = Pincel()
    p.color = (18, 15, 14, 255)
    for i in range(9):
        jinete(p, 200 + i * 230 + (i % 2) * 40, H0 * (0.9 + 0.03 * (i % 3)), 190, fase=i * 0.9)
    img = p.sobre(img)
    return humo(img, 53, 0.4, (200, 175, 140), 0.75, 1.0)


def sc_llanos(noche=False):
    if noche:
        img = gradiente([(0, (8, 12, 30)), (0.55, (35, 40, 70)), (0.68, (80, 60, 70))])
        img = estrellas(img, 700, 5)
        img = disco(img, W0 * 0.78, H0 * 0.2, 55, (240, 235, 210))
        img = resplandor(img, W0 * 0.78, H0 * 0.2, 260, (120, 120, 140), 0.4)
        col = (8, 8, 12, 255)
    else:
        img = gradiente([(0, (80, 120, 170)), (0.5, (240, 190, 120)), (0.7, (250, 220, 160))])
        img = resplandor(img, W0 * 0.3, H0 * 0.68, 500, (255, 200, 120), 0.6)
        img = nubes(img, 0.05, 0.5, (250, 230, 215), 0.45, 61)
        col = (25, 20, 15, 255)
    img = suelo(img, 0.7, (60, 55, 40) if not noche else (15, 15, 22), (40, 35, 25) if not noche else (8, 8, 12))
    p = Pincel()
    p.color = col
    for i, x in enumerate((150, 420, 1600, 1830, 2150)):
        palmera(p, x, H0 * 0.71 + (i % 2) * 6, 380 + (i * 37) % 120, 0.12 * (1 if i % 2 else -1), i)
    for i in range(7):
        jinete(p, 650 + i * 150, H0 * (0.86 + 0.02 * (i % 2)), 150, fase=i * 1.3)
    img = p.sobre(img)
    if noche:
        img = humo(img, 63, 0.25, (60, 60, 80), 0.6, 1.0)
    return img


def sc_rio():
    img = gradiente([(0, (90, 120, 150)), (0.45, (230, 190, 140)), (0.55, (240, 210, 160))])
    img = nubes(img, 0.0, 0.4, (240, 230, 220), 0.4, 71)
    img = montes(img, 0.52, 0.12, (90, 100, 90), 72, 400)
    img = niebla(img, 0.4, 0.6, (225, 205, 170), 0.5)
    img = agua(img, 0.55, (90, 95, 80), W0 * 0.45, (255, 220, 160))
    p = Pincel()
    p.color = (20, 25, 18, 255)
    for i in range(30):
        arbol(p, 40 + i * 30 + (i % 4) * 9, H0 * 0.6 - (i % 3) * 6, 160 + (i * 13) % 70, i)
        arbol(p, W0 - 40 - i * 28, H0 * 0.6 - (i % 2) * 8, 150 + (i * 17) % 70, i + 50)
    for k, (x, y, s) in enumerate(((900, 0.8, 40), (1350, 0.7, 26))):
        yb = H0 * y
        p.poly([(x - 4 * s, yb - s * 0.7), (x + 4 * s, yb - s * 0.7), (x + 3 * s, yb), (x - 3 * s, yb)])
        for j in range(3):
            figura(p, x - 2 * s + j * 2 * s, yb - s * 0.6, s * 2.2, sombrero=j == 1)
        p.linea([(x + 2.6 * s, yb - 2.5 * s), (x + 3.4 * s, yb + 0.6 * s)], s * 0.15)
    return p.sobre(img)


def sc_colonia(variante="caracas"):
    img = gradiente([(0, (50, 60, 100)), (0.5, (220, 140, 100)), (0.68, (245, 190, 130))])
    img = nubes(img, 0.0, 0.45, (240, 180, 150), 0.5, 81)
    img = montes(img, 0.6, 0.33 if variante == "caracas" else 0.12, (90, 90, 115), 82, 900, filo=1.2)
    img = niebla(img, 0.45, 0.72, (230, 170, 130), 0.4)
    p = Pincel()
    p.color = (30, 22, 26, 255)
    luz = (255, 200, 110, 255)
    base = H0 * 0.86
    x = -40
    k = 0
    while x < W0:
        wc = 150 + (k * 47) % 120
        hc = 120 + (k * 31) % 90
        if k == 6:
            iglesia(p, x, base - 30, 300, 300, luz)
            x += 330
        else:
            casa(p, x, base + (k % 2) * 20, wc, hc, True, luz)
            x += wc + 8
        k += 1
    if variante == "lima":
        iglesia(p, 1500, base - 10, 420, 380, luz)
    p.rect(0, base + 20, W0, H0)
    for i in range(5):
        palmera(p, 120 + i * 520, base + 40, 300 + i * 20, 0.1, i)
    img = p.sobre(img)
    return img


def sc_entrada():
    img = sc_colonia()
    p = Pincel()
    p.color = (14, 10, 12, 255)
    tri = [(210, 160, 30, 255), (30, 50, 130, 255), (170, 30, 35, 255)]
    for i in range(34):
        figura(p, 40 + i * 70, H0 * 0.99, 150 + (i % 3) * 10, mira=1 if i < 17 else -1, sombrero=i % 2 == 0,
               falda=i % 5 == 2, brazo=1.0 if i % 4 == 0 else 0)
    jinete(p, W0 * 0.5, H0 * 0.93, 230, lanza=False)
    for x in (500, 1800):
        bandera(p, x, H0 * 0.9, 380, tri, x / 300)
    return p.sobre(img)


def sc_hacienda():
    img = gradiente([(0, (90, 130, 170)), (0.5, (245, 200, 140)), (0.66, (250, 220, 170))])
    img = nubes(img, 0.0, 0.45, (250, 235, 220), 0.45, 91)
    img = montes(img, 0.62, 0.22, (110, 120, 120), 92, 800)
    img = niebla(img, 0.5, 0.7, (230, 210, 170), 0.5)
    img = suelo(img, 0.68, (100, 110, 60), (60, 70, 35))
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    surcos = (np.sin((xx - w / 2) / (yy - h * 0.6 + 1) * 40) > 0.6) * (yy > h * 0.72)
    img = mezclar(img, (70, 80, 40), surcos * 0.35)
    p = Pincel()
    p.color = (45, 35, 30, 255)
    luz = (255, 210, 130, 255)
    casa(p, 900, H0 * 0.72, 520, 150, True, luz)
    p.rect(940, H0 * 0.72 - 110, 1380, H0 * 0.72 - 95)
    for i in range(9):
        p.rect(950 + i * 52, H0 * 0.72 - 100, 962 + i * 52, H0 * 0.72)
    for i, x in enumerate((300, 600, 1600, 1900, 2150)):
        arbol(p, x, H0 * 0.73, 260, i)
    for i, x in enumerate((760, 1500)):
        palmera(p, x, H0 * 0.73, 420, 0.1 * (-1) ** i, i)
    return p.sobre(img)


def sc_quinta():
    img = gradiente([(0, (40, 50, 90)), (0.5, (230, 130, 90)), (0.6, (250, 180, 120))])
    img = disco(img, W0 * 0.3, H0 * 0.55, 80, (255, 220, 160))
    img = resplandor(img, W0 * 0.3, H0 * 0.55, 400, (255, 150, 80), 0.6)
    img = nubes(img, 0.05, 0.5, (240, 150, 120), 0.45, 101)
    img = agua(img, 0.6, (60, 50, 70), W0 * 0.3, (255, 190, 120))
    p = Pincel()
    p.color = (24, 18, 22, 255)
    p.poly([(W0 * 0.45, H0 * 0.66), (W0, H0 * 0.6), (W0, H0), (W0 * 0.38, H0)])
    casa(p, 1420, H0 * 0.68, 540, 170, True, (255, 200, 120, 255))
    for i in range(10):
        p.rect(1440 + i * 55, H0 * 0.68 - 130, 1452 + i * 55, H0 * 0.68)
    for i, x in enumerate((1150, 1300, 2050, 2200)):
        palmera(p, x, H0 * 0.72, 470 + i * 25, 0.12 * (-1) ** i, i + 3)
    return p.sobre(img)


def sc_mar(variante="dia"):
    if variante == "noche":
        img = gradiente([(0, (6, 10, 25)), (0.55, (30, 40, 70)), (0.62, (50, 60, 90))])
        img = estrellas(img, 900, 7)
        img = disco(img, W0 * 0.7, H0 * 0.25, 60, (240, 235, 215))
        img = resplandor(img, W0 * 0.7, H0 * 0.25, 300, (110, 120, 150), 0.5)
        img = agua(img, 0.62, (15, 22, 38), W0 * 0.7, (200, 210, 230))
        velas = (90, 95, 110, 255)
        col = (6, 8, 12, 255)
    else:
        img = gradiente([(0, (70, 100, 150)), (0.5, (235, 175, 120)), (0.62, (250, 205, 150))])
        img = disco(img, W0 * 0.25, H0 * 0.56, 70, (255, 230, 180))
        img = resplandor(img, W0 * 0.25, H0 * 0.56, 450, (255, 170, 90), 0.6)
        img = nubes(img, 0.0, 0.5, (250, 210, 190), 0.5, 111)
        img = agua(img, 0.62, (60, 70, 90), W0 * 0.25, (255, 200, 130))
        velas = (230, 215, 185, 255)
        col = (25, 22, 26, 255)
    p = Pincel()
    p.color = col
    if variante == "flota":
        for i, (x, y, s) in enumerate(((600, 0.8, 30), (1300, 0.74, 20), (1800, 0.7, 14), (1000, 0.67, 10), (2100, 0.66, 9))):
            barco(p, x, H0 * y, s, velas, fase=i)
    else:
        barco(p, W0 * 0.58, H0 * 0.78, 34, velas)
    return p.sobre(img)


def sc_caribe():
    img = gradiente([(0, (60, 120, 170)), (0.5, (170, 205, 210)), (0.6, (230, 220, 190))])
    img = nubes(img, 0.05, 0.5, (250, 250, 245), 0.5, 121)
    img = agua(img, 0.58, (40, 110, 130), W0 * 0.6, (240, 240, 220))
    img = suelo(img, 0.82, (215, 195, 150), (190, 170, 130))
    p = Pincel()
    p.color = (30, 40, 30, 255)
    for i, x in enumerate((180, 420, 1950, 2200)):
        palmera(p, x, H0 * 0.86, 600 + i * 30, 0.18 * (-1) ** i, i + 8)
    figura(p, 1200, H0 * 0.92, 260, mira=-1)
    barco(p, 1650, H0 * 0.64, 9, (220, 220, 215, 255))
    return p.sobre(img)


def sc_atardecer_mar():
    img = gradiente([(0, (30, 25, 60)), (0.45, (190, 80, 70)), (0.6, (250, 160, 90))])
    img = disco(img, W0 * 0.5, H0 * 0.6, 120, (255, 200, 130))
    img = resplandor(img, W0 * 0.5, H0 * 0.6, 600, (255, 120, 60), 0.6)
    img = nubes(img, 0.1, 0.5, (150, 60, 70), 0.5, 131)
    img = agua(img, 0.6, (50, 30, 50), W0 * 0.5, (255, 170, 100))
    p = Pincel()
    p.color = (16, 10, 16, 255)
    p.poly([(0, H0), (0, H0 * 0.7), (W0 * 0.25, H0 * 0.74), (W0 * 0.3, H0)])
    palmera(p, 300, H0 * 0.74, 520, 0.2, 2)
    return p.sobre(img)


def sc_amanecer():
    img = gradiente([(0, (40, 60, 110)), (0.45, (230, 160, 120)), (0.6, (255, 220, 160))])
    img = disco(img, W0 * 0.5, H0 * 0.6, 100, (255, 240, 200))
    img = resplandor(img, W0 * 0.5, H0 * 0.58, 800, (255, 190, 110), 0.7)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    ang = np.arctan2(yy - h * 0.6, xx - w * 0.5)
    rayos = (np.sin(ang * 24) > 0.6) * (yy < h * 0.6)
    img = mezclar(img, (255, 230, 180), rayos * 0.12)
    img = nubes(img, 0.0, 0.45, (240, 200, 180), 0.45, 141)
    img = montes(img, 0.7, 0.2, (110, 100, 120), 142, 600)
    img = niebla(img, 0.55, 0.8, (240, 200, 160), 0.5)
    img = montes(img, 0.85, 0.15, (60, 50, 60), 143, 400)
    img = montes(img, 1.0, 0.12, (25, 20, 25), 144, 300)
    p = Pincel()
    p.color = (25, 20, 25, 255)
    figura(p, W0 * 0.5, H0 * 0.9, 230)
    return p.sobre(img)


def sc_tormenta():
    img = gradiente([(0, (25, 28, 35)), (0.5, (70, 70, 80)), (0.7, (100, 95, 95))])
    img = nubes(img, 0.0, 0.7, (40, 42, 50), 0.7, 151, 400)
    img = nubes(img, 0.0, 0.6, (110, 110, 120), 0.4, 152, 300, 0.5)
    img = rayo(img, W0 * 0.66, 5)
    img = resplandor(img, W0 * 0.66, H0 * 0.3, 500, (120, 130, 160), 0.4)
    img = montes(img, 0.85, 0.2, (35, 35, 40), 153, 500)
    img = lluvia(img, 9, 3000, (150, 155, 165))
    return img


def sc_noche(ventana=False):
    img = gradiente([(0, (5, 8, 20)), (0.6, (25, 30, 55)), (1, (35, 35, 55))])
    img = estrellas(img, 500, 11)
    img = disco(img, W0 * 0.8, H0 * 0.18, 50, (235, 230, 210))
    img = resplandor(img, W0 * 0.8, H0 * 0.18, 260, (100, 110, 140), 0.5)
    img = nubes(img, 0.05, 0.35, (60, 65, 90), 0.4, 161, fuerza=0.6)
    p = Pincel()
    p.color = (8, 8, 14, 255)
    luz = (255, 190, 100, 255)
    if ventana:
        p.rect(0, 0, W0, H0 * 0.12)
        p.rect(0, 0, W0 * 0.3, H0)
        p.rect(W0 * 0.7, 0, W0, H0)
        p.rect(0, H0 * 0.86, W0, H0)
        p.rect(W0 * 0.495, 0, W0 * 0.505, H0)
        p.rect(0, H0 * 0.49, W0, H0 * 0.5)
        p.poly([(W0 * 0.3, H0 * 0.12), (W0 * 0.42, H0 * 0.12), (W0 * 0.33, H0 * 0.86), (W0 * 0.3, H0 * 0.86)], (90, 20, 25, 255))
        figura(p, W0 * 0.6, H0 * 0.86, 330, mira=1, sombrero=False)
        img = p.sobre(img)
        return resplandor(img, W0 * 0.2, H0 * 0.6, 500, (200, 120, 50), 0.25)
    base = H0 * 0.92
    x, k = -20, 0
    while x < W0:
        wc = 180 + (k * 53) % 140
        hc = 180 + (k * 37) % 140
        casa(p, x, base, wc, hc, True, luz)
        x += wc + 6
        k += 1
    p.rect(0, base, W0, H0)
    for i in range(4):
        figura(p, 700 + i * 120, base + 30, 170 + i * 5, mira=1, sombrero=True)
    img = p.sobre(img)
    img = resplandor(img, 900, H0 * 0.85, 300, (255, 160, 60), 0.25)
    return img


def sc_roma():
    img = gradiente([(0, (60, 70, 110)), (0.5, (230, 160, 110)), (0.65, (250, 210, 160))])
    img = disco(img, W0 * 0.62, H0 * 0.55, 85, (255, 230, 180))
    img = resplandor(img, W0 * 0.62, H0 * 0.55, 600, (255, 180, 100), 0.6)
    img = nubes(img, 0.0, 0.45, (245, 200, 180), 0.45, 171)
    p = Pincel()
    p.color = (35, 25, 25, 255)
    p.poly([(0, H0), (0, H0 * 0.78), (W0 * 0.2, H0 * 0.7), (W0 * 0.45, H0 * 0.66), (W0 * 0.7, H0 * 0.72), (W0, H0 * 0.8), (W0, H0)])
    for i in range(7):
        cx = 300 + i * 140
        alto = 260 - (i % 3) * 70 if i not in (2, 5) else 90
        p.rect(cx, H0 * 0.7 - alto, cx + 48, H0 * 0.72)
        p.rect(cx - 10, H0 * 0.7 - alto - 20, cx + 58, H0 * 0.7 - alto)
    p.rect(290, H0 * 0.7 - 280, 790, H0 * 0.7 - 260)
    for i in range(9):
        p.elipse(1700 + i * 50, H0 * 0.66 - (i % 3) * 30, 40, 120)
    figura(p, W0 * 0.5, H0 * 0.665, 190, mira=1, brazo=1.0)
    figura(p, W0 * 0.5 - 120, H0 * 0.67, 180, mira=1)
    return p.sobre(img)


def sc_congreso():
    img = gradiente([(0, (35, 28, 25)), (0.6, (70, 55, 45)), (1, (40, 30, 25))])
    h, w = img.shape[:2]
    p = Pincel()
    luz = (255, 225, 170, 255)
    for i in range(3):
        cx = W0 * (0.3 + i * 0.2)
        p.rect(cx - 90, H0 * 0.12, cx + 90, H0 * 0.55, luz)
        p.elipse(cx, H0 * 0.12, 90, 90, luz)
    img = p.sobre(img, 3)
    img = resplandor(img, W0 * 0.5, H0 * 0.35, 900, (255, 200, 140), 0.35)
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(3):
        cx = W0 * (0.3 + i * 0.2)
        haz = np.clip(1 - np.abs((xx - cx - (yy - h * 0.3) * 0.5) / (110 + (yy - h * 0.3).clip(0) * 0.25)), 0, 1)
        haz *= (yy > h * 0.3)
        img = mezclar(img, (255, 225, 170), haz * 0.18)
    p = Pincel()
    p.color = (30, 22, 20, 255)
    for cx in (W0 * 0.2, W0 * 0.4, W0 * 0.6, W0 * 0.8):
        p.rect(cx - 45, H0 * 0.05, cx + 45, H0 * 0.8)
        p.rect(cx - 65, H0 * 0.05, cx + 65, H0 * 0.1)
        p.rect(cx - 65, H0 * 0.76, cx + 65, H0 * 0.8)
    p.rect(0, 0, W0, H0 * 0.06)
    p.rect(W0 * 0.3, H0 * 0.66, W0 * 0.7, H0 * 0.72)
    p.rect(W0 * 0.32, H0 * 0.72, W0 * 0.34, H0 * 0.82)
    p.rect(W0 * 0.66, H0 * 0.72, W0 * 0.68, H0 * 0.82)
    for i in range(7):
        figura(p, W0 * 0.34 + i * 110, H0 * 0.68, 150, sombrero=False)
    figura(p, W0 * 0.5, H0 * 0.66, 200, sombrero=False, brazo=0.8)
    for fila in range(3):
        for i in range(14):
            x = 60 + i * 165 + fila * 40
            figura(p, x, H0 * (0.9 + fila * 0.06), 230 + fila * 30, sombrero=False, mira=1)
    img = p.sobre(img)
    return img


def sc_boda():
    img = gradiente([(0, (25, 18, 15)), (1, (45, 32, 25))])
    p = Pincel()
    luz = (255, 220, 160, 255)
    p.rect(W0 * 0.4, H0 * 0.18, W0 * 0.6, H0 * 0.7, luz)
    p.elipse(W0 * 0.5, H0 * 0.18, W0 * 0.1, W0 * 0.1, luz)
    img = p.sobre(img, 6)
    img = resplandor(img, W0 * 0.5, H0 * 0.3, 700, (255, 190, 120), 0.5)
    p = Pincel()
    p.color = (20, 14, 12, 255)
    p.rect(W0 * 0.495, H0 * 0.1, W0 * 0.505, H0 * 0.7)
    p.rect(W0 * 0.4, H0 * 0.44, W0 * 0.6, H0 * 0.455)
    for cx in (W0 * 0.25, W0 * 0.75):
        p.rect(cx - 50, 0, cx + 50, H0)
    p.rect(0, H0 * 0.8, W0, H0)
    for i, x in enumerate((W0 * 0.32, W0 * 0.68)):
        p.rect(x - 6, H0 * 0.55, x + 6, H0 * 0.8)
        p.elipse(x, H0 * 0.54, 12, 22, (255, 200, 110, 255))
    figura(p, W0 * 0.46, H0 * 0.82, 380, mira=1, sombrero=False)
    figura(p, W0 * 0.54, H0 * 0.82, 360, mira=-1, sombrero=False, falda=True)
    p.poly([(W0 * 0.54 - 30, H0 * 0.82 - 330), (W0 * 0.54 + 90, H0 * 0.82), (W0 * 0.54 - 70, H0 * 0.82)], (230, 225, 215, 120))
    img = p.sobre(img)
    for x in (W0 * 0.32, W0 * 0.68):
        img = resplandor(img, x, H0 * 0.54, 120, (255, 170, 80), 0.6)
    return img


def sc_vela():
    img = gradiente([(0, (10, 8, 8)), (1, (25, 18, 15))])
    cx, cy = W0 * 0.5, H0 * 0.42
    img = resplandor(img, cx, cy, 700, (255, 150, 60), 0.55)
    img = resplandor(img, cx, cy, 200, (255, 200, 120), 0.6)
    p = Pincel()
    p.rect(cx - 50, cy + 60, cx + 50, H0 * 0.86, (230, 215, 185, 255))
    p.elipse(cx, cy + 60, 50, 12, (245, 235, 210, 255))
    p.linea([(cx, cy + 60), (cx + 2, cy + 30)], 5, (30, 20, 15, 255))
    p.elipse(cx, cy - 10, 20, 52, (255, 190, 90, 255))
    p.elipse(cx, cy + 5, 11, 30, (255, 245, 210, 255))
    p.elipse(cx, H0 * 0.88, 260, 40, (60, 45, 35, 255))
    p.rect(0, H0 * 0.88, W0, H0, (40, 28, 22, 255))
    img = p.sobre(img)
    return resplandor(img, cx, cy - 10, 70, (255, 220, 150), 0.5)


def sc_libros():
    img = gradiente([(0, (20, 15, 12)), (1, (40, 30, 22))])
    img = resplandor(img, W0 * 0.7, H0 * 0.35, 700, (255, 160, 70), 0.5)
    p = Pincel()
    base = H0 * 0.72
    p.rect(0, base, W0, H0, (70, 45, 30, 255))
    colores = [(110, 40, 30), (40, 60, 90), (90, 70, 40), (60, 30, 40), (40, 70, 50), (120, 90, 50)]
    x = 200
    for i in range(14):
        ancho = 60 + (i * 17) % 50
        alto = 340 + (i * 41) % 160
        c = colores[i % len(colores)]
        p.rect(x, base - alto, x + ancho, base, c + (255,))
        p.rect(x, base - alto + 30, x + ancho, base - alto + 40, (200, 160, 80, 255))
        p.rect(x, base - 50, x + ancho, base - 40, (200, 160, 80, 255))
        x += ancho + 4
    for k in range(4):
        y = base - k * 45
        p.rect(1500 - k * 10, y - 42, 2050 + k * 6, y, colores[k] + (255,))
        p.rect(1500 - k * 10, y - 42, 1520 - k * 10, y, (220, 205, 170, 255))
    p.poly([(1150, base - 10), (1500, base - 30), (1520, base + 40), (1180, base + 60)], (230, 215, 180, 255))
    for k in range(6):
        p.linea([(1200, base + 10 + k * 8), (1480, base - 8 + k * 8)], 2, (120, 100, 80, 255))
    p.linea([(1380, base - 20), (1700, base - 420)], 5, (220, 210, 190, 255))
    p.poly([(1700, base - 420), (1640, base - 300), (1600, base - 330)], (235, 225, 205, 255))
    cx = W0 * 0.7
    p.rect(cx + 220, base - 240, cx + 270, base - 180, (230, 215, 185, 255))
    p.elipse(cx + 245, base - 270, 12, 30, (255, 200, 110, 255))
    img = p.sobre(img)
    return resplandor(img, cx + 245, base - 270, 80, (255, 210, 140), 0.5)


def sc_balanza():
    img = gradiente([(0, (25, 20, 18)), (1, (50, 38, 30))])
    img = resplandor(img, W0 * 0.5, H0 * 0.4, 800, (220, 160, 90), 0.45)
    p = Pincel()
    oro = (200, 160, 80, 255)
    cx = W0 * 0.5
    p.rect(cx - 12, H0 * 0.22, cx + 12, H0 * 0.82, oro)
    p.elipse(cx, H0 * 0.84, 200, 30, oro)
    p.elipse(cx, H0 * 0.2, 26, 26, oro)
    ang = 0.12
    lx, ly = cx - 520, H0 * 0.24 + 520 * math.sin(ang)
    rx, ry = cx + 520, H0 * 0.24 - 520 * math.sin(ang)
    p.linea([(lx, ly), (rx, ry)], 14, oro)
    f = fuente("serif_b", 64)
    for (x, y, txt) in ((lx, ly, "PODER"), (rx, ry, "LIBERTAD")):
        p.linea([(x, y), (x - 160, y + 300)], 3, oro)
        p.linea([(x, y), (x + 160, y + 300)], 3, oro)
        p.poly([(x - 200, y + 300), (x + 200, y + 300), (x + 140, y + 360), (x - 140, y + 360)], oro)
        p.texto(x, y + 430, txt, f, (235, 215, 170, 255))
    img = p.sobre(img)
    return img


def sc_caminos():
    img = gradiente([(0, (80, 110, 150)), (0.5, (235, 190, 140)), (0.62, (245, 215, 170))])
    img = nubes(img, 0.0, 0.45, (245, 230, 215), 0.45, 181)
    img = montes(img, 0.6, 0.18, (110, 115, 130), 182, 700)
    img = niebla(img, 0.48, 0.7, (230, 200, 165), 0.5)
    img = suelo(img, 0.6, (100, 100, 60), (60, 60, 35))
    p = Pincel()
    camino = (200, 175, 130, 255)
    p.poly([(W0 * 0.42, H0), (W0 * 0.58, H0), (W0 * 0.51, H0 * 0.75), (W0 * 0.49, H0 * 0.75)], camino)
    p.poly([(W0 * 0.49, H0 * 0.76), (W0 * 0.505, H0 * 0.74), (W0 * 0.2, H0 * 0.6), (W0 * 0.19, H0 * 0.605)], camino)
    p.poly([(W0 * 0.495, H0 * 0.74), (W0 * 0.51, H0 * 0.76), (W0 * 0.81, H0 * 0.605), (W0 * 0.8, H0 * 0.6)], camino)
    p.color = (30, 25, 20, 255)
    figura(p, W0 * 0.38, H0 * 0.665, 90, mira=-1)
    figura(p, W0 * 0.64, H0 * 0.665, 90, mira=1)
    for i, x in enumerate((150, 400, 1900, 2150)):
        arbol(p, x, H0 * 0.66, 260, i + 20)
    return p.sobre(img)


def sc_campamento():
    img = gradiente([(0, (8, 10, 25)), (0.6, (40, 35, 55)), (0.7, (70, 50, 50))])
    img = estrellas(img, 800, 13)
    img = montes(img, 0.66, 0.2, (25, 25, 35), 191, 600)
    img = suelo(img, 0.66, (25, 20, 20), (15, 12, 12))
    p = Pincel()
    p.color = (12, 10, 12, 255)
    for i in range(9):
        tienda(p, 150 + i * 260, H0 * (0.7 + 0.015 * (i % 2)), 220, 160)
    for (fx, fy) in ((700, 0.88), (1600, 0.84)):
        img = fogata(img, p, fx, H0 * fy, 22)
        for k in range(5):
            ang = k / 5 * math.pi * 2
            figura(p, fx + math.cos(ang) * 150, H0 * fy + 40 + math.sin(ang) * 25, 160, sombrero=k % 2 == 0,
                   mira=1 if math.cos(ang) < 0 else -1)
    for i in range(6):
        p.linea([(2000 + i * 25, H0 * 0.8), (2060 + i * 25, H0 * 0.6)], 5)
    return p.sobre(img)


def sc_fortaleza():
    img = gradiente([(0, (40, 45, 70)), (0.5, (190, 120, 90)), (0.6, (230, 160, 110))])
    img = nubes(img, 0.0, 0.5, (150, 100, 100), 0.55, 201)
    img = agua(img, 0.66, (40, 45, 60), W0 * 0.7, (240, 160, 110))
    p = Pincel()
    p.color = (25, 20, 22, 255)
    base = H0 * 0.7
    p.poly([(W0 * 0.1, base), (W0 * 0.75, base), (W0 * 0.72, base - 230), (W0 * 0.13, base - 230)])
    for i in range(20):
        x = W0 * 0.13 + i * (W0 * 0.59 / 20)
        p.rect(x, base - 260, x + 40, base - 225)
    for tx in (W0 * 0.13, W0 * 0.72):
        p.rect(tx - 70, base - 340, tx + 70, base)
        p.elipse(tx, base - 340, 70, 30)
    for i in range(5):
        canon(p, W0 * 0.25 + i * 180, base - 230, 18, 1)
    bandera(p, W0 * 0.42, base - 230, 260, [(200, 30, 35, 255), (230, 190, 40, 255), (200, 30, 35, 255)], 1)
    img = p.sobre(img)
    return humo(img, 203, 0.4, (160, 140, 130), 0.3, 0.7)


def sc_lima():
    return sc_colonia("lima")


def sc_estatua():
    img = gradiente([(0, (40, 70, 120)), (0.55, (220, 170, 120)), (0.75, (245, 210, 160))])
    img = nubes(img, 0.0, 0.6, (240, 215, 200), 0.45, 211)
    img = resplandor(img, W0 * 0.62, H0 * 0.5, 600, (255, 190, 110), 0.5)
    p = Pincel()
    p.color = (30, 26, 28, 255)
    cx = W0 * 0.5
    p.rect(cx - 260, H0 * 0.68, cx + 260, H0)
    p.rect(cx - 300, H0 * 0.66, cx + 300, H0 * 0.7)
    p.rect(cx - 240, H0 * 0.94, cx + 240, H0)
    jinete(p, cx - 40, H0 * 0.66, 360, fase=0.4, lanza=False)
    p.linea([(cx - 10, H0 * 0.66 - 290), (cx + 220, H0 * 0.66 - 520)], 14)
    for i in range(8):
        arbol(p, 100 + i * 70, H0, 240, i + 40)
        arbol(p, W0 - 100 - i * 70, H0, 240, i + 60)
    return p.sobre(img)


def sc_dos_figuras():
    img = gradiente([(0, (30, 24, 20)), (1, (55, 42, 34))])
    p = Pincel()
    luz = (255, 225, 175, 255)
    p.rect(W0 * 0.38, H0 * 0.1, W0 * 0.62, H0 * 0.72, luz)
    img = p.sobre(img, 4)
    img = resplandor(img, W0 * 0.5, H0 * 0.4, 800, (255, 190, 120), 0.45)
    p = Pincel()
    p.color = (22, 16, 14, 255)
    p.rect(W0 * 0.497, H0 * 0.1, W0 * 0.503, H0 * 0.72)
    p.rect(W0 * 0.38, H0 * 0.4, W0 * 0.62, H0 * 0.41)
    p.rect(0, H0 * 0.86, W0, H0)
    figura(p, W0 * 0.4, H0 * 0.9, 640, mira=1, brazo=0.55)
    figura(p, W0 * 0.6, H0 * 0.9, 620, mira=-1, brazo=0.0)
    p.rect(W0 * 0.43, H0 * 0.64, W0 * 0.57, H0 * 0.67)
    return p.sobre(img)


# ---- retratos en silueta (estilo camafeo de la época) ----

PERFIL_H = [(38, 70), (34, 58), (33, 45), (36, 33), (45, 24), (55, 22.5), (62, 27), (65, 35), (66.3, 41), (65.6, 43.5),
            (71.5, 50.5), (67.2, 52.6), (67.6, 54.2), (68.2, 55.6), (66.6, 56.6), (67.6, 58.2), (66, 60.2), (66.6, 63.2),
            (63.4, 66.6), (58.5, 67.4), (56, 70.5), (57, 72), (63, 73.5), (64.5, 80), (69, 90), (81, 100), (8, 100),
            (12, 87), (22, 80), (36, 72)]
PERFIL_M = [(40, 70), (37, 58), (36, 45), (39, 34), (47, 26), (56, 25), (62, 29), (64.5, 36), (65.3, 41.5), (64.8, 44),
            (69.2, 50.5), (66.2, 52), (66.6, 53.6), (67, 55), (65.6, 56), (66.4, 57.6), (65, 59.5), (65.3, 62),
            (62, 65), (57.5, 66), (56, 70), (60, 76), (68, 86), (80, 100), (12, 100), (18, 86), (28, 78), (38, 72)]


def camafeo(nombre, fechas, perfil, mujer=False, espejo=False):
    img = gradiente([(0, (30, 22, 18)), (1, (55, 40, 30))])
    img = resplandor(img, W0 * 0.5, H0 * 0.45, 900, (180, 120, 60), 0.35)
    p = Pincel()
    cx, cy, rx, ry = W0 * 0.5, H0 * 0.45, 330, 430
    p.elipse(cx, cy, rx + 34, ry + 34, (150, 110, 50, 255))
    p.elipse(cx, cy, rx + 22, ry + 22, (215, 175, 95, 255))
    p.elipse(cx, cy, rx + 8, ry + 8, (120, 85, 40, 255))
    p.elipse(cx, cy, rx, ry, (225, 205, 165, 255))
    img = p.sobre(img)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    dentro = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1
    som = np.clip(np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2), 0, 1) ** 3
    img = mezclar(img, (150, 120, 80), som * dentro * 0.6)
    p = Pincel()
    p.color = (25, 20, 22, 255)
    esc = 7.0
    ox, oy = cx - 50 * esc, cy - 60 * esc

    def T(pt):
        x, y = pt
        if espejo:
            x = 100 - x
        return (ox + x * esc, oy + y * esc)

    p.poly([T(q) for q in perfil])
    if mujer:
        for (x, y, r) in ((34, 40, 7), (36, 30, 6), (44, 24, 5), (30, 48, 5), (60, 28, 3), (63, 33, 2.5)):
            q = T((x, y))
            p.elipse(q[0], q[1], r * esc, r * esc)
        q = T((30, 37))
        p.elipse(q[0], q[1], 9 * esc, 8 * esc)
    else:
        for (x, y, r) in ((40, 27, 5), (48, 23, 4.5), (56, 23, 3.5), (60.5, 25.5, 2.5), (36, 34, 5), (34, 44, 4),
                          (52, 50, 2.6), (52, 56, 2.6)):
            q = T((x, y))
            p.elipse(q[0], q[1], r * esc, r * esc)
        oro = (200, 160, 70, 255)
        p.linea([T((56.5, 72.5)), T((63, 74)), T((64.5, 80))], 1.2 * esc, oro)
        for k in range(9):
            a = T((12 + k * 1.3, 86 - k * 0.7))
            b = T((10.5 + k * 1.5, 93 - k * 0.5))
            p.linea([a, b], 0.6 * esc, oro)
        p.poly([T((12, 87)), T((22, 80)), T((26, 82)), T((15, 88.5))], oro)
        for k in range(4):
            q = T((66, 84 + k * 4))
            p.elipse(q[0], q[1], 1.0 * esc, 1.0 * esc, oro)
    img = p.sobre(img)
    h, w = img.shape[:2]
    fuera = ~dentro
    # recorta la silueta al óvalo
    fondo = gradiente([(0, (30, 22, 18)), (1, (55, 40, 30))])
    fondo = resplandor(fondo, W0 * 0.5, H0 * 0.45, 900, (180, 120, 60), 0.35)
    marco = (((xx - cx) / (rx + 34)) ** 2 + ((yy - cy) / (ry + 34)) ** 2 < 1) & fuera
    img = np.where((fuera & ~marco)[..., None], fondo, img)
    p = Pincel()
    p.elipse(cx, cy, rx + 34, ry + 34, None, (150, 110, 50, 255), 12)
    p.elipse(cx, cy, rx + 22, ry + 22, None, (225, 185, 105, 255), 8)
    p.elipse(cx, cy, rx + 4, ry + 4, None, (100, 70, 35, 255), 6)
    placa_y = cy + ry + 95
    p.rect(cx - 360, placa_y - 55, cx + 360, placa_y + 55, (150, 110, 50, 255))
    p.rect(cx - 350, placa_y - 45, cx + 350, placa_y + 45, (205, 165, 90, 255))
    p.texto(cx, placa_y - 2, nombre, fuente("serif_b", 50), (50, 32, 20, 255))
    img = p.sobre(img)
    if fechas:
        p = Pincel()
        p.texto(cx, placa_y + 95, fechas, fuente("serif_i", 40), (210, 185, 140, 255))
        img = p.sobre(img)
    return img


def sc_linea_vida():
    img = gradiente([(0, (30, 22, 18)), (1, (50, 38, 30))])
    img = resplandor(img, W0 * 0.5, H0 * 0.5, 900, (170, 120, 60), 0.35)
    p = Pincel()
    oro = (215, 175, 95, 255)
    crema = (235, 220, 190, 255)
    y = H0 * 0.52
    x0, x1 = W0 * 0.1, W0 * 0.9
    p.linea([(x0, y), (x1, y)], 6, oro)
    hitos = [(1783, "Nace en Caracas"), (1805, "Juramento\ndel Monte Sacro"), (1813, "Campaña\nAdmirable"),
             (1819, "Boyacá y\nGran Colombia"), (1824, "Ayacucho"), (1830, "Muere en\nSanta Marta")]
    for i, (anio, txt) in enumerate(hitos):
        x = x0 + (anio - 1783) / (1830 - 1783) * (x1 - x0)
        p.elipse(x, y, 20, 20, oro)
        p.elipse(x, y, 10, 10, (60, 40, 25, 255))
        arriba = i % 2 == 0
        p.texto(x, y + (-70 if arriba else 70), str(anio), fuente("serif_b", 62), oro)
        for k, linea in enumerate(txt.split("\n")):
            dy = (-150 - (len(txt.split("\n")) - 1 - k) * 48) if arriba else (140 + k * 48)
            p.texto(x, y + dy, linea, fuente("serif", 42), crema)
    return p.sobre(img)


def sc_suscribete():
    img = gradiente([(0, (25, 18, 15)), (1, (45, 32, 25))])
    img = resplandor(img, W0 * 0.5, H0 * 0.45, 900, (190, 130, 60), 0.4)
    p = Pincel()
    oro = (215, 175, 95, 255)
    p.texto(W0 * 0.5, H0 * 0.3, "CURIOSIDADES DEL MUNDO", fuente("serif_b", 110), oro)
    p.linea([(W0 * 0.3, H0 * 0.38), (W0 * 0.7, H0 * 0.38)], 3, oro)
    p.texto(W0 * 0.5, H0 * 0.45, "Historias que cambiaron el mundo", fuente("serif_i", 60), (235, 220, 190, 255))
    bx, by = W0 * 0.5, H0 * 0.64
    p.d.rounded_rectangle(((bx - 330) * SS, (by - 75) * SS, (bx + 330) * SS, (by + 75) * SS), radius=40 * SS,
                          fill=(200, 30, 30, 255))
    p.texto(bx, by, "SUSCRÍBETE", fuente("sans_b", 80), (255, 255, 255, 255))
    cx, cy = bx + 470, by
    p.elipse(cx, cy + 10, 60, 60, (235, 220, 190, 255))
    p.rect(cx - 60, cy + 10, cx + 60, cy + 55, (235, 220, 190, 255))
    p.rect(cx - 80, cy + 50, cx + 80, cy + 62, (235, 220, 190, 255))
    p.elipse(cx, cy + 75, 16, 16, (235, 220, 190, 255))
    p.texto(W0 * 0.5, H0 * 0.8, "Activa las notificaciones", fuente("sans", 48), (210, 190, 160, 255))
    return p.sobre(img)


# ---- documentos (pergaminos) ----

DOCUMENTOS = {
    "doc_19abril": ("19 de abril de 1810", "Junta Suprema de Caracas", "Caracas"),
    "doc_independencia": ("5 de julio de 1811", "Acta de la Declaración de Independencia", "Congreso de Venezuela"),
    "doc_cartagena": ("15 de diciembre de 1812", "Manifiesto de Cartagena", "Simón Bolívar"),
    "doc_jamaica": ("6 de septiembre de 1815", "Carta de Jamaica", "Kingston · Simón Bolívar"),
    "doc_angostura": ("17 de diciembre de 1819", "Ley Fundamental de la República de Colombia", "Congreso de Angostura"),
    "doc_cucuta": ("1821", "Constitución de Cúcuta", "Congreso General de Colombia"),
    "doc_bolivia": ("1826", "Proyecto de Constitución para Bolivia", "Simón Bolívar"),
    "doc_renuncia": ("1830", "Renuncia a la Presidencia", "Bogotá · Simón Bolívar"),
}


def sc_documento(clave):
    fecha, titulo, firma = DOCUMENTOS[clave]
    img = gradiente([(0, (35, 25, 20)), (1, (60, 42, 30))])
    h, w = img.shape[:2]
    madera = ruido2d(w, h, 25, 3, 7)
    vetas = np.sin(np.linspace(0, 60, h)[:, None] + madera * 8)
    img = img + vetas[..., None] * 8
    img = resplandor(img, W0 * 0.65, H0 * 0.3, 900, (200, 140, 70), 0.35)
    # pergamino
    x0, y0, x1, y1 = W0 * 0.24, H0 * 0.07, W0 * 0.76, H0 * 1.05
    mascara = np.zeros((h, w))
    borde = (ruido2d(w, h, 30, 3, 8) - 0.5) * 30
    mascara = ((xx := np.arange(w)[None, :]) > x0 + borde) & (xx < x1 - borde) & \
              (np.arange(h)[:, None] > y0 + borde) & (np.arange(h)[:, None] < y1)
    sombra = Image.fromarray((mascara * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(25))
    img = mezclar(img, (10, 6, 4), np.roll(np.roll(np.asarray(sombra, float) / 255, 18, 0), 18, 1) * 0.7)
    papel = gradiente([(0, (232, 214, 172)), (1, (214, 190, 140))])
    manchas = ruido2d(w, h, 140, 5, 9)
    papel = papel - (manchas[..., None] - 0.5) * 50
    yy, xx2 = np.mgrid[0:h, 0:w]
    dist_borde = np.minimum.reduce([xx2 - x0, x1 - xx2, yy - y0]).clip(0) / 120
    papel = papel - (1 - np.clip(dist_borde, 0, 1))[..., None] * 60
    img = np.where(mascara[..., None], papel, img)
    p = Pincel()
    tinta = (60, 38, 25, 255)
    cx = W0 * 0.5
    p.texto(cx, H0 * 0.16, fecha, fuente("libre_i", 46), tinta)
    lineas_titulo = []
    f = fuente("serif_b", 78)
    actual = ""
    for pal in titulo.split():
        prueba = (actual + " " + pal).strip()
        if f.getlength(prueba) > W0 * 0.44 and actual:
            lineas_titulo.append(actual)
            actual = pal
        else:
            actual = prueba
    lineas_titulo.append(actual)
    y = H0 * 0.27
    for lt in lineas_titulo:
        p.texto(cx, y, lt, f, tinta)
        y += 90
    p.linea([(cx - 260, y), (cx + 260, y)], 3, tinta)
    rng = random.Random(hash(clave) % 1000)
    y += 70
    while y < H0 * 0.86:
        x = W0 * 0.29 + (40 if rng.random() < 0.15 else 0)
        fin = W0 * 0.71 - rng.uniform(0, 120)
        while x < fin:
            largo = rng.uniform(25, 110)
            pts = []
            for t in np.linspace(0, 1, 8):
                pts.append((x + largo * t, y + math.sin(t * 9 + x) * 6 + rng.uniform(-2, 2)))
            p.linea(pts, 2.6, (75, 50, 35, 200))
            x += largo + rng.uniform(14, 26)
        y += 52
    p.texto(W0 * 0.6, H0 * 0.92, firma, fuente("libre_i", 52), tinta)
    p.elipse(W0 * 0.34, H0 * 0.92, 70, 70, (150, 30, 30, 255))
    p.elipse(W0 * 0.34, H0 * 0.92, 52, 52, None, (110, 20, 20, 255), 5)
    p.linea([(W0 * 0.83, H0 * 0.95), (W0 * 0.95, H0 * 0.35)], 8, (230, 220, 200, 255))
    p.poly([(W0 * 0.95, H0 * 0.35), (W0 * 0.92, H0 * 0.55), (W0 * 0.89, H0 * 0.52)], (240, 230, 210, 255))
    p.elipse(W0 * 0.85, H0 * 0.95, 60, 30, (30, 25, 30, 255))
    return p.sobre(img)


# ======================= registro =======================

ESCENAS = {
    "andes": lambda: sc_andes(False),
    "andes_marcha": lambda: sc_andes(True),
    "volcan": sc_volcan,
    "batalla": lambda: sc_batalla("noche"),
    "batalla_humo": lambda: sc_batalla("humo"),
    "batalla_victoria": lambda: sc_batalla("victoria"),
    "caballeria": sc_caballeria,
    "llanos": lambda: sc_llanos(False),
    "llanos_noche": lambda: sc_llanos(True),
    "rio": sc_rio,
    "colonia": sc_colonia,
    "lima": sc_lima,
    "entrada_caracas": sc_entrada,
    "hacienda": sc_hacienda,
    "quinta": sc_quinta,
    "barco": lambda: sc_mar("dia"),
    "barco_noche": lambda: sc_mar("noche"),
    "flota": lambda: sc_mar("flota"),
    "caribe": sc_caribe,
    "atardecer_mar": sc_atardecer_mar,
    "amanecer": sc_amanecer,
    "tormenta": sc_tormenta,
    "noche": lambda: sc_noche(False),
    "ventana": lambda: sc_noche(True),
    "roma": sc_roma,
    "congreso": sc_congreso,
    "boda": sc_boda,
    "vela": sc_vela,
    "libros": sc_libros,
    "balanza": sc_balanza,
    "caminos": sc_caminos,
    "campamento": sc_campamento,
    "fortaleza": sc_fortaleza,
    "estatua": sc_estatua,
    "dos_figuras": sc_dos_figuras,
    "retrato": lambda: camafeo("SIMÓN BOLÍVAR", "1783 – 1830", PERFIL_H),
    "sucre": lambda: camafeo("ANTONIO JOSÉ DE SUCRE", "1795 – 1830", PERFIL_H, espejo=True),
    "manuela": lambda: camafeo("MANUELA SÁENZ", "1797 – 1856", PERFIL_M, mujer=True),
    "linea_vida": sc_linea_vida,
    "suscribete": sc_suscribete,
}
for _k in DOCUMENTOS:
    ESCENAS[_k] = (lambda k: (lambda: sc_documento(k)))(_k)

SIN_ACABADO = {"linea_vida", "suscribete"}


def generar(nombre, forzar=False):
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / f"{nombre}.png"
    if ruta.exists() and not forzar:
        return ruta
    propia = next((q for q in (AQUI / "imagenes").glob(f"{nombre}.*")), None) if (AQUI / "imagenes").exists() else None
    if propia:
        im = Image.open(propia).convert("RGB")
        esc = max(W0 / im.width, H0 / im.height)
        im = im.resize((int(im.width * esc + 0.5), int(im.height * esc + 0.5)), Image.LANCZOS)
        l, t = (im.width - W0) // 2, (im.height - H0) // 2
        im.crop((l, t, l + W0, t + H0)).save(ruta)
        return ruta
    arr = ESCENAS[nombre]()
    if nombre in SIN_ACABADO:
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    else:
        im = acabado(arr)
    im.save(ruta)
    return ruta


if __name__ == "__main__":
    nombres = sys.argv[1:] or list(ESCENAS)
    for n in nombres:
        print("dibujando", n)
        generar(n, forzar=True)
