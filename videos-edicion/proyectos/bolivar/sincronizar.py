#!/usr/bin/env python3
"""Paso 1 (versión ElevenLabs): sincroniza la narración generada con el guion.

Lee las 18 partes de narracion/proyectos/bolivar/audio/parte-NN.mp3 (una por capítulo),
detecta las pausas reales de la voz y reparte cada frase del guion en su momento exacto.
Escribe build/narracion.wav y build/linea.json, con el mismo formato que narracion.py,
para que render.py arme el video con esta voz.

Uso (desde proyectos/bolivar/):
  python3 sincronizar.py
"""
import json
import subprocess
from pathlib import Path

import numpy as np

from narracion import BUILD, FINAL_EXTRA, INTRO, frases, leer_guion

AQUI = Path(__file__).resolve().parent
AUDIO = AQUI.parent.parent / "narracion" / "proyectos" / "bolivar" / "audio"
SR = 44100
ENTRE_CAPITULOS = 1.5
VENTANA = 0.02  # segundos por cuadro de análisis


def cargar(ruta):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


def silencios(x, minimo=0.18):
    """Tramos sin voz (inicio, fin) en segundos, con umbral adaptado al ruido de cada parte."""
    n = int(SR * VENTANA)
    cuadros = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((cuadros ** 2).mean(axis=1)) + 1e-9)
    voz = np.percentile(db, 90)
    piso = np.percentile(db, 8)
    umbral = max(piso + 0.35 * (voz - piso), voz - 30)
    bajo = db < umbral
    out, ini = [], None
    for i, b in enumerate(np.append(bajo, False)):
        if b and ini is None:
            ini = i
        elif not b and ini is not None:
            if (i - ini) * VENTANA >= minimo:
                out.append((ini * VENTANA, i * VENTANA))
            ini = None
    return out


def sincronizar_parte(x, titulo, parrafos):
    dur = len(x) / SR
    sil = silencios(x)
    # inicio y fin reales de la voz
    hablado = [s for s in sil if s[0] > 0.05 and s[1] < dur - 0.05]
    inicio = sil[0][1] if sil and sil[0][0] <= 0.05 else 0.0
    fin = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 else dur
    # el título termina en la primera pausa larga ([long pause])
    largas = [s for s in hablado if s[0] > inicio + 0.8 and s[0] < inicio + 8 and s[1] - s[0] >= 0.45]
    fin_titulo, ini_texto = (largas[0] if largas else (inicio + 3.0, inicio + 3.5))
    # frases con su peso (caracteres + pausa esperada)
    lista = []
    for j, par in enumerate(parrafos):
        fr = frases(par)
        for k, f in enumerate(fr):
            lista.append({"texto": f, "peso": len(f) + (16 if k == len(fr) - 1 else 7), "parrafo": j})
    total = sum(f["peso"] for f in lista)
    candidatos = [s for s in hablado if s[0] > ini_texto]
    t, acum, usados = ini_texto, 0, set()
    for i, f in enumerate(lista):
        f["inicio"] = t
        acum += f["peso"]
        if i == len(lista) - 1:
            f["fin"] = fin
            break
        esperado = ini_texto + (fin - ini_texto) * acum / total
        mejor = None
        for idx, (a, b) in enumerate(candidatos):
            if idx in usados or a <= t + 0.6:
                continue
            dist = abs((a + b) / 2 - esperado)
            if dist < 2.5 and (mejor is None or dist < mejor[0] - 0.35 * ((b - a) - mejor[3])):
                mejor = (dist, idx, a, b - a)
        if mejor:
            usados.add(mejor[1])
            f["fin"] = mejor[2]
            t = mejor[2] + mejor[3]
        else:
            f["fin"] = esperado - 0.15
            t = esperado + 0.15
    return {"inicio": inicio, "fin_titulo": fin_titulo, "fin": fin, "dur": dur, "frases": lista}


def main():
    bloques = leer_guion(AQUI / "guion.txt")
    capitulos = []
    for b in bloques:
        if b["tipo"] == "capitulo":
            capitulos.append({"titulo": b["titulo"], "planos": []})
        else:
            capitulos[-1]["planos"].append(b)
    partes = sorted(AUDIO.glob("parte-*.mp3"))
    if len(partes) != len(capitulos):
        raise SystemExit(f"Hay {len(partes)} partes de audio y {len(capitulos)} capítulos en el guion.")

    pistas = [np.zeros(int(INTRO * SR), np.float32)]
    t0 = INTRO
    escenas = [{"tipo": "portada", "inicio": 0.0, "fin": INTRO}]
    for num, (cap, ruta) in enumerate(zip(capitulos, partes)):
        x = cargar(ruta)
        parrafos = [p for pl in cap["planos"] for p in pl["parrafos"]]
        s = sincronizar_parte(x, cap["titulo"], parrafos)
        fin_tarjeta = t0 + s["fin_titulo"] + 0.5
        escenas.append({"tipo": "capitulo", "titulo": cap["titulo"], "num": num, "inicio": round(t0, 3),
                        "fin": round(fin_tarjeta, 3),
                        "frases": [{"texto": cap["titulo"], "inicio": round(t0 + s["inicio"], 3),
                                    "fin": round(t0 + s["fin_titulo"], 3)}]})
        # reparte las frases entre los planos (cada plano tiene sus párrafos)
        idx_par = 0
        ini_plano = fin_tarjeta
        for k, pl in enumerate(cap["planos"]):
            pars = set(range(idx_par, idx_par + len(pl["parrafos"])))
            idx_par += len(pl["parrafos"])
            fr = [f for f in s["frases"] if f["parrafo"] in pars]
            ultimo = k == len(cap["planos"]) - 1
            fin_plano = (t0 + s["dur"] + ENTRE_CAPITULOS) if ultimo else None
            if not ultimo:
                sig = [f for f in s["frases"] if f["parrafo"] == idx_par]
                fin_plano = t0 + sig[0]["inicio"] - 0.15
            if num == len(capitulos) - 1 and ultimo:
                fin_plano += FINAL_EXTRA
            escenas.append({"tipo": "plano", "visual": pl["visual"], "capitulo": num,
                            "inicio": round(ini_plano, 3), "fin": round(fin_plano, 3),
                            "frases": [{"texto": f["texto"], "inicio": round(t0 + f["inicio"], 3),
                                        "fin": round(t0 + f["fin"], 3)} for f in fr]})
            ini_plano = fin_plano
        pistas.append(x)
        pistas.append(np.zeros(int(ENTRE_CAPITULOS * SR), np.float32))
        t0 += s["dur"] + ENTRE_CAPITULOS
        print(f"{t0/60:6.2f} min  {cap['titulo'][:60]}  ({len(s['frases'])} frases)")
    pistas.append(np.zeros(int(FINAL_EXTRA * SR), np.float32))
    total = t0 + FINAL_EXTRA
    audio = np.concatenate(pistas)
    BUILD.mkdir(exist_ok=True)
    import wave
    with wave.open(str(BUILD / "narracion.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    (BUILD / "linea.json").write_text(json.dumps({"duracion": round(total, 3), "capitulos": [c["titulo"] for c in capitulos],
                                                  "voz": "elevenlabs", "escenas": escenas},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Narración: {total/60:.1f} min, {len(escenas)} escenas")


if __name__ == "__main__":
    main()
