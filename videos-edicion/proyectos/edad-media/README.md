# La Edad Media: la verdad detrás de los castillos — documental (Curiosidades del Mundo)

Documental de ~23 minutos con la narración de ElevenLabs (voz "Ludovico"), las ~100 imágenes de los
collages separadas una por una y ampliadas a HD con Real-ESRGAN, escenas propias (línea de tiempo animada
y un duelo de caballeros en silueta), ráfagas de combate y sonido medieval sintetizado (espadas, cuernos,
tambores, ejército, flechas, asedio, mercado, herrería, campanas).

## Cómo generarlo

```bash
python3 recortar.py                 # separa y amplía las imágenes (~40 min con Real-ESRGAN en CPU)
# narración: salida/voz/cap0.mp3 … cap11.mp3 (identificadores de ElevenLabs en voz_elevenlabs.txt)
python3 montaje.py --procesos 4     # video + audio (~45 min)
python3 alinear.py                  # subtítulos sincronizados con la voz real
python3 partir.py                   # subtítulos grabados y clips de ~1 minuto
# revisar una sola parte:  python3 montaje.py --prueba 4
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion.txt` | Texto narrado (introducción, 10 capítulos y conclusión) |
| `originales/` | Collages y fotos tal como llegaron |
| `recortar.py` | Separa cada collage en imágenes y las amplía con superresolución |
| `montaje.py` | Orden de las escenas, efectos, escenas propias, mezcla y subtítulos |
| `sonido_medieval.py` | Efectos de sonido medievales sintetizados |
| `alinear.py` | Sincroniza cada subtítulo con la voz real (DTW contra una lectura de referencia con Kokoro) |
| `partir.py` | Graba los subtítulos y parte el video en clips de ~1 minuto |
