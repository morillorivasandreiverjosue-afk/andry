"""Lee guion.txt y lo divide en capítulos y párrafos narrables."""
import re
from pathlib import Path

AQUI = Path(__file__).parent

# Cómo debe pronunciar la voz algunos nombres (solo afecta al audio, no a los subtítulos)
PRONUNCIACION = [
    ("Napoleone Buonaparte", "Napoleóne Buonapárte"),
    ("Napoléon Bonaparte", "Napoleón Bonapárt"),
    ("Marie Josèphe Rose Tascher de La Pagerie", "Marí Yosef Ros Tashé de La Pashrí"),
    ("Joséphine", "Yosefín"),
    ("Beauharnais", "Boarné"),
    ("Alexandre de", "Alexándr de"),
    ("Alexandre Walewski", "Alexándr Valevski"),
    ("Eugène", "Eushén"),
    ("Hortense", "Ortáns"),
    ("Éléonore Denuelle de La Plaigne", "Eleonór Denuél de La Plén"),
    ("Charles Léon", "Sharl León"),
    ("Walewska", "Valevska"),
    ("Malmaison", "Malmesón"),
    ("Ajaccio", "Ayáchio"),
    ("Letizia", "Letísia"),
    ("Saint-Cloud", "San Clú"),
    ("Grande Armée", "Grand Armé"),
    ("Luis XVIII", "Luis dieciocho"),
    ("Francisco I.", "Francisco primero."),
    ("siglo XIX", "siglo diecinueve"),
    ("siglo XVIII", "siglo dieciocho"),
    ("Gebhard Leberecht von Blücher", "Guébjard Lébereijt fon Blíjer"),
    ("Wellington", "Uélinton"),
    ("Horatio Nelson", "Joréisho Nélson"),
    ("Notre Dame", "Notr Dam"),
    ("Longwood House", "Lóngwud Jáus"),
    ("Reichstadt", "Ráijshtat"),
    ("Auerstedt", "Áuershtet"),
    ("Jena", "Iéna"),
    ("Leipzig", "Láipsig"),
    ("Waterloo", "Uaterlú"),
    ("Tilsit", "Tílsit"),
    (" — ", ". "),
]

NUMEROS = {str(i): w for i, w in enumerate(
    "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce".split())}


def para_voz(texto):
    for a, b in PRONUNCIACION:
        texto = texto.replace(a, b)
    return texto


def leer():
    """Devuelve una lista de capítulos: {titulo, numero, nota, parrafos[]}"""
    caps = []
    for linea in (AQUI / "guion.txt").read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        m = re.match(r"^(INTRODUCCIÓN|CAPÍTULO (\d+)|FINAL) — (.+)$", linea)
        if m:
            caps.append({"etiqueta": m.group(1), "numero": int(m.group(2)) if m.group(2) else None,
                         "titulo": m.group(3), "nota": "", "parrafos": []})
        elif linea.startswith("["):
            caps[-1]["nota"] = linea.strip("[]")
        else:
            caps[-1]["parrafos"].append(linea)
    return caps


def texto_titulo_voz(cap):
    t = cap["titulo"].lower().replace("joséphine", "yosefín").replace("waterloo", "uaterlú")
    t = t[0].upper() + t[1:] + "."
    if cap["numero"]:
        return f"Capítulo {NUMEROS[str(cap['numero'])]}. {t}"
    return t


def frases(texto):
    """Divide un párrafo en frases (para subtítulos)."""
    partes = re.split(r"(?<=[.?!:])\s+(?=[¿¡A-ZÁÉÍÓÚÑ0-9])", texto)
    return [p for p in partes if p]
