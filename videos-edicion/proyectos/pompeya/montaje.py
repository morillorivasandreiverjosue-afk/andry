"""Paso 2: monta el documental de Pompeya (imagen, efectos, música, voz y subtítulos).

Uso: python3 montaje.py <carpeta_salida> [--procesos 4] [--prueba SECCION]
Necesita <salida>/imagenes/t01..t16.png (recortar.py) y <salida>/voz/cap1..cap9.mp3 (ElevenLabs).
Crea <salida>/Pompeya_documental.mp4, pompeya.srt y capitulos.txt.
"""
import argparse
import math
import re
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "napoleon"))
import sonido as S  # noqa: E402

W, H, FPS = 1920, 1080, 30
VELOCIDAD_VOZ = 1.25  # la narración original dura ~11 min; así queda en ~9
INTRO = 5.0          # segundos de la portada antes del primer capítulo
PAUSA = 1.0          # silencio entre capítulos
FUENTES = AQUI.parent / "napoleon" / "fuentes"
ROMANOS = "I II III IV V VI VII VIII IX".split()

# Cada capítulo: imágenes (nombre, desde, hasta en fracción del capítulo), música, acción y datos curiosos
CAPITULOS = [
    {"imagenes": [("t01", 0, .45), ("t03", .45, .62), ("t16", .62, 1)], "musica": "misterio",
     "accion": [(.45, .62)], "datos": []},
    {"imagenes": [("t02", 0, .4), ("t06", .4, .75), ("t01", .75, 1)], "musica": "romantico", "accion": [],
     "datos": [(.42, "En los muros de Pompeya se han hallado miles de grafitis: anuncios electorales, "
                     "bromas e incluso declaraciones de amor.")]},
    {"imagenes": [("t03", 0, .3), ("mapa", .3, .58), ("t04", .58, .8), ("t03", .8, 1)], "musica": "tension",
     "accion": [(0, .3), (.58, 1)],
     "datos": [(.04, "Plinio el Joven vio la erupción desde Miseno y comparó la nube con un pino gigantesco.")]},
    {"imagenes": [("t04", 0, .35), ("t05", .35, .55), ("t03", .55, .8), ("t05", .8, 1)], "musica": "epico",
     "accion": [(0, .8)],
     "datos": [(.56, "Los flujos piroclásticos pueden superar los 100 km/h y alcanzar cientos de grados.")]},
    {"imagenes": [("t05", 0, .3), ("t09", .3, .7), ("t06", .7, 1)], "musica": "triste", "accion": [],
     "datos": [(.42, "Los moldes de yeso se hacen desde 1863, con la técnica del arqueólogo Giuseppe Fiorelli.")]},
    {"imagenes": [("t10", 0, .5), ("t05", .5, 1)], "musica": "misterio", "accion": [], "datos": []},
    {"imagenes": [("t07", 0, .5), ("t11", .5, 1)], "musica": "majestuoso", "accion": [],
     "datos": [(.08, "Las excavaciones comenzaron en 1748, pero hasta 1763 una inscripción no confirmó "
                     "que aquella ciudad era Pompeya.")]},
    {"imagenes": [("t08", 0, .5), ("t12", .5, 1)], "musica": "misterio", "accion": [],
     "datos": [(.55, "Aún hoy, cerca de un tercio de la antigua ciudad sigue sin excavar.")]},
    {"imagenes": [("t13", 0, .25), ("t14", .25, .5), ("t15", .5, .75), ("t16", .75, 1)], "musica": "majestuoso",
     "accion": [], "datos": []},
]
# Ceniza que cae (0 = nada) en cada capítulo
CENIZA = [0, 0, 1.0, 1.4, 0.35, 0, 0, 0, 0]


def fuente(nombre, tam):
    return ImageFont.truetype(str(FUENTES / nombre), tam)


def leer_guion():
    titulo, caps = None, []
    for linea in (AQUI / "guion.txt").read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            caps.append({"titulo": linea[3:], "texto": ""})
        elif linea.strip() and caps:
            caps[-1]["texto"] = linea.strip()
        elif linea.strip():
            titulo = linea.strip()
    return titulo, caps


