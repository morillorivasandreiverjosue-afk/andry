"""Monta el documental del Triángulo de las Bermudas: fotos de dominio público con movimiento, pantalla tipo radar,
subtítulos,
música de suspenso y efectos. Todo el material es de dominio público o generado con código.

Uso: python3 montaje.py <salida/> [--procesos 4] [--prueba DESDE DURACION]
Necesita <salida>/frases.json (alinear.py), narracion.wav e imagenes/.
Crea <salida>/Triangulo_Bermudas_documental.mp4, bermudas.srt, capitulos.txt y creditos_imagenes.txt.
"""
import argparse
import json
import math
import re
import subprocess
import time
from multiprocessing import Process
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import sys

sys.path.append(str(Path(__file__).resolve().parent.parent / "apolo11"))
import plan  # noqa: E402  (plan.py de esta carpeta)
import sonido_mar as S  # noqa: E402

AQUI = Path(__file__).parent
W, H, FPS = 1920, 1080, 24
PRE = 11.0       # apertura: radar y "señal perdida"
GAP = 4.5        # pausa visual antes de cada capítulo
FIN = 14.0       # tarjeta final
XF = 0.7         # fundido entre fotos
GRAN = (2112, 1188)  # tamaño de trabajo de cada foto (10 % más para el movimiento)

FD = "/usr/share/fonts/truetype/"
_F = {}


def fuente(nombre, tam):
    ruta = {"sans": FD + "liberation/LiberationSans-Bold.ttf", "sansr": FD + "liberation/LiberationSans-Regular.ttf",
            "mono": FD + "dejavu/DejaVuSansMono.ttf", "monob": FD + "dejavu/DejaVuSansMono-Bold.ttf",
            "sub": FD + "dejavu/DejaVuSans-Bold.ttf"}[nombre]
    if (ruta, tam) not in _F:
        _F[(ruta, tam)] = ImageFont.truetype(ruta, tam)
    return _F[(ruta, tam)]


def suave(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# ===================================================================== línea de tiempo
_SIL = []


def cortar_en_silencio(t):
    """Punto de corte antes de un título de capítulo: el centro de la pausa real más larga justo antes de
    `t`, para no partir ninguna palabra (la hora de `t` es aproximada)."""
    if not _SIL:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(AQUI / "narracion.wav"), "-af",
                              "silencedetect=noise=-38dB:d=0.15", "-f", "null", "-"], capture_output=True,
                             text=True).stderr
        _SIL.extend(zip([float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)],
                        [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]))
    cand = [(a, b) for a, b in _SIL if t - 3.0 < (a + b) / 2 < t + 0.6]
    if not cand:
        return max(0.0, t - 0.3)
    a, b = max(cand, key=lambda s: s[1] - s[0])
    return (a + b) / 2


