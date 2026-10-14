#!/usr/bin/env python3
"""Genera el video vertical (9:16) "¿El día que el mundo se quedó sin internet?".

Uso (desde videos-edicion/):
  python3 proyectos/sin-internet/generar_video.py -o exportados/sin-internet.mp4

Necesita: Pillow, numpy y FFmpeg.
"""
import argparse
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SR = 44100

FUENTES = {
    "black": ["/usr/share/fonts/opentype/inter/Inter-Black.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "bold": ["/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "medium": ["/usr/share/fonts/opentype/inter/Inter-Medium.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"],
}
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

BLANCO = (245, 247, 255)
GRIS = (160, 172, 200)
CIAN = (64, 224, 255)
ROJO = (255, 70, 85)
AMARILLO = (255, 205, 60)
VERDE = (60, 220, 130)

_cache = {}


def fuente(peso, tam):
    clave = (peso, tam)
    if clave not in _cache:
        for ruta in FUENTES[peso]:
            if Path(ruta).exists():
                _cache[clave] = ImageFont.truetype(ruta, tam)
                break
        else:
            _cache[clave] = ImageFont.load_default(tam)
    return _cache[clave]


_emoji_cache = {}


def emoji(ch, tam):
    clave = (ch, tam)
    if clave not in _emoji_cache:
        try:
            f = ImageFont.truetype(EMOJI, 109)
            img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(img).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
            img = img.crop(img.getbbox() or (0, 0, 160, 160))
            esc = tam / max(img.size)
            img = img.resize((max(1, int(img.width * esc)), max(1, int(img.height * esc))), Image.LANCZOS)
        except OSError:
            img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        _emoji_cache[clave] = img
    return _emoji_cache[clave]


# ---------- utilidades de animación ----------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def aparecer(t, inicio, dur=0.5):
    return ease_out((t - inicio) / dur)


def envolver(texto, f, ancho):
    lineas = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = (actual + " " + palabra).strip()
            if f.getlength(prueba) <= ancho or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


def texto(capa, txt, y, tam, peso="bold", color=BLANCO, alfa=1.0, ancho=920, interlineado=1.18,
          dy=0, sombra=True, centro_x=W // 2):
    """Dibuja texto centrado con salto de línea; devuelve la y final."""
    if alfa <= 0:
        return y + tam
    f = fuente(peso, tam)
    d = ImageDraw.Draw(capa)
    a = int(255 * clamp(alfa))
    for linea in envolver(txt, f, ancho):
        if sombra:
            d.text((centro_x + 4, y + dy + 6), linea, font=f, fill=(0, 0, 0, int(a * 0.55)), anchor="ma")
        d.text((centro_x, y + dy), linea, font=f, fill=color + (a,), anchor="ma")
        y += int(tam * interlineado)
    return y


def pegar(capa, img, cx, cy, alfa=1.0, escala=1.0):
    if alfa <= 0 or escala <= 0:
        return
    if escala != 1.0:
        img = img.resize((max(1, int(img.width * escala)), max(1, int(img.height * escala))), Image.LANCZOS)
    if alfa < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alfa)))
    capa.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def pastilla(capa, cx, cy, txt, tam, fondo, color=BLANCO, alfa=1.0, pad=(34, 18), peso="black"):
    if alfa <= 0:
        return
    f = fuente(peso, tam)
    d = ImageDraw.Draw(capa)
    ancho = f.getlength(txt)
    a = int(255 * alfa)
    caja = (cx - ancho / 2 - pad[0], cy - tam / 2 - pad[1], cx + ancho / 2 + pad[0], cy + tam / 2 + pad[1] + 4)
    d.rounded_rectangle(caja, radius=tam // 2 + pad[1], fill=fondo + (a,))
    d.text((cx, cy), txt, font=f, fill=color + (a,), anchor="mm")


# ---------- fondo: red de nodos ----------

class Red:
    def __init__(self, n=46, semilla=7):
        rnd = random.Random(semilla)
        self.nodos = [(rnd.uniform(-60, W + 60), rnd.uniform(-60, H + 60),
                       rnd.uniform(-14, 14), rnd.uniform(-14, 14), rnd.uniform(0, 6.28)) for _ in range(n)]
        y = np.linspace(0, 1, H)[:, None]
        x = np.linspace(0, 1, W)[None, :]
        r = 6 + 10 * y + 0 * x
        g = 10 + 14 * y + 0 * x
        b = 24 + 30 * y + 0 * x
        vin = 1 - 0.55 * ((x - 0.5) ** 2 + (y - 0.45) ** 2)
        base = np.stack([r * vin, g * vin, b * vin], axis=-1).clip(0, 255).astype(np.uint8)
        self.base = Image.fromarray(base, "RGB").convert("RGBA")

    def dibujar(self, t, rojo=0.0, corte=0.0, brillo=1.0):
        img = self.base.copy()
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        pos = []
        for i, (x, y, vx, vy, fase) in enumerate(self.nodos):
            px = x + vx * t + 18 * math.sin(t * 0.4 + fase)
            py = y + vy * t + 18 * math.cos(t * 0.33 + fase)
            pos.append((px % (W + 120) - 60, py % (H + 120) - 60))
        col = tuple(int(CIAN[k] * (1 - rojo) + ROJO[k] * rojo) for k in range(3))
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                dx, dy = pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]
                dist = math.hypot(dx, dy)
                if dist < 330:
                    # al "cortarse" la red, las conexiones van desapareciendo
                    if corte > 0 and ((i * 31 + j * 17) % 100) / 100 < corte:
                        continue
                    a = int(70 * (1 - dist / 330) * brillo)
                    d.line([pos[i], pos[j]], fill=col + (a,), width=2)
        for i, (px, py) in enumerate(pos):
            pulso = 0.6 + 0.4 * math.sin(t * 2 + i)
            r = 5 + 2 * pulso
            d.ellipse((px - r * 2.4, py - r * 2.4, px + r * 2.4, py + r * 2.4), fill=col + (int(25 * brillo),))
            d.ellipse((px - r, py - r, px + r, py + r), fill=col + (int(150 * pulso * brillo),))
        img.alpha_composite(capa)
        return img


