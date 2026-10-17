import hashlib, sys, time, urllib.request, urllib.parse, os
UA = "CuriosidadesDelMundoVideo/1.0 (https://github.com/morillorivasandreiverjosue-afk/andry)"
for n, t in enumerate(l.strip() for l in open(sys.argv[1]) if l.strip()):
    out = f"{n:02d}.jpg"
    if os.path.exists(out): continue
    f = t.replace("File:", "").replace(" ", "_")
    h = hashlib.md5(f.encode()).hexdigest()
    q = urllib.parse.quote(f)
    for w in (1920, 1280, 960, 500, None):
        url = (f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{w}px-{q}" if w
               else f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}")
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()
            open(out, "wb").write(d); print(out, w, t, flush=True); break
        except Exception as e:
            print("  ", w, e, flush=True); time.sleep(1.5)
    time.sleep(1)
