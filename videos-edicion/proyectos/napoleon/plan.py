"""Plan visual y sonoro: qué escena, efectos y música acompañan a cada párrafo."""

ORO, ORO2, ROJO, AZUL = (205, 165, 80, 255), (225, 200, 130, 255), (185, 110, 100, 255), (150, 160, 185, 255)

L = {  # lugares (lon, lat)
    "París": (2.35, 48.86), "Ajaccio": (8.74, 41.92), "Génova": (8.93, 44.41), "Marsella": (5.37, 43.3),
    "Brienne": (4.53, 48.39), "Tolón": (5.93, 43.12), "Niza": (7.27, 43.7), "Montenotte": (8.4, 44.4),
    "Lodi": (9.5, 45.31), "Milán": (9.19, 45.46), "Arcole": (11.27, 45.36), "Rivoli": (10.8, 45.57),
    "Campo Formio": (13.1, 46.0), "Malta": (14.5, 35.9), "Alejandría": (29.9, 31.2), "El Cairo": (31.24, 30.04),
    "Pirámides": (31.13, 29.98), "Abukir": (30.07, 31.32), "Jaffa": (34.75, 32.05), "Acre": (35.07, 32.93),
    "Fréjus": (6.74, 43.43), "Ulm": (9.99, 48.4), "Viena": (16.37, 48.21), "Austerlitz": (16.76, 49.15),
    "Trafalgar": (-6.04, 36.18), "Jena": (11.59, 50.93), "Berlín": (13.4, 52.52), "Tilsit": (21.88, 55.08),
    "Madrid": (-3.7, 40.42), "Bailén": (-3.77, 38.09), "Zaragoza": (-0.88, 41.65), "Kaunas": (23.9, 54.9),
    "Vilna": (25.28, 54.69), "Smolensk": (32.04, 54.78), "Borodinó": (35.82, 55.52), "Moscú": (37.62, 55.75),
    "Berézina": (28.4, 54.3), "Leipzig": (12.37, 51.34), "Montmirail": (3.54, 48.87), "Elba": (10.25, 42.78),
    "Golfe-Juan": (7.07, 43.57), "Grenoble": (5.72, 45.19), "Lyon": (4.83, 45.76), "Bruselas": (4.35, 50.85),
    "Waterloo": (4.41, 50.68), "Ligny": (4.58, 50.51), "Charleroi": (4.44, 50.41), "Plymouth": (-4.14, 50.37),
    "Santa Elena": (-5.7, -15.95), "Cherburgo": (-1.62, 49.64), "Martinica": (-61.0, 14.6), "Varsovia": (21.0, 52.23),
    "Fontainebleau": (2.7, 48.4),
}


def lug(*nombres, izq=()):
    return [(n, *L[n]) + (("izq",) if n in izq else ()) for n in nombres]


def ruta(*nombres, color=(160, 25, 25), ini=0.1, fin=0.75):
    return {"pts": [L[n] if isinstance(n, str) else n for n in nombres], "color": color, "ini": ini, "fin": fin}


def mapa(titulo, caja, lugares, rutas=(), batallas=(), resaltar=None, zoom=(1.0, 1.07)):
    return {"tipo": "mapa", "titulo": titulo, "caja": caja, "lugares": lugares, "rutas": list(rutas),
            "batallas": [L[b] for b in batallas], "resaltar": resaltar or {"France": ORO}, "zoom": zoom}


IMPERIO = {k: ORO for k in ("France", "Belgium", "Netherlands", "Luxembourg", "Italy", "Germany", "Poland",
                            "Switzerland", "Slovenia", "Croatia", "Spain", "Austria", "Czechia")}
IMPERIO.update({"United Kingdom": ROJO, "Russia": ROJO, "Portugal": ROJO, "Sweden": AZUL})

