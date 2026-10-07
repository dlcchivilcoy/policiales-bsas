# -*- coding: utf-8 -*-
"""Lee las notas de Infobae por sus feeds RSS de sección.

Sondeado el 06/10/2026:
- robots.txt deja todo menos el buscador interno (/buscador), que no se usa.
- Cada sección tiene su feed (Arc Publishing) con las últimas 100 notas: título, fecha, texto
  COMPLETO y foto. Cubren de 3,5 a 8 días, así que una pasada cada 3 horas no pierde nada.
- El feed general NO sirve: son las ediciones de España, México, Colombia…, y 100 notas
  alcanzan para 20 minutos.

LA FOTO (decisión del editor del 07/10, después de un día con placa propia):
la de la nota, SALVO que sea de una AGENCIA (AP, AFP, Reuters, EFE, Getty…): esas agencias
rastrean la web y le facturan cada foto al sitio que la usa. Esas notas siguen con la placa
propia (nacionales/placa.py). El crédito casi nunca viene en el feed (33 de 45 sin crédito el
06/10): está en el EPÍGRAFE de la página («(Foto: Reuters)», «(AP)»), así que se lee la página
de cada nota elegida (3 por pasada). Si la página no contesta, no se sabe de quién es la foto
y va la placa: ante la duda, sin foto.
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
            "imagen": ((e.get("media_content") or [{}])[0].get("url") or "").strip(),
            "credito_feed": " ".join(str(e.get("credit") or "").split()),
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


# Agencias que cobran por foto. Las siglas cortas (AP, NA) van en mayúscula y pegadas a un
# paréntesis, una barra o «Foto:» —«(AP)», «(Foto AP/…)», «NA/»—, para no confundirlas con
# una palabra cualquiera. NA = Noticias Argentinas.
_AGENCIAS = re.compile(r"\b(?:AFP|Reuters|REUTERS|EFE|Getty|GETTY|Bloomberg|Europa Press|Xinhua|XINHUA|DPA|dpa|"
                       r"ANSA|Noticias Argentinas|Associated Press|Shutterstock|iStock|Agencia Brasil|"
                       r"Anadolu|Sputnik|TASS|Kyodo|Yonhap)\b")
_SIGLAS = re.compile(r"(?:[(/:]|\bFotos?)\s*(?:AP|NA)\b|\b(?:AP|NA)\s*[)/]")


def es_de_agencia(credito: str) -> str:
    """La agencia nombrada en el crédito, o "" si no es de agencia."""
    m = _AGENCIAS.search(credito or "") or _SIGLAS.search(credito or "")
    return m.group(0).strip(" (/:") if m else ""


def credito_foto(url: str, cliente=None) -> tuple:
    """(crédito, leído): el epígrafe de la foto principal de la nota. leído=False si la página
    no contestó (y entonces no se sabe de quién es la foto)."""
    from bs4 import BeautifulSoup
    cliente = cliente or httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
    try:
        r = cliente.get(url)
        r.raise_for_status()
    except Exception:                                # noqa: BLE001 — sin página no hay crédito
        return "", False
    fig = BeautifulSoup(r.text, "html.parser").find("figcaption")
    return (" ".join(fig.get_text(" ", strip=True).split()) if fig else ""), True
