"""Efectos de sonido y música sintetizados con numpy (no necesitan archivos externos).

Todo trabaja a 44100 Hz en estéreo (arrays de forma [n, 2], float32).
"""
import numpy as np
from scipy import signal

SR = 44100
rng = np.random.default_rng(1812)


# ----------------------------------------------------------------- utilidades
def seg(s):
    return int(s * SR)


def ruido(n):
    return rng.standard_normal(n).astype(np.float32)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR)).astype(np.float32)


def lp(x, f, orden=2):
    b, a = signal.butter(orden, min(f / (SR / 2), 0.99), "low")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def hp(x, f, orden=2):
    b, a = signal.butter(orden, f / (SR / 2), "high")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def bp(x, f1, f2, orden=2):
    b, a = signal.butter(orden, [f1 / (SR / 2), f2 / (SR / 2)], "band")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def estereo(x, pan=0.0):
    """pan -1 (izquierda) .. 1 (derecha)"""
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l * 1.41, x * r * 1.41], axis=1).astype(np.float32)


_IR = {}


def reverb(x, segundos=2.5, mezcla=0.35, brillo=3000):
    """Reverb por convolución con una respuesta impulsional sintética."""
    clave = (segundos, brillo)
    if clave not in _IR:
        n = seg(segundos)
        ir = np.stack([ruido(n), ruido(n)], 1) * env_exp(n, segundos / 6.5)[:, None]
        ir = lp(ir, brillo)
        ir[: seg(0.01)] *= np.linspace(0, 1, seg(0.01))[:, None]
        _IR[clave] = ir / np.sqrt((ir ** 2).sum(0))
    ir = _IR[clave]
    if x.ndim == 1:
        x = estereo(x)
    mojado = np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)
    seco = np.zeros_like(mojado)
    seco[: len(x)] = x
    return (seco * (1 - mezcla) + mojado * mezcla * 2.0).astype(np.float32)


def normal(x, pico=0.9):
    m = np.abs(x).max()
    return (x / m * pico).astype(np.float32) if m > 0 else x


# ------------------------------------------------------------------- efectos
def disparo(distancia=0.0, pan=0.0):
    """Disparo de mosquete: chasquido + pólvora + cola. distancia 0 (cerca) .. 1 (lejos)"""
    n = seg(0.9)
    crack = ruido(n) * env_exp(n, 0.012)
    cuerpo = lp(ruido(n), 1800) * env_exp(n, 0.07) * 1.6
    t = np.arange(n) / SR
    golpe = np.sin(2 * np.pi * (90 * t - 40 * t ** 2)) * env_exp(n, 0.06) * 0.9
    x = crack + cuerpo + golpe
    x = lp(x, 9000 - 7000 * distancia)
    x = normal(x, 1.0 - 0.6 * distancia)
    return reverb(estereo(x, pan), 1.8, 0.25 + 0.4 * distancia)


def canon(distancia=0.0, pan=0.0):
    """Cañonazo: estallido grave con retumbe largo."""
    n = seg(3.0)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (55 * t - 8 * t ** 2)) * env_exp(n, 0.35)
    explosion = lp(ruido(n), 900) * env_exp(n, 0.25) * 2.5
    crack = hp(ruido(n), 1500) * env_exp(n, 0.02) * 0.8
    retumbe = lp(ruido(n), 200, 4) * env_exp(n, 0.9) * 2.0
    x = sub * 1.4 + explosion + crack * (1 - distancia) + retumbe
    x = lp(x, 6000 - 4500 * distancia)
    x = normal(x, 1.0 - 0.5 * distancia)
    return reverb(estereo(x, pan), 3.5, 0.3 + 0.3 * distancia, 2000)


def descarga(n_tiros=14, duracion=1.6, distancia=0.3):
    """Descarga de fusilería: muchos disparos casi a la vez."""
    salida = np.zeros((seg(duracion + 3), 2), np.float32)
    for _ in range(n_tiros):
        d = disparo(min(1, distancia + rng.random() * 0.4), rng.uniform(-0.9, 0.9))
        i = seg(rng.random() ** 2 * duracion)
        salida[i: i + len(d)] += d[: len(salida) - i] * 0.45
    return salida


def impacto():
    """Golpe cinematográfico (tráiler) para títulos y momentos dramáticos."""
    n = seg(5)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (48 * t - 4 * t ** 2)) * env_exp(n, 0.9)
    boom = lp(ruido(n), 400, 4) * env_exp(n, 0.4) * 2
    metal = sum(np.sin(2 * np.pi * f * t) * env_exp(n, 0.5 + 0.3 * i)
                for i, f in enumerate([220, 331, 497, 750])) * 0.15
    crack = hp(ruido(n), 2500) * env_exp(n, 0.03)
    x = normal(sub * 1.5 + boom + metal + crack)
    return reverb(estereo(x), 4.0, 0.4, 2500)


