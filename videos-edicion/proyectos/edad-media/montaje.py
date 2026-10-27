"""Paso 2: monta el documental de la Edad Media (imágenes, escenas propias, efectos, música, voz).

Uso: python3 montaje.py [--procesos 4] [--prueba PARTE]
Necesita salida/imagenes/*.png (recortar.py) y salida/voz/cap0..cap11.mp3 (ElevenLabs).
Crea salida/EdadMedia_documental.mp4, salida/edad_media.srt y salida/capitulos.txt.
"""
import argparse
import importlib.util
import math
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import sonido_medieval as SM
from sonido import SR  # noqa: F401  (sonido_medieval ya añadió ../napoleon al path)
import sonido as S

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida"
# utilidades compartidas con el documental de Pompeya (fuentes, subtítulos, voz)
_spec = importlib.util.spec_from_file_location("pompeya_montaje", AQUI.parent / "pompeya" / "montaje.py")
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

W, H, FPS = 1920, 1080, 30
VELOCIDAD_VOZ = 1.1   # algo más de ritmo que la locución original
INTRO = 6.0           # portada
CIERRE = 6.0
PAUSA = 1.0
ROMANOS = "I II III IV V VI VII VIII IX X".split()

# Escenas de cada parte: (imagen, peso, opciones). El peso reparte el tiempo de la parte.
#   a: acción (temblor, chispas, cortes con destello)   fuego: brasas y humo
#   sfx: sonidos durante la escena   combate: ráfaga de cortes rápidos entre varias imágenes
#   "duelo" y "linea" son escenas propias dibujadas por código
PARTES = [
    {"musica": "epico", "escenas": [
        ("f1", 1, {"sfx": ["viento"]}), ("1_19", 1, {}), ("2_02", 1, {"sfx": ["multitud"]}),
        ("1_03", 0.8, {"sfx": ["caballos"]}),
        ("combate", 1.4, {"imagenes": ["f3", "4_08", "1_09", "2_18"]}),
        ("2_12", 0.8, {"a": 1, "fuego": 1, "sfx": ["asedio", "fuego"]}), ("1_16", 1, {"sfx": ["viento"]})]},
    {"musica": "majestuoso", "datos": [(0.2, "Rómulo Augústulo, el último emperador romano de Occidente, "
                                              "fue depuesto en el año 476.")], "escenas": [
        ("linea", 1.6, {"foco": "inicio"}), ("1_14", 1, {"sfx": ["viento"]}),
        ("2_09", 1, {"a": 1, "sfx": ["tambores", "ejercito"]}), ("4_19", 1, {"sfx": ["viento"]}),
        ("2_07", 1, {}), ("5_10", 1, {}), ("4_12", 1, {"sfx": ["viento"]}), ("3_14", 1, {}), ("1_08", 1, {})]},
    {"musica": "romantico", "datos": [(0.33, "Muchos campesinos dejaban una parte de sus tierras sin cultivar "
                                             "cada año para que el suelo recuperara su fertilidad.")], "escenas": [
        ("1_05", 1, {}), ("3_04", 1, {}), ("5_11", 1, {}), ("2_05", 1, {}), ("4_05", 1, {}),
        ("5_14", 1, {"sfx": ["viento"]}), ("1_18", 1, {}), ("f4", 1, {"sfx": ["fuego_bajo"]}),
        ("2_13", 1, {"sfx": ["fuego_bajo"]}), ("5_04", 1, {"sfx": ["fuego_bajo"]}), ("2_16", 1, {}),
        ("3_10", 1, {"sfx": ["multitud"]}), ("1_06", 1, {"sfx": ["multitud"]})]},
    {"musica": "majestuoso", "datos": [(0.28, "Los primeros castillos de «mota y patio» se levantaban con tierra "
                                              "y madera en relativamente poco tiempo.")], "escenas": [
        ("1_01", 1, {"sfx": ["viento"]}), ("2_01", 1, {}), ("4_01", 1, {}), ("5_07", 1, {}), ("3_01", 1, {}),
        ("4_18", 1, {}), ("2_11", 1, {}), ("2_06", 1, {}), ("4_04", 1, {}), ("1_07", 1, {}), ("4_02", 1, {}),
        ("4_16", 1, {"sfx": ["viento"]}), ("1_20", 1, {"sfx": ["cuerno"]})]},
    {"musica": "epico", "datos": [(0.62, "Una armadura de placas completa pesaba entre 15 y 25 kilos, "
                                         "repartidos por todo el cuerpo.")], "escenas": [
        ("1_17", 1, {"sfx": ["cuerno"]}), ("2_03", 0.9, {"sfx": ["caballos"]}), ("5_03", 0.8, {}),
        ("2_14", 0.8, {}), ("4_03", 0.8, {"sfx": ["tambores"]}), ("3_13", 0.8, {"sfx": ["tambores", "ejercito"]}),
        ("duelo", 1.4, {}),
        ("combate", 2.2, {"imagenes": ["f3", "4_08", "1_09", "2_18", "5_06", "4_13"]}),
        ("3_07", 0.9, {"a": 1, "fuego": 1, "sfx": ["asedio", "flechas"]}),
        ("4_15", 0.9, {"a": 1, "fuego": 1, "sfx": ["asedio", "fuego"]}), ("3_05", 0.8, {"sfx": ["caballos"]}),
        ("5_15", 0.8, {"sfx": ["multitud"]}), ("5_18", 0.9, {"sfx": ["viento"]}), ("1_13", 0.9, {})]},
    {"musica": "misterio", "datos": [(0.4, "Copiar a mano un libro grande, como una Biblia completa, "
                                           "podía llevar meses o incluso años.")], "escenas": [
        ("1_12", 1, {"sfx": ["campana"]}), ("2_15", 1, {}), ("5_05", 1, {}), ("1_04", 1, {}), ("3_03", 1, {}),
        ("4_07", 1, {}), ("2_19", 1, {}), ("3_12", 1, {}), ("3_08", 1, {"sfx": ["multitud"]}),
        ("5_12", 1, {}), ("5_17", 1, {"sfx": ["campana"]})]},
    {"musica": "romantico", "datos": [(0.55, "Las grandes ferias de Champaña, en Francia, reunían a mercaderes "
                                             "llegados de toda Europa.")], "escenas": [
        ("f2", 1, {"sfx": ["multitud"]}), ("1_02", 1, {"sfx": ["multitud"]}), ("3_02", 1, {"sfx": ["multitud"]}),
        ("4_06", 1, {"sfx": ["multitud"]}), ("1_11", 1, {"sfx": ["yunque"]}), ("2_08", 1, {"sfx": ["yunque"]}),
        ("5_08", 1, {"sfx": ["yunque"]}), ("4_17", 1, {"sfx": ["yunque"]}), ("5_02", 1, {"sfx": ["multitud"]}),
        ("1_15", 1, {"sfx": ["viento"]}), ("4_14", 1, {}), ("2_20", 1, {"sfx": ["multitud"]})]},
    {"musica": "frio", "tono": "peste", "datos": [(0.3, "Los famosos médicos con máscara de pico son del siglo XVII; "
                                                        "no existían durante la Peste Negra.")], "escenas": [
        ("1_10", 1, {"sfx": ["campana_doble"]}), ("5_09", 1, {"sfx": ["latido"]}), ("1_13", 1, {}),
        ("4_20", 1, {"sfx": ["latido"]}), ("3_15", 1, {}), ("4_11", 1, {}), ("1_08", 1, {"sfx": ["viento"]}),
        ("5_12", 1, {}), ("2_19", 1, {}), ("2_17", 1, {"sfx": ["viento"]})]},
    {"musica": "romantico", "escenas": [
        ("2_10", 1, {}), ("5_16", 1, {}), ("5_13", 1, {"sfx": ["fuego_bajo"]}), ("3_09", 1, {"sfx": ["fuego_bajo"]}),
        ("4_10", 1, {}), ("5_04", 1, {"sfx": ["fuego_bajo"]}), ("1_06", 1, {"sfx": ["multitud"]}),
        ("2_05", 1, {})]},
    {"musica": "majestuoso", "datos": [(0.3, "La Universidad de Bolonia, fundada hacia 1088, se considera la más "
                                             "antigua de Europa que sigue funcionando.")], "escenas": [
        ("5_20", 1, {}), ("2_04", 1, {}), ("4_09", 1, {"sfx": ["campana"]}), ("3_06", 1, {}), ("f5", 1, {}),
        ("3_14", 1, {}), ("3_12", 1, {}), ("1_15", 1, {})]},
    {"musica": "misterio", "datos": [(0.32, "La Biblia de Gutenberg, uno de los primeros grandes libros impresos "
                                            "en Europa, se terminó hacia 1455.")], "escenas": [
        ("linea", 1.6, {"foco": "final"}), ("3_03", 1, {}), ("4_14", 1, {}), ("1_15", 1, {"sfx": ["viento"]}),
        ("5_18", 1, {}), ("3_16", 1, {"sfx": ["viento"]}), ("5_19", 1, {})]},
    {"musica": "majestuoso", "escenas": [
        ("4_06", 1, {"sfx": ["campana", "multitud"]}), ("1_19", 1, {"sfx": ["multitud"]}), ("5_11", 1, {}),
        ("3_11", 1, {"sfx": ["yunque"]}), ("5_10", 1, {}), ("5_20", 1, {}), ("1_17", 1, {"sfx": ["viento"]}),
        ("5_01", 1, {}), ("1_20", 1, {"sfx": ["cuerno"]})]},
]


