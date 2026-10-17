"""Reel vertical (1080x1920, 30 fps) «El primer automóvil de la historia».

Uso: python3 montaje.py [--prueba INICIO FIN] [--salida archivo.mp4]

Necesita en material/: voz.wav (narración), motor1.wav y motor2.wav (efectos de motor)
e img/*.jpg (fotos históricas de Wikimedia Commons, ver descargar_imagenes.py).
La música de fondo, los golpes y los barridos de transición se sintetizan aquí.
"""
import argparse
import json
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal

AQUI = Path(__file__).parent
MAT = AQUI / "material"
W, H, FPS, SR = 1080, 1920, 30, 48000
VO = 0.40          # la voz empieza a los 0,4 s
MARCA = 47.2       # inicio del cierre de marca
TOTAL = 53.0
DORADO = (255, 205, 70)

# ----------------------------------------------------------------- tipografías
def montserrat(tam, peso="ExtraBold"):
    f = ImageFont.truetype(str(AQUI / "fuentes/Montserrat.ttf"), tam)
    f.set_variation_by_name(peso)
    return f


def cinzel(tam):
    return ImageFont.truetype(str(AQUI / "fuentes/cinzel-latin-700-normal.woff"), tam)


# ----------------------------------------------------------------- planos
# (inicio en tiempo de voz, imagen, modo, (cx, cy, zoom) inicial, (cx, cy, zoom) final, rótulo)
# cover: la foto llena la pantalla; tarjeta: la foto entera sobre un fondo desenfocado.
PLANOS = [
    (-0.4, "00", "cover", (0.40, 0.55, 1.00), (0.46, 0.55, 1.18), "Ilustración de 1888"),
    (3.55, "02", "cover", (0.50, 0.45, 1.00), (0.50, 0.33, 1.25), "Karl Benz, hacia 1889"),
    (7.90, "05", "cover", (0.30, 0.30, 1.05), (0.52, 0.22, 1.30), "Patente n.º 37435 · 1886"),
    (11.50, "07", "cover", (0.28, 0.55, 1.00), (0.70, 0.55, 1.05), "Benz Patent-Motorwagen"),
    (14.35, "15", "cover", (0.75, 0.55, 1.05), (0.40, 0.55, 1.00), "Patent-Motorwagen · modelo 1886"),
    (17.80, "08", "cover", (0.35, 0.60, 1.20), (0.55, 0.60, 1.00), None),
    (19.45, "09", "cover", (0.42, 0.50, 1.00), (0.45, 0.42, 1.35), "Motor de un cilindro"),
    (22.00, "14", "cover", (0.30, 0.60, 1.00), (0.62, 0.60, 1.08), None),
    (26.60, "10", "tarjeta", (0.50, 0.50, 1.00), (0.50, 0.42, 1.15), "Réplica · Verkehrsmuseum Dresden"),
    (29.70, "00", "cover", (0.80, 0.50, 1.25), (0.62, 0.50, 1.05), "Ilustración de 1888"),
    (33.10, "16", "cover", (0.30, 0.55, 1.00), (0.62, 0.50, 1.10), "Un Benz posterior, ya de cuatro ruedas"),
    (37.00, "13", "cover", (0.55, 0.60, 1.10), (0.45, 0.60, 1.00), "Réplica · Museo Mercedes-Benz"),
    (40.20, "17", "cover", (0.50, 0.42, 1.00), (0.50, 0.36, 1.18), "Karl Benz en 1869"),
    (44.25, "15", "cover", (0.45, 0.55, 1.00), (0.38, 0.50, 1.30), None),
    (MARCA - VO, "08", "marca", None, None, None),
]
FUNDIDO = 0.45

# ----------------------------------------------------------------- subtítulos
CAMBIOS = {("mil", "ochocientos", "ochenta", "y", "seis,"): "1886,",
           ("dieciséis", "kilómetros", "por", "hora."): "16_km/h."}
DESTACAR = {"1886,", "KARL", "BENZ", "PATENT-MOTORWAGEN", "TRES", "RUEDAS,", "GASOLINA",
            "16 KM/H.", "REVOLUCIÓN", "PRIMER", "AUTOMÓVIL", "CILINDRO,", "CONDUCIR"}


