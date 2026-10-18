"""Descarga las pinturas (dominio público, Wikimedia Commons) que usa el video.

Uso: python3 descargar_imagenes.py   → imagenes/<clave>.jpg y imagenes/creditos.txt
"""
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

UA = "CuriosidadesDelMundoVideo/1.0 (https://github.com/morillorivasandreiverjosue-afk/andry) python-urllib"
DESTINO = Path(__file__).parent / "imagenes"
IMAGENES = {
    "partida": "Thomas Cole, The Departure, 1837, NGA 166439.jpg",
    "regreso": "Thomas Cole, The Return, 1837, NGA 166438.jpg",
    "godspeed": "Leighton-God Speed!.jpg",
    "accolade": "Accolade by Edmund Blair Leighton.jpg",
    "san_romano": "Battle of San Romano, by Paolo Uccello (Uffizi Gallery, Florence).jpg",
    "ciudad": "Ambrogio Lorenzetti - Effects of Good Government in the city - Google Art Project.jpg",
    "catedral": "Construction du Temple de Jérusalem.jpg",
    "schinkel": "Schinkel Mittelalterliche Stadt.jpg",
    "destruccion": "Cole Thomas The Course of Empire Destruction 1836.jpg",
    "carlomagno": "03-albrecht durer-charlemagne - Image 208240.jpg",
    "enero": "Les Très Riches Heures du duc de Berry Janvier.jpg",
    "junio": "Les Très Riches Heures du duc de Berry juin.jpg",
    "octubre": "Les Très Riches Heures du duc de Berry octobre.jpg",
    "torneo": "Codex Manesse 052r Walther von Klingen.jpg",
    "universidad": "Laurentius de Voltolina 001.jpg",
    "kells": "Meister des Book of Kells 001.jpg",
}


def pedir(url):
    for k in range(8):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(r, timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            espera = int(e.headers.get("retry-after") or 60)
            print(f"Wikimedia pide esperar {espera} s", flush=True)
            time.sleep(min(espera, 660) + 5)
    raise RuntimeError(url)


DESTINO.mkdir(exist_ok=True)
titulos = "|".join("File:" + t for t in IMAGENES.values())
q = urllib.parse.urlencode({"action": "query", "titles": titulos, "prop": "imageinfo", "format": "json",
                            "iiprop": "url|extmetadata", "iiextmetadatafilter": "LicenseShortName|Artist"})
datos = json.loads(pedir("https://commons.wikimedia.org/w/api.php?" + q))
info = {}
for p in datos["query"]["pages"].values():
    if "imageinfo" in p:
        info[p["title"].removeprefix("File:")] = p["imageinfo"][0]
norm = {n["to"].removeprefix("File:"): n["from"].removeprefix("File:") for n in datos["query"].get("normalized", [])}
creditos = []
for clave, titulo in IMAGENES.items():
    ii = info.get(titulo) or next((v for k, v in info.items() if norm.get(k) == titulo), None)
    if ii is None:
        print("NO ENCONTRADA:", clave, titulo)
        continue
    ruta = DESTINO / f"{clave}.jpg"
    if not ruta.exists():
        img = Image.open(io.BytesIO(pedir(ii["url"].split("?")[0]))).convert("RGB")
        img.thumbnail((2600, 2600), Image.LANCZOS)
        img.save(ruta, quality=92)
        time.sleep(20)
    m = ii.get("extmetadata", {})
    autor = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()
    creditos.append(f"{clave}: {titulo} — {autor} — {m.get('LicenseShortName', {}).get('value')} — {ii['descriptionurl']}")
    print("ok", clave, flush=True)
(DESTINO / "creditos.txt").write_text("\n".join(creditos) + "\n", encoding="utf-8")
