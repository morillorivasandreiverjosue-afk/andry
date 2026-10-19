"""Guion de «La caída de Constantinopla — 1453» (Curiosidades del Mundo, 60 s, 9:16).

Cada escena tiene sus frases (« | » marca dónde cortar el subtítulo), las imágenes que se muestran y el
estado de la música. `voz` ajusta solo la pronunciación, no los subtítulos.
"""

ESCENAS = [
    {"frases": ["Durante más de mil años, | una ciudad fue considerada | una de las fortalezas | más poderosas del mundo.",
                "Pero en 1453, | un ejército llegó | para cambiar la historia | para siempre."],
     "imagenes": ["01_ciudad_amanecer", "10_murallas_ejercito"], "musica": "frio"},
    {"frases": ["Constantinopla era la capital | del Imperio bizantino, | heredero del antiguo | Imperio romano.",
                "Sus murallas habían protegido | la ciudad durante siglos, | pero una nueva potencia | amenazaba sus puertas: | el Imperio otomano."],
     "imagenes": ["07_ciudad_reconstruccion", "06_murallas_canones"], "musica": "tension"},
    {"frases": ["El sultán Mehmed Segundo | reunió un enorme ejército | y utilizó grandes cañones | para bombardear las defensas.",
                "Durante semanas, | los otomanos intentaron | abrir una brecha en las murallas | mientras los defensores | luchaban por mantener la ciudad."],
     "imagenes": ["05_mehmed_tienda", "08_murallas_fuego", "02_asalto_brecha"], "musica": "epico"},
    {"frases": ["El 29 de mayo de 1453, | las fuerzas otomanas | lograron conquistar Constantinopla.",
                "El emperador Constantino Undécimo | murió durante la defensa | y el Imperio bizantino | llegó a su fin."],
     "imagenes": ["03_bandera_escombros", "04_mehmed_entrada"], "musica": "triste"},
    {"frases": ["La conquista consolidó | el poder otomano | sobre una ciudad estratégica | entre Europa y Asia.",
                "Para muchos historiadores, | también representa | uno de los grandes puntos | de transición | entre la Edad Media | y la Edad Moderna.",
                "Una ciudad cayó… | y el mundo entró | en una nueva etapa."],
     "imagenes": ["mapa", "01_ciudad_amanecer"], "musica": "majestuoso"},
]

PRONUNCIACION = [
    ("29 de mayo de 1453", "veintinueve de mayo de mil cuatrocientos cincuenta y tres"),
    ("1453", "mil cuatrocientos cincuenta y tres"),
    ("Mehmed", "Méjmed"),
    ("…", ","),
    (" | ", " "),
]


def voz(texto):
    for a, b in PRONUNCIACION:
        texto = texto.replace(a, b)
    return texto
