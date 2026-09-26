# -*- coding: utf-8 -*-
"""Que lo automatico en Instagram salga SIEMPRE como reel de prueba. No usa la red."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reels import instagram as IG

URL = "https://ejemplo.com/reel.mp4"
fallas = []


def chequear(nombre, condicion):
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


p = IG.contenedor_reel(URL, "Texto del posteo")
chequear("la regla esta encendida", IG.SOLO_REELS_DE_PRUEBA is True)
chequear("graduacion MANUAL: nada le llega solo a los seguidores", IG.GRADUACION == "MANUAL")
chequear("es un reel", p["media_type"] == "REELS")
chequear("lleva trial_params",
         json.loads(p.get("trial_params", "{}")) == {"graduation_strategy": "MANUAL"})

# Un valor mal escrito tiene que frenar, no caer en un reel normal.
IG.GRADUACION = "manual"
try:
    IG.contenedor_reel(URL, "x")
    chequear("graduacion mal escrita frena", False)
except ValueError:
    chequear("graduacion mal escrita frena", True)
IG.GRADUACION = "MANUAL"

try:
    IG.contenedor_reel("C:\\salida_reels\\reel.mp4", "x")
    chequear("un archivo local frena: Instagram necesita URL publica", False)
except ValueError:
    chequear("un archivo local frena: Instagram necesita URL publica", True)

print(f"\n--- {6 - len(fallas)}/6 correctos ---")
sys.exit(1 if fallas else 0)
