"""Mini documental vertical (1080x1920, 30 fps) «¿Elon Musk está a punto de hacer volar a Tesla?».

Uso: python3 montaje.py [--prueba INICIO FIN] [--procesos 4] [--salida archivo.mp4]

Necesita en material/: voz.wav (narración), propulsor.wav, propulsor2.wav, electrico.wav, impacto.wav
(efectos de ElevenLabs) e img/*.jpg (fotos: u* = imágenes de la demostración de octubre de 2026,
c*/d*/e* = Wikimedia Commons, ver README.md). La música y los barridos se sintetizan aquí.
"""
import argparse
import json
import subprocess
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal

AQUI = Path(__file__).parent
MAT = AQUI / "material"
W, H, FPS, SR = 1080, 1920, 30, 48000
VO = 0.35            # la voz empieza a los 0,35 s
MARCA = 112.3        # inicio del cierre (tiempo absoluto)
TOTAL = 117.0
CIAN = (70, 224, 255)
ROJO = (255, 70, 70)
T_ELEVA = 61.369     # «elevándose» (tiempo de voz): golpe de la maniobra

# ----------------------------------------------------------------- tipografías
def montserrat(tam, peso="ExtraBold"):
    f = ImageFont.truetype(str(AQUI / "fuentes/Montserrat.ttf"), tam)
    f.set_variation_by_name(peso)
    return f


def cinzel(tam):
    return ImageFont.truetype(str(AQUI / "fuentes/cinzel-latin-700-normal.woff"), tam)


# ----------------------------------------------------------------- planos
# (inicio en tiempo de voz, imagen, modo, (cx, cy, zoom) inicial, (cx, cy, zoom) final, rótulo)
# cover: la foto llena la pantalla; tarjeta: la foto entera a lo ancho sobre un fondo desenfocado
# (para las imágenes pequeñas de la demostración, que no aguantan más ampliación).
EVENTO = "Demostración de Tesla · 15 oct. 2026"
PROTO = "Prototipo presentado en 2017 (diseño anterior)"
PLANOS = [
    (-0.35, "u2", "tarjeta", (0.50, 0.45, 1.00), (0.50, 0.45, 1.22), EVENTO),
    (1.70, "u3", "tarjeta", (0.45, 0.40, 1.05), (0.45, 0.32, 1.35), EVENTO),
    (3.60, "c09", "tarjeta", (0.50, 0.50, 1.00), (0.45, 0.55, 1.15), "Roadster de Musk en el espacio · SpaceX, 2018"),
    (6.30, "d02", "cover", (0.50, 0.55, 1.05), (0.50, 0.58, 1.20), PROTO),
    (8.20, "u1", "tarjeta", (0.55, 0.35, 1.05), (0.60, 0.30, 1.40), EVENTO),
    (11.50, "c05", "cover", (0.50, 0.60, 1.00), (0.50, 0.50, 1.15), "Lanzamiento de Starship · SpaceX"),
    (14.80, "c00", "cover", (0.50, 0.35, 1.00), (0.50, 0.30, 1.20), "Elon Musk"),
    (18.45, "u3", "tarjeta", (0.45, 0.45, 1.00), (0.45, 0.45, 1.12), None),
    (21.70, "d00", "cover", (0.30, 0.60, 1.00), (0.62, 0.60, 1.05), PROTO),
    (24.60, "d01", "cover", (0.35, 0.60, 1.05), (0.65, 0.60, 1.10), PROTO),
    (28.20, "c04", "cover", (0.50, 0.55, 1.00), (0.50, 0.45, 1.20), "Lanzamiento de Falcon Heavy · SpaceX, 2018"),
    (30.60, "c12", "cover", (0.35, 0.50, 1.00), (0.60, 0.45, 1.05), "Propulsores de Falcon Heavy aterrizando · 2018"),
    (32.00, "c01", "cover", (0.50, 0.40, 1.00), (0.50, 0.35, 1.15), "Elon Musk"),
    (34.35, "c06", "cover", (0.50, 0.65, 1.00), (0.50, 0.55, 1.25), "Encendido de Starship · SpaceX"),
    (36.80, "d06", "cover", (0.45, 0.45, 1.00), (0.40, 0.42, 1.25), "Propulsores de gas frío de un cohete Falcon 9"),
    (39.40, "d07", "cover", (0.50, 0.45, 1.00), (0.50, 0.45, 1.20), "Propulsores de gas frío de un cohete Falcon 9"),
    (41.40, "u2", "tarjeta", (0.50, 0.60, 1.10), (0.50, 0.68, 1.45), EVENTO),
    (43.20, "d03", "cover", (0.50, 0.60, 1.05), (0.50, 0.62, 1.25), PROTO),
    (46.00, "d09", "cover", (0.40, 0.55, 1.00), (0.60, 0.55, 1.05), PROTO),
    (47.50, "c02", "cover", (0.50, 0.40, 1.00), (0.50, 0.35, 1.18), "Elon Musk"),
    (50.10, "d10", "cover", (0.50, 0.50, 1.00), (0.50, 0.45, 1.15), PROTO),
    (51.30, "e00", "cover", (0.45, 0.55, 1.00), (0.55, 0.55, 1.10), "AeroMobil: auto volador de otra empresa (2014)"),
    # momento impactante: la maniobra
    (54.20, "u2", "tarjeta", (0.50, 0.45, 1.00), (0.50, 0.45, 1.15), EVENTO),
    (56.80, "u1", "tarjeta", (0.50, 0.40, 1.00), (0.55, 0.35, 1.20), EVENTO),
    (58.30, "u3", "tarjeta", (0.45, 0.45, 1.00), (0.45, 0.40, 1.25), EVENTO),
    (60.50, "u2", "tarjeta", (0.50, 0.50, 1.20), (0.50, 0.55, 1.40), None),
    (T_ELEVA, "u1", "tarjeta", (0.62, 0.30, 1.55), (0.62, 0.30, 1.85), None),
    (63.20, "u3", "tarjeta", (0.45, 0.35, 1.30), (0.45, 0.42, 1.05), EVENTO),
    (64.50, "c05", "cover", (0.50, 0.45, 1.15), (0.50, 0.55, 1.00), "Lanzamiento de Starship · SpaceX"),
    (67.80, "u1", "tarjeta", (0.50, 0.45, 1.00), (0.50, 0.45, 1.15), EVENTO),
    (71.90, "c00", "cover", (0.50, 0.05, 1.05), (0.50, 0.05, 1.20), "Elon Musk"),
    (76.80, "d01", "cover", (0.60, 0.60, 1.10), (0.40, 0.60, 1.00), PROTO),
    (80.20, "d00", "cover", (0.55, 0.55, 1.20), (0.45, 0.55, 1.05), PROTO),
    (85.50, "u2", "tarjeta", (0.50, 0.45, 1.05), (0.50, 0.45, 1.20), EVENTO),
    (88.10, "d03", "cover", (0.50, 0.55, 1.20), (0.50, 0.55, 1.05), PROTO),
    (91.60, "e01", "cover", (0.35, 0.55, 1.00), (0.55, 0.55, 1.05), "AeroMobil 4.0: auto volador de otra empresa"),
    (95.50, "c04", "cover", (0.50, 0.40, 1.15), (0.50, 0.55, 1.00), "Lanzamiento de Falcon Heavy · SpaceX, 2018"),
    (98.50, "d09", "cover", (0.60, 0.55, 1.10), (0.40, 0.55, 1.00), PROTO),
    (101.10, "c09", "tarjeta", (0.35, 0.40, 1.25), (0.50, 0.50, 1.00), "Roadster de Musk en el espacio · SpaceX, 2018"),
    (104.40, "u1", "tarjeta", (0.50, 0.45, 1.00), (0.55, 0.40, 1.20), EVENTO),
    (MARCA - VO, "u2", "marca", None, None, None),
]
FUNDIDO = 0.35
CORTES_SECOS = {T_ELEVA, 60.50, 63.20}   # cortes sin fundido en la maniobra

