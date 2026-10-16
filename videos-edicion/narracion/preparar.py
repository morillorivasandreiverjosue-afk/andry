#!/usr/bin/env python3
"""Prepara un guion para narrarlo con ElevenLabs.

Lee un guion de texto, lo divide en partes (una por capítulo, sin pasar de
max_caracteres), aplica el diccionario de pronunciación y las etiquetas de estilo
de voz.json, y guarda el trabajo en <salida>/trabajo.json y <salida>/textos/.

Formato del guion (texto plano):
  - Los párrafos se separan con una línea en blanco.
  - "## TÍTULO" o una línea en MAYÚSCULAS que empiece por CAPÍTULO / INTRODUCCIÓN / FINAL
    marca un capítulo nuevo (se lee en voz alta).
  - Las líneas que empiezan por "@" o "# " se ignoran (sirven para los videos).

Uso:
  python3 narracion/preparar.py mi_guion.txt -o narracion/proyectos/mi-video
"""
import argparse
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CAPITULO = re.compile(r"^(CAP[IÍ]TULO\b|INTRODUCCI[OÓ]N\b|FINAL\b|EP[IÍ]LOGO\b|PR[OÓ]LOGO\b)")


def cargar(nombre):
    datos = json.loads((AQUI / nombre).read_text(encoding="utf-8"))
    return {k: v for k, v in datos.items() if not k.startswith("_")}


def leer_capitulos(ruta):
    capitulos, actual, parrafo = [], {"titulo": None, "parrafos": []}, []

    def cerrar_parrafo():
        if parrafo:
            actual["parrafos"].append(" ".join(parrafo))
            parrafo.clear()

    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        s = linea.strip()
        if s.startswith("@") or s.startswith("# ") or s == "#":
            cerrar_parrafo()
            continue
        if not s:
            cerrar_parrafo()
            continue
        titulo = s[3:].strip() if s.startswith("## ") else (s if CAPITULO.match(s) and s.upper() == s else None)
        if titulo:
            cerrar_parrafo()
            if actual["titulo"] or actual["parrafos"]:
                capitulos.append(actual)
            actual = {"titulo": titulo, "parrafos": []}
        else:
            parrafo.append(s)
    cerrar_parrafo()
    if actual["titulo"] or actual["parrafos"]:
        capitulos.append(actual)
    return capitulos


def pronunciar(texto, dic):
    for orig in sorted(dic, key=len, reverse=True):
        texto = re.sub(rf"(?<!\w){re.escape(orig)}(?!\w)", dic[orig], texto)
    return texto


def titulo_hablado(t):
    if t.isupper():
        t = t.lower()
    return ". ".join(x.strip()[:1].upper() + x.strip()[1:] for x in t.split(":")) + "."


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("guion")
    p.add_argument("-o", "--salida", required=True, help="carpeta del proyecto de narración")
    args = p.parse_args()

    voz = cargar("voz.json")
    dic = cargar("pronunciacion.json")
    estilo = voz["estilo"]
    maximo = voz["partes"]["max_caracteres"]
    if not voz.get("voice_id"):
        raise SystemExit("voz.json no tiene voice_id. Elige una voz antes de preparar el guion.")

    partes = []

    def nueva(titulo):
        partes.append({"capitulo": titulo, "bloques": []})

    for cap in leer_capitulos(args.guion):
        nueva(cap["titulo"])
        for par in cap["parrafos"]:
            largo = sum(len(b) + 1 for b in partes[-1]["bloques"])
            if partes[-1]["bloques"] and largo + len(par) > maximo:
                nueva(cap["titulo"])
            partes[-1]["bloques"].append(par)

    salida = Path(args.salida)
    (salida / "textos").mkdir(parents=True, exist_ok=True)
    trabajo = {"voice_id": voz["voice_id"], "voice_nombre": voz["voice_nombre"], "modelo": voz["modelo"],
               "variaciones_por_parte": voz["partes"]["variaciones_por_parte"], "partes": []}
    total = 0
    for i, parte in enumerate(partes, 1):
        cuerpo = f" {estilo['pausa_entre_parrafos']} ".join(pronunciar(b, dic) for b in parte["bloques"])
        es_inicio = i == 1 or partes[i - 2]["capitulo"] != parte["capitulo"]
        if parte["capitulo"] and es_inicio:
            cuerpo = f"{titulo_hablado(parte['capitulo'])} {estilo['pausa_capitulo']} {cuerpo}"
        texto = f"{estilo['etiqueta_inicial']} {cuerpo}".strip()
        nombre = f"parte-{i:02d}"
        (salida / "textos" / f"{nombre}.txt").write_text(texto + "\n", encoding="utf-8")
        trabajo["partes"].append({"parte": nombre, "capitulo": parte["capitulo"], "caracteres": len(texto),
                                  "texto": texto, "url": None, "generation_id": None})
        total += len(texto)
    (salida / "trabajo.json").write_text(json.dumps(trabajo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(partes)} partes, {total} caracteres en total -> {salida / 'trabajo.json'}")
    print(f"Voz: {voz['voice_nombre']} ({voz['voice_id']}), modelo {voz['modelo']}")
    for pt in trabajo["partes"]:
        print(f"  {pt['parte']}  {pt['caracteres']:>5} car.  {pt['capitulo'] or ''}")


if __name__ == "__main__":
    main()
