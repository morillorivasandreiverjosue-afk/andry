"""Paso 1: recorta las 16 imágenes del collage, borra la marca de tiempo de la esquina,
las amplía con superresolución (EDSR x4) y les da más contraste, color y nitidez.

Uso: python3 recortar.py <collage> <carpeta_salida> [carpeta_modelos]
Crea <salida>/imagenes/t01.png … t16.png a 2400 px de ancho (16:9).
Si no encuentra <modelos>/EDSR_x4.pb (o no está instalado opencv-contrib) amplía sin IA.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from scipy import ndimage

AQUI = Path(__file__).parent

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


def superresolucion(modelos):
    try:
        import cv2
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(modelos / "EDSR_x4.pb"))
        sr.setModel("edsr", 4)
        return sr
    except Exception as e:  # sin el modelo se usa la ampliación normal
        print("Sin superresolución:", e, flush=True)
        return None


def ampliar(img, sr):
    if sr is None:
        return img
    rgb = np.asarray(img)
    return Image.fromarray(sr.upsample(rgb[:, :, ::-1].copy())[:, :, ::-1])


def realzar(img):
    """Quita el aspecto apagado: niveles automáticos, más contraste local, color y nitidez."""
    a = np.asarray(img).astype(np.float32)
    lum = a.mean(2)
    bajo, alto = np.percentile(lum, 0.5), np.percentile(lum, 99.6)
    a = np.clip((a - bajo) / max(1, alto - bajo) * 255, 0, 255)
    img = Image.fromarray(a.astype(np.uint8))
    img = img.filter(ImageFilter.UnsharpMask(radius=40, percent=22, threshold=0))  # claridad
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.22)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))


def a_16_9(img):
    w, h = img.size
    if w / h > 16 / 9:
        nw = int(h * 16 / 9)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w * 9 / 16)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize((ANCHO, ALTO), Image.LANCZOS)


collage, salida = Image.open(sys.argv[1]).convert("RGB"), Path(sys.argv[2]) / "imagenes"
salida.mkdir(parents=True, exist_ok=True)
sr = superresolucion(Path(sys.argv[3]) if len(sys.argv) > 3 else AQUI.parent.parent / "modelos")
k = 0
for y0, y1 in FILAS:
    for x0, x1 in COLUMNAS:
        k += 1
        img = ampliar(borrar_etiqueta(collage.crop((x0, y0, x1, y1))), sr)
        realzar(a_16_9(img)).save(salida / f"t{k:02d}.png")
        print(f"imagen {k} lista", flush=True)
