# Reglas para los videos de "Curiosidades del Mundo"

Cada vez que el usuario pida un video o documental, aplicar SIEMPRE estas reglas, sin que tenga que repetirlas.
Proyecto de referencia (ya aprobado por el usuario): `videos-edicion/proyectos/11-septiembre/`.

## 1. Logo (lo más importante — NO cambiarlo nunca)
- Arriba a la derecha, visible todo el video: **"CURIOSIDADES"** (Bebas Neue, blanco) y debajo una
  **rayita roja** (#E5202A) + **"DEL MUNDO"** (Oswald Light, gris, letras espaciadas). Ligera sombra, opacidad ~88 %.
- **Sin globo, sin planeta, sin ícono** (el usuario lo pidió quitar: parecía de noticiero).
- Imagen lista: `videos-edicion/marca/logo_curiosidades_del_mundo.png`, colocada a 40 px del borde derecho y 34 px del borde superior en 1920x1080.
  Código que lo genera: función `logo()` en `videos-edicion/proyectos/11-septiembre/graficos.py`.
- No cambiar el diseño, ni los colores, ni la posición, ni el tamaño.

## 2. Estilo: documental tipo Netflix (llamativo, serio)
- Tarjetas de capítulo: "— CAPÍTULO N" en rojo + título grande en Bebas Neue blanco + número gigante translúcido a la derecha,
  sobre el video oscurecido. **En pantalla SÍ debe decir "CAPÍTULO 1, 2, 3…".**
- Título de apertura grande al inicio y pantalla final con "CURIOSIDADES DEL MUNDO" + botón rojo "SUSCRÍBETE" (sin globo).
- Rótulos abajo a la izquierda con fechas, horas y cifras clave (barra roja + texto Bebas/Oswald).
- Zoom lento en fotos y videos, corrección de color suave, grano ligero, viñeta SUAVE (nada de efecto túnel).
- Tipografías en `videos-edicion/marca/` (Bebas Neue, Oswald, Inter; licencia OFL).

## 3. Narración (audios de ElevenLabs que manda el usuario)
- **La voz NUNCA debe decir "Capítulo 1, 2, 3…", ni "Introducción" ni "Conclusión".** Cortar esas palabras del audio
  y dejar la pausa para la tarjeta en pantalla. La voz sí dice el título del capítulo.
- Revisar TODOS los cortes uno por uno (transcripción + perfil de energía): no puede quedar ningún trozo ("Ca…", "…cinco").
  La transcripción automática a veces no detecta restos: comprobar también que haya silencio antes del título.
- Herramientas: `transcribe.py`, `cuts.py`, `narr.py`, `verify.py` del proyecto de referencia.

## 4. Audio: SIN MÚSICA
- **Nada de música de fondo en ninguna parte del video.** Es un documental: solo la voz del narrador y
  el sonido real del momento (aviones, impactos, explosiones, sirenas, gente, ambiente).
- Si un video que manda el usuario trae música, quitarla. Si no se puede separar, reemplazar ese audio por sonido
  real/ambiente sincronizado con lo que se ve (motor, impacto, etc.). No dejar música.
- Bajo la narración, ambiente real de los videos de archivo a volumen bajo. Golpes graves (sin tonos musicales) en títulos.
- Volumen final normalizado a -14 LUFS (YouTube).

## 5. Material visual
- Usar videos e imágenes REALES de cómo pasó (archivo de dominio público o con licencia libre) + los videos que mande el usuario.
- Nunca dejar pantallas negras por error (revisar con `blackdetect`). Solo negro cuando sea un efecto pedido.
- Momentos dramáticos (p. ej. "pero lo peor todavía estaba por llegar"): pantalla negra con la frase en grande,
  luego un "boom" y vuelve el video.
- Guardar los créditos/licencias del material en `creditos.txt` del proyecto.

## 6. Entrega
- Exportar en **4K (3840x2160)** y también en 1080p. El límite para enviar archivos al usuario es de ~400 MB:
  ajustar la tasa de bits para que quepa (HEVC para la 4K).
- Avisar al usuario cuánto falta cuando lo pregunte, y hablarle en español.
