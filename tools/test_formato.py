# -*- coding: utf-8 -*-
"""El formato de los reels con la estética nueva del bot (03/10/2026) y la imagen que usan.
Sin red: las descargas, el motor y las redes se reemplazan.

- Lo horizontal sale 4:5: Facebook lo recibe en una copia 9:16 con bandas grafito, y el
  corte de la placa final para YouTube compara contra la placa recortada como el motor.
- La imagen del reel es SIEMPRE la foto o el video original de la nota (decisión del
  editor del 05/10: nada de reemplazarla por otra para esquivar el logo de un medio).
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from PIL import Image

from reels import flujo as F, publicador as PUB, reel_bot as R

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


tmp = Path(tempfile.mkdtemp(prefix="formato_"))

# --- 1. La placa final, recortada como en el reel 4:5 ------------------------------------
placa = Image.new("L", (1080, 1920), 0)
chequear("placa al cuadro: en un reel 4:5 se compara contra la placa recortada a 1080x1350",
         R._placa_al_cuadro(placa, (1080, 1350)).size == (1080, 1350))
chequear("placa al cuadro: en 9:16 queda entera", R._placa_al_cuadro(placa, (1080, 1920)).size == (1080, 1920))
chequear("a_9x16: un reel 9:16 no se toca", R.a_9x16_si_hace_falta(tmp / "x.mp4", tmp / "y.mp4", 1920) is None)

# --- 2. Facebook recibe 9:16 -----------------------------------------------------------
mp4 = tmp / "reel.mp4"
mp4.write_bytes(b"x")
convertidos = []
original_a9 = R.a_9x16_si_hace_falta
try:
    R.a_9x16_si_hace_falta = lambda src, dst, alto=0: convertidos.append(alto) or Path(dst)
    chequear("Facebook: un reel 4:5 sube en su copia 9:16",
             PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp).parent == tmp and convertidos)
    convertidos.clear()
    chequear("Facebook: un reel 9:16 (o una pieza vieja sin medidas) sube tal cual",
             PUB._para_facebook({"video": {"alto": 1920}}, mp4, tmp / "otra") == mp4
             and PUB._para_facebook({"video": {}}, mp4, tmp / "otra") == mp4 and not convertidos)
    os.environ["FB_9X16"] = "0"
    chequear("Facebook: FB_9X16=0 sube siempre el original",
             PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp / "otra") == mp4)
    os.environ.pop("FB_9X16")
    R.a_9x16_si_hace_falta = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ffmpeg"))
    chequear("Facebook: si la copia falla, va el original (nunca frena la subida)",
             PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp / "otra") == mp4)
finally:
    R.a_9x16_si_hace_falta = original_a9

# --- 3. La imagen del reel es la ORIGINAL de la nota (05/10) ------------------------------
foto = tmp / "original.jpg"
Image.new("RGB", (800, 600), (90, 90, 90)).save(foto, "JPEG")
usadas = []


def foto_usable_falsa(nota, destino):
    Path(destino).write_bytes(foto.read_bytes())
    return Path(destino), nota["imagen"], ""


reemplazos = {"_bajar_video": lambda url, destino: None, "material": lambda nota: nota,
              "_foto_usable": foto_usable_falsa}
guardados = {k: getattr(F, k) for k in reemplazos}
armar, generar = F.R.armar, F.G.generar
try:
    for k, v in reemplazos.items():
        setattr(F, k, v)
    F.R.armar = lambda g, salida, foto=None, clip=None: usadas.append(foto) or {
        "duracion": 13, "peso_kb": 120, "tramos": ["nota"], "alto": 1350}
    F.G.generar = lambda nota, **k: {"volanta": "Robo en Junín", "titular": "Robaron una moto en pleno centro de Junín",
                                     "bajada": "La moto estaba estacionada frente a un comercio de la avenida.",
                                     "zocalo": "Robo", "pie": "x", "via": "gemini:falso", "tipo": "robo",
                                     "descripcion_final": "Texto", "fuera_de_temario": "", "copia": {}}
    carpeta = tmp / "lote"
    carpeta.mkdir()
    p = F.procesar({"url": "https://medio.test/a", "titulo": "Robo", "localidad_medio": "Junín",
                    "imagen": "https://medio.test/foto-con-logo.jpg"}, carpeta, True, 1)
    chequear("el reel se arma con la foto de la nota, tal cual", p["apto_para_publicar"] and usadas
             and Path(usadas[0]).read_bytes() == foto.read_bytes())
    chequear("...y la nota de la web lleva esa misma foto",
             p["imagen_url"] == "https://medio.test/foto-con-logo.jpg")
    chequear("...sin nada de imágenes de reemplazo", "imagen_ilustrativa" not in p
             and not any("marca" in a or "ilustrativa" in a for a in p["avisos"]))
finally:
    for k, v in guardados.items():
        setattr(F, k, v)
    F.R.armar, F.G.generar = armar, generar

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
