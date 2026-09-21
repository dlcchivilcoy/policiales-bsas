# -*- coding: utf-8 -*-
"""Motor de descarga y parseo. Portado del scraper de NoticIAs Chivilcoy y
generalizado: aca no hay un parser por medio, hay UNA estrategia que se adapta.

Orden de preferencia para listar las notas de un medio:
  1. RSS  -> es lo mas barato, estable y trae fecha + imagen ya parseadas.
  2. HTML -> se descubren los links de nota de la home por heuristica.

Descubrir el feed automaticamente es lo que hace viable tener 56 medios: mantener
56 parsers a mano seria imposible.
"""
import re
import unicodedata
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}
TIMEOUT = 20

# Rutas donde suele vivir el feed. El orden importa: las primeras dos cubren
# practicamente todo WordPress, que es lo que usa la enorme mayoria de estos medios.
RUTAS_RSS = [
    "/feed/", "/rss", "/feed", "/rss.xml", "/index.xml", "/atom.xml",
    "/?feed=rss2", "/feed/rss/", "/rss/noticias", "/noticiasrss/rss.html",
]

_WP_SIZE_RE = re.compile(r"-\d{2,4}x\d{2,4}(?=\.(?:jpg|jpeg|png|webp|gif)$)", re.IGNORECASE)
_RESIZE_PARAMS = {"resize", "fit", "w", "h", "width", "height", "quality", "q", "strip", "ssl", "crop", "s"}


def limpiar(texto):
    return re.sub(r"\s+", " ", texto).strip() if texto else ""


def _sin_tildes(texto):
    """Necesario para comparar rotulos: 'Espectaculos' y 'Espectáculos' son lo mismo
    y sin esto el filtro de menu no matcheaba ninguno de los dos casos reales."""
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn")


def mejorar_imagen(url):
    """Devuelve la version de mayor calidad: saca el sufijo de tamaño de WordPress
    (foo-300x200.jpg -> foo.jpg) y los parametros de resize del CDN."""
    if not url:
        return url
    path, _, qs = url.partition("?")
    path = _WP_SIZE_RE.sub("", path)
    if qs:
        kept = "&".join(p for p in qs.split("&")
                        if p and p.split("=")[0].lower() not in _RESIZE_PARAMS)
        return f"{path}?{kept}" if kept else path
    return path


def get(url, timeout=TIMEOUT):
    return httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)


def get_soup(url, timeout=TIMEOUT):
    r = get(url, timeout)
    r.raise_for_status()
    encoding = r.charset_encoding or "utf-8"
    return BeautifulSoup(r.content.decode(encoding, errors="replace"), "html.parser")


# Sitios que hay que leer con navegador de verdad. Se llena al vuelo cuando un
# dominio contesta 403 o devuelve una home sin un solo link, asi el resto de las
# paginas de ese mismo medio ya van derecho al navegador y no se reintenta por HTTP.
DOMINIOS_CON_NAVEGADOR = set()


def obtener_html(url, permitir_navegador=False, timeout=TIMEOUT):
    """Devuelve (html, via). `via` es 'http', 'navegador' o None si no se pudo.

    Se recurre al navegador solo cuando HTTP no alcanza (403 de Cloudflare o
    pagina que se arma con JavaScript), porque cuesta unas 20 veces mas.
    """
    dominio = urlparse(url).netloc.replace("www.", "")
    if permitir_navegador and dominio in DOMINIOS_CON_NAVEGADOR:
        from scraper import navegador
        html = navegador.html_de(url)
        return (html, "navegador") if html else (None, None)

    bloqueado = False
    try:
        r = get(url, timeout)
        if r.status_code == 403:
            bloqueado = True
        elif r.status_code < 400 and r.content:
            encoding = r.charset_encoding or "utf-8"
            return r.content.decode(encoding, errors="replace"), "http"
    except Exception:
        pass

    if permitir_navegador:
        from scraper import navegador
        html = navegador.html_de(url)
        if html:
            if bloqueado:
                DOMINIOS_CON_NAVEGADOR.add(dominio)
            return html, "navegador"
    return None, None


