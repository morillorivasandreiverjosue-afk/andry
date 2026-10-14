#!/usr/bin/env python3
"""Mapas animados del documental (datos de Natural Earth, dominio público).

Cada mapa tiene una imagen base (build/img/<mapa>.png) y unas capas animadas
(rutas que se dibujan, ciudades que aparecen) que se pintan cuadro a cuadro.
"""
import math
from pathlib import Path

import numpy as np
import shapefile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ilustraciones import AQUI, H0, SALIDA, SS, W0, fuente, textura

LUGARES = {
    "Caracas": (-66.9, 10.5), "Madrid": (-3.7, 40.4), "Cádiz": (-6.3, 36.5), "Roma": (12.5, 41.9),
    "París": (2.35, 48.85), "Londres": (-0.13, 51.5), "Filadelfia": (-75.2, 39.95),
    "Puerto Cabello": (-68.01, 10.47), "Cartagena": (-75.5, 10.4), "Mompox": (-74.43, 9.24),
    "Ocaña": (-73.35, 8.24), "Cúcuta": (-72.5, 7.89), "Mérida": (-71.15, 8.6), "Trujillo": (-70.43, 9.37),
    "Valencia": (-68.0, 10.16), "Kingston": (-76.79, 17.97), "Puerto Príncipe": (-72.34, 18.54),
    "Los Cayos": (-73.75, 18.2), "Margarita": (-63.9, 11.0), "Angostura": (-63.55, 8.12),
    "Mantecal": (-69.15, 7.55), "Tame": (-71.73, 6.46), "Pisba": (-72.6, 5.85), "Boyacá": (-73.36, 5.45),
    "Bogotá": (-74.08, 4.6), "Carabobo": (-68.1, 9.98), "Quito": (-78.5, -0.2), "Pichincha": (-78.6, -0.17),
    "Guayaquil": (-79.9, -2.2), "Lima": (-77.04, -12.05), "Junín": (-75.99, -11.15), "Ayacucho": (-74.22, -13.16),
    "Chuquisaca": (-65.26, -19.04), "Potosí": (-65.75, -19.58), "Panamá": (-79.52, 8.98),
    "Ciudad de México": (-99.13, 19.43), "Guatemala": (-90.5, 14.6), "Santiago": (-70.65, -33.45),
    "Buenos Aires": (-58.4, -34.6), "Berruecos": (-77.3, 1.6), "Santa Marta": (-74.2, 11.24),
    "Honda": (-74.75, 5.2), "Turbaco": (-75.4, 10.33), "Cuzco": (-71.97, -13.53),
}

ROJO = (185, 40, 35)
ORO = (220, 170, 60)
AZUL = (60, 90, 150)

GRAN_COLOMBIA = ["Venezuela", "Colombia", "Ecuador", "Panama"]
IMPERIO = ["Mexico", "Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama", "Cuba",
           "Dominican Rep.", "Puerto Rico", "Venezuela", "Colombia", "Ecuador", "Peru", "Bolivia", "Chile",
           "Argentina", "Paraguay", "Uruguay"]

SUDAMERICA = (-95, -30, -45, 22)
NORTE = (-84, -58, -5, 16)

