# -*- coding: utf-8 -*-
"""Dibuja la placa 1080x1920 del reel con Pillow.

Es un port fiel de `placa_layout()` + el filtergraph de `video.py` del repo
social_publisher. Allá el texto lo estampa ffmpeg con `drawtext` sobre el video; acá
se dibuja con Pillow sobre una imagen fija, porque en esta fase la fuente es una FOTO
de la nota, no un video de corresponsal.

El orden vertical y las reglas de ajuste son los mismos:
  marca → (piso del isologo) → volanta → titular → bajada → imagen → pie
"""
import colorsys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from reels import marca as M

_cache_fuentes: dict = {}


# =============================================================================
# Tipografía
# =============================================================================

def fuente(ruta: Path, cuerpo: int, peso: str = "") -> ImageFont.FreeTypeFont:
    """Carga la fuente pidiendo la INSTANCIA del peso.

    Estas tipografías son variables: sin pedir la instancia sale la Regular, que sobre
    una foto se lee finita y mal. Hay que pedirla igual al medir y al dibujar, si no el
    cálculo de cuánto entra queda mintiendo."""
    clave = (str(ruta), cuerpo, peso)
    if clave in _cache_fuentes:
        return _cache_fuentes[clave]
    try:
        f = ImageFont.truetype(str(ruta), cuerpo)
        if peso:
            try:
                f.set_variation_by_name(peso)
            except Exception:
                pass          # no es variable o no trae ese peso: queda la default
    except OSError:
        f = ImageFont.load_default()
    _cache_fuentes[clave] = f
    return f


def _ancho(draw, texto, f) -> int:
    return round(draw.textlength(texto, font=f))


def _alto_linea(f) -> int:
    """Alto REAL de un renglón: ascendente + descendente de esa tipografía en ese cuerpo.

    NO sirve el bbox de una muestra: mide solo las letras de la muestra y se olvida de la
    cola de la «g», la «p» o la «j», que sobresale por debajo. Con el bbox, la bajada
    arrancaba pegada al titular."""
    try:
        a, d = f.getmetrics()
        return int(a + d)
    except Exception:
        return int(f.size * 1.2)


# =============================================================================
# Reparto del texto en renglones
# =============================================================================

def _envolver(draw, texto, f, ancho_max) -> list:
    """Parte el texto en los renglones que entren en `ancho_max`."""
    palabras = (texto or "").split()
    if not palabras:
        return []
    lineas, linea = [], ""
    for p in palabras:
        probe = (linea + " " + p).strip()
        if _ancho(draw, probe, f) <= ancho_max or not linea:
            linea = probe
        else:
            lineas.append(linea)
            linea = p
    if linea:
        lineas.append(linea)
    return lineas


def _mas_grande_que_entra(draw, texto, ruta, peso, ancho_max, renglones,
                          tam_max, tam_min):
    """El cuerpo MÁS GRANDE con el que `texto` entra en `renglones`. (cuerpo, lineas)
    o (None, []) si ni al mínimo entra."""
    for cuerpo in range(tam_max, tam_min - 1, -2):
        f = fuente(ruta, cuerpo, peso)
        lineas = _envolver(draw, texto, f, ancho_max)
        if len(lineas) <= renglones:
            return cuerpo, lineas
    return None, []


def _emparejar(draw, texto, ruta, peso, cuerpo, ancho_max, renglones) -> list:
    """Reparte el texto PAREJO entre `renglones`, en vez de dejar el último colgando
    con una palabra. Mismo cuerpo, mismos renglones, mejor bloque."""
    palabras = (texto or "").split()
    if len(palabras) <= 1 or renglones <= 1:
        return _envolver(draw, texto, fuente(ruta, cuerpo, peso), ancho_max)
    f = fuente(ruta, cuerpo, peso)
    objetivo = _ancho(draw, texto, f) / renglones
    lineas, linea = [], ""
    for p in palabras:
        probe = (linea + " " + p).strip()
        # Cierra el renglón cuando pasarse del objetivo empeora el reparto.
        if linea and len(lineas) < renglones - 1 and \
                abs(_ancho(draw, probe, f) - objetivo) > abs(_ancho(draw, linea, f) - objetivo):
            lineas.append(linea)
            linea = p
        else:
            linea = probe
    if linea:
        lineas.append(linea)
    if len(lineas) > renglones or any(_ancho(draw, l, f) > ancho_max for l in lineas):
        return _envolver(draw, texto, f, ancho_max)   # el reparto no dio: al método simple
    return lineas