def normalizar_base(dominio):
    """'foo.com.ar' o 'http://foo.com.ar/x' -> 'https://foo.com.ar'."""
    d = dominio.strip()
    if not d.startswith("http"):
        d = "https://" + d
    p = urlparse(d)
    return f"{p.scheme}://{p.netloc}"


def resolver_base(dominio, timeout=12):
    """Encuentra la URL base que realmente responde, probando variantes.

    Varios de estos medios siguen solo en HTTP o solo responden con 'www'. Forzar
    https://dominio los daba por muertos cuando estaban perfectamente vivos
    (bolivarhoy.com.ar e inforoqueperez.com.ar son dos casos reales).
    Devuelve (base, None) o (None, motivo_del_fallo).
    """
    d = re.sub(r"^https?://", "", dominio.strip()).rstrip("/")
    sin_www = d[4:] if d.startswith("www.") else d
    variantes = [f"https://{sin_www}", f"https://www.{sin_www}",
                 f"http://www.{sin_www}", f"http://{sin_www}"]
    ultimo, bloqueada = None, None
    for v in variantes:
        try:
            r = get(v, timeout=timeout)
            if r.status_code < 400:
                p = urlparse(str(r.url))
                return f"{p.scheme}://{p.netloc}", None
            # 403 no es un sitio muerto: es un sitio VIVO que rechaza al cliente
            # automatico. Lo anotamos para leerlo con navegador en vez de darlo
            # por caido (asi se recuperaron Diario Suipacha y Rumores de Pehuajo).
            if r.status_code == 403 and bloqueada is None:
                p = urlparse(str(r.url))
                bloqueada = f"{p.scheme}://{p.netloc}"
            ultimo = f"HTTP {r.status_code}"
        except Exception as e:
            ultimo = type(e).__name__
    if bloqueada:
        DOMINIOS_CON_NAVEGADOR.add(urlparse(bloqueada).netloc.replace("www.", ""))
        return bloqueada, None
    return None, ultimo or "sin respuesta"


# =============================================================================
# Descubrimiento de feed
# =============================================================================

def descubrir_rss(base):
    """Devuelve la URL del feed del sitio, o None.

    Primero mira el <link rel="alternate" type="application/rss+xml"> de la home,
    que es la fuente autoritativa; si no esta, prueba las rutas tipicas. Solo
    acepta un feed que efectivamente traiga entradas: hay sitios que responden 200
    con un XML vacio y eso es peor que no tener feed, porque parece que anda.
    """
    candidatas = []
    try:
        soup = get_soup(base)
        for link in soup.find_all("link", rel=lambda r: r and "alternate" in (r if isinstance(r, list) else [r])):
            tipo = (link.get("type") or "").lower()
            if "rss" in tipo or "atom" in tipo or "xml" in tipo:
                href = link.get("href")
                if href:
                    candidatas.append(urljoin(base, href))
    except Exception:
        pass

    candidatas += [base.rstrip("/") + ruta for ruta in RUTAS_RSS]

    vistas = set()
    for url in candidatas:
        if url in vistas:
            continue
        vistas.add(url)
        try:
            r = get(url, timeout=15)
            if r.status_code != 200 or not r.content:
                continue
            feed = feedparser.parse(r.content)
            if feed.entries:
                return url
        except Exception:
            continue
    return None


# =============================================================================
# Listado de notas
# =============================================================================

def _imagen_de_entry(entry):
    if getattr(entry, "media_content", None):
        mejor, mejor_w = None, -1
        for m in entry.media_content:
            u = m.get("url")
            if not u:
                continue
            try:
                w = int(m.get("width") or 0)
            except (TypeError, ValueError):
                w = 0
            if w >= mejor_w:
                mejor, mejor_w = u, w
        if mejor:
            return mejorar_imagen(mejor)
    if getattr(entry, "media_thumbnail", None):
        return mejorar_imagen(entry.media_thumbnail[0].get("url"))
    if getattr(entry, "enclosures", None):
        return mejorar_imagen(entry.enclosures[0].get("href"))
    html = (entry.get("content", [{}])[0].get("value", "") or entry.get("summary", ""))
    if html:
        img = BeautifulSoup(html, "html.parser").find("img")
        if img:
            return mejorar_imagen(img.get("src"))
    return None


