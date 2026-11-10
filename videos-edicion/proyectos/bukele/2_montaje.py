"""Paso 2: monta el documental (imagen + música) sobre la voz preparada por 1_voz.py.

Estilo cinematográfico propio: fotos de archivo con movimiento lento de cámara, color con
sombras frías y luces cálidas, viñeta y grano suave, fundidos discretos, fechas en pantalla,
rótulos de capítulo sobre negro y el sello "CURIOSIDADES DEL MUNDO" arriba a la derecha.

Uso:
  python3 2_montaje.py                       # documental completo
  python3 2_montaje.py --prueba 380 60       # solo 60 s a partir del segundo 380
  python3 2_montaje.py --cuadro 395          # una imagen fija del segundo 395 (para revisar)
Opciones: --procesos N (por defecto 4), --audio (rehacer la mezcla de audio)
"""
import argparse
import importlib.util
import json
import math
import subprocess
import sys
import time
from functools import lru_cache
from multiprocessing import Process
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import plan

AQUI = Path(__file__).parent
MATERIAL = AQUI / "material"
SALIDA = AQUI / "salida" / "corta"   # versión corta (~25 min), creada por 1b_recorte.py
W, H, FPS = 1920, 1080, 24
FUNDIDO = 0.45         # fundido entre tomas
ROJO = (214, 32, 39)
Image.MAX_IMAGE_PIXELS = None

# sonido.py del documental de Napoleón: música orquestal sintetizada
_spec = importlib.util.spec_from_file_location("sonido", AQUI.parent / "napoleon" / "sonido.py")
SN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SN)

CREDITOS = json.loads((MATERIAL / "creditos.json").read_text()) if (MATERIAL / "creditos.json").exists() else {}


# ====================================================================== tipografías
@lru_cache(None)
def fuente(nombre, tam, peso):
    f = ImageFont.truetype(str(AQUI / "fuentes" / nombre), tam)
    try:
        f.set_variation_by_axes([peso])
    except Exception:  # noqa: BLE001
        pass
    return f


def oswald(tam, peso=500):
    return fuente("Oswald[wght].ttf", tam, peso)


def mont(tam, peso=500):
    return fuente("Montserrat[wght].ttf", tam, peso)


def texto_espaciado(d, xy, txt, f, fill, espacio=0, ancla="la"):
    """Texto con separación entre letras (tracking). ancla: l/m/r + a/m/s."""
    anchos = [d.textlength(c, font=f) for c in txt]
    total = sum(anchos) + espacio * (len(txt) - 1)
    x, y = xy
    if ancla[0] == "m":
        x -= total / 2
    elif ancla[0] == "r":
        x -= total
    for c, a in zip(txt, anchos):
        d.text((x, y), c, font=f, fill=fill, anchor="l" + ancla[1])
        x += a + espacio
    return total


def partir(txt, f, ancho, d):
    palabras, lineas, actual = txt.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if d.textlength(prueba, font=f) > ancho and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = prueba
    return lineas + [actual]


# ====================================================================== color
def _curva():
    x = np.arange(256) / 255.0
    s = x + 0.10 * np.sin(2 * np.pi * x) * -0.5          # curva en S suave (más contraste)
    s = np.clip(0.035 + s * 0.94, 0, 1)                   # negros levantados, blancos suaves
    r = np.clip(s + 0.025 * (x - 0.35), 0, 1)             # luces cálidas
    g = s
    b = np.clip(s + 0.045 * (0.5 - x), 0, 1)              # sombras frías
    return [np.round(c * 255).astype(np.uint8) for c in (r, g, b)]


LUT = _curva()


def gradar(arr, saturacion=0.82):
    """Aplica la corrección de color cinematográfica a un array RGB uint8."""
    a = arr.astype(np.float32)
    gris = a.mean(axis=2, keepdims=True)
    a = gris + (a - gris) * saturacion
    a = np.clip(a, 0, 255).astype(np.uint8)
    for c in range(3):
        a[..., c] = LUT[c][a[..., c]]
    return a


def _vineta():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return np.clip(1.0 - 0.38 * np.clip(d - 0.45, 0, None) ** 1.6, 0.45, 1.0)[..., None].astype(np.float32)


