"""Paso 1: recorta las 16 imágenes del collage y borra la marca de tiempo de la esquina.

Uso: python3 recortar.py <collage> <carpeta_salida>
Crea <salida>/imagenes/t01.png … t16.png a 2400 px de ancho (16:9).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

COLUMNAS = [(0, 396), (400, 797), (800, 1200), (1204, 1600)]
FILAS = [(0, 258), (261, 489), (494, 685), (689, 900)]
ANCHO, ALTO = 2400, 1350


def borrar_etiqueta(img):
    """Detecta el texto blanco de la esquina superior izquierda y lo tapa con la textura
    que hay justo debajo (reflejada), fundiendo los bordes para que no se note."""
    a = np.asarray(img).astype(np.float32)
    region = a[:34, :116]
    texto = (region.mean(2) > 150) & (region.max(2) - region.min(2) < 60)
    ys, xs = np.where(texto)
    if not len(ys):
        return img
    h, w = ys.max() + 6, xs.max() + 8
    parche = a[h: 2 * h, :w][::-1].copy()
    # mezcla suave: 1 dentro del rectángulo, baja a 0 en los últimos 10 px de la derecha y de abajo
    borde = 10
    mx = np.clip((w - np.arange(w)) / borde, 0, 1)
    my = np.clip((h - np.arange(h)) / borde, 0, 1)
    alfa = np.minimum(my[:, None], mx[None, :])[..., None]
    a[:h, :w] = parche * alfa + a[:h, :w] * (1 - alfa)
    # reaplica el parche sin fundido sobre el texto mismo, por si el fundido dejó restos
    nucleo = np.zeros(a.shape[:2], bool)
    nucleo[:34, :116] = ndimage.binary_dilation(texto, iterations=3)
    nucleo = nucleo[:h, :w]
    a[:h, :w][nucleo] = parche[nucleo]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def a_16_9(img):
    w, h = img.size
    if w / h > 16 / 9:
        nw = int(h * 16 / 9)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w * 9 / 16)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.resize((ANCHO, ALTO), Image.LANCZOS)
    return img.filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=2))


collage, salida = Image.open(sys.argv[1]).convert("RGB"), Path(sys.argv[2]) / "imagenes"
salida.mkdir(parents=True, exist_ok=True)
k = 0
for y0, y1 in FILAS:
    for x0, x1 in COLUMNAS:
        k += 1
        a_16_9(borrar_etiqueta(collage.crop((x0, y0, x1, y1)))).save(salida / f"t{k:02d}.png")
        print(f"imagen {k} lista", flush=True)
