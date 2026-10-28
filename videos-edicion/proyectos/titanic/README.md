# Titanic — video corto para TikTok, Instagram y YouTube

Video de ~61 s con voz en off (ElevenLabs, voz «Daniel», modelo eleven_v4), las 13 imágenes
de `imagenes/` (el collage se recorta en 6), subtítulos sincronizados, etiquetas de fecha,
música y efectos sintetizados.

## Cómo generarlo

1. Guarda la narración como `salida/voz.mp3` (no se sube al repositorio).
   Si cambias la voz, actualiza los tiempos de `FRASES` en `montaje.py`
   (se miden con `ffmpeg -i salida/voz.mp3 -af silencedetect=n=-38dB:d=0.15 -f null -`).
2. Ejecuta:

```bash
python3 montaje.py                # los tres formatos
python3 montaje.py vertical       # solo uno: vertical | horizontal | feed
```

## Resultado (en `../../exportados/`)

| Archivo | Para |
|---|---|
| `Titanic_TikTok_Reels_Shorts_1080x1920.mp4` | TikTok, Instagram Reels, YouTube Shorts (9:16) |
| `Titanic_YouTube_1920x1080.mp4` | YouTube normal (16:9) |
| `Titanic_Instagram_Feed_1080x1350.mp4` | Publicación del feed de Instagram (4:5) |

## Orden de las imágenes

| Tiempo | Imagen | Narración |
|---|---|---|
| 0–5 s | collage 1 (atardecer) | Gancho: «uno de los barcos más impresionantes…» |
| 5–10 s | collage 4 (hundimiento) | «…una de las mayores tragedias» |
| 10–13 s | puerto_southampton (real) | 10 de abril de 1912 |
| 13–16 s | collage 2 (despedida en el puerto) | Rumbo a Nueva York |
| 16–19 s | navegando_1912 (real) | Más de 2.200 personas |
| 19–21 s | luna_iceberg | Noche del 14 de abril |
| 21–28 s | collage 3 (iceberg) | El choque |
| 28–31 s | botes_niebla | El agua inunda el barco |
| 31–35 s | collage 5 (bote con farol) | Botes insuficientes |
| 35–43 s | hundimiento_pintura | 15 de abril, +1.500 vidas |
| 43–48 s | collage 6 (restos con submarino) | Restos ocultos |
| 48–54 s | restos_proa_real (real) | Descubiertos en 1985 |
| 54–61 s | collage 1 (cierre) | ¿Conocías esta historia? Síguenos |
