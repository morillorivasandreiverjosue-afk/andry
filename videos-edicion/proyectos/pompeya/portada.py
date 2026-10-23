"""Portada vertical (1080×1920) para TikTok, Instagram Reels y YouTube Shorts.

Uso: python3 portada.py <carpeta_salida>
Crea <salida>/portada.jpg y <salida>/portada_vista_perfil.jpg (cómo se ve recortada en la cuadrícula del perfil).
Los textos importantes van dentro del centro 3:4 (1080×1440), que es lo que muestran los perfiles.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
spec = importlib.util.spec_from_file_location("montaje", AQUI / "2_montaje.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

salida = Path(sys.argv[1])
W, H = M.W, M.H

# Fondo: la erupción del Vesubio, con más contraste y color
fondo = M.encuadre(Image.open(salida / "escenas" / "04.png").convert("RGB"), 1.0, 0.5, 0.52)
fondo = ImageEnhance.Contrast(ImageEnhance.Color(fondo).enhance(1.15)).enhance(1.12).convert("RGBA")

# Brillo cálido alrededor del cráter
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.sqrt(((xx - 560) / 330) ** 2 + ((yy - 1110) / 420) ** 2)
brillo = np.zeros((H, W, 4), np.uint8)
brillo[..., :3] = (255, 120, 30)
brillo[..., 3] = (np.clip(1 - r, 0, 1) ** 2 * 110).astype(np.uint8)
fondo.alpha_composite(Image.fromarray(brillo))

# Oscurecer arriba (título) y abajo (texto de la app) para que se lean los textos
a = np.zeros(H, np.float32)
a[:820] = np.linspace(0.78, 0, 820)
a[1350:] = np.linspace(0, 0.85, H - 1350)
sombra = np.zeros((H, W, 4), np.uint8)
sombra[..., 3] = (a[:, None] * 255).astype(np.uint8)
fondo.alpha_composite(Image.fromarray(sombra))
fondo.alpha_composite(M.vineta())

# Ceniza en el aire
capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
M.Particulas(220, 7, (1.5, 4.0), (20, 60), (60, 55, 50), 0).dibujar(capa, 0.6, 0.9)
fondo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(0.6)))

# Textos
marca = M.marca_canal()
M.pegar(fondo, marca, W / 2, 330)
anio = M.texto_con_borde([[("AÑO 79 d. C.", M.AMARILLO)]], M.fuente(M.F_SUB, 52, 800), borde=5)
M.pegar(fondo, anio, W / 2, 450)
titulo = M.texto_con_borde([[("POMPEYA", M.BLANCO)]], M.fuente(M.F_TITULO, 168, 900), borde=9)
M.pegar(fondo, titulo, W / 2, 610)
sub = M.texto_con_borde([[("LA CIUDAD QUE", M.BLANCO)], [("DESAPARECIÓ", M.AMARILLO)]],
                        M.fuente(M.F_ANTON, 120), borde=8, interlineado=1.0)
M.pegar(fondo, sub, W / 2, 1420)
d = ImageDraw.Draw(fondo)
d.line((W / 2 - 230, 770, W / 2 + 230, 770), fill=M.AMARILLO + (255,), width=5)

fondo = fondo.convert("RGB")
fondo.save(salida / "portada.jpg", quality=95)

# Vista previa del recorte 3:4 de la cuadrícula del perfil
recorte = fondo.crop((0, (H - 1440) // 2, W, (H + 1440) // 2)).resize((540, 720))
recorte.save(salida / "portada_vista_perfil.jpg", quality=90)
print("Portada lista")
