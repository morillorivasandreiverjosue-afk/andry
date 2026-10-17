#!/usr/bin/env python3
"""Paso 3: arma el documental en 1920x1080 (YouTube) a partir de linea.json + ilustraciones + mapas.

Uso (desde proyectos/bolivar/):
  python3 render.py                       # video completo -> ../../exportados/simon-bolivar-documental.mp4
  python3 render.py --vista 125.5         # guarda un PNG del segundo indicado (para revisar)
  python3 render.py --hasta 120           # solo los primeros 120 s (prueba rápida)
"""
import argparse
import json
import math
import random
import re
import subprocess
import sys
import wave
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fotos as FT
import ilustraciones as IL
import mapas as MP

AQUI = Path(__file__).resolve().parent
BUILD = AQUI / "build"
W, H, FPS = 1920, 1080, 24
FUNDIDO = 0.8

ORO = (215, 175, 95)
CREMA = (240, 228, 200)

LINEA = json.loads((BUILD / "linea.json").read_text(encoding="utf-8"))
ESCENAS = LINEA["escenas"]
TODAS_FRASES = [f for e in ESCENAS for f in e.get("frases", [])]
# obras de Wikimedia por escena (solo las ya descargadas por fotos.py)
FOTOS = {i: ["foto:" + t for t in v if FT.ruta_prep(t).exists()] for i, v in FT.mapa().items()}
FOTOS = {i: v for i, v in FOTOS.items() if v}


def fuente(clave, tam):
    return IL.fuente(clave, tam)


# ---------------- recursos por proceso ----------------

_img = {}
_vin = None
_grano = None


def imagen(nombre, desenfoque=0):
    clave = (nombre, desenfoque)
    if clave not in _img:
        if desenfoque:
            im = imagen(nombre).filter(ImageFilter.GaussianBlur(desenfoque))
            im = Image.fromarray((np.asarray(im, np.float32) * 0.42).astype(np.uint8))
        else:
            if nombre.startswith("foto:"):
                ruta = FT.ruta_prep(nombre[5:])
            else:
                ruta = (MP.generar(nombre) if nombre in MP.MAPAS else IL.generar(nombre))
            im = Image.open(ruta).convert("RGB")
        _img[clave] = im
    return _img[clave]


def viñeta_y_grano():
    global _vin, _grano
    if _vin is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _vin = np.clip(1.08 - 0.42 * d ** 2.2, 0.35, 1)[..., None].astype(np.float32)
        rng = np.random.default_rng(1)
        _grano = [rng.normal(0, 5.5, (H, W, 1)).astype(np.float32) for _ in range(6)]
    return _vin, _grano


def visual_de(i):
    e = ESCENAS[i]
    if e["tipo"] == "plano":
        return FOTOS[i][0] if i in FOTOS else e["visual"]
    if e["tipo"] == "portada":
        return "andes"
    for j in range(i + 1, len(ESCENAS)):
        if ESCENAS[j]["tipo"] == "plano":
            return visual_de(j)
    return "retrato"


def ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


# ---------------- planos ----------------