VINETA = _vineta()
_rng = np.random.default_rng(7)
GRANO = [(_rng.standard_normal((H // 2, W // 2)) * 1.8).astype(np.float32) for _ in range(6)]


def acabado(frame, n):
    """Viñeta + grano de película (el grano cambia cada cuadro)."""
    f = frame.astype(np.float32) * VINETA
    g = GRANO[n % len(GRANO)]
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    return np.clip(f + g, 0, 255).astype(np.uint8)


def suave(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# ====================================================================== fuentes de imagen
@lru_cache(maxsize=24)
def cargar_foto(nombre):
    """Foto preparada: graduada y ajustada a 16:9 (las verticales llevan fondo desenfocado)."""
    ruta = MATERIAL / nombre.replace(" ", "_")
    if not ruta.exists():
        print("  FALTA", ruta.name, file=sys.stderr)
        return Image.new("RGB", (int(W * 1.18), int(H * 1.18)), (40, 40, 44))
    im = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    lienzo_w, lienzo_h = int(W * 1.18), int(H * 1.18)
    r = im.width / im.height
    if r < 1.2:  # vertical o casi cuadrada → fondo desenfocado y foto centrada
        fondo = ImageOps.fit(im, (lienzo_w // 4, lienzo_h // 4)).filter(ImageFilter.GaussianBlur(10))
        fondo = fondo.resize((lienzo_w, lienzo_h), Image.BILINEAR)
        fondo = Image.eval(fondo, lambda v: int(v * 0.35))
        alto = int(lienzo_h * 0.92)
        fg = im.resize((int(alto * r), alto), Image.LANCZOS)
        fondo.paste(fg, ((lienzo_w - fg.width) // 2, (lienzo_h - alto) // 2))
        im = fondo
    else:
        im = ImageOps.fit(im, (lienzo_w, lienzo_h), Image.LANCZOS)
    return Image.fromarray(gradar(np.asarray(im)))


def ken_burns(im, u, toma):
    """Recorte animado de la foto (u de 0 a 1 a lo largo de la toma)."""
    fx, fy = toma.get("foco", (0.5, 0.45))
    amp = 0.22 if toma.get("rapido") else 0.15
    z0, z1 = (1.0, 1.0 + amp) if toma.get("zoom", "in") == "in" else (1.0 + amp, 1.0)
    z = z0 + (z1 - z0) * u
    cw, ch = im.width / (1.18 * z) * 1.0, im.height / (1.18 * z) * 1.0
    cw, ch = W * im.width / (W * 1.18) / z, H * im.height / (H * 1.18) / z
    # el centro se desplaza del centro de la foto hacia el foco
    cx = im.width / 2 + (fx - 0.5) * (im.width - cw) * (u if z1 > z0 else 1 - u)
    cy = im.height / 2 + (fy - 0.5) * (im.height - ch) * (u if z1 > z0 else 1 - u)
    cx = min(max(cx, cw / 2), im.width - cw / 2)
    cy = min(max(cy, ch / 2), im.height - ch / 2)
    caja = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return np.asarray(im.resize((W, H), Image.BILINEAR, box=caja))


class LectorVideo:
    """Lee cuadros de un video de archivo con ffmpeg, a 24 fps y 1920x1080."""

    def __init__(self, nombre, desde):
        ruta = MATERIAL / nombre.replace(" ", "_")
        filtro = (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"eq=saturation=0.85")
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(desde), "-i", str(ruta), "-an",
                                   "-vf", filtro, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE)
        self.ultimo = np.zeros((H, W, 3), np.uint8)

    def siguiente(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.ultimo = gradar(np.frombuffer(b, np.uint8).reshape(H, W, 3))
        return self.ultimo

    def cerrar(self):
        self.p.kill()


# ====================================================================== mapas
@lru_cache(None)
def mundo():
    import warnings
    warnings.filterwarnings("ignore")
    import geopandas as gpd
    # fronteras de Natural Earth 1:50m (dominio público)
    d = gpd.read_file(AQUI / "datos" / "paises_50m.geojson")
    return d.rename(columns={"NAME": "name"})


@lru_cache(None)
def mapa_base(cual, marca=None):
    """Mapa grande (más que la pantalla) para poder acercarse. Devuelve imagen y función lon/lat→px."""
    MW, MH = int(W * 1.5), int(H * 1.5)
    if cual == "centroamerica":
        lon0, lon1, lat0, lat1 = -95.5, -79.0, 6.0, 19.5
    else:
        lon0, lon1, lat0, lat1 = -90.6, -87.2, 12.6, 14.7
    k = math.cos(math.radians((lat0 + lat1) / 2))
    esc = min(MW / ((lon1 - lon0) * k), MH / (lat1 - lat0))
    cx, cy = (lon0 + lon1) / 2, (lat0 + lat1) / 2

    def px(lon, lat):
        return MW / 2 + (lon - cx) * k * esc, MH / 2 - (lat - cy) * esc

    im = Image.new("RGB", (MW, MH), (14, 20, 28))
    d = ImageDraw.Draw(im)
    # retícula sutil
    for lon in range(-100, -70, 2 if cual == "centroamerica" else 1):
        d.line([px(lon, -10), px(lon, 30)], fill=(22, 30, 40), width=1)
    for lat in range(0, 30, 2 if cual == "centroamerica" else 1):
        d.line([px(-110, lat), px(-60, lat)], fill=(22, 30, 40), width=1)
    gdf = mundo()

    def poligonos(geom):
        return [geom] if geom.geom_type == "Polygon" else list(geom.geoms)

    for _, fila in gdf.iterrows():
        es = fila["name"] == "El Salvador"
        for pol in poligonos(fila.geometry):
            pts = [px(x, y) for x, y in pol.exterior.coords]
            d.polygon(pts, fill=(150, 26, 32) if es else (48, 54, 60), outline=(95, 102, 110))
    for _, fila in gdf.iterrows():
        if fila["name"] == "El Salvador":
            for pol in poligonos(fila.geometry):
                d.line([px(x, y) for x, y in pol.exterior.coords], fill=(240, 90, 90), width=3)
    etiquetas = {"Guatemala": (-90.4, 15.6), "Honduras": (-86.6, 14.9), "Nicaragua": (-85.2, 12.8),
                 "México": (-92.8, 17.6), "Belice": (-88.7, 17.3), "Costa Rica": (-84.2, 9.9)}
    if cual == "centroamerica":
        for nombre, (lo, la) in etiquetas.items():
            texto_espaciado(d, px(lo, la), nombre.upper(), oswald(30, 400), (150, 156, 164), 4, "mm")
        texto_espaciado(d, px(-91.5, 10.0), "OCÉANO PACÍFICO", oswald(30, 300), (70, 96, 120), 10, "mm")
    else:
        texto_espaciado(d, px(-89.2, 12.95), "OCÉANO PACÍFICO", oswald(40, 300), (70, 96, 120), 12, "mm")
        texto_espaciado(d, px(-89.9, 14.45), "GUATEMALA", oswald(38, 400), (150, 156, 164), 5, "mm")
        texto_espaciado(d, px(-87.9, 14.35), "HONDURAS", oswald(38, 400), (150, 156, 164), 5, "mm")
    puntos = {"San Salvador": (-89.19, 13.69), "Nuevo Cuscatlán": (-89.265, 13.648)}
    for nombre, (lo, la) in puntos.items():
        if cual == "centroamerica" and nombre != "San Salvador":
            continue
        if cual != "centroamerica" and marca and nombre != marca:
            continue
        x, y = px(lo, la)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(255, 255, 255))
        d.ellipse([x - 18, y - 18, x + 18, y + 18], outline=(255, 255, 255), width=2)
        d.text((x + 28, y), nombre, font=mont(40 if cual != "centroamerica" else 30, 600),
               fill=(255, 255, 255), anchor="lm")
    if cual == "centroamerica":
        x, y = px(-88.9, 13.75)
        texto_espaciado(d, (x, y + 60), "EL SALVADOR", oswald(40, 600), (255, 255, 255), 5, "mm")
    foco = px(*puntos[marca]) if marca else px(-89.0, 13.75)
    return im, (foco[0] / MW, foco[1] / MH)


def cuadro_mapa(toma, u):
    im, (fx, fy) = mapa_base(toma["cual"], toma.get("marca"))
    z = 1.0 + 0.35 * suave(u)
    vis_w, vis_h = im.width / 1.5 / z, im.height / 1.5 / z
    cx = im.width / 2 + (fx * im.width - im.width / 2) * suave(u) * 0.8
    cy = im.height / 2 + (fy * im.height - im.height / 2) * suave(u) * 0.8
    cx = min(max(cx, vis_w / 2), im.width - vis_w / 2)
    cy = min(max(cy, vis_h / 2), im.height - vis_h / 2)
    return np.asarray(im.resize((W, H), Image.BILINEAR,
                                box=(cx - vis_w / 2, cy - vis_h / 2, cx + vis_w / 2, cy + vis_h / 2)))


# ====================================================================== tarjetas gráficas
@lru_cache(maxsize=8)
def fondo_oscuro(nombre):
    im = cargar_foto(nombre).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(14))
    return Image.eval(im, lambda v: int(v * 0.28))


def cuadro_dato(toma, u):
    """Cifra grande sobre la foto oscurecida y desenfocada."""
    im = fondo_oscuro(toma["fondo"]).copy()
    d = ImageDraw.Draw(im)
    a = suave(u * 4)                 # aparición
    sube = int((1 - a) * 30)
    cifra = toma["cifra"]
    f = oswald(230 if len(cifra) < 8 else 180, 600)
    col = tuple(int(255 * a) for _ in range(3))
    d.text((W / 2, H / 2 - 90 + sube), cifra, font=f, fill=col, anchor="ms")
    ancho = int(260 * suave(u * 3))
    d.rectangle([W / 2 - ancho / 2, H / 2 - 40, W / 2 + ancho / 2, H / 2 - 34], fill=ROJO)
    for i, linea in enumerate(partir(toma["texto"], mont(46, 500), 1300, d)):
        d.text((W / 2, H / 2 + 30 + i * 60 + sube), linea, font=mont(46, 500), fill=col, anchor="ma")
    if toma.get("sub"):
        gris = tuple(int(165 * a) for _ in range(3))
        d.text((W / 2, H / 2 + 175), toma["sub"], font=mont(28, 400), fill=gris, anchor="ma")
    return np.asarray(im)


@lru_cache(None)
def telefono():
    """Teléfono genérico con publicaciones (sin marcas reales)."""
    tw, th = 520, 1900
    im = Image.new("RGB", (tw, th), (18, 20, 24))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(3)
    y = 30
    while y < th - 200:
        d.rounded_rectangle([24, y, tw - 24, y + 330], 22, fill=(44, 50, 60))
        d.ellipse([46, y + 22, 106, y + 82], fill=(70 + int(rng.integers(0, 60)), 90, 120))
        d.rounded_rectangle([122, y + 34, 122 + int(rng.integers(120, 230)), y + 50], 8, fill=(200, 205, 212))
        d.rounded_rectangle([122, y + 60, 230, y + 72], 6, fill=(120, 126, 134))
        for k in range(int(rng.integers(2, 4))):
            d.rounded_rectangle([46, y + 104 + k * 30, tw - 46 - int(rng.integers(0, 140)), y + 120 + k * 30],
                                8, fill=(160, 166, 174))
        if rng.random() < 0.6:
            d.rounded_rectangle([46, y + 200, tw - 46, y + 290], 14, fill=(70, 84, 104))
        for k, xx in enumerate((60, 190, 320)):
            d.ellipse([xx, y + 300, xx + 18, y + 318], fill=(214, 32, 39) if k == 0 else (110, 116, 124))
        y += 360
    return im


def cuadro_redes(u):
    im = Image.new("RGB", (W, H), (10, 12, 16))
    d = ImageDraw.Draw(im)
    # resplandor detrás del teléfono
    for r in range(520, 0, -40):
        c = int(16 + 34 * (1 - r / 520))
        d.ellipse([W / 2 - r * 1.3, H / 2 - r, W / 2 + r * 1.3, H / 2 + r], fill=(c, c + 2, c + 6))
    pw, ph = 560, 960
    x0, y0 = (W - pw) // 2, (H - ph) // 2 + 20
    d.rounded_rectangle([x0 - 14, y0 - 14, x0 + pw + 14, y0 + ph + 14], 64, fill=(70, 74, 82))
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 52, fill=(18, 20, 24))
    feed = telefono()
    off = int(u * (feed.height - ph + 60))
    ventana = feed.crop((0, off, feed.width, off + ph - 40)).resize((pw - 40, ph - 40))
    mascara = Image.new("L", ventana.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, ventana.width, ventana.height], 40, fill=255)
    im.paste(ventana, (x0 + 20, y0 + 20), mascara)
    # notificaciones que aparecen a los lados
    for k, (xx, yy) in enumerate([(x0 - 430, y0 + 160), (x0 + pw + 60, y0 + 380), (x0 - 400, y0 + 620)]):
        a = suave((u - 0.12 - k * 0.22) * 5)
        if a <= 0:
            continue
        c = int(58 * a)
        d.rounded_rectangle([xx, yy, xx + 370, yy + 92], 20, fill=(c, c + 3, c + 8))
        d.ellipse([xx + 20, yy + 22, xx + 68, yy + 70], fill=(int(214 * a), int(32 * a), int(39 * a)))
        d.rounded_rectangle([xx + 86, yy + 28, xx + 330, yy + 42], 7, fill=(int(215 * a),) * 3)
        d.rounded_rectangle([xx + 86, yy + 54, xx + 260, yy + 66], 6, fill=(int(140 * a),) * 3)
    return gradar(np.asarray(im), 1.0)


# ====================================================================== rótulos
def cuadro_capitulo(toma, u, dur):
    """Rótulo de capítulo sobre negro: "CAPÍTULO 3" + título."""
    t = u * dur
    if toma.get("fondo"):
        f = fondo_oscuro(toma["fondo"])
        z = 1.0 + 0.06 * u
        cw, ch = W / z, H / z
        im = f.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        m = suave(t / 0.6) * suave((dur - t) / 0.5)
        im = Image.blend(Image.new("RGB", (W, H), (6, 6, 8)), im, m)
    else:
        im = Image.new("RGB", (W, H), (6, 6, 8))
    d = ImageDraw.Draw(im)
    a = suave(t / 0.9) * suave((dur - t) / 0.7)
    a2 = suave((t - 0.35) / 0.9) * suave((dur - t) / 0.7)
    blanco = tuple(int(240 * a2) for _ in range(3))
    rojo = tuple(int(c * a) for c in ROJO)
    etiqueta = toma["etiqueta"]
    texto_espaciado(d, (W / 2, H / 2 - 70), etiqueta, oswald(40, 500), rojo, 14, "ms")
    ancho = int(120 + 60 * suave(t / 1.5))
    d.rectangle([W / 2 - ancho / 2, H / 2 - 44, W / 2 + ancho / 2, H / 2 - 40], fill=rojo)
    lineas = partir(toma["titulo"], mont(70, 600), 1500, d)
    y = H / 2 + 20 - (len(lineas) - 1) * 44 + int((1 - a2) * 16)
    for i, linea in enumerate(lineas):
        d.text((W / 2, y + i * 88), linea, font=mont(70, 600), fill=blanco, anchor="ma")
    return np.asarray(im)


def cuadro_titulo(u, dur):
    """Apertura tras el avance: NAYIB BUKELE entra con un golpe sobre una foto oscura."""
    base = Image.fromarray(ken_burns(cargar_foto("Nayib Bukele 2022 Independence Day Speech.jpg"), u, {}))
    base = Image.eval(base, lambda v: int(v * 0.3))
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rectangle([0, H / 2 - 260, W, H / 2 + 170], fill=150)
    base = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), base, sombra.filter(ImageFilter.GaussianBlur(70)))
    t = u * dur
    a = suave(t / 0.25) * suave((dur - t) / 0.8)
    b = suave((t - 1.0) / 1.0) * suave((dur - t) / 0.8)
    esc = 1.0 + 0.18 * (1 - suave(t / 0.45))          # el título "cae" desde más grande
    capa = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    texto_espaciado(dc, (W / 2, 250), "NAYIB BUKELE", oswald(200, 600), (255, 255, 255, 255), 24, "ms")
    if esc != 1.0:
        capa = capa.resize((int(W * esc), int(400 * esc)), Image.BILINEAR)
    capa.putalpha(Image.eval(capa.getchannel("A"), lambda v: int(v * a)))
    base = base.convert("RGBA")
    base.alpha_composite(capa, (int((W - capa.width) / 2), int(H / 2 - 230 * esc)))
    base = base.convert("RGB")
    d = ImageDraw.Draw(base)
    ancho = int(560 * suave((t - 0.4) / 1.2))
    d.rectangle([W / 2 - ancho / 2, H / 2 + 50, W / 2 + ancho / 2, H / 2 + 57],
                fill=tuple(int(c * a) for c in ROJO))
    d.text((W / 2, H / 2 + 95), "La historia completa del hombre que cambió El Salvador", font=mont(44, 400),
           fill=tuple(int(230 * b) for _ in range(3)), anchor="ma")
    return np.asarray(base)


def cuadro_final(u, dur):
    """Cierre: sello del canal, agradecimiento e invitación a suscribirse."""
    im = Image.new("RGB", (W, H), (6, 6, 8))
    d = ImageDraw.Draw(im)
    t = u * dur
    a = suave((t - 0.2) / 1.0) * suave((dur - t) / 1.2)
    b = suave((t - 1.2) / 1.0) * suave((dur - t) / 1.2)
    w = texto_espaciado(d, (W / 2, H / 2 - 10), "CURIOSIDADES DEL MUNDO", oswald(96, 600),
                        tuple(int(245 * a) for _ in range(3)), 12, "ms")
    ancho = w * suave((t - 0.3) / 1.2)
    d.rectangle([W / 2 - ancho / 2, H / 2 + 16, W / 2 + ancho / 2, H / 2 + 24], fill=tuple(int(c * a) for c in ROJO))
    d.text((W / 2, H / 2 + 70), "Gracias por ver", font=mont(40, 500), fill=tuple(int(225 * b) for _ in range(3)),
           anchor="ma")
    texto_espaciado(d, (W / 2, H / 2 + 175), "SUSCRÍBETE PARA MÁS HISTORIAS", oswald(34, 500),
                    tuple(int(c * b) for c in ROJO), 6, "ms")
    return np.asarray(im)


@lru_cache(None)
def sello():
    """CURIOSIDADES DEL MUNDO con la rayita roja (arriba a la derecha). Sin planeta."""
    im = Image.new("RGBA", (520, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = texto_espaciado(d, (510, 46), "CURIOSIDADES DEL MUNDO", oswald(30, 500), (255, 255, 255, 235), 4, "rs")
    d.rectangle([510 - w, 56, 510, 60], fill=ROJO + (255,))
    sombra = im.filter(ImageFilter.GaussianBlur(4))
    sombra = Image.eval(sombra.getchannel("A"), lambda v: int(v * 0.6))
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    capa.putalpha(sombra)
    return Image.alpha_composite(capa, im)


def rotulo_fecha(fecha, lugar):
    im = Image.new("RGBA", (1000, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 18, 6, 118 if lugar else 82], fill=ROJO + (255,))
    texto_espaciado(d, (26, 62), fecha.upper(), oswald(50, 500), (255, 255, 255, 255), 3, "ls")
    if lugar:
        d.text((28, 82), lugar, font=mont(28, 500), fill=(220, 220, 220, 255), anchor="la")
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sombra.putalpha(Image.eval(im.getchannel("A").filter(ImageFilter.GaussianBlur(6)), lambda v: int(v * 0.7)))
    return Image.alpha_composite(sombra, im)


@lru_cache(maxsize=64)
def rotulo_fecha_c(fecha, lugar):
    return rotulo_fecha(fecha, lugar)


@lru_cache(maxsize=64)
def rotulo_credito(nombre):
    c = CREDITOS.get(nombre.replace(" ", "_"))
    if not c or c["licencia"] in ("CC0", "Public domain", "Dominio público", "PDM"):
        return None
    autor = (c.get("autor") or "").replace("\n", " ").strip()
    if len(autor) > 45:
        autor = autor[:44] + "…"
    txt = f"{'Video' if nombre.endswith(('.webm', '.ogv')) else 'Foto'}: {autor} · {c['licencia']}"
    f = mont(17, 500)
    im = Image.new("RGBA", (int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f)) + 10, 28),
                   (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 4), txt, font=f, fill=(235, 235, 235, 150))
    return im


@lru_cache(None)
def texto_grande(txt):
    im = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    texto_espaciado(d, (W / 2, 120), txt, oswald(92, 600), (255, 255, 255, 255), 6, "ms")
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sombra.putalpha(Image.eval(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)), lambda v: int(v * 0.85)))
    return Image.alpha_composite(sombra, im)


def pegar(frame, capa, x, y, alfa=1.0):
    if alfa <= 0:
        return frame
    a = np.asarray(capa).astype(np.float32)
    h, w = a.shape[:2]
    reg = frame[y:y + h, x:x + w].astype(np.float32)
    m = a[..., 3:4] / 255.0 * alfa
    frame[y:y + h, x:x + w] = (reg * (1 - m) + a[..., :3] * m).astype(np.uint8)
    return frame


# ====================================================================== línea de tiempo
def construir():
    """Línea de tiempo de la versión corta: avance, título, capítulos y final."""
    voz = json.loads((SALIDA / "voz.json").read_text())
    fr = voz["frases"]
    total = voz["duracion"] + 5.0
    nuevo = {f["orig"]: k for k, f in enumerate(fr) if not f.get("avance")}
    avance = [f for f in fr if f.get("avance")]

    def t_orig(i, frac=0.0):
        f = fr[nuevo[i]]
        return f["ini"] + frac * (f["fin"] - f["ini"]) - 0.25

    def siguiente_orig(i):
        return min((o for o in nuevo if o > i), default=max(nuevo))

    bloques = []
    # 1) avance: cortes rápidos dentro de cada frase, con destello y golpe al empezar cada una
    destellos = []
    for k, f in enumerate(avance):
        ini = 0.0 if k == 0 else f["ini"] - 0.3
        fin = avance[k + 1]["ini"] - 0.3 if k + 1 < len(avance) else f["fin"] + 0.5
        fotos = plan.AVANCE[f["orig"]]
        paso = (fin - ini) / len(fotos)
        for m, a in enumerate(fotos):
            bloques.append(dict(tipo="foto", archivo=a, ini=ini + m * paso, fin=ini + (m + 1) * paso,
                                rapido=True, zoom="in" if (k + m) % 2 == 0 else "out",
                                texto_grande="¿QUIÉN ES REALMENTE NAYIB BUKELE?" if f["orig"] == 16 else None))
        destellos.append(ini if k else 0.25)
    fin_avance = avance[-1]["fin"] + 0.5
    # 2) título (golpe fuerte) hasta el rótulo de la introducción
    i_intro = min(plan.SECCIONES)
    bloques.append(dict(tipo="titulo", ini=fin_avance, fin=t_orig(i_intro) - 0.3))
    destellos.append(fin_avance + 0.05)
    # 3) rótulos de capítulo y secciones
    for n, (i, titulo) in list(plan.CAPITULOS.items()) + [(None, (i, v)) for i, v in plan.SECCIONES.items()]:
        if isinstance(titulo, tuple):
            etiqueta, titulo = titulo
        else:
            etiqueta = f"CAPÍTULO {n}"
        f = fr[nuevo[i]]
        ini = f["ini"] - 0.75
        bloques.append(dict(tipo="capitulo", etiqueta=etiqueta, titulo=titulo, ini=ini,
                            fin=max(f["fin"] + 1.0, ini + 3.4)))
    bloques.append(dict(tipo="final", ini=fr[-1]["ini"] - 0.3, fin=total))
    bloques.sort(key=lambda b: b["ini"])
    # fondo de cada rótulo de capítulo: la primera foto que viene después

    # 4) tomas del plan; las de frases quitadas quedan de reserva para rellenar tomas largas
    tomas, reserva = [], []
    for ancla, t in sorted(plan.TOMAS, key=lambda x: x[0]):
        i = int(ancla)
        if i in nuevo:
            tomas.append(dict(t, ini=t_orig(i, ancla - i)))
        else:
            reserva.append(dict(t, ini=t_orig(siguiente_orig(i)), fecha=None, lugar=None))
    for tm in tomas:
        for b in bloques:
            if b["ini"] - 0.3 <= tm["ini"] < b["fin"]:
                tm["ini"] = b["fin"]
    tomas.sort(key=lambda x: x["ini"])
    # quitar tomas que quedan casi encima de otra
    limpias = []
    for tm in tomas:
        if limpias and tm["ini"] - limpias[-1]["ini"] < 1.6:
            continue
        limpias.append(tm)
    tomas = limpias

    def asignar_fin(tomas):
        cortes = sorted([t["ini"] for t in tomas] + [b["ini"] for b in bloques] + [total])
        for tm in tomas:
            tm["fin"] = min((c for c in cortes if c > tm["ini"] + 1e-6), default=tm["ini"])

    asignar_fin(tomas)
    # 5) ritmo: ninguna foto dura más de 6,5 s; se parten con fotos de reserva cercanas
    #    (o con la misma foto en otro encuadre si no hay)
    MAX = 6.5
    for _ in range(6):
        nuevas = []
        for tm in tomas:
            dur = tm["fin"] - tm["ini"]
            if (tm["tipo"] == "foto" and dur > MAX) or (tm["tipo"] in ("dato", "redes") and dur > 8.0):
                mitad = tm["ini"] + (min(dur * 0.55, 6.5) if tm["tipo"] != "foto" else dur / 2)
                cerca = sorted((r for r in reserva if abs(r["ini"] - mitad) < 90),
                               key=lambda r: abs(r["ini"] - mitad))
                if cerca:
                    r = cerca[0]
                    reserva.remove(r)
                    extra = dict(r, ini=mitad)
                elif tm["tipo"] in ("dato", "redes"):
                    extra = dict(tipo="foto", archivo=tm.get("fondo") or "Palacio Nacional en San Salvador.JPG",
                                 ini=mitad, zoom="out")
                else:
                    extra = dict(tm, ini=mitad, fecha=None, lugar=None,
                                 zoom="out" if tm.get("zoom", "in") == "in" else "in",
                                 foco=(0.3, 0.4) if tm.get("foco", (0.5, 0.45))[0] >= 0.5 else (0.7, 0.4))
                nuevas.append(extra)
        if not nuevas:
            break
        tomas = sorted(tomas + nuevas, key=lambda x: x["ini"])
        asignar_fin(tomas)
    lista = [tm for tm in tomas if tm["fin"] - tm["ini"] >= 1.2 and tm["ini"] < total]
    clips = sorted(lista + bloques, key=lambda c: c["ini"])
    for a, b in zip(clips, clips[1:]):
        if b["ini"] > a["fin"]:
            a["fin"] = b["ini"]
    # fondo desenfocado de cada rótulo de capítulo: la foto que sigue
    for k, c in enumerate(clips):
        if c["tipo"] == "capitulo":
            sig = next((d for d in clips[k + 1:] if d["tipo"] == "foto"), None)
            c["fondo"] = sig["archivo"] if sig else None
        if c["tipo"] == "dato":
            destellos.append(c["ini"])
    return dict(clips=clips, total=total, frases=fr, destellos=sorted(destellos))


# ====================================================================== render
class Render:
    def __init__(self, tl):
        self.tl = tl
        self.clips = tl["clips"]
        self.videos = {}

    def base(self, ci, t):
        c = self.clips[ci]
        dur = c["fin"] - c["ini"] + FUNDIDO
        u = min(max((t - c["ini"]) / dur, 0), 1)
        tipo = c["tipo"]
        if tipo == "foto":
            return ken_burns(cargar_foto(c["archivo"]), u, c)
        if tipo == "video":
            lv = self.videos.get(ci)
            if lv is None:
                lv = self.videos[ci] = LectorVideo(c["archivo"], c.get("desde", 0) + max(0.0, t - c["ini"]))
            return lv.siguiente()
        if tipo == "mapa":
            return gradar(cuadro_mapa(c, u), 0.95)
        if tipo == "dato":
            return cuadro_dato(c, u)
        if tipo == "redes":
            return cuadro_redes(u)
        dur = c["fin"] - c["ini"]
        u = min(max((t - c["ini"]) / dur, 0), 1)
        if tipo == "capitulo":
            return cuadro_capitulo(c, u, dur)
        if tipo == "titulo":
            return gradar(cuadro_titulo(u, dur), 1.0)
        if tipo == "final":
            return cuadro_final(u, dur)
        raise ValueError(tipo)

    def cuadro(self, n):
        t = n / FPS
        idx = [i for i, c in enumerate(self.clips) if c["ini"] <= t < c["fin"] + FUNDIDO]
        actual = [i for i in idx if self.clips[i]["ini"] <= t < self.clips[i]["fin"]]
        ci = actual[0] if actual else idx[-1]
        frame = self.base(ci, t)
        # fundido con el clip anterior (que sigue un poco más allá de su final)
        prev = [i for i in idx if i < ci and t < self.clips[i]["fin"] + FUNDIDO]
        if prev:
            p = prev[-1]
            u = (t - self.clips[ci]["ini"]) / FUNDIDO
            a = suave(u)
            if a < 1:
                otro = self.base(p, t)
                frame = (otro.astype(np.float32) * (1 - a) + frame.astype(np.float32) * a).astype(np.uint8)
        # cerrar lectores de video que ya no se usan
        for k in list(self.videos):
            if t > self.clips[k]["fin"] + FUNDIDO + 0.1:
                self.videos.pop(k).cerrar()
        if not frame.flags.writeable:
            frame = frame.copy()
        c = self.clips[ci]
        en_rotulo = c["tipo"] in ("capitulo", "final")
        if not en_rotulo:
            frame = acabado(frame, n)
            # fecha y lugar (abajo a la izquierda)
            if c.get("fecha") or c.get("lugar"):
                tt = t - c["ini"]
                a = suave((tt - 0.5) / 0.6) * suave((min(5.5, c["fin"] - c["ini"] - 0.3) - tt) / 0.6)
                if a > 0:
                    rot = rotulo_fecha_c(c.get("fecha") or "", c.get("lugar") or "") if c.get("fecha") else \
                        rotulo_fecha_c(c["lugar"], "")
                    frame = pegar(frame, rot, 90, H - 230, a)
            # crédito de la foto (CC BY / BY-SA)
            nombre = c.get("archivo") or c.get("fondo")
            if nombre:
                cr = rotulo_credito(nombre)
                if cr is not None:
                    tt = t - c["ini"]
                    a = suave(tt / 0.5) * suave((c["fin"] - t) / 0.4)
                    frame = pegar(frame, cr, W - cr.width - 40, H - 46, a)
        # texto grande del avance
        if c.get("texto_grande"):
            tt = t - c["ini"]
            a = suave((tt - 0.6) / 0.5)
            frame = pegar(frame, texto_grande(c["texto_grande"]), 0, H - 330, a)
        # destellos (golpes de luz en el avance, el título y las cifras)
        for d0 in self.tl.get("destellos", []):
            if d0 <= t < d0 + 0.35:
                k = 0.85 * math.exp(-(t - d0) / 0.09)
                frame = (frame.astype(np.float32) * (1 - k) + 255 * k).astype(np.uint8)
        # sello del canal (siempre arriba a la derecha, salvo en el rótulo final)
        if c["tipo"] != "final":
            a = 1.0
            if c["tipo"] == "titulo":
                a = suave((t - c["ini"] - 1.5) / 1.0)
            frame = pegar(frame, sello(), W - 520 - 60, 38, a)
        return frame


def trabajador(tl, f0, f1, ruta):
    r = Render(tl)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-b:v", "2150k", "-maxrate", "2800k",
           "-bufsize", "5600k",
           "-pix_fmt", "yuv420p", "-tune", "film", str(ruta)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(f0, f1):
        p.stdin.write(r.cuadro(n).tobytes())
        if (n - f0) % 480 == 0 and n > f0:
            hecho = (n - f0) / (f1 - f0)
            print(f"  [{ruta.stem}] {hecho * 100:.0f} %  ({(time.time() - t0) / 60:.1f} min)", flush=True)
    p.stdin.close()
    p.wait()


# ====================================================================== audio
MUSICA = {   # estado de ánimo de la música por capítulo (-1 = avance, 0 = introducción)
    -1: "tension", 0: "misterio", 1: "triste", 2: "misterio", 3: "majestuoso", 4: "majestuoso", 5: "misterio",
    6: "epico", 7: "tension", 8: "tension", 9: "frio", 10: "misterio", 11: "tension", 12: "frio",
    13: "misterio", 14: "triste", 15: "frio", 16: "majestuoso", 17: "frio", 18: "misterio",
    19: "majestuoso", 20: "misterio", 21: "triste",
}


def mezclar(tl):
    SR = SN.SR
    voz, sr = sf.read(SALIDA / "voz.wav", dtype="float32")
    assert sr == SR
    n = int(tl["total"] * SR)
    v = np.zeros(n, np.float32)
    v[: len(voz)] = voz[:n]
    # secciones musicales: empiezan en cada rótulo de capítulo
    titulo = next(c for c in tl["clips"] if c["tipo"] == "titulo")
    marcas = [(0.0, -1), (titulo["ini"], 0)]          # -1 = avance (tensión)
    for c in tl["clips"]:
        if c["tipo"] == "capitulo":
            num = int(c["etiqueta"].split()[-1]) if c["etiqueta"].startswith("CAP") else (
                0 if c["etiqueta"] == "INTRODUCCIÓN" else 21)
            if num:
                marcas.append((c["ini"], num))
    marcas.append((tl["total"], None))
    musica = np.zeros((n, 2), np.float32)
    for (t0, num), (t1, _) in zip(marcas, marcas[1:]):
        m = SN.musica(MUSICA[num], t1 - t0 + 3.0)
        i = int(t0 * SR)
        musica[i: i + len(m)] += m[: n - i]
    # efectos: golpe grave suave en cada rótulo de capítulo
    for c in tl["clips"]:
        if c["tipo"] in ("capitulo", "final"):
            g = SN.impacto() * 0.35
            w = SN.whoosh(1.4) * 0.18
            i = int(c["ini"] * SR)
            j = max(0, i - len(w) + int(0.2 * SR))
            musica[j: j + len(w)] += w[: n - j]
            musica[i: i + len(g)] += g[: n - i]
    # golpes de sonido en cada destello (avance, título y cifras) y un "boom" grande en el título
    for d0 in tl.get("destellos", []):
        grande = abs(d0 - titulo["ini"]) < 0.3
        g = SN.impacto() * (0.9 if grande else 0.45)
        i = int(d0 * SR)
        musica[i: i + len(g)] += g[: n - i]
        if grande:
            w = SN.whoosh(2.2) * 0.35
            j = max(0, i - len(w))
            musica[j: j + len(w)] += w[: n - j]
            tb = SN.timbal(36.7) * 1.2
            musica[i: i + len(tb)] += tb[: n - i]
    # la música baja cuando habla la voz (compresión lateral)
    env = np.abs(v)
    k = int(0.35 * SR)
    env = np.convolve(env, np.ones(k, np.float32) / k, mode="same")
    habla = np.clip(env / 0.02, 0, 1)
    # suavizar subidas/bajadas
    paso = int(0.05 * SR)
    hs = habla[::paso]
    for i in range(1, len(hs)):
        hs[i] = max(hs[i], hs[i - 1] * 0.93)
    habla = np.repeat(hs, paso)[:n]
    if len(habla) < n:
        habla = np.pad(habla, (0, n - len(habla)), mode="edge")
    gan_m = 0.42 - 0.30 * habla
    voz_st = np.repeat(v[:, None], 2, 1) * 1.0
    mezcla = voz_st + musica * gan_m[:, None]
    # fundido final
    f = int(3.0 * SR)
    mezcla[-f:] *= np.linspace(1, 0, f)[:, None]
    pico = np.abs(mezcla).max()
    mezcla = mezcla / max(pico, 1e-6) * 0.93
    sf.write(SALIDA / "audio_final.wav", mezcla, SR, subtype="PCM_16")


# ====================================================================== textos
def hms(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}"


def srt_t(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t % 1 * 1000):03d}"


