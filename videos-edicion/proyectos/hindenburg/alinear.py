"""Tiempos por palabra de la narración sin transcribirla: alinea el texto conocido con las pausas del audio.

Las frases (y dentro de ellas los trozos entre comas) se asignan a las pausas reales de la voz con
programación dinámica, de modo que la duración de cada trozo se parezca a la esperada por su número de
sílabas. Dentro de cada trozo las palabras se reparten por sílabas.

Uso: python3 alinear.py <carpeta_salida>
Necesita <salida>/voz.mp3. Crea <salida>/voz.wav y <salida>/voz.json (párrafos > frases > palabras).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

AQUI = Path(__file__).parent
# En la voz los números van con letras; en los subtítulos, con cifras
CIFRAS = [("mil novecientos treinta y siete", "1937"), ("doscientos cuarenta y cinco", "245"),
          ("treinta y seis", "36"), ("sesenta y dos", "62"), ("noventa y siete", "97"), ("seis de mayo", "6 de mayo")]


def silabas(palabra):
    return max(1, len(re.findall(r"[aeiouáéíóúü]+", palabra.lower())))


def pausas(audio, sr, minimo=0.07):
    """Tramos sin voz: [(inicio, fin), ...] y el inicio y fin del habla."""
    hop = sr // 100
    e = np.sqrt(np.convolve(audio ** 2, np.ones(hop * 2) / (hop * 2), "same")[::hop])
    db = 20 * np.log10(e + 1e-9)
    habla = db > db.max() - 38
    idx = np.flatnonzero(habla)
    ini, fin = idx[0] / 100, (idx[-1] + 1) / 100
    out, i = [], idx[0]
    while i < idx[-1]:
        if not habla[i]:
            j = i
            while not habla[j]:
                j += 1
            if (j - i) / 100 >= minimo:
                out.append((i / 100, j / 100))
            i = j
        i += 1
    return out, ini, fin


def repartir(trozos, ini, fin, huecos):
    """Asigna len(trozos)-1 cortes a pausas de `huecos` entre ini y fin. Devuelve [(ini, fin)] por trozo."""
    n = len(trozos)
    if n == 1:
        return [(ini, fin)]
    pesos = np.array([sum(silabas(w) for w in t) for t in trozos], float)
    habla = (fin - ini) - sum(b - a for a, b in huecos)
    esperado = pesos / pesos.sum() * habla
    m = len(huecos)
    if m < n - 1:  # sin pausas suficientes: reparto proporcional
        bordes = ini + np.concatenate([[0], np.cumsum(esperado)]) * (fin - ini) / habla
        return list(zip(bordes[:-1], bordes[1:]))
    INF = float("inf")
    # coste[k][j]: los k primeros trozos terminan en la pausa j
    coste = np.full((n, m), INF)
    prev = np.zeros((n, m), int)

    def c(dur, k):
        return ((dur - esperado[k]) / max(esperado[k], 0.4)) ** 2

    for j in range(m):
        coste[0][j] = c(huecos[j][0] - ini, 0)
    for k in range(1, n - 1):
        for j in range(k, m):
            for i in range(k - 1, j):
                v = coste[k - 1][i] + c(huecos[j][0] - huecos[i][1], k)
                if v < coste[k][j]:
                    coste[k][j], prev[k][j] = v, i
    mejor, jf = INF, 0
    for j in range(n - 2, m):
        v = coste[n - 2][j] + c(fin - huecos[j][1], n - 1)
        if v < mejor:
            mejor, jf = v, j
    cortes = [jf]
    for k in range(n - 2, 0, -1):
        cortes.append(prev[k][cortes[-1]])
    cortes = cortes[::-1]
    bordes = [ini] + [x for j in cortes for x in huecos[j]] + [fin]
    return [(bordes[2 * k], bordes[2 * k + 1]) for k in range(n)]


def palabras_en(texto, ini, fin, huecos):
    """Reparte las palabras de un trozo entre ini y fin por sílabas (saltando las pausas internas)."""
    ws = texto.split()
    pesos = np.array([silabas(w) + 0.4 for w in ws])
    tramos = [(a, b) for a, b in zip([ini] + [h[1] for h in huecos], [h[0] for h in huecos] + [fin])]
    largo = sum(b - a for a, b in tramos)

    def reloj(x):  # posición en tiempo de habla -> tiempo real
        for a, b in tramos:
            if x <= b - a:
                return a + x
            x -= b - a
        return fin

    acum = np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * largo
    return [{"t": w, "ini": reloj(acum[i]), "fin": reloj(acum[i + 1])} for i, w in enumerate(ws)]


def juntar_cifras(palabras):
    out, i = [], 0
    while i < len(palabras):
        for texto, cifra in CIFRAS:
            n = len(texto.split())
            trozo = palabras[i:i + n]
            if " ".join(re.sub(r"[^\wáéíóúñü]", "", p["t"].lower()) for p in trozo) == texto:
                fin = re.sub(r"^.*?([.,:;?!…]*)$", r"\1", trozo[-1]["t"])
                partes = (cifra + fin).split()
                a, b = trozo[0]["ini"], trozo[-1]["fin"]
                paso = (b - a) / len(partes)
                out += [{"t": t, "ini": a + k * paso, "fin": a + (k + 1) * paso} for k, t in enumerate(partes)]
                i += n
                break
        else:
            out.append(palabras[i])
            i += 1
    return out


def main():
    salida = Path(sys.argv[1])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(salida / "voz.mp3"), "-ac", "1", "-ar", "44100",
                    str(salida / "voz.wav")], check=True)
    audio, sr = sf.read(salida / "voz.wav", dtype="float32")
    huecos, ini, fin = pausas(audio, sr)

    texto = (AQUI / "voz_elevenlabs.txt").read_text()
    pars = [re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", p)).strip() for p in texto.split("\n\n") if p.strip()]
    frases = [(p, f) for p, par in enumerate(pars) for f in re.split(r"(?<=[.?!:…])\s+", par) if f]

    # nivel 1: frases sobre las pausas largas
    largas = [h for h in huecos if h[1] - h[0] >= 0.12]
    tiempos = repartir([f.split() for _, f in frases], ini, fin, largas)
    resultado = [[] for _ in pars]
    for (p, f), (a, b) in zip(frases, tiempos):
        dentro = [h for h in huecos if a < h[0] and h[1] < b]
        # nivel 2: trozos entre comas sobre las pausas de dentro de la frase
        trozos = [t for t in re.split(r"(?<=,)\s+", f) if t]
        palabras = []
        for t, (ta, tb) in zip(trozos, repartir([t.split() for t in trozos], a, b, dentro)):
            palabras += palabras_en(t, ta, tb, [h for h in dentro if ta < h[0] and h[1] < tb])
        palabras = juntar_cifras([dict(w, t=w["t"].replace("…", "")) for w in palabras])
        resultado[p].append({"texto": " ".join(w["t"] for w in palabras), "ini": a, "fin": b, "palabras": palabras})

    (salida / "voz.json").write_text(json.dumps({"wav": str(salida / "voz.wav"), "dur": len(audio) / sr,
                                                 "parrafos": resultado}, ensure_ascii=False, indent=1))
    for p, fr in enumerate(resultado):
        for f in fr:
            print(p, f"{f['ini']:6.2f}-{f['fin']:6.2f}", f["texto"][:80])


if __name__ == "__main__":
    main()
