# -*- coding: utf-8 -*-
"""EL MAPA DE LA ZONA por tema: Chivilcoy y sus 9 partidos vecinos pintados según un dato (20/11/2026).

Pedido del editor: «cuando armes los reels de videos o imágenes interactivos que arranque de una, no inventes una
portada con fotos, prefiero que vaya directo a la info con el mapa interactivo de la temática». Es la primera
diapositiva de los reels de datos de la zona (agro/reel_zona.py) y la tapa de los perfiles (agro/perfil.py): los
partidos se van pintando del menor al mayor valor, con el número encima; Chivilcoy con borde naranja.

Contornos: georef (IGN), agro/datos/partidos.json. Claves por slug de ArgenFields («25-de-mayo»).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

from agro import diseno as D

PARTIDOS = Path(__file__).resolve().parent / "datos" / "partidos.json"
NARANJA = D.NARANJA
BLANCO = (255, 255, 255)


@lru_cache(maxsize=1)
def poligonos() -> dict:
    """{slug: {"nombre", "anillos": [[[lon, lat]…]…]}}."""
    try:
        crudo = json.loads(PARTIDOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k.replace(" ", "-"): v for k, v in crudo.items()}


def proyeccion(lado_x: int, lado_y: int, margen: int = 30, solo: str = ""):
    """fn(lon, lat) → (x, y) que encaja los partidos (o solo `solo`) en el rectángulo."""
    polis = poligonos()
    anillos = [a for k, v in polis.items() for a in v["anillos"] if not solo or k == solo]
    xs = [x for a in anillos for x, _ in a] or [0, 1]
    ys = [y for a in anillos for _, y in a] or [0, 1]
    lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    esc = min((lado_x - 2 * margen) / ((lon1 - lon0) * k or 1), (lado_y - 2 * margen) / ((lat1 - lat0) or 1))
    ox = (lado_x - (lon1 - lon0) * k * esc) / 2
    oy = (lado_y - (lat1 - lat0) * esc) / 2
    return lambda lon, lat: (ox + (lon - lon0) * k * esc, oy + (lat1 - lat) * esc)


def centro(anillo: list) -> tuple:
    return sum(x for x, _ in anillo) / len(anillo), sum(y for _, y in anillo) / len(anillo)


def _mezcla(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def color_de(v: float, lo: float, hi: float, divergente: bool = False) -> tuple:
    if divergente:
        tope = max(abs(lo), abs(hi)) or 1
        t = min(1.0, abs(v) / tope)
        return _mezcla((70, 76, 84), (118, 196, 70) if v >= 0 else (214, 69, 65), 0.35 + 0.65 * t)
    t = 0.0 if hi == lo else (v - lo) / (hi - lo)
    return _mezcla((58, 92, 52), (150, 214, 72), t)


def dibujar(valores: dict, t: float, lado_x: int = 960, lado_y: int = 900, fmt=lambda v: f"{v:g}",
            divergente: bool = False, resaltar: str = "chivilcoy", durar: float = 1.6, fondo=(44, 47, 53)) -> Image.Image:
    """El mapa con los partidos de `valores` ({slug: número}) pintados en orden, del menor al mayor, durante
    `durar` segundos; los que no tienen dato, grises. Devuelve RGBA lado_x × lado_y."""
    im = Image.new("RGBA", (lado_x, lado_y), (0, 0, 0, 0))
    polis = poligonos()
    if not polis:
        return im
    p = proyeccion(lado_x, lado_y)
    d = ImageDraw.Draw(im)
    con = sorted([(v, k) for k, v in valores.items() if v is not None and k in polis])
    lo, hi = (con[0][0], con[-1][0]) if con else (0, 1)
    orden = {k: i for i, (_, k) in enumerate(con)}
    n = max(1, len(con))
    for k, v in polis.items():
        for a in v["anillos"]:
            pts = [p(x, y) for x, y in a]
            if k in orden:
                aparece = max(0.0, min(1.0, (t - durar * orden[k] / n) / 0.35))
                color = _mezcla(fondo, color_de(valores[k], lo, hi, divergente), aparece)
            else:
                color = fondo
            d.polygon(pts, fill=color + (255,), outline=(20, 22, 26, 255))
            d.line(pts + [pts[0]], fill=(20, 22, 26, 255), width=3)
    if resaltar in polis:
        for a in polis[resaltar]["anillos"]:
            pts = [p(x, y) for x, y in a]
            d.line(pts + [pts[0]], fill=NARANJA + (255,), width=7, joint="curve")
    for k, v in polis.items():
        a = max(v["anillos"], key=len)
        cx, cy = p(*centro(a))
        nombre = v["nombre"]
        pts = [p(x, y) for x, y in a]
        area = abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2
        chico = area < lado_x * lado_y * 0.035          # los partidos chicos: letra más chica
        f_n = D.fuente("bold", 19 if chico else (25 if len(nombre) > 12 else 28))
        es = k == resaltar
        sombra = (0, 0, 0, 200)
        if k in orden and t >= durar * orden[k] / n + 0.2:
            num = fmt(valores[k])
            f_v = D.fuente("negra", 44 if es else (28 if chico else 38))
            wv = d.textlength(num, font=f_v)
            d.text((cx - wv / 2 + 2, cy - 30 + 2), num, font=f_v, fill=sombra)
            d.text((cx - wv / 2, cy - 30), num, font=f_v, fill=BLANCO)
            yn = cy + (8 if chico else 18)
        else:
            yn = cy - 12
        wn = d.textlength(nombre, font=f_n)
        d.text((cx - wn / 2 + 2, yn + 2), nombre, font=f_n, fill=sombra)
        d.text((cx - wn / 2, yn), nombre, font=f_n, fill=NARANJA if es else (236, 238, 240))
    return im


def pueblos(puntos: list, t: float, lado_x: int = 960, lado_y: int = 900, partido: str = "chivilcoy",
            fmt=lambda v: f"{v:.0f} mm", durar: float = 1.4, fondo=(44, 47, 53)) -> Image.Image:
    """El partido con sus pueblos como burbujas que crecen según el valor: puntos [(nombre, lat, lon, valor)]."""
    im = Image.new("RGBA", (lado_x, lado_y), (0, 0, 0, 0))
    polis = poligonos()
    if partido not in polis:
        return im
    p = proyeccion(lado_x, lado_y, 70, solo=partido)
    d = ImageDraw.Draw(im)
    for a in polis[partido]["anillos"]:
        pts = [p(x, y) for x, y in a]
        d.polygon(pts, fill=fondo + (255,))
        d.line(pts + [pts[0]], fill=NARANJA + (255,), width=6, joint="curve")
    tope = max([v for *_, v in puntos] + [5.0])
    for i, (nombre, lat, lon, v) in enumerate(sorted(puntos, key=lambda q: q[3])):
        crec = max(0.0, min(1.0, (t - durar * i / max(1, len(puntos))) / 0.4))
        x, y = p(lon, lat)
        r = (16 + 70 * math.sqrt(max(v, 0) / tope)) * crec
        if r > 1:
            d.ellipse((x - r, y - r, x + r, y + r), fill=(64, 140, 245, 170), outline=(160, 205, 255, 255), width=3)
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=BLANCO)
        f_n, f_v = D.fuente("bold", 26), D.fuente("negra", 34)
        if crec > 0.5:
            txt = fmt(v)
            d.text((x - d.textlength(txt, font=f_v) / 2 + 2, y - 50 + 2), txt, font=f_v, fill=(0, 0, 0, 200))
            d.text((x - d.textlength(txt, font=f_v) / 2, y - 50), txt, font=f_v, fill=BLANCO)
        d.text((x - d.textlength(nombre, font=f_n) / 2 + 2, y + 14), nombre, font=f_n, fill=(0, 0, 0, 200))
        d.text((x - d.textlength(nombre, font=f_n) / 2, y + 12), nombre, font=f_n, fill=(236, 238, 240))
    return im
