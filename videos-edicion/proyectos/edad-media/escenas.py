"""Planos del video de la Edad Media. Cada función recibe (t, d) — segundo dentro del plano y
duración — y devuelve una imagen RGB de W×H.

Las pinturas (dominio público) están en imagenes/; se animan con movimiento de cámara
(«Ken Burns») y encima se añaden niebla, brasas, destellos y títulos.
"""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from base import ease, ease_out, fuente, rampa, ruido, texto
from guion import H, W

IMAGENES = Path(__file__).parent / "imagenes"
ORO = (240, 196, 92)
CREMA = (245, 232, 200)
BLANCO = (250, 246, 238)
SANGRE = (200, 40, 30)


@lru_cache(None)
def pintura(nombre):
    """La pintura descargada si existe; si no, la ilustración dibujada con código."""
    ruta = IMAGENES / f"{nombre}.jpg"
    if ruta.exists():
        return Image.open(ruta).convert("RGB")
    from ilustraciones import ESCENAS
    return ESCENAS[nombre]().convert("RGB")


def ken_burns(nombre, t, d, foco=(0.5, 0.5), z=(1.0, 1.15), pan=(0.0, 0.0)):
    """Encuadre vertical 9:16 que se acerca (zoom) y se desplaza (pan) sobre la pintura."""
    img = pintura(nombre)
    iw, ih = img.size
    k = ease(t / d) if d > 0 else 0
    zoom = z[0] + (z[1] - z[0]) * k
    base_h = min(ih, iw * H / W)              # el recorte 9:16 más grande que cabe
    ch = base_h / zoom
    cw = ch * W / H
    cx = (foco[0] + pan[0] * (k - 0.5)) * iw
    cy = (foco[1] + pan[1] * (k - 0.5)) * ih
    cx = min(max(cx, cw / 2), iw - cw / 2)
    cy = min(max(cy, ch / 2), ih - ch / 2)
    return img.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


# ------------------------------------------------------------------ efectos
@lru_cache(None)
def capa_niebla():
    n = ruido(540, 1920, 51, 5, 3, 0.6)
    return np.clip((n - 0.4) * 2.2, 0, 1)


def niebla(img, t, fuerza=0.35, color=(220, 210, 190)):
    n = capa_niebla()
    off = int(t * 25) % 900
    a = n[off: off + 960] if off + 960 <= n.shape[0] else n[:960]
    capa = Image.new("RGBA", (W, H), color + (0,))
    capa.putalpha(Image.fromarray((a * 255 * fuerza).astype(np.uint8)).resize((W, H), Image.BILINEAR))
    img = img.convert("RGBA")
    img.alpha_composite(capa)
    return img


@lru_cache(None)
def particulas(semilla=3, n=90):
    rng = np.random.default_rng(semilla)
    return rng.random((n, 5))


def brasas(img, t, n=70, color=(255, 150, 50), semilla=3):
    """Brasas encendidas que suben por la pantalla."""
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for x0, y0, vel, tam, fase in particulas(semilla, n):
        y = H - ((y0 * H + t * (90 + 160 * vel)) % (H + 100))
        x = x0 * W + 40 * math.sin(t * (0.8 + vel) + fase * 6)
        r = 2 + 4 * tam
        brillo = 0.5 + 0.5 * math.sin(t * 7 + fase * 9)
        d.ellipse((x - r * 2.5, y - r * 2.5, x + r * 2.5, y + r * 2.5), fill=color + (int(40 * brillo),))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 220, 150, int(220 * brillo)))
    img = img.convert("RGBA")
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(1.2)))
    return img


def oscurecer_abajo(img, fuerza=0.75):
    """Degradado oscuro abajo y arriba para que se lean títulos y subtítulos."""
    g = np.ones((H, 1), np.float32)
    y = np.linspace(0, 1, H)[:, None]
    g *= 1 - fuerza * np.clip((y - 0.55) / 0.45, 0, 1) ** 1.3
    g *= 1 - 0.55 * np.clip((0.28 - y) / 0.28, 0, 1)
    a = np.asarray(img.convert("RGB")).astype(np.float32) * g[..., None]
    return Image.fromarray(a.astype(np.uint8))


