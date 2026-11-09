"""Renderiza cada plano (video o foto) a 1920x1080/30fps y luego monta todo."""
import sys, os, json, subprocess, shlex
from concurrent.futures import ThreadPoolExecutor
S=sys.argv[1]; MODE=sys.argv[2] if len(sys.argv)>2 else "all"
B=f"{S}/build"; CL=f"{B}/clips"; os.makedirs(CL,exist_ok=True)
sys.path.insert(0,f"{S}/scripts")
from shots import SHOTS, END, OVERLAYS, CLIPSOUND
V=f"{S}/media/vid"; I=f"{S}/media/img"; R=f"{S}/ref"
REF={"ref1":f"{R}/WhatsApp Video 2026-11-08 at 1.38.22 PM.mp4","ref2":f"{R}/WhatsApp Video 2026-11-08 at 1.38.26 PM.mp4"}
def path(src):
    if src in REF: return REF[src]
    if "/" in src and not src.startswith("/"): return f"{I}/{src}.jpg"
    return f"{V}/{src}"
VG=f"{B}/gfx/vineta.png"
GRADE="eq=contrast=1.07:saturation=0.88:gamma=0.97,colorbalance=rs=-0.02:bs=0.03:rh=0.03:bh=-0.02"
def build(i,shot,t0,dur):
    out=f"{CL}/{i:03d}.mp4"
    key=json.dumps([shot,round(dur,3)],sort_keys=True)
    if os.path.exists(out) and os.path.exists(out+".key") and open(out+".key").read()==key: return out
    src=path(shot["src"]); img=src.endswith(".jpg") or shot.get("black")
    sp=shot.get("speed",1.0); z0,z1=shot.get("z",(1.0,1.07)); px,py=shot.get("pan",(0,0))
    fit=shot.get("fit","cover")
    if src.endswith(".jpg") and "fit" not in shot:
        from PIL import Image
        w,h=Image.open(src).size
        if w/h<1.45: fit="blur"
    pre=[]
    if shot.get("crop"): pre.append("crop=%s"%shot["crop"])
    if shot.get("pillar"): pre.append("crop=ih*4/3:ih")       # quita barras negras de un 4:3 dentro de 16:9
    if not img: pre.append(f"setpts=(PTS-STARTPTS)/{sp}")
    pre.append("fps=30")
    if shot.get("black"):
        inp=["-f","lavfi","-t",f"{dur:.3f}","-i","color=c=black:s=1920x1080:r=30","-i",VG]; chain="[0:v]null[o]"
    else:
        if img: inp=["-loop","1","-framerate","30","-t",f"{dur+0.2:.3f}","-i",src]
        else: inp=["-ss",f"{shot['ss']:.3f}","-t",f"{dur*sp+0.6:.3f}","-i",src]
        inp+=["-loop","1","-framerate","30","-i",VG]
        D=max(dur,0.1)
        zexp=f"({z0}+({z1}-{z0})*t/{D:.3f})"
        W2,H2=2112,1188   # 1.1x para tener margen de movimiento
        base=",".join(pre)
        if fit=="cover":
            chain=(f"[0:v]{base},scale={W2}:{H2}:force_original_aspect_ratio=increase,crop={W2}:{H2},setsar=1[c];")
        else:  # blur: imagen completa con fondo desenfocado
            chain=(f"[0:v]{base},split[a][b];[a]scale={W2}:{H2}:force_original_aspect_ratio=increase,crop={W2}:{H2},boxblur=40:2,eq=brightness=-0.12[bg];"
                   f"[b]scale={W2}:{H2}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[c];")
        chain+=(f"[c]scale=w='max(1924,trunc({W2}*{zexp}/1.1/2)*2)':h='max(1084,trunc({H2}*{zexp}/1.1/2)*2)':eval=frame,"
                f"crop=1920:1080:x='(iw-1920)/2+({px})*(iw-1920)/2*(2*t/{D:.3f}-1)':y='(ih-1080)/2+({py})*(ih-1080)/2*(2*t/{D:.3f}-1)',"
                f"{GRADE},noise=alls=5:allf=t[k];[1:v]format=rgba[vg];[k][vg]overlay=0:0,format=yuv420p[o]")
    cmd=["ffmpeg","-v","error","-y",*inp,"-filter_complex",chain,"-map","[o]","-t",f"{dur:.3f}","-r","30","-shortest",
         "-c:v","libx264","-preset","veryfast","-crf","17","-pix_fmt","yuv420p","-an",out]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: print("ERROR",i,shot,r.stderr[-800:],flush=True); raise SystemExit(1)
    open(out+".key","w").write(key)
    return out
