"""Paso 1: genera la narración frase por frase con Kokoro (voz em_alex, español latino).

Uso: python3 1_voz.py <carpeta_modelos> <carpeta_salida>
Crea <salida>/voz/*.wav y <salida>/voz.json con la duración de cada frase.
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

import guion

modelos, salida = Path(sys.argv[1]), Path(sys.argv[2])
(salida / "voz").mkdir(parents=True, exist_ok=True)
k = Kokoro(str(modelos / "kokoro-v1.0.onnx"), str(modelos / "voices-v1.0.bin"))
VOZ, VELOCIDAD, IDIOMA = "em_alex", 1.18, "es-419"

resultado = []
for e, escena in enumerate(guion.ESCENAS):
    frases = []
    for f, frase in enumerate(escena["frases"]):
        ruta = salida / "voz" / f"e{e}_f{f}.wav"
        if not ruta.exists():
            audio, sr = k.create(guion.para_voz(frase), voice=VOZ, speed=VELOCIDAD, lang=IDIOMA)
            umbral = 0.01 * np.abs(audio).max()
            idx = np.where(np.abs(audio) > umbral)[0]
            sf.write(ruta, audio[max(0, idx[0] - 600): idx[-1] + 1800], sr)
        info = sf.info(ruta)
        frases.append({"frase": frase, "wav": str(ruta), "dur": info.frames / info.samplerate})
    resultado.append(frases)
    print(f"escena {e} lista", flush=True)

(salida / "voz.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
total = sum(f["dur"] for es in resultado for f in es)
print(f"Narración: {total:.1f} s")