E = {  # escenas con nombre
    # --- mapas
    "m_corcega": mapa("Córcega · 1769", (2, 16, 38.5, 46.5), lug("Ajaccio", "Génova", "Marsella", "Niza"),
                      resaltar={"France": ORO, "Italy": (200, 185, 150, 255)}),
    "m_estudios": mapa("De Córcega a Francia · 1779", (-5, 14, 40, 51.5), lug("Ajaccio", "Brienne", "París"),
                       [ruta("Ajaccio", "Marsella", "Lyon", "Brienne", color=(40, 60, 130))]),
    "m_europa": mapa("Europa · 1789", (-12, 40, 34, 62), lug("París", "Viena", "Berlín", "Moscú", "Madrid"),
                     resaltar={"France": ORO, "United Kingdom": ROJO, "Austria": AZUL, "Russia": AZUL,
                               "Spain": AZUL, "Germany": AZUL}),
    "m_tolon": mapa("Asedio de Tolón · 1793", (-2, 14, 39, 49), lug("Tolón", "París", "Marsella", izq=("Marsella",)),
                    [ruta("París", "Lyon", "Tolón")], ["Tolón"], zoom=(1.0, 1.12)),
    "m_italia": mapa("Campaña de Italia · 1796–1797", (4, 16.5, 41.5, 48.2),
                     lug("Niza", "Montenotte", "Lodi", "Milán", "Arcole", "Rivoli", "Campo Formio", izq=("Milán", "Rivoli")),
                     [ruta("Niza", "Montenotte", "Lodi", "Milán", "Rivoli", "Arcole", "Campo Formio", fin=0.85)],
                     ["Montenotte", "Lodi", "Arcole", "Rivoli"], {"France": ORO, "Austria": ROJO}),
    "m_formio": mapa("Tratado de Campo Formio · 1797", (2, 20, 40, 50), lug("Campo Formio", "Viena", "París"),
                     resaltar={"France": ORO, "Austria": ROJO, "Italy": ORO2}, zoom=(1.1, 1.0)),
    "m_egipto": mapa("Expedición a Egipto · 1798", (-2, 42, 24, 47), lug("Tolón", "Malta", "Alejandría", "El Cairo"),
                     [ruta("Tolón", (9.5, 38.5), "Malta", (24, 33.5), "Alejandría", "El Cairo", fin=0.85)],
                     ["Pirámides"], {"France": ORO, "Egypt": (215, 175, 110, 255)}),
    "m_nilo": mapa("Batalla del Nilo · 1798", (24, 38, 27, 36), lug("Abukir", "Alejandría", "Acre", "Jaffa", izq=("Alejandría",)),
                   [ruta("El Cairo", "Jaffa", "Acre", color=(160, 25, 25), ini=0.4, fin=0.9)], ["Abukir", "Acre"],
                   {"Egypt": (215, 175, 110, 255)}, zoom=(1.0, 1.1)),
    "m_regreso": mapa("Regreso a Francia · 1799", (-2, 36, 26, 50), lug("Alejandría", "Fréjus", "París"),
                      [ruta("Alejandría", (22, 34), (12, 37.5), "Fréjus", "París", color=(40, 60, 130), fin=0.85)]),
    "m_1805": mapa("Austerlitz y Trafalgar · 1805", (-12, 25, 34, 56), lug("París", "Ulm", "Viena", "Austerlitz", "Trafalgar"),
                   [ruta("París", "Ulm", "Viena", "Austerlitz")], ["Austerlitz", "Trafalgar"],
                   {"France": ORO, "Austria": ROJO, "United Kingdom": ROJO}),
    "m_trafalgar": mapa("Trafalgar · 1805", (-14, 6, 33, 47), lug("Trafalgar", "Madrid"), [], ["Trafalgar"],
                        {"Spain": ORO2, "France": ORO, "United Kingdom": ROJO}, zoom=(1.0, 1.12)),
    "m_prusia": mapa("Jena, Auerstedt y Tilsit · 1806–1807", (-2, 28, 44, 58), lug("París", "Jena", "Berlín", "Tilsit"),
                     [ruta("París", "Jena", "Berlín", "Tilsit")], ["Jena", "Tilsit"],
                     {"France": ORO, "Germany": ROJO, "Russia": ROJO}),
    "m_imperio": mapa("El Imperio en su apogeo · 1810", (-12, 40, 34, 62), lug("París", "Madrid", "Viena", "Moscú"),
                      resaltar=IMPERIO, zoom=(1.1, 1.0)),
    "m_espana": mapa("Guerra de la Independencia · 1808–1814", (-11, 6, 35, 46.5), lug("Madrid", "Bailén", "Zaragoza", "París"),
                     [ruta("París", "Zaragoza", "Madrid")], ["Bailén", "Zaragoza"],
                     {"Spain": ROJO, "France": ORO, "Portugal": ROJO}),
    "m_coalicion": mapa("La coalición contra Napoleón", (-12, 45, 34, 62), lug("París", "Londres" if False else "Viena", "Berlín", "Moscú"),
                        resaltar={"France": ORO, "United Kingdom": ROJO, "Russia": ROJO, "Austria": ROJO,
                                  "Germany": ROJO, "Sweden": ROJO}),
    "m_rusia": mapa("Invasión de Rusia · 1812", (12, 42, 47, 60), lug("Kaunas", "Vilna", "Smolensk", "Borodinó", "Moscú", izq=("Borodinó",)),
                    [ruta("Kaunas", "Vilna", "Smolensk", "Borodinó", "Moscú", fin=0.9)], ["Borodinó"],
                    {"Russia": (190, 150, 140, 255), "Belarus": (190, 150, 140, 255), "Lithuania": (190, 150, 140, 255)}),
    "m_retirada": mapa("La retirada · 1812", (12, 42, 47, 60), lug("Moscú", "Smolensk", "Berézina", "Vilna", "Kaunas"),
                       [ruta("Moscú", "Smolensk", "Berézina", "Vilna", "Kaunas", color=(40, 50, 110), fin=0.9)], ["Berézina"],
                       {"Russia": (190, 150, 140, 255), "Belarus": (190, 150, 140, 255)}),
    "m_leipzig": mapa("Leipzig · Batalla de las Naciones · 1813", (-2, 25, 44, 56), lug("Leipzig", "París"),
                      [ruta("Leipzig", "París", color=(40, 50, 110))], ["Leipzig"],
                      {"France": ORO, "Germany": ROJO, "Austria": ROJO, "Poland": ROJO}),
    "m_1814": mapa("Campaña de Francia · 1814", (-3, 13, 43, 53), lug("París", "Montmirail", "Fontainebleau", izq=("Montmirail",)),
                   [ruta((8.5, 49.5), (5.5, 49.0), "París", color=(160, 25, 25)), ruta((7.5, 47.6), (4.5, 48.2), "París")],
                   ["Montmirail"], {"France": ORO, "Germany": ROJO}),
    "m_elba": mapa("Exilio en Elba · 1814", (3, 17, 39, 49), lug("Elba", "Fontainebleau", "Ajaccio"),
                   [ruta("Fontainebleau", "Lyon", "Niza", "Elba", color=(40, 50, 110))], zoom=(1.0, 1.12)),
    "m_100dias": mapa("Los Cien Días · 1815", (0, 13, 41, 50.5), lug("Elba", "Golfe-Juan", "Grenoble", "Lyon", "París", izq=("Grenoble",)),
                      [ruta("Elba", "Golfe-Juan", "Grenoble", "Lyon", "París", fin=0.85)]),
    "m_waterloo": mapa("Waterloo · 18 de junio de 1815", (0, 9, 47.5, 53), lug("Bruselas", "Waterloo", "Ligny", "Charleroi", "París", izq=("Charleroi",)),
                       [ruta("París", "Charleroi", "Ligny", "Waterloo", fin=0.8)], ["Ligny", "Waterloo"],
                       {"France": ORO, "Belgium": (210, 180, 160, 255), "Netherlands": ROJO}, zoom=(1.0, 1.12)),
    "m_santa_elena": mapa("Rumbo a Santa Elena · 1815", (-48, 38, -26, 58), lug("Plymouth", "París", "Santa Elena"),
                          [ruta("Plymouth", (-14, 38), (-20, 15), (-14, -5), "Santa Elena", color=(40, 50, 110), fin=0.9)],
                          zoom=(1.0, 1.08)),
    "m_restos": mapa("El regreso de los restos · 1840", (-48, 38, -26, 58), lug("Santa Elena", "Cherburgo", "París"),
                     [ruta("Santa Elena", (-14, -5), (-20, 15), (-14, 38), "Cherburgo", "París", color=(160, 120, 30), fin=0.9)]),
    "m_martinica": mapa("De Martinica a París", (-75, 12, 5, 55), lug("Martinica", "París"),
                        [ruta("Martinica", (-40, 30), (-12, 44), "París", color=(120, 30, 80))], zoom=(1.0, 1.1),
                        resaltar={"France": ORO}),
    "m_polonia": mapa("Polonia repartida", (0, 38, 44, 60), lug("Varsovia", "París", "Berlín", "Viena"),
                      resaltar={"Poland": (215, 120, 120, 255), "France": ORO, "Russia": AZUL, "Austria": AZUL, "Germany": AZUL}),
    "m_austria": mapa("Alianza con Austria · 1810", (-3, 22, 42, 54), lug("Viena", "París"),
                      [ruta("Viena", "Ulm", "París", color=(120, 30, 80))], resaltar={"France": ORO, "Austria": ORO2}),
    # --- paisajes y escenas
    "corcega": {"tipo": "corcega"}, "corcega_noche": {"tipo": "corcega", "hora": "noche"},
    "familia": {"tipo": "doble", "quienes": [("hombre", "Carlo Buonaparte"), ("mujer", "Letizia Ramolino")]},
    "padre": {"tipo": "retrato", "quien": "hombre", "nombre": "Carlo Buonaparte"},
    "madre": {"tipo": "retrato", "quien": "mujer", "nombre": "Letizia Ramolino"},
    "estudio": {"tipo": "estudio"}, "estudio_mapa": {"tipo": "estudio", "mapa": "Ars Bellica"},
    "academia": {"tipo": "documento", "titulo": "École Militaire · Artillerie", "sello": True,
                 "lineas": ["Calibre de 12 · alcance 900 toesas", "Pólvora, metralla y bala rasa"]},
    "marcha": {"tipo": "marcha"}, "marcha_dia": {"tipo": "marcha", "hora": "dia", "semilla": 4},
    "marcha_noche": {"tipo": "marcha", "hora": "noche"}, "marcha_nieve": {"tipo": "marcha", "hora": "nieve"},
    "revolucion": {"tipo": "revolucion"},
    "batalla": {"tipo": "batalla"}, "batalla_dia": {"tipo": "batalla", "hora": "dia", "semilla": 3},
    "batalla_noche": {"tipo": "batalla", "hora": "noche", "semilla": 5},
    "batalla_tormenta": {"tipo": "batalla", "hora": "tormenta", "semilla": 6},
    "batalla_nieve": {"tipo": "batalla", "hora": "nieve", "semilla": 7},
    "piramides": {"tipo": "batalla", "hora": "desierto", "semilla": 2},
    "naval": {"tipo": "naval"}, "naval_dia": {"tipo": "naval", "hora": "tormenta"},
    "colina": {"tipo": "colina"}, "colina_nieve": {"tipo": "colina", "hora": "nieve"},
    "colina_tormenta": {"tipo": "colina", "hora": "tormenta"},
    "heroe": {"tipo": "heroe"}, "heroe_general": {"tipo": "heroe", "texto": "GENERAL DE BRIGADA · 1793"},
    "heroe_consul": {"tipo": "heroe", "texto": "PRIMER CÓNSUL · 1799"},
    "heroe_emperador": {"tipo": "heroe", "texto": "EMPERADOR DE LOS FRANCESES"},
    "napoleon": {"tipo": "retrato", "quien": "napoleon", "nombre": "Napoleón Bonaparte"},
    "napoleon_joven": {"tipo": "retrato", "quien": "napoleon", "nombre": "El general Bonaparte"},
    "napoleon_viejo": {"tipo": "retrato", "quien": "anciano", "nombre": "Santa Elena · 1821"},
    "consul": {"tipo": "retrato", "quien": "napoleon", "nombre": "Primer Cónsul"},
    "palacio_golpe": {"tipo": "castillo", "hora": "noche", "ancho": 0.36},
    "tullerias": {"tipo": "castillo", "hora": "atardecer", "ancho": 0.4},
    "malmaison": {"tipo": "castillo", "hora": "atardecer", "rosas": True, "ancho": 0.25},
    "malmaison_noche": {"tipo": "castillo", "hora": "noche", "rosas": True, "ancho": 0.25},
    "brumario": {"tipo": "documento", "titulo": "18 Brumaire an VIII", "firma": "Bonaparte", "giro": 2},
    "constitucion": {"tipo": "documento", "titulo": "Constitution de l'an VIII", "lineas": ["Le Premier Consul..."]},
    "banco": {"tipo": "documento", "titulo": "Banque de France · 1800", "giro": -2},
    "codigo": {"tipo": "documento", "titulo": "Code Civil des Français", "firma": "Napoléon",
               "lineas": ["Livre premier · Des personnes", "Titre I · De la jouissance..."]},
    "codigo2": {"tipo": "documento", "titulo": "Code Napoléon · 1804", "giro": 3, "semilla": 8},
    "tratado": {"tipo": "documento", "titulo": "Traité de Campo-Formio", "firma": "Bonaparte"},
    "tratado_tilsit": {"tipo": "documento", "titulo": "Traités de Tilsit · 1807", "firma": "Napoléon"},
    "boletin": {"tipo": "documento", "titulo": "Bulletin de l'Armée d'Italie", "sello": False,
                "lineas": ["Soldats ! Vous avez remporté...", "... six victoires en quinze jours"]},
    "abdicacion": {"tipo": "documento", "titulo": "Acte d'abdication · 1814", "firma": "Napoléon",
                   "lineas": ["Les puissances alliées ayant proclamé...", "l'Empereur Napoléon renonce..."]},
    "anulacion": {"tipo": "documento", "titulo": "Acte de divorce · 1809", "firma": "Napoléon", "giro": -4},
    "memorias": {"tipo": "documento", "titulo": "Mémorial de Sainte-Hélène", "sello": False, "giro": 2},
    "autopsia": {"tipo": "documento", "titulo": "Rapport d'autopsie · 1821", "sello": False,
                 "lineas": ["Estomac : ulcère cancéreux...", "Longwood, le 6 mai 1821"]},
    "coronacion": {"tipo": "coronacion"},
    "josefina": {"tipo": "retrato", "quien": "josefina", "nombre": "Joséphine de Beauharnais"},
    "josefina_emperatriz": {"tipo": "retrato", "quien": "josefina", "nombre": "La emperatriz Joséphine"},
    "pareja": {"tipo": "doble", "quienes": [("napoleon", "Napoleón"), ("mujer", "Joséphine")]},
    "pareja2": {"tipo": "doble", "quienes": [("napoleon", "Napoleón"), ("mujer", "María Luisa")]},
    "eleonore": {"tipo": "retrato", "quien": "mujer", "nombre": "Éléonore Denuelle"},
    "walewska": {"tipo": "retrato", "quien": "mujer", "nombre": "Maria Walewska"},
    "maria_luisa": {"tipo": "retrato", "quien": "maria_luisa", "nombre": "María Luisa de Austria"},
    "salon": {"tipo": "salon"},
    "carta": {"tipo": "rosa"},
    "carta2": {"tipo": "rosa", "lineas": ["Je ne t'ai pas écrit...", "mais je pense à toi", "à chaque instant.", "     — Bonaparte"]},
    "carta_polaca": {"tipo": "rosa", "lineas": ["Marie, ma douce Marie,", "ma pensée est à toi..."]},
    "cuna": {"tipo": "cuna"},
    "paris": {"tipo": "ciudad"}, "paris_noche": {"tipo": "ciudad", "hora": "noche"},
    "paris_amanecer": {"tipo": "ciudad", "hora": "amanecer"},
    "invalides": {"tipo": "ciudad", "cual": "invalides"}, "invalides_noche": {"tipo": "ciudad", "cual": "invalides", "hora": "noche"},
    "moscu": {"tipo": "moscu"},
    "elba": {"tipo": "isla", "cual": "elba"}, "elba_noche": {"tipo": "isla", "cual": "elba", "hora": "noche"},
    "santa_elena": {"tipo": "isla", "cual": "santa_elena"},
    "santa_elena_ocaso": {"tipo": "isla", "cual": "santa_elena", "hora": "atardecer", "barco": False},
    "longwood": {"tipo": "longwood"},
    "barco_noche": {"tipo": "naval", "hora": "noche", "semilla": 9},
}