def construir(salida):
    frases = json.loads((salida / "frases.json").read_text())
    # capítulo 0 = introducción (sin título propio), 1..7 = secciones del guion
    cortes = [cortar_en_silencio(it["ini"]) for it in frases if it["tipo"] == "titulo"]

    def ot(t):
        """tiempo de la narración -> tiempo del video"""
        return t + PRE + GAP * sum(1 for c in cortes if c <= t + 1e-6)

    narr_dur = sf.info(str(AQUI / "narracion.wav")).duration
    total = ot(narr_dur) + 1.0 + FIN
    imgs = sorted(p for p in (AQUI / "imagenes").iterdir() if p.suffix in (".jpg", ".png"))
    por_tema = {}
    for p in imgs:
        por_tema.setdefault(re.sub(r"_\d+$", "", p.stem), []).append(p.name)
    cursor = {}

    ultima = []

    def foto(tema, cap):
        """Elige foto del tema (y temas parecidos), turnándolas y sin repetir la anterior."""
        grupo = []
        for t in [tema] + plan.ALIAS.get(tema, []):
            grupo += por_tema.get(t, [])
        if len(grupo) < 3:
            for t in plan.POR_CAPITULO.get(cap, []):
                grupo += [x for x in por_tema.get(t, []) if x not in grupo]
        if not grupo:
            for t in plan.POR_CAPITULO[0]:
                grupo += por_tema.get(t, [])
        grupo = grupo or [imgs[0].name]
        k = cursor.get(tema, 0)
        elegido = grupo[k % len(grupo)]
        if ultima and elegido == ultima[-1] and len(grupo) > 1:
            k += 1
            elegido = grupo[k % len(grupo)]
        cursor[tema] = k + 1
        ultima.append(elegido)
        return elegido

    tomas = []

    def toma(tipo, ini, fin, **kw):
        tomas.append({"tipo": tipo, "ini": ini, "fin": fin, "semilla": len(tomas), **kw})

    # --- apertura: cortes rápidos de mar, radar y "señal perdida"
    arranque = ["oceano", "tormenta_mar", "noche_mar", "radar", "huracan", "avenger", "cyclops", "rayos",
                "oceano", "mapa"]
    for k, tema in enumerate(arranque):
        toma("cuenta", k * 1.0 + 0.4, (k + 1) * 1.0 + 0.4, img=foto(tema, 0), numero=10 - k)
    tomas[0]["ini"] = 0.0
    # --- portada (el narrador lee el título)
    t_cap0 = [it for it in frases if it["tipo"] == "titulo"][0]
    titulo, _, sub = frases[0]["texto"].partition(":")
    toma("portada", PRE - 0.6, ot(frases[1]["ini"]) - 0.2, img=foto("mapa", 0), titulo=titulo.strip(),
         subtitulo=sub.strip())
    # --- capítulos y frases
    actual = None
    for k, it in enumerate(frases):
        if it["tipo"] == "portada":
            continue
        cap = it["capitulo"]
        if it["tipo"] == "titulo":
            ini = ot(it["ini"]) - GAP
            etiqueta = it["etiqueta"].replace("CAPÍTULO ", "CAPÍTULO 0") if re.search(r"CAPÍTULO \d$", it["etiqueta"]) \
                else it["etiqueta"]
            toma("capitulo", ini, ot(it["fin"]) + 1.2, img=foto(plan.POR_CAPITULO[cap][0], cap),
                 etiqueta=etiqueta, titulo=it["texto"], cap=cap)
            actual = None
            continue
        tema = next((t for palabra, t in plan.PALABRAS if palabra in it["texto"]), None)
        ini = ot(it["ini"]) - 0.15
        if tomas[-1]["tipo"] == "capitulo":
            ini = max(ini, tomas[-1]["fin"] - XF)
        sig = frases[k + 1]["ini"] if k + 1 < len(frases) else narr_dur
        fin = ot(sig) - 0.15 if k + 1 < len(frases) and frases[k + 1]["tipo"] != "titulo" else ot(it["fin"]) + 0.8
        largo_actual = (fin - actual["ini"]) if actual else 99
        if actual and (tema is None or tema == actual["tema"]) and largo_actual < 8.5:
            actual["fin"] = fin
        elif actual and tema is None and largo_actual >= 8.5 and fin - ini < 3.0:
            actual["fin"] = fin
        else:
            t_elegido = tema or plan.POR_CAPITULO[cap][len(tomas) % len(plan.POR_CAPITULO[cap])]
            toma("foto", ini, fin, img=foto(t_elegido, cap), tema=tema or "_", cap=cap)
            actual = tomas[-1]
    # el último plano dura hasta la tarjeta final
    tomas[-1]["fin"] = total - FIN + XF
    toma("final", total - FIN, total, img=foto("noche_mar", 7))
    # tomas largas: partir en dos fotos para que haya más movimiento
    nuevas = []
    for tm in tomas:
        if tm["tipo"] == "foto" and tm["fin"] - tm["ini"] > 13:
            mitad = (tm["ini"] + tm["fin"]) / 2
            nuevas.append({**tm, "fin": mitad + XF / 2})
            nuevas.append({**tm, "ini": mitad - XF / 2, "img": foto(tm["tema"] if tm["tema"] != "_" else
                                                                     plan.POR_CAPITULO[tm["cap"]][-1], tm["cap"]),
                           "semilla": tm["semilla"] + 500})
        else:
            nuevas.append(tm)
    tomas = nuevas

    # --- subtítulos (trozos de máximo dos líneas)
    subs = []
    for it in frases:
        if it["tipo"] != "texto":
            continue
        fin = it["fin"]
        for c in cortes:  # que ningún subtítulo se quede en pantalla durante la pausa del capítulo
            if it["ini"] < c < fin:
                fin = c - 0.05
        a, b = ot(it["ini"]), ot(fin)
        trozos = trocear(it["texto"])
        pesos = np.cumsum([0] + [len(x) for x in trozos]) / sum(len(x) for x in trozos)
        for j, tr in enumerate(trozos):
            subs.append((a + (b - a) * pesos[j], a + (b - a) * pesos[j + 1] + (0.25 if j == len(trozos) - 1 else 0), tr))
    # --- rótulos
    rotulos, usados = [], set()
    for it in frases:
        for clave, rol in plan.ROTULOS.items():
            if clave in it["texto"] and clave not in usados:
                usados.add(clave)
                nombre = getattr(plan, "NOMBRES", {}).get(clave, clave)
                rotulos.append((ot(it["ini"]) + 0.3, nombre, rol))
    # --- capítulos (para YouTube)
    capitulos = [(0.0, "Introducción")]
    for tm in tomas:
        if tm["tipo"] == "capitulo":
            tt = tm["titulo"].lower()
            k = 1 if tt.startswith("¿") else 0
            tt = tt[:k] + tt[k].upper() + tt[k + 1:]
            for a, b in (("uss cyclops", "USS Cyclops"), ("flight 19", "Flight 19"),
                         ("triángulo de las bermudas", "Triángulo de las Bermudas")):
                tt = tt.replace(a, b)
            capitulos.append((tm["ini"], tt))
    capitulos.append((total - FIN, "Cierre"))
    # --- telemetría de la cabina (reloj de misión, altitud del descenso)
    inicio_cap = {tm["cap"]: tm["ini"] for tm in tomas if tm["tipo"] == "capitulo"}
    toque = 0.0
    eventos = []
    for it in frases:
        for clave, ef in plan.EFECTOS:
            if clave in it["texto"]:
                eventos.append((ot(it["ini"]), ot(it["fin"]), ef))
    return {"tomas": tomas, "subs": subs, "rotulos": rotulos, "capitulos": capitulos, "total": total,
            "cortes": cortes, "inicio_cap": inicio_cap, "toque": toque, "eventos": eventos, "pre": PRE,
            "narr_dur": narr_dur, "secciones": [(tm["ini"], tm["cap"]) for tm in tomas if tm["tipo"] == "capitulo"]}


