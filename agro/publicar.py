# -*- coding: utf-8 -*-
"""Publica UNA pieza agro: Short en YouTube (Radio del Centro) → nota en la web (sección Agro, ex Campo) →
reel en Facebook e Instagram de @diarioyradioagro.

Activado por el editor el 14/10/2026 («activá el sistema y hacé una como primer posteo»), con el
arranque decidido el 13/10: 3 reels por día en 3 pasadas (ver agro/seleccion.py).

Reusa los publicadores de policiales (reels/publicador.py: reintentos, contenedores de IG que mienten,
Facebook que procesa en silencio, subida reanudable de YouTube). Esos leen las credenciales de
INSTAGRAM_* / FACEBOOK_*, que son las de @diarioyradio. Para publicar en agro se ponen las AGRO_*
en su lugar SOLO mientras dura la publicación (`credenciales_agro`), con una SALVAGUARDA: si algún
ID agro es uno del diario, no publica nada. Así un error de configuración nunca termina con una
nota del agro en la cuenta del diario.

El orden importa: YouTube primero (la web solo muestra videos de YouTube dentro de la nota), después
la nota web (el texto de Facebook lleva su link), después Facebook e Instagram.

Una red que falla no frena a las demás; lo que salió queda anotado en la memoria para no repetirlo.

17/10/2026 (más contenido, pedido del editor): además del reel (ahora 4:5; Facebook recibe una copia
9:16 con bandas, como policiales), CARRUSELES (nota web → Instagram carrusel → Facebook: las diapositivas
como fotos de una publicación con el link a la nota; no van a YouTube) e HISTORIAS (Instagram y Facebook,
foto 9:16). La portada de cada posteo queda subida al Release para que la tanda de historias siguiente
(otra corrida) la muestre como «novedad».
"""
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

DIARIO_IDS = {"1456376377985890", "17841405971293744"}   # página e IG de @diarioyradio
CAMPO_ID = "0b4eafce-3bb8-44df-96dd-43e53fa24a9c"         # sección «Agro» de la web (ex «Campo», 14/10/2026)
REDES = ("youtube", "web", "facebook", "instagram")
_CLAVES = ("INSTAGRAM_USER_ID", "INSTAGRAM_ACCESS_TOKEN", "FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN")


class SalvaguardaAgro(RuntimeError):
    """Las credenciales agro faltan o apuntan a la cuenta del diario."""