def _fecha_de_entry(entry):
    for campo in ("published_parsed", "updated_parsed"):
        val = getattr(entry, campo, None)
        if val:
            try:
                return datetime(*val[:6]).isoformat()
            except Exception:
                pass
    return None


def listar_por_rss(rss_url, limite=40):
    """Lee el feed con httpx + UA de navegador. feedparser.parse(url) directo usa su
    UA propio y NO sigue redirecciones: varios WordPress con plugins de seguridad o
    Cloudflare devuelven 0 entradas asi, sobre todo desde IPs de datacenter."""
    feed = None
    try:
        r = get(rss_url)
        if r.status_code == 200 and r.content:
            feed = feedparser.parse(r.content)
    except Exception:
        pass
    if feed is None or not feed.entries:
        feed = feedparser.parse(rss_url)

    notas = []
    for e in feed.entries[:limite]:
        resumen = BeautifulSoup(e.get("summary", ""), "html.parser").get_text()
        notas.append({
            "titulo": limpiar(e.get("title", "")),
            "url": (e.get("link") or "").strip(),
            "copete": limpiar(resumen),
            "imagen": _imagen_de_entry(e),
            "autor": e.get("author", ""),
            "publicado": _fecha_de_entry(e),
            "metodo": "rss",
        })
    return [n for n in notas if n["titulo"] and n["url"]]


# Basura tipica de una home que NO es una nota.
_NO_NOTA = re.compile(
    r"/(categor|category|tag|etiqueta|author|autor|seccion|section|page|pagina|"
    r"contacto|about|nosotros|publicidad|staff|suscri|login|registro|privacidad|"
    r"terminos|wp-|feed|comment|#)", re.IGNORECASE)

# Rotulos de menu que pasan el largo minimo y se cuelan como si fueran titulares
# ("Cultura y Espectaculos", "Guia de Profesionales"). Un titular de verdad tiene
# un verbo o dos puntos; estos son solo el nombre de una seccion.
_ROTULO_MENU = re.compile(
    r"^(cultura( y espectaculos)?|espectaculos|guia de profesionales|guia profesional|"
    r"ultimas noticias|noticias destacadas|mas noticias|notas relacionadas|"
    r"informacion general|interes general|politica y economia|deportes?|sociedad|"
    r"opinion|editorial|clasificados|servicios|institucional|quienes somos|"
    r"contactanos|newsletter|suscribite|publicidad|inicio|home)$",
    re.IGNORECASE)


def listar_por_html(base, limite=40, permitir_navegador=False):
    """Descubre links de nota en la home por heuristica.

    Una URL de nota en estos medios casi siempre: (a) vive en el mismo dominio,
    (b) tiene un path largo con guiones (el slug del titular), una fecha /AAAA/MM/
    o un id numerico, y (c) el texto del link alcanza para ser un titular.
    """
    html, _ = obtener_html(base, permitir_navegador)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    dominio = urlparse(base).netloc.replace("www.", "")
    vistas, notas = set(), []

    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"].split("#")[0]).rstrip("/")
        if not href.startswith("http"):
            continue
        partes = urlparse(href)
        if partes.netloc.replace("www.", "") != dominio:
            continue
        path, query = partes.path, partes.query
        if (not path or path == "/") and not query:
            continue
        if _NO_NOTA.search(path):
            continue

        slug = path.rstrip("/").split("/")[-1]
        tiene_fecha = re.search(r"/20\d{2}/\d{1,2}/", path)
        # Slug de nota: varias palabras separadas por guion O guion bajo. Hay CMS
        # viejos que arman el slug con "_" (bolivarhoy: /leernoticias/22379/titulo_asi).
        separadores = slug.count("-") + slug.count("_")
        slug_de_nota = separadores >= 2 and len(slug) > 15
        # CMS viejos sin URL amigable: la nota es "algo.php?...id=1234". Sin esto,
        # sitios perfectamente vivos quedaban como "sin notas detectadas".
        nota_por_id = bool(re.search(r"(^|&)(id|nota|noticia|codigo)=\d{2,}", query, re.I))
        # /leernoticias/22379/... : id numerico en la ruta
        id_en_ruta = bool(re.search(r"/(?:leer|ver|nota|noticia)[a-z]*/\d{3,}/", path, re.I))

        if not (tiene_fecha or slug_de_nota or nota_por_id or id_en_ruta):
            continue

        titulo = limpiar(a.get_text(" ", strip=True))
        if len(titulo) < 20:
            # El link puede ser la foto; probamos con el title/aria-label o el texto
            # del contenedor (h2/h3), que es donde suele estar el titular.
            titulo = limpiar(a.get("title") or a.get("aria-label") or "")
            if len(titulo) < 20:
                cont = a.find_parent(["article", "li", "div"])
                h = cont.find(["h1", "h2", "h3"]) if cont else None
                titulo = limpiar(h.get_text(" ", strip=True)) if h else ""
        if len(titulo) < 20 or href in vistas:
            continue
        if _ROTULO_MENU.match(_sin_tildes(limpiar(titulo)).strip(" |·-")):
            continue

        vistas.add(href)
        notas.append({
            "titulo": titulo, "url": href, "copete": "", "imagen": None,
            "autor": "", "publicado": None, "metodo": "html",
        })
        if len(notas) >= limite:
            break
    return notas