# ---------- dibujos ----------

def celular(capa, cx, cy, t, alfa, sin_senal):
    d = ImageDraw.Draw(capa)
    a = int(255 * alfa)
    w, h = 380, 720
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=58, fill=(20, 24, 38, a), outline=(120, 135, 170, a), width=8)
    d.rounded_rectangle((x0 + 20, y0 + 22, x0 + w - 20, y0 + h - 22), radius=42, fill=(10, 14, 26, a))
    d.rounded_rectangle((cx - 60, y0 + 34, cx + 60, y0 + 62), radius=14, fill=(0, 0, 0, a))
    # hora
    d.text((cx, y0 + 130), "7:00", font=fuente("bold", 96), fill=BLANCO + (a,), anchor="mm")
    d.text((cx, y0 + 200), "lunes", font=fuente("medium", 34), fill=GRIS + (a,), anchor="mm")
    # icono wifi
    wy = y0 + 420
    col = ROJO if sin_senal > 0.5 else CIAN
    for k, rad in enumerate((130, 90, 50)):
        d.arc((cx - rad, wy - rad, cx + rad, wy + rad), 225, 315, fill=col + (a,), width=18)
    d.ellipse((cx - 14, wy - 14, cx + 14, wy + 14), fill=col + (a,))
    if sin_senal > 0:
        e = ease_out(sin_senal)
        d.line((cx - 120, wy - 150, cx - 120 + 240 * e, wy - 150 + 200 * e), fill=ROJO + (a,), width=20)
        d.text((cx, y0 + 560), "Sin conexión", font=fuente("bold", 44),
               fill=ROJO + (int(a * clamp(sin_senal * 2)),), anchor="mm")


