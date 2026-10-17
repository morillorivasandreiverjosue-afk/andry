"""Acceso educado a Wikimedia Commons: búsqueda, metadatos y descarga con pausas y reintentos."""
import json
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "BolivarDocumental/1.0 (video educativo; descarga puntual de obras de dominio publico)"
_ultimo = [0.0]


def _get(url, binario=False, intentos=8, espera=4, tope=60):
    for _ in range(intentos):
        pausa = 1.5 - (time.time() - _ultimo[0])
        if pausa > 0:
            time.sleep(pausa)
        _ultimo[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                datos = r.read()
            return datos if binario else json.loads(datos)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(espera)
        espera = min(espera * 2, tope)
    raise RuntimeError(f"Wikimedia no respondió: {url}")


def api(**params):
    params.update(format="json", formatversion=2)
    return _get(API + "?" + urllib.parse.urlencode(params))


def buscar(texto, n=8):
    """Devuelve títulos de archivos (imágenes) que coinciden con el texto."""
    r = api(action="query", list="search", srnamespace=6, srlimit=n, srsearch=f"{texto} filetype:bitmap")
    return [s["title"] for s in r["query"]["search"]]


def info(titulos, ancho=2400):
    """Metadatos (url a ~ancho px, tamaño, autor, licencia) de varios archivos."""
    r = api(action="query", titles="|".join(titulos), prop="imageinfo", iiprop="url|size|extmetadata",
            iiurlwidth=ancho, iiextmetadatafilter="Artist|LicenseShortName|DateTimeOriginal|ObjectName")
    out = {}
    for p in r["query"]["pages"]:
        if "imageinfo" not in p:
            continue
        ii = p["imageinfo"][0]
        md = {k: v.get("value", "") for k, v in ii.get("extmetadata", {}).items()}
        out[p["title"]] = {"url": ii.get("thumburl") or ii["url"], "ancho": ii["width"], "alto": ii["height"],
                           "pagina": ii.get("descriptionurl", ""), "autor": md.get("Artist", ""),
                           "licencia": md.get("LicenseShortName", ""), "fecha": md.get("DateTimeOriginal", "")}
    return out


def url_descarga(m, ancho=1920):
    """URL de una miniatura en tamaño estándar (lo que pide Wikimedia) o el original si es más pequeño."""
    # thumb.wikimedia.org no está permitido en este entorno: las mismas rutas sirven desde upload.wikimedia.org
    base = m["url"].split("?")[0].replace("://thumb.wikimedia.org/", "://upload.wikimedia.org/")
    if m["ancho"] <= ancho:
        return base
    if "/thumb/" not in base:
        dir_, nombre = base.rsplit("/", 1)
        return f"{dir_.replace('/commons/', '/commons/thumb/')}/{nombre}/{ancho}px-{nombre}"
    dir_, nombre = base.rsplit("/", 1)
    return f"{dir_}/{ancho}px-{dir_.rsplit('/', 1)[1]}"


def descargar(m):
    # el servidor de imágenes limita mucho por IP: esperas largas antes de rendirse
    return _get(url_descarga(m), binario=True, intentos=14, espera=15, tope=180)