# ---------------------------------------------------------------- guion y voz
def leer_guion():
    titulo, caps = None, []
    for linea in (AQUI / "guion.txt").read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            caps.append({"titulo": linea[3:], "texto": ""})
        elif linea.strip() and caps:
            caps[-1]["texto"] = (caps[-1]["texto"] + " " + linea.strip()).strip()
        elif linea.strip():
            titulo = linea.strip()
    return titulo, caps


def preparar_voz():
    for i in range(len(PARTES)):
        wav = SALIDA / "voz" / f"cap{i}.wav"
        if not wav.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SALIDA / "voz" / f"cap{i}.mp3"),
                            "-af", f"atempo={VELOCIDAD_VOZ}", "-ar", "44100", "-ac", "2", str(wav)], check=True)


def linea_de_tiempo():
    t, plan = INTRO, []
    for i in range(len(PARTES)):
        d = P.duracion(SALIDA / "voz" / f"cap{i}.wav")
        plan.append({"inicio": t, "voz": t + 0.6, "dur": d + 0.6 + PAUSA, "dur_voz": d})
        t += d + 0.6 + PAUSA
    return plan, t + CIERRE


def tramos(i, plan):
    """(nombre, t0, t1, opciones) de cada escena de la parte i, en segundos absolutos."""
    p, esc = plan[i], PARTES[i]["escenas"]
    total = sum(e[1] for e in esc)
    t, out = p["inicio"], []
    for nombre, peso, op in esc:
        d = p["dur"] * peso / total
        out.append((nombre, t, t + d, op))
        t += d
    return out


