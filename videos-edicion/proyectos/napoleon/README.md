# Napoleón Bonaparte — documental para YouTube

Genera un documental de ~40 minutos a partir de `guion.txt`, sin usar material externo:
voz en off sintetizada, música y efectos (disparos, cañones, tambores, campanas, viento, olas…)
generados con código, escenas animadas con siluetas, mapas de las campañas y subtítulos.

## Cómo generarlo

En las sesiones de Claude Code en la nube todo se instala solo al empezar
(`.claude/hooks/session-start.sh`): ffmpeg, las librerías y los modelos de voz en `videos-edicion/modelos/`.
En tu computadora:

```bash
pip install -r requirements.txt
mkdir -p ../../modelos
curl -L -o ../../modelos/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o ../../modelos/voices-v1.0.bin  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

python3 1_voz.py ../../modelos salida                               # narración (≈30 min de CPU)
python3 2_montaje.py salida --modelos ../../modelos --procesos 4    # audio + video (≈1,5 h)
# prueba rápida de un tramo:  python3 2_montaje.py salida --prueba 0 40
```

Resultado en `salida/`: `Napoleon_Bonaparte_documental.mp4`, `napoleon.srt` (subtítulos) y
`capitulos.txt` (marcas de tiempo para la descripción de YouTube).

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion.txt` | El guion completo |
| `guion.py` | Lee el guion y ajusta la pronunciación de nombres franceses |
| `plan.py` | Escena, efectos de sonido y música de cada párrafo |
| `escenas.py` | Dibujo de escenas, siluetas y mapas |
| `sonido.py` | Efectos de sonido y música sintetizados |
| `fuentes/` | Tipografías Cinzel, EB Garamond e IM Fell (licencia OFL) |
