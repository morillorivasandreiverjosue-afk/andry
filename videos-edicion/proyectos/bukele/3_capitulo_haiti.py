"""Paso 3: Capítulo 21 — "10 de noviembre de 2026: Nayib Bukele y Haití".

  python3 3_capitulo_haiti.py            # renderiza el capítulo suelto (para revisarlo)
  python3 3_capitulo_haiti.py --pegar    # lo inserta en el documental, antes de la Conclusión

Voz: audio/parte5.mp3 (ElevenLabs). Frases y tiempos: transcripcion/parte5.json.
Salida: salida/corta/Capitulo_21_Haiti.mp4 y, con --pegar,
        salida/corta/Nayib_Bukele_documental_con_Haiti.mp4 (un solo archivo de menos de 400 MB).
"""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

AQUI = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("montaje", AQUI / "2_montaje.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
SN, SR = M.SN, M.SN.SR
SALIDA = M.SALIDA
TITULO = "10 de noviembre de 2026: Nayib Bukele y Haití"
INICIO = 0.8          # silencio antes de la voz (entra el rótulo)


def ov(texto):
    """Archivo de Openverse cuyo título contiene `texto` (para no escribir los ids a mano)."""
    encontrados = sorted(k for k, v in M.CREDITOS.items() if k.startswith("ov_") and texto.lower() in
                         (v.get("titulo") or "").lower())
    if not encontrados:
        raise SystemExit(f"falta descargar una imagen con «{texto}» en el título")
    return encontrados


def F(archivo, **o):
    return dict(tipo="foto", archivo=archivo, **o)


def plan_haiti():
    dss = ov("DSS Response to Haiti")
    mss = ov("MSS force")[0]
    mapa_pandillas = ov("Gang war in Haiti")[0]
    pap = ov("Port")
    palacio = ov("National Palace")[0]
    soldados = "Soldados de la FAES.jpg"
    return [   # (frase de transcripcion/parte5.json, toma)
        (2, dict(tipo="mapa", cual="caribe")),
        (3, F(dss[0])),
        (3.5, F(pap[0])),
        (4, F("Nayib Bukele with military officers.jpg", fecha="10 de noviembre de 2026", lugar="Haití")),
        (4.5, F(dss[1], zoom="out")),
        (5, F(mapa_pandillas, zoom="out")),
        (6, F(dss[2])),
        (7, F(soldados)),
        (7.5, F(mss)),
        (8, F(dss[3], zoom="out")),
        (9, F("Salvadoran Army patrol in Santa Tecla, El Salvador (July 2022).jpg",
              texto_grande="¿POR QUÉ ESTÁN EN HAITÍ?")),
        (11, F(dss[4])),
        (12, F(pap[1 % len(pap)], fecha="18 de octubre de 2026", lugar="Desaparecen cuatro técnicos salvadoreños")),
        (14, dict(tipo="dato", cifra="+2000", texto="militares salvadoreños desplegados en Haití",
                  fondo=soldados, sub="Según Al Jazeera, a partir de octubre de 2026")),
        (15, F(pap[2 % len(pap)], fecha="6 de noviembre de 2026", lugar="Apoyo a los soldados salvadoreños")),
        (16.5, F(dss[5 % len(dss)])),
        (17, dict(tipo="mapa", cual="caribe")),
        (18, F("Nayib Bukele saluting soldiers at his 2024 inauguration.jpg", zoom="out")),
        (19, F(dss[6 % len(dss)])),
        (20, F(palacio)),
        (20.5, F(pap[3 % len(pap)], zoom="out")),
        (21, F(dss[7 % len(dss)])),
        (22, F(dss[8 % len(dss)], zoom="out")),
        (24, F(mss, zoom="out")),
        (25, F("Inter-American Commission on Human Rights (2021).jpg")),
        (26, F(dss[9 % len(dss)])),
        (27, F(pap[4 % len(pap)], zoom="out")),
        (29, F("Nayib Bukele at Shield of the Americas (IMG 3387).jpg", zoom="out")),
    ]


def construir():
    fr = json.loads((AQUI / "transcripcion" / "parte5.json").read_text())
    for f in fr:
        f["ini"] += INICIO
        f["fin"] += INICIO
    total = fr[-1]["fin"] + 1.4
    clips = [dict(tipo="capitulo", etiqueta="CAPÍTULO 21", titulo=TITULO, ini=0.0, fin=fr[1]["fin"] + 1.0)]
    tomas = []
    for ancla, t in plan_haiti():
        i = int(ancla)
        tomas.append(dict(t, ini=max(clips[0]["fin"], fr[i]["ini"] + (ancla - i) * (fr[i]["fin"] - fr[i]["ini"]) - 0.25)))
    tomas.sort(key=lambda x: x["ini"])
    for a, b in zip(tomas, tomas[1:] + [None]):
        a["fin"] = b["ini"] if b else total
    clips += [t for t in tomas if t["fin"] - t["ini"] >= 1.2]
    clips[0]["fondo"] = clips[1].get("archivo") or "Soldados de la FAES.jpg"
    destellos = [c["ini"] for c in clips if c["tipo"] == "dato"]
    return dict(clips=clips, total=total, frases=fr, destellos=destellos)


def audio(tl, ruta):
    voz, sr = sf.read(AQUI / "salida" / "haiti_voz.wav", dtype="float32")
    n = int(tl["total"] * SR)
    v = np.zeros(n, np.float32)
    i0 = int(INICIO * SR)
    v[i0: i0 + len(voz)] = voz[: n - i0]
    musica = SN.musica("tension", tl["total"] + 3)[:n]
    g = SN.impacto() * 0.35
    w = SN.whoosh(1.4) * 0.18
    musica[: len(g)] += g[:n]
    musica[: len(w)] += w[:n]
    for d0 in tl["destellos"]:
        k = int(d0 * SR)
        g = SN.impacto() * 0.45
        musica[k: k + len(g)] += g[: n - k]
    env = np.convolve(np.abs(v), np.ones(int(0.35 * SR), np.float32) / int(0.35 * SR), mode="same")
    habla = np.clip(env / 0.02, 0, 1)
    paso = int(0.05 * SR)
    hs = habla[::paso]
    for j in range(1, len(hs)):
        hs[j] = max(hs[j], hs[j - 1] * 0.93)
    habla = np.repeat(hs, paso)[:n]
    habla = np.pad(habla, (0, n - len(habla)), mode="edge")
    mezcla = np.repeat(v[:, None], 2, 1) + musica * (0.42 - 0.30 * habla)[:, None]
    f = int(0.6 * SR)
    mezcla[-f:] *= np.linspace(1, 0, f)[:, None]
    # mismo nivel que el documental
    ref, _ = sf.read(SALIDA / "audio_final.wav", dtype="float32", frames=SR * 120, start=SR * 300)
    mezcla *= np.sqrt((ref ** 2).mean() / max((mezcla ** 2).mean(), 1e-9))
    mezcla = np.clip(mezcla, -0.98, 0.98)
    sf.write(ruta, mezcla, SR, subtype="PCM_16")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pegar", action="store_true")
    a = ap.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    cap = SALIDA / "Capitulo_21_Haiti.mp4"
    if not a.pegar:
        # voz: del mp3 a wav, sin silencios largos al principio ni al final
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(AQUI / "audio" / "parte5.mp3"), "-ac", "1",
                        "-ar", str(SR), str(AQUI / "salida" / "haiti_voz.wav")], check=True)
        tl = construir()
        audio(tl, SALIDA / "haiti_audio.wav")
        r = M.Render(tl)
        nfr = int(tl["total"] * M.FPS)
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                              f"{M.W}x{M.H}", "-r", str(M.FPS), "-i", "-", "-i", str(SALIDA / "haiti_audio.wav"),
                              "-c:v", "libx264", "-preset", "medium", "-b:v", "2000k", "-maxrate", "2600k",
                              "-bufsize", "5200k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
                              "-shortest", "-movflags", "+faststart", str(cap)], stdin=subprocess.PIPE)
        for k in range(nfr):
            p.stdin.write(r.cuadro(k).tobytes())
        p.stdin.close()
        p.wait()
        print("Listo:", cap, f"({tl['total']:.1f} s)")
        return
    # --pegar: documental hasta la Conclusión + capítulo 21 + Conclusión y final
    clips = json.loads((SALIDA / "linea_de_tiempo.json").read_text())
    t_c = next(c["ini"] for c in clips if c["tipo"] == "capitulo" and c["etiqueta"] == "CONCLUSIÓN")
    doc = SALIDA / "Nayib_Bukele_documental.mp4"
    final = SALIDA / "Nayib_Bukele_documental_con_Haiti.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(doc), "-i", str(cap),
        "-filter_complex",
        f"[0:v]trim=0:{t_c},setpts=PTS-STARTPTS[v1];[0:a]atrim=0:{t_c},asetpts=PTS-STARTPTS,afade=t=out:st={t_c - 0.4}:d=0.4[a1];"
        f"[1:v]setpts=PTS-STARTPTS[v2];[1:a]asetpts=PTS-STARTPTS[a2];"
        f"[0:v]trim=start={t_c},setpts=PTS-STARTPTS[v3];[0:a]atrim=start={t_c},asetpts=PTS-STARTPTS,afade=t=in:d=0.3[a3];"
        "[v1][a1][v2][a2][v3][a3]concat=n=3:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-b:v", "1850k", "-maxrate", "2500k",
        "-bufsize", "5000k", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
        str(final)], check=True)
    print("Listo:", final)


if __name__ == "__main__":
    main()
