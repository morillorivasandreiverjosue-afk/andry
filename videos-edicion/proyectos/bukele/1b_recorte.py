"""Paso 1b: versión corta (~25 min) con un avance impactante al principio.

Toma salida/voz.wav + voz.json (de 1_voz.py) y:
  1. Monta un AVANCE con las frases más fuertes del documental (plan.AVANCE).
  2. Sigue con la narración completa en orden, pero sin las frases de plan.QUITAR
     (repeticiones, explicaciones largas, detalles secundarios) ni las palabras
     "Introducción" / "Conclusión" (el rótulo solo sale escrito en pantalla).
Salida: salida/corta/voz.wav y salida/corta/voz.json (cada frase guarda su número original).

Uso: python3 1b_recorte.py
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

import plan

AQUI = Path(__file__).parent
SR = 44100
ANTES, DESPUES = 0.08, 0.16     # margen de audio alrededor de cada frase
PAUSA = 0.38                    # silencio al saltar frases quitadas
PAUSA_TITULO = 0.9              # silencio antes del título de cada capítulo
PAUSA_AVANCE = 0.75             # silencio entre frases del avance (para los golpes de sonido)
TRAS_AVANCE = 1.6               # silencio tras el avance: aparece el título NAYIB BUKELE


def main():
    voz, sr = sf.read(AQUI / "salida" / "voz.wav", dtype="float32")
    assert sr == SR
    fr = json.loads((AQUI / "salida" / "voz.json").read_text())["frases"]
    titulos = {i for i, _ in plan.CAPITULOS.values()} | set(plan.SECCIONES)
    trozos, frases, t = [], [], 0.0

    def silencio(s):
        nonlocal t
        trozos.append(np.zeros(int(s * SR), np.float32))
        t += s

    def tramo(i0, i1, avance=False):
        """Copia las frases i0..i1 (seguidas en el original) con sus pausas naturales."""
        nonlocal t
        a = max(0.0, fr[i0]["ini"] - ANTES)
        b = min(len(voz) / SR, fr[i1]["fin"] + DESPUES)
        x = voz[int(a * SR): int(b * SR)].copy()
        r = int(0.012 * SR)
        x[:r] *= np.linspace(0, 1, r)
        x[-r:] *= np.linspace(1, 0, r)
        for i in range(i0, i1 + 1):
            frases.append(dict(fr[i], orig=i, ini=round(t + fr[i]["ini"] - a, 3),
                               fin=round(t + fr[i]["fin"] - a, 3), avance=avance))
        trozos.append(x)
        t += len(x) / SR

    # 1) avance
    silencio(0.6)
    for k, i in enumerate(plan.AVANCE_FRASES):
        if k:
            silencio(PAUSA_AVANCE)
        tramo(i, i, avance=True)
    silencio(TRAS_AVANCE)
    # 2) narración sin las frases quitadas, en tramos de frases seguidas
    quedan = [i for i in range(len(fr)) if i not in plan.QUITAR]
    tramos, ini = [], quedan[0]
    for a, b in zip(quedan, quedan[1:] + [None]):
        if b is None or b != a + 1 or b in titulos:
            tramos.append((ini, a))
            ini = b
    for k, (i0, i1) in enumerate(tramos):
        if k:
            silencio(PAUSA_TITULO if i0 in titulos else PAUSA)
        tramo(i0, i1)
    silencio(1.0)
    y = np.concatenate(trozos)
    out = AQUI / "salida" / "corta"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "voz.wav", y, SR, subtype="PCM_16")
    (out / "voz.json").write_text(json.dumps({"duracion": len(y) / SR, "frases": frases}, ensure_ascii=False,
                                             indent=0))
    print(f"versión corta: {len(y) / SR / 60:.1f} min ({len(frases)} frases, {len(plan.QUITAR)} quitadas)")


if __name__ == "__main__":
    main()
