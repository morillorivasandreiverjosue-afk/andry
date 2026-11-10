"""Transcribe la voz con Whisper (local, sherpa-onnx) y guarda las frases con sus tiempos.

Modelos en videos-edicion/modelos/asr/ (sherpa-onnx-whisper-small y silero_vad.onnx, de las
"releases" de k2-fsa/sherpa-onnx en GitHub). Uso: python3 transcribir.py audio/parte1.wav ...
(los .wav a 16 kHz mono: ffmpeg -i parte1.mp3 -ac 1 -ar 16000 parte1.wav)
"""
import sys, json
from pathlib import Path
import numpy as np, soundfile as sf, sherpa_onnx
M = str(Path(__file__).resolve().parents[2] / "modelos" / "asr") + "/"
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=M+"sherpa-onnx-whisper-small/small-encoder.int8.onnx",
    decoder=M+"sherpa-onnx-whisper-small/small-decoder.int8.onnx",
    tokens=M+"sherpa-onnx-whisper-small/small-tokens.txt",
    language="es", task="transcribe", num_threads=1)
cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = M+"silero_vad.onnx"
cfg.silero_vad.min_silence_duration = 0.25
cfg.silero_vad.max_speech_duration = 20
cfg.sample_rate = 16000
for path in sys.argv[1:]:
    x, sr = sf.read(path, dtype="float32")
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
    segs = []
    w = 512
    for i in range(0, len(x), w):
        vad.accept_waveform(x[i:i+w])
        while not vad.empty():
            segs.append((vad.front.start, np.array(vad.front.samples))); vad.pop()
    vad.flush()
    while not vad.empty():
        segs.append((vad.front.start, np.array(vad.front.samples))); vad.pop()
    out = []
    for st, s in segs:
        r = rec.create_stream(); r.accept_waveform(16000, s); rec.decode_stream(r)
        out.append({"ini": round(st/16000, 3), "fin": round((st+len(s))/16000, 3), "texto": r.result.text.strip()})
    json.dump(out, open(path.replace(".wav", ".json"), "w"), ensure_ascii=False, indent=0)
    print(path, len(out), flush=True)
