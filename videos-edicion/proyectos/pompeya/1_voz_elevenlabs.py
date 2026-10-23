"""Paso 1 (alternativa): usa una narración completa de ElevenLabs en lugar de Kokoro.

Uso: python3 1_voz_elevenlabs.py <narracion.mp3> <palabras.json> <carpeta_salida>
<palabras.json> es la transcripción con tiempos por palabra: [{"text": ..., "start": s, "end": s}, ...]
Corta la narración en una pista por frase y guarda en <salida>/voz.json el momento exacto en que
empieza cada fragmento de subtítulo, para que el montaje los sincronice palabra por palabra.
"""
import difflib
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf

import guion

audio_mp3, palabras_json, salida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
(salida / "voz").mkdir(parents=True, exist_ok=True)


def norma(p):
    p = unicodedata.normalize("NFD", p.lower())
    return "".join(c for c in p if c.isalnum())


wav = salida / "voz" / "narracion.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio_mp3), "-ac", "1", "-ar", "44100", str(wav)],
               check=True)
audio, sr = sf.read(wav, dtype="float32")

transcritas = [w for w in json.loads(palabras_json.read_text()) if norma(w["text"])]
oidas = [norma(w["text"]) for w in transcritas]

# Palabras esperadas, en orden, con (escena, frase, fragmento) de cada una
esperadas, origen = [], []
for e, escena in enumerate(guion.ESCENAS):
    for f, frase in enumerate(escena["frases"]):
        for g, frag in enumerate(frase.split("|")):
            for p in guion.para_voz(frag).split():
                if norma(p):
                    esperadas.append(norma(p))
                    origen.append((e, f, g))

# Emparejar lo esperado con lo transcrito; lo que no empareje se interpola
ini, fin = [None] * len(esperadas), [None] * len(esperadas)
for bloque in difflib.SequenceMatcher(None, esperadas, oidas, autojunk=False).get_matching_blocks():
    for k in range(bloque.size):
        w = transcritas[bloque.b + k]
        ini[bloque.a + k], fin[bloque.a + k] = w["start"], w["end"]
emparejadas = sum(x is not None for x in ini)
idx = np.arange(len(esperadas))
ok = np.array([x is not None for x in ini])
ini = np.interp(idx, idx[ok], np.array([x for x in ini if x is not None]))
fin = np.interp(idx, idx[ok], np.array([x for x in fin if x is not None]))
print(f"Palabras sincronizadas: {emparejadas}/{len(esperadas)}")

resultado = []
for e, escena in enumerate(guion.ESCENAS):
    frases = []
    for f, frase in enumerate(escena["frases"]):
        ks = [k for k, o in enumerate(origen) if o[:2] == (e, f)]
        a, b = max(0.0, ini[ks[0]] - 0.04), fin[ks[-1]] + 0.12
        ruta = salida / "voz" / f"e{e}_f{f}.wav"
        trozo = audio[int(a * sr): int(b * sr)].copy()
        rampa = min(len(trozo) // 4, int(0.015 * sr))
        trozo[:rampa] *= np.linspace(0, 1, rampa)
        trozo[-rampa:] *= np.linspace(1, 0, rampa)
        sf.write(ruta, trozo, sr)
        n_frag = len(frase.split("|"))
        frag_t = [float(ini[next(k for k in ks if origen[k][2] == g)] - a) for g in range(n_frag)]
        frases.append({"frase": frase, "wav": str(ruta), "dur": b - a, "frag_t": frag_t})
    resultado.append(frases)

(salida / "voz.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
print(f"Narración: {sum(f['dur'] for es in resultado for f in es):.1f} s")
