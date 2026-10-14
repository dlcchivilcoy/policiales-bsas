# -*- coding: utf-8 -*-
"""La portada vertical 1080x1920 de cada pieza agro (punto 13 del documento): moderna, «medio
económico + AgTech», con aire. Imagen arriba, bloque grafito abajo con la categoría chica, el
titular grande, la bajada y la marca. Sin el nombre del medio de origen (punto 11).

Si la imagen es generada por IA lleva la leyenda «Imagen ilustrativa generada con IA»: Meta pide
avisar las imágenes realistas hechas con IA, y es lo honesto con el lector.
"""
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
MARCA = Path(__file__).resolve().parent / "marca"
FUENTES = RAIZ / "estetica_bot" / "fonts"

W, H = 1080, 1920
ALTO_IMAGEN = 1150
FONDO = (17, 19, 23)
NARANJA = (255, 112, 0)
VERDE = (118, 178, 60)
GRIS = (196, 200, 207)
BLANCO = (255, 255, 255)
USUARIO = "@diarioyradioagro"
MARGEN = 72


def fuente(nombre: str, tam: int):
    rutas = {"titulo": "Montserrat-Bold.ttf", "texto": "GoogleSans-Variable.ttf",
             "angosta": "ArchivoNarrow-Variable.ttf"}
    try:
        return ImageFont.truetype(str(FUENTES / rutas[nombre]), tam)
    except OSError:
        return ImageFont.load_default()


def logo(alto: int) -> Image.Image:
    """El dibujo del logo (sin el fondo grafito) en RGBA, de `alto` px (una copia: se puede tocar)."""
    return _logo(alto).copy()


@lru_cache(maxsize=8)
def _logo(alto: int) -> Image.Image:
    im = Image.open(MARCA / "logo_original.png").convert("RGB")
    gris = im.convert("L").point(lambda v: 255 if v > 30 else 0)
    caja = gris.getbbox() or (0, 0, im.width, im.height)
    im, alfa = im.crop(caja), gris.crop(caja)
    rgba = im.convert("RGBA")
    rgba.putalpha(alfa.filter(ImageFilter.GaussianBlur(0.6)))
    return rgba.resize((round(rgba.width * alto / rgba.height), alto), Image.LANCZOS)


def renglones(draw, texto: str, f, ancho: int) -> list:
    out, linea = [], ""
    for p in (texto or "").split():
        prueba = f"{linea} {p}".strip()
        if draw.textlength(prueba, font=f) <= ancho or not linea:
            linea = prueba
        else:
            out.append(linea)
            linea = p
    if linea:
        out.append(linea)
    return out


def ajustar(draw, texto: str, nombre: str, tam_max: int, tam_min: int, ancho: int, max_renglones: int):
    """(fuente, renglones): el cuerpo más grande en el que el texto entra en `max_renglones`."""
    for tam in range(tam_max, tam_min - 1, -2):
        f = fuente(nombre, tam)
        r = renglones(draw, texto, f, ancho)
        if len(r) <= max_renglones:
            return f, r
    f = fuente(nombre, tam_min)
    r = renglones(draw, texto, f, ancho)
    if len(r) > max_renglones:
        r = r[:max_renglones]
        r[-1] = r[-1].rstrip(" ,.;:") + "…"
    return f, r


def imagen_arriba(ruta, alto: int = ALTO_IMAGEN, zoom: float = 1.0, corrimiento: float = 0.0,
                  rapido: bool = False) -> Image.Image:
    """La imagen (ruta o PIL) recortada a W x alto (cubriendo), con `zoom` ≥ 1 y un corrimiento
    horizontal (-1..1) para el movimiento lento del reel. `rapido`: filtro bilineal (cuadros del reel)."""
    im = ruta if isinstance(ruta, Image.Image) else Image.open(ruta).convert("RGB")
    k = max(W / im.width, alto / im.height) * zoom
    im = im.resize((max(W, round(im.width * k)), max(alto, round(im.height * k))),
                   Image.BILINEAR if rapido else Image.LANCZOS)
    x0 = (im.width - W) / 2 * (1 + corrimiento)
    y0 = (im.height - alto) / 2
    return im.crop((round(x0), round(y0), round(x0) + W, round(y0) + alto))


def fundido(lienzo: Image.Image, desde: int, hasta: int):
    """Degradé de transparente a grafito entre dos alturas (la imagen se funde con el bloque)."""
    lienzo.alpha_composite(_capa_fundido(hasta - desde), (0, desde))


