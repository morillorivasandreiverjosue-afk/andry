# El desastre del Hindenburg: video para TikTok

Video vertical (1080×1920) de unos 92 segundos con las fotos de `imagenes/`, voz en off de ElevenLabs
(voz de Daniel, ver `CLAUDE.md`), música y efectos del documental de Napoleón (fuego, golpes, latido),
textos clave arriba y subtítulos grandes al estilo TikTok sincronizados con la voz.

## Cómo generarlo

```bash
# 1. narración: genera voz_elevenlabs.txt en ElevenLabs y guárdala como salida/voz.mp3
python3 alinear.py salida    # tiempos por palabra a partir de las pausas de la voz
python3 montaje.py salida    # salida/Hindenburg_TikTok.mp4 y salida/hindenburg.srt
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `voz_elevenlabs.txt` | Texto de la narración, con las etiquetas de tono |
| `imagenes/` | `1.jpg` comedor · `2.jpg` en tierra · `3.jpg` restos · `4.jpg` incendio · `5.jpg` sobre el público |
| `alinear.py` | Alinea el texto con las pausas del audio (sin transcribir) y reparte las palabras por sílabas |
| `montaje.py` | Imágenes de cada párrafo, carteles, música, subtítulos y render del video |
