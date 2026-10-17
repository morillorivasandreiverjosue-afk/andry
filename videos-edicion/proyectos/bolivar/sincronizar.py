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
import re
import subprocess
from pathlib import Path

import numpy as np

from narracion import BUILD, FINAL_EXTRA, INTRO, frases, leer_guion

AQUI = Path(__file__).resolve().parent
AUDIO = AQUI.parent.parent / "narracion" / "proyectos" / "bolivar" / "audio"
SR = 44100
ENTRE_CAPITULOS = 1.5
OBJETIVO_LUFS = -23.0  # misma sonoridad para todas las partes de la voz
VENTANA = 0.02  # segundos por cuadro de análisis


def sonoridad(ruta):
    """Sonoridad integrada (LUFS) de un archivo de audio."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ruta), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def cargar(ruta):
    """Audio mono a SR, llevado a OBJETIVO_LUFS para que todas las partes suenen igual de fuertes."""
    ganancia = OBJETIVO_LUFS - sonoridad(ruta)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-af", f"volume={ganancia:.2f}dB", "-ac", "1",
                        "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


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


def alinear(esperados, fin_parrafo, candidatos, sigma=2.2):
    """Asigna a cada límite entre frases una pausa real, en orden, con el menor costo total
    (distancia al tiempo esperado, premiando pausas largas sobre todo entre párrafos)."""
    n, m = len(esperados), len(candidatos)
    if n == 0:
        return []
    if m < n:
        return [None] * n
    centros = [(a + b) / 2 for a, b in candidatos]
    largos = [b - a for a, b in candidatos]
    INF = float("inf")
    costo = [[((centros[j] - esperados[i]) / sigma) ** 2 - largos[j] * (6 if fin_parrafo[i] else 3)
              for j in range(m)] for i in range(n)]
    dp = [[INF] * m for _ in range(n)]
    atras = [[-1] * m for _ in range(n)]
    for j in range(m):
        dp[0][j] = costo[0][j]
    for i in range(1, n):
        mejor, arg = INF, -1
        for j in range(m):
            if j > 0 and dp[i - 1][j - 1] < mejor:
                mejor, arg = dp[i - 1][j - 1], j - 1
            if arg >= 0:
                dp[i][j] = mejor + costo[i][j]
                atras[i][j] = arg
    j = min(range(m), key=lambda k: dp[n - 1][k])
    out = [0] * n
    for i in range(n - 1, -1, -1):
        out[i] = j
        j = atras[i][j]
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
    candidatos = [s for s in hablado if s[0] > ini_texto + 0.5 and s[1] < fin - 0.3]
    # límites esperados entre frases según la cantidad de texto
    esperados, acum = [], 0
    for f in lista[:-1]:
        acum += f["peso"]
        esperados.append(ini_texto + (fin - ini_texto) * acum / total)
    fin_parrafo = [lista[i]["parrafo"] != lista[i + 1]["parrafo"] for i in range(len(lista) - 1)]
    asignado = alinear(esperados, fin_parrafo, candidatos)
    t = ini_texto
    for i, f in enumerate(lista):
        f["inicio"] = t
        if i == len(lista) - 1:
            f["fin"] = fin
        elif asignado[i] is not None:
            a, b = candidatos[asignado[i]]
            f["fin"], t = a, b
        else:
            f["fin"], t = esperados[i] - 0.15, esperados[i] + 0.15
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