@lru_cache(maxsize=4)
def _capa_fundido(alto: int) -> Image.Image:
    capa = Image.new("RGBA", (W, alto), FONDO + (0,))
    d = ImageDraw.Draw(capa)
    for y in range(alto):
        d.line([(0, y), (W, y)], fill=FONDO + (round(255 * (y / alto) ** 1.6),))
    return capa


@lru_cache(maxsize=1)
def _capa_sombra() -> Image.Image:
    sombra = Image.new("RGBA", (W, 280), (0, 0, 0, 0))
    d = ImageDraw.Draw(sombra)
    for y in range(280):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, round(190 * (1 - y / 280) ** 1.3)))
    return sombra


def cabecera(lienzo: Image.Image):
    """Logo y nombre arriba a la izquierda, sobre una sombra suave para que se lea en cualquier foto."""
    lienzo.alpha_composite(_capa_sombra(), (0, 0))
    lg = _logo(92)
    lienzo.alpha_composite(lg, (MARGEN - 10, 56))
    d = ImageDraw.Draw(lienzo)
    x = MARGEN - 10 + lg.width + 18
    # Un contorno oscuro fino: con cielo claro arriba, el naranja solo no se leía.
    borde = {"stroke_width": 2, "stroke_fill": (0, 0, 0)}
    d.text((x, 64), "DIARIO Y RADIO", font=fuente("titulo", 30), fill=BLANCO, **borde)
    d.text((x, 100), "AGRO", font=fuente("titulo", 30), fill=NARANJA, **borde)


def etiqueta(draw, x: int, y: int, texto: str, color=VERDE) -> int:
    """La categoría en una píldora. Devuelve el alto ocupado."""
    f = fuente("titulo", 30)
    t = (texto or "Agro").upper()
    ancho = draw.textlength(t, font=f)
    draw.rounded_rectangle((x, y, x + ancho + 44, y + 54), radius=27, fill=color)
    draw.text((x + 22, y + 9), t, font=f, fill=FONDO if color == VERDE else BLANCO)
    return 54


def pie(draw, ia: bool, credito: str = ""):
    y = H - 118
    draw.rectangle((MARGEN, y, MARGEN + 90, y + 6), fill=NARANJA)
    draw.text((MARGEN, y + 26), USUARIO, font=fuente("titulo", 34), fill=VERDE)
    t = "Imagen ilustrativa generada con IA" if ia else (f"Foto: {credito}" if credito else "")
    if t:
        f = fuente("texto", 24)
        draw.text((W - MARGEN - draw.textlength(t, font=f), y + 34), t, font=f, fill=(140, 145, 152))


def armar(datos: dict, imagen, salida: Path, ia: bool = False, credito: str = "") -> Path:
    """datos: volanta, titular, bajada. imagen: ruta (o None → solo grafito con el logo)."""
    lienzo = Image.new("RGBA", (W, H), FONDO + (255,))
    if imagen:
        lienzo.paste(imagen_arriba(imagen), (0, 0))
        fundido(lienzo, ALTO_IMAGEN - 420, ALTO_IMAGEN)
    else:
        marca_agua = logo(700)
        marca_agua.putalpha(marca_agua.getchannel("A").point(lambda a: a * 0.12))
        lienzo.alpha_composite(marca_agua, ((W - marca_agua.width) // 2, 230))
    cabecera(lienzo)
    d = ImageDraw.Draw(lienzo)
    y = ALTO_IMAGEN - 60
    y += etiqueta(d, MARGEN, y, datos.get("volanta")) + 34
    ft, rt = ajustar(d, datos.get("titular", ""), "titulo", 76, 50, W - 2 * MARGEN, 4)
    alto_t = round(ft.size * 1.14)
    for r in rt:
        d.text((MARGEN, y), r, font=ft, fill=BLANCO)
        y += alto_t
    y += 26
    fb, rb = ajustar(d, datos.get("bajada", ""), "texto", 38, 30, W - 2 * MARGEN, 4)
    for r in rb:
        if y + fb.size > H - 150:
            break
        d.text((MARGEN, y), r, font=fb, fill=GRIS)
        y += round(fb.size * 1.32)
    pie(d, ia, credito)
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    lienzo.convert("RGB").save(salida, "JPEG", quality=92)
    return salida
