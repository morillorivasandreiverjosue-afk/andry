"""Música de suspenso (sin miedo) y efectos espaciales, sintetizados con numpy: sin copyright.

Reutiliza las herramientas básicas de ../napoleon/sonido.py (filtros, reverb, cuerdas, piano).
Todo a 44100 Hz estéreo, arrays [n, 2] float32.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "napoleon"))
import sonido as B  # noqa: E402

SR = B.SR
seg, lp, hp, bp, ruido, estereo, reverb, normal, env_exp = (B.seg, B.lp, B.hp, B.bp, B.ruido, B.estereo,
                                                            B.reverb, B.normal, B.env_exp)
rng = np.random.default_rng(1969)


def hz(nota, octava):
    return B.hz(nota, octava)


def voicing(raiz, tipo):
    """Acordes abiertos y consonantes (sus2, add9, maj7): misterio sin miedo."""
    semis = {"m9": [0, 7, 14, 15, 19], "sus2": [0, 7, 12, 14, 19], "maj7": [0, 7, 11, 16, 19],
             "add9": [0, 7, 14, 16, 19], "m7": [0, 7, 10, 15, 19], "sus4": [0, 7, 12, 17, 19]}[tipo]
    base = hz(raiz, 2)
    return [base * 2 ** (s / 12) for s in semis]


# estado: progresión, bpm, brillo, pulso (corcheas graves), arpegio de cristal, metales, timbal
ESTADOS = {
    "suspenso": {"prog": [("D", "m9"), ("A#", "maj7"), ("G", "m7"), ("A", "sus4")], "bpm": 64,
                 "brillo": 1400, "pulso": 2, "cristal": True, "metales": False, "timbal": True},
    "espacio": {"prog": [("E", "sus2"), ("C", "maj7"), ("A", "m9"), ("B", "sus4")], "bpm": 56,
                "brillo": 1700, "pulso": 0, "cristal": True, "metales": False, "timbal": False},
    "tension": {"prog": [("D", "m9"), ("D", "m9"), ("A#", "maj7"), ("C", "sus2")], "bpm": 92,
                "brillo": 1200, "pulso": 4, "cristal": False, "metales": False, "timbal": True},
    "triunfo": {"prog": [("D", "add9"), ("A", "sus4"), ("B", "m7"), ("G", "maj7")], "bpm": 70,
                "brillo": 2600, "pulso": 2, "cristal": True, "metales": True, "timbal": True},
    "calma": {"prog": [("F", "maj7"), ("C", "add9"), ("D", "m9"), ("A#", "maj7")], "bpm": 60,
              "brillo": 1600, "pulso": 0, "cristal": True, "metales": False, "timbal": False},
}


def cristal(f, dur=2.5):
    """Nota de campanita de cristal (seno con armónico suave), muy limpia."""
    n = seg(dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2.01 * f * t)) * env_exp(n, 0.7)
    return (x * np.minimum(1, t / 0.005) * 0.09).astype(np.float32)


def pulso_grave(f, dur):
    n = seg(dur)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return lp(x * env_exp(n, 0.12) * np.minimum(1, t / 0.004), 500) * 0.22


def musica(estado, dur):
    e = ESTADOS[estado]
    compas = 4 * 60 / e["bpm"]
    n = seg(dur)
    out = np.zeros((n + seg(8), 2), np.float32)
    t, i = 0.0, 0
    while t < dur:
        raiz, tipo = e["prog"][i % len(e["prog"])]
        fr = voicing(raiz, tipo)
        largo = compas * 2
        k = seg(t)
        bloque = B.cuerdas(fr, largo + 2.0, e["brillo"]) * 0.8
        out[k: k + len(bloque)] += bloque[: len(out) - k]
        # pad sub-grave
        sub = estereo(np.sin(2 * np.pi * fr[0] / 2 * np.arange(seg(largo + 1)) / SR).astype(np.float32) * 0.05)
        sub *= np.minimum(1, np.arange(len(sub)) / seg(1.0))[:, None] * np.minimum(1, (len(sub) - np.arange(len(sub))) / seg(1.0))[:, None]
        out[k: k + len(sub)] += sub[: len(out) - k]
        if e["metales"] and i % 2 == 0:
            m = B.metales([fr[1], fr[2], fr[3]], largo) * 0.7
            out[k: k + len(m)] += m[: len(out) - k]
        if e["timbal"] and i % 2 == 0:
            tb = B.timbal(fr[0]) * 0.35
            out[k: k + len(tb)] += tb[: len(out) - k]
        if e["pulso"]:
            paso = compas / (2 * e["pulso"])
            for j in range(int(largo / paso)):
                kk = seg(t + j * paso)
                p = estereo(pulso_grave(fr[0], 0.5) * (1.0 if j % 4 == 0 else 0.6))
                out[kk: kk + len(p)] += p[: len(out) - kk]
        if e["cristal"]:
            arpe = [fr[2] * 2, fr[3] * 2, fr[4] * 2, fr[3] * 4, fr[4] * 2, fr[2] * 4]
            for j, f in enumerate(arpe):
                if rng.random() < 0.75:
                    kk = seg(t + j * largo / len(arpe) + rng.uniform(0, 0.05))
                    c = estereo(cristal(f), rng.uniform(-0.7, 0.7))
                    out[kk: kk + len(c)] += c[: len(out) - kk]
        t += largo
        i += 1
    out = reverb(out[:n], 4.0, 0.45, 4000)[:n]
    fade = seg(min(3, dur / 4))
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return normal(out, 0.5)


# ------------------------------------------------------------------ efectos
def quindar(entrada=True):
    """Pitido de radio de la NASA (tono Quindar de 2525/2475 Hz, 250 ms)."""
    f = 2525 if entrada else 2475
    n = seg(0.25)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.005) * np.minimum(1, (0.25 - t) / 0.005)
    return estereo((x * 0.25).astype(np.float32))


def estatica(dur):
    x = bp(ruido(seg(dur)), 800, 3500) * 0.12
    x *= (1 + 0.5 * np.sin(2 * np.pi * 3.1 * np.arange(len(x)) / SR)).astype(np.float32)
    return estereo(x)


def pitido_cuenta(f=1000):
    n = seg(0.12)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * np.minimum(1, (0.12 - t) / 0.01)
    return estereo((x * 0.25).astype(np.float32))


def rugido_cohete(dur, subida=2.0):
    """Rugido grave de los motores del Saturno V."""
    n = seg(dur)
    t = np.arange(n) / SR
    x = lp(ruido(n), 160, 2) * 2.2 + lp(ruido(n), 900, 2) * 0.35
    crackle = (rng.random(n) < 0.002).astype(np.float32) * rng.uniform(-1, 1, n).astype(np.float32)
    x += hp(crackle, 400) * 0.5
    env = np.minimum(1, t / subida) * np.minimum(1, (dur - t) / 2.0)
    l = x * env
    r = np.roll(x, 300) * env
    return np.stack([l, r], 1).astype(np.float32) * 0.5


def whoosh(dur=1.4):
    return B.whoosh(dur)


def impacto():
    return B.impacto()


def alarma(veces=4):
    """Alarma del ordenador de a bordo (suave, dos tonos)."""
    out = []
    for _ in range(veces):
        for f in (1400, 1000):
            n = seg(0.18)
            t = np.arange(n) / SR
            out.append(np.sin(2 * np.pi * f * t) * np.minimum(1, (0.18 - t) / 0.01) * 0.18)
        out.append(np.zeros(seg(0.35)))
    return estereo(np.concatenate(out).astype(np.float32))


def latido_suave(dur, bpm=58):
    return B.latido(dur, bpm) * 0.5


def zumbido_nave(dur):
    """Ambiente interior de la cápsula: ventiladores y zumbido eléctrico."""
    n = seg(dur)
    t = np.arange(n) / SR
    x = lp(ruido(n), 400) * 0.25 + 0.03 * np.sin(2 * np.pi * 120 * t)
    return estereo(x.astype(np.float32))
