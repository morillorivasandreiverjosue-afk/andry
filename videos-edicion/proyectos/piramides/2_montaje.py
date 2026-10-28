"""Paso 2: monta el video vertical para TikTok (1080x1920) con imágenes, voz, música y subtítulos.

Uso: python3 2_montaje.py <carpeta_salida>
Necesita <salida>/imagenes/ (0_imagenes.py) y <salida>/voz.json (1_voz.py).
Crea <salida>/Piramides_de_Egipto_TikTok.mp4 y <salida>/piramides.srt
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import resample_poly

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "napoleon"))
import sonido as SN  # noqa: E402  (música y efectos sintetizados del documental de Napoleón)

W, H, FPS = 1080, 1920, 30
XF = 0.35          # fundido entre imágenes
GAP = 0.25         # silencio entre frases
COLA = 0.45        # silencio al final de cada párrafo
INICIO = 0.4       # silencio antes de la primera palabra
FINAL = 2.5        # imagen final tras la última frase
FUENTE = AQUI.parent / "napoleon" / "fuentes" / "cinzel-latin-700-normal.woff"
ORO = (255, 206, 92)

# Imágenes de cada párrafo: (nombre, x_inicial, x_final, zoom_inicial, zoom_final)
# x va de 0 (borde izquierdo de la foto) a 1 (borde derecho): la cámara recorre la foto en horizontal.
PLAN = [
    [("esfinge_atardecer", 0.35, 0.55, 1.12, 1.0)],                                 # título
    [("estrellas", 0.30, 0.70, 1.0, 1.08), ("atardecer", 0.20, 0.55, 1.08, 1.0)],
    [("esfinge_dia", 0.75, 0.45, 1.05, 1.0), ("camellos", 0.30, 0.60, 1.0, 1.06)],
    [("obra_nilo", 0.60, 0.35, 1.15, 1.0)],
    [("arrastre_agua", 0.25, 0.50, 1.0, 1.06), ("rampa_subida", 0.30, 0.65, 1.06, 1.0),
     ("grua_rampa", 0.70, 0.40, 1.0, 1.06), ("arrastre_bloque", 0.80, 0.50, 1.06, 1.0)],
    [("pasillo", 0.50, 0.50, 1.0, 1.25), ("jeroglificos", 0.20, 0.60, 1.05, 1.0)],
    [("rampa_dibujo", 0.45, 0.60, 1.0, 1.12)],
    [("esfinge_atardecer", 0.60, 0.45, 1.0, 1.15)],
    [("obra_nilo", 0.15, 0.45, 1.0, 1.10)],
]


# =================================================================== línea de tiempo
def construir(voz):
    clips, voces, subs = [], [], []
    t = INICIO
    for p, frases in enumerate(voz):
        ini = t
        for f in frases:
            voces.append((t, f["wav"]))
            subs.append((t, t + f["dur"], f["texto"], p == 0))
            t += f["dur"] + GAP
        t += COLA - GAP
        fin = t if p < len(voz) - 1 else t + FINAL
        if p == 0:
            ini = 0.0
        tramo = (fin - ini) / len(PLAN[p])
        for k, (nombre, *mov) in enumerate(PLAN[p]):
            clips.append({"img": nombre, "mov": mov, "ini": ini + k * tramo, "dur": tramo, "parrafo": p})
        t = fin
    return clips, voces, subs, t


# =================================================================== imagen
class Fotos:
    def __init__(self, carpeta):
        self.carpeta, self.cache = carpeta, {}

    def __call__(self, nombre):
        if nombre not in self.cache:
            im = Image.open(self.carpeta / f"{nombre}.png").convert("RGB")
            esc = H * 1.25 / im.height  # margen para el zoom
            if im.width * esc < W * 1.25:
                esc = W * 1.25 / im.width
            self.cache[nombre] = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
        return self.cache[nombre]


def suave(x):
    return x * x * (3 - 2 * x)


def encuadre(foto, mov, u):
    """Recorte 9:16 que se mueve y acerca a lo largo del clip (u de 0 a 1)."""
    x0, x1, z0, z1 = mov
    u = suave(min(max(u, 0), 1))
    zoom = z0 + (z1 - z0) * u
    ch = foto.height / 1.25 / zoom  # alto visible en píxeles de la foto
    cw = ch * W / H
    cx = cw / 2 + (foto.width - cw) * (x0 + (x1 - x0) * u)
    cy = foto.height / 2
    a = cw / W
    return foto.transform((W, H), Image.AFFINE, (a, 0, cx - cw / 2, 0, a, cy - ch / 2), Image.BICUBIC)


def degradados():
    y = np.linspace(0, 1, H)[:, None]
    arriba = np.clip(1 - y / 0.22, 0, 1) ** 1.5 * 0.55
    abajo = np.clip((y - 0.5) / 0.35, 0, 1) ** 1.3 * 0.6
    sombra = np.broadcast_to(np.maximum(arriba, abajo), (H, W))
    return (1 - sombra)[:, :, None].astype(np.float32)


# =================================================================== textos
def fuente(tam):
    return ImageFont.truetype(str(FUENTE), tam)


def partir(texto, max_palabras=4):
    """Subtítulos al estilo TikTok: pocas palabras cada vez."""
    palabras = texto.split()
    grupos, actual = [], []
    for w in palabras:
        actual.append(w)
        if len(actual) >= max_palabras or w[-1] in ",:;.?" and len(actual) >= 2:
            grupos.append(actual)
            actual = []
    if actual:
        if grupos and len(actual) == 1:
            grupos[-1] += actual
        else:
            grupos.append(actual)
    return [" ".join(g) for g in grupos]


def bloques_subtitulos(subs):
    """Reparte el tiempo de cada frase entre sus grupos de palabras según su longitud."""
    out = []
    for ini, fin, texto, es_titulo in subs:
        if es_titulo:
            continue
        grupos = partir(texto)
        pesos = np.array([len(g) + 4 for g in grupos], float)
        cortes = ini + np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * (fin - ini)
        for g, a, b in zip(grupos, cortes[:-1], cortes[1:]):
            out.append((a, b, g))
    return out


def texto_centrado(draw, y, lineas, tam, color, borde=8):
    f = fuente(tam)
    for linea in lineas:
        ancho = draw.textlength(linea, font=f)
        draw.text(((W - ancho) / 2, y), linea, font=f, fill=color, stroke_width=borde, stroke_fill=(0, 0, 0))
        y += tam * 1.18
    return y


def ajustar(texto, tam, ancho_max=W - 140):
    f = fuente(tam)
    lineas, actual = [], ""
    for w in texto.split():
        prueba = (actual + " " + w).strip()
        if actual and f.getlength(prueba) > ancho_max:
            lineas.append(actual)
            actual = w
        else:
            actual = prueba
    return lineas + [actual]


def capa_subtitulo(texto, u):
    """Subtítulo en mayúsculas con un pequeño 'pop' al aparecer."""
    escala = 1.0 + 0.12 * max(0, 1 - u / 0.12)
    tam = int(88 * escala)
    lineas = ajustar(texto.upper().rstrip(".,:;"), tam)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    alto = len(lineas) * tam * 1.18
    texto_centrado(d, H * 0.68 - alto / 2, lineas, tam, (255, 255, 255), borde=9)
    return capa


def capa_titulo(u):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    alfa = int(255 * min(1, u / 0.08))
    y = texto_centrado(d, H * 0.30, ["LAS PIRÁMIDES", "DE EGIPTO"], 112, ORO + (alfa,), borde=10)
    texto_centrado(d, y + 30, ["El misterio de", "una civilización"], 64, (255, 255, 255, alfa), borde=7)
    return capa


def capa_pregunta(u):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    alfa = int(255 * min(1, u / 0.1))
    texto_centrado(d, H * 0.22, ["¿TÚ QUÉ CREES?"], 104, ORO + (alfa,), borde=10)
    texto_centrado(d, H * 0.22 + 150, ["Déjalo en los", "comentarios"], 64, (255, 255, 255, alfa), borde=7)
    return capa


# =================================================================== audio
def leer_voz(ruta):
    a, sr = sf.read(ruta, dtype="float32")
    if sr != SN.SR:
        a = resample_poly(a, SN.SR, sr).astype(np.float32)
    return a


def audio(clips, voces, total, ruta):
    n = SN.seg(total)
    voz = np.zeros(n + SN.SR * 2, np.float32)
    for t, wav in voces:
        a = leer_voz(wav)
        i = SN.seg(t)
        voz[i: i + len(a)] += a
    voz = voz[:n]
    mezcla = np.zeros((n + SN.SR * 8, 2), np.float32)

    def poner(s, t, v):
        i = SN.seg(t)
        mezcla[i: i + len(s)] += s[: len(mezcla) - i] * v

    # música: misterio al principio y al final, épica durante la construcción
    t_constr = next(c["ini"] for c in clips if c["parrafo"] == 3)
    t_relig = next(c["ini"] for c in clips if c["parrafo"] == 5)
    poner(SN.musica("misterio", t_constr + 2), 0, 0.9)
    poner(SN.musica("epico", t_relig - t_constr + 2), t_constr - 1, 0.8)
    poner(SN.musica("majestuoso", total - t_relig + 2), t_relig - 1, 0.85)
    poner(SN.impacto(), 0.0, 0.7)
    poner(SN.viento(6.0, 0.6), 0.0, 0.6)
    for c in clips[1:]:
        poner(SN.whoosh(0.5), c["ini"] - 0.3, 0.35)
    poner(SN.timbal(55.0), t_constr, 0.8)
    musica = mezcla[:n]
    # la música baja mientras habla la voz
    env = np.convolve(np.abs(voz), np.ones(SN.SR // 10) / (SN.SR // 10), "same")
    env = np.clip(env / (env.max() * 0.15), 0, 1)
    env = np.convolve(env, np.ones(SN.SR // 4) / (SN.SR // 4), "same")
    musica *= (1 - 0.55 * env)[:, None]
    final = musica * 0.6 + SN.estereo(voz * 1.4)
    fade = SN.seg(1.5)
    final[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sf.write(ruta, SN.normal(final, 0.95), SN.SR, subtype="PCM_16")


# =================================================================== render
def main():
    salida = Path(sys.argv[1])
    voz = json.loads((salida / "voz.json").read_text())
    clips, voces, subs, total = construir(voz)
    bloques = bloques_subtitulos(subs)
    fotos = Fotos(salida / "imagenes")
    sombra = degradados()

    with open(salida / "piramides.srt", "w", encoding="utf-8") as f:
        hms = lambda s: f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(s % 1 * 1000):03d}"
        for i, (a, b, texto, _) in enumerate(subs, 1):
            f.write(f"{i}\n{hms(a)} --> {hms(b)}\n{texto}\n\n")

    wav = salida / "audio.wav"
    audio(clips, voces, total, wav)
    t_pregunta = subs[-1][0]
    mp4 = salida / "Piramides_de_Egipto_TikTok.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n_cuadros = int(total * FPS)
    for k in range(n_cuadros):
        t = k / FPS
        activos = [c for c in clips if c["ini"] - XF / 2 <= t < c["ini"] + c["dur"] + XF / 2]
        cuadro = None
        for c in activos:
            u = (t - c["ini"] + XF / 2) / (c["dur"] + XF)
            im = encuadre(fotos(c["img"]), c["mov"], u)
            if cuadro is None:
                cuadro = im
            else:
                alfa = min(1, max(0, (t - (c["ini"] - XF / 2)) / XF))
                cuadro = Image.blend(cuadro, im, alfa)
        arr = np.asarray(cuadro).astype(np.float32) * sombra
        if t < 0.25:  # entrada desde negro
            arr *= t / 0.25
        if t > total - 1.0:
            arr *= max(0, (total - t) / 1.0)
        cuadro = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
        if t < subs[0][1] + 0.6:
            cuadro.alpha_composite(capa_titulo(t / (subs[0][1] + 0.6)))
        if t >= t_pregunta:
            cuadro.alpha_composite(capa_pregunta((t - t_pregunta) / 2))
        for a, b, texto in bloques:
            if a <= t < b + 0.05:
                cuadro.alpha_composite(capa_subtitulo(texto, (t - a) / max(b - a, 0.01)))
                break
        proc.stdin.write(cuadro.convert("RGB").tobytes())
        if k % 150 == 0:
            print(f"{k / n_cuadros * 100:.0f}%", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"Listo: {mp4} ({total:.1f} s)")


if __name__ == "__main__":
    main()
