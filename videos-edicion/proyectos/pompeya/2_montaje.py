"""Paso 2: monta el video vertical 9:16 (1080×1920, 30 fps) con voz, música, efectos y subtítulos.

Uso: python3 2_montaje.py <carpeta_salida> [--prueba INICIO FIN]
Necesita <salida>/escenas/*.png (paso 0) y <salida>/voz.json (paso 1).
Resultado: <salida>/Pompeya_Curiosidades_del_Mundo.mp4 y <salida>/pompeya.srt
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal

AQUI = Path(__file__).parent
sys.path.append(str(AQUI.parent / "napoleon"))
import sonido as SN  # noqa: E402  (efectos y música sintetizados del proyecto Napoleón)

import guion  # noqa: E402

W, H, FPS = 1080, 1920, 30
CANAL = "CURIOSIDADES DEL MUNDO"
AMARILLO, BLANCO = (255, 206, 0), (255, 255, 255)
F_SUB = AQUI / "fuentes" / "Montserrat.ttf"
F_TITULO = AQUI / "fuentes" / "Cinzel.ttf"
F_ANTON = AQUI / "fuentes" / "Anton-Regular.ttf"

# Zona segura: los botones de TikTok/Instagram ocupan la franja inferior (~380 px) y la columna derecha
SUB_Y, SUB_ANCHO = 1300, 820

# Movimiento de cámara de cada imagen: (zoom inicial, zoom final, (x, y) inicial, (x, y) final)
# zoom 1 = toda la altura de la imagen; x, y = centro normalizado
CAMARA = {
    1: (1.05, 1.30, (0.50, 0.55), (0.50, 0.45)),
    2: (1.10, 1.25, (0.30, 0.55), (0.65, 0.55)),
    3: (1.25, 1.08, (0.55, 0.50), (0.40, 0.55)),
    4: (1.00, 1.35, (0.50, 0.60), (0.47, 0.42)),
    5: (1.10, 1.30, (0.35, 0.55), (0.55, 0.50)),
    6: (1.25, 1.05, (0.60, 0.55), (0.40, 0.55)),
    7: (1.05, 1.35, (0.50, 0.60), (0.50, 0.55)),
    8: (1.10, 1.30, (0.30, 0.55), (0.60, 0.65)),
    9: (1.25, 1.05, (0.35, 0.50), (0.60, 0.50)),
    10: (1.30, 1.05, (0.35, 0.65), (0.50, 0.55)),
    11: (1.05, 1.30, (0.50, 0.50), (0.52, 0.48)),
    12: (1.15, 1.30, (0.35, 0.50), (0.70, 0.50)),
}

INICIO, PAUSA, PAUSA_ESCENA, CIERRE = 0.30, 0.06, 0.22, 2.4
TRANS = 0.35  # duración de las transiciones


# ------------------------------------------------------------------ línea de tiempo
def linea_de_tiempo(voz):
    """Calcula cuándo suena cada frase, cuándo sale cada subtítulo y qué imagen se ve."""
    t = INICIO
    frases, subs, escenas = [], [], []
    for e, (escena, items) in enumerate(zip(guion.ESCENAS, voz)):
        t0 = t
        for i, it in enumerate(items):
            frases.append((t, it["wav"]))
            frags = guion.fragmentos(it["frase"])
            pesos = [sum(silabas(p) for p, _ in fr) + (1.2 if fr[-1][0][-1] in ",." else 0) for fr in frags]
            total, a = sum(pesos), t
            for fr, p in zip(frags, pesos):
                b = a + it["dur"] * p / total
                subs.append([a, b, fr])
                a = b
            t += it["dur"] + (PAUSA if i < len(items) - 1 else 0)
        t += PAUSA_ESCENA
        escenas.append((t0, t, escena))
    fin_voz = t - PAUSA_ESCENA
    for k in range(len(subs) - 1):  # cada subtítulo se queda hasta que entra el siguiente (sin huecos largos)
        if subs[k + 1][0] - subs[k][1] < 0.4:
            subs[k][1] = subs[k + 1][0]
    total = fin_voz + CIERRE
    # imágenes: cada escena se reparte entre sus imágenes; la primera escena empieza en 0
    clips = []
    for e, (t0, t1, escena) in enumerate(escenas):
        t0 = 0.0 if e == 0 else t0
        t1 = total if e == len(escenas) - 1 else escenas[e + 1][0]
        n = len(escena["imagenes"])
        for k, img in enumerate(escena["imagenes"]):
            clips.append({"img": img, "t0": t0 + (t1 - t0) * k / n, "t1": t0 + (t1 - t0) * (k + 1) / n,
                          "escena": escena["nombre"]})
    return frases, subs, escenas, clips, fin_voz, total


def silabas(palabra):
    vocales, n, prev = "aeiouáéíóúü", 0, False
    for c in palabra.lower():
        v = c in vocales
        n += v and not prev
        prev = v
    return max(1, n)


# ---------------------------------------------------------------------- sonido
def sonido(salida, frases, escenas, clips, fin_voz, total):
    sr = SN.SR
    n = SN.seg(total + 0.5)
    voz = np.zeros((n, 2), np.float32)
    for t, wav in frases:
        a, sr_v = sf.read(wav, dtype="float32")
        if sr_v != sr:
            a = signal.resample_poly(a, sr, sr_v).astype(np.float32)
        k = SN.seg(t)
        voz[k: k + len(a)] += np.stack([a, a], 1)[: n - k]
    voz = SN.normal(voz, 0.85)

    def poner(pista, x, t, vol=1.0):
        k = SN.seg(t)
        if k < n:
            pista[k: k + len(x)] += x[: n - k] * vol

    # música por bloques de ánimo con fundidos cruzados
    musica = np.zeros((n, 2), np.float32)
    bloques = []
    for t0, t1, esc in escenas:
        if bloques and bloques[-1][2] == esc["musica"]:
            bloques[-1][1] = t1
        else:
            bloques.append([t0 if bloques else 0.0, t1, esc["musica"]])
    bloques[-1][1] = total
    for i, (t0, t1, estado) in enumerate(bloques):
        m = SN.musica(estado, t1 - t0 + 2.5)
        vol = {"misterio": 0.8, "tension": 1.25, "majestuoso": 0.85}[estado]
        if estado == "tension":  # la tensión crece durante la erupción
            m *= np.linspace(0.7, 1.25, len(m))[:, None]
        poner(musica, m, max(0, t0 - 1.0), vol)

    sfx = np.zeros((n, 2), np.float32)
    t_erup = next(t0 for t0, _, e in escenas if e["nombre"] == "erupcion")
    t_cat = next(t0 for t0, _, e in escenas if e["nombre"] == "catastrofe")
    t_desc = next(t0 for t0, _, e in escenas if e["nombre"] == "descubrimiento")
    poner(sfx, SN.impacto(), 0.05, 0.55)                                   # golpe del título
    retumbe = SN.estereo(SN.lp(SN.ruido(SN.seg(t_desc - 2)), 90, 4))       # el volcán ruge por debajo
    retumbe *= np.clip(np.linspace(-0.3, 1.6, len(retumbe)), 0, 1)[:, None] ** 1.5
    retumbe[-SN.seg(2):] *= np.linspace(1, 0, SN.seg(2))[:, None]
    poner(sfx, retumbe, 2.0, 1.1)
    poner(sfx, SN.impacto(), t_erup - 0.05, 0.9)                           # erupción
    poner(sfx, SN.canon(0.6), t_erup + 0.05, 0.6)
    poner(sfx, lluvia_pomez(t_desc - t_erup - 1.5), t_erup + 1.0, 0.55)    # piedra pómez cayendo
    poner(sfx, SN.viento(t_desc - t_erup + 2, 1.3), t_erup, 0.8)
    poner(sfx, SN.impacto(), t_cat - 0.05, 0.6)
    poner(sfx, SN.latido(t_desc - t_cat - 0.3, 72), t_cat, 0.8)
    poner(sfx, SN.viento(total - t_desc, 0.5), t_desc, 0.6)
    for c in clips[1:]:
        poner(sfx, SN.whoosh(0.9), c["t0"] - 0.45, 0.35)
    poner(sfx, SN.impacto(), fin_voz + 0.1, 0.5)                           # tarjeta final

    # la música baja cuando habla el narrador
    env = np.abs(voz[:, 0])
    env = signal.lfilter([1 - 0.9995], [1, -0.9995], (env > 0.02).astype(np.float32))
    presencia = np.clip(env * 4, 0, 1)
    mezcla = voz * 1.0 + musica * (0.5 - 0.3 * presencia[:, None]) + sfx * (0.6 - 0.2 * presencia[:, None])
    fade = SN.seg(1.0)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sf.write(salida / "audio.wav", SN.normal(mezcla, 0.95), sr)


def lluvia_pomez(dur):
    """Granizo de piedra pómez sobre tejados y adoquines."""
    n = SN.seg(dur)
    out = np.zeros((n, 2), np.float32)
    golpe = SN.seg(0.05)
    for _ in range(int(dur * 22)):
        k = int(SN.rng.integers(0, n - golpe))
        g = SN.bp(SN.ruido(golpe), 600, 4000) * SN.env_exp(golpe, 0.006) * SN.rng.uniform(0.2, 1.0)
        pan = SN.rng.uniform(-1, 1)
        out[k: k + golpe, 0] += g * (1 - pan) / 2
        out[k: k + golpe, 1] += g * (1 + pan) / 2
    out *= np.minimum(1, np.linspace(0, 3, n))[:, None]
    return SN.reverb(out, 1.2, 0.25)


# ---------------------------------------------------------------------- imagen
def fuente(ruta, tam, peso=None):
    f = ImageFont.truetype(str(ruta), tam)
    if peso:
        f.set_variation_by_axes([peso])
    return f


def suave(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def encuadre(img, zoom, cx, cy, dx=0.0, dy=0.0):
    """Recorta un cuadro 9:16 de la imagen (con zoom y centro dados) y lo escala a 1080×1920."""
    iw, ih = img.size
    h = ih / zoom
    w = h * W / H
    if w > iw:
        w, h = iw, iw * H / W
    x = min(max(cx * iw + dx - w / 2, 0), iw - w)
    y = min(max(cy * ih + dy - h / 2, 0), ih - h)
    return img.transform((W, H), Image.EXTENT, (x, y, x + w, y + h), Image.BICUBIC)


def cuadro_clip(clip, t, img):
    z0, z1, (x0, y0), (x1, y1) = CAMARA[clip["img"]]
    u = suave((t - clip["t0"] + TRANS) / (clip["t1"] - clip["t0"] + 2 * TRANS))
    dx = dy = 0.0
    if clip["escena"] in ("erupcion", "catastrofe"):  # temblor del suelo
        fuerza = 14 * math.exp(-(t - clip["t0"]) * 1.2) + 3
        dx = fuerza * math.sin(t * 47.0) * math.sin(t * 13.0)
        dy = fuerza * math.sin(t * 39.0 + 1.0)
    return encuadre(img, z0 + (z1 - z0) * u, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, dx, dy)


def mezclar(a, b, alfa):
    return Image.blend(a, b, alfa) if alfa > 0 else a


def humo(semilla):
    """Textura de nube oscura (ruido fractal) para la nube que avanza sobre la ciudad."""
    r = np.random.default_rng(semilla)
    capa = np.zeros((H + 600, W), np.float32)
    for oct_, peso in ((8, 1.0), (16, 0.5), (32, 0.25), (64, 0.12)):
        ruido = r.random((max(2, (H + 600) * oct_ // W), oct_)).astype(np.float32)
        capa += np.asarray(Image.fromarray(ruido).resize((W, H + 600), Image.BICUBIC)) * peso
    capa = (capa - capa.min()) / (capa.max() - capa.min())
    return capa


class Particulas:
    def __init__(self, n, semilla, tam, vel, color, deriva):
        r = np.random.default_rng(semilla)
        self.x, self.y = r.random(n) * W, r.random(n) * (H + 200)
        self.s = r.uniform(*tam, n)
        self.v = r.uniform(*vel, n)
        self.f = r.random(n) * 6.28
        self.a = r.uniform(0.35, 1.0, n)
        self.color, self.deriva = color, deriva

    def dibujar(self, capa, t, intensidad):
        if intensidad <= 0:
            return
        d = ImageDraw.Draw(capa)
        y = (self.y + self.v * t) % (H + 200) - 100
        x = (self.x + self.deriva * t + 25 * np.sin(t * 0.9 + self.f)) % W
        for xi, yi, si, ai, vi in zip(x, y, self.s, self.a, self.v):
            alfa = int(255 * ai * intensidad)
            largo = si * (1 + abs(vi) / 300)
            d.ellipse((xi - si, yi - largo, xi + si, yi + largo), fill=self.color + (alfa,))


def vineta():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    a = np.clip((r - 0.55) * 1.4, 0, 0.75)
    a[: 320] = np.maximum(a[: 320], np.linspace(0.5, 0, 320)[:, None])         # sombra arriba (marca del canal)
    a[1100:] = np.maximum(a[1100:], np.linspace(0, 0.55, H - 1100)[:, None])   # sombra abajo (subtítulos)
    capa = np.zeros((H, W, 4), np.uint8)
    capa[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(capa, "RGBA")


def texto_con_borde(lineas, fnt, borde=9, sombra=True, interlineado=1.08):
    """lineas: lista de listas de (palabra, color). Devuelve una imagen RGBA centrada."""
    espacio = fnt.getlength(" ")
    alto = int(fnt.size * interlineado)
    anchos = [sum(fnt.getlength(p) for p, _ in l) + espacio * (len(l) - 1) for l in lineas]
    cw, ch = int(max(anchos)) + 4 * borde + 40, alto * len(lineas) + 4 * borde + 40
    capa = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for i, (l, ancho) in enumerate(zip(lineas, anchos)):
        x, y = (cw - ancho) / 2, 20 + 2 * borde + i * alto
        for p, col in l:
            d.text((x, y), p, font=fnt, fill=col + (255,), stroke_width=borde, stroke_fill=(0, 0, 0, 255))
            x += fnt.getlength(p) + espacio
    if sombra:
        s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        s.putalpha(capa.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.6))
        fondo = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        fondo.alpha_composite(s, (0, 8))
        fondo.alpha_composite(capa)
        capa = fondo
    return capa


def subtitulo(frag):
    """Fragmento en mayúsculas, como máximo 2 líneas dentro del ancho seguro."""
    palabras = [(p.upper(), AMARILLO if r else BLANCO) for p, r in frag]
    for tam in range(84, 50, -4):
        fnt = fuente(F_SUB, tam, 900)
        esp = fnt.getlength(" ")
        lineas, actual, ancho = [], [], 0
        for p, c in palabras:
            w = fnt.getlength(p)
            if actual and ancho + esp + w > SUB_ANCHO:
                lineas.append(actual)
                actual, ancho = [], 0
            actual.append((p, c))
            ancho += (esp if ancho else 0) + w
        lineas.append(actual)
        if len(lineas) <= 2 and all(sum(fnt.getlength(p) for p, _ in l) < SUB_ANCHO for l in lineas):
            break
    return texto_con_borde(lineas, fnt, borde=max(6, tam // 9))


def marca_canal():
    fnt = fuente(F_SUB, 34, 800)
    texto = " ".join(CANAL)  # letras espaciadas
    ancho = fnt.getlength(texto)
    capa = Image.new("RGBA", (int(ancho) + 80, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.text((40, 14), texto, font=fnt, fill=(255, 255, 255, 235), stroke_width=3, stroke_fill=(0, 0, 0, 200))
    d.line((40, 64, 40 + ancho, 64), fill=AMARILLO + (230,), width=3)
    return capa


def titulo_inicial():
    capa = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
    t1 = texto_con_borde([[("POMPEYA", BLANCO)]], fuente(F_TITULO, 170, 900), borde=8)
    t2 = texto_con_borde([[("LA CIUDAD QUE", BLANCO), ("DESAPARECIÓ", AMARILLO)]], fuente(F_SUB, 54, 900), borde=6)
    capa.alpha_composite(t1, ((W - t1.width) // 2, 0))
    capa.alpha_composite(t2, ((W - t2.width) // 2, t1.height - 40))
    return capa


def tarjeta_final():
    capa = Image.new("RGBA", (W, 600), (0, 0, 0, 0))
    a = texto_con_borde([[("CURIOSIDADES", BLANCO)]], fuente(F_ANTON, 150), borde=7)
    b = texto_con_borde([[("DEL MUNDO", AMARILLO)]], fuente(F_ANTON, 150), borde=7)
    capa.alpha_composite(a, ((W - a.width) // 2, 0))
    capa.alpha_composite(b, ((W - b.width) // 2, a.height - 70))
    d = ImageDraw.Draw(capa)
    y = a.height + b.height - 70
    d.line((W / 2 - 260, y, W / 2 + 260, y), fill=AMARILLO + (255,), width=5)
    return capa


def pegar(base, capa, cx, cy, escala=1.0, alfa=1.0):
    if alfa <= 0.01:
        return
    if abs(escala - 1) > 0.005:
        capa = capa.resize((max(1, int(capa.width * escala)), max(1, int(capa.height * escala))), Image.BICUBIC)
    if alfa < 0.99:
        capa = capa.copy()
        capa.putalpha(capa.getchannel("A").point(lambda v: int(v * alfa)))
    base.alpha_composite(capa, (int(cx - capa.width / 2), int(cy - capa.height / 2)))


# ---------------------------------------------------------------------- render
def render(salida, subs, escenas, clips, fin_voz, total, desde=0.0, hasta=None):
    hasta = hasta or total
    imgs = {c["img"]: Image.open(salida / "escenas" / f"{c['img']:02d}.png").convert("RGB") for c in clips}
    sub_imgs = [subtitulo(fr) for _, _, fr in subs]
    marca, titulo, final, vin = marca_canal(), titulo_inicial(), tarjeta_final(), vineta()
    ceniza = Particulas(260, 1, (1.5, 4.5), (220, 520), (70, 66, 62), 40)
    pomez = Particulas(70, 2, (4, 9), (700, 1100), (45, 42, 40), 20)
    polvo = Particulas(60, 3, (1.2, 3.0), (-30, -10), (255, 220, 150), 15)
    nube = humo(5)
    granos = [Image.fromarray(np.random.default_rng(i).normal(128, 18, (H // 2, W // 2)).clip(0, 255)
                              .astype(np.uint8)).resize((W, H)) for i in range(6)]
    t_e = {e["nombre"]: (t0, t1) for t0, t1, e in escenas}
    t_erup, t_cat, t_desc = t_e["erupcion"][0], t_e["catastrofe"][0], t_e["descubrimiento"][0]

    video = salida / ("prueba.mp4" if desde > 0 or hasta < total else "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "18", "-pix_fmt", "yuv420p", str(video)], stdin=subprocess.PIPE)
    n0, n1 = int(desde * FPS), int(hasta * FPS)
    for fr in range(n0, n1):
        t = fr / FPS
        # imagen de fondo con transición tipo "zoom" entre clips
        i = max(k for k, c in enumerate(clips) if c["t0"] - 1e-6 <= t or k == 0)
        c = clips[i]
        cuadro = cuadro_clip(c, t, imgs[c["img"]])
        if i + 1 < len(clips) and t > clips[i + 1]["t0"] - TRANS:
            sig = clips[i + 1]
            u = (t - (sig["t0"] - TRANS)) / TRANS
            cuadro = mezclar(cuadro, cuadro_clip(sig, t, imgs[sig["img"]]), suave(u))
        elif i > 0 and t < c["t0"] + 0.02:
            pass
        cuadro = cuadro.convert("RGBA")

        # efectos por escena
        if t < t_erup:  # el cielo se oscurece en el gancho y al final de la vida normal
            osc = 0.45 * suave(t / 5.0) if t < 5.5 else 0.25
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            grad = np.linspace(1, 0, H // 2)[:, None] * np.ones((1, W))
            capa.putalpha(Image.fromarray((grad * 255 * osc).astype(np.uint8)).resize((W, H)))
            cuadro.alpha_composite(capa)
        if t_erup <= t < t_desc:
            k = (t - t_erup) / (t_desc - t_erup)
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ceniza.dibujar(capa, t, min(1, (t - t_erup) / 2.5))
            pomez.dibujar(capa, t, min(1, max(0, (t - t_erup - 3) / 2)) * (1 - max(0, k - 0.8) * 5))
            cuadro.alpha_composite(capa)
            if t >= t_cat:  # nube oscura avanzando
                kk = (t - t_cat) / (t_desc - t_cat)
                off = int((1 - kk) * 600)
                a = np.clip((nube[off: off + H] - 0.45) * 2.2, 0, 1) * min(0.85, 0.2 + kk * 0.9)
                a *= np.clip(np.linspace(1.4, -0.2, H), 0, 1)[:, None] * 0.6 + kk * 0.5
                humo_c = np.zeros((H, W, 4), np.uint8)
                humo_c[..., :3] = (35, 30, 28)
                humo_c[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
                cuadro.alpha_composite(Image.fromarray(humo_c, "RGBA"))
            tinte = Image.new("RGBA", (W, H), (120, 40, 10, int(40 + 30 * k)))
            cuadro.alpha_composite(tinte)
        if t >= t_desc:
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            polvo.dibujar(capa, t, 0.5 * min(1, (t - t_desc) / 1.5))
            cuadro.alpha_composite(capa)
        flash = 0.0
        for tf, f0 in ((t_erup, 0.75), (t_cat, 0.35)):
            if tf <= t < tf + 0.5:
                flash = max(flash, f0 * (1 - (t - tf) / 0.5) ** 2)
        if flash:
            cuadro.alpha_composite(Image.new("RGBA", (W, H), (255, 235, 210, int(255 * flash))))
        if t < 0.5:  # aparición desde negro
            cuadro.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / 0.5)))))

        cuadro.alpha_composite(vin)
        # grano de película
        rgb = Image.blend(cuadro.convert("RGB"), Image.merge("RGB", [granos[fr % 6]] * 3), 0.05)
        cuadro = rgb.convert("RGBA")

        # textos
        en_final = t >= fin_voz
        if t < 4.6:
            u = suave((t - 0.25) / 0.6) * (1 - suave((t - 4.0) / 0.6))
            pegar(cuadro, titulo, W / 2, 560, 0.92 + 0.08 * suave((t - 0.25) / 0.6) + 0.02 * t, u)
        if not en_final:
            pegar(cuadro, marca, W / 2, 230, 1.0, suave(t / 0.8) if t < 4.6 else 1.0)
        for (a, b, _), img in zip(subs, sub_imgs):
            if a <= t < b:
                p = (t - a) / 0.16
                escala = 0.82 + 0.23 * suave(p) - 0.05 * suave(p - 1) if p < 2 else 1.0
                pegar(cuadro, img, W / 2, SUB_Y, escala, min(1, p * 1.6))
        if en_final:
            u = suave((t - fin_voz) / 0.5)
            cuadro.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(140 * u))))
            pegar(cuadro, final, W / 2, 880, 0.9 + 0.1 * u + 0.015 * (t - fin_voz), u)
        if t > total - 0.6:
            cuadro.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * suave((t - total + 0.6) / 0.6)))))
        ff.stdin.write(cuadro.convert("RGB").tobytes())
        if fr % 150 == 0:
            print(f"  {t:5.1f} / {hasta:.1f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    return video


def srt(salida, subs):
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    bloques = [f"{i}\n{ts(a)} --> {ts(b)}\n{' '.join(p for p, _ in fr)}\n" for i, (a, b, fr) in enumerate(subs, 1)]
    (salida / "pompeya.srt").write_text("\n".join(bloques), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("salida", type=Path)
    ap.add_argument("--prueba", nargs=2, type=float, metavar=("INICIO", "FIN"))
    a = ap.parse_args()
    voz = json.loads((a.salida / "voz.json").read_text())
    frases, subs, escenas, clips, fin_voz, total = linea_de_tiempo(voz)
    print(f"Duración total: {total:.1f} s · {len(clips)} imágenes · {len(subs)} subtítulos")
    srt(a.salida, subs)
    if a.prueba:
        render(a.salida, subs, escenas, clips, fin_voz, total, *a.prueba)
        sys.exit()
    print("Audio…")
    sonido(a.salida, frases, escenas, clips, fin_voz, total)
    print("Video…")
    video = render(a.salida, subs, escenas, clips, fin_voz, total)
    final = a.salida / "Pompeya_Curiosidades_del_Mundo.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(a.salida / "audio.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
                    str(final)], check=True)
    print(f"Listo: {final}")
