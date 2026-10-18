"""Guion (TikTok, ~1:19), tiempos de la narración y subtítulos.

La narración (voz «Franco – Narrador documental/misterio», ElevenLabs v4) está en
salida/voz_tiktok.wav. El inicio y el fin de cada frase se midieron detectando los silencios.
"""

INICIO_VOZ = 0.6
DURACION = 79.0
FPS = 30
W, H = 1080, 1920

# (inicio, fin) en segundos del audio de la voz, y texto de los subtítulos
FRASES = [
    (0.00, 2.45, "¿Cómo era realmente vivir en la Edad Media?"),
    (3.07, 5.85, "Imagínate despertar en un mundo sin electricidad,"),
    (6.20, 8.31, "sin automóviles y sin teléfonos."),
    (8.83, 11.50, "Un mundo dominado por enormes castillos,"),
    (12.02, 13.56, "reyes poderosos"),
    (13.83, 16.17, "y caballeros preparados para la guerra."),
    (16.98, 19.05, "Bienvenidos a la Edad Media,"),
    (19.40, 24.60, "un período histórico que comenzó aproximadamente en el año 476,"),
    (25.19, 27.90, "tras la caída del Imperio romano de Occidente,"),
    (28.26, 32.08, "y terminó convencionalmente hacia finales del siglo XV."),
    (32.68, 36.74, "En aquellos tiempos, la sociedad estaba marcada por grandes diferencias."),
    (37.20, 40.96, "Mientras algunos reyes y nobles vivían rodeados de riquezas,"),
    (41.37, 45.07, "gran parte de la población trabajaba en el campo para sobrevivir."),
    (45.62, 50.39, "Los castillos servían como residencias fortificadas y lugares de defensa."),
    (50.74, 53.10, "Los caballeros entrenaban para combatir,"),
    (53.10, 56.80, "y las guerras podían cambiar el destino de reinos enteros."),
    (57.35, 59.80, "Pero no todo era oscuridad y batallas."),
    (60.28, 61.74, "También existían mercados,"),
    (62.10, 62.93, "universidades,"),
    (63.37, 64.70, "avances científicos,"),
    (65.07, 68.09, "grandes construcciones y culturas fascinantes."),
    (68.51, 70.95, "Y esta es solo una pequeña parte…"),
    (71.33, 74.64, "de una época que duró cerca de mil años."),
]

# Palabras que se resaltan en dorado en los subtítulos
CLAVE = {"edad", "media", "castillos", "reyes", "caballeros", "guerra", "476", "imperio", "romano", "xv",
         "riquezas", "campo", "defensa", "guerras", "reinos", "mercados", "universidades", "científicos",
         "construcciones", "culturas", "mil", "años", "electricidad", "automóviles", "teléfonos", "nobles"}


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
