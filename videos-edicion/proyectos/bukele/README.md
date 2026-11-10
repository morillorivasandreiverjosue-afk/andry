# Nayib Bukele — documental para YouTube (Curiosidades del Mundo)

Documental de unos 34 minutos montado sobre la narración grabada con ElevenLabs.
Estilo cinematográfico propio: fotos y videos de archivo con movimiento lento de cámara,
color con sombras frías y luces cálidas, grano suave, fundidos discretos, fechas en pantalla,
rótulos de capítulo sobre negro, mapas y cifras animadas, y el sello
**CURIOSIDADES DEL MUNDO** con su rayita roja arriba a la derecha (sin planeta).

La voz **no dice** "Capítulo 1", "Capítulo 2"…: esas palabras se quitan del audio y el
número del capítulo solo aparece en pantalla junto con su título.

## Cómo generarlo

1. Copia las 4 partes de la voz en `audio/` como `parte1.mp3` … `parte4.mp3` (en orden).
2. Ejecuta:

```bash
python3 transcribir.py audio/parte*.wav   # solo si cambias la voz (ver abajo)
python3 1_voz.py                          # une las partes y quita "Capítulo N"
python3 commons.py bajar ...              # (automático con la lista de plan.py, ver abajo)
python3 2_montaje.py --prueba 380 60      # prueba de 1 minuto
python3 2_montaje.py                      # documental completo (≈1 h con 4 procesos)
```

Para descargar todo el material que usa el plan:

```bash
python3 -c "import plan, commons; commons.bajar(['File:' + a for a in plan.archivos()])"
```

Resultado en `salida/`:

| Archivo | Para qué |
|---|---|
| `Nayib_Bukele_documental.mp4` | El video final (1920×1080, 24 fps) |
| `capitulos.txt` | Marcas de tiempo para la descripción de YouTube |
| `bukele.srt` | Subtítulos (se suben aparte a YouTube) |
| `creditos.txt` | Créditos del material de archivo, para la descripción |

## Archivos

| Archivo | Qué hace |
|---|---|
| `transcripcion/` | Frases de la voz con sus tiempos (Whisper, local) |
| `1_voz.py` | Une las partes, quita "Capítulo N" y deja una pausa antes de cada título |
| `plan.py` | Qué foto, video, mapa o cifra aparece en cada frase, y las fechas en pantalla |
| `commons.py` | Busca y descarga material libre de Wikimedia Commons y Openverse (Flickr) |
| `2_montaje.py` | Monta imagen, rótulos, música y mezcla final |
| `fuentes/` | Oswald y Montserrat (licencia OFL) |
| `datos/` | Fronteras de Natural Earth (dominio público) para los mapas |

## Material y licencias

Solo se usa material con licencia libre: dominio público, CC0, CC BY y CC BY-SA
(nada "no comercial" ni "sin derivadas"). Las fotos con licencia CC BY / BY-SA muestran su
autor abajo a la derecha, y `salida/creditos.txt` trae la lista completa para la
descripción del video. La música y los efectos se generan con código (`../napoleon/sonido.py`).
