"""Dibujo de escenas: siluetas, paisajes, mapas, documentos y efectos.

Cada escena se prepara una vez (capas estáticas grandes) y luego se anima cuadro a
cuadro con movimiento de cámara, partículas, fogonazos, etc.
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080                 # tamaño final
LW, LH = 2112, 1188               # capas con margen para mover la cámara
SS = 2                            # superresolución para bordes suaves

FUENTES = Path(__file__).parent / "fuentes"


@lru_cache(None)
def fuente(nombre, tam):
    rutas = {
        "titulo": "cinzel-latin-700-normal.woff",
        "titulo_n": "cinzel-latin-400-normal.woff",
        "deco": "cinzel-decorative-latin-700-normal.woff",
        "texto": "eb-garamond-latin-400-normal.woff",
        "texto_b": "eb-garamond-latin-700-normal.woff",
        "antigua": "im-fell-english-latin-400-normal.woff",
    }
    return ImageFont.truetype(str(FUENTES / rutas[nombre]), tam)


# ------------------------------------------------------------------ texturas
def ruido_fractal(w, h, semilla, octavas=6, base=4, persistencia=0.55):
    rng = np.random.default_rng(semilla)
    total = np.zeros((h, w), np.float32)
    amp, suma = 1.0, 0.0
    for o in range(octavas):
        n = base * 2 ** o
        grid = rng.random((max(2, int(n * h / w)) + 1, n + 1)).astype(np.float32)
        capa = Image.fromarray(grid).resize((w, h), Image.BICUBIC)
        total += np.asarray(capa) * amp
        suma += amp
        amp *= persistencia
    total /= suma
    total -= total.min()
    return total / max(total.max(), 1e-6)


def degradado(w, h, colores):
    """colores: lista de (posición 0..1, (r,g,b)) de arriba a abajo."""
    y = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, 1, 3), np.float32)
    pos = [p for p, _ in colores]
    for c in range(3):
        out[:, 0, c] = np.interp(y[:, 0], pos, [col[c] for _, col in colores])
    return np.repeat(out, w, axis=1)


def cielo(w, h, colores, semilla=0, nubes=0.35, color_nube=(255, 230, 200), sol=None):
    arr = degradado(w, h, colores)
    if sol:
        sx, sy, radio, col = sol
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt((xx - sx * w) ** 2 + (yy - sy * h) ** 2) / (radio * w)
        brillo = np.exp(-d ** 2 * 2.5)[..., None]
        arr = arr + np.array(col, np.float32) * brillo * 0.9
    if nubes:
        n = ruido_fractal(w, h, semilla, 6, 3)
        n = np.clip((n - 0.45) * 2.6, 0, 1) ** 1.4
        n *= (1 - np.linspace(0, 1, h)[:, None] ** 0.8)
        arr = arr * (1 - n[..., None] * nubes) + np.array(color_nube, np.float32) * n[..., None] * nubes
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def textura_papel(w, h, semilla=3, tono=(222, 200, 160)):
    n = ruido_fractal(w, h, semilla, 7, 6, 0.6)
    fino = np.random.default_rng(semilla).random((h, w)).astype(np.float32)
    arr = np.array(tono, np.float32) * (0.82 + 0.25 * n[..., None]) - fino[..., None] * 12
    yy, xx = np.mgrid[0:h, 0:w]
    borde = np.minimum.reduce([xx, yy, w - xx, h - yy]).astype(np.float32) / (0.12 * min(w, h))
    arr *= (0.55 + 0.45 * np.clip(borde, 0, 1) ** 0.6)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def humo(w, h, semilla, color=(200, 190, 175), densidad=0.8):
    n = ruido_fractal(w, h, semilla, 6, 3, 0.6)
    a = np.clip((n - 0.35) * 2.2, 0, 1) ** 1.5 * 255 * densidad
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a.astype(np.uint8)
    im = Image.fromarray(arr, "RGBA")
    im.info["deriva"] = 1
    return im


# ------------------------------------------------------- lienzo con supermuestreo
class Lienzo:
    """Capa RGBA dibujada al doble de tamaño y reducida al final (bordes suaves)."""

    def __init__(self, w=LW, h=LH, fondo=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * SS, h * SS), fondo)
        self.d = ImageDraw.Draw(self.im)

    def p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, fill):
        self.d.polygon(self.p(pts), fill=fill)

    def elipse(self, cx, cy, rx, ry, fill, outline=None, ancho=1):
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS],
                       fill=fill, outline=outline, width=ancho * SS)

    def rect(self, x0, y0, x1, y1, fill):
        self.d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill)

    def linea(self, pts, fill, ancho):
        self.d.line(self.p(pts), fill=fill, width=max(1, int(ancho * SS)), joint="curve")

    def texto(self, xy, txt, f, fill, ancla="mm", **kw):
        fnt = fuente(f[0], int(f[1] * SS))
        self.d.text((xy[0] * SS, xy[1] * SS), txt, font=fnt, fill=fill, anchor=ancla, **kw)

    def imagen(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


# ------------------------------------------------------------------- siluetas
def tf(pts, x, y, s, flip=False):
    return [((-px if flip else px) * s + x, py * s + y) for px, py in pts]


def soldado(L, x, y, s, fase=0.0, col=(10, 8, 8, 255), flip=False, bandera=None):
    """Soldado de infantería con chacó y mosquete. (x,y) = pies, s = altura en px."""
    P = lambda pts: tf(pts, x, y, s, flip)
    L.poly(P([(-0.075, -1.0), (0.075, -1.0), (0.065, -0.88), (-0.065, -0.88)]), col)
    L.poly(P([(-0.015, -1.09), (0.015, -1.09), (0.012, -1.0), (-0.012, -1.0)]), col)
    L.poly(P([(-0.09, -0.88), (0.11, -0.88), (0.1, -0.86), (-0.09, -0.86)]), col)
    L.elipse(*P([(0.005, -0.82)])[0], 0.055 * s, 0.06 * s, col)
    L.poly(P([(-0.085, -0.76), (0.085, -0.76), (0.095, -0.48), (-0.095, -0.48)]), col)
    L.poly(P([(-0.16, -0.74), (-0.07, -0.74), (-0.07, -0.55), (-0.15, -0.55)]), col)
    L.poly(P([(-0.095, -0.5), (0.095, -0.5), (0.06, -0.38), (-0.13, -0.36)]), col)
    paso = math.sin(fase) * 0.13
    for sg in (1, -1):
        L.linea(P([(0.0, -0.48), (paso * sg * 0.5, -0.24), (paso * sg, 0.0)]), col, 0.055 * s)
        L.linea(P([(paso * sg, -0.01), (paso * sg + 0.06, -0.01)]), col, 0.03 * s)
    L.linea(P([(0.06, -0.73), (0.09, -0.58)]), col, 0.04 * s)
    if bandera:
        L.linea(P([(0.09, -0.6), (0.09, -1.75)]), col, 0.02 * s)
        ondas = [(0.09 + 0.55 * i / 10, -1.72 + 0.03 * math.sin(i + fase * 3)) for i in range(11)]
        abajo = [(px, py + 0.32) for px, py in ondas[::-1]]
        franjas = [(0, 0.33, (30, 50, 140, 255)), (0.33, 0.66, (225, 220, 210, 255)),
                   (0.66, 1.0, (170, 30, 35, 255))] if bandera == "tricolor" else [(0, 1, bandera)]
        for a, b, c in franjas:
            i0, i1 = int(a * 10), int(b * 10)
            L.poly(P(ondas[i0:i1 + 1] + abajo[10 - i1:11 - i0]), c)
    else:
        L.linea(P([(0.07, -0.55), (-0.03, -1.32)]), col, 0.02 * s)
        L.linea(P([(-0.03, -1.32), (-0.045, -1.46)]), col, 0.008 * s)


def canon_pieza(L, x, y, s, col=(12, 10, 10, 255), flip=False):
    """Cañón de campaña. Devuelve la posición de la boca (para el fogonazo)."""
    P = lambda pts: tf(pts, x, y, s, flip)
    L.poly(P([(0.0, -0.32), (-1.05, -0.02), (-1.05, 0.02), (0.05, -0.24)]), col)
    L.poly(P([(-0.3, -0.42), (0.95, -0.55), (0.98, -0.53), (0.98, -0.7), (0.95, -0.68), (-0.3, -0.7),
              (-0.36, -0.56)]), col)
    cx, cy = P([(0.0, -0.35)])[0]
    L.elipse(cx, cy, 0.35 * s, 0.35 * s, None, outline=col, ancho=max(2, int(0.05 * s)))
    for k in range(8):
        a = k * math.pi / 4
        L.linea([(cx, cy), (cx + math.cos(a) * 0.33 * s, cy + math.sin(a) * 0.33 * s)], col, 0.03 * s)
    L.elipse(cx, cy, 0.07 * s, 0.07 * s, col)
    return P([(1.0, -0.615)])[0]


def napoleon_busto(L, x, y, s, col=(8, 6, 6, 255), detalle=None):
    """Busto frontal con el bicornio. (x,y)=centro de la cabeza, s=alto de la cabeza."""
    P = lambda pts: tf(pts, x, y, s)
    claro = (228, 220, 202, 255) if detalle else col
    L.poly(P([(-1.8, 2.5), (-1.72, 1.05), (-1.35, 0.76), (-0.5, 0.6), (0.5, 0.6), (1.35, 0.76),
              (1.72, 1.05), (1.8, 2.5)]), col)
    L.poly(P([(-0.4, 0.62), (0.4, 0.62), (0.12, 1.75), (-0.12, 1.75)]), claro)
    L.poly(P([(-0.3, 0.4), (0.3, 0.4), (0.34, 0.7), (0.05, 0.95), (-0.05, 0.95), (-0.34, 0.7)]), claro)
    for sg in (-1, 1):
        L.poly(P([(sg * 0.62, 1.0), (sg * 0.48, 0.35), (sg * 0.22, 0.62), (sg * 0.3, 0.9), (sg * 0.12, 1.8),
                  (sg * 0.7, 1.8)]), col)
        L.elipse(*P([(sg * 1.3, 0.82)])[0], 0.46 * s, 0.16 * s, col)
        for k in range(9):
            fx = sg * (0.95 + k * 0.09)
            L.linea(P([(fx, 0.86), (fx + sg * 0.02, 1.22)]), col, 0.035 * s)
    L.poly(P([(-0.42, -0.4), (0.42, -0.4), (0.46, -0.05), (0.38, 0.25), (0.2, 0.45), (0.0, 0.52), (-0.2, 0.45),
              (-0.38, 0.25), (-0.46, -0.05)]), col)
    L.poly(P([(-0.27, 0.3), (0.27, 0.3), (0.27, 0.45), (-0.27, 0.45)]), col)
    arriba = [(1.55 * math.cos(a), -0.42 - 0.85 * math.sin(a) ** 0.9) for a in np.linspace(0, math.pi, 40)]
    abajo = [(1.55 * math.cos(a), -0.36 - 0.05 * math.sin(a)) for a in np.linspace(math.pi, 0, 40)]
    L.poly(P([(1.62, -0.3)] + arriba + [(-1.62, -0.3)] + abajo), col)
    if detalle:  # escarapela y botones dorados
        L.elipse(*P([(-1.05, -0.5)])[0], 0.14 * s, 0.14 * s, detalle)
        for k in range(4):
            for sg in (-1, 1):
                L.elipse(*P([(sg * 0.42, 1.1 + k * 0.3)])[0], 0.045 * s, 0.045 * s, detalle)


def napoleon_espalda(L, x, y, s, col=(8, 6, 6, 255)):
    """Napoleón de pie, de espaldas, con capote y manos atrás. (x,y)=pies, s=altura."""
    P = lambda pts: tf(pts, x, y, s)
    arriba = [(0.17 * math.cos(a), -0.905 - 0.1 * math.sin(a) ** 0.7) for a in np.linspace(0, math.pi, 24)]
    abajo = [(0.17 * math.cos(a), -0.895 - 0.025 * math.sin(a)) for a in np.linspace(math.pi, 0, 24)]
    L.poly(P([(0.18, -0.88)] + arriba + [(-0.18, -0.88)] + abajo), col)
    L.elipse(*P([(0, -0.86)])[0], 0.05 * s, 0.058 * s, col)
    for sg in (-1, 1):
        L.elipse(*P([(sg * 0.13, -0.775)])[0], 0.06 * s, 0.025 * s, col)
    L.poly(P([(-0.06, -0.82), (0.06, -0.82), (0.15, -0.78), (0.15, -0.6), (0.2, -0.32), (0.26, -0.2),
              (-0.26, -0.2), (-0.2, -0.32), (-0.15, -0.6), (-0.15, -0.78)]), col)
    L.poly(P([(-0.09, -0.21), (-0.02, -0.21), (-0.025, 0.0), (-0.1, 0.0)]), col)
    L.poly(P([(0.02, -0.21), (0.09, -0.21), (0.1, 0.0), (0.025, 0.0)]), col)


def perfil_mujer(L, x, y, s, col=(8, 6, 6, 255), joya=None):
    """Perfil femenino estilo Imperio (moño y rizos). (x,y)=centro cabeza, s=alto cabeza."""
    P = lambda pts: tf(pts, x, y, s)
    L.elipse(*P([(0.0, -0.3)])[0], 0.4 * s, 0.47 * s, col)
    L.elipse(*P([(-0.38, -0.5)])[0], 0.25 * s, 0.24 * s, col)
    for cx, cy, r in [(0.22, -0.72, 0.1), (0.05, -0.8, 0.11), (-0.15, -0.78, 0.1), (0.31, -0.6, 0.08),
                      (-0.55, -0.62, 0.09), (-0.6, -0.4, 0.07), (0.3, -0.15, 0.06), (0.24, -0.02, 0.07)]:
        L.elipse(*P([(cx, cy)])[0], r * s, r * s, col)
    L.poly(P([(0.25, -0.62), (0.34, -0.45), (0.37, -0.3), (0.49, -0.1), (0.4, -0.05), (0.42, 0.02),
              (0.37, 0.06), (0.4, 0.11), (0.33, 0.24), (0.18, 0.3), (0.16, 0.55), (0.55, 0.92),
              (0.85, 1.5), (-1.0, 1.5), (-0.7, 0.92), (-0.22, 0.55), (-0.2, 0.1), (-0.1, -0.2)]), col)
    if joya:
        L.linea(P([(-0.3, -0.72), (0.0, -0.78), (0.25, -0.7)]), joya, 0.035 * s)
        for k in range(5):
            L.elipse(*P([(-0.2 + k * 0.1, -0.75 - 0.02 * (2 - abs(k - 2)))])[0], 0.03 * s, 0.03 * s, joya)
        for k in range(12):
            a = -0.15 + k * 0.12
            L.elipse(*P([(a * 0.9 + 0.1, 0.62 + 0.18 * math.sin((k / 11) * math.pi))])[0],
                     0.03 * s, 0.03 * s, joya)


def perfil_hombre(L, x, y, s, col=(8, 6, 6, 255), peluca=True):
    P = lambda pts: tf(pts, x, y, s)
    L.elipse(*P([(-0.02, -0.3)])[0], 0.42 * s, 0.5 * s, col)
    if peluca:
        for cy in (-0.3, -0.1):
            L.elipse(*P([(-0.2, cy)])[0], 0.16 * s, 0.1 * s, col)
        L.linea(P([(-0.38, -0.05), (-0.45, 0.3)]), col, 0.06 * s)
        L.elipse(*P([(-0.4, 0.0)])[0], 0.07 * s, 0.05 * s, col)
    L.poly(P([(0.3, -0.7), (0.38, -0.4), (0.4, -0.3), (0.55, -0.08), (0.42, -0.04), (0.43, 0.03),
              (0.39, 0.08), (0.41, 0.12), (0.34, 0.27), (0.2, 0.33), (0.2, 0.55), (0.9, 0.85),
              (1.1, 1.5), (-1.1, 1.5), (-0.9, 0.85), (-0.25, 0.55), (-0.25, 0.1), (-0.1, -0.2)]), col)
    L.poly(P([(0.2, 0.5), (0.42, 0.58), (0.3, 0.85), (0.15, 0.7)]), (235, 228, 215, 255) if col[3] else col)


def barco(L, x, y, s, col=(10, 9, 9, 255), velas=(225, 215, 190, 255), flip=False):
    """Navío de línea. (x,y)=línea de flotación centro, s=eslora."""
    P = lambda pts: tf(pts, x, y, s, flip)
    L.poly(P([(-0.5, -0.06), (0.45, -0.06), (0.55, -0.13), (0.42, 0.06), (-0.44, 0.06), (-0.52, -0.12)]), col)
    L.poly(P([(-0.5, -0.06), (-0.55, -0.16), (-0.42, -0.14), (-0.4, -0.06)]), col)
    for mx, alto in ((-0.25, 0.7), (0.05, 0.85), (0.32, 0.65)):
        L.linea(P([(mx, -0.06), (mx, -alto)]), col, 0.012 * s)
        for k, (ya, yb, an) in enumerate(((0.15, 0.32, 0.12), (0.35, 0.52, 0.11), (0.55, 0.68, 0.08))):
            if yb > alto - 0.02:
                continue
            L.poly(P([(mx - an, -yb), (mx + an, -yb), (mx + an * 1.1, -ya), (mx - an * 1.1, -ya)]), velas)
    L.linea(P([(0.45, -0.1), (0.7, -0.3)]), col, 0.008 * s)
    return [P([(xx, -0.02)])[0] for xx in np.linspace(-0.38, 0.38, 7)]


def cupula_cebolla(L, x, y, s, col):
    P = lambda pts: tf(pts, x, y, s)
    pts = []
    for a in np.linspace(0, math.pi, 30):
        r = math.sin(a) * (1 + 0.6 * math.sin(a * 0.9)) * 0.5
        pts.append((r, -a / math.pi * 1.4))
    L.poly(P(pts + [(-px, py) for px, py in pts[::-1]]), col)
    L.linea(P([(0, -1.4), (0, -1.9)]), col, 0.06 * s)
    L.linea(P([(-0.15, -1.75), (0.15, -1.75)]), col, 0.05 * s)


def resplandor(tam, color, potencia=2.0):
    """Sprite RGBA con un brillo radial (para fogonazos, velas, soles)."""
    yy, xx = np.mgrid[0:tam, 0:tam]
    d = np.sqrt((xx - tam / 2) ** 2 + (yy - tam / 2) ** 2) / (tam / 2)
    a = np.clip(1 - d, 0, 1) ** potencia
    arr = np.zeros((tam, tam, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def con_brillo(capa, color=(255, 190, 90), radio=18, fuerza=1.6):
    """Añade un halo de luz (contraluz) alrededor de las siluetas de una capa."""
    alfa = capa.split()[3]
    halo = alfa.filter(ImageFilter.GaussianBlur(radio)).point(lambda v: min(255, int(v * fuerza)))
    brillo = Image.new("RGBA", capa.size, color + (0,))
    brillo.putalpha(halo)
    return Image.alpha_composite(brillo, capa)


# -------------------------------------------------------------- paisajes base
def colinas(L, base_y, amp, color, semilla, rugosidad=0.5, pasos=60):
    rng = np.random.default_rng(semilla)
    fases = rng.random(4) * 10
    pts = []
    for i in range(pasos + 1):
        xx = i / pasos * L.w
        v = sum(math.sin(xx / L.w * f * math.pi + fases[k]) / (k + 1) ** rugosidad
                for k, f in enumerate((1.3, 3.1, 7.3, 15.7)))
        pts.append((xx, base_y - amp * (0.5 + 0.35 * v)))
    L.poly(pts + [(L.w, L.h), (0, L.h)], color)


def mar(w, h, horizonte, arriba, abajo, semilla=5, brillo=None):
    """Mar con reflejos: devuelve RGBA del tamaño completo, transparente sobre el horizonte."""
    arr = np.zeros((h, w, 4), np.float32)
    hy = int(horizonte * h)
    zona = degradado(w, h - hy, [(0, arriba), (1, abajo)])
    n = ruido_fractal(w, h - hy, semilla, 5, 8)
    lineas = (np.sin(np.linspace(0, 1, h - hy)[:, None] ** 0.5 * 260 + n * 9) * 0.5 + 0.5) ** 6
    zona = zona * (0.85 + 0.25 * n[..., None]) + lineas[..., None] * 18
    if brillo:
        bx, col = brillo
        xx = np.arange(w)[None, :]
        franja = np.exp(-((xx - bx * w) / (w * (0.03 + 0.12 * np.linspace(0, 1, h - hy)[:, None]))) ** 2)
        zona += np.array(col, np.float32) * (franja * lineas * 1.4 + franja * 0.25)[..., None]
    arr[hy:, :, :3] = zona
    arr[hy:, :, 3] = 255
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


# ------------------------------------------------------------------ escenas
NEGRO = (8, 6, 6, 255)


def _base(spec):
    """Cielo según el momento del día pedido en la escena."""
    hora = spec.get("hora", "atardecer")
    sem = spec.get("semilla", 1)
    if hora == "atardecer":
        return cielo(LW, LH, [(0, (40, 30, 55)), (0.45, (190, 90, 50)), (0.7, (250, 175, 90)), (1, (90, 40, 30))],
                     sem, 0.4, (255, 170, 110), sol=(0.62, 0.66, 0.25, (255, 200, 120)))
    if hora == "noche":
        return cielo(LW, LH, [(0, (5, 8, 20)), (0.6, (25, 35, 60)), (1, (10, 12, 20))], sem, 0.25, (80, 90, 120),
                     sol=(0.75, 0.2, 0.06, (200, 210, 240)))
    if hora == "fuego":
        return cielo(LW, LH, [(0, (25, 5, 5)), (0.5, (140, 35, 10)), (0.75, (240, 110, 30)), (1, (60, 10, 5))],
                     sem, 0.5, (90, 30, 20))
    if hora == "nieve":
        return cielo(LW, LH, [(0, (70, 80, 95)), (0.6, (150, 160, 175)), (1, (200, 205, 215))], sem, 0.5,
                     (230, 235, 240))
    if hora == "desierto":
        return cielo(LW, LH, [(0, (60, 70, 120)), (0.5, (230, 150, 80)), (0.72, (255, 210, 130)), (1, (180, 120, 60))],
                     sem, 0.2, (255, 200, 150), sol=(0.3, 0.6, 0.2, (255, 220, 150)))
    if hora == "tormenta":
        return cielo(LW, LH, [(0, (25, 28, 35)), (0.6, (70, 75, 85)), (1, (40, 42, 48))], sem, 0.7, (120, 125, 135))
    if hora == "amanecer":
        return cielo(LW, LH, [(0, (50, 70, 120)), (0.5, (220, 160, 150)), (0.72, (255, 210, 160)), (1, (120, 90, 80))],
                     sem, 0.35, (255, 220, 200), sol=(0.5, 0.7, 0.2, (255, 220, 170)))
    return cielo(LW, LH, [(0, (60, 90, 140)), (0.7, (180, 190, 200)), (1, (120, 110, 90))], sem, 0.4)


def escena_batalla(spec):
    hora = spec.get("hora", "atardecer")
    fondo = _base(spec)
    lejos = Lienzo()
    tono_lejos = {"nieve": (120, 125, 140, 255), "desierto": (150, 95, 60, 255)}.get(hora, (60, 35, 35, 255))
    colinas(lejos, LH * 0.66, 120, tono_lejos, spec.get("semilla", 1) + 7)
    if hora == "desierto":
        for px, ancho in ((0.25, 380), (0.43, 260), (0.12, 160)):
            lejos.poly([(LW * px - ancho, LH * 0.66), (LW * px, LH * 0.66 - ancho * 0.75),
                        (LW * px + ancho, LH * 0.66)], (175, 115, 70, 255))
            lejos.poly([(LW * px, LH * 0.66 - ancho * 0.75), (LW * px + ancho, LH * 0.66),
                        (LW * px + ancho * 0.3, LH * 0.66)], (120, 75, 50, 255))
    rng = np.random.default_rng(spec.get("semilla", 1))
    tono_tropa = {"nieve": (70, 72, 85, 255)}.get(hora, (35, 20, 20, 255))
    for i in range(60):
        soldado(lejos, LW * (0.05 + i * 0.015), LH * 0.69, 34, rng.random() * 6, tono_tropa, flip=True)
    cerca = Lienzo()
    suelo = {"nieve": (225, 228, 235, 255), "desierto": (95, 60, 35, 255)}.get(hora, (14, 10, 10, 255))
    colinas(cerca, LH * 0.86, 70, suelo, spec.get("semilla", 1) + 11, 0.8)
    bocas = []
    for k, cx in enumerate((0.16, 0.42, 0.7)):
        bocas.append(canon_pieza(cerca, LW * cx, LH * 0.84 + k * 6, 150, NEGRO if hora != "nieve" else (30, 30, 40, 255)))
    for i in range(14):
        soldado(cerca, LW * (0.02 + i * 0.075) + rng.random() * 20, LH * 0.95, 260, rng.random() * 6,
                NEGRO if hora != "nieve" else (25, 25, 35, 255), bandera="tricolor" if i == 8 else None)
    capas = [(lejos.imagen(), 0.35), (humo(LW, LH, spec.get("semilla", 1) + 99, (190, 170, 150), 0.55), 0.6),
             (cerca.imagen(), 1.0)]
    return {"fondo": fondo, "capas": capas, "bocas": [(b[0], b[1], 1.0) for b in bocas],
            "particulas": "nieve" if hora == "nieve" else "brasas", "tono": hora, "humo_mov": True}


def escena_marcha(spec):
    hora = spec.get("hora", "atardecer")
    fondo = _base(spec)
    lejos = Lienzo()
    colinas(lejos, LH * 0.7, 150, (50, 30, 35, 255) if hora != "nieve" else (130, 135, 150, 255),
            spec.get("semilla", 2))
    col = NEGRO if hora != "nieve" else (40, 40, 52, 255)
    suelo = Lienzo()
    colinas(suelo, LH * 0.86, 30, col if hora != "nieve" else (230, 232, 240, 255), spec.get("semilla", 2) + 5, 0.9)
    tropa = Lienzo()
    for i in range(30):
        soldado(tropa, i * 75 - 40, LH * 0.84 - (i % 2) * 18, 270 - (i % 2) * 20, i * 0.9, col,
                bandera="tricolor" if i in (6, 20) and hora != "nieve" else None)
    tropa = tropa.imagen()
    tropa.info["desfile"] = 150
    return {"fondo": fondo, "capas": [(lejos.imagen(), 0.3), (tropa, 1.0), (suelo.imagen(), 1.0)],
            "particulas": "nieve" if hora == "nieve" else "polvo", "tono": hora}


def escena_naval(spec):
    fondo = _base({**spec, "hora": spec.get("hora", "noche")})
    agua = mar(LW, LH, 0.6, (40, 45, 60), (5, 8, 15), 4, (0.6, (255, 160, 80)))
    barcos = Lienzo()
    bocas = []
    for k, (bx, by, bs, fl) in enumerate([(0.28, 0.66, 520, False), (0.72, 0.68, 600, True), (0.5, 0.62, 260, False)]):
        cos = barco(barcos, LW * bx, LH * by, bs, NEGRO, (60, 50, 45, 255), fl)
        bocas += [(x, y, 0.6) for x, y in cos]
    return {"fondo": fondo, "capas": [(agua, 0.6), (humo(LW, LH, 31, (150, 120, 100), 0.5), 0.7),
                                      (barcos.imagen(), 1.0)],
            "bocas": bocas, "particulas": "brasas", "tono": "noche", "humo_mov": True}


def escena_retrato(spec):
    """Retrato en marco ovalado dorado con una silueta y una placa con el nombre."""
    quien = spec.get("quien", "napoleon")
    fondos = {"napoleon": [(0, (90, 20, 25)), (1, (25, 5, 8))], "josefina": [(0, (60, 40, 70)), (1, (15, 8, 20))],
              "mujer": [(0, (40, 55, 75)), (1, (10, 12, 20))], "hombre": [(0, (55, 45, 30)), (1, (15, 12, 8))],
              "anciano": [(0, (40, 45, 55)), (1, (8, 9, 12))], "maria_luisa": [(0, (60, 70, 90)), (1, (12, 14, 22))]}
    pared = Image.fromarray(np.clip(degradado(LW, LH, fondos.get(quien, fondos["hombre"])) *
                                    (0.8 + 0.3 * ruido_fractal(LW, LH, 8, 5, 6)[..., None]), 0, 255).astype(np.uint8)).convert("RGBA")
    m = Lienzo()
    cx, cy, rx, ry = LW / 2, LH * 0.55, 300, 380
    m.elipse(cx, cy, rx + 46, ry + 46, (120, 85, 30, 255))
    m.elipse(cx, cy, rx + 34, ry + 34, (215, 170, 80, 255))
    m.elipse(cx, cy, rx + 18, ry + 18, (140, 100, 40, 255))
    lienzo_col = {"napoleon": (205, 150, 80, 255), "anciano": (120, 125, 135, 255)}.get(quien, (190, 160, 120, 255))
    m.elipse(cx, cy, rx, ry, lienzo_col)
    marco = m.imagen()
    fig = Lienzo()
    oro = (230, 180, 80, 255)
    if quien in ("napoleon", "anciano"):
        napoleon_busto(fig, cx, cy - 40, 160, NEGRO, oro if quien == "napoleon" else None)
    elif quien in ("josefina", "mujer", "maria_luisa"):
        perfil_mujer(fig, cx - 20, cy - 40, 300, NEGRO, oro if quien != "mujer" else (200, 200, 210, 255))
    else:
        perfil_hombre(fig, cx - 20, cy - 40, 290, NEGRO, spec.get("peluca", True))
    figura = fig.imagen()
    mascara = Image.new("L", (LW, LH), 0)
    ImageDraw.Draw(mascara).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    figura.putalpha(ImageChops.multiply(figura.split()[3], mascara))
    capa = Image.alpha_composite(marco, figura)
    if spec.get("nombre"):
        p = Lienzo()
        p.rect(cx - 360, cy - ry - 150, cx + 360, cy - ry - 70, (25, 18, 10, 230))
        p.texto((cx, cy - ry - 110), spec["nombre"].upper(), ("titulo", 44), (235, 195, 110, 255))
        capa = Image.alpha_composite(capa, p.imagen())
    capa = con_brillo(capa, (255, 200, 120), 30, 0.8)
    return {"fondo": pared, "capas": [(capa, 1.0)], "particulas": "polvo",
            "tono": "frio" if quien == "anciano" else "calido", "zoom": (1.0, 1.12)}


def escena_doble(spec):
    """Dos retratos lado a lado (padres, o Napoleón y su esposa)."""
    izq, der = spec["quienes"]
    pared = Image.fromarray(np.clip(degradado(LW, LH, [(0, (70, 50, 35)), (1, (15, 10, 8))]) *
                                    (0.8 + 0.3 * ruido_fractal(LW, LH, 18, 5, 6)[..., None]), 0, 255).astype(np.uint8)).convert("RGBA")
    capa = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    for k, (quien, nombre) in enumerate((izq, der)):
        cx = LW * (0.31 + 0.38 * k)
        cy, rx, ry = LH * 0.53, 230, 300
        m = Lienzo()
        m.elipse(cx, cy, rx + 36, ry + 36, (120, 85, 30, 255))
        m.elipse(cx, cy, rx + 26, ry + 26, (215, 170, 80, 255))
        m.elipse(cx, cy, rx, ry, (190, 160, 120, 255))
        if quien == "hombre":
            perfil_hombre(m, cx - 10, cy - 30, 220, NEGRO)
        elif quien == "napoleon":
            napoleon_busto(m, cx, cy - 30, 120, NEGRO, (230, 180, 80, 255))
        else:
            perfil_mujer(m, cx - 10, cy - 30, 230, NEGRO, (230, 180, 80, 255))
        m.rect(cx - 280, cy - ry - 130, cx + 280, cy - ry - 60, (25, 18, 10, 230))
        m.texto((cx, cy - ry - 95), nombre.upper(), ("titulo", 34), (235, 195, 110, 255))
        im = m.imagen()
        mascara = Image.new("L", (LW, LH), 255)
        capa = Image.alpha_composite(capa, im)
    return {"fondo": pared, "capas": [(con_brillo(capa, (255, 200, 120), 25, 0.7), 1.0)],
            "particulas": "polvo", "tono": "calido", "zoom": (1.0, 1.08)}


def escena_colina(spec):
    """Napoleón de espaldas en una colina mirando el campo de batalla."""
    hora = spec.get("hora", "atardecer")
    fondo = _base(spec)
    lejos = Lienzo()
    colinas(lejos, LH * 0.7, 90, (70, 40, 40, 255) if hora != "nieve" else (140, 145, 160, 255), 21)
    rng = np.random.default_rng(4)
    for i in range(110):
        soldado(lejos, LW * (0.05 + (i % 55) * 0.017), LH * (0.72 + (i // 55) * 0.03), 26, rng.random() * 6,
                (45, 25, 25, 255) if hora != "nieve" else (90, 92, 105, 255))
    cerca = Lienzo()
    col = NEGRO if hora != "nieve" else (25, 25, 32, 255)
    cerca.poly([(0, LH * 0.82), (LW * 0.25, LH * 0.78), (LW * 0.45, LH * 0.8), (LW * 0.6, LH * 0.9), (LW, LH * 0.95),
                (LW, LH), (0, LH)], col)
    napoleon_espalda(cerca, LW * 0.33, LH * 0.8, 430, col)
    for k, dx in enumerate((-260, 230)):
        soldado(cerca, LW * 0.33 + dx, LH * 0.82 + 8, 330, 0.0, col, bandera="tricolor" if k else None)
    capa = con_brillo(cerca.imagen(), (255, 180, 100) if hora != "nieve" else (220, 230, 255), 22, 1.2)
    return {"fondo": fondo, "capas": [(lejos.imagen(), 0.4), (humo(LW, LH, 61, (200, 170, 150), 0.4), 0.6), (capa, 1.0)],
            "particulas": "nieve" if hora == "nieve" else "brasas", "tono": hora, "humo_mov": True,
            "bocas": [(LW * x, LH * 0.7, 0.5) for x in (0.6, 0.75, 0.88)]}


def escena_heroe(spec):
    """Busto de Napoleón a contraluz con rayos y estandartes: para momentos épicos."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (60, 15, 15)), (0.6, (130, 50, 20)), (1, (20, 5, 5))]),
                                    0, 255).astype(np.uint8)).convert("RGBA")
    rayos = Lienzo()
    for k in range(36):
        a = k * math.pi * 2 / 36
        rayos.poly([(LW / 2, LH * 0.45), (LW / 2 + math.cos(a) * 2400, LH * 0.45 + math.sin(a) * 2400),
                    (LW / 2 + math.cos(a + 0.05) * 2400, LH * 0.45 + math.sin(a + 0.05) * 2400)],
                   (255, 200, 120, 40 if k % 2 else 22))
    fig = Lienzo()
    napoleon_busto(fig, LW / 2, LH * 0.4, 185, NEGRO, (230, 180, 80, 255))
    for sx in (0.14, 0.86):
        x = LW * sx
        fig.linea([(x, LH), (x, LH * 0.15)], (30, 20, 15, 255), 8)
        fig.poly([(x, LH * 0.15), (x - 70, LH * 0.13), (x - 70, LH * 0.05), (x + 70, LH * 0.05), (x + 70, LH * 0.13)],
                 (215, 170, 70, 255))
        for k, c in enumerate(((30, 50, 140, 255), (225, 220, 210, 255), (170, 30, 35, 255))):
            fig.rect(x - 110 + k * 73, LH * 0.17, x - 37 + k * 73, LH * 0.5, c)
    capa = con_brillo(fig.imagen(), (255, 190, 100), 35, 1.4)
    if spec.get("texto"):
        t = Lienzo()
        t.texto((LW / 2, LH * 0.9), spec["texto"], ("titulo", 60), (240, 200, 120, 255))
        capa = Image.alpha_composite(capa, t.imagen())
    return {"fondo": Image.alpha_composite(fondo, rayos.imagen()), "capas": [(capa, 1.0)],
            "particulas": "brasas", "tono": "calido", "zoom": (1.0, 1.1), "rayos": True}


