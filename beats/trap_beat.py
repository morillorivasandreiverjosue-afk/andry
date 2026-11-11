"""Genera un beat de trap (140 BPM, Do menor) como archivo WAV.

Uso:
    python3 beats/trap_beat.py            # crea beats/trap_beat.wav
Requiere solo numpy.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 140
STEP = 60 / BPM / 4  # duración de una semicorchea (1/16)
BARS = 16
STEPS_PER_BAR = 16
TOTAL = int(SR * (BARS * STEPS_PER_BAR * STEP + 2.5))

rng = np.random.default_rng(7)


def note_freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n, decay, attack=0.002):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    return a * np.exp(-t / decay)


def highpass(x, amount=0.95):
    y = np.zeros_like(x)
    prev_x = prev_y = 0.0
    for i, v in enumerate(x):
        prev_y = amount * (prev_y + v - prev_x)
        prev_x = v
        y[i] = prev_y
    return y


def lowpass(x, alpha):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


# ---------- Sonidos ----------
def kick():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.03)
    phase = 2 * np.pi * np.cumsum(f) / SR
    click = rng.standard_normal(n) * env(n, 0.003)
    return np.tanh(2.5 * np.sin(phase) * env(n, 0.12)) * 0.9 + click * 0.15


def bass808(midi, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    base = note_freq(midi)
    f = base * (1 + 0.6 * np.exp(-t / 0.025))  # golpe de tono al inicio
    phase = 2 * np.pi * np.cumsum(f) / SR
    e = env(n, 0.9, attack=0.004)
    e[-int(SR * 0.02):] *= np.linspace(1, 0, int(SR * 0.02))
    return np.tanh(1.8 * np.sin(phase)) * e * 0.85


def snare():
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    noise = highpass(rng.standard_normal(n), 0.9) * env(n, 0.07)
    tone = np.sin(2 * np.pi * 190 * t) * env(n, 0.05)
    return (noise * 0.55 + tone * 0.5) * 0.8


def clap():
    n = int(SR * 0.35)
    out = np.zeros(n)
    noise = highpass(rng.standard_normal(n), 0.85)
    for off in (0.0, 0.009, 0.019, 0.028):
        o = int(off * SR)
        out[o:] += noise[: n - o] * env(n - o, 0.012 if off < 0.028 else 0.09)
    return out * 0.35


def hat(open_=False):
    n = int(SR * (0.25 if open_ else 0.05))
    noise = highpass(highpass(rng.standard_normal(n), 0.7), 0.7)
    return noise * env(n, 0.08 if open_ else 0.012) * 0.28


def bell(midi, length=0.9):
    n = int(SR * length)
    t = np.arange(n) / SR
    f = note_freq(midi)
    s = (np.sin(2 * np.pi * f * t)
         + 0.5 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t / 0.15)
         + 0.25 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t / 0.06))
    return s * env(n, 0.35, attack=0.003) * 0.16


def pad(midis, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in midis:
        f = note_freq(m)
        for det in (-0.12, 0.12):
            s += np.sign(np.sin(2 * np.pi * f * (1 + det / 100) * t))
    s = lowpass(s, 0.03)
    e = np.minimum(1, t / 0.4) * np.minimum(1, (length - t) / 0.3)
    return s * e * 0.025


# ---------- Mezcla ----------
mix = np.zeros((TOTAL, 2))


def place(sample, step, gain=1.0, pan=0.0):
    i = int(round(step * STEP * SR))
    j = min(TOTAL, i + len(sample))
    l, r = gain * (1 - max(0, pan)), gain * (1 + min(0, pan))
    mix[i:j, 0] += sample[: j - i] * l
    mix[i:j, 1] += sample[: j - i] * r


K, SN, CL = kick(), snare(), clap()
HC, HO = hat(), hat(True)

# Progresión Do menor: Cm - Ab - Fm - G  (i - VI - iv - V)
chords = [[60, 63, 67], [56, 60, 63], [53, 56, 60], [55, 59, 62]]
roots808 = [36, 32, 29, 31]
# Melodía de campana por compás (paso, nota)
melodies = [
    [(0, 72), (3, 75), (6, 79), (10, 75), (12, 74)],
    [(0, 72), (3, 75), (6, 80), (10, 79), (13, 75)],
    [(0, 77), (3, 75), (6, 72), (10, 75), (12, 77)],
    [(0, 74), (3, 71), (6, 74), (8, 79), (12, 77), (14, 74)],
]

kick_pat = [0, 7, 10]          # patrón de kick típico de trap
kick_pat_b = [0, 3, 7, 11, 14]

for bar in range(BARS):
    b0 = bar * STEPS_PER_BAR
    c = bar % 4
    intro = bar < 4
    break_ = bar in (11,)

    # Melodía y pad siempre
    for s, m in melodies[c]:
        place(bell(m), b0 + s, pan=-0.3 if s % 2 else 0.3)
        place(bell(m + 12, 0.4), b0 + s + 0.75, 0.35, pan=0.5)  # eco
    place(pad(chords[c], STEPS_PER_BAR * STEP), b0)

    # Hi-hats (con rolls)
    roll_bar = bar % 2 == 1
    s = 0.0
    while s < 16:
        if roll_bar and 12 <= s < 14:
            sub = 1 / 3            # tresillos
        elif roll_bar and 14 <= s < 16:
            sub = 0.25             # fusas
        elif s in (6, 7) and bar % 4 == 2:
            sub = 0.5
        else:
            sub = 1 if intro else 0.5
        accent = 1.0 if abs(s - round(s)) < 1e-6 and int(round(s)) % 4 == 0 else 0.65
        place(HC, b0 + s, (0.55 if intro else 1.0) * accent, pan=0.2)
        s = round(s + sub, 6)
    if not intro:
        place(HO, b0 + 14 if bar % 2 == 0 else b0 + 6, 0.7, pan=-0.2)

    if intro or break_:
        continue

    # Kick + 808
    pat = kick_pat_b if bar % 4 == 3 else kick_pat
    for i, s in enumerate(pat):
        place(K, b0 + s)
        nxt = pat[i + 1] if i + 1 < len(pat) else 16
        root = roots808[c] + (12 if (bar % 4 == 3 and s == 14) else 0)
        place(bass808(root, (nxt - s) * STEP), b0 + s, 0.95)

    # Snare + clap en el tiempo 3
    place(SN, b0 + 8)
    place(CL, b0 + 8, pan=0.1)
    if bar % 4 == 3:
        place(SN, b0 + 15, 0.5)

# Golpe final
end = BARS * STEPS_PER_BAR
place(K, end)
place(bass808(36, 2.0), end)
place(CL, end)
place(bell(72, 2.0), end)

# Master: limitador suave y normalización
mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) / 0.95
out = Path(__file__).with_name("trap_beat.wav")
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"Listo: {out}  ({TOTAL / SR:.1f} s, {BPM} BPM)")
