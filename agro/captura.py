# -*- coding: utf-8 -*-
"""Captura: lee el RSS de cada fuente (o, si el sitio no tiene, su página de notas) y deja cada nota con los campos del documento.

Respeta robots.txt (se lee una vez por sitio) y no pide nada que no haga falta: el feed y,
más adelante y SOLO para las notas elegidas, la nota completa (`completar`). El texto
completo no se le manda a la IA para puntuar: se puntúa con título, bajada y metadatos
(control de costos del documento, punto 27).
"""
import hashlib
import html as htmlmod
import re
import unicodedata
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from scraper import fetch as FE

TZ_AR = timezone(timedelta(hours=-3))
_robots = {}


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def normalizar_titulo(t: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", _sin_tildes(t).lower()).split())


def canonica(url: str) -> str:
    """La URL sin rastreadores (utm_*, fbclid…), sin #, sin barra final y con el host en minúscula."""
    p = urlparse((url or "").strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith(("utm_", "fbclid", "gclid", "amp"))]
    ruta = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower() or "https", p.netloc.lower().removeprefix("www."), ruta, "",
                       urlencode(q), ""))


def huella(titulo: str, descripcion: str) -> str:
    return hashlib.sha1(f"{normalizar_titulo(titulo)}|{normalizar_titulo(descripcion)[:400]}"
                        .encode("utf-8")).hexdigest()[:16]


def id_de(url: str) -> str:
    return hashlib.sha1(canonica(url).encode("utf-8")).hexdigest()[:12]


def permitido(url: str) -> bool:
    """robots.txt del sitio (cacheado). Si no se puede leer, se asume permitido (como un navegador)."""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    rp = _robots.get(base)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = FE.get(base + "/robots.txt")
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except Exception:                                  # noqa: BLE001
            rp.parse([])
        _robots[base] = rp
    return rp.can_fetch(FE.HEADERS["User-Agent"], url)


def _fecha(iso: str):
    """La fecha del feed (feedparser la da en UTC) como datetime con zona."""
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso[:19])
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    except ValueError:
        return None


def normalizar(cruda: dict, fuente: dict, feed: str, ahora: datetime) -> dict:
    url = cruda.get("url") or ""
    pub = _fecha(cruda.get("publicado"))
    titulo = " ".join((cruda.get("titulo") or "").split())
    desc = " ".join((cruda.get("copete") or "").split())
    return {
        "id": id_de(url), "fuente": fuente["nombre"], "tipo_fuente": fuente.get("tipo", "medio"),
        "source_url": feed, "url": url, "canonical_url": canonica(url),
        "titulo": titulo, "titulo_norm": normalizar_titulo(titulo),
        "descripcion": desc[:900], "imagen_url": cruda.get("imagen") or "",
        "autor": cruda.get("autor") or "",
        "publicado": pub.astimezone(TZ_AR).isoformat(timespec="minutes") if pub else "",
        "capturado": ahora.isoformat(timespec="minutes"),
        "idioma": fuente.get("idioma", "es"), "pais": fuente.get("pais", "AR"), "hash": huella(titulo, desc),
    }


def _meta(html: str, clave: str) -> str:
    m = re.search(r'<meta[^>]+(?:property|name)="' + re.escape(clave) + r'"[^>]+content="([^"]*)"', html)
    return htmlmod.unescape(m.group(1)).strip() if m else ""


def listar_portada(url: str, patron: str, limite: int = 12, get=None) -> list:
    """Para un sitio SIN RSS (la Bolsa de Comercio de Rosario): los links de `url` que cumplen
    `patron` y, de cada uno, título, resumen, foto y fecha de sus metadatos (og:*). Misma forma
    que `listar_por_rss`."""
    get = get or FE.get
    r = get(url)
    r.raise_for_status()
    links = []
    for ruta in re.findall(r'href="([^"#?]+)"', r.text):
        absoluta = urljoin(url, ruta)
        if re.search(patron, absoluta) and absoluta not in links:
            links.append(absoluta)
    notas = []
    for link in links[:limite]:
        n = _metadatos(link, get)
        if n and n["titulo"]:
            notas.append(n)
    return notas


def _metadatos(link: str, get, titulo: str = "", publicado: str = "") -> dict:
    """Título, resumen, foto y fecha de una nota por sus metadatos og:*. {} si no se pudo leer y
    no hay título de otro lado."""
    base = {"titulo": titulo, "url": link, "copete": "", "imagen": "", "autor": "", "publicado": publicado,
            "metodo": "html"}
    if not permitido(link):
        return {}
    try:
        h = get(link)
        if h.status_code != 200:
            return base if titulo else {}
    except Exception:                                      # noqa: BLE001 — una nota rota no frena
        return base if titulo else {}
    fecha = _meta(h.text, "article:published_time")
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", fecha)
    fecha = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}T12:00:00" if m else fecha
    return dict(base, titulo=titulo or _meta(h.text, "og:title"), copete=_meta(h.text, "og:description"),
                imagen=_meta(h.text, "og:image"), publicado=publicado or fecha)