def credenciales() -> dict:
    pag = (os.environ.get("AGRO_FACEBOOK_PAGE_ID") or "").strip()
    ig = (os.environ.get("AGRO_INSTAGRAM_USER_ID") or "").strip()
    tok = (os.environ.get("AGRO_FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
    tok_ig = (os.environ.get("AGRO_INSTAGRAM_ACCESS_TOKEN") or "").strip() or tok   # el de página sirve
    faltan = [n for n, v in (("AGRO_FACEBOOK_PAGE_ID", pag), ("AGRO_INSTAGRAM_USER_ID", ig),
                             ("AGRO_FACEBOOK_PAGE_ACCESS_TOKEN", tok)) if not v]
    if faltan:
        raise SalvaguardaAgro("faltan " + ", ".join(faltan))
    if pag in DIARIO_IDS or ig in DIARIO_IDS:
        raise SalvaguardaAgro("los IDs agro son los de @diarioyradio: no se publica nada")
    otros = {(os.environ.get(k) or "").strip() for k in ("FACEBOOK_PAGE_ACCESS_TOKEN", "INSTAGRAM_ACCESS_TOKEN")}
    if tok in otros - {""} and tok:
        raise SalvaguardaAgro("el token agro es el mismo que el del diario: no se publica nada")
    return {"INSTAGRAM_USER_ID": ig, "INSTAGRAM_ACCESS_TOKEN": tok_ig,
            "FACEBOOK_PAGE_ID": pag, "FACEBOOK_PAGE_ACCESS_TOKEN": tok}


@contextmanager
def credenciales_agro():
    """Pone las AGRO_* donde las leen los publicadores de policiales y, al salir (aunque falle),
    deja todo como estaba."""
    nuevas = credenciales()
    antes = {k: os.environ.get(k) for k in _CLAVES}
    os.environ.update(nuevas)
    try:
        yield nuevas
    finally:
        for k, v in antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def pieza_publicador(pieza: dict) -> dict:
    """La pieza agro con la forma que esperan reels/publicador.py y reels/web.py."""
    from agro import guion as GU
    g = pieza["guion"]
    return {"descripcion_tiktok": GU.texto_red(g, "instagram"),
            "video": {"alto": (pieza.get("reel") or {}).get("alto") or 1350},     # 4:5 → FB en 9:16
            "guion": {"titular": g["titular"], "bajada": g["bajada"]},
            "placa": pieza.get("portada"),
            "web": {"titulo": g.get("titulo_web") or g["titular"], "cuerpo": g.get("nota_web", "")},
            "url_original": pieza["rep"]["url"],
            "imagen_url": ""}       # la foto de otro medio NUNCA se usa en la web: va la nuestra


def metadatos_youtube(pieza: dict, url_web: str = "") -> dict:
    from agro import guion as GU
    from reels import publicador as PB
    g = pieza["guion"]
    titulo = re.sub(r"[<>]", "", g["titular"]).strip()
    if len(titulo) > 100:
        titulo = titulo[:99].rstrip() + "…"
    desc = re.sub(r"[<>]", "", GU.texto_red(g, "youtube", url_web))
    etiquetas = [t.lstrip("#") for t in g.get("hashtags") or []] + ["agro", "campo", "Argentina"]
    ia = (pieza.get("imagen") or {}).get("origen") == "ia"
    return {"snippet": {"title": titulo, "description": desc[:5000], "tags": etiquetas[:12],
                        "categoryId": PB.YT_CATEGORIA, "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            # Imagen ilustrativa generada con IA: se declara (política de YouTube de contenido sintético).
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True,
                       "containsSyntheticMedia": ia}}


def publicar(pieza: dict, ya: dict = None, redes=REDES, log=print) -> dict:
    """Publica la pieza según su formato (reel o carrusel). Devuelve {red: {"id"…} | {"error": …}} y
    «portada_url» (la portada subida al Release, para las historias)."""
    # La portada (imagen + texto SEO, agro/portada.py) se sube PRIMERO: es la miniatura del reel en
    # Instagram (cover_url) y en Facebook, y la «novedad» de las historias.
    portada_url = _subir_portada(pieza)
    if pieza.get("formato") == "carrusel":
        salida = publicar_carrusel(pieza, ya, log=log)
    else:
        if pieza.get("youtube") is False:              # solo el primer reel de cada corrida (agro/pasada.py)
            redes = tuple(r for r in redes if r != "youtube")
        salida = publicar_reel(pieza, ya, redes, log=log, portada_url=portada_url)
    salida["portada_url"] = portada_url
    return salida


def _subir_portada(pieza: dict) -> str:
    from reels import publicador as PB
    portada = pieza.get("portada")
    if not portada or not Path(portada).is_file():
        return ""
    try:
        return PB.subir_a_release(Path(portada), f"agro_{pieza['id']}_portada.jpg")
    except Exception:                                      # noqa: BLE001 — solo la usa la historia
        return ""


def _reel_instagram(pp: dict, mp4: Path, nombre: str, portada_url: str = "") -> dict:
    """El reel en Instagram con la PORTADA propia de miniatura en la grilla (`cover_url`, 17/10/2026).
    Es publicador.publicar_instagram más la portada; si Instagram no la toma, sale sin ella."""
    from reels import instagram as IG
    from reels import publicador as PB
    if not portada_url:
        return PB.publicar_instagram(pp, mp4, nombre)
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    url = PB.subir_a_release(mp4, nombre)
    caption = PB.texto_del_posteo(pp, "instagram")
    params = IG.contenedor_reel(url, caption, portada=portada_url)
    try:
        cid = PB._contenedor_listo(uid, tok, params)
        portada = "propia"
    except PB.FalloRed:
        params.pop("cover_url", None)                      # una portada rechazada no cuesta el reel
        cid = PB._contenedor_listo(uid, tok, params)
        portada = "la que elige Instagram (rechazó la propia)"
    return {"id": PB._publicar_contenedor(uid, tok, cid, caption) or None, "portada": portada}


def _miniatura_facebook(video_id: str, jpg) -> str:
    """La portada como miniatura del reel de Facebook (POST /{video}/thumbnails, is_preferred). Por la
    API no está documentado para reels: si no la toma, queda la que elige Facebook (que con el primer
    cuadro del reel ya es la misma portada)."""
    from reels import publicador as PB
    tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    if not video_id or not jpg or not Path(jpg).is_file():
        return "sin portada"
    try:
        r = PB._pedir("POST", f"{PB.GRAPH}/{video_id}/thumbnails", tok, data={"is_preferred": "true"},
                      files={"source": ("portada.jpg", Path(jpg).read_bytes(), "image/jpeg")})
    except Exception as e:                                 # noqa: BLE001
        return f"no se pudo ({type(e).__name__})"
    return "propia" if r.status_code < 400 else f"la del primer cuadro (HTTP {r.status_code})"


def publicar_reel(pieza: dict, ya: dict = None, redes=REDES, log=print, portada_url: str = "") -> dict:
    """Publica en las `redes` que todavía no salieron (`ya`: {red: resultado} de un intento anterior).
    Devuelve {red: {"id"…} | {"error": …}}. Nunca lanza por una red: la siguiente sigue."""
    from reels import publicador as PB
    from reels import web as W
    ya = dict(ya or {})
    mp4 = Path((pieza.get("reel") or {}).get("archivo") or "")
    if not mp4.is_file():
        return {"error": "la pieza no tiene reel"}
    pp = pieza_publicador(pieza)
    salida = dict(ya)

    def hecho(red):
        return red in salida and not (salida[red] or {}).get("error")

    if "youtube" in redes and not hecho("youtube"):
        try:
            info = PB._subir_youtube(pp, mp4, metadatos_youtube(pieza))
            salida["youtube"] = PB._poner_miniatura(info, pp, mp4)
            log(f"   YouTube: {salida['youtube'].get('url') or salida['youtube'].get('id')}")
        except PB.SinCupoYouTube as e:
            # 19/10/2026: 6 Shorts por día comparten el cupo de la API con policiales y nacionales. Sin
            # cupo, el reel sale igual en las demás redes y no se cuenta como falla.
            salida["youtube"] = {"omitido": f"sin cupo de YouTube por hoy ({str(e)[:120]})"}
            log(f"   YouTube: {salida['youtube']['omitido']}")
        except Exception as e:                             # noqa: BLE001
            salida["youtube"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   YouTube FALLÓ: {salida['youtube']['error']}")
    yt_id = (salida.get("youtube") or {}).get("id") if hecho("youtube") else ""

    if "web" in redes and not hecho("web") and W.activa() and not W.faltantes():
        imagen = (pieza.get("imagen") or {}).get("archivo")
        try:
            respaldo = (lambda: PB.subir_a_release(Path(imagen), f"agro_{pieza['id']}.jpg")) if imagen else ""
            salida["web"] = W.publicar(lambda m, u, **kw: PB._pedir(m, u, "", **kw), pp, youtube_id=yt_id or "",
                                       foto_respaldo=respaldo, categorias=[CAMPO_ID])
            log(f"   Web: {salida['web'].get('url')}")
        except Exception as e:                             # noqa: BLE001
            salida["web"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Web FALLÓ: {salida['web']['error']}")
    url_web = (salida.get("web") or {}).get("url", "") if hecho("web") else ""

    with credenciales_agro():
        if "facebook" in redes and not hecho("facebook"):
            try:
                salida["facebook"] = PB.publicar_facebook(pp, mp4, url_web)
                salida["facebook"]["miniatura"] = _miniatura_facebook(salida["facebook"].get("id"), pieza.get("portada"))
                log(f"   Facebook: video {salida['facebook'].get('id')} (miniatura: {salida['facebook']['miniatura']})")
            except Exception as e:                         # noqa: BLE001
                salida["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Facebook FALLÓ: {salida['facebook']['error']}")
        if "instagram" in redes and not hecho("instagram"):
            try:
                salida["instagram"] = _reel_instagram(pp, mp4, f"agro_{pieza['id']}.mp4", portada_url)
                log(f"   Instagram: {salida['instagram'].get('id')} (portada: {salida['instagram'].get('portada', '—')})")
            except Exception as e:                         # noqa: BLE001
                salida["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Instagram FALLÓ: {salida['instagram']['error']}")
    return salida


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Carrusel
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _carrusel_instagram(urls: list, caption: str) -> dict:
    """Las diapositivas como contenedores hijos y el CAROUSEL padre (lo mismo que nacionales)."""
    from reels import publicador as PB
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    hijos = []
    for url in urls:
        hijos.append(PB._contenedor_listo(uid, tok, {"image_url": url, "is_carousel_item": "true"}))
    padre = PB._contenedor_listo(uid, tok, {"media_type": "CAROUSEL", "children": ",".join(hijos),
                                            "caption": caption[:PB.MAX_CAPTION_IG]})
    return {"id": PB._publicar_contenedor(uid, tok, padre, caption) or None, "diapositivas": len(urls)}


def _fotos_facebook(urls: list, mensaje: str) -> dict:
    """Una publicación del muro con las diapositivas como fotos (lo más parecido a un carrusel en una
    página): cada foto se sube sin publicar y después va todo junto con el texto."""
    from reels import publicador as PB
    pid = os.environ.get("FACEBOOK_PAGE_ID", "")
    tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    ids = []
    for i, url in enumerate(urls):
        r = PB._pedir("POST", f"{PB.GRAPH}/{pid}/photos", tok, data={"url": url, "published": "false"})
        if r.status_code >= 400:
            raise PB.FalloRed(PB._error(r, f"Facebook (foto {i + 1})"))
        ids.append(str((r.json() or {}).get("id")))
    datos = {"message": mensaje}
    for i, fid in enumerate(ids):
        datos[f"attached_media[{i}]"] = json.dumps({"media_fbid": fid})
    try:
        r = PB._pedir("POST", f"{PB.GRAPH}/{pid}/feed", tok, data=datos)
    except PB._Cortado as e:
        raise PB.SinConfirmar(f"Facebook (publicación con fotos): {e}")
    if r.status_code >= 400:
        raise PB.FalloRed(PB._error(r, "Facebook (publicación con fotos)"))
    return {"id": str((r.json() or {}).get("id") or ""), "fotos": len(ids)}


def publicar_carrusel(pieza: dict, ya: dict = None, log=print) -> dict:
    """Web (si es una noticia) → Instagram (carrusel) → Facebook (fotos + link)."""
    from agro import guion as GU
    from reels import publicador as PB
    from reels import web as W
    salida = dict(ya or {})
    jpgs = [j for j in (pieza.get("carrusel") or {}).get("archivos") or [] if Path(j).is_file()]
    if len(jpgs) < 2:
        return {"error": "el carrusel no tiene diapositivas"}
    g = pieza["guion"]

    def hecho(red):
        return red in salida and not (salida[red] or {}).get("error")

    if not pieza.get("datos") and not hecho("web") and W.activa() and not W.faltantes():
        imagen = (pieza.get("imagen") or {}).get("archivo") or jpgs[0]
        try:
            pp = pieza_publicador(pieza)

            def respaldo():
                return PB.subir_a_release(Path(imagen), f"agro_{pieza['id']}.jpg")
            salida["web"] = W.publicar(lambda m, u, **kw: PB._pedir(m, u, "", **kw), pp, youtube_id="",
                                       foto_respaldo=respaldo, categorias=[CAMPO_ID])
            log(f"   Web: {salida['web'].get('url')}")
        except Exception as e:                             # noqa: BLE001
            salida["web"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Web FALLÓ: {salida['web']['error']}")
    url_web = (salida.get("web") or {}).get("url", "") if hecho("web") else ""
    caption = (pieza.get("carrusel") or {}).get("caption") or GU.texto_red(g, "instagram")
    mensaje = caption if pieza.get("datos") else GU.texto_red(g, "facebook", url_web)
    marca = re.sub(r"[^\w-]", "", str(pieza["id"]))[:40]
    try:
        urls = [PB.subir_a_release(Path(j), f"agro_{marca}_c{i:02d}.jpg") for i, j in enumerate(jpgs)]
    except Exception as e:                                 # noqa: BLE001
        error = {"error": f"no se pudieron subir las diapositivas: {type(e).__name__}: {str(e)[:160]}"}
        return dict(salida, **{red: error for red in ("instagram", "facebook") if not hecho(red)})
    with credenciales_agro():
        if not hecho("instagram"):
            try:
                salida["instagram"] = _carrusel_instagram(urls, caption)
                log(f"   Instagram (carrusel): {salida['instagram'].get('id')}")
            except Exception as e:                         # noqa: BLE001
                salida["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Instagram FALLÓ: {salida['instagram']['error']}")
        if not hecho("facebook"):
            try:
                salida["facebook"] = _fotos_facebook(urls, mensaje)
                log(f"   Facebook (fotos): {salida['facebook'].get('id')}")
            except Exception as e:                         # noqa: BLE001
                salida["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Facebook FALLÓ: {salida['facebook']['error']}")
    return salida


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Historias
# ─────────────────────────────────────────────────────────────────────────────────────────────
ESPERAS_HISTORIA_IG = (20, 60)       # contenedores nuevos si Instagram confirma que la historia no salió


def _historia_instagram(url: str) -> dict:
    from reels import publicador as PB
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    # 26/10/2026: media_publish contestó 400 «No se encuentra el contenido multimedia con el identificador…»
    # con un contenedor FINISHED (la historia del dólar de las 19; la corrida quedó en rojo). Ese contenedor
    # ya no sirve: se arma uno NUEVO. FalloRed = Instagram confirmó que NO salió, así que no se duplica.
    for intento in range(len(ESPERAS_HISTORIA_IG) + 1):
        if intento:
            PB._dormir(ESPERAS_HISTORIA_IG[intento - 1])
        try:
            cid = PB._contenedor_listo(uid, tok, {"image_url": url, "media_type": "STORIES"})
            return {"id": PB._publicar_contenedor(uid, tok, cid, "") or None}
        except PB.FalloRed as e:
            if intento == len(ESPERAS_HISTORIA_IG):
                raise
            print(f"   (Instagram: la historia no salió — {str(e)[:120]}; va con un contenedor nuevo)")


def _historia_facebook(url: str) -> dict:
    from reels import publicador as PB
    pid = os.environ.get("FACEBOOK_PAGE_ID", "")
    tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    r = PB._pedir("POST", f"{PB.GRAPH}/{pid}/photos", tok, data={"url": url, "published": "false"})
    if r.status_code >= 400:
        raise PB.FalloRed(PB._error(r, "Facebook (foto de la historia)"))
    foto = str((r.json() or {}).get("id"))
    try:
        r = PB._pedir("POST", f"{PB.GRAPH}/{pid}/photo_stories", tok, data={"photo_id": foto})
    except PB._Cortado as e:
        raise PB.SinConfirmar(f"Facebook (historia): {e}")
    if r.status_code >= 400:
        raise PB.FalloRed(PB._error(r, "Facebook (historia)"))
    d = r.json() or {}
    return {"id": str(d.get("post_id") or d.get("id") or foto)}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# @diarioyradio (23/10/2026, pedido del editor: «quiero que las historias de @diarioyradioagro también se
# carguen en @diarioyradio (clima, alertas, commodities, dólar, soja, trigo, maíz)» y el reel de datos de
# las 5 «como colab»). Acá SÍ se usan las credenciales del diario, a propósito y solo para esto; la
# salvaguarda (credenciales_diario) mira que sean las de @diarioyradio y no las de agro.
# ─────────────────────────────────────────────────────────────────────────────────────────────
TIPOS_AL_DIARIO = {"alerta", "clima", "clima_manana", "granos", "dolar", "chicago",
                   "semana_granos", "semana_dolar", "semana_chicago"}
DIARIO_IG_USUARIO = "diarioyradio"


def historias_al_diario() -> bool:
    """¿Se copian las historias de datos en @diarioyradio? APAGADO desde el 28/10/2026 a pedido del editor
    («deshabilitá las historias que se suben a @diarioyradio de @diarioyradioagro»). Variable del repo
    AGRO_HISTORIAS_DIARIO=1 las vuelve a prender."""
    return (os.environ.get("AGRO_HISTORIAS_DIARIO") or "0").strip() == "1"


def usuario_diario() -> str:
    return (os.environ.get("DIARIO_IG_USUARIO") or DIARIO_IG_USUARIO).strip().lstrip("@")


def credenciales_diario() -> dict:
    """Las del diario tal como están en el entorno (las que usan policiales y nacionales), verificadas."""
    ig = (os.environ.get("INSTAGRAM_USER_ID") or "").strip()
    pag = (os.environ.get("FACEBOOK_PAGE_ID") or "").strip()
    tok_fb = (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
    tok_ig = (os.environ.get("INSTAGRAM_ACCESS_TOKEN") or "").strip() or tok_fb
    faltan = [n for n, v in (("INSTAGRAM_USER_ID", ig), ("FACEBOOK_PAGE_ID", pag),
                             ("FACEBOOK_PAGE_ACCESS_TOKEN", tok_fb)) if not v]
    if faltan:
        raise SalvaguardaAgro("faltan las del diario: " + ", ".join(faltan))
    if ig not in DIARIO_IDS or pag not in DIARIO_IDS:
        raise SalvaguardaAgro("las credenciales del diario no son las de @diarioyradio")
    return {"INSTAGRAM_USER_ID": ig, "INSTAGRAM_ACCESS_TOKEN": tok_ig, "FACEBOOK_PAGE_ID": pag,
            "FACEBOOK_PAGE_ACCESS_TOKEN": tok_fb}


def publicar_historias_diario(tanda: list, log=print) -> dict:
    """Las historias de datos también en Instagram y Facebook de @diarioyradio. En Instagram solo si al
    diario le queda cupo (las 100 por día las comparte con el bot, policiales y nacionales)."""
    from reels import publicador as PB
    try:
        credenciales_diario()
    except SalvaguardaAgro as e:
        log(f"   @diarioyradio: no se copian las historias ({e})")
        return {"error": str(e)}
    lugar = PB._lugar_en_instagram()
    con_ig = lugar is None or lugar[0] >= len(tanda)
    if not con_ig:
        log(f"   @diarioyradio: sin cupo de Instagram ({lugar[1]}/{lugar[2]}): las historias van solo a Facebook")
    items = []
    for i, h in enumerate(tanda):
        r = {}
        try:
            url = PB.subir_a_release(Path(h["archivo"]), f"agro_hist_diario_{Path(h['archivo']).parent.name}_{i:02d}.jpg")
        except Exception as e:                             # noqa: BLE001
            items.append({"error": f"subida: {e}"[:200]})
            continue
        for red, fn in (("instagram", _historia_instagram), ("facebook", _historia_facebook)):
            if red == "instagram" and not con_ig:
                r[red] = {"omitido": "sin cupo de Instagram"}
                continue
            try:
                r[red] = fn(url)
            except Exception as e:                         # noqa: BLE001
                r[red] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        log(f"   @diarioyradio historia {i + 1} ({h['tipo']}): IG {_ver(r.get('instagram'))} · FB {_ver(r.get('facebook'))}")
        items.append(r)
    return {"items": items}


def _ver(r) -> str:
    r = r or {}
    return str(r.get("id") or r.get("error") or r.get("omitido") or "—")


def aceptar_colab(media_id: str, log=print, esperas=(5, 10, 20, 30, 60)) -> dict:
    """Con la cuenta de @diarioyradio, acepta la invitación a colaborar en `media_id` (Instagram,
    /collaboration_invites, desde diciembre de 2025). La invitación tarda unos segundos en aparecer."""
    from reels import publicador as PB
    c = credenciales_diario()
    uid, tok = c["INSTAGRAM_USER_ID"], c["INSTAGRAM_ACCESS_TOKEN"]
    ultimo = ""
    for espera in (0,) + tuple(esperas):
        if espera:
            PB._dormir(espera)
        r = PB._pedir("GET", f"{PB.GRAPH}/{uid}/collaboration_invites", tok)
        if r.status_code >= 400:
            ultimo = PB._error(r, "invitaciones de colab")
            continue
        ids = {str(x.get("media_id") or x.get("id") or "") for x in (r.json() or {}).get("data") or []}
        if str(media_id) not in ids:
            ultimo = "la invitación todavía no aparece"
            continue
        r = PB._pedir("POST", f"{PB.GRAPH}/{uid}/collaboration_invites", tok,
                      data={"media_id": str(media_id), "accept": "true"})
        if r.status_code < 400 and (r.json() or {}).get("success", True):
            log("   colab: @diarioyradio aceptó")
            return {"estado": "aceptada"}
        ultimo = PB._error(r, "aceptar la colab")
    log(f"   colab: no se pudo aceptar sola ({ultimo}); queda para aceptarla desde la app de @diarioyradio")
    return {"estado": "pendiente", "detalle": ultimo}


def publicar_historias(tanda: list, log=print) -> dict:
    """Cada historia en Instagram y en Facebook, en orden. Una que falla no frena a las demás.
    {"items": [{"instagram": {...}, "facebook": {...}}…]}."""
    from reels import publicador as PB
    items = []
    with credenciales_agro():
        for i, h in enumerate(tanda):
            r = {}
            try:
                url = PB.subir_a_release(Path(h["archivo"]), f"agro_hist_{Path(h['archivo']).parent.name}_{i:02d}.jpg")
            except Exception as e:                         # noqa: BLE001
                items.append({"instagram": {"error": f"subida: {e}"[:200]}, "facebook": {"error": "sin subida"}})
                continue
            for red, fn in (("instagram", _historia_instagram), ("facebook", _historia_facebook)):
                try:
                    r[red] = fn(url)
                except Exception as e:                     # noqa: BLE001
                    r[red] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   historia {i + 1} ({h['tipo']}): IG {r['instagram'].get('id') or r['instagram'].get('error')}"
                f" · FB {r['facebook'].get('id') or r['facebook'].get('error')}")
            items.append(r)
    return {"items": items}
