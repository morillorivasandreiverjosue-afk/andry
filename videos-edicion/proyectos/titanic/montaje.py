"""Video corto del Titanic para TikTok, Instagram y YouTube.

Uso: python3 montaje.py [vertical|horizontal|feed ...]   (sin argumentos: los tres)

Necesita salida/voz.mp3 (narración generada con ElevenLabs). Recorta el collage,
mejora las imágenes a HD, sincroniza subtítulos con la voz, añade música y efectos
sintetizados (../napoleon/sonido.py) y exporta a ../../exportados/.
"""
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "napoleon"))
import sonido as so  # noqa: E402

IMG = AQUI / "imagenes"
SALIDA = AQUI / "salida"
EXPORTADOS = AQUI.parent.parent / "exportados"
FPS = 30
DUR = 61.0
ZMAX = 1.12

FUENTE_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FUENTE_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FUENTE_TITULO = str(AQUI.parent / "napoleon" / "fuentes" / "cinzel-latin-700-normal.woff")
ORO = (240, 196, 92)
AMARILLO = (255, 214, 10)

FORMATOS = {
    # nombre: ancho, alto, caja de la imagen (ancho, alto), centro vertical de la caja,
    #         altura de subtítulos, altura de etiquetas, tamaño de subtítulos
    "vertical": dict(W=1080, H=1920, caja=(1080, 1340), caja_y=0.40, sub_y=0.735, chip_y=0.115, sub=80,
                     archivo="Titanic_TikTok_Reels_Shorts_1080x1920.mp4"),
    "horizontal": dict(W=1920, H=1080, caja=(1300, 1080), caja_y=0.50, sub_y=0.85, chip_y=0.09, sub=66,
                       archivo="Titanic_YouTube_1920x1080.mp4"),
    "feed": dict(W=1080, H=1350, caja=(1080, 1100), caja_y=0.43, sub_y=0.845, chip_y=0.075, sub=64,
                 archivo="Titanic_Instagram_Feed_1080x1350.mp4"),
}

# Frases de la narración con su inicio y fin en segundos (medidos sobre salida/voz.mp3)
FRASES = [
    ("El Titanic era considerado uno de los barcos más impresionantes de su época…", 0.05, 4.77),
    ("pero su primer viaje terminó en una de las mayores tragedias marítimas de la historia.", 5.62, 10.08),
    ("El 10 de abril de 1912,", 10.68, 12.86),
    ("el Titanic partió de Inglaterra rumbo a Nueva York,", 13.08, 15.55),
    ("llevando a más de 2.200 personas a bordo.", 15.90, 18.54),
    ("Pero durante la noche del 14 de abril,", 19.14, 21.39),
    ("el barco chocó contra un iceberg en el Atlántico Norte.", 21.58, 24.33),
    ("El impacto dañó varios compartimentos del casco.", 24.96, 27.45),
    ("Poco a poco, el agua comenzó a inundar el barco.", 27.81, 30.62),
    ("Los botes salvavidas no eran suficientes para todas las personas a bordo.", 31.17, 34.80),
    ("En la madrugada del 15 de abril,", 35.25, 37.14),
    ("el Titanic desapareció bajo las aguas heladas.", 37.41, 39.92),
    ("Más de 1.500 personas perdieron la vida.", 40.63, 43.21),
    ("Durante décadas,", 43.58, 44.60),
    ("sus restos permanecieron ocultos en las profundidades,", 44.76, 47.48),
    ("hasta que fueron descubiertos en 1985.", 47.93, 50.86),
    ("Una tragedia que el mundo nunca olvidó.", 51.36, 53.50),
]
DESTACAR = {"titanic", "1912", "2.200", "iceberg", "14", "15", "1.500", "1985", "tragedias", "tragedia",
            "impresionantes", "salvavidas", "heladas", "vida", "profundidades", "nunca"}