# --------------------------------------------------------------------- imagen
_CACHE = {}


def imagen(nombre):
    if nombre not in _CACHE:
        _CACHE[nombre] = Image.open(SALIDA / "imagenes" / f"{nombre}.png").convert("RGB")
    return _CACHE[nombre]


def suave(u):
    u = min(1, max(0, u))
    return u * u * (3 - 2 * u)


def ken_burns(img, u, semilla, accion=False, t_abs=0.0, golpe=0.0):
    sw, sh = img.size
    r = np.random.default_rng(semilla)
    z0, z1 = (1.04, 1.18) if r.random() < .5 else (1.18, 1.04)
    if accion:
        z0, z1 = 1.12, 1.3
    z = z0 + (z1 - z0) * suave(u) + 0.12 * golpe
    w, h = sw / z, sh / z
    ax, bx, ay, by = r.uniform(0, 1, 4)
    x = (ax + (bx - ax) * suave(u)) * (sw - w)
    y = (ay + (by - ay) * suave(u)) * (sh - h)
    if accion:
        a = 6 + 26 * golpe
        x += a * (math.sin(t_abs * 47.1) + 0.6 * math.sin(t_abs * 83.3 + 1.3))
        y += a * (math.sin(t_abs * 53.7 + 2.1) + 0.6 * math.sin(t_abs * 91.9))
    x, y = min(max(x, 0), sw - w), min(max(y, 0), sh - h)
    return img.transform((W, H), Image.EXTENT, (x, y, x + w, y + h), Image.BICUBIC)


# ------------------------------------------------- escena propia: línea de tiempo
RANGOS = {"inicio": (420, 1530), "final": (1280, 1520)}
PERIODOS = [(476, 1000, "ALTA EDAD MEDIA", (120, 86, 52)), (1000, 1300, "PLENA EDAD MEDIA", (150, 112, 60)),
            (1300, 1492, "BAJA EDAD MEDIA", (110, 60, 46))]
HITOS = {"inicio": [(476, "476 · Cae el Imperio romano de Occidente")],
         "final": [(1347, "1347 · Peste Negra"), (1450, "~1450 · Imprenta de Gutenberg"),
                   (1453, "1453 · Caída de Constantinopla"), (1492, "1492 · Viajes por el Atlántico")]}


def xa(anio, foco="inicio"):
    a0, a1 = RANGOS[foco]
    return 140 + (min(max(anio, a0), a1) - a0) / (a1 - a0) * (W - 280)


