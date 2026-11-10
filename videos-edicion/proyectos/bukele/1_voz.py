"""Paso 1: une las 4 partes de la narración y quita las palabras "Capítulo N".

El rótulo del capítulo sale en pantalla, pero la voz no dice "Capítulo 1", "Capítulo 2"...
Solo dice el título del capítulo ("su nacimiento, su familia y su infancia") y sigue.

Entrada:  audio/parte1.mp3 ... audio/parte4.mp3   (la voz de ElevenLabs)
          transcripcion/parteN.json              (frases con sus tiempos, de transcribir.py)
Salida:   salida/voz.wav  y  salida/voz.json     (frases con los tiempos ya corregidos)

Uso: python3 1_voz.py
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

AQUI = Path(__file__).parent
SR = 44100
PAUSA_CAPITULO = 0.7   # silencio extra antes del título de cada capítulo
PAUSA_PARTES = 0.5     # silencio entre una parte y la siguiente

# Frases de la transcripción que son solo el número de capítulo (la transcripción a veces
# las escribe mal: "Apitulo 12", "Ep. 3", "a p. 20"; en la parte 1, a los 232 s, sale "a").
MARCA = re.compile(r"^(c?ap[ií]tulo|ep\.|a p\.)\s*\d+[.,]?\s*$", re.I)
MARCA_CON_TITULO = re.compile(r"^(c?ap[ií]tulo)\s*\d+\s*,", re.I)   # "Capítulo 11, Marzo de 2022"


def leer(n):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(AQUI / f"audio/parte{n}.mp3"), "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).copy()


def energia(x, paso=0.01):
    h = int(SR * paso)
    if len(x) < h:
        x = np.zeros(h, np.float32)
    m = len(x) // h
    return np.sqrt((x[: m * h].reshape(m, h) ** 2).mean(1) + 1e-12), paso


def inicio_voz(x, t0, t1):
    """Primer instante con voz entre t0 y t1 (segundos)."""
    t0 = max(t0, 0.0)
    e, p = energia(x[int(t0 * SR): int(t1 * SR)])
    umbral = max(0.012, e.max() * 0.06)
    i = np.argmax(e > umbral)
    return t0 + i * p


def fin_voz(x, t0, t1):
    e, p = energia(x[int(t0 * SR): int(t1 * SR)])
    umbral = max(0.012, e.max() * 0.06)
    idx = np.nonzero(e > umbral)[0]
    return t0 + (idx[-1] + 1) * p if len(idx) else t1


def pausa_interna(x, t0, t1):
    """Centro del silencio más largo entre t0 y t1 (para partir "Capítulo 11, Marzo de 2022")."""
    e, p = energia(x[int(t0 * SR): int(t1 * SR)])
    bajo = e < max(0.012, e.max() * 0.05)
    mejor, ini, largo = None, None, 0
    for i, b in enumerate(np.append(bajo, False)):
        if b and ini is None:
            ini = i
        elif not b and ini is not None:
            if i - ini > largo:
                mejor, largo = (ini, i), i - ini
            ini = None
    return t0 + mejor[0] * p, t0 + mejor[1] * p


def es_marca(texto, parte, ini):
    return bool(MARCA.match(texto)) or (parte == 1 and abs(ini - 232.39) < 0.5 and texto.strip() == "a")


def main():
    salida = AQUI / "salida"
    salida.mkdir(exist_ok=True)
    trozos, frases, t_global, cortes = [], [], 0.0, []
    capitulo = 0
    for n in range(1, 5):
        x = leer(n)
        segs = json.loads((AQUI / f"transcripcion/parte{n}.json").read_text())
        quitar = []           # intervalos (ini, fin) a eliminar dentro de esta parte
        titulo_en = set()     # índices de frases que son el título hablado del capítulo
        for i, s in enumerate(segs):
            sig = segs[i + 1]["ini"] if i + 1 < len(segs) else s["fin"] + 0.5
            if es_marca(s["texto"], n, s["ini"]):
                a = inicio_voz(x, s["ini"] - 0.15, s["fin"]) - 0.03
                b = inicio_voz(x, sig - 0.2, sig + 0.6) - 0.06
                quitar.append((a, b))
                titulo_en.add(i + 1)
            elif MARCA_CON_TITULO.match(s["texto"]):
                a = inicio_voz(x, s["ini"] - 0.15, s["fin"]) - 0.03
                p0, p1 = pausa_interna(x, a + 0.5, a + 2.0)
                b = p1 - 0.04
                quitar.append((a, b))
                s = dict(s, texto=s["texto"].split(",", 1)[1].strip(), ini=b)
                segs[i] = s
                titulo_en.add(i)
        # construir la parte sin los cortes, con una pausa extra antes de cada título
        pos, partes_audio, mapa = 0.0, [], []   # mapa: (t_original_ini, t_original_fin, desplazamiento)
        t_local = 0.0
        for a, b in quitar:
            partes_audio.append(x[int(pos * SR): int(a * SR)])
            mapa.append((pos, a, t_local - pos))
            t_local += a - pos
            cortes.append({"parte": n, "desde": round(a, 3), "hasta": round(b, 3)})
            partes_audio.append(np.zeros(int(PAUSA_CAPITULO * SR), np.float32))
            t_local += PAUSA_CAPITULO
            pos = b
        partes_audio.append(x[int(pos * SR):])
        mapa.append((pos, len(x) / SR, t_local - pos))

        def nuevo_t(t):
            for a, b, d in mapa:
                if a - 0.3 <= t <= b + 0.3:
                    return t + d
            return t + mapa[-1][2]

        for i, s in enumerate(segs):
            if es_marca(s["texto"], n, s["ini"]):
                continue
            if i in titulo_en:
                capitulo += 1
            frases.append({"ini": round(t_global + nuevo_t(max(s["ini"], 0)), 3),
                           "fin": round(t_global + nuevo_t(s["fin"]), 3),
                           "texto": s["texto"], "parte": n, "capitulo": capitulo,
                           "titulo": i in titulo_en})
        y = np.concatenate(partes_audio)
        trozos.append(y)
        trozos.append(np.zeros(int(PAUSA_PARTES * SR), np.float32))
        t_global += len(y) / SR + PAUSA_PARTES

    voz = np.concatenate(trozos)
    sf.write(salida / "voz.wav", voz, SR, subtype="PCM_16")
    (salida / "voz.json").write_text(json.dumps({"duracion": len(voz) / SR, "frases": frases, "cortes": cortes},
                                                ensure_ascii=False, indent=0))
    print(f"voz.wav: {len(voz) / SR / 60:.1f} min, {len(cortes)} marcas de capítulo quitadas,"
          f" {capitulo} capítulos")


if __name__ == "__main__":
    main()