def _oraciones(texto: str) -> list:
    """Corta en oraciones. La bajada SIEMPRE cierra en punto: nunca un «…»."""
    import re
    partes = re.split(r"(?<=[.!?…])\s+", (texto or "").strip())
    return [p.strip() for p in partes if p.strip()]


def _texto_cerrado(draw, texto, ruta, peso, cuerpo, ancho_max, renglones):
    """Las oraciones ENTERAS que entren en `renglones`, o [] si no entra ni la primera.
    Nunca corta a mitad de oración: prefiere decir menos y decirlo completo."""
    f = fuente(ruta, cuerpo, peso)
    acumulado = ""
    for o in _oraciones(texto):
        probe = (acumulado + " " + o).strip()
        if len(_envolver(draw, probe, f, ancho_max)) <= renglones:
            acumulado = probe
        else:
            break
    if not acumulado:
        return []
    return _envolver(draw, acumulado, f, ancho_max)


def _bajada(draw, texto, ruta, peso, ancho_max, renglones, tam_max, tam_min):
    """Cuerpo y renglones de la bajada: oraciones enteras, el cuerpo más grande posible."""
    for cuerpo in range(tam_max, tam_min - 1, -2):
        lineas = _texto_cerrado(draw, texto, ruta, peso, cuerpo, ancho_max, renglones)
        if lineas:
            return cuerpo, lineas
    return tam_min, []


# =============================================================================
# Color de fondo tomado de la imagen
# =============================================================================

def color_de_fondo(foto: Path | None) -> tuple:
    """Saca el color dominante de la foto y lo APAGA (luz baja, saturación corta) para
    que la placa y la imagen se sientan la misma pieza. Sin foto: el gris por defecto."""
    if not foto or not Path(foto).exists():
        return M.PLACA_FONDO
    try:
        im = Image.open(foto).convert("RGB").resize((64, 64))
        # El color más frecuente tras reducir la paleta: más estable que el promedio,
        # que sobre una foto con cielo y asfalto devuelve siempre un gris sucio.
        paleta = im.quantize(colors=8, method=Image.Quantize.FASTOCTREE).convert("RGB")
        colores = sorted(paleta.getcolors(64 * 64), reverse=True)
        r, g, b = colores[0][1]
        h, _, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        r2, g2, b2 = colorsys.hls_to_rgb(h, M.PLACA_FONDO_LUZ, M.PLACA_FONDO_SAT)
        return (round(r2 * 255), round(g2 * 255), round(b2 * 255))
    except Exception:
        return M.PLACA_FONDO


# =============================================================================
# Piezas
# =============================================================================

def _pegar_isologo(canvas: Image.Image) -> tuple:
    """Isologo arriba a la derecha. Devuelve su caja (x0, y0, x1, y1) o None."""
    if not M.LOGO_REEL.exists():
        return None
    iso = Image.open(M.LOGO_REEL).convert("RGBA")
    alto = round(M.LOGO_ANCHO * iso.height / iso.width)
    iso = iso.resize((M.LOGO_ANCHO, alto), Image.LANCZOS)
    x0 = (M.W - M.LOGO_ANCHO - M.LOGO_MX) if M.LOGO_A_LA_DERECHA else M.LOGO_MX
    canvas.paste(iso, (x0, M.LOGO_MY), iso)
    return (x0, M.LOGO_MY, x0 + M.LOGO_ANCHO, M.LOGO_MY + alto)


