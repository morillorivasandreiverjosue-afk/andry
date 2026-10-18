"""Planos del video. Cada función recibe (t, d) — segundo dentro del plano y duración — y
devuelve una imagen RGB de W×H. Los fondos pesados se dibujan una sola vez (lru_cache).
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from base import (BLANCO, CREMA, ORO, ROJO, bandera_guyana, bandera_venezuela, caja_redondeada, degradado,
                  ease, ease_out, fuente, ondear, rampa, ruido, texto, union_jack)
from guion import W, H
from mapa import mapa

AMARILLO = (255, 214, 10)


def titulo(img, t, txt, y, tam=96, color=BLANCO, aparece=0.0, f="negra", sub=None, sub_color=AMARILLO):
    """Título con entrada tipo «punch» (escala + aparición)."""
    a = rampa(t, aparece, aparece + 0.18)
    if a <= 0:
        return
    s = 1 + 0.25 * (1 - ease_out((t - aparece) / 0.25))
    texto(img, (W / 2, y), txt, (f, int(tam * s)), fill=color, sombra=14, alfa=a, borde=3, color_borde=(0, 0, 0))
    if sub:
        a2 = rampa(t, aparece + 0.2, aparece + 0.4)
        texto(img, (W / 2, y + tam * 0.85), sub, ("fuerte", int(tam * 0.42)), fill=sub_color, sombra=10, alfa=a2,
              borde=2, color_borde=(0, 0, 0))


def etiqueta_caja(img, x, y, txt, color=(0, 0, 0, 170), tc=BLANCO, tam=40, a=1.0, f="fuerte"):
    fo = fuente(f, tam)
    w = fo.getlength(txt)
    caja_redondeada(img, x - w / 2 - 26, y - tam * 0.75, x + w / 2 + 26, y + tam * 0.75, color, 16, a)
    texto(img, (x, y), txt, fo, fill=tc, sombra=0, alfa=a)


# ------------------------------------------------------------------ mapas
ZONA = (-59.95, 5.0)      # centro aproximado de la zona en reclamación


def leyenda(img, a=1.0, y=1560):
    """Leyenda que distingue frontera administrada y zona reclamada."""
    if a <= 0:
        return
    caja_redondeada(img, 70, y - 20, W - 70, y + 190, (0, 0, 0, 175), 20, a)
    d = ImageDraw.Draw(img)
    al = int(255 * a)
    d.line((110, y + 40, 190, y + 40), fill=(255, 250, 235, al), width=8)
    texto(img, (215, y + 40), "Frontera administrada hoy (laudo de 1899)", ("media", 34), ancla="lm", sombra=0, alfa=a)
    for k in range(5):
        d.line((110 + k * 16, y + 135, 130 + k * 16, y + 105), fill=(235, 50, 55, al), width=6)
    d.rectangle((110, y + 105, 190, y + 135), outline=(255, 80, 80, al), width=3)
    texto(img, (215, y + 120), "Zona reclamada por Venezuela", ("media", 34), ancla="lm", sombra=0, alfa=a)


def p_gancho(t, d):
    """0–3.6 s: zoom rápido de Sudamérica al Esequibo. Gancho en pantalla."""
    m = mapa()
    k = ease(t / 2.2)
    alto = 46 * (9.6 / 46) ** k
    lon = -63 + (ZONA[0] + 63) * k
    lat = -4 + (ZONA[1] + 4) * k
    pulso = 0.75 + 0.25 * math.sin(t * 9)
    img, _ = m.render(lon, lat, alto, t, capas={"fronteras": 1, "zona": pulso, "zona_brillo": pulso * rampa(t, 1.2, 2)},
                      nubes=0.25 * (1 - k))
    img = img.convert("RGBA")
    titulo(img, t, "VENEZUELA RECLAMA", 300, 92, aparece=0.05)
    titulo(img, t, "ESTE TERRITORIO", 410, 104, color=(255, 70, 70), aparece=0.35)
    if t > 1.9:
        a = rampa(t, 1.9, 2.3)
        d = ImageDraw.Draw(img)
        y = 1150 + 30 * math.sin(t * 6)
        d.polygon([(W / 2 - 40, y - 80), (W / 2 + 40, y - 80), (W / 2, y - 10)], fill=(255, 214, 10, int(255 * a)))
    return img.convert("RGB")


def p_km2(t, d):
    """3.6–7.2 s: la zona de cerca con el contador de km²."""
    m = mapa()
    pulso = 0.8 + 0.2 * math.sin(t * 6)
    img, _ = m.render(ZONA[0] + 0.25, ZONA[1] - 0.2, 8.8 - 0.6 * t / d, t,
                      capas={"fronteras": 1, "guyana": 0.5, "zona": pulso, "zona_brillo": 0.7, "esequibo": rampa(t, 1.2, 1.8)},
                      etiquetas=[{"lon": -58.0, "lat": 3.2, "texto": "GUYANA", "fuente": ("fuerte", 46), "a": rampa(t, 0.3, 0.7)},
                                 {"lon": -63.2, "lat": 7.2, "texto": "VENEZUELA", "fuente": ("fuerte", 46), "a": rampa(t, 0.3, 0.7)},
                                 {"lon": -58.55, "lat": 2.2, "texto": "río Esequibo", "fuente": ("media", 36),
                                  "color": (120, 230, 255), "a": rampa(t, 1.3, 1.8)}],
                      nubes=0.15)
    img = img.convert("RGBA")
    n = int(160000 * ease_out(t / 1.6)) if t < 1.6 else 160000
    titulo(img, t, f"≈ {n:,}".replace(",", ".") + " km²", 330, 120, color=AMARILLO, aparece=0.0)
    titulo(img, t, "CONTROLADOS HOY POR GUYANA", 460, 50, aparece=0.6)
    return img.convert("RGB")


# ------------------------------------------------------------------ selva
@lru_cache(None)
def fondo_selva():
    w, h = 1500, 3200
    base = degradado(w, h, (18, 40, 20), (14, 34, 16)) * (0.7 + 0.6 * ruido(w, h, 41, 6, 6, 0.6))[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    # río serpenteante
    rio = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(rio)
    pts = [(w / 2 + 330 * math.sin(y / 520) + 120 * math.sin(y / 170), y) for y in range(-50, h + 50, 20)]
    d.line(pts, fill=(95, 82, 55, 255), width=200, joint="curve")
    d.line(pts, fill=(130, 118, 85, 255), width=120, joint="curve")
    d.line([(x + 25, y) for x, y in pts], fill=(175, 175, 160, 120), width=26, joint="curve")
    img.alpha_composite(rio.filter(ImageFilter.GaussianBlur(3)))
    # copas de árboles
    rng = np.random.default_rng(5)
    copas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(copas)
    for _ in range(9000):
        x, y = rng.random() * w, rng.random() * h
        rx = w / 2 + 330 * math.sin(y / 520) + 120 * math.sin(y / 170)
        if abs(x - rx) < 95 + rng.random() * 30:
            continue
        r = rng.uniform(18, 48)
        g = rng.uniform(0.6, 1.25)
        c = (int(30 * g), int(rng.uniform(70, 105) * g), int(28 * g))
        d.ellipse((x - r + 6, y - r + 8, x + r + 6, y + r + 8), fill=(5, 15, 5, 150))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c + (255,))
        d.ellipse((x - r * 0.6, y - r * 0.7, x + r * 0.2, y + r * 0.1), fill=(min(255, c[0] + 30), min(255, c[1] + 45), c[2] + 15, 160))
    img.alpha_composite(copas.filter(ImageFilter.GaussianBlur(1.2)))
    return img.convert("RGB")


@lru_cache(None)
def niebla():
    n = ruido(540, 1600, 44, 5, 3, 0.6)
    return np.clip((n - 0.45) * 2.5, 0, 1)


def p_selva(t, d):
    """7.2–9.8 s: vuelo de dron sobre la selva y el río. Título EL ESEQUIBO."""
    f = fondo_selva()
    y = 2900 - 1700 - (t / d) * 500
    z = 1.0 + 0.06 * t / d
    cw, ch = 1100 / z, 1955 / z
    img = f.resize((W, H), Image.BILINEAR, box=(200 + (1100 - cw) / 2, y, 200 + (1100 - cw) / 2 + cw, y + ch)).convert("RGBA")
    n = niebla()
    off = int(t * 40) % 600
    a = n[off: off + 960, :] if off + 960 <= n.shape[0] else n[:960, :]
    neb = Image.new("RGBA", (W, H), (220, 230, 225, 0))
    neb.putalpha(Image.fromarray((a * 150).astype(np.uint8)).resize((W, H)))
    img.alpha_composite(neb)
    titulo(img, t, "EL ESEQUIBO", 760, 150, color=BLANCO, aparece=0.1, f="titulo",
           sub="selva · ríos · oro · diamantes", sub_color=CREMA)
    return img.convert("RGB")


def p_anios(t, d):
    """9.8–12.4 s: contador de años 1899 → hoy."""
    img = Image.fromarray(degradado(W, H, (25, 18, 12), (5, 4, 3)).astype(np.uint8)).convert("RGBA")
    anio = int(1899 + (2026 - 1899) * ease_out(t / 1.8))
    texto(img, (W / 2, 820), str(anio), ("negra", 300), fill=AMARILLO, sombra=30)
    titulo(img, t, "MÁS DE 100 AÑOS", 1060, 90, aparece=0.3)
    titulo(img, t, "SIN RESOLVERSE", 1170, 90, color=(255, 70, 70), aparece=0.6)
    # barra de tiempo
    dr = ImageDraw.Draw(img)
    p = ease_out(t / 1.8)
    dr.rounded_rectangle((140, 600, W - 140, 616), 8, fill=(255, 255, 255, 50))
    dr.rounded_rectangle((140, 600, 140 + (W - 280) * p, 616), 8, fill=AMARILLO + (255,))
    texto(img, (140, 560), "1899", ("fuerte", 40), ancla="lm", sombra=0)
    texto(img, (W - 140, 560), "HOY", ("fuerte", 40), ancla="rm", sombra=0)
    return img.convert("RGB")


# ------------------------------------------------------------------ 1899
def silueta_persona(d, x, y, s, col, barba=False, sombrero=False):
    d.ellipse((x - 34 * s, y - 150 * s, x + 34 * s, y - 70 * s), fill=col)          # cabeza
    if barba:
        d.ellipse((x - 30 * s, y - 105 * s, x + 30 * s, y - 50 * s), fill=col)
    d.polygon([(x - 18 * s, y - 75 * s), (x + 18 * s, y - 75 * s), (x + 22 * s, y - 55 * s), (x - 22 * s, y - 55 * s)], fill=col)
    d.rounded_rectangle((x - 95 * s, y - 60 * s, x + 95 * s, y + 200 * s), int(55 * s), fill=col)   # torso


@lru_cache(None)
def fondo_tribunal():
    img = Image.fromarray(degradado(W, H, (70, 58, 44), (25, 20, 15)).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    # ventanales con luz
    for x in (150, 450, 750):
        d.rectangle((x, 260, x + 180, 900), fill=(200, 180, 140, 255))
        d.rectangle((x + 84, 260, x + 96, 900), fill=(60, 50, 38, 255))
        d.rectangle((x, 560, x + 180, 572), fill=(60, 50, 38, 255))
        d.pieslice((x, 170, x + 180, 350), 180, 360, fill=(200, 180, 140, 255))
    luz = Image.new("RGBA", (W, H), (255, 235, 190, 0))
    dl = ImageDraw.Draw(luz)
    for x in (150, 450, 750):
        dl.polygon([(x, 300), (x + 180, 300), (x + 420, 1500), (x + 120, 1500)], fill=(255, 235, 190, 45))
    img.alpha_composite(luz.filter(ImageFilter.GaussianBlur(30)))
    # cinco árbitros tras la mesa
    p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dp = ImageDraw.Draw(p)
    col = (14, 11, 8, 255)
    for k, x in enumerate((140, 330, 540, 750, 940)):
        silueta_persona(dp, x, 1150 - (40 if k == 2 else 0), 1.05, col, barba=k in (0, 2, 3))
    dp.rectangle((0, 1250, W, 1920), fill=(20, 15, 10, 255))           # mesa
    dp.rectangle((0, 1250, W, 1275), fill=(60, 48, 34, 255))
    for x in (230, 640, 860):                                           # papeles sobre la mesa
        dp.polygon([(x, 1290), (x + 120, 1285), (x + 130, 1330), (x + 5, 1335)], fill=(210, 195, 160, 255))
    img.alpha_composite(p)
    return img.convert("RGB")


def p_tribunal(t, d):
    """12.4–15.8 s: recreación del tribunal arbitral de París (1899)."""
    f = fondo_tribunal()
    z = 1.06 + 0.08 * t / d
    cw, ch = W / z, H / z
    img = f.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2 + 30, (W + cw) / 2, (H + ch) / 2 + 30)).convert("RGBA")
    titulo(img, t, "PARÍS · 1899", 1080, 120, color=CREMA, aparece=0.15, f="titulo", sub="TRIBUNAL ARBITRAL", sub_color=BLANCO)
    texto(img, (W / 2, 1290), "Recreación ilustrativa", ("normal", 28), fill=(220, 210, 190), sombra=4, alfa=0.8)
    return img.convert("RGB")


def p_mapa1899(t, d):
    """15.8–20.1 s: el laudo dibuja la frontera; la zona queda para la Guayana Británica."""
    m = mapa()
    img, _ = m.render(-60.6, 5.6, 9.8 - 0.6 * t / d, t,
                      capas={"fronteras": 0.6, "zona": 0.6 * rampa(t, 0.8, 1.6), "linea1899": rampa(t, 0.2, 0.9)},
                      etiquetas=[{"lon": -62.0, "lat": 7.6, "texto": "VENEZUELA", "fuente": ("titulo", 48)},
                                 {"lon": -59.3, "lat": 4.9, "texto": "GUAYANA", "fuente": ("titulo", 46),
                                  "a": rampa(t, 1.2, 1.7)},
                                 {"lon": -59.3, "lat": 4.45, "texto": "BRITÁNICA", "fuente": ("titulo", 46),
                                  "a": rampa(t, 1.2, 1.7)}],
                      nubes=0)
    img = img.convert("RGBA")
    etiqueta_caja(img, W / 2, 330, "LAUDO ARBITRAL DE PARÍS", (0, 0, 0, 190), CREMA, 50, rampa(t, 0.0, 0.3), "titulo")
    etiqueta_caja(img, W / 2, 425, "3 de octubre de 1899", (0, 0, 0, 160), BLANCO, 36, rampa(t, 0.2, 0.5), "media")
    return img.convert("RGB")


# ------------------------------------------------------------------ documentos
@lru_cache(None)
def papel(w, h, semilla=3, tono=(226, 210, 172)):
    n = ruido(w, h, semilla, 6, 4, 0.6)
    a = np.array(tono, np.float32) * (0.82 + 0.25 * n)[..., None]
    y, x = np.mgrid[0:h, 0:w]
    borde = np.minimum(np.minimum(x, w - x), np.minimum(y, h - y)).astype(np.float32)
    a *= (0.75 + 0.25 * np.clip(borde / 60, 0, 1))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def documento(titulo_doc, sub, semilla, lineas=14, firma=None, progreso_firma=1.0):
    w, h = 820, 1080
    img = papel(w, h, semilla).copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    texto(img, (w / 2, 120), titulo_doc, ("titulo", 46), fill=(50, 32, 20), sombra=0)
    texto(img, (w / 2, 185), sub, ("serif", 34), fill=(70, 50, 30), sombra=0)
    d.line((120, 225, w - 120, 225), fill=(90, 60, 40, 255), width=2)
    rng = np.random.default_rng(semilla)
    for k in range(lineas):          # renglones manuscritos ilegibles (no se inventa texto)
        y = 280 + k * 46
        x = 90.0
        fin = w - 90 - (rng.random() * 200 if k % 4 == 3 else 0)
        pts = []
        while x < fin:
            pts.append((x, y + math.sin(x / 7 + k) * 6 * rng.random()))
            x += 4
        d.line(pts, fill=(60, 45, 35, 170), width=2)
    if firma:
        pts = [(w - 380 + i * 2.6, 960 + 22 * math.sin(i / 6) * math.cos(i / 17)) for i in range(110)]
        n = int(len(pts) * progreso_firma)
        if n > 1:
            d.line(pts[:n], fill=(20, 25, 70, 255), width=4)
        d.line((w - 400, 1000, w - 90, 1000), fill=(60, 45, 35, 200), width=2)
        texto(img, (w - 245, 1030), firma, ("serif", 26), fill=(60, 45, 35), sombra=0)
    return img


@lru_cache(None)
def sello(txt="NULO E ÍRRITO"):
    s = Image.new("RGBA", (760, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((10, 10, 750, 250), 24, outline=(200, 20, 30, 255), width=14)
    d.text((380, 130), txt, font=fuente("negra", 86), fill=(200, 20, 30, 255), anchor="mm")
    n = ruido(760, 260, 9, 4, 8, 0.6)
    a = np.asarray(s.split()[3]).astype(np.float32) * np.clip(n * 1.8 - 0.1, 0, 1)
    s.putalpha(Image.fromarray(a.astype(np.uint8)))
    return s.rotate(14, expand=True, resample=Image.BICUBIC)


@lru_cache(None)
def bandera_grande():
    return bandera_venezuela(1500, 1000)


def fondo_bandera(t, oscuro=0.45):
    b = ondear(bandera_grande(), t * 0.55, amp=0.07, ondas=1.3)
    fondo = Image.new("RGB", (W, H), (8, 8, 12))
    bb = b.resize((int(b.width * 1.75), int(b.height * 1.75)), Image.BILINEAR).rotate(-8, expand=True, resample=Image.BILINEAR)
    fondo.paste(bb, ((W - bb.width) // 2, (H - bb.height) // 2), bb)
    a = np.asarray(fondo).astype(np.float32) * (1 - oscuro)
    return Image.fromarray(a.astype(np.uint8))


def p_nulo(t, d):
    """20.1–24.3 s: Venezuela rechaza el laudo: sello «NULO E ÍRRITO» sobre la bandera."""
    img = fondo_bandera(t, 0.5).convert("RGBA")
    doc = documento("LAUDO ARBITRAL", "París, 1899", 3)
    doc = doc.rotate(-4, expand=True, resample=Image.BICUBIC)
    esc = 0.9 + 0.05 * t / d
    doc = doc.resize((int(doc.width * esc), int(doc.height * esc)), Image.BILINEAR)
    ts = 1.4
    sh = max(0.0, 1 - (t - ts) / 0.35) if t >= ts else 0.0
    dx, dy = int(math.sin(t * 90) * 22 * sh), int(math.cos(t * 77) * 22 * sh)
    img.alpha_composite(doc, ((W - doc.width) // 2 + dx, 470 + dy))
    if t >= ts:
        k = ease_out((t - ts) / 0.12)
        s = sello()
        f = 2.2 - 1.2 * k
        s = s.resize((int(s.width * f), int(s.height * f)), Image.BILINEAR)
        if k < 1:
            s.putalpha(s.split()[3].point(lambda v: int(v * k)))
        img.alpha_composite(s, ((W - s.width) // 2 + dx, 1000 - s.height // 2 + dy))
    titulo(img, t, "POSICIÓN DE VENEZUELA", 300, 72, color=AMARILLO, aparece=0.0)
    titulo(img, t, "Rechaza el laudo de 1899", 390, 50, aparece=0.3, f="fuerte")
    return img.convert("RGB")


@lru_cache(None)
def banderas_1966():
    gb = union_jack(240, 120)
    bg = Image.new("RGB", (240, 120), (1, 33, 105))      # Guayana Británica: enseña azul (simplificada)
    bg.paste(union_jack(120, 60), (0, 0))
    ImageDraw.Draw(bg).ellipse((160, 40, 200, 80), fill=(235, 235, 235))
    return [bandera_venezuela(240, 160).resize((240, 120)), gb, bg]


def p_ginebra(t, d):
    """24.3–28.6 s: el Acuerdo de Ginebra (17 de febrero de 1966), película en blanco y negro."""
    img = Image.fromarray(degradado(W, H, (60, 60, 64), (15, 15, 18)).astype(np.uint8)).convert("RGBA")
    doc = documento("ACUERDO DE GINEBRA", "17 de febrero de 1966", 8, 13, firma="Firmado en Ginebra",
                    progreso_firma=rampa(t, 0.6, 2.4))
    esc = 1.0 + 0.05 * t / d
    doc = doc.resize((int(doc.width * esc), int(doc.height * esc)), Image.BILINEAR)
    img.alpha_composite(doc, ((W - doc.width) // 2, 560))
    titulo(img, t, "GINEBRA · 1966", 270, 110, color=BLANCO, aparece=0.0, f="titulo")
    for k, (b, nombre) in enumerate(zip(banderas_1966(), ["Venezuela", "Reino Unido", "Guayana Británica"])):
        a = rampa(t, 0.3 + 0.15 * k, 0.5 + 0.15 * k)
        x = 90 + k * 330 + 45
        bb = b.convert("RGBA")
        bb.putalpha(int(255 * a))
        img.alpha_composite(bb, (x, 380))
        texto(img, (x + 120, 530), nombre, ("media", 30), sombra=4, alfa=a)
    return img.convert("RGB")


def p_mesa(t, d):
    """28.6–31.7 s: delegaciones negociando (recreación) y el objetivo del acuerdo."""
    img = Image.fromarray(degradado(W, H, (55, 55, 58), (12, 12, 14)).astype(np.uint8)).convert("RGBA")
    dr = ImageDraw.Draw(img)
    dr.rectangle((0, 1100, W, H), fill=(22, 20, 18, 255))
    dr.polygon([(80, 1100), (W - 80, 1100), (W + 200, 1500), (-200, 1500)], fill=(48, 40, 32, 255))
    col = (10, 10, 10, 255)
    for x in (170, 400):
        silueta_persona(dr, x + 15 * math.sin(t), 1080, 1.0, col)
    for x in (680, 910):
        silueta_persona(dr, x, 1080, 1.0, col)
    for k, b in enumerate(banderas_1966()[:2]):
        bb = b.resize((120, 60))
        x = 380 if k == 0 else 600
        dr.line((x + 60, 1150, x + 60, 1060), fill=(150, 150, 150, 255), width=4)
        img.paste(bb, (x, 1000))
    titulo(img, t, "OBJETIVO:", 330, 70, color=AMARILLO, aparece=0.0)
    titulo(img, t, "UNA SOLUCIÓN PRÁCTICA", 440, 72, aparece=0.25)
    titulo(img, t, "A LA CONTROVERSIA", 540, 72, aparece=0.45)
    texto(img, (W / 2, 1560), "Recreación ilustrativa", ("normal", 28), fill=(200, 200, 200), sombra=4, alfa=0.8)
    return img.convert("RGB")


# ------------------------------------------------------------------ posiciones
def p_posiciones(t, d):
    """31.7–38.3 s: Guyana considera válido el laudo y administra el territorio; Venezuela lo reclama."""
    m = mapa()
    img, _ = m.render(-60.3, 5.4, 10.5 - 0.5 * t / d, t,
                      capas={"fronteras": 0.7, "guyana": rampa(t, 0.0, 0.4), "linea1899": 1, "zona": 0.6 + 0.3 * rampa(t, 3.2, 3.6),
                             "venezuela": 0.6 * rampa(t, 3.2, 3.6)},
                      etiquetas=[{"lon": -62.2, "lat": 6.6, "texto": "VENEZUELA", "fuente": ("fuerte", 44)},
                                 {"lon": -58.1, "lat": 3.3, "texto": "GUYANA", "fuente": ("fuerte", 44)}],
                      nubes=0)
    img = img.convert("RGBA")
    a1 = rampa(t, 0.2, 0.5)
    caja_redondeada(img, 60, 190, W - 60, 470, (0, 0, 0, 185), 22, a1)
    gb = bandera_guyana(150, 94).convert("RGBA")
    gb.putalpha(int(255 * a1))
    img.alpha_composite(gb, (100, 225))
    texto(img, (290, 250), "POSICIÓN DE GUYANA", ("negra", 46), fill=(120, 235, 160), ancla="lm", sombra=0, alfa=a1)
    texto(img, (290, 320), "• El laudo de 1899 es válido", ("media", 38), ancla="lm", sombra=0, alfa=rampa(t, 0.5, 0.8))
    texto(img, (290, 390), "• Administra el territorio", ("media", 38), ancla="lm", sombra=0, alfa=rampa(t, 2.6, 2.9))
    a2 = rampa(t, 3.3, 3.6)
    caja_redondeada(img, 60, 500, W - 60, 640, (0, 0, 0, 185), 22, a2)
    vb = bandera_venezuela(150, 100).convert("RGBA")
    vb.putalpha(int(255 * a2))
    img.alpha_composite(vb, (100, 520))
    texto(img, (290, 545), "POSICIÓN DE VENEZUELA", ("negra", 46), fill=AMARILLO, ancla="lm", sombra=0, alfa=a2)
    texto(img, (290, 605), "• Reclama la zona hasta el río", ("media", 38), ancla="lm", sombra=0, alfa=a2)
    leyenda(img, rampa(t, 1.0, 1.4), y=700)
    return img.convert("RGB")


# ------------------------------------------------------------------ petróleo
@lru_cache(None)
def cielo_noche():
    a = degradado(W, 1000, (6, 10, 28), (120, 60, 40))
    a[700:] = a[700:] * 1.0
    return a


def plataforma(d, x, y, s, col):
    for dx in (-110, -40, 40, 110):                               # patas
        d.polygon([(x + dx * s - 8 * s, y), (x + dx * s + 8 * s, y), (x + dx * s * 0.8 + 6 * s, y - 230 * s),
                   (x + dx * s * 0.8 - 6 * s, y - 230 * s)], fill=col)
    d.rectangle((x - 150 * s, y - 260 * s, x + 150 * s, y - 220 * s), fill=col)             # cubierta
    d.rectangle((x - 130 * s, y - 330 * s, x + 20 * s, y - 260 * s), fill=col)              # módulos
    d.polygon([(x + 50 * s, y - 260 * s), (x + 120 * s, y - 260 * s), (x + 85 * s, y - 520 * s)], fill=col)   # torre
    d.line((x + 85 * s, y - 520 * s, x + 85 * s, y - 560 * s), fill=col, width=int(6 * s))
    d.line((x - 120 * s, y - 330 * s, x - 260 * s, y - 470 * s), fill=col, width=int(10 * s))  # quemador
    d.line((x - 100 * s, y - 330 * s, x + 10 * s, y - 440 * s), fill=col, width=int(7 * s))   # grúa


def p_petroleo(t, d):
    """38.3–41.8 s: plataforma petrolera de noche con su llama."""
    img = Image.new("RGB", (W, H))
    img.paste(Image.fromarray(cielo_noche().astype(np.uint8)), (0, 0))
    # mar
    yy = np.arange(H - 1000)[:, None].astype(np.float32)
    xx = np.arange(W)[None, :].astype(np.float32)
    ola = np.sin(xx / 23 + yy * 0.6 - t * 3) * np.sin(xx / 61 - yy * 0.13 + t) * np.exp(-yy / 900)
    mar = np.stack([10 + 30 * np.clip(ola, 0, 1), 18 + 25 * np.clip(ola, 0, 1), 32 + 20 * np.clip(ola, 0, 1)], -1)
    brillo = np.exp(-((xx - 330) / (60 + yy * 0.4)) ** 2) * np.clip(ola + 0.6, 0, 1.6) * (0.9 + 0.2 * math.sin(t * 13))
    mar += brillo[..., None] * np.array([210, 120, 40])
    img.paste(Image.fromarray(np.clip(mar, 0, 255).astype(np.uint8)), (0, 1000))
    img = img.convert("RGBA")
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(capa)
    dy = 6 * math.sin(t * 1.3)
    plataforma(dr, 560, 1040 + dy, 1.25, (6, 6, 9, 255))
    plataforma(dr, 930, 1010, 0.45, (20, 16, 22, 255))
    img.alpha_composite(capa)
    # llama del quemador
    fx, fy = 560 - 260 * 1.25, 1040 + dy - 470 * 1.25
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(gl)
    fl = 1 + 0.25 * math.sin(t * 17) + 0.15 * math.sin(t * 29)
    dg.ellipse((fx - 160 * fl, fy - 200 * fl, fx + 160 * fl, fy + 80), fill=(255, 120, 30, 120))
    gl = gl.filter(ImageFilter.GaussianBlur(50))
    dg = ImageDraw.Draw(gl)
    dg.polygon([(fx - 24, fy), (fx + 24, fy), (fx + 10 * math.sin(t * 9), fy - 140 * fl)], fill=(255, 210, 120, 255))
    dg.polygon([(fx - 12, fy), (fx + 12, fy), (fx + 6 * math.sin(t * 11), fy - 80 * fl)], fill=(255, 250, 220, 255))
    img.alpha_composite(gl)
    for k in range(9):                                     # luces de la plataforma
        lx, ly = 560 - 140 + k * 33, 1040 + dy - 245 * 1.25
        if (k + int(t * 2)) % 4:
            dr2 = ImageDraw.Draw(img)
            dr2.ellipse((lx - 4, ly - 4, lx + 4, ly + 4), fill=(255, 230, 160, 255))
    titulo(img, t, "PETRÓLEO", 330, 170, color=AMARILLO, aparece=0.1, f="negra",
           sub="ENORMES RESERVAS", sub_color=BLANCO)
    texto(img, (W / 2, 1880), "Imagen ilustrativa", ("normal", 26), fill=(200, 200, 200), sombra=4, alfa=0.7)
    return img.convert("RGB")


def p_stabroek(t, d):
    """41.8–45.4 s: hallazgos frente a la costa de Guyana (bloque Stabroek, ubicación aproximada)."""
    m = mapa()
    img, _ = m.render(-58.4, 6.9, 7.2 - 0.6 * t / d, t,
                      capas={"fronteras": 0.8, "zona": 0.45, "stabroek": rampa(t, 0.3, 0.7)},
                      etiquetas=[{"lon": -57.3, "lat": 7.8, "texto": "Bloque Stabroek", "fuente": ("fuerte", 40),
                                  "color": (255, 190, 70), "a": rampa(t, 0.6, 1.0)},
                                 {"lon": -57.3, "lat": 7.45, "texto": "(ubicación aproximada)", "fuente": ("media", 30),
                                  "a": rampa(t, 0.6, 1.0)},
                                 {"lon": -58.17, "lat": 6.80, "texto": "Georgetown", "punto": True, "r": 9,
                                  "fuente": ("media", 34), "ancla": "lm", "dx": 22, "a": rampa(t, 0.2, 0.5)},
                                 {"lon": -59.9, "lat": 5.2, "texto": "ESEQUIBO", "fuente": ("fuerte", 40),
                                  "color": (255, 200, 200)}],
                      nubes=0.1)
    img = img.convert("RGBA")
    etiqueta_caja(img, W / 2, 330, "2015: PRIMER GRAN HALLAZGO", (0, 0, 0, 190), AMARILLO, 50, rampa(t, 0.0, 0.3), "negra")
    etiqueta_caja(img, W / 2, 430, "frente a las costas de Guyana", (0, 0, 0, 160), BLANCO, 38, rampa(t, 0.2, 0.5), "media")
    return img.convert("RGB")


# ------------------------------------------------------------------ CIJ
@lru_cache(None)
def palacio():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = (10, 10, 16, 255)
    base = 1300
    d.rectangle((60, base - 360, 1020, base), fill=c)                     # cuerpo
    for x in range(80, 1000, 60):                                         # tejado inclinado
        d.polygon([(x, base - 360), (x + 60, base - 360), (x + 30, base - 430)], fill=c)
    d.rectangle((60, base - 420, 1020, base - 360), fill=c)
    d.rectangle((90, base - 700, 250, base - 360), fill=c)                # torre del reloj (izquierda)
    d.polygon([(80, base - 700), (260, base - 700), (170, base - 900)], fill=c)
    d.ellipse((130, base - 640, 210, base - 560), fill=(230, 200, 120, 255))
    d.rectangle((850, base - 560, 960, base - 360), fill=c)               # torre derecha
    d.polygon([(840, base - 560), (970, base - 560), (905, base - 700)], fill=c)
    for x in range(300, 820, 70):                                         # ventanas iluminadas
        for y in (base - 300, base - 180):
            d.rectangle((x, y, x + 34, y + 80), fill=(250, 200, 110, 255))
    d.rectangle((0, base, W, H), fill=(6, 6, 10, 255))
    return img


def p_cij(t, d):
    """45.4–49.2 s: Palacio de la Paz (La Haya), sede de la Corte Internacional de Justicia."""
    img = Image.fromarray(degradado(W, H, (20, 30, 70), (190, 110, 70)).astype(np.uint8)).convert("RGBA")
    p = palacio()
    z = 1.0 + 0.05 * t / d
    p2 = p.resize((int(W * z), int(H * z)), Image.BILINEAR)
    img.alpha_composite(p2, (-(p2.width - W) // 2, -(p2.height - H) // 2 + 120))
    titulo(img, t, "CORTE INTERNACIONAL", 330, 82, aparece=0.05)
    titulo(img, t, "DE JUSTICIA", 430, 82, aparece=0.2)
    etiqueta_caja(img, W / 2, 560, "La Haya · caso Guyana c. Venezuela", (0, 0, 0, 170), AMARILLO, 38, rampa(t, 0.5, 0.8))
    etiqueta_caja(img, W / 2, 1180, "CASO EN CURSO", (200, 30, 40, 220), BLANCO, 52, rampa(t, 1.3, 1.6), "negra")
    return img.convert("RGB")


# ------------------------------------------------------------------ pregunta y cierre
def p_pregunta(t, d):
    """49.2–52.2 s: ¿podrá Venezuela recuperar el Esequibo?"""
    img = fondo_bandera(t, 0.55).convert("RGBA")
    m = mapa()
    mp, _ = m.render(ZONA[0], ZONA[1], 9.5, t, capas={"zona": 0.7 + 0.3 * math.sin(t * 7), "zona_brillo": 1, "fronteras": 1},
                     nubes=0)
    mp = mp.resize((720, 1280)).convert("RGBA")
    mk = Image.new("L", (720, 1280), 0)
    ImageDraw.Draw(mk).rounded_rectangle((0, 0, 720, 1280), 40, fill=255)
    mp.putalpha(mk.point(lambda v: int(v * rampa(t, 0, 0.3))))
    img.alpha_composite(mp, (180, 420))
    s = 1 + 0.06 * math.sin(t * 5)
    texto(img, (W / 2, 1050), "?", ("negra", int(420 * s)), fill=AMARILLO, sombra=30, alfa=rampa(t, 0.5, 0.8),
          borde=6, color_borde=(0, 0, 0))
    titulo(img, t, "¿PODRÁ RECUPERARLO?", 290, 84, aparece=0.0)
    return img.convert("RGB")


def p_desenlace(t, d):
    """52.2–55.6 s: «El desenlace todavía está por conocerse»."""
    img = Image.fromarray(degradado(W, H, (10, 10, 14), (0, 0, 0)).astype(np.uint8)).convert("RGBA")
    m = mapa()
    mp, _ = m.render(ZONA[0], ZONA[1], 11 - 1.5 * t / d, t, capas={"zona": 0.6, "fronteras": 0.6}, nubes=0)
    a = np.asarray(mp).astype(np.float32) * 0.28
    img = Image.fromarray(a.astype(np.uint8)).convert("RGBA")
    titulo(img, t, "EL DESENLACE", 820, 120, aparece=0.0)
    titulo(img, t, "TODAVÍA ESTÁ", 960, 110, color=AMARILLO, aparece=1.4)
    titulo(img, t, "POR CONOCERSE", 1090, 110, color=AMARILLO, aparece=1.75)
    return img.convert("RGB")


def globo(img, cx, cy, r, a, t):
    d = ImageDraw.Draw(img)
    col = (255, 214, 10, int(255 * a))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=10)
    for k in range(3):
        f = math.cos(t * 1.5 + k * math.pi / 3)
        d.ellipse((cx - r * abs(f), cy - r, cx + r * abs(f), cy + r), outline=col, width=6)
    for la in (-0.5, 0, 0.5):
        y = cy + r * la
        hw = r * math.sqrt(1 - la * la)
        d.line((cx - hw, y, cx + hw, y), fill=col, width=6)


def p_final(t, d):
    """55.6–60 s: cierre con el nombre del canal."""
    img = fondo_bandera(t + 3, 0.62).convert("RGBA")
    a = rampa(t, 0.0, 0.35)
    globo(img, W / 2, 700, 150, a, t)
    titulo(img, t, "CURIOSIDADES", 1000, 112, aparece=0.15, f="negra")
    titulo(img, t, "DEL MUNDO", 1120, 112, color=AMARILLO, aparece=0.35, f="negra")
    etiqueta_caja(img, W / 2, 1330, "Síguenos para más", (255, 255, 255, 235), (10, 10, 10), 48, rampa(t, 0.9, 1.2), "negra")
    return img.convert("RGB")


# (inicio, función, efectos de imagen)  — el final de cada plano es el inicio del siguiente
PLANOS = [
    (0.0, p_gancho, {}),
    (3.6, p_km2, {}),
    (7.2, p_selva, {}),
    (9.8, p_anios, {"sepia": 0.4}),
    (12.4, p_tribunal, {"sepia": 0.9, "antiguo": True}),
    (15.8, p_mapa1899, {"sepia": 0.75, "antiguo": True}),
    (19.5, p_nulo, {}),
    (25.1, p_ginebra, {"sepia": 0.0, "byn": True, "antiguo": True}),
    (28.6, p_mesa, {"byn": True, "antiguo": True}),
    (31.4, p_posiciones, {}),
    (37.8, p_petroleo, {}),
    (41.4, p_stabroek, {}),
    (45.2, p_cij, {}),
    (49.1, p_pregunta, {}),
    (52.1, p_desenlace, {}),
    (55.4, p_final, {}),
]
