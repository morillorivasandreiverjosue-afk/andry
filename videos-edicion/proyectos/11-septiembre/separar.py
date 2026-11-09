"""Separación de fuentes con HTDemucs (pesos ONNX) reimplementada en numpy."""
import sys, numpy as np, subprocess, onnxruntime as ort
MODEL, INP, OUTP = sys.argv[1], sys.argv[2], sys.argv[3]
SR=44100; SEG=int(7.8*SR); HL=1024; NFFT=4096
def load(f):
    b=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','2','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(b,np.float32).reshape(-1,2).T.copy()
WIN=(0.5*(1-np.cos(2*np.pi*np.arange(NFFT)/NFFT))).astype(np.float64)
def stft(x):  # x [..., L] -> complex [..., F, T]  (torch.stft center reflect normalized)
    p=NFFT//2; x=np.pad(x,[(0,0)]*(x.ndim-1)+[(p,p)],mode='reflect')
    n=(x.shape[-1]-NFFT)//HL+1
    idx=np.arange(NFFT)[None,:]+HL*np.arange(n)[:,None]
    fr=x[...,idx]*WIN/np.sqrt(NFFT)
    return np.swapaxes(np.fft.rfft(fr,axis=-1),-1,-2)
def istft(z,length):  # z [..., F, T]
    fr=np.fft.irfft(np.swapaxes(z,-1,-2),n=NFFT,axis=-1)*np.sqrt(NFFT)*WIN
    T=z.shape[-1]; out=np.zeros(z.shape[:-2]+(length,)); ws=np.zeros(length)
    for t in range(T):
        s=t*HL-NFFT//2; a=max(0,s); b=min(length,s+NFFT)
        if b<=a: continue
        out[...,a:b]+=fr[...,t,a-s:b-s]; ws[a:b]+=WIN[a-s:b-s]**2
    return out/np.where(ws>1e-8,ws,1)
def spec(x):
    L=x.shape[-1]; le=int(np.ceil(L/HL)); pad=HL//2*3
    xp=np.pad(x,[(0,0)]*(x.ndim-1)+[(pad,pad+le*HL-L)],mode='reflect')
    z=stft(xp)[...,:-1,:]
    return z[...,2:2+le]
def ispec(z,length):
    z=np.pad(z,[(0,0)]*(z.ndim-2)+[(0,1),(2,2)])
    pad=HL//2*3; le=HL*int(np.ceil(length/HL))+2*pad
    x=istft(z,le)
    return x[...,pad:pad+length]
sess=ort.InferenceSession(MODEL,providers=['CPUExecutionProvider'])
ins=[i.name for i in sess.get_inputs()]; outs=[o.name for o in sess.get_outputs()]
def infer(chunk):  # chunk [2, SEG]
    z=spec(chunk[None].astype(np.float64))          # [1,2,F,T]
    mag=np.stack([z.real,z.imag],axis=2).reshape(1,4,z.shape[-2],z.shape[-1]).astype(np.float32)
    ox,oxt=sess.run(outs,{ins[0]:chunk[None].astype(np.float32),ins[1]:mag})
    B,Sx,C,F,T=ox.shape
    zc=ox.reshape(B,Sx,C//2,2,F,T); zc=zc[:,:,:,0]+1j*zc[:,:,:,1]
    return (oxt+ispec(zc,SEG))[0]                 # [4,2,SEG]
mix=load(INP); L=mix.shape[1]
stride=int(0.75*SEG)
w=np.concatenate([np.arange(1,SEG//2+2),SEG-np.arange(SEG//2+1,SEG)]).astype(np.float64); w/=w.max()
out=np.zeros((4,2,L)); ws=np.zeros(L); off=0
while off<L:
    n=min(SEG,L-off); delta=SEG-n; st=off-delta//2
    ch=np.zeros((2,SEG),np.float32); a=max(0,st); b=min(L,st+SEG); ch[:,a-st:b-st]=mix[:,a:b]
    y=infer(ch); y=y[...,delta//2:delta//2+n]
    out[...,off:off+n]+=w[:n]*y; ws[off:off+n]+=w[:n]; off+=stride
    print("segmento",off,L,flush=True)
out/=ws
for i,nm in enumerate(['drums','bass','other','vocals']):
    np.save(f"{OUTP}_{nm}.npy",out[i].astype(np.float32))
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','2','-i','-',f"{OUTP}_{nm}.wav"],input=out[i].T.astype(np.float32).tobytes())
print("listo")