def whoosh(dur=1.2, subida=True):
    n = seg(dur)
    x = ruido(n)
    out = np.zeros(n, np.float32)
    bloques = 40
    for b in range(bloques):
        a, z = b * n // bloques, (b + 1) * n // bloques
        f = 300 + 4000 * ((b / bloques) if subida else (1 - b / bloques))
        out[a:z] = bp(x[a - 2000 if a > 2000 else 0:z], f * 0.6, min(f * 1.6, 20000))[-(z - a):]
    out *= np.sin(np.linspace(0, np.pi, n)) ** 2
    return reverb(estereo(normal(out, 0.6)), 1.5, 0.3)


def tambor_militar(tiempo_total, bpm=110, pan=0.0, volumen=0.5):
    """Redoble de marcha militar (caja) en bucle."""
    n = seg(tiempo_total)
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    golpe_n = seg(0.25)

    def golpe(v):
        t = np.arange(golpe_n) / SR
        tono = np.sin(2 * np.pi * 190 * t) * env_exp(golpe_n, 0.03)
        bordon = bp(ruido(golpe_n), 2000, 9000) * env_exp(golpe_n, 0.06)
        return (tono * 0.6 + bordon) * v

    # patrón: 16 semicorcheas por compás; 1 = golpe, 0.4 = nota fantasma
    patron = [1, 0, .4, .4, 1, 0, .4, 0, 1, .4, .4, .4, 1, 0, 1, 0]
    t = 0.0
    i = 0
    while t < tiempo_total - 0.3:
        v = patron[i % 16]
        if v:
            k = seg(t)
            g = golpe(v * rng.uniform(0.8, 1.0))
            out[k: k + golpe_n] += g[: n - k]
        t += beat / 4
        i += 1
    return estereo(out * volumen, pan)


def timbal(nota=55.0):
    n = seg(2.5)
    t = np.arange(n) / SR
    f = nota * (1 + 0.15 * np.exp(-t * 20))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.6)
    x += lp(ruido(n), 300) * env_exp(n, 0.05) * 0.8
    return reverb(estereo(normal(x, 0.8)), 2.5, 0.3)


def campana(nota=196.0, dur=7.0):
    """Campana de catedral (parciales inarmónicos)."""
    n = seg(dur)
    t = np.arange(n) / SR
    parciales = [(0.5, 1.0, 3.5), (1.0, 0.8, 2.5), (1.19, 0.6, 2.0), (1.5, 0.5, 1.6),
                 (2.0, 0.45, 1.2), (2.52, 0.3, 0.9), (3.0, 0.25, 0.7), (4.07, 0.15, 0.5)]
    x = sum(a * np.sin(2 * np.pi * nota * r * t) * env_exp(n, tau) for r, a, tau in parciales)
    x += hp(ruido(n), 3000) * env_exp(n, 0.01) * 0.3
    return reverb(estereo(normal(x, 0.7)), 4.0, 0.45)


def viento(dur, fuerza=1.0):
    n = seg(dur)
    t = np.arange(n) / SR
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t + rng.random() * 6) * np.sin(2 * np.pi * 0.13 * t)
    l = bp(ruido(n), 250, 1400) * (0.4 + 0.6 * mod)
    r = bp(ruido(n), 250, 1400) * (0.4 + 0.6 * mod[::-1])
    silbido = bp(ruido(n), 1800, 2600, 4) * mod ** 3 * 0.6
    return (np.stack([l + silbido, r + silbido], 1) * 0.35 * fuerza).astype(np.float32)


def olas(dur, fuerza=1.0):
    n = seg(dur)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    for c in range(2):
        fase = rng.random() * 6
        swell = np.clip(np.sin(2 * np.pi * t / 7.5 + fase), 0, 1) ** 2.5
        x = lp(ruido(n), 1200) * (0.15 + swell) + hp(ruido(n), 2500) * swell ** 2 * 0.5
        out[:, c] = x
    return (out * 0.35 * fuerza).astype(np.float32)


def fuego(dur, fuerza=1.0):
    n = seg(dur)
    base = lp(ruido(n), 500) * 0.5
    chasquidos = np.zeros(n, np.float32)
    for _ in range(int(dur * 18)):
        k = rng.integers(0, n - 2000)
        largo = rng.integers(80, 900)
        chasquidos[k: k + largo] += hp(ruido(largo), 1500) * env_exp(largo, 0.002) * rng.uniform(0.3, 1.5)
    out = np.stack([base + chasquidos, base + np.roll(chasquidos, 3000)], 1)
    return (out * 0.4 * fuerza).astype(np.float32)


