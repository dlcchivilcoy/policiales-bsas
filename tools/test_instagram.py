# -*- coding: utf-8 -*-
"""Cómo sale cada reel en Instagram. No usa la red.

Desde el 10/10/2026 (pedido del editor): reel NORMAL, al feed y a la pestaña de reels. La regla
de los reels de prueba (26/09 a 10/10) sigue en reels/instagram.py y se prueba prendiéndola.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reels import instagram as IG

URL = "https://ejemplo.com/reel.mp4"
fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


p = IG.contenedor_reel(URL, "Texto del posteo")
chequear("desde el 10/10 NO son reels de prueba", IG.SOLO_REELS_DE_PRUEBA is False)
chequear("es un reel", p["media_type"] == "REELS")
chequear("sin trial_params", "trial_params" not in p)
chequear("va al feed además de la pestaña de reels", p.get("share_to_feed") == "true")

# La regla de prueba, si algún día se vuelve a prender.
IG.SOLO_REELS_DE_PRUEBA = True
p = IG.contenedor_reel(URL, "x")
chequear("prendida: lleva trial_params con graduación automática",
         json.loads(p.get("trial_params", "{}")) == {"graduation_strategy": "SS_PERFORMANCE"}
         and "share_to_feed" not in p)
IG.GRADUACION = "ss_performance"
try:
    IG.contenedor_reel(URL, "x")
    chequear("prendida: una graduación mal escrita frena", False)
except ValueError:
    chequear("prendida: una graduación mal escrita frena", True)
IG.GRADUACION = "SS_PERFORMANCE"
IG.SOLO_REELS_DE_PRUEBA = False

try:
    IG.contenedor_reel("C:\\salida_reels\\reel.mp4", "x")
    chequear("un archivo local frena: Instagram necesita URL publica", False)
except ValueError:
    chequear("un archivo local frena: Instagram necesita URL publica", True)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