# Planos: imagen, inicio, fin, zoom inicial/final, desplazamiento inicial/final (-1..1)
FINAL = 53.68
PLANOS = [
    ("c1", 0.00, 5.20, 1.00, 1.10, (0, 0.2), (0, -0.2)),
    ("c4", 5.20, 10.38, 1.10, 1.00, (0, 0), (0, 0)),
    ("puerto_southampton", 10.38, 12.97, 1.00, 1.08, (-0.6, 0), (0.6, 0)),
    ("c2", 12.97, 15.72, 1.08, 1.00, (0.3, 0), (-0.3, 0)),
    ("navegando_1912", 15.72, 18.84, 1.00, 1.06, (-1, 0), (1, 0)),
    ("luna_iceberg", 18.84, 21.48, 1.00, 1.10, (-0.3, 0), (0.4, 0)),
    ("c3", 21.48, 27.63, 1.12, 1.00, (-0.6, 0), (0.2, 0)),
    ("botes_niebla", 27.63, 30.90, 1.00, 1.08, (0.5, 0), (-0.5, 0)),
    ("c5", 30.90, 35.02, 1.00, 1.10, (0, 0.5), (0, -0.3)),
    ("hundimiento_pintura", 35.02, 43.40, 1.00, 1.12, (0.4, -0.5), (-0.2, 0.4)),
    ("c6", 43.40, 47.70, 1.00, 1.10, (0.3, -0.4), (-0.2, 0.3)),
    ("restos_proa_real", 47.70, FINAL, 1.12, 1.00, (0, 0.6), (0, -0.3)),
    ("c1", FINAL, DUR, 1.06, 1.00, (0, 0), (0, 0)),
]
ETIQUETAS = [
    ("10 DE ABRIL DE 1912", 10.45, 18.80),
    ("14 DE ABRIL · 23:40", 18.90, 27.55),
    ("15 DE ABRIL · 2:20", 35.10, 43.30),
    ("DESCUBIERTO EN 1985", 47.80, 53.60),
]
DESTELLOS = [0.0, 21.48, 35.02, FINAL]  # flash blanco
SACUDIDAS = [21.6]  # temblor de cámara (choque con el iceberg)


# ------------------------------------------------------------------ imágenes
def fuentes_imagenes():
    imgs = {p.stem: Image.open(p).convert("RGB") for p in IMG.glob("*.jpg") if p.stem != "collage_6"}
    collage = Image.open(IMG / "collage_6.jpg").convert("RGB")
    # el collage tiene 2 columnas y 3 filas separadas por líneas blancas
    xs, ys = [(0, 448), (451, 900)], [(0, 533), (536, 1059), (1062, 1600)]
    n = 0
    for y0, y1 in ys:
        for x0, x1 in xs:
            n += 1
            imgs[f"c{n}"] = collage.crop((x0 + 2, y0 + 2, x1 - 2, y1 - 2))
    return imgs


def es_bn(img):
    a = np.asarray(img.resize((64, 64))).astype(int)
    return np.abs(a[..., 0] - a[..., 1]).mean() + np.abs(a[..., 1] - a[..., 2]).mean() < 6


def mejorar_hd(img, tam):
    """Escala con Lanczos, limpia artefactos JPEG y realza el detalle."""
    bn = es_bn(img)
    x = img.resize(tam, Image.LANCZOS)
    x = x.filter(ImageFilter.MedianFilter(3))
    x = x.filter(ImageFilter.UnsharpMask(radius=2.4, percent=110, threshold=2))
    x = x.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=1))
    x = ImageOps.autocontrast(x, cutoff=0.4)
    if bn:
        x = ImageOps.grayscale(x).convert("RGB")
        x = ImageEnhance.Contrast(x).enhance(1.08)
    else:
        x = ImageEnhance.Color(x).enhance(1.10)
        x = ImageEnhance.Contrast(x).enhance(1.05)
    return x


# ------------------------------------------------------------------ estado global por proceso
G = {}