def listar_notas(base, rss_url=None, limite=40, permitir_navegador=False):
    """Entrada unica: usa RSS si hay, si no cae a HTML."""
    if rss_url:
        notas = listar_por_rss(rss_url, limite)
        if notas:
            return notas
    return listar_por_html(base, limite, permitir_navegador)


# =============================================================================
# Seccion de policiales
# =============================================================================

# Casi todos estos medios separan "Policiales" en su propia seccion. Ir directo a
# esa seccion rinde muchisimo mas que filtrar el feed general: el feed general de
# un diario chico trae 10 notas de las que 1 es policial, mientras que la seccion
# trae 10 de 10. Ademas baja el gasto de IA, porque casi no entran falsos positivos.
RUTAS_SECCION = [
    "/policiales/feed/", "/categoria/policiales/feed/", "/category/policiales/feed/",
    "/seccion/policiales/feed/", "/tag/policiales/feed/", "/tema/policiales/feed/",
    "/tags/policiales/feed/", "/policiales", "/categoria/policiales/",
    "/category/policiales/", "/seccion/policiales/", "/tag/policiales/",
    "/tema/policiales/", "/tags/policiales", "/contenidos/policiales.html",
    "/policiales.html", "/secciones/policiales", "/noticias/policiales",
    # varios medios usan "seguridad" o "sucesos" en vez de "policiales"
    "/categoria/seguridad/feed/", "/seccion/seguridad/", "/tag/sucesos/",
]


def descubrir_seccion_policial(base, minimo=3, permitir_navegador=False):
    """Busca la seccion de policiales del medio.

    Devuelve {"url", "rss", "n"} o None. Solo la acepta si trae al menos `minimo`
    notas: hay sitios que responden 200 a cualquier ruta con una pagina de "no se
    encontraron resultados", y tomar eso por una seccion viva es peor que no tenerla.
    """
    for ruta in RUTAS_SECCION:
        url = base.rstrip("/") + ruta
        es_feed = ruta.endswith("/feed/") or ruta.endswith("feed")
        try:
            if es_feed:
                r = get(url, timeout=15)
                if r.status_code >= 400 or not r.content:
                    continue
                # Una redireccion a la home significa que la seccion no existe.
                if urlparse(str(r.url)).path.rstrip("/") in ("", "/"):
                    continue
                feed = feedparser.parse(r.content)
                if len(feed.entries) >= minimo:
                    return {"url": url, "rss": url, "n": len(feed.entries)}
            else:
                notas = listar_por_html(url, limite=40, permitir_navegador=permitir_navegador)
                if len(notas) >= minimo:
                    return {"url": url, "rss": None, "n": len(notas)}
        except Exception:
            continue
    return None


# =============================================================================
# Detalle de la nota
# =============================================================================

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
          "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
          "noviembre": 11, "diciembre": 12}


def _parsear_fecha(texto):
    if not texto:
        return None
    texto = texto.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:len(datetime.now().strftime(fmt)) + 6], fmt).isoformat()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).isoformat()
    except Exception:
        pass
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", texto.lower())
    if m and m.group(2) in _MESES:
        try:
            return datetime(int(m.group(3)), _MESES[m.group(2)], int(m.group(1))).isoformat()
        except Exception:
            pass
    return None


