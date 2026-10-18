"""Utilidades de dibujo compartidas: fuentes, ruido, texto con sombra, viñeta y grano."""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

from guion import W, H

AQUI = Path(__file__).parent
FUENTES_NAPOLEON = AQUI.parent / "napoleon" / "fuentes"
INTER = Path("/usr/share/fonts/opentype/inter")

ORO = (245, 200, 60)
ROJO = (215, 35, 45)
AZUL = (20, 60, 160)
BLANCO = (245, 242, 235)
CREMA = (238, 224, 190)


@lru_cache(None)
def fuente(nombre, tam):
    rutas = {
        "titulo": FUENTES_NAPOLEON / "cinzel-latin-700-normal.woff",
        "titulo_n": FUENTES_NAPOLEON / "cinzel-latin-400-normal.woff",
        "serif": FUENTES_NAPOLEON / "eb-garamond-latin-400-normal.woff",
        "serif_b": FUENTES_NAPOLEON / "eb-garamond-latin-700-normal.woff",
        "antigua": FUENTES_NAPOLEON / "im-fell-english-latin-400-normal.woff",
        "negra": INTER / "InterDisplay-Black.otf",
        "fuerte": INTER / "InterDisplay-ExtraBold.otf",
        "media": INTER / "InterDisplay-SemiBold.otf",
        "normal": INTER / "Inter-Medium.otf",
    }
    return ImageFont.truetype(str(rutas[nombre]), tam)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def rampa(t, a, b):
    """0 antes de a, 1 después de b, suave entre medias."""
    return ease((t - a) / max(1e-6, b - a))


@lru_cache(None)
def ruido(w, h, semilla, octavas=6, base=4, persistencia=0.55):
    """Ruido fractal en [0,1] de tamaño (h, w)."""
    rng = np.random.default_rng(semilla)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octavas):
        n = base * 2 ** o
        g = rng.random((max(2, int(n * h / max(w, h)) + 2), n + 2)).astype(np.float32)
        z = ndimage.zoom(g, (h / (g.shape[0] - 2), w / (g.shape[1] - 2)), order=3)[:h, :w]
        out[: z.shape[0], : z.shape[1]] += z * amp
        total += amp
        amp *= persistencia
    out /= total
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def degradado(w, h, arriba, abajo):
    t = np.linspace(0, 1, h)[:, None, None]
    a, b = np.array(arriba, np.float32), np.array(abajo, np.float32)
    return np.broadcast_to(a + (b - a) * t, (h, w, 3)).astype(np.float32)


def texto(img, xy, txt, f, fill=BLANCO, ancla="mm", sombra=10, borde=0, color_borde=(0, 0, 0), alfa=1.0,
          espaciado=0):
    """Texto con sombra difusa (estilo tráiler). img es RGBA o RGB; se modifica en el sitio."""
    if alfa <= 0.01:
        return img
    if isinstance(f, tuple):
        f = fuente(*f)
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    if espaciado:
        # texto con letras separadas: se dibuja letra a letra
        anchos = [f.getlength(c) + espaciado for c in txt]
        total = sum(anchos) - espaciado
        x0 = xy[0] - (total / 2 if ancla[0] == "m" else (total if ancla[0] == "r" else 0))
        for c, aw in zip(txt, anchos):
            d.text((x0, xy[1]), c, font=f, fill=fill + (255,), anchor="l" + ancla[1],
                   stroke_width=borde, stroke_fill=color_borde + (255,))
            x0 += aw
    else:
        d.text(xy, txt, font=f, fill=fill + (255,), anchor=ancla, stroke_width=borde,
               stroke_fill=color_borde + (255,))
    if sombra:
        s = capa.split()[3].filter(ImageFilter.GaussianBlur(sombra))
        negra = Image.new("RGBA", img.size, (0, 0, 0, 0))
        negra.putalpha(s.point(lambda v: int(v * 0.85 * alfa)))
        img.alpha_composite(negra) if img.mode == "RGBA" else img.paste(negra, (0, 0), negra)
    if alfa < 1:
        capa.putalpha(capa.split()[3].point(lambda v: int(v * alfa)))
    if img.mode == "RGBA":
        img.alpha_composite(capa)
    else:
        img.paste(capa, (0, 0), capa)
    return img


def caja_redondeada(img, x0, y0, x1, y1, color, r=18, alfa=1.0):
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).rounded_rectangle((x0, y0, x1, y1), r, fill=color[:3] + (int(color[3] * alfa),)
                                           if len(color) == 4 else color + (int(255 * alfa),))
    img.paste(capa, (0, 0), capa) if img.mode == "RGB" else img.alpha_composite(capa)


@lru_cache(None)
def vineta(fuerza=0.55):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return (1 - fuerza * np.clip(d, 0, 1.3) ** 2.2)[..., None].astype(np.float32)


