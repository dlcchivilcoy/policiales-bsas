# -*- coding: utf-8 -*-
"""TODOS los portales del PDF «Prompt integral», con su ORDEN de importancia por categoría (pedido del
editor del 18/10/2026: «scrapeá todos los portales que te envié en el PDF… hay un ranking de sitios por
categoría y es en ese orden que le tenés que dar la importancia»).

Cada fuente se lee por la vía que tiene (probadas el 18/10/2026, ver data/registro_fuentes.json):
- «rss»: el feed del portal (Infobae, La Nación, Ámbito, Clarín, Olé, El Cronista, BBC Mundo, Liga
  Profesional, Zapier, Microsoft, HubSpot, n8n).
- «espn»: la API pública en JSON que usa la propia web de ESPN.
- «lista»: la portada o el listado de la sección (TyC Sports, AFA, Google Workspace y Shopify no tienen
  RSS): se toman los links de notas en el orden en que aparecen y de cada una se lee la página (título,
  bajada, foto, fecha y texto).
Las que no dejan leer (EFE, AP y Make contestan 403; Reuters solo da titulares en inglés; Netflix Tudum
no tiene listado) quedan en el registro, inactivas, y NO cuentan para el ranking.

El ranking que usa nacionales/impacto.py es el orden del PDF entre las fuentes ACTIVAS de cada categoría.
"""
import calendar
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx

from nacionales.infobae import HEADERS, _texto

ARC = "https://www.{sitio}/arc/outboundfeeds/rss/category/{seccion}/?outputType=xml"
INFOBAE = lambda s: ARC.format(sitio="infobae.com", seccion=s)        # noqa: E731
LANACION = lambda s: ARC.format(sitio="lanacion.com.ar", seccion=s)   # noqa: E731
AMBITO = "https://www.ambito.com/rss/pages/{}.xml"
CLARIN = "https://www.clarin.com/rss/{}/"
TN = "https://tn.com.ar/arc/outboundfeeds/rss/category/{}/?outputType=xml"
OLE = "https://www.ole.com.ar/rss/{}/"
ESPN_ARG = "https://site.api.espn.com/apis/site/v2/sports/soccer/arg.1/news?lang=es&region=ar&limit=50"
ESPN_TODO = "https://now.core.api.espn.com/v1/sports/news?lang=es&region=ar&limit=50"

# El ORDEN del PDF por categoría (apartados 3 a 7), y después los portales que el mismo PDF pide como
# «cobertura y contexto complementarios». Una fuente inactiva no ocupa lugar (ver ranking()).
RANKING = {
    # 3. Fuentes nacionales y economía
    "nacionales": ["Infobae", "Ámbito", "El Cronista", "La Nación", "Clarín"],
    # 4. Internacionales y agencias (EFE, Reuters y AP: inactivas, ver el registro)
    # TN, a pedido del editor (18/10/2026): su sección Internacional trae los videos virales del mundo.
    "internacionales": ["EFE", "Reuters", "AP", "BBC Mundo", "Infobae", "La Nación", "TN", "Clarín", "Ámbito"],
    # 5. Deportivas, más AFA y la Liga Profesional como fuentes primarias
    "deportes": ["TyC Sports", "ESPN", "Olé", "AFA", "Liga Profesional", "Infobae", "La Nación", "Clarín",
                 "Ámbito"],
    # 6. IA aplicada a empresas y emprendedores (Make: inactiva), y los diarios
    "tecnologia_ia": ["Zapier", "Make", "Google Workspace", "Microsoft", "HubSpot", "n8n", "Shopify",
                      "El Cronista", "Infobae", "La Nación", "Clarín", "Ámbito"],
    # 7. Espectáculos, cine, series y virales: Infobae Teleshow, Netflix Tudum (inactiva) y las secciones
    # de Infobae, La Nación, Clarín y El Cronista
    "espectaculos": ["Infobae", "Netflix Tudum", "La Nación", "Clarín", "El Cronista", "Ámbito"],
    "cine_series": ["Infobae", "Netflix Tudum", "La Nación", "Clarín", "El Cronista", "Ámbito"],
    "virales": ["Infobae", "La Nación", "Clarín", "El Cronista", "Ámbito"],
}
BLOGS = {"Zapier", "Make", "Google Workspace", "Microsoft", "HubSpot", "n8n", "Shopify"}
INACTIVAS = {"EFE": "403: bloquea la lectura automática (Cloudflare)",
             "AP": "403: bloquea la lectura automática",
             "Reuters": "solo titulares en inglés y las notas bloqueadas (DataDome)",
             "Make": "403: bloquea la lectura automática (Cloudflare)",
             "Netflix Tudum": "sin listado ni RSS (404)"}