# cada bloque es lo que se ve a la vez en pantalla (las cifras sustituyen a las palabras dichas)
BLOQUES = ["¿Te imaginas", "cómo era", "el primer automóvil", "de la historia?",
           "En 1886,", "el ingeniero alemán", "Karl Benz", "patentó un vehículo", "que cambiaría",
           "el mundo para siempre.",
           "Se llamaba", "Benz Patent-Motorwagen...", "y no se parecía en nada", "a los carros",
           "que conocemos hoy.",
           "Tenía tres ruedas,", "un motor de gasolina", "de un solo cilindro,", "y una velocidad máxima",
           "de aproximadamente", "16_km/h.",
           "Pero lo más", "sorprendente...", "es que este invento", "ayudó a iniciar",
           "una revolución", "en el transporte.",
           "Años después,", "los automóviles", "evolucionarían", "hasta convertirse",
           "en las máquinas", "que hoy vemos", "en todas partes.",
           "Así comenzó", "una historia", "que transformó", "la manera", "en que viajamos.",
           "¿Te imaginas", "conducir", "uno de estos hoy?"]


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
    assert i == len(out)
    res = []
    for k, b in enumerate(bloques):
        ini = b[0]["ini"] - 0.06
        fin = b[-1]["fin"] + 0.35
        if k + 1 < len(bloques):
            sig = bloques[k + 1][0]["ini"] - 0.06
            fin = sig if sig - b[-1]["fin"] < 0.45 else min(fin, sig)
        palabras = [x["t"].replace("...", "").replace("_", " ").upper() for x in b]
        res.append((ini + VO, min(fin + VO, MARCA - 0.05), palabras))
    return res


SUBS = bloques_subtitulos()
F_SUB = montserrat(86)


@lru_cache(maxsize=None)
def imagen_subtitulo(k):
    palabras = SUBS[k][2]
    trazo = 9
    fuente = F_SUB
    mayor = max(F_SUB.getlength(p) for p in palabras)
    if mayor > 920:  # palabras muy largas (PATENT-MOTORWAGEN) no deben tocar los bordes
        fuente = montserrat(int(86 * 920 / mayor))
    esp = fuente.getlength(" ")
    anchos = [fuente.getlength(p) for p in palabras]
    # una o dos líneas, máx. 900 px de ancho
    lineas, linea, ancho = [], [], 0
    for p, a in zip(palabras, anchos):
        if linea and ancho + esp + a > 900:
            lineas.append(linea)
            linea, ancho = [], 0
        ancho += (esp if linea else 0) + a
        linea.append((p, a))
    lineas.append(linea)
    alto_l = 104
    im = Image.new("RGBA", (W, alto_l * len(lineas) + 2 * trazo + 20), (0, 0, 0, 0))
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sombra)
    for n, linea in enumerate(lineas):
        total = sum(a for _, a in linea) + esp * (len(linea) - 1)
        x = (W - total) / 2
        y = trazo + n * alto_l
        for p, a in linea:
            color = DORADO if p in DESTACAR else (255, 255, 255)
            ds.text((x + 4, y + 8), p, font=fuente, fill=(0, 0, 0, 170), stroke_width=trazo, stroke_fill=(0, 0, 0, 170))
            d.text((x, y), p, font=fuente, fill=color, stroke_width=trazo, stroke_fill=(0, 0, 0))
            x += a + esp
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(sombra, im)


# ----------------------------------------------------------------- imágenes
@lru_cache(maxsize=None)
def foto(nombre):
    im = Image.open(MAT / "img" / f"{nombre}.jpg").convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255
    # gradación común: algo de contraste y tono cálido de archivo
    a = np.clip((a - 0.5) * 1.08 + 0.5, 0, 1)
    a = a * np.array([1.03, 1.0, 0.93])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


@lru_cache(maxsize=None)
def fondo_desenfocado(nombre):
    im = foto(nombre)
    s = max(W / im.width, H / im.height) * 1.1
    im = im.resize((int(im.width * s / 4), int(im.height * s / 4)), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(10)).resize((int(im.width * 4), int(im.height * 4)), Image.BICUBIC)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    a = np.asarray(im.crop((x, y, x + W, y + H))).astype(np.float32) * 0.42
    return a


