"""Paso 1: prepara la narración de ElevenLabs y sus tiempos por palabra.

La voz es siempre la misma (ver CLAUDE.md en la raíz del repositorio): ElevenLabs, «Daniel - TI - Professional»
(voice_id OBZYgl3mMau7WE6jCWvm), modelo eleven_v4, con el texto de `voz_elevenlabs.txt`.
Necesita <salida>/voz.mp3 (la narración) y `voz_palabras.json` (su transcripción por palabra con Scribe).

Uso: python3 1_voz.py <carpeta_salida>
Crea <salida>/voz.wav y <salida>/voz.json con párrafos, frases y palabras con su inicio y fin.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import soundfile as sf

AQUI = Path(__file__).parent
# En la voz los números van con letras; en los subtítulos, con cifras
CIFRAS = [("cuatro mil quinientos", "4.500"), ("ciento cuarenta y siete", "147")]


def juntar_cifras(palabras):
    out = []
    i = 0
    while i < len(palabras):
        for texto, cifra in CIFRAS:
            n = len(texto.split())
            trozo = palabras[i:i + n]
            if " ".join(p["t"].lower() for p in trozo) == texto:
                out.append({"t": cifra, "ini": trozo[0]["ini"], "fin": trozo[-1]["fin"]})
                i += n
                break
        else:
            out.append(palabras[i])
            i += 1
    return out


def main():
    salida = Path(sys.argv[1])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(salida / "voz.mp3"), "-ar", "44100",
                    str(salida / "voz.wav")], check=True)
    dur = sf.info(salida / "voz.wav").duration
    palabras = json.loads((AQUI / "voz_palabras.json").read_text())["words"]

    # cada etiqueta de tono ([intrigued], [storytelling]…) abre un párrafo nuevo
    parrafos, dentro_etiqueta = [], False
    for w in palabras:
        if w["type"] != "word":
            continue
        t = w["text"]
        if t.startswith("[") or dentro_etiqueta:
            nuevo = t.startswith("[") and not dentro_etiqueta
            dentro_etiqueta = not t.endswith("]")
            if nuevo and t != "[dramatic":
                parrafos.append([])
            continue
        parrafos[-1].append({"t": t.replace("…", ""), "ini": w["start"], "fin": w["end"]})

    resultado = []
    for par in parrafos:
        frases, actual = [], []
        for w in juntar_cifras(par):
            actual.append(w)
            if re.search(r"[.?!:]$", w["t"]):
                frases.append(actual)
                actual = []
        if actual:
            frases.append(actual)
        resultado.append([{"texto": " ".join(w["t"] for w in f), "ini": f[0]["ini"], "fin": f[-1]["fin"],
                           "palabras": f} for f in frases])
    (salida / "voz.json").write_text(json.dumps({"wav": str(salida / "voz.wav"), "dur": dur,
                                                 "parrafos": resultado}, ensure_ascii=False, indent=1))
    for p, fr in enumerate(resultado):
        print(p, f"{fr[0]['ini']:.2f}-{fr[-1]['fin']:.2f}", " | ".join(f["texto"] for f in fr))


if __name__ == "__main__":
    main()