def escena_corcega(spec):
    fondo = _base({**spec, "hora": spec.get("hora", "amanecer")})
    montes = Lienzo()
    colinas(montes, LH * 0.55, 260, (90, 70, 90, 255), 41, 0.4)
    colinas(montes, LH * 0.6, 160, (60, 45, 60, 255), 42, 0.5)
    pueblo = Lienzo()
    rng = np.random.default_rng(9)
    colinas(pueblo, LH * 0.66, 50, (35, 25, 30, 255), 43, 0.8)
    x = LW * 0.3
    while x < LW * 0.85:
        w_, h_ = rng.integers(50, 110), rng.integers(70, 170)
        y = LH * 0.66 - 10
        pueblo.rect(x, y - h_, x + w_, y + 40, (35, 25, 30, 255))
        pueblo.poly([(x - 8, y - h_), (x + w_ / 2, y - h_ - 35), (x + w_ + 8, y - h_)], (35, 25, 30, 255))
        for _ in range(2):
            vx = x + rng.integers(10, max(11, w_ - 20))
            vy = y - rng.integers(20, h_)
            pueblo.rect(vx, vy, vx + 10, vy + 16, (255, 190, 100, 255) if rng.random() < 0.5 else (35, 25, 30, 255))
        x += w_ + rng.integers(0, 20)
    pueblo.rect(LW * 0.22, LH * 0.66 - 230, LW * 0.22 + 60, LH * 0.66 + 20, (35, 25, 30, 255))
    pueblo.poly([(LW * 0.22 - 10, LH * 0.66 - 230), (LW * 0.22 + 30, LH * 0.66 - 300), (LW * 0.22 + 70, LH * 0.66 - 230)],
                (35, 25, 30, 255))
    agua = mar(LW, LH, 0.68, (150, 120, 130), (20, 30, 50), 12, (0.5, (255, 220, 170)))
    barcos = Lienzo()
    barco(barcos, LW * 0.75, LH * 0.78, 300, (25, 20, 25, 255), (200, 180, 160, 255))
    return {"fondo": fondo, "capas": [(montes.imagen(), 0.25), (pueblo.imagen(), 0.5), (agua, 0.7),
                                      (barcos.imagen(), 1.0)],
            "particulas": "gaviotas", "tono": "calido", "barco_mov": True}


