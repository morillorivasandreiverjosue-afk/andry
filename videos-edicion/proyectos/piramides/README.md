# Las pirámides de Egipto: video para TikTok

Video vertical (1080×1920) de unos 70 segundos, hecho a partir de `guion.txt` y las fotos de `imagenes/`.
Lleva voz en off sintetizada, música y efectos (los del documental de Napoleón), subtítulos grandes al estilo
TikTok y un movimiento de cámara suave sobre cada imagen.

## Cómo generarlo

Necesita lo mismo que el documental de Napoleón (`../napoleon/requirements.txt`), los modelos de voz en
`../../modelos/` y el modelo para mejorar imágenes:

```bash
curl -L -o ../../modelos/RealESRGAN_x4plus.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth

OPENBLAS_NUM_THREADS=1 python3 0_imagenes.py ../../modelos salida   # mejora las imágenes con IA (≈20-30 min de CPU)
python3 1_voz.py ../../modelos salida                                # narración (≈1 min)
python3 2_montaje.py salida                                          # video final (≈5 min)
```

Resultado en `salida/`: `Piramides_de_Egipto_TikTok.mp4` y `piramides.srt`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion.txt` | El guion |
| `imagenes/` | Las fotos originales (`3.jpg` es un collage de 8 que se corta automáticamente) |
| `esrgan.py` | Real-ESRGAN x4 hecho con numpy: amplía las imágenes 4 veces sin necesitar PyTorch |
| `0_imagenes.py` | Corta el collage y mejora todas las imágenes |
| `1_voz.py` | Genera la voz frase por frase |
| `2_montaje.py` | Qué imagen va con cada párrafo, música, subtítulos y render del video |
