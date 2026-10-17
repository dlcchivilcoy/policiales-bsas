# -*- coding: utf-8 -*-
"""Lo visual común de agro: el cuadro 4:5 ESTILO BLOQUE de los reels de policiales, con la marca de
@diarioyradioagro, y las piezas que usan los carruseles y las historias.

Pedido del editor (17/10/2026): «los reels/publicaciones tienen que ser 4:5 … estética estilo los reels
de policiales 4:5». Es la misma diagramación del motor del bot (estetica_bot/video.py, «estilo
bloque», 12/10/2026): la imagen a todo el ancho desde el borde de ARRIBA, una línea naranja y un
BLOQUE macizo hasta el piso con el isologo y el nombre, la volanta naranja en mayúsculas y el
titular. Dos temas que se alternan de un posteo al siguiente: «blanco» (fondo blanco, titular
grafito) y «grafito» (fondo grafito, titular blanco). Las medidas son las del motor (BLOQUE_*); la
marca, la de agro (el isologo naranja y verde, «DIARIO Y RADIO» + «AGRO»).

El motor del bot no se usa directo porque lleva la marca del diario en sus archivos; acá se dibuja
igual con PIL.
"""
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
MARCA = Path(__file__).resolve().parent / "marca"
FUENTES = RAIZ / "estetica_bot" / "fonts"

W, H45, H916 = 1080, 1350, 1920
GRAFITO = (32, 34, 38)                   # #202226, el del motor
NARANJA = (239, 150, 60)                 # #EF963C: la línea y los acentos
NARANJA_OSCURO = (222, 112, 26)          # la volanta sobre blanco
NARANJA_CAJA = (179, 91, 24)             # #B35B18: cajas
VERDE = (118, 178, 60)                   # el verde de las hojas del isologo
VERDE_OSCURO = (78, 138, 32)             # el verde sobre blanco
ROJO = (214, 69, 65)
BLANCO = (255, 255, 255)
GRIS_CLARO = (236, 237, 240)
USUARIO = "@diarioyradioagro"

TEMAS = {
    "blanco": dict(fondo=BLANCO, volanta=NARANJA_OSCURO, titular=GRAFITO, texto=(70, 74, 82), tenue=(140, 145, 152),
                   verde=VERDE_OSCURO, linea=(225, 227, 231)),
    "grafito": dict(fondo=GRAFITO, volanta=NARANJA, titular=BLANCO, texto=(214, 217, 222), tenue=(150, 155, 163),
                    verde=VERDE, linea=(62, 65, 72)),
}
ORDEN_TEMAS = ("blanco", "grafito")

LINEA = 10                # la línea naranja entre la imagen y el bloque
X = 80                    # margen izquierdo de todo lo del bloque
ANCHO = 850               # de X 80 a 930: lejos de la columna de botones de Instagram
PAD = (40, 50)            # aire arriba y abajo, adentro del bloque
ISOLOGO = 76              # alto del renglón de la marca
GAP_LOGO = 32
VOLANTA = (36, 26)        # cuerpo, mínimo
GAP_VOLANTA = 20
TITULAR = (78, 44)        # tope, piso
SALTO = 1.1
RECORTE_MAX = 0.25        # lo más que se le saca a la imagen (desde abajo) para que entre el texto


def tema_siguiente(anterior: str = "") -> str:
    a = (anterior or "").strip().lower()
    return ORDEN_TEMAS[(ORDEN_TEMAS.index(a) + 1) % 2] if a in ORDEN_TEMAS else ORDEN_TEMAS[0]


@lru_cache(maxsize=64)
def fuente(peso: str, tam: int):
    """«regular», «medium», «bold» (Google Sans, la de los reels del bot) o «negra» (Libre Franklin 800,
    para los números grandes)."""
    try:
        if peso == "negra":
            f = ImageFont.truetype(str(FUENTES / "LibreFranklin-Variable.ttf"), tam)
            f.set_variation_by_axes([800])
            return f
        f = ImageFont.truetype(str(FUENTES / "GoogleSans-Variable.ttf"), tam)
        f.set_variation_by_name({"regular": "Regular", "medium": "Medium", "bold": "Bold"}.get(peso, "Regular"))
        return f
    except (OSError, ValueError):
        return ImageFont.load_default()


@lru_cache(maxsize=8)
def _isologo(alto: int) -> Image.Image:
    im = Image.open(MARCA / "logo_original.png").convert("RGB")
    gris = im.convert("L").point(lambda v: 255 if v > 30 else 0)
    caja = gris.getbbox() or (0, 0, im.width, im.height)
    im, alfa = im.crop(caja), gris.crop(caja)
    rgba = im.convert("RGBA")
    rgba.putalpha(alfa.filter(ImageFilter.GaussianBlur(0.6)))
    return rgba.resize((round(rgba.width * alto / rgba.height), alto), Image.LANCZOS)