def duracion(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)],
                       capture_output=True, text=True)
    return float(r.stdout)


def preparar_voz(salida):
    """Acelera cada capítulo y lo pasa a wav estéreo 44,1 kHz."""
    for i in range(1, 10):
        wav = salida / "voz" / f"cap{i}.wav"
        if not wav.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(salida / "voz" / f"cap{i}.mp3"),
                            "-af", f"atempo={VELOCIDAD_VOZ}", "-ar", "44100", "-ac", "2", str(wav)], check=True)


def linea_de_tiempo(salida):
    t, plan = INTRO, []
    for i in range(9):
        d = duracion(salida / "voz" / f"cap{i + 1}.wav")
        plan.append({"inicio": t, "voz": t + 0.6, "dur": d + 0.6 + PAUSA, "dur_voz": d})
        t += d + 0.6 + PAUSA
    return plan, t + 3.0  # 3 s de cierre


# ------------------------------------------------------------------ imagen
_CACHE = {}


def imagen(nombre):
    if nombre not in _CACHE:
        _CACHE[nombre] = Image.open(SALIDA / "imagenes" / f"{nombre}.png").convert("RGB")
    return _CACHE[nombre]


def suave(u):
    return u * u * (3 - 2 * u)


def ken_burns(img, u, semilla, accion, t_abs, golpe):
    """Encuadre con zoom y paneo. Nunca muestra la franja superior (donde estaba la marca de tiempo)."""
    sw, sh = img.size
    r = np.random.default_rng(semilla)
    z0, z1 = (1.22, 1.42) if r.random() < .5 else (1.42, 1.22)
    if accion:
        z0, z1 = 1.25, 1.5
    z = z0 + (z1 - z0) * suave(u) + 0.10 * golpe
    w, h = sw / z, sh / z
    ymin = sh * 0.16
    ax, bx = r.uniform(0, 1, 2)
    ay, by = r.uniform(0, 1, 2)
    x = (ax + (bx - ax) * suave(u)) * (sw - w)
    y = ymin + (ay + (by - ay) * suave(u)) * max(0, sh - h - ymin)
    if accion:  # temblor de cámara
        a = 7 + 22 * golpe
        x += a * (math.sin(t_abs * 47.1) + 0.6 * math.sin(t_abs * 83.3 + 1.3))
        y += a * (math.sin(t_abs * 53.7 + 2.1) + 0.6 * math.sin(t_abs * 91.9))
    x = min(max(x, 0), sw - w)
    y = min(max(y, ymin), sh - h)
    return img.transform((W, H), Image.EXTENT, (x, y, x + w, y + h), Image.BILINEAR)


# --------------------------------------------------- mapa (escena propia)
LON0, LON1, LAT0, LAT1 = 13.98, 14.78, 40.52, 40.94
COSTA = [(40.94, 14.03), (40.84, 14.04), (40.79, 14.06), (40.778, 14.09), (40.81, 14.10), (40.823, 14.12),
         (40.80, 14.16), (40.795, 14.18), (40.83, 14.22), (40.84, 14.26), (40.81, 14.335), (40.785, 14.37),
         (40.75, 14.445), (40.70, 14.48), (40.66, 14.43), (40.63, 14.375), (40.61, 14.34), (40.57, 14.325),
         (40.60, 14.40), (40.63, 14.48), (40.634, 14.60), (40.68, 14.76), (40.67, 14.78), (40.94, 14.78)]
LUGARES = {"Vesubio": (40.821, 14.426), "Pompeya": (40.749, 14.485), "Herculano": (40.806, 14.348),
           "Neápolis (Nápoles)": (40.85, 14.255), "Miseno": (40.778, 14.09), "Estabia": (40.70, 14.49)}


def geo(lat, lon):
    mx, my = 140, 90
    x = mx + (lon - LON0) / (LON1 - LON0) * (W - 2 * mx)
    y = my + (LAT1 - lat) / (LAT1 - LAT0) * (H - 2 * my)
    return x, y


