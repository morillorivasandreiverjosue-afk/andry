"""Genera los efectos de sonido y la voz del reel en public/reel/.

Uso:  python3 scripts/generar-audio.py RUTA_PIPER RUTA_MODELO_VOZ.onnx
  - Piper:  https://github.com/rhasspy/piper/releases (piper_linux_x86_64.tar.gz)
  - Voz:    https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-es-carlfm-x-low.tar.gz
El texto de la voz está en src/reel/guion.json. Requiere numpy y ffmpeg.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "public" / "reel"
SALIDA.mkdir(parents=True, exist_ok=True)
GUION = json.loads((RAIZ / "src" / "reel" / "guion.json").read_text())
rng = np.random.default_rng(7)


def guardar(nombre, x):
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * 0.9, -1, 1)
    with wave.open(str(SALIDA / nombre), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def t(seg):
    return np.arange(int(SR * seg)) / SR


def env(n, ataque=0.005, caida=None):
    e = np.ones(n)
    a = max(1, int(SR * ataque))
    e[:a] = np.linspace(0, 1, a)
    if caida:
        e *= np.exp(-np.arange(n) / (SR * caida))
    return e


def paso_banda(x, centro, ancho=0.3):
    f = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    f *= np.exp(-((np.log(fr + 1) - np.log(centro)) ** 2) / (2 * ancho**2))
    return np.fft.irfft(f, len(x))


def barrido_ruido(seg, f0, f1, ancho=0.35):
    """Ruido filtrado cuya frecuencia central se desplaza (whoosh/riser)."""
    n = int(SR * seg)
    ruido = rng.standard_normal(n)
    trozos = 40
    out = np.zeros(n)
    for i in range(trozos):
        a, b = i * n // trozos, (i + 1) * n // trozos
        c = f0 * (f1 / f0) ** (i / trozos)
        out[a:b] = paso_banda(ruido, c, ancho)[a:b]
    return out


def medir(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    return float(r.stdout)


# ---------- Efectos ----------
n = int(SR * 0.6)
guardar("whoosh.wav", barrido_ruido(0.6, 300, 6000) * np.sin(np.linspace(0, np.pi, n)) ** 2)

tt = t(1.2)
frec = 110 * np.exp(-tt * 3) + 38
boom = np.sin(2 * np.pi * np.cumsum(frec) / SR) * env(len(tt), 0.002, 0.45)
boom += 0.4 * rng.standard_normal(len(tt)) * env(len(tt), 0.001, 0.02)
guardar("boom.wav", np.tanh(boom * 2.5))

tt = t(0.12)
guardar("pop.wav", np.sin(2 * np.pi * np.cumsum(np.linspace(400, 1400, len(tt))) / SR) * env(len(tt), 0.002, 0.035))

tt = t(1.5)
ding = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) for f, a, d in [(1568, 1, 3), (3136, 0.5, 5), (4704, 0.25, 8), (2093, 0.4, 4)])
guardar("ding.wav", ding * env(len(tt), 0.001))

tt = t(2.0)
riser = barrido_ruido(2.0, 200, 8000, 0.25) * (tt / 2) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 * 2 ** (tt * 2)) / SR) * (tt / 2) ** 2
guardar("riser.wav", riser)

tt = t(0.04)
guardar("tick.wav", np.sin(2 * np.pi * 2500 * tt) * env(len(tt), 0.0005, 0.006))

tt = t(0.18)
cuadrada = lambda f: np.sign(np.sin(2 * np.pi * f * tt)) * env(len(tt), 0.002, 0.12)
guardar("error.wav", np.concatenate([cuadrada(520), np.zeros(SR // 40), cuadrada(330)]))
print("Efectos listos")

# ---------- Voz ----------
if len(sys.argv) < 3:
    print("Sin Piper: se omite la voz")
    sys.exit()
piper, modelo = sys.argv[1], sys.argv[2]
datos = []
for i, linea in enumerate(GUION, 1):
    inicio, fin, texto = linea["inicio"], linea["fin"], linea["texto"]
    crudo = SALIDA / f"voz-{i}-crudo.wav"
    subprocess.run([piper, "-m", modelo, "--length_scale", "0.82", "--sentence_silence", "0.1", "-f", str(crudo)], input=texto.encode(), check=True, capture_output=True)
    # Si la frase no cabe en su escena, se acelera un poco (máximo 1.4x)
    tempo = min(1.4, max(1.0, medir(crudo) / (fin - inicio)))
    final = SALIDA / f"voz-{i}.wav"
    # Voz de locutor: recorta silencios, quita graves, da presencia, comprime y sube el volumen
    filtro = (
        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
        f"atempo={tempo:.3f},highpass=f=90,equalizer=f=3000:t=q:w=1:g=5,equalizer=f=200:t=q:w=1:g=2,"
        "acompressor=threshold=-20dB:ratio=4:attack=5:release=60,loudnorm=I=-14:TP=-1.5"
    )
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(crudo), "-af", filtro, "-ar", str(SR), str(final)], check=True)
    crudo.unlink()
    dur = medir(final)
    # Reparte la duración entre palabras según su largo (aproximado) para los subtítulos
    palabras = texto.split()
    pesos = [len(p) + (4 if p[-1] in ".,!?:" else 1) for p in palabras]
    total = sum(pesos)
    acum = 0.0
    lista = []
    for p, w in zip(palabras, pesos):
        d = dur * w / total
        lista.append({"texto": p, "desde": round(inicio + acum, 3), "hasta": round(inicio + acum + d, 3)})
        acum += d
    datos.append({"archivo": f"reel/voz-{i}.wav", "inicio": inicio, "duracion": round(dur, 3), "palabras": lista})
    print(f"Frase {i}: {dur:.2f}s (hueco {fin - inicio:.1f}s, tempo {tempo:.2f})")

(RAIZ / "src" / "reel" / "voz.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2))
print("Voz lista")