# Para cada mapa: vista (lon0, lon1, lat0, lat1), países resaltados, puntos y rutas animadas.
#   puntos: (lugar, segundo en que aparece, etiqueta opcional)
#   rutas: (lista de lugares, segundo inicio, segundo fin, curva)
MAPAS = {
    "mapa_imperio": dict(vista=(-118, -30, -45, 32), resaltar={p: ROJO for p in IMPERIO},
                         gris=["Brazil"], titulo="Dominio español en América",
                         rotulos=[("IMPERIO ESPAÑOL", -64, -27, 0.5), ("Brasil (Portugal)", -50, -6, 1.0)]),
    "mapa_atlantico": dict(vista=(-90, 10, -10, 50), resaltar={"Spain": ROJO}, titulo="Las decisiones se tomaban en Madrid",
                           puntos=[("Madrid", 0.3), ("Caracas", 1.5)], rutas=[(["Madrid", "Caracas"], 0.6, 3.0, 0.25)]),
    "mapa_caracas": dict(vista=NORTE, resaltar={"Venezuela": ORO}, titulo="Capitanía General de Venezuela",
                         puntos=[("Caracas", 0.5, "Caracas, 1783")]),
    "mapa_ideas": dict(vista=(-90, 20, 0, 58), titulo="La era de las revoluciones",
                       puntos=[("París", 0.3), ("Londres", 0.5), ("Filadelfia", 1.0), ("Caracas", 1.4)],
                       rutas=[(["París", "Caracas"], 0.6, 3.2, 0.2), (["Filadelfia", "Caracas"], 1.2, 3.0, 0.15),
                              (["Londres", "Filadelfia"], 1.6, 3.6, -0.15)]),
    "mapa_europa_viaje": dict(vista=(-80, 20, 0, 55), resaltar={"Spain": ORO}, titulo="Viaje a Europa",
                              puntos=[("Caracas", 0.3), ("Madrid", 2.2)],
                              rutas=[(["Caracas", "Cádiz", "Madrid"], 0.6, 3.4, 0.2)]),
    "mapa_napoleon": dict(vista=(-12, 14, 35, 52), resaltar={"France": AZUL, "Spain": ROJO}, titulo="1808: Napoleón invade España",
                          puntos=[("París", 0.3), ("Madrid", 2.0)], rutas=[(["París", "Madrid"], 0.6, 2.8, 0.1)]),
    "mapa_londres": dict(vista=(-80, 15, 0, 58), resaltar={"United Kingdom": ORO}, titulo="Misión diplomática a Londres, 1810",
                         puntos=[("Caracas", 0.3), ("Londres", 2.4)], rutas=[(["Caracas", "Londres"], 0.6, 3.4, 0.2)]),
    "mapa_1812": dict(vista=NORTE, resaltar={"Venezuela": ROJO}, titulo="1812: cae la Primera República",
                      puntos=[("Caracas", 0.3), ("Puerto Cabello", 0.9), ("Valencia", 1.4)]),
    "mapa_cartagena": dict(vista=NORTE, resaltar={"Colombia": ORO}, titulo="Exilio en Cartagena",
                           puntos=[("Caracas", 0.3), ("Cartagena", 2.4)],
                           rutas=[(["Caracas", "Cartagena"], 0.6, 3.2, -0.12)]),
    "mapa_admirable": dict(vista=NORTE, resaltar={"Venezuela": ORO, "Colombia": ORO}, titulo="La Campaña Admirable, 1813",
                           puntos=[("Cartagena", 0.2), ("Cúcuta", 2.0), ("Mérida", 3.0), ("Trujillo", 3.8),
                                   ("Caracas", 5.5, "Caracas · 6 de agosto de 1813")],
                           rutas=[(["Cartagena", "Mompox", "Ocaña", "Cúcuta", "Mérida", "Trujillo", "Valencia", "Caracas"], 0.5, 6.0, 0)]),
    "mapa_jamaica": dict(vista=(-85, -60, 5, 22), resaltar={"Jamaica": ORO}, titulo="Exilio en Jamaica, 1815",
                         puntos=[("Cartagena", 0.3), ("Kingston", 2.2)], rutas=[(["Cartagena", "Kingston"], 0.6, 3.0, 0.15)]),
    "mapa_haiti": dict(vista=(-85, -60, 5, 22), resaltar={"Haiti": ORO}, titulo="Haití: la primera república negra",
                       puntos=[("Kingston", 0.3), ("Puerto Príncipe", 2.0), ("Margarita", 4.6)],
                       rutas=[(["Kingston", "Puerto Príncipe"], 0.6, 2.4, 0.15), (["Los Cayos", "Margarita"], 2.8, 5.0, -0.1)]),
    "mapa_angostura": dict(vista=NORTE, resaltar={"Venezuela": ORO}, titulo="Angostura, a orillas del Orinoco",
                           puntos=[("Angostura", 0.5, "Angostura (hoy Ciudad Bolívar)"), ("Caracas", 1.2)]),
    "mapa_andes": dict(vista=(-80, -60, 0, 13), resaltar={"Colombia": ORO}, titulo="El cruce de los Andes, 1819",
                       puntos=[("Angostura", 0.2), ("Mantecal", 1.2), ("Tame", 2.4), ("Pisba", 3.4, "Páramo de Pisba"),
                               ("Boyacá", 4.4)],
                       rutas=[(["Angostura", "Mantecal", "Tame", "Pisba", "Boyacá"], 0.5, 4.6, 0)]),
    "mapa_boyaca": dict(vista=(-80, -60, 0, 13), resaltar={"Colombia": ORO}, titulo="7 de agosto de 1819",
                        puntos=[("Boyacá", 0.2, "Batalla de Boyacá"), ("Bogotá", 2.0)],
                        rutas=[(["Boyacá", "Bogotá"], 0.6, 2.2, 0)]),
    "mapa_gran_colombia": dict(vista=(-95, -55, -8, 16), resaltar={p: ORO for p in GRAN_COLOMBIA},
                               titulo="La Gran Colombia (1819 – 1831)", aparicion=True,
                               puntos=[("Caracas", 0.6), ("Bogotá", 1.0, "Bogotá (capital)"), ("Quito", 1.4), ("Panamá", 1.8)]),
    "mapa_gran_colombia_crisis": dict(vista=(-95, -55, -8, 16), resaltar={p: ORO for p in GRAN_COLOMBIA},
                                      titulo="Tensiones en la Gran Colombia", grietas=True,
                                      puntos=[("Caracas", 0.4), ("Bogotá", 0.8), ("Quito", 1.2)]),
    "mapa_separacion": dict(vista=(-95, -55, -8, 16),
                            resaltar={"Venezuela": ROJO, "Colombia": ORO, "Panama": ORO, "Ecuador": AZUL},
                            titulo="1830: la Gran Colombia se divide",
                            rotulos=[("VENEZUELA", -66, 7, 0.5), ("NUEVA GRANADA", -73.5, 3.5, 1.0), ("ECUADOR", -78, -1.6, 1.5)]),
    "mapa_carabobo": dict(vista=NORTE, resaltar={"Venezuela": ORO}, titulo="24 de junio de 1821",
                          puntos=[("Carabobo", 0.4, "Batalla de Carabobo")]),
    "mapa_sur": dict(vista=SUDAMERICA, resaltar={"Ecuador": ROJO, "Peru": ROJO, "Bolivia": ROJO},
                     gris=["Brazil"], titulo="Territorios todavía realistas",
                     puntos=[("Quito", 0.8), ("Lima", 1.4)]),
    "mapa_pichincha": dict(vista=(-84, -70, -6, 4), resaltar={"Ecuador": ORO}, titulo="24 de mayo de 1822",
                           puntos=[("Guayaquil", 0.3), ("Pichincha", 2.2, "Batalla de Pichincha")],
                           rutas=[(["Guayaquil", "Quito"], 0.6, 2.4, 0)]),
    "mapa_guayaquil": dict(vista=SUDAMERICA, resaltar={"Ecuador": ORO, "Peru": AZUL, "Chile": AZUL, "Argentina": AZUL},
                           gris=["Brazil"], titulo="Encuentro de Guayaquil, 1822",
                           puntos=[("Guayaquil", 0.4), ("Bogotá", 0.8), ("Lima", 1.2)],
                           rutas=[(["Bogotá", "Quito", "Guayaquil"], 0.6, 2.6, 0),
                                  (["Buenos Aires", "Santiago", "Lima", "Guayaquil"], 0.8, 3.2, 0)]),
    "mapa_peru": dict(vista=(-90, -55, -25, 2), resaltar={"Peru": ROJO}, titulo="El Perú realista",
                      puntos=[("Lima", 0.5), ("Cuzco", 1.0), ("Guayaquil", 1.4)]),
    "mapa_ayacucho": dict(vista=(-90, -55, -25, 2), resaltar={"Peru": ORO}, titulo="La campaña del Perú, 1824",
                          puntos=[("Lima", 0.3), ("Junín", 1.6, "Junín"), ("Ayacucho", 3.6, "Ayacucho")],
                          rutas=[(["Lima", "Junín"], 0.6, 1.8, 0.1), (["Junín", "Ayacucho"], 2.2, 3.8, 0)]),
    "mapa_bolivia": dict(vista=(-90, -45, -35, 0), resaltar={"Bolivia": ORO}, gris=["Brazil"],
                         titulo="1825: nace Bolivia", aparicion=True,
                         puntos=[("Chuquisaca", 0.8, "Chuquisaca")],
                         rotulos=[("BOLIVIA", -64.5, -16.5, 1.2)]),
    "mapa_unidad": dict(vista=SUDAMERICA, resaltar={p: ORO for p in IMPERIO if p not in ("Cuba", "Puerto Rico")},
                        gris=["Brazil"], titulo="El sueño de una América unida",
                        puntos=[("Caracas", 0.2), ("Bogotá", 0.4), ("Quito", 0.6), ("Lima", 0.8), ("Chuquisaca", 1.0),
                                ("Santiago", 1.2), ("Buenos Aires", 1.4), ("Panamá", 1.6)],
                        red=["Caracas", "Bogotá", "Quito", "Lima", "Chuquisaca", "Santiago", "Buenos Aires", "Panamá"]),
    "mapa_panama": dict(vista=(-110, -50, -20, 28), resaltar={"Panama": ORO}, titulo="Congreso Anfictiónico de Panamá, 1826",
                        puntos=[("Panamá", 0.3), ("Ciudad de México", 1.0), ("Guatemala", 1.2), ("Bogotá", 1.4), ("Lima", 1.6)],
                        rutas=[(["Ciudad de México", "Panamá"], 1.0, 3.0, 0.1), (["Guatemala", "Panamá"], 1.2, 3.0, 0.1),
                               (["Bogotá", "Panamá"], 1.4, 3.0, 0.1), (["Lima", "Panamá"], 1.6, 3.2, -0.1)]),
    "mapa_ultimo_viaje": dict(vista=(-82, -66, 0, 13), resaltar={"Colombia": ORO}, titulo="El último viaje, 1830",
                              puntos=[("Bogotá", 0.3), ("Honda", 1.4), ("Cartagena", 3.6), ("Santa Marta", 4.6)],
                              rutas=[(["Bogotá", "Honda", "Mompox", "Turbaco", "Cartagena", "Santa Marta"], 0.6, 5.0, 0)]),
    "mapa_berruecos": dict(vista=(-82, -66, -4, 9), resaltar={"Colombia": ORO, "Ecuador": ORO}, titulo="4 de junio de 1830",
                           puntos=[("Bogotá", 0.3), ("Berruecos", 2.6, "Berruecos"), ("Quito", 3.2)],
                           rutas=[(["Bogotá", "Berruecos"], 0.6, 2.8, 0)], cruz="Berruecos"),
    "mapa_legado": dict(vista=SUDAMERICA,
                        resaltar={"Venezuela": ORO, "Colombia": ORO, "Ecuador": ORO, "Peru": ORO, "Bolivia": ORO, "Panama": ORO},
                        gris=["Brazil"], titulo="Las naciones bolivarianas", aparicion=True,
                        rotulos=[("Venezuela", -66, 7, 0.4), ("Colombia", -73.5, 3.5, 0.8), ("Ecuador", -78.2, -1.6, 1.2),
                                 ("Perú", -75, -9, 1.6), ("Bolivia", -64.5, -16.5, 2.0)]),
}