# ----------------------------------------------------------------- subtítulos
CAMBIOS = {("dos", "mil", "veintiséis,"): "2026,", ("dos", "mil", "veintiocho."): "2028."}
BLOQUES = [
    "¿Elon Musk", "está a punto", "de hacer volar", "a Tesla?",
    "¿Te imaginas", "conducir un automóvil", "que no solo pueda", "correr por las carreteras...",
    "sino que también", "sea capaz", "de elevarse por el aire?",
    "Aunque parezca", "sacado de una película", "de ciencia ficción,", "Elon Musk",
    "está llevando esta idea", "a otro nivel.",
    "En octubre de 2026,", "una demostración", "del esperado", "Tesla Roadster", "de nueva generación",
    "llamó la atención", "por sus sorprendentes", "movimientos.",
    "El proyecto", "está relacionado", "con la tecnología", "de SpaceX,", "la compañía aeroespacial", "de Musk.",
    "Pero aquí viene", "lo más interesante...", "se ha hablado", "de incorporar", "pequeños propulsores",
    "que utilizarían", "gas a presión", "para generar impulso.",
    "Esta tecnología", "podría permitir", "movimientos extraordinarios...", "aunque todavía", "no significa",
    "que tengamos", "un automóvil convencional", "capaz de volar", "libremente por la ciudad.",
    "Durante la demostración,", "el vehículo,", "sin nadie al volante,", "mostró una maniobra", "espectacular",
    "sobre una rampa...", "elevándose brevemente", "antes de aterrizar.",
    "Las imágenes", "despertaron", "una enorme pregunta:", "¿estamos ante el comienzo", "de una nueva era",
    "para los automóviles?",
    "Elon Musk", "ha hablado de producir", "el nuevo Roadster", "en 2028.", "Sin embargo,", "esa fecha",
    "todavía podría cambiar...", "y aún quedan", "importantes desafíos", "de ingeniería,", "seguridad y regulación.",
    "Además,", "hay una gran diferencia", "entre un automóvil", "que realiza", "una maniobra aérea", "controlada...",
    "y uno que puede volar", "de forma segura", "por encima del tráfico.",
    "Por ahora,", "el proyecto sigue", "generando curiosidad", "y expectativas", "en todo el mundo.",
    "¿Será este", "el primer paso", "hacia el futuro", "que imaginábamos", "en las películas...",
    "o tendremos", "que esperar", "muchos años más?",
    "Síguenos en", "Curiosidades del Mundo", "para descubrir más.",
]
DESTACAR = {"ELON", "MUSK", "TESLA", "VOLAR", "ELEVARSE", "AIRE", "2026", "ROADSTER", "SPACEX", "PROPULSORES",
            "GAS", "PRESIÓN", "SIN", "VOLANTE", "RAMPA", "ELEVÁNDOSE", "ATERRIZAR", "2028", "CAMBIAR",
            "INGENIERÍA", "SEGURIDAD", "REGULACIÓN", "CONTROLADA", "FUTURO", "CURIOSIDADES", "MUNDO",
            "NUEVA", "ERA", "LIBREMENTE", "CIENCIA", "FICCIÓN"}


