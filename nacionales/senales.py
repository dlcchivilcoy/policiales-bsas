# -*- coding: utf-8 -*-
"""Señales REALES de impacto para el puntaje (pedido del editor del 18/10/2026: «las notas que tengan más
impacto viral y generen mejor interacción, SEO, viralidad, compartidas, me gusta, comentarios…»).

Todas son datos observados, nada inventado (PDF, apartado 7: «no declares viral algo porque una
herramienta generó ese adjetivo»):
- LECTORES: las listas «Las más leídas» / «Lo más visto» de El Cronista, La Nación, Ámbito y Clarín
  (lo que la gente está leyendo AHORA, con su puesto).
- BÚSQUEDAS (SEO): las búsquedas en tendencia de Google en la Argentina, con su volumen aproximado.
- AGENDA: Google News Argentina (portada y secciones): el orden en que Google pone cada tema y cuántos
  medios distintos lo cubren.
- INTERACCIÓN: los videos en tendencia de YouTube Argentina, con vistas, me gusta y comentarios (solo
  en la nube, con el token del canal; 1 unidad de cupo por pasada).
Facebook ya no informa compartidos ni reacciones de notas ajenas (probado el 18/10/2026: da 0 en todas),
e Instagram, TikTok y X no tienen una vía autorizada para medir posteos de otros: no se usan.
"""
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import httpx

from nacionales.infobae import HEADERS, _texto

# (medio, portada, dónde empieza la lista, links de notas, cuántos)
MAS_LEIDAS = (
    ("El Cronista", "https://www.cronista.com/", r"most-read__list",
     r'href="(https://www\.cronista\.com/[a-z0-9-]+/[a-z0-9-]{20,}/?)"', 8),
    ("La Nación", "https://www.lanacion.com.ar/", r">Más leídas<", r'href="(/[a-z0-9-]+/[^"]+-nid\d+/?)"', 10),
    ("Ámbito", "https://www.ambito.com/", r"(?i)masleidas", r'href="(https://www\.ambito\.com/[^"]+-n\d+)"', 10),
    ("Clarín", "https://www.clarin.com/", r"(?i)(?:lomasvisto|mostread)",
     r'href="((?:https://www\.clarin\.com)?/(?!suscripciones|centro-de-ayuda)[a-z0-9-]+/[^"]+_0_[^"]+\.html)"', 8),
)
TENDENCIAS = "https://trends.google.com/trending/rss?geo=AR"
GN = "https://news.google.com/rss{}?hl=es-419&gl=AR&ceid=AR:es-419"
GOOGLE_NEWS = (("portada", GN.format("")),
               ("nacionales", GN.format("/headlines/section/topic/NATION")),
               ("internacionales", GN.format("/headlines/section/topic/WORLD")),
               ("deportes", GN.format("/headlines/section/topic/SPORTS")),
               ("espectaculos", GN.format("/headlines/section/topic/ENTERTAINMENT")),
               ("tecnologia_ia", GN.format("/headlines/section/topic/TECHNOLOGY")))
YT_API = "https://www.googleapis.com/youtube/v3/videos"


def slug_a_texto(url: str) -> str:
    """«/deportes/dibu-martinez-sufrio-un-fuerte-golpe-n6334968» → «dibu martinez sufrio un fuerte golpe»."""
    partes = [p for p in re.sub(r"^https?://[^/]+", "", url).split("/") if p]
    slug = max(partes, key=len) if partes else ""
    slug = re.sub(r"(_0_\w+\.html|-nid\d+|-n\d+|-id\d+\.html|\.html)$", "", slug)
    return " ".join(slug.split("-"))


def mas_leidas_de(html: str, medio: str, base: str, marca: str, patron: str, tope: int) -> list:
    m = re.search(marca, html)
    if not m:
        return []
    raiz = re.match(r"https://[^/]+", base).group(0)
    urls = []
    for l in re.findall(patron, html[m.start():m.start() + 25000]):
        u = (l if l.startswith("http") else raiz + l).split("?")[0]
        if u not in urls:
            urls.append(u)
    return [{"medio": medio, "puesto": i, "url": u, "texto": slug_a_texto(u)} for i, u in enumerate(urls[:tope], 1)]


def _trafico(t: str) -> int:
    d = re.sub(r"\D", "", t or "")
    return int(d) if d else 0


