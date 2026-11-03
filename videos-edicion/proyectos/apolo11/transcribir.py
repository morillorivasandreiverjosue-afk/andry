"""Transcribe la narración con Whisper (sherpa-onnx, sin internet) para sincronizar subtítulos.

Uso: python3 transcribir.py <narracion.wav> <carpeta_modelo_whisper> <salida/>
Corta el audio en tramos de voz de hasta ~7 s (por las pausas), transcribe cada uno y guarda
<salida>/whisper.json  [{ini, fin, texto}]
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

MAX = 7.0


def tramos(wav):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "silencedetect=noise=-38dB:d=0.12",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    dur = sf.info(str(wav)).duration
    habla, t = [], 0.0
    for a, b in zip(ini, fin + [dur]):
        if a - t > 0.05:
            habla.append((t, a))
        t = b
    if dur - t > 0.05:
        habla.append((t, dur))
    # juntar tramos cortos en ventanas de hasta MAX segundos
    ventanas = []
    for a, b in habla:
        if ventanas and b - ventanas[-1][0] <= MAX and a - ventanas[-1][1] < 0.6:
            ventanas[-1] = (ventanas[-1][0], b)
        else:
            ventanas.append((a, b))
    return ventanas


_rec = None


def _init(modelo):
    global _rec
    import sherpa_onnx
    m = Path(modelo)
    _rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(m / "base-encoder.int8.onnx"), decoder=str(m / "base-decoder.int8.onnx"),
        tokens=str(m / "base-tokens.txt"), language="es", task="transcribe", num_threads=1)


def _trans(args):
    audio, sr = args
    s = _rec.create_stream()
    s.accept_waveform(sr, audio)
    _rec.decode_stream(s)
    return s.result.text.strip()


def main():
    wav, modelo, salida = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    audio, sr = sf.read(str(wav), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(1)
    if sr != 16000:
        from scipy.signal import resample_poly
        audio = resample_poly(audio, 16000, sr).astype(np.float32)
        sr = 16000
    vs = tramos(wav)
    trozos = [(np.pad(audio[int(a * sr): int(b * sr)], (1600, 1600)), sr) for a, b in vs]
    with ProcessPoolExecutor(4, initializer=_init, initargs=(modelo,)) as ex:
        textos = list(ex.map(_trans, trozos, chunksize=4))
    res = [{"ini": round(a, 3), "fin": round(b, 3), "texto": t} for (a, b), t in zip(vs, textos)]
    (salida / "whisper.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"{len(res)} tramos transcritos")


if __name__ == "__main__":
    main()