def mapa_base():
    if "mapa" in _CACHE:
        return _CACHE["mapa"]
    rng = np.random.default_rng(79)
    mar = np.zeros((H, W, 3), np.float32) + np.array([28, 52, 68], np.float32)
    papel = Image.fromarray(np.clip(mar + rng.normal(0, 5, mar.shape), 0, 255).astype(np.uint8))
    tierra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(tierra).polygon([geo(*p) for p in COSTA], fill=255)
    cx, cy = geo(40.55, 14.235)
    ImageDraw.Draw(tierra).ellipse((cx - 38, cy - 14, cx + 38, cy + 14), fill=255)  # Capri
    textura = np.zeros((H, W, 3), np.float32) + np.array([156, 128, 88], np.float32)
    textura += rng.normal(0, 9, textura.shape)
    papel.paste(Image.fromarray(np.clip(textura, 0, 255).astype(np.uint8)), (0, 0), tierra)
    # línea de costa luminosa
    borde = tierra.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.5))
    papel.paste(Image.new("RGB", (W, H), (230, 205, 150)), (0, 0), borde)
    # Vesubio: relieve
    d = ImageDraw.Draw(papel)
    vx, vy = geo(*LUGARES["Vesubio"])
    for k, c in enumerate([(110, 88, 62), (92, 72, 52), (74, 56, 42)]):
        rr = 95 - k * 28
        d.ellipse((vx - rr, vy - rr * .8, vx + rr, vy + rr * .8), fill=c)
    papel = papel.filter(ImageFilter.GaussianBlur(0.8))
    d = ImageDraw.Draw(papel)
    f = fuente("cinzel-latin-700-normal.woff", 46)
    d.text((W / 2, 52), "EL GOLFO DE NÁPOLES · AÑO 79 d. C.", font=f, fill=(240, 222, 180), anchor="mm")
    d.text((geo(40.62, 14.13)), "MAR TIRRENO", font=fuente("cinzel-latin-400-normal.woff", 38),
           fill=(120, 150, 170), anchor="mm")
    _CACHE["mapa"] = papel
    # nube de ceniza (se escala en cada fotograma)
    nube = Image.new("L", (900, 420), 0)
    ImageDraw.Draw(nube).ellipse((40, 60, 860, 360), fill=255)
    _CACHE["nube"] = nube.filter(ImageFilter.GaussianBlur(60)).rotate(-28, expand=True)
    return papel


