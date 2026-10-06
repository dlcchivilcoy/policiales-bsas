# -*- coding: utf-8 -*-
"""Lee las notas de Infobae por sus feeds RSS de sección.

Sondeado el 06/10/2026:
- robots.txt deja todo menos el buscador interno (/buscador), que no se usa.
- Cada sección tiene su feed (Arc Publishing) con las últimas 100 notas: título, fecha, texto
  COMPLETO y foto. Cubren de 3,5 a 8 días, así que una pasada cada 3 horas no pierde nada.
- El feed general NO sirve: son las ediciones de España, México, Colombia…, y 100 notas
  alcanzan para 20 minutos.

La FOTO de Infobae no se usa nunca (decisión del editor del 06/10): sus fotos son de sus
fotógrafos o de agencias, y los reclamos de derechos caerían sobre la página entera. Las
piezas salen con la placa propia (nacionales/placa.py). Por eso acá ni se guarda.
"""
import calendar
import re

import httpx

SECCIONES = ("politica", "economia", "sociedad", "sociedad/policiales", "judiciales", "salud")
FEED = "https://www.infobae.com/arc/outboundfeeds/rss/category/{seccion}/?outputType=xml"
SITIO = "https://www.infobae.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}


def _texto(html: str) -> str:
    from bs4 import BeautifulSoup
    return " ".join(BeautifulSoup(html or "", "html.parser").get_text(" ").split())


def notas_del_feed(xml: str, seccion: str) -> list:
    """Las notas de UN feed, sin red (se prueba solo)."""
    import feedparser
    salida = []
    for e in feedparser.parse(xml).entries:
        url = (e.get("link") or "").split("?")[0]
        if not url.startswith(SITIO):
            continue
        cuerpo = _texto((e.get("content") or [{}])[0].get("value", ""))
        salida.append({
            "url": url,
            "seccion_feed": seccion,
            "titulo": " ".join((e.get("title") or "").split()),
            "resumen": _texto(e.get("summary") or ""),
            "cuerpo": cuerpo,
            "fecha": calendar.timegm(e.published_parsed) if e.get("published_parsed") else 0,
        })
    return salida


def bajar(secciones=SECCIONES, cliente=None) -> tuple:
    """(notas, fallas). Una sección que no contesta no frena las otras."""
    cliente = cliente or httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
    notas, vistas, fallas = [], set(), []
    for s in secciones:
        try:
            r = cliente.get(FEED.format(seccion=s))
            r.raise_for_status()
        except Exception as e:                       # noqa: BLE001 — una sección no frena el resto
            fallas.append(f"{s}: {type(e).__name__}: {str(e)[:120]}")
            continue
        for n in notas_del_feed(r.text, s):
            if n["url"] not in vistas:
                vistas.add(n["url"])
                notas.append(n)
    return notas, fallas


def ruta(url: str) -> str:
    """/politica/2026/10/05/... (la sección real sale de acá, no del feed)."""
    return re.sub(r"^https?://[^/]+", "", url or "")
