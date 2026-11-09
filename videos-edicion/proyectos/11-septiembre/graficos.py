"""Genera los gráficos PNG (con transparencia) del documental."""
import sys, os, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S=sys.argv[1]; F=f"{S}/fonts"; O=f"{S}/build/gfx"; os.makedirs(O,exist_ok=True)
W,H=1920,1080
RED=(229,32,42); WHITE=(255,255,255); GREY=(200,200,200)
def font(name,size):
    p={"bebas":"fontsource-bebas-neue/files/bebas-neue-latin-400-normal.woff",
       "oswald":"fontsource-oswald/files/oswald-latin-500-normal.woff",
       "oswaldL":"fontsource-oswald/files/oswald-latin-300-normal.woff",
       "inter":"fontsource-inter/files/inter-latin-400-normal.woff",
       "interB":"fontsource-inter/files/inter-latin-700-normal.woff",
       "interBl":"fontsource-inter/files/inter-latin-900-normal.woff"}[name]
    return ImageFont.truetype(f"{F}/{p}",size)
def spaced(d,xy,text,f,fill,sp,anchor="l"):
    # texto con espaciado entre letras
    w=sum(d.textlength(c,font=f) for c in text)+sp*(len(text)-1)
    x,y=xy
    if anchor=="m": x-=w/2
    if anchor=="r": x-=w
    for c in text:
        d.text((x,y),c,font=f,fill=fill); x+=d.textlength(c,font=f)+sp
    return w
