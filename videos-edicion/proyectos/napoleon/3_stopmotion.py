"""Video de prueba de 40 segundos en estilo stop motion con las escenas del documental.

Las imágenes avanzan a saltos (12 dibujos por segundo, cada uno repetido dos veces),
con un pequeño temblor y parpadeo en cada dibujo, como una animación cuadro a cuadro.

Uso: python3 3_stopmotion.py <archivo_salida.mp4>
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image

import plan
import sonido as SN

AQUI = Path(__file__).parent
spec = importlib.util.spec_from_file_location("montaje", AQUI / "2_montaje.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

DIBUJOS_POR_SEGUNDO = 12
TOTAL = 40.0

ESCENAS = [  # (escena, duración, cañonazos en segundos dentro de la escena)
    ({"tipo": "titulo", "etiqueta": "CURIOSIDADES DEL MUNDO", "titulo": "PRUEBA · STOP MOTION",
      "subtitulo": "Napoleón Bonaparte", "tam": 110, "semilla": 5}, 4.0, []),
    (plan.E["marcha"], 6.0, []),
    (plan.E["batalla"], 6.0, [0.4, 1.6, 2.9, 4.2, 5.2]),
    (plan.E["m_italia"], 5.0, [2.5, 3.6]),
    (plan.E["coronacion"], 5.0, []),
    (plan.E["moscu"], 5.0, [1.0]),
    (plan.E["marcha_nieve"], 5.0, []),
    (plan.E["heroe_emperador"], 4.0, [0.1]),
]


def linea_de_tiempo():
    clips, t = [], 0.0
    for escena, dur, canones in ESCENAS:
        cues = [(c, "impacto" if escena["tipo"] == "heroe" else "canon", 1.0) for c in canones]
        clips.append({"spec": escena, "ini": t, "dur": dur, "clave": None, "cues": cues, "fecha": None})
        t += dur
    return {"clips": clips, "subs": [], "rotulos": [], "total": t}


def audio(tl, ruta):
    n = SN.seg(TOTAL)
    mezcla = np.zeros((n + SN.SR * 6, 2), np.float32)

    def poner(s, t, v):
        i = SN.seg(t)
        mezcla[i: i + len(s)] += s[: len(mezcla) - i] * v

    poner(SN.musica("epico", TOTAL), 0, 0.6)
    poner(SN.impacto(), 0.05, 0.8)
    poner(SN.tambor_militar(6.0, 110, volumen=0.6), 4.0, 0.8)
    poner(SN.descarga(), 10.1, 0.8)
    poner(SN.campana(), 21.2, 0.5)
    poner(SN.fuego(5.0), 26.0, 0.8)
    poner(SN.viento(5.0), 31.0, 0.9)
    for c in tl["clips"]:
        for tc, tipo, _ in c["cues"]:
            poner(SN.impacto() if tipo == "impacto" else SN.canon(0.1), c["ini"] + tc, 0.9)
    # chasquido suave de cámara en cada cambio de escena
    for c in tl["clips"][1:]:
        poner(SN.whoosh(0.6), c["ini"] - 0.4, 0.5)
    mezcla = np.tanh(mezcla[:n] * 1.1) / np.tanh(1.1)
    sf.write(ruta, SN.normal(mezcla, 0.95), SN.SR, subtype="PCM_16")


def main():
    salida = Path(sys.argv[1])
    salida.parent.mkdir(parents=True, exist_ok=True)
    tl = linea_de_tiempo()
    r = M.Render(tl)
    rng = np.random.default_rng(24)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        audio(tl, wav)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{M.W}x{M.H}",
               "-r", str(M.FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
               str(salida)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        repetir = M.FPS // DIBUJOS_POR_SEGUNDO
        for k in range(int(TOTAL * DIBUJOS_POR_SEGUNDO)):
            cuadro = Image.frombytes("RGB", (M.W, M.H), r.cuadro(k * repetir))
            # temblor de cámara y luz distintos en cada dibujo, como en el stop motion real
            dx, dy = rng.integers(-5, 6, 2)
            cuadro = cuadro.transform(cuadro.size, Image.AFFINE, (1.01, 0, dx - 9, 0, 1.01, dy - 5), Image.BILINEAR)
            arr = np.asarray(cuadro).astype(np.float32) * rng.uniform(0.95, 1.04)
            datos = np.clip(arr, 0, 255).astype(np.uint8).tobytes()
            for _ in range(repetir):
                p.stdin.write(datos)
            if k % 60 == 0:
                print(f"{k / (TOTAL * DIBUJOS_POR_SEGUNDO) * 100:.0f}%", flush=True)
        p.stdin.close()
        p.wait()
    print("Listo:", salida)


if __name__ == "__main__":
    main()
