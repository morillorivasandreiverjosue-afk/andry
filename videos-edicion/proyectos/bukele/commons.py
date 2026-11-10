"""Búsqueda y descarga de material libre (fotos, videos, mapas) en Wikimedia Commons.

Uso:
  python3 commons.py buscar "texto" [--videos] [--n 30]     # lista candidatos
  python3 commons.py bajar "File:Nombre.jpg" [...]          # descarga a material/ con su licencia
"""
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "DocumentalArchivoBot/1.1 (proyecto educativo sin fines de lucro)"
MATERIAL = Path(__file__).parent / "material"
CREDITOS = MATERIAL / "creditos.json"


def api(**p):
    time.sleep(0.4)
    p.update(format="json", formatversion=2)
    url = API + "?" + urllib.parse.urlencode(p)
    for intento in range(30):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:  # noqa: BLE001
            espera(e, intento)
            err = e
    raise err


def espera(e, intento):
    """Espera antes de reintentar; si Wikimedia pide calma (error 429), espera más."""
    seg = min(60, 5 * 2 ** intento)
    if getattr(e, "code", None) == 429:
        try:
            seg = max(seg, min(120, int(e.headers.get("Retry-After", 0))))
        except (TypeError, ValueError):
            pass
        seg = max(seg, 90)
    time.sleep(seg)


def limpiar(html):
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()


def info(paginas):
    out = []
    for p in paginas:
        if "imageinfo" not in p:
            continue
        ii = p["imageinfo"][0]
        md = ii.get("extmetadata", {})
        out.append({
            "titulo": p["title"], "url": ii["url"], "mime": ii.get("mime"), "w": ii.get("width"),
            "h": ii.get("height"), "dur": ii.get("duration"), "bytes": ii.get("size"),
            "thumb": ii.get("thumburl"),
            "licencia": limpiar(md.get("LicenseShortName", {}).get("value")),
            "autor": limpiar(md.get("Artist", {}).get("value"))[:120],
            "fecha": limpiar(md.get("DateTimeOriginal", {}).get("value"))[:40],
            "desc": limpiar(md.get("ImageDescription", {}).get("value"))[:200],
            "pagina": ii.get("descriptionurl"),
        })
    return out


PROPS = dict(prop="imageinfo", iiprop="url|size|mime|extmetadata|dimensions", iiurlwidth=320,
             iiextmetadatafilter="LicenseShortName|Artist|DateTimeOriginal|ImageDescription")


def buscar(q, videos=False, n=30):
    filtro = "filetype:video" if videos else "filetype:bitmap"
    d = api(action="query", generator="search", gsrnamespace=6, gsrsearch=f"{filtro} {q}", gsrlimit=n, **PROPS)
    pags = sorted(d.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
    return info(pags)


def datos(titulos, ancho=320):
    d = api(action="query", titles="|".join(titulos), **dict(PROPS, iiurlwidth=ancho))
    return info(d.get("query", {}).get("pages", []))


def bajar(titulos):
    MATERIAL.mkdir(exist_ok=True)
    cred = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    for i in range(0, len(titulos), 20):
        for f in datos(titulos[i:i + 20], ancho=1920):
            nombre = f["titulo"].split(":", 1)[1].replace(" ", "_")
            dest = MATERIAL / nombre
            if not dest.exists():
                url = f["url"]
                if f["mime"].startswith("image/") and (f["w"] or 0) > 2400:
                    # miniatura estándar de 1920 px (Wikimedia limita los tamaños no estándar)
                    url = f["thumb"]
                if f["mime"].startswith(("video/", "application/ogg")) and (f["bytes"] or 0) > 150e6:
                    # videos enormes: usar la versión recodificada a 720p que ofrece Commons
                    der = api(action="query", titles=f["titulo"], prop="videoinfo",
                              viprop="derivatives")["query"]["pages"][0]["videoinfo"][0]["derivatives"]
                    der = [d for d in der if d.get("height") == 720] or der
                    url = der[0]["src"]
                for intento in range(30):
                    r = subprocess.run(["curl", "-sS", "-L", "-f", "-A", UA, "-o", str(dest), url],
                                       capture_output=True, text=True)
                    if r.returncode == 0:
                        break
                    dest.unlink(missing_ok=True)
                    print("  reintento", nombre, r.stderr.strip()[:120], file=sys.stderr, flush=True)
                    time.sleep(min(120, 15 * (intento + 1)))
                time.sleep(2.0)
            cred[nombre] = {k: f[k] for k in ("titulo", "autor", "licencia", "pagina")}
            print("ok", nombre, f["licencia"], flush=True)
            CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=1))
    CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=1))


