"""Paso 2: monta el documental completo (línea de tiempo, mezcla de audio, render de video).

Uso: python3 2_montaje.py <carpeta_salida> [--prueba SEGUNDOS_DESDE SEGUNDOS_DURACION] [--procesos N]
Necesita <salida>/voz.json (lo crea 1_voz.py).
"""
import argparse
import bisect
import json
import math
import re
import subprocess
import time
from multiprocessing import Process
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw
from scipy.signal import resample_poly

import escenas as ES
import plan
import sonido as SN

FPS = 24
W, H = ES.W, ES.H
XF = 0.5          # duración del fundido entre escenas
GAP_FRASE = 0.28  # silencio entre frases
COLA = 0.75       # silencio al final de cada párrafo
BELICOS = {"descarga", "canon", "batalla", "impacto"}


# =================================================================== timeline
def construir(voz):
    clips, efectos, voces, subs, rotulos, capitulos, secciones = [], [], [], [], [], [], []
    rng = np.random.default_rng(1769)

    def nuevo_clip(spec, inicio, dur, clave=None, **extra):
        clips.append({"spec": spec, "ini": inicio, "dur": dur, "clave": clave, "cues": [], "fecha": None, **extra})
        return clips[-1]

    def sfx(nombre, t, vol=1.0, dur=None, **kw):
        efectos.append({"n": nombre, "t": t, "v": vol, "d": dur, **kw})

    def eventos_batalla(clip, t0, dur, intensidad=1.0):
        """Disparos y cañonazos sueltos durante un párrafo, con su fogonazo en pantalla."""
        t = t0 + 0.3
        while t < t0 + dur - 0.5:
            if rng.random() < 0.22:
                d = rng.uniform(0.25, 0.8)
                sfx("canon", t, 0.55 * intensidad, dist=d, pan=rng.uniform(-0.8, 0.8))
                clip["cues"].append((t - clip["ini"], "canon", 1 - d * 0.6))
            else:
                d = rng.uniform(0.2, 1.0)
                sfx("disparo", t, 0.45 * intensidad, dist=d, pan=rng.uniform(-1, 1))
                clip["cues"].append((t - clip["ini"], "disparo", 1 - d * 0.7))
            t += rng.exponential(0.55)

    # ------------------------------------------------ apertura (batalla + título)
    t = 0.0
    c0 = nuevo_clip(plan.E["batalla"], 0, 6.0, "apertura_batalla")
    sfx("tambor", 0.0, 0.5, 6.5)
    sfx("descarga", 0.6, 0.9)
    c0["cues"] += [(0.6 + k * 0.12, "disparo", 0.8) for k in range(8)]
    for k, tc in enumerate((1.8, 3.0, 4.1, 5.0)):
        sfx("canon", tc, 0.9 - 0.1 * k, dist=0.1 * k, pan=(-0.5, 0.5, -0.2, 0.3)[k])
        c0["cues"].append((tc, "canon", 1.0))
    eventos_batalla(c0, 0, 6.0, 0.7)
    sfx("whoosh", 5.2, 0.7)
    nuevo_clip({"tipo": "titulo", "etiqueta": "CURIOSIDADES DEL MUNDO", "titulo": "NAPOLEÓN BONAPARTE", "tam": 120,
                "subtitulo": "Del poder absoluto a la soledad del exilio", "semilla": 99}, 6.0, 8.0, "apertura_titulo")
    sfx("impacto", 6.0, 1.0)
    sfx("campana", 9.5, 0.35)
    t = 14.0
    secciones.append((0.0, "epico"))

    # ------------------------------------------------ capítulos
    for c, cap in enumerate(voz):
        etiqueta = "INTRODUCCIÓN" if cap["etiqueta"] == "INTRODUCCIÓN" else (
            "FINAL" if cap["etiqueta"] == "FINAL" else f"CAPÍTULO {cap['numero']}")
        dur_tarjeta = max(6.5, 1.3 + cap["titulo_voz"]["dur"] + 1.8)
        nuevo_clip({"tipo": "titulo", "etiqueta": etiqueta, "titulo": cap["titulo"], "semilla": c}, t, dur_tarjeta,
                   f"titulo{c}")
        capitulos.append((t, etiqueta, cap["titulo"]))
        sfx("whoosh", t - 0.7, 0.6)
        sfx("impacto", t + 0.05, 0.75)
        voces.append((t + 1.3, cap["titulo_voz"]["wav"]))
        musica_cap = dict(plan.MUSICA[c])
        if c > 0:
            secciones.append((t, musica_cap.pop(0)))
        t += dur_tarjeta
        for p, frases in enumerate(cap["parrafos"]):
            entrada = plan.P[c][p]
            if isinstance(entrada, dict):
                clave, spec, fx = None, entrada, []
            else:
                clave, *fx = entrada.split("+")
                spec = plan.E[clave]
            if p in musica_cap and not (c == 0 and p == 0):
                secciones.append((t, musica_cap[p]))
            entrada_lenta = 1.5 if BELICOS & set(fx) else 0.35
            habla = sum(f["dur"] for f in frases) + GAP_FRASE * (len(frases) - 1)
            dur = entrada_lenta + habla + COLA
            previo = clips[-1]
            if clave and previo.get("clave") == clave and not fx:
                previo["dur"] += dur
                clip = previo
            else:
                clip = nuevo_clip(spec, t, dur, clave)
            # voz y subtítulos
            tv = t + entrada_lenta
            for f in frases:
                voces.append((tv, f["wav"]))
                subs.append((tv, tv + f["dur"], f["texto"]))
                for nombre, rol in plan.ROTULOS.items():
                    if nombre in f["texto"] and nombre not in {r[1] for r in rotulos}:
                        rotulos.append((tv, nombre, rol))
                tv += f["dur"] + GAP_FRASE
            texto = " ".join(f["texto"] for f in frases)
            anio = re.search(r"\b(1[78]\d\d)\b", texto)
            if anio and spec["tipo"] not in ("texto", "mapa", "titulo"):
                clip["fecha"] = (t - clip["ini"], anio.group(1))
            # efectos
            for e in fx:
                if e == "descarga":
                    sfx("descarga", t + 0.15, 0.85)
                    clip["cues"] += [(t + 0.15 + k * 0.1 - clip["ini"], "disparo", 0.9) for k in range(10)]
                elif e == "canon":
                    sfx("canon", t + 0.6, 1.0, dist=0.0)
                    clip["cues"].append((t + 0.6 - clip["ini"], "canon", 1.2))
                    tc = t + 4.5
                    while tc < t + dur - 1:
                        d = rng.uniform(0.5, 0.9)
                        sfx("canon", tc, 0.4, dist=d, pan=rng.uniform(-0.8, 0.8))
                        clip["cues"].append((tc - clip["ini"], "canon", 0.6))
                        tc += rng.uniform(4, 7)
                elif e == "batalla":
                    sfx("ruido_batalla", t, 0.5, dur)
                    eventos_batalla(clip, t, dur, 0.6)
                elif e == "impacto":
                    sfx("impacto", t + 0.05, 0.9)
                    clip["cues"].append((t + 0.05 - clip["ini"], "impacto", 1.0))
                elif e == "campana":
                    for k in range(3):
                        if k * 3.5 < dur - 1:
                            sfx("campana", t + 0.3 + k * 3.5, 0.45 - k * 0.1)
                elif e == "pluma":
                    sfx("pluma", t + 0.4, 0.7, min(dur - 0.5, 7))
                elif e == "whoosh":
                    sfx("whoosh", t - 0.6, 0.6)
                elif e in ("latido", "caballos", "tambor", "fuego", "viento", "olas"):
                    vol = {"latido": 0.6, "caballos": 0.55, "tambor": 0.4, "fuego": 0.6, "viento": 0.7, "olas": 0.6}[e]
                    sfx(e, t, vol, dur + 0.5)
            t += dur

    # ------------------------------------------------ cierre
    nuevo_clip({"tipo": "titulo", "etiqueta": "GRACIAS POR VER", "titulo": "CURIOSIDADES DEL MUNDO", "tam": 104,
                "subtitulo": "Suscríbete y activa la campana para más historias", "semilla": 77}, t, 13.0, "cierre")
    sfx("impacto", t + 0.05, 0.8)
    sfx("campana", t + 1.5, 0.3)
    voces.append((t + 1.5, "CIERRE"))
    capitulos.append((t, "", "Cierre"))
    t += 13.0
    secciones.append((t, None))
    return {"clips": clips, "efectos": efectos, "voces": voces, "subs": subs, "rotulos": rotulos,
            "capitulos": capitulos, "secciones": secciones, "total": t}


