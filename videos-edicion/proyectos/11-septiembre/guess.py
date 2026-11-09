import sys, hashlib, urllib.request, urllib.parse, urllib.error, time, os
UA={"User-Agent":"ClaudeCodeDocumentaryBot/1.0 (https://claude.ai/code) python-urllib/3.13"}
out=sys.argv[1]; os.makedirs(out,exist_ok=True)
for name in sys.argv[2:]:
    n=name.replace(" ","_"); h=hashlib.md5(n.encode()).hexdigest()
    q=urllib.parse.quote(n)
    url=f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/1280px-{q}"
    if n.lower().endswith((".tif",".tiff")): url+=".jpg"
    for k in range(4):
        try:
            b=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
            fn=os.path.join(out,hashlib.md5(n.encode()).hexdigest()[:8]+".jpg"); open(fn,"wb").write(b)
            print("OK",os.path.basename(fn),len(b),name,flush=True); break
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(12); continue
            if e.code in (400,404,500):
                # quizá es más pequeña que 1280: probar el original
                try:
                    b=urllib.request.urlopen(urllib.request.Request(f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}",headers=UA),timeout=60).read()
                    fn=os.path.join(out,hashlib.md5(n.encode()).hexdigest()[:8]+".jpg"); open(fn,"wb").write(b); print("OK-orig",os.path.basename(fn),len(b),name,flush=True)
                except Exception as e2: print("NO",e.code,name,flush=True)
                break
            print("ERR",e.code,name); break
    time.sleep(1.2)
