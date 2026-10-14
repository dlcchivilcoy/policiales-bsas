# -*- coding: utf-8 -*-
"""Publica UNA pieza agro: Short en YouTube (Radio del Centro) → nota en la web (sección Campo) →
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
"""
import os
import re
from contextlib import contextmanager
from pathlib import Path

DIARIO_IDS = {"1456376377985890", "17841405971293744"}   # página e IG de @diarioyradio
CAMPO_ID = "0b4eafce-3bb8-44df-96dd-43e53fa24a9c"         # sección «Campo» de la web (Wix)
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
                log(f"   Facebook: video {salida['facebook'].get('id')}")
            except Exception as e:                         # noqa: BLE001
                salida["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Facebook FALLÓ: {salida['facebook']['error']}")
        if "instagram" in redes and not hecho("instagram"):
            try:
                salida["instagram"] = PB.publicar_instagram(pp, mp4, f"agro_{pieza['id']}.mp4")
                log(f"   Instagram: {salida['instagram'].get('id')}")
            except Exception as e:                         # noqa: BLE001
                salida["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Instagram FALLÓ: {salida['instagram']['error']}")
    return salida
