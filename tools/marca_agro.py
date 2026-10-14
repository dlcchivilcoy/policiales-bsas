# -*- coding: utf-8 -*-
"""Arma la foto de perfil (1080x1080) y la portada de Facebook (1640x624) de @diarioyradioagro.

Uso:
    venv\Scripts\python.exe tools\marca_agro.py [logo_original] [carpeta_destino]

Por defecto toma agro/marca/logo_original.png y escribe en agro/marca/. La foto de
perfil deja el dibujo entero dentro del círculo con el que la recortan IG y FB.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "agro" / "marca" / "logo_original.png"
DESTINO = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "agro" / "marca"
FUENTES = RAIZ / "estetica_bot" / "fonts"
DESTINO.mkdir(parents=True, exist_ok=True)

FONDO = (17, 19, 23)
NARANJA = (255, 112, 0)
VERDE = (118, 178, 60)
GRIS = (200, 204, 210)

src = Image.open(ORIGEN).convert("RGB")
# Recorte al dibujo: todo lo que se separa del fondo.
dif = ImageChops.difference(src, Image.new("RGB", src.size, FONDO)).convert("L")
dif = dif.point(lambda v: 255 if v > 24 else 0)
caja = dif.getbbox()
# Los restos de compresión del .webp (manchas casi negras) se llevan al fondo exacto.
src = Image.composite(src, Image.new("RGB", src.size, FONDO), dif.point(lambda v: v))
logo = src.crop(caja)
if ORIGEN.resolve() != (DESTINO / "logo_original.png").resolve():
    src.save(DESTINO / "logo_original.png")
print("caja del dibujo:", caja, "->", logo.size)


def pegar_centrado(lienzo, img, cx, cy):
    lienzo.paste(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# --- Perfil: IG y FB lo recortan en círculo; el dibujo entra entero en el 86 % del círculo.
L = 1080
perfil = Image.new("RGB", (L, L), FONDO)
diag = (logo.width ** 2 + logo.height ** 2) ** 0.5
esc = (L * 0.86) / diag
lp = logo.resize((round(logo.width * esc), round(logo.height * esc)), Image.LANCZOS)
pegar_centrado(perfil, lp, L / 2, L / 2)
perfil.save(DESTINO / "perfil_1080.png")

# --- Portada de Facebook 1640x624. En el celular se ven los ~1100 px del centro y en la
# compu se tapa abajo a la izquierda con la foto de perfil: todo va centrado.
W, H = 1640, 624
port = Image.new("RGB", (W, H), FONDO)
d = ImageDraw.Draw(port)
alto_logo = 400
lc = logo.resize((round(logo.width * alto_logo / logo.height), alto_logo), Image.LANCZOS)

f_titulo = ImageFont.truetype(str(FUENTES / "Montserrat-Bold.ttf"), 84)
f_sub = ImageFont.truetype(str(FUENTES / "Montserrat-Bold.ttf"), 34)
f_user = ImageFont.truetype(str(FUENTES / "Montserrat-Bold.ttf"), 30)

linea1, linea2 = "DIARIO Y RADIO", "AGRO"
sub = "Campo · AgTech · Mercados · Ganadería"
user = "@diarioyradioagro"
ancho_txt = max(d.textlength(linea1, font=f_titulo), d.textlength(sub, font=f_sub))
sep = 56
total = lc.width + sep + ancho_txt
x0 = (W - total) / 2
port.paste(lc, (int(x0), int((H - lc.height) / 2)))
tx = x0 + lc.width + sep
y = H / 2 - 150
d.text((tx, y), linea1, font=f_titulo, fill=(255, 255, 255))
d.text((tx, y + 92), linea2, font=f_titulo, fill=NARANJA)
d.rectangle((tx, y + 200, tx + 120, y + 206), fill=VERDE)
d.text((tx, y + 226), sub, font=f_sub, fill=GRIS)
d.text((tx, y + 276), user, font=f_user, fill=VERDE)
port.save(DESTINO / "portada_facebook_1640x624.png")
print("listo:", sorted(p.name for p in DESTINO.iterdir()))
