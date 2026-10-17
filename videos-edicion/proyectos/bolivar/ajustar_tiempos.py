#!/usr/bin/env python3
"""Paso 1b: corrige los tiempos de subtítulos y escenas con la transcripción de ElevenLabs (Scribe).

sincronizar.py reparte las frases según las pausas de la voz, y a veces se equivoca de pausa.
Aquí se cruza el guion palabra por palabra con build/stt_palabras.json (tiempo real de cada palabra)
y se reescriben en build/linea.json el inicio y fin de cada frase y los cortes entre escenas.
La versión anterior queda en build/linea_pausas.json.

Uso (desde proyectos/bolivar/):  python3 ajustar_tiempos.py
"""
import difflib
import json
import re
import shutil
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BUILD = AQUI / "build"


def norm(p):
    p = unicodedata.normalize("NFD", p.lower())
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]", "", p)


def tokens(texto):
    return [t for t in (norm(p) for p in texto.split()) if t]


def main():
    linea = json.loads((BUILD / "linea.json").read_text(encoding="utf-8"))
    if not (BUILD / "linea_pausas.json").exists():
        shutil.copy(BUILD / "linea.json", BUILD / "linea_pausas.json")
    stt = json.loads((BUILD / "stt_palabras.json").read_text(encoding="utf-8"))
    stt = [w for w in (stt["words"] if isinstance(stt, dict) else stt) if w.get("type") == "word"]
    hab = [norm(w["text"]) for w in stt]

    # todas las palabras del guion, en orden, recordando a qué frase pertenecen
    frases = [f for e in linea["escenas"] for f in e.get("frases", [])]
    gui, de_frase = [], []
    for k, f in enumerate(frases):
        for t in tokens(f["texto"]):
            gui.append(t)
            de_frase.append(k)

    # cada palabra del guion -> índice de la palabra dicha (None si no coincide)
    par = [None] * len(gui)
    sm = difflib.SequenceMatcher(None, gui, hab, autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for i in range(n):
            par[a + i] = b + i
    cubiertas = sum(p is not None for p in par)

    viejo = [(f["inicio"], f["fin"]) for f in frases]
    for k, f in enumerate(frases):
        idx = [par[i] for i in range(len(gui)) if de_frase[i] == k and par[i] is not None]
        if idx:
            f["inicio"], f["fin"] = round(stt[min(idx)]["start"], 3), round(stt[max(idx)]["end"], 3)
        else:
            f["_sin"] = True
    # frases sin coincidencias: entre la anterior y la siguiente
    for k, f in enumerate(frases):
        if f.pop("_sin", False):
            a = frases[k - 1]["fin"] if k else 0
            b = next((g["inicio"] for g in frases[k + 1:] if "_sin" not in g), a + 2)
            f["inicio"], f["fin"] = round(a + 0.1, 3), round(max(a + 0.2, b - 0.1), 3)

    # cortes entre escenas con las mismas reglas que sincronizar.py
    esc = linea["escenas"]
    for i, e in enumerate(esc):
        if e["tipo"] == "capitulo":
            e["fin"] = round(e["frases"][0]["fin"] + 0.5, 3)
            if i + 1 < len(esc) and esc[i + 1]["tipo"] == "plano":
                esc[i + 1]["inicio"] = e["fin"]
        elif e["tipo"] == "plano" and i > 0 and esc[i - 1]["tipo"] == "plano" and e["frases"]:
            corte = round(e["frases"][0]["inicio"] - 0.15, 3)
            esc[i - 1]["fin"] = e["inicio"] = max(corte, esc[i - 1]["inicio"] + 0.5)
    for a, b in zip(esc, esc[1:]):
        assert abs(a["fin"] - b["inicio"]) < 1e-6 and a["fin"] > a["inicio"], (a, b)

    dif = sorted(abs(f["inicio"] - v[0]) for f, v in zip(frases, viejo))
    print(f"Palabras del guion encontradas en el audio: {cubiertas}/{len(gui)}")
    print(f"Desfase que había en el inicio de las frases: mediana {dif[len(dif)//2]:.2f} s, "
          f"90% {dif[int(len(dif)*0.9)]:.2f} s, máximo {dif[-1]:.2f} s ({sum(d > 0.5 for d in dif)} frases con más de 0,5 s)")
    (BUILD / "linea.json").write_text(json.dumps(linea, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
