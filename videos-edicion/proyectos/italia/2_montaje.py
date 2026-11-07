"""Montaje del documental de Italia: imágenes + voz + música + efectos -> MP4 1080p.

Uso:
  python3 2_montaje.py salida audio1.mp3 audio2.mp3 audio3.mp3 [--procesos 4] [--prueba INI FIN]
"""
import argparse
import json
import math
import subprocess
from multiprocessing import Process
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

import plan
import sonido as SN

W, H, FPS = 1920, 1080, 30
INTRO = 13.0          # segundos de apertura antes de la primera voz
PAUSA = 0.8           # silencio entre un audio y el siguiente
OUTRO = 8.0
FUNDIDO = 0.7         # duración de los fundidos entre imágenes
CAP_DUR = 4.6         # duración de los rótulos de capítulo
FUENTES = Path(__file__).parent / "fuentes"
ORO = (226, 185, 92)


def fuente(nombre, tam):
    return ImageFont.truetype(str(FUENTES / nombre), tam)


def suave(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# =================================================================== línea de tiempo
def linea_de_tiempo(sal, audios):
    dur = [sf.info(a).duration for a in audios]
    off = [INTRO]
    for d in dur[:-1]:
        off.append(off[-1] + d + PAUSA)
    total = off[-1] + dur[-1] + OUTRO
    imgs = json.loads((sal / "imagenes.json").read_text())

    escenas = []
    for ia, lista in enumerate(plan.AUDIOS):
        for n, (t, q) in enumerate(lista):
            clave = f"{ia}_{n:03d}"
            if clave in imgs and clave not in plan.OMITIR and (sal / "img" / f"{clave}.jpg").exists():
                escenas.append({"ini": off[ia] + t, "img": clave})
    escenas.sort(key=lambda e: e["ini"])
    for a, b in zip(escenas, escenas[1:]):
        a["fin"] = b["ini"]
    escenas[-1]["fin"] = total - OUTRO + 1.0

    caps = []
    for c in plan.CAPITULOS:
        ia, t, *txt = c
        caps.append({"ini": off[ia] + t, "txt": txt})
    musica = [(off[ia] + t, est) for ia, t, est in plan.MUSICA]
    musica[0] = (0.0, "epico")
    return {"dur": dur, "off": off, "total": total, "escenas": escenas, "caps": caps,
            "musica": musica, "imgs": imgs}


def clave_de(imgs, texto):
    for k, v in imgs.items():
        if texto.lower() in v.get("busqueda", "").lower():
            return k
    return next(iter(imgs))


# =================================================================== audio
def hacer_audio(sal, audios, tl):
    n = SN.seg(tl["total"])
    voz = np.zeros(n, np.float32)
    for a, o in zip(audios, tl["off"]):
        x, sr = sf.read(a, dtype="float32", always_2d=True)
        x = x.mean(1)
        if sr != SN.SR:
            from scipy.signal import resample_poly
            x = resample_poly(x, SN.SR, sr).astype(np.float32)
        i = SN.seg(o)
        voz[i: i + len(x)] += x[: n - i]
    voz = voz / (np.abs(voz).max() + 1e-6) * 0.92

    # presencia de voz -> la música baja cuando se habla
    bloque = 2205
    m = len(voz) // bloque * bloque
    rms = np.sqrt((voz[:m].reshape(-1, bloque) ** 2).mean(1))
    pres = (rms > 0.02).astype(np.float32)
    sv = np.zeros_like(pres)
    for i in range(1, len(pres)):
        coef = 0.35 if pres[i] > sv[i - 1] else 0.015
        sv[i] = sv[i - 1] + (pres[i] - sv[i - 1]) * coef
    presencia = np.pad(np.repeat(sv, bloque), (0, n - m))[:n]

    print("  música...", flush=True)
    musica = np.zeros((n, 2), np.float32)
    secs = tl["musica"] + [(tl["total"], None)]
    for (t0, est), (t1, _) in zip(secs, secs[1:]):
        mm = SN.musica(est, t1 - t0 + 3.0)
        i = SN.seg(max(0, t0 - 1.5))
        musica[i: i + len(mm)] += mm[: n - i]
    # la música de la apertura empieza al aparecer la bandera
    k = SN.seg(10.3)
    musica[:k] = 0
    musica[k: k + SN.seg(0.5)] *= np.linspace(0, 1, SN.seg(0.5))[:, None]
    # salida: subir y apagar
    fin = SN.seg(tl["total"])
    musica[fin - SN.seg(3):] *= np.linspace(1, 0, SN.seg(3))[:, None]

    print("  efectos...", flush=True)
    fx = np.zeros((n, 2), np.float32)

    def poner(s, t, v):
        i = SN.seg(max(0, t))
        fx[i: i + len(s)] += s[: n - i] * v

    imp, wh, tb = SN.impacto(), SN.whoosh(1.4), SN.timbal(41.2)
    wh_corto = SN.whoosh(0.6)
    # --- apertura: latido, golpes en cada destello, redoble y gran impacto con la bandera
    poner(SN.latido(9.5, 72), 0.0, 0.9)
    poner(SN.estereo(SN.lp(SN.ruido(SN.seg(10.5)), 90, 4)) * np.linspace(0, 1, SN.seg(10.5))[:, None] ** 2, 0.0, 0.7)
    for t in INTRO_GOLPES:
        poner(wh_corto, t - 0.45, 0.5)
        poner(imp, t, 0.42)
        poner(tb, t, 0.4)
    redoble = SN.tambor_militar(2.0, 160, volumen=0.9)
    redoble *= np.linspace(0.2, 1.0, len(redoble))[:, None]
    poner(redoble, 8.3, 0.6)
    poner(SN.whoosh(2.2, True), 8.4, 0.7)
    poner(imp, 10.5, 0.8)
    poner(tb, 10.5, 0.9)
    poner(SN.campana(98.0, 8.0), 10.55, 0.35)
    # --- capítulos: whoosh + golpe
    for c in tl["caps"]:
        poner(wh, c["ini"] - 1.0, 0.55)
        poner(imp, c["ini"], 0.6)
    # --- ambientes en momentos clave
    off = tl["off"]
    for ia, t, nombre, d, v in AMBIENTES:
        s = getattr(SN, nombre)(d)
        f = min(len(s), SN.seg(1.0))
        s[:f] *= np.linspace(0, 1, f)[:, None]
        s[-f:] *= np.linspace(1, 0, f)[:, None]
        poner(s, off[ia] + t, v)
    # --- final: golpe con el logotipo
    poner(imp, tl["total"] - OUTRO + 0.6, 0.7)
    poner(SN.campana(130.8, 7.0), tl["total"] - OUTRO + 0.6, 0.3)

    mezcla = (voz[:, None] * 1.0
              + musica * (0.50 - 0.32 * presencia[:, None])
              + fx * (0.80 - 0.45 * presencia[:, None]))
    mezcla = np.tanh(mezcla * 1.1) / np.tanh(1.1)
    mezcla = SN.normal(mezcla, 0.95)
    ruta = sal / "audio_final.wav"
    sf.write(ruta, mezcla, SN.SR, subtype="PCM_16")
    return ruta


# instantes (s) de los cortes de la apertura
INTRO_GOLPES = [1.6, 2.75, 3.9, 5.05, 6.2, 7.35]
INTRO_PALABRAS = ["IMPERIOS", "GUERRAS", "TRAICIONES", "CONQUISTAS", "GLORIA", "2.700 AÑOS"]
INTRO_IMGS = ["Pollice Verso", "Hannibal crossing", "Death of Caesar", "Colosseum at night",
              "Napoleon Crossing", "Roman legionaries reenactment"]

# (audio, segundo, efecto de sonido.py, duración, volumen)
AMBIENTES = [
    (0, 236.3, "batalla", 9.0, 0.22),
    (0, 246.9, "viento", 12.0, 0.35),
    (0, 303.9, "batalla", 7.0, 0.2),
    (0, 315.7, "caballos", 7.0, 0.3),
    (0, 412.6, "batalla", 10.0, 0.12),
    (1, 39.4, "fuego", 10.0, 0.3),
    (1, 64.1, "batalla", 7.0, 0.2),
    (1, 118.1, "olas", 10.0, 0.3),
    (1, 269.6, "batalla", 9.0, 0.2),
    (1, 305.4, "caballos", 8.0, 0.25),
    (2, 5.6, "batalla", 12.0, 0.22),
    (2, 53.8, "batalla", 12.0, 0.22),
    (2, 177.6, "olas", 7.0, 0.25),
]


# =================================================================== imágenes
def preparar(ruta, escala=1.14):
    """Imagen graduada y ampliada a un lienzo algo mayor que el cuadro (para el movimiento)."""
    im = Image.open(ruta)
    im = ImageOps.exif_transpose(im).convert("RGB")
    cw, ch = int(W * escala), int(H * escala)
    asp = im.width / im.height
    if asp >= 1.55:
        im = ImageOps.fit(im, (cw, ch), Image.LANCZOS, centering=(0.5, 0.45))
    else:
        # vertical o cuadrada: fondo desenfocado + imagen completa encima
        fondo = ImageOps.fit(im, (cw // 4, ch // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(9))
        fondo = ImageEnhance.Brightness(fondo.resize((cw, ch), Image.BILINEAR)).enhance(0.45)
        alto = ch
        ancho = int(alto * asp)
        if ancho > cw * 0.92:
            ancho = int(cw * 0.92)
            alto = int(ancho / asp)
        fg = im.resize((ancho, alto), Image.LANCZOS)
        sombra = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(sombra).rectangle([(cw - ancho) // 2 - 10, (ch - alto) // 2 - 10,
                                          (cw + ancho) // 2 + 10, (ch + alto) // 2 + 10], fill=170)
        sombra = sombra.filter(ImageFilter.GaussianBlur(25))
        fondo.paste(Image.new("RGB", (cw, ch), 0), (0, 0), sombra)
        fondo.paste(fg, ((cw - ancho) // 2, (ch - alto) // 2))
        im = fondo
    # gradación cinematográfica: contraste, color y un toque cálido en las luces
    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = ImageEnhance.Color(im).enhance(1.18)
    a = np.asarray(im).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True)
    a = a + (lum - 0.5) * np.array([0.05, 0.015, -0.05], np.float32)  # luces cálidas, sombras frías
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def vineta():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return np.clip(1 - 0.42 * np.clip(d - 0.55, 0, None) ** 1.6, 0, 1)[..., None].astype(np.float32)


def recorte(lienzo, u, idx, zoom_extra=0.0, sacudida=0.0):
    """Movimiento Ken Burns: acercar/alejar y desplazar según el índice de la escena."""
    cw, ch = lienzo.size
    modo = idx % 4
    u = suave(u) * 0.85 + u * 0.15
    if modo in (0, 2):
        z = 1.0 + 0.11 * u
    else:
        z = 1.11 - 0.11 * u
    z += zoom_extra
    vw, vh = cw / z, ch / z
    vw, vh = min(vw, cw), min(vh, ch)
    dx = {0: 0.5, 1: 0.5 - 0.35 * (u - 0.5), 2: 0.35 + 0.3 * u, 3: 0.65 - 0.3 * u}[modo]
    dy = 0.5
    x0 = (cw - vw) * dx + sacudida * np.random.uniform(-1, 1) * 12
    y0 = (ch - vh) * dy + sacudida * np.random.uniform(-1, 1) * 12
    x0 = min(max(x0, 0), cw - vw)
    y0 = min(max(y0, 0), ch - vh)
    im = lienzo.transform((W, H), Image.AFFINE, (vw / W, 0, x0, 0, vh / H, y0), Image.BILINEAR)
    return np.asarray(im).astype(np.float32) / 255


# =================================================================== textos
def capa_texto(dibujar):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dibujar(ImageDraw.Draw(im), im)
    a = np.asarray(im).astype(np.float32) / 255
    return a[..., :3], a[..., 3:]


def texto_espaciado(d, xy, txt, f, fill, esp, ancla="mm"):
    ancho = sum(d.textlength(c, font=f) for c in txt) + esp * (len(txt) - 1)
    x, y = xy
    x = x - ancho / 2 if ancla == "mm" else x - ancho
    for c in txt:
        d.text((x, y), c, font=f, fill=fill, anchor="lm")
        x += d.textlength(c, font=f) + esp
    return ancho


def marca_agua():
    def dib(d, im):
        f = fuente("montserrat-latin-200-normal.woff", 26)
        txt = "GIGA CURIOSIDADES DEL MUNDO"
        # sombra suave para que se lea sobre cualquier fondo
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sombra)
        texto_espaciado(ds, (W - 46, 52), txt, f, (0, 0, 0, 150), 4, "rm")
        sombra = sombra.filter(ImageFilter.GaussianBlur(3))
        im.alpha_composite(sombra)
        texto_espaciado(d, (W - 48, 50), txt, f, (255, 255, 255, 225), 4, "rm")
        anc = sum(d.textlength(c, font=f) for c in txt) + 4 * (len(txt) - 1)
        d.line([(W - 48 - anc, 70), (W - 48 - anc + 46, 70)], fill=ORO + (200,), width=1)
    return capa_texto(dib)


def rotulo_capitulo(txt):
    numero, titulo = txt[0], txt[1]
    sub = txt[2] if len(txt) > 2 else ""

    def dib(d, im):
        f1 = fuente("montserrat-latin-600-normal.woff", 30)
        f2 = fuente("cinzel-latin-700-normal.woff", 104 if len(titulo) < 20 else 86)
        f3 = fuente("montserrat-latin-300-normal.woff", 40)
        y = H / 2 - (30 if sub else 0)
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sombra)
        ds.text((W / 2, y + 4), titulo.upper(), font=f2, fill=(0, 0, 0, 230), anchor="mm")
        sombra = sombra.filter(ImageFilter.GaussianBlur(10))
        im.alpha_composite(sombra)
        anc = texto_espaciado(d, (W / 2, y - 105), numero, f1, ORO + (255,), 9)
        d.line([(W / 2 - anc / 2 - 130, y - 105), (W / 2 - anc / 2 - 30, y - 105)], fill=ORO + (220,), width=2)
        d.line([(W / 2 + anc / 2 + 30, y - 105), (W / 2 + anc / 2 + 130, y - 105)], fill=ORO + (220,), width=2)
        d.text((W / 2, y), titulo.upper(), font=f2, fill=(250, 246, 236, 255), anchor="mm")
        if sub:
            d.text((W / 2, y + 100), sub, font=f3, fill=(235, 230, 220, 240), anchor="mm")
    return capa_texto(dib)


def palabra_intro(p):
    def dib(d, im):
        f = fuente("cinzel-latin-900-normal.woff", 150)
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).text((W / 2, H / 2 + 6), p, font=f, fill=(0, 0, 0, 255), anchor="mm")
        im.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(14)))
        d.text((W / 2, H / 2), p, font=f, fill=(255, 250, 240, 255), anchor="mm")
    return capa_texto(dib)


def titulo_principal():
    def dib(d, im):
        f = fuente("cinzel-latin-900-normal.woff", 270)
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sombra)
        ds.text((W / 2, H / 2 - 40), "ITALIA", font=f, fill=(0, 0, 0, 255), anchor="mm")
        im.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(22)))
        im.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(6)))
        # degradado dorado dentro de las letras
        mascara = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mascara).text((W / 2, H / 2 - 40), "ITALIA", font=f, fill=255, anchor="mm",
                                     stroke_width=0)
        grad = np.zeros((H, W, 4), np.uint8)
        yy = np.linspace(0, 1, H)[:, None]
        g = np.clip(1 - np.abs(yy - 0.42) * 3.2, 0, 1)
        grad[..., 0] = (200 + 55 * g).astype(np.uint8)
        grad[..., 1] = (150 + 90 * g).astype(np.uint8)
        grad[..., 2] = (60 + 130 * g).astype(np.uint8)
        grad[..., 3] = np.asarray(mascara)
        im.alpha_composite(Image.fromarray(grad, "RGBA"))
    return capa_texto(dib)