def clips():
    jobs=[]
    for i,(t0,shot) in enumerate(SHOTS):
        t1=SHOTS[i+1][0] if i+1<len(SHOTS) else END
        jobs.append((i,shot,t0,t1-t0))
    with ThreadPoolExecutor(4) as ex: outs=list(ex.map(lambda j:build(*j),jobs))
    with open(f"{B}/concat.txt","w") as f:
        for o in outs: f.write(f"file '{o}'\n")
    subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",f"{B}/concat.txt","-c","copy",f"{B}/base.mp4"],check=True)
    print("base lista",flush=True)
def final(t_from=None,t_to=None,name="documental.mp4"):
    G=f"{B}/gfx"
    inp=["-i",f"{B}/base.mp4"]; fc=[]; n=1
    # audio: narración, música, efectos y sonido original de algunos clips
    ainp=["-i",f"{B}/narr.wav","-i",f"{B}/music.wav","-i",f"{B}/sfx.wav"]
    last="[0:v]"
    ov=OVERLAYS
    for k,(png,a,b,fi,fo) in enumerate(ov):
        inp+=["-loop","1","-framerate","30","-t",f"{b-a:.3f}","-i",f"{G}/{png}"]
        f=f"[{n}:v]format=rgba"
        if fi: f+=f",fade=t=in:st=0:d={fi}:alpha=1"
        if fo: f+=f",fade=t=out:st={b-a-fo:.3f}:d={fo}:alpha=1"
        f+=f",setpts=PTS+{a:.3f}/TB[g{k}]"; fc.append(f)
        fc.append(f"{last}[g{k}]overlay=0:0:eof_action=pass[v{k}]"); last=f"[v{k}]"; n+=1
    inp+=["-loop","1","-framerate","30","-i",f"{G}/logo_s.png"]
    fc.append(f"[{n}:v]format=rgba[lg]"); fc.append(f"{last}[lg]overlay=W-w-40:34:shortest=1[vl]"); last="[vl]"; n+=1
    fc.append(f"{last}fade=t=in:st=0:d=1.2,fade=t=out:st={END-2.5:.3f}:d=2.5,format=yuv420p[vout]")
    na=n; inp+=ainp
    # sonidos de clips
    mixin=[]
    for k,(src,ss,t0,dur,vol) in enumerate(CLIPSOUND):
        inp+=["-ss",f"{ss:.3f}","-t",f"{dur:.3f}","-i",path(src)]
        fc.append(f"[{na+3+k}:a]aformat=sample_rates=44100:channel_layouts=stereo,afade=t=in:d=0.3,afade=t=out:st={dur-0.6:.3f}:d=0.6,volume={vol},adelay={int(t0*1000)}|{int(t0*1000)}[cs{k}]")
        mixin.append(f"[cs{k}]")
    fc.append(f"[{na}:a]aformat=sample_rates=44100:channel_layouts=stereo,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,volume=1.0,asplit[nv][key]")
    fc.append(f"[{na+1}:a]volume=0.36[mus]")
    fc.append(f"[mus][key]sidechaincompress=threshold=0.04:ratio=6:attack=40:release=600[mduck]")
    fc.append(f"[{na+2}:a]volume=0.8[fx]")
    fc.append(f"[nv][mduck][fx]{''.join(mixin)}amix=inputs={3+len(mixin)}:normalize=0:duration=longest,alimiter=limit=0.95,atrim=0:{END:.3f}[aout]")
    cmd=["ffmpeg","-v","error","-stats","-y",*inp,"-filter_complex",";".join(fc),"-map","[vout]","-map","[aout]",
         "-c:v","libx264","-preset","faster","-crf","21","-tune","grain","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart"]
    if t_from is not None: cmd+=["-ss",str(t_from),"-to",str(t_to)]
    cmd+=[f"{B}/{name}"]
    subprocess.run(cmd,check=True)
    print("final listo",name,flush=True)
if MODE in ("all","clips"): clips()
if MODE in ("all","final"): final()
if MODE=="preview": final(float(sys.argv[3]),float(sys.argv[4]),"preview.mp4")