def limpio(p):
    return p.strip("¿?¡!.,:;…")


def bloques_subtitulos():
    pal = json.loads((AQUI / "palabras.json").read_text())
    out, i = [], 0
    while i < len(pal):
        for clave, texto in CAMBIOS.items():
            n = len(clave)
            if tuple(p["t"] for p in pal[i:i + n]) == clave:
                out.append({"t": texto, "ini": pal[i]["ini"], "fin": pal[i + n - 1]["fin"]})
                i += n
                break
        else:
            out.append(dict(pal[i]))
            i += 1
    bloques, i = [], 0
    for texto in BLOQUES:
        n = len(texto.split())
        assert [p["t"] for p in out[i:i + n]] == texto.split(), (texto, out[i:i + n])
        bloques.append(out[i:i + n])
        i += n
    assert i == len(out), out[i:]
    res = []
    for k, b in enumerate(bloques):
        ini = b[0]["ini"] - 0.06
        fin = b[-1]["fin"] + 0.35
        if k + 1 < len(bloques):
            sig = bloques[k + 1][0]["ini"] - 0.06
            fin = sig if sig - b[-1]["fin"] < 0.45 else min(fin, sig)
        palabras = [x["t"].replace("...", "").upper() for x in b]
        res.append((ini + VO, min(fin + VO, MARCA - 0.05), palabras))
    return res


SUBS = bloques_subtitulos()
F_SUB = montserrat(84)


@lru_cache(maxsize=None)
def imagen_subtitulo(k):
    palabras = SUBS[k][2]
    trazo = 9
    fuente = F_SUB
    esp = fuente.getlength(" ")
    anchos = [fuente.getlength(p) for p in palabras]
    lineas, linea, ancho = [], [], 0
    for p, a in zip(palabras, anchos):
        if linea and ancho + esp + a > 900:
            lineas.append(linea)
            linea, ancho = [], 0
        ancho += (esp if linea else 0) + a
        linea.append((p, a))
    lineas.append(linea)
    alto_l = 102
    im = Image.new("RGBA", (W, alto_l * len(lineas) + 2 * trazo + 20), (0, 0, 0, 0))
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sombra)
    for n, linea in enumerate(lineas):
        total = sum(a for _, a in linea) + esp * (len(linea) - 1)
        x = (W - total) / 2
        y = trazo + n * alto_l
        for p, a in linea:
            color = CIAN if limpio(p) in DESTACAR else (255, 255, 255)
            ds.text((x + 4, y + 8), p, font=fuente, fill=(0, 0, 0, 170), stroke_width=trazo, stroke_fill=(0, 0, 0, 170))
            d.text((x, y), p, font=fuente, fill=color, stroke_width=trazo, stroke_fill=(0, 0, 0))
            x += a + esp
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(sombra, im)


# ----------------------------------------------------------------- imágenes
@lru_cache(maxsize=None)
def foto(nombre):
    im = Image.open(MAT / "img" / f"{nombre}.jpg").convert("RGB")
    if im.width < 1100:  # imágenes pequeñas: ampliar con buen filtro y algo de nitidez
        s = 1100 / im.width
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    a = np.asarray(im).astype(np.float32) / 255
    # gradación tecnológica: contraste, sombras frías y luces cálidas suaves
    a = np.clip((a - 0.5) * 1.12 + 0.5, 0, 1)
    lum = a.mean(axis=2, keepdims=True)
    a = a + (1 - lum) * np.array([-0.025, 0.005, 0.04]) + lum * np.array([0.02, 0.0, -0.02])
    sat = 1.08
    a = lum + (a - lum) * sat
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


@lru_cache(maxsize=None)
def fondo_desenfocado(nombre):
    im = foto(nombre)
    s = max(W / im.width, H / im.height) * 1.1
    im = im.resize((int(im.width * s / 4), int(im.height * s / 4)), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(9)).resize((int(im.width * 4), int(im.height * 4)), Image.BICUBIC)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return np.asarray(im.crop((x, y, x + W, y + H))).astype(np.float32) * 0.45


