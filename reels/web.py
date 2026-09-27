# -*- coding: utf-8 -*-
"""La NOTA en la web del diario por cada reel, para que el posteo de Facebook lleve a la web.

Pedido del editor el 27/09/2026: «que el reel por lo menos lleve, a través de un enlace de
texto, a la nota en mi página web». Cada reel publicado tiene su nota en la sección
**Región** de www.diariolacampaña.com.ar, y el posteo de Facebook cierra con
«📲 Nota completa: <link>».

Decisiones que no se ven en el código:
- La sección «Región» es una categoría de Wix creada el 27/09 (id abajo) SOLO para esto.
  La web la deja FUERA de la portada, de «Lo más leído» y del archivo general (diario_web,
  commit 73d9e14): son ~20-30 notas por día de otros pueblos y la portada es de Chivilcoy.
  Por eso la nota va ÚNICAMENTE a Región, nunca a «Inicio», y sin destacar.
- El texto lo escribe la IA con palabras propias (NOTA_WEB del guion). Acá se agrega lo que
  no puede faltar y no conviene dejarle al modelo: la FUENTE con el link a la nota original.
- La web (Astro) solo muestra videos de YouTube dentro de una nota, no los subidos a Wix:
  por eso el reel entra como el Short de Radio del Centro, y por eso YouTube se publica
  ANTES que la nota (ver reels/publicador.py).
- El slug lleva una marca corta sacada de la URL original. Así es único (Wix no le cambia
  el nombre) y sirve para no duplicar: antes de crear se busca si ya existe.

Las credenciales son las del bot del diario (WIX_API_KEY, WIX_SITE_ID, WIX_MEMBER_ID).
"""
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

REGION_ID = "55c5c23e-4ac1-43c4-ae24-125fce001311"
SITIO = "www.diariolacampaña.com.ar"          # con la Ñ: es lo que se lee en el posteo
MARCA = "Diario La Campaña"
CREDENCIALES = ("WIX_API_KEY", "WIX_SITE_ID", "WIX_MEMBER_ID")

MEDIA_IMPORT_URL = "https://www.wixapis.com/site-media/v1/files/import"
DRAFT_POSTS_URL = "https://www.wixapis.com/blog/v3/draft-posts"
POSTS_QUERY_URL = "https://www.wixapis.com/blog/v3/posts/query"
TZ_AR = timezone(timedelta(hours=-3))


class FalloWeb(RuntimeError):
    """Wix dijo que no, o no contestó."""


def activa() -> bool:
    """Se apaga sin tocar código con la variable NOTAS_WEB=0."""
    return (os.environ.get("NOTAS_WEB") or "1").strip() != "0"


def faltantes() -> list:
    return [k for k in CREDENCIALES if not os.environ.get(k)]


def _headers() -> dict:
    return {"Authorization": os.environ.get("WIX_API_KEY", ""),
            "wix-site-id": os.environ.get("WIX_SITE_ID", ""),
            "Content-Type": "application/json"}


def slugify(texto: str, max_len: int = 70) -> str:
    t = unicodedata.normalize("NFD", texto or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").replace("ñ", "n").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    if len(t) > max_len:
        t = t[:max_len].rsplit("-", 1)[0]
    return t or "nota"


def slug_de(pieza: dict) -> str:
    marca = hashlib.sha1((pieza.get("url_original") or "").encode("utf-8")).hexdigest()[:6]
    return f"{slugify((pieza.get('web') or {}).get('titulo') or '', 64)}-{marca}"


def link(slug: str) -> str:
    """El link corto y con la Ñ que sirve la web: /n/{slug} redirige a la nota."""
    return f"https://{SITIO}/n/{slug}"


def _texto(texto: str, url: str = "") -> dict:
    deco = []
    if url:
        deco = [{"type": "LINK", "linkData": {"link": {"url": url, "target": "BLANK"}}}]
    return {"type": "TEXT", "id": "", "textData": {"text": texto, "decorations": deco}}


def _parrafo(i: int, *partes) -> dict:
    return {"type": "PARAGRAPH", "id": f"p{i}", "nodes": list(partes)}


def _fuente(pieza: dict) -> str:
    medio = pieza.get("medio") or "un medio de la zona"
    loc = pieza.get("localidad") or ""
    if loc and loc.lower() not in medio.lower():
        medio = f"{medio} ({loc})"
    return medio


def armar_borrador(pieza: dict, file_id: str = "", youtube_id: str = "",
                   member_id: str = "") -> dict:
    """El pedido para Wix, sin tocar la red (se prueba solo)."""
    web = pieza.get("web") or {}
    titulo = " ".join((web.get("titulo") or "").split())[:200]
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", web.get("cuerpo") or "") if p.strip()]
    nodos = []
    if file_id:
        nodos.append({"type": "IMAGE", "id": "img0", "nodes": [], "imageData": {
            "containerData": {"width": {"size": "CONTENT"}, "alignment": "CENTER"},
            "image": {"src": {"id": file_id}}}})
    if youtube_id:
        # La web reconoce el video por «v=<id>» en la URL (diario_web/src/lib/wix.js).
        nodos.append({"type": "VIDEO", "id": f"yt-{youtube_id}", "nodes": [], "videoData": {
            "containerData": {"width": {"size": "CONTENT"}, "alignment": "CENTER"},
            "video": {"src": {"url": f"https://www.youtube.com/watch?v={youtube_id}"}}}})
    for i, p in enumerate(parrafos):
        nodos.append(_parrafo(i, _texto(p)))
    fuente = [_texto(f"Fuente: {_fuente(pieza)}. ")]
    if pieza.get("url_original"):
        fuente.append(_texto("Ver la nota original", pieza["url_original"]))
    nodos.append(_parrafo(len(parrafos), *fuente))

    resumen = " ".join(((pieza.get("guion") or {}).get("bajada") or (parrafos[:1] or [""])[0]).split())
    descripcion = resumen if len(resumen) <= 155 else resumen[:155].rsplit(" ", 1)[0] + "…"
    ahora = datetime.now(TZ_AR).isoformat(timespec="seconds")
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": titulo[:110],
          "description": descripcion, "datePublished": ahora, "dateModified": ahora,
          "inLanguage": "es-AR",
          "author": {"@type": "Organization", "name": MARCA, "url": f"https://{SITIO}"},
          "publisher": {"@type": "Organization", "name": MARCA, "url": f"https://{SITIO}"}}
    borrador = {
        "title": titulo,
        "memberId": member_id or os.environ.get("WIX_MEMBER_ID", ""),
        "categoryIds": [REGION_ID],          # SOLO Región: nunca «Inicio» (la portada)
        "featured": False,
        "excerpt": descripcion,
        "richContent": {"nodes": nodos},
        "seoSlug": slug_de(pieza),
        "seoData": {"tags": [
            {"type": "title", "children": titulo, "custom": False, "disabled": False},
            {"type": "meta", "props": {"name": "description", "content": descripcion},
             "custom": False, "disabled": False},
            {"type": "meta", "props": {"property": "og:title", "content": titulo}},
            {"type": "meta", "props": {"property": "og:description", "content": descripcion}},
            {"type": "meta", "props": {"property": "og:type", "content": "article"}},
            {"type": "script", "props": {"type": "application/ld+json"},
             "children": json.dumps(ld, ensure_ascii=False), "custom": True, "disabled": False},
        ]},
    }
    if file_id:
        borrador["media"] = {"wixMedia": {"image": {"id": file_id}}, "displayed": True, "custom": True}
    return {"draftPost": borrador}