DOMINIOS = {"infobae.com": "Infobae", "ambito.com": "Ámbito", "cronista.com": "El Cronista",
            "lanacion.com.ar": "La Nación", "clarin.com": "Clarín", "tycsports.com": "TyC Sports",
            "espn.com.ar": "ESPN", "espn.com": "ESPN", "ole.com.ar": "Olé", "afa.com.ar": "AFA",
            "ligaprofesional.ar": "Liga Profesional", "bbc.com": "BBC Mundo", "zapier.com": "Zapier",
            "workspace.google.com": "Google Workspace", "microsoft.com": "Microsoft",
            "blog.hubspot.com": "HubSpot", "hubspot.com": "HubSpot", "n8n.io": "n8n", "blog.n8n.io": "n8n",
            "shopify.com": "Shopify", "tn.com.ar": "TN"}

# (categoría, fuente, vía, url, extra). Categoría «espectaculos+cine»: lo que es de cine o series va a
# cine_series y lo demás a espectáculos. «general»: secciones generales de donde solo se sacan los
# VIRALES (el título lo dice: «video viral», «se viralizó»…) y, para las nacionales, la cobertura.
FUENTES = (
    # --- Deportes (TyC, ESPN, Olé, AFA, Liga Profesional, y los diarios) ---
    ("deportes", "TyC Sports", "lista", "https://www.tycsports.com/",
     {"links": r'href="((?:https://www\.tycsports\.com)?/[a-z0-9-]+/[a-z0-9-]+-id\d+\.html)"', "max": 10}),
    ("deportes", "ESPN", "espn", ESPN_ARG, {}),
    ("deportes", "ESPN", "espn", ESPN_TODO, {}),
    ("deportes", "Olé", "rss", OLE.format("ultimas-noticias"), {}),
    ("deportes", "Olé", "rss", OLE.format("seleccion"), {}),
    ("deportes", "AFA", "lista", "https://www.afa.com.ar/es/posts",
     {"links": r'href="(https://www\.afa\.com\.ar/es/posts/(?!categories/)[a-z0-9-]+)"', "max": 8}),
    ("deportes", "Liga Profesional", "rss", "https://www.ligaprofesional.ar/feed/", {}),
    ("deportes", "Infobae", "rss", INFOBAE("deportes"), {}),
    ("deportes", "La Nación", "rss", LANACION("deportes"), {}),
    ("deportes", "Clarín", "rss", CLARIN.format("deportes"), {}),
    ("deportes", "Ámbito", "rss", AMBITO.format("deportes"), {}),
    # --- Espectáculos, cine y series ---
    ("espectaculos", "Infobae", "rss", INFOBAE("teleshow"), {}),
    ("cine_series", "Infobae", "rss", INFOBAE("que-puedo-ver"), {}),
    ("espectaculos+cine", "Infobae", "rss", INFOBAE("entretenimiento"), {}),
    ("espectaculos+cine", "La Nación", "rss", LANACION("espectaculos"), {}),
    ("espectaculos+cine", "Clarín", "rss", CLARIN.format("espectaculos"), {}),
    ("espectaculos+cine", "Ámbito", "rss", AMBITO.format("espectaculos"), {}),
    # --- Mundo ---
    ("internacionales", "BBC Mundo", "rss", "https://feeds.bbci.co.uk/mundo/rss.xml", {}),
    ("internacionales", "Infobae", "rss", INFOBAE("america"), {}),
    ("internacionales", "La Nación", "rss", LANACION("el-mundo"), {}),
    ("internacionales", "TN", "rss", TN.format("internacional"), {}),
    ("internacionales", "Clarín", "rss", CLARIN.format("mundo"), {}),
    ("internacionales", "Ámbito", "rss", AMBITO.format("mundo"), {}),
    # --- Virales ---
    ("virales", "Infobae", "rss", INFOBAE("virales"), {}),
    ("general", "Infobae", "rss", INFOBAE("sociedad"), {}),
    ("general", "La Nación", "rss", LANACION("sociedad"), {}),
    ("general", "Clarín", "rss", CLARIN.format("sociedad"), {}),
    ("general", "Clarín", "rss", CLARIN.format("internacional"), {}),
    ("general", "Clarín", "rss", CLARIN.format("lo-ultimo"), {}),
    ("general", "Ámbito", "rss", AMBITO.format("informacion-general"), {}),
    ("general", "El Cronista", "rss", "https://www.cronista.com/files/rss/news.xml", {}),
    # --- IA para comercios y emprendedores ---
    ("tecnologia_ia", "Zapier", "rss", "https://zapier.com/blog/feeds/latest/", {}),
    ("tecnologia_ia", "Google Workspace", "lista", "https://workspace.google.com/blog/ai-and-machine-learning",
     {"links": r'href="((?:https://workspace\.google\.com)?/blog/[a-z0-9-]+/[a-z0-9-]+)"', "max": 8}),
    ("tecnologia_ia", "Microsoft", "rss", "https://www.microsoft.com/en-us/copilot/blog/feed/", {}),
    ("tecnologia_ia", "HubSpot", "rss", "https://blog.hubspot.com/marketing/rss.xml", {}),
    ("tecnologia_ia", "HubSpot", "rss", "https://blog.hubspot.com/sales/rss.xml", {}),
    ("tecnologia_ia", "HubSpot", "rss", "https://blog.hubspot.com/service/rss.xml", {}),
    ("tecnologia_ia", "n8n", "rss", "https://blog.n8n.io/rss/", {}),
    ("tecnologia_ia", "Shopify", "lista", "https://www.shopify.com/blog",
     {"links": r'href="((?:https://www\.shopify\.com)?/blog/(?!latest|topics|search|tags?/)[a-z0-9-]{12,})"',
      "max": 8}),
    ("tecnologia_ia", "El Cronista", "rss", "https://www.cronista.com/files/rss/news.xml", {}),
    ("tecnologia_ia", "Infobae", "rss", INFOBAE("tecno"), {}),
    ("tecnologia_ia", "La Nación", "rss", LANACION("tecnologia"), {}),
    ("tecnologia_ia", "Clarín", "rss", CLARIN.format("tecnologia"), {}),
    ("tecnologia_ia", "Ámbito", "rss", AMBITO.format("tecnologia"), {}),
)

