# -*- coding: utf-8 -*-
"""Reels 4:5 estilo bloque (12/10/2026): el bloque blanco y el grafito se ALTERNAN de un posteo al
otro. Arma dos reels de verdad con una foto apaisada (sin red ni IA)."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw  # noqa: E402

from reels import reel_bot as R  # noqa: E402
from tools.guardar_estado import combinar_tema  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


GUION = {"volanta": "Chacabuco · Policiales", "titular": "Detuvieron a dos jóvenes por el robo a un comercio",
         "bajada": "La Policía secuestró una moto.", "zocalo": "Robo"}

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    estado = tmp / "tema_reels.json"
    chequear("sin memoria arranca con el blanco", R.proximo_tema(estado) == "blanco")
    R.anotar_tema("blanco", estado)
    chequear("después del blanco va el grafito", R.proximo_tema(estado) == "grafito")
    R.anotar_tema("", estado)
    chequear("un reel 9:16 (tema vacío) no mueve la alternancia", R.proximo_tema(estado) == "grafito")
    viejo = {"ultimo": "blanco", "cuando": 10}
    nuevo = {"ultimo": "grafito", "cuando": 20}
    chequear("al combinar dos pasadas gana el más nuevo",
             combinar_tema(viejo, nuevo) == nuevo and combinar_tema(nuevo, viejo) == nuevo)

    foto = tmp / "apaisada.jpg"
    im = Image.new("RGB", (1600, 900), (70, 110, 150))
    dib = ImageDraw.Draw(im)
    for k in range(0, 2600, 60):                    # textura: que no parezca un afiche
        dib.line((k, 0, k - 900, 900), fill=(90 + k % 80, 130, 170 - k % 60), width=25)
    im.save(foto, quality=90)
    m = R.motor()
    for tema in ("blanco", "grafito"):
        info = R.armar(GUION, tmp / f"reel_{tema}.mp4", foto=foto, tema=tema)
        chequear(f"foto apaisada → 4:5 con el bloque {tema}",
                 (info["ancho"], info["alto"]) == (1080, 1350) and info["tema"] == tema)
        cuadro = Image.open(info["placa"]).convert("RGB")
        fondo = m.BLOQUE_TEMAS[tema]["fondo"][:3]
        px = cuadro.getpixel((1040, 1320))           # abajo a la derecha: el bloque, sin texto
        chequear(f"el bloque {tema} es del color del tema ({px})",
                 all(abs(a - b) < 18 for a, b in zip(px, fondo)))
        arriba = cuadro.getpixel((540, 20))
        chequear(f"la imagen arranca arriba de todo ({arriba})",
                 not all(abs(a - b) < 18 for a, b in zip(arriba, fondo)))
    vertical = tmp / "vertical.jpg"
    im.rotate(90, expand=True).save(vertical, quality=90)
    info = R.armar(GUION, tmp / "reel_v.mp4", foto=vertical, tema="blanco")
    chequear("foto vertical → 9:16, sin tema que anotar", info["alto"] == 1920 and info["tema"] == "")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