CORRECCIONES = {"Najib": "Nayib", "Boukele": "Bukele", "Buque le": "Bukele", "secot": "CECOT",
                "Secot": "CECOT", "Nallí Barmando Bukele Ortés": "Nayib Armando Bukele Ortez",
                "Olga Hortés": "Olga Ortez", "Overmed": "Obermet", "nuevas ideas": "Nuevas Ideas",
                "arena": "ARENA", "Arena": "ARENA", "Salvadorénea": "salvadoreña", "el Salvador": "El Salvador",
                "del Salvador": "de El Salvador", "Ep. 3": "", "¿Cómo fue su inf": "¿Cómo fue su infancia?"}


def corregir(txt):
    for a, b in CORRECCIONES.items():
        txt = txt.replace(a, b)
    return txt[:1].upper() + txt[1:]


def escribir_textos(tl):
    fr = tl["frases"]
    with open(SALIDA / "bukele.srt", "w") as f:
        for k, s in enumerate(fr, 1):
            f.write(f"{k}\n{srt_t(s['ini'])} --> {srt_t(s['fin'])}\n{corregir(s['texto'])}\n\n")
    lineas = ["00:00:00 Avance"]
    for c in tl["clips"]:
        if c["tipo"] == "capitulo":
            nombre = f"Capítulo {c['etiqueta'].split()[-1]}: {c['titulo']}" if c["etiqueta"].startswith("CAP") \
                else c["etiqueta"].capitalize() + ": " + c["titulo"]
            lineas.append(f"{hms(c['ini'] + 0.5)} {nombre}")
    (SALIDA / "capitulos.txt").write_text("\n".join(lineas) + "\n")
    usados = {c.get("archivo") for c in tl["clips"]} | {c.get("fondo") for c in tl["clips"]}
    usados = sorted(u.replace(" ", "_") for u in usados if u)
    cr = ["Material de archivo (licencias libres):", ""]
    for u in usados:
        c = CREDITOS.get(u)
        if c:
            cr.append(f"- {c.get('titulo') or u} — {c.get('autor') or 'autor desconocido'} — {c['licencia']}"
                      f" — {c.get('pagina') or ''}")
    cr += ["", "Fuentes Oswald y Montserrat (SIL Open Font License).",
           "Música y efectos de sonido generados por código."]
    (SALIDA / "creditos.txt").write_text("\n".join(cr) + "\n")