def escena_estudio(spec):
    """Escritorio con vela, libros, mapa y pluma."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (25, 15, 10)), (1, (8, 5, 3))]) *
                                    (0.7 + 0.5 * ruido_fractal(LW, LH, 70, 5, 5)[..., None]), 0, 255).astype(np.uint8)).convert("RGBA")
    m = Lienzo()
    m.rect(0, LH * 0.62, LW, LH, (55, 32, 18, 255))
    for k in range(18):
        m.linea([(0, LH * 0.62 + k * 25), (LW, LH * 0.62 + k * 25 + 5)], (45, 26, 14, 255), 2)
    papel = textura_papel(900, 560, 4)
    pd = ImageDraw.Draw(papel)
    pts = [(80 + i * 45, 250 + 70 * math.sin(i * 0.7) + 40 * math.cos(i * 1.7)) for i in range(17)]
    pd.line(pts, fill=(110, 70, 40), width=5)
    for i in range(0, 16, 3):
        pd.line([(pts[i][0], pts[i][1] - 10), (pts[i][0] + 35, pts[i][1] + 10)], fill=(150, 30, 30), width=6)
        pd.line([(pts[i][0] + 35, pts[i][1] - 10), (pts[i][0], pts[i][1] + 10)], fill=(150, 30, 30), width=6)
    pd.text((450, 80), spec.get("mapa", "Theatrum Belli"), font=fuente("antigua", 54), fill=(80, 50, 30), anchor="mm")
    papel = papel.rotate(4, expand=True, resample=Image.BICUBIC)
    capa = m.imagen()
    capa.alpha_composite(papel, (int(LW * 0.38), int(LH * 0.5)))
    o = Lienzo()
    for k, (w_, h_, c) in enumerate(((420, 70, (90, 25, 20, 255)), (380, 60, (30, 45, 70, 255)),
                                     (440, 75, (60, 45, 20, 255)), (360, 55, (85, 60, 30, 255)))):
        y = LH * 0.68 - sum((70, 60, 75, 55)[:k + 1])
        o.rect(LW * 0.08, y, LW * 0.08 + w_, y + h_ - 4, c)
        o.rect(LW * 0.08 + 30, y + 12, LW * 0.08 + 34, y + h_ - 16, (210, 170, 80, 255))
    vx, vy = LW * 0.8, LH * 0.68
    o.rect(vx - 70, vy - 15, vx + 70, vy, (140, 110, 50, 255))
    o.rect(vx - 26, vy - 260, vx + 26, vy - 15, (235, 225, 200, 255))
    o.linea([(vx, vy - 260), (vx, vy - 280)], (20, 15, 10, 255), 4)
    o.linea([(LW * 0.66, LH * 0.78), (LW * 0.58, LH * 0.5)], (230, 225, 215, 255), 6)
    o.poly([(LW * 0.58, LH * 0.5), (LW * 0.56, LH * 0.44), (LW * 0.62, LH * 0.6), (LW * 0.61, LH * 0.52)],
           (235, 230, 220, 255))
    capa = Image.alpha_composite(capa, o.imagen())
    return {"fondo": fondo, "capas": [(capa, 1.0)], "vela": (vx, vy - 300), "particulas": "polvo",
            "tono": "vela", "zoom": (1.0, 1.08)}


def escena_documento(spec):
    """Pergamino con título y texto (código, tratado, carta, abdicación)."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (35, 22, 14)), (1, (10, 6, 4))]) *
                                    (0.7 + 0.5 * ruido_fractal(LW, LH, 71, 5, 5)[..., None]), 0, 255).astype(np.uint8)).convert("RGBA")
    pw, ph = 1250, 1500
    papel = textura_papel(pw, ph, spec.get("semilla", 6))
    d = ImageDraw.Draw(papel)
    titulo = spec.get("titulo", "Code Civil des Français")
    d.text((pw / 2, 170), titulo, font=fuente("antigua", 84 if len(titulo) < 26 else 64), fill=(60, 35, 20), anchor="mm")
    d.line([(pw * 0.25, 250), (pw * 0.75, 250)], fill=(90, 55, 30), width=3)
    rng = np.random.default_rng(len(titulo))
    lineas = spec.get("lineas") or []
    y = 330
    for ln in lineas:
        d.text((130, y), ln, font=fuente("antigua", 46), fill=(55, 35, 25))
        y += 70
    while y < ph - 260:
        x = 130
        while x < pw - 200:
            largo = rng.integers(40, 170)
            d.line([(x, y + 20), (x + largo, y + 20)], fill=(90, 65, 45), width=6)
            x += largo + 22
        y += 62
    if spec.get("firma"):
        d.text((pw * 0.62, ph - 190), spec["firma"], font=fuente("antigua", 92), fill=(40, 25, 15), anchor="mm")
    if spec.get("sello", True):
        sx, sy = pw * 0.22, ph - 200
        d.ellipse([sx - 95, sy - 95, sx + 95, sy + 95], fill=(130, 20, 20))
        d.ellipse([sx - 70, sy - 70, sx + 70, sy + 70], outline=(170, 50, 40), width=6)
        d.text((sx, sy), "N", font=fuente("deco", 90), fill=(170, 50, 40), anchor="mm")
    papel = papel.rotate(spec.get("giro", -3), expand=True, resample=Image.BICUBIC)
    capa = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    sombra = Image.new("RGBA", papel.size, (0, 0, 0, 160))
    sombra.putalpha(papel.split()[3].point(lambda v: v * 0.6))
    sombra = sombra.filter(ImageFilter.GaussianBlur(25))
    ox, oy = (LW - papel.width) // 2, 60
    capa.alpha_composite(sombra, (ox + 30, oy + 40))
    capa.alpha_composite(papel, (ox, oy))
    return {"fondo": fondo, "capas": [(capa, 1.0)], "particulas": "polvo", "tono": "vela",
            "zoom": (1.0, 1.3), "pan": (0.0, -0.08), "vela": (LW * 0.86, LH * 0.25)}