# =================================================================== audio
def mezclar(tl, salida, kokoro_dir):
    n = SN.seg(tl["total"]) + SN.SR * 5
    voz = np.zeros(n, np.float32)
    for t, wav in tl["voces"]:
        if wav == "CIERRE":
            wav = str(salida / "voz" / "cierre.wav")
            if not Path(wav).exists():
                from kokoro_onnx import Kokoro
                k = Kokoro(str(kokoro_dir / "kokoro-v1.0.onnx"), str(kokoro_dir / "voices-v1.0.bin"))
                a, sr = k.create("Gracias por ver este documental. Si te gustó, suscríbete a Curiosidades del Mundo, "
                                 "y activa la campana para no perderte la próxima historia.",
                                 voice="em_alex", speed=0.9, lang="es-419")
                sf.write(wav, a, sr)
        a, sr = sf.read(wav, dtype="float32")
        a = resample_poly(a, 147, 80).astype(np.float32) if sr == 24000 else a
        i = SN.seg(t)
        voz[i: i + len(a)] += a[: n - i]
    voz = SN.normal(voz, 0.9)
    # envolvente de la voz para bajar música y efectos mientras se habla
    bloque = 441
    m = len(voz) // bloque * bloque
    rms = np.sqrt((voz[:m].reshape(-1, bloque) ** 2).mean(1))
    pres = (rms > 0.02).astype(np.float32)
    suave = np.zeros_like(pres)
    for i in range(1, len(pres)):
        coef = 0.35 if pres[i] > suave[i - 1] else 0.012
        suave[i] = suave[i - 1] + (pres[i] - suave[i - 1]) * coef
    presencia = np.repeat(suave, bloque)[:n]
    presencia = np.pad(presencia, (0, n - len(presencia)))

    print("  música...", flush=True)
    musica = np.zeros((n, 2), np.float32)
    secs = tl["secciones"]
    for (t0, estado), (t1, _) in zip(secs, secs[1:]):
        m = SN.musica(estado, t1 - t0 + 3.0)
        i = SN.seg(max(0, t0 - 1.5))
        musica[i: i + len(m)] += m[: n - i]
    print("  efectos...", flush=True)
    fx = np.zeros((n, 2), np.float32)
    cache = {}
    for e in tl["efectos"]:
        nm, d = e["n"], e["d"]
        if nm == "disparo":
            s = SN.disparo(e.get("dist", 0.3), e.get("pan", 0))
        elif nm == "canon":
            s = SN.canon(e.get("dist", 0.0), e.get("pan", 0))
        elif nm in ("descarga", "impacto", "whoosh", "campana"):
            if nm not in cache:
                cache[nm] = {"descarga": SN.descarga, "impacto": SN.impacto, "whoosh": SN.whoosh,
                             "campana": SN.campana}[nm]()
            s = cache[nm]
        elif nm == "tambor":
            s = SN.tambor_militar(d, 110, volumen=0.6)
        elif nm == "ruido_batalla":
            s = SN.estereo(SN.lp(SN.ruido(SN.seg(d)), 120, 4) * 0.5)
        else:
            s = {"latido": SN.latido, "caballos": SN.caballos, "fuego": SN.fuego, "viento": SN.viento,
                 "olas": SN.olas, "pluma": SN.pluma}[nm](d)
        if d and nm not in ("descarga", "impacto", "whoosh", "campana"):
            s = s[: SN.seg(d) + SN.SR * 3].copy()
            f = min(len(s), SN.seg(0.8))
            s[:f] *= np.linspace(0, 1, f)[:, None]
            s[-f:] *= np.linspace(1, 0, f)[:, None]
        i = SN.seg(max(0, e["t"]))
        fx[i: i + len(s)] += s[: n - i] * e["v"]
    mezcla = (voz[:, None] * 1.0
              + musica * (0.55 - 0.42 * presencia[:, None])
              + fx * (0.75 - 0.4 * presencia[:, None]))
    # limitador suave
    mezcla = np.tanh(mezcla * 1.1) / np.tanh(1.1)
    mezcla = SN.normal(mezcla, 0.95)[: SN.seg(tl["total"])]
    ruta = salida / "audio_final.wav"
    sf.write(ruta, mezcla, SN.SR, subtype="PCM_16")
    return ruta


