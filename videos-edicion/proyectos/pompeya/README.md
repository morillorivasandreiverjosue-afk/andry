# Pompeya — documental para YouTube (Curiosidades del Mundo)

Video de ~9 minutos a partir de `guion.txt`, con la narración de ElevenLabs (voz "Damián"),
las 16 imágenes del collage, un mapa animado del golfo de Nápoles, datos curiosos en pantalla,
escenas de acción en la erupción (temblor de cámara, ceniza, brasas, destellos) y música y
efectos sintetizados (se reutiliza `../napoleon/sonido.py`).

## Cómo generarlo

```bash
python3 recortar.py collage.webp salida        # recorta las 16 imágenes y borra las marcas de tiempo
# copia la narración de ElevenLabs como salida/voz/cap1.mp3 … cap9.mp3 (un archivo por capítulo)
python3 montaje.py salida --procesos 4          # video + audio (~15 min de CPU)
# revisar un solo capítulo:  python3 montaje.py salida --prueba 2
python3 partir.py salida                        # subtítulos grabados + un video por capítulo
```

Resultado en `salida/`: `Pompeya_documental.mp4`, `pompeya.srt` (subtítulos) y
`capitulos.txt` (marcas de tiempo para la descripción de YouTube). `partir.py` añade
`Pompeya_subtitulado.mp4` y la carpeta `por_capitulos/` con las 9 partes.

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion.txt` | El texto narrado, por capítulos |
| `recortar.py` | Separa las imágenes del collage y tapa la marca de tiempo de cada una |
| `montaje.py` | Escenas, mapa, efectos, datos curiosos, mezcla de audio y subtítulos |
| `partir.py` | Graba los subtítulos en la imagen y parte el video por capítulos |
