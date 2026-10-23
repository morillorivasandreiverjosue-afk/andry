# Pompeya: la ciudad que desapareció — Reel / TikTok (9:16, ~64 s)

Video vertical para **CURIOSIDADES DEL MUNDO**: 12 escenas sacadas de `referencia.jpg` y ampliadas a HD,
voz en off, música de suspenso y efectos sintetizados, y subtítulos grandes con palabras clave en amarillo.

## Cómo generarlo

```bash
python3 0_escenas.py ../../modelos salida   # separa y amplía las 12 escenas (≈8 min)
python3 1_voz.py     ../../modelos salida   # narración con Kokoro (≈1 min)
# o, con una narración de ElevenLabs (voz «Damián», eleven_v4) y su transcripción con tiempos por palabra:
# ffmpeg -i toma.mp3 -af atempo=1.12 narracion.mp3
# python3 1_voz_elevenlabs.py narracion.mp3 palabras.json salida
python3 2_montaje.py salida                 # audio + video (≈7 min)
# prueba rápida de un tramo:  python3 2_montaje.py salida --prueba 16 34
```

Para la ampliación con IA hace falta `pip install opencv-contrib-python-headless` y el modelo
`../../modelos/EDSR_x4.pb` (<https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x4.pb>).
Si no está, `0_escenas.py` amplía con Lanczos.

Resultado en `salida/`: `Pompeya_Curiosidades_del_Mundo.mp4` (1080×1920, 30 fps, −14 LUFS) y `pompeya.srt`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion.py` | Guion por escenas; `\|` separa los fragmentos de subtítulo y `*palabra*` se resalta en amarillo |
| `0_escenas.py` | Recorta la cuadrícula 3×4 de `referencia.jpg` y amplía cada imagen ×4 |
| `1_voz.py` | Voz en off frase por frase (Kokoro, sin conexión) |
| `1_voz_elevenlabs.py` | Corta una narración completa de ElevenLabs en frases y sincroniza cada subtítulo con su palabra |
| `2_montaje.py` | Movimientos de cámara, transiciones, ceniza y piedra pómez, nube oscura, subtítulos, marca del canal, música y efectos (usa `../napoleon/sonido.py`) |
| `portada.py` | Portada vertical para TikTok, Reels y Shorts (`salida/portada.jpg`) |
| `fuentes/` | Montserrat, Anton y Cinzel (licencia OFL) |

## Zona segura de los textos

- Subtítulos centrados en y≈1300, ancho máximo 820 px: quedan por encima de la descripción y fuera de la
  columna de botones de TikTok/Instagram.
- Marca del canal arriba (y≈230), debajo de la barra superior de la app.
