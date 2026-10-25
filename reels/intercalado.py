# -*- coding: utf-8 -*-
"""Intercalado dentro de cada cuenta: nunca dos policiales seguidos (pedido del editor, 17/10/2026,
PDF «Prompt integral», etapa 3).

Antes de subir un reel policial a Instagram o a Facebook se mira lo ÚLTIMO publicado en esa cuenta,
venga de donde venga (el bot del diario, nacionales, las entrevistas, a mano o nosotros). Si es
policial, el reel espera dentro de la pasada a que salga otra temática; si no sale a tiempo, esa
red se saltea para ese reel (YouTube y la web siguen igual). Nunca se rellena ni se borra ni se
mueve nada ajeno.

Qué es policial:
- un posteo nuestro (su ID está en estado/publicados.json), o
- un posteo ajeno que el diccionario del scraper (scraper/keywords.py) da por policial: el bot
  también publica choques, robos y operativos de Chivilcoy.
El 16-17/10 la madrugada tenía hasta tres policiales seguidos en Instagram.

Variables: INTERCALADO=0 lo apaga; MIN_NON_POLICE_POSTS_BETWEEN_POLICE (1) cuántos posteos de otra
temática tiene que haber entre dos policiales.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from scraper import keywords as KW

REDES = ("instagram", "facebook")
# En el ledger, qué entradas son publicaciones en cada cuenta (el enlace del Short también es
# un posteo de la página de Facebook).
CAMPOS = {"instagram": ("instagram",), "facebook": ("facebook", "fb_youtube")}
# Lo nuestro recién publicado puede tardar en aparecer en el listado de la cuenta.
DEMORA_LISTADO = timedelta(minutes=2)


def activo() -> bool:
    """APAGADO de fábrica desde el 25/10/2026: el editor pidió 5 policiales, uno cada 30 minutos de 19 a 21
    (corrida de las 18:30), y con el intercalado prendido el 24/10 Instagram dejó esperando 3 de los 5.
    INTERCALADO=1 lo vuelve a prender."""
    return (os.environ.get("INTERCALADO") or "0").strip().lower() not in ("0", "no", "false", "off")


def minimo() -> int:
    try:
        return max(1, int(os.environ.get("MIN_NON_POLICE_POSTS_BETWEEN_POLICE") or 1))
    except ValueError:
        return 1


def es_policial_texto(texto: str) -> bool:
    """El diccionario del scraper sobre un posteo: la primera línea pesa como titular."""
    lineas = [l.strip() for l in (texto or "").splitlines()
              if l.strip() and not l.lstrip().startswith(("#", "📲", "📰"))]
    if not lineas:
        return False
    return KW.es_probable_policial(lineas[0], " ".join(lineas[1:6]))


def cuando_local(ts: str):
    """«2026-10-17T18:11:00+0000» (Meta, UTC) → hora local sin zona, como `publicador._ahora()`
    (en la nube, UTC; en una PC de acá, la argentina)."""
    try:
        return datetime.fromisoformat((ts or "").replace("+0000", "+00:00")).astimezone().replace(tzinfo=None)
    except ValueError:
        return None


def propios(ledger: dict, red: str) -> tuple:
    """(IDs de nuestras publicaciones en esa cuenta, cuándo fue la última)."""
    ids, ultima = set(), None
    for e in ledger.values():
        if not isinstance(e, dict):
            continue
        for campo in CAMPOS[red]:
            r = e.get(campo) or {}
            if r.get("estado") not in ("ok", "sin_confirmar"):
                continue
            if r.get("id"):
                ids.add(str(r["id"]))
            try:
                c = datetime.fromisoformat(r.get("cuando") or "")
            except ValueError:
                continue
            ultima = c if ultima is None or c > ultima else ultima
    return ids, ultima


def clasificar(posteos: list, ids_propios: set) -> list:
    """posteos: [{"id", "cuando" (datetime), "texto", "adjuntos": [ids]}] → con "policial" y "propio"."""
    out = []
    for p in posteos:
        ids = {str(p.get("id") or "")} | {str(p.get("id") or "").split("_")[-1]} | \
              {str(a) for a in (p.get("adjuntos") or []) if a}
        propio = bool(ids & ids_propios)
        out.append(dict(p, propio=propio, policial=propio or es_policial_texto(p.get("texto") or "")))
    return out


def libre(red: str, posteos, ledger: dict, n: int = None) -> tuple:
    """(se puede publicar un policial ya, motivo). `posteos` None = no se pudo leer la cuenta:
    se publica igual (perder el reel por un bache de lectura es peor) y queda dicho."""
    n = n or minimo()
    ids, ultima_nuestra = propios(ledger, red)
    if posteos is None:
        return True, "no se pudo leer la cuenta: sale sin verificar el intercalado"
    lista = clasificar(posteos, ids)
    # Lo nuestro que todavía no aparece en el listado (Meta tarda en mostrarlo) cuenta igual, en su
    # hora; si empata con un posteo ajeno, se lo da por último: ante la duda, no se pega otro.
    if ultima_nuestra and not any(p["propio"] and p.get("cuando") and
                                  abs(p["cuando"] - ultima_nuestra) <= DEMORA_LISTADO for p in lista):
        lista.append({"cuando": ultima_nuestra, "texto": "(nuestro último reel policial)",
                      "policial": True, "propio": True})
    lista.sort(key=lambda p: (p.get("cuando") or datetime.min, p["propio"]), reverse=True)
    for p in lista[:n]:
        if p["policial"]:
            quien = "nuestro" if p["propio"] else "de otro origen"
            texto = " ".join((p.get("texto") or "").split())[:70]
            return False, (f"intercalado: lo último en {'Instagram' if red == 'instagram' else 'Facebook'} "
                           f"ya es un policial ({quien}: «{texto}»); espera otra temática")
    return True, ""


def peso(pieza: dict, bono: int = 0) -> float:
    """Entre varios reels que esperan el mismo hueco, va el de más interés (viral + cercanía)."""
    return (pieza.get("viral") or 5) + bono