# =================================================================== video
def suave(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


class Render:
    def __init__(self, tl):
        self.tl = tl
        self.clips = tl["clips"]
        self.inicios = [c["ini"] for c in self.clips]
        self.cache = {}
        self.subs = tl["subs"]
        self.sub_ini = [s[0] for s in self.subs]
        self.cache_txt = {}
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        self.vineta = np.clip(1.08 - 0.42 * d ** 2.2, 0.25, 1.0).astype(np.float32)
        rng = np.random.default_rng(7)
        self.grano = [rng.normal(0, 2.5, (H, W, 1)).astype(np.int16) for _ in range(3)]
        self.grade = {}
        self.sprite = ES.resplandor(256, (255, 210, 140))
        self.sprite_rojo = ES.resplandor(256, (255, 120, 40))
        self.marca = self._texto_img("CURIOSIDADES DEL MUNDO", ("titulo", 24), (235, 210, 160, 120))

    # ---------------------------------------------------------- utilidades
    def _texto_img(self, txt, f, color, borde=0):
        fnt = ES.fuente(*f)
        x0, y0, x1, y1 = fnt.getbbox(txt, stroke_width=borde)
        im = Image.new("RGBA", (x1 - x0 + 8, y1 - y0 + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - x0, 4 - y0), txt, font=fnt, fill=color, stroke_width=borde,
                                stroke_fill=(0, 0, 0, 230))
        return im

    def _grade(self, tono):
        if tono not in self.grade:
            col = {"calido": (1.06, 0.98, 0.86), "frio": (0.86, 0.95, 1.1), "nieve": (0.9, 0.97, 1.1),
                   "fuego": (1.1, 0.92, 0.8), "noche": (0.85, 0.92, 1.1), "oro": (1.08, 1.0, 0.82),
                   "vela": (1.08, 0.96, 0.8), "mapa": (1.02, 0.98, 0.9), "tormenta": (0.9, 0.95, 1.05),
                   "desierto": (1.08, 1.0, 0.85)}.get(tono, (1.03, 0.99, 0.92))
            self.grade[tono] = (self.vineta[..., None] * np.array(col, np.float32) * 256).astype(np.uint32)
        return self.grade[tono]

    def escena(self, i):
        if i not in self.cache:
            if len(self.cache) > 3:
                self.cache.pop(min(self.cache))
            d = ES.preparar(self.clips[i]["spec"])
            d["rng"] = np.random.default_rng(1000 + i)
            d["parts"] = self._particulas(d.get("particulas"), d["rng"])
            self.cache[i] = d
        return self.cache[i]

    def _particulas(self, tipo, rng):
        if not tipo:
            return None
        n = {"nieve": 260, "brasas": 90, "brasas_fuerte": 220, "polvo": 70, "chispas": 60, "lluvia": 300,
             "gaviotas": 5, "petalos": 24, "luciernagas": 40}[tipo]
        return {"tipo": tipo, "x": rng.random(n) * W, "y": rng.random(n) * H, "v": rng.uniform(0.5, 1.5, n),
                "s": rng.uniform(0.6, 1.4, n), "f": rng.random(n) * 6.28}

    # ---------------------------------------------------------- cámara
    def camara(self, clip, d, tl, i, sacudida):
        u = suave(tl / max(clip["dur"], 0.1))
        z0, z1 = d.get("zoom") or ((1.0, 1.1) if i % 2 == 0 else (1.1, 1.0))
        z = z0 + (z1 - z0) * u
        pan = d.get("pan") or ((0.025, 0.0) if i % 3 == 0 else (-0.025, 0.0) if i % 3 == 1 else (0.0, -0.02))
        return z, pan, u, sacudida

    def caja(self, z, pan, u, p, sac, extra=(0, 0)):
        zz = 1 + (z - 1) * p
        vw, vh = W / zz, H / zz
        cx = ES.LW / 2 + pan[0] * ES.LW * (u - 0.5) * 2 * p + sac[0] * p + extra[0]
        cy = ES.LH / 2 + pan[1] * ES.LH * (u - 0.5) * 2 * p + sac[1] * p + extra[1]
        cx = min(max(cx, vw / 2), ES.LW - vw / 2)
        cy = min(max(cy, vh / 2), ES.LH - vh / 2)
        return (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)

    @staticmethod
    def a_pantalla(caja, x, y):
        x0, y0, x1, y1 = caja
        return ((x - x0) * W / (x1 - x0), (y - y0) * H / (y1 - y0))

    # ---------------------------------------------------------- un clip
    def dibujar(self, i, tl):
        clip = self.clips[i]
        d = self.escena(i)
        rng_s = np.random.default_rng(int(tl * FPS) * 7 + i)
        sac = (0.0, 0.0)
        fogonazos = []
        for tc, tipo, fuerza in clip["cues"]:
            edad = tl - tc
            if 0 <= edad < 0.5:
                fogonazos.append((tc, tipo, fuerza, edad))
                if tipo in ("canon", "impacto") and edad < 0.4:
                    amp = 14 * fuerza * (1 - edad / 0.4)
                    sac = (rng_s.uniform(-amp, amp), rng_s.uniform(-amp, amp))
        z, pan, u, sac = self.camara(clip, d, tl, i, sac)
        es_mapa = clip["spec"]["tipo"] == "mapa"
        caja_fondo = self.caja(z, pan, u, 1.0 if es_mapa else 0.15, sac)
        frame = d["fondo"].transform((W, H), Image.EXTENT, caja_fondo, Image.BILINEAR)
        caja_frente = self.caja(z, pan, u, 1.0, sac)
        for k, (capa, p) in enumerate(d["capas"]):
            extra = (0, 0)
            if capa.info.get("deriva"):
                extra = (80 * math.sin(tl * 2 * math.pi / 40 + i), 0)
            if d.get("barco_mov") and p == 1.0:
                extra = (25 * math.sin(tl * 0.2), 6 * math.sin(tl * 1.3))
            if d.get("flotar") == k:
                extra = (0, 10 * math.sin(tl * 1.1))
            caja_c = self.caja(z, pan, u, p, sac, extra)
            if capa.info.get("desfile"):
                x0 = 171 - (tl * 55) % capa.info["desfile"] + sac[0]
                y0 = (ES.LH - H) / 2 + 5 * abs(math.sin(tl * 5.5)) + sac[1]
                caja_c = (x0, y0, x0 + W, y0 + H)
            capa_t = capa.transform((W, H), Image.EXTENT, caja_c, Image.BILINEAR)
            frame.paste(capa_t, (0, 0), capa_t)
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dib = ImageDraw.Draw(capa)
        self._efectos(d, dib, capa, tl, caja_frente, clip, fogonazos, u)
        frame = frame.convert("RGBA")
        frame.alpha_composite(capa)
        arr = np.asarray(frame.convert("RGB"))
        brillo = 0
        for tc, tipo, fuerza, edad in fogonazos:
            if tipo in ("canon", "impacto") and edad < 0.25:
                brillo += int(38 * fuerza * (1 - edad / 0.25))
        return arr, d.get("tono", "calido"), brillo

    def _efectos(self, d, dib, capa, tl, caja, clip, fogonazos, u):
        # partículas
        pt = d.get("parts")
        if pt:
            tipo = pt["tipo"]
            x, y, v, s, f = pt["x"], pt["y"], pt["v"], pt["s"], pt["f"]
            if tipo == "nieve":
                px = (x + np.sin(tl * 0.8 + f) * 30 + tl * 40 * v) % W
                py = (y + tl * 110 * v) % H
                for a, b, r in zip(px, py, s * 3.2):
                    dib.ellipse([a - r, b - r, a + r, b + r], fill=(245, 248, 255, 210))
            elif tipo in ("brasas", "brasas_fuerte"):
                px = (x + np.sin(tl * 1.5 + f) * 25) % W
                py = (y - tl * 70 * v) % H
                for a, b, r, ff in zip(px, py, s * 2.6, f):
                    al = int(150 + 100 * math.sin(tl * 8 + ff))
                    dib.ellipse([a - r, b - r, a + r, b + r], fill=(255, 150 + int(60 * math.sin(ff)), 50, al))
            elif tipo == "polvo":
                px = (x + tl * 12 * v) % W
                py = (y + np.sin(tl * 0.5 + f) * 20) % H
                for a, b, r in zip(px, py, s * 1.6):
                    dib.ellipse([a - r, b - r, a + r, b + r], fill=(255, 235, 200, 70))
            elif tipo in ("chispas", "luciernagas"):
                for a, b, r, ff in zip(x, y, s, f):
                    al = max(0.0, math.sin(tl * 2 + ff * 3))
                    if al > 0.05:
                        rr = r * (3 if tipo == "chispas" else 4)
                        b2 = (b - tl * 10) % H
                        dib.ellipse([a - rr, b2 - rr, a + rr, b2 + rr], fill=(255, 225, 140, int(220 * al)))
            elif tipo == "lluvia":
                px = (x - tl * 300 * v) % W
                py = (y + tl * 1400 * v) % H
                for a, b in zip(px, py):
                    dib.line([(a, b), (a - 8, b + 30)], fill=(200, 210, 230, 90), width=2)
            elif tipo == "petalos":
                px = (x + np.sin(tl * 0.7 + f) * 60) % W
                py = (y + tl * 45 * v) % H
                for a, b, r, ff in zip(px, py, s, f):
                    w_ = 10 * r * abs(math.sin(tl * 2 + ff)) + 3
                    dib.ellipse([a - w_, b - 6 * r, a + w_, b + 6 * r], fill=(170, 20, 40, 220))
            elif tipo == "gaviotas":
                for a, b, r, ff in zip(x, y * 0.4, s, f):
                    a = (a + tl * 60 * r) % (W + 200) - 100
                    ala = 12 * math.sin(tl * 6 + ff)
                    dib.line([(a - 22 * r, b - ala), (a, b), (a + 22 * r, b - ala)], fill=(30, 25, 30, 200), width=3)
        # vela
        if d.get("vela"):
            vx, vy = self.a_pantalla(caja, *d["vela"])
            parpadeo = 1 + 0.12 * math.sin(tl * 13) + 0.08 * math.sin(tl * 29)
            g = self.sprite.resize((int(420 * parpadeo), int(420 * parpadeo)))
            capa.alpha_composite(g, (int(vx - g.width / 2), int(vy - g.height / 2)))
            dib.ellipse([vx - 9, vy - 28 * parpadeo, vx + 9, vy + 6], fill=(255, 240, 190, 255))
        # fuego de Moscú
        if d.get("fuego"):
            for k in range(6):
                fx = W * (0.1 + k * 0.16) + 30 * math.sin(tl * 2 + k)
                tam = int(600 + 120 * math.sin(tl * 5 + k * 2))
                g = self.sprite_rojo.resize((tam, tam))
                capa.alpha_composite(g, (int(fx - tam / 2), int(H * 0.72 - tam / 2)))
        # rutas del mapa
        for r in d.get("rutas", []):
            prog = min(max((u - r["ini"]) / max(r["fin"] - r["ini"], 0.01), 0), 1)
            if prog <= 0:
                continue
            pts = [self.a_pantalla(caja, *p) for p in r["pts"]]
            largos = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
            objetivo = sum(largos) * prog
            dibujados = [pts[0]]
            for (a, b), l in zip(zip(pts, pts[1:]), largos):
                if objetivo >= l:
                    dibujados.append(b)
                    objetivo -= l
                else:
                    k = objetivo / l if l else 0
                    dibujados.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
                    break
            dib.line(dibujados, fill=(40, 20, 10, 200), width=14, joint="curve")
            dib.line(dibujados, fill=tuple(r["color"]) + (255,), width=8, joint="curve")
            if len(dibujados) > 1:
                (ax, ay), (bx, by) = dibujados[-2], dibujados[-1]
                ang = math.atan2(by - ay, bx - ax)
                tip = [(bx + math.cos(ang) * 26, by + math.sin(ang) * 26),
                       (bx + math.cos(ang + 2.4) * 22, by + math.sin(ang + 2.4) * 22),
                       (bx + math.cos(ang - 2.4) * 22, by + math.sin(ang - 2.4) * 22)]
                dib.polygon(tip, fill=tuple(r["color"]) + (255,))
        # batallas en el mapa: pulsos constantes + explosión con cada cañonazo
        exps = d.get("explosiones", [])
        for k, (ex, ey) in enumerate(exps):
            sx, sy = self.a_pantalla(caja, ex, ey)
            fase = (tl * 0.8 + k * 0.37) % 1
            if u > 0.2:
                r = 20 + fase * 60
                dib.ellipse([sx - r, sy - r, sx + r, sy + r], outline=(190, 30, 20, int(220 * (1 - fase))), width=5)
                dib.line([(sx - 16, sy - 16), (sx + 16, sy + 16)], fill=(150, 20, 15, 255), width=7)
                dib.line([(sx + 16, sy - 16), (sx - 16, sy + 16)], fill=(150, 20, 15, 255), width=7)
        # fogonazos sincronizados con los disparos
        bocas = d.get("bocas") or []
        for tc, tipo, fuerza, edad in fogonazos:
            if edad > 0.3:
                continue
            k = int(tc * 1000) % 997
            if exps:
                bx, by = exps[k % len(exps)]
                escala = 1.0
            elif bocas:
                bx, by, escala = bocas[k % len(bocas)]
                if tipo == "disparo":
                    bx, by = bx + (k % 7 - 3) * 160, by + 40 - (k % 5) * 30
                    escala *= 0.35
            else:
                if tipo != "impacto":
                    continue
                bx, by, escala = ES.LW / 2, ES.LH / 2, 3.0
            sx, sy = self.a_pantalla(caja, bx, by)
            vida = 1 - edad / 0.3
            tam = int(max(8, 380 * escala * fuerza * (0.6 + 0.4 * vida)))
            g = (self.sprite if tipo != "canon" else self.sprite_rojo).resize((tam, tam))
            if vida < 1:
                g.putalpha(g.split()[3].point(lambda a, v=vida: int(a * v)))
            capa.alpha_composite(g, (int(sx - tam / 2), int(sy - tam / 2)))
            if tipo != "impacto":
                rr = tam * 0.12
                dib.ellipse([sx - rr, sy - rr * 0.6, sx + rr, sy + rr * 0.6], fill=(255, 250, 220, int(255 * vida)))

    # ---------------------------------------------------------- textos encima
    def textos(self, frame, T):
        clip_i = max(0, bisect.bisect_right(self.inicios, T) - 1)
        clip = self.clips[clip_i]
        tl = T - clip["ini"]
        # fecha
        if clip.get("fecha"):
            t0, anio = clip["fecha"]
            edad = tl - t0
            if 0.3 < edad < 6.5:
                al = min(1, (edad - 0.3) / 0.5, (6.5 - edad) / 0.6)
                im = self.cache_txt.setdefault(("f", anio), self._texto_img(anio, ("titulo", 78), (245, 205, 120, 255), 2))
                self._pegar(frame, im, 70, 60, al)
                barra = self.cache_txt.setdefault("barra", Image.new("RGBA", (180, 4), (230, 190, 100, 255)))
                self._pegar(frame, barra, 72, 60 + im.height + 6, al)
        # rótulos con nombres
        for t0, nombre, rol in self.tl["rotulos"]:
            edad = T - t0
            if 0 < edad < 5.5:
                al = min(1, edad / 0.4, (5.5 - edad) / 0.5)
                a = self.cache_txt.setdefault(("rn", nombre), self._texto_img(nombre.upper(), ("titulo", 46), (245, 210, 130, 255), 2))
                b = self.cache_txt.setdefault(("rr", nombre), self._texto_img(rol, ("texto", 36), (235, 228, 210, 255), 2))
                desliz = int(40 * (1 - min(1, edad / 0.4)))
                fondo = self.cache_txt.setdefault(("rf", nombre), Image.new("RGBA", (max(a.width, b.width) + 60, a.height + b.height + 34), (10, 6, 4, 170)))
                self._pegar(frame, fondo, 50 - desliz, 520, al)
                self._pegar(frame, Image.new("RGBA", (6, fondo.height), (230, 185, 90, 255)), 50 - desliz, 520, al)
                self._pegar(frame, a, 80 - desliz, 532, al)
                self._pegar(frame, b, 80 - desliz, 538 + a.height, al)
        # subtítulos
        j = bisect.bisect_right(self.sub_ini, T) - 1
        if j >= 0 and self.subs[j][0] <= T < self.subs[j][1] + 0.15:
            t0, t1, texto = self.subs[j]
            trozos = trocear(texto)
            pesos = np.cumsum([len(x) for x in trozos]) / sum(len(x) for x in trozos)
            k = int(np.searchsorted(pesos, (T - t0) / max(t1 - t0, 0.01)))
            k = min(k, len(trozos) - 1)
            clave = ("s", j, k)
            if clave not in self.cache_txt:
                self.cache_txt = {kk: vv for kk, vv in self.cache_txt.items() if kk[0] != "s"} if len(self.cache_txt) > 400 else self.cache_txt
                self.cache_txt[clave] = self._subtitulo(trozos[k])
            im = self.cache_txt[clave]
            self._pegar(frame, im, (W - im.width) // 2, H - im.height - 46, 1.0)
        self._pegar(frame, self.marca, W - self.marca.width - 40, 34, 1.0)

    def _subtitulo(self, texto):
        fnt = ES.fuente("texto", 50)
        lineas = ES.partir(texto, 52)
        anchos = [fnt.getlength(l) for l in lineas]
        alto_l = 62
        im = Image.new("RGBA", (int(max(anchos)) + 70, alto_l * len(lineas) + 30), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.rounded_rectangle([0, 0, im.width - 1, im.height - 1], 14, fill=(0, 0, 0, 140))
        for i, l in enumerate(lineas):
            dd.text((im.width / 2, 15 + alto_l * i + alto_l / 2), l, font=fnt, fill=(255, 250, 240, 255), anchor="mm",
                    stroke_width=2, stroke_fill=(0, 0, 0, 255))
        return im

    @staticmethod
    def _pegar(frame, im, x, y, alfa):
        if alfa < 1:
            im = im.copy()
            im.putalpha(im.split()[3].point(lambda a: int(a * alfa)))
        frame.paste(im, (int(x), int(y)), im)

    # ---------------------------------------------------------- cuadro final
    def cuadro(self, n):
        T = n / FPS
        i = max(0, bisect.bisect_right(self.inicios, T) - 1)
        clip = self.clips[i]
        tl = T - clip["ini"]
        arr, tono, brillo = self.dibujar(i, tl)
        # fundido con la escena anterior
        if i > 0 and tl < XF:
            prev = self.clips[i - 1]
            arr2, tono2, b2 = self.dibujar(i - 1, T - prev["ini"])
            k = suave(tl / XF)
            arr = (arr.astype(np.float32) * k + arr2.astype(np.float32) * (1 - k)).astype(np.uint8)
        # fundido de entrada/salida a negro al principio y al final
        g = self._grade(tono)
        out = (arr.astype(np.uint32) * g >> 8).astype(np.int16)
        out += self.grano[(n // 2) % 3]
        if brillo:
            out += brillo
        parpadeo = 1 + 0.012 * math.sin(T * 17) * math.sin(T * 3.1)
        if T < 0.8:
            parpadeo *= T / 0.8
        if T > self.tl["total"] - 2.0:
            parpadeo *= max(0, (self.tl["total"] - T) / 2.0)
        if parpadeo != 1:
            out = (out * parpadeo).astype(np.int16)
        frame = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        self.textos(frame, T)
        return frame.tobytes()


def trocear(texto, maximo=104):
    """Divide una frase larga en trozos de hasta dos líneas para los subtítulos."""
    if len(texto) <= maximo:
        return [texto]
    palabras = texto.split()
    trozos, actual = [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > maximo and actual:
            trozos.append(actual)
            actual = p
        else:
            actual = (actual + " " + p).strip()
    trozos.append(actual)
    if len(trozos) > 1 and len(trozos[-1]) < 25:
        ultimo = trozos.pop()
        trozos[-1] += " " + ultimo
    return trozos


def trabajador(tl, f0, f1, ruta, idx):
    r = Render(tl)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "faster", "-crf", "23", "-tune", "film", "-threads", "2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 4), str(ruta)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(f0, f1):
        p.stdin.write(r.cuadro(n))
        if (n - f0) % 480 == 0:
            hecho = (n - f0) / max(1, f1 - f0)
            print(f"[proceso {idx}] {hecho * 100:5.1f}%  ({(time.time() - t0) / 60:.1f} min)", flush=True)
    p.stdin.close()
    p.wait()
    print(f"[proceso {idx}] terminado en {(time.time() - t0) / 60:.1f} min", flush=True)


def hms(t):
    t = int(t)
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def srt_tiempo(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# =================================================================== principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--modelos", default=None)
    ap.add_argument("--prueba", nargs=2, type=float)
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--sin-audio", action="store_true")
    a = ap.parse_args()
    salida = Path(a.salida)
    voz = json.loads((salida / "voz.json").read_text())
    tl = construir(voz)
    print(f"Duración total: {tl['total'] / 60:.1f} min · {len(tl['clips'])} escenas · {len(tl['efectos'])} efectos")

    # subtítulos .srt y descripción con capítulos para YouTube
    with open(salida / "napoleon.srt", "w", encoding="utf-8") as f:
        k = 1
        for t0, t1, texto in tl["subs"]:
            trozos = trocear(texto)
            pesos = np.concatenate([[0], np.cumsum([len(x) for x in trozos]) / sum(len(x) for x in trozos)])
            for j, tr in enumerate(trozos):
                f.write(f"{k}\n{srt_tiempo(t0 + (t1 - t0) * pesos[j])} --> {srt_tiempo(t0 + (t1 - t0) * pesos[j + 1])}\n{tr}\n\n")
                k += 1
    with open(salida / "capitulos.txt", "w", encoding="utf-8") as f:
        f.write("0:00 Apertura\n")
        for t0, et, titulo in tl["capitulos"]:
            nombre = titulo.capitalize() if et in ("", "INTRODUCCIÓN", "FINAL") else f"Cap. {et.split()[-1]} · {titulo.capitalize()}"
            f.write(f"{hms(t0)} {nombre}\n")

    if not a.sin_audio and not a.prueba:
        print("Mezclando audio...", flush=True)
        mezclar(tl, salida, Path(a.modelos) if a.modelos else None)

    f_ini, f_fin = 0, int(tl["total"] * FPS)
    if a.prueba:
        f_ini = int(a.prueba[0] * FPS)
        f_fin = f_ini + int(a.prueba[1] * FPS)
    partes = []
    cortes = np.linspace(f_ini, f_fin, a.procesos + 1).astype(int)
    procesos = []
    for k in range(a.procesos):
        ruta = salida / f"parte{k}.mp4"
        partes.append(ruta)
        pr = Process(target=trabajador, args=(tl, cortes[k], cortes[k + 1], ruta, k))
        pr.start()
        procesos.append(pr)
    for pr in procesos:
        pr.join()
    lista = salida / "partes.txt"
    lista.write_text("".join(f"file '{p.name}'\n" for p in partes))
    video = salida / ("prueba.mp4" if a.prueba else "video_sin_audio.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(video)], check=True)
    if a.prueba:
        audio = salida / "audio_final.wav"
        if audio.exists():
            con = salida / "prueba_con_audio.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-ss", str(a.prueba[0]),
                            "-t", str(a.prueba[1]), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", str(con)], check=True)
        print("Prueba lista:", video)
        return
    final = salida / "Napoleon_Bonaparte_documental.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(salida / "audio_final.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(final)], check=True)
    print("VIDEO TERMINADO:", final)


if __name__ == "__main__":
    main()
