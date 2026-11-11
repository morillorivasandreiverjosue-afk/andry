"""Beat de trap latino romántico estilo Anuel (no es una copia del tema).

144 BPM con sensación half-time, Sol menor, progresión i - VI - III - VII
(Gm - Eb - Bb - F), guitarra de nylon arpegiada, piano oscuro, pad,
808 pesado con slides, rolls de hi-hat y snare con reverb.

Estructura (34 compases, ~57 s):
    intro 4 | coro 8 | verso 8 | puente 4 | coro 8 | final 2

Uso:
    python3 beats/trap_latino_castillo.py   # crea beats/trap_latino_castillo.wav
Requiere solo numpy.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 144
STEP = 60 / BPM / 4
SPB = 16
SECTIONS = [("intro", 4), ("coro", 8), ("verso", 8), ("puente", 4),
            ("coro", 8), ("final", 2)]
BARS = sum(n for _, n in SECTIONS)
TOTAL = int(SR * (BARS * SPB * STEP + 4.0))

rng = np.random.default_rng(21)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, decay, attack=0.003):
    t = np.arange(n) / SR
    return np.clip(t / attack, 0, 1) * np.exp(-t / decay)


def lp(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def hp(x, a=0.9):
    y = np.empty_like(x)
    px = py = 0.0
    for i, v in enumerate(x):
        py = a * (py + v - px)
        px = v
        y[i] = py
    return y


def reverb(x, seconds=2.8, damp=2.6):
    n = int(SR * seconds)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * damp)
        ir = np.convolve(ir, np.ones(8) / 8, mode="same")
        ir[: int(0.02 * SR)] = 0
        size = 1 << (len(x) + n - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[:, ch], size) * np.fft.rfft(ir, size), size)
        out[:, ch] = y[: len(x)]
    return out / (np.max(np.abs(out)) + 1e-9)


# ---------- Instrumentos ----------
def nylon(m, length=1.4):
    """Guitarra de nylon (Karplus-Strong con ataque suavizado)."""
    n = int(SR * length)
    p = int(SR / hz(m))
    buf = lp(rng.uniform(-1, 1, p), 0.35)
    out = np.empty(n)
    for i in range(n):
        v = buf[i % p]
        out[i] = v
        buf[i % p] = 0.997 * 0.5 * (v + buf[(i + 1) % p])
    return lp(out, 0.45) * env(n, 0.8, 0.002) * 0.3


def piano(m, length):
    n = int(SR * (length + 1.0))
    t = np.arange(n) / SR
    f = hz(m)
    s = (np.sin(2 * np.pi * f * t)
         + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.4)
         + 0.15 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.2))
    e = env(n, 1.1, 0.002)
    rel = t > length
    e[rel] *= np.exp(-(t[rel] - length) / 0.2)
    return s * e * 0.06


def pad(ms, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in ms:
        for d in (-0.15, 0.0, 0.15):
            ph = 2 * np.pi * hz(m) * (1 + d / 100) * t
            s += 2 * (ph / (2 * np.pi) % 1) - 1  # diente de sierra
    s = lp(lp(s, 0.02), 0.05)
    e = np.minimum(1, t / 0.6) * np.minimum(1, (length - t) / 0.4)
    return s * e * 0.03


def kick():
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    f = 50 + 100 * np.exp(-t / 0.022)
    return np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.09)) * 0.8


def bass808(m, length, from_m=None):
    n = int(SR * length)
    t = np.arange(n) / SR
    tgt = hz(m)
    if from_m is None:
        f = tgt * (1 + 0.4 * np.exp(-t / 0.02))
    else:
        f = tgt + (hz(from_m) - tgt) * np.exp(-t / 0.07)
    s = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR))
    e = env(n, 2.0, 0.005)
    fade = min(n, int(SR * 0.03))
    e[-fade:] *= np.linspace(1, 0, fade)
    return s * e * 0.85


def snare():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    noise = hp(rng.standard_normal(n), 0.85) * env(n, 0.09)
    body = np.sin(2 * np.pi * 180 * t) * env(n, 0.04)
    return (noise * 0.5 + body * 0.45) * 0.75


def hat(open_=False):
    n = int(SR * (0.3 if open_ else 0.04))
    x = hp(hp(rng.standard_normal(n), 0.6), 0.6)
    return x * env(n, 0.1 if open_ else 0.009) * 0.2


def riser(length):
    n = int(SR * length)
    t = np.arange(n) / SR
    x = hp(rng.standard_normal(n), 0.95)
    return x * (t / length) ** 2 * 0.15


# ---------- Mezcla ----------
dry = np.zeros((TOTAL, 2))
send = np.zeros((TOTAL, 2))


def place(s, step, g=1.0, pan=0.0, rv=0.0):
    i = int(round(step * STEP * SR))
    j = min(TOTAL, i + len(s))
    s = s[: j - i]
    l, r = g * (1 - max(0, pan)), g * (1 + min(0, pan))
    dry[i:j, 0] += s * l
    dry[i:j, 1] += s * r
    if rv:
        send[i:j, 0] += s * l * rv
        send[i:j, 1] += s * r * rv


K, SN, HC, HO = kick(), snare(), hat(), hat(True)

# Gm - Eb - Bb - F
chords = [[55, 58, 62], [51, 55, 58], [58, 62, 65], [53, 57, 60]]
roots = [31, 27, 34, 29]
# Arpegio de guitarra (paso, índice de nota; +12 = octava arriba)
guitar = [(0, 0), (2, 1), (3, 2), (5, 1), (6, 2), (8, 0), (10, 1),
          (11, 2), (13, 1), (14, 12)]
# Piano: motivo agudo para el coro
hook = [
    [(0, 74), (3, 74), (6, 72), (8, 70), (12, 69)],
    [(0, 70), (3, 70), (6, 72), (8, 74), (12, 70)],
    [(0, 74), (3, 77), (6, 74), (8, 72), (12, 70)],
    [(0, 69), (3, 70), (6, 72), (10, 69), (14, 72)],
]

bar = 0
prev = None
for name, length in SECTIONS:
    for k in range(length):
        b0 = bar * SPB
        c = bar % 4
        last_of_section = k == length - 1
        drums = name in ("coro", "verso")

        # Guitarra (siempre salvo el final) y pad
        if name != "final":
            for s, idx in guitar:
                notes = chords[c]
                m = notes[0] + 12 if idx == 12 else notes[idx]
                place(nylon(m + 12), b0 + s, 1.0 if name != "puente" else 0.7,
                      pan=-0.3 if s % 2 else 0.3, rv=0.3)
        place(pad([n - 12 for n in chords[c]] + [chords[c][0]], SPB * STEP),
              b0, 1.0 if name != "verso" else 0.6)

        # Piano: hook en el coro y el puente
        if name in ("coro", "puente"):
            for s, m in hook[c]:
                place(piano(m + 12, 3 * STEP), b0 + s, 1.0, pan=0.15, rv=0.55)

        # Riser antes de entrar la batería
        if last_of_section and name in ("intro", "puente"):
            place(riser(SPB * STEP), b0, 1.0, rv=0.4)

        if drums:
            # Hi-hats: 8vos en el verso, 16vos en el coro, rolls cada 2 compases
            base = 1 if name == "coro" else 2
            s = 0.0
            while s < 16:
                if bar % 2 == 1 and 12 <= s < 14:
                    sub = 1 / 3
                elif bar % 4 == 3 and 14 <= s < 16:
                    sub = 0.25
                else:
                    sub = base
                g = 1.0 if s == int(s) and int(s) % 4 == 0 else 0.6
                place(HC, b0 + s, g, pan=0.2)
                s = round(s + sub, 6)
            if bar % 2 == 0:
                place(HO, b0 + 6, 0.55, pan=-0.2, rv=0.2)

            # Kick + 808 con slides
            pat = [0, 7, 10] if name == "coro" else [0, 10]
            if bar % 4 == 3:
                pat = [0, 3, 7, 10, 14]
            for i, s in enumerate(pat):
                place(K, b0 + s)
                nxt = pat[i + 1] if i + 1 < len(pat) else 16
                root = roots[c] + (12 if (bar % 4 == 3 and s == 14) else 0)
                place(bass808(root, (nxt - s) * STEP, prev), b0 + s, 0.95)
                prev = root

            # Snare en el 3 (half-time)
            place(SN, b0 + 8, 1.0, rv=0.45)
            if last_of_section:
                for s in (13, 14, 15):
                    place(SN, b0 + s, 0.35 + 0.15 * (s - 13), rv=0.3)
        else:
            prev = None
        bar += 1

# Golpe final
end = BARS * SPB
place(K, end)
place(bass808(31, 2.5), end, 0.8)
place(SN, end, 0.8, rv=0.8)
for k, m in enumerate(chords[0]):
    place(piano(m + 12, 2.5), end + k * 0.1, 1.0, rv=0.8)

mix = dry + reverb(send) * np.max(np.abs(send)) * 0.6
mix = np.tanh(mix * 1.25)
mix /= np.max(np.abs(mix)) / 0.93
out = Path(__file__).with_name("trap_latino_castillo.wav")
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"Listo: {out}  ({TOTAL / SR:.1f} s, {BPM} BPM)")
