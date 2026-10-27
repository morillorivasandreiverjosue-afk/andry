"""Paso 2b: sincroniza los subtítulos con la voz real.

Para cada parte se sintetiza el mismo texto con Kokoro (voz local), trozo de subtítulo a trozo, de modo que
se sabe exactamente dónde empieza cada trozo en esa versión. Después se alinea esa versión con la
narración de ElevenLabs por DTW sobre MFCC y cada inicio se ajusta a la pausa real más cercana.

Uso: python3 alinear.py        (escribe salida/edad_media_sincronizado.srt, que usa partir.py)
"""
import re

import librosa
import numpy as np
from kokoro_onnx import Kokoro

import montaje as M

SR = 16000
HOP = 320  # 20 ms
MODELOS = M.AQUI.parent.parent / "modelos"


def trozos(texto):
    """Los mismos trozos que usa el generador de subtítulos (frases y, si son largas, partes de frase)."""
    out = []
    for f in (f for f in re.split(r"(?<=[.?!:…])\s+", texto) if f):
        partes = M.P.trocear(f)
        out += [(p, j == len(partes) - 1) for j, p in enumerate(partes)]
    return out


def para_voz(texto):
    return texto.replace("siglo XIV", "siglo catorce").replace("siglo XV", "siglo quince")


def rasgos(audio):
    m = librosa.feature.mfcc(y=audio, sr=SR, n_mfcc=20, hop_length=HOP, n_fft=1024)[1:]
    m = (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-6)
    return np.vstack([m, librosa.feature.delta(m)])


def alinear_parte(k, wav_real, lista):
    """Devuelve los inicios (s) de cada trozo en la voz real, más el final del último."""
    piezas, inicios, t = [], [], 0.0
    for texto, fin_frase in lista:
        audio, sr = k.create(para_voz(texto), voice="em_alex", speed=1.0, lang="es")
        audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=SR)
        idx = np.where(np.abs(audio) > 0.02 * np.abs(audio).max())[0]
        audio = audio[max(0, idx[0] - 160): idx[-1] + 160]
        inicios.append(t)
        silencio = np.zeros(int(SR * (0.35 if fin_frase else 0.12)), np.float32)
        piezas += [audio, silencio]
        t += (len(audio) + len(silencio)) / SR
    ref = np.concatenate(piezas)
    real, _ = librosa.load(str(wav_real), sr=SR, mono=True)
    _, camino = librosa.sequence.dtw(X=rasgos(ref), Y=rasgos(real), metric="cosine")
    camino = camino[::-1]
    mapa = np.zeros(camino[:, 0].max() + 1)
    for i in range(len(mapa)):
        mapa[i] = np.median(camino[camino[:, 0] == i, 1])
    marcas = [mapa[min(len(mapa) - 1, int(x * SR / HOP))] * HOP / SR for x in inicios]
    # se ajusta cada marca a la pausa real más cercana (si hay una muy cerca)
    pausas = M.P.pausas_voz(wav_real)
    voz = np.where(np.abs(real) > 0.03 * np.abs(real).max())[0]
    marcas[0] = voz[0] / SR
    for j in range(1, len(marcas)):
        cerca = pausas[np.abs(pausas - marcas[j]) < 0.45] if len(pausas) else pausas
        if len(cerca):
            marcas[j] = float(cerca[np.argmin(np.abs(cerca - marcas[j]))])
        marcas[j] = max(marcas[j], marcas[j - 1] + 0.7)
    marcas.append(max(voz[-1] / SR + 0.3, marcas[-1] + 0.8))
    return marcas


def ts(s):
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def main():
    plan, _ = M.linea_de_tiempo()
    _, caps = M.leer_guion()
    k = Kokoro(str(MODELOS / "kokoro-v1.0.onnx"), str(MODELOS / "voices-v1.0.bin"))
    lineas, n = [], 1
    for i, cap in enumerate(caps):
        lista = trozos(cap["texto"])
        marcas = alinear_parte(k, M.SALIDA / "voz" / f"cap{i}.wav", lista)
        for (texto, _), a, b in zip(lista, marcas[:-1], marcas[1:]):
            t0, t1 = plan[i]["voz"] + a, plan[i]["voz"] + b
            lineas += [str(n), f"{ts(t0)} --> {ts(t1 - 0.05)}", M.P.dos_lineas(texto), ""]
            n += 1
        print(f"parte {i}: {len(lista)} subtítulos alineados", flush=True)
    (M.SALIDA / "edad_media_sincronizado.srt").write_text("\n".join(lineas), encoding="utf-8")
    print("Subtítulos sincronizados:", M.SALIDA / "edad_media_sincronizado.srt")


if __name__ == "__main__":
    main()