def ken_burns(i, t, dur, mapa):
    rng = random.Random(i * 7919)
    if mapa:
        z0, z1 = 1.0, 1.06
        c0 = c1 = (W0 / 2, H0 / 2)
    else:
        z0, z1 = (1.0, 1.13) if rng.random() < 0.6 else (1.13, 1.0)
        ang = rng.uniform(0, 2 * math.pi)
        c0 = (W0 / 2 + math.cos(ang) * 60, H0 / 2 + math.sin(ang) * 35)
        c1 = (W0 / 2 - math.cos(ang) * 60, H0 / 2 - math.sin(ang) * 35)
    u = t / max(dur, 0.1)
    u = u * 0.85 + 0.15 * ease(u)
    z = z0 + (z1 - z0) * u
    cx = c0[0] + (c1[0] - c0[0]) * u
    cy = c0[1] + (c1[1] - c0[1]) * u
    cw, ch = W0 / z, H0 / z
    cx = min(max(cx, cw / 2), W0 - cw / 2)
    cy = min(max(cy, ch / 2), H0 - ch / 2)
    return (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


W0, H0 = IL.W0, IL.H0


def titulo_partes(titulo):
    if ":" in titulo:
        a, b = titulo.split(":", 1)
        return a.strip(), b.strip()
    return "", titulo


def envolver(texto, f, ancho):
    lineas, actual = [], ""
    for pal in texto.split():
        prueba = (actual + " " + pal).strip()
        if f.getlength(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = pal
    if actual:
        lineas.append(actual)
    return lineas


# ---------------- efectos animados (lluvia, humo, chispas, polvo, luz) ----------------

EFECTOS = {
    "lluvia": {"andes_marcha", "tormenta", "andes"},
    "humo": {"batalla", "batalla_humo", "caballeria", "fortaleza", "batalla_victoria"},
    "brasas": {"campamento", "batalla", "batalla_humo"},
    "polvo": {"congreso", "dos_figuras", "libros", "vela", "boda", "retrato", "sucre", "manuela", "balanza",
              "ventana"} | {k for k in IL.DOCUMENTOS},
    "parpadeo": {"vela", "campamento", "libros", "boda"},
    "niebla": {"andes", "volcan", "amanecer", "rio", "llanos_noche", "andes_marcha", "noche"},
}
_tex = {}


def textura_efecto(tipo):
    if tipo in _tex:
        return _tex[tipo]
    rng = np.random.default_rng(hash(tipo) % 1000)
    if tipo == "lluvia":
        capa = Image.new("L", (W, H * 2), 0)
        d = ImageDraw.Draw(capa)
        for _ in range(1600):
            x, y = rng.integers(-200, W), rng.integers(0, H * 2)
            lng = rng.integers(30, 70)
            d.line((x, y, x + lng * 0.22, y + lng), fill=int(rng.integers(60, 140)), width=2)
        _tex[tipo] = capa
    elif tipo in ("humo", "niebla"):
        n = IL.ruido2d(W * 2, H, 320 if tipo == "humo" else 500, 5, 77 if tipo == "humo" else 78)
        a = np.clip((n - 0.45) * 2.4, 0, 1)
        y = np.linspace(0, 1, H)[:, None]
        if tipo == "niebla":
            a = a * np.clip((y - 0.35) / 0.4, 0, 1)
        _tex[tipo] = Image.fromarray((a * 255).astype(np.uint8))
    elif tipo in ("brasas", "polvo"):
        cuantas = 70 if tipo == "brasas" else 110
        _tex[tipo] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.4, 1.0), rng.uniform(0, 6.28))
                      for _ in range(cuantas)]
    return _tex[tipo]


def efectos(im, nombre, T, quitar=()):
    activos = [k for k, v in EFECTOS.items() if nombre in v and k not in quitar]
    if not activos:
        return im
    im = im.convert("RGBA")
    for tipo in activos:
        if tipo == "lluvia":
            tex = textura_efecto("lluvia")
            off = int((T * 900) % H)
            a = tex.crop((0, H - off, W, 2 * H - off)).point(lambda v: int(v * (0.55 if nombre == "andes" else 0.9)))
            capa = Image.new("RGBA", (W, H), (200, 205, 215, 0))
            capa.putalpha(a)
            im.alpha_composite(capa)
        elif tipo in ("humo", "niebla"):
            tex = textura_efecto(tipo)
            vel = 35 if tipo == "humo" else 18
            off = int((T * vel) % W)
            a = tex.crop((off, 0, off + W, H)).point(lambda v: int(v * (0.32 if tipo == "humo" else 0.28)))
            color = (150, 135, 120, 0) if tipo == "humo" else (215, 205, 195, 0)
            capa = Image.new("RGBA", (W, H), color)
            capa.putalpha(a)
            im.alpha_composite(capa)
        elif tipo in ("brasas", "polvo"):
            d = ImageDraw.Draw(im)
            for (x0, y0, v, f) in textura_efecto(tipo):
                if tipo == "brasas":
                    y = (y0 - T * 90 * v) % H
                    x = x0 + 25 * math.sin(T * 1.5 + f)
                    r = 2.5 * v
                    alfa = int(220 * v * (0.6 + 0.4 * math.sin(T * 6 + f)))
                    d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 170, 70, alfa))
                else:
                    y = (y0 - T * 12 * v) % H
                    x = (x0 + T * 8 * v + 30 * math.sin(T * 0.4 + f)) % W
                    r = 1.6 * v + 0.6
                    alfa = int(110 * v * (0.5 + 0.5 * math.sin(T * 1.2 + f)))
                    d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 235, 200, alfa))
    im = im.convert("RGB")
    if "parpadeo" in activos:
        k = 1 + 0.035 * math.sin(T * 9.1) + 0.025 * math.sin(T * 13.7 + 1) + 0.02 * math.sin(T * 3.3)
        im = Image.fromarray(np.clip(np.asarray(im, np.float32) * k, 0, 255).astype(np.uint8))
    return im


