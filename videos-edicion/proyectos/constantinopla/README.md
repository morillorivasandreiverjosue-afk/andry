# La caída de Constantinopla — 1453 (Curiosidades del Mundo)

Video vertical de 60 segundos (1080×1920, 9:16) para Instagram Reels y TikTok:
narración en español latino, subtítulos grandes, imágenes con movimiento de cámara,
música épica y efectos (viento, cañones, campana, golpes) generados con código.

## Cómo generarlo

```bash
python3 1_voz.py ../../modelos salida 1.3        # narración con Kokoro (≈1 min)
python3 2_montaje.py salida --procesos 4         # audio + video (≈5 min)
# vista previa rápida de algunos cuadros:  python3 2_montaje.py salida --cuadros 14
```

Resultado en `salida/`: `Caida_de_Constantinopla.mp4` y `constantinopla.srt`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion.py` | Texto de cada escena, cortes de subtítulos (`|`), imágenes y música |
| `1_voz.py` | Narración frase por frase (voz `em_alex`, `es-419`) |
| `2_montaje.py` | Montaje vertical, mapa añadido, subtítulos, cierre y mezcla de audio |
| `imagenes/` | Ilustraciones usadas (recreaciones artísticas, no fotografías) |

Reutiliza `../napoleon/sonido.py` (música y efectos) y `../napoleon/fuentes/` (tipografías).