def isologo(alto: int) -> Image.Image:
    return _isologo(alto).copy()


@lru_cache(maxsize=8)
def _lockup(tema: str, alto: int) -> Image.Image:
    """El isologo y al lado «DIARIO Y RADIO» / «AGRO» (verde, espaciado al mismo ancho)."""
    t = TEMAS[tema]
    iso = _isologo(alto)
    f1 = fuente("bold", round(alto * 0.40))
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    texto1 = "DIARIO Y RADIO"
    ancho1 = medir.textlength(texto1, font=f1)
    f2 = fuente("bold", round(alto * 0.40))
    letras = "AGRO"
    anchos = [medir.textlength(c, font=f2) for c in letras]
    track = (ancho1 - sum(anchos)) / (len(letras) - 1)
    gap = 18
    lienzo = Image.new("RGBA", (iso.width + gap + round(ancho1) + 2, alto), (0, 0, 0, 0))
    lienzo.alpha_composite(iso, (0, 0))
    d = ImageDraw.Draw(lienzo)
    x0 = iso.width + gap
    d.text((x0, round(alto * 0.47)), texto1, font=f1, fill=t["titular"], anchor="ls")
    x = float(x0)
    for c, aw in zip(letras, anchos):
        d.text((x, round(alto * 0.95)), c, font=f2, fill=t["verde"], anchor="ls")
        x += aw + track
    return lienzo


def lockup(tema: str, alto: int = ISOLOGO) -> Image.Image:
    return _lockup(tema, alto).copy()


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


def ajustar(draw, texto: str, peso: str, tope: int, piso: int, ancho: int, max_renglones: int,
            alto_max: int = 0, salto: float = SALTO):
    """(fuente, renglones): la letra más grande en la que el texto entra en `max_renglones` (y en
    `alto_max` px si se da). Al piso, lo que no entra termina en «…»."""
    for tam in range(tope, piso - 1, -2):
        f = fuente(peso, tam)
        r = renglones(draw, texto, f, ancho)
        if len(r) <= max_renglones and (not alto_max or alto_texto(f, len(r), salto) <= alto_max):
            return f, r
    f = fuente(peso, piso)
    r = renglones(draw, texto, f, ancho)
    if len(r) > max_renglones:
        r = r[:max_renglones]
        r[-1] = r[-1].rstrip(" ,.;:") + "…"
    return f, r


def alto_texto(f, n: int, salto: float = SALTO) -> int:
    return round(f.size * (1 + (n - 1) * salto)) if n else 0


def escribir(draw, x: int, y: int, renglones_: list, f, color, salto: float = SALTO) -> int:
    """Escribe los renglones desde `y` (tope de las letras) y devuelve el y de abajo."""
    for i, r in enumerate(renglones_):
        draw.text((x, y + round(i * f.size * salto)), r, font=f, fill=color)
    return y + alto_texto(f, len(renglones_), salto)


def cubrir(im: Image.Image, w: int, h: int, zoom: float = 1.0, dx: float = 0.0, dy: float = 0.0,
           rapido: bool = False) -> Image.Image:
    """La imagen recortada a w×h cubriendo, con `zoom` ≥ 1 y un corrimiento (-1..1) para el movimiento."""
    k = max(w / im.width, h / im.height) * zoom
    nueva = im.resize((max(w, round(im.width * k)), max(h, round(im.height * k))),
                      Image.BILINEAR if rapido else Image.LANCZOS)
    x0 = (nueva.width - w) / 2 * (1 + dx)
    y0 = (nueva.height - h) / 2 * (1 + dy)
    return nueva.crop((round(x0), round(y0), round(x0) + w, round(y0) + h))


def leyenda(capa: Image.Image, texto: str, y_base: int):
    """La leyenda chica de la imagen («Imagen generada con IA», «Foto: INTA»), abajo a la derecha de
    la imagen, sobre una píldora oscura para que se lea en cualquier foto."""
    if not texto:
        return
    d = ImageDraw.Draw(capa)
    f = fuente("medium", 22)
    w = d.textlength(texto, font=f)
    x1, y1 = W - 24, y_base - 16
    d.rounded_rectangle((x1 - w - 28, y1 - 38, x1, y1), radius=19, fill=(0, 0, 0, 150))
    d.text((x1 - w - 14, y1 - 30), texto, font=f, fill=(240, 240, 240, 255))