def _encuadrar(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Cover a sangre con leve sesgo hacia arriba (para no cortar cabezas)."""
    img = img.convert("RGB")
    escala = max(box_w / img.width, box_h / img.height)
    nw, nh = max(1, round(img.width * escala)), max(1, round(img.height * escala))
    re = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - box_w) // 2
    top = max(0, min(int((nh - box_h) * 0.30), nh - box_h))
    return re.crop((left, top, left + box_w, top + box_h))


def _fundir_arriba(canvas: Image.Image, img: Image.Image, y: int, alto_fundido: int):
    """Pega la imagen fundiéndola con el fondo por el borde de ARRIBA."""
    mascara = Image.new("L", img.size, 255)
    px = mascara.load()
    for i in range(min(alto_fundido, img.height)):
        v = round(255 * (i / max(1, alto_fundido)))
        for x in range(img.width):
            px[x, i] = v
    canvas.paste(img, (0, y), mascara)


# =============================================================================
# Composición
# =============================================================================

def componer(guion: dict, foto: Path | None, salida: Path, capas: bool = False) -> dict:
    """Arma la placa. `guion` trae volanta, titular, bajada y (opcional) pie.

    Se dibuja en DOS capas y recién al final se juntan:
      · `base` — el fondo de color y la foto;
      · `capa` — el isologo y TODO el texto, sobre transparente.

    Es lo que permite que el video mueva la foto sin arrastrar el texto: con `capas=True`
    se guardan las dos por separado y ffmpeg anima la de abajo y superpone la de arriba
    quieta. La imagen fija sale de juntar exactamente esas mismas dos capas, así no puede
    haber diferencia entre lo que se ve en el JPG y lo que se ve en el video.

    Devuelve un informe con la geometría real usada — sirve para auditar que nada quedó
    dentro de las zonas que tapan las apps.
    """
    fondo = color_de_fondo(foto)
    base = Image.new("RGB", (M.W, M.H), fondo)
    capa = Image.new("RGBA", (M.W, M.H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    ancho = M.W - 2 * M.PLACA_MX
    informe = {"fondo": fondo, "bloques": []}

    caja_logo = _pegar_isologo(capa)
    y = M.PLACA_Y0

    # --- Marca: a la izquierda, haciendo pareja con el isologo de la derecha ---
    f_marca = fuente(M.FUENTE_ZOCALO, M.PLACA_MARCA_TAM)
    nombres = " | ".join(p.strip() for p in M.MARCA_TEXTO.split("|") if p.strip())
    for txt in (nombres, M.MARCA_USUARIO):
        draw.text((M.PLACA_MX, y), txt, font=f_marca, fill=M.GRIS)
        informe["bloques"].append(("marca", txt, M.PLACA_MARCA_TAM, y))
        y += round(M.PLACA_MARCA_TAM * 1.25)
    y += 46

    # El isologo es MÁS ALTO que el bloque de marca, y la volanta y el titular van
    # centrados y pueden ser anchos. Sin este piso se le montan encima (pasa solo con
    # textos largos, por eso cuesta verlo).
    if caja_logo:
        piso = caja_logo[3] + 26
        if y < piso:
            informe["bajado_por_logo"] = (y, piso)
            y = piso

    # --- Volanta (NARANJA, centrada) ---
    vol = (guion.get("volanta") or "").strip().upper()
    if vol:
        cuerpo, lineas = _mas_grande_que_entra(draw, vol, M.FUENTE_RESUMEN, M.PESO_RESUMEN,
                                               ancho, 1, M.PLACA_VOLANTA_TAM, M.PLACA_VOLANTA_MIN)
        if not cuerpo:   # no entra en un renglón: va a dos, antes que cortarla con «…»
            cuerpo, lineas = _mas_grande_que_entra(draw, vol, M.FUENTE_RESUMEN, M.PESO_RESUMEN,
                                                   ancho, 2, M.PLACA_VOLANTA_TAM, M.PLACA_VOLANTA_MIN)
        if not cuerpo:
            cuerpo = M.PLACA_VOLANTA_MIN
            lineas = _envolver(draw, vol, fuente(M.FUENTE_RESUMEN, cuerpo, M.PESO_RESUMEN), ancho)[:2]
        f = fuente(M.FUENTE_RESUMEN, cuerpo, M.PESO_RESUMEN)
        for l in lineas:
            draw.text(((M.W - _ancho(draw, l, f)) // 2, y), l, font=f, fill=M.NARANJA)
            informe["bloques"].append(("volanta", l, cuerpo, y))
            y += round(cuerpo * 1.2)
        y += 8

    # --- Titular (BLANCO, centrado, lo más grande que entre) ---
    tit = (guion.get("titular") or "").strip()
    if tit:
        cuerpo, _ = _mas_grande_que_entra(draw, tit, M.FUENTE_TITULAR, M.PESO_TITULAR, ancho,
                                          M.PLACA_TITULAR_RENGLONES, M.PLACA_TITULAR_TAM,
                                          M.PLACA_TITULAR_MIN)
        cuerpo = cuerpo or M.PLACA_TITULAR_MIN
        lineas = _emparejar(draw, tit, M.FUENTE_TITULAR, M.PESO_TITULAR, cuerpo, ancho,
                            M.PLACA_TITULAR_RENGLONES)[:M.PLACA_TITULAR_RENGLONES]
        f = fuente(M.FUENTE_TITULAR, cuerpo, M.PESO_TITULAR)
        salto = round(cuerpo * M.PLACA_TITULAR_INTERLINEA)
        for i, l in enumerate(lineas):
            draw.text(((M.W - _ancho(draw, l, f)) // 2, y + i * salto), l, font=f, fill=M.BLANCO)
            informe["bloques"].append(("titular", l, cuerpo, y + i * salto))
        y += (len(lineas) - 1) * salto + _alto_linea(f) + 22

    # --- Bajada (NARANJA, centrada, SIEMPRE cerrada en punto) ---
    baj = (guion.get("bajada") or "").strip()
    if baj:
        cuerpo, lineas = _bajada(draw, baj, M.FUENTE_RESUMEN, M.PESO_RESUMEN, ancho,
                                 M.PLACA_BAJADA_RENGLONES, M.PLACA_BAJADA_TAM, M.PLACA_BAJADA_MIN)
        if lineas:
            parejo = _emparejar(draw, " ".join(lineas), M.FUENTE_RESUMEN, M.PESO_RESUMEN,
                                cuerpo, ancho, len(lineas))
            if parejo:
                lineas = parejo
            f = fuente(M.FUENTE_RESUMEN, cuerpo, M.PESO_RESUMEN)
            salto = round(cuerpo * M.PLACA_BAJADA_INTERLINEA)
            for i, l in enumerate(lineas):
                draw.text(((M.W - _ancho(draw, l, f)) // 2, y + i * salto), l, font=f, fill=M.NARANJA)
                informe["bloques"].append(("bajada", l, cuerpo, y + i * salto))
            y += (len(lineas) - 1) * salto + _alto_linea(f)

    # --- Imagen a sangre ---
    y_img = min(y + 46, M.H - M.PLACA_IMG_MIN)
    y_img = max(M.PLACA_Y0, y_img)
    informe["y_img"] = y_img
    alto_img = M.H - y_img

    hay_pie = bool((guion.get("pie") or "").strip())
    if foto and Path(foto).exists():
        try:
            original = Image.open(foto)
            prop = original.width / original.height
            alto_natural = round(M.W / prop)
            # Una foto apaisada deja un hueco abajo. Ese hueco es el lugar del PIE; pero
            # si no hay pie que poner, el hueco queda como una franja de color muerta que
            # se come el tercio inferior del reel. En ese caso conviene recortar la foto
            # para que LLENE el cuadro: se pierde algo de los costados y se gana un reel
            # que no parece a medio armar.
            if alto_natural < alto_img and hay_pie:
                img = original.convert("RGB").resize((M.W, alto_natural), Image.LANCZOS)
                _fundir_arriba(base, img, y_img, M.PLACA_FUNDIDO)
                informe["pie_zona"] = (y_img + alto_natural, M.H - M.BANDA_SEGURO)
            else:
                img = _encuadrar(original, M.W, alto_img)
                _fundir_arriba(base, img, y_img, M.PLACA_FUNDIDO)
                informe["pie_zona"] = None
                if alto_natural < alto_img:
                    informe["foto_recortada"] = "apaisada sin pie: se recortó para llenar"
        except Exception as e:
            informe["error_foto"] = f"{type(e).__name__}: {e}"
    else:
        informe["error_foto"] = "sin foto"

    # --- Pie: la primera oración fuerte, en el hueco bajo una foto apaisada ---
    pie = (guion.get("pie") or "").strip()
    zona = informe.get("pie_zona")
    if pie and zona:
        desde, hasta = zona
        hueco = hasta - desde
        if hueco >= M.PLACA_PIE_MIN_ALTO:
            elegido = None
            for cuerpo in range(M.PLACA_PIE_TAM, M.PLACA_PIE_MIN - 1, -2):
                f = fuente(M.FUENTE_RESUMEN, cuerpo, M.PESO_RESUMEN)
                salto = round(cuerpo * M.PLACA_PIE_INTERLINEA)
                alto_l = _alto_linea(f)
                if alto_l > hueco:
                    continue
                # El hueco es chico y fijo, así que acá manda el hueco: para cada cuerpo se
                # calcula CUÁNTOS renglones entran y recién ahí se prueba el texto.
                cabe = min(M.PLACA_PIE_RENGLONES, 1 + max(0, (hueco - alto_l) // salto))
                lineas = _texto_cerrado(draw, pie, M.FUENTE_RESUMEN, M.PESO_RESUMEN,
                                        cuerpo, ancho, cabe)
                if lineas:
                    elegido = (cuerpo, lineas, salto, (len(lineas) - 1) * salto + alto_l)
                    break
            if elegido:
                cuerpo, lineas, salto, alto = elegido
                f = fuente(M.FUENTE_RESUMEN, cuerpo, M.PESO_RESUMEN)
                y0 = desde + max(0, (hueco - alto) // 2)
                for i, l in enumerate(lineas):
                    draw.text(((M.W - _ancho(draw, l, f)) // 2, y0 + i * salto), l,
                              font=f, fill=M.GRIS)
                    informe["bloques"].append(("pie", l, cuerpo, y0 + i * salto))
            else:
                informe["pie_omitido"] = f"no entra en {hueco}px"

    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    final = base.convert("RGBA")
    final.alpha_composite(capa)
    final.convert("RGB").save(salida, quality=95)
    informe["archivo"] = str(salida)
    informe["alto_imagen"] = alto_img

    if capas:
        # La capa de texto, con su transparencia, para que ffmpeg la superponga quieta.
        ruta_texto = salida.with_name(salida.stem + "_texto.png")
        capa.save(ruta_texto)
        informe["capa_texto"] = str(ruta_texto)

        # La foto ya recortada al hueco exacto, al DOBLE de resolución: el zoom lento del
        # video se come píxeles, y si se parte de 1080 de ancho la imagen llega blanda al
        # final del movimiento. Con 2160 hay margen para todo el recorrido.
        ruta_foto = salida.with_name(salida.stem + "_foto.jpg")
        if foto and Path(foto).exists():
            try:
                recorte = _encuadrar(Image.open(foto), M.W * 2, alto_img * 2)
                recorte.save(ruta_foto, quality=94)
                informe["capa_foto"] = str(ruta_foto)
            except Exception as e:
                informe["capa_foto_error"] = f"{type(e).__name__}: {e}"

        # El fondo solo (sin foto ni texto): lo usa el video cuando no hay imagen.
        ruta_fondo = salida.with_name(salida.stem + "_fondo.png")
        Image.new("RGB", (M.W, M.H), fondo).save(ruta_fondo)
        informe["capa_fondo"] = str(ruta_fondo)

    return informe


def auditar(informe: dict) -> list:
    """Avisos si algún texto cayó en una zona que la app tapa. Devuelve [] si está bien."""
    avisos = []
    tope = M.SEGURO_ARRIBA
    piso = M.H - M.BANDA_SEGURO
    for tipo, texto, cuerpo, y in informe.get("bloques", []):
        if y < tope:
            avisos.append(f"{tipo} «{texto[:28]}» arranca en y={y}, sobre el techo ({tope})")
        if y + cuerpo > piso:
            avisos.append(f"{tipo} «{texto[:28]}» termina en y={y + cuerpo}, bajo el piso ({piso})")
    return avisos
