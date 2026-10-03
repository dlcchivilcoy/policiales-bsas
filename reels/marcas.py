# -*- coding: utf-8 -*-
"""¿La foto o el video del medio traen su logo o su marca de agua?

Pedido del editor el 03/10/2026: que en los reels no se note de qué medio sale la nota.
La marca NO se borra ni se tapa: es la firma del medio sobre su foto, y quitarla para
republicarla es otra cosa que contar la noticia con palabras propias. Lo que se hace es
NO USAR esa imagen: reels/flujo.py busca la misma noticia en otro medio con una imagen
limpia y, si no hay, arma una imagen ilustrativa propia (reels/ilustrativa.py).

Quién mira: Gemini, con el mismo pool gratis de claves que redacta los guiones. Una
llamada por foto y una por video (dos cuadros juntos).

Si no se puede mirar (sin claves, sin cupo, imagen que no abre), la respuesta es «no sé»
(marca=None) y la imagen se usa igual, con un aviso: el control es un filtro, y que falle
no tiene que dejar la pasada sin reels. Se apaga sin tocar código con MARCAS=0.
"""
import io
import os

PROMPT = """Mirás imágenes que acompañan una noticia policial de un medio digital argentino.
Decí si ALGUNA tiene una MARCA agregada encima de la imagen, que delate de qué medio sale:
- el logo o el nombre de un medio, radio, canal, portal o productora, en una esquina o en
  el medio, aunque sea chico o transparente (marca de agua);
- una dirección web (www…, .com, .com.ar), un usuario de redes (@…) o «Foto: <medio>»;
- una placa armada por el medio: titular, zócalo, volanta o texto escrito encima de la foto.
NO cuentan, porque son parte de lo que se fotografió: carteles de la calle, la palabra
POLICÍA o BOMBEROS en un vehículo o un uniforme, patentes, nombres de comercios, y el escudo
o logo de un organismo oficial (Policía, Ministerio de Seguridad, Municipio, Bomberos)
puesto encima de una foto de prensa oficial.
Respondé SOLO con este JSON:
{"marca": true o false, "que": "si hay marca: qué dice o qué es y dónde está, en pocas palabras"}"""

LADO_MAXIMO = 1024        # más grande no le agrega nada a Gemini y gasta más tokens


def activo() -> bool:
    return (os.environ.get("MARCAS") or "1").strip() != "0"


def _jpeg(ruta) -> bytes:
    """La imagen como JPEG chico. b"" si no abre (AVIF sin soporte, archivo roto)."""
    try:
        from PIL import Image, ImageOps
        with Image.open(ruta) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85)
            return buf.getvalue()
    except Exception:
        return b""


def revisar(rutas) -> dict:
    """{"marca": True|False|None, "que": str}. None = no se pudo saber."""
    if not activo():
        return {"marca": None, "que": "control apagado (MARCAS=0)"}
    imagenes = tuple(b for b in (_jpeg(r) for r in rutas if r) if b)
    if not imagenes:
        return {"marca": None, "que": "la imagen no se pudo abrir para revisarla"}
    from reels import ia
    try:
        texto, detalle = ia.redactar_gemini(PROMPT, f"{len(imagenes)} imagen(es) a revisar.",
                                            imagenes=imagenes)
        datos = ia._parsear(texto)
    except Exception as e:
        return {"marca": None, "que": "no se pudo revisar: " + " ".join(str(e).split())[:120]}
    valor = datos.get("marca")
    if isinstance(valor, str):
        valor = valor.strip().lower() in ("true", "si", "sí", "1")
    if not isinstance(valor, bool):
        return {"marca": None, "que": "Gemini no contestó si hay marca"}
    return {"marca": valor, "que": " ".join(str(datos.get("que") or "").split())[:160],
            "via": detalle}
