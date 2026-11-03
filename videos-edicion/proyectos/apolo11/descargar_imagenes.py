"""Descarga fotos de dominio público (NASA y similares) desde Wikimedia Commons.

Uso: python3 descargar_imagenes.py <carpeta_destino>
Por cada tema busca archivos en Commons, se queda solo con los que tienen licencia de dominio público
y descarga la versión de 1920 px. Guarda creditos.json con el autor y la licencia de cada foto.
"""
import json
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

PD = ("public domain", "pd-", "pd ", "cc0", "pdm")


def get(params):
    params = {**params, "format": "json", "formatversion": "2"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    for intento in range(6):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:  # 429 u otros: esperar y reintentar
            time.sleep(5 * (intento + 1))
    raise RuntimeError(f"no se pudo consultar {params}")


def bajar(url, ruta):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for intento in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                ruta.write_bytes(r.read())
            return True
        except Exception:
            time.sleep(5 * (intento + 1))
    return False


def main():
    destino = Path(sys.argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    cred_path = destino / "creditos.json"
    creditos = json.loads(cred_path.read_text()) if cred_path.exists() else {}
    usados = {c["titulo"] for c in creditos.values()}
    for tema, (q, cuantas) in TEMAS.items():
        ya = [k for k in creditos if k.startswith(tema + "_")]
        if len(ya) >= cuantas:
            continue
        r = get({"action": "query", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
                 "gsrnamespace": "6", "gsrlimit": "25", "prop": "imageinfo",
                 "iiprop": "url|size|extmetadata|mime", "iiurlwidth": "1920"})
        paginas = sorted(r.get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
        n = len(ya)
        for p in paginas:
            if n >= cuantas:
                break
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            lic = (meta.get("LicenseShortName", {}).get("value", "") + " " +
                   meta.get("License", {}).get("value", "")).lower()
            if not any(k in lic for k in PD) or p["title"] in usados:
                continue
            if ii.get("mime") not in ("image/jpeg", "image/png", "image/tiff") or ii.get("width", 0) < 1000:
                continue
            url = ii.get("thumburl") or ii.get("url")
            nombre = f"{tema}_{n}.jpg"
            if bajar(url, destino / nombre):
                creditos[nombre] = {"titulo": p["title"], "licencia": lic.strip(),
                                    "autor": meta.get("Artist", {}).get("value", ""),
                                    "fuente": ii.get("descriptionurl", "")}
                usados.add(p["title"])
                n += 1
                print(f"{nombre}  <- {p['title']}", flush=True)
            time.sleep(1.0)
        cred_path.write_text(json.dumps(creditos, ensure_ascii=False, indent=1))
        time.sleep(1.5)
    print(f"Listo: {len(creditos)} fotos")


main()