# Nacionales generales: Infobae sigue armando las piezas («actualidad general y detección de temas»,
# PDF 3); los otros cuatro portales del apartado 3 dan la COBERTURA del tema para el puntaje.
FUENTES_NACIONALES = (
    ("nacionales", "Ámbito", "rss", AMBITO.format("home"), {}),
    ("nacionales", "Ámbito", "rss", AMBITO.format("economia"), {}),
    ("nacionales", "Ámbito", "rss", AMBITO.format("politica"), {}),
    ("nacionales", "El Cronista", "rss", "https://www.cronista.com/files/rss/economia-politica.xml", {}),
    ("nacionales", "La Nación", "rss", LANACION("politica"), {}),
    ("nacionales", "La Nación", "rss", LANACION("economia"), {}),
    ("nacionales", "La Nación", "rss", LANACION("sociedad"), {}),
    ("nacionales", "Clarín", "rss", CLARIN.format("politica"), {}),
    ("nacionales", "Clarín", "rss", CLARIN.format("economia"), {}),
    ("nacionales", "Clarín", "rss", CLARIN.format("sociedad"), {}),
)


def ranking(cat: str) -> list:
    """El orden del PDF entre las fuentes ACTIVAS de la categoría."""
    activas = {f[1] for f in FUENTES + FUENTES_NACIONALES}
    return [m for m in RANKING.get(cat, []) if m in activas and m not in INACTIVAS]


