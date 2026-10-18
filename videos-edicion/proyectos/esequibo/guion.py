"""Guion corto (TikTok, 60 s), tiempos de la narración y subtítulos.

La narración (voz venezolana «José Manuel», ElevenLabs v4, ralentizada un 6 %) está en
salida/voz_tiktok.wav. El inicio y el fin
de cada frase se midieron sobre ese archivo detectando los silencios entre frases.
"""

DURACION = 60.0
INICIO_VOZ = 0.4     # la voz entra justo después del golpe inicial
FPS = 30
W, H = 1080, 1920

# (inicio, fin) en segundos del audio de la voz, y texto para los subtítulos
FRASES = [
    (0.15, 6.40, "¿Sabías que Venezuela reclama un territorio de casi 160.000 km² que hoy controla otro país?"),
    (6.89, 11.40, "Se llama el Esequibo, y la disputa lleva más de 100 años sin resolverse."),
    (12.00, 18.67, "Todo comenzó en 1899, cuando un tribunal arbitral en París otorgó el territorio a la Guayana Británica."),
    (19.16, 24.24, "Venezuela rechazó esa decisión y sostiene que el Esequibo le pertenece históricamente."),
    (24.79, 30.55, "En 1966 se firmó el Acuerdo de Ginebra, para buscar una solución práctica a la controversia."),
    (31.10, 36.98, "Pero Guyana considera válido el laudo de 1899, y mantiene el control del territorio."),
    (37.49, 44.27, "La disputa se volvió aún más importante con el descubrimiento de enormes reservas de petróleo frente a las costas de Guyana."),
    (44.89, 48.21, "Hoy, el caso está en la Corte Internacional de Justicia."),
    (48.81, 51.25, "¿Podrá Venezuela recuperar el Esequibo algún día?"),
    (51.83, 52.63, "El desenlace…"),
    (53.07, 54.80, "todavía está por conocerse."),
]

# Palabras que se resaltan en amarillo en los subtítulos
CLAVE = {"venezuela", "esequibo", "guyana", "160.000", "km²", "100", "1899", "1966", "ginebra", "petróleo",
         "corte", "internacional", "justicia", "británica", "laudo", "parís", "recuperar", "desenlace"}


def frase(i):
    """(inicio, fin) de la frase i en segundos del video."""
    a, b, _ = FRASES[i]
    return INICIO_VOZ + a, INICIO_VOZ + b


def bloques_subtitulos(max_letras=17):
    """Trozos cortos (estilo TikTok) con el tiempo repartido según el número de letras."""
    salida = []
    for i, (_, _, texto) in enumerate(FRASES):
        a, b = frase(i)
        trozos, actual = [], []
        for p in texto.split():
            if actual and len(" ".join(actual + [p])) > max_letras:
                trozos.append(actual)
                actual = []
            actual.append(p)
            if p.endswith((",", ":", "?")) and len(" ".join(actual)) > 6:
                trozos.append(actual)
                actual = []
        if actual:
            trozos.append(actual)
        total = sum(len(" ".join(t)) + 2 for t in trozos)
        t = a
        for tr in trozos:
            d = (b - a) * (len(" ".join(tr)) + 2) / total
            salida.append((t, t + d, tr))
            t += d
    return salida
