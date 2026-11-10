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

## 4. Audio y música
- **SIEMPRE quitar la música que traigan los videos que manda el usuario** (o cualquier música ajena que aparezca).
  De esos clips solo debe oírse el sonido real del momento (aviones, impactos, explosiones, sirenas, gente).
  Si la música no se puede separar, reemplazar ese audio por sonido real/ambiente sincronizado con lo que se ve.
- **Mi propia música de fondo SÍ va** (al usuario le gusta "ese sonidito"): la banda sonora cinematográfica generada
  con `videos-edicion/proyectos/napoleon/sonido.py` (`musica()`), un ánimo por capítulo (misterio, majestuoso, tensión,
  triste…), bajita y que se agache sola cuando habla el narrador (sidechain), golpes/whoosh en los títulos.
  Ver `musica.py` del proyecto 11-septiembre. En los momentos de impacto real, bajar la música para que se oiga el sonido real.
- Ambiente real de los videos de archivo a volumen bajo bajo la narración.
- Volumen final normalizado a -14 LUFS (YouTube).
- (En el video del 11S, la versión entregada quedó sin música porque así se pidió en ese momento; en los próximos videos
  usar mi música de fondo como se describe arriba).

## 4b. Errores que NO deben repetirse
- Pantallas negras por error, restos de la palabra "capítulo" o del número en la voz, música dentro de los clips del usuario,
  ícono/planeta en el logo, viñeta demasiado oscura.

## 5. Material visual
- Usar videos e imágenes REALES de cómo pasó (archivo de dominio público o con licencia libre) + los videos que mande el usuario.
- Nunca dejar pantallas negras por error (revisar con `blackdetect`). Solo negro cuando sea un efecto pedido.
- Momentos dramáticos (p. ej. "pero lo peor todavía estaba por llegar"): pantalla negra con la frase en grande,
  luego un "boom" y vuelve el video.
- Guardar los créditos/licencias del material en `creditos.txt` del proyecto.

## 6. Entrega
- Exportar en **4K (3840x2160)** y también en 1080p. El límite para enviar archivos al usuario es de ~400 MB:
  ajustar la tasa de bits para que quepa. Usar **H.264** (no HEVC/H.265): en el celular del usuario
  el HEVC solo reproducía el audio, sin imagen.
- Avisar al usuario cuánto falta cuando lo pregunte, y hablarle en español.
