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
VOZ, VELOCIDAD, IDIOMA = "em_alex", 0.9, "es-419"


def decir(texto, nombre):
    ruta = salida / "voz" / f"{nombre}.wav"
    if not ruta.exists():
        audio, sr = k.create(guion.para_voz(texto), voice=VOZ, speed=VELOCIDAD, lang=IDIOMA)
        # quitar silencio del principio y final
        umbral = 0.01 * np.abs(audio).max()
        idx = np.where(np.abs(audio) > umbral)[0]
        audio = audio[max(0, idx[0] - 600): idx[-1] + 2400]
        sf.write(ruta, audio, sr)
    info = sf.info(ruta)
    return {"texto": texto, "wav": str(ruta), "dur": info.frames / info.samplerate}


resultado = []
for c, cap in enumerate(guion.leer()):
    item = {"etiqueta": cap["etiqueta"], "numero": cap["numero"], "titulo": cap["titulo"],
            "nota": cap["nota"], "titulo_voz": None, "parrafos": []}
    a, sr = k.create(guion.texto_titulo_voz(cap), voice=VOZ, speed=0.85, lang=IDIOMA)
    ruta = salida / "voz" / f"c{c:02d}_titulo.wav"
    sf.write(ruta, a, sr)
    item["titulo_voz"] = {"wav": str(ruta), "dur": len(a) / sr}
    for p, parrafo in enumerate(cap["parrafos"]):
        item["parrafos"].append([decir(f, f"c{c:02d}_p{p:02d}_f{i:02d}")
                                 for i, f in enumerate(guion.frases(parrafo))])
        print(f"cap {c} párrafo {p} listo", flush=True)
    resultado.append(item)

(salida / "voz.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
total = sum(f["dur"] for c in resultado for p in c["parrafos"] for f in p)
print(f"Narración total: {total / 60:.1f} minutos")