def pluma(dur):
    """Pluma escribiendo sobre papel."""
    n = seg(dur)
    out = np.zeros(n, np.float32)
    t = 0
    while t < n - seg(0.4):
        largo = seg(rng.uniform(0.08, 0.35))
        trazo = bp(ruido(largo), 2500, 7000) * np.sin(np.linspace(0, np.pi, largo)) ** 0.5
        out[t: t + largo] += trazo * rng.uniform(0.3, 0.8)
        t += largo + seg(rng.uniform(0.03, 0.2))
    return estereo(out * 0.25)


def latido(dur, bpm=60):
    n = seg(dur)
    out = np.zeros(n, np.float32)
    golpe = seg(0.3)
    tt = np.arange(golpe) / SR
    g = np.sin(2 * np.pi * 48 * tt) * env_exp(golpe, 0.06)
    t = 0.0
    while t < dur - 0.6:
        for d, v in ((0, 1.0), (0.28, 0.7)):
            k = seg(t + d)
            out[k: k + golpe] += g[: n - k] * v
        t += 60 / bpm
    return estereo(lp(out, 150) * 0.9)


def caballos(dur):
    """Galope de caballería a lo lejos."""
    n = seg(dur)
    out = np.zeros(n, np.float32)
    golpe = seg(0.08)
    g = lp(ruido(golpe), 700) * env_exp(golpe, 0.015)
    t = 0.0
    while t < dur - 0.3:
        for d in (0, 0.07, 0.15):
            for _ in range(4):
                k = seg(t + d + rng.uniform(0, 0.05))
                if k + golpe < n:
                    out[k: k + golpe] += g * rng.uniform(0.3, 0.7)
        t += 0.42
    env = np.sin(np.linspace(0, np.pi, n)) ** 0.7
    return reverb(estereo(out * env * 0.6), 2.0, 0.3)


def batalla(dur, intensidad=1.0):
    """Ambiente de batalla: fusilería, cañones y retumbe constante."""
    n = seg(dur)
    out = np.zeros((n + seg(4), 2), np.float32)
    out[:n] += estereo(lp(ruido(n), 120, 4) * 0.4 * intensidad)
    t = 0.0
    while t < dur:
        k = seg(t)
        if rng.random() < 0.18:
            s = canon(rng.uniform(0.3, 0.9), rng.uniform(-0.8, 0.8)) * 0.7
        else:
            s = disparo(rng.uniform(0.2, 1.0), rng.uniform(-1, 1)) * 0.5
        out[k: k + len(s)] += s[: len(out) - k] * intensidad
        t += rng.exponential(0.5 / intensidad)
    return out[:n]


# ------------------------------------------------------------------- música
NOTAS = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(nombre, octava):
    return 440.0 * 2 ** ((NOTAS[nombre] + 12 * (octava + 1) - 69) / 12)


def acorde(raiz, menor):
    """Frecuencias de un acorde en voicing amplio de orquesta."""
    tercera = 3 if menor else 4
    base = hz(raiz, 2)
    semis = [0, 12, 12 + 7, 24, 24 + tercera, 24 + 7]
    return [base * 2 ** (s / 12) for s in semis]


def cuerdas(freqs, dur, brillo=1800.0):
    """Pad de cuerdas: sierras desafinadas filtradas con ataque lento."""
    n = seg(dur)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    for f in freqs:
        for c, det in enumerate((-0.12, 0.12)):
            for d in (-0.06, 0.0, 0.06):
                ff = f * 2 ** ((det + d) / 12)
                vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * t + rng.random() * 6)
                fase = 2 * np.pi * np.cumsum(ff * vib) / SR + rng.random() * 6
                out[:, c] += signal.sawtooth(fase).astype(np.float32) / (1 + f / 400)
    out = lp(out, brillo, 2)
    ataque = np.minimum(1, t / min(1.5, dur / 3)) * np.minimum(1, (dur - t) / min(1.5, dur / 3))
    return (out * ataque[:, None] * 0.05).astype(np.float32)


def metales(freqs, dur):
    """Metales (trompas) para los momentos épicos."""
    n = seg(dur)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for f in freqs:
        fase = 2 * np.pi * f * t
        out += (np.sin(fase) + 0.5 * np.sin(2 * fase) + 0.3 * np.sin(3 * fase) + 0.15 * np.sin(4 * fase))
    env = np.minimum(1, t / 0.4) * np.clip((dur - t) / 0.8, 0, 1)
    out = lp(out * env, 2200)
    return estereo(out * 0.06)


