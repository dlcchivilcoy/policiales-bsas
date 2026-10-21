# -*- coding: utf-8 -*-
"""La PLACA PROPIA de las piezas nacionales. Desde el 07/10/2026 (decisión del editor) cada
pieza lleva la FOTO de su nota de Infobae, salvo que sea de una agencia (AP, AFP, Reuters, EFE…,
que facturan cada foto usada): ahí, o si la nota no trae foto, va esta placa
(nacionales/pasada.py, foto_de_la_nota). Del 06/10 al 07/10 todas salieron con placa.

Qué se dibuja, todo con la paleta del estilo «corresponsal» del bot (grafito + naranja):
- fondo(): el fondo de cada pieza: grafito con un resplandor naranja y la SECCIÓN en letras
  enormes («POLÍTICA», «ECONOMÍA»…). Es el «foto» que recibe el motor de reels del bot, que le
  pone encima la marca, la volanta y el titular como a cualquier reel.
  ⚠️ Lleva GRANO a propósito: el motor reconoce una gráfica por sus rellenos lisos y a una
  gráfica la muestra entera, SIN las cajas del titular (video.py, _es_grafica). Con grano es
  una «foto» más.
- slide_carrusel(): la placa 4:5 del carrusel de Instagram y del posteo de Facebook, estilo
  portal en GRAFITO (pedido del 12/10/2026, story_image.compose_carrusel_slide) sobre la foto o
  ese fondo. Desde ese día el carrusel arranca con la primera nota (ya no hay tapa con la lista de
  titulares) y el posteo de Facebook usa la misma placa, sin número ni flecha.
- portada_web(): la imagen 1200x675 de la nota de la web (tarjeta de la sección, Google).
"""
import random
import zlib
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
ESTETICA = RAIZ / "estetica_bot"
FUENTE = ESTETICA / "fonts" / "GoogleSans-Variable.ttf"
ISO_NARANJA = ESTETICA / "logo_reel_naranja.png"

GRAFITO = (32, 34, 38)          # #202226, la caja principal del estilo corresponsal
GRAFITO_OSCURO = (18, 19, 23)
NARANJA = (239, 150, 60)        # #EF963C, acentos
NARANJA_CAJA = (179, 91, 24)    # #B35B18, la caja de la volanta
BLANCO = (255, 255, 255)
GRIS = (210, 211, 216)

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def fecha_larga(d: datetime) -> str:
    """«martes 6 de octubre»."""
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def fuente(tam: int, peso: int = 700) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FUENTE), tam)
    try:
        f.set_variation_by_axes([18, peso, 0])         # tamaño óptico, peso, grado
    except Exception:                                   # noqa: BLE001 — sin ejes: el peso de base
        pass
    return f


def _partir(draw, texto: str, f, ancho: int) -> list:
    lineas, linea = [], ""
    for w in (texto or "").split():
        prueba = f"{linea} {w}".strip()
        if draw.textlength(prueba, font=f) <= ancho or not linea:
            linea = prueba
        else:
            lineas.append(linea)
            linea = w
    if linea:
        lineas.append(linea)
    return lineas