def tarjeta_app(capa, cx, cy, nombre, color, alfa, caida, sacudida=0):
    if alfa <= 0:
        return
    d = ImageDraw.Draw(capa)
    a = int(255 * alfa)
    w, h = 820, 150
    cx += sacudida
    gris = tuple(int(c * (1 - 0.65 * caida) + 60 * 0.65 * caida) for c in color)
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=36, fill=(22, 26, 42, int(a * 0.92)),
                        outline=gris + (a,), width=5)
    d.rounded_rectangle((cx - w / 2 + 26, cy - 50, cx - w / 2 + 126, cy + 50), radius=26, fill=gris + (a,))
    d.text((cx - w / 2 + 76, cy), nombre[0], font=fuente("black", 62), fill=BLANCO + (a,), anchor="mm")
    d.text((cx - w / 2 + 160, cy - 26), nombre, font=fuente("bold", 50), fill=BLANCO + (a,), anchor="lm")
    estado = "fuera de servicio" if caida > 0.5 else "funcionando"
    ce = ROJO if caida > 0.5 else VERDE
    d.ellipse((cx - w / 2 + 162, cy + 22, cx - w / 2 + 184, cy + 44), fill=ce + (a,))
    d.text((cx - w / 2 + 198, cy + 33), estado, font=fuente("medium", 36), fill=ce + (a,), anchor="lm")


# ---------- escenas ----------
# Cada escena: (duración, función(capa, t, dur) -> dict opcional con estado de la red)

