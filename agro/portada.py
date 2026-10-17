# -*- coding: utf-8 -*-
"""La portada de cada pieza agro: el cuadro 4:5 estilo bloque (agro/diseno.py), igual al primer tramo
del reel. Es la miniatura del Short, la foto de la nota web y la tapa del carrusel.

Desde el 17/10/2026 (pedido del editor: «4:5, estilo policiales») reemplaza a la portada vertical
1080x1920 del arranque. Sin el nombre del medio de origen. La imagen generada o recreada con IA lleva
«Imagen generada con IA» (Meta pide avisar las imágenes realistas hechas con IA, y es lo honesto con el
lector); la foto de una fuente oficial, su crédito.
"""
from pathlib import Path

from agro import diseno as D

USUARIO = D.USUARIO


def armar(datos: dict, imagen, salida: Path, ia: bool = False, credito: str = "", origen: str = "",
          tema: str = "blanco") -> Path:
    """datos: volanta, portada_seo (o titular). imagen: ruta (o None: solo el bloque, nunca debería pasar).
    Es la MINIATURA: el texto corto con la palabra clave, en letra grande (17/10/2026)."""
    origen = origen or ("ia" if ia else "fuente")
    cuadro = D.cuadro_bloque(imagen, datos.get("volanta"), D.texto_portada(datos), tema,
                             D.texto_leyenda(origen, credito), tope=D.PORTADA)
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    cuadro.convert("RGB").save(salida, "JPEG", quality=92)
    return salida