def trocear(texto, maximo=84):
    palabras, trozos, linea = texto.split(), [], ""
    for p in palabras:
        if len(linea) + len(p) + 1 > maximo and linea:
            trozos.append(linea)
            linea = p
        else:
            linea = f"{linea} {p}".strip()
    if linea:
        trozos.append(linea)
    if len(trozos) > 1 and len(trozos[-1]) < 18:
        ultimo = trozos.pop()
        trozos[-1] += " " + ultimo
    return trozos


# ===================================================================== audio
def mezclar(tl, salida):
    n = S.seg(tl["total"]) + S.SR * 2
    narr, sr = sf.read(str(AQUI / "narracion.wav"), dtype="float32")
    if narr.ndim > 1:
        narr = narr.mean(1)
    if sr != S.SR:
        from scipy.signal import resample_poly
        narr = resample_poly(narr, S.SR, sr).astype(np.float32)
    voz = np.zeros(n, np.float32)
    bordes = [0.0] + tl["cortes"] + [tl["narr_dur"]]
    for k, (a, b) in enumerate(zip(bordes, bordes[1:])):
        destino = a + PRE + GAP * k
        trozo = narr[S.seg(a): S.seg(b)]
        i = S.seg(destino)
        voz[i: i + len(trozo)] += trozo[: n - i]
    voz = S.normal(voz, 0.89)
    # presencia de voz para bajar la música mientras se habla
    bloque = 441
    m = len(voz) // bloque * bloque
    rms = np.sqrt((voz[:m].reshape(-1, bloque) ** 2).mean(1))
    pres = (rms > 0.02).astype(np.float32)
    sv = np.zeros_like(pres)
    for i in range(1, len(pres)):
        sv[i] = sv[i - 1] + (pres[i] - sv[i - 1]) * (0.3 if pres[i] > sv[i - 1] else 0.01)
    presencia = np.pad(np.repeat(sv, bloque), (0, n - m))[:n]

    print("  música...", flush=True)
    musica = np.zeros((n, 2), np.float32)
    secs = [(0.0, "intriga")] + [(t, plan.MUSICA[c]) for t, c in tl["secciones"]] + [(tl["total"], None)]
    for (t0, est), (t1, _) in zip(secs, secs[1:]):
        if t0 == 0.0:
            t1 = PRE + 6
        a = max(0.0, t0 - 1.5)
        mm = S.musica(est, t1 - a + 3.0)
        i = S.seg(a)
        musica[i: i + len(mm)] += mm[: n - i]
    # final: música triunfal bajo la tarjeta de cierre
    print("  efectos...", flush=True)
    fx = np.zeros((n, 2), np.float32)

    def poner(s, t, v=1.0):
        i = S.seg(max(0.0, t))
        fx[i: i + len(s)] += s[: n - i] * v

    # apertura: olas, sonar y estática hasta "SEÑAL PERDIDA"
    poner(S.olas(PRE + 4), 0.0, 0.7)
    for k in range(5):
        poner(S.sonar(), 0.3 + k * 1.9, 0.75)
    poner(S.estatica(2.5), 7.6, 0.7)
    poner(S.impacto(), PRE - 0.5, 1.0)
    poner(S.whoosh(1.6), PRE - 1.6, 0.6)
    for tm in tl["tomas"]:
        if tm["tipo"] == "capitulo":
            poner(S.whoosh(1.4), tm["ini"] - 1.0, 0.5)
            poner(S.impacto(), tm["ini"] + 0.05, 0.45)
            poner(S.sonar(), tm["ini"] + 0.8, 0.6)
            poner(S.estatica(0.9), tm["ini"] + 2.2, 0.4)
    for a, b, ef in tl["eventos"]:
        if ef == "radio":
            poner(S.estatica(b - a + 0.6), a - 0.3, 0.45)
        elif ef == "sonar":
            poner(S.sonar(), a, 0.7)
            poner(S.sonar(), a + 1.9, 0.5)
        elif ef == "olas":
            poner(S.olas(b - a + 3), a - 0.5, 0.55)
        elif ef == "viento":
            poner(S.viento(b - a + 3), a - 0.5, 0.55)
        elif ef == "trueno":
            poner(S.trueno(), a + 0.3, 0.8)
        elif ef == "motor":
            poner(S.motor_avion(b - a + 3), a - 0.3, 0.5)
        elif ef == "latido":
            poner(S.latido_suave(8.0), a, 0.8)
        elif ef == "impacto":
            poner(S.impacto(), a + 0.1, 0.6)
    for t, cap in tl["secciones"]:  # ambiente de mar de fondo en todo el video
        nxt = min([x for x, _ in tl["secciones"] if x > t] + [tl["total"]])
        z = S.olas(nxt - t)
        z[: S.seg(2)] *= np.linspace(0, 1, S.seg(2))[:, None]
        z[-S.seg(2):] *= np.linspace(1, 0, S.seg(2))[:, None]
        poner(z, t, 0.18)
    mezcla = (voz[:, None] + musica * (0.5 - 0.33 * presencia[:, None]) + fx * (0.8 - 0.35 * presencia[:, None]))
    mezcla = np.tanh(mezcla * 1.1) / np.tanh(1.1)
    mezcla = S.normal(mezcla, 0.95)[: S.seg(tl["total"])]
    ruta = salida / "audio_final.wav"
    sf.write(str(ruta), mezcla, S.SR, subtype="PCM_16")
    return ruta


