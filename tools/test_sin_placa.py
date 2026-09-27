# -*- coding: utf-8 -*-
"""YouTube va sin la placa final (reel_bot.sin_placa_final), con reels REALES del motor.

Nació el 27/09/2026: YouTube elegía la placa «Seguinos en redes» de miniatura y la grilla
de Shorts del canal quedaba toda igual.
"""
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from reels import reel_bot as R

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


GUION = {"volanta": "Choque en la ruta", "titular": "Un auto y una camioneta chocaron en la Ruta 5",
         "bajada": "El conductor fue trasladado al hospital con heridas leves."}

m = R.motor()
placa = m._asset("REEL_PLACA_FINAL", m.PLACA_FINAL)
tmp = Path(tempfile.mkdtemp(prefix="sin_placa_"))
try:
    foto = tmp / "foto.jpg"
    im = Image.new("RGB", (1600, 900))
    px = im.load()
    for x in range(0, 1600, 4):                 # degradé con grano: una «foto», no un afiche
        for y in range(0, 900, 4):
            c = (x // 8 + random.randint(0, 30), y // 6, 120)
            for dx in range(4):
                for dy in range(4):
                    px[x + dx, y + dy] = c
    im.save(foto, quality=90)

    reel = tmp / "reel.mp4"
    R.armar(GUION, reel, foto=foto)
    dur = m.duration_seconds(reel)
    corto = R.sin_placa_final(reel, tmp / "corto.mp4")
    dc = m.duration_seconds(corto) if corto else 0
    chequear(f"el reel entero ({dur:.1f} s) termina en la placa", R._parecido_a_placa(reel, dur - 1, placa, tmp) < R.UMBRAL_PLACA)
    chequear(f"el corte saca justo la placa ({dc:.1f} s ≈ {dur:.1f} - 5)", corto and abs(dc - (dur - 5.2)) < 0.3)
    chequear("el último cuadro del corte es la nota, no la placa ni el fundido a negro",
             corto and R._parecido_a_placa(corto, dc - 0.05, placa, tmp) > 60)
    chequear("un reel ya cortado no se vuelve a cortar", R.sin_placa_final(corto, tmp / "otra.mp4") is None)

    os.environ["REEL_PLACA_FINAL"] = "0"        # el motor sin placa (como su escalón de emergencia)
    try:
        sin = tmp / "sin.mp4"
        R.armar(GUION, sin, foto=foto)
    finally:
        os.environ.pop("REEL_PLACA_FINAL")
    chequear("un reel que NO trae placa no se toca (no se le come la nota)",
             R.sin_placa_final(sin, tmp / "sin_corto.mp4") is None)
    chequear("un archivo que no es video devuelve None, sin romper",
             R.sin_placa_final(foto, tmp / "x.mp4") is None)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
