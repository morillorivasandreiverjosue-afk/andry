"""Compone 5 pistas de fondo originales (sin derechos de autor) de 72 s en public/musica/.

Uso: python3 scripts/generar-musica.py      (requiere numpy y scipy)
Cada pista hace un "corte" de silencio justo antes de los golpes del video
(truco viral: la música se calla y vuelve con el impacto).
"""
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
DUR = 72.0
SALIDA = Path(__file__).resolve().parent.parent / "public" / "musica"
SALIDA.mkdir(parents=True, exist_ok=True)
GOLPES = [17.2, 43.0, 55.0, 67.2]
rng = np.random.default_rng(3)


def t(seg):
    return np.arange(int(SR * seg)) / SR


def env(n, ataque=0.003, caida=0.2):
    e = np.exp(-np.arange(n) / (SR * caida))
    a = max(1, int(SR * ataque))
    e[:a] *= np.linspace(0, 1, a)
    return e


def filtro(x, corte, tipo="low", orden=2):
    w = np.clip(np.asarray(corte, dtype=float) / (SR / 2), 1e-4, 0.99)
    b, a = butter(orden, w if w.ndim else float(w), btype=tipo)
    return lfilter(b, a, x)


def nota(n):
    """Número MIDI a Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


class Pista:
    def __init__(self, bpm):
        self.bpm = bpm
        self.beat = 60 / bpm
        self.l = np.zeros(int(SR * DUR))
        self.r = np.zeros(int(SR * DUR))

    def poner(self, x, seg, vol=1.0, pan=0.0):
        i = int(seg * SR)
        if i >= len(self.l):
            return
        j = min(len(self.l), i + len(x))
        self.l[i:j] += x[: j - i] * vol * (1 - max(0, pan))
        self.r[i:j] += x[: j - i] * vol * (1 + min(0, pan))

    def beats(self):
        return range(int(DUR / self.beat))

    def guardar(self, nombre):
        # Cortes de silencio antes de cada golpe + entrada y salida suaves
        g = np.ones(len(self.l))
        for s in GOLPES:
            a, b = int((s - 0.45) * SR), int(s * SR)
            g[a:b] = 0.03
        g[: int(SR * 0.3)] *= np.linspace(0, 1, int(SR * 0.3))
        g[-int(SR * 2.5):] *= np.linspace(1, 0, int(SR * 2.5))
        est = np.stack([self.l * g, self.r * g], axis=1)
        est = np.tanh(est * 1.3)
        est /= np.max(np.abs(est)) + 1e-9
        est *= 0.89
        with wave.open(str(SALIDA / nombre), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((est * 32767).astype(np.int16).tobytes())
        print("Lista:", nombre)


# ---------- Instrumentos ----------
def bombo(dur=0.4, f0=160, f1=48):
    tt = t(dur)
    fr = (f0 - f1) * np.exp(-tt * 30) + f1
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(len(tt), 0.001, 0.13)


def ochocientos(f, dur, desliz=None):
    """Bajo 808 distorsionado (con deslizamiento opcional hacia otra nota)."""
    tt = t(dur)
    fr = np.full(len(tt), f) if desliz is None else f * (desliz / f) ** np.clip(tt / 0.12, 0, 1)
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(len(tt), 0.002, dur * 0.6)
    return np.tanh(x * 3)


def palmas(dur=0.25):
    n = int(SR * dur)
    r = filtro(rng.standard_normal(n), [900, 4000], "band")
    e = env(n, 0.001, 0.06)
    for d in (0.008, 0.016):
        e[int(d * SR):] += 0.6 * env(n - int(d * SR), 0.001, 0.05)
    return r * e


def caja(dur=0.25):
    tt = t(dur)
    return 0.6 * filtro(rng.standard_normal(len(tt)), 1800, "high") * env(len(tt), 0.001, 0.07) + 0.5 * np.sin(2 * np.pi * 190 * tt) * env(len(tt), 0.001, 0.05)


def hihat(dur=0.05, caida=0.015):
    n = int(SR * dur)
    return filtro(rng.standard_normal(n), 7000, "high") * env(n, 0.0005, caida)


def cencerro(f=560, dur=0.35):
    """Cowbell del phonk/funk."""
    tt = t(dur)
    x = np.sign(np.sin(2 * np.pi * f * tt)) + np.sign(np.sin(2 * np.pi * f * 1.48 * tt))
    return filtro(x, [f * 0.8, f * 4], "band") * env(len(tt), 0.001, 0.12)


def pluck(f, dur=0.5, brillo=0.5):
    """Cuerda pulsada (Karplus-Strong): pizzicato, marimba suave."""
    n = int(SR * dur)
    p = max(2, int(SR / f))
    buf = filtro(rng.uniform(-1, 1, p), 2000 + 8000 * brillo)
    bloques = []
    for _ in range(n // p + 1):
        bloques.append(buf)
        buf = 0.996 * 0.5 * (buf + np.roll(buf, -1))
    out = np.concatenate(bloques)[:n]
    return out * env(n, 0.001, dur)


def sierra(f, dur, voces=3, corte=3000):
    tt = t(dur)
    x = sum(2 * ((tt * f * (1 + 0.006 * (v - 1))) % 1) - 1 for v in range(voces)) / voces
    return filtro(x, corte)


def acorde_pad(notas, dur, corte=1800):
    x = sum(sierra(nota(n), dur, 3, corte) for n in notas) / len(notas)
    a = int(SR * min(0.4, dur / 3))
    e = np.ones(len(x))
    e[:a] = np.linspace(0, 1, a)
    e[-a:] = np.linspace(1, 0, a)
    return x * e


def marimba(f, dur=0.4):
    tt = t(dur)
    return (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 4 * tt) * np.exp(-tt * 30)) * env(len(tt), 0.001, 0.18)


def campanita(f, dur=0.8):
    tt = t(dur)
    return sum(a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt * d) for m, a, d in [(1, 1, 4), (2.76, 0.4, 7), (5.4, 0.2, 12)])


# ========== 1. PHONK BRASILEÑO (130 BPM) ==========
p = Pista(130)
b = p.beat
mel = [69, 72, 74, 72, 76, 74, 72, 69, 67, 69, 72, 69, 74, 72, 69, 67]
raices = [45, 45, 41, 43]
for k in p.beats():
    s = k * b
    compas = k // 4
    if k % 4 in (0, 2) or (k % 8 == 7):
        p.poner(bombo(0.4, 180, 45), s, 1.0)
    if k % 4 in (1, 3):
        p.poner(palmas(), s, 0.6)
    for sub in range(4):
        p.poner(hihat(0.04, 0.01), s + sub * b / 4, 0.18 if sub % 2 else 0.28, 0.3)
    if k % 2 == 0:
        r = nota(raices[(compas // 2) % 4])
        p.poner(ochocientos(r, b * 2.05, r * (1.5 if k % 8 == 6 else 1)), s, 0.9)
    # cencerro melódico en corcheas
    for sub in range(2):
        idx = (k * 2 + sub) % 16
        if (k * 2 + sub) % 3 != 2:
            p.poner(cencerro(nota(mel[idx]), 0.3), s + sub * b / 2, 0.35, -0.2)
p.guardar("1-phonk.wav")

# ========== 2. REGGAETÓN / DEMBOW (96 BPM) ==========
p = Pista(96)
b = p.beat
prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
lead = [76, 74, 72, 74, 76, 79, 76, 74]
for k in p.beats():
    s = k * b
    compas = k // 4
    p.poner(bombo(0.35, 150, 50), s, 1.0)
    # patrón dembow: 3/16 y 2/4 dentro de cada tiempo
    p.poner(caja(), s + b * 0.75, 0.5)
    if k % 2 == 1:
        p.poner(caja(), s, 0.55)
        p.poner(caja(), s + b * 0.5, 0.35)
    for sub in range(2):
        p.poner(hihat(0.05, 0.02), s + sub * b / 2 + b / 4, 0.2, 0.4)
    if k % 4 == 0:
        ac = prog[compas % 4]
        p.poner(acorde_pad(ac, b * 4, 1400), s, 0.35)
        p.poner(ochocientos(nota(ac[0] - 24), b * 1.5), s, 0.7)
        p.poner(ochocientos(nota(ac[0] - 24), b * 1.2), s + b * 2.5, 0.6)
    if compas % 2 == 1:
        for sub in range(2):
            p.poner(pluck(nota(lead[(k * 2 + sub) % 8]), 0.35, 0.8), s + sub * b / 2, 0.35, 0.3)
p.guardar("2-reggaeton.wav")

# ========== 3. MISTERIO CURIOSO / PIZZICATO (110 BPM, estilo "storytime") ==========
p = Pista(110)
b = p.beat
linea = [57, None, 60, 64, 62, None, 60, 59, 57, None, 64, 62, 60, 59, 57, None]
bajo = [45, 45, 41, 40]
for k in p.beats():
    s = k * b
    compas = k // 4
    for sub in range(2):
        i = (k * 2 + sub) % 16
        sw = 0.08 * b if sub == 1 else 0  # swing
        if linea[i] is not None:
            p.poner(pluck(nota(linea[i]), 0.4, 0.3), s + sub * b / 2 + sw, 0.55, -0.25)
    if k % 2 == 0:
        p.poner(pluck(nota(bajo[(compas) % 4]), 0.6, 0.2), s, 0.7)
    p.poner(hihat(0.03, 0.008), s + b / 2 + 0.08 * b, 0.12, 0.5)
    if k % 4 == 2:
        p.poner(caja(0.15), s, 0.18)
    if k % 8 == 0 and compas >= 4:
        p.poner(campanita(nota(81 + (compas // 2) % 3 * 2)), s + b * 3.5, 0.15, 0.4)
p.guardar("3-misterio.wav")

# ========== 4. ELECTRO VIRAL / HYPERPOP (140 BPM) ==========
p = Pista(140)
b = p.beat
prog = [[64, 68, 71], [61, 64, 68], [57, 61, 64], [59, 63, 66]]
arpe = [0, 1, 2, 1, 2, 0, 2, 1]
for k in p.beats():
    s = k * b
    compas = k // 4
    p.poner(bombo(0.3, 200, 55), s, 1.0)
    if k % 2 == 1:
        p.poner(palmas(), s, 0.5)
    p.poner(hihat(0.05, 0.02), s + b / 2, 0.3, 0.3)
    ac = prog[(compas // 2) % 4]
    # bajo "sidechain" (bombea con el bombo)
    tb = t(b)
    bajo = sierra(nota(ac[0] - 24), b, 2, 600) * (1 - np.exp(-tb * 12))
    p.poner(bajo, s, 0.55)
    for sub in range(4):
        n = ac[arpe[(k * 4 + sub) % 8] % 3] + 12
        x = sierra(nota(n), b / 4, 2, 5000) * env(int(SR * b / 4), 0.002, 0.06)
        p.poner(x, s + sub * b / 4, 0.25, 0.35 if sub % 2 else -0.35)
    if k % 8 == 0:
        p.poner(acorde_pad([n + 12 for n in ac], b * 8, 2500), s, 0.18)
p.guardar("4-electro.wav")

# ========== 5. DOCUMENTAL ÉPICO / SUSPENSO (90 BPM) ==========
p = Pista(90)
b = p.beat
prog = [[45, 52, 57, 60], [41, 48, 53, 57], [43, 50, 55, 59], [40, 47, 52, 56]]
for k in p.beats():
    s = k * b
    compas = k // 4
    # tic-tac de reloj
    p.poner(hihat(0.03, 0.006) * 0.8 + 0.3 * cencerro(2000, 0.03), s, 0.25, 0.5 if k % 2 else -0.5)
    if k % 4 == 0:
        ac = prog[compas % 4]
        p.poner(acorde_pad(ac, b * 4, 900 + 300 * (compas % 4)), s, 0.45)
        p.poner(bombo(1.2, 90, 35) * 1.2, s, 0.9)
    if k % 4 == 2 and compas >= 2:
        p.poner(bombo(0.6, 120, 40), s, 0.6)
    if compas >= 4:
        for sub in range(2):
            n = prog[compas % 4][(k * 2 + sub) % 4] + 24
            p.poner(marimba(nota(n), 0.3), s + sub * b / 2, 0.18, 0.3)
p.guardar("5-documental.wav")
