#!/usr/bin/env python3
"""Paso 1: lee guion.txt, genera la voz del narrador (Piper TTS) y la línea de tiempo.

Salida (en proyectos/bolivar/build/):
  narracion.wav   voz completa
  linea.json      escenas, frases y tiempos exactos para el video
"""
import argparse
import json
import re
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
BUILD = AQUI / "build"

INTRO = 7.0           # segundos de la portada antes de la primera palabra
PAUSA_FRASE = 0.35
PAUSA_PARRAFO = 0.85
FINAL_EXTRA = 5.0     # cola de la pantalla final


def leer_guion(ruta):
    """Devuelve una lista de bloques: {"tipo": "capitulo"|"plano", ...}."""
    bloques, visual, parrafos = [], None, []

    def cerrar():
        nonlocal parrafos
        if parrafos:
            bloques.append({"tipo": "plano", "visual": visual, "parrafos": parrafos})
            parrafos = []

    actual = []
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines() + [""]:
        s = linea.strip()
        if s.startswith("# ") or s == "#":
            continue
        if not s:
            if actual:
                parrafos.append(" ".join(actual))
                actual = []
            continue
        if s.startswith("## "):
            cerrar()
            bloques.append({"tipo": "capitulo", "titulo": s[3:].strip()})
        elif s.startswith("@"):
            if actual:
                parrafos.append(" ".join(actual))
                actual = []
            cerrar()
            visual = s[1:].strip()
        else:
            actual.append(s)
    cerrar()
    return bloques


def frases(parrafo):
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", parrafo) if f.strip()]


def para_voz(texto):
    """Ajustes de pronunciación que solo afectan al audio."""
    t = texto.replace("—", ", ")
    if t.isupper():
        t = t.lower().capitalize()
    return t


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--voz", required=True, help="modelo .onnx de Piper")
    p.add_argument("--velocidad", type=float, default=1.12, help="length_scale (más alto = más lento)")
    args = p.parse_args()

    from piper import PiperVoice, SynthesisConfig

    voz = PiperVoice.load(args.voz)
    cfg = SynthesisConfig(length_scale=args.velocidad, noise_scale=0.6, noise_w_scale=0.7)
    sr = voz.config.sample_rate
    BUILD.mkdir(exist_ok=True)

    def decir(texto):
        trozos = [np.frombuffer(c.audio_int16_bytes, np.int16) for c in voz.synthesize(para_voz(texto), cfg)]
        a = np.concatenate(trozos) if trozos else np.zeros(1, np.int16)
        # recorta silencios del principio y del final
        idx = np.nonzero(np.abs(a) > 300)[0]
        if len(idx):
            a = a[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.08 * sr)]
        return a

    pistas, t = [], INTRO
    pistas.append(np.zeros(int(INTRO * sr), np.int16))
    escenas = [{"tipo": "portada", "inicio": 0.0, "fin": INTRO}]
    num_cap = -1

    def silencio(seg):
        nonlocal t
        pistas.append(np.zeros(int(seg * sr), np.int16))
        t += seg

    def hablar(texto):
        nonlocal t
        a = decir(texto)
        ini = t
        pistas.append(a)
        t += len(a) / sr
        return {"texto": texto, "inicio": round(ini, 3), "fin": round(t, 3)}

    bloques = leer_guion(AQUI / "guion.txt")
    for i, b in enumerate(bloques):
        if b["tipo"] == "capitulo":
            num_cap += 1
            ini = t
            silencio(0.9)
            f = hablar(b["titulo"].replace(":", "."))
            silencio(1.6)
            escenas.append({"tipo": "capitulo", "titulo": b["titulo"], "num": num_cap,
                            "inicio": round(ini, 3), "fin": round(t, 3), "frases": [f]})
            print(f"{t/60:6.1f} min  {b['titulo']}")
        else:
            ini = t
            lista = []
            for j, par in enumerate(b["parrafos"]):
                fr = frases(par)
                for k, f in enumerate(fr):
                    lista.append(hablar(f))
                    ultima = k == len(fr) - 1
                    silencio(PAUSA_PARRAFO if ultima else PAUSA_FRASE)
            if i == len(bloques) - 1:
                silencio(FINAL_EXTRA)
            escenas.append({"tipo": "plano", "visual": b["visual"], "capitulo": num_cap,
                            "inicio": round(ini, 3), "fin": round(t, 3), "frases": lista})

    audio = np.concatenate(pistas)
    with wave.open(str(BUILD / "narracion.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio.tobytes())
    capitulos = [b["titulo"] for b in bloques if b["tipo"] == "capitulo"]
    (BUILD / "linea.json").write_text(json.dumps({"duracion": round(t, 3), "capitulos": capitulos,
                                                  "escenas": escenas}, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"Narración: {t/60:.1f} min, {len(escenas)} escenas")


if __name__ == "__main__":
    main()
