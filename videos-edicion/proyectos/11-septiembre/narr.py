"""Arma la narración final: quita 'Capítulo N'/'Introducción'/'Conclusión' y deja una pausa para la tarjeta."""
import json, subprocess, numpy as np, sys
S=sys.argv[1]; SR=44100
PRE=7.0   # segundos de apertura antes de la voz
GAP=1.7   # pausa donde estaba "Capítulo N"
C=json.load(open(f"{S}/audio/cuts.json"))
def load(f):
    b=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(b,np.float32)
pieces=[]; marks=[]; out=[np.zeros(int(PRE*SR),np.float32)]; t=PRE
for c in C:
    fi=c['file']; x=load(f"{S}/audio/a{fi+1}.mp3"); pos=0.0
    for cs,ce,lab in c['cuts']:
        if cs>pos+0.01:
            seg=x[int(pos*SR):int(cs*SR)]; pieces.append([fi,pos,cs,t]); out.append(seg); t+=len(seg)/SR
        g=GAP if t>PRE+0.1 else 0.0   # al inicio no hace falta pausa extra (ya está la apertura)
        marks.append([lab,t,t+g])     # tarjeta empieza en t; la voz (título) empieza en t+g
        out.append(np.zeros(int(g*SR),np.float32)); t+=g
        pos=ce
    seg=x[int(pos*SR):]; pieces.append([fi,pos,len(x)/SR,t]); out.append(seg); t+=len(seg)/SR
y=np.concatenate(out); 
# fade de 15 ms en cada unión para evitar clics
open(f"{S}/build/narr.f32","wb").write(y.astype(np.float32).tobytes())
subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar',str(SR),'-ac','1','-i',f"{S}/build/narr.f32",f"{S}/build/narr.wav",'-y'])
json.dump({"pieces":pieces,"marks":marks,"dur":t},open(f"{S}/build/timeline.json","w"),indent=1,ensure_ascii=False)
for m in marks: print(m)
print("dur",t)