def escena_coronacion(spec):
    """Interior de catedral gótica con haces de luz y una corona."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (20, 15, 25)), (1, (50, 35, 25))]), 0, 255)
                            .astype(np.uint8)).convert("RGBA")
    m = Lienzo()
    for k in range(7):
        x = LW * (0.05 + k * 0.15)
        m.rect(x - 35, LH * 0.15, x + 35, LH, (12, 10, 14, 255))
        pts = [(x + 35 + (LW * 0.15 - 70) * i / 20,
                LH * 0.15 - math.sin(i / 20 * math.pi) * 170 - 0 * i) for i in range(21)]
        m.linea(pts, (12, 10, 14, 255), 30)
    m.rect(0, 0, LW, LH * 0.05, (12, 10, 14, 255))
    vit = Lienzo()
    for k in range(6):
        x = LW * (0.125 + k * 0.15)
        cols = [(200, 40, 40, 255), (40, 70, 190, 255), (230, 180, 60, 255), (60, 140, 80, 255)]
        for j in range(4):
            vit.rect(x - 40, LH * 0.25 + j * 60, x + 40, LH * 0.25 + j * 60 + 56, cols[(j + k) % 4])
        vit.elipse(x, LH * 0.25, 40, 40, cols[k % 4])
    rosa = Lienzo()
    rosa.elipse(LW / 2, LH * 0.3, 170, 170, (180, 140, 60, 200))
    for k in range(16):
        a = k * math.pi / 8
        rosa.linea([(LW / 2, LH * 0.3), (LW / 2 + math.cos(a) * 170, LH * 0.3 + math.sin(a) * 170)], (20, 15, 20, 255), 8)
    rosa.elipse(LW / 2, LH * 0.3, 40, 40, (20, 15, 20, 255))
    luz = Lienzo()
    for k in range(5):
        x = LW * (0.3 + k * 0.1)
        luz.poly([(x - 40, 0), (x + 40, 0), (x + 260, LH), (x + 60, LH)], (255, 220, 150, 26))
    c = Lienzo()
    cx, cy = LW / 2, LH * 0.62
    oro = (235, 185, 70, 255)
    c.poly([(cx - 210, cy + 80), (cx + 210, cy + 80), (cx + 230, cy - 60), (cx + 120, cy + 10), (cx, cy - 120),
            (cx - 120, cy + 10), (cx - 230, cy - 60)], oro)
    c.rect(cx - 215, cy + 60, cx + 215, cy + 110, (200, 150, 50, 255))
    for k, jx in enumerate((-140, -70, 0, 70, 140)):
        c.elipse(cx + jx, cy + 85, 16, 16, ((170, 20, 30, 255), (30, 60, 170, 255))[k % 2])
    for px in (-230, 0, 230):
        c.elipse(cx + px, cy - 60 - (60 if px == 0 else 0), 18, 18, (250, 240, 220, 255))
    c.elipse(cx, cy - 210, 30, 30, oro)
    c.linea([(cx, cy - 245), (cx, cy - 175)], oro, 12)
    c.linea([(cx - 25, cy - 220), (cx + 25, cy - 220)], oro, 12)
    corona = con_brillo(c.imagen(), (255, 210, 120), 40, 1.6)
    altar = Lienzo()
    altar.rect(LW * 0.3, LH * 0.88, LW * 0.7, LH, (25, 18, 18, 255))
    altar.rect(LW * 0.28, LH * 0.86, LW * 0.72, LH * 0.89, (190, 150, 70, 255))
    fon = Image.alpha_composite(fondo, vit.imagen().filter(ImageFilter.GaussianBlur(3)))
    fon = Image.alpha_composite(fon, rosa.imagen())
    fon = Image.alpha_composite(fon, m.imagen())
    return {"fondo": fon, "capas": [(luz.imagen().filter(ImageFilter.GaussianBlur(20)), 0.8), (corona, 1.0),
                                    (altar.imagen(), 1.0)],
            "particulas": "chispas", "tono": "oro", "zoom": (1.0, 1.15), "flotar": 1}


def escena_salon(spec):
    """Salón de baile con lámparas y parejas (vida social de París)."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (60, 35, 20)), (0.7, (120, 70, 35)), (1, (40, 25, 15))]), 0, 255)
                            .astype(np.uint8)).convert("RGBA")
    m = Lienzo()
    for k in range(6):
        x = LW * (0.08 + k * 0.17)
        m.rect(x - 45, LH * 0.1, x + 45, LH * 0.8, (80, 50, 25, 255))
        m.rect(x - 60, LH * 0.1, x + 60, LH * 0.14, (150, 110, 50, 255))
        m.rect(x + 70, LH * 0.2, x + LW * 0.17 - 70, LH * 0.65, (30, 25, 35, 255))
    m.rect(0, LH * 0.8, LW, LH, (50, 30, 18, 255))
    lamp = Lienzo()
    for lx in (0.3, 0.7):
        x = LW * lx
        lamp.linea([(x, 0), (x, LH * 0.12)], (180, 140, 60, 255), 4)
        for k in range(3):
            lamp.elipse(x, LH * (0.16 + k * 0.05), 120 - k * 30, 18, (200, 160, 80, 255))
        for k in range(9):
            lamp.elipse(x - 110 + k * 27.5, LH * 0.14, 8, 14, (255, 230, 160, 255))
    gente = Lienzo()
    for k in range(7):
        x = LW * (0.07 + k * 0.145)
        perfil_hombre(gente, x - 50, LH * 0.6, 95, NEGRO, False)
        gente.rect(x - 110, LH * 0.66, x + 10, LH * 0.98, NEGRO)
        perfil_mujer(gente, x + 70, LH * 0.62, 95, NEGRO)
        gente.poly([(x + 20, LH * 0.7), (x + 120, LH * 0.7), (x + 170, LH * 0.98), (x - 30, LH * 0.98)], NEGRO)
    return {"fondo": Image.alpha_composite(fondo, m.imagen()),
            "capas": [(con_brillo(lamp.imagen(), (255, 220, 150), 30, 2.0), 0.7), (gente.imagen(), 1.0)],
            "particulas": "chispas", "tono": "calido", "desfile_lento": True}


