"""Descarga fotos de dominio público (NASA y similares) desde Wikimedia Commons (páginas web públicas).

Uso: python3 descargar_imagenes.py <carpeta_destino>
Por cada tema busca archivos en Commons, se queda solo con los que tienen licencia de dominio público
y descarga la versión de 1920 px. Guarda creditos.json con el autor y la licencia de cada foto.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "ApolloDocumentaryBuilder/1.0 (https://github.com/morillorivasandreiverjosue-afk/andry)"
API = "https://commons.wikimedia.org/w/api.php"

# tema -> búsqueda en Commons (cuántas fotos)
TEMAS = {
    "luna_llena": ("Full Moon photograph NASA lunar near side", 3),
    "luna_superficie": ("Apollo 11 lunar surface Hasselblad", 8),
    "luna_orbita": ("Apollo 11 lunar orbit crater view from command module", 6),
    "tierra_espacio": ("Apollo 11 Earth view from spacecraft", 4),
    "earthrise": ("Earthrise Apollo 8", 2),
    "sputnik": ("Sputnik 1 replica", 2),
    "gagarin": ("Yuri Gagarin 1961", 2),
    "kennedy": ("Kennedy speech Congress May 25 1961 moon", 3),
    "kennedy_rice": ("Kennedy Rice University speech 1962", 2),
    "apolo1": ("Apollo 1 crew Grissom White Chaffee", 2),
    "tripulacion": ("Apollo 11 crew portrait Armstrong Collins Aldrin", 3),
    "armstrong": ("Neil Armstrong portrait NASA 1969", 2),
    "aldrin": ("Buzz Aldrin portrait NASA", 2),
    "collins": ("Michael Collins astronaut portrait", 2),
    "saturno_v": ("Apollo 11 Saturn V launch pad", 5),
    "vab": ("Saturn V Vehicle Assembly Building rollout Apollo 11", 3),
    "lanzamiento": ("Apollo 11 launch liftoff July 16 1969", 6),
    "multitud": ("crowd watching Apollo 11 launch", 2),
    "control_mision": ("Apollo 11 Mission Control Houston", 5),
    "columbia": ("Apollo 11 Command Module Columbia", 3),
    "eagle": ("Apollo 11 Lunar Module Eagle", 6),
    "astronautas_nave": ("Apollo 11 crew training", 3),
    "agc": ("Apollo Guidance Computer DSKY", 2),
    "huella": ("Apollo 11 bootprint", 2),
    "aldrin_superficie": ("Aldrin Apollo 11 lunar surface", 4),
    "bandera": ("Apollo 11 flag lunar surface", 2),
    "placa": ("Apollo 11 plaque", 2),
    "experimentos": ("Apollo 11 seismic experiment retroreflector", 3),
    "armstrong_eagle": ("Armstrong Apollo 11 lunar module interior", 2),
    "eagle_ascenso": ("Apollo 11 ascent stage lunar module rendezvous", 3),
    "rocas": ("Apollo 11 lunar sample rock", 3),
    "reentrada": ("Apollo command module reentry parachutes", 3),
    "amerizaje": ("Apollo 11 splashdown recovery", 4),
    "hornet": ("USS Hornet Apollo 11 recovery", 2),
    "cuarentena": ("Apollo 11 Mobile Quarantine Facility Nixon", 2),
    "desfile": ("Apollo 11 ticker tape parade New York", 2),
    "apolo12": ("Apollo 12 Surveyor 3", 2),
    "apolo17": ("Apollo 17 Blue Marble", 2),
    "apolo17_superficie": ("Apollo 17 Harrison Schmitt boulder", 2),
    "artemis": ("Artemis I SLS launch", 2),
    "estrellas": ("Milky Way night sky", 2),
}

PD = ("public domain", "pd-", "cc0")
WEB = "https://commons.wikimedia.org"


def leer(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for intento in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            time.sleep(6 * (intento + 1))
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
    cred_path = destino / "creditos.json"
    creditos = json.loads(cred_path.read_text()) if cred_path.exists() else {}
    usados = {c["titulo"] for c in creditos.values()}
    for tema, (q, cuantas) in TEMAS.items():
        n = len([k for k in creditos if k.startswith(tema + "_")])
        if n >= cuantas:
            continue
        for archivo in buscar(q):
            if n >= cuantas:
                break
            if archivo in usados:
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
            nombre = f"{tema}_{n}" + (".png" if nom.lower().endswith(".png") else ".jpg")
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