def _json(r, paso: str) -> dict:
    if r.status_code >= 400:
        raise FalloWeb(f"Wix ({paso}): HTTP {r.status_code} — {r.text[:200]}")
    try:
        return r.json() or {}
    except ValueError:
        raise FalloWeb(f"Wix ({paso}): respuesta que no es JSON")


def _ya_publicada(pedir, slug: str) -> str:
    """El slug si ya hay una nota publicada con ese slug (una corrida anterior la creó y se
    cortó antes de anotarla); "" si no."""
    r = pedir("POST", POSTS_QUERY_URL, headers=_headers(),
              json={"query": {"filter": {"slug": {"$eq": slug}}, "paging": {"limit": 1}}}, timeout=30)
    posts = _json(r, "buscar si ya existe").get("posts") or []
    return (posts[0].get("slug") or slug) if posts else ""


def _importar_foto(pedir, url: str, titulo: str) -> str:
    """Importa la foto al Media Manager de Wix desde una URL pública. "" si no se pudo:
    la nota sale igual, sin foto, antes que perderla."""
    if not url:
        return ""
    try:
        r = pedir("POST", MEDIA_IMPORT_URL, headers=_headers(), timeout=60,
                  json={"mediaType": "IMAGE", "url": url, "mimeType": "image/jpeg",
                        "displayName": slugify(titulo)[:80]})
        return (_json(r, "importar foto").get("file") or {}).get("id") or ""
    except Exception:
        return ""


def publicar(pedir, pieza: dict, youtube_id: str = "", foto_respaldo="") -> dict:
    """Crea y publica la nota. Devuelve {id, slug, url}. `pedir(metodo, url, **kw)` es el
    cliente HTTP del publicador (el mismo que se reemplaza en las pruebas). `foto_respaldo`
    es una URL o una función que la devuelve: se usa SOLO si la foto del medio no se deja
    importar (así no se sube nada de más)."""
    slug = slug_de(pieza)
    existente = _ya_publicada(pedir, slug)
    if existente:
        return {"id": None, "slug": existente, "url": link(existente), "ya_estaba": True}

    titulo = (pieza.get("web") or {}).get("titulo") or ""
    file_id = _importar_foto(pedir, pieza.get("imagen_url") or "", titulo)
    if not file_id and foto_respaldo:
        try:
            url = foto_respaldo() if callable(foto_respaldo) else foto_respaldo
        except Exception:
            url = ""
        file_id = _importar_foto(pedir, url, titulo)
    cuerpo = armar_borrador(pieza, file_id, youtube_id)
    r = pedir("POST", DRAFT_POSTS_URL, headers=_headers(), json=cuerpo, timeout=30)
    draft_id = (_json(r, "crear borrador").get("draftPost") or {}).get("id")
    if not draft_id:
        raise FalloWeb("Wix (crear borrador): no devolvió el id")
    r = pedir("POST", f"{DRAFT_POSTS_URL}/{draft_id}/publish", headers=_headers(), json={}, timeout=30)
    _json(r, "publicar")
    return {"id": draft_id, "slug": slug, "url": link(slug), "foto": bool(file_id),
            "video": bool(youtube_id)}
