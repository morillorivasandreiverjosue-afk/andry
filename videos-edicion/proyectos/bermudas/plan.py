"""Qué foto, música y efectos lleva cada parte del documental del Triángulo de las Bermudas.

Secciones: 0 introducción, 1 dónde está, 2 USS Cyclops, 3 Flight 19, 4 teorías, 5 explicación científica,
6 por qué sigue siendo un misterio, 7 el océano guarda sus secretos.
"""

# palabras del guion -> tema de foto (gana la primera que coincida)
PALABRAS = [
    ("No hay tierra a la vista", "oceano"), ("barco avanza", "tormenta_mar"),
    ("comunicación se interrumpe", "radio"), ("radares", "radar"), ("equipos de rescate", "rescate"),
    ("Ni barcos", "naufragio"), ("Ni pasajeros", "noche_mar"), ("Ni restos", "naufragio"),
    ("fuerzas magnéticas", "brujula"), ("tiempo y el espacio", "noche_mar"),
    ("civilizaciones desaparecidas", "atlantida"), ("objetos voladores", "ovni"),
    ("Miami", "miami"), ("islas Bermudas", "bermudas_espacio"), ("Puerto Rico", "puerto_rico"),
    ("límites", "mapa"), ("mapas náuticos", "mapa"), ("Vincent Gaddis", "mapa"),
    ("USS Cyclops", "cyclops"), ("manganeso", "cyclops"), ("306 personas", "cyclops"), ("Brasil", "barco_antiguo"),
    ("señal de socorro", "radio"), ("submarinos", "barco_antiguo"), ("historia naval", "cyclops"),
    ("Cinco aviones", "avenger"), ("TBM Avenger", "avenger"), ("Avengers", "avenger"), ("Flight 19", "avenger"),
    ("base aérea", "base_aerea"), ("Charles Taylor", "radio"), ("informó por radio", "radio"),
    ("personal de tierra", "radio"), ("desorientados", "avenger"), ("se perdió el contacto", "radar"),
    ("Martin Mariner", "mariner"), ("avión de rescate", "mariner"), ("operación de búsqueda", "rescate"),
    ("kilómetros cuadrados", "rescate"), ("condiciones meteorológicas", "tormenta_mar"),
    ("Atlántida", "atlantida"), ("antigua civilización", "atlantida"), ("extraterrestres", "ovni"),
    ("otros planetas", "ovni"), ("paranormales", "ovni"), ("brújulas", "brujula"), ("magnétic", "brujula"),
    ("metano", "metano"), ("flotabilidad", "metano"),
    ("huracanes", "huracan"), ("tormentas tropicales", "huracan"), ("olas enormes", "tormenta_mar"),
    ("predicción meteorológica", "satelite"), ("corriente del Golfo", "corriente_golfo"),
    ("agua cálida", "corriente_golfo"), ("arrecifes", "arrecife"), ("poca profundidad", "arrecife"),
    ("errores humanos", "radio"), ("instrumentos", "brujula"), ("Administración Nacional Oceánica", "satelite"),
    ("seguimiento por satélite", "satelite"), ("operaciones de rescate", "rescate"), ("aguas profundas", "naufragio"),
    ("restos", "naufragio"), ("películas", "faro"), ("océano sigue siendo inmenso", "oceano"),
    ("secretos", "noche_mar"), ("comentarios", "faro"), ("Curiosidades del Mundo", "noche_mar"),
]

POR_CAPITULO = {
    0: ["oceano", "tormenta_mar", "noche_mar", "radar", "naufragio", "rayos"],
    1: ["mapa", "bermudas_espacio", "miami", "puerto_rico", "oceano"],
    2: ["cyclops", "barco_antiguo", "tormenta_mar", "naufragio", "noche_mar"],
    3: ["avenger", "mariner", "radio", "base_aerea", "rescate", "tormenta_mar"],
    4: ["atlantida", "ovni", "brujula", "metano", "noche_mar", "rayos"],
    5: ["huracan", "tormenta_mar", "corriente_golfo", "arrecife", "satelite", "rayos"],
    6: ["satelite", "rescate", "naufragio", "radio", "noche_mar"],
    7: ["oceano", "faro", "noche_mar", "mapa", "bermudas_espacio"],
}

ALIAS = {
    "radio": ["radar"], "radar": ["radio"], "base_aerea": ["avenger"], "mariner": ["rescate", "avenger"],
    "barco_antiguo": ["cyclops"], "naufragio": ["tormenta_mar", "oceano"], "noche_mar": ["oceano"],
    "miami": ["bermudas_espacio", "mapa"], "puerto_rico": ["bermudas_espacio", "mapa"],
    "metano": ["naufragio", "oceano"], "satelite": ["huracan"], "faro": ["tormenta_mar"],
    "rayos": ["tormenta_mar"], "ovni": ["noche_mar"], "atlantida": ["mapa"], "brujula": ["radar", "mapa"],
}

MUSICA = {0: "intriga", 1: "investigacion", 2: "misterio", 3: "intriga", 4: "misterio", 5: "investigacion",
          6: "misterio", 7: "epico_mar"}

FECHAS = {0: "ATLÁNTICO OCCIDENTAL", 1: "1964", 2: "MARZO 1918", 3: "05.12.1945", 4: "TEORÍAS", 5: "CIENCIA",
          6: "SIN RESPUESTA", 7: "ATLÁNTICO OCCIDENTAL", 8: ""}

ROTULOS = {
    "Vincent Gaddis": "Escritor · popularizó el nombre en 1964",
    "USS Cyclops desapareció": "Buque de la Armada de EE. UU. · 306 personas a bordo",
    "TBM Avenger": "Torpederos de la Armada de EE. UU.",
    "Charles Taylor": "Líder de la formación del Flight 19",
    "Martin Mariner": "Hidroavión de rescate · 13 tripulantes",
    "corriente del Golfo": "Corriente cálida del Atlántico",
    "Administración Nacional Oceánica": "NOAA · agencia oceánica de EE. UU.",
}
MET = {}

EFECTOS = [
    ("sonido del viento golpea las olas", "olas"),
    ("La comunicación se interrumpe", "radio"),
    ("Los radares dejan de recibir señales", "sonar"),
    ("De repente, algo extraño sucede", "impacto"),
    ("Nunca llegó a su destino", "impacto"),
    ("despegaron desde una base aérea", "motor"),
    ("informó por radio", "radio"),
    ("Las comunicaciones registraron dificultades", "radio"),
    ("Finalmente, se perdió el contacto", "sonar"),
    ("Los cinco aviones desaparecieron", "impacto"),
    ("Sin embargo, tampoco regresó", "impacto"),
    ("Los minutos pasaban", "latido"),
    ("huracanes y las tormentas tropicales", "trueno"),
    ("olas enormes, fuertes vientos", "viento"),
    ("El océano sigue siendo inmenso", "olas"),
]

NOMBRES = {"USS Cyclops desapareció": "USS Cyclops", "TBM Avenger": "TBM Avenger", "corriente del Golfo":
           "Corriente del Golfo", "Administración Nacional Oceánica": "NOAA", "Martin Mariner": "PBM Mariner"}