def subtitulo_principal():
    def dib(d, im):
        f = fuente("montserrat-latin-300-normal.woff", 40)
        banda = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(banda).rectangle([0, H / 2 + 105, W, H / 2 + 255], fill=(0, 0, 0, 200))
        im.alpha_composite(banda.filter(ImageFilter.GaussianBlur(24)))
        f = fuente("montserrat-latin-600-normal.woff", 46)
        texto_espaciado(d, (W / 2, H / 2 + 150), "EL NACIMIENTO DE UN IMPERIO", f, (255, 255, 255, 255), 10)
        f2 = fuente("montserrat-latin-300-normal.woff", 38)
        texto_espaciado(d, (W / 2, H / 2 + 212), "y la historia de una nación eterna", f2, ORO + (255,), 3)
    return capa_texto(dib)


def cierre():
    def dib(d, im):
        f1 = fuente("montserrat-latin-200-normal.woff", 30)
        f2 = fuente("cinzel-latin-700-normal.woff", 92)
        f3 = fuente("montserrat-latin-300-normal.woff", 34)
        texto_espaciado(d, (W / 2, H / 2 - 120), "GRACIAS POR VER", f1, ORO + (255,), 10)
        d.text((W / 2, H / 2), "GIGA CURIOSIDADES", font=f2, fill=(250, 246, 236, 255), anchor="mm")
        texto_espaciado(d, (W / 2, H / 2 + 90), "DEL MUNDO", f1, (250, 246, 236, 255), 14)
        d.line([(W / 2 - 160, H / 2 + 150), (W / 2 + 160, H / 2 + 150)], fill=ORO + (220,), width=2)
        d.text((W / 2, H / 2 + 200), "Suscríbete para más historias", font=f3, fill=(235, 230, 220, 230),
               anchor="mm")
    return capa_texto(dib)