def escena_linea(u, foco):
    clave = ("linea_fondo",)
    if clave not in _CACHE:
        rng = np.random.default_rng(3)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
        base = np.stack([46 - 30 * r, 34 - 22 * r, 24 - 16 * r], 2) + rng.normal(0, 4, (H, W, 1))
        _CACHE[clave] = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    img = _CACHE[clave].copy()
    d = ImageDraw.Draw(img, "RGBA")
    ft = P.fuente("cinzel-latin-700-normal.woff", 54)
    fp = P.fuente("cinzel-latin-700-normal.woff", 30)
    fx = P.fuente("eb-garamond-latin-700-normal.woff", 36)
    titulo = "MIL AÑOS DE HISTORIA" if foco == "inicio" else "EL FINAL DE UNA ÉPOCA"
    d.text((W / 2, 150), titulo, font=ft, fill=(236, 206, 140, int(255 * min(1, u * 5))), anchor="mm")
    y = 560
    a_ini, a_fin = RANGOS[foco]
    avance = suave(u / 0.55) if foco == "inicio" else 1.0
    fin = a_ini + (a_fin - a_ini) * avance
    for p0, p1, nombre, color in PERIODOS:
        if p0 >= fin or p1 <= a_ini:
            continue
        x0, x1 = xa(p0, foco), xa(min(p1, fin), foco)
        d.rectangle((x0, y - 34, x1, y + 34), fill=color + (235,))
        if x1 - x0 > 330:
            d.text(((x0 + x1) / 2, y), nombre, font=fp, fill=(250, 238, 210, 255), anchor="mm")
    d.line((xa(a_ini, foco), y + 40, xa(a_fin, foco), y + 40), fill=(220, 190, 130, 255), width=3)
    paso = 100 if foco == "inicio" else 25
    for anio in range((a_ini // paso + 1) * paso, a_fin + 1, paso):
        d.line((xa(anio, foco), y + 34, xa(anio, foco), y + 50), fill=(220, 190, 130, 255), width=3)
        d.text((xa(anio, foco), y + 76), str(anio), font=P.fuente("eb-garamond-latin-400-normal.woff", 28),
               fill=(220, 190, 130, 255), anchor="mm")
    for k, (anio, texto) in enumerate(HITOS[foco]):
        aparece = suave((u - 0.12 - k * 0.13) / 0.08) if foco == "final" else suave((u - 0.05) / 0.1)
        if aparece <= 0 or anio > fin:
            continue
        a = int(255 * aparece)
        x = xa(anio, foco)
        arriba = k % 2 == 0
        ytxt = y - 130 - (k // 2) * 75 if arriba else y + 160 + (k // 2) * 70
        d.line((x, y - 34 if arriba else y + 50, x, ytxt + (28 if arriba else -28)), fill=(255, 210, 120, a), width=3)
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(255, 90, 40, a), outline=(30, 10, 0, a), width=3)
        ancho = fx.getlength(texto) / 2
        d.text((min(max(x, 120 + ancho), W - 120 - ancho), ytxt), texto, font=fx, fill=(255, 236, 200, a),
               anchor="mm", stroke_width=3, stroke_fill=(20, 10, 0, a))
    z = 1.0 + 0.06 * suave(u)
    w, h = W / z, H / z
    return img.transform((W, H), Image.EXTENT, ((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2), Image.BICUBIC)


# --------------------------------------------- escena propia: duelo de caballeros
def cielo_duelo():
    if "duelo" in _CACHE:
        return _CACHE["duelo"]
    yy = np.linspace(0, 1, H)[:, None, None]
    cielo = (np.array([30, 8, 6]) * (1 - yy) + np.array([235, 110, 30]) * yy ** 1.6).astype(np.float32)
    cielo = np.repeat(cielo, W, 1)
    img = Image.fromarray(np.clip(cielo, 0, 255).astype(np.uint8))
    resplandor = Image.new("L", (W, H), 0)
    ImageDraw.Draw(resplandor).ellipse((1050, 330, 1850, 950), fill=170)
    img.paste(Image.new("RGB", (W, H), (255, 140, 40)), (0, 0), resplandor.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    # castillo en llamas al fondo
    base = 760
    torres = [(1180, 230, 70), (1290, 300, 90), (1420, 250, 70), (1530, 330, 100), (1660, 240, 70)]
    d.rectangle((1150, base - 150, 1720, base), fill=(28, 12, 10))
    for x, alto, ancho in torres:
        d.rectangle((x, base - alto, x + ancho, base), fill=(28, 12, 10))
        for k in range(0, ancho, 22):
            d.rectangle((x + k, base - alto - 18, x + k + 12, base - alto), fill=(28, 12, 10))
        for k in range(2):  # ventanas encendidas
            d.rectangle((x + ancho / 2 - 6, base - alto + 50 + k * 70, x + ancho / 2 + 6, base - alto + 80 + k * 70),
                        fill=(255, 170, 60))
    # colinas y suelo
    d = ImageDraw.Draw(img)
    pts = [(0, 830)] + [(x, 800 + 30 * math.sin(x / 180) + 15 * math.sin(x / 61)) for x in range(0, W + 40, 40)] + [(W, H), (0, H)]
    d.polygon(pts, fill=(14, 6, 4))
    _CACHE["duelo"] = img
    return img


def caballero(d, x, y, mira, brazo, escudo_alto, t, color=(8, 4, 3), borde=None):
    """Caballero en silueta (yelmo cerrado, capa, escudo y espada). `brazo`: ángulo de la espada en radianes
    (0 = horizontal hacia delante). Con `borde` se dibuja desplazado para hacer el contorno iluminado."""
    s = mira  # 1 mira a la derecha, -1 a la izquierda
    if borde:
        x, y, color = x + borde[0], y + borde[1], borde[2]
    ondea = 18 * math.sin(t * 3 + x)
    # capa por detrás
    d.polygon([(x - 40 * s, y - 400), (x - 10 * s, y - 400), (x - 70 * s + ondea, y - 120),
               (x - 150 * s + ondea, y - 100), (x - 110 * s, y - 260)], fill=color)
    # piernas en guardia
    d.polygon([(x - 40, y - 240), (x + 10, y - 240), (x - 60 * s + 14, y - 8), (x - 60 * s - 26, y - 8)], fill=color)
    d.polygon([(x - 10, y - 240), (x + 40, y - 240), (x + 75 * s + 22, y - 8), (x + 75 * s - 20, y - 8)], fill=color)
    d.ellipse((x - 60 * s - 40, y - 24, x - 60 * s + 30, y + 4), fill=color)
    d.ellipse((x + 75 * s - 34, y - 24, x + 75 * s + 36, y + 4), fill=color)
    # torso con sobreveste
    d.polygon([(x - 62, y - 410), (x + 62, y - 410), (x + 44, y - 280), (x + 70, y - 200), (x - 70, y - 200),
               (x - 44, y - 280)], fill=color)
    # yelmo cerrado con cimera
    d.rounded_rectangle((x - 36, y - 505, x + 36, y - 410), 12, fill=color)
    d.polygon([(x - 36, y - 498), (x, y - 528), (x + 36, y - 498)], fill=color)
    d.polygon([(x, y - 520), (x - 40 * s, y - 560), (x - 110 * s + ondea * 0.6, y - 540),
               (x - 60 * s, y - 512)], fill=color)
    if not borde:  # rendija del yelmo iluminada por el fuego
        d.rectangle((x + 4 * s - 26, y - 468, x + 4 * s + 26, y - 462), fill=(255, 150, 60))
    # escudo en el brazo delantero
    ex, ey = x + 62 * s, y - 330 - escudo_alto
    d.polygon([(ex - 46, ey - 92), (ex + 46, ey - 92), (ex + 42, ey + 30), (ex, ey + 100), (ex - 42, ey + 30)],
              fill=color)
    # brazo y espada
    hx, hy = x - 26 * s, y - 395
    cx, cy = hx + s * 105 * math.cos(brazo), hy - 105 * math.sin(brazo)
    d.line((hx, hy, cx, cy), fill=color, width=30)
    d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=color)
    punta = (cx + s * 250 * math.cos(brazo), cy - 250 * math.sin(brazo))
    d.line((cx, cy, *punta), fill=color, width=11)
    gx, gy = math.sin(brazo) * 30, s * math.cos(brazo) * 30
    d.line((cx - gx, cy - gy, cx + gx, cy + gy), fill=color, width=10)
    return punta


GOLPE = 1.25  # segundos por intercambio de golpes en el duelo


def estado_duelo(t):
    """Ángulos de las espadas y si hay choque en este instante."""
    ciclo, fase = divmod(t, GOLPE)
    ataca = int(ciclo) % 2  # 0: ataca el de la izquierda, 1: el de la derecha
    golpe = min(1, fase / 0.45)
    alto, bajo = 2.0, -0.35
    atk = alto + (bajo - alto) * suave(golpe) if fase < 0.45 else bajo + (alto - bajo) * suave((fase - 0.45) / 0.8)
    defensa = 0.9 + 0.25 * math.sin(fase * 4)
    return (atk, defensa) if ataca == 0 else (defensa, atk), ataca, fase


def escena_duelo(u, t_rel, t_abs):
    img = cielo_duelo().copy()
    d = ImageDraw.Draw(img)
    (aa, ab), ataca, fase = estado_duelo(t_rel)
    avance = 25 * math.sin(t_rel * 1.3)
    xa_, xb_ = 790 + avance + (35 if ataca == 0 and fase < 0.45 else 0), 1130 + avance - (35 if ataca == 1 and fase < 0.45 else 0)
    for borde in ((6, -3, (255, 120, 40)), None):  # primero el contorno de luz, luego la silueta
        caballero(d, xa_, 905, 1, aa, 24 if ataca == 1 else 0, t_rel, borde=borde)
        caballero(d, xb_, 905, -1, ab, 24 if ataca == 0 else 0, t_rel + 1.7, borde=borde)
    # niebla baja
    impacto = math.exp(-abs(fase - 0.45) / 0.05)
    if impacto > 0.05:
        cx, cy = (xa_ + xb_) / 2, 455
        capa = Image.new("RGBA", (W, H))
        dc = ImageDraw.Draw(capa)
        r = np.random.default_rng(int(t_rel / GOLPE) + 7)
        for _ in range(40):
            ang, lon = r.uniform(0, 2 * math.pi), r.uniform(40, 240) * (0.4 + 0.6 * impacto)
            ini = r.uniform(0.1, 0.5) * lon
            dc.line((cx + ini * math.cos(ang), cy + ini * math.sin(ang), cx + lon * math.cos(ang),
                     cy + lon * math.sin(ang)), fill=(255, 200 + int(r.uniform(0, 55)), 110, int(255 * impacto)),
                    width=int(r.uniform(2, 4)))
        nucleo = 22 * impacto
        dc.ellipse((cx - nucleo, cy - nucleo, cx + nucleo, cy + nucleo), fill=(255, 252, 235, int(255 * impacto)))
        brillo = capa.filter(ImageFilter.GaussianBlur(6))
        img = Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), brillo), capa).convert("RGB")
    z = 1.05 + 0.08 * u + 0.05 * impacto
    w, h = W / z, H / z
    sx = 10 * impacto * math.sin(t_abs * 90)
    return img.transform((W, H), Image.EXTENT, ((W - w) / 2 + sx, (H - h) / 2, (W + w) / 2 + sx, (H + h) / 2),
                         Image.BICUBIC)