_paises = None


def paises():
    global _paises
    if _paises is None:
        r = shapefile.Reader(str(AQUI / "datos" / "naturalearth_lowres.shp"))
        _paises = []
        for sr, rec in zip(r.shapes(), r.records()):
            partes = list(sr.parts) + [len(sr.points)]
            anillos = [sr.points[partes[i]:partes[i + 1]] for i in range(len(partes) - 1)]
            _paises.append((rec["name"], anillos))
    return _paises


class Proyeccion:
    def __init__(self, vista):
        lon0, lon1, lat0, lat1 = vista
        latc = (lat0 + lat1) / 2
        k = math.cos(math.radians(latc))
        ancho, alto = (lon1 - lon0) * k, (lat1 - lat0)
        # ajusta la vista a 16:9 sin deformar
        if ancho / alto > W0 / H0:
            alto = ancho * H0 / W0
        else:
            ancho = alto * W0 / H0
        ancho, alto = ancho * 1.12, alto * 1.12  # margen
        self.cx, self.cy, self.k = (lon0 + lon1) / 2, latc + alto * 0.06, k  # deja sitio arriba para el título
        self.esc = W0 / ancho

    def __call__(self, lon, lat):
        return (W0 / 2 + (lon - self.cx) * self.k * self.esc, H0 / 2 - (lat - self.cy) * self.esc)