def t(grande, pequeno=""):
    return {"tipo": "texto", "grande": grande, "pequeno": pequeno}


# Una entrada por párrafo: "escena[+efecto+efecto...]" o un dict de escena de texto.
# Efectos: canon, descarga, batalla, impacto, campana, latido, caballos, pluma, tambor, whoosh, fuego, viento, olas, trueno
P = [
    # 0 Introducción
    ["corcega_noche+olas", "batalla+descarga+canon", "colina+latido", "heroe+impacto",
     t("1769 – 1821", "Ajaccio · Santa Elena"), "m_imperio+tambor", "batalla_nieve+viento+canon", "napoleon+impacto"],
    # 1 Infancia
    ["m_corcega+olas", "m_corcega", t("Napoleone Buonaparte", "Napoléon Bonaparte"), "familia", "corcega",
     "corcega_noche", "estudio+pluma", "estudio_mapa+pluma", "corcega_noche+viento", "m_estudios+whoosh",
     "estudio", "academia+tambor", "marcha_dia+tambor", "napoleon_joven+impacto"],
    # 2 El joven general
    ["academia+canon", t("1785", "Oficial de artillería · 16 años"), "m_europa", "estudio", "revolucion+impacto",
     t("1789", "La Revolución francesa"), "revolucion+batalla", "marcha+tambor", "colina", "m_tolon+canon",
     "batalla_noche+batalla", "heroe_general+impacto", "napoleon_joven", "marcha_dia", "colina+tambor",
     "m_italia+whoosh"],
    # 3 Italia y Egipto
    ["m_italia+tambor", "marcha_noche", "estudio_mapa", "batalla_dia+batalla", "marcha+tambor", "heroe+impacto",
     "boletin+pluma", "tratado+pluma", "paris", "colina", "m_egipto+whoosh", "piramides+batalla",
     "naval+batalla", "m_nilo+canon", "m_nilo+descarga", "piramides+viento", "napoleon", "m_regreso+olas",
     "paris_noche+latido", "colina_tormenta+impacto"],
    # 4 El golpe
    ["palacio_golpe+latido", "brumario+impacto", "heroe_consul+impacto", "consul", "paris", "revolucion",
     "constitucion+pluma", "banco+pluma", "codigo+pluma", "codigo2", t("Igualdad", "...pero no para todos"),
     "salon", "codigo", t("1802", "Cónsul vitalicio"), "paris_amanecer+whoosh", "coronacion+campana",
     "coronacion+campana", "heroe_emperador+impacto", "colina_tormenta+latido"],
    # 5 Joséphine
    ["salon", "josefina", "m_martinica+olas", "revolucion", "salon", "napoleon_joven", t("9 de marzo de 1796", "La boda"),
     "pareja", "m_italia+caballos", "carta+pluma", "malmaison_noche", "salon", "carta2+pluma", "josefina",
     "pareja", "josefina_emperatriz", "malmaison", "malmaison_noche+latido", "cuna", "josefina", "josefina_emperatriz",
     "napoleon+latido", "pareja+latido"],
    # 6 Otras mujeres
    ["salon", "carta+pluma", "eleonore", t("1806", "Nace Charles Léon"), "cuna", "walewska", "m_polonia",
     "m_polonia+tambor", t("1810", "Nace Alexandre Walewski"), "walewska", "pareja", "carta_polaca+pluma",
     "napoleon", "malmaison_noche+latido"],
    # 7 Divorcio y María Luisa
    [t("1809", "La separación"), "anulacion+pluma", "malmaison_noche", "josefina_emperatriz", "pareja",
     "malmaison", "tullerias", "maria_luisa+campana", "m_austria", "m_austria", t("1810", "Segunda boda"),
     "pareja2", "tullerias+campana", "cuna+campana", t("El rey de Roma", "Heredero del Imperio"),
     "paris_noche+canon", "heroe_emperador", "tullerias", "m_coalicion+tambor", "batalla_nieve+impacto"],
    # 8 Grandes victorias
    ["marcha+tambor", "m_1805+batalla", "naval_dia+batalla", "m_trafalgar+canon", "colina+tambor",
     "m_prusia+batalla", "m_imperio+tambor", "tullerias", "batalla_tormenta+latido", "revolucion+batalla",
     "estudio_mapa", "marcha_noche+tambor", "m_espana+whoosh", t("1808", "José Bonaparte, rey de España"),
     "batalla_noche+batalla", "batalla+descarga+canon", "marcha_noche", "m_coalicion", "m_imperio",
     "batalla_tormenta+canon"],
    # 9 Rusia
    [t("1812", "La invasión de Rusia"), "m_europa", "marcha+tambor", "m_rusia+tambor", "colina",
     "marcha_dia", "marcha_noche+fuego", "batalla+batalla+descarga+canon", "batalla_dia+batalla", "m_rusia+caballos",
     "moscu+fuego", "colina_tormenta", "moscu+fuego+canon", "colina_nieve+viento", "m_retirada+viento",
     "marcha_nieve+viento", "batalla_nieve+viento+descarga", "marcha_nieve+viento",
     t("Cientos de miles", "de soldados perdidos"), "marcha_nieve+viento", "m_coalicion", "napoleon",
     "m_coalicion+tambor", "heroe", "colina_nieve+viento", "batalla_nieve+impacto"],
    # 10 Abdicación y Elba
    ["m_leipzig+batalla+canon", "batalla_tormenta+batalla", "m_1814+tambor", "paris_noche+latido",
     "batalla_dia+batalla", "palacio_golpe", "abdicacion+pluma+impacto", "m_elba+olas", "tullerias",
     "elba+olas", "elba_noche", "elba+olas", "malmaison_noche", t("29 de mayo de 1814", "Muere Joséphine"),
     "josefina", "carta+latido", "coronacion", "elba_noche+olas", "elba_noche+impacto"],
    # 11 Cien Días y Waterloo
    ["m_100dias+olas", "barco_noche", "marcha+tambor", "paris_noche", "tullerias", t("100 días", "1815"),
     "m_coalicion+tambor", "marcha_noche+tambor", "colina+latido", "m_waterloo+caballos",
     t("18 de junio de 1815", "Waterloo"), "batalla_tormenta+batalla+descarga+canon", "colina_tormenta+latido",
     "batalla_tormenta+batalla+caballos+canon", "batalla_nieve+impacto", "colina_tormenta+viento",
     "abdicacion+pluma", "napoleon+latido", "m_santa_elena+olas", "santa_elena+olas",
     t("Santa Elena", "Atlántico Sur")],
    # 12 Familia y soledad
    ["napoleon_viejo", "maria_luisa", "m_austria", "cuna", "m_austria", t("1832", "Muere el duque de Reichstadt"),
     "pareja2", "josefina", "malmaison_noche", "carta", "carta_polaca", "longwood+viento", "napoleon_viejo",
     "santa_elena+olas"],
    # 13 Santa Elena
    ["m_santa_elena+olas", "santa_elena+olas", "barco_noche+olas", "santa_elena+viento", "longwood+viento",
     "longwood", "memorias+pluma", "napoleon_viejo", "revolucion", "batalla_tormenta+canon", "colina_tormenta",
     "longwood+viento+latido", t("5 de mayo de 1821", "Muere Napoleón Bonaparte"), "autopsia+pluma",
     "santa_elena_ocaso+olas", "invalides+campana"],
    # 14 Legado
    ["heroe", "batalla+descarga", "codigo+pluma", "codigo2", "paris", "marcha_dia+tambor", "batalla_tormenta+canon",
     "m_imperio", "m_espana", "revolucion", "paris_amanecer", "m_restos+olas", "invalides+campana", "estudio",
     "napoleon"],
    # 15 Final
    ["corcega+olas", "m_imperio", "coronacion", "carta", "pareja", "colina+tambor", "marcha_nieve+viento",
     "batalla_tormenta+canon", "santa_elena_ocaso+olas", "colina", "heroe", "invalides", "santa_elena_ocaso",
     "heroe+impacto", "napoleon+impacto"],
]

