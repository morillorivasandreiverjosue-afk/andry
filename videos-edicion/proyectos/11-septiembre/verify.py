import json, subprocess, numpy as np, sys
from faster_whisper import WhisperModel
S=sys.argv[1]; SR=16000
C=json.load(open(f"{S}/audio/cuts.json"))
m=WhisperModel(f"{S}/npmmodel/m",device="cpu",compute_type="int8",cpu_threads=4)
def load(f):
    b=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(b,np.float32)
for c in C:
    x=load(f"{S}/audio/a{c['file']+1}.mp3")
    for cut in c["cuts"]:
        cs,ce,lab=cut[:3]
        a=x[max(0,int((cs-3)*SR)):int(cs*SR)]; b=x[int(ce*SR):int((ce+3)*SR)]
        y=np.concatenate([a,np.zeros(int(0.5*SR),np.float32),b])
        r=' '.join(s.text for s in m.transcribe(y,language="es",beam_size=5)[0])
        print(c['file']+1,lab,'=>',r)