def titulo(img, t, txt, y, tam=96, color=BLANCO, aparece=0.0, f="titulo", sub=None, sub_color=ORO, sub_tam=None):
    a = rampa(t, aparece, aparece + 0.25)
    if a <= 0:
        return img
    img = img.convert("RGBA")
    s = 1 + 0.18 * (1 - ease_out((t - aparece) / 0.35))
    texto(img, (W / 2, y), txt, (f, int(tam * s)), fill=color, sombra=16, alfa=a, borde=2, color_borde=(20, 10, 0))
    if sub:
        a2 = rampa(t, aparece + 0.25, aparece + 0.5)
        texto(img, (W / 2, y + tam * 0.95), sub, ("titulo_n", sub_tam or int(tam * 0.45)), fill=sub_color, sombra=10,
              alfa=a2, borde=1, color_borde=(20, 10, 0))
    return img


def tachado(img, t, txt, y, aparece, tacha):
    """Palabra que aparece y luego se tacha en rojo (sin electricidad, sin automóviles…)."""
    a = rampa(t, aparece, aparece + 0.2)
    if a <= 0:
        return img
    img = img.convert("RGBA")
    f = fuente("negra", 92)
    texto(img, (W / 2, y), txt, f, fill=BLANCO, sombra=12, alfa=a, borde=3, color_borde=(0, 0, 0))
    p = rampa(t, tacha, tacha + 0.18)
    if p > 0:
        w = f.getlength(txt) + 40
        d = ImageDraw.Draw(img)
        d.line((W / 2 - w / 2, y + 8, W / 2 - w / 2 + w * p, y - 8), fill=SANGRE + (255,), width=16)
    return img


# ------------------------------------------------------------------ planos
def p_gancho(t, d):
    img = ken_burns("partida", t, d, foco=(0.42, 0.45), z=(1.25, 1.05))
    img = niebla(oscurecer_abajo(img, 0.6), t, 0.25)
    img = brasas(img, t, 60)
    img = titulo(img, t, "¿CÓMO ERA", 330, 104, aparece=0.0)
    img = titulo(img, t, "REALMENTE VIVIR", 450, 92, aparece=0.25)
    img = titulo(img, t, "EN LA EDAD MEDIA?", 560, 92, color=ORO, aparece=0.5)
    return img.convert("RGB")


@lru_cache(None)
def fondo_vela():
    a = np.zeros((H, W, 3), np.float32)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt((x - W / 2) ** 2 + ((y - 1250) * 0.9) ** 2)
    luz = np.exp(-dist / 520)
    piedra = ruido(W, H, 61, 6, 5, 0.6)
    a += (np.array([60, 42, 25]) * (0.5 + piedra[..., None])) * luz[..., None]
    a += np.array([8, 6, 5])
    # mesa
    a[1460:] *= 0.55
    a[1460:1470] += 30
    return a


def p_vela(t, d):
    """Sin electricidad, sin automóviles y sin teléfonos: solo la luz de una vela."""
    parpadeo = 1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 31)
    a = fondo_vela() * parpadeo
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    dr = ImageDraw.Draw(img)
    cx = W / 2
    dr.rounded_rectangle((cx - 45, 1180, cx + 45, 1470), 10, fill=(225, 210, 180, 255))    # vela
    dr.rounded_rectangle((cx - 45, 1180, cx - 20, 1470), 10, fill=(190, 172, 140, 255))
    dr.ellipse((cx - 100, 1450, cx + 100, 1490), fill=(70, 55, 40, 255))                   # candelero
    dr.line((cx, 1180, cx, 1150), fill=(30, 20, 10, 255), width=5)
    llama = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(llama)
    oscila = 8 * math.sin(t * 9) + 4 * math.sin(t * 23)
    dl.ellipse((cx - 150, 950, cx + 150, 1250), fill=(255, 150, 40, 70))
    llama = llama.filter(ImageFilter.GaussianBlur(50))
    dl = ImageDraw.Draw(llama)
    dl.polygon([(cx - 22, 1150), (cx + 22, 1150), (cx + 14, 1120), (cx + oscila, 1030), (cx - 14, 1120)], fill=(255, 190, 80, 255))
    dl.polygon([(cx - 10, 1150), (cx + 10, 1150), (cx + oscila * 0.6, 1075)], fill=(255, 250, 220, 255))
    img.alpha_composite(llama)
    img = tachado(img, t, "ELECTRICIDAD", 380, 0.4, 1.4)
    img = tachado(img, t, "AUTOMÓVILES", 520, 2.9, 3.6)
    img = tachado(img, t, "TELÉFONOS", 660, 4.0, 4.7)
    return img.convert("RGB")


