"""Paso 0: separa las 12 escenas de referencia.jpg y las amplía a calidad HD.

Uso: python3 0_escenas.py <carpeta_modelos> <carpeta_salida>
Crea <salida>/escenas/01.png … 12.png (unos 1200×1600 px cada una).
Si existe <modelos>/EDSR_x4.pb usa superresolución con IA (OpenCV); si no, Lanczos.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

modelos, salida = Path(sys.argv[1]), Path(sys.argv[2])
(salida / "escenas").mkdir(parents=True, exist_ok=True)
ref = Image.open(Path(__file__).with_name("referencia.jpg")).convert("RGB")

# Bordes de la cuadrícula 3×4 (las líneas blancas que separan las imágenes)
COLUMNAS = [(0, 300), (305, 594), (600, 900)]
FILAS = [(0, 390), (396, 799), (805, 1197), (1203, 1600)]
M = 2  # margen para no arrastrar restos de la línea blanca

sr = None
edsr = modelos / "EDSR_x4.pb"
if edsr.exists():
    import cv2
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(edsr))
    sr.setModel("edsr", 4)

n = 0
for y0, y1 in FILAS:
    for x0, x1 in COLUMNAS:
        n += 1
        ruta = salida / "escenas" / f"{n:02d}.png"
        if ruta.exists():
            continue
        trozo = ref.crop((x0 + M, y0 + M, x1 - M, y1 - M))
        if sr is not None:
            bgr = np.asarray(trozo)[:, :, ::-1].copy()
            grande = Image.fromarray(sr.upsample(bgr)[:, :, ::-1])
        else:
            grande = trozo.resize((trozo.width * 4, trozo.height * 4), Image.LANCZOS)
        grande = grande.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        grande.save(ruta)
        print(f"escena {n:02d} lista {grande.size}", flush=True)