def plan_bloque(volanta: str, titular: str, tema: str, alto_imagen: int, alto: int = H45) -> dict:
    """Dónde va cada cosa en el cuadro 4:5: {alto_imagen, y_logo, y_texto, zona, volanta, f_tit, tit}.

    La imagen va entera; si el titular no entra con letra ≥ 52 se le resigna imagen desde abajo
    (hasta RECORTE_MAX) antes de achicar más la letra (lo mismo que hace el motor)."""
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    vtxt = " ".join((volanta or "").split()).upper()
    fv = fuente("bold", VOLANTA[0])
    tam = VOLANTA[0]
    while vtxt and tam > VOLANTA[1] and medir.textlength(vtxt, font=fv) > ANCHO:
        tam -= 1
        fv = fuente("bold", tam)
    fijo = LINEA + PAD[0] + ISOLOGO + GAP_LOGO + PAD[1] + (fv.size + GAP_VOLANTA if vtxt else 0)

    def medir_tit(hueco, piso):
        return ajustar(medir, titular, "bold", TITULAR[0], piso, ANCHO, 4, alto_max=hueco)

    hm = alto_imagen
    ft, tit = medir_tit(alto - hm - fijo, 52)
    if alto_texto(ft, len(tit)) > alto - hm - fijo or (tit and tit[-1].endswith("…")):
        hm_min = round(alto_imagen * (1 - RECORTE_MAX))
        ft, tit = medir_tit(alto - hm_min - fijo, TITULAR[1])
        hm = max(hm_min, min(alto_imagen, alto - fijo - alto_texto(ft, len(tit))))
    hm = hm // 2 * 2
    extra = max(0, alto - hm - fijo - alto_texto(ft, len(tit)))
    y_logo = hm + LINEA + PAD[0] + round(extra * 0.38)
    y_texto = y_logo + ISOLOGO + GAP_LOGO + round(min(extra * 0.12, 40))
    return {"alto_imagen": hm, "y_logo": y_logo, "y_texto": y_texto, "zona": (y_texto, alto - PAD[1]),
            "volanta": vtxt, "f_vol": fv, "f_tit": ft, "tit": tit, "tema": tema, "alto": alto}


def base_bloque(plan: dict) -> Image.Image:
    """El cuadro sin la imagen ni el texto: la línea naranja, el bloque del tema y la marca."""
    t = TEMAS[plan["tema"]]
    lienzo = Image.new("RGBA", (W, plan["alto"]), t["fondo"] + (255,))
    d = ImageDraw.Draw(lienzo)
    hm = plan["alto_imagen"]
    d.rectangle((0, hm, W, hm + LINEA), fill=NARANJA)
    lienzo.alpha_composite(lockup(plan["tema"]), (X, plan["y_logo"]))
    return lienzo


def texto_titular(capa: Image.Image, plan: dict, alfa: float = 1.0):
    """La volanta y el titular del plan, en su lugar (con `alfa` para el fundido)."""
    t = TEMAS[plan["tema"]]
    d = ImageDraw.Draw(capa)
    a = round(255 * alfa)
    y = plan["y_texto"]
    if plan["volanta"]:
        d.text((X, y), plan["volanta"], font=plan["f_vol"], fill=t["volanta"] + (a,))
        y += plan["f_vol"].size + GAP_VOLANTA
    escribir(d, X, y, plan["tit"], plan["f_tit"], t["titular"] + (a,))


def cuadro_bloque(imagen, volanta: str, titular: str, tema: str = "blanco", leyenda_img: str = "",
                  proporcion: float = 4 / 3) -> Image.Image:
    """El cuadro 4:5 fijo (portada del reel, primera diapositiva del carrusel)."""
    alto_img = round(W / proporcion)
    plan = plan_bloque(volanta, titular, tema, alto_img)
    lienzo = base_bloque(plan)
    if imagen is not None:
        im = imagen if isinstance(imagen, Image.Image) else Image.open(imagen).convert("RGB")
        lienzo.paste(cubrir(im, W, plan["alto_imagen"]), (0, 0))
        leyenda(lienzo, leyenda_img, plan["alto_imagen"])
    texto_titular(lienzo, plan)
    return lienzo


def texto_leyenda(origen: str, credito: str = "") -> str:
    """Lo que dice la imagen: IA (generada o recreada) o el crédito de la foto oficial."""
    if origen in ("ia", "recreada"):
        return "Imagen generada con IA"
    if origen == "video" and credito:
        return f"Video: {credito}"
    return f"Foto: {credito}" if credito else ""
