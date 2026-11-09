import sys, json, subprocess, numpy as np
def load(f):
    b=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar','16000','-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(b,np.float32)
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[1], device="cpu", compute_type="int8", cpu_threads=4)
out = []
for f in sys.argv[3:]:
    segs, info = m.transcribe(load(f), language="es", word_timestamps=True, beam_size=5)
    words=[]; ss=[]
    for s in segs:
        ss.append({"s":s.start,"e":s.end,"t":s.text})
        for w in s.words: words.append({"s":w.start,"e":w.end,"w":w.word})
        print(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text}", flush=True)
    out.append({"file":f,"segments":ss,"words":words})
json.dump(out, open(sys.argv[2],"w"), ensure_ascii=False, indent=1)