def plano_pintura(nombre, foco, z, pan=(0, 0), etiqueta=None, sub=None, y=330, tam=100, color=BLANCO,
                  efecto="niebla", aparece=0.1, f="titulo"):
    def plano(t, d):
        img = ken_burns(nombre, t, d, foco, z, pan)
        img = oscurecer_abajo(img, 0.55)
        if efecto in ("niebla", "ambos"):
            img = niebla(img, t, 0.22)
        if efecto in ("brasas", "ambos"):
            img = brasas(img, t)
        if etiqueta:
            img = titulo(img, t, etiqueta, y, tam, color=color, aparece=aparece, f=f, sub=sub)
        return img.convert("RGB")
    plano.__name__ = f"p_{nombre}"
    return plano


def p_destruccion(t, d):
    """476: la caída del Imperio romano de Occidente."""
    img = ken_burns("destruccion", t, d, foco=(0.40, 0.5), z=(1.15, 1.35), pan=(0.35, 0))
    img = brasas(niebla(oscurecer_abajo(img, 0.55), t, 0.3, (120, 110, 100)), t, 90)
    n = int(476 * ease_out(t / 1.3)) if t < 1.3 else 476
    img = titulo(img, t, f"AÑO {n}", 330, 140, color=ORO, aparece=0.0, sub="d. C.")
    img = titulo(img, t, "CAÍDA DEL IMPERIO", 560, 70, aparece=5.6)
    img = titulo(img, t, "ROMANO DE OCCIDENTE", 650, 70, color=(255, 120, 90), aparece=5.8)
    return img.convert("RGB")


@lru_cache(None)
def pergamino():
    n = ruido(W, H, 71, 6, 4, 0.6)
    a = np.array([214, 190, 140], np.float32) * (0.78 + 0.3 * n)[..., None]
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    borde = np.minimum(np.minimum(x, W - x), np.minimum(y, H - y))
    a *= (0.55 + 0.45 * np.clip(borde / 220, 0, 1))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def p_linea_tiempo(t, d):
    """476 → finales del siglo XV: casi mil años."""
    img = pergamino().copy().convert("RGBA")
    dr = ImageDraw.Draw(img)
    tinta = (60, 35, 15)
    x0, x1, y = 250, W - 250, 980
    p = ease_out(t / 1.6)
    dr.line((x0, y, x0 + (x1 - x0) * p, y), fill=tinta + (255,), width=10)
    for k, (x, a, b) in enumerate(((x0, "476", "Caída de Roma"), (x1, "S. XV", "Fin de la época"))):
        al = rampa(t, 0.1 + k * 1.4, 0.4 + k * 1.4)
        if al > 0:
            dr.ellipse((x - 26, y - 26, x + 26, y + 26), fill=(150, 30, 20, int(255 * al)))
            texto(img, (x, y - 110), a, ("titulo", 96), fill=tinta, sombra=0, alfa=al)
            texto(img, (x, y + 90), b, ("serif_b", 42), fill=tinta, sombra=0, alfa=al)
    img = titulo(img, t, "CASI 1000 AÑOS", 640, 100, color=(130, 25, 15), aparece=1.8)
    img = titulo(img, t, "LA EDAD MEDIA", 360, 80, color=tinta, aparece=0.0, f="titulo")
    return img.convert("RGB")


def p_piramide(t, d):
    """La sociedad medieval: grandes diferencias."""
    img = pergamino().copy().convert("RGBA")
    dr = ImageDraw.Draw(img)
    niveles = [("REY", (150, 30, 20)), ("NOBLES Y CLERO", (120, 70, 30)), ("CABALLEROS", (95, 80, 50)),
               ("CAMPESINOS", (70, 60, 45))]
    base_y, alto = 1560, 230
    for k, (nombre, col) in enumerate(niveles[::-1]):
        a = rampa(t, 0.3 + k * 0.55, 0.6 + k * 0.55)
        if a <= 0:
            continue
        y1 = base_y - k * alto
        y0 = y1 - alto + 14
        m1 = 470 - k * 105
        m0 = m1 - 105
        dr.polygon([(W / 2 - m1, y1), (W / 2 + m1, y1), (W / 2 + m0, y0), (W / 2 - m0, y0)],
                   fill=col + (int(235 * a),))
        texto(img, (W / 2, (y0 + y1) / 2), nombre, ("titulo", 54 if k < 2 else 44), fill=CREMA, sombra=0, alfa=a)
    img = titulo(img, t, "GRANDES", 330, 104, color=(60, 35, 15), aparece=0.0)
    img = titulo(img, t, "DIFERENCIAS", 450, 104, color=(150, 30, 20), aparece=0.2)
    return img.convert("RGB")


