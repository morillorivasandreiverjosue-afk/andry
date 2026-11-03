"""Dibuja los mapas del Triángulo de las Bermudas (estilo radar), con datos de Natural Earth (dominio público).

Uso: python3 dibujar_mapas.py imagenes/
Crea mapa_0.png (Atlántico), mapa_1.png (acercamiento al triángulo) y mapa_2.png (triángulo con rutas).
"""
import sys
import warnings
from pathlib import Path

import geopandas as gpd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

warnings.filterwarnings("ignore")
MUNDO = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
W, H = 2400, 1350
PUNTOS = {"MIAMI": (-80.19, 25.77), "BERMUDAS": (-64.78, 32.30), "PUERTO RICO": (-66.11, 18.47)}
F = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
CIAN = (90, 215, 255)


def mapa(ruta, lon0, lon1, lat0, lat1, rutas=False):
    def xy(lon, lat):
        return (lon - lon0) / (lon1 - lon0) * W, (lat1 - lat) / (lat1 - lat0) * H

    im = Image.new("RGB", (W, H), (4, 14, 26))
    d = ImageDraw.Draw(im, "RGBA")
    # cuadrícula de coordenadas
    for lon in range(int(lon0) // 5 * 5, int(lon1) + 5, 5):
        x, _ = xy(lon, 0)
        d.line([(x, 0), (x, H)], fill=(40, 90, 120, 90), width=1)
    for lat in range(int(lat0) // 5 * 5, int(lat1) + 5, 5):
        _, y = xy(0, lat)
        d.line([(0, y), (W, y)], fill=(40, 90, 120, 90), width=1)
    # tierra
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    for geom in MUNDO.geometry:
        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        for p in polys:
            pts = [xy(x, y) for x, y in p.exterior.coords]
            dc.polygon(pts, fill=(22, 48, 64, 255), outline=(90, 215, 255, 200))
    brillo = capa.filter(ImageFilter.GaussianBlur(6))
    im.paste(brillo, (0, 0), brillo)
    im.paste(capa, (0, 0), capa)
    d = ImageDraw.Draw(im, "RGBA")
    # triángulo
    tri = [xy(*PUNTOS[k]) for k in ("MIAMI", "BERMUDAS", "PUERTO RICO")]
    relleno = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(relleno).polygon(tri, fill=(255, 60, 50, 70))
    im.paste(relleno, (0, 0), relleno)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(tri + [tri[0]], fill=(255, 80, 60, 255), width=14)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    im.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(im, "RGBA")
    d.line(tri + [tri[0]], fill=(255, 110, 90, 255), width=5)
    if rutas:  # rutas de barcos y aviones que cruzan la zona
        for a, b in (((-80.1, 26.0), (-60, 30)), ((-79.5, 24.0), (-62, 21.0)), ((-76, 36), (-68, 17)),
                     ((-81, 28.5), (-64, 25.5))):
            pa, pb = xy(*a), xy(*b)
            n = 40
            for k in range(0, n, 2):
                p0 = (pa[0] + (pb[0] - pa[0]) * k / n, pa[1] + (pb[1] - pa[1]) * k / n)
                p1 = (pa[0] + (pb[0] - pa[0]) * (k + 1) / n, pa[1] + (pb[1] - pa[1]) * (k + 1) / n)
                d.line([p0, p1], fill=CIAN + (170,), width=3)
    fuente = ImageFont.truetype(F, 46 if lon1 - lon0 < 40 else 36)
    for nombre, (lon, lat) in PUNTOS.items():
        x, y = xy(lon, lat)
        d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=(255, 255, 255, 255), outline=(255, 80, 60, 255), width=4)
        dx = -fuente.getlength(nombre) - 30 if nombre == "MIAMI" else 30
        d.text((x + dx, y - 30), nombre, font=fuente, fill=(255, 255, 255, 255), stroke_width=3,
               stroke_fill=(0, 0, 0, 255))
    f2 = ImageFont.truetype(F, 30)
    x, y = xy(-55 if lon1 > -50 else -60, 33 if lat1 > 40 else 35)
    d.text((x, y), "OCÉANO ATLÁNTICO", font=f2, fill=CIAN + (200,))
    im.save(ruta)


destino = Path(sys.argv[1])
destino.mkdir(parents=True, exist_ok=True)
mapa(destino / "mapa_0.png", -100, -20, 5, 50)
mapa(destino / "mapa_1.png", -86, -56, 14, 37)
mapa(destino / "mapa_2.png", -86, -56, 14, 37, rutas=True)
print("mapas listos")