# ------------------------------------------------------------- superposiciones
def particulas(n, semilla):
    r = np.random.default_rng(semilla)
    return {"x": r.uniform(0, W, n), "y": r.uniform(0, H, n), "vx": r.uniform(-90, -20, n),
            "vy": r.uniform(50, 170, n), "s": r.uniform(1.5, 4.5, n)}


BRASAS = particulas(90, 2)
POLVO = particulas(60, 4)


def capas(img, t, brasas=0.0, polvo=0.0, humo=0.0):
    if not (brasas or polvo or humo):
        return img
    base = img.convert("RGBA")
    if humo:
        if "humo" not in _CACHE:
            ruido = np.random.default_rng(9).random((H // 8, W // 4))
            nube = Image.fromarray((ruido * 255).astype(np.uint8)).resize((W * 2, H), Image.BICUBIC)
            nube = nube.filter(ImageFilter.GaussianBlur(40))
            a = np.asarray(nube).astype(np.float32)
            a = np.clip((a - 110) * 2.2, 0, 255)
            capa = np.zeros((H, W * 2, 4), np.uint8)
            capa[..., :3] = 30
            capa[..., 3] = a.astype(np.uint8)
            _CACHE["humo"] = Image.fromarray(capa)
        off = int(t * 40) % W
        trozo = _CACHE["humo"].crop((off, 0, off + W, H))
        trozo.putalpha(trozo.getchannel("A").point(lambda v: int(v * 0.6 * humo)))
        base.alpha_composite(trozo)
    capa = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(capa)
    if brasas:
        p = BRASAS
        xs = (p["x"] - p["vx"] * 0.6 * t + 20 * np.sin(t * 2 + p["x"])) % W
        ys = (p["y"] - p["vy"] * 0.9 * t) % H
        for x, y, s in zip(xs, ys, p["s"]):
            parpadeo = 0.6 + 0.4 * math.sin(t * 11 + x)
            d.ellipse((x - s * 3, y - s * 3, x + s * 3, y + s * 3), fill=(255, 110, 20, int(45 * parpadeo * brasas)))
            d.ellipse((x - s * .8, y - s * .8, x + s * .8, y + s * .8), fill=(255, 205, 90, int(235 * parpadeo * brasas)))
    if polvo:
        p = POLVO
        xs = (p["x"] + 25 * t + 30 * np.sin(t * 0.5 + p["y"])) % W
        ys = (p["y"] + 10 * np.sin(t * 0.7 + p["x"])) % H
        for x, y, s in zip(xs, ys, p["s"]):
            d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 235, 200, int(70 * polvo)))
    base.alpha_composite(capa)
    return base.convert("RGB")


