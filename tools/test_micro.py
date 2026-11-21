# -*- coding: utf-8 -*-
"""Pruebas de las micro animaciones de las placas (agro/micro.py, 21/11/2026) y de dónde se usan: el resumen
«El campo hoy» (agro/historias.py + agro/reel_datos.py), el mapa de lluvias y el reel de «Los números de la semana».

    python tools/test_micro.py
"""
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from agro import historias as HI  # noqa: E402
from agro import micro as MI  # noqa: E402
from agro import reel_datos as RD  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


def igual(a, b) -> bool:
    return np.array_equal(np.asarray(a.convert("RGB")), np.asarray(b.convert("RGB")))


# Una placa de prueba: fondo gris, un título, dos tarjetas en la misma fila y un pie.
fondo = Image.new("RGB", (600, 800), (24, 26, 30))
final = fondo.copy()
d = ImageDraw.Draw(final)
d.rectangle((40, 40, 400, 90), fill=(255, 255, 255))
d.rectangle((40, 150, 280, 300), fill=(60, 64, 70))
d.rectangle((320, 150, 560, 300), fill=(60, 64, 70))
d.rectangle((40, 700, 300, 720), fill=(200, 200, 200))
grupos = MI.franjas(MI.contenido(final, fondo))
chequear("encuentra 3 franjas (título, tarjetas, pie)", len(grupos) == 3)
chequear("las dos tarjetas de la fila son dos bloques", len(grupos[1]) == 2)

an = MI.Animacion(final, fondo, inicio=0.2)
chequear("en el primer cuadro todavía no hay nada (es el fondo)", igual(an(0.0), fondo))
chequear("a mitad de camino hay algo pero no todo", not igual(an(0.45), fondo) and not igual(an(0.45), final))
chequear("al terminar es la placa completa", igual(an(an.fin + 0.01), final))
chequear("un tiempo de sonido por franja, en orden", len(an.tiempos) == 3 and an.tiempos == sorted(an.tiempos))
chequear("todo entra en menos de 2,5 s", an.fin < 2.5)
ev = MI.eventos(an.tiempos, 10.0)
chequear("los pops del sonido arrancan con la placa", len(ev) == 3 and abs(ev[0][0] - 10.2) < 1e-6)

# Un especial (un mapa propio) reemplaza al recorte de su franja y puede seguir moviéndose.
llamadas = []


def mapa(p):
    llamadas.append(p)
    return Image.new("RGBA", (240, 150), (0, 200, 0, 255))


an = MI.Animacion(final, fondo, especiales=[{"caja": (40, 150, 520, 150), "fn": mapa, "dur": 1.0, "continuo": True}])
cuadro = an(3.0)
chequear("el especial se dibuja con su función y sigue después de entrar", llamadas and cuadro.getpixel((100, 200)) == (0, 200, 0))

# Las placas del resumen quedan anotadas al guardarse, con su fondo.
with tempfile.TemporaryDirectory() as tmp:
    im, dr = HI.lienzo()
    y = HI.encabezado(im, dr, "EL CAMPO HOY", "Prueba de placa", "subtítulo")
    for k in range(3):
        HI.tarjeta(dr, y, 110)
        dr.text((80, y + 20), f"Fila {k}", font=HI.D.fuente("bold", 38), fill=(255, 255, 255))
        y += 130
    HI.pie(dr, "prueba")
    destino = HI.guardar(im, Path(tmp) / "placa.jpg")
    reg = HI.ANIMABLES.get(str(HI.ruta_45(destino)))
    chequear("la placa 4:5 queda anotada con su fondo", reg is not None and reg["final"].size == (1080, 1350))
    fn, pops = RD._animada(HI.ruta_45(destino), 4.2)
    chequear("el reel la anima por partes (no el acercamiento de antes)", isinstance(fn, MI.Animacion) and len(pops) >= 5)
    chequear("y termina igual a la placa publicada", igual(fn(4.0), reg["final"]))
    fn2, pops2 = RD._animada(Path(tmp) / "otra.jpg", 4.2) if (Path(tmp) / "otra.jpg").write_bytes(
        Path(HI.ruta_45(destino)).read_bytes()) else (None, None)
    chequear("una placa que no está anotada vuelve al acercamiento", not isinstance(fn2, MI.Animacion) and pops2 == [])

    # El mapa de lluvias: se arma desde Chivilcoy.
    from agro import mapa_lluvia as ML
    grilla = [[(4.0 if abs(i - 6) < 3 and abs(j - 6) < 3 else 0.0) for j in range(ML.NODOS + 2)] for i in range(ML.NODOS + 2)]
    fm = ML.mapa_animado({"grilla": grilla}, 300)
    a0, a1 = fm(0.0), fm(1.0)
    chequear("el mapa de lluvias arranca invisible y termina armado",
             a0.getchannel("A").getbbox() is None and a1.getchannel("A").getbbox() is not None)
    chequear("Chivilcoy queda marcado en naranja", (np.asarray(a1)[:, :, :3] == HI.D.NARANJA).all(axis=2).sum() > 50)

# AGRO_MICRO=0: la placa quieta de antes.
import os  # noqa: E402
os.environ["AGRO_MICRO"] = "0"
chequear("AGRO_MICRO=0 lo apaga", not MI.activo())
os.environ.pop("AGRO_MICRO")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