@lru_cache(None)
def astrolabio_capa():
    s = 900
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    oro, oro2 = (215, 170, 80, 255), (150, 110, 45, 255)
    d.ellipse((20, 20, s - 20, s - 20), outline=oro, width=22)
    d.ellipse((70, 70, s - 70, s - 70), outline=oro2, width=6)
    for k in range(72):
        a = k * math.pi / 36
        r0 = c - 70 - (22 if k % 6 == 0 else 10)
        d.line((c + math.cos(a) * (c - 70), c + math.sin(a) * (c - 70), c + math.cos(a) * r0, c + math.sin(a) * r0),
               fill=oro, width=4 if k % 6 == 0 else 2)
    for r in (120, 200, 280):
        d.ellipse((c - r, c - r * 0.8 + 40, c + r, c + r * 0.8 + 40), outline=oro2, width=3)
    d.line((c, 80, c, s - 80), fill=oro2, width=3)
    d.line((80, c, s - 80, c), fill=oro2, width=3)
    return img


@lru_cache(None)
def red_rete():
    s = 900
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    oro = (240, 200, 110, 255)
    d.ellipse((c - 300, c - 260, c + 220, c + 260), outline=oro, width=10)
    for k in range(9):
        a = k * 2 * math.pi / 9
        x, y = c + math.cos(a) * 250, c + math.sin(a) * 250
        d.line((c, c, x, y), fill=oro, width=5)
        d.polygon([(x, y - 18), (x + 12, y), (x, y + 18), (x - 12, y)], fill=oro)
    d.line((60, c, s - 60, c), fill=(250, 230, 170, 255), width=8)
    d.ellipse((c - 22, c - 22, c + 22, c + 22), fill=oro)
    return img


