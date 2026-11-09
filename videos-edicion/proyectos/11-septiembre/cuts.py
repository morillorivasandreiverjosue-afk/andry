import json, subprocess, numpy as np, sys, re
S=sys.argv[1]
SR=44100
d=json.load(open(f"{S}/audio/trans.json"))
def load(f):
    b=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(b,np.float32).copy()
# markers: (file idx, label word index) -> find in words
plan=[]
for fi,f in enumerate(d):
    W=f['words']
    for i,w in enumerate(W):
        t=w['w'].strip().lower()
        hdr=None
        if t.startswith('introducci') or t.startswith('conclusi'):
            hdr=(i,i)  # header only one word
        elif t.startswith('capítulo') or t.startswith('capitulo'):
            hdr=(i,i+1)
        elif re.match(r'^[789]\.$',t) and i>0 and W[i-1]['w'].strip().endswith('.'):
            hdr=(i,i)
        if hdr: plan.append((fi,hdr[0],hdr[1]))
out=[]
for fi in range(3):
    x=load(f"{S}/audio/a{fi+1}.mp3")
    hop=int(SR*0.01)
    n=len(x)//hop
    rms=np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)+1e-12)
    db=20*np.log10(rms)
    W=d[fi]['words']
    cuts=[]
    for (f2,a,b) in plan:
        if f2!=fi: continue
        s=W[a]['s']; e=W[b]['e']; ts=W[b+1]['s']
        # cut start: last quiet frame run before speech onset in [s-1.0, s+0.25]
        lo=int(max(0,s-1.2)*100); hi=int((s+0.3)*100)
        seg=db[lo:hi]; thr=-45
        # find onset: first frame after the last quiet stretch where loud
        quiet=seg<thr
        # take the speech onset = index of first loud frame after last quiet frame preceding first loud run near s
        idx=None
        for k in range(len(seg)-1,-1,-1):
            if quiet[k] and (k+1<len(seg)) and not quiet[k+1] and lo+k<= (s+0.3)*100:
                idx=k+1
                # ensure the loud run after is speech (header) -> choose the latest such transition before s+0.3
                break
        cs=(lo+(idx if idx is not None else int((s-lo/100)*100)))/100-0.03
        if s<0.05: cs=0.0
        # cut end: minimum energy between number end and title start
        lo2=int((e-0.3)*100); hi2=int((ts+0.15)*100)
        seg2=db[lo2:hi2]
        # find quiet frames; cut end = onset of title speech = last quiet->loud transition in window
        q2=seg2<thr
        ce=None
        for k in range(len(seg2)-1,0,-1):
            if q2[k-1] and not q2[k]: ce=(lo2+k)/100-0.03; break
        if ce is None: ce=(lo2+int(np.argmin(seg2)))/100
        cuts.append((cs,ce,' '.join(w['w'].strip() for w in W[a:b+1])))
    out.append({"file":fi,"dur":len(x)/SR,"cuts":cuts})
    for c in cuts: print(fi+1, "%.2f-%.2f"%c[:2], c[2])
json.dump(out,open(f"{S}/audio/cuts.json","w"),indent=1,ensure_ascii=False)