@lru_cache(None)
def granos(n=8):
    rng = np.random.default_rng(7)
    g = rng.standard_normal((n, H // 2, W // 2)).astype(np.float32)
    return [ndimage.zoom(x, 2, order=0)[..., None] for x in g]


def acabado(img, i_cuadro, grano=7.0, vin=0.55, tinte=None, sepia=0.0, parpadeo=0.0, rayas=False):
    """Gradación de color final: tinte, sepia, viñeta, grano y (opcional) película antigua."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    if sepia > 0:
        gris = a @ np.array([0.30, 0.59, 0.11], np.float32)
        sep = np.stack([gris * 1.07 + 18, gris * 0.88 + 8, gris * 0.66], -1)
        a = a * (1 - sepia) + sep * sepia
    if tinte is not None:
        a = a * np.array(tinte, np.float32)
    if parpadeo:
        rng = np.random.default_rng(i_cuadro)
        a *= 1 + (rng.random() - 0.5) * parpadeo
    a *= vineta(vin)
    a += granos()[i_cuadro % 8] * grano
    if rayas:
        rng = np.random.default_rng(i_cuadro * 31)
        for _ in range(rng.integers(0, 3)):
            x = int(rng.integers(0, W))
            a[:, x: x + 2] = a[:, x: x + 2] * 0.5 + 110
        if rng.random() < 0.3:
            y, x = int(rng.integers(0, H)), int(rng.integers(0, W))
            a[y: y + 6, x: x + 6] = 20
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def bandera_venezuela(w, h, estrellas=True):
    """Bandera nacional (versión civil: tricolor con las 8 estrellas en arco)."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, h / 3), fill=(255, 204, 0))
    d.rectangle((0, h / 3, w, 2 * h / 3), fill=(0, 36, 125))
    d.rectangle((0, 2 * h / 3, w, h), fill=(207, 20, 43))
    if estrellas:
        cx, cy, r = w / 2, h / 2 + h * 0.17, h * 0.30
        re = h * 0.04
        for k in range(8):
            ang = math.radians(180 + 30 + k * (120 / 7))
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
            pts = []
            for j in range(10):
                rr = re if j % 2 == 0 else re * 0.4
                a = -math.pi / 2 + j * math.pi / 5 + (ang + math.pi / 2)
                pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
            d.polygon(pts, fill=(255, 255, 255))
    return img


def union_jack(w, h):
    img = Image.new("RGB", (w, h), (1, 33, 105))
    d = ImageDraw.Draw(img)
    t = h / 30
    for a, b in (((0, 0), (w, h)), ((0, h), (w, 0))):
        d.line([a, b], fill=(255, 255, 255), width=int(6 * t))
        d.line([a, b], fill=(200, 16, 46), width=int(2 * t))
    d.rectangle((w / 2 - 5 * t, 0, w / 2 + 5 * t, h), fill=(255, 255, 255))
    d.rectangle((0, h / 2 - 5 * t, w, h / 2 + 5 * t), fill=(255, 255, 255))
    d.rectangle((w / 2 - 3 * t, 0, w / 2 + 3 * t, h), fill=(200, 16, 46))
    d.rectangle((0, h / 2 - 3 * t, w, h / 2 + 3 * t), fill=(200, 16, 46))
    return img


def bandera_guyana(w, h):
    """Bandera de Guyana («Golden Arrowhead», desde 1966)."""
    img = Image.new("RGB", (w, h), (0, 158, 73))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (w, h / 2), (0, h)], fill=(255, 255, 255))
    d.polygon([(0, h * 0.04), (w * 0.95, h / 2), (0, h * 0.96)], fill=(252, 209, 22))
    d.polygon([(0, 0), (w / 2, h / 2), (0, h)], fill=(0, 0, 0))
    d.polygon([(0, h * 0.05), (w * 0.45, h / 2), (0, h * 0.95)], fill=(206, 17, 38))
    return img


def ondear(bandera, t, amp=0.06, ondas=1.6, vel=1.0, sombra=0.45):
    """Deforma una bandera como si ondeara con el viento. Devuelve RGBA con margen vertical."""
    b = np.asarray(bandera).astype(np.float32)
    h, w = b.shape[:2]
    m = int(h * (amp * 1.3 + 0.02))
    y, x = np.mgrid[0:h + 2 * m, 0:w].astype(np.float32)
    u = x / w
    fase = 2 * np.pi * (ondas * u - vel * t) + 0.7 * np.sin(2 * np.pi * ((y - m) / h * 0.6 + t * 0.25))
    fuerza = amp * h * (0.1 + u)        # el lado del asta casi no se mueve
    dy = np.sin(fase) * fuerza
    dx = np.cos(fase) * fuerza * 0.12
    luz = np.cos(fase - 0.6)            # luz y sombra en los pliegues
    sy = y - m - dy
    sx = np.clip(x - dx, 0, w - 1)
    out = np.stack([ndimage.map_coordinates(b[..., c], [np.clip(sy, 0, h - 1), sx], order=1)
                    for c in range(3)], -1)
    out *= (1 + luz * sombra * (0.25 + u))[..., None]
    alfa = np.clip(np.minimum(sy + 1, h - sy), 0, 1) * 255
    rgba = np.dstack([np.clip(out, 0, 255), alfa]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")