OPENVERSE = "https://api.openverse.org/v1/images/"


def bajar_openverse(ids):
    """Descarga imágenes de Openverse (Flickr y otros) por su id. Se guardan como ov_<id>.jpg."""
    MATERIAL.mkdir(exist_ok=True)
    cred = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    for i in ids:
        nombre = f"ov_{i[:8]}.jpg"
        r = None
        for intento in range(6):
            try:
                req = urllib.request.Request(f"{OPENVERSE}{i}/", headers={"User-Agent": UA})
                r = json.load(urllib.request.urlopen(req, timeout=60))
                break
            except Exception as e:  # noqa: BLE001
                print("  reintento", i[:8], e, file=sys.stderr, flush=True)
                time.sleep(5 * (intento + 1))
        if r is None:
            print("FALLO", i)
            continue
        if r["license"] not in ("cc0", "pdm", "by", "by-sa"):
            print("licencia no permitida", i, r["license"])
            continue
        dest = MATERIAL / nombre
        if not dest.exists():
            url = r["url"]
            if "upload.wikimedia.org" in url and (r.get("width") or 0) > 1920:
                url = url_directa(url.rsplit("/", 1)[1], 1920)
            for intento in range(6):
                res = subprocess.run(["curl", "-sS", "-L", "-f", "-A", UA, "-o", str(dest), url],
                                     capture_output=True, text=True)
                if res.returncode == 0:
                    break
                dest.unlink(missing_ok=True)
                time.sleep(10 * (intento + 1))
            if not dest.exists():
                print("FALLO descarga", i)
                continue
        lic = {"cc0": "CC0", "pdm": "Dominio público"}.get(r["license"],
                                                          f"CC {r['license'].upper()} {r.get('license_version', '')}")
        cred[nombre] = {"titulo": r.get("title"), "autor": r.get("creator"), "licencia": lic.strip(),
                        "pagina": r.get("foreign_landing_url")}
        print("ok", nombre, lic, "|", r.get("title"))
        time.sleep(0.5)
    CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "buscar":
        a = sys.argv[2:]
        vid = "--videos" in a
        n = int(a[a.index("--n") + 1]) if "--n" in a else 30
        for f in buscar(a[0], vid, n):
            extra = f" {f['dur']:.0f}s" if f["dur"] else ""
            print(f"{f['titulo'][5:]} | {f['w']}x{f['h']}{extra} | {f['licencia']} | {f['fecha']} | {f['desc'][:90]}")
    elif sys.argv[1] == "bajar":
        bajar(sys.argv[2:])
    elif sys.argv[1] == "openverse":
        bajar_openverse(sys.argv[2:])


def url_directa(titulo, ancho=None):
    """URL de upload.wikimedia.org calculada a partir del nombre (sin usar la API)."""
    import hashlib
    nombre = titulo.split(":", 1)[-1].replace(" ", "_")
    h = hashlib.md5(nombre.encode()).hexdigest()
    q = urllib.parse.quote(nombre)
    base = "https://upload.wikimedia.org/wikipedia/commons"
    if ancho:
        return f"{base}/thumb/{h[0]}/{h[:2]}/{q}/{ancho}px-{q}"
    return f"{base}/{h[0]}/{h[:2]}/{q}"


