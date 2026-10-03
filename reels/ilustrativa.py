# -*- coding: utf-8 -*-
"""Imagen ilustrativa PROPIA para cuando la foto del medio trae su logo.

Pedido del editor el 03/10/2026. Cuando la foto (y el video) de una noticia traen la marca
del medio y ningún otro medio publicó la misma noticia con una imagen limpia, el reel no
usa esa foto (ver reels/marcas.py): va una de estas.

De dónde sale, en este orden:
  1. reels/banco/<grupo>/*.jpg — fotos PROPIAS del diario, si el editor carga alguna
     (patrulleros, ambulancias, rutas de la zona). Se elige una por nota, siempre la
     misma para la misma nota, y van rotando entre notas.
  2. Si la carpeta está vacía, se DIBUJA por código: luces desenfocadas según el hecho
     (rojo y azul de patrullero, faros en la ruta, fuego, tormenta). Es abstracta a
     propósito: nadie la toma por una foto del hecho, no es de nadie más y no hay que
     bajarla de ningún lado.

Lleva grano fino de foto: el motor del bot reconoce los afiches por los rellenos lisos, y
una imagen lisa podía pasar por afiche y armarse con otra diagramación.
"""
import hashlib
import random
import shutil
from pathlib import Path

BANCO = Path(__file__).resolve().parent / "banco"
ANCHO, ALTO = 1600, 1200          # 4:3, la forma de una foto de nota

GRUPOS = ("policial", "vial", "fuego", "clima")
_GRUPO_POR_TIPO = {"accidente_vial": "vial", "incendio": "fuego",
                   "alerta_meteorologica": "clima"}


def grupo(tipo: str) -> str:
    return _GRUPO_POR_TIPO.get(tipo or "", "policial")


def _azar(semilla: str) -> random.Random:
    return random.Random(int(hashlib.sha1((semilla or "").encode("utf-8")).hexdigest()[:12], 16))


def _del_banco(g: str, rng: random.Random):
    carpeta = BANCO / g
    fotos = sorted(p for p in carpeta.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    return rng.choice(fotos) if fotos else None


# ─── El dibujo ───────────────────────────────────────────────────────────────

def _degrade(arriba, abajo):
    from PIL import Image
    tira = Image.new("RGB", (1, ALTO))
    for y in range(ALTO):
        t = y / (ALTO - 1)
        tira.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(arriba, abajo)))
    return tira.resize((ANCHO, ALTO))


