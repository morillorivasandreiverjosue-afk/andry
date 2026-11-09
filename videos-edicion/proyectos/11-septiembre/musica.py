import sys, json, numpy as np, subprocess
sys.path.insert(0,"/home/user/andry/videos-edicion/proyectos/napoleon")
import sonido as so
S=sys.argv[1]; T=json.load(open(f"{S}/build/timeline.json"))
END=T["dur"]+9.0   # cola final con tarjeta de cierre
m=[x[1] for x in T["marks"]]
moods=["misterio","majestuoso","frio","tension","tension","tension","triste","epico","frio","triste","majestuoso"]
starts=[0.0]+m[1:]
SR=so.SR; out=np.zeros((int(END*SR)+SR,2),np.float32)
for i,mood in enumerate(moods):
    a=starts[i]; b=(starts[i+1] if i+1<len(starts) else END)
    dur=b-a+3.0
    print(i,mood,round(a,1),round(dur,1),flush=True)
    x=so.musica(mood,dur)
    k=int(a*SR); out[k:k+len(x)]+=x[:len(out)-k]
out=out[:int(END*SR)]
out=so.normal(out,0.8)
open(f"{S}/build/music.f32","wb").write(out.astype(np.float32).tobytes())
subprocess.run(["ffmpeg","-v","error","-f","f32le","-ar",str(SR),"-ac","2","-i",f"{S}/build/music.f32",f"{S}/build/music.wav","-y"])
# efectos: impacto + whoosh
sfx=np.zeros_like(out)
imp=so.impacto(); wh=so.whoosh(1.2,True)
for t in m[1:]+[0.0]:
    tt = 5.4 if t==0.0 else t   # en la apertura el golpe va con el título
    k=int(tt*SR); sfx[k:k+len(imp)]+=imp[:len(sfx)-k]*0.9
    k2=int(max(0,tt-1.15)*SR); sfx[k2:k2+len(wh)]+=wh[:len(sfx)-k2]*0.7
# golpe final
k=int((T["dur"]+0.3)*SR); sfx[k:k+len(imp)]+=imp[:len(sfx)-k]*0.9
open(f"{S}/build/sfx.f32","wb").write(sfx.astype(np.float32).tobytes())
subprocess.run(["ffmpeg","-v","error","-f","f32le","-ar",str(SR),"-ac","2","-i",f"{S}/build/sfx.f32",f"{S}/build/sfx.wav","-y"])
print("listo",END)