def tarjeta_dato(texto):
    return P.tarjeta_dato(texto)


def rotulo(i, titulo):
    if 1 <= i <= 10:
        return P.rotulo_capitulo(i - 1, titulo)
    img = Image.new("RGBA", (1700, 170))
    d = ImageDraw.Draw(img)
    d.text((0, 60), titulo.upper(), font=P.fuente("cinzel-latin-700-normal.woff", 60), fill=(250, 244, 230, 255),
           stroke_width=3, stroke_fill=(0, 0, 0, 180))
    return img


_VIN = None
_GRANO = None


def acabado(img, tono=None, oscuro=0.0, destello=0.0, k=0):
    global _VIN, _GRANO
    if _VIN is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIN = (1 - 0.25 * np.clip(r - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)
        rg = np.random.default_rng(5)
        _GRANO = [rg.normal(0, 2.5, (H, W, 1)).astype(np.float32) for _ in range(6)]
    if tono == "peste":
        img = ImageEnhance.Color(img).enhance(0.45)
    a = np.asarray(img).astype(np.float32)
    if tono == "peste":
        a = a * np.array([0.92, 0.97, 1.04], np.float32) * 0.9
    a = a * _VIN + _GRANO[k % 6]
    if destello > 0:
        a = a * (1 - destello) + np.array([255, 240, 215], np.float32) * destello
    if oscuro > 0:
        a *= (1 - oscuro)
    return np.clip(a, 0, 255).astype(np.uint8)


def fotograma(i, t, plan, extras):
    """Fotograma de la parte i en el instante t (segundos absolutos)."""
    p = plan[i]
    lista = tramos(i, plan)
    k = next(j for j, tr in enumerate(lista) if t < tr[2] or j == len(lista) - 1)

    def dibujar(j, tt):
        nombre, a0, a1, op = lista[j]
        u = min(1, max(0, (tt - a0) / (a1 - a0)))
        if nombre == "linea":
            return escena_linea(u, op["foco"]), 0.0
        if nombre == "duelo":
            return escena_duelo(u, tt - a0, tt), 0.0
        if nombre == "combate":
            imgs = op["imagenes"]
            corte = 1.6
            c = int((tt - a0) / corte)
            uc = ((tt - a0) % corte) / corte
            golpe = math.exp(-((tt - a0) % corte) / 0.25)
            return ken_burns(imagen(imgs[c % len(imgs)]), uc, 100 + c, True, tt, golpe), 0.9 * math.exp(
                -((tt - a0) % corte) / 0.09)
        accion = bool(op.get("a"))
        golpe = math.exp(-(tt - a0) / 0.35) if accion else 0.0
        return ken_burns(imagen(nombre), u, hash((i, j, nombre)) % 10000, accion, tt, golpe), 0.0

    nombre, t0, t1, op = lista[k]
    img, destello = dibujar(k, t)
    if k > 0 and t - t0 < 0.7:
        previo = lista[k - 1]
        if op.get("a") or nombre in ("combate", "duelo") or previo[3].get("a") or previo[0] == "combate":
            destello = max(destello, 0.8 * math.exp(-(t - t0) / 0.12))
        else:
            img = Image.blend(dibujar(k - 1, t)[0], img, (t - t0) / 0.7)
    combate = nombre in ("combate", "duelo") or op.get("a")
    img = capas(img, t, brasas=1.0 if (op.get("fuego") or nombre in ("combate", "duelo")) else (0.5 if combate else 0),
                polvo=0.6 if (not combate and nombre not in ("linea",) and PARTES[i].get("tono") != "peste") else 0,
                humo=1.0 if op.get("fuego") or PARTES[i].get("tono") == "peste" else 0)
    img = P.pegar(img, extras["rotulo"], (110, H - 330), P.entrada_salida(t, p["inicio"] + 0.5, p["inicio"] + 5.0, 0.6))
    for frac, tarjeta in extras["datos"]:
        ta = p["inicio"] + frac * p["dur"]
        al = P.entrada_salida(t, ta, ta + 9, 0.5)
        if al:
            img = P.pegar(img, tarjeta, (W - tarjeta.width - 90 + 40 * (1 - al), 90), al)
    oscuro = max(0, 1 - (t - p["inicio"]) / 0.5, 1 - (p["inicio"] + p["dur"] - t) / 0.5)
    if i == len(PARTES) - 1:
        oscuro = max(0, 1 - (t - p["inicio"]) / 0.5)
    return acabado(img, PARTES[i].get("tono") if t < p["inicio"] + p["dur"] * 0.85 else None, oscuro, destello,
                   int(t * FPS))


def portada():
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    d.text((W / 2, H / 2 - 50), "LA EDAD MEDIA", font=P.fuente("cinzel-decorative-latin-700-normal.woff", 170),
           fill=(250, 236, 205, 255), anchor="mm", stroke_width=5, stroke_fill=(30, 10, 0, 220))
    d.text((W / 2, H / 2 + 95), "LA VERDAD DETRÁS DE LOS CASTILLOS", font=P.fuente("cinzel-latin-700-normal.woff", 58),
           fill=(235, 180, 90, 255), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 220))
    return img