def preparar(nombre_formato):
    f = FORMATOS[nombre_formato]
    W, H = f["W"], f["H"]
    bw, bh = f["caja"]
    u = min(W, H) / 1080
    imgs = fuentes_imagenes()
    planos = []
    for clave, t0, t1, z0, z1, p0, p1 in PLANOS:
        src = imgs[clave]
        iw, ih = src.size
        s = max(bw / iw, bh / ih)
        s = min(s, bw / (0.72 * iw), bh / (0.72 * ih))
        pre = mejorar_hd(src, (round(iw * s * ZMAX), round(ih * s * ZMAX)))
        fondo = ImageOps.fit(src, (W // 4, H // 4), Image.LANCZOS)
        fondo = fondo.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BICUBIC)
        brillo = np.asarray(fondo.convert("L")).mean()
        fondo = ImageEnhance.Brightness(fondo).enhance(min(0.45, 42 / max(brillo, 1)))
        final = t0 >= FINAL
        if final:
            pre = ImageEnhance.Brightness(pre).enhance(0.42)
        planos.append(dict(pre=pre, s=s, iw=iw, ih=ih, t0=t0, t1=t1, z0=z0, z1=z1, p0=p0, p1=p1,
                           fondo=fondo, final=final))
    # viñeta y degradado inferior para leer los subtítulos
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vin = np.clip((d - 0.75) / 0.7, 0, 1) ** 1.5 * 0.55
    g0 = f["sub_y"] * H - 260 * u
    vin = np.maximum(vin, np.clip((yy - g0) / (380 * u), 0, 1) * 0.55)
    G.update(f=f, W=W, H=H, u=u, planos=planos, vin=(1 - vin)[..., None].astype(np.float32),
             nombre=nombre_formato)
    G["subs"] = trozos_subtitulos()


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


@lru_cache(maxsize=64)
def mascara(w, h, borde):
    m = np.ones((h, w), np.float32)
    r = np.linspace(0, 1, borde, dtype=np.float32) ** 1.3
    if h > 2 * borde:
        m[:borde] *= r[:, None]
        m[-borde:] *= r[::-1][:, None]
    if w > 2 * borde:
        m[:, :borde] *= r[None, :]
        m[:, -borde:] *= r[::-1][None, :]
    return Image.fromarray((m * 255).astype(np.uint8))


def cuadro_plano(i, t):
    p = G["planos"][i]
    W, H, f = G["W"], G["H"], G["f"]
    bw, bh = f["caja"]
    k = suave((t - p["t0"]) / max(p["t1"] - p["t0"], 0.01))
    z = p["z0"] + (p["z1"] - p["z0"]) * k
    px = p["p0"][0] + (p["p1"][0] - p["p0"][0]) * k
    py = p["p0"][1] + (p["p1"][1] - p["p0"][1]) * k
    pre = p["pre"]
    dw, dh = p["iw"] * p["s"] * z, p["ih"] * p["s"] * z
    vw, vh = int(min(bw, dw)), int(min(bh, dh))
    a = ZMAX / z
    cx = pre.width / 2 + px * max(0, (pre.width - vw * a) / 2)
    cy = pre.height / 2 + py * max(0, (pre.height - vh * a) / 2)
    vista = pre.transform((vw, vh), Image.AFFINE, (a, 0, cx - a * vw / 2, 0, a, cy - a * vh / 2),
                          resample=Image.BICUBIC)
    lienzo = p["fondo"].copy()
    borde = int(110 * G["u"])
    x0 = (W - vw) // 2
    y0 = int(f["caja_y"] * H - vh / 2)
    lienzo.paste(vista, (x0, y0), mascara(vw, vh, borde))
    return lienzo


def plano_en(t):
    for i, p in enumerate(G["planos"]):
        if p["t0"] <= t < p["t1"]:
            return i
    return len(G["planos"]) - 1


# ------------------------------------------------------------------ texto
@lru_cache(maxsize=32)
def fuente(ruta, tam):
    return ImageFont.truetype(ruta, tam)


def limpio(palabra):
    return palabra.lower().strip(".,…¿?¡!")


def trozos_subtitulos():
    """Divide cada frase en grupos de 1-3 palabras con tiempos proporcionales a su longitud."""
    trozos = []
    for texto, t0, t1 in FRASES:
        palabras = texto.split()
        grupos, actual = [], []
        for w in palabras:
            if actual and (len(" ".join(actual + [w])) > 17 or len(actual) == 3):
                grupos.append(actual)
                actual = []
            actual.append(w)
        grupos.append(actual)
        pesos = [sum(len(w) + 2 for w in g) for g in grupos]
        total = sum(pesos)
        t = t0
        for g, pz in zip(grupos, pesos):
            d = (t1 - t0) * pz / total
            trozos.append((g, t, t + d))
            t += d
    # cada trozo se mantiene hasta que empieza el siguiente (si la pausa es corta)
    salida = []
    for j, (g, a, b) in enumerate(trozos):
        sig = trozos[j + 1][1] if j + 1 < len(trozos) else b + 0.4
        salida.append((g, a, sig if sig - b < 0.9 else b + 0.25))
    return salida


@lru_cache(maxsize=256)
def imagen_subtitulo(palabras, tam, ancho_max):
    fnt = fuente(FUENTE_BLACK, tam)
    trazo = max(4, tam // 11)
    esp = fnt.getlength(" ")
    lineas, actual = [], []
    for w in palabras:
        prueba = actual + [w]
        if actual and sum(fnt.getlength(x.upper()) for x in prueba) + esp * (len(prueba) - 1) > ancho_max:
            lineas.append(actual)
            actual = []
        actual.append(w)
    lineas.append(actual)
    alto_l = int(tam * 1.18)
    anchos = [sum(fnt.getlength(x.upper()) for x in l) + esp * (len(l) - 1) for l in lineas]
    Wc, Hc = int(max(anchos) + 4 * trazo + 20), alto_l * len(lineas) + 4 * trazo + 20
    img = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    sombra = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    ds, d = ImageDraw.Draw(sombra), ImageDraw.Draw(img)
    for n, (l, an) in enumerate(zip(lineas, anchos)):
        x = (Wc - an) / 2
        y = 2 * trazo + 10 + n * alto_l
        for w in l:
            texto = w.upper()
            color = AMARILLO if limpio(w) in DESTACAR else (255, 255, 255)
            ds.text((x + 5, y + 7), texto, font=fnt, fill=(0, 0, 0, 170), stroke_width=trazo, stroke_fill=(0, 0, 0, 170))
            d.text((x, y), texto, font=fnt, fill=color, stroke_width=trazo, stroke_fill=(0, 0, 0))
            x += fnt.getlength(texto) + esp
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(sombra, img)


def pegar_centrado(lienzo, img, cx, cy, escala=1.0, alfa=1.0):
    if escala != 1.0:
        img = img.resize((max(1, int(img.width * escala)), max(1, int(img.height * escala))), Image.BICUBIC)
    if alfa < 1.0:
        a = img.getchannel("A").point(lambda v: int(v * alfa))
        img = img.copy()
        img.putalpha(a)
    lienzo.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


@lru_cache(maxsize=16)
def imagen_etiqueta(texto, tam):
    fnt = fuente(FUENTE_BOLD, tam)
    an = fnt.getlength(texto)
    pad_x, pad_y = tam * 0.9, tam * 0.55
    Wc, Hc = int(an + 2 * pad_x), int(tam * 1.2 + 2 * pad_y)
    img = Image.new("RGBA", (Wc + 8, Hc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, Wc + 4, Hc + 4), radius=Hc // 2, fill=(10, 14, 24, 190), outline=ORO + (255,),
                        width=max(3, tam // 14))
    d.text((4 + pad_x, 4 + pad_y - tam * 0.05), texto, font=fnt, fill=(255, 255, 255))
    return img


@lru_cache(maxsize=16)
def imagen_titulo(texto, tam, color, ruta=FUENTE_TITULO, trazo=0):
    fnt = fuente(ruta, tam)
    l, t, r, b = fnt.getbbox(texto, stroke_width=trazo)
    pad = int(tam * 0.4)
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    brillo = img.copy()
    ImageDraw.Draw(brillo).text((pad - l, pad - t), texto, font=fnt, fill=(0, 0, 0, 230),
                                stroke_width=trazo + max(2, tam // 18), stroke_fill=(0, 0, 0, 230))
    brillo = brillo.filter(ImageFilter.GaussianBlur(max(4, tam // 10)))
    ImageDraw.Draw(img).text((pad - l, pad - t), texto, font=fnt, fill=color,
                             stroke_width=trazo, stroke_fill=(0, 0, 0))
    return Image.alpha_composite(brillo, img)


def aparicion(t, t0, t1, entrada=0.25, salida=0.25):
    if t < t0 or t > t1:
        return 0.0
    return min(suave((t - t0) / entrada), suave((t1 - t) / salida))


def textos(lienzo, t):
    W, H, f, u = G["W"], G["H"], G["f"], G["u"]
    horizontal = W > H
    # gancho: título
    a = aparicion(t, 0.15, 5.1, 0.5, 0.4)
    if a > 0:
        e = 1.0 + 0.04 * (1 - suave((t - 0.15) / 0.8))
        ty = (0.15 if not horizontal else 0.14) * H
        pegar_centrado(lienzo, imagen_titulo("TITANIC", int(150 * u), ORO), W / 2, ty, e, a)
        pegar_centrado(lienzo, imagen_titulo("EL BARCO «INSUMERGIBLE»", int(40 * u), (255, 255, 255), FUENTE_BOLD),
                       W / 2, ty + 115 * u, 1.0, a)
    # etiquetas de fecha
    for texto, t0, t1 in ETIQUETAS:
        a = aparicion(t, t0, t1, 0.3, 0.3)
        if a > 0:
            dy = (1 - suave((t - t0) / 0.35)) * -30 * u
            pegar_centrado(lienzo, imagen_etiqueta(texto, int(42 * u)), W / 2, f["chip_y"] * H + dy, 1.0, a)
    # cifra grande de víctimas
    a = aparicion(t, 40.55, 43.35, 0.2, 0.3)
    if a > 0:
        e = 1.0 + 0.25 * (1 - suave((t - 40.55) / 0.35))
        cy = f["caja_y"] * H - (60 if not horizontal else 40) * u
        pegar_centrado(lienzo, imagen_titulo("+1.500", int(230 * u), (255, 255, 255), FUENTE_BLACK, int(6 * u)),
                       W / 2, cy, e, a)
        pegar_centrado(lienzo, imagen_titulo("VIDAS PERDIDAS", int(56 * u), AMARILLO, FUENTE_BLACK, int(4 * u)),
                       W / 2, cy + 170 * u, 1.0, a)
    # subtítulos
    if t < FINAL:
        ancho = int((0.86 if not horizontal else 0.6) * W)
        for g, t0, t1 in G["subs"]:
            if t0 <= t < t1:
                pop = 0.86 + 0.14 * suave((t - t0) / 0.12)
                pegar_centrado(lienzo, imagen_subtitulo(tuple(g), int(f["sub"] * u), ancho),
                               W / 2, f["sub_y"] * H, pop, 1.0)
                break
    else:
        cierre(lienzo, t)


def cierre(lienzo, t):
    W, H, u = G["W"], G["H"], G["u"]
    horizontal = W > H
    base = 0.22 if not horizontal else 0.17
    paso = 1.0 if not horizontal else 0.82
    a = aparicion(t, 53.86, DUR, 0.3, 0.6)
    if a > 0:
        e = 0.8 + 0.2 * suave((t - 53.86) / 0.18)
        pegar_centrado(lienzo, imagen_titulo("¿CONOCÍAS", int(104 * u), (255, 255, 255), FUENTE_BLACK, int(5 * u)),
                       W / 2, base * H, e, a)
        pegar_centrado(lienzo, imagen_titulo("ESTA HISTORIA?", int(104 * u), AMARILLO, FUENTE_BLACK, int(5 * u)),
                       W / 2, base * H + 120 * u, e, a)
    a = aparicion(t, 55.79, DUR, 0.35, 0.6)
    if a > 0:
        y = (base + 0.20 * paso) * H + 40 * u
        pegar_centrado(lienzo, imagen_titulo("SÍGUENOS EN", int(48 * u), (255, 255, 255), FUENTE_BOLD),
                       W / 2, y, 1.0, a)
        e = 0.9 + 0.1 * suave((t - 55.79) / 0.3)
        pegar_centrado(lienzo, imagen_titulo("CURIOSIDADES", int(104 * u), ORO), W / 2, y + 110 * u, e, a)
        pegar_centrado(lienzo, imagen_titulo("DEL MUNDO", int(104 * u), ORO), W / 2, y + 225 * u, e, a)
    a = aparicion(t, 56.6, DUR, 0.3, 0.6)
    if a > 0:
        y = (base + 0.20 * paso) * H + 410 * u
        late = 1.0 + 0.06 * max(0.0, np.sin((t - 56.6) * 2 * np.pi * 1.2))
        pegar_centrado(lienzo, boton(int(56 * u)), W / 2, y, late, a)
        pegar_centrado(lienzo, imagen_titulo("Más historias que cambiaron el mundo", int(38 * u), (230, 230, 230),
                                             FUENTE_BOLD), W / 2, y + 120 * u, 1.0, a)


@lru_cache(maxsize=4)
def boton(tam):
    fnt = fuente(FUENTE_BLACK, tam)
    texto = "+  SEGUIR"
    an = fnt.getlength(texto)
    Wc, Hc = int(an + tam * 2.2), int(tam * 2.1)
    img = Image.new("RGBA", (Wc + 30, Hc + 30), (0, 0, 0, 0))
    sombra = img.copy()
    ImageDraw.Draw(sombra).rounded_rectangle((15, 20, Wc + 15, Hc + 20), radius=Hc // 2, fill=(0, 0, 0, 160))
    sombra = sombra.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((15, 15, Wc + 15, Hc + 15), radius=Hc // 2, fill=(254, 44, 85))
    d.text((15 + (Wc - an) / 2, 15 + (Hc - tam * 1.2) / 2), texto, font=fnt, fill=(255, 255, 255))
    return Image.alpha_composite(sombra, img)


# ------------------------------------------------------------------ cuadro completo
def cuadro(n):
    t = n / FPS
    W, H = G["W"], G["H"]
    i = plano_en(t)
    img = cuadro_plano(i, t)
    p = G["planos"][i]
    fundido = 0.35
    if i > 0 and t - p["t0"] < fundido:
        prev = cuadro_plano(i - 1, t)
        img = Image.blend(prev, img, suave((t - p["t0"]) / fundido))
    arr = np.asarray(img).astype(np.float32)
    # oscurecer durante la cifra de víctimas
    osc = aparicion(t, 40.4, 43.4, 0.4, 0.3) * 0.35
    arr *= G["vin"] * (1 - osc)
    for td in DESTELLOS:
        if 0 <= t - td < 0.5:
            b = (1 - (t - td) / 0.5) ** 2 * (0.85 if td > 0 else 0.6)
            arr = arr * (1 - b) + 255 * b
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    for ts in SACUDIDAS:
        if 0 <= t - ts < 0.7:
            amp = (1 - (t - ts) / 0.7) * 22 * G["u"]
            dx, dy = int(amp * np.sin(t * 90)), int(amp * np.cos(t * 77))
            img = img.transform(img.size, Image.AFFINE, (1.03, 0, dx + W * -0.015, 0, 1.03, dy + H * -0.015),
                                resample=Image.BILINEAR)
    textos(img, t)
    return img.convert("RGB").tobytes()


def iniciar(nombre):
    preparar(nombre)


# ------------------------------------------------------------------ audio
def audio():
    ruta = SALIDA / "mezcla.wav"
    voz_wav = SALIDA / "voz.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(SALIDA / "voz.mp3"), "-ar", str(so.SR),
                    "-ac", "2", str(voz_wav)], check=True)
    import soundfile as sf
    voz, _ = sf.read(voz_wav, dtype="float32")
    n = so.seg(DUR)
    mezcla = np.zeros((n, 2), np.float32)
    v = np.zeros((n, 2), np.float32)
    v[: min(n, len(voz))] = voz[:n]
    v = v / np.abs(v).max() * 0.9

    def poner(x, t, g):
        k = so.seg(t)
        x = x[: n - k]
        mezcla[k: k + len(x)] += x * g

    # música: misterio hasta el hundimiento, triste desde ahí
    m1 = so.musica("misterio", 37.0)
    m2 = so.musica("triste", DUR - 33.0)
    musica = np.zeros((n, 2), np.float32)
    musica[: len(m1)] += m1
    k = so.seg(33.0)
    musica[k: k + len(m2)] += m2[: n - k]
    # la música baja cuando habla la voz
    env = np.abs(v).mean(1)
    env = so.lp(env, 3, 1)
    env = np.clip(env / (env.max() * 0.25), 0, 1)
    musica *= (0.55 - 0.25 * env)[:, None]
    mezcla += musica
    # efectos
    poner(so.impacto(), 0.0, 0.55)
    for _, t0, *_ in PLANOS[1:]:
        poner(so.whoosh(0.9), max(0, t0 - 0.45), 0.22)
    poner(so.olas(9.5, 0.8), 10.2, 0.16)
    poner(so.viento(16.0, 0.8), 18.8, 0.12)
    poner(so.impacto(), 21.48, 0.75)
    poner(so.impacto(), 35.02, 0.45)
    poner(so.lp(so.viento(10.5, 1.0), 300, 2), 43.4, 0.35)  # silencio de las profundidades
    poner(so.impacto(), FINAL, 0.35)
    mezcla += v
    mezcla = mezcla / np.abs(mezcla).max() * 0.95
    sf.write(ruta, mezcla, so.SR)
    return ruta


# ------------------------------------------------------------------ exportar
def exportar(nombre, wav):
    f = FORMATOS[nombre]
    EXPORTADOS.mkdir(exist_ok=True)
    destino = EXPORTADOS / f["archivo"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{f['W']}x{f['H']}", "-r", str(FPS), "-i", "-", "-i", str(wav),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", str(destino)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    with Pool(4, initializer=iniciar, initargs=(nombre,)) as pool:
        for j, datos in enumerate(pool.imap(cuadro, range(total), chunksize=6)):
            proc.stdin.write(datos)
            if j % 300 == 0:
                print(f"{nombre}: {j}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("Listo:", destino)


if __name__ == "__main__":
    formatos = sys.argv[1:] or list(FORMATOS)
    wav = audio()
    for nombre in formatos:
        exportar(nombre, wav)