def escena_castillo(spec):
    """Castillo/palacio (Malmaison, Tullerías, Saint-Cloud) con jardín."""
    hora = spec.get("hora", "atardecer")
    fondo = _base({**spec, "hora": hora})
    m = Lienzo()
    col = (20, 15, 20, 255)
    cx, base = LW / 2, LH * 0.72
    ancho = spec.get("ancho", 0.32)
    m.rect(cx - LW * ancho, base - 230, cx + LW * ancho, base, col)
    m.poly([(cx - LW * ancho - 20, base - 230), (cx - LW * ancho + 40, base - 300), (cx + LW * ancho - 40, base - 300),
            (cx + LW * ancho + 20, base - 230)], col)
    m.rect(cx - 140, base - 340, cx + 140, base, col)
    m.poly([(cx - 160, base - 340), (cx, base - 430), (cx + 160, base - 340)], col)
    luz = (255, 200, 110, 255) if hora in ("noche", "atardecer") else (60, 60, 70, 255)
    for fila in range(2):
        for k in range(int(ancho * 60)):
            x = cx - LW * ancho + 40 + k * 32
            if abs(x - cx) < 150:
                continue
            m.rect(x, base - 200 + fila * 100, x + 16, base - 160 + fila * 100, luz)
    for k in range(5):
        m.rect(cx - 110 + k * 50, base - 300, cx - 90 + k * 50, base - 240, luz)
    jardin = Lienzo()
    colinas(jardin, LH * 0.84, 30, (12, 14, 10, 255), 77, 0.9)
    for k in range(16):
        x = LW * (0.03 + k * 0.065)
        jardin.elipse(x, LH * 0.8, 50, 80, (15, 18, 12, 255))
        jardin.rect(x - 6, LH * 0.8, x + 6, LH * 0.88, (15, 18, 12, 255))
    if spec.get("rosas"):
        rng = np.random.default_rng(3)
        for _ in range(60):
            x, y = rng.random() * LW, LH * (0.88 + rng.random() * 0.1)
            jardin.elipse(x, y, 14, 12, (150 + int(rng.random() * 60), 20, 35, 255))
    return {"fondo": fondo, "capas": [(m.imagen(), 0.5), (jardin.imagen(), 1.0)],
            "particulas": "luciernagas" if hora == "noche" else "polvo", "tono": hora}


