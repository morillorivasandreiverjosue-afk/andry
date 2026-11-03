"""Música de misterio llamativa y efectos marinos (olas, viento, sonar, trueno, motor de avión).

Se apoya en ../apolo11/sonido_espacio.py y ../napoleon/sonido.py. Todo sintetizado: sin copyright.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent / "apolo11"))
from sonido_espacio import *  # noqa: F401,F403,E402
import sonido_espacio as E  # noqa: E402

B = E.B

# estados de misterio: menores pero sin disonancias de terror, con pulso marcado para que enganche
E.ESTADOS.update({
    "intriga": {"prog": [("A", "m9"), ("F", "maj7"), ("D", "m9"), ("E", "sus4")], "bpm": 96,
                "brillo": 1500, "pulso": 4, "cristal": True, "metales": False, "timbal": True},
    "misterio": {"prog": [("E", "m9"), ("C", "maj7"), ("A", "m7"), ("B", "sus4")], "bpm": 84,
                 "brillo": 1300, "pulso": 2, "cristal": True, "metales": False, "timbal": True},
    "investigacion": {"prog": [("D", "m9"), ("A#", "maj7"), ("F", "add9"), ("C", "sus2")], "bpm": 90,
                      "brillo": 1700, "pulso": 2, "cristal": True, "metales": False, "timbal": False},
    "epico_mar": {"prog": [("D", "m9"), ("A#", "maj7"), ("F", "add9"), ("C", "sus4")], "bpm": 76,
                  "brillo": 2400, "pulso": 2, "cristal": True, "metales": True, "timbal": True},
})


def bombo(n_tiempos, bpm, vol=0.35):
    """Bombo grave suave en cada tiempo: da ritmo sin asustar."""
    paso = 60 / bpm
    n = E.seg(n_tiempos * paso + 1)
    out = np.zeros(n, np.float32)
    m = E.seg(0.35)
    t = np.arange(m) / E.SR
    golpe = np.sin(2 * np.pi * (48 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
    for k in range(n_tiempos):
        i = E.seg(k * paso)
        out[i: i + m] += golpe[: n - i] * (1.0 if k % 4 == 0 else 0.7)
    return E.estereo(out * vol)


def musica(estado, dur):
    m = E.musica(estado, dur)
    if estado in ("intriga", "misterio", "investigacion", "epico_mar"):
        bpm = E.ESTADOS[estado]["bpm"]
        b = bombo(int(dur * bpm / 60), bpm)[: len(m)]
        f = min(len(b), E.seg(3))
        b[:f] *= np.linspace(0, 1, f)[:, None]
        b[len(b) - f:] *= np.linspace(1, 0, f)[:, None]
        m[: len(b)] += b * 0.6
    return E.normal(m, 0.5)


def olas(dur):
    return B.olas(dur) * 0.8


def viento(dur):
    return B.viento(dur)


def sonar():
    """Ping de sonar con eco."""
    n = E.seg(2.0)
    t = np.arange(n) / E.SR
    x = np.sin(2 * np.pi * 1180 * t) * np.exp(-t * 3.5) * np.minimum(1, t / 0.004) * 0.3
    return E.reverb(E.estereo(x.astype(np.float32)), 2.5, 0.45, 5000)[:n]


def trueno():
    n = E.seg(4.0)
    t = np.arange(n) / E.SR
    x = E.lp(E.ruido(n), 250, 2) * 3 * np.exp(-t * 0.9) * np.minimum(1, t / 0.05)
    x += E.lp(E.ruido(n), 1800, 2) * np.exp(-t * 6) * 0.8
    return E.estereo(x.astype(np.float32) * 0.4)


def motor_avion(dur):
    """Zumbido de motor de hélice."""
    n = E.seg(dur)
    t = np.arange(n) / E.SR
    x = np.sign(np.sin(2 * np.pi * 38 * t)) * 0.2 + E.lp(E.ruido(n), 300) * 0.6
    x = E.lp(x.astype(np.float32), 600) * (1 + 0.15 * np.sin(2 * np.pi * 0.4 * t)).astype(np.float32)
    env = np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.5)
    return E.estereo((x * env * 0.5).astype(np.float32), 0.2)
