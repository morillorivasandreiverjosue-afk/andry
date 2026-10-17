# El primer automóvil de la historia — reel para «Curiosidades del Mundo»

Reel vertical 9:16 (1080 × 1920, 30 fps, ~53 s) sobre el Benz Patent-Motorwagen de Karl Benz (patente
n.º 37435, 1886), listo para TikTok, Instagram Reels y YouTube Shorts.

- **Voz:** narración en español latinoamericano generada con ElevenLabs (voz «Jorge», grave y documental).
- **Subtítulos:** grandes, sincronizados palabra por palabra (tiempos en `palabras.json`) y con palabras clave en dorado.
- **Imágenes:** fotos e ilustraciones históricas de Wikimedia Commons con movimientos de cámara suaves y fundidos.
  Las réplicas de museo llevan el rótulo «Réplica».
- **Audio:** música de suspenso documental sintetizada en `montaje.py` (cuerdas, bajo, piano y timbal),
  que baja sola cuando habla la voz; efectos de motor antiguo (ElevenLabs) y barridos de transición.
  Volumen final normalizado a −14 LUFS.
- **Cierre:** «CURIOSIDADES DEL MUNDO».

## Cómo generarlo

```bash
python3 descargar_imagenes.py imagenes.txt     # dentro de material/img (fotos de Wikimedia Commons)
python3 montaje.py                             # → ../../exportados/primer_automovil_reel.mp4 (+ .srt)
python3 montaje.py --prueba 10 20              # prueba rápida de un tramo
```

`material/` (gitignored) necesita `voz.wav`, `motor1.wav` y `motor2.wav` a 48 kHz y las imágenes en `img/`.

## Datos usados (verificados)

- Karl Benz solicitó la patente DRP n.º 37435 el 29 de enero de 1886 (Mannheim).
- Tres ruedas, motor de gasolina de cuatro tiempos y un cilindro (~954 cm³, ~0,75 CV).
- Velocidad máxima: unos 16 km/h.

## Créditos de las imágenes (Wikimedia Commons)

| Archivo | Imagen en Commons | Rótulo en el vídeo |
|---|---|---|
| 00 | Benz-Patent-Motorwagen - Illustrirte Zeitung 1888.jpg (dominio público) | Ilustración de 1888 |
| 02 | Carl Benz c. 1889.jpg | Karl Benz, hacia 1889 |
| 05 | Benz 37435.jpg | Patente n.º 37435 · 1886 |
| 07 | Patent-Motorwagen Nr.1 Benz 2.jpg | Benz Patent-Motorwagen |
| 08 | Benz Patent Motorwagen 1886.jpg | — |
| 09 | Benz Patent-Motorwagen 1886 Modell 1 Engine SATM 05June2013 (14414242307).jpg | Motor de un cilindro |
| 10 | Verkehrsmuseum Dresden Replika Benz-Patent-Motorwagen von 1886 Detail Motor IX.jpg | Réplica · Verkehrsmuseum Dresden |
| 13 | Benz Patent-Motorwagen 1886 Light Wood Black Rims LRear MBMuse 9June2013 (14980476431).jpg | Réplica · Museo Mercedes-Benz |
| 14 | Benz Patent-Motorwagen 1886 Modell 1 RSideRear SATM 05June2013 (14414018410).jpg | — |
| 15 | 1886 Benz Patent Motorwagen (29744182207).jpg | Patent-Motorwagen · modelo 1886 |
| 16 | Karl Benz Automobile.jpg | Un Benz posterior, ya de cuatro ruedas |
| 17 | Carl Benz 1869.png | Karl Benz en 1869 |

Varias fotos tienen licencia Creative Commons (CC BY / CC BY-SA). Si lo publicas, añade en la descripción:
«Imágenes: Wikimedia Commons (dominio público y CC BY-SA)».

Tipografías: Montserrat y Cinzel (licencia OFL, ver `fuentes/LICENCIA-OFL.txt`).
