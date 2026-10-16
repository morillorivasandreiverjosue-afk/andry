# Narraciones con ElevenLabs — Curiosidades del Mundo

Configuración para generar las narraciones de los videos con una voz fija de ElevenLabs.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `voz.json` | **La voz del canal**: `voice_id`, modelo, idioma, estilo y tamaño de las partes. Se reutiliza en todos los videos. |
| `pronunciacion.json` | Palabras que la voz lee mal y cómo deben leerse (solo cambia el audio, no los subtítulos). |
| `voces_candidatas.json` | Voces latinoamericanas encontradas en la biblioteca de ElevenLabs, con su ID real. |
| `preparar.py` | Divide un guion en partes (una por capítulo, máx. 2500 caracteres) y aplica estilo y pronunciación. |
| `descargar.py` | Descarga los MP3 generados, los verifica y crea `narracion-completa.mp3`. |
| `elevenlabs_api.py` | Genera directamente con la API de ElevenLabs desde **tu computadora** (necesita `ELEVENLABS_API_KEY`). |

## Flujo de trabajo

1. Escribe el guion en un `.txt`. Los capítulos van en una línea en MAYÚSCULAS
   (`CAPÍTULO 1: ...`, `INTRODUCCIÓN: ...`, `FINAL: ...`) o con `## Título`.
2. Prepara las partes:
   ```bash
   python3 narracion/preparar.py mi_guion.txt -o narracion/proyectos/mi-video
   ```
3. Genera el audio. Hay dos caminos:
   - **Con Claude (conector de ElevenLabs):** pídele *"genera la narración de narracion/proyectos/mi-video"*.
     Claude envía cada parte con la voz de `voz.json`, guarda los enlaces en `trabajo.json`
     y ejecuta el paso 4.
   - **En tu computadora:** `export ELEVENLABS_API_KEY=...` y
     `python3 narracion/elevenlabs_api.py narracion/proyectos/mi-video`.
4. Une las partes:
   ```bash
   python3 narracion/descargar.py narracion/proyectos/mi-video
   ```
   Resultado: `narracion/proyectos/mi-video/audio/parte-NN.mp3` y `narracion-completa.mp3`.

## Reglas de la voz

- La voz es **siempre** la de `voz.json`. Para cambiarla, edita `voice_id` y `voice_nombre`.
- Si pides una voz concreta, se usa ese ID tal cual. Si no existe o falla, el proceso **se detiene**
  y avisa; nunca la sustituye por otra.
- Los IDs solo salen del catálogo de ElevenLabs o de ti, nunca se inventan.

## Estilo de narración (ya configurado)

- **Modelo `eleven_v4`**: el más natural y el único que entiende etiquetas de interpretación.
- **Tono**: `[serious]` al inicio de cada parte (serio y profesional).
- **Pausas**: `[pause]` entre párrafos y `[long pause]` después del título de cada capítulo.
  En el guion, los puntos suspensivos (…) también crean pausas y las comas, pausas cortas.
- **Énfasis**: escribe en MAYÚSCULAS una palabra clave (con moderación).
- **Pronunciación**: añade entradas a `pronunciacion.json`. Por ejemplo, `"siglo XIX": "siglo diecinueve"`.
- **Velocidad**: con el conector se controla con la puntuación y las pausas. Con la API directa,
  `voice_settings.speed` en `voz.json` (0.95 = un poco más pausado que lo normal).

## Costo aproximado

Medido en la prueba del 2026-10-16: **1 crédito por carácter** con `eleven_v4`
(294 caracteres = 294 créditos ≈ 0,05 USD por toma).
El documental de Bolívar tiene unos 26.500 caracteres → ~26.500 créditos por toma completa.
Por eso `voz.json` genera **1 variación por parte** (el conector por defecto genera 4).

## Usar tu propia voz (voz clonada)

Solo con **tu propia voz** o la de alguien que te haya dado permiso por escrito.

**Instant Voice Clone (rápido, desde el plan Starter):**
1. Graba de 1 a 3 minutos leyendo en tu tono de narrador. Hazlo en un cuarto silencioso,
   con el micrófono a un palmo de la boca, sin música ni eco. Expórtalo en WAV o MP3 de buena calidad.
2. En elevenlabs.io: **Voices → Add a new voice → Instant Voice Clone**.
3. Sube la grabación, ponle un nombre (por ejemplo "Narrador Curiosidades del Mundo") y
   confirma que tienes los derechos de esa voz.
4. Copia el **Voice ID** que aparece en la ficha de la voz.

**Professional Voice Clone (más fiel, desde el plan Creator):**
igual que el anterior, pero con 30 minutos o más de grabación limpia. ElevenLabs además verifica
que la voz es tuya (te pide leer una frase en vivo). Tarda unas horas en entrenarse.

**Después:** pon ese ID en `voice_id` de `voz.json` o pásaselo a Claude diciendo
*"usa la voz con ID ..."*. A partir de ahí todas las narraciones salen con tu voz.
