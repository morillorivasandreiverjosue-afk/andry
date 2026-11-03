"""Sincroniza el guion (guion_original.txt) con la narración usando la transcripción de Whisper.

Uso: python3 alinear.py <salida/>
Necesita <salida>/whisper.json (lo crea transcribir.py). Compara palabra por palabra el guion con lo
que reconoció Whisper y da a cada frase su inicio y final reales.
Crea <salida>/frases.json  [{texto, ini, fin, tipo (portada|titulo|texto), capitulo, etiqueta}]
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).parent


def normal(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def frases(p):
    partes = re.split(r'(?<!\s[A-Z]\.)(?<=[.?!])\s+(?=[¿¡"A-ZÁÉÍÓÚÑ0-9])', p)
    return [x.strip() for x in partes if x.strip()]


def leer_guion():
    items, cap, etiqueta = [], 0, ""
    lineas = [l.strip() for l in (AQUI / "guion_original.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    for k, l in enumerate(lineas):
        m = re.match(r"^(INTRODUCCIÓN|CAPÍTULO (\d+)|CONCLUSIÓN) — (.+)$", l)
        if k < 2:  # título del documental
            items.append({"texto": l, "tipo": "portada", "capitulo": 0, "etiqueta": ""})
        elif m:
            cap += 1
            etiqueta = m.group(1)
            items.append({"texto": m.group(3), "tipo": "titulo", "capitulo": cap, "etiqueta": etiqueta})
        else:
            for f in frases(l):
                items.append({"texto": f, "tipo": "texto", "capitulo": cap, "etiqueta": etiqueta})
    return items


def main():
    salida = Path(sys.argv[1])
    wh = json.loads((salida / "whisper.json").read_text())
    # palabras reconocidas con su tiempo (repartido por letras dentro de cada tramo)
    pw, pt = [], []
    for v in wh:
        ws = [w for w in v["texto"].split() if normal(w)]
        largos = [len(normal(w)) + 1 for w in ws]
        tot, acc = sum(largos) or 1, 0
        for w, L in zip(ws, largos):
            a = v["ini"] + (v["fin"] - v["ini"]) * acc / tot
            acc += L
            b = v["ini"] + (v["fin"] - v["ini"]) * acc / tot
            pw.append(normal(w))
            pt.append((a, b))
    items = leer_guion()
    gw, gi = [], []
    for i, it in enumerate(items):
        texto = it["texto"] if it["tipo"] != "titulo" else f"{it['etiqueta']} {it['texto']}"
        for w in texto.split():
            if normal(w):
                gw.append(normal(w))
                gi.append(i)
    sm = difflib.SequenceMatcher(None, gw, pw, autojunk=False)
    t_ini = [None] * len(gw)
    t_fin = [None] * len(gw)
    emparejadas = 0
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            t_ini[a + k], t_fin[a + k] = pt[b + k]
            emparejadas += 1
    # interpolar las palabras que no coincidieron
    conocidos = [k for k in range(len(gw)) if t_ini[k] is not None]
    for k in range(len(gw)):
        if t_ini[k] is None:
            izq = max([c for c in conocidos if c < k], default=None)
            der = min([c for c in conocidos if c > k], default=None)
            if izq is None:
                t_ini[k] = t_fin[k] = t_ini[der]
            elif der is None:
                t_ini[k] = t_fin[k] = t_fin[izq]
            else:
                f = (k - izq) / (der - izq)
                t_ini[k] = t_fin[izq] + (t_ini[der] - t_fin[izq]) * f
                t_fin[k] = t_ini[k]
    for i, it in enumerate(items):
        ks = [k for k in range(len(gw)) if gi[k] == i]
        it["ini"] = round(t_ini[ks[0]], 3)
        it["fin"] = round(t_fin[ks[-1]], 3)
    for a, b in zip(items, items[1:]):  # sin solapes
        if b["ini"] < a["fin"]:
            a["fin"] = b["ini"]
    print(f"{len(items)} frases; {emparejadas}/{len(gw)} palabras del guion encontradas en el audio")
    (salida / "frases.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))


main()