def visual(i, t):
    """Imagen 1920x1080 RGB de la escena i en su segundo t (sin subtítulos)."""
    e = ESCENAS[i]
    dur = e["fin"] - e["inicio"]
    nombre = visual_de(i)
    es_mapa = nombre in MP.MAPAS and e["tipo"] == "plano"
    if e["tipo"] == "plano" and i in FOTOS:
        # varias obras en la escena: cada una ocupa un tramo igual, con fundido entre ellas
        lista = FOTOS[i]
        tramo = dur / len(lista)
        k = min(int(t // tramo), len(lista) - 1)

        def obra(k, tl):
            caja = ken_burns(i * 31 + k, tl, tramo + FUNDIDO, False)
            return imagen(lista[k]).resize((W, H), Image.BICUBIC, box=caja)

        im = obra(k, t - k * tramo)
        if k > 0 and t - k * tramo < FUNDIDO:
            im = Image.blend(obra(k - 1, t - (k - 1) * tramo), im, ease((t - k * tramo) / FUNDIDO))
        # sobre fotos y pinturas no van las brasas ni el parpadeo de vela de las ilustraciones
        return efectos(im, e["visual"], e["inicio"] + t, quitar=("brasas", "parpadeo"))
    if e["tipo"] == "plano":
        base = imagen(nombre)
        if es_mapa:
            big = base.convert("RGBA")
            MP.capas(nombre, t, big)
            base = big.convert("RGB")
        caja = ken_burns(i, t, dur + FUNDIDO, es_mapa)
        im = base.resize((W, H), Image.BICUBIC, box=caja)
        return efectos(im, nombre, e["inicio"] + t)
    # portada y capítulos: fondo desenfocado y oscuro + texto
    base = imagen(nombre, 14)
    z = 1.0 + 0.06 * t / dur
    cw, ch = W0 / z, H0 / z
    im = base.resize((W, H), Image.BICUBIC, box=((W0 - cw) / 2, (H0 - ch) / 2, (W0 + cw) / 2, (H0 + ch) / 2))
    d = ImageDraw.Draw(im, "RGBA")
    if e["tipo"] == "portada":
        a = ease((t - 0.8) / 1.5)
        fa = fuente("serif_b", 150)
        d.text((W / 2, H * 0.42), "SIMÓN BOLÍVAR", font=fa, anchor="mm", fill=ORO + (int(255 * a),))
        b = ease((t - 1.8) / 1.2)
        ancho = 520 * b
        d.line((W / 2 - ancho, H * 0.52, W / 2 + ancho, H * 0.52), fill=ORO + (int(255 * b),), width=3)
        d.text((W / 2, H * 0.585), "LA HISTORIA DEL LIBERTADOR DE AMÉRICA", font=fuente("serif", 54), anchor="mm",
               fill=CREMA + (int(255 * b),))
        c = ease((t - 3.0) / 1.2)
        d.text((W / 2, H * 0.8), "UN DOCUMENTAL DE CURIOSIDADES DEL MUNDO", font=fuente("sans", 30), anchor="mm",
               fill=(200, 185, 160, int(255 * c)))
        return im
    arriba, titulo = titulo_partes(e["titulo"])
    a = ease((t - 0.3) / 1.0)
    d.text((W / 2, H * 0.36 - 20 * (1 - a)), arriba, font=fuente("serif", 50), anchor="mm", fill=ORO + (int(255 * a),))
    b = ease((t - 0.7) / 1.0)
    ancho = 300 * b
    d.line((W / 2 - ancho, H * 0.42, W / 2 + ancho, H * 0.42), fill=ORO + (int(255 * b),), width=3)
    d.ellipse((W / 2 - 7, H * 0.42 - 7, W / 2 + 7, H * 0.42 + 7), fill=ORO + (int(255 * b),))
    ft = fuente("serif_b", 82)
    lineas = envolver(titulo, ft, 1500)
    y = H * 0.5
    c = ease((t - 1.0) / 1.2)
    for ln in lineas:
        d.text((W / 2, y + 20 * (1 - c)), ln, font=ft, anchor="ma", fill=CREMA + (int(255 * c),))
        y += 100
    return im


# ---------------- subtítulos y rótulos ----------------

def trozos(frase, max_c=95):
    """Divide una frase larga en trozos de subtítulo con su fracción de tiempo."""
    palabras = frase.split()
    n = max(1, math.ceil(len(frase) / max_c))
    objetivo = len(frase) / n
    out, actual = [], ""
    for p in palabras:
        if actual and len(actual) + len(p) + 1 > objetivo * 1.15 and len(out) < n - 1:
            out.append(actual)
            actual = p
        else:
            actual = (actual + " " + p).strip()
    out.append(actual)
    return out


FECHA = re.compile(r"\b(\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de \d{4})")
ANIO = re.compile(r"\b(1[78]\d\d)\b")


def rotulos(im, T, i):
    e = ESCENAS[i]
    d = ImageDraw.Draw(im, "RGBA")
    if e["tipo"] != "plano":
        return
    # capítulo arriba a la izquierda
    cap = e.get("capitulo", -1)
    if 0 <= cap < len(LINEA["capitulos"]):
        arriba, titulo = titulo_partes(LINEA["capitulos"][cap])
        txt = (arriba + "  ·  " + titulo) if arriba else titulo
        d.text((60, 48), txt, font=fuente("sans", 24), fill=(235, 225, 205, 150), stroke_width=2, stroke_fill=(0, 0, 0, 90))
    for f in e["frases"]:
        if f["inicio"] - 0.1 <= T < f["fin"] + 0.3:
            # fecha destacada (no en mapas: ya tienen título)
            if e["visual"] not in MP.MAPAS:
                m = FECHA.search(f["texto"]) or ANIO.search(f["texto"])
                if m:
                    a = ease((T - f["inicio"]) / 0.6) * ease((f["fin"] + 0.3 - T) / 0.4)
                    txt = m.group(1)
                    fa = fuente("serif_b", 68 if len(txt) < 6 else 46)
                    ancho = fa.getlength(txt)
                    x1, y = W - 70, 92
                    d.rectangle((x1 - ancho - 40, y - 52, x1, y + 52), fill=(20, 14, 10, int(170 * a)))
                    d.line((x1 - ancho - 40, y + 52, x1, y + 52), fill=ORO + (int(255 * a),), width=3)
                    d.text((x1 - 20, y), txt, font=fa, anchor="rm", fill=ORO + (int(255 * a),))
            partes = trozos(f["texto"])
            total = sum(len(p) for p in partes)
            t0 = f["inicio"]
            dur = f["fin"] - f["inicio"]
            for k, p in enumerate(partes):
                t1 = t0 + dur * len(p) / total
                if t0 - (0.1 if k == 0 else 0) <= T < (t1 if k < len(partes) - 1 else t1 + 0.3):
                    fs = fuente("sans", 42)
                    lineas = envolver(p, fs, 1560)
                    y = H - 70 - 54 * len(lineas)
                    for ln in lineas:
                        d.text((W / 2, y), ln, font=fs, anchor="ma", fill=(255, 250, 240, 255), stroke_width=4,
                               stroke_fill=(0, 0, 0, 200))
                        y += 54
                t0 = t1
            break


def cuadro(n):
    T = n / FPS
    i = indice(T)
    e = ESCENAS[i]
    t = T - e["inicio"]
    im = visual(i, t)
    if i > 0 and t < FUNDIDO:
        prev = ESCENAS[i - 1]
        im = Image.blend(visual(i - 1, prev["fin"] - prev["inicio"] + t), im, ease(t / FUNDIDO))
    rotulos(im, T, i)
    vin, grano = viñeta_y_grano()
    arr = np.asarray(im, np.float32) * vin + grano[n % len(grano)]
    # fundido de entrada y salida del video
    total = LINEA["duracion"]
    fade = min(ease(T / 1.5), ease((total - T) / 2.0))
    if fade < 1:
        arr *= fade
    return np.clip(arr, 0, 255).astype(np.uint8)


_inicios = [e["inicio"] for e in ESCENAS]


def indice(T):
    import bisect
    return max(0, bisect.bisect_right(_inicios, T) - 1)


# ---------------- codificación en paralelo ----------------

def segmento(args):
    k, n0, n1, ruta = args
    if ruta.exists():
        return k
    tmp = ruta.with_suffix(".tmp.mp4")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
           "-pix_fmt", "yuv420p", "-threads", "2", str(tmp)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        pr.stdin.write(cuadro(n).tobytes())
    pr.stdin.close()
    if pr.wait() != 0:
        raise RuntimeError(f"ffmpeg falló en el segmento {k}")
    tmp.rename(ruta)
    return k


# ---------------- música ----------------

def musica(ruta, dur, sr=22050):
    n = int(dur * sr)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(3)

    def nota(m):
        return 440 * 2 ** ((m - 69) / 12)

    # progresión menor, solemne: Dm - Bb - F - C / Dm - Gm - A - Dm
    acordes = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [48, 55, 60, 64],
               [50, 57, 62, 65], [43, 55, 58, 62], [45, 52, 57, 61], [50, 57, 62, 65]]
    compas = 8.0
    nb = int(dur // compas) + 1
    for b in range(nb):
        i0 = int(b * compas * sr)
        largo = int((compas + 3) * sr)
        i1 = min(n, i0 + largo)
        if i0 >= n:
            break
        tt = np.arange(i1 - i0, dtype=np.float32) / sr
        env = np.minimum(1, tt / 2.5) * np.clip((compas + 3 - tt) / 3, 0, 1)
        ac = acordes[b % len(acordes)]
        seg = np.zeros(i1 - i0, np.float32)
        for m in ac:
            f = nota(m)
            for h, amp in ((1, 1.0), (2, 0.35), (3, 0.18), (4, 0.08)):
                for det in (-0.12, 0.12):
                    seg += amp * np.sin(2 * np.pi * f * h * (1 + det / 100) * tt + rng.uniform(0, 6))
        seg *= 0.018 * env * (1 + 0.15 * np.sin(2 * np.pi * 0.2 * tt))
        bajo = nota(ac[0] - 12)
        seg += 0.06 * env * np.sin(2 * np.pi * bajo * tt)
        out[i0:i1] += seg
        # notas sueltas tipo piano
        for _ in range(3):
            m = rng.choice(ac) + 12
            t0 = rng.uniform(0.5, compas - 1)
            j0 = i0 + int(t0 * sr)
            L = int(3.5 * sr)
            if j0 + L >= n:
                continue
            tn = np.arange(L, dtype=np.float32) / sr
            f = nota(m)
            pn = (np.sin(2 * np.pi * f * tn) + 0.3 * np.sin(4 * np.pi * f * tn) + 0.1 * np.sin(6 * np.pi * f * tn))
            out[j0:j0 + L] += 0.05 * pn * np.exp(-tn * 1.6) * np.minimum(1, tn / 0.01)
    # timbal al inicio de cada capítulo
    for e in ESCENAS:
        if e["tipo"] in ("capitulo", "portada"):
            j0 = int((e["inicio"] + 0.2) * sr)
            L = int(2.5 * sr)
            if j0 + L < n:
                tn = np.arange(L, dtype=np.float32) / sr
                golpe = np.sin(2 * np.pi * (70 - 15 * tn) * tn) * np.exp(-tn * 2.2)
                golpe += 0.3 * rng.standard_normal(L).astype(np.float32) * np.exp(-tn * 25)
                out[j0:j0 + L] += 0.35 * golpe
    # suavizado (paso bajo simple) para un sonido cálido
    k = np.ones(6, np.float32) / 6
    out = np.convolve(out, k, mode="same")
    # sube la música donde no hay voz y la baja bajo la narración
    gan = np.full(n, 1.0, np.float32)
    for f in TODAS_FRASES:
        a, b = int((f["inicio"] - 0.4) * sr), int((f["fin"] + 0.4) * sr)
        gan[max(0, a):min(n, b)] = 0.32
    ventana = int(0.8 * sr)
    gan = np.convolve(gan, np.ones(ventana, np.float32) / ventana, mode="same")
    out *= gan
    t = np.arange(n, dtype=np.float32) / sr
    out *= np.minimum(1, t / 3) * np.clip((dur - t) / 4, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.6
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


# ---------------- sonidos de ambiente (ElevenLabs) ----------------

def ambientes(ruta, dur, sr=44100):
    conf = json.loads((AQUI / "ambientes.json").read_text(encoding="utf-8"))
    carpeta = BUILD / "ambientes"
    disponibles = {f.stem for f in carpeta.glob("*.mp3")} if carpeta.exists() else set()
    sustitutos = {"victoria": "batalla", "mar_noche": "mar", "playa": "mar", "tormenta": "andes",
                  "llanos": "viento", "rio": "viento", "salon": "ciudad"}
    cache = {}

    def cargar(nombre):
        if nombre not in cache:
            r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(carpeta / f"{nombre}.mp3"), "-ac", "1", "-ar",
                                str(sr), "-f", "f32le", "-"], capture_output=True, check=True)
            x = np.frombuffer(r.stdout, np.float32)
            cache[nombre] = x / (np.sqrt((x ** 2).mean()) + 1e-9) * 0.1  # mismo volumen para todos
        return cache[nombre]

    n = int(dur * sr)
    out = np.zeros(n, np.float32)
    for e in ESCENAS:
        if e["tipo"] != "plano":
            continue
        nombre = conf["escenas"].get(e["visual"])
        if nombre and nombre not in disponibles:
            nombre = sustitutos.get(nombre)
        if not nombre or nombre not in disponibles:
            continue
        x = cargar(nombre)
        a, b = int(max(0, e["inicio"] - 0.8) * sr), int(min(dur, e["fin"] + 0.8) * sr)
        largo = b - a
        if largo <= 0:
            continue
        rep = np.tile(x, largo // len(x) + 2)
        ini = int(np.random.default_rng(a).integers(0, len(x)))
        seg = rep[ini:ini + largo].copy()
        f = min(int(1.2 * sr), largo // 2)
        seg[:f] *= np.linspace(0, 1, f) ** 0.5
        seg[-f:] *= np.linspace(1, 0, f) ** 0.5
        out[a:b] += seg
    gan = np.full(n, 1.0, np.float32)
    for fr in TODAS_FRASES:
        a, b = int((fr["inicio"] - 0.3) * sr), int((fr["fin"] + 0.3) * sr)
        gan[max(0, a):min(n, b)] = 0.45
    v = int(0.6 * sr)
    gan = np.convolve(gan, np.ones(v, np.float32) / v, mode="same")
    out *= gan
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-o", default=str(AQUI.parent.parent / "exportados" / "simon-bolivar-documental.mp4"))
    p.add_argument("--vista", type=float)
    p.add_argument("--hasta", type=float)
    p.add_argument("--procesos", type=int, default=4)
    args = p.parse_args()

    if args.vista is not None:
        Image.fromarray(cuadro(int(args.vista * FPS))).save(args.o if args.o.endswith(".png") else "vista.png")
        return

    total = LINEA["duracion"] if not args.hasta else min(args.hasta, LINEA["duracion"])
    nf = int(total * FPS)
    segdir = BUILD / "seg"
    segdir.mkdir(exist_ok=True)
    trabajos = []
    for k, e in enumerate(ESCENAS):
        n0, n1 = math.ceil(e["inicio"] * FPS), min(nf, math.ceil(e["fin"] * FPS))
        if k == len(ESCENAS) - 1:
            n1 = nf
        if n1 > n0:
            trabajos.append((k, n0, n1, segdir / f"{k:04d}_{n0}_{n1}.mp4"))
    print(f"{len(trabajos)} segmentos, {nf} cuadros ({total/60:.1f} min)", file=sys.stderr)
    orden = sorted(trabajos, key=lambda x: -(x[2] - x[1]))
    hechos = 0
    with Pool(args.procesos) as pool:
        for _ in pool.imap_unordered(segmento, orden):
            hechos += 1
            if hechos % 10 == 0:
                print(f"  {hechos}/{len(trabajos)}", file=sys.stderr)
    lista = segdir / "lista.txt"
    lista.write_text("".join(f"file '{t[3].name}'\n" for t in trabajos))
    video = BUILD / "video_sin_audio.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", str(video)], check=True)
    mus = BUILD / "musica.wav"
    musica(mus, LINEA["duracion"])
    amb = BUILD / "ambientes.wav"
    ambientes(amb, LINEA["duracion"])
    if LINEA.get("voz") == "elevenlabs":
        voz = "highpass=f=60,acompressor=threshold=-18dB:ratio=2.5:attack=15:release=250,aresample=48000,volume=1.3"
    else:
        voz = ("highpass=f=80,lowpass=f=7200,equalizer=f=180:t=q:w=1:g=3,equalizer=f=3000:t=q:w=1.5:g=2,"
               "aecho=0.85:0.6:35|60:0.12|0.07,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,"
               "aresample=48000,volume=1.6")
    filtro = (f"[1:a]{voz}[v];[2:a]aresample=48000,volume=0.5[m];[3:a]aresample=48000,volume=0.9[s];"
              f"[v][m][s]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                    "-i", str(BUILD / "narracion.wav"), "-i", str(mus), "-i", str(amb), "-filter_complex", filtro,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
                    "-t", f"{total:.3f}", "-movflags", "+faststart", args.o], check=True)
    print("Listo:", args.o)


if __name__ == "__main__":
    main()