def escena_revolucion(spec):
    fondo = _base({**spec, "hora": "fuego"})
    m = Lienzo()
    colinas(m, LH * 0.6, 40, (30, 10, 10, 255), 80, 1.0)
    for k in range(14):
        x = LW * k / 13
        m.rect(x - 60, LH * 0.6 - 120 - (k % 3) * 60, x + 60, LH * 0.62, (30, 10, 10, 255))
    gente = Lienzo()
    rng = np.random.default_rng(14)
    for i in range(30):
        x = LW * (i / 29)
        soldado(gente, x, LH * (0.97 - (i % 3) * 0.04), 300 + rng.random() * 60, rng.random() * 6, NEGRO,
                bandera="tricolor" if i % 7 == 3 else None)
    gente.poly([(LW * 0.3, LH), (LW * 0.4, LH * 0.8), (LW * 0.55, LH * 0.82), (LW * 0.7, LH * 0.78),
                (LW * 0.8, LH)], NEGRO)
    return {"fondo": fondo, "capas": [(m.imagen(), 0.4), (humo(LW, LH, 44, (90, 40, 30), 0.6), 0.6),
                                      (gente.imagen(), 1.0)],
            "particulas": "brasas", "tono": "fuego", "humo_mov": True}


def escena_moscu(spec):
    fondo = _base({**spec, "hora": "fuego"})
    ciudad = Lienzo()
    col = (20, 6, 6, 255)
    rng = np.random.default_rng(12)
    ciudad.rect(0, LH * 0.7, LW, LH, col)
    for k in range(11):
        x = LW * (0.05 + k * 0.09) + rng.integers(-30, 30)
        alto = rng.integers(150, 380)
        ciudad.rect(x - 35, LH * 0.7 - alto, x + 35, LH * 0.71, col)
        cupula_cebolla(ciudad, x, LH * 0.7 - alto + 5, 90 + rng.integers(0, 40), col)
    for x in np.linspace(0, LW, 30):
        ciudad.rect(x, LH * 0.7 - rng.integers(40, 120), x + 70, LH * 0.71, col)
    return {"fondo": fondo, "capas": [(humo(LW, LH, 55, (60, 25, 20), 0.85), 0.4), (ciudad.imagen(), 1.0)],
            "particulas": "brasas_fuerte", "tono": "fuego", "humo_mov": True, "fuego": True}


def escena_isla(spec):
    """Isla en el océano (Elba o Santa Elena)."""
    cual = spec.get("cual", "santa_elena")
    hora = spec.get("hora", "tormenta" if cual == "santa_elena" else "atardecer")
    fondo = _base({**spec, "hora": hora})
    agua = mar(LW, LH, 0.62, (70, 75, 90) if hora == "tormenta" else (160, 110, 90),
               (10, 15, 25), 23, (0.6, (200, 200, 210) if hora == "tormenta" else (255, 190, 120)))
    isla = Lienzo()
    col = (18, 18, 22, 255)
    if cual == "santa_elena":
        isla.poly([(LW * 0.15, LH * 0.63), (LW * 0.2, LH * 0.38), (LW * 0.3, LH * 0.33), (LW * 0.4, LH * 0.28),
                   (LW * 0.5, LH * 0.3), (LW * 0.62, LH * 0.25), (LW * 0.72, LH * 0.35), (LW * 0.8, LH * 0.45),
                   (LW * 0.86, LH * 0.63)], col)
        isla.rect(LW * 0.52, LH * 0.25 - 30, LW * 0.58, LH * 0.255, col)
        isla.poly([(LW * 0.515, LH * 0.25 - 30), (LW * 0.545, LH * 0.25 - 55), (LW * 0.585, LH * 0.25 - 30)], col)
        isla.rect(LW * 0.535, LH * 0.25 - 22, LW * 0.545, LH * 0.25 - 10, (255, 200, 110, 255))
    else:
        isla.poly([(LW * 0.25, LH * 0.63), (LW * 0.35, LH * 0.5), (LW * 0.45, LH * 0.45), (LW * 0.55, LH * 0.5),
                   (LW * 0.7, LH * 0.56), (LW * 0.78, LH * 0.63)], col)
    bar = Lienzo()
    if spec.get("barco", True):
        barco(bar, LW * 0.8, LH * 0.74, 260, (12, 12, 14, 255), (170, 165, 155, 255), flip=cual != "santa_elena")
    return {"fondo": fondo, "capas": [(isla.imagen(), 0.35), (agua, 0.7), (bar.imagen(), 1.0)],
            "particulas": "lluvia" if hora == "tormenta" else "gaviotas", "tono": "frio" if hora == "tormenta" else hora,
            "barco_mov": True, "relampagos": hora == "tormenta"}