def p_ciencia(t, d):
    """Avances científicos: un astrolabio dorado girando."""
    img = Image.new("RGB", (W, H), (14, 10, 8)).convert("RGBA")
    brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(brillo).ellipse((W / 2 - 520, 520, W / 2 + 520, 1560), fill=(200, 140, 60, 70))
    img.alpha_composite(brillo.filter(ImageFilter.GaussianBlur(120)))
    base = astrolabio_capa()
    rete = red_rete().rotate(-t * 25, resample=Image.BICUBIC)
    a = base.copy()
    a.alpha_composite(rete)
    s = 0.95 + 0.05 * t / d
    a = a.resize((int(900 * s), int(900 * s)), Image.BICUBIC)
    img.alpha_composite(a, ((W - a.width) // 2, 1040 - a.height // 2))
    img = brasas(img, t, 40, (255, 200, 120), 7)
    img = titulo(img, t, "CIENCIA", 330, 110, color=ORO, aparece=0.0, sub="astrolabios · astronomía · medicina")
    return img.convert("RGB")


def p_final(t, d):
    img = ken_burns("regreso", 2.5 + t * 0.4, 6, foco=(0.55, 0.45), z=(1.2, 1.4))
    a = np.asarray(img).astype(np.float32) * 0.32
    img = Image.fromarray(a.astype(np.uint8))
    img = brasas(img, t, 80)
    img = titulo(img, t, "CURIOSIDADES", 860, 110, color=BLANCO, aparece=0.1, f="titulo")
    img = titulo(img, t, "DEL MUNDO", 990, 110, color=ORO, aparece=0.3, f="titulo")
    img = img.convert("RGBA")
    a2 = rampa(t, 0.9, 1.2)
    if a2 > 0:
        f = fuente("negra", 50)
        w = f.getlength("Síguenos para más")
        caja = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(caja).rounded_rectangle((W / 2 - w / 2 - 30, 1170, W / 2 + w / 2 + 30, 1260), 20,
                                               fill=ORO + (int(240 * a2),))
        img.alpha_composite(caja)
        texto(img, (W / 2, 1215), "Síguenos para más", f, fill=(25, 15, 5), sombra=0, alfa=a2)
    return img.convert("RGB")


def p_bienvenidos(t, d):
    img = ken_burns("accolade", t, d, foco=(0.5, 0.45), z=(1.12, 1.0))
    img = brasas(niebla(oscurecer_abajo(img, 0.55), t, 0.25), t, 70)
    img = titulo(img, t, "BIENVENIDOS A LA", 290, 64, aparece=0.0)
    img = titulo(img, t, "EDAD MEDIA", 400, 130, color=ORO, aparece=0.3)
    return img.convert("RGB")


def p_mil_anios(t, d):
    """Y esta es solo una pequeña parte… de una época que duró cerca de mil años."""
    img = ken_burns("regreso", t, d, foco=(0.5, 0.5), z=(1.0, 1.25), pan=(0.1, 0))
    img = brasas(niebla(oscurecer_abajo(img, 0.55), t, 0.25), t, 70)
    n = int(1000 * ease_out((t - 2.6) / 2.0)) if t > 2.6 else 0
    if t > 2.6:
        img = titulo(img, t, f"{n} AÑOS", 360, 150, color=ORO, aparece=2.6, sub="de historia")
    return img.convert("RGB")


# (inicio, función, efectos de imagen) — el final de cada plano es el inicio del siguiente
PLANOS = [
    (0.0, p_gancho, {}),
    (3.6, p_vela, {}),
    (9.3, plano_pintura("schinkel", (0.45, 0.45), (1.05, 1.3), (0.2, 0), "CASTILLOS", "enormes fortalezas", y=330), {}),
    (12.5, plano_pintura("carlomagno", (0.5, 0.35), (1.0, 1.18), (0, 0.1), "REYES", "poderosos", y=330), {}),
    (14.3, plano_pintura("godspeed", (0.5, 0.42), (1.0, 1.15), (0, 0.1), "CABALLEROS", "listos para la guerra", y=300, efecto="brasas"), {}),
    (17.5, p_bienvenidos, {}),
    (20.0, p_destruccion, {}),
    (28.7, p_linea_tiempo, {}),
    (33.2, p_piramide, {}),
    (37.7, plano_pintura("enero", (0.5, 0.62), (1.05, 1.3), (0, -0.1), "RIQUEZAS", "reyes y nobles", y=330, color=ORO), {}),
    (41.9, plano_pintura("junio", (0.5, 0.75), (1.1, 1.3), (0.15, 0), "EL CAMPO", "trabajar para sobrevivir", y=330), {}),
    (46.1, plano_pintura("octubre", (0.5, 0.35), (1.3, 1.6), (0, -0.05), "FORTALEZAS", "residencia y defensa", y=330), {}),
    (51.2, plano_pintura("torneo", (0.5, 0.62), (1.05, 1.25), (0, 0), "ENTRENAMIENTO", "torneos y justas", y=300, tam=86), {}),
    (53.6, plano_pintura("san_romano", (0.45, 0.5), (1.1, 1.35), (0.3, 0), "GUERRAS", "que cambiaban reinos", y=330, color=(255, 120, 90), efecto="brasas"), {"sacudida": True}),
    (57.8, plano_pintura("ciudad", (0.35, 0.55), (1.1, 1.3), (0.3, 0), "MERCADOS", "comercio y vida en la ciudad", y=330, aparece=3.0), {"amanecer": True}),
    (62.6, plano_pintura("universidad", (0.5, 0.5), (1.05, 1.2), (0, 0), "UNIVERSIDADES", None, y=330, tam=86), {}),
    (63.8, p_ciencia, {}),
    (65.5, plano_pintura("catedral", (0.5, 0.45), (1.05, 1.25), (0, 0.1), "CATEDRALES", "grandes construcciones", y=330, tam=90), {}),
    (67.4, plano_pintura("kells", (0.5, 0.45), (1.05, 1.2), (0, 0), "CULTURA", "arte y manuscritos", y=330, color=ORO), {}),
    (69.0, p_mil_anios, {}),
    (75.6, p_final, {}),
]
