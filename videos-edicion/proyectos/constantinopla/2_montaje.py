"""Paso 2: monta el video vertical (1080x1920, 60 s) con imágenes, subtítulos, música y efectos.

Uso: python3 2_montaje.py <carpeta_salida> [--procesos 4]
Necesita <salida>/voz.json (paso 1). Crea <salida>/Caida_de_Constantinopla.mp4 y constantinopla.srt.
"""
import argparse
import json
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from guion import ESCENAS

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "napoleon"))
import sonido as S  # noqa: E402

W, H, FPS, DURACION = 1080, 1920, 30, 60.0
FH = 1240                      # alto de la imagen principal
FY = 250                       # posición vertical de la imagen principal
FUNDIDO = 0.6                  # fundido entre imágenes
MARCA = "CURIOSIDADES DEL MUNDO"
FOCO = {"05_mehmed_tienda": 0.72, "04_mehmed_entrada": 0.33}  # centro horizontal del personaje
FUENTES = AQUI.parent / "napoleon" / "fuentes"


def fuente(nombre, tam):
    rutas = {"titulo": FUENTES / "cinzel-latin-700-normal.woff",
             "deco": FUENTES / "cinzel-decorative-latin-700-normal.woff",
             "sub": "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
             "nota": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"}
    return ImageFont.truetype(str(rutas[nombre]), tam)


# ------------------------------------------------------------------ línea de tiempo
def linea_de_tiempo(voz):
    """Coloca cada frase en el tiempo y reparte las imágenes de cada escena."""
    t, frases, escenas = 0.35, [], []
    for e, (escena, vf) in enumerate(zip(ESCENAS, voz)):
        ini = 0.0 if e == 0 else t - 0.2
        for i, f in enumerate(vf):
            if f["texto"].startswith("Una ciudad cayó"):
                t += 0.45  # pausa dramática antes de la frase final
            frases.append({**f, "ini": t, "fin": t + f["dur"]})
            t += f["dur"] + 0.2
        t += 0.15
        escenas.append({"ini": ini, "fin": t - 0.2, "imagenes": escena["imagenes"], "musica": escena["musica"]})
    fin_voz = frases[-1]["fin"]
    global DURACION
    DURACION = max(DURACION, round(fin_voz + 2.2, 1))  # deja sitio al cierre si la voz es más larga
    escenas[-1]["fin"] = DURACION
    for a, b in zip(escenas, escenas[1:]):
        a["fin"] = b["ini"]
    tramos = []
    for e, esc in enumerate(escenas):
        fin = fin_voz + 0.3 if e == len(escenas) - 1 else esc["fin"]
        n = len(esc["imagenes"])
        for k, nombre in enumerate(esc["imagenes"]):
            tramos.append({"img": nombre, "ini": esc["ini"] + (fin - esc["ini"]) * k / n,
                           "fin": esc["ini"] + (fin - esc["ini"]) * (k + 1) / n, "escena": e})
    return frases, escenas, tramos, fin_voz


def trozos(frase):
    """Parte una frase en los trozos marcados con « | » en el guion, repartiendo su duración."""
    if "trozos" in frase:  # tiempos exactos por palabra (1b_voz_externa.py)
        return [{**t, "ini": frase["ini"] + t["ini"], "fin": frase["ini"] + t["fin"]} for t in frase["trozos"]]
    textos = frase["texto"].split(" | ")
    pesos = np.array([len(x) + 4 for x in textos], float)
    limites = frase["ini"] + np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * frase["dur"]
    return [{"texto": x, "ini": limites[i], "fin": limites[i + 1]} for i, x in enumerate(textos)]


# ------------------------------------------------------------------ imágenes
def sin_bandas(img):
    """Quita las bandas negras de arriba/abajo/lados."""
    a = np.asarray(img.convert("L")).astype(float)
    filas = np.where(a.mean(1) > 18)[0]
    cols = np.where(a.mean(0) > 18)[0]
    return img.crop((cols[0] + 2, filas[0] + 2, cols[-1] - 1, filas[-1] - 1))


def mapa():
    """Imagen añadida: mapa de la posición de Constantinopla entre Europa y Asia."""
    import warnings
    warnings.filterwarnings("ignore")
    import geopandas as gpd
    from shapely.ops import unary_union
    w, h = 1250, 1430
    lon0, lon1, lat0, lat1 = 15.0, 43.0, 33.0, 50.5
    k = math.cos(math.radians(41))
    esc = min(w / ((lon1 - lon0) * k), h / (lat1 - lat0))
    cx, cy = (lon0 + lon1) / 2, (lat0 + lat1) / 2

    def f(lon, lat):
        return (w / 2 + (lon - cx) * k * esc, h / 2 - (lat - cy) * esc)

    yy = np.linspace(0, 1, h)[:, None, None]
    mar = np.broadcast_to(np.array([18, 38, 58]) * (1 - yy) + np.array([10, 24, 40]) * yy, (h, w, 3))
    img = Image.fromarray(mar.astype(np.uint8)).convert("RGBA")
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    tierra = unary_union(list(gpd.read_file(gpd.datasets.get_path("naturalearth_lowres")).geometry.buffer(0)))
    for pg in getattr(tierra, "geoms", [tierra]):
        pts = [f(x, y) for x, y in pg.exterior.coords]
        if max(p[0] for p in pts) < 0 or min(p[0] for p in pts) > w:
            continue
        d.polygon(pts, fill=(196, 168, 120, 255))
        d.line(pts + [pts[0]], fill=(240, 210, 150, 255), width=3)
    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sombra.putalpha(capa.split()[3].filter(ImageFilter.GaussianBlur(18)).point(lambda v: v * 0.8))
    img = Image.alpha_composite(img, sombra)
    img = Image.alpha_composite(img, capa)
    d = ImageDraw.Draw(img)
    x, y = f(28.98, 41.01)
    for r, a in ((70, 50), (46, 90), (26, 150)):
        brillo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(brillo).ellipse((x - r, y - r, x + r, y + r), fill=(255, 200, 90, a))
        img = Image.alpha_composite(img, brillo.filter(ImageFilter.GaussianBlur(r / 2)))
    d = ImageDraw.Draw(img)
    d.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(255, 225, 150), outline=(90, 20, 10), width=4)

    def rotulo(px, py, texto, tam, color=(60, 40, 20), fuente_="titulo", sombra_=(240, 220, 180)):
        d.text((px, py), texto, font=fuente(fuente_, tam), fill=color, anchor="mm",
               stroke_width=3, stroke_fill=sombra_)

    rotulo(*f(25.5, 46.8), "EUROPA", 96)
    rotulo(*f(35.0, 38.6), "ASIA", 96)
    rotulo(*f(35.0, 43.4), "Mar Negro", 44, (220, 230, 240), "titulo", (15, 30, 45))
    rotulo(*f(23.0, 34.6), "Mar Mediterráneo", 44, (220, 230, 240), "titulo", (15, 30, 45))
    rotulo(x, y + 62, "CONSTANTINOPLA", 50, (255, 230, 170), "titulo", (40, 15, 5))
    return img.convert("RGB")


