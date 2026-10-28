"""Paso 1: genera la narración frase por frase con Kokoro (voz em_alex, español latino).

Uso: python3 1_voz.py <carpeta_modelos> <carpeta_salida>
Crea <salida>/voz/*.wav y <salida>/voz.json con el texto y la duración de cada frase.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

AQUI = Path(__file__).parent
VOZ, VELOCIDAD, IDIOMA = "em_alex", 1.0, "es-419"  # un poco más rápida que en el documental: es para TikTok

# Solo cambia cómo suena, no los subtítulos
PRONUNCIACION = [("4.500", "cuatro mil quinientos"), ("147", "ciento cuarenta y siete"), ("Keops", "Kéops")]


def parrafos():
    lineas = [l.strip() for l in (AQUI / "guion.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    titulo = lineas[0].replace(": ", ". ").capitalize()
    titulo = titulo.replace("egipto", "Egipto")
    return [titulo] + lineas[1:]


def frases(texto):
    partes = re.split(r"(?<=[.?!:])\s+", texto)
    return [p for p in partes if p]


def para_voz(texto):
    for a, b in PRONUNCIACION:
        texto = texto.replace(a, b)
    return texto


def main():
    modelos, salida = Path(sys.argv[1]), Path(sys.argv[2])
    (salida / "voz").mkdir(parents=True, exist_ok=True)
    k = Kokoro(str(modelos / "kokoro-v1.0.onnx"), str(modelos / "voices-v1.0.bin"))
    resultado = []
    for p, parrafo in enumerate(parrafos()):
        lista = []
        for i, f in enumerate(frases(parrafo)):
            ruta = salida / "voz" / f"p{p:02d}_f{i:02d}.wav"
            audio, sr = k.create(para_voz(f), voice=VOZ, speed=VELOCIDAD, lang=IDIOMA)
            umbral = 0.01 * np.abs(audio).max()
            idx = np.where(np.abs(audio) > umbral)[0]
            audio = audio[max(0, idx[0] - 600): idx[-1] + 2400]
            sf.write(ruta, audio, sr)
            lista.append({"texto": f, "wav": str(ruta), "dur": len(audio) / sr})
        resultado.append(lista)
        print(f"párrafo {p} listo", flush=True)
    (salida / "voz.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
    total = sum(f["dur"] for p in resultado for f in p)
    print(f"Narración: {total:.1f} segundos")


if __name__ == "__main__":
    main()
