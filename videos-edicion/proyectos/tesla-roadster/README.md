# ¿Elon Musk está a punto de hacer volar a Tesla? — mini documental para «Curiosidades del Mundo»

Vídeo vertical 9:16 (1080 × 1920, 30 fps, ~1 min 57 s) para Reels, TikTok y YouTube Shorts.

- **Voz:** ElevenLabs, voz «Jorge» (masculina, grave, documental), español latinoamericano.
- **Subtítulos:** sincronizados palabra por palabra (`palabras.json`), palabras clave en cian.
- **Imágenes:** cambio de plano cada 2–4 s, zooms lentos, fundidos; cortes secos, sacudida y destello en la maniobra.
- **Audio:** música tecnológica sintetizada en `montaje.py` (baja sola bajo la voz), subida de tensión y
  silencio dramático antes de la maniobra, efectos de propulsores, motor eléctrico e impactos (ElevenLabs).
  Volumen final −14 LUFS.
- **Marca de agua** «CURIOSIDADES DEL MUNDO» y cierre con botón «SÍGUENOS».

```bash
python3 montaje.py --procesos 4          # → ../../exportados/Curiosidades_del_Mundo_Tesla_Roadster.mp4 (+ .srt)
python3 montaje.py --prueba 50 70        # prueba rápida de un tramo
```

`material/` (gitignored) necesita `voz.wav`, `propulsor.wav`, `propulsor2.wav`, `electrico.wav`, `impacto.wav`
(48 kHz) y las imágenes en `img/`.

## Verificación de datos (17 oct. 2026)

- La demostración se hizo el **15 de octubre de 2026** en el sitio de pruebas de SpaceX en **McGregor, Texas**.
- El prototipo subió por una rampa curva, se despegó del suelo, giró en el aire y aterrizó, **sin conductor**.
  Usó ventiladores de succión y **propulsores de gas frío / aire comprimido** desarrollados con SpaceX.
- Fueron maniobras breves y controladas, **no vuelo libre**. Musk habla de **producción en 2028**, sin garantía.

Fuentes: [Aviation Week](https://aviationweek.com/aerospace/emerging-technologies/tesla-demos-flying-roadster-powered-spacex-cold-gas-thrusters),
[TechCrunch](https://techcrunch.com/2026/10/15/tesla-reveals-spacex-powered-roadster-that-flies-and-falls-with-style/),
[CNBC](https://www.cnbc.com/2026/10/15/tesla-roadster-reveal-what-to-know-about-the-delayed-ev.html),
[The Next Web](https://thenextweb.com/news/tesla-roadster-reveal-thrusters-2028),
[Yahoo Finance](https://finance.yahoo.com/markets/stocks/article/tesla-unveils-roadster-featuring-compressed-air-thrusters-for-limited-flight-015532745.html).

## Imágenes y rótulos

No hay escenas generadas con IA. Cada imagen lleva un rótulo con lo que es:

| Archivo | Origen | Rótulo |
|---|---|---|
| u1, u2, u3 | Imágenes enviadas por el canal (demostración de oct. 2026) | Demostración de Tesla · 15 oct. 2026 |
| c00, c01, c02 | Wikimedia Commons: Elon Musk Royal Society (crop2), Elon Musk 2015, Elon Musk Colorado 2022 (cropped2) | Elon Musk |
| c04 | Commons: Successful Falcon Heavy Launch Today (40090461942) | Lanzamiento de Falcon Heavy · SpaceX, 2018 |
| c05, c06 | Commons: Starship lifted off from Starbase during flight test 11; SpaceX Starship ignition during IFT-5 | Lanzamiento / Encendido de Starship |
| c09 | Commons: Elon Musk's Tesla Roadster (40110304192) | Roadster de Musk en el espacio · SpaceX, 2018 |
| c12 | Commons: Falcon Heavy Side Boosters landing on LZ1 and LZ2 - 2018 | Propulsores de Falcon Heavy aterrizando |
| d00–d03, d09, d10 | Commons: fotos del prototipo de Roadster de 2017 (salones 2018–2019) | Prototipo presentado en 2017 (diseño anterior) |
| d06, d07 | Commons: Falcon 9 / THAICOM 8 landing (cropped to cold gas thruster section) | Propulsores de gas frío de un cohete Falcon 9 |
| e00, e01 | Commons: AeroMobil (Pioneers Festival 2014), Aeromobil 4.0 | AeroMobil: auto volador de otra empresa |

Créditos para la descripción: «Imágenes: Wikimedia Commons (CC BY / CC BY-SA / dominio público, SpaceX CC0) e
imágenes de la demostración de Tesla».
