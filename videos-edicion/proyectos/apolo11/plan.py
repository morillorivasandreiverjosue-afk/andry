"""Qué foto, música y efectos lleva cada parte del documental."""

# palabras del guion -> tema de foto (el primero que coincida gana)
PALABRAS = [
    ("Sputnik", "sputnik"), ("Gagarin", "gagarin"), ("cosmonauta", "gagarin"),
    ("Kennedy anunció", "kennedy"), ("presidente Kennedy", "kennedy_rice"), ("Kennedy", "kennedy"),
    ("Guerra Fría", "tierra_espacio"), ("superpotencias", "tierra_espacio"),
    ("fallo", "apolo1"), ("peligro", "apolo1"),
    ("ingenieros", "control_mision"), ("NASA", "vab"),
    ("Neil Armstrong, comandante", "armstrong"), ("Buzz Aldrin. Su", "aldrin"), ("conocido como Buzz", "aldrin"),
    ("Michael Collins, encargado", "collins"), ("tres astronautas", "tripulacion"), ("Los tres", "tripulacion"),
    ("fotografías históricas", "aldrin_superficie"),
    ("Saturno V", "saturno_v"), ("cohete", "saturno_v"), ("etapas", "saturno_v"), ("etapa", "saturno_v"),
    ("Columbia", "columbia"), ("Eagle", "eagle"), ("módulo lunar", "eagle"), ("módulo de mando", "columbia"),
    ("ordenadores", "agc"), ("ordenador", "agc"), ("computadora", "agc"),
    ("Houston", "control_mision"), ("controladores", "control_mision"), ("control de la misión", "control_mision"),
    ("centro de control", "control_mision"),
    ("espectadores", "multitud"), ("observaban", "multitud"),
    ("plataforma", "saturno_v"), ("motores", "lanzamiento"), ("humo", "lanzamiento"), ("elevarse", "lanzamiento"),
    ("lanzamiento", "lanzamiento"),
    ("Tierra se veía", "tierra_espacio"), ("órbita terrestre", "tierra_espacio"), ("384.000", "tierra_espacio"),
    ("órbita lunar", "luna_orbita"), ("orbitando", "luna_orbita"), ("proximidades de la Luna", "luna_orbita"),
    ("Mar de la Tranquilidad", "luna_orbita"), ("cráteres", "luna_orbita"),
    ("escalera", "armstrong_eagle"), ("primer paso", "huella"), ("apoyó su pie", "huella"), ("pie", "huella"),
    ("huellas", "huella"), ("transmisión televisiva", "control_mision"),
    ("Aldrin también", "aldrin_superficie"), ("gravedad", "aldrin_superficie"), ("caminaron", "aldrin_superficie"),
    ("placa", "placa"), ("bandera", "bandera"), ("instrumentos científicos", "experimentos"),
    ("muestras", "rocas"), ("rocas", "rocas"), ("laboratorios", "rocas"), ("21,5", "rocas"),
    ("sistema solar", "luna_llena"),
    ("despegue", "eagle_ascenso"), ("despegar", "eagle_ascenso"), ("reunieron", "eagle_ascenso"),
    ("encontrarse con la nave", "eagle_ascenso"),
    ("reentrada", "reentrada"), ("escudo térmico", "reentrada"), ("atmósfera", "reentrada"),
    ("paracaídas", "reentrada"), ("océano Pacífico", "amerizaje"), ("recuperación", "hornet"),
    ("sanos y salvos", "amerizaje"), ("héroes", "desfile"), ("cuarentena", "cuarentena"),
    ("Apolo 12", "apolo12"), ("Apolo 17", "apolo17_superficie"), ("misiones robóticas", "luna_llena"),
    ("nuevas expediciones", "artemis"), ("programas espaciales", "artemis"),
    ("medio siglo", "earthrise"), ("imágenes siguen", "huella"),
]

