# -*- coding: utf-8 -*-
"""LOS MEDIOS DE LA COMPETENCIA NO SE USAN (15/11/2026, pedido del editor).

«Para los policiales no scrappees medios o notas que estén sacadas de La Razón de Chivilcoy, La Gaceta del
Oeste, DeChivilcoy o Chivilcoy al Día. Hoy subiste una nota sacada de La Razón, que es mi competencia.»

Ninguno de esos medios está en el padrón (scraper/medios.py), pero otros los copian: el 15/11 Junín 24 publicó
el choque de Chivilcoy con la foto de La Razón (con su marca de agua) y salió en nuestro carrusel. Dos controles:

- `en_texto`: la nota (URL, título, texto, crédito, URL de la foto) nombra a uno de esos medios o a su dominio
  («Fuente: La Razón», «Foto: Chivilcoy al Día», «dechivilcoy.com.ar»…). «La razón» suelta no cuenta: es una
  frase común; cuenta «La Razón de Chivilcoy», «diario La Razón» o «La Razón» como crédito o fuente.
- `en_imagen`: Gemini mira la foto (y un cuadro del video) y dice si tiene la marca de agua, el logo o la firma
  de alguno. Si la IA no contesta, la pieza sigue (no se frena todo por una falla de la IA).

COMPETENCIA_IMAGEN=0 apaga el control de la imagen; el del texto no se apaga.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

MEDIOS = ("La Razón de Chivilcoy", "La Gaceta del Oeste", "DeChivilcoy", "Chivilcoy al Día")
DOMINIOS = ("larazondechivilcoy", "gacetadeloeste", "dechivilcoy", "chivilcoyaldia")

_RAZON = "La Razón de Chivilcoy"
PATRONES = (
    (_RAZON, r"la razon de chivilcoy|larazondechivilcoy|diario la razon\b"),
    (_RAZON, r"(?:fuente|foto|fotos|imagen|imagenes|gentileza|credito|creditos|via|informacion)\s*:?\s*"
             r"(?:diario\s+)?la razon\b"),
    (_RAZON, r"segun (?:informo|publico|indico|consigno)\s+(?:el\s+)?(?:diario\s+)?la razon\b"),
    (_RAZON, r"\(\s*(?:foto:?\s*)?la razon\s*\)"),
    ("La Gaceta del Oeste", r"la gaceta del oeste|gacetadeloeste"),
    ("DeChivilcoy", r"dechivilcoy|de chivilcoy\s*\.\s*com"),
    ("Chivilcoy al Día", r"chivilcoy al dia|chivilcoyaldia"),
)
_RX = [(m, re.compile(p)) for m, p in PATRONES]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def en_texto(*textos) -> str:
    """El nombre del medio de la competencia que aparece en alguno de los textos, o ""."""
    junto = _norm(" ".join(str(t or "") for t in textos))
    for medio, rx in _RX:
        if rx.search(junto):
            return medio
    return ""


def de_la_nota(nota: dict) -> str:
    """El medio de la competencia que nombra la nota (URL, título, textos, créditos, foto), o ""."""
    claves = ("url", "titulo", "resumen", "copete", "cuerpo", "texto_completo", "imagen", "credito",
              "credito_foto", "fuente", "medio", "dominio", "video", "video_titulo")
    return en_texto(*(nota.get(k) for k in claves))


SISTEMA = (
    "Mirás imágenes de una noticia. Decí si en alguna se ve la MARCA DE AGUA, el LOGO o la FIRMA de alguno de "
    "estos medios de Chivilcoy: «La Razón de Chivilcoy» (a veces solo «LA RAZON»), «La Gaceta del Oeste», "
    "«DeChivilcoy» o «Chivilcoy al Día». Solo si se lee o se reconoce el nombre; otros logos o textos no cuentan. "
    'Respondé SOLO con JSON: {"medio": "el nombre del medio, o vacío si no hay ninguno", "donde": "dónde se ve"}')


def activo_imagen() -> bool:
    return (os.environ.get("COMPETENCIA_IMAGEN") or "1").strip() != "0"


def en_imagen(rutas, preguntar=None) -> str:
    """El medio de la competencia cuya marca se ve en alguna de las imágenes, o "". Si la IA no contesta, ""."""
    if not activo_imagen():
        return ""
    rutas = [Path(r) for r in rutas or [] if r and Path(r).is_file()]
    if not rutas:
        return ""
    try:
        if preguntar is None:
            from reels import ia as IA
            if IA.proveedor_disponible() != "gemini":
                return ""
            partes = [("image/jpeg", r.read_bytes()) for r in rutas]
            crudo, _via = IA.redactar_gemini(SISTEMA, f"Van {len(rutas)} imagen(es).", max_tokens=200, imagenes=partes)
            datos = IA._parsear(crudo)
        else:
            datos = preguntar(rutas)
    except Exception as e:                           # noqa: BLE001 — sin la IA, la pieza sigue
        print(f"   (control de la competencia en la imagen: la IA no contestó: {type(e).__name__})", flush=True)
        return ""
    dicho = str((datos or {}).get("medio") or "").strip()
    if not dicho:
        return ""
    return en_texto(dicho) or next((m for m in MEDIOS if _norm(m) in _norm(dicho) or _norm(dicho) in _norm(m)), "") \
        or (_RAZON if "razon" in _norm(dicho) else "")


def motivo(medio: str) -> str:
    return f"copiada de {medio}, un medio de la competencia (pedido del editor: no se usan)"
