"""Banda sonora épica: tambores de guerra, cuerdas, coro, golpes en los cortes y la voz encima.

Reutiliza los sintetizadores de ../napoleon/sonido.py. Uso: python3 audio.py
Crea salida/mezcla.wav (estéreo, 44,1 kHz).
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage

AQUI = Path(__file__).parent
sys.path.append(str(AQUI.parent / "napoleon"))
import sonido as s  # noqa: E402

from escenas import PLANOS  # noqa: E402
from guion import DURACION, INICIO_VOZ  # noqa: E402

SR = s.SR
N = s.seg(DURACION)
BPM = 84
NEGRA = 60 / BPM
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


def tambor_guerra(nota=55.0, largo=1.4):
    """Tambor grande (estilo taiko): golpe grave con cuerpo y piel."""
    n = s.seg(largo)
    t = np.arange(n) / SR
    f = nota * (1 + 0.6 * np.exp(-t * 25))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * s.env_exp(n, 0.32)
    x += s.lp(s.ruido(n), 900) * s.env_exp(n, 0.05) * 0.9
    return s.reverb(s.estereo(np.tanh(x * 1.8) * 0.8), 2.5, 0.35)


def coro(freqs, dur):
    """Coro «aah»: sierras filtradas por formantes de la vocal a."""
    n = s.seg(dur)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for f in freqs:
        for det in (-0.08, 0.0, 0.08):
            ff = f * 2 ** (det / 12) * (1 + 0.004 * np.sin(2 * np.pi * 5 * t + det * 40))
            out += np.sign(np.sin(2 * np.pi * np.cumsum(ff) / SR)) * 0.2
    voz = s.bp(out, 650, 1100) + s.bp(out, 1000, 1400) * 0.6 + s.bp(out, 2500, 3000) * 0.2
    env = np.minimum(1, t / 1.2) * np.clip((dur - t) / 1.2, 0, 1)
    return s.estereo(voz * env * 0.25)


def golpe_metal():
    """Choque de espadas."""
    n = s.seg(1.6)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t) * s.env_exp(n, 0.25 + 0.1 * k) for k, f in enumerate([1750, 2630, 3810, 5120]))
    x = x * 0.3 + s.hp(s.ruido(n), 3000) * s.env_exp(n, 0.015) * 0.9
    return s.reverb(s.estereo(s.normal(x, 0.6)), 1.5, 0.3)


def musica():
    m = np.zeros((N + s.seg(8), 2), np.float32)
    prog = [("D", 1), ("A#", 0), ("F", 0), ("C", 0), ("D", 1), ("G", 1), ("A#", 0), ("A", 0)]
    compas = 4 * NEGRA
    t, i = 0.0, 0
    while t < DURACION:
        raiz, menor = prog[i % len(prog)]
        fr = s.acorde(raiz, menor)
        poner(m, s.cuerdas(fr, 2 * compas + 1.5, 1700), t, 1.5)
        if t > 9:
            poner(m, coro([fr[2], fr[3], fr[4]], 2 * compas + 1.0), t, 0.7)
        if t > INI["p_destruccion"] and i % 2 == 0:
            poner(m, s.metales([fr[1], fr[2], fr[4]], 2 * compas), t, 0.9)
        t += 2 * compas
        i += 1
    # tambores de guerra: entran con los castillos, crecen en las batallas, se calman en el final
    t = INI["p_schinkel"]
    b = 0
    patron = [1.0, 0, 0.5, 0, 0.8, 0, 0.5, 0.6]       # corcheas
    while t < INI["p_mil_anios"] + 2 * compas:
        v = patron[b % 8]
        fuerte = 1.4 if INI["p_torneo"] <= t < INI["p_ciudad"] else 1.0
        if v:
            poner(m, tambor_guerra(52 if b % 8 == 0 else 70), t, 0.55 * v * fuerte)
        t += NEGRA / 2
        b += 1
    a, z = s.seg(INI["p_ciudad"]), s.seg(INI["p_mil_anios"])
    m[a:z] *= 0.8
    return m[:N]


def efectos():
    e = np.zeros((N + s.seg(8), 2), np.float32)
    poner(e, s.impacto(), 0.0, 1.0)
    poner(e, s.viento(3.6, 1.0), 0.0, 0.7)
    for c in CORTES:
        poner(e, s.whoosh(0.6, True), c - 0.4, 0.5)
    v = INI["p_vela"]
    poner(e, s.fuego(5.7, 0.4), v, 0.6)
    for k in (1.4, 3.6, 4.7):                                     # tachones
        poner(e, s.impacto()[: s.seg(1.2)] * 0.5, v + k, 0.5)
    poner(e, s.timbal(49), INI["p_schinkel"], 0.8)
    poner(e, s.campana(98, 6), INI["p_carlomagno"], 0.35)
    poner(e, s.caballos(3.2), INI["p_godspeed"], 0.7)
    poner(e, s.impacto(), INI["p_bienvenidos"], 0.9)
    poner(e, s.fuego(8.7, 1.0), INI["p_destruccion"], 0.6)
    poner(e, s.pluma(1.6), INI["p_linea_tiempo"] + 0.1, 0.8)
    poner(e, s.timbal(55), INI["p_piramide"], 0.6)
    poner(e, s.campana(147, 5), INI["p_enero"], 0.3)
    poner(e, s.viento(4.2, 0.6), INI["p_junio"], 0.5)
    poner(e, s.timbal(49), INI["p_octubre"], 0.7)
    poner(e, s.caballos(2.4), INI["p_torneo"], 0.8)
    poner(e, golpe_metal(), INI["p_torneo"] + 1.0, 0.8)
    poner(e, s.batalla(4.2, 0.8), INI["p_san_romano"], 0.55)
    poner(e, golpe_metal(), INI["p_san_romano"] + 0.2, 0.9)
    poner(e, golpe_metal(), INI["p_san_romano"] + 1.6, 0.6)
    poner(e, s.campana(196, 6), INI["p_universidad"], 0.35)
    poner(e, s.campana(131, 7), INI["p_catedral"], 0.45)
    poner(e, s.impacto(), INI["p_mil_anios"] + 2.6, 0.8)
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
    env = ndimage.uniform_filter1d(np.abs(v), s.seg(0.25))
    env = np.clip(env / (env.max() * 0.35), 0, 1)
    env = ndimage.uniform_filter1d(env, s.seg(0.3))
    gan = 0.34 - 0.2 * env                      # la música baja cuando habla el narrador
    total = m * gan[:, None] + e * 0.4 + np.stack([v, v], 1)
    fade = s.seg(1.5)
    total[-fade:] *= np.linspace(1, 0, fade)[:, None]
    total = np.tanh(total / 1.05)
    sf.write(AQUI / "salida" / "mezcla.wav", total, SR)
    print("mezcla lista:", total.shape[0] / SR, "s")


if __name__ == "__main__":
    mezclar()