def fuente_de(n: dict) -> str:
    """El nombre de la fuente: el de la nota o, si no lo trae, el del dominio."""
    if n.get("fuente"):
        return n["fuente"]
    dom = re.sub(r"^https?://(www\.)?", "", n.get("url") or "").split("/")[0]
    return DOMINIOS.get(dom) or DOMINIOS.get(".".join(dom.split(".")[-2:])) or n.get("medio") or dom


def nota_nueva(url: str, cat: str, fuente: str, titulo: str, resumen: str = "", cuerpo: str = "",
               fecha: float = 0, imagen: str = "", credito: str = "") -> dict:
    blog = fuente in BLOGS
    return {"url": url, "seccion_feed": cat, "categoria": cat, "fuente": fuente,
            # «medio» vacío = el blog de una empresa: el guion atribuye todo a ella (y puede nombrarla).
            "medio": "" if blog else fuente, "es_blog": blog,
            "titulo": " ".join((titulo or "").split()), "resumen": (resumen or "")[:600], "cuerpo": cuerpo or "",
            "fecha": fecha or 0, "imagen": imagen or "", "credito_feed": " ".join((credito or "").split())}


# =============================================================================
# Las vías de lectura
# =============================================================================

def _imagen_rss(e) -> str:
    for m in (e.get("media_content") or []) + (e.get("media_thumbnail") or []):
        if (m.get("url") or "").startswith("http") and "video" not in (m.get("type") or ""):
            return m["url"].strip()
    for l in e.get("links") or []:
        if (l.get("type") or "").startswith("image/") and (l.get("href") or "").startswith("http"):
            return l["href"]
    return ""


def notas_rss(xml: str, cat: str, fuente: str) -> list:
    import feedparser
    salida = []
    for e in feedparser.parse(xml).entries:
        url = (e.get("link") or "").split("?")[0].split("#")[0]
        if not url.startswith("https://"):
            continue
        cuerpo = _texto((e.get("content") or [{}])[0].get("value", "")) or _texto(e.get("summary") or "")
        f = e.get("published_parsed") or e.get("updated_parsed")
        salida.append(nota_nueva(url, cat, fuente, e.get("title") or "", _texto(e.get("summary") or ""), cuerpo,
                                 calendar.timegm(f) if f else 0, _imagen_rss(e), str(e.get("credit") or "")))
    return salida


