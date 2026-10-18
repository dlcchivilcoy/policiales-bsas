# -*- coding: utf-8 -*-
"""La PORTADA de cada reel: la miniatura que se ve en la grilla de Instagram (`cover_url`).

Pedido del editor (18/10/2026): «que se haga una buena miniatura para el feed donde se vea la imagen y
texto con buen SEO». Antes Instagram elegía el primer cuadro del video.

1080x1920 (lo que pide un reel) con TODO lo importante en la franja del medio que muestra la grilla del
perfil (3:4, y 240 a 1680) y el feed (4:5, y 285 a 1635):
- arriba, la FOTO de la nota o un CUADRO del video del medio (nunca una imagen hecha con IA);
- la línea naranja y el bloque (grafito o blanco, el mismo tema que el reel) con la marca, la volanta
  y el TEXTO DE PORTADA: pocas palabras, en letra grande, con la palabra clave que la gente busca
  primero (campo «portada» del guion; si la IA no lo dio, el titular).
"""
from pathlib import Path

from PIL import Image, ImageDraw

from nacionales import placa as P

W, H = 1080, 1920
M = 72
ALTO_FOTO = 1060                    # la foto llega hasta acá; la grilla la muestra de y 240 en adelante
LINEA = 10
TOPE_TEXTO = 1630                   # el título termina antes del borde de la grilla (1680)
TEMAS = {
    "grafito": {"fondo": P.GRAFITO, "titulo": P.BLANCO, "volanta": P.NARANJA, "marca": P.BLANCO},
    "blanco": {"fondo": (255, 255, 255), "titulo": (18, 19, 22), "volanta": (222, 112, 26),
               "marca": (18, 19, 22)},
}


def texto(guion: dict) -> str:
    """El texto SEO de la miniatura: «portada» del guion o, si no vino, el titular."""
    return " ".join(((guion or {}).get("portada") or (guion or {}).get("titular") or "").split())


def _marca(img: Image.Image, x: int, y: int, alto: int, color):
    """Isotipo naranja + «DIARIO LA CAMPAÑA» en el color del tema."""
    try:
        iso = Image.open(P.ISO_NARANJA).convert("RGBA")
        ancho = round(iso.width * alto / iso.height)
        iso = iso.resize((ancho, alto), Image.LANCZOS)
        img.paste(iso, (x, y), iso)
        x += ancho + round(alto * 0.3)
    except OSError:
        pass
    ImageDraw.Draw(img).text((x, y + alto // 2), "DIARIO LA CAMPAÑA", font=P.fuente(round(alto * 0.46), 700),
                             fill=color, anchor="lm")


def armar(imagen, volanta: str, titulo: str, destino: Path, tema: str = "grafito") -> Path:
    """La portada .jpg. `imagen`: la foto de la nota o un cuadro del video (obligatoria: un reel sin
    imagen real no se publica)."""
    if not imagen or not Path(imagen).is_file():
        raise ValueError("la portada necesita la foto de la nota o un cuadro del video")
    t = TEMAS.get(tema) or TEMAS["grafito"]
    img = Image.new("RGB", (W, H), t["fondo"])
    img.paste(P._foto_arriba(imagen, W, ALTO_FOTO), (0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, ALTO_FOTO, W, ALTO_FOTO + LINEA), fill=P.NARANJA)
    y = ALTO_FOTO + LINEA + 44
    _marca(img, M, y, 50, t["marca"])
    y += 50 + 40
    vol = (volanta or "").strip().upper()
    if vol:
        fv, lv, lhv = P._encajar(d, vol, W - 2 * M, 60, 40, 30, 700, 1.1, 1)
        d.text((M, y), lv[0], font=fv, fill=t["volanta"])
        y += lhv + 22
    ft, lineas, lh = P._encajar(d, titulo, W - 2 * M, TOPE_TEXTO - y, 108, 60, 800, 1.06, 4)
    for ln in lineas:
        d.text((M, y), ln, font=ft, fill=t["titulo"])
        y += lh
    # Abajo, fuera de la grilla pero a la vista en la pestaña de reels: el sitio.
    d.line((M, 1745, W - M, 1745), fill=(64, 66, 74) if tema != "blanco" else (220, 221, 226), width=2)
    d.text((M, 1810), "www.diariolacampaña.com.ar", font=P.fuente(34, 600), fill=t["volanta"], anchor="lm")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=92)
    return destino
