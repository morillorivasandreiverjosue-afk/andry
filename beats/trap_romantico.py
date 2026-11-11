"""Genera un beat de trap romántico (136 BPM, La menor) como archivo WAV.

Acordes cálidos tipo R&B (Fmaj7 - G6 - Em7 - Am9), piano eléctrico,
arpegio de cuerda pulsada, 808 suave con glides, clap con reverb
y hi-hats discretos.

Uso:
    python3 beats/trap_romantico.py       # crea beats/trap_romantico.wav
Requiere solo numpy.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 136
STEP = 60 / BPM / 4
BARS = 20
SPB = 16
TOTAL = int(SR * (BARS * SPB * STEP + 4.0))

rng = np.random.default_rng(14)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n, decay, attack=0.003):
    t = np.arange(n) / SR
    return np.clip(t / attack, 0, 1) * np.exp(-t / decay)


def onepole_lp(x, alpha):
    # filtro paso bajo de un polo, vectorizado por bloques vía IIR simple
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
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


def reverb(x, seconds=2.4, damp=3.0):
    """Reverb por convolución con respuesta impulsional sintética (FFT)."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * damp)
        ir = np.convolve(ir, np.ones(6) / 6, mode="same")  # más oscura
        ir[: int(0.015 * SR)] = 0  # pre-delay
        m = len(x) + n
        size = 1 << (m - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[:, ch], size) * np.fft.rfft(ir, size), size)
        out[:, ch] = y[: len(x)]
    return out / np.max(np.abs(out) + 1e-9)


# ---------- Instrumentos ----------
def epiano(midi, length):
    """Piano eléctrico tipo Rhodes (síntesis FM)."""
    n = int(SR * (length + 1.2))
    t = np.arange(n) / SR
    f = hz(midi)
    idx = 1.6 * np.exp(-t / 0.35) + 0.2
    body = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    tine = np.sin(2 * np.pi * f * 14.0 * t) * np.exp(-t / 0.03) * 0.15
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    e = env(n, 1.4, 0.004)
    rel = t > length
    e[rel] *= np.exp(-(t[rel] - length) / 0.25)
    return (body + tine) * e * trem * 0.07


def pluck(midi, length=1.2):
    """Cuerda pulsada (Karplus-Strong)."""
    n = int(SR * length)
    p = int(SR / hz(midi))
    buf = onepole_lp(rng.uniform(-1, 1, p), 0.5)
    out = np.empty(n)
    for i in range(n):
        v = buf[i % p]
        out[i] = v
        buf[i % p] = 0.996 * 0.5 * (v + buf[(i + 1) % p])
    return out * env(n, 0.6, 0.001) * 0.18


def kick():
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.025)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.1)) * 0.75


def bass808(midi, length, from_midi=None):
    n = int(SR * length)
    t = np.arange(n) / SR
    target = hz(midi)
    if from_midi is None:
        f = target * (1 + 0.3 * np.exp(-t / 0.02))
    else:  # glide desde la nota anterior
        start = hz(from_midi)
        f = target + (start - target) * np.exp(-t / 0.06)
    s = np.tanh(1.3 * np.sin(2 * np.pi * np.cumsum(f) / SR))
    e = env(n, 1.6, 0.006)
    fade = min(n, int(SR * 0.04))
    e[-fade:] *= np.linspace(1, 0, fade)
    return s * e * 0.8


def clap():
    n = int(SR * 0.4)
    out = np.zeros(n)
    noise = hp(rng.standard_normal(n), 0.8)
    for k, off in enumerate((0.0, 0.008, 0.017, 0.025)):
        o = int(off * SR)
        out[o:] += noise[: n - o] * env(n - o, 0.012 if k < 3 else 0.11)
    return out * 0.28


def snap():
    n = int(SR * 0.12)
    return hp(rng.standard_normal(n), 0.6) * env(n, 0.018, 0.0005) * 0.3


def hat(open_=False):
    n = int(SR * (0.3 if open_ else 0.045))
    x = hp(hp(rng.standard_normal(n), 0.65), 0.65)
    return x * env(n, 0.09 if open_ else 0.01) * 0.17


# ---------- Mezcla ----------
dry = np.zeros((TOTAL, 2))
wet_send = np.zeros((TOTAL, 2))