def _iso(texto: str) -> float:
    try:
        return datetime.fromisoformat((texto or "").strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def notas_espn(js: str, cat: str, fuente: str) -> list:
    """La API de ESPN (la misma que usa su web): titular, bajada, foto y link."""
    try:
        datos = json.loads(js)
    except ValueError:
        return []
    salida = []
    for a in datos.get("articles") or datos.get("headlines") or []:
        links = a.get("links") or {}
        url = ((links.get("web") or {}).get("href") or "").split("?")[0]
        if not url.startswith("https://") or "/video/" in url:      # los clips sueltos no son notas
            continue
        img = next((i.get("url") for i in a.get("images") or [] if (i.get("url") or "").startswith("http")), "")
        salida.append(nota_nueva(url, cat, fuente, a.get("headline") or "", a.get("description") or "",
                                 a.get("story") and _texto(a["story"]) or "", _iso(a.get("published")), img))
    return salida


def links_de_lista(html: str, patron: str, base: str, tope: int) -> list:
    raiz = re.match(r"https://[^/]+", base).group(0)
    salida = []
    for l in re.findall(patron, html):
        url = (l if l.startswith("http") else raiz + l).split("?")[0].rstrip("/")
        if url not in salida and url.rstrip("/") != base.rstrip("/"):
            salida.append(url)
    return salida[:tope]


# =============================================================================
# La página de una nota: título, bajada, foto, video, fecha y TEXTO
# =============================================================================
_META = r'<meta[^>]+(?:property|name|itemprop)="{}"[^>]+content="([^"]*)"|<meta[^>]+content="([^"]*)"[^>]+(?:property|name|itemprop)="{}"'
_LD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S)
_LD_VIDEO = re.compile(r'"contentUrl"\s*:\s*"(https:(?:\\?/){2}[^"]+?\.mp4[^"]*)"')
_JW_MP4 = re.compile(r'https://cdn\.jwplayer\.com/videos/[\w-]+\.mp4')
# Los videos de JW Player (La Nación, Infobae, Clarín): el id de 8 letras de cada uno, en el orden de la
# página. La página trae también los de otras notas y «loops» de cabecera: se elige con la API pública
# de JW (título, duración y versiones), en video_jw().
_JW_ID = re.compile(r'cdn\.jwplayer\.com/(?:videos|manifests|v2/media)/([A-Za-z0-9]{8})(?=[-./"&?])')
JW_MEDIA = "https://cdn.jwplayer.com/v2/media/{}"
JW_ALTO = 720                 # la versión que se baja: 720p (o la más cercana por debajo)
# TN (18/10/2026): su reproductor propio (vodgc, «genoa»), el MP4 viene en el contenido de la nota.
_GENOA = re.compile(r'"highQuality"\s*:\s*"(https://vod\.vodgc\.net/[^"]+?\.mp4)"')
_SUFIJOS = re.compile(r"\s*[|\-–—]\s*(TyC Sports|AFA|Infobae|LA NACION|La Nación|Clarín|Olé|ESPN|"
                      r"Google Workspace Blog|Shopify.*|Ámbito|El Cronista|BBC News Mundo|Zapier|"
                      r"AI at Work Blog|HubSpot.*|n8n Blog|Sitio Oficial de la Asociación del Fútbol Argentino)\s*$",
                      re.I)
_DMA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b")
AR = timezone(timedelta(hours=-3))


def _meta(html: str, nombre: str) -> str:
    m = re.search(_META.format(re.escape(nombre), re.escape(nombre)), html)
    return (m.group(1) or m.group(2) or "").replace("&amp;", "&").replace("&quot;", '"').strip() if m else ""


def _objetos_ld(html: str):
    for bloque in _LD.findall(html):
        try:
            d = json.loads(bloque.strip())
        except ValueError:
            continue
        for x in d if isinstance(d, list) else d.get("@graph") or [d]:
            if isinstance(x, dict):
                yield x


