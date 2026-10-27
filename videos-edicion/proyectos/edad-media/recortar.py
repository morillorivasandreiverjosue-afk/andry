"""Paso 1: separa las imágenes de cada collage (cuadrículas con bordes blancos), las amplía con
superresolución (Real-ESRGAN x4) y las deja en 16:9 a 2400 px. Las fotos sueltas solo se ajustan.

Uso: python3 recortar.py [--solo-recorte]
Lee originales/collage1..5.webp y originales/foto1..5.webp; escribe salida/imagenes/*.png
y salida/indice.jpg (hoja con todas las imágenes numeradas, para revisar).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "pompeya"))
ANCHO, ALTO = 2400, 1350
# columnas x filas de cada collage
CUADRICULAS = {"collage1": (4, 5), "collage2": (4, 5), "collage3": (4, 4), "collage4": (5, 4), "collage5": (4, 5)}
# en collage1 los bordes de las filas son muy tenues: se dan a mano
FILAS_FIJAS = {"collage1": [265, 499, 721, 932]}
COLUMNAS_FIJAS = {"collage1": [322, 640, 959]}


def cortes(perfil, n, minimo):
    """Las n posiciones más 'blancas' del perfil, separadas al menos `minimo` píxeles."""
    elegidos = []
    for i in np.argsort(-perfil):
        if all(abs(i - j) > minimo for j in elegidos):
            elegidos.append(int(i))
        if len(elegidos) == n:
            break
    return sorted(elegidos)


def blanco(a):
    return (a.min(2) > 175) & (a.max(2) - a.min(2) < 40)


def separar(img, columnas, filas, filas_fijas=None, columnas_fijas=None):
    a = np.asarray(img).astype(np.int16)
    h, w = a.shape[:2]
    b = blanco(a)
    ys = [0] + (filas_fijas or cortes(b.mean(1), filas - 1, h / filas * 0.6)) + [h]
    piezas = []
    for y0, y1 in zip(ys[:-1], ys[1:]):
        banda = b[y0 + 6: y1 - 6]
        xs = [0] + (columnas_fijas or cortes(banda.mean(0), columnas - 1, w / columnas * 0.6)) + [w]
        for x0, x1 in zip(xs[:-1], xs[1:]):
            piezas.append(recortar_borde(img.crop((x0, y0, x1, y1))))
    return piezas


def recortar_borde(img):
    """Quita las líneas blancas que hayan quedado en los bordes de la pieza."""
    a = np.asarray(img).astype(np.int16)
    b = blanco(a)
    alto, ancho = a.shape[:2]
    maximo = 8  # un borde nunca es más grueso; así un cielo claro no se toma por borde
    top = next((i for i in range(maximo) if b[i].mean() <= 0.3), maximo)
    bottom = alto - next((i for i in range(maximo) if b[alto - 1 - i].mean() <= 0.3), maximo)
    left = next((i for i in range(maximo) if b[:, i].mean() <= 0.3), maximo)
    right = ancho - next((i for i in range(maximo) if b[:, ancho - 1 - i].mean() <= 0.3), maximo)
    m = 2  # margen extra por el borde suavizado
    return img.crop((left + m, top + m, right - m, bottom - m))


def a_16_9(img):
    w, h = img.size
    if w / h > 16 / 9:
        nw = int(h * 16 / 9)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w * 9 / 16)
        y = int((h - nh) * 0.3)  # más cerca de arriba: así no se cortan las caras
        img = img.crop((0, y, w, y + nh))
    return img.resize((ANCHO, ALTO), Image.LANCZOS)


def realzar(img, fuerza=1.0):
    img = img.filter(ImageFilter.UnsharpMask(radius=40, percent=int(12 * fuerza), threshold=0))
    img = ImageEnhance.Color(img).enhance(1 + 0.1 * fuerza)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(35 * fuerza), threshold=2))


def main():
    salida = AQUI / "salida" / "imagenes"
    salida.mkdir(parents=True, exist_ok=True)
    piezas = []
    for nombre, (c, f) in CUADRICULAS.items():
        for k, p in enumerate(separar(Image.open(AQUI / "originales" / f"{nombre}.webp").convert("RGB"), c, f,
                                       FILAS_FIJAS.get(nombre), COLUMNAS_FIJAS.get(nombre))):
            piezas.append((f"{nombre[-1]}_{k + 1:02d}", p))
    fotos = [(f"f{k}", Image.open(AQUI / "originales" / f"foto{k}.webp").convert("RGB")) for k in range(1, 6)]
    # hoja de revisión
    miniaturas = piezas + fotos
    col = 10
    hoja = Image.new("RGB", (col * 256, (len(miniaturas) + col - 1) // col * 160), "black")
    d = ImageDraw.Draw(hoja)
    for i, (n, p) in enumerate(miniaturas):
        x, y = i % col * 256, i // col * 160
        hoja.paste(p.resize((250, 140)), (x + 3, y + 3))
        d.rectangle((x + 3, y + 3, x + 70, y + 24), fill="black")
        d.text((x + 6, y + 6), n, fill="yellow")
    hoja.save(AQUI / "salida" / "indice.jpg", quality=85)
    print(len(piezas), "piezas de collage +", len(fotos), "fotos", flush=True)
    if "--solo-recorte" in sys.argv:
        return
    import recortar as rp  # superresolución del proyecto de Pompeya
    sr = rp.superresolucion(AQUI.parent.parent / "modelos")
    for n, p in piezas:
        destino = salida / f"{n}.png"
        if not destino.exists():
            realzar(a_16_9(rp.ampliar(p, sr))).save(destino)
            print("lista", n, flush=True)
    for n, p in fotos:
        realzar(a_16_9(p), 0.6).save(salida / f"{n}.png")
    print("Imágenes listas", flush=True)


if __name__ == "__main__":
    main()
