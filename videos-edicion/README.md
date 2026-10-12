# 🎬 Videos Edición

Todo lo necesario para editar videos, gratis.

## 1. Instalar los programas (una sola vez)

Descarga esta carpeta en tu computadora y ejecuta el instalador de tu sistema:

| Sistema | Cómo instalar |
|---|---|
| **Windows** | Abre *Terminal (Administrador)* en esta carpeta y ejecuta: `powershell -ExecutionPolicy Bypass -File .\instalar-windows.ps1` |
| **Mac** | Abre *Terminal* en esta carpeta y ejecuta: `bash instalar-mac.sh` |
| **Linux** | Abre una terminal en esta carpeta y ejecuta: `bash instalar-linux.sh` |

### Qué se instala

| Programa | Para qué sirve |
|---|---|
| **Shotcut** | Editor de video fácil: cortar, unir, transiciones, texto, música. **Empieza por aquí.** |
| **Kdenlive** | Editor más completo: muchas pistas, efectos, corrección de color. |
| **OBS Studio** | Grabar la pantalla, la cámara o hacer directos. |
| **Audacity** | Limpiar la voz, quitar ruido, editar audio. |
| **HandBrake** | Comprimir y convertir videos para que pesen menos. |
| **VLC** | Reproductor que abre cualquier video. |
| **GIMP** | Editar imágenes y hacer miniaturas/portadas. |
| **FFmpeg** | Motor que usan las herramientas rápidas de abajo. |
| **Python + MoviePy** | Para editar con scripts (`requirements.txt`). |

Opcional: **DaVinci Resolve** (editor profesional, gratis) — se descarga a mano en
<https://www.blackmagicdesign.com/products/davinciresolve>. Necesita una computadora potente.

## 2. Organización de carpetas

```
videos-edicion/
├── material/      ← pon aquí los videos, fotos y audios originales
├── proyectos/     ← guarda aquí los proyectos de Shotcut / Kdenlive
├── exportados/    ← aquí van los videos terminados
└── herramientas/  ← atajos rápidos (editar.py)
```

Los videos no se suben a GitHub (pesan mucho); solo se quedan en tu computadora.

## 3. Atajos rápidos sin abrir un editor

Desde esta carpeta (en Windows usa `py` en lugar de `python3`):

```bash
python3 herramientas/editar.py info      material/video.mp4                       # duración, resolución, peso
python3 herramientas/editar.py cortar    material/video.mp4 00:00:10 00:00:25    # recortar un trozo
python3 herramientas/editar.py unir      parte1.mp4 parte2.mp4 -o exportados/final.mp4
python3 herramientas/editar.py comprimir material/video.mp4 --calidad 28          # que pese menos
python3 herramientas/editar.py audio     material/video.mp4                       # sacar el audio en MP3
python3 herramientas/editar.py silenciar material/video.mp4                       # quitar el sonido
python3 herramientas/editar.py musica    material/video.mp4 cancion.mp3 --volumen 0.3
python3 herramientas/editar.py vertical  material/video.mp4                       # 9:16 para TikTok/Reels/Shorts
python3 herramientas/editar.py velocidad material/video.mp4 2                     # 2 = doble de rápido, 0.5 = cámara lenta
python3 herramientas/editar.py gif       material/video.mp4
python3 herramientas/editar.py miniatura material/video.mp4 00:00:05             # foto para portada
python3 herramientas/editar.py texto     material/video.mp4 "Mi título"
```

Si no pones `-o`, el resultado se guarda junto al original con un sufijo (por ejemplo `video_vertical.mp4`).

## 4. Pasos básicos para editar tu primer video (Shotcut)

1. Copia tus clips a `material/`.
2. Abre **Shotcut** → *Abrir archivo* → arrastra los clips a la **Línea de tiempo**.
3. Corta con la tecla **S** (dividir) y borra lo que sobra.
4. Añade música: arrástrala a una pista de audio.
5. Texto: *Filtros* → **+** → *Texto: simple*.
6. *Exportar* → preset **YouTube** (o *H.264 High Profile*) → guarda en `exportados/`.