def escena_mapa(u, t_abs):
    img = mapa_base().copy()
    d = ImageDraw.Draw(img, "RGBA")
    vx, vy = geo(*LUGARES["Vesubio"])
    # nube que crece hacia el sureste (el viento la empujó hacia Pompeya)
    crece = min(1, max(0, (u - 0.15) / 0.7))
    if crece > 0:
        nube = _CACHE["nube"]
        esc = 0.15 + 0.85 * crece
        n = nube.resize((int(nube.width * esc), int(nube.height * esc)))
        alfa = n.point(lambda p: int(p * 0.82))
        gris = Image.new("RGB", n.size, (55, 52, 50))
        img.paste(gris, (int(vx - n.width * 0.12), int(vy - n.height * 0.2)), alfa)
    # brillo del cráter
    br = 18 + 8 * math.sin(t_abs * 9)
    d.ellipse((vx - br, vy - br, vx + br, vy + br), fill=(255, 90, 20, 200))
    d.ellipse((vx - br * 2, vy - br * 2, vx + br * 2, vy + br * 2), fill=(255, 120, 40, 60))
    f = fuente("eb-garamond-latin-700-normal.woff", 40)
    orden = ["Vesubio", "Pompeya", "Herculano", "Neápolis (Nápoles)", "Miseno", "Estabia"]
    for k, nombre in enumerate(orden):
        aparece = min(1, max(0, (u - 0.04 - k * 0.07) / 0.06))
        if aparece <= 0:
            continue
        x, y = geo(*LUGARES[nombre])
        a = int(255 * aparece)
        color = (255, 80, 40, a) if nombre == "Pompeya" else (250, 240, 215, a)
        if nombre != "Vesubio":
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color, outline=(30, 20, 10, a), width=3)
        dx = {"Pompeya": 22, "Estabia": 22, "Miseno": -22, "Neápolis (Nápoles)": -22, "Herculano": -22}.get(nombre, 0)
        ancla = "lm" if dx > 0 else ("rm" if dx < 0 else "mb")
        dy = -70 if nombre == "Vesubio" else 0
        d.text((x + dx, y + dy), nombre.upper() if nombre in ("Vesubio", "Pompeya") else nombre, font=f,
               fill=color, anchor=ancla, stroke_width=3, stroke_fill=(20, 14, 10, a))
    # distancia Vesubio–Pompeya
    if u > 0.5:
        a = int(255 * min(1, (u - 0.5) / 0.08))
        px, py = geo(*LUGARES["Pompeya"])
        for s in np.linspace(0, 1, 14)[::2]:
            e = s + 1 / 14
            d.line((vx + (px - vx) * s, vy + (py - vy) * s, vx + (px - vx) * e, vy + (py - vy) * e),
                   fill=(255, 220, 120, a), width=5)
        d.text(((vx + px) / 2 + 26, (vy + py) / 2 - 10), "unos 10 km", font=f, fill=(255, 220, 120, a),
               anchor="lm", stroke_width=3, stroke_fill=(20, 14, 10, a))
    # Plinio en Miseno
    if u > 0.62:
        a = int(255 * min(1, (u - 0.62) / 0.08))
        mx, my = geo(*LUGARES["Miseno"])
        d.text((mx - 10, my + 46), "Plinio el Joven lo vio desde aquí",
               font=fuente("eb-garamond-latin-400-normal.woff", 32), fill=(250, 240, 215, a), anchor="mm",
               stroke_width=3, stroke_fill=(20, 14, 10, a))
    z = 1.0 + 0.12 * suave(u)
    w, h = W / z, H / z
    cx, cy = W / 2 + (vx - W / 2) * 0.35 * suave(u), H / 2 + (vy - H / 2) * 0.35 * suave(u)
    return img.transform((W, H), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Image.BILINEAR)


# ---------------------------------------------------------- superposiciones
def particulas(n, semilla):
    r = np.random.default_rng(semilla)
    return {"x": r.uniform(0, W, n), "y": r.uniform(0, H, n), "vx": r.uniform(-90, -20, n),
            "vy": r.uniform(50, 170, n), "s": r.uniform(1.5, 5.5, n), "a": r.uniform(90, 210, n)}


CENIZA_P = particulas(320, 1)
BRASAS_P = particulas(70, 2)


def dibujar_particulas(img, t, ceniza, brasas):
    capa = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(capa)
    if ceniza > 0:
        p = CENIZA_P
        n = int(len(p["x"]) * min(1, ceniza))
        xs = (p["x"][:n] + p["vx"][:n] * t + 14 * np.sin(t * 1.3 + p["y"][:n])) % W
        ys = (p["y"][:n] + p["vy"][:n] * t * (0.7 + 0.5 * ceniza)) % H
        for x, y, s, a in zip(xs, ys, p["s"][:n], p["a"][:n]):
            g = int(60 + s * 12)
            d.ellipse((x - s, y - s * .8, x + s, y + s * .8), fill=(g, g, g, int(a * min(1, ceniza))))
    if brasas > 0:
        p = BRASAS_P
        xs = (p["x"] - p["vx"] * 0.6 * t + 20 * np.sin(t * 2 + p["x"])) % W
        ys = (p["y"] - p["vy"] * 0.8 * t) % H
        for x, y, s in zip(xs, ys, p["s"]):
            parpadeo = 0.6 + 0.4 * math.sin(t * 11 + x)
            d.ellipse((x - s * 3, y - s * 3, x + s * 3, y + s * 3), fill=(255, 110, 20, int(40 * parpadeo * brasas)))
            d.ellipse((x - s * .7, y - s * .7, x + s * .7, y + s * .7),
                      fill=(255, 200, 90, int(230 * parpadeo * brasas)))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def tarjeta_dato(texto):
    """Recuadro '¿Sabías que...?' (RGBA)."""
    ft = fuente("cinzel-latin-700-normal.woff", 34)
    fx = fuente("eb-garamond-latin-400-normal.woff", 40)
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if fx.getlength(actual + " " + p) > 760 and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = (actual + " " + p).strip()
    lineas.append(actual)
    alto = 110 + 50 * len(lineas)
    img = Image.new("RGBA", (860, alto))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 859, alto - 1), 18, fill=(12, 10, 8, 200), outline=(212, 170, 90, 255), width=3)
    d.rectangle((0, 18, 10, alto - 18), fill=(212, 170, 90, 255))
    d.text((44, 30), "¿SABÍAS QUE…?", font=ft, fill=(232, 190, 100, 255))
    for k, l in enumerate(lineas):
        d.text((44, 86 + 50 * k), l, font=fx, fill=(245, 238, 225, 255))
    return img


