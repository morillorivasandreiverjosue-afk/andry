# 11 de septiembre — documental (Curiosidades del Mundo)

Documental de ~14 minutos a partir de la narración de ElevenLabs (3 audios), con material
de archivo real (NIST, Pentágono, Casa Blanca, Wikimedia Commons) y los 2 clips que aportó el autor.

Qué hace cada paso (todo se ejecuta con una carpeta de trabajo `S` que contiene `audio/`, `media/`, `ref/`, `fonts/`):

| Script | Qué hace |
|---|---|
| `transcribe.py` | Transcribe la narración con marcas de tiempo por palabra (faster-whisper) |
| `cuts.py` | Encuentra "Introducción", "Capítulo N" y "Conclusión" y calcula dónde cortar |
| `narr.py` | Arma la narración sin esas palabras y deja una pausa para la tarjeta del capítulo |
| `musica.py` | Música de fondo por capítulo + golpes/whoosh en cada título (usa `../napoleon/sonido.py`) |
| `graficos.py` | Logo "CURIOSIDADES DEL MUNDO", tarjetas de capítulo, rótulos con horas y cifras |
| `shots.py` | Guion visual: qué video/foto va en cada segundo |
| `render.py` | Renderiza cada plano (zoom lento, color, grano, viñeta) y monta el video final |
| `fetch.py`, `guess.py` | Descarga del material de Wikimedia Commons |

`cortes_capitulos.json` tiene los cortes exactos (en segundos de cada audio original).
`creditos.txt` lista el origen y la licencia del material de archivo.
