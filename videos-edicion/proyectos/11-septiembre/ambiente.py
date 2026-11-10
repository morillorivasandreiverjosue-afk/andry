"""Sonido documental sin música: golpes graves en títulos, avión + explosión para el clip 2."""
import sys, json, numpy as np, subprocess
sys.path.insert(0,"/home/user/andry/videos-edicion/proyectos/napoleon")
import sonido as so
from scipy import signal
S=sys.argv[1]; SR=so.SR; B=f"{S}/build"
T=json.load(open(f"{B}/timeline.json")); END=T["dur"]+9.0
rng=np.random.default_rng(911)
def save(x,name):
    subprocess.run(["ffmpeg","-v","error","-y","-f","f32le","-ar",str(SR),"-ac","2","-i","-",f"{B}/{name}"],input=x.astype(np.float32).tobytes())
def boom(dur=4.0, grave=1.0):
    """Explosión/golpe grave sin tonos musicales: ruido filtrado con cola de retumbo."""
    n=so.seg(dur); t=np.arange(n)/SR
    sub=np.sin(2*np.pi*(42*t-6*t**2))*so.env_exp(n,0.5)*grave
    cuerpo=so.lp(so.ruido(n),300,4)*so.env_exp(n,0.35)*2.2
    rumble=so.lp(so.ruido(n),120,4)*so.env_exp(n,1.4)*1.6
    crack=so.hp(so.ruido(n),1800)*so.env_exp(n,0.05)*0.7
    x=so.normal(sub+cuerpo+rumble+crack,0.95)
    return so.reverb(so.estereo(x),2.5,0.3,1800)
def avion(dur, pico):
    """Rugido de reactor que se acerca (crece hasta 'pico' segundos) con efecto Doppler simple."""
    n=so.seg(dur); t=np.arange(n)/SR
    env=np.clip(np.exp((t-pico)/0.9),0,1)**1.3
    roar=so.bp(so.ruido(n),200,3500,2)*1.0
    f=900+600*np.clip((t-pico+2)/2,0,1)
    whine=np.sin(2*np.pi*np.cumsum(f)/SR)*0.08
    x=(roar+whine)*env
    return so.estereo(so.normal(x,0.9),0.0)
def ciudad(dur):
    n=so.seg(dur); x=so.lp(so.ruido(n),500,2)*0.25+so.bp(so.ruido(n),800,3000,2)*0.05
    return so.estereo(x)
# 1) efectos generales: golpe grave en cada título + golpe tras "lo peor todavía estaba por llegar"
sfx=np.zeros((int(END*SR)+SR*5,2),np.float32)
def put(x,t,v):
    k=int(t*SR); sfx[k:k+len(x)]+=x[:len(sfx)-k]*v
b=boom(4.0)
for m in [x[1] for x in T["marks"][1:]]: put(b,m,0.55)
put(boom(5.0,1.3),5.3,0.6)            # título de apertura
put(boom(5.0,1.4),295.3,0.9)          # "...lo peor estaba por llegar" -> BOOM
put(b,T["dur"]+0.3,0.5)                # cierre
save(sfx[:int(END*SR)],"sfx_doc.wav")
# 2) audio nuevo para el clip 2 (bomberos, primer avión): ciudad + reactor + explosión a los 5.0 s
D=7.5; x=ciudad(D)*0.6
a=avion(5.05,5.0); x[:len(a)]+=a*0.8
e=boom(3.0,1.2); k=int(5.0*SR); x[k:]+=e[:len(x)-k]*1.0
x[-int(0.5*SR):]*=np.linspace(1,0,int(0.5*SR))[:,None]
save(so.normal(x,0.9),"ref2_sonido.wav")
# 3) bola de fuego (clip 2, 7.5-12.4 s): retumbo + fuego
D=5.0; y=ciudad(D)*0.5+so.estereo(so.lp(so.ruido(so.seg(D)),150,3))*0.6
y+=so.fuego(D,1.0)*0.5 if so.fuego(D,1.0).ndim==2 else so.estereo(so.fuego(D,1.0))*0.5
save(so.normal(y,0.7),"ref2_fuego.wav")
print("ok")
# 4) reactor que se acerca durante la pantalla negra (desde 292.3 s) y termina en el golpe de 295.3 s
D=6.0; z=np.zeros((so.seg(D),2),np.float32)
a=avion(3.0,3.0); z[:len(a)]+=a*0.7
save(so.normal(z,0.8),"avion_impacto.wav")
print("avion ok")