def rotulo_capitulo(i, titulo):
    img = Image.new("RGBA", (1700, 170))
    d = ImageDraw.Draw(img)
    tam = 56
    while fuente("cinzel-latin-700-normal.woff", tam).getlength(titulo.upper()) > 1650:
        tam -= 2
    d.text((0, 10), f"CAPÍTULO {ROMANOS[i]}", font=fuente("cinzel-latin-400-normal.woff", 34),
           fill=(240, 196, 110, 255), stroke_width=3, stroke_fill=(0, 0, 0, 230))
    d.line((0, 62, 420, 62), fill=(222, 180, 100, 255), width=3)
    d.text((0, 76), titulo.upper(), font=fuente("cinzel-latin-700-normal.woff", tam),
           fill=(250, 244, 230, 255), stroke_width=3, stroke_fill=(0, 0, 0, 180))
    return img


def pegar(img, capa, pos, alfa):
    if alfa <= 0:
        return img
    if alfa < 1:
        capa = capa.copy()
        capa.putalpha(capa.getchannel("A").point(lambda p: int(p * alfa)))
    base = img.convert("RGBA")
    base.alpha_composite(capa, (int(pos[0]), int(pos[1])))
    return base.convert("RGB")


def entrada_salida(t, t0, t1, fundido=0.5):
    if t < t0 or t > t1:
        return 0.0
    return min(1, (t - t0) / fundido, (t1 - t) / fundido)


_VIN = None
_GRANO = None