def _luces(lienzo, rng, colores, n, radio, desenfoque, zona=(0, 0, 1, 1), brillo=(0.5, 1.0)):
    """Círculos de luz desenfocados, sumados a la imagen como luz (modo pantalla)."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    capa = Image.new("RGB", lienzo.size, (0, 0, 0))
    d = ImageDraw.Draw(capa)
    x0, y0, x1, y1 = zona
    for _ in range(n):
        x = rng.uniform(x0, x1) * ANCHO
        y = rng.uniform(y0, y1) * ALTO
        color = colores(x / ANCHO, rng) if callable(colores) else rng.choice(colores)
        k = rng.uniform(*brillo)
        r = rng.uniform(*radio)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * k) for c in color))
    return ImageChops.screen(lienzo, capa.filter(ImageFilter.GaussianBlur(desenfoque)))


def _vineta(img):
    from PIL import Image, ImageDraw, ImageFilter
    mascara = Image.new("L", img.size, 0)
    ImageDraw.Draw(mascara).ellipse((-ANCHO * 0.15, -ALTO * 0.2, ANCHO * 1.15, ALTO * 1.2), fill=255)
    mascara = mascara.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), mascara)


def _grano(img, rng, sigma=9):
    """Grano fino, del mismo azar de la nota (Image.effect_noise no se puede sembrar: la misma
    nota daba otra imagen cada vez)."""
    from PIL import Image, ImageChops
    w, h = img.size
    plano = Image.frombytes("L", (w, h), rng.randbytes(w * h))   # parejo entre 0 y 255
    escala = sigma / 73.9                                         # desvío del parejo: 73,9
    ruido = plano.point(lambda v: max(0, min(255, round(128 + (v - 128) * escala)))).convert("RGB")
    return ImageChops.add(img, ruido, 1.0, -128)


ROJO, AZUL, AMBAR, BLANCO = (235, 30, 45), (35, 90, 255), (255, 170, 40), (255, 240, 215)


def _policial(rng):
    img = _degrade((10, 12, 28), (2, 3, 9))
    # Rojo a la izquierda y azul a la derecha, como la barra de luces de un patrullero,
    # mezclados en el medio.
    def lado(x, r):
        return ROJO if r.random() < (1.15 - x) * 0.8 else AZUL
    img = _luces(img, rng, lado, 14, (90, 190), 70, (0, 0.15, 1, 0.7), (0.6, 1.0))
    img = _luces(img, rng, lado, 40, (25, 70), 20, (0, 0.1, 1, 0.8))
    img = _luces(img, rng, lado, 60, (5, 16), 3, (0, 0.05, 1, 0.9), (0.4, 0.9))
    img = _luces(img, rng, [AMBAR], 10, (30, 80), 40, (0, 0.75, 1, 1), (0.15, 0.35))
    return img


def _vial(rng):
    img = _degrade((12, 12, 20), (3, 3, 6))
    img = _luces(img, rng, [AMBAR, BLANCO], 12, (80, 170), 70, (0, 0.45, 1, 0.8), (0.4, 0.8))
    img = _luces(img, rng, [AMBAR, BLANCO, BLANCO, ROJO], 55, (12, 45), 10, (0, 0.5, 1, 0.75))
    img = _luces(img, rng, [ROJO, AZUL], 10, (40, 100), 40, (0, 0.3, 1, 0.6), (0.3, 0.6))
    img = _luces(img, rng, [AMBAR, BLANCO], 60, (3, 9), 2, (0, 0.52, 1, 0.72), (0.4, 1.0))
    return img


def _fuego(rng):
    img = _degrade((18, 6, 3), (5, 1, 0))
    naranja, rojo_fuego, amarillo = (255, 110, 20), (220, 40, 10), (255, 210, 80)
    img = _luces(img, rng, [rojo_fuego, naranja], 16, (150, 300), 90, (0, 0.65, 1, 1.15))
    img = _luces(img, rng, [naranja, amarillo], 30, (40, 110), 35, (0.05, 0.6, 0.95, 1.0))
    img = _luces(img, rng, [naranja, amarillo], 90, (2, 7), 1.5, (0, 0.05, 1, 0.75), (0.5, 1.0))
    return img


def _clima(rng):
    from PIL import Image, ImageDraw, ImageFilter, ImageChops
    img = _degrade((44, 50, 64), (10, 12, 18))
    nubes = [(70, 76, 90), (95, 100, 115), (40, 44, 56)]
    img = _luces(img, rng, nubes, 45, (120, 280), 80, (-0.1, -0.1, 1.1, 0.65), (0.5, 1.0))
    if rng.random() < 0.6:                                  # un relámpago lejano
        img = _luces(img, rng, [(190, 205, 255)], 2, (120, 220), 110, (0.2, 0.05, 0.8, 0.35), (0.6, 0.9))
    lluvia = Image.new("RGB", img.size, (0, 0, 0))
    d = ImageDraw.Draw(lluvia)
    for _ in range(900):
        x, y = rng.uniform(-200, ANCHO), rng.uniform(-100, ALTO)
        largo = rng.uniform(25, 60)
        g = int(rng.uniform(40, 95))
        d.line((x, y, x + largo * 0.35, y + largo), fill=(g, g, g + 10), width=1)
    return ImageChops.screen(img, lluvia.filter(ImageFilter.GaussianBlur(0.8)))


_DIBUJOS = {"policial": _policial, "vial": _vial, "fuego": _fuego, "clima": _clima}


def generar(tipo: str, destino, semilla: str = "") -> Path:
    """Deja la imagen ilustrativa en `destino` (JPEG) y devuelve la ruta."""
    from PIL import Image
    destino = Path(destino)
    g = grupo(tipo)
    rng = _azar(f"{g}|{semilla}")
    propia = _del_banco(g, rng)
    if propia:
        if propia.suffix.lower() in (".jpg", ".jpeg"):
            shutil.copyfile(propia, destino)
        else:
            Image.open(propia).convert("RGB").save(destino, "JPEG", quality=92)
        return destino
    img = _grano(_vineta(_DIBUJOS[g](rng)), rng)
    img.save(destino, "JPEG", quality=92)
    return destino
