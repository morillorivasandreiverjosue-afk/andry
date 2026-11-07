"""Edición del video de la apertura del carro, con música y efectos al ritmo.

1. Restaura la imagen: quita el tono azul y la viñeta oscura, sube a 1080x1920, limpia y enfoca.
2. Ritmo: intro normal, la parte de trabajo acelerada, y la apertura de la puerta en cámara lenta.
3. Música propia generada con código (100 BPM) y efectos cuadrados con el beat:
   zoom en cada compás, sacudida y destello cuando se abre la puerta.

Uso: python3 editar.py <video_original.mp4> <salida.mp4> [trap|dembow|nostalgico]
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image
from scipy import signal

SR = 44100
W, H, FPS = 1080, 1920, 60
BPM = 100
BEAT = 60 / BPM          # 0.6 s
BAR = 4 * BEAT           # 2.4 s

# Tramos del original: (inicio, fin, velocidad)
TRAMOS = [
    (0.0, 2.4, 1.0),       # intro             -> 1 compás
    (2.4, 38.6, 1.81),     # trabajo acelerado -> ~20 s
    (38.6, 40.2, 1.0),     # tensión antes de abrir
    (40.2, 42.4, 0.6),     # la puerta se abre en cámara lenta
]
DROP = 24.0              # momento (en el video final) en que se abre la puerta
TOTAL = 28.8             # 12 compases
ESTILO = sys.argv[3] if len(sys.argv) > 3 else "trap"
if ESTILO == "nostalgico":   # video entero a velocidad normal, sin efectos, solo fundidos
    TRAMOS = [(0.0, 42.4, 1.0)]
    TOTAL = 45.0                 # el último cuadro (puerta abierta) se queda quieto mientras se apaga
    ENTRADA, SALIDA = 3.0, 3.5   # segundos de fundido desde negro y hacia negro


# ---------------------------------------------------------------- imagen
def filtro_video():
    color = ("vignette=angle=PI/5:mode=backward,"
             "colorlevels=rimax=0.62:gimax=0.80:bimax=0.95,"
             "colorbalance=rm=-0.04:bm=-0.03:gs=0.02,"
             "eq=gamma=1.08:saturation=1.05:contrast=1.06,"
             "hqdn3d=2:2:4:4,"
             f"scale={W}:-2:flags=lanczos,crop={W}:{H},cas=0.5,fps={FPS}")
    if ESTILO == "nostalgico":   # tono apagado: gris, negros lavados y un toque de azul
        color += (",eq=saturation=0.38:contrast=0.88:brightness=-0.02,"
                  "curves=r='0/0.09 0.5/0.47 1/0.88':g='0/0.10 0.5/0.49 1/0.90':b='0/0.15 0.5/0.54 1/0.93',"
                  "vignette=angle=PI/4.5")
    partes, nombres = [], []
    for i, (a, b, v) in enumerate(TRAMOS):
        partes.append(f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/{v}[t{i}]")
        nombres.append(f"[t{i}]")
    partes.append(f"{''.join(nombres)}concat=n={len(TRAMOS)}:v=1:a=0,{color},"
                  f"tpad=stop_mode=clone:stop_duration=3,trim=0:{TOTAL},format=rgb24[v]")
    return ";".join(partes)


TITULO = "APERTURA DE CARRO"
TITULO_ENTRA, TITULO_SALE = (1.2, 2.4), (5.0, 6.4)    # aparece poco a poco y luego se va


def capa_titulo():
    from PIL import ImageDraw, ImageFilter, ImageFont
    fuente = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Light.otf", 76)
    espacio = 14                                              # letras separadas, estilo elegante
    anchos = [fuente.getlength(ch) for ch in TITULO]
    total = sum(anchos) + espacio * (len(TITULO) - 1)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x, y = (W - total) / 2, H * 0.44
    for ch, a in zip(TITULO, anchos):
        d.text((x, y), ch, font=fuente, fill=(240, 242, 246, 255))
        x += a + espacio
    linea_y = y + 118
    d.line([(W / 2 - 120, linea_y), (W / 2 + 120, linea_y)], fill=(240, 242, 246, 200), width=2)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sombra.putalpha(capa.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.55))
    fondo = Image.alpha_composite(sombra, capa)
    rgb = np.asarray(fondo.convert("RGB")).astype(np.float32)
    alfa = np.asarray(fondo.getchannel("A")).astype(np.float32)[:, :, None] / 255
    return rgb, alfa


_TITULO = None


def efectos(cuadro, t, rng):
    if ESTILO == "nostalgico":
        global _TITULO
        arr = np.asarray(cuadro).astype(np.float32)
        (e0, e1), (s0, s1) = TITULO_ENTRA, TITULO_SALE
        if e0 < t < s1:
            if _TITULO is None:
                _TITULO = capa_titulo()
            k = min(1.0, (t - e0) / (e1 - e0), (s1 - t) / (s1 - s0))
            k = k * k * (3 - 2 * k)                             # transición suave
            rgb, alfa = _TITULO
            arr = arr * (1 - alfa * k) + rgb * alfa * k
        a = min(1.0, t / ENTRADA, (TOTAL - t) / SALIDA)
        a = max(0.0, a) ** 1.6 if a < 1 else 1.0            # curva suave: aparece y se va poco a poco
        return np.clip(arr * a, 0, 255).astype(np.uint8)
    """Zoom de golpe en cada compás, sacudida y destello en la apertura."""
    if ESTILO == "dembow":                                   # golpe pequeño en cada tiempo
        zoom = 1.0 + (0.035 * np.exp(-((t % BEAT) / 0.1)) if t >= BAR else 0.0)
    else:
        zoom = 1.0 + 0.06 * np.exp(-((t % BAR) / 0.18))      # golpe en cada compás
    if t >= BAR and ESTILO != "dembow":                                             # golpecito en el tiempo 3 (aplauso)
        zoom += 0.025 * np.exp(-(((t - 2 * BEAT) % BAR) / 0.12))
    dx = dy = 0.0
    d = t - DROP
    if 0 <= d < 0.9:                                         # sacudida al abrir la puerta
        fuerza = 22 * np.exp(-d / 0.25)
        dx, dy = rng.uniform(-fuerza, fuerza, 2)
        zoom += 0.12 * np.exp(-d / 0.3)
    if t > DROP:                                             # empuje lento final
        zoom += 0.05 * min(1.0, (t - DROP) / 4.8)
    if zoom > 1.0005 or dx or dy:
        cx, cy = W / 2, H / 2
        s = 1 / zoom
        cuadro = cuadro.transform((W, H), Image.AFFINE,
                                  (s, 0, cx - s * cx + dx, 0, s, cy - s * cy + dy), Image.BICUBIC)
    arr = np.asarray(cuadro).astype(np.float32)
    if ESTILO == "dembow" and 0 <= d < 0.6:                 # separación de colores (glitch)
        o = int(28 * (1 - d / 0.6))
        arr = arr.copy()
        arr[:, :, 0] = np.roll(arr[:, :, 0], o, 1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -o, 1)
    elif 0 <= d < 0.35:                                      # destello blanco
        a = 0.85 * (1 - d / 0.35)
        arr = arr * (1 - a) + 255 * a
    if t < 0.5:                                              # entrada desde negro
        arr *= t / 0.5
    if t > TOTAL - 1.0:                                      # salida a negro
        arr *= max(0.0, (TOTAL - t) / 1.0)
    return np.clip(arr, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- música
def n(seg):
    return int(seg * SR)


def env(largo, ataque, tau):
    t = np.arange(n(largo)) / SR
    return np.minimum(1, t / max(ataque, 1e-4)) * np.exp(-t / tau)


def lp(x, f):
    b, a = signal.butter(2, f / (SR / 2))
    return signal.lfilter(b, a, x)


def hp(x, f):
    b, a = signal.butter(2, f / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def kick():
    t = np.arange(n(0.45)) / SR
    f = 45 + 110 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)


def clap(rng):
    x = hp(rng.standard_normal(n(0.3)), 900) * env(0.3, 0.001, 0.07)
    x[:n(0.02)] *= 1 + np.sin(np.linspace(0, 9 * np.pi, n(0.02)))  # palmadas múltiples
    return x * 0.6


def hat(rng, largo=0.05):
    return hp(rng.standard_normal(n(largo)), 7000) * env(largo, 0.0005, largo / 4) * 0.35


def bajo808(f, largo):
    t = np.arange(n(largo)) / SR
    x = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * t))
    return np.tanh(1.8 * x) * np.minimum(1, t / 0.005) * np.exp(-t / (largo * 0.7))


def pluck(f, largo):
    t = np.arange(n(largo)) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.4 for k in range(1, 7))
    return lp(x, 3500) * env(largo, 0.003, 0.22)


def pad(fs, largo):
    t = np.arange(n(largo)) / SR
    x = sum(np.sin(2 * np.pi * f * (1 + d) * t) for f in fs for d in (-0.004, 0, 0.004))
    return lp(x, 1400) * np.minimum(1, t / 0.4) * np.minimum(1, (largo - t) / 0.3 + 1e-9).clip(0, 1) / (3 * len(fs))


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def musica():
    if ESTILO == "nostalgico":
        return musica_nostalgica()
    return musica_dembow() if ESTILO == "dembow" else musica_trap()


def piano_suave(f, largo, fuerza=1.0):
    t = np.arange(n(largo)) / SR
    x = np.zeros_like(t)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)             # leve inarmonía de cuerda real
        x += np.sin(2 * np.pi * fk * t) / k ** 1.6 * np.exp(-t * (0.9 + 0.7 * k))
    x *= np.minimum(1, t / 0.006) * fuerza
    return lp(x, 2600 + 1500 * fuerza)


def musica_nostalgica():
    """Piano lo-fi, cuerdas suaves, cinta que ondula y crujido de disco viejo."""
    rng = np.random.default_rng(21)
    largo = TOTAL + 4
    L, R = np.zeros(n(largo)), np.zeros(n(largo))

    def poner(x, t, v=1.0, pan=0.0):
        i = n(t)
        x = x[: len(L) - i]
        L[i:i + len(x)] += x * v * (1 - max(0, pan))
        R[i:i + len(x)] += x * v * (1 + min(0, pan))

    negra = 60 / 70
    compas = 4 * negra
    # Fmaj7 - Em7 - Dm7 - Cmaj7 (bajada clásica que suena a recuerdo)
    acordes = [(41, [57, 60, 64, 65]), (40, [55, 59, 62, 64]), (38, [53, 57, 60, 62]), (36, [52, 55, 59, 60])]
    melodia = {0: [(0, 76), (1.5, 74), (2, 72)], 1: [(0, 71), (2, 67)], 2: [(0, 69), (1, 72), (2.5, 74)],
               3: [(0, 72), (2, 71)]}
    c = 0
    while c * compas < TOTAL:
        t0 = c * compas
        bajo, notas = acordes[c % 4]
        poner(piano_suave(hz(bajo), compas * 1.2, 0.8), t0, 0.35)
        for k in range(8):                                   # arpegio en corcheas
            m = notas[[0, 1, 2, 3, 2, 1, 2, 3][k]]
            poner(piano_suave(hz(m), 2.0, 0.55 + 0.1 * rng.random()), t0 + k * negra / 2 + rng.normal(0, 0.008),
                  0.16, pan=-0.25 + 0.5 * (k % 2))
        if c >= 4:                                           # entra la melodía
            for b, m in melodia[c % 4]:
                poner(piano_suave(hz(m), 3.0, 0.9), t0 + b * negra, 0.24, pan=0.1)
        poner(pad([hz(m - 12) for m in notas[:3]], compas + 0.6), t0, 0.35 if c >= 2 else 0.18)
        if 4 <= c < 11:                                      # batería lo-fi muy suave
            for b in range(4):
                if b in (0, 2):
                    poner(lp(kick(), 900), t0 + b * negra + (0.5 * negra if b == 2 else 0), 0.35)
                if b in (1, 3):
                    poner(lp(snare(rng), 3500), t0 + b * negra, 0.13)
                for h in range(2):
                    poner(lp(hat(rng, 0.04), 9000), t0 + b * negra + h * negra / 2 + 0.02, 0.18)
        c += 1
    mezcla = np.stack([L, R], 1)
    # reverberación suave
    ir = rng.standard_normal((n(2.2), 2)) * np.exp(-np.arange(n(2.2)) / SR / 0.55)[:, None]
    ir = np.stack([lp(ir[:, 0], 3000), lp(ir[:, 1], 3000)], 1) * 0.02
    mezcla = mezcla + np.stack([signal.fftconvolve(mezcla[:, i], ir[:, i])[: len(mezcla)] for i in range(2)], 1)
    # cinta vieja: el tono ondula un poquito (wow & flutter)
    t = np.arange(len(mezcla)) / SR
    retraso = 0.0025 * np.sin(2 * np.pi * 0.45 * t) + 0.0004 * np.sin(2 * np.pi * 6.0 * t)
    idx = np.clip(np.arange(len(mezcla)) - (retraso + 0.003) * SR, 0, len(mezcla) - 1)
    mezcla = np.stack([np.interp(idx, np.arange(len(mezcla)), mezcla[:, i]) for i in range(2)], 1)
    mezcla = np.stack([lp(hp(mezcla[:, i], 60), 5500) for i in range(2)], 1)  # sonido cálido de radio vieja
    # crujido de disco
    crujido = np.zeros(len(mezcla))
    pos = rng.integers(0, len(crujido) - 50, int(TOTAL * 9))
    crujido[pos] = rng.uniform(-1, 1, len(pos)) * rng.uniform(0.1, 1, len(pos)) ** 3
    crujido = hp(crujido, 1500) * 0.5 + lp(rng.standard_normal(len(crujido)), 1200) * 0.012
    mezcla += crujido[:, None] * np.array([0.9, 1.0])
    mezcla = mezcla[: n(TOTAL)]
    mezcla /= np.abs(mezcla).max()
    mezcla = np.tanh(mezcla * 1.2)
    tt = np.arange(len(mezcla)) / SR                          # fundidos iguales al video
    vol = np.clip(np.minimum(tt / ENTRADA, (TOTAL - tt) / SALIDA), 0, 1) ** 1.2
    mezcla *= vol[:, None]
    return (mezcla / np.abs(mezcla).max() * 0.9).astype(np.float32)


def snare(rng):
    t = np.arange(n(0.2)) / SR
    tono = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04)
    return (hp(rng.standard_normal(len(t)), 1800) * np.exp(-t / 0.06) * 0.7 + tono * 0.5)


def musica_dembow():
    rng = np.random.default_rng(11)
    L, R = np.zeros(n(TOTAL + 3)), np.zeros(n(TOTAL + 3))

    def poner(x, t, v=1.0, pan=0.0):
        i = n(t)
        x = x[: len(L) - i]
        L[i:i + len(x)] += x * v * (1 - max(0, pan))
        R[i:i + len(x)] += x * v * (1 + min(0, pan))

    acordes = [(50, [62, 65, 69]), (46, [62, 65, 70]), (53, [60, 65, 69]), (48, [60, 64, 67])]  # Dm Bb F C
    melodia = [74, 0, 77, 74, 0, 72, 69, 0, 74, 0, 77, 79, 77, 0, 74, 72]  # semicorcheas de 2 en 2 (0 = silencio)
    for c in range(int(TOTAL / BAR)):
        t0 = c * BAR
        raiz, notas = acordes[c % 4]
        intro, subida, final = c == 0, c == 9, t0 >= DROP
        poner(pad([hz(m) for m in notas], BAR + 0.3), t0, 0.45)
        for k, m in enumerate(melodia):                      # marimba/pluck reguetonero
            if m and not (intro and k % 4):
                poner(pluck(hz(m - (12 if final else 0)), 0.35), t0 + k * BEAT / 4, 0.2,
                      pan=-0.3 if k % 2 else 0.3)
        if intro:
            continue
        for b in range(4):                                   # dembow: bum - ch - bum-chik
            tb = t0 + b * BEAT
            if not subida or b == 0:
                poner(kick(), tb, 0.9)
            if not subida:
                poner(snare(rng), tb + 0.75 * BEAT, 0.55)
                if b % 2 == 1:
                    poner(snare(rng), tb + 0.5 * BEAT, 0.4)
            for h in range(2):
                poner(hat(rng, 0.04), tb + h * BEAT / 2 + BEAT / 4, 0.5, pan=0.25)
        if not subida:
            poner(bajo808(hz(raiz - 12), BAR * 0.95), t0, 0.55)
        else:
            for k in range(16):
                poner(snare(rng), t0 + k * BEAT / 4, 0.1 + 0.5 * k / 16)
            barrido = lp(rng.standard_normal(n(BAR)), 4000) * np.linspace(0, 0.45, n(BAR)) ** 2
            poner(barrido, t0)
    t = np.arange(n(2.5)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(32 + 90 * np.exp(-t / 0.07)) / SR) * np.exp(-t / 0.6)
    poner(boom + lp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.2) * 0.4, DROP, 1.0)
    # sirena corta tipo 'air horn' en el golpe
    th = np.arange(n(0.9)) / SR
    horn = sum(np.sign(np.sin(2 * np.pi * f * th)) for f in (466, 470, 698)) * np.exp(-th / 0.5) * 0.08
    poner(lp(horn, 3000), DROP + 0.02, 1.0)
    mezcla = np.tanh(np.stack([L, R], 1)[: n(TOTAL)] * 1.3)
    caida = np.ones(len(mezcla))
    caida[-n(1.5):] = np.linspace(1, 0, n(1.5))
    mezcla *= caida[:, None]
    return (mezcla / np.abs(mezcla).max() * 0.95).astype(np.float32)


def musica_trap():
    rng = np.random.default_rng(7)
    L, R = np.zeros(n(TOTAL + 3)), np.zeros(n(TOTAL + 3))

    def poner(x, t, v=1.0, pan=0.0):
        i = n(t)
        x = x[: len(L) - i]
        L[i:i + len(x)] += x * v * (1 - max(0, pan))
        R[i:i + len(x)] += x * v * (1 + min(0, pan))

    acordes = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]  # Am F C G
    melodia = [76, 72, 69, 72, 74, 72, 69, 67]   # notas del pluck por corchea (ciclo)
    compases = int(TOTAL / BAR)
    for c in range(compases):
        t0 = c * BAR
        raiz, notas = acordes[c % 4]
        intro = c == 0
        subida = c == 9                         # compás antes de abrir la puerta
        final = t0 >= DROP
        poner(pad([hz(m) for m in notas], BAR + 0.3), t0, 0.5 if not final else 0.7)
        # melodía
        for k in range(8):
            if intro and k % 2:
                continue
            poner(pluck(hz(melodia[(c * 8 + k) % 8] - (12 if final else 0)), 0.5), t0 + k * BEAT / 2,
                  0.22, pan=0.35 if k % 2 else -0.35)
        if intro:
            for k in range(8):
                poner(hat(rng), t0 + k * BEAT / 2, 0.6)
            continue
        # batería
        for k in (0, 2.5) if not subida else (0,):
            poner(kick(), t0 + k * BEAT, 0.95)
        if not subida:
            poner(clap(rng), t0 + 2 * BEAT, 0.8)
            poner(bajo808(hz(raiz - 24), BEAT * 2.4), t0, 0.7)
            poner(bajo808(hz(raiz - 24), BEAT * 1.4), t0 + 2.5 * BEAT, 0.6)
        for k in range(16):                                  # hi-hats en semicorcheas con redobles
            tk = t0 + k * BEAT / 4
            if k % 2 == 0 or (c % 2 == 1 and k >= 12):
                poner(hat(rng), tk, 0.7 if k % 4 == 0 else 0.45, pan=0.2)
        if subida:                                           # redoble y subida antes del golpe
            for k in range(16):
                poner(clap(rng), t0 + k * BEAT / 4, 0.15 + 0.5 * k / 16)
            largo = BAR
            ruido = rng.standard_normal(n(largo))
            corte = np.linspace(300, 9000, n(largo))
            sube = np.zeros_like(ruido)
            for j in range(0, len(ruido), 2048):              # filtro que se abre poco a poco
                sube[j:j + 2048] = lp(ruido[max(0, j - 2048):j + 2048], corte[j])[-len(ruido[j:j + 2048]):]
            poner(sube * np.linspace(0, 0.5, n(largo)) ** 1.5, t0)
    # golpe al abrir la puerta
    t = np.arange(n(2.5)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 80 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.7)
    boom += lp(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.25) * 0.5
    poner(boom, DROP, 1.0)
    # 'whoosh' de entrada
    wl = 0.6
    poner(lp(rng.standard_normal(n(wl)), 2000) * np.sin(np.linspace(0, np.pi, n(wl))) ** 2, 0.0, 0.3)

    mezcla = np.stack([L, R], 1)[: n(TOTAL)]
    mezcla = np.tanh(mezcla * 1.3)                           # compresión suave
    caida = np.ones(len(mezcla))
    caida[-n(1.5):] = np.linspace(1, 0, n(1.5))
    mezcla *= caida[:, None]
    return (mezcla / np.abs(mezcla).max() * 0.95).astype(np.float32)


# ---------------------------------------------------------------- render
def main():
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "musica.wav"
        sf.write(wav, musica(), SR, subtype="PCM_16")
        lee = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(entrada), "-filter_complex", filtro_video(),
                                "-map", "[v]", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        escribe = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(wav),
                                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                                    str(salida)], stdin=subprocess.PIPE)
        rng = np.random.default_rng(3)
        tam = W * H * 3
        k = 0
        while True:
            datos = lee.stdout.read(tam)
            if len(datos) < tam:
                break
            cuadro = Image.frombytes("RGB", (W, H), datos)
            escribe.stdin.write(efectos(cuadro, k / FPS, rng).tobytes())
            k += 1
            if k % 300 == 0:
                print(f"{k / FPS:.0f}s / {TOTAL}s", flush=True)
        escribe.stdin.close()
        escribe.wait()
        lee.wait()
    print("Listo:", salida)


if __name__ == "__main__":
    main()
