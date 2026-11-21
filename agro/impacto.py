# -*- coding: utf-8 -*-
"""EL ESTILO «IMPACTO» de los carruseles y las portadas de @diarioyradioagro (20/11/2026).

Pedido del editor: «para diarioyradioagro necesito que hagas carruseles como este [un carrusel de una cuenta
grande del agro] … necesito que copies el estilo». Se toma el LENGUAJE VISUAL (no la marca ni los textos de nadie):

  - Tapa 4:5: la foto arriba que se funde en un fondo grafito; arriba a la izquierda nuestra marca y a la derecha
    una ETIQUETA verde («PARA GUARDAR», «MERCADOS», «CHIVILCOY»); abajo, la volanta en verde espaciada, la CIFRA
    enorme en verde con lo que mide al costado en mayúsculas, el título en mayúsculas condensadas (Anton) con las
    palabras clave en verde y «DESLIZÁ →».
  - Láminas: fondo grafito, el número de lámina, el título condensado, el dato grande si lo hay y el texto claro;
    los puntos como chips con tilde verde.
  - Cierre: la pregunta para comentar (con la parte clave en verde), «guardalo y compartilo» y la cuenta.

AGRO_CARRUSEL_ESTILO=bot vuelve a las placas del diario (las de antes).
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from agro import diseno as D

W, H = D.W, D.H45
FONDO = (27, 29, 32)
VERDE = (141, 205, 62)
VERDE_OSCURO = (24, 40, 14)
NARANJA = D.NARANJA_MARCA                # el naranja del isologo (21/11/2026)
BLANCO = (255, 255, 255)
GRIS = (196, 200, 206)
GRIS_TENUE = (130, 135, 142)
M = 72                                   # margen
ALTO_FOTO = 930
ANTON = D.MARCA / "Anton-Regular.ttf"           # Google Fonts, licencia OFL (OFL-Anton.txt)
MESES = re.compile(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b", re.I)


def activo() -> bool:
    return (os.environ.get("AGRO_CARRUSEL_ESTILO") or "impacto").strip().lower() != "bot"


@lru_cache(maxsize=64)
def anton(tam: int):
    try:
        return ImageFont.truetype(str(ANTON), tam)
    except OSError:
        return D.fuente("negra", tam)


def _norm(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Texto: renglones con palabras en verde
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _marcas(palabras: list, destacado: str) -> list:
    """[bool | "naranja"] por palabra: True (verde) si es parte de `destacado` (la primera vez que aparece,
    completo); "naranja" lo que va ANTES de los dos puntos (20/11/2026, pedido del editor: «usá también mi color
    naranja para los textos»: la primera parte naranja y la segunda verde, como el isologo)."""
    marca = [False] * len(palabras)
    corte = next((i + 1 for i, p in enumerate(palabras[:-1]) if p.endswith(":")), 0)
    for k in range(corte):
        marca[k] = "naranja"
    obj = [_norm(re.sub(r"[^\w%$.,]", "", p)) for p in (destacado or "").split()]
    obj = [o for o in obj if o]
    if not obj:
        return marca
    limpias = [_norm(re.sub(r"[^\w%$.,]", "", p)) for p in palabras]
    for i in range(len(palabras) - len(obj) + 1):
        if limpias[i:i + len(obj)] == obj:
            for k in range(i, i + len(obj)):
                marca[k] = True
            break
    # Sin dos puntos (20/11/2026, el editor: «en esos también»): lo que no es la palabra clave va en naranja, así
    # todo título es naranja + verde, como el isologo.
    if not corte and any(m is True for m in marca):
        marca = [m if m is True else "naranja" for m in marca]
    return marca


def destacado_de(titulo: str, sugerido: str = "") -> str:
    """Las palabras en verde: las que propone la IA si están en el título; si no, lo que va después de los dos
    puntos; si no, las últimas tres."""
    if sugerido and _norm(sugerido) in _norm(titulo):
        return sugerido
    if ":" in titulo:
        return titulo.split(":", 1)[1].strip()
    p = titulo.split()
    return " ".join(p[-3:]) if len(p) > 4 else ""


def _renglones(d: ImageDraw.ImageDraw, palabras: list, f, ancho: int) -> list:
    """[[(palabra, i)]]: corta en renglones que entran en `ancho`."""
    salida, linea, largo = [], [], 0
    esp = d.textlength(" ", font=f)
    for i, p in enumerate(palabras):
        w = d.textlength(p, font=f)
        if linea and largo + esp + w > ancho:
            salida.append(linea)
            linea, largo = [], 0
        largo += (esp if linea else 0) + w
        linea.append((p, i))
    if linea:
        salida.append(linea)
    return salida


def _equilibrar(d, linea: list, f, ancho: int) -> list:
    """Los mismos renglones que el corte común, pero repartidos PAREJOS: de todos los cortes posibles con esa
    cantidad de renglones, el que deja el renglón más largo lo más corto posible (y los demás parecidos). Así no
    queda «SE PERDIÓ EL 42 % DE LA» arriba y «SOJA» sola abajo."""
    from itertools import combinations
    base = [[linea[j] for _p, j in r] for r in _renglones(d, [p for p, _ in linea], f, ancho)]
    n, k = len(base), len(linea)
    if n <= 1 or k > 22:
        return base
    esp = d.textlength(" ", font=f)
    w = [d.textlength(p, font=f) for p, _ in linea]

    def largo(a, b):
        return sum(w[a:b]) + esp * (b - a - 1)
    mejor, puntos = None, None
    for cortes in combinations(range(1, k), n - 1):
        lim = (0, *cortes, k)
        anchos = [largo(lim[j], lim[j + 1]) for j in range(n)]
        if max(anchos) > ancho:
            continue
        clave = (round(max(anchos)), sum((a - sum(anchos) / n) ** 2 for a in anchos))
        if mejor is None or clave < mejor:
            mejor, puntos = clave, lim
    if puntos is None:
        return base
    return [linea[puntos[j]:puntos[j + 1]] for j in range(n)]


def _renglones_titulo(d, palabras: list, f, ancho: int) -> list:
    """Los renglones de un TÍTULO (20/11/2026, pedido del editor: «que después de los dos puntos vaya un renglón
    aparte, con equilibrio y simetría»): lo que sigue a «:» arranca renglón nuevo, y cada parte se reparte en
    renglones parejos (_equilibrar)."""
    pares = [(p, i) for i, p in enumerate(palabras)]
    corte = next((i + 1 for i, p in enumerate(palabras[:-1]) if p.endswith(":")), None)
    partes = [pares[:corte], pares[corte:]] if corte else [pares]
    salida = []
    for parte in partes:
        salida += _equilibrar(d, parte, f, ancho)
    return salida


def ajustar(d, texto: str, ancho: int, max_renglones: int, tope: int, piso: int, mayus: bool = True):
    """(fuente, renglones, palabras): Anton lo más grande posible en `max_renglones`, cortado como título
    (después de «:» renglón aparte; renglones parejos)."""
    palabras = (texto.upper() if mayus else texto).split()
    for tam in range(tope, piso - 1, -4):
        f = anton(tam)
        r = _renglones_titulo(d, palabras, f, ancho)
        if len(r) <= max_renglones:
            return f, r, palabras
    f = anton(piso)
    r = _renglones_titulo(d, palabras, f, ancho)
    if len(r) > max_renglones:                           # no entra ni al mínimo: el corte común, como antes
        r = _renglones(d, palabras, f, ancho)
    return f, r[:max_renglones], palabras


def escribir(im: Image.Image, x: int, y: int, renglones: list, f, marca: list, color=BLANCO, verde=VERDE,
             salto: float = 1.02) -> int:
    """Escribe los renglones (con las palabras marcadas en verde); devuelve la y de abajo."""
    d = ImageDraw.Draw(im)
    esp = d.textlength(" ", font=f)
    alto = round(f.size * salto)
    ultima = y
    for linea in renglones:
        xx = x
        for p, i in linea:
            d.text((xx, y), p, font=f, fill=D.NARANJA_MARCA if marca[i] == "naranja" else verde if marca[i] else color)
            xx += d.textlength(p, font=f) + esp
        ultima = y
        y += alto
    # Lo que de verdad ocupa el último renglón (Anton dibuja más abajo de lo que dice su tamaño).
    return ultima + f.getbbox("HÁGQ")[3] if renglones else y


def alto_bloque(f, n: int, salto: float = 1.02) -> int:
    return round(f.size * salto) * n


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Piezas comunes
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _marca(im: Image.Image, y: int = 56, alto: int = 70) -> None:
    lg = D.lockup("grafito", alto)
    im.alpha_composite(lg, (M, y)) if im.mode == "RGBA" else im.paste(lg, (M, y), lg)


def _etiqueta(im: Image.Image, texto: str, y: int = 66) -> None:
    if not texto:
        return
    d = ImageDraw.Draw(im)
    f = D.fuente("bold", 26)
    txt = " ".join(texto.upper().split())[:28]
    tw = d.textlength(txt, font=f) + 4 * len(txt) * 0.0
    w = tw + 40 + 30
    x = W - M - w
    # 21/11/2026 (el editor: «usá también el color naranja en diarioyradioagro para mis carruseles»): la etiqueta, la
    # volanta, la raya de las láminas y «deslizá» van en el naranja del isologo; las cifras y los tildes, en verde.
    d.rounded_rectangle((x, y, x + w, y + 50), radius=8, fill=NARANJA)
    # El marcador (la cinta de «guardar»).
    bx, by = x + 18, y + 13
    d.polygon([(bx, by), (bx + 18, by), (bx + 18, by + 25), (bx + 9, by + 18), (bx, by + 25)], fill=FONDO)
    d.text((x + 50, y + 10), txt, font=f, fill=FONDO)


def _deslizá(im: Image.Image, y: int, x: int = M) -> None:
    d = ImageDraw.Draw(im)
    f = D.fuente("bold", 28)
    d.text((x, y), "DESLIZÁ", font=f, fill=BLANCO)
    cx = x + d.textlength("DESLIZÁ", font=f) + 44
    cy = y + 17
    d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), outline=NARANJA, width=4)
    d.line((cx - 11, cy, cx + 10, cy), fill=NARANJA, width=4)
    d.polygon([(cx + 13, cy), (cx + 3, cy - 9), (cx + 3, cy + 9)], fill=NARANJA)


def _foto(imagen, alto: int = ALTO_FOTO) -> Image.Image:
    """La foto llenando el ancho y `alto` (se recorta lo que sobra, centrado un poco arriba), o un fondo liso."""
    if imagen and Path(str(imagen)).is_file():
        f = Image.open(imagen).convert("RGB")
        return ImageOps.fit(f, (W, alto), Image.LANCZOS, centering=(0.5, 0.42))
    return Image.new("RGB", (W, alto), (60, 70, 52))


def _degradado(im: Image.Image, desde: int, hasta: int, color=FONDO) -> None:
    """Funde la foto en el color de fondo entre `desde` y `hasta` (y abajo de `hasta`, liso)."""
    capa = Image.new("RGBA", (W, H), color + (0,))
    a = Image.new("L", (1, H), 0)
    for y in range(H):
        t = 0 if y < desde else (1 if y >= hasta else (y - desde) / (hasta - desde))
        a.putpixel((0, y), round(255 * (t ** 0.85)))
    capa.putalpha(a.resize((W, H)))
    im.alpha_composite(capa)
    # Arriba, una sombra suave para que se lean la marca y la etiqueta.
    sombra = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
    sa = Image.new("L", (1, 260), 0)
    for y in range(260):
        sa.putpixel((0, y), round(120 * (1 - y / 260) ** 1.6))
    sombra.putalpha(sa.resize((W, 260)))
    im.alpha_composite(sombra, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Tapa
# ─────────────────────────────────────────────────────────────────────────────────────────────
def tapa(imagen, d: dict, destino: Path, leyenda: str = "", deslizar: bool = True) -> Path:
    """d: titulo, destacado, volanta, etiqueta, cifra, cifra_rotulo. La foto arriba y el texto abajo, desde el pie."""
    im = Image.new("RGBA", (W, H), FONDO + (255,))
    im.paste(_foto(imagen), (0, 0))
    _degradado(im, 430, ALTO_FOTO - 40)
    _marca(im)
    _etiqueta(im, d.get("etiqueta") or "")
    dr = ImageDraw.Draw(im)
    titulo = " ".join((d.get("titulo") or "").split()).rstrip(".")
    ancho = W - 2 * M
    # De abajo para arriba: deslizá, el título, la cifra, la volanta.
    y_pie = H - 92
    f_t, r_t, pal = ajustar(dr, titulo, ancho, 3 if d.get("cifra") else 4, 104 if not d.get("cifra") else 84, 52)
    marca = _marcas(pal, destacado_de(titulo, d.get("destacado") or "").upper())
    y_t = y_pie - 60 - alto_bloque(f_t, len(r_t))
    cifra = (d.get("cifra") or "").strip()
    y_c = y_t
    if cifra:
        f_c = anton(250)
        while dr.textlength(cifra, font=f_c) > ancho * 0.66 and f_c.size > 120:
            f_c = anton(f_c.size - 10)
        alto_c = f_c.size
        y_c = y_t - 18 - round(alto_c * 1.04)
        # Anton tiene aire arriba: se sube un poco para que la cifra apoye en la línea del título.
        dr.text((M - 4, y_c - round(alto_c * 0.12)), cifra, font=f_c, fill=VERDE)
        rot = (d.get("cifra_rotulo") or "").upper().split()
        if rot:
            x_r = M + dr.textlength(cifra, font=f_c) + 24
            ancho_r = W - M - x_r
            f_r = anton(70)
            rr = _renglones(dr, rot, f_r, ancho_r)
            while (len(rr) > 4 or alto_bloque(f_r, len(rr), 1.0) > alto_c * 0.92) and f_r.size > 34:
                f_r = anton(f_r.size - 4)
                rr = _renglones(dr, rot, f_r, ancho_r)
            y_r = y_c + round(alto_c * 0.92) - alto_bloque(f_r, len(rr), 1.0)
            escribir(im, round(x_r), y_r, rr, f_r, [False] * len(rot), salto=1.0)
    if d.get("volanta"):
        f_v = D.fuente("bold", 30)
        vol = " ".join(d["volanta"].upper().split())
        y_v = (y_c if cifra else y_t) - 58
        _espaciado(dr, (M, y_v), vol[:40], f_v, NARANJA, 4)
    escribir(im, M, y_t, r_t, f_t, marca)
    if deslizar:
        _deslizá(im, y_pie)
    if leyenda:
        f_l = D.fuente("regular", 22)
        dr.text((W - M - dr.textlength(leyenda[:70], font=f_l), y_pie + 6), leyenda[:70], font=f_l, fill=GRIS_TENUE)
    return _guardar(im, destino)


def _espaciado(dr, xy, texto, f, color, extra: int = 4) -> None:
    x, y = xy
    for c in texto:
        dr.text((x, y), c, font=f, fill=color)
        x += dr.textlength(c, font=f) + extra


def _guardar(im: Image.Image, destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return destino


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Láminas y cierre
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _cabeza(im: Image.Image, i, n) -> None:
    dr = ImageDraw.Draw(im)
    _marca(im, 56, 60)
    if i is not None:                                     # en el reel no hay «2/5»
        f = D.fuente("bold", 30)
        txt = f"{i}/{n}"
        dr.text((W - M - dr.textlength(txt, font=f), 70), txt, font=f, fill=GRIS_TENUE)
    dr.rectangle((M, 160, M + 90, 168), fill=NARANJA)


def lamina(x: dict, i: int, n: int, destino: Path, volanta: str = "", reel: bool = False) -> Path:
    """x: titulo, texto | puntos, dato, dato_rotulo. `reel`: sin «2/5» ni «deslizá» (es una placa de un reel)."""
    im = Image.new("RGBA", (W, H), FONDO + (255,))
    _cabeza(im, None if reel else i, n)
    dr = ImageDraw.Draw(im)
    ancho = W - 2 * M
    y = 214
    if volanta:
        _espaciado(dr, (M, y), " ".join(volanta.upper().split())[:40], D.fuente("bold", 28), NARANJA, 4)
        y += 60
    titulo = (x.get("titulo") or "").rstrip(".")
    f_t, r_t, pal = ajustar(dr, titulo, ancho, 3, 112, 64)
    y = escribir(im, M, y, r_t, f_t, _marcas(pal, destacado_de(titulo).upper()))
    y += 44
    dato = (x.get("dato") or "").strip()
    if dato and re.search(r"\d", dato) and not MESES.search(dato):     # una fecha no va como cifra gigante
        f_d = anton(170)
        while dr.textlength(dato, font=f_d) > ancho and f_d.size > 80:
            f_d = anton(f_d.size - 10)
        y_d = y - round(f_d.size * 0.12)
        dr.text((M - 3, y_d), dato, font=f_d, fill=VERDE)
        y = y_d + f_d.getbbox(dato)[3] + 18
        if x.get("dato_rotulo"):
            f_r = D.fuente("bold", 36)
            dr.text((M, y), x["dato_rotulo"].upper()[:48], font=f_r, fill=BLANCO)
            y += 64
        y += 16
    elif dato and MESES.search(dato):                                  # la fecha, en una línea en verde
        f_r = D.fuente("bold", 36)
        rot = (x.get("dato_rotulo") or "").strip().rstrip(":.")
        linea = (f"{rot[0].upper()}{rot[1:]}: {dato}" if rot else dato)[:60]
        dr.text((M, y), linea, font=f_r, fill=VERDE)
        y += 76
    if x.get("puntos"):
        f_p = D.fuente("medium", 38)
        for p in x["puntos"][:4]:
            r = D.renglones(dr, p, f_p, ancho - 120)[:3]
            alto = 36 + len(r) * 50
            dr.rounded_rectangle((M, y, W - M, y + alto), radius=16, fill=(40, 43, 47))
            cx, cy = M + 44, y + 24 + 25
            dr.line((cx - 13, cy, cx - 4, cy + 10, cx + 14, cy - 12), fill=VERDE, width=6, joint="curve")
            for k, linea in enumerate(r):
                dr.text((M + 86, y + 18 + k * 50), linea, font=f_p, fill=BLANCO)
            y += alto + 18
    elif x.get("texto"):
        f_x = D.fuente("regular", 44)
        for linea in D.renglones(dr, x["texto"], f_x, ancho)[:9]:
            dr.text((M, y), linea, font=f_x, fill=GRIS)
            y += 60
    if i < n and not reel:
        _deslizá(im, H - 92)
    return _guardar(im, destino)


def cierre(pregunta: str, n: int, destino: Path, imagen=None) -> Path:
    # 20/11/2026 (el editor: «la placa final de los reels/carruseles, actualizá el logo e isologo»): el carrusel
    # termina con LA MISMA placa final que los reels (agro/reel.cierre: isologo nuevo, nombre, usuario, redes),
    # con la pregunta como frase. AGRO_CIERRE_PLACA=0 vuelve a la lámina de la pregunta grande.
    if os.environ.get("AGRO_CIERRE_PLACA", "1").strip() != "0":
        from agro import reel as RE
        pregunta = (pregunta or "").strip() or "¿Qué opinás?"
        frase = pregunta if "comentario" in pregunta.lower() else f"{pregunta} Contanos en los comentarios"
        return _guardar(RE.cierre("grafito", frase, H), destino)
    im = Image.new("RGBA", (W, H), FONDO + (255,))
    if imagen:
        foto = _foto(imagen, H).filter(ImageFilter.GaussianBlur(14))
        im.paste(foto, (0, 0))
        im.alpha_composite(Image.new("RGBA", (W, H), FONDO + (205,)))
    _cabeza(im, n, n)
    dr = ImageDraw.Draw(im)
    pregunta = pregunta or "¿Qué opinás?"
    f, r, pal = ajustar(dr, pregunta, W - 2 * M, 5, 120, 64)
    y = 330
    y = escribir(im, M, y, r, f, _marcas(pal, destacado_de(pregunta).upper()))
    dr.text((M, y + 36), "CONTANOS EN LOS COMENTARIOS", font=D.fuente("bold", 34), fill=VERDE)
    y0 = H - 330
    dr.rectangle((M, y0, W - M, y0 + 2), fill=(70, 74, 80))
    dr.text((M, y0 + 40), "Guardalo y compartilo con alguien del campo.", font=D.fuente("medium", 38), fill=GRIS)
    lg = D.lockup("grafito", 80)
    im.alpha_composite(lg, (M, y0 + 120))
    f_u = D.fuente("bold", 36)
    dr.text((W - M - dr.textlength(D.USUARIO, font=f_u), y0 + 142), D.USUARIO, font=f_u, fill=VERDE)
    return _guardar(im, destino)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Desde el guion y el contenido del carrusel
# ─────────────────────────────────────────────────────────────────────────────────────────────
CIFRA = re.compile(r"(?:US\$|u\$s|\$|\+|-|−)?\s?\d[\d.,]*\s?(?:°\s?C|°|%|ha\b|hectáreas|millones|mil|t\b|toneladas|qq|kg|"
                   r"mm|cabezas|litros)?", re.I)


def cifra_corta(texto: str) -> str:
    """La cifra con su unidad, corta para la tapa («40%», «+50.000 ha», «US$ 372»), o ''."""
    m = CIFRA.search(texto or "")
    if not m:
        return ""
    c = " ".join(m.group(0).split()).replace("hectáreas", "ha").replace("toneladas", "t")
    return c if len(c) <= 12 and re.search(r"\d", c) else ""


def datos_tapa(g: dict, c: dict = None) -> dict:
    c = c or {}
    titulo = c.get("gancho") or D.texto_portada(g) or g.get("titular", "")
    cifra = cifra_corta(c.get("cifra_tapa") or "")
    rotulo = c.get("cifra_rotulo") or ""
    if not cifra:
        for x in c.get("diapositivas") or []:
            cifra = cifra_corta(x.get("dato") or "")
            if cifra and x.get("dato_rotulo"):
                rotulo = x["dato_rotulo"]
                break
            cifra = ""
    return {"titulo": titulo, "destacado": destacado_de(titulo, c.get("destacado") or ""),
            "volanta": (g.get("volanta") or "").split("·")[0].strip(), "etiqueta": c.get("etiqueta") or "PARA GUARDAR",
            "cifra": cifra, "cifra_rotulo": " ".join(rotulo.split()[:6])}
