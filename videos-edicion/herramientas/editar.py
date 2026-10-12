#!/usr/bin/env python3
"""Atajos rápidos de edición de video con FFmpeg.

Ejemplos:
  python editar.py info      video.mp4
  python editar.py cortar    video.mp4 00:00:10 00:00:25 -o clip.mp4
  python editar.py unir      parte1.mp4 parte2.mp4 -o final.mp4
  python editar.py comprimir video.mp4 -o ligero.mp4 --calidad 28
  python editar.py audio     video.mp4 -o audio.mp3
  python editar.py silenciar video.mp4 -o sin_audio.mp4
  python editar.py musica    video.mp4 cancion.mp3 -o con_musica.mp4 --volumen 0.3
  python editar.py vertical  video.mp4 -o tiktok.mp4
  python editar.py velocidad video.mp4 2 -o rapido.mp4
  python editar.py gif       video.mp4 -o animacion.gif
  python editar.py miniatura video.mp4 00:00:05 -o portada.jpg
  python editar.py texto     video.mp4 "Hola mundo" -o titulado.mp4
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("No se encontró FFmpeg. Ejecuta primero el instalador de esta carpeta.")


def run(*args):
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)]
    print("→", " ".join(cmd[1:]))
    subprocess.run(cmd, check=True)


def salida(args, sufijo, ext=None):
    if args.o:
        return args.o
    src = Path(args.video)
    return str(src.with_name(f"{src.stem}_{sufijo}{ext or src.suffix}"))


def info(args):
    probe = shutil.which("ffprobe") or ffmpeg_bin().replace("ffmpeg", "ffprobe")
    out = subprocess.run(
        [probe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", args.video],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    fmt = data["format"]
    print(f"Archivo:  {fmt['filename']}")
    print(f"Duración: {float(fmt['duration']):.2f} s")
    print(f"Tamaño:   {int(fmt['size']) / 1_048_576:.2f} MB")
    for s in data["streams"]:
        if s["codec_type"] == "video":
            print(f"Video:    {s['codec_name']} {s['width']}x{s['height']} @ {s['r_frame_rate']} fps")
        elif s["codec_type"] == "audio":
            print(f"Audio:    {s['codec_name']} {s.get('sample_rate', '?')} Hz, {s.get('channels', '?')} canales")


def cortar(args):
    run("-ss", args.inicio, "-to", args.fin, "-i", args.video,
        "-c:v", "libx264", "-c:a", "aac", salida(args, "corte"))


def unir(args):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for v in args.videos:
            f.write(f"file '{Path(v).resolve()}'\n")
        lista = f.name
    run("-f", "concat", "-safe", "0", "-i", lista,
        "-c:v", "libx264", "-c:a", "aac", args.o or "unido.mp4")
    Path(lista).unlink()


def comprimir(args):
    run("-i", args.video, "-c:v", "libx264", "-crf", args.calidad, "-preset", "medium",
        "-c:a", "aac", "-b:a", "128k", salida(args, "comprimido", ".mp4"))


def audio(args):
    run("-i", args.video, "-vn", "-q:a", "2", salida(args, "audio", ".mp3"))


def silenciar(args):
    run("-i", args.video, "-c:v", "copy", "-an", salida(args, "mudo"))


def musica(args):
    run("-i", args.video, "-i", args.cancion, "-filter_complex",
        f"[1:a]volume={args.volumen}[m];[0:a][m]amix=inputs=2:duration=first[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", salida(args, "musica"))


def vertical(args):
    # 1080x1920 con el video centrado y fondo desenfocado (TikTok / Reels / Shorts)
    filtro = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20[fondo];"
              "[0:v]scale=1080:-2[frente];[fondo][frente]overlay=(W-w)/2:(H-h)/2")
    run("-i", args.video, "-filter_complex", filtro, "-c:v", "libx264", "-c:a", "aac",
        salida(args, "vertical", ".mp4"))


def velocidad(args):
    f = float(args.factor)
    atempo, resto = [], f
    while resto > 2.0:
        atempo.append("atempo=2.0")
        resto /= 2.0
    while resto < 0.5:
        atempo.append("atempo=0.5")
        resto /= 0.5
    atempo.append(f"atempo={resto}")
    run("-i", args.video, "-filter_complex",
        f"[0:v]setpts=PTS/{f}[v];[0:a]{','.join(atempo)}[a]",
        "-map", "[v]", "-map", "[a]", salida(args, f"x{args.factor}"))


def gif(args):
    run("-i", args.video, "-vf",
        "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
        salida(args, "gif", ".gif"))


def miniatura(args):
    run("-ss", args.tiempo, "-i", args.video, "-frames:v", "1", "-q:v", "2",
        salida(args, "miniatura", ".jpg"))


def texto(args):
    escapado = args.texto.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    run("-i", args.video, "-vf",
        f"drawtext=text='{escapado}':fontcolor=white:fontsize=h/12:"
        "box=1:boxcolor=black@0.5:boxborderw=20:x=(w-text_w)/2:y=h-text_h-h/10",
        "-c:a", "copy", salida(args, "texto"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def cmd(nombre, fn, ayuda, *posicionales):
        s = sub.add_parser(nombre, help=ayuda)
        for pos in posicionales:
            s.add_argument(pos)
        s.add_argument("-o", help="archivo de salida")
        s.set_defaults(fn=fn)
        return s

    cmd("info", info, "muestra duración, resolución y tamaño", "video")
    cmd("cortar", cortar, "recorta entre dos tiempos (HH:MM:SS)", "video", "inicio", "fin")
    u = sub.add_parser("unir", help="une varios videos en orden")
    u.add_argument("videos", nargs="+")
    u.add_argument("-o", help="archivo de salida")
    u.set_defaults(fn=unir)
    cmd("comprimir", comprimir, "reduce el peso del video", "video").add_argument(
        "--calidad", default="23", help="18 = mejor calidad, 28 = más ligero (por defecto 23)")
    cmd("audio", audio, "extrae el audio en MP3", "video")
    cmd("silenciar", silenciar, "quita el audio", "video")
    cmd("musica", musica, "añade música de fondo", "video", "cancion").add_argument(
        "--volumen", default="0.3", help="volumen de la música (0.0 a 1.0)")
    cmd("vertical", vertical, "convierte a formato vertical 9:16", "video")
    cmd("velocidad", velocidad, "acelera o ralentiza (2 = doble, 0.5 = mitad)", "video", "factor")
    cmd("gif", gif, "convierte a GIF animado", "video")
    cmd("miniatura", miniatura, "saca una foto del video", "video", "tiempo")
    cmd("texto", texto, "pone un título abajo del video", "video", "texto")

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