def base(nombre):
    spec = MAPAS[nombre]
    pr = Proyeccion(spec["vista"])
    img = Image.new("RGB", (W0, H0), (30, 44, 52))
    arr = np.asarray(img, float).copy()
    yy, xx = np.mgrid[0:H0, 0:W0]
    d = np.sqrt((xx - W0 / 2) ** 2 + (yy - H0 / 2) ** 2) / (W0 * 0.7)
    arr *= (1.15 - 0.5 * d)[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    capa = Image.new("RGBA", (W0 * SS, H0 * SS), (0, 0, 0, 0))
    dr = ImageDraw.Draw(capa)
    # retícula
    for lon in range(-180, 181, 10):
        dr.line([tuple(v * SS for v in pr(lon, la)) for la in (-80, 80)], fill=(150, 170, 170, 28), width=2)
    for lat in range(-80, 81, 10):
        dr.line([tuple(v * SS for v in pr(lo, lat)) for lo in (-180, 180)], fill=(150, 170, 170, 28), width=2)
    resaltar = spec.get("resaltar", {})
    gris = set(spec.get("gris", []))
    sombra = Image.new("L", (W0 * SS, H0 * SS), 0)
    ds = ImageDraw.Draw(sombra)
    for nombre_p, anillos in paises():
        for an in anillos:
            pts = [tuple(v * SS for v in pr(lo, la)) for lo, la in an]
            if len(pts) > 2:
                ds.polygon([(x + 14, y + 18) for x, y in pts], fill=200)
    capa_s = sombra.resize((W0, H0), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(Image.merge("RGBA", (Image.new("L", (W0, H0), 5),) * 3 + (capa_s.point(lambda v: v * 0.6),)))
    for nombre_p, anillos in paises():
        if nombre_p in resaltar and not spec.get("aparicion"):
            c = resaltar[nombre_p]
            relleno = tuple(int(0.55 * c[k] + 0.45 * (205, 188, 150)[k]) for k in range(3)) + (255,)
        elif nombre_p in gris:
            relleno = (150, 140, 120, 255)
        else:
            relleno = (205, 188, 150, 255)
        for an in anillos:
            pts = [tuple(v * SS for v in pr(lo, la)) for lo, la in an]
            if len(pts) > 2:
                dr.polygon(pts, fill=relleno, outline=(95, 75, 55, 255), width=3)
    img.alpha_composite(capa.resize((W0, H0), Image.LANCZOS))
    arr = np.asarray(img.convert("RGB"), float) + textura()[..., None] * 0.8
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img


def generar(nombre, forzar=False):
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / f"{nombre}.png"
    if forzar or not ruta.exists():
        base(nombre).save(ruta)
    return ruta


# ---------------- capas animadas ----------------

def _curva(a, b, curva, n=60):
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * curva, my + dx * curva
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
            for t in np.linspace(0, 1, n)]


def _parcial(pts, frac):
    if frac <= 0:
        return []
    largos = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(largos) * min(1, frac)
    out = [pts[0]]
    for i, l in enumerate(largos):
        if total >= l:
            out.append(pts[i + 1])
            total -= l
        else:
            t = total / l if l else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
            break
    return out


def _ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


def capas(nombre, t, img):
    """Dibuja sobre img (RGBA 2304x1296) las rutas, ciudades y títulos del mapa en el segundo t."""
    spec = MAPAS[nombre]
    pr = Proyeccion(spec["vista"])
    d = ImageDraw.Draw(img)
    if spec.get("aparicion"):
        a = _ease((t - 0.3) / 1.5)
        if a > 0:
            capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
            dc = ImageDraw.Draw(capa)
            for nombre_p, anillos in paises():
                if nombre_p in spec["resaltar"]:
                    c = spec["resaltar"][nombre_p]
                    for an in anillos:
                        pts = [pr(lo, la) for lo, la in an]
                        if len(pts) > 2:
                            dc.polygon(pts, fill=c + (int(150 * a),), outline=c + (int(255 * a),), width=3)
            img.alpha_composite(capa)
    if spec.get("grietas"):
        pulso = 0.5 + 0.5 * math.sin(t * 3)
        for nombre_p, anillos in paises():
            if nombre_p in ("Venezuela", "Ecuador"):
                for an in anillos:
                    pts = [pr(lo, la) for lo, la in an]
                    d.line(pts + [pts[0]], fill=(200, 30, 30, int(120 + 135 * pulso)), width=7)
    if spec.get("red"):
        a = _ease((t - 1.6) / 2.0)
        nodos = [pr(*LUGARES[n]) for n in spec["red"]]
        for i in range(len(nodos)):
            for j in range(i + 1, len(nodos)):
                d.line([nodos[i], nodos[j]], fill=(240, 210, 130, int(110 * a)), width=3)
    for (lugares, t0, t1, curva) in spec.get("rutas", []):
        pts_l = [pr(*LUGARES[n]) for n in lugares]
        if len(pts_l) == 2:
            pts = _curva(pts_l[0], pts_l[1], curva)
        else:
            pts = []
            for i in range(len(pts_l) - 1):
                pts += _curva(pts_l[i], pts_l[i + 1], 0.06 * (1 if i % 2 else -1), 20)
        frac = _ease((t - t0) / max(0.1, t1 - t0))
        parte = _parcial(pts, frac)
        if len(parte) > 1:
            # línea discontinua
            acum = 0
            for i in range(len(parte) - 1):
                seg = math.dist(parte[i], parte[i + 1])
                if int(acum / 26) % 2 == 0:
                    d.line([parte[i], parte[i + 1]], fill=(170, 25, 25, 255), width=9)
                acum += seg
            x, y = parte[-1]
            d.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(170, 25, 25, 255), outline=(255, 240, 210, 255), width=4)
    fl = fuente("serif_b", 46)
    for pt in spec.get("puntos", []):
        lugar, t0 = pt[0], pt[1]
        etiqueta = pt[2] if len(pt) > 2 else lugar
        a = _ease((t - t0) / 0.5)
        if a <= 0:
            continue
        x, y = pr(*LUGARES[lugar])
        r = 12 + 30 * (1 - a) + 4 * math.sin(t * 4 + t0) * a
        d.ellipse((x - r * 1.9, y - r * 1.9, x + r * 1.9, y + r * 1.9), outline=(170, 25, 25, int(160 * a)), width=4)
        d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=(40, 25, 20, int(255 * a)), outline=(255, 240, 210, int(255 * a)), width=4)
        tx, ty = x + 24, y - 30
        if tx + fl.getlength(etiqueta) > W0 - 40:
            tx = x - 24 - fl.getlength(etiqueta)
        d.text((tx, ty), etiqueta, font=fl, fill=(30, 20, 15, int(255 * a)), stroke_width=7,
               stroke_fill=(240, 228, 200, int(230 * a)))
        if spec.get("cruz") == lugar and a > 0.5:
            d.line((x - 22, y + 30, x + 22, y + 74), fill=(170, 25, 25, 255), width=8)
            d.line((x + 22, y + 30, x - 22, y + 74), fill=(170, 25, 25, 255), width=8)
    fr = fuente("serif_b", 64)
    for (txt, lon, lat, t0) in spec.get("rotulos", []):
        a = _ease((t - t0) / 0.8)
        if a > 0:
            x, y = pr(lon, lat)
            d.text((x, y), txt, font=fr, anchor="mm", fill=(60, 30, 20, int(235 * a)), stroke_width=6,
                   stroke_fill=(240, 225, 190, int(200 * a)))
    if spec.get("titulo"):
        a = _ease((t - 0.2) / 0.8)
        ft = fuente("serif_b", 64)
        ancho = ft.getlength(spec["titulo"])
        x, y = W0 / 2, 175
        d.rectangle((x - ancho / 2 - 50, y - 60, x + ancho / 2 + 50, y + 60), fill=(25, 18, 14, int(200 * a)))
        d.line((x - ancho / 2 - 50, y + 60, x + ancho / 2 + 50, y + 60), fill=(215, 175, 95, int(255 * a)), width=4)
        d.text((x, y), spec["titulo"], font=ft, anchor="mm", fill=(240, 225, 190, int(255 * a)))


if __name__ == "__main__":
    import sys
    for n in sys.argv[1:] or MAPAS:
        print("mapa", n)
        generar(n, forzar=True)
