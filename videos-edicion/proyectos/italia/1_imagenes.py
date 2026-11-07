"""Descarga de Wikimedia Commons (licencias libres) una imagen para cada escena del plan.

Uso: python3 1_imagenes.py salida
Guarda salida/img/<audio>_<n>.jpg, salida/imagenes.json y salida/creditos.txt
"""
import json, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

import plan

UA = "GigaCuriosidadesDoc/1.0 (documental personal; peticiones lentas)"
LIBRES = re.compile(r"(public domain|cc0|cc[- ]by|pd|gfdl|attribution|no restrictions)", re.I)


def get(url, intentos=60, espera=None):
    for _ in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(espera or int(e.headers.get("retry-after") or 10) + 2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5)
    raise RuntimeError("no se pudo descargar " + url)


def buscar(q, n=12):
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": q + " filetype:bitmap",
         "gsrnamespace": 6, "gsrlimit": n, "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime",
         "iiurlwidth": 1920, "iiextmetadatafilter": "LicenseShortName|Artist"}
    d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p), intentos=200, espera=3))
    pags = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 0))
    res = []
    for pg in pags:
        ii = pg["imageinfo"][0]
        md = ii.get("extmetadata", {})
        artista = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        res.append({"titulo": pg["title"], "w": ii["width"], "h": ii["height"], "mime": ii.get("mime", ""),
                    "thumb": ii.get("thumburl", ii["url"]).split("?")[0].replace("thumb.wikimedia.org", "upload.wikimedia.org"),
                    "licencia": md.get("LicenseShortName", {}).get("value", ""), "autor": artista[:120],
                    "pagina": ii.get("descriptionurl", "")})
    return res


def miniatura(r):
    """URL de una miniatura (el servidor limita mucho más las descargas de originales)."""
    u = r["thumb"]
    pre = "https://upload.wikimedia.org/wikipedia/commons/"
    if "/thumb/" in u or not u.startswith(pre):
        return u
    resto = u[len(pre):]
    nombre = resto.split("/")[-1]
    ancho = 1280 if r["w"] > 1280 else 960
    extra = "lossy-page1-" if nombre.lower().endswith((".tif", ".tiff")) else ""
    fin = ".jpg" if extra else ""
    return f"{pre}thumb/{resto}/{extra}{ancho}px-{nombre}{fin}"


def puntuar(r):
    if r["mime"] not in ("image/jpeg", "image/png", "image/tiff", "image/webp"):
        return -1
    if not LIBRES.search(r["licencia"] or ""):
        return -1
    if r["w"] < 900 or r["h"] < 500:
        return -1
    asp = r["w"] / r["h"]
    s = 3 if 1.3 <= asp <= 2.1 else (2 if asp >= 1.05 else 1)
    return s + min(r["w"], 4000) / 4000


def main():
    sal = Path(sys.argv[1]); (sal / "img").mkdir(parents=True, exist_ok=True)
    rj = sal / "imagenes.json"
    hecho = json.loads(rj.read_text()) if rj.exists() else {}
    usados = {v["titulo"] for v in hecho.values()}
    forzar = dict(a.split("=", 1) for a in sys.argv[2:])  # clave=nueva búsqueda
    for ia, escenas in enumerate(plan.AUDIOS):
        for n, (t, q) in enumerate(escenas):
            clave = f"{ia}_{n:03d}"
            q = forzar.get(clave, q)
            if clave in hecho and clave not in forzar and (sal / "img" / f"{clave}.jpg").exists():
                continue
            if clave in hecho:
                usados.discard(hecho[clave]["titulo"])
            cands = [r for r in buscar(q) if r["titulo"] not in usados and puntuar(r) >= 0]
            if not cands:
                cands = [r for r in buscar(" ".join(q.split()[:2])) if r["titulo"] not in usados and puntuar(r) >= 0]
            if not cands:
                print(f"!! {clave} sin resultado: {q}", flush=True)
                continue
            # entre los 4 primeros resultados (los más relevantes), el de mejor encuadre
            mejor = max(cands[:4], key=puntuar)
            mejor["busqueda"] = q
            hecho[clave] = mejor
            usados.add(mejor["titulo"])
            (sal / "img" / f"{clave}.jpg").unlink(missing_ok=True)
            rj.write_text(json.dumps(hecho, ensure_ascii=False, indent=1))
            print(f"{clave} {q!r} -> {mejor['titulo']} [{mejor['licencia']}]", flush=True)
    # segunda pasada: descargar (el servidor de imágenes limita la velocidad, así que se reintenta)
    for clave, v in sorted(hecho.items()):
        ruta = sal / "img" / f"{clave}.jpg"
        if ruta.exists():
            continue
        ruta.write_bytes(get(miniatura(v), intentos=200, espera=3))
        print("  descargada", clave, flush=True)
    with open(sal / "creditos.txt", "w") as f:
        f.write("Imágenes de Wikimedia Commons (licencias libres)\n\n")
        for k in sorted(hecho):
            v = hecho[k]
            f.write(f"{v['titulo'][5:]} — {v['autor'] or 'autor desconocido'} — {v['licencia']} — {v['pagina']}\n")


if __name__ == "__main__":
    main()