def _fecha_de_url(url):
    m = re.search(r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)", url or "")
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except Exception:
            pass
    return None


def _fecha_del_html(soup):
    for attr, val in (("property", "article:published_time"), ("name", "article:published_time"),
                      ("itemprop", "datePublished"), ("name", "date"), ("property", "og:published_time")):
        tag = soup.find("meta", attrs={attr: val})
        if tag and tag.get("content"):
            f = _parsear_fecha(tag["content"])
            if f:
                return f
    # JSON-LD malformado es comun en estos CMS; sacamos el campo con regex antes de
    # rendirnos, si no la nota queda sin fecha y se la toma como recien salida.
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', str(soup))
    if m:
        f = _parsear_fecha(m.group(1))
        if f:
            return f
    t = soup.find("time")
    if t and t.get("datetime"):
        f = _parsear_fecha(t["datetime"])
        if f:
            return f
    for cls in ("post-date", "entry-date", "meta-date", "published", "date", "fecha"):
        for el in soup.find_all(class_=cls):
            f = _parsear_fecha(el.get_text(" ", strip=True))
            if f:
                return f
    return None


def _imagen_del_html(soup, base_url):
    for attr, val in (("property", "og:image"), ("name", "og:image"),
                      ("name", "twitter:image"), ("property", "twitter:image")):
        tag = soup.find("meta", attrs={attr: val})
        if tag and tag.get("content"):
            abs_url = urljoin(base_url, tag["content"].strip())
            if abs_url.startswith("http"):
                return mejorar_imagen(abs_url)
    return None


_CUERPO_RE = re.compile(
    r"entry-content|post-content|article-content|single-content|td-post-content|"
    r"post-body|cuerponota|nota-cuerpo|contenido-nota|texto-nota")


def detalle(url, timeout=TIMEOUT, permitir_navegador=False):
    """Baja la nota una sola vez y devuelve cuerpo + fecha + imagen.
    `ok` False significa que la URL murio (404/error): esa nota no se guarda."""
    vacio = {"ok": False, "cuerpo": "", "descripcion": "", "publicado": None, "imagen": None}
    try:
        html, _ = obtener_html(url, permitir_navegador, timeout)
        if not html:
            return vacio
        soup = BeautifulSoup(html, "html.parser")
        publicado = _fecha_del_html(soup) or _fecha_de_url(url)
        imagen = _imagen_del_html(soup, url)

        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        nodo = soup.find(class_=_CUERPO_RE) or soup.find("article")
        cuerpo = limpiar(nodo.get_text(" ")) if nodo else ""

        # og:description es el resumen que ESCRIBIO EL PROPIO MEDIO: corto, del tema y
        # sin menus ni "notas relacionadas". Se devuelve aparte del cuerpo porque para
        # redactar una bajada sirve MUCHO mas que el volcado entero de la pagina, que en
        # varios de estos sitios arrastra la nota de al lado (una bajada sobre un robo
        # terminaba hablando de futbol).
        meta = (soup.find("meta", attrs={"property": "og:description"})
                or soup.find("meta", attrs={"name": "description"}))
        descripcion = limpiar(meta["content"]) if (meta and meta.get("content")) else ""
        if not cuerpo:
            cuerpo = descripcion
        return {"ok": True, "cuerpo": cuerpo, "descripcion": descripcion,
                "publicado": publicado, "imagen": imagen}
    except Exception:
        return vacio


def logo_del_sitio(base):
    """apple-touch-icon > <link rel=icon> mas grande > favicon de Google."""
    try:
        soup = get_soup(base)
        cands = []
        for tag in soup.find_all("link", rel=True):
            rels = " ".join(tag["rel"] if isinstance(tag["rel"], list) else [tag["rel"]]).lower()
            href = tag.get("href")
            if not href:
                continue
            if "apple-touch-icon" in rels:
                cands.insert(0, href)
            elif "icon" in rels:
                cands.append(href)
        for href in cands:
            abs_url = urljoin(base, href)
            if abs_url.startswith("http"):
                return abs_url
    except Exception:
        pass
    return f"https://www.google.com/s2/favicons?domain={urlparse(base).netloc}&sz=128"