def place(sample, step, gain=1.0, pan=0.0, send=0.0):
    i = int(round(step * STEP * SR))
    j = min(TOTAL, i + len(sample))
    s = sample[: j - i]
    l, r = gain * (1 - max(0, pan)), gain * (1 + min(0, pan))
    dry[i:j, 0] += s * l
    dry[i:j, 1] += s * r
    if send:
        wet_send[i:j, 0] += s * l * send
        wet_send[i:j, 1] += s * r * send


K, CL, SNP = kick(), clap(), snap()
HC, HO = hat(), hat(True)

# Fmaj7 - G6 - Em7 - Am9
chords = [
    [53, 57, 60, 64],
    [55, 59, 62, 64],
    [52, 55, 59, 62],
    [57, 60, 64, 67, 71],
]
roots = [29, 31, 28, 33]
# Arpegio por compás (paso -> índice de nota del acorde, una octava arriba)
arp = [(0, 0), (2, 2), (4, 3), (6, 1), (8, 2), (10, 3), (12, 2), (14, 1)]
# Melodía suave (piano, registro agudo) para las secciones completas
melody = [
    [(0, 76), (6, 74), (8, 72), (12, 69)],
    [(0, 71), (6, 72), (8, 74), (14, 76)],
    [(0, 74), (4, 71), (8, 67), (12, 71)],
    [(0, 72), (8, 69), (11, 71), (14, 72)],
]

prev_root = None
for bar in range(BARS):
    b0 = bar * SPB
    c = bar % 4
    intro = bar < 4
    brk = 12 <= bar < 16
    outro = bar >= 19
    full = not (intro or brk or outro)

    # Acordes de piano (ligeramente "rasgueados")
    for k, m in enumerate(chords[c]):
        place(epiano(m, SPB * STEP * 0.95), b0 + k * 0.08, 1.0,
              pan=(k - 2) * 0.15, send=0.5)

    # Arpegio de cuerda
    if not outro:
        for s, ni in arp:
            notes = chords[c]
            m = notes[ni % len(notes)] + 12
            place(pluck(m), b0 + s, 0.8 if not brk else 0.55,
                  pan=0.35 if s % 4 else -0.35, send=0.35)

    # Melodía
    if full or brk:
        for s, m in melody[c]:
            place(epiano(m + 12, 4 * STEP), b0 + s, 0.9, pan=0.1, send=0.6)

    # Hi-hats suaves
    if not outro:
        roll = full and bar % 4 == 3
        s = 0.0
        while s < 16:
            sub = 1 / 3 if roll and 12 <= s < 16 else (2 if intro else 1)
            g = 1.0 if int(s) % 4 == 0 and s == int(s) else 0.6
            place(HC, b0 + s, g * (0.6 if intro or brk else 1.0), pan=0.25)
            s = round(s + sub, 6)
        if full and bar % 2 == 1:
            place(HO, b0 + 14, 0.6, pan=-0.25, send=0.2)

    if not full:
        prev_root = None
        continue

    # Kick + 808 con glide
    pat = [0, 10] if bar % 2 == 0 else [0, 3, 10, 13]
    for i, s in enumerate(pat):
        place(K, b0 + s)
        nxt = pat[i + 1] if i + 1 < len(pat) else 16
        root = roots[c]
        if bar % 4 == 3 and s == 13:
            root += 7  # subidita antes de volver al inicio
        place(bass808(root, (nxt - s) * STEP, prev_root), b0 + s, 0.9)
        prev_root = root

    # Clap en el 3 con reverb, snaps de adorno
    place(CL, b0 + 8, 1.0, send=0.5)
    place(SNP, b0 + 12 if bar % 2 else b0 + 6, 0.6, pan=-0.2, send=0.4)

# Final: acorde sostenido
end = BARS * SPB
for k, m in enumerate(chords[3]):
    place(epiano(m, 2.5), end + k * 0.12, 1.0, pan=(k - 2) * 0.15, send=0.7)
place(bass808(33, 2.5), end, 0.7)

# Master
mix = dry + reverb(wet_send) * np.max(np.abs(wet_send)) * 0.55
mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix)) / 0.93
out = Path(__file__).with_name("trap_romantico.wav")
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"Listo: {out}  ({TOTAL / SR:.1f} s, {BPM} BPM)")
