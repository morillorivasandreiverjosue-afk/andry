"""Banda sonora: beat oscuro estilo TikTok, efectos en cada corte y la voz por encima.

Reutiliza los sintetizadores de ../napoleon/sonido.py. Uso: python3 audio.py
Crea salida/mezcla.wav (60 s, estéreo, 44,1 kHz).
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage

AQUI = Path(__file__).parent
sys.path.append(str(AQUI.parent / "napoleon"))
import sonido as s  # noqa: E402

from guion import DURACION, INICIO_VOZ  # noqa: E402

SR = s.SR
N = s.seg(DURACION)
BPM = 96
NEGRA = 60 / BPM
from escenas import PLANOS  # noqa: E402

INI = {f.__name__: t for t, f, _ in PLANOS}
CORTES = [t for t, _, _ in PLANOS[1:]]


def st(x):
    return s.estereo(x) if x.ndim == 1 else x


def poner(pista, x, t, vol=1.0):
    k = s.seg(t)
    x = st(x)
    if k >= len(pista):
        return
    n = min(len(x), len(pista) - k)
    pista[k: k + n] += x[:n] * vol


def bombo():
    n = s.seg(0.6)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * s.env_exp(n, 0.22)
    x += s.hp(s.ruido(n), 3000) * s.env_exp(n, 0.004) * 0.3
    return np.tanh(x * 1.6) * 0.8


def palmada():
    n = s.seg(0.35)
    x = s.bp(s.ruido(n), 900, 5000) * s.env_exp(n, 0.06)
    return s.reverb(s.estereo(s.normal(x, 0.5)), 1.2, 0.3)


def charles(abierto=False):
    n = s.seg(0.25 if abierto else 0.06)
    return s.hp(s.ruido(n), 7000) * s.env_exp(n, 0.08 if abierto else 0.012) * 0.25


def sub(f, dur):
    n = s.seg(dur)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.01) * np.clip((dur - t) / 0.08, 0, 1)
    return np.tanh(x * 1.4) * 0.55


def musica():
    m = np.zeros((N + s.seg(6), 2), np.float32)
    prog = [("D", 1), ("A#", 0), ("G", 1), ("A", 0)]
    compas = 4 * NEGRA
    t, i = 0.0, 0
    while t < DURACION:
        raiz, menor = prog[i % 4]
        fr = s.acorde(raiz, menor)
        poner(m, s.cuerdas(fr, 2 * compas + 1.5, 1300), t, 1.4)
        t += 2 * compas
        i += 1
    # ritmo: entra con el segundo plano y se corta en el desenlace
    b = 0
    t = 3.6
    raices = {0: "D", 1: "A#", 2: "G", 3: "A"}
    while t < INI["p_desenlace"]:
        en_compas = b % 8                     # corcheas
        if en_compas in (0, 3, 6) or (en_compas == 5 and b % 32 > 24):
            poner(m, bombo(), t, 0.9)
            idx = int(t / (2 * compas)) % 4
            poner(m, sub(s.hz(raices[idx], 1), NEGRA * 1.4), t, 0.8)
        if en_compas in (2, 6) and t > 7.2:
            poner(m, palmada(), t, 0.55)
        if t > 9.8:
            poner(m, charles(en_compas == 7), t, 0.6 if b % 2 else 0.35)
        t += NEGRA / 2
        b += 1
    # parte antigua (1899–1966): más suave, sin palmas → se quita aplicando un filtro de paso bajo
    a, z = s.seg(INI["p_tribunal"]), s.seg(INI["p_posiciones"])
    m[a:z] = s.lp(m[a:z], 900) * 1.3
    return m[:N]


def efectos():
    e = np.zeros((N + s.seg(6), 2), np.float32)
    poner(e, s.impacto(), 0.0, 0.9)
    for c in CORTES:
        poner(e, s.whoosh(0.5, True), c - 0.35, 0.55)
    # subida antes de 1899
    n = s.seg(1.6)
    r = s.bp(s.ruido(n), 400, 6000) * np.linspace(0, 1, n) ** 2
    poner(e, s.reverb(s.estereo(r * 0.5), 1.5, 0.3), INI["p_tribunal"] - 1.6, 0.6)
    poner(e, s.timbal(55), INI["p_tribunal"], 0.7)
    # reloj en el contador de años
    for k in range(13):
        n = s.seg(0.03)
        poner(e, s.hp(s.ruido(n), 3000) * s.env_exp(n, 0.006), INI["p_anios"] + k * 0.2, 0.6)
    poner(e, s.impacto(), INI["p_nulo"] + 1.4, 0.8)                 # sello «nulo e írrito»
    poner(e, s.pluma(1.8), INI["p_ginebra"] + 0.6, 0.9)                # firma del acuerdo
    poner(e, s.olas(3.6, 1.2), INI["p_petroleo"], 0.9)
    poner(e, s.fuego(3.5, 0.8), INI["p_petroleo"], 0.5)
    poner(e, s.timbal(49), INI["p_cij"], 0.6)
    poner(e, s.latido(3.2, 70), INI["p_desenlace"], 1.0)
    poner(e, s.impacto(), INI["p_final"], 1.0)
    return e[:N]


def voz():
    v, sr = sf.read(AQUI / "salida" / "voz_tiktok.wav")
    assert sr == SR
    v = v.astype(np.float32)
    v = v / np.abs(v).max() * 0.9
    out = np.zeros(N, np.float32)
    k = s.seg(INICIO_VOZ)
    out[k: k + len(v)] = v[: N - k]
    return out


def mezclar():
    v = voz()
    m = musica()
    e = efectos()
    # la música baja cuando habla el narrador
    env = ndimage.uniform_filter1d(np.abs(v), s.seg(0.25))
    env = np.clip(env / (env.max() * 0.35), 0, 1)
    env = ndimage.uniform_filter1d(env, s.seg(0.3))
    gan = 0.32 - 0.18 * env
    total = m * gan[:, None] + e * 0.45 + np.stack([v, v], 1)
    fade = s.seg(1.2)
    total[-fade:] *= np.linspace(1, 0, fade)[:, None]
    total = np.tanh(total / 1.05) * 1.0
    sf.write(AQUI / "salida" / "mezcla.wav", total, SR)
    print("mezcla lista:", total.shape[0] / SR, "s")


if __name__ == "__main__":
    mezclar()