# ===================================================================== video
class Render:
    def __init__(self, tl):
        self.tl = tl
        self.tomas = tl["tomas"]
        self.ini = [t["ini"] for t in self.tomas]
        self.cache, self.ctxt = {}, {}
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        self.vineta = np.clip(1.06 - 0.38 * d ** 2.4, 0.3, 1.0).astype(np.float32)[..., None]
        rng = np.random.default_rng(11)
        self.grano = [rng.normal(0, 3.0, (H, W, 1)).astype(np.float32) for _ in range(4)]
        self.hud = self._hud()

    # ------------------------------------------------------------- fotos
    def foto(self, nombre):
        if nombre not in self.cache:
            if len(self.cache) > 6:
                self.cache.pop(next(iter(self.cache)))
            im = Image.open(AQUI / "imagenes" / nombre).convert("RGB")
            gw, gh = GRAN
            r = im.width / im.height
            if 1.25 < r < 2.4:  # cubrir toda la pantalla
                esc = max(gw / im.width, gh / im.height)
                im2 = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
                x0, y0 = (im2.width - gw) // 2, int((im2.height - gh) * 0.4)
                base = im2.crop((x0, y0, x0 + gw, y0 + gh))
            else:  # vertical o cuadrada: fondo desenfocado + foto entera
                esc = max(gw / im.width, gh / im.height)
                fondo = im.resize((round(im.width * esc), round(im.height * esc)), Image.BILINEAR)
                x0, y0 = (fondo.width - gw) // 2, (fondo.height - gh) // 2
                fondo = fondo.crop((x0, y0, x0 + gw, y0 + gh)).filter(ImageFilter.GaussianBlur(40))
                fondo = Image.eval(fondo, lambda v: int(v * 0.45))
                esc = min(gw * 0.92 / im.width, gh * 0.96 / im.height)
                fr = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
                sombra = Image.new("L", (fr.width + 60, fr.height + 60), 0)
                ImageDraw.Draw(sombra).rectangle([30, 30, fr.width + 30, fr.height + 30], fill=170)
                sombra = sombra.filter(ImageFilter.GaussianBlur(18))
                px, py = (gw - fr.width) // 2, (gh - fr.height) // 2
                fondo.paste((0, 0, 0), (px - 30, py - 30), sombra)
                fondo.paste(fr, (px, py))
                base = fondo
            # contraste suave
            base = Image.fromarray(np.clip((np.asarray(base, np.float32) - 128) * 1.08 + 126, 0, 255).astype(np.uint8))
            self.cache[nombre] = base
        return self.cache[nombre]

    def kenburns(self, tm, t, oscuro=1.0):
        im = self.foto(tm["img"])
        rng = np.random.default_rng(tm["semilla"] + 7)
        dur = max(tm["fin"] - tm["ini"], 0.1)
        u = suave((t - tm["ini"]) / dur) if tm["tipo"] != "cuenta" else (t - tm["ini"]) / dur
        acercar = rng.random() < 0.6
        z0, z1 = (1.0, 1.09) if acercar else (1.09, 1.0)
        if tm["tipo"] == "cuenta":
            z0, z1 = 1.0, 1.06
        z = z0 + (z1 - z0) * u
        dx, dy = rng.uniform(-1, 1) * 0.035, rng.uniform(-1, 1) * 0.025
        gw, gh = GRAN
        vw, vh = W / z * (gw / W) / 1.1, H / z * (gh / H) / 1.1
        cx = gw / 2 + dx * gw * (u - 0.5) * 2
        cy = gh / 2 + dy * gh * (u - 0.5) * 2
        cx = min(max(cx, vw / 2), gw - vw / 2)
        cy = min(max(cy, vh / 2), gh - vh / 2)
        fr = im.transform((W, H), Image.EXTENT, (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2), Image.BILINEAR)
        a = np.asarray(fr, np.float32)
        return a * oscuro if oscuro != 1.0 else a

    # ------------------------------------------------------------- texto
    def texto(self, clave, txt, f, tam, color, borde=0, espacio=0):
        k = (clave, txt, f, tam, color, borde, espacio)
        if k not in self.ctxt:
            if len(self.ctxt) > 300:
                self.ctxt.clear()
            fnt = fuente(f, tam)
            if espacio:
                anchos = [fnt.getlength(c) + espacio for c in txt]
                ancho = int(sum(anchos)) + 10 + 2 * borde
            else:
                ancho = int(fnt.getlength(txt)) + 10 + 2 * borde
            alto = int(tam * 1.35) + 2 * borde
            im = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            if espacio:
                x = 5 + borde
                for c, a in zip(txt, anchos):
                    d.text((x, borde), c, font=fnt, fill=color, stroke_width=borde, stroke_fill=(0, 0, 0, 220))
                    x += a
            else:
                d.text((5 + borde, borde), txt, font=fnt, fill=color, stroke_width=borde, stroke_fill=(0, 0, 0, 220))
            self.ctxt[k] = im
        return self.ctxt[k]

    @staticmethod
    def pegar(frame, im, x, y, alfa=1.0):
        if alfa <= 0.01:
            return
        if alfa < 0.99:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alfa)))
        frame.paste(im, (int(x), int(y)), im)

    def _hud(self):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = (235, 245, 255, 150)
        m, L = 46, 70
        for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
            d.line([(x, y), (x + sx * L, y)], fill=c, width=3)
            d.line([(x, y), (x, y + sy * L)], fill=c, width=3)
        # retícula central muy sutil
        d.line([(W / 2 - 18, H / 2), (W / 2 - 6, H / 2)], fill=(235, 245, 255, 70), width=2)
        d.line([(W / 2 + 6, H / 2), (W / 2 + 18, H / 2)], fill=(235, 245, 255, 70), width=2)
        d.line([(W / 2, H / 2 - 18), (W / 2, H / 2 - 6)], fill=(235, 245, 255, 70), width=2)
        d.line([(W / 2, H / 2 + 6), (W / 2, H / 2 + 18)], fill=(235, 245, 255, 70), width=2)
        caja = im.getbbox()
        return im.crop(caja), caja

    def dibujar_hud(self, frame, t, cap):
        hud, caja = self.hud
        frame.paste(hud, caja[:2], hud)
        d = ImageDraw.Draw(frame)
        if int(t * 1.5) % 2 == 0:
            d.ellipse([72, 70, 88, 86], fill=(255, 70, 60))
        else:
            d.ellipse([72, 70, 88, 86], fill=(90, 30, 30))
        etiqueta = "INTRO" if cap == 0 else ("FIN" if cap >= 8 else f"EXPEDIENTE {cap:02d}")
        self.pegar(frame, self.texto("hud", f"REC  ·  {etiqueta}", "monob", 24, (235, 245, 255, 210)), 98, 62)
        im = self.texto("hud", plan.FECHAS.get(cap, ""), "monob", 24, (235, 245, 255, 210))
        self.pegar(frame, im, W - 74 - im.width, 62)
        # coordenadas que "derivan" lentamente, como un rastreo
        lat = 25.0 + 0.6 * math.sin(t / 37.0)
        lon = 71.0 + 0.9 * math.cos(t / 53.0)
        txt = f"{int(lat):02d}°{int(lat % 1 * 60):02d}'N  {int(lon):02d}°{int(lon % 1 * 60):02d}'W"
        self.pegar(frame, self.texto("hud", txt, "monob", 22, (90, 215, 255, 200)), 98, 100)

    def subtitulo(self, frame, t):
        for a, b, tx in self.tl["subs"]:
            if a <= t < b:
                lineas = [tx]
                if len(tx) > 46:  # dos líneas equilibradas
                    medio = len(tx) // 2
                    esp = [k for k, c in enumerate(tx) if c == " "]
                    corte = min(esp, key=lambda k: abs(k - medio))
                    lineas = [tx[:corte], tx[corte + 1:]]
                y = H - 92 - 56 * len(lineas)
                for ln in lineas:
                    im = self.texto("sub", ln, "sub", 44, (255, 255, 255, 255), borde=3)
                    alfa = min(1, (t - a) / 0.12, (b - t) / 0.12)
                    self.pegar(frame, im, (W - im.width) / 2, y, alfa)
                    y += 56
                return

    def rotulo(self, frame, t):
        for t0, nombre, rol in self.tl["rotulos"]:
            if t0 <= t < t0 + 5.5:
                u = t - t0
                ent = suave(u / 0.5) * min(1, (5.5 - u) / 0.5)
                x = 90 - 40 * (1 - suave(u / 0.5))
                y = H - 360
                d = ImageDraw.Draw(frame, "RGBA")
                d.rectangle([x, y + 4, x + 6, y + 100], fill=(90, 215, 255, int(230 * ent)))
                self.pegar(frame, self.texto("rot", nombre.upper(), "sans", 46, (255, 255, 255, 255), borde=2), x + 22, y,
                           ent)
                self.pegar(frame, self.texto("rot", rol, "sansr", 30, (210, 225, 240, 255), borde=2), x + 24, y + 60, ent)
                return

    # ------------------------------------------------------------- tomas especiales
    def tarjeta_capitulo(self, tm, t, frame):
        u = t - tm["ini"]
        d = ImageDraw.Draw(frame, "RGBA")
        largo = 820 * suave((u - 0.2) / 0.8)
        cy = H / 2 + 10
        d.line([(W / 2 - largo / 2, cy), (W / 2 + largo / 2, cy)], fill=(90, 215, 255, 200), width=2)
        etiqueta = tm["etiqueta"]
        n = int(max(0, (u - 0.5)) / 0.06)
        vis = etiqueta[:n] + ("█" if n < len(etiqueta) or int(u * 2.5) % 2 == 0 else " ")
        im = self.texto("cap", vis, "monob", 40, (90, 215, 255, 255), espacio=6)
        self.pegar(frame, im, (W - self.texto("cap", etiqueta + "█", "monob", 40, (0, 0, 0, 0), espacio=6).width) / 2,
                   cy - 92)
        alfa = suave((u - 1.6) / 0.8) * min(1, (tm["fin"] - t) / 0.5)
        lineas = trocear(tm["titulo"].upper(), 30)
        y = cy + 30
        for ln in lineas:
            im = self.texto("cap", ln, "sans", 64, (255, 255, 255, 255), borde=2, espacio=3)
            self.pegar(frame, im, (W - im.width) / 2, y, alfa)
            y += 84

    def portada(self, tm, t, frame):
        u = t - tm["ini"]
        alfa = suave((u - 0.4) / 1.0) * min(1, (tm["fin"] - t) / 0.6)
        palabras = tm["titulo"].split()
        lineas = [" ".join(palabras[:2]), " ".join(palabras[2:])] if len(palabras) > 3 else [tm["titulo"]]
        y = H / 2 - 170
        for k, ln in enumerate(lineas):
            im = self.texto("port", ln, "sans", 76 if k == 0 else 104, (255, 255, 255, 255), borde=3, espacio=5)
            self.pegar(frame, im, (W - im.width) / 2, y, alfa)
            y += 100 if k == 0 else 150
        a2 = suave((u - 1.6) / 1.0) * min(1, (tm["fin"] - t) / 0.6)
        d = ImageDraw.Draw(frame, "RGBA")
        d.line([(W / 2 - 340, y - 14), (W / 2 + 340, y - 14)], fill=(90, 215, 255, int(200 * a2)), width=2)
        im = self.texto("port", tm["subtitulo"].upper(), "monob", 34, (90, 215, 255, 255), espacio=3)
        self.pegar(frame, im, (W - im.width) / 2, y + 6, a2)

    def cuenta(self, tm, t, frame):
        linea = "ATLÁNTICO OCCIDENTAL  ·  ZONA MIAMI — BERMUDAS — PUERTO RICO"
        n = int(t / 0.035)
        self.pegar(frame, self.texto("cnt", linea[:n], "monob", 26, (90, 215, 255, 230), espacio=3), 120, 140)
        d = ImageDraw.Draw(frame, "RGBA")
        # barrido de radar en la esquina inferior derecha
        cx, cy, r = W - 230, H - 230, 140
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(90, 215, 255, 160), width=2)
        d.ellipse([cx - r / 2, cy - r / 2, cx + r / 2, cy + r / 2], outline=(90, 215, 255, 90), width=1)
        ang = t * 2.2
        for k in range(14):
            a = ang - k * 0.05
            d.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], fill=(90, 215, 255, 200 - k * 14), width=3)
        if t < 7.5:
            px, py = cx + 60 * math.cos(1.1), cy + 60 * math.sin(1.1)
            if (ang % (2 * math.pi)) > 1.1 or t > 2.9:
                d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(255, 210, 90, 230))
        if t >= 7.5 and int(t * 3) % 2 == 0:
            im = self.texto("cnt", "SEÑAL PERDIDA", "monob", 110, (255, 80, 70, 255), borde=4, espacio=8)
            self.pegar(frame, im, (W - im.width) / 2, H / 2 - 80)

    def final(self, tm, t, frame):
        u = t - tm["ini"]
        a = suave((u - 0.8) / 1.0)
        y = H / 2 - 130
        for txt, f, tam, col, esp in (("CURIOSIDADES DEL MUNDO", "sans", 84, (255, 255, 255, 255), 6),
                                      ("Suscríbete y activa la campana para más historias", "sansr", 40,
                                       (230, 238, 250, 255), 0),
                                      ("IMÁGENES: NASA · NOAA · US NAVY · DOMINIO PÚBLICO   ·   MÚSICA ORIGINAL", "mono", 24,
                                       (90, 215, 255, 230), 3)):
            im = self.texto("fin", txt, f, tam, col, borde=2 if tam > 30 else 0, espacio=esp)
            self.pegar(frame, im, (W - im.width) / 2, y, a)
            y += tam * 1.9
            a = suave((u - 1.6) / 1.0)

    # ------------------------------------------------------------- un fotograma
    def base(self, tm, t):
        oscuro = {"capitulo": 0.42, "portada": 0.6, "final": 0.35}.get(tm["tipo"], 1.0)
        return self.kenburns(tm, t, oscuro)

    def cuadro(self, n):
        t = n / FPS
        i = max(0, np.searchsorted(self.ini, t, side="right") - 1)
        tm = self.tomas[i]
        while i + 1 < len(self.tomas) and self.tomas[i + 1]["ini"] <= t:
            i += 1
            tm = self.tomas[i]
        a = self.base(tm, t)
        # fundido con la toma anterior
        if i > 0 and tm["tipo"] != "cuenta":
            prev = self.tomas[i - 1]
            u = (t - tm["ini"]) / XF
            if u < 1 and prev["fin"] > t - 0.01 and prev["tipo"] != "cuenta":
                b = self.base(prev, t)
                k = suave(u)
                a = a * k + b * (1 - k)
            elif u < 1 and prev["tipo"] == "cuenta":
                a = a + 255 * (1 - suave(u)) * 0.9  # destello blanco al terminar la apertura
        # destellos (despegue)
        for e0, e1, ef in self.tl["eventos"]:
            if ef == "despegue" and 0 <= t - e0 < 1.2:
                a = a + 120 * (1 - (t - e0) / 1.2)
        if 7.5 <= t < PRE - 0.4:  # interferencia de señal
            a = a * 0.55 + self.grano[n % 4] * 9
        a = a * self.vineta + self.grano[n % 4]
        frame = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        cap = tm.get("cap", 0) if tm["tipo"] not in ("final",) else 8
        if tm["tipo"] in ("foto",):
            self.dibujar_hud(frame, t, cap)
        elif tm["tipo"] == "capitulo":
            self.dibujar_hud(frame, t, cap)
            self.tarjeta_capitulo(tm, t, frame)
        elif tm["tipo"] == "portada":
            self.portada(tm, t, frame)
        elif tm["tipo"] == "cuenta":
            self.dibujar_hud(frame, t, 0)
            self.cuenta(tm, t, frame)
        elif tm["tipo"] == "final":
            self.final(tm, t, frame)
        self.rotulo(frame, t)
        self.subtitulo(frame, t)
        return np.asarray(frame)


