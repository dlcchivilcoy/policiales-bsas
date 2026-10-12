# -*- coding: utf-8 -*-
"""La ETIQUETA DE UBICACIÓN del reel de Instagram según la localidad del hecho (pedido del editor, 12/10/2026).

«📍 Chacabuco, Buenos Aires» arriba del reel: lo ubica en la página de ese lugar y en las búsquedas de
la zona. (Cambiar la IP desde donde se publica NO sirve para esto: Instagram no reparte por la IP del
que sube, y una cuenta que publica desde una ciudad distinta cada 5 minutos parece hackeada.)

`location_id` es el ID de la PÁGINA DE LUGAR de Facebook de la ciudad (categoría «Localidad»). La API
no deja buscarlos (Place Search cerrado para terceros desde 2020), así que viven en
reels/ubicaciones.json, sacados del buscador de lugares de Instagram y validados contra la API con
`python tools/ubicaciones_ig.py --validar`. Localidad sin ID = el reel sale sin ubicación, como antes.
"""
import json
import unicodedata
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parent / "ubicaciones.json"


def clave(texto: str) -> str:
    """«San Andrés de Giles» / «san andres de giles» / «Ciudad de Chacabuco» → «san andres de giles» / «chacabuco»."""
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = " ".join(t.replace(",", " ").split())
    for prefijo in ("ciudad de ", "partido de "):
        if t.startswith(prefijo):
            t = t[len(prefijo):]
    return t.split(" buenos aires")[0].strip()


def cargar() -> dict:
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def location_id(localidad: str, tabla: dict = None) -> str:
    """El location_id de la localidad del hecho, o '' si no hay (el reel sale sin ubicación)."""
    tabla = cargar() if tabla is None else tabla
    dato = tabla.get(clave(localidad)) or {}
    return str(dato.get("id") or "") if dato.get("valido", True) else ""
