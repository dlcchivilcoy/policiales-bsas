# -*- coding: utf-8 -*-
"""Genera agro/marca/isologo_agro.png: el isologo NUEVO del diario (16/10/2026: las tres C gruesas y el punto,
naranja #FD8511, cortes radiales a ±45°; la misma geometría que diario_web/public/logo-c.svg) con el brote verde
de @diarioyradioagro (las hojas y el circuito, recortados de agro/marca/logo_original.png) saliendo del punto.

Pedido del editor (20/11/2026): «la placa final de los reels/carruseles de agro, actualizá el logo e isologo».
Se corre una sola vez (o si cambia el logo): python tools/generar_isologo_agro.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
MARCA = RAIZ / "agro" / "marca"
NARANJA = (253, 133, 17, 255)          # #FD8511
ESCALA = 4                             # se dibuja grande y se achica: bordes limpios

# Geometría del logo-c.svg (en px del dibujo original de 1254): centro, anillos (radio medio, grosor) y el punto.
CX, CY = 659.5, 624.0
ANILLOS = ((387.5, 65), (267.5, 61), (151.0, 60))
PUNTO = 68
BROTE = 0.93                           # el brote, un poco más chico que en el logo viejo (las C nuevas son menores)


def brote_viejo() -> tuple:
    """Las hojas y el circuito verdes del logo viejo, con transparencia, y dónde estaba el centro del punto."""
    im = np.asarray(Image.open(MARCA / "logo_original.png").convert("RGB")).astype(float)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    naranja = (r > 200) & (g < 150) & (b < 80)
    cerca = (xx - 615) ** 2 + (yy - 612) ** 2 < 80 ** 2
    sel = naranja & cerca
    cx0, cy0 = xx[sel].mean(), yy[sel].mean()
    fondo = np.array([17.0, 18.0, 22.0])
    verde = (g > r + 8) & (g > b + 20) & (xx > cx0 + 55)
    a = np.clip((g - fondo[1]) / 150.0, 0, 1) * verde
    col = np.zeros_like(im)
    for k in range(3):
        col[..., k] = np.where(a > 0.02, (im[..., k] - (1 - a) * fondo[k]) / np.maximum(a, 0.02), 0)
    rgba = np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8)
    capa = Image.fromarray(rgba, "RGBA")
    caja = capa.getbbox()
    return capa.crop(caja), (cx0 - caja[0], cy0 - caja[1])


def generar(destino: Path = MARCA / "isologo_agro.png", alto: int = 1000) -> Path:
    hojas, (hx, hy) = brote_viejo()
    hojas = hojas.resize((round(hojas.width * BROTE * ESCALA), round(hojas.height * BROTE * ESCALA)), Image.LANCZOS)
    hx, hy = hx * BROTE * ESCALA, hy * BROTE * ESCALA
    # Lienzo: de la C de afuera al borde derecho de las hojas, en px del dibujo × ESCALA.
    r_ext = ANILLOS[0][0] + ANILLOS[0][1] / 2
    x0, y0 = CX - r_ext, CY - r_ext
    ox, oy = (CX - x0) * ESCALA, (CY - y0) * ESCALA
    ancho = max(2 * r_ext * ESCALA, ox - hx + hojas.width) + 8
    alto_l = 2 * r_ext * ESCALA + 8
    lienzo = Image.new("RGBA", (round(ancho), round(alto_l)), (0, 0, 0, 0))
    lienzo.alpha_composite(hojas, (round(ox - hx), round(oy - hy)))
    d = ImageDraw.Draw(lienzo)
    for rm, w in ANILLOS:
        re_ = (rm + w / 2) * ESCALA
        d.arc((ox - re_, oy - re_, ox + re_, oy + re_), 45, 315, fill=NARANJA, width=round(w * ESCALA))
    rp = PUNTO * ESCALA
    d.ellipse((ox - rp, oy - rp, ox + rp, oy + rp), fill=NARANJA)
    lienzo = lienzo.crop(lienzo.getbbox())
    lienzo = lienzo.resize((round(lienzo.width * alto / lienzo.height), alto), Image.LANCZOS)
    lienzo.save(destino)
    return destino


def iconos() -> list:
    """Los íconos de Instagram y Facebook de la placa final del diario (estetica_bot/placa_final_4x5.png), blancos
    con transparencia: agro/marca/icono_ig.png y icono_fb.png (agro está en esas dos redes)."""
    im = np.asarray(Image.open(RAIZ / "estetica_bot" / "placa_final_4x5.png").convert("L")).astype(float)
    fondo = np.median(im[1250:1340, 20:200])
    salida = []
    for nombre, caja in (("icono_ig.png", (240, 1095, 335, 1185)), ("icono_fb.png", (370, 1095, 440, 1185))):
        x0, y0, x1, y1 = caja
        a = np.clip((im[y0:y1, x0:x1] - fondo) / (255 - fondo), 0, 1) * 255
        capa = Image.new("RGBA", (x1 - x0, y1 - y0), (255, 255, 255, 0))
        capa.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
        capa = capa.crop(capa.getbbox())
        capa.save(MARCA / nombre)
        salida.append(MARCA / nombre)
    return salida


if __name__ == "__main__":
    print(generar(Path(sys.argv[1]) if len(sys.argv) > 1 else MARCA / "isologo_agro.png"))
    if len(sys.argv) == 1:
        print(*iconos())