def e_titulo(c, t, dur):
    pegar(c, emoji("🌎", 300), W / 2, 560 - 40 * (1 - ease_back(t / 0.8)), aparecer(t, 0, 0.5), 0.6 + 0.4 * ease_back(t / 0.8))
    y = 820
    for i, linea in enumerate(["¿EL DÍA QUE", "EL MUNDO", "SE QUEDÓ", "SIN INTERNET?"]):
        al = aparecer(t, 0.35 + i * 0.22, 0.4)
        col = ROJO if i == 3 else BLANCO
        dy = 40 * (1 - al)
        if i == 3 and t > 1.4:
            # efecto "glitch"
            j = int(t * 30)
            if j % 7 in (0, 1):
                texto(c, linea, y + (j % 3) * 4, 132, "black", CIAN, 0.6, dy=dy, sombra=False, centro_x=W // 2 - 10)
        texto(c, linea, y, 132, "black", col, al, dy=dy, ancho=1040)
        y += 150
    texto(c, "Una historia que deberías conocer", 1520, 44, "medium", GRIS, aparecer(t, 2.2))


def e_imagina(c, t, dur):
    texto(c, "¿Te imaginas despertar un día, agarrar tu celular y…", 230, 64, "bold", BLANCO, aparecer(t, 0.1))
    celular(c, W / 2, 1120, t, aparecer(t, 0.5), clamp((t - 2.6) / 0.8))
    texto(c, "…descubrir que no tienes internet?", 1550, 64, "black", AMARILLO, aparecer(t, 3.2))


def e_sin(c, t, dur):
    texto(c, "Sin conexión significa…", 420, 60, "bold", GRIS, aparecer(t, 0))
    for i, (em, txt) in enumerate([("💬", "Sin WhatsApp"), ("📱", "Sin redes sociales"), ("🎬", "Sin tus videos favoritos")]):
        al = aparecer(t, 0.5 + i * 0.7, 0.45)
        y = 720 + i * 230
        x = 90 + 60 * (1 - al)
        pegar(c, emoji(em, 110), x + 60, y + 50, al)
        d = ImageDraw.Draw(c)
        d.text((x + 150, y + 50), txt, font=fuente("black", 60), fill=BLANCO + (int(255 * al),), anchor="lm")
        tacha = clamp((t - (1.0 + i * 0.7)) / 0.35)
        if tacha > 0:
            ancho = fuente("black", 60).getlength(txt)
            d.line((x + 140, y + 54, x + 140 + (ancho + 20) * tacha, y + 54), fill=ROJO + (int(255 * al),), width=12)


def e_interrupciones(c, t, dur):
    parpadeo = 1.0 if (t * 3) % 1 < 0.7 else 0.35
    pegar(c, emoji("⚠️", 220), W / 2, 620, aparecer(t, 0) * parpadeo, 0.8 + 0.2 * ease_back(t / 0.6))
    texto(c, "Aunque parezca increíble…", 840, 64, "bold", GRIS, aparecer(t, 0.3))
    texto(c, "el mundo ha sufrido grandes interrupciones de internet.", 980, 90, "black", BLANCO, aparecer(t, 1.0), ancho=960)
    return {"rojo": 0.35 * aparecer(t, 1.0)}


def e_arpanet(c, t, dur):
    pastilla(c, W / 2, 330, "29 · OCTUBRE · 1969", 64, (35, 60, 110), alfa=aparecer(t, 0))
    d = ImageDraw.Draw(c)
    a = aparecer(t, 0.4)
    caja = (110, 480, W - 110, 1000)
    d.rounded_rectangle(caja, radius=28, fill=(4, 10, 6, int(235 * a)), outline=(60, 220, 130, int(200 * a)), width=4)
    d.text((150, 520), "ARPANET  ·  UCLA → STANFORD", font=fuente("mono", 36), fill=(60, 220, 130, int(180 * a)))
    mensaje = "LO"
    n = int(clamp((t - 1.0) / 0.9) * len(mensaje) + 0.0001)
    cursor = "█" if int(t * 2.5) % 2 == 0 else " "
    d.text((150, 640), "> " + mensaje[:n] + cursor, font=fuente("mono", 170), fill=(60, 230, 140, int(255 * a)))
    texto(c, "Se envía uno de los primeros mensajes a través de ARPANET", 1090, 62, "black", BLANCO, aparecer(t, 1.8), ancho=940)
    texto(c, "la red precursora del internet moderno", 1360, 52, "medium", CIAN, aparecer(t, 2.8))


def e_decadas(c, t, dur):
    texto(c, "Décadas después…", 420, 72, "bold", GRIS, aparecer(t, 0))
    anio = int(1969 + (2026 - 1969) * ease_out((t - 0.4) / 1.8))
    texto(c, str(anio), 560, 240, "black", CIAN, aparecer(t, 0.3), sombra=True)
    texto(c, "internet se convirtió en una herramienta esencial para", 950, 64, "bold", BLANCO, aparecer(t, 1.6))
    texto(c, "millones de personas", 1180, 92, "black", AMARILLO, aparecer(t, 2.4))
    return {"brillo": 1 + 0.6 * aparecer(t, 1.5)}


def e_depende(c, t, dur):
    texto(c, "Parece que siempre está disponible…", 300, 60, "bold", GRIS, aparecer(t, 0))
    texto(c, "pero depende de:", 420, 84, "black", BLANCO, aparecer(t, 0.7))
    items = [("🌊", "Cables submarinos"), ("🏢", "Centros de datos"), ("🖥️", "Servidores"), ("⚙️", "Muchas otras tecnologías")]
    for i, (em, txt) in enumerate(items):
        al = aparecer(t, 1.4 + i * 0.6, 0.45)
        y = 650 + i * 200
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((110, y, W - 110, y + 160), radius=34, fill=(25, 40, 70, int(200 * al)),
                            outline=CIAN + (int(160 * al),), width=3)
        pegar(c, emoji(em, 96), 200 + 40 * (1 - al), y + 80, al)
        d.text((290 + 40 * (1 - al), y + 80), txt, font=fuente("bold", 52), fill=BLANCO + (int(255 * al),), anchor="lm")


def e_falla(c, t, dur):
    texto(c, "Cuando alguno de estos sistemas falla…", 520, 76, "black", BLANCO, aparecer(t, 0))
    texto(c, "millones de personas pueden quedarse", 1020, 64, "bold", GRIS, aparecer(t, 1.6))
    texto(c, "SIN CONEXIÓN", 1180, 120, "black", ROJO, aparecer(t, 2.2))
    return {"rojo": clamp((t - 0.8) / 1.2), "corte": clamp((t - 0.8) / 2.2) * 0.85}


def e_2021(c, t, dur):
    pastilla(c, W / 2, 300, "OCTUBRE 2021", 64, (120, 30, 40), alfa=aparecer(t, 0))
    texto(c, "Una falla en la infraestructura de Facebook dejó fuera de servicio:", 420, 56, "bold", BLANCO,
          aparecer(t, 0.4), ancho=960)
    apps = [("Facebook", (24, 119, 242)), ("Instagram", (225, 48, 108)), ("WhatsApp", (37, 211, 102))]
    for i, (n, col) in enumerate(apps):
        al = aparecer(t, 1.2 + i * 0.35)
        caida = clamp((t - (2.6 + i * 0.35)) / 0.2)
        sac = int(14 * math.sin(t * 80)) if 0 < t - (2.6 + i * 0.35) < 0.35 else 0
        tarjeta_app(c, W / 2, 800 + i * 210, n, col, al, caida, sac)
    texto(c, "durante varias horas", 1480, 60, "black", AMARILLO, aparecer(t, 4.0))
    return {"rojo": 0.6 * clamp((t - 2.6) / 0.8)}


def e_no_todo(c, t, dur):
    pegar(c, emoji("👀", 130), W / 2, 330, aparecer(t, 0))
    texto(c, "Pero ojo…", 430, 70, "bold", GRIS, aparecer(t, 0))
    texto(c, "No fue una caída de todo internet…", 560, 88, "black", BLANCO, aparecer(t, 0.5))
    al = aparecer(t, 2.2)
    texto(c, "…sino de los servicios de", 960, 70, "bold", CIAN, al)
    texto(c, "UNA MISMA EMPRESA", 1080, 104, "black", AMARILLO, al)
    return {"rojo": 0.6 * (1 - aparecer(t, 0.5, 1.5))}


def e_dependemos(c, t, dur):
    texto(c, "Hoy dependemos tanto de internet que una simple interrupción puede afectar…", 280, 64, "black",
          BLANCO, aparecer(t, 0), ancho=940)
    items = [("💬", "Nuestras comunicaciones"), ("💼", "Nuestros trabajos"), ("🏪", "Hasta nuestros negocios")]
    for i, (em, txt) in enumerate(items):
        al = aparecer(t, 1.6 + i * 0.75, 0.5)
        y = 820 + i * 240
        esc = 0.7 + 0.3 * ease_back((t - 1.6 - i * 0.75) / 0.5)
        pegar(c, emoji(em, 110), 170, y, al, esc)
        ImageDraw.Draw(c).text((260, y), txt, font=fuente("black", 58), fill=BLANCO + (int(255 * al),), anchor="lm")


def e_cierre(c, t, dur):
    pegar(c, emoji("🤔", 220), W / 2, 600, aparecer(t, 0), 0.7 + 0.3 * ease_back(t / 0.7))
    texto(c, "¿Y tú qué harías\nun día", 800, 88, "black", BLANCO, aparecer(t, 0.3))
    texto(c, "SIN INTERNET?", 1030, 124, "black", ROJO, aparecer(t, 0.7), ancho=1040)
    texto(c, "Cuéntamelo en los comentarios", 1300, 58, "bold", GRIS, aparecer(t, 1.5))
    pegar(c, emoji("👇", 110), W / 2, 1470 + 18 * math.sin(t * 6), aparecer(t, 1.8))


ESCENAS = [
    (5.0, e_titulo), (6.5, e_imagina), (5.0, e_sin), (5.0, e_interrupciones), (7.0, e_arpanet),
    (5.5, e_decadas), (7.0, e_depende), (5.0, e_falla), (7.0, e_2021), (6.5, e_no_todo),
    (7.0, e_dependemos), (5.5, e_cierre),
]
FUNDIDO = 0.35


def cuadro(red, n):
    t_global = n / FPS
    t0 = 0.0
    for dur, fn in ESCENAS:
        if t_global < t0 + dur:
            break
        t0 += dur
    t = t_global - t0
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    estado = fn(capa, t, dur) or {}
    img = red.dibujar(t_global, estado.get("rojo", 0.0), estado.get("corte", 0.0), estado.get("brillo", 1.0))
    alfa = min(clamp(t / FUNDIDO), clamp((dur - t) / FUNDIDO))
    if alfa < 1:
        capa.putalpha(capa.getchannel("A").point(lambda v: int(v * alfa)))
    img.alpha_composite(capa)
    # barra de progreso
    d = ImageDraw.Draw(img)
    total = sum(e[0] for e in ESCENAS)
    d.rectangle((0, H - 10, W * t_global / total, H), fill=CIAN + (255,))
    return img.convert("RGB")


# ---------- música de fondo ----------

def musica(ruta, dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sal = np.zeros(n)

    def nota(m):
        return 440 * 2 ** ((m - 69) / 12)

    acordes = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    compas = 4.0
    for k in range(int(dur // compas) + 1):
        ini = int(k * compas * SR)
        fin = min(n, int((k + 1) * compas * SR) + SR // 2)
        if ini >= n:
            break
        tt = t[ini:fin] - k * compas
        env = np.minimum(1, tt / 1.2) * np.exp(-np.maximum(0, tt - compas + 0.4) * 3)
        for m in acordes[k % 4]:
            f = nota(m)
            sal[ini:fin] += env * 0.05 * (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.004 * tt))
        bajo = nota(acordes[k % 4][0] - 12)
        sal[ini:fin] += env * 0.08 * np.sin(2 * np.pi * bajo * tt)
    # pulso suave (como un latido de datos) a 96 bpm
    beat = 60 / 96
    for k in range(int(dur / beat)):
        ini = int(k * beat * SR)
        tt = np.arange(int(0.25 * SR)) / SR
        seg = 0.12 * np.exp(-tt * 18) * np.sin(2 * np.pi * (70 - 30 * tt) * tt)
        sal[ini:ini + len(seg)] += seg[: n - ini]
    # "whoosh" en cada cambio de escena
    rng = np.random.default_rng(1)
    t0 = 0
    for d, _ in ESCENAS[:-1]:
        t0 += d
        ini = int((t0 - 0.35) * SR)
        m = int(0.7 * SR)
        ruido = rng.standard_normal(m)
        ruido = np.convolve(ruido, np.ones(30) / 30, mode="same")
        env = np.sin(np.linspace(0, np.pi, m)) ** 2
        sal[ini:ini + m] += 0.25 * ruido * env
    # fade in/out general
    sal *= np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 2.5)
    sal = sal / (np.max(np.abs(sal)) + 1e-9) * 0.7
    est = np.stack([sal, np.roll(sal, 300)], axis=1)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((est * 32767).astype(np.int16).tobytes())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-o", default="exportados/sin-internet.mp4")
    p.add_argument("--vista", type=float, help="solo guarda un PNG del segundo indicado")
    args = p.parse_args()

    red = Red()
    if args.vista is not None:
        cuadro(red, int(args.vista * FPS)).save(args.o)
        return

    dur = sum(e[0] for e in ESCENAS)
    total = int(dur * FPS)
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "musica.wav"
        musica(audio, dur)
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", str(audio), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.o]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for n in range(total):
            proc.stdin.write(cuadro(red, n).tobytes())
            if n % (FPS * 5) == 0:
                print(f"  {n // FPS:>3}s / {int(dur)}s", file=sys.stderr)
        proc.stdin.close()
        proc.wait()
    print("Listo:", args.o)


if __name__ == "__main__":
    main()