def vista(im, ow, oh, cx, cy, zoom):
    """Recorte tipo cámara: la foto cubre ow x oh, ampliada `zoom` y centrada en (cx, cy)."""
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
    """Fotograma del plano k en el tiempo absoluto t."""
    ini, nombre, modo, a, b, _ = PLANOS[k]
    ini += VO
    fin = (PLANOS[k + 1][0] + VO) if k + 1 < len(PLANOS) else TOTAL
    if modo == "marca":
        return cuadro_marca(t - ini)
    u = (t - ini + FUNDIDO) / (fin - ini + 2 * FUNDIDO)
    e = 0.15 + 0.7 * u + 0.15 * suave(u)  # movimiento casi lineal, como un travelling
    cx, cy, z = (a[i] + (b[i] - a[i]) * e for i in range(3))
    im = foto(nombre)
    if modo == "cover":
        return vista(im, W, H, cx, cy, z)
    # tarjeta: foto completa a lo ancho sobre su propio fondo desenfocado
    base = fondo_desenfocado(nombre).copy()
    tw = 1000
    th = int(min(tw * im.height / im.width, 1300))
    fr = vista(im, tw, th, cx, cy, z)
    y = (H - th) // 2 - 80
    base[y:y + th, (W - tw) // 2:(W - tw) // 2 + tw] = fr
    return base


# ----------------------------------------------------------------- cierre de marca
def cuadro_marca(dt):
    fondo = fondo_desenfocado("08") * (0.75 - 0.25 * suave(dt / 3))
    im = Image.fromarray(np.clip(fondo, 0, 255).astype(np.uint8)).convert("RGBA")
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f1, f2 = cinzel(100), cinzel(76)
    ap = suave((dt - 0.25) / 0.9)
    sep = int(22 * (1 - ap))  # las letras se juntan mientras aparecen
    yc = 860
    for texto, f, y in (("CURIOSIDADES", f1, yc - 140), ("DEL MUNDO", f2, yc + 20)):
        anchos = [f.getlength(c) for c in texto]
        total = sum(anchos) + sep * (len(texto) - 1)
        x = (W - total) / 2
        for c, aw in zip(texto, anchos):
            d.text((x, y), c, font=f, fill=(255, 255, 255, int(255 * ap)),
                   stroke_width=2, stroke_fill=(0, 0, 0, int(160 * ap)))
            x += aw + sep
    # líneas doradas que se abren desde el centro
    l = suave((dt - 0.6) / 0.8) * 330
    for y in (yc - 175, yc + 140):
        d.rectangle((W / 2 - l, y, W / 2 + l, y + 4), fill=DORADO + (230,))
    ap2 = suave((dt - 1.4) / 0.7)
    f3 = montserrat(40, "SemiBold")
    s = "Síguenos para más historias"
    d.text(((W - f3.getlength(s)) / 2, yc + 200), s, font=f3, fill=(255, 255, 255, int(220 * ap2)))
    im = Image.alpha_composite(im, capa.filter(ImageFilter.GaussianBlur(0.6)))
    return np.asarray(im.convert("RGB")).astype(np.float32)


# ----------------------------------------------------------------- rótulos y efectos
F_ROT = montserrat(40, "SemiBold")


@lru_cache(maxsize=None)
def imagen_rotulo(texto):
    pad = 22
    tw = int(F_ROT.getlength(texto))
    im = Image.new("RGBA", (tw + 2 * pad + 14, 76), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, 75), radius=14, fill=(0, 0, 0, 150))
    d.rectangle((0, 13, 6, 62), fill=DORADO + (255,))
    d.text((pad + 8, 13), texto, font=F_ROT, fill=(255, 255, 255, 240))
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
VIÑETA = (1 - 0.55 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2))[..., None]
VIÑETA = np.clip(VIÑETA, 0.35, 1).astype(np.float32)
# degradado oscuro abajo para que los subtítulos se lean siempre
DEGRADADO = (1 - 0.45 * np.clip((yy - H * 0.55) / (H * 0.45), 0, 1))[..., None].astype(np.float32)
rng = np.random.default_rng(7)
GRANO = [rng.normal(0, 3.5, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]


def velocidad(base, dt):
    """Indicador «≈ 16 km/h» que aparece cuando la voz dice la velocidad."""
    ap = suave(dt / 0.35)
    if ap <= 0:
        return
    f1, f2 = montserrat(150, "Black"), montserrat(46, "Bold")
    im = Image.new("RGBA", (W, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t1, t2 = "≈ 16 km/h", "VELOCIDAD MÁXIMA"
    d.text(((W - f2.getlength(t2)) / 2, 20), t2, font=f2, fill=(255, 255, 255, 235), stroke_width=4, stroke_fill=(0, 0, 0))
    d.text(((W - f1.getlength(t1)) / 2, 85), t1, font=f1, fill=DORADO + (255,), stroke_width=8, stroke_fill=(0, 0, 0))
    esc = 0.8 + 0.2 * ap
    im = im.resize((int(W * esc), int(330 * esc)), Image.BICUBIC)
    pegar(base, im, (W - im.width) // 2, 430 - im.height // 2 + 120, ap)


def cuadro(n):
    t = n / FPS
    # plano actual y fundido con el siguiente
    ks = [k for k in range(len(PLANOS)) if PLANOS[k][0] + VO - FUNDIDO / 2 <= t]
    k = ks[-1] if ks else 0
    ini_k = PLANOS[k][0] + VO
    img = plano(k, t)
    if k > 0 and t < ini_k + FUNDIDO / 2:
        m = suave((t - (ini_k - FUNDIDO / 2)) / FUNDIDO)
        img = plano(k - 1, t) * (1 - m) + img * m
    if PLANOS[k][2] != "marca" or t < MARCA + FUNDIDO / 2:
        img = img * VIÑETA * DEGRADADO
    # fundido de entrada desde negro
    img *= suave(t / 0.35)
    # rótulo del plano
    rot = PLANOS[k][5]
    if rot and PLANOS[k][2] != "marca":
        dt = t - ini_k
        fin_k = PLANOS[k + 1][0] + VO
        ap = suave((dt - 0.35) / 0.4) * (1 - suave((t - (fin_k - 0.5)) / 0.35))
        if ap > 0:
            pegar(img, imagen_rotulo(rot), 60 - int(30 * (1 - ap)), 250, ap)
    # velocidad
    t16 = 24.565 + VO
    if t16 <= t < PLANOS[8][0] + VO - 0.2:
        velocidad(img, t - t16)
    # subtítulos con pequeño "pop" al entrar
    for k2, (si, sf_, _) in enumerate(SUBS):
        if si <= t < sf_:
            dt = t - si
            esc = 0.88 + 0.12 * suave(dt / 0.12) + 0.025 * np.sin(min(dt / 0.2, 1) * np.pi)
            sub = imagen_subtitulo(k2)
            if abs(esc - 1) > 0.002:
                sub = sub.resize((int(sub.width * esc), int(sub.height * esc)), Image.BICUBIC)
            ap = suave(dt / 0.08) * (1 - suave((t - (sf_ - 0.08)) / 0.08))
            pegar(img, sub, (W - sub.width) // 2, 1330 - sub.height // 2, ap)
    g = GRANO[n % len(GRANO)]
    img = img + np.repeat(np.repeat(g, 2, 0), 2, 1)
    return np.clip(img, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------- audio
def nota(f):
    return 440.0 * 2 ** ((f - 69) / 12)


def adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
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
    ir = pasa_bajos(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x * (1 - mezcla) + signal.fftconvolve(x, ir)[:len(x)] * mezcla * 2.2


def musica(n):
    """Fondo documental de suspenso: colchón de cuerdas, bajo, pulso de timbal y arpegio de piano."""
    t = np.arange(n) / SR
    r = np.random.default_rng(3)
    # progresión en re menor, un acorde cada 3,2 s
    acordes = [(50, 53, 57, 62), (46, 50, 53, 58), (41, 48, 53, 57), (48, 52, 55, 60),
               (50, 53, 57, 62), (46, 50, 53, 62), (43, 50, 55, 58), (45, 49, 52, 57)]
    dur = 3.2
    cuerdas = np.zeros(n)
    bajo = np.zeros(n)
    piano = np.zeros(n)
    # intensidad: suave al principio, crece en «revolución» (≈28 s) y cae antes de la marca
    inten = np.interp(t, [0, 3, 12, 27, 31, 40, MARCA - 0.5, MARCA, TOTAL],
                      [0.35, 0.5, 0.6, 0.65, 1.0, 1.0, 0.75, 0.0, 0.0])
    i = 0
    while i * dur < MARCA:
        ac = acordes[i % len(acordes)]
        s0, s1 = int(i * dur * SR), min(n, int(((i + 1) * dur + 0.8) * SR))
        tt = np.arange(s1 - s0) / SR
        env = adsr(s1 - s0, 1.2, 1.4)
        for m in ac[1:]:
            for det in (-0.12, 0.0, 0.11):
                f = nota(m + 12) * 2 ** (det / 12)
                fase = r.uniform(0, 2 * np.pi)
                # diente de sierra suave (pocos armónicos) = cuerdas
                cuerdas[s0:s1] += env * sum(np.sin(2 * np.pi * f * h * tt + fase * h) / h ** 1.6 for h in range(1, 7)) * 0.05
        fb = nota(ac[0] - 12)
        bajo[s0:s1] += env * (np.sin(2 * np.pi * fb * tt) + 0.3 * np.sin(4 * np.pi * fb * tt)) * 0.22
        # arpegio de piano en corcheas (0,4 s)
        notas = [ac[1] + 24, ac[2] + 24, ac[3] + 12, ac[2] + 24]
        for j in range(8):
            p0 = int((i * dur + j * 0.4) * SR)
            if p0 >= n:
                break
            f = nota(notas[j % 4])
            ln = min(int(2.0 * SR), n - p0)
            tp = np.arange(ln) / SR
            golpe = (np.sin(2 * np.pi * f * tp) + 0.35 * np.sin(4 * np.pi * f * tp) + 0.12 * np.sin(6 * np.pi * f * tp))
            piano[p0:p0 + ln] += golpe * np.exp(-tp * 3.2) * (0.10 if j % 2 == 0 else 0.07)
        i += 1
    cuerdas = pasa_bajos(cuerdas, 2400)
    # pulso de timbal grave cada 1,6 s, más presente cuando crece la intensidad
    timbal = np.zeros(n)
    for k in np.arange(0, MARCA - 0.5, 1.6):
        p0 = int(k * SR)
        ln = min(int(1.2 * SR), n - p0)
        tp = np.arange(ln) / SR
        f = 55 * (1 + 0.6 * np.exp(-tp * 25))
        timbal[p0:p0 + ln] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tp * 4.5) * 0.5
    timbal *= np.clip((inten - 0.5) * 2, 0, 1)
    m = (cuerdas * (0.6 + 0.4 * inten) + bajo * inten + piano * np.clip(inten * 1.2, 0, 1) * 0.9 + timbal) * inten
    m = reverb(m, 3.0, 0.4)
    return m


def golpe_marca(n, t0):
    """Impacto grave + brillo para el cierre de marca."""
    x = np.zeros(n)
    p0 = int(t0 * SR)
    ln = n - p0
    tp = np.arange(ln) / SR
    f = 42 * (1 + 1.2 * np.exp(-tp * 18))
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tp * 1.6)
    ruido = pasa_bajos(np.random.default_rng(5).normal(0, 1, ln), 900) * np.exp(-tp * 6) * 0.5
    brillo = sum(np.sin(2 * np.pi * nota(m) * tp) for m in (74, 81, 86)) * np.exp(-tp * 0.9) * 0.05
    acorde = sum(np.sin(2 * np.pi * nota(m) * tp) / (1 + (m > 60)) for m in (38, 50, 57, 62, 65)) * \
        np.minimum(tp / 0.3, 1) * np.exp(-tp * 0.45) * 0.08
    x[p0:] = boom * 0.9 + ruido + brillo + acorde
    return reverb(x, 3.5, 0.45, 2)


def barrido(n, t0, dur=0.7, vol=0.12):
    """Whoosh de transición: ruido filtrado que sube y baja."""
    x = np.zeros(n)
    p0 = max(0, int((t0 - dur * 0.6) * SR))
    ln = min(int(dur * SR), n - p0)
    ruido = np.random.default_rng(int(t0 * 100)).normal(0, 1, ln)
    fc = 300 + 3500 * np.sin(np.linspace(0, np.pi, ln)) ** 2
    y = np.zeros(ln)
    # filtro paso-banda variable por bloques
    blo = 512
    zi = None
    for s in range(0, ln, blo):
        b, a = signal.butter(2, [max(80, fc[s] * 0.5) / (SR / 2), min(fc[s] * 1.6, 20000) / (SR / 2)], "band")
        if zi is None:
            zi = signal.lfilter_zi(b, a) * 0
        y[s:s + blo], zi = signal.lfilter(b, a, ruido[s:s + blo], zi=zi)
    x[p0:p0 + ln] = y * np.sin(np.linspace(0, np.pi, ln)) ** 2 * vol
    return x


def cargar(nombre):
    a, sr = sf.read(MAT / nombre, always_2d=True)
    assert sr == SR, f"{nombre} debe estar a {SR} Hz"
    return a.mean(axis=1)


def motor(n, t0, dur, vol, archivo="motor1.wav"):
    """Coloca el efecto de motor en bucle (con fundidos cruzados) entre t0 y t0+dur."""
    s = cargar(archivo)
    x = np.zeros(n)
    cruce = int(0.25 * SR)
    largo = int(dur * SR)
    pista = np.zeros(largo + len(s))
    pos = 0
    ventana = np.ones(len(s))
    ventana[:cruce] = np.linspace(0, 1, cruce)
    ventana[-cruce:] = np.linspace(1, 0, cruce)
    while pos < largo:
        pista[pos:pos + len(s)] += s * ventana
        pos += len(s) - cruce
    pista = pista[:largo] * adsr(largo, 0.3, 0.8)
    p0 = int(t0 * SR)
    ln = min(largo, n - p0)
    x[p0:p0 + ln] = pista[:ln] * vol
    return x


def mezcla(ruta):
    n = int(TOTAL * SR)
    voz = np.zeros(n)
    v = cargar("voz.wav")
    p0 = int(VO * SR)
    voz[p0:p0 + len(v)] = v[:n - p0]
    voz = signal.lfilter(*signal.butter(2, 70 / (SR / 2), "high"), voz)
    # compresión suave de la voz
    env = np.sqrt(signal.lfilter([0.002], [1, -0.998], voz ** 2)) + 1e-6
    voz = voz * np.minimum(1, (0.12 / env) ** 0.35)

    mus = musica(n)
    # ducking: la música baja mientras hay voz
    hay_voz = signal.lfilter([0.0005], [1, -0.9995], np.abs(voz) > 0.02) > 0.15
    duck = signal.lfilter([0.0002], [1, -0.9998], hay_voz.astype(float))
    duck = 1 - 0.55 * np.clip(duck * 1.3, 0, 1)

    sfx = np.zeros(n)
    sfx += motor(n, 17.6 + VO, 5.0, 0.20)           # «tres ruedas, un motor de gasolina»
    sfx += motor(n, 44.0 + VO, 3.2, 0.24, "motor2.wav")  # «¿te imaginas conducir uno?»
    for k in range(1, len(PLANOS)):
        if PLANOS[k][2] != "marca":
            sfx += barrido(n, PLANOS[k][0] + VO, vol=0.06)
    sfx += barrido(n, MARCA, 1.0, 0.10)
    golpe = golpe_marca(n, MARCA + 0.15)

    def nivel(x):
        return np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))
    voz = voz / nivel(voz) * 0.16
    mus = mus / nivel(mus[: int(MARCA * SR)]) * 0.16 * 0.22   # ~-13 dB bajo la voz, más con el ducking
    total = voz + mus * duck + sfx * 0.9 + golpe * 0.35
    total = total * adsr(n, 0.05, 1.5)
    estereo = np.stack([total, total], axis=1)
    # leve anchura estéreo a la música
    retardo = int(0.012 * SR)
    m2 = np.roll(mus * duck, retardo) * 0.15
    estereo[:, 0] += m2
    estereo[:, 1] -= m2
    estereo /= np.max(np.abs(estereo)) / 0.9
    sf.write(ruta, estereo.astype(np.float32), SR, subtype="FLOAT")


# ----------------------------------------------------------------- salida
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", nargs=2, type=float)
    ap.add_argument("--salida", default=str(AQUI.parent.parent / "exportados/Curiosidades_del_Mundo_Primer_Automovil.mp4"))
    args = ap.parse_args()
    tmp = AQUI / "salida"
    tmp.mkdir(exist_ok=True)
    audio = tmp / "mezcla.wav"
    if not args.prueba or not audio.exists():
        mezcla(audio)
        print("audio listo", flush=True)
    a, b = args.prueba if args.prueba else (0, TOTAL)
    n0, n1 = int(a * FPS), int(b * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-ss", str(a), "-t", str(b - a), "-i", str(audio),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000",
           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", args.salida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        p.stdin.write(cuadro(n).tobytes())
        if n % 150 == 0:
            print(f"{n / FPS:.1f} s", flush=True)
    p.stdin.close()
    p.wait()
    srt = []
    for k, (si, sf_, pal) in enumerate(SUBS):
        f = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x % 1 * 1000):03d}"
        srt.append(f"{k + 1}\n{f(si)} --> {f(sf_)}\n{' '.join(pal)}\n")
    Path(args.salida).with_suffix(".srt").write_text("\n".join(srt))
    print("listo:", args.salida)


if __name__ == "__main__":
    main()