def ficha(html: str) -> dict:
    """{titulo, resumen, imagen, video, fecha, texto} de la página de una nota, sin red (se prueba solo)."""
    import html as H
    titulo = _SUFIJOS.sub("", H.unescape(_meta(html, "og:title")))
    fecha, texto = 0, ""
    for x in _objetos_ld(html):
        fecha = fecha or _iso(x.get("datePublished") or "")
        if isinstance(x.get("articleBody"), str) and len(x["articleBody"]) > len(texto):
            texto = x["articleBody"]
    fecha = fecha or _iso(_meta(html, "article:published_time")) or _iso(_meta(html, "datePublished"))
    if not fecha:
        # <time datetime>, o la primera fecha ISO de un meta (Shopify), o «14/10/2026» (AFA)
        t = (re.search(r'<time[^>]+datetime="([^"]+)"', html)
             or re.search(r'(?:datetime|content)="(20\d\d-\d\d-\d\dT[^"]*)"', html))
        fecha = _iso(t.group(1)) if t else 0
    if not fecha:
        m = _DMA.search(html)
        if m:
            try:
                fecha = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), 12, tzinfo=AR).timestamp()
            except ValueError:
                fecha = 0
    if len(texto) < 400:
        # Sin articleBody (Olé, BBC, los blogs): los párrafos de la nota.
        cuerpo = re.search(r"<article\b.*?</article>", html, re.S)
        parrafos = [_texto(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", cuerpo.group(0) if cuerpo else html, re.S)]
        unido = " ".join(p for p in parrafos if len(p) >= 60)
        if len(unido) > len(texto):
            texto = unido
    video = (_LD_VIDEO.findall(html) or _video_tn(html) or _JW_MP4.findall(html) or [""])[0]
    video = video.replace("\\u002F", "/").replace("\\/", "/")
    jw = []
    for i in _JW_ID.findall(html):
        if i not in jw:
            jw.append(i)
    return {"titulo": " ".join(titulo.lstrip("◉•● ").split()), "resumen": H.unescape(_meta(html, "og:description")),
            "imagen": _meta(html, "og:image"), "video": video, "fecha": fecha,
            "texto": " ".join(H.unescape(texto).split())[:12000], "jw": jw[:6]}


def _video_tn(html: str) -> list:
    """El video PROPIO de una nota de TN (el de su portada o el primero del cuerpo), no los de otras
    notas que la página también trae."""
    m = re.search(r"Fusion\.globalContent\s*=\s*(\{.*?\});\s*Fusion\.", html, re.S)
    if not m:
        return []
    try:
        gc = json.loads(m.group(1))
    except ValueError:
        return []
    bloques = [((gc.get("promo_items") or {}).get("basic") or {})]
    bloques += [e for e in gc.get("content_elements") or [] if e.get("type") == "custom_embed"]
    for b in bloques:
        cfg = ((b.get("embed") or {}).get("config") or {})
        if b.get("subtype") == "genoa" and cfg.get("content_type") == "video" and cfg.get("highQuality"):
            return [cfg["highQuality"]]
    return []


def video_jw(ids: list, titulo: str, cliente=None) -> str:
    """El MP4 de la nota entre los videos de JW de la página: el que se parece al título de la nota, de
    más de 8 segundos (los «loops» de cabecera no) y en su versión de 720p. "" si ninguno sirve."""
    if not ids:
        return ""
    cliente = cliente or _cliente()
    from nacionales import impacto as IM
    buscado = IM.palabras(titulo)
    opciones = []
    for orden, i in enumerate(ids[:6]):
        try:
            r = cliente.get(JW_MEDIA.format(i))
            r.raise_for_status()
            d = r.json()
            item = (d.get("playlist") or [{}])[0]
        except Exception:                             # noqa: BLE001
            continue
        nombre = f"{d.get('title') or ''} {item.get('title') or ''}"
        if (item.get("duration") or 0) < 8 or re.search(r"\bloop\b", nombre, re.I):
            continue
        mp4 = [x for x in item.get("sources") or [] if x.get("type") == "video/mp4" and x.get("file")]
        if not mp4:
            continue
        corto = lambda x: min(x.get("width") or x.get("height") or 0, x.get("height") or 0)   # noqa: E731 — verticales
        abajo = [x for x in mp4 if corto(x) <= JW_ALTO]
        elegido = max(abajo, key=corto) if abajo else min(mp4, key=corto)
        comunes = len(buscado & IM.palabras(nombre))
        opciones.append((comunes, -orden, elegido["file"]))
    return max(opciones)[2] if opciones else ""


def _cliente():
    return httpx.Client(headers=HEADERS, timeout=25, follow_redirects=True)


ESPN_NOTA = "https://content.core.api.espn.com/v1/sports/news/{}?lang=es&region=ar"


def ficha_espn(js: str) -> dict:
    """ESPN no deja leer su página (202 vacío): el texto sale de su API de contenido."""
    try:
        a = (json.loads(js).get("headlines") or [{}])[0]
    except ValueError:
        a = {}
    img = next((i.get("url") for i in a.get("images") or [] if (i.get("url") or "").startswith("http")), "")
    return {"titulo": a.get("headline") or "", "resumen": a.get("description") or "", "imagen": img, "video": "",
            "fecha": _iso(a.get("published") or ""), "texto": " ".join(_texto(a.get("story") or "").split())[:12000]}


def leer(url: str, cliente=None) -> dict:
    """La ficha de la página (un pedido). Vacía si no contesta."""
    cliente = cliente or _cliente()
    espn = re.search(r"espn\.com(?:\.ar)?/.*/id/(\d+)", url or "")
    if espn:
        try:
            r = cliente.get(ESPN_NOTA.format(espn.group(1)))
            r.raise_for_status()
            return ficha_espn(r.text)
        except Exception:                             # noqa: BLE001
            return {"titulo": "", "resumen": "", "imagen": "", "video": "", "fecha": 0, "texto": ""}
    try:
        r = cliente.get(url)
        r.raise_for_status()
    except Exception:                                 # noqa: BLE001
        return {"titulo": "", "resumen": "", "imagen": "", "video": "", "fecha": 0, "texto": ""}
    f = ficha(r.text)
    if f.get("jw") and not _video_tn(r.text):
        # El de JW que corresponde a la nota, en 720p (18/10/2026): antes, el primer MP4 de la página
        # (a veces un «loop» de 6 segundos o la versión de 180p).
        f["video"] = video_jw(f["jw"], f.get("titulo") or "", cliente) or ""
    return f


def _una_fuente(fuente, cliente) -> tuple:
    cat, nombre, via, url, extra = fuente
    r = cliente.get(url)
    r.raise_for_status()
    if via == "rss":
        return notas_rss(r.text, cat, nombre)
    if via == "espn":
        return notas_espn(r.text, cat, nombre)
    salida = []
    for link in links_de_lista(r.text, extra["links"], url, extra.get("max", 8)):
        f = leer(link, cliente)
        # Sin fecha no se sabe si es de hoy o de hace un año: queda afuera (fecha 0 = vieja).
        if f["titulo"]:
            salida.append(nota_nueva(link, cat, nombre, f["titulo"], f["resumen"], f["texto"], f["fecha"],
                                     f["imagen"]))
    return salida


def bajar(fuentes=FUENTES, cliente=None, hilos: int = 8) -> tuple:
    """(notas, fallas, conteo por fuente). Una fuente que no contesta no frena a las otras. En paralelo:
    son ~45 pedidos más las páginas de los listados."""
    cliente = cliente or _cliente()
    notas, vistas, fallas, conteo = [], set(), [], {}

    def una(f):
        try:
            return f, _una_fuente(f, cliente), ""
        except Exception as e:                       # noqa: BLE001
            return f, [], f"{f[1]} ({f[3][:60]}): {type(e).__name__}: {str(e)[:80]}"

    with ThreadPoolExecutor(max_workers=max(1, hilos)) as ex:
        resultados = list(ex.map(una, fuentes))
    for f, lista, falla in resultados:              # en el orden de FUENTES: la primera vez manda
        if falla:
            fallas.append(falla)
        conteo[f[1]] = conteo.get(f[1], 0) + len(lista)
        for n in lista:                             # la misma nota puede venir de dos categorías
            if (n["url"], n["categoria"]) not in vistas:
                vistas.add((n["url"], n["categoria"]))
                notas.append(n)
    return notas, fallas, conteo
