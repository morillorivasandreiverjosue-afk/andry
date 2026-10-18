# El Esequibo — video para TikTok (60 s)

Video vertical 1080×1920 para «Curiosidades del Mundo»: narración con voz venezolana
(ElevenLabs, voz «José Manuel»), mapas reales (Natural Earth), recreaciones de 1899 y 1966,
petróleo, la Corte Internacional de Justicia, música y efectos sintetizados y subtítulos.

```bash
# salida/voz_tiktok.wav = narración de ElevenLabs ralentizada un 6 %
python3 audio.py                     # música + efectos + voz → salida/mezcla.wav
python3 montaje.py --procesos 4      # → salida/Esequibo_TikTok.mp4 y salida/esequibo.srt
# prueba rápida de un tramo:  python3 montaje.py --prueba 18 26
```

| Archivo | Qué hace |
|---|---|
| `guion.py` | Texto, tiempos de cada frase y subtítulos |
| `mapa.py` | Mapas con relieve y capas: fronteras, zona en reclamación, río Esequibo |
| `escenas.py` | Los 16 planos del video |
| `audio.py` | Beat, efectos y mezcla con la voz |
| `montaje.py` | Render de los cuadros, subtítulos y unión con ffmpeg |
| `datos/` | Recortes de Natural Earth 1:10m (dominio público) |

La zona en reclamación se muestra como reclamación (rayado rojo), distinta de la frontera
administrada hoy (línea del laudo de 1899).