def escena_longwood(spec):
    fondo = _base({**spec, "hora": "tormenta"})
    m = Lienzo()
    col = (15, 15, 18, 255)
    colinas(m, LH * 0.75, 60, (35, 38, 40, 255), 90, 0.6)
    m.rect(LW * 0.35, LH * 0.6, LW * 0.68, LH * 0.76, col)
    m.poly([(LW * 0.33, LH * 0.6), (LW * 0.4, LH * 0.52), (LW * 0.63, LH * 0.52), (LW * 0.7, LH * 0.6)], col)
    for k in range(6):
        m.rect(LW * (0.38 + k * 0.05), LH * 0.64, LW * (0.38 + k * 0.05) + 26, LH * 0.69,
               (255, 190, 100, 255) if k in (1, 4) else (30, 30, 35, 255))
    for x in (0.12, 0.2, 0.82, 0.9):
        m.linea([(LW * x, LH * 0.78), (LW * x + 30, LH * 0.45)], col, 14)
        m.elipse(LW * x + 30, LH * 0.43, 90, 60, col)
    cerca = Lienzo()
    cerca.poly([(0, LH * 0.88), (LW, LH * 0.84), (LW, LH), (0, LH)], (8, 8, 10, 255))
    napoleon_espalda(cerca, LW * 0.22, LH * 0.88, 330, (8, 8, 10, 255))
    return {"fondo": fondo, "capas": [(humo(LW, LH, 91, (150, 155, 165), 0.45), 0.3), (m.imagen(), 0.6),
                                      (con_brillo(cerca.imagen(), (180, 190, 210), 15, 0.8), 1.0)],
            "particulas": "lluvia", "tono": "frio", "humo_mov": True}


def escena_ciudad(spec):
    """París: Notre Dame y tejados, o la cúpula de Los Inválidos."""
    cual = spec.get("cual", "paris")
    fondo = _base({**spec, "hora": spec.get("hora", "atardecer")})
    m = Lienzo()
    col = (18, 12, 14, 255)
    rng = np.random.default_rng(31)
    x = 0
    while x < LW:
        w_ = rng.integers(60, 140)
        alto = rng.integers(80, 200)
        m.rect(x, LH * 0.78 - alto, x + w_, LH, col)
        m.poly([(x, LH * 0.78 - alto), (x + w_ / 2, LH * 0.78 - alto - 40), (x + w_, LH * 0.78 - alto)], col)
        for _ in range(3):
            vx, vy = x + rng.integers(8, max(9, w_ - 16)), LH * 0.78 - alto + rng.integers(20, alto)
            if rng.random() < 0.4:
                m.rect(vx, vy, vx + 9, vy + 14, (255, 200, 110, 255))
        x += w_
    if cual == "paris":
        cx = LW * 0.55
        for dx in (-170, 120):
            m.rect(cx + dx, LH * 0.25, cx + dx + 110, LH * 0.8, col)
            m.rect(cx + dx - 8, LH * 0.25, cx + dx + 118, LH * 0.27, col)
        m.rect(cx - 60, LH * 0.38, cx + 120, LH * 0.8, col)
        m.elipse(cx + 30, LH * 0.45, 55, 55, (200, 150, 80, 255))
        m.elipse(cx + 30, LH * 0.45, 25, 25, col)
        m.rect(cx + 130, LH * 0.45, cx + 520, LH * 0.8, col)
        m.poly([(cx + 300, LH * 0.45), (cx + 310, LH * 0.18), (cx + 320, LH * 0.45)], col)
    else:
        cx = LW * 0.5
        m.rect(cx - 380, LH * 0.6, cx + 380, LH * 0.82, col)
        m.rect(cx - 210, LH * 0.42, cx + 210, LH * 0.62, col)
        m.elipse(cx, LH * 0.42, 200, 200, (200, 160, 70, 255))
        m.rect(cx - 210, LH * 0.42, cx + 210, LH * 0.62, col)
        m.rect(cx - 25, LH * 0.15, cx + 25, LH * 0.25, (200, 160, 70, 255))
        m.poly([(cx - 10, LH * 0.15), (cx, LH * 0.05), (cx + 10, LH * 0.15)], (200, 160, 70, 255))
        for k in range(12):
            m.rect(cx - 200 + k * 35, LH * 0.47, cx - 190 + k * 35, LH * 0.6, (60, 45, 35, 255))
    agua = mar(LW, LH, 0.86, (90, 60, 50), (15, 12, 15), 4, (0.55, (255, 190, 110)))
    return {"fondo": fondo, "capas": [(con_brillo(m.imagen(), (255, 170, 90), 20, 0.7), 0.7), (agua, 1.0)],
            "particulas": "polvo", "tono": "calido", "zoom": (1.0, 1.1)}


def escena_cuna(spec):
    """Cuna imperial bajo una corona: nacimiento del rey de Roma."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (30, 35, 60)), (1, (8, 8, 15))]), 0, 255)
                            .astype(np.uint8)).convert("RGBA")
    m = Lienzo()
    cx, cy = LW / 2, LH * 0.7
    oro = (225, 180, 80, 255)
    m.poly([(cx - 300, cy - 100), (cx + 300, cy - 100), (cx + 250, cy + 60), (cx - 250, cy + 60)], oro)
    m.elipse(cx, cy - 100, 300, 40, (240, 235, 225, 255))
    m.linea([(cx - 300, cy + 200), (cx - 250, cy + 60)], oro, 14)
    m.linea([(cx + 300, cy + 200), (cx + 250, cy + 60)], oro, 14)
    m.linea([(cx - 280, cy - 100), (cx - 250, cy - 420), (cx - 150, cy - 520)], oro, 10)
    m.poly([(cx - 150, cy - 520), (cx - 340, cy - 110), (cx - 280, cy - 100), (cx - 120, cy - 500)], (180, 30, 40, 200))
    m.poly([(cx - 150, cy - 520), (cx + 280, cy - 110), (cx + 340, cy - 100), (cx - 100, cy - 480)], (150, 20, 35, 180))
    m.poly([(cx - 220, cy - 560), (cx - 80, cy - 560), (cx - 60, cy - 650), (cx - 120, cy - 600), (cx - 150, cy - 690),
            (cx - 180, cy - 600), (cx - 240, cy - 650)], oro)
    m.elipse(cx - 150, cy - 710, 14, 14, oro)
    for k in range(12):
        a = k * math.pi / 6
        m.elipse(cx + math.cos(a) * 140, cy + 140 + math.sin(a) * 30, 10, 10, (255, 220, 140, 255))
    return {"fondo": fondo, "capas": [(con_brillo(m.imagen(), (255, 210, 140), 35, 1.3), 1.0)],
            "particulas": "chispas", "tono": "noche", "zoom": (1.0, 1.12)}


def escena_rosa(spec):
    """Rosa marchita y carta: amor y pérdida."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (30, 12, 18)), (1, (8, 3, 5))]) *
                                    (0.7 + 0.5 * ruido_fractal(LW, LH, 72, 5, 5)[..., None]), 0, 255).astype(np.uint8)).convert("RGBA")
    papel = textura_papel(1100, 800, 9)
    d = ImageDraw.Draw(papel)
    for i, ln in enumerate(spec.get("lineas", ["Mon amour,", "je ne passe pas un jour", "sans t'aimer...",
                                               "                  — N."])):
        d.text((120, 140 + i * 110), ln, font=fuente("antigua", 70), fill=(60, 35, 25))
    papel = papel.rotate(6, expand=True, resample=Image.BICUBIC)
    capa = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    capa.alpha_composite(papel, (int(LW * 0.1), int(LH * 0.12)))
    r = Lienzo()
    tx, ty = LW * 0.7, LH * 0.55
    r.linea([(tx, ty), (tx - 260, ty + 380)], (40, 70, 30, 255), 12)
    r.elipse(tx - 120, ty + 170, 60, 22, (50, 90, 40, 255))
    for k in range(7):
        a = k * math.pi * 2 / 7
        r.elipse(tx + math.cos(a) * 45, ty + math.sin(a) * 40, 70, 60, (130 + k * 10, 15, 30, 255))
    for k in range(5):
        a = k * math.pi * 2 / 5 + 0.3
        r.elipse(tx + math.cos(a) * 22, ty + math.sin(a) * 20, 45, 40, (170 + k * 8, 25, 40, 255))
    r.elipse(tx, ty, 25, 22, (110, 10, 25, 255))
    for k, (px, py) in enumerate(((0.55, 0.85), (0.62, 0.9), (0.48, 0.78))):
        r.elipse(LW * px, LH * py, 30, 18, (140, 20, 35, 255))
    capa = Image.alpha_composite(capa, r.imagen())
    return {"fondo": fondo, "capas": [(capa, 1.0)], "particulas": "petalos", "tono": "vela",
            "zoom": (1.0, 1.12), "vela": (LW * 0.92, LH * 0.15)}