def vista(im, ow, oh, cx, cy, zoom):
    s = max(ow / im.width, oh / im.height) * zoom
    vw, vh = ow / s, oh / s
    x0 = np.clip(cx * im.width - vw / 2, 0, im.width - vw)
    y0 = np.clip(cy * im.height - vh / 2, 0, im.height - vh)
    return np.asarray(im.transform((ow, oh), Image.AFFINE, (1 / s, 0, x0, 0, 1 / s, y0),
                                   resample=Image.BICUBIC)).astype(np.float32)


def suave(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def plano(k, t):
    ini, nombre, modo, a, b, _ = PLANOS[k]
    ini += VO
    fin = (PLANOS[k + 1][0] + VO) if k + 1 < len(PLANOS) else TOTAL
    if modo == "marca":
        return cuadro_marca(t - ini)
    u = (t - ini + FUNDIDO) / (fin - ini + 2 * FUNDIDO)
    e = 0.15 + 0.7 * u + 0.15 * suave(u)
    cx, cy, z = (a[i] + (b[i] - a[i]) * e for i in range(3))
    im = foto(nombre)
    if modo == "cover":
        return vista(im, W, H, cx, cy, z)
    base = fondo_desenfocado(nombre).copy()
    tw = W
    th = int(min(tw * im.height / im.width, 1250))
    fr = vista(im, tw, th, cx, cy, z)
    y = (H - th) // 2 - 120
    # bordes superior e inferior fundidos con el fondo
    m = np.ones((th, 1, 1), np.float32)
    r = 60
    m[:r, 0, 0] = np.linspace(0, 1, r)
    m[-r:, 0, 0] = np.linspace(1, 0, r)
    base[y:y + th] = base[y:y + th] * (1 - m) + fr * m
    return base


# ----------------------------------------------------------------- textos grandes
def texto_grande(base, lineas, dt, y0, colores=None, dur=None):
    """Bloque de texto que aparece deslizándose (fechas, datos clave)."""
    ap = suave(dt / 0.35)
    if dur is not None:
        ap *= 1 - suave((dt - dur + 0.3) / 0.3)
    if ap <= 0:
        return
    y = y0
    for n, (texto, tam, peso) in enumerate(lineas):
        f = montserrat(tam, peso)
        col = colores[n] if colores else (255, 255, 255)
        im = Image.new("RGBA", (W, int(tam * 1.4)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text(((W - f.getlength(texto)) / 2, 0), texto, font=f, fill=col + (255,), stroke_width=max(3, tam // 16),
               stroke_fill=(0, 0, 0))
        pegar(base, im, int(-60 * (1 - ap)) * (1 if n % 2 else -1), y, ap)
        y += int(tam * 1.25)


def lista_desafios(base, t):
    """INGENIERÍA · SEGURIDAD · REGULACIÓN, sincronizado con la voz."""
    items = [("INGENIERÍA", 82.33), ("SEGURIDAD", 83.29), ("REGULACIÓN", 84.17)]
    f = montserrat(64, "Black")
    for n, (txt, tv) in enumerate(items):
        dt = t - (tv + VO)
        ap = suave(dt / 0.25) * (1 - suave((t - (85.4 + VO)) / 0.3))
        if ap <= 0:
            continue
        im = Image.new("RGBA", (W, 110), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        tw = f.getlength(txt) + 120
        x = (W - tw) / 2
        d.rounded_rectangle((x, 8, x + tw, 100), radius=18, fill=(0, 0, 0, 165), outline=CIAN + (255,), width=4)
        d.text((x + 60, 18), txt, font=f, fill=(255, 255, 255, 255))
        pegar(base, im, 0, 420 + n * 130, ap)


# ----------------------------------------------------------------- cierre
def cuadro_marca(dt):
    fondo = fondo_desenfocado("u2") * (0.8 - 0.3 * suave(dt / 3))
    im = Image.fromarray(np.clip(fondo, 0, 255).astype(np.uint8)).convert("RGBA")
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f1, f2 = cinzel(100), cinzel(76)
    ap = suave((dt - 0.2) / 0.9)
    sep = int(22 * (1 - ap))
    yc = 800
    for texto, f, y in (("CURIOSIDADES", f1, yc - 140), ("DEL MUNDO", f2, yc + 20)):
        anchos = [f.getlength(c) for c in texto]
        total = sum(anchos) + sep * (len(texto) - 1)
        x = (W - total) / 2
        for c, aw in zip(texto, anchos):
            d.text((x, y), c, font=f, fill=(255, 255, 255, int(255 * ap)), stroke_width=2,
                   stroke_fill=(0, 0, 0, int(160 * ap)))
            x += aw + sep
    l = suave((dt - 0.6) / 0.8) * 330
    for y in (yc - 175, yc + 140):
        d.rectangle((W / 2 - l, y, W / 2 + l, y + 4), fill=CIAN + (230,))
    ap2 = suave((dt - 1.2) / 0.5)
    if ap2 > 0:
        f3 = montserrat(50, "Black")
        s = "SÍGUENOS"
        bw = f3.getlength(s) + 110
        esc = 0.85 + 0.15 * ap2 + 0.03 * np.sin(max(dt - 1.7, 0) * 5) * (dt > 1.7)
        bx, by = W / 2 - bw * esc / 2, yc + 230
        d.rounded_rectangle((bx, by, bx + bw * esc, by + 100 * esc), radius=int(50 * esc), fill=ROJO + (int(255 * ap2),))
        f3b = montserrat(int(50 * esc), "Black")
        d.text((W / 2 - f3b.getlength(s) / 2, by + 20 * esc), s, font=f3b, fill=(255, 255, 255, int(255 * ap2)))
        f4 = montserrat(38, "SemiBold")
        s2 = "para más curiosidades cada semana"
        d.text(((W - f4.getlength(s2)) / 2, by + 135), s2, font=f4, fill=(255, 255, 255, int(220 * ap2)))
    im = Image.alpha_composite(im, capa)
    return np.asarray(im.convert("RGB")).astype(np.float32)


# ----------------------------------------------------------------- capas
F_ROT = montserrat(36, "SemiBold")


@lru_cache(maxsize=None)
def imagen_rotulo(texto):
    pad = 20
    tw = int(F_ROT.getlength(texto))
    im = Image.new("RGBA", (tw + 2 * pad + 14, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, 69), radius=14, fill=(0, 0, 0, 160))
    d.rectangle((0, 12, 6, 57), fill=CIAN + (255,))
    d.text((pad + 8, 12), texto, font=F_ROT, fill=(255, 255, 255, 240))
    return im


@lru_cache(maxsize=None)
def marca_agua():
    f = montserrat(28, "Bold")
    s = "CURIOSIDADES DEL MUNDO"
    im = Image.new("RGBA", (int(f.getlength(s)) + 60, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 15, 22, 33), outline=CIAN + (255,), width=3)
    d.line((13, 15, 13, 33), fill=CIAN + (255,), width=2)
    d.line((4, 24, 22, 24), fill=CIAN + (255,), width=2)
    d.text((34, 8), s, font=f, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 200))
    return im


def pegar(base, capa, x, y, alfa=1.0):
    a = np.asarray(capa).astype(np.float32)
    h, w = a.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    a = a[y0 - y:y1 - y, x0 - x:x1 - x]
    m = a[..., 3:4] / 255 * alfa
    base[y0:y1, x0:x1] = base[y0:y1, x0:x1] * (1 - m) + a[..., :3] * m


yy, xx = np.mgrid[0:H, 0:W]
VIÑETA = np.clip(1 - 0.5 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2), 0.4, 1)[..., None]
VIÑETA = VIÑETA.astype(np.float32)
DEGRADADO = (1 - 0.45 * np.clip((yy - H * 0.55) / (H * 0.45), 0, 1))[..., None].astype(np.float32)
LINEAS = (1 - 0.035 * (yy % 4 < 1))[..., None].astype(np.float32)   # leve textura de pantalla
rng = np.random.default_rng(7)
GRANO = [rng.normal(0, 3.0, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
del yy, xx


def indice_plano(t):
    k = 0
    for i, p in enumerate(PLANOS):
        if p[0] + VO - (0 if p[0] in CORTES_SECOS else FUNDIDO / 2) <= t:
            k = i
    return k


def cuadro(n):
    t = n / FPS
    k = indice_plano(t)
    ini_k = PLANOS[k][0] + VO
    img = plano(k, t)
    if k > 0 and PLANOS[k][0] not in CORTES_SECOS and t < ini_k + FUNDIDO / 2:
        m = suave((t - (ini_k - FUNDIDO / 2)) / FUNDIDO)
        img = plano(k - 1, t) * (1 - m) + img * m
    marca = PLANOS[k][2] == "marca"
    # sacudida y destello en la maniobra
    te = T_ELEVA + VO
    if te <= t < te + 0.6:
        dt = t - te
        amp = 18 * np.exp(-dt * 7)
        dx, dy = int(amp * np.sin(dt * 90)), int(amp * np.cos(dt * 70))
        img = np.roll(img, (dy, dx), axis=(0, 1))
        img = img + 255 * np.exp(-dt * 12) * 0.85
    if not marca:
        img = img * VIÑETA * DEGRADADO * LINEAS
    img *= suave(t / 0.25)
    # rótulo del plano
    rot = PLANOS[k][5]
    if rot and not marca:
        dt = t - ini_k
        fin_k = PLANOS[k + 1][0] + VO
        ap = suave((dt - 0.25) / 0.35) * (1 - suave((t - (fin_k - 0.4)) / 0.3))
        if ap > 0:
            pegar(img, imagen_rotulo(rot), 50 - int(30 * (1 - ap)), 230, ap)
    # textos grandes con datos verificados
    if 18.45 + VO <= t < 21.6 + VO:
        texto_grande(img, [("15 · OCTUBRE · 2026", 76, "Black"), ("McGregor, Texas (EE. UU.)", 44, "SemiBold")],
                     t - (18.5 + VO), 470, [CIAN, (255, 255, 255)], 3.1)
    if 57.0 + VO <= t < 58.3 + VO:
        texto_grande(img, [("SIN CONDUCTOR", 92, "Black")], t - (57.0 + VO), 470, [ROJO], 1.3)
    if 72.4 + VO <= t < 80.1 + VO:
        texto_grande(img, [("PRODUCCIÓN PREVISTA", 52, "Bold"), ("2028", 150, "Black"),
                           ("Fecha no garantizada", 44, "SemiBold")],
                     t - (72.4 + VO), 330, [(255, 255, 255), CIAN, (255, 200, 200)], 7.7)
    if 82.0 + VO <= t < 85.8 + VO:
        lista_desafios(img, t)
    if 90.0 + VO <= t < 95.4 + VO:
        texto_grande(img, [("MANIOBRA BREVE ≠ VOLAR", 62, "Black"), ("sobre el tráfico", 50, "Bold")],
                     t - (90.0 + VO), 470, [(255, 255, 255), CIAN], 5.4)
    # subtítulos
    for k2, (si, sf_, _) in enumerate(SUBS):
        if si <= t < sf_:
            dt = t - si
            esc = 0.88 + 0.12 * suave(dt / 0.12) + 0.025 * np.sin(min(dt / 0.2, 1) * np.pi)
            sub = imagen_subtitulo(k2)
            if abs(esc - 1) > 0.002:
                sub = sub.resize((int(sub.width * esc), int(sub.height * esc)), Image.BICUBIC)
            ap = suave(dt / 0.08) * (1 - suave((t - (sf_ - 0.08)) / 0.08))
            pegar(img, sub, (W - sub.width) // 2, 1330 - sub.height // 2, ap)
    # marca de agua
    if not marca:
        wm = marca_agua()
        pegar(img, wm, W - wm.width - 40, 140, 0.75)
    g = GRANO[n % len(GRANO)]
    img = img + np.repeat(np.repeat(g, 2, 0), 2, 1)
    return np.clip(img, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------- audio
def nota(f):
    return 440.0 * 2 ** ((f - 69) / 12)


def adsr(n, a, r):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def pasa_bajos(x, fc, orden=2):
    b, a = signal.butter(orden, fc / (SR / 2))
    return signal.lfilter(b, a, x)


def reverb(x, seg=2.8, mezcla=0.35, semilla=1):
    r = np.random.default_rng(semilla)
    n = int(seg * SR)
    ir = r.normal(0, 1, n) * np.exp(-np.linspace(0, 7, n))
    ir = pasa_bajos(ir, 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - mezcla) + signal.fftconvolve(x, ir)[:len(x)] * mezcla * 2.2


def musica(n):
    """Música cinematográfica tecnológica: colchón de sintetizador, bajo pulsante, arpegio y timbales."""
    t = np.arange(n) / SR
    r = np.random.default_rng(11)
    te = T_ELEVA + VO
    # progresión en do sostenido menor (i - VI - III - VII), un acorde cada 4,8 s (2 compases a 100 ppm)
    acordes = [(49, 52, 56, 61), (45, 49, 52, 57), (52, 56, 59, 64), (47, 51, 54, 59)]
    dur = 4.8
    beat = 0.6
    pad = np.zeros(n)
    bajo = np.zeros(n)
    arp = np.zeros(n)
    inten = np.interp(t, [0, 3.5, 18, 34, 50, 53.5, te - 0.1, te + 0.2, te + 3, 70, 95, 108, MARCA, MARCA + 0.5, TOTAL],
                      [0.55, 0.6, 0.65, 0.75, 0.8, 0.9, 1.0, 1.0, 0.85, 0.7, 0.65, 0.75, 0.6, 0.0, 0.0])
    i = 0
    while i * dur < MARCA:
        ac = acordes[i % len(acordes)]
        s0, s1 = int(i * dur * SR), min(n, int(((i + 1) * dur + 1.0) * SR))
        tt = np.arange(s1 - s0) / SR
        env = adsr(s1 - s0, 1.0, 1.6)
        for m in ac[1:]:
            for det in (-0.10, 0.0, 0.09):
                f = nota(m + 12) * 2 ** (det / 12)
                fase = r.uniform(0, 2 * np.pi)
                pad[s0:s1] += env * sum(np.sin(2 * np.pi * f * h * tt + fase * h) / h ** 1.4 for h in range(1, 8)) * 0.04
        # bajo en corcheas con envolvente pulsante
        fb = nota(ac[0] - 12)
        pulso = 0.55 + 0.45 * np.exp(-((tt % (beat / 2)) / 0.08))
        bajo[s0:s1] += env * pulso * (np.sin(2 * np.pi * fb * tt) + 0.5 * np.sign(np.sin(2 * np.pi * fb * tt)) * 0.3) * 0.2
        # arpegio en semicorcheas
        notas = [ac[1] + 24, ac[2] + 24, ac[3] + 24, ac[2] + 36, ac[3] + 24, ac[2] + 24]
        for j in range(int(dur / (beat / 4))):
            p0 = int((i * dur + j * beat / 4) * SR)
            if p0 >= n:
                break
            f = nota(notas[j % len(notas)])
            ln = min(int(0.5 * SR), n - p0)
            tp = np.arange(ln) / SR
            onda = np.sign(np.sin(2 * np.pi * f * tp)) * 0.3 + np.sin(2 * np.pi * f * tp)
            arp[p0:p0 + ln] += onda * np.exp(-tp * 9) * (0.05 if j % 4 == 0 else 0.03)
        i += 1
    pad = pasa_bajos(pad, 2600)
    arp = pasa_bajos(arp, 4500)
    # timbales en negras cuando sube la tensión
    perc = np.zeros(n)
    for k in np.arange(0, MARCA - 0.5, beat * 2):
        p0 = int(k * SR)
        ln = min(int(0.9 * SR), n - p0)
        tp = np.arange(ln) / SR
        f = 50 * (1 + 0.8 * np.exp(-tp * 30))
        perc[p0:p0 + ln] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tp * 6) * 0.6
    perc *= np.clip((inten - 0.62) * 3, 0, 1)
    # silencio dramático justo antes de la maniobra
    hueco = 1 - 0.85 * np.exp(-((t - (te - 0.25)) / 0.25) ** 2)
    m = (pad * (0.7 + 0.3 * inten) + bajo * inten + arp * np.clip((inten - 0.5) * 2, 0.2, 1) + perc) * inten * hueco
    return reverb(m, 2.6, 0.32)


def riser(n, t_fin, dur=4.0, vol=0.25):
    """Subida de tensión (ruido filtrado + tono ascendente) que culmina en t_fin."""
    x = np.zeros(n)
    p0 = int((t_fin - dur) * SR)
    ln = int(dur * SR)
    tp = np.linspace(0, 1, ln)
    ruido = np.random.default_rng(4).normal(0, 1, ln)
    ruido = signal.lfilter(*signal.butter(2, [800 / (SR / 2), 9000 / (SR / 2)], "band"), ruido)
    f = 200 * 2 ** (tp * 3)
    tono = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    x[p0:p0 + ln] = (ruido * 0.6 + tono) * tp ** 2.5 * vol
    return x


def golpe(n, t0, vol=1.0, semilla=5):
    x = np.zeros(n)
    p0 = int(t0 * SR)
    ln = min(int(4 * SR), n - p0)
    tp = np.arange(ln) / SR
    f = 40 * (1 + 1.5 * np.exp(-tp * 16))
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tp * 1.5)
    ruido = pasa_bajos(np.random.default_rng(semilla).normal(0, 1, ln), 1500) * np.exp(-tp * 5) * 0.5
    x[p0:p0 + ln] = (boom + ruido) * vol
    return reverb(x, 3.0, 0.4, semilla)


def barrido(n, t0, dur=0.6, vol=0.05):
    x = np.zeros(n)
    p0 = max(0, int((t0 - dur * 0.6) * SR))
    ln = min(int(dur * SR), n - p0)
    ruido = np.random.default_rng(int(t0 * 100)).normal(0, 1, ln)
    fc = 400 + 5000 * np.sin(np.linspace(0, np.pi, ln)) ** 2
    y = np.zeros(ln)
    zi = None
    for s in range(0, ln, 512):
        b, a = signal.butter(2, [max(80, fc[s] * 0.5) / (SR / 2), min(fc[s] * 1.6, 20000) / (SR / 2)], "band")
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        y[s:s + 512], zi = signal.lfilter(b, a, ruido[s:s + 512], zi=zi)
    x[p0:p0 + ln] = y * np.sin(np.linspace(0, np.pi, ln)) ** 2 * vol
    return x


def cargar(nombre):
    a, sr = sf.read(MAT / nombre, always_2d=True)
    assert sr == SR, f"{nombre} debe estar a {SR} Hz"
    return a.mean(axis=1)


def efecto(n, archivo, t0, vol, estirar=1.0):
    s = cargar(archivo)
    if estirar != 1.0:  # más largo y grave
        s = signal.resample(s, int(len(s) * estirar))
    s = s / (np.max(np.abs(s)) + 1e-9)
    x = np.zeros(n)
    p0 = int(t0 * SR)
    ln = min(len(s), n - p0)
    x[p0:p0 + ln] = s[:ln] * vol * adsr(ln, 0.005, min(0.3, ln / SR / 2))
    return x


def silbido_propulsor(n, t0, dur, vol):
    """Siseo de gas a presión sintetizado para alargar los propulsores."""
    x = np.zeros(n)
    p0 = int(t0 * SR)
    ln = int(dur * SR)
    ruido = np.random.default_rng(9).normal(0, 1, ln)
    ruido = signal.lfilter(*signal.butter(2, [1500 / (SR / 2), 12000 / (SR / 2)], "band"), ruido)
    grave = pasa_bajos(np.random.default_rng(10).normal(0, 1, ln), 250) * 2.5
    x[p0:p0 + ln] = (ruido + grave) * adsr(ln, 0.03, dur * 0.6) * vol
    return x


def mezcla(ruta):
    n = int(TOTAL * SR)
    voz = np.zeros(n)
    v = cargar("voz.wav")
    p0 = int(VO * SR)
    voz[p0:p0 + len(v)] = v[:n - p0]
    voz = signal.lfilter(*signal.butter(2, 70 / (SR / 2), "high"), voz)
    env = np.sqrt(signal.lfilter([0.002], [1, -0.998], voz ** 2)) + 1e-6
    voz = voz * np.minimum(1, (0.12 / env) ** 0.35)

    mus = musica(n)
    hay_voz = signal.lfilter([0.0005], [1, -0.9995], np.abs(voz) > 0.02) > 0.15
    duck = signal.lfilter([0.0002], [1, -0.9998], hay_voz.astype(float))
    duck = 1 - 0.5 * np.clip(duck * 1.3, 0, 1)

    te = T_ELEVA + VO
    sfx = np.zeros(n)
    sfx += golpe(n, 0.05, 0.5)                                         # gancho
    sfx += efecto(n, "impacto.wav", 0.05, 0.5, 1.6)
    sfx += efecto(n, "propulsor.wav", 1.7 + VO, 0.35, 1.5)             # «hacer volar»
    sfx += efecto(n, "electrico.wav", 6.3 + VO, 0.35, 1.8)             # «correr por las carreteras»
    sfx += silbido_propulsor(n, 9.6 + VO, 1.4, 0.05)                   # «elevarse por el aire»
    sfx += efecto(n, "propulsor2.wav", 38.6 + VO, 0.3, 1.4)            # «pequeños propulsores»
    sfx += silbido_propulsor(n, 40.2 + VO, 1.2, 0.04)                  # «gas a presión»
    sfx += efecto(n, "electrico.wav", 54.2 + VO, 0.3, 2.0)             # arranca la demostración
    sfx += riser(n, te, 5.5, 0.22)
    sfx += efecto(n, "propulsor.wav", te, 0.6, 1.8)                    # la maniobra
    sfx += silbido_propulsor(n, te, 2.4, 0.09)
    sfx += golpe(n, te, 0.9, 6)
    sfx += efecto(n, "impacto.wav", 63.3 + VO, 0.45, 1.3)              # «aterrizar»
    sfx += efecto(n, "impacto.wav", 72.4 + VO, 0.3, 1.8)               # «2028»
    for k in range(1, len(PLANOS)):
        if PLANOS[k][2] != "marca" and PLANOS[k][0] not in CORTES_SECOS:
            sfx += barrido(n, PLANOS[k][0] + VO)
    sfx += golpe(n, MARCA + 0.1, 0.7, 7)
    sfx += barrido(n, MARCA, 1.0, 0.1)

    def nivel(x):
        return np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))
    voz = voz / nivel(voz) * 0.16
    mus = mus / nivel(mus[: int(MARCA * SR)]) * 0.16 * 0.24
    total = voz + mus * duck + sfx * 0.8
    total *= adsr(n, 0.02, 1.5)
    estereo = np.stack([total, total], axis=1)
    retardo = int(0.012 * SR)
    m2 = np.roll(mus * duck, retardo) * 0.18
    estereo[:, 0] += m2
    estereo[:, 1] -= m2
    estereo /= np.max(np.abs(estereo)) / 0.9
    sf.write(ruta, estereo.astype(np.float32), SR, subtype="FLOAT")


# ----------------------------------------------------------------- salida
def renderizar_tramo(args):
    n0, n1, ruta = args
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", str(ruta)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        p.stdin.write(cuadro(n).tobytes())
    p.stdin.close()
    p.wait()
    print(f"tramo {n0 / FPS:.0f}-{n1 / FPS:.0f} s listo", flush=True)
    return ruta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", nargs=2, type=float)
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--salida", default=str(AQUI.parent.parent / "exportados/Curiosidades_del_Mundo_Tesla_Roadster.mp4"))
    args = ap.parse_args()
    tmp = AQUI / "salida"
    tmp.mkdir(exist_ok=True)
    audio = tmp / "mezcla.wav"
    if not args.prueba or not audio.exists():
        mezcla(audio)
        print("audio listo", flush=True)
    a, b = args.prueba if args.prueba else (0, TOTAL)
    n0, n1 = int(a * FPS), int(b * FPS)
    paso = -(-(n1 - n0) // args.procesos)
    tramos = [(i, min(i + paso, n1), tmp / f"tramo{j:02d}.mp4") for j, i in enumerate(range(n0, n1, paso))]
    with Pool(args.procesos) as pool:
        rutas = pool.map(renderizar_tramo, tramos)
    lista = tmp / "tramos.txt"
    lista.write_text("".join(f"file '{r.name}'\n" for r in rutas))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-ss", str(a), "-t", str(b - a), "-i", str(audio),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M",
                    "-profile:v", "high", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", args.salida], check=True)
    srt = []
    f = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x % 1 * 1000):03d}"
    for k, (si, sf_, pal) in enumerate(SUBS):
        srt.append(f"{k + 1}\n{f(si)} --> {f(sf_)}\n{' '.join(pal)}\n")
    Path(args.salida).with_suffix(".srt").write_text("\n".join(srt))
    print("listo:", args.salida)


if __name__ == "__main__":
    main()
