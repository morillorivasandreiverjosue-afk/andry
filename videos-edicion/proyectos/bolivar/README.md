# Documental: Simón Bolívar, la historia del Libertador de América

Video 1920x1080 (YouTube), estilo documental, con narrador, subtítulos, mapas animados,
ilustraciones, tarjetas de capítulo y música de fondo. Todo se genera desde `guion.txt`.

## Cómo regenerarlo

```bash
pip install piper-tts pyshp pillow numpy      # y tener FFmpeg instalado
cd proyectos/bolivar

# Voz del narrador (una sola vez)
mkdir -p voz && curl -L -o voz.tgz https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-es-carlfm-x-low.tar.gz
tar xzf voz.tgz -C voz && rm voz.tgz

python3 narracion.py --voz voz/es-carlfm-x-low.onnx   # 1) voz + línea de tiempo
python3 render.py                                     # 2) ilustraciones, mapas y video final
```

El resultado queda en `exportados/simon-bolivar-documental.mp4`.

## Cómo cambiarlo

- **Texto**: edita `guion.txt`. `## Título` crea un capítulo y `@nombre` elige la imagen
  que se ve desde ese párrafo (por ejemplo `@andes`, `@batalla`, `@mapa_admirable`).
- **Usar imágenes reales** (pinturas, grabados): guarda la imagen en `imagenes/` con el mismo
  nombre que la escena (por ejemplo `imagenes/retrato.jpg`), borra `build/img/retrato.png`
  y vuelve a ejecutar `render.py` (borra también `build/seg/` para regenerar los tramos).
- **Velocidad del narrador**: `--velocidad 1.2` en `narracion.py` (más alto = más lento).
- **Prueba rápida**: `python3 render.py --vista 125` guarda una imagen del segundo 125.

Los mapas usan datos de Natural Earth (dominio público), en `datos/`.