def trabajador(tl, f0, f1, ruta):
    r = Render(tl)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "faster", "-crf", "19", "-tune", "film",
           "-threads", "2", "-pix_fmt", "yuv420p", str(ruta)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(f0, f1):
        p.stdin.write(r.cuadro(n).tobytes())
        if (n - f0) % 600 == 0:
            hecho = (n - f0) / max(f1 - f0, 1)
            print(f"  [{ruta.stem}] {hecho * 100:4.0f} %  ({time.time() - t0:.0f} s)", flush=True)
    p.stdin.close()
    p.wait()


def hms(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}"


def srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--prueba", type=float, nargs=2)
    ap.add_argument("--solo-video", action="store_true")
    a = ap.parse_args()
    salida = Path(a.salida)
    tl = construir(salida)
    print(f"Duración: {hms(tl['total'])}  ·  {len(tl['tomas'])} planos  ·  {len(tl['subs'])} subtítulos")
    with open(salida / "bermudas.srt", "w", encoding="utf-8") as f:
        for k, (x, y, tx) in enumerate(tl["subs"], 1):
            f.write(f"{k}\n{srt(x)} --> {srt(y)}\n{tx}\n\n")
    (salida / "capitulos.txt").write_text("\n".join(f"{hms(t)} {n}" for t, n in tl["capitulos"]) + "\n")
    cred = {}
    for f in (AQUI / "imagenes").glob("creditos*.json"):
        cred.update(json.loads(f.read_text()))
    usadas = sorted({tm["img"] for tm in tl["tomas"]})
    (salida / "creditos_imagenes.txt").write_text(
        "Imágenes de dominio público (NASA, NOAA, US Navy y otras), vía Wikimedia Commons:\n" +
        "\n".join(f"{u}: {cred.get(u, {}).get('fuente', '')} [{cred.get(u, {}).get('licencia', '')}]" for u in usadas)
        + "\n")
    if a.prueba:
        f0, f1 = int(a.prueba[0] * FPS), int((a.prueba[0] + a.prueba[1]) * FPS)
    else:
        f0, f1 = 0, int(tl["total"] * FPS)
    if not a.solo_video and not a.prueba:
        print("Mezclando audio...", flush=True)
        mezclar(tl, salida)
    print("Renderizando video...", flush=True)
    partes, procs = [], []
    paso = math.ceil((f1 - f0) / a.procesos)
    for k in range(a.procesos):
        g0, g1 = f0 + k * paso, min(f1, f0 + (k + 1) * paso)
        if g0 >= g1:
            continue
        ruta = salida / f"parte_{k}.mp4"
        partes.append(ruta)
        pr = Process(target=trabajador, args=(tl, g0, g1, ruta))
        pr.start()
        procs.append(pr)
    for pr in procs:
        pr.join()
    lista = salida / "partes.txt"
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
    video = salida / "video_sin_audio.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(video)], check=True)
    final = salida / ("prueba.mp4" if a.prueba else "Triangulo_Bermudas_documental.mp4")
    audio = salida / "audio_final.wav"
    if a.prueba and audio.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-ss", str(a.prueba[0]), "-t",
                        str(a.prueba[1]), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", str(final)], check=True)
    elif audio.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        "-shortest", str(final)], check=True)
    for p in partes:
        p.unlink()
    print(f"Listo: {final}")


if __name__ == "__main__":
    main()