def poner_capa(fr, capa, alfa):
    if alfa <= 0.001:
        return fr
    rgb, a = capa
    a = a * alfa
    return fr * (1 - a) + rgb * a


# =================================================================== bandera ondeando
class Bandera:
    def __init__(self):
        self.y, self.x = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)

    def cuadro(self, t):
        x, y = self.x / (W / 2), self.y / (H / 2)
        fase = 7.0 * x - 2.6 * t
        amp = 0.035 * (0.3 + x)
        yy = 0.06 + 0.88 * y + amp * np.sin(fase) + 0.01 * np.sin(13 * x - 4.1 * t)
        xx = x + 0.012 * np.sin(5 * y + 1.7 * t) * x
        colores = np.zeros(x.shape + (3,), np.float32)
        verde = np.array([0, 146, 70]) / 255
        blanco = np.array([244, 245, 240]) / 255
        rojo = np.array([206, 43, 55]) / 255
        colores[xx < 1 / 3] = verde
        colores[(xx >= 1 / 3) & (xx < 2 / 3)] = blanco
        colores[xx >= 2 / 3] = rojo
        luz = 0.78 + 0.32 * np.cos(fase - 0.6) * (0.4 + x) + 0.06 * np.sin(13 * x - 4.1 * t)
        img = colores * np.clip(luz, 0.3, 1.25)[..., None]
        img = np.clip(img, 0, 1)
        im = Image.fromarray((img * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        return np.asarray(im).astype(np.float32) / 255


# =================================================================== render
class Render:
    def __init__(self, sal, tl):
        self.sal, self.tl = sal, tl
        self.escenas = tl["escenas"]
        self.cache = {}
        self.vin = vineta()
        self.marca = marca_agua()
        self.caps = [(c["ini"], rotulo_capitulo(c["txt"])) for c in tl["caps"]]
        self.palabras = [palabra_intro(p) for p in INTRO_PALABRAS]
        disp = {k: v for k, v in tl["imgs"].items() if (sal / "img" / f"{k}.jpg").exists()}
        self.intro_imgs = [clave_de(disp, q) for q in INTRO_IMGS]
        self.titulo = titulo_principal()
        self.subtitulo = subtitulo_principal()
        self.cierre = cierre()
        self.bandera = Bandera()
        rng = np.random.default_rng(7)
        self.grano = [np.repeat(np.repeat(rng.normal(0, 0.022, (H // 2, W // 2, 1)).astype(np.float32), 2, 0), 2, 1)
                      for _ in range(6)]
        self.idx = {e["img"]: i for i, e in enumerate(self.escenas)}

    def lienzo(self, clave):
        if clave not in self.cache:
            if len(self.cache) > 6:
                self.cache.pop(next(iter(self.cache)))
            self.cache[clave] = preparar(self.sal / "img" / f"{clave}.jpg")
        return self.cache[clave]

    def escena(self, e, t, i):
        u = (t - e["ini"] + FUNDIDO) / (e["fin"] - e["ini"] + 2 * FUNDIDO)
        return recorte(self.lienzo(e["img"]), u, i)

    def apertura(self, t):
        g = INTRO_GOLPES
        fr = np.zeros((H, W, 3), np.float32)
        if t < g[0]:
            return fr
        if t < 8.5:
            k = max(i for i, x in enumerate(g) if x <= t)
            u = (t - g[k]) / 1.15
            img = recorte(self.lienzo(self.intro_imgs[k]), u * 0.5, k, zoom_extra=0.08 * (1 - u),
                          sacudida=max(0, 1 - u * 4))
            # blanco y negro con tinte rojo/dorado, muy contrastado
            lum = img.mean(2, keepdims=True)
            img = np.clip((lum - 0.5) * 1.5 + 0.5, 0, 1) * np.array([1.0, 0.82, 0.62], np.float32)
            img *= suave(min(1, (8.5 - t) / 0.3))
            fr = poner_capa(img, self.palabras[k], suave((t - g[k] - 0.1) / 0.15) * (1 - suave((u - 0.8) / 0.2)))
            flash = max(0, 1 - (t - g[k]) / 0.18)
            fr = fr + (1 - fr) * flash
            return fr
        if t < 10.5:
            return fr
        # bandera + título
        fb = self.bandera.cuadro(t) * 0.88
        fb = fb * (0.75 + 0.25 * suave((t - 10.5) / 2))
        brasas = self.brasas(t)
        fr = np.clip(fb + brasas, 0, 1)
        e = suave((t - 10.5) / 0.5)
        fr = poner_capa(fr, self.titulo, e)
        fr = poner_capa(fr, self.subtitulo, suave((t - 12.0) / 1.0))
        flash = max(0, 1 - (t - 10.5) / 0.35)
        return fr + (1 - fr) * flash

    def brasas(self, t):
        rng = np.random.default_rng(3)
        capa = np.zeros((H // 4, W // 4, 3), np.float32)
        n = 90
        x0 = rng.uniform(0, W // 4, n)
        vel = rng.uniform(12, 35, n)
        fase = rng.uniform(0, 100, n)
        for i in range(n):
            yy = (H // 4) - ((t * vel[i] + fase[i] * 3) % (H // 4 + 20))
            xx = x0[i] + 6 * math.sin(t * 1.3 + fase[i])
            if 0 <= yy < H // 4 - 1 and 0 <= xx < W // 4 - 1:
                b = 0.6 + 0.4 * math.sin(t * 5 + fase[i])
                capa[int(yy), int(xx)] += np.array([1.0, 0.55, 0.15]) * b
        im = Image.fromarray((np.clip(capa, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        im = im.filter(ImageFilter.GaussianBlur(2))
        return np.asarray(im).astype(np.float32) / 255 * 2.2

    def cuadro(self, n):
        t = n / FPS
        tl = self.tl
        off0 = tl["off"][0]
        escenas = self.escenas
        if t < off0 + escenas[0]["ini"] - off0 - FUNDIDO and t < escenas[0]["ini"] - FUNDIDO:
            fr = self.apertura(t)
        else:
            activas = [(i, e) for i, e in enumerate(escenas)
                       if e["ini"] - FUNDIDO <= t < e["fin"] + FUNDIDO]
            fr = None
            for i, e in activas:
                img = self.escena(e, t, i)
                a = suave((t - (e["ini"] - FUNDIDO)) / FUNDIDO) if i > 0 else 1.0
                fr = img if fr is None else fr * (1 - a) + img * a
            if fr is None:
                fr = np.zeros((H, W, 3), np.float32)
            # fundido desde la bandera hacia la primera escena
            if t < escenas[0]["ini"] + FUNDIDO:
                a = suave((t - (escenas[0]["ini"] - FUNDIDO)) / (2 * FUNDIDO))
                fr = self.apertura(t) * (1 - a) + fr * a
            # rótulos de capítulo
            for ini, capa in self.caps:
                if ini - 0.2 <= t < ini + CAP_DUR:
                    u = t - ini
                    a = suave((u + 0.2) / 0.5) * (1 - suave((u - CAP_DUR + 0.8) / 0.8))
                    fr = fr * (1 - 0.5 * a)
                    fr = poner_capa(fr, capa, a)
                    flash = max(0, 1 - abs(u) / 0.25) * 0.85
                    fr = fr + (1 - fr) * flash
            # cierre
            fin = tl["total"] - OUTRO
            if t >= fin - 1.0:
                a = suave((t - fin + 1.0) / 1.4)
                fr = fr * (1 - a * 0.85)
                fr = poner_capa(fr, self.cierre, suave((t - fin - 0.3) / 0.8))
                fr = fr * (1 - suave((t - (tl["total"] - 1.5)) / 1.5))
        fr = fr * self.vin
        fr += self.grano[n % len(self.grano)]
        if t > 10.5:  # marca del canal: solo se mezcla la zona de la esquina
            y0, y1, x0 = 20, 95, 1200
            rgb, a = self.marca
            fr[y0:y1, x0:] = fr[y0:y1, x0:] * (1 - a[y0:y1, x0:]) + rgb[y0:y1, x0:] * a[y0:y1, x0:]
        np.clip(fr, 0, 1, out=fr)
        fr *= 255
        return fr.astype(np.uint8)


def trozo(sal, tl, n0, n1, ruta):
    r = Render(sal, tl)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                          "-pix_fmt", "yuv420p", str(ruta)], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        p.stdin.write(r.cuadro(n).tobytes())
        if (n - n0) % 900 == 0:
            print(f"    {ruta.name}: {(n - n0) / max(1, n1 - n0) * 100:.0f}%", flush=True)
    p.stdin.close()
    p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("audios", nargs=3)
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--prueba", nargs=2, type=float)
    ap.add_argument("--sin-audio", action="store_true")
    a = ap.parse_args()
    sal = Path(a.salida)
    tl = linea_de_tiempo(sal, a.audios)
    print(f"Duración total: {tl['total'] / 60:.1f} min, {len(tl['escenas'])} imágenes", flush=True)
    audio = sal / "audio_final.wav"
    if not a.sin_audio or not audio.exists():
        print("Audio...", flush=True)
        audio = hacer_audio(sal, a.audios, tl)
    if a.prueba:
        n0, n1 = int(a.prueba[0] * FPS), int(a.prueba[1] * FPS)
        partes = 1
    else:
        n0, n1 = 0, int(tl["total"] * FPS)
        partes = a.procesos
    print("Video...", flush=True)
    cortes = np.linspace(n0, n1, partes + 1).astype(int)
    rutas = [sal / f"parte_{i}.mp4" for i in range(partes)]
    procs = [Process(target=trozo, args=(sal, tl, cortes[i], cortes[i + 1], rutas[i])) for i in range(partes)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    (sal / "lista.txt").write_text("".join(f"file '{r.name}'\n" for r in rutas))
    nombre = "prueba.mp4" if a.prueba else "Italia_documental.mp4"
    ss = ["-ss", str(n0 / FPS)] if a.prueba else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(sal / "lista.txt"),
                    *ss, "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(sal / nombre)], check=True)
    for r in rutas:
        r.unlink()
    print("Listo:", sal / nombre, flush=True)


if __name__ == "__main__":
    main()
