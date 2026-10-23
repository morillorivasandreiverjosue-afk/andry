"""Guion de «Pompeya: la ciudad que desapareció» (≈60 s, 9:16).

Cada escena tiene sus imágenes (números de salida/escenas/NN.png) y sus frases.
Cada frase se locuta de una vez; dentro de ella, «|» separa los fragmentos que salen
en pantalla y *palabra* se resalta en amarillo.
"""

ESCENAS = [
    {"nombre": "gancho", "imagenes": [1], "musica": "misterio", "frases": [
        "Imagina salir de casa | un *día cualquiera*…",
        "sin saber que tu ciudad | está a punto de *desaparecer* | bajo una *catástrofe volcánica*.",
    ]},
    {"nombre": "vida", "imagenes": [2, 3], "musica": "misterio", "frases": [
        "*Pompeya* era una ciudad romana | llena de comercios, viviendas, | tabernas y calles transitadas.",
        "La gente trabajaba, compraba | y hacía su *vida normal*,",
        "junto al imponente | volcán *Vesubio*.",
    ]},
    {"nombre": "erupcion", "imagenes": [4, 5], "musica": "tension", "frases": [
        "Pero en el año *79* | *después de Cristo*, | el Vesubio *entró en erupción*.",
        "Una enorme *columna de ceniza* | se elevó sobre la región.",
        "La *piedra pómez* | comenzó a caer sobre la ciudad,",
        "y algunos tejados | se *desplomaron* por el peso.",
    ]},
    {"nombre": "catastrofe", "imagenes": [6, 7], "musica": "tension", "frases": [
        "La situación *empeoró*.",
        "Los materiales volcánicos | cubrieron calles y edificios,",
        "mientras *corrientes ardientes* | de gases y ceniza | alcanzaron la zona.",
        "Pompeya quedó *sepultada* | y muchos de sus habitantes | *murieron*.",
    ]},
    {"nombre": "descubrimiento", "imagenes": [8, 9, 10], "musica": "majestuoso", "frases": [
        "Durante *siglos*, | gran parte de la ciudad | permaneció *enterrada*.",
        "Con las excavaciones | sistemáticas de *1748*,",
        "el mundo descubrió | una *ventana extraordinaria* | a la vida de la antigua *Roma*.",
    ]},
    {"nombre": "cierre", "imagenes": [11, 12], "musica": "majestuoso", "frases": [
        "Lo más increíble | es que la catástrofe | que *destruyó* Pompeya",
        "también ayudó a *conservarla*.",
        "Hoy, sus ruinas nos muestran | cómo vivían los romanos | hace casi *dos mil años*.",
    ]},
]

# Cómo debe leer la voz algunos números y palabras
PRONUNCIACION = {
    "79": "setenta y nueve",
    "1748": "mil setecientos cuarenta y ocho",
}


def limpio(frase):
    """Texto tal como se lee en pantalla, sin marcas."""
    return " ".join(frase.replace("|", " ").replace("*", "").split())


def para_voz(frase):
    texto = limpio(frase)
    for k, v in PRONUNCIACION.items():
        texto = texto.replace(k, v)
    return texto


def fragmentos(frase):
    """Lista de fragmentos; cada uno es una lista de (palabra, resaltada)."""
    resultado = []
    for trozo in frase.split("|"):
        palabras, dentro = [], False
        for p in trozo.split():
            empieza = p.startswith("*")
            dentro = dentro or empieza
            limpia = p.replace("*", "")
            palabras.append((limpia, dentro))
            if p.rstrip(".,…").endswith("*"):
                dentro = False
        resultado.append(palabras)
    return resultado
