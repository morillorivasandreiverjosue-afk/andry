"""Video vertical para TikTok (1080x1920) del desastre del Hindenburg: imágenes, voz, música y subtítulos.

Uso: python3 montaje.py <carpeta_salida>
Necesita <salida>/voz.json (alinear.py, con la narración de ElevenLabs en <salida>/voz.mp3).
Crea <salida>/Hindenburg_TikTok.mp4 y <salida>/hindenburg.srt
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from scipy.signal import resample_poly

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "napoleon"))
import sonido as SN  # noqa: E402  (música y efectos sintetizados del documental de Napoleón)

W, H, FPS = 1080, 1920, 30
XF = 0.5             # fundido entre imágenes
INICIO = 0.3         # silencio antes de la primera palabra
FINAL = 2.5          # imagen final tras la última frase
FUENTE = AQUI.parent / "napoleon" / "fuentes" / "cinzel-latin-700-normal.woff"
ORO = (255, 206, 92)
ROJO = (255, 120, 70)

FOTOS = {"comedor": "1.jpg", "en_tierra": "2.jpg", "restos": "3.jpg", "incendio": "4.jpg", "sobre_publico": "5.jpg"}

# Imágenes de cada párrafo de voz_elevenlabs.txt: (nombre, x_inicial, x_final, zoom_inicial, zoom_final)
# x va de 0 (borde izquierdo de la foto) a 1 (borde derecho): la cámara recorre la foto en horizontal.
PLAN = [
    [("comedor", 0.30, 0.75, 1.0, 1.08), ("incendio", 0.50, 0.60, 1.0, 1.15)],      # gancho
    [("en_tierra", 0.05, 0.70, 1.0, 1.0), ("comedor", 0.80, 0.45, 1.12, 1.0)],      # el protagonista
    [("en_tierra", 0.55, 0.45, 1.0, 1.30)],                                          # hidrógeno
    [("sobre_publico", 0.50, 0.40, 1.0, 1.12)],                                      # 6 de mayo
    [("incendio", 0.35, 0.65, 1.15, 1.0)],                                           # las llamas
    [("restos", 0.25, 0.60, 1.0, 1.10)],                                             # víctimas
    [("incendio", 0.70, 0.45, 1.0, 1.10)],                                           # imágenes al mundo
    [("restos", 0.75, 0.50, 1.10, 1.0)],                                             # declive
    [("en_tierra", 0.80, 0.30, 1.05, 1.0)],                                          # el gigante
    [("sobre_publico", 0.45, 0.55, 1.0, 1.15)],                                      # pregunta final
]

# Textos clave en la parte de arriba: (párrafo, palabra con la que aparece, duración, grandes, pequeñas, color)
# palabra None = al empezar el párrafo
CARTELES = [
    (0, None, 4.5, ["HINDENBURG"], ["La tragedia de 1937"], ORO),
    (1, "245", 4.5, ["245 METROS"], ["de longitud"], ORO),
    (2, "hidrógeno,", 4.5, ["HIDRÓGENO"], ["gas extremadamente", "inflamable"], ROJO),
    (3, None, 5.0, ["6 DE MAYO", "DE 1937"], ["Lakehurst, Nueva Jersey"], ORO),
    (5, "36", 2.6, ["36 FALLECIDOS"], [], ROJO),
    (5, "62", 4.5, ["62 DE 97"], ["sobrevivieron"], ORO),
    (9, None, 2.4, ["¿TE HABRÍAS", "ATREVIDO?"], ["Déjalo en los", "comentarios"], ORO),
    (9, "Déjanos", 99, ["SÍGUENOS"], ["Curiosidades", "del Mundo"], ORO),
]


# =================================================================== línea de tiempo
def construir(voz):
    """La narración va entera desde INICIO; cada párrafo ocupa su tramo de voz con sus imágenes."""
    parrafos = voz["parrafos"]
    assert len(parrafos) == len(PLAN), (len(parrafos), len(PLAN))
    subs = [(INICIO + f["ini"], INICIO + f["fin"], f["texto"],
             [(INICIO + w["ini"], INICIO + w["fin"], w["t"]) for w in f["palabras"]])
            for frases in parrafos for f in frases]
    total = INICIO + voz["dur"] + FINAL
    inicios = [0.0] + [INICIO + fr[0]["ini"] - 0.15 for fr in parrafos[1:]]
    limites = inicios + [total]
    clips = []
    for p, imagenes in enumerate(PLAN):
        tramo = (limites[p + 1] - limites[p]) / len(imagenes)
        for k, (nombre, *mov) in enumerate(imagenes):
            clips.append({"img": nombre, "mov": mov, "ini": limites[p] + k * tramo, "dur": tramo, "parrafo": p})
    carteles = []
    for p, palabra, d, g, c, col in CARTELES:
        a = inicios[p] + 0.2 if palabra is None else next(
            INICIO + w["ini"] for f in parrafos[p] for w in f["palabras"] if w["t"] == palabra)
        carteles.append((a, min(a + d, limites[p + 1] + 0.3), g, c, col))
    return inicios, clips, carteles, subs, total


# =================================================================== imagen
class Fotos:
    def __init__(self):
        self.cache = {}

    def __call__(self, nombre):
        if nombre not in self.cache:
            im = Image.open(AQUI / "imagenes" / FOTOS[nombre]).convert("L")
            im = ImageEnhance.Contrast(im).enhance(1.12)
            esc = H * 1.3 / im.height  # margen para el zoom
            im = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
            im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=2))
            # tono sepia muy suave, de foto antigua
            arr = np.asarray(im, np.float32)[:, :, None] * np.array([1.0, 0.96, 0.88], np.float32)
            self.cache[nombre] = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
        return self.cache[nombre]


def suave(x):
    return x * x * (3 - 2 * x)


def encuadre(foto, mov, u):
    """Recorte 9:16 que se mueve y acerca a lo largo del clip (u de 0 a 1)."""
    x0, x1, z0, z1 = mov
    u = suave(min(max(u, 0), 1))
    zoom = z0 + (z1 - z0) * u
    ch = foto.height / 1.3 / zoom  # alto visible en píxeles de la foto
    cw = ch * W / H
    cx = cw / 2 + (foto.width - cw) * (x0 + (x1 - x0) * u)
    cy = foto.height / 2
    a = cw / W
    return foto.transform((W, H), Image.AFFINE, (a, 0, cx - cw / 2, 0, a, cy - ch / 2), Image.BICUBIC)


def viñeta():
    y = np.linspace(-1, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    v = 1 - 0.35 * np.clip(x ** 2 * 0.8 + y ** 2 * 0.6 - 0.2, 0, 1)
    arriba = np.clip(1 - (y + 1) / 2 / 0.2, 0, 1) ** 1.5 * 0.5
    return (v * (1 - arriba))[:, :, None].astype(np.float32)


# =================================================================== textos
def fuente(tam):
    return ImageFont.truetype(str(FUENTE), tam)


def texto_centrado(draw, y, lineas, tam, color, borde=8):
    f = fuente(tam)
    for linea in lineas:
        ancho = draw.textlength(linea, font=f)
        draw.text(((W - ancho) / 2, y), linea, font=f, fill=color, stroke_width=borde, stroke_fill=(0, 0, 0))
        y += tam * 1.18
    return y


def capa_cartel(grandes, chicas, color, u, quedan):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    alfa = int(255 * min(1, u / 0.35, max(quedan, 0) / 0.35))
    tam = int(118 * (1 + 0.1 * max(0, 1 - u / 0.25)))  # pequeño 'pop' al aparecer
    if max(len(g) for g in grandes) > 11:
        tam = int(tam * 0.85)
    y = texto_centrado(d, H * 0.13, grandes, tam, color + (alfa,), borde=10)
    texto_centrado(d, y + 20, chicas, 66, (255, 255, 255, alfa), borde=7)
    return capa


def partir(texto, max_palabras=4):
    """Subtítulos al estilo TikTok: pocas palabras cada vez."""
    grupos, actual = [], []
    for w in texto.split():
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
    """Grupos de pocas palabras que aparecen justo cuando la voz los dice."""
    out = []
    for _, _, _, palabras in subs:
        i = 0
        for g in partir(" ".join(w[2] for w in palabras)):
            n = len(g.split())
            out.append((palabras[i][0], palabras[i + n - 1][1], g))
            i += n
    # cada grupo se queda en pantalla hasta que empieza el siguiente (si la pausa es corta)
    return [(a, min(b + 0.6, out[k + 1][0]) if k + 1 < len(out) else b + 0.6, g)
            for k, (a, b, g) in enumerate(out)]


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
    tam = int(84 * escala)
    lineas = ajustar(texto.upper().rstrip(".,:;"), tam)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    alto = len(lineas) * tam * 1.18
    texto_centrado(d, H * 0.70 - alto / 2, lineas, tam, (255, 255, 255), borde=9)
    return capa


def degradado_abajo():
    y = np.linspace(0, 1, H)[:, None, None]
    return (1 - np.clip((y - 0.5) / 0.35, 0, 1) ** 1.3 * 0.5).astype(np.float32)


# =================================================================== audio
def musica(estado, dur):
    """SN.musica con la duración redondeada a acordes completos (si no, el último arpegio se sale)."""
    acorde = 2 * 4 * 60 / SN.ESTADOS[estado]["bpm"]
    return SN.musica(estado, np.ceil(dur / acorde) * acorde - 0.01)


def leer_voz(ruta):
    a, sr = sf.read(ruta, dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    if sr != SN.SR:
        a = resample_poly(a, SN.SR, sr).astype(np.float32)
    return a


def audio(inicios, voz_wav, total, ruta):
    n = SN.seg(total)
    voz = np.zeros(n + SN.SR * 2, np.float32)
    a = leer_voz(voz_wav)
    voz[SN.seg(INICIO): SN.seg(INICIO) + len(a)] += a
    voz = voz[:n]
    mezcla = np.zeros((n + SN.SR * 10, 2), np.float32)

    def poner(s, t, v):
        i = SN.seg(t)
        mezcla[i: i + len(s)] += s[: len(mezcla) - i] * v

    t_fecha, t_llamas, t_victimas = inicios[3], inicios[4], inicios[5]
    poner(musica("misterio", t_fecha + 2), 0, 0.8)
    poner(musica("tension", t_victimas - t_fecha + 2), t_fecha - 1, 0.85)
    poner(musica("triste", total - t_victimas + 2), t_victimas - 1, 0.85)
    poner(SN.impacto(), 0.0, 0.6)
    poner(SN.viento(t_fecha, 0.4), 0.0, 0.35)
    poner(SN.latido(t_llamas - t_fecha, 72), t_fecha, 0.5)
    poner(SN.impacto(), t_llamas - 0.1, 0.9)
    poner(SN.canon(0.4), t_llamas, 0.6)
    poner(SN.fuego(t_victimas - t_llamas + 3, 1.0), t_llamas, 0.8)
    poner(SN.fuego(inicios[6] - t_victimas, 0.4), t_victimas, 0.4)
    poner(SN.timbal(55.0), t_victimas, 0.6)
    poner(SN.impacto(), inicios[9], 0.5)
    musica_ = mezcla[:n]
    # la música baja mientras habla la voz
    env = np.convolve(np.abs(voz), np.ones(SN.SR // 10) / (SN.SR // 10), "same")
    env = np.clip(env / (env.max() * 0.15), 0, 1)
    env = np.convolve(env, np.ones(SN.SR // 4) / (SN.SR // 4), "same")
    musica_ *= (1 - 0.6 * env)[:, None]
    final = musica_ * 0.5 + SN.estereo(voz * 1.4)
    fade = SN.seg(2.0)
    final[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sf.write(ruta, SN.normal(final, 0.95), SN.SR, subtype="PCM_16")


# =================================================================== render
def main():
    salida = Path(sys.argv[1])
    salida.mkdir(parents=True, exist_ok=True)
    voz = json.loads((salida / "voz.json").read_text())
    inicios, clips, carteles, subs, total = construir(voz)
    bloques = bloques_subtitulos(subs)
    with open(salida / "hindenburg.srt", "w", encoding="utf-8") as f:
        hms = lambda s: f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(s % 1 * 1000):03d}"
        for i, (a, b, texto, _) in enumerate(subs, 1):
            f.write(f"{i}\n{hms(a)} --> {hms(b)}\n{texto}\n\n")

    wav = salida / "audio.wav"
    audio(inicios, voz["wav"], total, wav)
    fotos, vin = Fotos(), viñeta() * degradado_abajo()
    mp4 = salida / "Hindenburg_TikTok.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    n_cuadros = int(total * FPS)
    for k in range(n_cuadros):
        t = k / FPS
        cuadro = None
        for c in clips:
            if not c["ini"] - XF / 2 <= t < c["ini"] + c["dur"] + XF / 2:
                continue
            im = encuadre(fotos(c["img"]), c["mov"], (t - c["ini"] + XF / 2) / (c["dur"] + XF))
            cuadro = im if cuadro is None else Image.blend(cuadro, im, min(1, (t - c["ini"] + XF / 2) / XF))
        arr = np.asarray(cuadro).astype(np.float32) * vin
        arr *= 1 + rng.normal(0, 0.012)  # parpadeo de película antigua
        if t < 0.3:
            arr *= t / 0.3
        if t > total - 1.2:
            arr *= max(0, (total - t) / 1.2)
        cuadro = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
        for a, b, grandes, chicas, color in carteles:
            if a <= t < min(b, total):
                cuadro.alpha_composite(capa_cartel(grandes, chicas, color, t - a, min(b, total - 1.2) - t + 0.35))
        for a, b, texto in bloques:
            if a <= t < b + 0.05:
                cuadro.alpha_composite(capa_subtitulo(texto, (t - a) / max(b - a, 0.01)))
                break
        proc.stdin.write(cuadro.convert("RGB").tobytes())
        if k % 300 == 0:
            print(f"{k / n_cuadros * 100:.0f}%", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"Listo: {mp4} ({total:.1f} s)")


if __name__ == "__main__":
    main()