def acabado(img, oscuro=0.0, destello=0.0):
    """Viñeta, grano de película y destellos."""
    global _VIN, _GRANO
    if _VIN is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIN = (1 - 0.42 * np.clip(r - 0.45, 0, 1) ** 1.6)[..., None].astype(np.float32)
        rg = np.random.default_rng(5)
        _GRANO = [rg.normal(0, 6, (H, W, 1)).astype(np.float32) for _ in range(6)]
        acabado.k = 0
    a = np.asarray(img).astype(np.float32) * _VIN
    acabado.k = (acabado.k + 1) % 6
    a += _GRANO[acabado.k]
    if destello > 0:
        a = a * (1 - destello) + np.array([255, 235, 200], np.float32) * destello
    if oscuro > 0:
        a *= (1 - oscuro)
    return np.clip(a, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------- render
def tramos(i, plan):
    """Lista de (nombre, t0, t1, accion) en segundos absolutos para el capítulo i."""
    c, p = CAPITULOS[i], plan[i]
    out = []
    for nombre, a, b in c["imagenes"]:
        t0, t1 = p["inicio"] + a * p["dur"], p["inicio"] + b * p["dur"]
        acc = any(x <= a + 1e-6 and b <= y + 1e-6 for x, y in c["accion"])
        out.append((nombre, t0, t1, acc))
    return out


def fotograma_capitulo(i, t, plan, extras):
    p = plan[i]
    lista = tramos(i, plan)
    k = next(j for j, tr in enumerate(lista) if t < tr[2] or j == len(lista) - 1)
    nombre, t0, t1, acc = lista[k]

    def dibujar(j, tt):
        nm, a0, a1, ac = lista[j]
        u = min(1, max(0, (tt - a0) / (a1 - a0)))
        golpe = math.exp(-(tt - a0) / 0.35) if ac else 0
        if nm == "mapa":
            return escena_mapa(u, tt)
        return ken_burns(imagen(nm), u, hash((i, j)) % 10000, ac, tt, golpe)

    img = dibujar(k, t)
    destello = 0.0
    # transición: fundido encadenado (o corte con destello en escenas de acción)
    if k > 0 and t - t0 < 0.8:
        if acc or lista[k - 1][3]:
            destello = 0.85 * math.exp(-(t - t0) / 0.12)
        else:
            img = Image.blend(dibujar(k - 1, t), img, (t - t0) / 0.8)
    ceniza = CENIZA[i] * (0.4 + 0.6 * (t - p["inicio"]) / p["dur"]) if CENIZA[i] else 0
    brasas = 0.0
    if acc:
        ceniza = max(ceniza, 1.0)
        brasas = 1.0 if nombre in ("t03", "t04") else 0.5
    if ceniza or brasas:
        img = dibujar_particulas(img, t, ceniza, brasas)
    # textos
    img = pegar(img, extras["rotulo"], (110, H - 330), entrada_salida(t, p["inicio"] + 0.5, p["inicio"] + 5.0, 0.6))
    for frac, tarjeta in extras["datos"]:
        ta = p["inicio"] + frac * p["dur"]
        al = entrada_salida(t, ta, ta + 8.5, 0.5)
        if al:
            img = pegar(img, tarjeta, (W - tarjeta.width - 90 + 40 * (1 - al), 90), al)
    oscuro = max(0, 1 - (t - p["inicio"]) / 0.5, 1 - (p["inicio"] + p["dur"] - t) / 0.5)
    if i == 8:  # el último capítulo no se funde a negro al final (lo hace el cierre)
        oscuro = max(0, 1 - (t - p["inicio"]) / 0.5)
    return acabado(img, max(0, oscuro), destello)


def fotograma_intro(t, titulo_img):
    u = t / INTRO
    img = ken_burns(imagen("t03"), u, 7, True, t, math.exp(-max(0, t - 1.0) / 0.4) if t > 1.0 else 0)
    img = dibujar_particulas(img, t, 0.8, 1.0)
    img = pegar(img, titulo_img, (0, 0), min(1, max(0, (t - 1.0) / 0.4)) * min(1, (INTRO - t) / 0.5))
    oscuro = max(0, 1 - t / 0.8) * 0.9 + 0.35 * min(1, t)
    destello = 0.9 * math.exp(-(t - 1.0) / 0.15) if t >= 1.0 else 0
    return acabado(img, min(0.95, oscuro if t < 0.8 else 0.35), destello)


def fotograma_cierre(t, total, plan, cierre_img):
    t0 = plan[8]["inicio"] + plan[8]["dur"]
    u = (t - t0) / (total - t0)
    img = ken_burns(imagen("t16"), 1.0, hash((8, 3)) % 10000, False, t, 0)
    img = pegar(img, cierre_img, (0, 0), min(1, u * 3))
    return acabado(img, min(1, u * 1.1) * 0.6 + max(0, u - 0.7) / 0.3 * 0.4)


def portada():
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    d.text((W / 2, H / 2 - 40), "POMPEYA", font=fuente("cinzel-decorative-latin-700-normal.woff", 190),
           fill=(250, 236, 205, 255), anchor="mm", stroke_width=5, stroke_fill=(30, 10, 0, 220))
    d.text((W / 2, H / 2 + 105), "LA CIUDAD QUE DESAPARECIÓ EN UN SOLO DÍA",
           font=fuente("cinzel-latin-700-normal.woff", 52), fill=(235, 180, 90, 255), anchor="mm",
           stroke_width=3, stroke_fill=(0, 0, 0, 220))
    return img


def cierre():
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    d.text((W / 2, H / 2 - 20), "CURIOSIDADES DEL MUNDO", font=fuente("cinzel-latin-700-normal.woff", 84),
           fill=(250, 236, 205, 255), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 220))
    d.text((W / 2, H / 2 + 70), "Suscríbete para más historias", font=fuente("eb-garamond-latin-400-normal.woff", 48),
           fill=(235, 190, 110, 255), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 200))
    return img


