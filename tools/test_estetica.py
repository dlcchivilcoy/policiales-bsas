# -*- coding: utf-8 -*-
"""Que los reels de policiales salgan con el motor del bot, y que el motor ande aca.

    venv\\Scripts\\python.exe tools\\test_estetica.py            # completo (~2 min)
    venv\\Scripts\\python.exe tools\\test_estetica.py --rapido   # sin el autochequeo del bot

Correrlo SIEMPRE despues de tools\\traer_estetica_bot.py: el adaptador usa algunas
piezas internas del motor, y un cambio en el bot puede renombrarlas.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import entorno
from reels import reel_bot as R

entorno.consola_utf8()
fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


def foto_de_prueba(ruta: Path, w: int, h: int):
    """Una 'foto' con degrade y grano: lisa del todo, el motor la tomaria por un afiche."""
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(1)
    y, x = np.mgrid[0:h, 0:w]
    rgb = np.stack([80 + 120 * x / w, 60 + 100 * y / h, 90 + 60 * (x + y) / (w + h)], -1)
    rgb += rng.normal(0, 18, rgb.shape)
    Image.fromarray(np.clip(rgb, 0, 255).astype("uint8")).save(ruta, quality=90)
    return ruta


GUION = {"volanta": "Robo en Junín", "titular": "Detuvieron a dos hombres por un robo en una casa",
         "bajada": "Los sospechosos fueron aprehendidos tras un operativo. Secuestraron herramientas."}

chequear("el motor del bot esta completo en estetica_bot/", R.faltantes() == [])
chequear("se sabe de que commit del bot es", R.origen() not in ("", "?"))
chequear("la bajada de policiales va como «resumen» del bot",
         R._textos(GUION) == {"volanta": "Robo en Junín", "titular": GUION["titular"],
                              "resumen": GUION["bajada"]})
m = R.motor()
chequear("el motor que se usa es el del bot (estetica_bot/video.py)",
         Path(m.__file__).resolve() == (R.ESTETICA / "video.py").resolve())
chequear("peso de policiales: CRF 32 y techo 1500k (salvo que el entorno diga otra cosa)",
         os.environ.get("REEL_CRF") == "32" and os.environ.get("REEL_MAXRATE") == "1500k")

with tempfile.TemporaryDirectory(prefix="test_estetica_") as tmp:
    tmp = Path(tmp)
    # Estilo de los reels de WhatsApp del bot (03/10): lo horizontal ENTERO en 4:5, lo
    # vertical a sangre en 9:16.
    for forma, (w, h), cuadro in (("apaisada", (1600, 900), (1080, 1350)),
                                  ("vertical", (900, 1600), (1080, 1920))):
        salida_dir = tmp / forma
        salida_dir.mkdir()
        foto = foto_de_prueba(tmp / f"{forma}.jpg", w, h)
        info = R.armar(GUION, salida_dir / "reel.mp4", foto=foto)
        ancho, alto = m._dimensiones(Path(info["archivo"]))
        chequear(f"{forma}: reel {cuadro[0]}x{cuadro[1]}", (ancho, alto) == cuadro)
        chequear(f"{forma}: las medidas quedan en la pieza (Facebook las usa)",
                 (info.get("ancho"), info.get("alto")) == cuadro)
        chequear(f"{forma}: dura ~{R.SEG_REEL_FOTO:.0f} s (8 de nota + 5 de cierre)",
                 abs(info["duracion"] - R.SEG_REEL_FOTO) < 1.0)
        chequear(f"{forma}: liviano (menos de 1 MB)", info["peso_kb"] < 1024)
        chequear(f"{forma}: deja el cuadro fijo .jpg al lado", bool(info["placa"]) and Path(info["placa"]).exists())
        chequear(f"{forma}: en la carpeta quedan SOLO el .mp4 y el .jpg (nada de trabajo)",
                 sorted(p.name for p in salida_dir.iterdir()) == ["reel.jpg", "reel.mp4"])
    fija = R.placa_fija(GUION, foto_de_prueba(tmp / "fija.jpg", 1600, 900), tmp / "fija_placa.jpg")
    from PIL import Image
    chequear("vista rapida (--sin-video) de una apaisada: el mismo cuadro 4:5 del reel",
             Image.open(fija).size == (1080, 1350))
    chequear("el estilo es el de los reels de WhatsApp del bot", R.estilo() == "corresponsal")

if "--rapido" not in sys.argv:
    print("\n--- autochequeo del propio bot (ffmpeg, filtros, letras, maquetas, reels) ---")
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = m.autochequeo()
    if not ok:
        print(buf.getvalue())
    chequear("el autochequeo del bot pasa dentro de policiales", ok)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