def bajar_directo(titulos):
    """Descarga sin la API. Imágenes: miniatura estándar de 1920 px (la que Wikimedia sirve sin
    límites) y, si la foto es más pequeña, el original. Videos: versión recodificada de Commons."""
    import hashlib
    MATERIAL.mkdir(exist_ok=True)
    for t in titulos:
        nombre = t.split(":", 1)[-1].replace(" ", "_")
        dest = MATERIAL / nombre
        if dest.exists() and dest.stat().st_size > 0:
            continue
        h = hashlib.md5(nombre.encode()).hexdigest()
        q = urllib.parse.quote(nombre)
        tc = f"https://upload.wikimedia.org/wikipedia/commons/transcoded/{h[0]}/{h[:2]}/{q}/{q}"
        if nombre.lower().endswith((".webm", ".ogv")):
            urls = [f"{tc}.1080p.vp9.webm", f"{tc}.720p.vp9.webm", f"{tc}.480p.vp9.webm"]
            if "A6iphPzEGtw" not in nombre:
                urls.append(url_directa(t))
        else:
            urls = [url_directa(t, 1920), url_directa(t)]
        ok, codigos = False, []
        for intento in range(10):
            codigos = []
            for u in urls:
                r = subprocess.run(["curl", "-sS", "-L", "-w", "%{http_code}", "-A", UA, "-o", str(dest), u],
                                   capture_output=True, text=True)
                codigo = r.stdout.strip()[-3:]
                codigos.append(codigo)
                if codigo == "200" and dest.stat().st_size > 1000:
                    ok = True
                    break
                dest.unlink(missing_ok=True)
                time.sleep(1.0)
            if ok or "429" not in codigos:
                break
            time.sleep(min(90, 15 * (intento + 1)))
        print("ok" if ok else f"FALLO {codigos}", nombre, flush=True)
        time.sleep(1.0)


def creditos_api(titulos):
    """Guarda autor, licencia y página de cada archivo (solo metadatos, en lotes y despacio)."""
    MATERIAL.mkdir(exist_ok=True)
    cred = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    faltan = [t for t in titulos if t.split(":", 1)[-1].replace(" ", "_") not in cred]
    for i in range(0, len(faltan), 20):
        for f in datos(faltan[i:i + 20]):
            nombre = f["titulo"].split(":", 1)[1].replace(" ", "_")
            cred[nombre] = {k: f[k] for k in ("titulo", "autor", "licencia", "pagina")}
        CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=1))
        print("créditos:", len(cred), flush=True)
        time.sleep(5)


def openverse_busqueda(consulta, filtro_titulo, maximo=12):
    """Busca en Openverse y descarga directamente desde los resultados (sin la ficha individual)."""
    MATERIAL.mkdir(exist_ok=True)
    cred = json.loads(CREDITOS.read_text()) if CREDITOS.exists() else {}
    url = OPENVERSE + "?" + urllib.parse.urlencode({"q": consulta, "page_size": 20,
                                                    "license": "cc0,pdm,by,by-sa"})
    d = None
    for intento in range(5):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}),
                                                 timeout=60))
            break
        except Exception as e:  # noqa: BLE001
            print("  reintento búsqueda", e, file=sys.stderr, flush=True)
            time.sleep(8 * (intento + 1))
    if d is None:
        return
    n = 0
    for r in d.get("results", []):
        if filtro_titulo.lower() not in (r.get("title") or "").lower() or n >= maximo:
            continue
        if r["license"] not in ("cc0", "pdm", "by", "by-sa"):
            continue
        nombre = f"ov_{r['id'][:8]}.jpg"
        dest = MATERIAL / nombre
        if not dest.exists():
            u = r["url"]
            if "upload.wikimedia.org" in u and (r.get("width") or 0) > 1920:
                u = url_directa(urllib.parse.unquote(u.rsplit("/", 1)[1]), 1920)
            res = subprocess.run(["curl", "-sS", "-L", "-f", "-m", "120", "-A", UA, "-o", str(dest), u],
                                 capture_output=True, text=True)
            if res.returncode != 0:
                dest.unlink(missing_ok=True)
                print("FALLO", nombre, res.stderr.strip()[:80], flush=True)
                continue
        lic = {"cc0": "CC0", "pdm": "Dominio público"}.get(r["license"],
                                                          f"CC {r['license'].upper()} {r.get('license_version', '')}")
        cred[nombre] = {"titulo": r.get("title"), "autor": r.get("creator"), "licencia": lic.strip(),
                        "pagina": r.get("foreign_landing_url")}
        CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=1))
        n += 1
        print("ok", nombre, lic, "|", r.get("title"), flush=True)
        time.sleep(0.5)