def piano(f, dur=3.0):
    n = seg(dur)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * env_exp(n, 1.6 / k)
            for k, a in enumerate([1, 0.5, 0.25, 0.12, 0.06], start=1))
    x *= np.minimum(1, t / 0.004)
    return x.astype(np.float32) * 0.18


# Progresiones por estado de ánimo: (raíz, menor, compases)
ESTADOS = {
    "epico": {"prog": [("D", 1), ("A#", 0), ("F", 0), ("C", 0)], "bpm": 84, "brillo": 2600,
              "tambores": True, "metales": True, "piano": False, "timbales": True},
    "marcha": {"prog": [("G", 1), ("D#", 0), ("A#", 0), ("F", 0)], "bpm": 104, "brillo": 2000,
               "tambores": True, "metales": True, "piano": False, "timbales": False},
    "tension": {"prog": [("C", 1), ("C", 1), ("G#", 0), ("G", 0)], "bpm": 70, "brillo": 900,
                "tambores": False, "metales": False, "piano": False, "timbales": True, "pulso": True},
    "romantico": {"prog": [("F", 0), ("D", 1), ("A#", 0), ("C", 0)], "bpm": 66, "brillo": 1500,
                  "tambores": False, "metales": False, "piano": True, "timbales": False},
    "misterio": {"prog": [("E", 1), ("C", 0), ("A", 1), ("B", 0)], "bpm": 64, "brillo": 1100,
                 "tambores": False, "metales": False, "piano": True, "timbales": False, "pulso": True},
    "triste": {"prog": [("A", 1), ("F", 0), ("C", 0), ("G", 0)], "bpm": 58, "brillo": 1200,
               "tambores": False, "metales": False, "piano": True, "timbales": False},
    "frio": {"prog": [("B", 1), ("G", 0), ("E", 1), ("F#", 0)], "bpm": 56, "brillo": 700,
             "tambores": False, "metales": False, "piano": False, "timbales": True, "pulso": True},
    "majestuoso": {"prog": [("D", 0), ("A", 0), ("B", 1), ("G", 0)], "bpm": 72, "brillo": 2400,
                   "tambores": False, "metales": True, "piano": False, "timbales": True},
}


def musica(estado, dur):
    """Genera una pista de música de `dur` segundos para un estado de ánimo."""
    e = ESTADOS[estado]
    compas = 4 * 60 / e["bpm"]
    n = seg(dur)
    out = np.zeros((n + seg(6), 2), np.float32)
    t, i = 0.0, 0
    while t < dur:
        raiz, menor = e["prog"][i % len(e["prog"])]
        freqs = acorde(raiz, menor)
        largo = compas * 2  # cada acorde dura dos compases
        k = seg(t)
        bloque = cuerdas(freqs, largo + 1.5, e["brillo"])
        out[k: k + len(bloque)] += bloque[: len(out) - k]
        if e["metales"] and i % 2 == 0:
            m = metales([freqs[1], freqs[2], freqs[4]], largo)
            out[k: k + len(m)] += m[: len(out) - k]
        if e["piano"]:
            arpegio = [freqs[1], freqs[2], freqs[4], freqs[5], freqs[4] * 2, freqs[5], freqs[4], freqs[2]]
            for j, f in enumerate(arpegio):
                kk = seg(t + j * compas / 4)
                p = estereo(piano(f), (j % 3 - 1) * 0.4)
                out[kk: kk + len(p)] += p[: len(out) - kk]
        if e["timbales"]:
            for j in (0, 1.5) if estado == "epico" else (0,):
                kk = seg(t + j * compas)
                tb = timbal(freqs[0]) * 0.55
                out[kk: kk + len(tb)] += tb[: len(out) - kk]
        if e.get("pulso"):
            for j in range(8):
                kk = seg(t + j * compas / 4)
                pn = seg(0.25)
                p = np.sin(2 * np.pi * freqs[0] * np.arange(pn) / SR) * env_exp(pn, 0.08) * 0.12
                out[kk: kk + pn, 0] += p[: len(out) - kk]
                out[kk: kk + pn, 1] += p[: len(out) - kk]
        t += largo
        i += 1
    if e["tambores"]:
        out[:n] += tambor_militar(dur, e["bpm"] * 1.0, volumen=0.18)
    out = reverb(out[:n], 3.0, 0.35, 3500)[:n]
    fade = seg(min(3, dur / 4))
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return normal(out, 0.5)