def fotograma_intro(t, titulo):
    img = ken_burns(imagen("4_16"), t / INTRO, 7, False, t, 0)
    img = capas(img, t, brasas=0.7, humo=0.5)
    img = P.pegar(img, titulo, (0, 0), suave((t - 1.2) / 0.5) * min(1, (INTRO - t) / 0.5))
    destello = 0.85 * math.exp(-(t - 1.2) / 0.15) if t >= 1.2 else 0
    return acabado(img, oscuro=max(0, 1 - t / 1.0) * 0.9, destello=destello, k=int(t * FPS))


def fotograma_cierre(t, total, plan, img_cierre):
    t0 = plan[-1]["inicio"] + plan[-1]["dur"]
    u = (t - t0) / (total - t0)
    img = ken_burns(imagen("1_20"), 1.0, 11, False, t, 0)
    img = P.pegar(img, img_cierre, (0, 0), min(1, u * 3))
    return acabado(img, oscuro=min(1, u * 1.1) * 0.6 + max(0, u - 0.7) / 0.3 * 0.4, k=int(t * FPS))


def render_parte(args):
    nombre, t0, t1, plan, total, caps = args
    destino = SALIDA / "partes" / f"{nombre}.mp4"
    if destino.exists():
        return
    tmp = destino.with_suffix(".tmp.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-b:v", "8M",
                           "-maxrate", "10M", "-bufsize", "16M", "-pix_fmt", "yuv420p", str(tmp)],
                          stdin=subprocess.PIPE)
    if nombre[1:].isdigit():
        i = int(nombre[1:])
        extras = {"rotulo": rotulo(i, caps[i]["titulo"]),
                  "datos": [(f, tarjeta_dato(tx)) for f, tx in PARTES[i].get("datos", [])]}
    elif nombre == "intro":
        extra = portada()
    else:
        extra = P.cierre()
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    for n in range(n0, n1):
        t = n / FPS
        if nombre[1:].isdigit():
            fr = fotograma(i, t, plan, extras)
        elif nombre == "intro":
            fr = fotograma_intro(t, extra)
        else:
            fr = fotograma_cierre(t, total, plan, extra)
        ff.stdin.write(fr.tobytes())
        if (n - n0) % (FPS * 15) == 0:
            print(f"{nombre}: {(n - n0) / FPS:.0f}/{(n1 - n0) / FPS:.0f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    tmp.rename(destino)


# ------------------------------------------------------------------- audio
def mezclar(plan, total):
    n = S.seg(total + 1)
    voz, mus, fx = (np.zeros((n, 2), np.float32) for _ in range(3))

    def poner(pista, x, t, g=1.0):
        k = S.seg(max(0, t))
        m = min(len(x), n - k)
        if m > 0:
            pista[k:k + m] += x[:m] * g

    poner(fx, SM.cuerno(4.0, 98.0), 0.2, 0.7)
    poner(fx, S.impacto(), 1.2, 0.9)
    poner(fx, S.fuego(INTRO), 0, 0.25)
    poner(mus, S.musica("epico", INTRO + 1.5), 0, 0.8)
    for i, p in enumerate(plan):
        poner(voz, P.cargar_wav(SALIDA / "voz" / f"cap{i}.wav"), p["voz"])
        poner(mus, S.musica(PARTES[i]["musica"], p["dur"] + 2.5), p["inicio"] - 0.5, 1.0)
        poner(fx, S.whoosh(1.4), p["inicio"] - 0.3, 0.3)
        if 1 <= i <= 10:
            poner(fx, S.timbal(55.0), p["inicio"] + 0.5, 0.45)
        for nombre, t0, t1, op in tramos(i, plan):
            d = t1 - t0
            for s in op.get("sfx", []):
                if s == "viento":
                    poner(fx, S.viento(d, 0.7), t0, 0.45)
                elif s == "multitud":
                    poner(fx, SM.multitud(d), t0, 0.55)
                elif s == "yunque":
                    poner(fx, SM.yunque(d), t0, 0.35)
                elif s == "caballos":
                    poner(fx, S.caballos(d), t0, 0.8)
                elif s == "tambores":
                    poner(fx, SM.tambores_guerra(d), t0, 0.55)
                elif s == "ejercito":
                    poner(fx, SM.ejercito(d), t0, 0.5)
                elif s == "fuego":
                    poner(fx, S.fuego(d), t0, 0.4)
                elif s == "fuego_bajo":
                    poner(fx, S.fuego(d, 0.5), t0, 0.25)
                elif s == "asedio":
                    poner(fx, SM.asedio(d), t0, 0.6)
                elif s == "flechas":
                    for k in range(int(d // 3)):
                        poner(fx, SM.flechas(14, 2.0), t0 + 0.5 + k * 3, 0.6)
                elif s == "latido":
                    poner(fx, S.latido(d, 52), t0, 0.5)
                elif s == "campana":
                    poner(fx, S.campana(196.0, 8.0), t0 + 0.3, 0.35)
                elif s == "campana_doble":
                    for k in range(int(d // 4)):
                        poner(fx, S.campana(147.0, 6.0), t0 + 0.3 + k * 4, 0.3)
                elif s == "cuerno":
                    poner(fx, SM.cuerno(3.5, 110.0), t0 + 0.3, 0.5)
            if op.get("a"):
                poner(fx, S.impacto(), t0, 0.5)
                poner(fx, SM.melee(d, 0.7), t0, 0.4)
            if nombre == "combate":
                poner(fx, SM.melee(d, 1.4), t0, 0.7)
                poner(fx, SM.ejercito(d, 1.0), t0, 0.6)
                poner(fx, S.caballos(d), t0, 0.7)
                poner(fx, SM.tambores_guerra(d, 110), t0, 0.5)
                for c in range(int(d / 1.6) + 1):
                    poner(fx, SM.espada(0, 1.0), t0 + c * 1.6, 0.8)
                    poner(fx, S.whoosh(0.6), t0 + c * 1.6 - 0.3, 0.3)
                poner(fx, SM.flechas(20, 2.5), t0 + d * 0.4, 0.6)
            if nombre == "duelo":
                poner(fx, S.fuego(d), t0, 0.4)
                poner(fx, SM.ejercito(d, 0.6), t0, 0.35)
                c = 0
                while c * GOLPE + 0.45 < d:
                    poner(fx, SM.tajo(), t0 + c * GOLPE + 0.25, 0.8)
                    poner(fx, SM.espada(0.0, 1.0), t0 + c * GOLPE + 0.45, 1.0)
                    c += 1
            if nombre == "linea":
                poner(fx, S.pluma(d * 0.6), t0 + 0.5, 0.25)
    t_cierre = plan[-1]["inicio"] + plan[-1]["dur"]
    poner(fx, S.impacto(), t_cierre - 0.2, 0.5)
    poner(mus, S.musica("majestuoso", total - t_cierre + 1), t_cierre - 0.5, 1.0)
    # la música y los efectos bajan mientras habla el narrador
    env = np.abs(voz[:, 0])
    ventana = S.seg(0.3)
    env = np.convolve(env, np.ones(ventana) / ventana, mode="same")
    habla = np.clip(env / 0.02, 0, 1)
    habla = np.convolve(habla, np.ones(S.seg(0.8)) / S.seg(0.8), mode="same")
    voz = voz / max(1e-6, np.abs(voz).max()) * 0.92
    mezcla = voz + mus * (0.55 - 0.33 * habla)[:, None] + fx * (0.8 - 0.35 * habla)[:, None]
    mezcla = np.tanh(mezcla * 1.1) / np.tanh(1.1)
    import soundfile as sf
    sf.write(str(SALIDA / "audio.wav"), mezcla[:S.seg(total)], S.SR)


# --------------------------------------------------------------- subtítulos
def srt(plan, caps):
    P.SALIDA = SALIDA
    # pompeya_montaje.srt busca la voz como cap{i+1}.wav: se le pasa una vista con esos nombres
    vista = SALIDA / "voz_srt"
    vista.mkdir(exist_ok=True)
    for i in range(len(caps)):
        enlace = vista / f"cap{i + 1}.wav"
        if not enlace.exists():
            enlace.symlink_to(SALIDA / "voz" / f"cap{i}.wav")
    original = P.SALIDA
    P.SALIDA = SALIDA / "_srt"
    (P.SALIDA).mkdir(exist_ok=True)
    if not (P.SALIDA / "voz").exists():
        (P.SALIDA / "voz").symlink_to(vista)
    P.srt(plan, caps)
    (P.SALIDA / "pompeya.srt").replace(SALIDA / "edad_media.srt")
    lineas = ["00:00 Introducción"] + [f"{int(p['inicio'] // 60):02d}:{int(p['inicio'] % 60):02d} {c['titulo']}"
                                       for p, c in list(zip(plan, caps))[1:]]
    (SALIDA / "capitulos.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    P.SALIDA = original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--prueba", type=int, help="renderiza solo esa parte (0-11)")
    a = ap.parse_args()
    (SALIDA / "partes").mkdir(parents=True, exist_ok=True)
    preparar_voz()
    plan, total = linea_de_tiempo()
    _, caps = leer_guion()
    print(f"Duración total: {total / 60:.2f} min", flush=True)
    partes = [("intro", 0, INTRO)] + [(f"c{i}", p["inicio"], p["inicio"] + p["dur"]) for i, p in enumerate(plan)]
    partes.append(("cierre", plan[-1]["inicio"] + plan[-1]["dur"], total))
    if a.prueba is not None:
        partes = [partes[a.prueba + 1]]
    trabajos = sorted([(n, t0, t1, plan, total, caps) for n, t0, t1 in partes], key=lambda x: -(x[2] - x[1]))
    with Pool(a.procesos) as pool:
        pool.map(render_parte, trabajos, chunksize=1)
    if a.prueba is not None:
        return
    srt(plan, caps)
    mezclar(plan, total)
    lista = SALIDA / "partes" / "lista.txt"
    lista.write_text("".join(f"file '{n}.mp4'\n" for n, _, _ in partes))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-i", str(SALIDA / "audio.wav"), "-c:v", "copy",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(SALIDA / "EdadMedia_documental.mp4")], check=True)
    print("Listo:", SALIDA / "EdadMedia_documental.mp4", flush=True)


if __name__ == "__main__":
    main()