# ====================================================================== principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", nargs=2, type=float)
    ap.add_argument("--cuadro", type=float)
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--audio", action="store_true", help="rehacer la mezcla de audio")
    a = ap.parse_args()
    tl = construir()
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "linea_de_tiempo.json").write_text(json.dumps(tl["clips"], ensure_ascii=False, indent=0))
    if a.cuadro is not None:
        img = Render(tl).cuadro(int(a.cuadro * FPS))
        ruta = SALIDA / f"cuadro_{a.cuadro:.0f}.jpg"
        Image.fromarray(img).save(ruta, quality=92)
        print(ruta)
        return
    t0 = time.time()
    audio = SALIDA / "audio_final.wav"
    if a.audio or not audio.exists() or audio.stat().st_mtime < (SALIDA / "voz.wav").stat().st_mtime:
        print("Audio (unos 6 minutos)...", flush=True)
        mezclar(tl)
    else:
        print("Audio: se reutiliza salida/audio_final.wav (usa --audio para rehacerlo)", flush=True)
    escribir_textos(tl)
    if a.prueba:
        f0, f1 = int(a.prueba[0] * FPS), int((a.prueba[0] + a.prueba[1]) * FPS)
    else:
        f0, f1 = 0, int(tl["total"] * FPS)
    partes = []
    paso = math.ceil((f1 - f0) / a.procesos)
    procs = []
    for k in range(a.procesos):
        g0, g1 = f0 + k * paso, min(f1, f0 + (k + 1) * paso)
        if g0 >= g1:
            continue
        ruta = SALIDA / f"trozo_{k}.mp4"
        partes.append(ruta)
        p = Process(target=trabajador, args=(tl, g0, g1, ruta))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
    lista = SALIDA / "trozos.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes))
    video = SALIDA / "video_sin_audio.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", str(video)], check=True)
    nombre = "Bukele_prueba.mp4" if a.prueba else "Nayib_Bukele_documental.mp4"
    ss = ["-ss", str(f0 / FPS), "-t", str((f1 - f0) / FPS)] if a.prueba else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), *ss, "-i",
                    str(SALIDA / "audio_final.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(SALIDA / nombre)], check=True)
    for p in partes:
        p.unlink()
    print(f"Listo: {SALIDA / nombre}  ({(time.time() - t0) / 60:.1f} min)")


if __name__ == "__main__":
    sys.exit(main())
