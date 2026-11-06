# -*- coding: utf-8 -*-
"""La portada de cada pieza agro: la tapa 4:5 de los carruseles (agro/carrusel.py), sin número ni flecha.
Es la miniatura del reel y del Short y la foto de la nota web.

Desde el 6/11/2026 usa el diseño nuevo del bot y policiales. Sin el nombre del medio de origen. La imagen generada o recreada con IA lleva
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
    from agro import carrusel as CAR
    origen = origen or ("ia" if ia else "fuente")
    return CAR.tapa(imagen, datos, D.texto_portada(datos), tema, D.texto_leyenda(origen, credito), salida)
