"""Paso 0: separa el collage y amplía todas las imágenes x4 con Real-ESRGAN.

Uso: python3 0_imagenes.py <carpeta_modelos> <carpeta_salida> [--procesos N]
Crea <salida>/imagenes/<nombre>.png. Las que ya existen no se repiten.
"""
import argparse
import os
from multiprocessing import Pool
from pathlib import Path

AQUI = Path(__file__).parent

# imagen original -> nombre (el collage 3.jpg se corta por sus líneas blancas)
SUELTAS = {"1.jpg": "arrastre_agua", "2.jpg": "obra_nilo", "4.jpg": "rampa_dibujo",
           "5.jpg": "grua_rampa", "6.jpg": "rampa_subida"}
COLLAGE_FILAS = [(0, 310), (316, 630), (636, 977), (982, 1295)]
COLLAGE_COLUMNAS = [(0, 604), (611, 1214)]
COLLAGE_NOMBRES = ["atardecer", "esfinge_dia", "camellos", "pasillo",
                   "jeroglificos", "arrastre_bloque", "estrellas", "esfinge_atardecer"]


def recortes():
    from PIL import Image
    for archivo, nombre in SUELTAS.items():
        yield nombre, Image.open(AQUI / "imagenes" / archivo).convert("RGB")
    collage = Image.open(AQUI / "imagenes" / "3.jpg").convert("RGB")
    nombres = iter(COLLAGE_NOMBRES)
    for y0, y1 in COLLAGE_FILAS:
        for x0, x1 in COLLAGE_COLUMNAS:
            # 3 px de margen para no arrastrar el borde blanco
            yield next(nombres), collage.crop((x0 + 3, y0 + 3, x1 - 3, y1 - 3))


def trabajar(args):
    nombre, img, modelo, destino = args
    import numpy as np
    from PIL import Image, ImageFilter
    import esrgan
    grande = esrgan.ampliar(np.asarray(img), modelo)
    # un toque de nitidez y contraste final
    out = Image.fromarray(grande).filter(ImageFilter.UnsharpMask(radius=2, percent=40, threshold=2))
    out.save(destino)
    print("lista:", nombre, out.size, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modelos", type=Path)
    ap.add_argument("salida", type=Path)
    ap.add_argument("--procesos", type=int, default=os.cpu_count())
    a = ap.parse_args()
    (a.salida / "imagenes").mkdir(parents=True, exist_ok=True)
    modelo = str(a.modelos / "RealESRGAN_x4plus.pth")
    tareas = [(n, img, modelo, a.salida / "imagenes" / f"{n}.png") for n, img in recortes()
              if not (a.salida / "imagenes" / f"{n}.png").exists()]
    tareas.sort(key=lambda t: -t[1].size[0] * t[1].size[1])  # las grandes primero
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    with Pool(a.procesos) as p:
        list(p.imap_unordered(trabajar, tareas))


if __name__ == "__main__":
    main()
