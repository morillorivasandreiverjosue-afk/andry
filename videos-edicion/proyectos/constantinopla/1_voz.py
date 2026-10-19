"""Paso 1: narración frase por frase con Kokoro (voz em_alex, español latino).

Uso: python3 1_voz.py <carpeta_modelos> <carpeta_salida> [velocidad]
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from guion import ESCENAS, voz

modelos, salida = Path(sys.argv[1]), Path(sys.argv[2])
velocidad = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
(salida / "voz").mkdir(parents=True, exist_ok=True)
k = Kokoro(str(modelos / "kokoro-v1.0.onnx"), str(modelos / "voices-v1.0.bin"))

resultado = []
for e, escena in enumerate(ESCENAS):
    frases = []
    for i, texto in enumerate(escena["frases"]):
        audio, sr = k.create(voz(texto), voice="em_alex", speed=velocidad, lang="es-419")
        umbral = 0.01 * np.abs(audio).max()
        idx = np.where(np.abs(audio) > umbral)[0]
        audio = audio[max(0, idx[0] - 600): idx[-1] + 2400]
        ruta = salida / "voz" / f"e{e}_f{i}.wav"
        sf.write(ruta, audio, sr)
        frases.append({"texto": texto, "wav": str(ruta), "dur": len(audio) / sr})
    resultado.append(frases)

(salida / "voz.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
print("Narración:", round(sum(f["dur"] for e in resultado for f in e), 1), "s")