def shadow(img,r=10,a=170):
    al=img.split()[3].filter(ImageFilter.GaussianBlur(r))
    sh=Image.new("RGBA",img.size,(0,0,0,0)); sh.putalpha(al.point(lambda v:min(255,v*a//255)))
    out=Image.new("RGBA",img.size,(0,0,0,0)); out.alpha_composite(sh,(0,0)); out.alpha_composite(img); return out
def globe(d,cx,cy,r,col,w=3):
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=col,width=w)
    for k in (0.45,0.85):
        d.ellipse((cx-r*k,cy-r,cx+r*k,cy+r),outline=col,width=max(1,w-1))
    d.line((cx,cy-r,cx,cy+r),fill=col,width=max(1,w-1))
    for k in (-0.5,0,0.5):
        yy=cy+r*k; xx=r*math.sqrt(1-k*k); d.line((cx-xx,yy,cx+xx,yy),fill=col,width=max(1,w-1))

# 1) Logo arriba a la derecha
def logo():
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    f1=font("bebas",50); f2=font("oswaldL",19)
    t1="CURIOSIDADES"; t2="DEL MUNDO"
    w1=d.textlength(t1,font=f1)
    x1=W-50-w1; y=38
    globe(d,x1-40,y+30,24,WHITE,3)
    d.text((x1,y),t1,font=f1,fill=WHITE)
    d.rectangle((x1,y+58,x1+44,y+62),fill=RED)
    spaced(d,(x1+54,y+50),t2,f2,GREY,7)
    im=shadow(im,6,200)
    # opacidad general 88 %
    a=im.split()[3].point(lambda v:int(v*0.88)); im.putalpha(a)
    im.save(f"{O}/logo.png")
    bb=im.getbbox(); sm=im.crop((bb[0]-12,bb[1]-12,bb[2]+12,bb[3]+12))
    sm=sm.resize((int(sm.width*1.3),int(sm.height*1.3)),Image.LANCZOS); sm.save(f"{O}/logo_s.png")

# 2) Tarjetas de capítulo
def wrap(d,text,f,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textlength(t,font=f)<=maxw: cur=t
        else: lines.append(cur); cur=w
    lines.append(cur); return lines
def card(i,num,title,fname):
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    fN=font("oswald",34); fT=font("bebas",132); fBig=font("bebas",520)
    # número gigante de fondo
    if num.isdigit():
        g=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(g)
        gd.text((W-140,H/2+30),num,font=fBig,fill=(255,255,255,26),anchor="rm")
        im.alpha_composite(g)
    lab=("CAPÍTULO "+num) if num.isdigit() else num
    x=150; lines=wrap(d,title.upper(),fT,1250)
    th=len(lines)*122
    y0=H/2-th/2-20
    d.rectangle((x,y0-66,x+70,y0-60),fill=RED)
    spaced(d,(x+90,y0-86),lab,fN,RED,9)
    for k,l in enumerate(lines):
        d.text((x-6,y0+k*122),l,font=fT,fill=WHITE)
    im=shadow(im,14,220)
    im.save(f"{O}/{fname}")

# 3) Rótulos (hora + descripción) abajo a la izquierda
def rotulo(fname,big,small):
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    fB=font("bebas",96); fS=font("oswald",34)
    x=110; y=H-250
    d.rectangle((x,y+12,x+8,y+176),fill=RED)
    d.text((x+30,y),big,font=fB,fill=WHITE)
    for k,l in enumerate(small.split("\n")):
        d.text((x+32,y+100+k*44),l.upper(),font=fS,fill=(235,235,235))
    im=shadow(im,10,230); im.save(f"{O}/{fname}")

# 4) Título de apertura y cierre
def apertura():
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    f0=font("oswaldL",30); fT=font("bebas",300); f2=font("oswald",44)
    spaced(d,(W/2,300),"CURIOSIDADES DEL MUNDO PRESENTA",f0,GREY,12,"m")
    d.text((W/2,H/2+10),"11 DE SEPTIEMBRE",font=fT,fill=WHITE,anchor="mm")
    d.rectangle((W/2-60,H/2+150,W/2+60,H/2+156),fill=RED)
    spaced(d,(W/2,H/2+185),"EL DÍA QUE CAMBIÓ EL MUNDO",f2,WHITE,14,"m")
    im=shadow(im,16,230); im.save(f"{O}/apertura.png")
def cierre():
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    fT=font("bebas",120); f2=font("oswald",40)
    cx=W/2; globe(d,cx,330,70,WHITE,5)
    d.text((cx,470),"CURIOSIDADES DEL MUNDO",font=fT,fill=WHITE,anchor="mt")
    # botón suscríbete
    bw,bh=520,96; d.rounded_rectangle((cx-bw/2,650,cx+bw/2,650+bh),radius=14,fill=RED)
    spaced(d,(cx,672),"SUSCRÍBETE",font("oswald",46),WHITE,10,"m")
    spaced(d,(cx,800),"EN MEMORIA DE LAS 2.977 VÍCTIMAS",font("oswaldL",30),GREY,8,"m")
    im=shadow(im,14,220); im.save(f"{O}/cierre.png")
def vineta():
    import numpy as np
    y,x=np.mgrid[0:H,0:W]; r=np.sqrt(((x-W/2)/(W/2))**2+((y-H/2)/(H/2))**2)
    a=np.clip((r-0.55)/0.75,0,1)**1.6*200
    im=Image.fromarray(np.dstack([np.zeros((H,W,3),np.uint8),a.astype(np.uint8)]),"RGBA"); im.save(f"{O}/vineta.png")
    # degradado para tarjetas (oscurece la izquierda)
    a=np.clip(1.15-x/W*1.0,0.35,1)*215
    Image.fromarray(np.dstack([np.zeros((H,W,3),np.uint8),a.astype(np.uint8)]),"RGBA").save(f"{O}/oscuro.png")
    a=np.clip((y-H*0.55)/(H*0.45),0,1)**1.2*190
    Image.fromarray(np.dstack([np.zeros((H,W,3),np.uint8),a.astype(np.uint8)]),"RGBA").save(f"{O}/bajo.png")

CARDS=[("PRÓLOGO","Una mañana que cambió el mundo"),
 ("1","Las torres que representaban el poder de Estados Unidos"),
 ("2","¿Quiénes estaban detrás del atentado?"),
 ("3","11 de septiembre: todo comienza"),
 ("4","El ataque se extiende"),
 ("5","El colapso de las Torres Gemelas"),
 ("6","Las víctimas y los héroes de aquel día"),
 ("7","La respuesta de Estados Unidos"),
 ("8","El mundo después del 11 de septiembre"),
 ("9","Ground Zero: el lugar que nunca se olvidará"),
 ("EPÍLOGO","Una fecha que cambió la historia")]
ROT=[("r0846","08:46 AM","Vuelo American Airlines 11\nimpacta la Torre Norte"),
 ("r0903","09:03 AM","Vuelo United Airlines 175\nimpacta la Torre Sur"),
 ("r0937","09:37 AM","Vuelo American Airlines 77\nimpacta el Pentágono"),
 ("r1003","10:03 AM","Vuelo United Airlines 93\ncae en Shanksville, Pensilvania"),
 ("r0959","09:59 AM","Se derrumba\nla Torre Sur"),
 ("r1028","10:28 AM","Se derrumba\nla Torre Norte"),
 ("r1993","26/02/1993","Atentado con bomba\nen el World Trade Center"),
 ("r2977","2.977","Víctimas mortales\nde 90 países"),
 ("r343","343","Bomberos de Nueva York\nperdieron la vida"),
 ("r19","19","Secuestradores\nen cuatro aviones"),
 ("r2001","OCTUBRE 2001","Comienza la guerra\nen Afganistán"),
 ("r2011","MAYO 2011","Muere Osama bin Laden\nen Pakistán"),
 ("r1wtc","541 METROS","One World Trade Center\ninaugurado en 2014"),
 ("rtsa","NOV. 2001","Se crea la TSA\n(seguridad en el transporte)"),
 ("r110","110 PISOS","Torre Norte y Torre Sur\n417 y 415 metros"),
]
logo(); apertura(); cierre(); vineta()
for i,(n,t) in enumerate(CARDS): card(i,n,t,f"card{i:02d}.png")
for r in ROT: rotulo(r[0]+".png",r[1],r[2])
print("ok")
