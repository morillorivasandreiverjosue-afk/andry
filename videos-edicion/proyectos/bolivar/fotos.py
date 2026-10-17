#!/usr/bin/env python3
"""Paso 2b: descarga de Wikimedia Commons las obras de fotos.json y las prepara para el render.

Cada imagen queda en build/fotos/prep/ a 2304x1296 (el lienzo de las ilustraciones). Las horizontales
grandes se recortan para llenar el cuadro; las verticales (retratos) y las pequeñas van completas sobre un fondo desenfocado
de sí mismas. Los créditos (autor y licencia) se guardan en creditos.txt.

Uso (desde proyectos/bolivar/):  python3 fotos.py
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

import wikimedia as WM
from ilustraciones import W0, H0

AQUI = Path(__file__).resolve().parent
DIR = AQUI / "build" / "fotos"
ORIG, PREP = DIR / "orig", DIR / "prep"
META = DIR / "meta.json"


def mapa():
    d = json.loads((AQUI / "fotos.json").read_text(encoding="utf-8"))
    return {int(k): v for k, v in d.items() if not k.startswith("_")}


def clave(titulo):
    return hashlib.md5(titulo.encode()).hexdigest()[:12]


def ruta_prep(titulo):
    return PREP / f"{clave(titulo)}.jpg"


def tono(im):
    """Acerca el color de fotos y pinturas a la paleta cálida y algo apagada del documental."""
    a = np.asarray(im, np.float32) / 255
    gris = a.mean(axis=2, keepdims=True)
    a = gris + (a - gris) * 0.82
    a = a * np.array([1.03, 1.0, 0.93]) + np.array([0.012, 0.004, -0.01])
    a = np.clip(a, 0, 1) ** 1.06
    return Image.fromarray((a * 255).astype(np.uint8))


def preparar(im):
    im = ImageOps.exif_transpose(im).convert("RGB")
    r = im.width / im.height
    if r >= 1.45 and im.width >= 1400:
        return tono(ImageOps.fit(im, (W0, H0), Image.LANCZOS))
    fondo = ImageOps.fit(im, (W0 // 4, H0 // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
    fondo = Image.fromarray((np.asarray(fondo.resize((W0, H0), Image.BICUBIC), np.float32) * 0.38).astype(np.uint8))
    alto = int(H0 * 0.92)
    ancho = min(int(alto * r), int(W0 * 0.8))
    # una imagen pequeña no se agranda más de 3,5 veces: mejor más chica que borrosa
    ancho = min(ancho, int(im.width * 3.5))
    alto = int(ancho / r)
    fig = im.resize((ancho, alto), Image.LANCZOS)
    x, y = (W0 - ancho) // 2, (H0 - alto) // 2
    sombra = Image.new("L", (W0, H0), 0)
    sombra.paste(200, (x + 14, y + 18, x + ancho + 14, y + alto + 18))
    fondo.paste((0, 0, 0), (0, 0), sombra.filter(ImageFilter.GaussianBlur(22)))
    fondo.paste(fig, (x, y))
    return tono(fondo)


def limpiar(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def main():
    ORIG.mkdir(parents=True, exist_ok=True)
    PREP.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text()) if META.exists() else {}
    titulos = list(dict.fromkeys(t for v in mapa().values() for t in v))
    faltan = [t for t in titulos if t not in meta]
    for k in range(0, len(faltan), 20):
        grupo = ["File:" + t for t in faltan[k:k + 20]]
        for tit, m in WM.info(grupo).items():
            meta[tit[5:]] = m
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    for n, t in enumerate(titulos, 1):
        if t not in meta:
            print(f"[{n}/{len(titulos)}] NO ENCONTRADO: {t}")
            continue
        if ruta_prep(t).exists():
            continue
        orig = ORIG / clave(t)
        if not orig.exists():
            try:
                orig.write_bytes(WM.descargar(meta[t]))
            except RuntimeError as e:
                print(f"[{n}/{len(titulos)}] FALLÓ: {t} ({e})", flush=True)
                continue
        preparar(Image.open(orig)).save(ruta_prep(t), quality=93)
        print(f"[{n}/{len(titulos)}] {t}", flush=True)
    lineas = ["Imágenes: Wikimedia Commons (https://commons.wikimedia.org)", ""]
    for t in sorted(titulos):
        if t in meta:
            m = meta[t]
            lineas.append(f"- {t} — {limpiar(m['autor']) or 'Autor desconocido'} — {m['licencia']} — {m['pagina']}")
    (AQUI / "creditos.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("Listo.", sum(ruta_prep(t).exists() for t in titulos), "de", len(titulos), "imágenes preparadas")


if __name__ == "__main__":
    main()