def tendencias_de(xml: str) -> list:
    """Las búsquedas en tendencia: [{consulta, trafico, titulos}] (los titulares que Google asocia)."""
    ns = {"ht": "https://trends.google.com/trending/rss"}
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return []
    salida = []
    for it in raiz.iter("item"):
        consulta = (it.findtext("title") or "").strip()
        if not consulta:
            continue
        salida.append({"consulta": consulta, "trafico": _trafico(it.findtext("ht:approx_traffic", "", ns)),
                       "titulos": [(n.findtext("ht:news_item_title", "", ns) or "").strip()
                                   for n in it.findall("ht:news_item", ns)]})
    return salida


def google_news_de(xml: str, seccion: str) -> list:
    """[{seccion, puesto, de, titulos, medios}]: cada tema de Google News con los (hasta 5) titulares y
    medios que Google junta en él."""
    import feedparser
    salida = []
    entradas = feedparser.parse(xml).entries
    for i, e in enumerate(entradas, 1):
        resumen = e.get("summary") or ""
        titulos = [_texto(t) for t in re.findall(r"<a [^>]*>(.*?)</a>", resumen)]
        medios = re.findall(r'<font color="#6f6f6f">([^<]+)</font>', resumen)
        principal = re.sub(r"\s+-\s+[^-]+$", "", e.get("title") or "")
        salida.append({"seccion": seccion, "puesto": i, "de": len(entradas), "titulos": [principal] + titulos,
                       "medios": sorted({m.strip() for m in medios} | {(e.get("source") or {}).get("title", "")} - {""})})
    return salida


def youtube_tendencias(sesion=None) -> list:
    """Los 50 videos en tendencia de YouTube Argentina con sus números reales. Vacío si no hay token
    (en la PC suele no estar: solo en la nube)."""
    if not (os.environ.get("YT_TOKEN_JSON") or "").strip():
        return []
    if sesion is None:
        from reels import publicador as PUB
        sesion = PUB._yt_sesion
    r = httpx.get(YT_API, params={"part": "snippet,statistics", "chart": "mostPopular", "regionCode": "AR",
                                  "maxResults": 50}, headers={"Authorization": f"Bearer {sesion()}"}, timeout=30)
    r.raise_for_status()
    salida = []
    for v in r.json().get("items") or []:
        s, sn = v.get("statistics") or {}, v.get("snippet") or {}
        salida.append({"titulo": sn.get("title") or "", "canal": sn.get("channelTitle") or "",
                       "vistas": int(s.get("viewCount") or 0), "me_gusta": int(s.get("likeCount") or 0),
                       "comentarios": int(s.get("commentCount") or 0), "id": v.get("id")})
    return salida


def juntar(cliente=None, con_youtube: bool = True) -> dict:
    """Todas las señales de una vez (en paralelo). Lo que falla queda en «fallas» y no frena nada."""
    cliente = cliente or httpx.Client(headers=HEADERS, timeout=25, follow_redirects=True)
    senales = {"mas_leidas": [], "tendencias": [], "google_news": [], "youtube": [], "fallas": []}

    def pedir(tarea):
        tipo, args = tarea
        try:
            if tipo == "youtube":
                return tipo, youtube_tendencias(), ""
            r = cliente.get(args[1])
            r.raise_for_status()
            if tipo == "mas_leidas":
                return tipo, mas_leidas_de(r.text, *args), ""
            if tipo == "tendencias":
                return tipo, tendencias_de(r.text), ""
            return tipo, google_news_de(r.text, args[0]), ""
        except Exception as e:                       # noqa: BLE001
            return tipo, [], f"{tipo} {args[0] if args else ''}: {type(e).__name__}: {str(e)[:80]}"

    tareas = [("mas_leidas", m) for m in MAS_LEIDAS] + [("tendencias", ("Google Trends", TENDENCIAS))]
    tareas += [("google_news", g) for g in GOOGLE_NEWS]
    if con_youtube:
        tareas.append(("youtube", ()))
    with ThreadPoolExecutor(max_workers=8) as ex:
        for tipo, lista, falla in ex.map(pedir, tareas):
            senales[tipo] += lista
            if falla:
                senales["fallas"].append(falla)
    for m in MAS_LEIDAS:
        if not any(x["medio"] == m[0] for x in senales["mas_leidas"]):
            senales["fallas"].append(f"más leídas de {m[0]}: no se encontró la lista")
    return senales


def vacias() -> dict:
    """Sin señales (las pruebas, o cuando la red no anda)."""
    return {"mas_leidas": [], "tendencias": [], "google_news": [], "youtube": [], "fallas": []}
