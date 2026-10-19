"""Paso 1 (alternativo): usa una narración grabada en un solo archivo (p. ej. de ElevenLabs).

Uso: python3 1b_voz_externa.py <audio> <palabras.json> <carpeta_salida> [ritmo]

<palabras.json> es la transcripción con el tiempo de cada palabra ({"words": [{text, start, end}]}).
Corta la narración frase por frase, acorta las pausas largas dentro de cada frase y acelera
sin cambiar el tono (ritmo, p. ej. 1.2). Crea <salida>/voz.json como 1_voz.py, con el tiempo
exacto de cada trozo de subtítulo, para que 2_montaje.py funcione sin cambios.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from guion import ESCENAS

audio, palabras, salida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ritmo = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
PAUSA_MAX = 0.22  # pausa máxima entre palabras de una misma frase (s)

(salida / "voz").mkdir(parents=True, exist_ok=True)
wav = salida / "voz" / "completa.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio), "-ac", "1", "-ar", "44100", str(wav)], check=True)
x, sr = sf.read(wav, dtype="float32")
# las etiquetas de interpretación ([intrigued], [dramatic pause]…) no son palabras habladas
lista = [p for p in json.loads(palabras.read_text())["words"]
         if p.get("type", "word") == "word" and not p["text"].startswith("[") and not p["text"].endswith("]")]

resultado, n = [], 0
for e, escena in enumerate(ESCENAS):
    frases = []
    for i, texto in enumerate(escena["frases"]):
        trozos_txt = texto.split(" | ")
        cuantas = [len(t.split()) for t in trozos_txt]
        mias = lista[n: n + sum(cuantas)]
        n += sum(cuantas)
        ini, fin = mias[0]["start"] - 0.04, mias[-1]["end"] + 0.12
        # tramos de audio a conservar, saltando el exceso de las pausas largas
        tramos, desde = [], ini
        for a, b in zip(mias, mias[1:]):
            if b["start"] - a["end"] > PAUSA_MAX:
                corte = a["end"] + PAUSA_MAX / 2
                tramos.append((desde, corte))
                desde = b["start"] - PAUSA_MAX / 2
        tramos.append((desde, fin))

        def nuevo(t):
            """Tiempo original → tiempo dentro de la frase ya recortada y acelerada."""
            acum = 0.0
            for a, b in tramos:
                if t <= b:
                    return (acum + max(0.0, t - a)) / ritmo
                acum += b - a
            return acum / ritmo

        trozo = np.concatenate([x[int(a * sr): int(b * sr)] for a, b in tramos])
        ruta = salida / "voz" / f"e{e}_f{i}.wav"
        sf.write(ruta, trozo, sr)
        if ritmo != 1.0:
            tmp = ruta.with_suffix(".tmp.wav")
            ruta.rename(tmp)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-af", f"atempo={ritmo}",
                            str(ruta)], check=True)
            tmp.unlink()
        dur = sf.info(ruta).duration
        subs, k = [], 0
        for t, c in zip(trozos_txt, cuantas):
            grupo = mias[k: k + c]
            k += c
            subs.append({"texto": t, "ini": nuevo(grupo[0]["start"]), "fin": nuevo(grupo[-1]["end"])})
        frases.append({"texto": texto, "wav": str(ruta), "dur": dur, "trozos": subs})
        print(f"{dur:5.2f} s  {' '.join(p['text'] for p in mias)[:70]}")
    resultado.append(frases)

(salida / "voz.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
print("Narración:", round(sum(f["dur"] for e in resultado for f in e), 1), "s")
