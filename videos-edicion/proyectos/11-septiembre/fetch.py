"""Descarga robusta desde Wikimedia Commons (una petición a la vez, respeta los 429)."""
import sys, json, time, urllib.request, urllib.parse, urllib.error, os, re
UA={"User-Agent":"ClaudeCodeDocumentaryBot/1.0 (https://claude.ai/code) python-urllib/3.13"}
S=sys.argv[1]; M=f"{S}/media"
def get(url, dest=None, minbytes=2000):
    wait=20
    for k in range(10):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=120)
            if dest:
                tmp=dest+".part"
                with open(tmp,"wb") as f:
                    while True:
                        b=r.read(1<<20)
                        if not b: break
                        f.write(b)
                if os.path.getsize(tmp)<minbytes: raise Exception("small")
                os.replace(tmp,dest); return True
            return r.read()
        except urllib.error.HTTPError as e:
            if e.code==404: print("404",url[:100],flush=True); return None
            ra=e.headers.get("Retry-After"); w=int(ra) if ra and ra.isdigit() else wait
            print(f"  {e.code} esperando {w}s",flush=True); time.sleep(w); wait=min(wait*2,180)
        except Exception as e:
            print("  err",e,flush=True); time.sleep(wait); wait=min(wait*2,180)
    return None
def api(p):
    p.update(format="json"); r=get("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(p))
    return json.loads(r) if r else {}
B="https://upload.wikimedia.org/wikipedia/commons/transcoded"
VIDS=json.load(open(f"{S}/scripts/vids.json"))
os.makedirs(f"{M}/vid",exist_ok=True)
for name,url in VIDS:
    dest=f"{M}/vid/{name}"
    if os.path.exists(dest) and os.path.getsize(dest)>100000: continue
    ok=get(url,dest,100000); print(name,"OK" if ok else "FALLO",flush=True); time.sleep(3)
credits=open(f"{M}/img/creditos.tsv","a")
for line in open(f"{S}/scripts/imgs.txt"):
    if not line.strip(): continue
    tag,q,n=line.strip().split("|"); n=int(n)
    d=f"{M}/img/{tag}"; os.makedirs(d,exist_ok=True)
    have=len([x for x in os.listdir(d) if x.endswith(".jpg")])
    if have>=n: continue
    r=api(dict(action="query",generator="search",gsrnamespace=6,gsrlimit=40,gsrsearch=q+" filetype:bitmap",prop="imageinfo",iiprop="url|size|extmetadata",iiurlwidth=1920,iiextmetadatafilter="LicenseShortName|Artist"))
    pages=sorted(r.get("query",{}).get("pages",{}).values(),key=lambda p:p.get("index",0))
    k=have
    for p in pages[have:]:
        ii=p["imageinfo"][0]; em=ii.get("extmetadata",{})
        lic=em.get("LicenseShortName",{}).get("value","")
        if not re.search(r"Public domain|CC BY|CC0|PD",lic,re.I) or "NC" in lic or "ND" in lic: continue
        if ii["width"]<1000: continue
        fn=f"{d}/{k+1:02d}.jpg"
        if not get(ii.get("thumburl") or ii["url"],fn,10000): continue
        k+=1
        art=re.sub("<[^>]+>","",em.get("Artist",{}).get("value",""))[:80].replace("\n"," ")
        credits.write(f"{tag}/{k:02d}.jpg\t{p['title']}\t{lic}\t{art}\n"); credits.flush()
        time.sleep(1.5)
        if k>=n: break
    print(tag,k,flush=True); time.sleep(3)
print("FIN")
