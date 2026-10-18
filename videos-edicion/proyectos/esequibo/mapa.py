"""Mapas con aspecto satelital (relieve, selva, sabanas, mar) y capas políticas animables.

Datos: Natural Earth 1:10m (dominio público), recortados en datos/. La zona en reclamación es
el polígono «West of Essequibo River — Admin. by Guyana; Claimed by Venezuela» de Natural Earth.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

from base import fuente, ruido, texto
from guion import W, H

DATOS = Path(__file__).parent / "datos"
CACHE = Path(__file__).parent / "salida" / "cache"
K = math.cos(math.radians(6))

# (lon0, lon1, lat0, lat1, px por grado)
BASES = {"fino": (-75.0, -52.0, -1.0, 13.5, 200), "ancho": (-100.0, -20.0, -48.0, 22.0, 34)}


def leer(nombre):
    return json.loads((DATOS / nombre).read_text())["features"]


def anillos(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def lineas(geom):
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        return geom["coordinates"]
    return []


class Base:
    def __init__(self, nombre):
        self.nombre = nombre
        self.lon0, self.lon1, self.lat0, self.lat1, self.P = BASES[nombre]
        self.w = int((self.lon1 - self.lon0) * self.P * K)
        self.h = int((self.lat1 - self.lat0) * self.P)

    def px(self, lon, lat):
        return ((lon - self.lon0) * self.P * K, (self.lat1 - lat) * self.P)

    def lienzo(self):
        return Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def poligono(self, d, geom, **kw):
        for pol in anillos(geom):
            d.polygon([self.px(*c[:2]) for c in pol[0]], **kw)
            for hueco in pol[1:]:
                d.polygon([self.px(*c[:2]) for c in hueco], fill=(0, 0, 0, 0))

    def contorno(self, d, geom, fill, width):
        for pol in anillos(geom):
            for anillo in pol:
                d.line([self.px(*c[:2]) for c in anillo], fill=fill, width=width, joint="curve")


def pais(nombre):
    for f in leer("paises.geojson"):
        if f["properties"]["nombre"] == nombre:
            return f["geometry"]
    raise KeyError(nombre)


def campo(lon, lat, centros):
    """Suma de gaussianas (lon, lat, sigma, peso) evaluada en la malla."""
    out = np.zeros_like(lon)
    for cx, cy, s, p in centros:
        out += p * np.exp(-(((lon - cx) * K) ** 2 + (lat - cy) ** 2) / (2 * s * s))
    return out


def cordillera(a, b, s, p, n=12):
    return [(a[0] + (b[0] - a[0]) * i / (n - 1), a[1] + (b[1] - a[1]) * i / (n - 1), s, p) for i in range(n)]


RELIEVE = (cordillera((-72.6, 7.2), (-69.6, 9.9), 0.45, 1.0) + cordillera((-68.6, 10.25), (-63.5, 10.45), 0.3, 0.55)
           + cordillera((-77, 0), (-73.2, 7.5), 0.8, 1.1) + cordillera((-73.5, 9.5), (-72.6, 11.1), 0.35, 0.8)
           + [(-61.0, 5.1, 0.9, 0.85), (-62.5, 5.8, 0.9, 0.7), (-64.5, 5.0, 1.1, 0.75), (-65.5, 3.0, 1.0, 0.6),
              (-60.0, 5.4, 0.6, 0.6), (-59.6, 4.6, 0.4, 0.4), (-59.0, 1.6, 0.6, 0.5), (-56.0, 3.5, 1.0, 0.35),
              (-63.0, 3.0, 1.2, 0.5), (-74.0, 11.0, 0.3, 1.2)])
SECO = [(-68.0, 8.0, 2.0, 1.0), (-71.0, 5.5, 1.8, 0.9), (-59.6, 3.1, 0.55, 0.9), (-61.4, 5.0, 0.5, 0.7),
        (-64.5, 8.8, 1.2, 0.5), (-70.5, 11.6, 0.7, 0.9), (-60.8, 3.4, 0.6, 0.6), (-64, 10.3, 0.7, 0.4)]


def terreno(b: Base):
    ruta = CACHE / f"terreno_{b.nombre}.png"
    if ruta.exists():
        return Image.open(ruta).convert("RGB")
    CACHE.mkdir(parents=True, exist_ok=True)
    tierra = b.lienzo()
    d = ImageDraw.Draw(tierra)
    for f in leer("paises.geojson"):
        b.poligono(d, f["geometry"], fill=(255, 255, 255, 255))
    for f in leer("lagos.geojson"):
        b.poligono(d, f["geometry"], fill=(0, 0, 0, 0))
    mask = np.asarray(tierra.split()[3]).astype(np.float32) / 255
    h, w = mask.shape
    # campos suaves a 1/4 de resolución
    q = 4
    yy, xx = np.mgrid[0:h:q, 0:w:q].astype(np.float32)
    lon = b.lon0 + xx / (b.P * K)
    lat = b.lat1 - yy / b.P
    elev = campo(lon, lat, RELIEVE)
    seco = np.clip(campo(lon, lat, SECO), 0, 1)
    sub = lambda a: ndimage.zoom(a, (h / a.shape[0], w / a.shape[1]), order=1)[:h, :w]
    elev, seco = sub(elev), sub(seco)
    det = ruido(w, h, 11, 8, 6, 0.6)
    det2 = ruido(w, h, 12, 6, 24, 0.5)
    e = elev * (0.55 + 0.9 * det) + det2 * 0.12
    gy, gx = np.gradient(ndimage.gaussian_filter(e, 1.2) * (b.P / 6))
    sombra = np.clip(1 + (-gx * 0.8 - gy * 0.9) * 1.6, 0.35, 1.6)
    selva = np.array([28, 58, 28], np.float32) + det2[..., None] * np.array([22, 30, 14], np.float32)
    sabana = np.array([138, 128, 82], np.float32) + det[..., None] * np.array([30, 26, 16], np.float32)
    roca = np.array([112, 104, 86], np.float32)
    s = np.clip(seco * (0.6 + 0.8 * det2), 0, 1)[..., None]
    col = selva * (1 - s) + sabana * s
    alto = np.clip((elev - 0.55) * 2.2, 0, 0.8)[..., None] * np.clip(det[..., None] * 1.5, 0, 1)
    col = col * (1 - alto) + roca * alto
    col *= sombra[..., None]
    # mar: profundo lejos de la costa, turquesa/turbio cerca (pluma del Orinoco)
    dist = ndimage.distance_transform_edt(mask[::q, ::q] < 0.5) * q / b.P
    dist = sub(dist.astype(np.float32))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lonf = b.lon0 + xx / (b.P * K)
    latf = b.lat1 - yy / b.P
    hondo = np.array([5, 20, 38], np.float32)
    costa = np.array([18, 62, 78], np.float32)
    turbio = np.array([70, 78, 58], np.float32)
    c = np.exp(-dist / 0.9)[..., None]
    pluma = (np.exp(-(((lonf + 60.3) * K) ** 2 + (latf - 8.9) ** 2) / 1.2) * np.exp(-dist / 0.5))[..., None]
    mar = hondo * (1 - c) + costa * c
    mar = mar * (1 - pluma * 0.8) + turbio * pluma * 0.8
    mar *= (0.92 + 0.12 * ruido(w, h, 13, 5, 3, 0.5))[..., None]
    m = ndimage.gaussian_filter(mask, 0.8)[..., None]
    img = col * m + mar * (1 - m)
    # ríos y lagos
    rios = b.lienzo()
    d = ImageDraw.Draw(rios)
    for f in leer("rios.geojson"):
        rango = f["properties"].get("rango") or 8
        ancho = max(2, int(b.P / 60 * (10 - rango) / 3))
        for ln in lineas(f["geometry"]):
            d.line([b.px(*c[:2]) for c in ln], fill=(40, 80, 92, 210), width=ancho, joint="curve")
    for f in leer("lagos.geojson"):
        b.poligono(d, f["geometry"], fill=(20, 55, 75, 255))
    ra = np.asarray(rios).astype(np.float32)
    a = ra[..., 3:4] / 255
    img = img * (1 - a) + ra[..., :3] * a
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    out.save(ruta)
    return out


def capas_politicas(b: Base):
    """Capas RGBA: fronteras, Venezuela, Guyana, zona en reclamación, línea de 1899, río Esequibo, Stabroek."""
    c = {}
    lw = max(2, int(b.P / 70))
    fr = b.lienzo()
    d = ImageDraw.Draw(fr)
    for f in leer("paises.geojson"):
        b.contorno(d, f["geometry"], (235, 235, 225, 150), lw)
    c["fronteras"] = fr

    ve = b.lienzo()
    d = ImageDraw.Draw(ve)
    b.poligono(d, pais("Venezuela"), fill=(255, 196, 0, 70))
    b.contorno(d, pais("Venezuela"), (255, 205, 40, 255), lw * 2)
    c["venezuela"] = ve

    gy = b.lienzo()
    d = ImageDraw.Draw(gy)
    b.poligono(d, pais("Guyana"), fill=(40, 190, 120, 60))
    b.contorno(d, pais("Guyana"), (90, 220, 150, 255), lw * 2)
    c["guyana"] = gy

    zona = leer("zona_reclamacion.geojson")[0]["geometry"]
    m = Image.new("L", (b.w, b.h), 0)
    b.poligono(ImageDraw.Draw(m), zona, fill=255)
    rayado = Image.new("L", (b.w, b.h), 0)
    dr = ImageDraw.Draw(rayado)
    paso = max(10, int(b.P / 9))
    for x in range(-b.h, b.w, paso):
        dr.line([(x, b.h), (x + b.h, 0)], fill=255, width=max(2, paso // 4))
    alfa = np.asarray(m).astype(np.float32) * (0.32 + 0.38 * np.asarray(rayado) / 255)
    zr = np.zeros((b.h, b.w, 4), np.uint8)
    zr[..., 0], zr[..., 1], zr[..., 2] = 225, 40, 45
    zr[..., 3] = alfa.astype(np.uint8)
    zimg = Image.fromarray(zr, "RGBA")
    # contorno discontinuo rojo (reclamación: NO es una frontera reconocida)
    borde = b.lienzo()
    d = ImageDraw.Draw(borde)
    for pol in anillos(zona):
        pts = [b.px(*q[:2]) for q in pol[0]]
        acum, dibuja, seg_ = 0.0, True, [pts[0]]
        L = max(8, b.P / 7)
        for p0, p1 in zip(pts, pts[1:]):
            dl = math.dist(p0, p1)
            acum += dl
            seg_.append(p1)
            if acum > L:
                if dibuja:
                    d.line(seg_, fill=(255, 70, 70, 255), width=lw * 2, joint="curve")
                dibuja, acum, seg_ = not dibuja, 0.0, [p1]
    zimg.alpha_composite(borde)
    c["zona"] = zimg
    gl = Image.new("RGBA", (b.w, b.h), (255, 40, 40, 0))
    gl.putalpha(m.filter(ImageFilter.GaussianBlur(b.P / 8)).point(lambda v: int(v * 0.55)))
    c["zona_brillo"] = gl

    # línea del laudo de 1899 = frontera Venezuela–Guyana administrada hoy
    from shapely.geometry import shape
    lv = shape(pais("Venezuela")).boundary.intersection(shape(pais("Guyana")).buffer(0.03))
    l99 = b.lienzo()
    d = ImageDraw.Draw(l99)
    for g in getattr(lv, "geoms", [lv]):
        if g.geom_type == "LineString":
            d.line([b.px(*q) for q in g.coords], fill=(255, 250, 235, 255), width=lw * 2 + 1, joint="curve")
    glow = l99.filter(ImageFilter.GaussianBlur(b.P / 25))
    glow.alpha_composite(l99)
    c["linea1899"] = glow

    rio = b.lienzo()
    d = ImageDraw.Draw(rio)
    for f in leer("rios.geojson"):
        if f["properties"]["nombre"] == "Essequibo":
            for ln in lineas(f["geometry"]):
                d.line([b.px(*q[:2]) for q in ln], fill=(90, 220, 255, 255), width=lw * 2 + 2, joint="curve")
    g = rio.filter(ImageFilter.GaussianBlur(b.P / 20))
    g.alpha_composite(rio)
    c["esequibo"] = g

    st = b.lienzo()
    d = ImageDraw.Draw(st)
    x0, y0 = b.px(-58.2, 8.7)
    x1, y1 = b.px(-56.4, 6.9)
    d.rounded_rectangle((x0, y0, x1, y1), int(b.P / 4), fill=(20, 20, 20, 120), outline=(255, 170, 40, 255),
                        width=lw * 2)
    c["stabroek"] = st
    return c


class Mapa:
    def __init__(self):
        self.bases = {n: Base(n) for n in BASES}
        self.terreno = {n: terreno(b) for n, b in self.bases.items()}
        self.capas = {n: capas_politicas(b) for n, b in self.bases.items()}
        self.nubes = ruido(900, 1600, 31, 6, 3, 0.6)

    def render(self, lon, lat, alto, t=0.0, capas=None, etiquetas=(), nubes=0.35, rot=0.0):
        """Encuadre centrado en (lon, lat) mostrando `alto` grados de latitud en vertical."""
        capas = capas or {}
        ppd = H / alto                          # píxeles de pantalla por grado
        lon_a = W / ppd / K                     # grados de longitud visibles
        nb = "fino"
        b = self.bases[nb]
        if not (lon - lon_a / 2 > b.lon0 and lon + lon_a / 2 < b.lon1 and lat - alto / 2 > b.lat0
                and lat + alto / 2 < b.lat1) or ppd < b.P * 0.45:
            nb = "ancho"
            b = self.bases[nb]
        cx, cy = b.px(lon, lat)
        sw, sh = W / ppd * b.P, H / ppd * b.P
        caja = (cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2)
        dentro = caja[0] >= 0 and caja[1] >= 0 and caja[2] <= b.w and caja[3] <= b.h

        def encuadrar(im):
            if dentro:
                return im.resize((W, H), Image.BILINEAR, box=caja)
            return im.crop(tuple(int(round(v)) for v in caja)).resize((W, H), Image.BILINEAR)

        img = encuadrar(self.terreno[nb]).convert("RGBA")
        for nombre, a in capas.items():
            if a <= 0.01:
                continue
            capa = encuadrar(self.capas[nb][nombre])
            if a < 0.99:
                capa.putalpha(capa.split()[3].point(lambda v: int(v * a)))
            img.alpha_composite(capa)
        if nubes:
            n = self.nubes
            off = int(t * 18) % 600
            sub = n[: H // 2, off: off + W // 2] if off + W // 2 <= n.shape[1] else n[: H // 2, : W // 2]
            a = np.clip((sub - 0.55) * 3.0, 0, 1) * nubes * 255
            a = ndimage.zoom(a, 2, order=1)
            nube = Image.new("RGBA", (W, H), (235, 240, 245, 0))
            nube.putalpha(Image.fromarray(a.astype(np.uint8)))
            img.alpha_composite(nube)

        def pantalla(lo, la):
            x, y = b.px(lo, la)
            return ((x - caja[0]) * W / sw, (y - caja[1]) * H / sh)

        for e in etiquetas:
            x, y = pantalla(e["lon"], e["lat"])
            if e.get("punto"):
                d = ImageDraw.Draw(img)
                r = e.get("r", 9)
                d.ellipse((x - r - 4, y - r - 4, x + r + 4, y + r + 4), fill=(0, 0, 0, int(140 * e.get("a", 1))))
                d.ellipse((x - r, y - r, x + r, y + r), fill=e.get("color", (255, 255, 255)) + (int(255 * e.get("a", 1)),))
            texto(img, (x + e.get("dx", 0), y + e.get("dy", 0)), e["texto"], e.get("fuente", ("fuerte", 44)),
                  fill=e.get("color", (255, 255, 255)), ancla=e.get("ancla", "mm"), sombra=8, alfa=e.get("a", 1),
                  espaciado=e.get("espaciado", 0), borde=e.get("borde", 0))
        if rot:
            img = img.rotate(rot, Image.BILINEAR, expand=False)
        return img.convert("RGB"), pantalla


@lru_cache(None)
def mapa():
    return Mapa()