def render_parte(args):
    nombre, t0, t1, plan, total, guion_caps = args
    destino = SALIDA / "partes" / f"{nombre}.mp4"
    if destino.exists():
        return str(destino)
    tmp = destino.with_suffix(".tmp.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    if nombre.startswith("c"):
        i = int(nombre[1:])
        extras = {"rotulo": rotulo_capitulo(i, guion_caps[i]["titulo"]),
                  "datos": [(f, tarjeta_dato(tx)) for f, tx in CAPITULOS[i]["datos"]]}
    elif nombre == "intro":
        extra = portada()
    else:
        extra = cierre()
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    for n in range(n0, n1):
        t = n / FPS
        if nombre.startswith("c"):
            fr = fotograma_capitulo(i, t, plan, extras)
        elif nombre == "intro":
            fr = fotograma_intro(t, extra)
        else:
            fr = fotograma_cierre(t, total, plan, extra)
        ff.stdin.write(fr.tobytes())
        if (n - n0) % (FPS * 10) == 0:
            print(f"{nombre}: {(n - n0) / FPS:.0f}/{(n1 - n0) / FPS:.0f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    tmp.rename(destino)
    return str(destino)


# ------------------------------------------------------------------ audio
def cargar_wav(ruta):
    import soundfile as sf
    a, sr = sf.read(str(ruta), dtype="float32", always_2d=True)
    return a if a.shape[1] == 2 else np.repeat(a, 2, 1)


def retumbo(dur, fuerza=1.0):
    n = S.seg(dur)
    t = np.arange(n) / S.SR
    x = S.lp(S.ruido(n), 90, 4) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t) ** 2) * 3
    return S.estereo(S.normal(x, 0.7) * fuerza)


def mezclar(plan, total):
    n = S.seg(total + 1)
    voz, mus, fx = (np.zeros((n, 2), np.float32) for _ in range(3))

    def poner(pista, x, t, g=1.0):
        k = S.seg(t)
        m = min(len(x), n - k)
        if m > 0:
            pista[k:k + m] += x[:m] * g

    # portada: golpe de tráiler y retumbo
    poner(fx, S.impacto(), 1.0, 0.9)
    poner(fx, retumbo(INTRO + 2), 0, 0.5)
    poner(fx, S.fuego(INTRO), 0, 0.25)
    poner(mus, S.musica("tension", INTRO + 1.5), 0, 0.8)
    for i, p in enumerate(plan):
        poner(voz, cargar_wav(SALIDA / "voz" / f"cap{i + 1}.wav"), p["voz"])
        poner(mus, S.musica(CAPITULOS[i]["musica"], p["dur"] + 2.5), p["inicio"] - 0.5, 1.0)
        poner(fx, S.whoosh(1.4), p["inicio"] - 0.3, 0.35)
        poner(fx, S.timbal(55.0) if hasattr(S, "timbal") else S.impacto(), p["inicio"] + 0.5, 0.5)
        for nombre, t0, t1, acc in tramos(i, plan):
            if acc:
                poner(fx, S.impacto(), t0, 0.55)
                poner(fx, S.whoosh(1.0), t0 - 0.5, 0.4)
                poner(fx, retumbo(t1 - t0), t0, 0.7)
                poner(fx, S.fuego(t1 - t0), t0, 0.35)
                poner(fx, S.viento(t1 - t0, 1.2), t0, 0.5)
            if nombre == "mapa":
                poner(fx, retumbo(t1 - t0, 0.6), t0, 0.5)
        if CENIZA[i] and i in (4,):
            poner(fx, S.viento(p["dur"], 0.8), p["inicio"], 0.5)
        if i == 5:
            poner(fx, S.viento(p["dur"], 0.6), p["inicio"], 0.35)
    t_cierre = plan[8]["inicio"] + plan[8]["dur"]
    poner(fx, S.impacto(), t_cierre - 0.2, 0.5)
    poner(mus, S.musica("majestuoso", total - t_cierre + 1), t_cierre - 0.5, 1.0)
    # la música baja cuando habla el narrador
    env = np.abs(voz[:, 0])
    ventana = S.seg(0.3)
    env = np.convolve(env, np.ones(ventana) / ventana, mode="same")
    habla = np.clip(env / 0.02, 0, 1)
    habla = np.convolve(habla, np.ones(S.seg(0.8)) / S.seg(0.8), mode="same")
    ganancia = (0.55 - 0.33 * habla)[:, None]
    voz = voz / max(1e-6, np.abs(voz).max()) * 0.92
    total_audio = voz + mus * ganancia + fx * (0.75 - 0.3 * habla)[:, None]
    total_audio = np.tanh(total_audio * 1.1) / np.tanh(1.1)
    import soundfile as sf
    sf.write(str(SALIDA / "audio.wav"), total_audio[:S.seg(total)], S.SR)