# Estado de ánimo de la música: por capítulo, lista de (desde_párrafo, estado)
MUSICA = [
    [(0, "epico")], [(0, "romantico")], [(0, "marcha"), (5, "tension"), (9, "epico")], [(0, "epico"), (10, "misterio"), (17, "tension")],
    [(0, "tension"), (13, "majestuoso")], [(0, "romantico")], [(0, "misterio")],
    [(0, "triste"), (6, "majestuoso"), (17, "tension")], [(0, "epico"), (8, "tension"), (12, "marcha")],
    [(0, "marcha"), (5, "tension"), (13, "frio")], [(0, "tension"), (6, "triste")],
    [(0, "marcha"), (6, "epico"), (14, "triste")], [(0, "triste")], [(0, "frio"), (7, "triste")],
    [(0, "majestuoso")], [(0, "triste"), (9, "epico")],
]

# Nombres que aparecen en un rótulo la primera vez que se mencionan
ROTULOS = {
    "Carlo Buonaparte": "Padre de Napoleón", "Letizia Ramolino": "Madre de Napoleón",
    "Horatio Nelson": "Almirante británico", "Joséphine de Beauharnais": "Primera esposa",
    "Éléonore Denuelle": "Madre de Charles Léon", "Maria Walewska": "Aristócrata polaca",
    "María Luisa de Austria": "Segunda esposa · Emperatriz", "Alejandro Primero": "Zar de Rusia",
    "Luis XVIII": "Rey de Francia", "Wellington": "Duque · Ejército aliado",
    "Blücher": "Mariscal prusiano",
}
