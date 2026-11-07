# Italia — documental para YouTube (Giga Curiosidades del Mundo)

Documental de ~18 minutos montado a partir de tres narraciones grabadas en ElevenLabs:
imágenes reales de Wikimedia Commons (licencias libres), música y efectos generados con código
(sin copyright), apertura épica con la bandera de Italia ondeando y la marca
**GIGA CURIOSIDADES DEL MUNDO** arriba a la derecha durante todo el video.

## Cómo generarlo

```bash
python3 1_imagenes.py salida                                   # busca y descarga ~200 imágenes
python3 2_montaje.py salida audio1.mp3 audio2.mp3 audio3.mp3   # audio + video 1080p (~30 min)
# prueba rápida de un tramo:  python3 2_montaje.py salida a1.mp3 a2.mp3 a3.mp3 --prueba 0 30
# cambiar una imagen:          python3 1_imagenes.py salida "0_012=nueva búsqueda"
```

Los audios van en el orden en que se pasan. Resultado en `salida/`: `Italia_documental.mp4`,
`descripcion_youtube.txt` (capítulos con su minuto + créditos de las imágenes) y `creditos.txt`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `plan.py` | Qué imagen va en cada segundo de cada audio, capítulos y música |
| `1_imagenes.py` | Busca en Wikimedia Commons y descarga (solo licencias libres) |
| `2_montaje.py` | Apertura, bandera, rótulos, movimiento de cámara, mezcla de audio y render |
| `sonido.py` | Música y efectos sintetizados (copiado del proyecto de Napoleón) |
| `fuentes/` | Cinzel y Montserrat (licencia OFL) |

Las imágenes con licencia CC BY / CC BY-SA piden mencionar al autor: pega
`descripcion_youtube.txt` en la descripción del video.