def _encajar(draw, texto: str, ancho: int, alto: int, maximo: int, minimo: int, peso=700,
             salto=1.12, renglones=0):
    """(fuente, líneas, alto de línea): lo más grande que entra en ancho × alto."""
    for tam in range(maximo, minimo - 1, -2):
        f = fuente(tam, peso)
        lineas = _partir(draw, texto, f, ancho)
        lh = round(tam * salto)
        if len(lineas) * lh <= alto and (not renglones or len(lineas) <= renglones):
            return f, lineas, lh
    f = fuente(minimo, peso)
    lh = round(minimo * salto)
    lineas = _partir(draw, texto, f, ancho)
    tope = max(1, min(renglones or 99, alto // lh))
    if len(lineas) > tope:
        lineas = lineas[:tope]
        lineas[-1] = lineas[-1].rstrip(" .,;:") + "…"
    return f, lineas, lh


def _grano(img: Image.Image, semilla: int, fuerza: int = 9) -> Image.Image:
    """Ruido parejo en toda la imagen (ver el ⚠️ del módulo). Con semilla: la misma pieza da
    siempre el mismo fondo."""
    rng = random.Random(semilla)
    ruido = Image.frombytes("L", img.size, rng.randbytes(img.width * img.height))
    ruido = ruido.point(lambda v: 128 + (v - 128) * fuerza // 128)
    return _sumar_ruido(img, Image.merge("RGB", (ruido, ruido, ruido)))


def _sumar_ruido(img: Image.Image, capa: Image.Image) -> Image.Image:
    # img + (capa - 128), recortado a 0-255, sin numpy.
    mas = ImageChops.subtract(capa, Image.new("RGB", img.size, (128,) * 3))
    menos = ImageChops.subtract(Image.new("RGB", img.size, (128,) * 3), capa)
    return ImageChops.subtract(ImageChops.add(img, mas), menos)


def fondo(seccion: str, tam=(1080, 1920), semilla: int = 0, etiqueta=True) -> Image.Image:
    """El fondo propio: grafito, un resplandor naranja y la SECCIÓN en letras enormes y tenues.
    `etiqueta`: True pone «NACIONALES» arriba; un texto pone ese (el Archivo Literario, 10/10); False, nada."""
    w, h = tam
    img = Image.new("RGB", tam, GRAFITO_OSCURO)
    # Degradé vertical: más claro arriba, donde va la palabra.
    grad = Image.linear_gradient("L").resize(tam)
    img = Image.composite(Image.new("RGB", tam, GRAFITO_OSCURO), Image.new("RGB", tam, (44, 46, 53)), grad)
    # Resplandor naranja arriba a la derecha.
    luz = Image.new("L", tam, 0)
    ImageDraw.Draw(luz).ellipse((int(w * 0.35), int(-h * 0.25), int(w * 1.45), int(h * 0.42)), fill=80)
    luz = luz.filter(ImageFilter.GaussianBlur(min(w, h) // 5))
    img = Image.composite(Image.new("RGB", tam, NARANJA_CAJA), img, luz)

    # La sección, enorme, en dos tonos: blanco muy tenue y un filo naranja.
    palabra = (seccion or "Nacionales").upper()
    capa = Image.new("L", tam, 0)
    d = ImageDraw.Draw(capa)
    tam_letra = 400
    while tam_letra > 60:
        f = fuente(tam_letra, 700)
        if d.textlength(palabra, font=f) <= w * 0.92:
            break
        tam_letra -= 10
    y = int(h * 0.30) - tam_letra // 2
    x = int(w * 0.045)
    d.text((x, y), palabra, font=f, fill=46)
    # El mismo texto, más abajo y más tenue: da profundidad (como una sombra impresa).
    d.text((x, y + int(tam_letra * 0.95)), palabra, font=f, fill=18)
    capa = capa.filter(ImageFilter.GaussianBlur(1.2))       # sin bordes duros (ver el ⚠️)
    img = Image.composite(Image.new("RGB", tam, BLANCO), img, capa)

    # Un filo naranja fino arriba de la palabra y la etiqueta NACIONALES (no en las tapas, que
    # llevan su propio título arriba).
    dd = ImageDraw.Draw(img)
    ya = y - int(tam_letra * 0.18)
    if etiqueta:
        dd.rectangle((x + 6, ya, x + 6 + int(w * 0.12), ya + max(4, h // 300)), fill=NARANJA)
        fe = fuente(max(22, w // 34), 600)
        rotulo = etiqueta if isinstance(etiqueta, str) else "NACIONALES"
        dd.text((x + 6, ya - int(w * 0.055)), rotulo.upper(), font=fe, fill=NARANJA)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return _grano(img, semilla or zlib.crc32(palabra.encode("utf-8")))


def guardar_fondo(seccion: str, destino: Path, tam=(1080, 1920), semilla: int = 0, etiqueta=True) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fondo(seccion, tam, semilla, etiqueta).save(destino, "JPEG", quality=92)
    return destino


def _story_image():
    if str(ESTETICA) not in sys.path:
        sys.path.insert(0, str(ESTETICA))
    import story_image                                   # el del bot (estetica_bot/)
    return story_image


def estilos_carrusel(fotos: list) -> list:
    """Estilo de cada diapositiva del carrusel (con foto alternan A y B; sin foto, C — 21/10/2026)."""
    return _story_image().estilos_carrusel(fotos)


def slide_carrusel(seccion: str, volanta: str, titular: str, bajada: str, destino: Path, *,
                   sitio: str = "", idx: int = None, total: int = None, semilla: int = 0, foto=None,
                   estilo: str = None) -> Path:
    """Placa 4:5 del carrusel de Instagram o del posteo de Facebook (sin idx: sin número ni
    flecha), fondo grafito. Sin `estilo`: con foto (de cualquier forma), la foto arriba y el bloque
    de texto abajo (A; desde el 21/10/2026 también las cuadradas y verticales). Sin foto (agencia o
    la nota no trae): el fondo propio a sangre y el titular en la caja (C)."""
    si = _story_image()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="slide_") as t:
        if not foto:
            foto = guardar_fondo(seccion, Path(t) / "fondo.jpg", (1080, 1350), semilla, etiqueta=False)
            estilo = "C"
        hecho = si.compose_carrusel_slide(foto, volanta or "", titular, bajada or "", sitio, idx, total,
                                          tema="grafito", estilo=estilo)
        shutil.move(str(hecho), str(destino))
    return destino


def _foto_arriba(foto, ancho: int, alto: int) -> Image.Image:
    """La foto ORIGINAL recortada al centro para la franja de arriba (sin deformarla)."""
    im = Image.open(foto).convert("RGB")
    escala = max(ancho / im.width, alto / im.height)
    im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
    x, y = (im.width - ancho) // 2, max(0, round((im.height - alto) * 0.35))   # un poco arriba: caras
    return im.crop((x, y, x + ancho, y + alto))


def lamina_texto(seccion: str, titulo: str, texto: str, destino: Path, *, idx: int, total: int,
                 foto=None, sitio: str = "", semilla: int = 0) -> Path:
    """Una lámina del CARRUSEL EXPLICATIVO: 1080x1350, SOLO TEXTO (pedido del editor, 18/10/2026: «para
    los carruseles siempre usá imágenes para la primera foto y para las siguientes enfocate en hacer
    solo texto bien diseñado»). La foto va únicamente en la tapa (slide_carrusel); `foto` queda en la
    firma por compatibilidad y no se usa.

    Grafito con un resplandor naranja tenue, la marca y el número arriba, el número de la lámina
    enorme y apenas visible de fondo, y el bloque centrado: sección con su filo naranja, el título en
    blanco y el texto en gris claro. Abajo, «Deslizá y seguí leyendo →» o, en la última, el sitio.
    """
    W, H, M = 1080, 1350, 84
    tam = (W, H)
    grad = Image.linear_gradient("L").resize(tam)
    img = Image.composite(Image.new("RGB", tam, GRAFITO_OSCURO), Image.new("RGB", tam, (42, 44, 50)), grad)
    luz = Image.new("L", tam, 0)
    ImageDraw.Draw(luz).ellipse((int(W * 0.45), int(-H * 0.30), int(W * 1.45), int(H * 0.35)), fill=60)
    img = Image.composite(Image.new("RGB", tam, NARANJA_CAJA), img, luz.filter(ImageFilter.GaussianBlur(220)))
    # El número de la lámina, enorme y casi transparente, abajo a la derecha.
    capa = Image.new("L", tam, 0)
    ImageDraw.Draw(capa).text((W - 40, H - 150), f"{idx:02d}", font=fuente(520, 800), fill=22, anchor="rs")
    img = Image.composite(Image.new("RGB", tam, BLANCO), img, capa)
    img = _grano(img, semilla or zlib.crc32(f"{titulo}{idx}".encode("utf-8")), 6)
    d = ImageDraw.Draw(img)

    # Arriba: la marca a la izquierda, «02 / 06» a la derecha, y un filete.
    _marca(img, M, 70, 50)
    d.text((W - M, 95), f"{idx:02d} / {total:02d}", font=fuente(32, 700), fill=NARANJA, anchor="rm")
    d.line((M, 160, W - M, 160), fill=(64, 66, 74), width=2)

    # El bloque, medido antes de dibujar para centrarlo entre el filete y el pie.
    arriba, abajo = 210, H - 170
    ancho = W - 2 * M
    rot = (seccion or "").upper()
    ft, lt, lht = _encajar(d, titulo, ancho, 330, 78, 50, 800, 1.08, 4)
    alto_rot = 30 + 24 + 8 + 40 if rot else 0
    resto = abajo - arriba - alto_rot - len(lt) * lht - 40
    fx, lx, lhx = _encajar(d, texto, ancho, max(resto, 120), 50, 34, 500, 1.36)
    alto = alto_rot + len(lt) * lht + 40 + len(lx) * lhx
    y = arriba + max(0, (abajo - arriba - alto) // 2)
    if rot:
        d.text((M, y), rot, font=fuente(30, 700), fill=NARANJA)
        y += 30 + 24
        d.rectangle((M, y, M + 96, y + 8), fill=NARANJA)
        y += 8 + 40
    for ln in lt:
        d.text((M, y), ln, font=ft, fill=BLANCO)
        y += lht
    y += 40
    for ln in lx:
        d.text((M, y), ln, font=fx, fill=GRIS)
        y += lhx

    # Pie: «Deslizá →» o el sitio.
    d.line((M, H - 120, W - M, H - 120), fill=(64, 66, 74), width=2)
    fin = f"Seguí leyendo en {sitio}" if idx == total and sitio else ("Deslizá y seguí leyendo  →" if idx < total else "")
    if fin:
        d.text((M, H - 70), fin, font=fuente(32, 700), fill=NARANJA, anchor="lm")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=92)
    return destino


def _marca(img: Image.Image, x: int, y: int, alto: int):
    """Isotipo naranja + «DIARIO LA CAMPAÑA», como en los carruseles del bot."""
    d = ImageDraw.Draw(img)
    try:
        iso = Image.open(ISO_NARANJA).convert("RGBA")
        ancho = round(iso.width * alto / iso.height)
        img.paste(iso.resize((ancho, alto), Image.LANCZOS), (x, y), iso.resize((ancho, alto), Image.LANCZOS))
        x += ancho + round(alto * 0.3)
    except OSError:
        pass
    f = fuente(round(alto * 0.44), 700)
    d.text((x, y + alto // 2), "DIARIO LA CAMPAÑA", font=f, fill=BLANCO, anchor="lm")


def portada_web(seccion: str, volanta: str, titular: str, destino: Path, semilla: int = 0) -> Path:
    """La imagen de la nota en la web (1200x675): fondo propio, volanta en caja y titular."""
    W, H, M = 1200, 675, 64
    img = fondo(seccion, (W, H), semilla, etiqueta=False)
    velo = Image.new("L", (W, H), 0)
    ImageDraw.Draw(velo).rectangle((0, int(H * 0.42), W, H), fill=190)
    velo = velo.filter(ImageFilter.GaussianBlur(50))
    img = Image.composite(Image.new("RGB", (W, H), GRAFITO_OSCURO), img, velo)
    d = ImageDraw.Draw(img)
    _marca(img, M, 40, 54)
    ft, lineas, lh = _encajar(d, titular, W - 2 * M, 250, 70, 40, 700, 1.08, 3)
    y = H - 56 - len(lineas) * lh
    vol = (volanta or seccion or "").upper()
    if vol:
        fv = fuente(30, 600)
        caja = d.textlength(vol, font=fv) + 36
        d.rectangle((M, y - 74, M + caja, y - 24), fill=NARANJA_CAJA)
        d.text((M + 18, y - 49), vol, font=fv, fill=BLANCO, anchor="lm")
    for ln in lineas:
        d.text((M, y), ln, font=ft, fill=BLANCO)
        y += lh
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=90)
    return destino
