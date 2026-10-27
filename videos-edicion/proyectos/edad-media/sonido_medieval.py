"""Efectos de sonido medievales sintetizados (sin archivos externos).

Complementa ../napoleon/sonido.py (galope, campanas, viento, fuego, latido, música) con lo que una
batalla medieval necesita y aquel módulo no tiene: espadas, cuernos, gritos, flechas, tambores de
guerra, el murmullo de un mercado y el yunque del herrero. Todo a 44,1 kHz en estéreo [n, 2].
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "napoleon"))
from sonido import (SR, bp, env_exp, estereo, hp, lp, normal, reverb, ruido, seg)  # noqa: E402

rng = np.random.default_rng(1066)


def espada(pan=0.0, fuerza=1.0):
    """Choque de dos espadas: parciales metálicos inarmónicos más el golpe."""
    n = seg(1.6)
    t = np.arange(n) / SR
    base = rng.uniform(900, 1500)
    x = np.zeros(n, np.float32)
    for r, a, tau in ((1.0, 1.0, 0.35), (2.31, 0.7, 0.25), (3.67, 0.5, 0.18), (5.12, 0.35, 0.12),
                      (6.94, 0.25, 0.08)):
        x += a * np.sin(2 * np.pi * base * r * t + rng.random() * 6) * env_exp(n, tau)
    x += hp(ruido(n), 2500) * env_exp(n, 0.015) * 1.5  # chasquido del impacto
    x += lp(ruido(n), 400) * env_exp(n, 0.03) * 0.8      # cuerpo del golpe
    return reverb(estereo(normal(x, 0.8 * fuerza), pan), 1.2, 0.25)


def tajo():
    """Silbido de una espada cortando el aire."""
    n = seg(0.35)
    x = bp(ruido(n), 1500, 6000) * np.sin(np.linspace(0, np.pi, n)) ** 2
    return estereo(normal(x, 0.4), rng.uniform(-0.6, 0.6))


def melee(dur, densidad=1.0):
    """Combate cuerpo a cuerpo: espadas por todas partes, golpes contra escudos y tajos."""
    n = seg(dur)
    out = np.zeros((n + seg(2), 2), np.float32)
    t = 0.0
    while t < dur:
        k = seg(t)
        r = rng.random()
        if r < 0.55:
            s = espada(rng.uniform(-0.9, 0.9), rng.uniform(0.3, 1.0))
        elif r < 0.8:
            s = escudo(rng.uniform(-0.9, 0.9))
        else:
            s = tajo()
        out[k: k + len(s)] += s[: len(out) - k] * rng.uniform(0.4, 0.9)
        t += rng.exponential(0.32 / densidad)
    return out[:n]


def escudo(pan=0.0):
    """Golpe seco contra un escudo de madera."""
    n = seg(0.6)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * rng.uniform(90, 140) * t) * env_exp(n, 0.07)
    x += bp(ruido(n), 300, 2500) * env_exp(n, 0.04) * 1.2
    return reverb(estereo(normal(x, 0.8), pan), 1.0, 0.2)


def ejercito(dur, fuerza=1.0):
    """Clamor de un ejército: muchas voces graves sostenidas (gritos de guerra)."""
    n = seg(dur)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    for _ in range(14):
        f0 = rng.uniform(95, 180)
        vib = 1 + 0.03 * np.sin(2 * np.pi * rng.uniform(3, 6) * t + rng.random() * 6)
        fase = 2 * np.pi * np.cumsum(f0 * vib) / SR
        voz = sum(np.sin(k * fase) / k for k in range(1, 9))
        voz = bp(voz.astype(np.float32), 250, 2200)
        pan = rng.uniform(-0.9, 0.9)
        out += estereo(voz * rng.uniform(0.4, 1.0), pan)
    out += estereo(bp(ruido(n), 300, 2500) * 0.6)  # el rumor de fondo de la multitud
    sube = np.minimum(1, t / 0.8) * np.clip((dur - t) / 1.5, 0, 1)
    return reverb(normal(out * sube[:, None], 0.5 * fuerza), 2.5, 0.35)


def cuerno(dur=3.5, nota=110.0):
    """Cuerno de guerra: un metal grave con ataque lento y algo de desafinación."""
    n = seg(dur)
    t = np.arange(n) / SR
    f = nota * (1 + 0.02 * np.minimum(1, t / 0.3)) * (1 + 0.004 * np.sin(2 * np.pi * 5 * t))
    fase = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * fase) * (0.8 ** k) for k in range(1, 12))
    x = lp(x.astype(np.float32), 1800)
    env = np.minimum(1, t / 0.25) * np.clip((dur - t) / 0.6, 0, 1)
    return reverb(estereo(normal(x * env, 0.7)), 3.5, 0.45)


def flechas(n_flechas=12, dur=2.0):
    """Lluvia de flechas: silbidos rápidos que cruzan el estéreo."""
    out = np.zeros((seg(dur + 1), 2), np.float32)
    for _ in range(n_flechas):
        m = seg(rng.uniform(0.25, 0.5))
        x = bp(ruido(m), 2500, 8000) * np.sin(np.linspace(0, np.pi, m)) ** 3
        p0 = rng.uniform(-1, 1)
        izq = np.linspace(1 - p0, 1 + p0, m) / 2
        s = np.stack([x * izq, x * (1 - izq)], 1) * 0.35
        k = seg(rng.uniform(0, dur))
        out[k: k + m] += s[: len(out) - k]
    return out


def tambores_guerra(dur, bpm=92, volumen=0.6):
    """Tambores graves de guerra (timbales de piel) con un patrón insistente."""
    n = seg(dur)
    out = np.zeros(n, np.float32)
    golpe_n = seg(0.6)
    tt = np.arange(golpe_n) / SR

    def golpe(f, v):
        return (np.sin(2 * np.pi * f * tt * (1 + 0.3 * np.exp(-tt * 30))) * env_exp(golpe_n, 0.18)
                + lp(ruido(golpe_n), 500) * env_exp(golpe_n, 0.02) * 0.6) * v

    patron = [(1, 70), (0, 0), (0.6, 90), (0, 0), (1, 70), (0.5, 90), (0.7, 80), (0, 0)]
    paso = 60 / bpm / 2
    t, i = 0.0, 0
    while t < dur - 0.6:
        v, f = patron[i % len(patron)]
        if v:
            k = seg(t)
            out[k: k + golpe_n] += golpe(f, v * rng.uniform(0.85, 1.0))[: n - k]
        t += paso
        i += 1
    return reverb(estereo(out * volumen), 2.0, 0.3)


def multitud(dur, fuerza=1.0):
    """Murmullo de mercado: voces lejanas sin palabras y algún sonido suelto."""
    n = seg(dur)
    out = np.zeros((n, 2), np.float32)
    for c in range(2):
        voces = np.zeros(n, np.float32)
        for _ in range(10):
            silabas = np.repeat(rng.random(int(dur * 6) + 2) > 0.45, seg(1 / 6))[:n].astype(np.float32)
            silabas = np.convolve(silabas, np.ones(seg(0.03)) / seg(0.03), "same")
            voces += bp(ruido(n), rng.uniform(250, 500), rng.uniform(1200, 2600)) * silabas
        out[:, c] = voces
    return reverb(normal(out, 0.3 * fuerza), 1.5, 0.3)


def yunque(dur, ritmo=1.1):
    """Martillo de herrero sobre el yunque."""
    n = seg(dur)
    out = np.zeros((n + seg(2), 2), np.float32)
    t = 0.3
    while t < dur:
        m = seg(1.2)
        tt = np.arange(m) / SR
        x = sum(a * np.sin(2 * np.pi * f * tt) * env_exp(m, tau)
                for f, a, tau in ((1850, 1, 0.5), (2730, 0.6, 0.3), (4400, 0.4, 0.15), (620, 0.3, 0.2)))
        x += hp(ruido(m), 3000) * env_exp(m, 0.01)
        k = seg(t)
        out[k: k + m] += estereo(normal(x, 0.5), 0.2)[: len(out) - k]
        t += ritmo * rng.uniform(0.85, 1.15)
    return reverb(out[:n], 1.2, 0.25)


def asedio(dur):
    """Asedio: impactos de piedras contra murallas, derrumbes y el ejército de fondo."""
    n = seg(dur)
    out = np.zeros((n + seg(3), 2), np.float32)
    t = 0.5
    while t < dur:
        m = seg(2.5)
        tt = np.arange(m) / SR
        x = lp(ruido(m), 300, 4) * env_exp(m, 0.35) * 2 + np.sin(2 * np.pi * 45 * tt) * env_exp(m, 0.4)
        x += bp(ruido(m), 800, 4000) * env_exp(m, 0.6) * 0.4 * (rng.random() < 0.6)  # cascotes
        k = seg(t)
        out[k: k + m] += reverb(estereo(normal(x, 0.8), rng.uniform(-0.7, 0.7)), 3.0, 0.4)[:m][: len(out) - k]
        t += rng.uniform(2.2, 4.5)
    return out[:n]