def listar_sitemap(url: str, patron: str, limite: int = 12, get=None) -> list:
    """Para un sitio con el RSS vacío pero con sitemap de noticias de Google (La Capital, donde
    publica Agroclave): las entradas cuyo link cumple `patron`, con su título y fecha del sitemap;
    el resumen y la foto, de los metadatos de cada nota. Misma forma que `listar_por_rss`."""
    get = get or FE.get
    r = get(url)
    r.raise_for_status()
    notas = []
    for bloque in re.findall(r"<url>(.*?)</url>", r.text, re.S):
        loc = re.search(r"<loc>\s*([^<\s]+)", bloque)
        if not loc or not re.search(patron, loc.group(1)):
            continue
        titulo = re.search(r"<news:title>(.*?)</news:title>", bloque, re.S)
        fecha = re.search(r"<news:publication_date>([^<]+)", bloque)
        titulo = htmlmod.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", titulo.group(1))).strip() if titulo else ""
        n = _metadatos(loc.group(1), get, titulo, fecha.group(1).strip() if fecha else "")
        if n and n["titulo"]:
            notas.append(n)
        if len(notas) >= limite:
            break
    return notas


def capturar(fuentes: list, ahora: datetime = None, horas_max: int = 48, listar=None, log=print) -> tuple:
    """(notas, informe_por_fuente). Solo notas de las últimas `horas_max` horas (las sin fecha
    entran: el feed es de lo último). `listar` se reemplaza en las pruebas."""
    ahora = ahora or datetime.now(TZ_AR)
    listar = listar or FE.listar_por_rss
    notas, informe, vistas = [], [], set()
    for f in fuentes:
        # Los RSS primero; las páginas (`portadas` + `patron`) solo para sitios sin RSS.
        origenes = [(feed, listar) for feed in f.get("rss", [])] + \
                   [(p, lambda u, _p=f["patron"]: listar_portada(u, _p)) for p in f.get("portadas", [])] + \
                   [(m, lambda u, _p=f["patron"]: listar_sitemap(u, _p)) for m in f.get("sitemaps", [])]
        fila = {"fuente": f["nombre"], "feeds": len(origenes), "leidas": 0, "nuevas": 0, "viejas": 0,
                "errores": []}
        for feed, leer in origenes:
            if not permitido(feed):
                fila["errores"].append(f"robots.txt no permite {feed}")
                continue
            try:
                crudas = leer(feed) or []
            except Exception as e:                         # noqa: BLE001 — una fuente rota no frena
                fila["errores"].append(f"{feed}: {type(e).__name__}")
                continue
            if not crudas:
                fila["errores"].append(f"{feed}: el feed vino vacío")
            for c in crudas:
                n = normalizar(c, f, feed, ahora)
                fila["leidas"] += 1
                if n["canonical_url"] in vistas:
                    continue                               # la misma nota en dos secciones del sitio
                vistas.add(n["canonical_url"])
                pub = _fecha(n["publicado"])
                # Una fuente semanal (la Bolsa) trae su propia ventana: lo del jueves sigue vigente el lunes.
                if pub and ahora - pub > timedelta(hours=max(horas_max, f.get("horas", 0))):
                    fila["viejas"] += 1
                    continue
                notas.append(n)
                fila["nuevas"] += 1
        informe.append(fila)
        log(f"  {f['nombre']}: {fila['leidas']} leídas, {fila['nuevas']} de las últimas {max(horas_max, f.get('horas', 0))} h"
            + (f" · {'; '.join(fila['errores'])}" if fila["errores"] else ""))
    return notas, informe


CUERPO_CORTO = 600      # menos que esto es el resumen, no la nota


def cuerpo_por_parrafos(html: str) -> str:
    """El bloque con más texto en párrafos <p> directos. Para los sitios donde el extractor
    general solo encuentra el resumen (la Bolsa de Comercio de Rosario, en Drupal)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    mejor, largo = None, 0
    for nodo in soup.find_all(["div", "article", "section"]):
        t = sum(len(p.get_text(" ", strip=True)) for p in nodo.find_all("p", recursive=False))
        if t > largo:
            mejor, largo = nodo, t
    if not mejor:
        return ""
    return " ".join(" ".join(p.get_text(" ", strip=True) for p in mejor.find_all("p", recursive=False)).split())


def completar(nota: dict, detalle=None, get=None) -> dict:
    """El texto completo de UNA nota (solo de las elegidas). Respeta robots.txt."""
    detalle = detalle or FE.detalle
    if not permitido(nota["url"]):
        return {"ok": False, "motivo": "robots.txt no permite leer la nota"}
    d = detalle(nota["url"])
    if not d.get("ok"):
        return {"ok": False, "motivo": "la nota no se pudo leer"}
    cuerpo = " ".join((d.get("cuerpo") or "").split())
    if len(cuerpo) < CUERPO_CORTO:
        try:
            r = (get or FE.get)(nota["url"])
            otro = cuerpo_por_parrafos(r.text) if r.status_code == 200 else ""
            if len(otro) > len(cuerpo):
                cuerpo = otro
        except Exception:                                  # noqa: BLE001 — queda el que había
            pass
    return {"ok": True, "cuerpo": cuerpo, "imagen": d.get("imagen") or nota.get("imagen_url") or "",
            "video": d.get("video") or ""}
