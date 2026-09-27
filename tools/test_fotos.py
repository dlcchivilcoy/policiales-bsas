# -*- coding: utf-8 -*-
"""Fotos con tamaño para un reel, y el video por sobre la foto. Sin red.

Nació el 27/09/2026: el reel de Chacabuco salió con una foto de 72x72 (la miniatura que da
el RSS de Blogger) y el editor pidió descartar las chicas y priorizar las notas con video.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
from reels import flujo as F
from scraper import fetch

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. Blogger / Google: pedir el tamaño original ---------------------------------------
mi = fetch.mejorar_imagen
B = "https://blogger.googleusercontent.com/img/b/R29v/AVvXsEg"
chequear("Blogger /s72-c/ -> /s1600/ (el caso de Chacabuco)",
         mi(f"{B}/s72-c/1001146373.webp") == f"{B}/s1600/1001146373.webp")
chequear("Blogger /w400-h300-rw/ -> /s1600/", mi(f"{B}/w400-h300-rw/foto.jpg") == f"{B}/s1600/foto.jpg")
chequear("Google al final (=s72-c) -> =s1600",
         mi("https://lh3.googleusercontent.com/abc123=s72-c") == "https://lh3.googleusercontent.com/abc123=s1600")
chequear("blogspot viejo también", mi("https://1.bp.blogspot.com/x/y/s320/a.jpg") == "https://1.bp.blogspot.com/x/y/s1600/a.jpg")
chequear("otro sitio con /s72/ en la ruta no se toca",
         mi("https://medio.com/s72/foto.jpg") == "https://medio.com/s72/foto.jpg")
chequear("WordPress sigue igual (-300x200)", mi("https://m.com/a/foto-300x200.jpg") == "https://m.com/a/foto.jpg")


# --- 2. Fotos chicas: se prueba la de la página y si no, se descarta -----------------------
tmp = Path(tempfile.mkdtemp(prefix="fotos_"))
tamanios = {}                         # url -> (w, h) de la "foto" que devuelve
bajadas = []
orig_bajar, orig_detalle = F._bajar_foto, fetch.detalle


def bajar_falso(url, destino):
    bajadas.append(url)
    if url not in tamanios:
        return None
    Image.new("RGB", tamanios[url], (90, 90, 90)).save(destino, "JPEG")
    return destino


pagina = {}
try:
    F._bajar_foto = bajar_falso
    fetch.detalle = lambda url, **k: {"ok": True, "imagen": pagina.get(url)}

    tamanios.update({"https://m.com/chica.jpg": (72, 72), "https://m.com/grande.jpg": (1200, 675)})
    pagina["https://m.com/nota1"] = "https://m.com/grande.jpg"
    foto, url, motivo = F._foto_usable({"imagen": "https://m.com/chica.jpg", "url": "https://m.com/nota1"},
                                       tmp / "a.jpg")
    chequear("foto chica: usa la foto principal de la página si es grande",
             foto and url == "https://m.com/grande.jpg" and motivo == "")

    pagina["https://m.com/nota2"] = "https://m.com/chica.jpg"
    foto, url, motivo = F._foto_usable({"imagen": "https://m.com/chica.jpg", "url": "https://m.com/nota2"},
                                       tmp / "b.jpg")
    chequear("foto chica y la página no tiene otra: se descarta, con el tamaño en el motivo",
             foto is None and url == "" and "72x72" in motivo and not (tmp / "b.jpg").exists())

    tamanios["https://m.com/borde.jpg"] = (442, 248)
    foto, url, _ = F._foto_usable({"imagen": "https://m.com/borde.jpg", "url": "https://m.com/n3"}, tmp / "c.jpg")
    chequear("442x248 (la más chica que salió bien el 27/09) sirve", foto and url == "https://m.com/borde.jpg")

    tamanios["https://m.com/finita.jpg"] = (1200, 150)
    foto, _, motivo = F._foto_usable({"imagen": "https://m.com/finita.jpg", "url": "https://m.com/n4"}, tmp / "d.jpg")
    chequear("una franja finita (1200x150) no sirve", foto is None and "1200x150" in motivo)

    bajadas.clear()
    foto, url, _ = F._foto_usable({"imagen": "https://m.com/grande.jpg", "url": "https://m.com/n5"}, tmp / "e.jpg")
    chequear("foto buena de entrada: no se baja la página de más", foto and bajadas == ["https://m.com/grande.jpg"])

    foto, url, motivo = F._foto_usable({"imagen": "https://m.com/rota.jpg", "url": "https://m.com/n6"}, tmp / "f.jpg")
    chequear("enlace roto y sin otra: el motivo lo dice", foto is None and "no se pudo bajar" in motivo)
finally:
    F._bajar_foto, fetch.detalle = orig_bajar, orig_detalle
    shutil.rmtree(tmp, ignore_errors=True)


# --- 3. El video pesa más que la foto al puntuar -------------------------------------------
base = {"titulo": "Robo", "tipo": "robo", "gravedad": "media", "score_keywords": 10,
        "localidad": "Lobos", "imagen": "https://m.com/f.jpg"}
chequear("con video suma 45 más que la misma nota con foto sola",
         F._puntaje(dict(base, video="https://m.com/v.mp4")) - F._puntaje(base) == 45)
con_video = dict(base, titulo="Choque en el centro de la ciudad con dos heridos", video="https://m.com/v.mp4",
                 url="https://m.com/v")
con_foto = dict(base, titulo="Robaron una camioneta estacionada en el barrio norte", url="https://m.com/f")
chequear("en el mismo pueblo, la del video es la que entra primero", F.elegir([con_foto, con_video], 1) == [con_video])

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