# ------------------------------------------------------------- subtítulos
def srt(plan, caps):
    def ts(s):
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"

    lineas, k = [], 1
    for i, c in enumerate(caps):
        frases = [f for f in re.split(r"(?<=[.?!:…])\s+", c["texto"]) if f]
        pesos = np.array([len(f) + 12 for f in frases], float)
        t = plan[i]["voz"]
        for f, pz in zip(frases, pesos):
            d = plan[i]["dur_voz"] * pz / pesos.sum()
            lineas += [str(k), f"{ts(t)} --> {ts(t + d - 0.05)}", f, ""]
            t += d
            k += 1
    (SALIDA / "pompeya.srt").write_text("\n".join(lineas), encoding="utf-8")
    cap = ["00:00 Introducción"] + [f"{int(p['inicio'] // 60):02d}:{int(p['inicio'] % 60):02d} {c['titulo']}"
                                    for p, c in zip(plan, caps)]
    (SALIDA / "capitulos.txt").write_text("\n".join(cap) + "\n", encoding="utf-8")


def main():
    global SALIDA
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--prueba", type=int, help="renderiza solo ese capítulo (0-8) para revisar")
    a = ap.parse_args()
    SALIDA = Path(a.salida).resolve()
    (SALIDA / "partes").mkdir(parents=True, exist_ok=True)
    preparar_voz(SALIDA)
    plan, total = linea_de_tiempo(SALIDA)
    _, caps = leer_guion()
    print(f"Duración total: {total / 60:.2f} min", flush=True)
    partes = [("intro", 0, INTRO)] + [(f"c{i}", p["inicio"], p["inicio"] + p["dur"]) for i, p in enumerate(plan)]
    partes.append(("cierre", plan[8]["inicio"] + plan[8]["dur"], total))
    if a.prueba is not None:
        partes = [partes[a.prueba + 1]]
    trabajos = [(n, t0, t1, plan, total, caps) for n, t0, t1 in partes]
    trabajos.sort(key=lambda x: -(x[2] - x[1]))  # las más largas primero
    with Pool(a.procesos, initializer=_iniciar, initargs=(SALIDA,)) as pool:
        pool.map(render_parte, trabajos, chunksize=1)
    if a.prueba is not None:
        return
    srt(plan, caps)
    mezclar(plan, total)
    lista = SALIDA / "partes" / "lista.txt"
    lista.write_text("".join(f"file '{n}.mp4'\n" for n, _, _ in partes))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-i", str(SALIDA / "audio.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(SALIDA / "Pompeya_documental.mp4")], check=True)
    print("Listo:", SALIDA / "Pompeya_documental.mp4")


def _iniciar(salida):
    global SALIDA
    SALIDA = salida


if __name__ == "__main__":
    main()
