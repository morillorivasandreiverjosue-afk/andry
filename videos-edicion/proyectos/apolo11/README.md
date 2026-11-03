# El día que el ser humano llegó a la Luna — documental del Apolo 11

Documental de ~19 minutos en 1080p, hecho con la narración grabada en ElevenLabs, fotos de la NASA
(dominio público), música de suspenso y efectos generados con código (sin copyright).

## Qué lleva el video

- Apertura con cuenta regresiva (T−10 … T−00), cortes rápidos y rugido del Saturno V.
- Pantalla tipo cabina: esquinas de visor, reloj de misión (MET), fecha, y en el descenso la altitud y el
  combustible bajando hasta el aterrizaje.
- Tarjetas de capítulo con texto tipo terminal, pitidos de radio de la NASA (tonos Quindar) y estática.
- Rótulos con nombre (Armstrong, Aldrin, Collins, Gagarin, Columbia, Eagle…).
- Subtítulos sincronizados palabra por palabra con la voz.

## Cómo generarlo

```bash
# 1. narración: los audios de ElevenLabs en audios/ (parte1, parte2, parte3, recibido4) unidos en narracion.wav
# 2. fotos de dominio público
python3 descargar_imagenes.py imagenes            # (se puede lanzar otro a la vez con: imagenes inverso)
# 3. sincronizar el guion con la voz (Whisper sin internet, modelo en ../../modelos/whisper)
python3 transcribir.py narracion.wav ../../modelos/whisper/sherpa-onnx-whisper-base salida
python3 alinear.py salida
# 4. montaje (prueba rápida: --prueba 640 40)
python3 montaje.py salida --procesos 4
```

Resultado en `salida/`: `Apolo11_documental.mp4`, `apolo11.srt`, `capitulos.txt` (para la descripción de
YouTube) y `creditos_imagenes.txt` (origen y licencia de cada foto).

## Archivos

| Archivo | Qué hace |
|---|---|
| `guion_original.txt` | El guion que lee la narración |
| `narracion_elevenlabs.txt` | Versión pulida del guion, dividida en partes para ElevenLabs |
| `descargar_imagenes.py` | Descarga fotos de Wikimedia Commons, solo de dominio público |
| `transcribir.py` / `alinear.py` | Sincronizan el texto con el audio |
| `plan.py` | Qué foto, música y efecto va con cada frase y capítulo |
| `sonido_espacio.py` | Música de suspenso y efectos (radio, cohete, alarma) |
| `montaje.py` | Línea de tiempo, mezcla de audio y render del video |