def escena_texto(spec):
    """Tarjeta de texto grande (fecha, cifra o frase)."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (20, 12, 8)), (0.5, (45, 25, 15)), (1, (10, 6, 4))]) *
                                    (0.6 + 0.6 * ruido_fractal(LW, LH, spec.get("semilla", 5), 5, 4)[..., None]), 0, 255)
                            .astype(np.uint8)).convert("RGBA")
    t = Lienzo()
    grande = spec.get("grande", "")
    t.texto((LW / 2, LH * 0.47), grande, ("titulo", 260 if len(grande) <= 5 else 130 if len(grande) < 18 else 90),
            (240, 200, 120, 255))
    if spec.get("pequeno"):
        t.texto((LW / 2, LH * 0.68), spec["pequeno"], ("texto", 58), (225, 215, 195, 255))
    t.linea([(LW * 0.35, LH * 0.6), (LW * 0.65, LH * 0.6)], (200, 160, 90, 255), 3)
    return {"fondo": fondo, "capas": [(humo(LW, LH, 13, (120, 100, 80), 0.4), 0.5),
                                      (con_brillo(t.imagen(), (255, 180, 90), 30, 1.0), 1.0)],
            "particulas": "brasas", "tono": "calido", "zoom": (1.0, 1.08), "humo_mov": True}


def escena_titulo(spec):
    """Tarjeta de capítulo."""
    fondo = Image.fromarray(np.clip(degradado(LW, LH, [(0, (8, 5, 4)), (0.5, (35, 18, 10)), (1, (5, 3, 2))]) *
                                    (0.6 + 0.6 * ruido_fractal(LW, LH, 400 + spec.get("semilla", 0), 5, 4)[..., None]),
                                    0, 255).astype(np.uint8)).convert("RGBA")
    t = Lienzo()
    if spec.get("etiqueta"):
        t.texto((LW / 2, LH * 0.36), spec["etiqueta"], ("titulo_n", 52), (200, 170, 120, 255), spacing=0)
    lineas = partir(spec["titulo"], 30)
    for i, ln in enumerate(lineas):
        t.texto((LW / 2, LH * 0.5 + (i - (len(lineas) - 1) / 2) * 110), ln, ("titulo", spec.get("tam", 92)),
                (245, 205, 120, 255))
    y = LH * 0.5 + len(lineas) * 55 + 40
    if spec.get("subtitulo"):
        t.texto((LW / 2, y + 70), spec["subtitulo"], ("texto", 54), (225, 215, 195, 255))
    t.linea([(LW * 0.3, y), (LW * 0.7, y)], (200, 160, 90, 255), 3)
    t.elipse(LW / 2, y, 10, 10, (230, 190, 100, 255))
    for k, xx in enumerate((LW * 0.3, LW * 0.7)):
        t.elipse(xx, y, 5, 5, (230, 190, 100, 255))
    return {"fondo": fondo, "capas": [(humo(LW, LH, 900 + spec.get("semilla", 0), (140, 110, 80), 0.45), 0.5),
                                      (con_brillo(t.imagen(), (255, 170, 80), 35, 1.3), 1.0)],
            "particulas": "brasas", "tono": "calido", "zoom": (1.12, 1.0), "humo_mov": True, "titulo": True}


def partir(texto, ancho):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > ancho and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = (actual + " " + p).strip()
    return lineas + [actual]


# --------------------------------------------------------------------- mapas
_MUNDO = None


def mundo():
    global _MUNDO
    if _MUNDO is None:
        import warnings
        warnings.filterwarnings("ignore")
        import geopandas as gpd
        _MUNDO = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    return _MUNDO


def proyector(caja):
    """caja = (lon0, lon1, lat0, lat1) → función lon,lat → px en la capa."""
    lon0, lon1, lat0, lat1 = caja
    k = math.cos(math.radians((lat0 + lat1) / 2))
    ancho_g = (lon1 - lon0) * k
    alto_g = lat1 - lat0
    escala = min(LW / ancho_g, LH / alto_g)
    cx, cy = (lon0 + lon1) / 2, (lat0 + lat1) / 2

    def f(lon, lat):
        return (LW / 2 + (lon - cx) * k * escala, LH / 2 - (lat - cy) * escala)
    return f


def escena_mapa(spec):
    caja = spec["caja"]
    f = proyector(caja)
    agua = textura_papel(LW, LH, 21, (120, 135, 130))
    arr = np.asarray(agua).astype(np.float32)
    olas_ = (np.sin(np.arange(LH)[:, None] / 7 + ruido_fractal(LW, LH, 22, 4, 6) * 20) > 0.92)
    arr[..., :3] -= olas_[..., None] * 12
    fondo = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    tierra = Lienzo()
    resaltes = spec.get("resaltar", {})
    w = mundo()
    for _, fila in w.iterrows():
        g = fila.geometry
        partes = g.geoms if g.geom_type == "MultiPolygon" else [g]
        color = resaltes.get(fila["name"], (214, 196, 156, 255))
        for pg in partes:
            pts = [f(x, y) for x, y in pg.exterior.coords]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < -200 or min(xs) > LW + 200 or max(ys) < -200 or min(ys) > LH + 200:
                continue
            tierra.poly(pts, color)
            tierra.linea(pts + [pts[0]], (110, 80, 50, 255), 2)
    capa_tierra = tierra.imagen()
    sombra = Image.new("RGBA", capa_tierra.size, (40, 30, 20, 0))
    sombra.putalpha(capa_tierra.split()[3].filter(ImageFilter.GaussianBlur(14)).point(lambda v: v * 0.7))
    papel = textura_papel(LW, LH, 23, (230, 210, 170))
    papel.putalpha(capa_tierra.split()[3])
    capa_tierra = Image.blend(capa_tierra, papel, 0.35)
    fondo = Image.alpha_composite(fondo, sombra)
    fondo = Image.alpha_composite(fondo, capa_tierra)
    deco = Lienzo()
    rx, ry = LW - 260, LH - 330
    for k in range(8):
        a = k * math.pi / 4
        largo = 110 if k % 2 == 0 else 60
        deco.poly([(rx, ry), (rx + math.cos(a - 0.15) * 25, ry + math.sin(a - 0.15) * 25),
                   (rx + math.cos(a) * largo, ry + math.sin(a) * largo),
                   (rx + math.cos(a + 0.15) * 25, ry + math.sin(a + 0.15) * 25)], (90, 60, 35, 230))
    deco.texto((rx, ry - 135), "N", ("titulo", 44), (90, 60, 35, 255))
    for lugar in spec.get("lugares", []):
        nombre, lon, lat = lugar[:3]
        izq = len(lugar) > 3 and lugar[3] == "izq"
        x, y = f(lon, lat)
        deco.elipse(x, y, 9, 9, (60, 30, 20, 255))
        deco.elipse(x, y, 5, 5, (230, 200, 140, 255))
        deco.texto((x - 16 if izq else x + 16, y - 4), nombre, ("texto_b", 40), (50, 30, 20, 255),
                   ancla="rm" if izq else "lm", stroke_width=int(3 * SS), stroke_fill=(235, 220, 185, 255))
    if spec.get("titulo"):
        tw = fuente("titulo", 50).getlength(spec["titulo"]) + 80
        deco.rect(LW / 2 - tw / 2, 150, LW / 2 + tw / 2, 240, (235, 220, 185, 235))
        deco.rect(LW / 2 - tw / 2 + 8, 158, LW / 2 + tw / 2 - 8, 232, (0, 0, 0, 0))
        deco.texto((LW / 2, 195), spec["titulo"], ("titulo", 50), (70, 40, 25, 255))
    fondo = Image.alpha_composite(fondo, deco.imagen())
    rutas = [{"pts": [f(lon, lat) for lon, lat in r["pts"]], "color": r.get("color", (160, 25, 25)),
              "ini": r.get("ini", 0.1), "fin": r.get("fin", 0.75)} for r in spec.get("rutas", [])]
    explosiones = [f(lon, lat) for lon, lat in spec.get("batallas", [])]
    return {"fondo": fondo, "capas": [], "rutas": rutas, "explosiones": explosiones,
            "particulas": None, "tono": "mapa", "zoom": spec.get("zoom", (1.0, 1.08)),
            "pan": spec.get("pan", (0, 0))}


ESCENAS = {
    "batalla": escena_batalla, "marcha": escena_marcha, "naval": escena_naval, "retrato": escena_retrato,
    "doble": escena_doble, "colina": escena_colina, "heroe": escena_heroe, "corcega": escena_corcega,
    "estudio": escena_estudio, "documento": escena_documento, "coronacion": escena_coronacion,
    "salon": escena_salon, "castillo": escena_castillo, "revolucion": escena_revolucion, "moscu": escena_moscu,
    "isla": escena_isla, "longwood": escena_longwood, "ciudad": escena_ciudad, "cuna": escena_cuna,
    "rosa": escena_rosa, "texto": escena_texto, "titulo": escena_titulo, "mapa": escena_mapa,
}


def preparar(spec):
    datos = ESCENAS[spec["tipo"]](spec)
    datos["fondo"] = datos["fondo"].convert("RGB")
    return datos
