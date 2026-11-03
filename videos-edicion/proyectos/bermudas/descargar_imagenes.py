"""Descarga fotos de dominio público (NASA y similares) desde Wikimedia Commons (páginas web públicas).

Uso: python3 descargar_imagenes.py <carpeta_destino> [inverso]
(con «inverso» recorre los temas desde el final, para descargar con dos procesos a la vez)
Por cada tema busca archivos en Commons, se queda solo con los que tienen licencia de dominio público
y descarga la versión de 1920 px. Guarda creditos.json con el autor y la licencia de cada foto.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

UA = "BermudaDocumentaryBuilder/1.0 (https://github.com/morillorivasandreiverjosue-afk/andry)"
API = "https://commons.wikimedia.org/w/api.php"

# tema -> búsqueda en Commons (cuántas fotos)
TEMAS = {
    "mapa": ("Bermuda Triangle map", 3),
    "bermudas_espacio": ("Bermuda islands from space ISS", 3),
    "oceano": ("NOAA Photo Library ocean waves", 5),
    "tormenta_mar": ("NOAA Photo Library storm waves ship", 5),
    "avenger": ("TBM Avenger", 5),
    "cyclops": ("USS Cyclops (AC-4)", 4),
    "radio": ("radioman US Navy World War II", 3),
    "huracan": ("hurricane from International Space Station", 4),
    "mariner": ("PBM Mariner", 3),
    "rescate": ("Coast Guard search rescue aircraft", 3),
    "rayos": ("NOAA Photo Library lightning", 3),
    "barco_antiguo": ("collier US Navy 1918", 2),
    "atlantida": ("Atlantis Kircher Mundus Subterraneus", 2),
    "ovni": ("flying saucer 1952 photograph", 2),
    "brujula": ("ship compass binnacle", 2),
    "corriente_golfo": ("Gulf Stream NASA MODIS", 2),
    "arrecife": ("Bahamas from International Space Station", 3),
    "naufragio": ("shipwreck NOAA National Marine Sanctuaries", 4),
    "satelite": ("GOES satellite hurricane image", 2),
    "metano": ("methane seep NOAA Okeanos", 2),
    "miami": ("Miami Florida from International Space Station", 2),
    "puerto_rico": ("Puerto Rico from International Space Station", 2),
    "faro": ("lighthouse storm NOAA", 2),
    "noche_mar": ("moon over ocean International Space Station", 2),
    "base_aerea": ("Naval Air Station Fort Lauderdale", 2),
}

PD = ("public domain", "pd-", "cc0")
WEB = "https://commons.wikimedia.org"


def leer(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            time.sleep(8 * (intento + 1))
    return None


def leer_rapido(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for intento in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                datos = r.read()
            time.sleep(4.0)  # ritmo tranquilo para no saturar el servidor
            return datos
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 500):
                return None
            time.sleep(60)  # 429: demasiadas peticiones, esperar un minuto
        except Exception:
            time.sleep(3 * (intento + 1))
    return None


def buscar(q):
    """Busca en Commons (página web de búsqueda) y devuelve nombres de archivo."""
    url = WEB + "/w/index.php?" + urllib.parse.urlencode(
        {"title": "Special:Search", "search": q, "ns6": "1", "fulltext": "1", "limit": "30"})
    html = (leer(url) or b"").decode("utf-8", "ignore")
    vistos = []
    for f in re.findall(r'href="/wiki/(File:[^"#?]+)"', html):
        if f not in vistos and re.search(r"\.(jpe?g|png|tiff?)$", f, re.I):
            vistos.append(f)
    return vistos


# Nombres de archivo con el código de catálogo de la NASA: obras del gobierno de EE. UU. (dominio público).
NASA_ID = re.compile(r"(NH_?\d{3,}|80-G-\d+|NOAA|USCG|U\.?S\._Navy|USN_|AS\d{1,2}-\d+-\d+|GPN-\d{4}-\d+|KSC-\d+|S\d{2}-\d+|\d{2}-H[CS]?-\d+|"
                     r"jsc\d{4}e\d+|NASA|Apollo_?\d+_.*(Launch|crew|Splashdown|Mission_Control))", re.I)


def directo(archivo):
    """URL de la versión de 1920 px calculada a partir del nombre (sin abrir la página)."""
    import hashlib
    nom = urllib.parse.unquote(archivo[5:]).replace(" ", "_")
    h = hashlib.md5(nom.encode()).hexdigest()
    q = urllib.parse.quote(nom)
    url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/1920px-{q}"
    if nom.lower().endswith((".tif", ".tiff")):
        url += ".jpg"
    return url, f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}"


def ficha(archivo):
    """Lee la página del archivo: licencia, autor, ancho y URL original."""
    html = (leer(WEB + "/wiki/" + archivo) or b"").decode("utf-8", "ignore")
    html = html.replace("&#95;", "_")
    lic = " ".join(sorted(set(re.findall(r'class="licensetpl_short"[^>]*>([^<]*)<', html)))).lower()
    if re.search(r'class="licensetpl_attr_req"[^>]*>true<', html):
        lic += " (atribución obligatoria)"
    orig = re.search(r'(https://upload\.wikimedia\.org/wikipedia/commons/([0-9a-f])/([0-9a-f]{2})/([^"?]+))'
                     r'\?[^"]*utm_content=original', html)
    ancho = re.search(r'class="fileInfo">\(([\d,\.\s]+)\s*(?:×|&#215;|x)', html)
    ancho = int(re.sub(r"\D", "", ancho.group(1))) if ancho else 0
    autor = re.search(r'id="fileinfotpl_aut"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', html, re.S)
    autor = re.sub(r"<[^>]+>", "", autor.group(1)).strip()[:200] if autor else ""
    return lic, orig, ancho, autor


def main():
    destino = Path(sys.argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    inverso = len(sys.argv) > 2 and sys.argv[2] == "inverso"
    cred_path = destino / ("creditos_inv.json" if inverso else "creditos.json")
    creditos = json.loads(cred_path.read_text()) if cred_path.exists() else {}
    temas = list(TEMAS.items())[::-1] if inverso else list(TEMAS.items())
    for tema, (q, cuantas) in temas:
        usados = set()
        for f in destino.glob("creditos*.json"):
            usados |= {c["titulo"] for c in json.loads(f.read_text()).values()}
        n = len(list(destino.glob(f"{tema}_[0-9]*.*")))
        if n >= cuantas:
            continue
        for archivo in buscar(q):
            if n >= cuantas:
                break
            if archivo in usados:
                continue
            if NASA_ID.search(archivo):  # foto oficial de la NASA: dominio público
                url, original = directo(archivo)
                datos = leer_rapido(url) or (None if archivo.lower().endswith((".tif", ".tiff"))
                                             else leer_rapido(original))
                if datos and len(datos) > 60000 and len(datos) < 40_000_000:
                    try:
                        from PIL import Image
                        import io
                        im = Image.open(io.BytesIO(datos))
                        if im.width < 1000:
                            continue
                    except Exception:
                        continue
                    ext = ".png" if archivo.lower().endswith(".png") else ".jpg"
                    while list(destino.glob(f"{tema}_{n}.*")):
                        n += 1
                    nombre = f"{tema}_{n}{ext}"
                    (destino / nombre).write_bytes(datos)
                    creditos[nombre] = {"titulo": archivo, "licencia": "public domain (NASA)", "autor": "NASA",
                                        "fuente": WEB + "/wiki/" + archivo}
                    n += 1
                    print(f"{nombre}  <- {archivo}  [NASA, dominio público]", flush=True)
                    cred_path.write_text(json.dumps(creditos, ensure_ascii=False, indent=1))
                continue
            lic, orig, ancho, autor = ficha(archivo)
            time.sleep(0.7)
            # solo dominio público y fotos grandes; nada con atribución obligatoria
            if not orig or not any(k in lic for k in PD) or "atribución" in lic or "by" in lic.split() or (ancho and ancho < 1000):
                continue
            url, a, b, nom = orig.groups()
            if ancho > 2400 or not ancho:
                url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{a}/{b}/{nom}/1920px-{nom}"
                if nom.lower().endswith((".tif", ".tiff")):
                    url += ".jpg"
            elif nom.lower().endswith((".tif", ".tiff")):
                url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{a}/{b}/{nom}/{ancho}px-{nom}.jpg"
            datos = leer(url)
            if not datos or len(datos) < 30000:
                continue
            ext = ".png" if nom.lower().endswith(".png") else ".jpg"
            while list(destino.glob(f"{tema}_{n}.*")):
                n += 1
            nombre = f"{tema}_{n}{ext}"
            (destino / nombre).write_bytes(datos)
            creditos[nombre] = {"titulo": archivo, "licencia": lic, "autor": autor,
                                "fuente": WEB + "/wiki/" + archivo}
            usados.add(archivo)
            n += 1
            print(f"{nombre}  <- {archivo}  [{lic}]", flush=True)
            cred_path.write_text(json.dumps(creditos, ensure_ascii=False, indent=1))
            time.sleep(0.7)
    print(f"Listo: {len(creditos)} fotos")


main()