# temas por defecto de cada capítulo (0 = introducción ... 13 = conclusión)
POR_CAPITULO = {
    0: ["luna_superficie", "eagle", "luna_orbita", "aldrin_superficie", "control_mision", "earthrise"],
    1: ["luna_llena", "estrellas", "sputnik", "tierra_espacio", "luna_llena"],
    2: ["kennedy", "kennedy_rice", "vab", "control_mision", "saturno_v", "astronautas_nave"],
    3: ["tripulacion", "armstrong", "aldrin", "collins", "astronautas_nave"],
    4: ["saturno_v", "vab", "columbia", "eagle", "agc"],
    5: ["lanzamiento", "saturno_v", "multitud", "tierra_espacio", "control_mision"],
    6: ["tierra_espacio", "luna_orbita", "earthrise", "columbia", "eagle"],
    7: ["eagle", "luna_orbita", "control_mision", "luna_superficie"],
    8: ["armstrong_eagle", "huella", "aldrin_superficie", "luna_superficie", "experimentos"],
    9: ["placa", "bandera", "rocas", "luna_superficie", "luna_orbita", "columbia"],
    10: ["eagle_ascenso", "columbia", "luna_orbita", "earthrise", "tierra_espacio"],
    11: ["reentrada", "amerizaje", "hornet", "cuarentena", "desfile"],
    12: ["apolo12", "apolo17", "apolo17_superficie", "luna_llena", "artemis"],
    13: ["earthrise", "huella", "aldrin_superficie", "tierra_espacio", "apolo17", "luna_llena"],
}

# música de cada capítulo
MUSICA = {0: "suspenso", 1: "espacio", 2: "suspenso", 3: "calma", 4: "suspenso", 5: "tension", 6: "espacio",
          7: "tension", 8: "triunfo", 9: "calma", 10: "suspenso", 11: "triunfo", 12: "espacio", 13: "triunfo"}

# fecha que aparece en la esquina de la pantalla (estilo cabina)
FECHAS = {0: "20.07.1969", 1: "1957 — 1961", 2: "25.05.1961", 3: "1969", 4: "1969", 5: "16.07.1969",
          6: "17-19.07.1969", 7: "20.07.1969", 8: "21.07.1969", 9: "21.07.1969", 10: "21-22.07.1969",
          11: "24.07.1969", 12: "1969 — 1972", 13: "20.07.1969"}

# reloj de misión (horas transcurridas desde el despegue) al empezar cada capítulo
MET = {5: 0.0, 6: 30.0, 7: 100.2, 8: 102.75, 9: 110.0, 10: 124.4, 11: 195.0}

# rótulos con nombre la primera vez que se menciona a alguien
ROTULOS = {
    "John F. Kennedy": "Presidente de Estados Unidos",
    "Yuri Gagarin": "Primer ser humano en el espacio · 1961",
    "Neil Armstrong, comandante": "Comandante · Apolo 11",
    "Buzz Aldrin.": "Piloto del módulo lunar · Apolo 11",
    "Michael Collins, encargado": "Piloto del módulo de mando · Apolo 11",
    "Columbia, era": "Módulo de mando · CSM-107",
    "Eagle, estaba": "Módulo lunar · LM-5",
    "Mar de la Tranquilidad": "0,67° N  23,47° E",
}

# efectos especiales ligados a frases
EFECTOS = [
    ("una voz llegó desde el espacio", "radio"),
    ("El módulo lunar había aterrizado", "radio"),
    ("los motores del cohete se encendieron", "despegue"),
    ("Enormes columnas de humo", "rugido"),
    ("las alarmas del ordenador", "alarma"),
    ("Cada segundo era importante", "latido"),
    ("el Eagle tocó la superficie", "toque"),
    ("Armstrong comunicó a Houston", "radio"),
    ("pronunció una frase", "radio"),
    ("atravesó la atmósfera", "rugido"),
    ("perdía temporalmente las comunicaciones", "estatica"),
]