def mejorar(img, alto):
    """Sube la resolución por pasos con realce, limpia artefactos JPEG y da un etalonaje cinematográfico."""
    img = img.filter(ImageFilter.GaussianBlur(0.5))           # suaviza bloques de compresión
    while img.height < alto:
        f = min(1.5, alto / img.height)
        img = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(1.2, 65, 1))  # recupera bordes en cada paso
    img = img.resize((round(img.width * alto / img.height), alto), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(18, 22, 0))      # claridad: contraste local
    img = img.filter(ImageFilter.UnsharpMask(1.0, 55, 2))     # nitidez fina
    img = ImageEnhance.Contrast(img).enhance(1.07)
    img = ImageEnhance.Color(img).enhance(1.10)
    a = np.asarray(img).astype(np.float32) / 255
    luz = a.mean(2, keepdims=True)
    # sombras ligeramente frías y luces cálidas (look de cine)
    tono = (1 - luz) * np.array([-0.012, 0.0, 0.02]) + luz * np.array([0.025, 0.008, -0.02])
    return Image.fromarray(np.clip((a + tono) * 255, 0, 255).astype(np.uint8))


def preparar_imagen(nombre):
    img = mapa() if nombre == "mapa" else sin_bandas(Image.open(AQUI / "imagenes" / f"{nombre}.jpg").convert("RGB"))
    # imagen principal a 1,15x para poder acercar la cámara sin perder definición
    alto = int(FH * 1.15)
    grande = img.resize((int(img.width * alto / img.height), alto), Image.LANCZOS) if nombre == "mapa" \
        else mejorar(img, alto)
    # fondo desenfocado y oscuro para rellenar arriba y abajo
    esc = max(W / img.width, H / img.height) * 1.1
    fondo = img.resize((int(img.width * esc), int(img.height * esc)), Image.BILINEAR)
    fondo = fondo.crop(((fondo.width - W) // 2, (fondo.height - H) // 2,
                        (fondo.width - W) // 2 + W, (fondo.height - H) // 2 + H))
    fondo = fondo.filter(ImageFilter.GaussianBlur(28))
    fondo = Image.fromarray((np.asarray(fondo).astype(np.float32) * 0.42).astype(np.uint8))
    return {"grande": grande, "fondo": fondo}


def mascara_imagen():
    m = np.ones((FH, W), np.float32)
    borde = 110
    rampa = np.linspace(0, 1, borde) ** 1.5
    m[:borde] *= rampa[:, None]
    m[-borde:] *= rampa[::-1, None]
    return Image.fromarray((m * 255).astype(np.uint8))


def viñeta():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return np.clip(1.08 - r ** 2.2 * 0.55, 0.45, 1.0).astype(np.float32)[..., None]


# ------------------------------------------------------------------ cuadros
G = {}


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def cuadro_tramo(tramo, t, indice):
    p = G["imgs"][tramo["img"]]
    grande, fondo = p["grande"], p["fondo"]
    dur = tramo["fin"] - tramo["ini"] + FUNDIDO
    u = suave((t - tramo["ini"]) / dur) * 0.85 + (t - tramo["ini"]) / dur * 0.15
    zoom = 1.0 + 0.12 * (u if indice % 2 == 0 else 1 - u)
    alto = grande.height / 1.15 / zoom * 1.0
    ancho = alto * W / FH
    holgura = max(grande.width - ancho, 0)
    sentido = 1 if indice % 2 == 0 else -1
    x0 = holgura * (0.5 + sentido * (u - 0.5) * 0.9)
    if tramo["img"] in FOCO:  # mantener al personaje en cuadro con un paneo corto
        x0 = FOCO[tramo["img"]] * grande.width - ancho / 2 + sentido * (u - 0.5) * 0.25 * ancho
        x0 = min(max(x0, 0), holgura)
    y0 = (grande.height - alto) * 0.5
    frente = grande.resize((W, FH), Image.BICUBIC, box=(x0, y0, x0 + ancho, y0 + alto))
    lienzo = fondo.copy()
    lienzo.paste(frente, (0, FY), G["mascara"])
    return np.asarray(lienzo).astype(np.float32)


def texto_centrado(d, y, texto, f, color, ancho_max, borde=7, interlinea=1.12):
    lineas, actual = [], ""
    for p in texto.split():
        prueba = (actual + " " + p).strip()
        if f.getlength(prueba) > ancho_max and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = prueba
    lineas.append(actual)
    alto = f.size * interlinea
    for i, l in enumerate(lineas):
        d.text((W / 2, y + (i - (len(lineas) - 1) / 2) * alto), l, font=f, fill=color, anchor="mm",
               stroke_width=borde, stroke_fill=(0, 0, 0))


def render(i):
    t = i / FPS
    tramos = G["tramos"]
    activos = [(k, tr) for k, tr in enumerate(tramos) if tr["ini"] - 1e-6 <= t < tr["fin"] + FUNDIDO]
    arr = None
    for k, tr in activos:
        capa = cuadro_tramo(tr, t, k)
        if arr is None or k == 0:
            arr = capa
        else:
            a = suave((t - tr["ini"]) / FUNDIDO)
            arr = arr * (1 - a) + capa * a
    if arr is None:
        arr = np.zeros((H, W, 3), np.float32)
    # destello breve en los cambios de escena
    for esc in G["escenas"][1:]:
        dt = t - esc["ini"]
        if -0.15 < dt < 0.5:
            arr = arr * (1 + 0.35 * math.exp(-abs(dt - 0.05) * 9))
    arr = arr * G["viñeta"]
    oy, ox = (i * 7919) % 256, (i * 104729) % 256
    arr = arr + G["grano"][oy:oy + H, ox:ox + W]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")

    fin_voz = G["fin_voz"]
    # marca arriba
    if t < fin_voz:
        f = fuente("titulo", 40)
        d.text((W / 2, 135), MARCA, font=f, fill=(232, 196, 120), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        d.line((W / 2 - 230, 175, W / 2 + 230, 175), fill=(232, 196, 120, 160), width=2)
    # aviso de recreación
    actual = activos[-1][1]["img"] if activos else ""
    aviso = "Mapa ilustrativo" if actual == "mapa" else "Recreación artística"
    d.text((40, FY + FH - 60), aviso, font=fuente("nota", 26), fill=(255, 255, 255, 150),
           stroke_width=2, stroke_fill=(0, 0, 0, 120))
    # título del gancho
    a = suave(t / 0.5) * (1 - suave((t - 3.6) / 0.6))
    if a > 0:
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        texto_centrado(dc, FY + 200, "LA CAÍDA DE", fuente("titulo", 64), (255, 240, 210), 1000, 4)
        texto_centrado(dc, FY + 290, "CONSTANTINOPLA", fuente("titulo", 92), (255, 210, 120), 1040, 5)
        texto_centrado(dc, FY + 390, "1453", fuente("titulo", 72), (255, 240, 210), 1000, 4)
        capa.putalpha(capa.split()[3].point(lambda v: int(v * a)))
        img.paste(capa, (0, 0), capa)
    # fecha de la conquista
    ini4 = G["escenas"][3]["ini"]
    a = suave((t - ini4 - 0.3) / 0.5) * (1 - suave((t - ini4 - 4.5) / 0.6))
    if a > 0:
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        texto_centrado(ImageDraw.Draw(capa), FY + 150, "29 DE MAYO DE 1453", fuente("titulo", 70),
                       (255, 215, 130), 1000, 5)
        capa.putalpha(capa.split()[3].point(lambda v: int(v * a)))
        img.paste(capa, (0, 0), capa)
    # subtítulos
    for s in G["subs"]:
        if s["ini"] <= t < s["fin"] + 0.08:
            texto_centrado(d, 1640, s["texto"].upper(), fuente("sub", 74), (255, 255, 255), 980, 8)
            break
    # cierre
    if t >= fin_voz:
        u = t - fin_voz
        negro = suave(u / 0.5)
        arr = np.asarray(img).astype(np.float32) * (1 - negro)
        img = Image.fromarray(arr.astype(np.uint8))
        a = suave((u - 0.25) / 0.5) * (1 - suave((t - (DURACION - 0.45)) / 0.45))
        if a > 0:
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(capa)
            oro = (236, 198, 118)
            texto_centrado(dc, H / 2 - 70, "CURIOSIDADES", fuente("deco", 104), oro, 1040, 0)
            dc.line((W / 2 - 300, H / 2 + 10, W / 2 + 300, H / 2 + 10), fill=oro, width=3)
            texto_centrado(dc, H / 2 + 85, "DEL  MUNDO", fuente("deco", 84), oro, 1040, 0)
            capa.putalpha(capa.split()[3].point(lambda v: int(v * a)))
            img.paste(capa, (0, 0), capa)
    return np.asarray(img).tobytes()


# ------------------------------------------------------------------ audio
def mezclar(destino, x, t, vol=1.0):
    k = S.seg(t)
    if x.ndim == 1:
        x = S.estereo(x)
    n = min(len(x), len(destino) - k)
    if n > 0:
        destino[k:k + n] += x[:n] * vol


def audio(frases, escenas, salida):
    n = S.seg(DURACION)
    voz = np.zeros((n, 2), np.float32)
    for f in frases:
        a, sr = sf.read(f["wav"], dtype="float32")
        if sr != S.SR:
            from scipy.signal import resample_poly
            a = resample_poly(a, S.SR, sr).astype(np.float32)
        a = S.normal(a, 0.9)
        mezclar(voz, np.stack([a, a], 1), f["ini"])
    musica = np.zeros((n + S.seg(8), 2), np.float32)
    for e, esc in enumerate(escenas):
        dur = esc["fin"] - esc["ini"] + 1.5
        m = S.musica(esc["musica"], dur)
        m[:S.seg(0.8)] *= np.linspace(0, 1, S.seg(0.8))[:, None]
        mezclar(musica, m, max(0, esc["ini"] - 0.7), 1.0)
    musica = musica[:n]
    # que la música baje cuando habla el narrador
    env = np.abs(voz[:, 0])
    env = S.lp(env, 3.0, 1)
    env = np.clip(env / (env.max() * 0.25), 0, 1)
    musica *= (1 - 0.55 * env)[:, None]
    efectos = np.zeros((n, 2), np.float32)
    mezclar(efectos, S.viento(escenas[1]["ini"] + 1, 1.0), 0, 0.9)
    mezclar(efectos, S.timbal(41.2), 0.05, 0.9)
    mezclar(efectos, S.impacto(), frases[1]["ini"] + 0.9, 0.35)       # "en 1453"
    for e in range(1, len(escenas)):
        mezclar(efectos, S.whoosh(0.9), escenas[e]["ini"] - 0.75, 0.5)
    e3 = escenas[2]
    for dt, pan, dist in ((1.4, -0.4, 0.2), (3.3, 0.5, 0.4), (5.6, -0.1, 0.1), (8.0, 0.6, 0.5), (10.4, -0.5, 0.3)):
        mezclar(efectos, S.canon(dist, pan), e3["ini"] + dt, 0.55)
    mezclar(efectos, S.impacto(), escenas[3]["ini"] + 0.15, 0.5)    # "29 de mayo"
    mezclar(efectos, S.campana(147.0, 7.0), escenas[3]["ini"] + 5.0, 0.35)
    mezclar(efectos, S.impacto(), G["fin_voz"] + 0.2, 0.75)          # golpe final
    total = voz * 1.0 + musica * 0.55 + efectos * 0.5
    final = S.seg(1.2)
    total[-final:] *= np.linspace(1, 0, final)[:, None] ** 2
    total = S.normal(total, 0.95)
    sf.write(salida, total, S.SR)


def srt(subs, ruta):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    ruta.write_text("\n".join(f"{i}\n{ts(s['ini'])} --> {ts(s['fin'])}\n{s['texto']}\n"
                              for i, s in enumerate(subs, 1)), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--cuadros", type=int, default=0, help="guardar solo N cuadros de prueba en PNG")
    args = ap.parse_args()
    salida = Path(args.salida)
    voz = json.loads((salida / "voz.json").read_text())
    frases, escenas, tramos, fin_voz = linea_de_tiempo(voz)
    subs = [s for f in frases for s in trozos(f)]
    G.update(frases=frases, escenas=escenas, tramos=tramos, fin_voz=fin_voz, subs=subs,
             mascara=mascara_imagen(), viñeta=viñeta(),
             grano=np.random.default_rng(1453).normal(0, 3.2, (H + 256, W + 256, 1)).astype(np.float32),
             imgs={n: preparar_imagen(n) for n in {tr["img"] for tr in tramos}})
    print(f"Duración {DURACION} s; voz termina en {fin_voz:.2f} s; escenas:", [round(e["ini"], 2) for e in escenas])
    total = int(DURACION * FPS)
    if args.cuadros:
        (salida / "prueba").mkdir(exist_ok=True)
        for i in np.linspace(0, total - 1, args.cuadros).astype(int):
            Image.frombytes("RGB", (W, H), render(i)).save(salida / "prueba" / f"{i:04d}.jpg", quality=85)
        return
    srt(subs, salida / "constantinopla.srt")
    wav = salida / "mezcla.wav"
    audio(frases, escenas, wav)
    video = salida / "Caida_de_Constantinopla.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(wav),
                           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "film", "-profile:v", "high",
                           "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                           "-movflags", "+faststart", "-shortest", str(video)], stdin=subprocess.PIPE)
    with Pool(args.procesos) as pool:
        for i, datos in enumerate(pool.imap(render, range(total), chunksize=8)):
            ff.stdin.write(datos)
            if i % 300 == 0:
                print(f"cuadro {i}/{total}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("Listo:", video)


if __name__ == "__main__":
    main()
