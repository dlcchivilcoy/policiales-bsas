# -*- coding: utf-8 -*-
"""Publica una tanda de reels: Instagram (PRUEBA), Facebook (normal) y YouTube (Short).

    venv\\Scripts\\python.exe -m reels.publicador                 # SIMULA la ultima tanda
    venv\\Scripts\\python.exe -m reels.publicador --publicar      # publica de verdad
    venv\\Scripts\\python.exe -m reels.publicador --lote salida_reels\\2026-09-26_1900
    venv\\Scripts\\python.exe -m reels.publicador --redes instagram,youtube

Decidido por el editor el 2026-09-26:
- Instagram: TODO sale como reel de prueba con graduacion automatica (el que anda
  con los no seguidores pasa solo al feed). El pedido lo arma
  `reels/instagram.py: contenedor_reel()` y este modulo no le agrega nada por su
  cuenta: la regla vive en un solo lugar.
- Facebook: reel normal, le llega directo a los seguidores. La API de Facebook no
  tiene reels de prueba (verificado en la referencia de `video_reels`).
- YouTube: Short publico en el canal RADIO DEL CENTRO (@radiodelcentro), con un
  tope diario de seguridad (ver YT_SHORTS_POR_DIA).
- TikTok: DESACTIVADO hasta que TikTok apruebe el Direct Post. Ni publicacion ni
  BORRADORES: no hay codigo que le hable, y la red se rechaza aunque se la pida.
- 5 minutos entre posteo y posteo (`MINUTOS_ENTRE_POSTEOS` de flujo.py). Al publicar
  de verdad la espera NO se puede saltear: es para que las redes no lean la cuenta
  como un bot.
- Sin revision humana: sale lo que el flujo marco `apto_para_publicar`.

SIN `--publicar` no se toca ninguna red: muestra que saldria, a que hora y con que
texto, y chequea todo lo que se puede chequear sin publicar. Es el default a
proposito: publicar tiene que ser un gesto explicito, nunca un olvido.

Lo que ya costo caro en el bot del diario y aca viene resuelto de entrada:
- Instagram a veces contesta 500 "transitorio" AUNQUE el reel haya salido (14 reels
  dados por fallidos que estaban publicados). Reintentar a ciegas lo duplica. Antes
  de reintentar se mira el estado del contenedor: si dice PUBLISHED, salio.
- Un contenedor en ERROR queda quemado: hay que crear uno nuevo, no reintentar el mismo.
- Facebook contesta 200 al "finish" y despues el procesamiento puede fallar en
  silencio. Se espera a que el video diga que salio.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reels import instagram as IG
from reels import limpieza as L
from reels.flujo import MINUTOS_ENTRE_POSTEOS, SALIDA_REELS
from scraper.localidades import nombre as _pueblo

import entorno

RAIZ = Path(__file__).resolve().parent.parent
# Memoria de lo publicado, por nota y por red. Vive en estado/ porque el workflow
# commitea esa carpeta de vuelta al repo: es lo que evita publicar dos veces.
LEDGER = RAIZ / "estado" / "publicados.json"
DIAS_LEDGER = 5

# La version importa: `trial_params` (reels de prueba) es nuevo, y una version vieja
# podria IGNORARLO sin dar error y sacar el reel normal, directo a los seguidores.
# Verificado el 26/09 que v26.0 responde con los tokens del diario.
VERSION_GRAPH = "v26.0"
GRAPH = f"https://graph.facebook.com/{VERSION_GRAPH}"

REDES = ("instagram", "facebook", "youtube")
NOMBRE_RED = {"instagram": "Instagram", "facebook": "Facebook", "youtube": "YouTube"}

# TikTok APAGADO por decision del editor (26/09/2026), hasta que TikTok apruebe la
# auditoria de Direct Post. Ni publicar ni mandar a BORRADORES. No es un ajuste
# tecnico: prenderlo es decision del editor, y ademas hoy no hay codigo que suba a
# TikTok. Si alguien pide la red igual, el publicador se niega (ver _rechazar_tiktok).
TIKTOK_ACTIVO = False

MAX_CAPTION_IG = 2200
DURACION_REEL = (3, 90)        # segundos que acepta un reel de Facebook (Instagram admite mas)

GITHUB_API = "https://api.github.com"
GITHUB_UPLOADS = "https://uploads.github.com"
TAG_RELEASE = "reels-policiales"          # el mismo que barre limpieza.limpiar_release()
REPO = "dlcchivilcoy/policiales-bsas"     # PUBLICO: por eso Instagram puede bajar el .mp4

ESPERA_PROCESO = 300                      # s que se espera a que IG/FB procesen el video
ESPERAS_CONTENEDOR = (20, 60)             # contenedor de IG en ERROR: hasta 3 en total
ESPERAS_PUBLICAR = (10, 30, 60)           # media_publish con error transitorio
_HTTP_TRANSITORIO = (429, 500, 502, 503, 504)

# YouTube. El token es YT_TOKEN_JSON = canal RADIO DEL CENTRO (verificado el 26/09 con
# channels.list; YT_SHORTS_TOKEN_JSON es el del canal del DIARIO, no se usa aca).
YT_API = "https://www.googleapis.com/youtube/v3"
YT_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_CATEGORIA = "25"                       # Noticias y politica
# CUPO DE YOUTUBE (verificado en la documentacion oficial el 26/09/2026):
# desde el 1/06/2026 las subidas (videos.insert) tienen su PROPIO cupo: 100 subidas por
# dia POR PROYECTO de Google, aparte de las 10.000 unidades del resto de la API. (Antes
# cada subida costaba ~1.600 de esas 10.000 = 6 por dia; ese numero quedo VIEJO y
# todavia aparece en comentarios del bot del diario.)
# El proyecto es el MISMO del bot, que tambien sube sus Shorts a Radio del Centro (~10
# por dia habil). 100 alcanza de sobra para los dos. El tope queda como freno ante un
# desborde (corridas a mano repetidas, un bucle), no como racion: 20 cubre las 3 pasadas
# de 5 piezas y le deja 80 al bot. Se cambia con YT_SHORTS_POR_DIA (variable del repo).
YT_SHORTS_POR_DIA_DEFAULT = 20

# Enganches para las pruebas (tools/test_publicador.py): la red, el reloj y la espera.
_http = None
_dormir = time.sleep
_ahora = datetime.now
_barrer_release = L.limpiar_release
_token_gh = ""
_ocultar = []              # tokens obtenidos en la corrida (gh, acceso de YouTube)
_yt_acceso = ""            # token de acceso de YouTube, ya verificado contra el canal
_yt_sin_cupo = False       # YouTube dijo "cupo agotado": no se insiste en esta pasada


class FalloRed(Exception):
    """La red dijo que no: no salio."""


class SinConfirmar(Exception):
    """Pudo haber salido y no hay forma de saberlo. NO se reintenta nunca: publicar
    dos veces el mismo hecho es peor que perder un posteo."""


class _Cortado(Exception):
    """No hubo respuesta (corte o timeout): no se sabe si el pedido llego."""


# =============================================================================
# Red
# =============================================================================

def _cliente() -> httpx.Client:
    global _http
    if _http is None:
        _http = httpx.Client(timeout=120, follow_redirects=True)
    return _http


def _tapar(texto: str) -> str:
    """Saca cualquier token de un mensaje antes de imprimirlo o guardarlo.

    El repo es PUBLICO y los logs de Actions tambien. GitHub enmascara los secrets que
    reconoce, pero un token que llega por `gh auth token` no es un secret suyo.
    """
    texto = str(texto)
    valores = [os.environ.get(k, "") for k in (
        "FACEBOOK_PAGE_ACCESS_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")]
    try:
        yt = json.loads(os.environ.get("YT_TOKEN_JSON") or "{}")
        valores += [str(yt.get(k) or "") for k in ("token", "refresh_token", "client_secret")]
    except (ValueError, AttributeError):
        pass
    for v in valores + [_token_gh] + _ocultar:
        if v and len(v) > 8:
            texto = texto.replace(v, "***")
    return texto


def _pedir(metodo: str, url: str, token: str = "", **kw) -> httpx.Response:
    """Un pedido HTTP. El token va en el ENCABEZADO, nunca en la URL: una URL termina
    en los mensajes de error, y de ahi en un log publico."""
    h = dict(kw.pop("headers", None) or {})
    if token:
        h.setdefault("Authorization", f"Bearer {token}")
    try:
        return _cliente().request(metodo, url, headers=h, **kw)
    except httpx.HTTPError as e:
        raise _Cortado(_tapar(f"{type(e).__name__}: {e}")) from None


def _error(r: httpx.Response, paso: str) -> str:
    try:
        err = (r.json() or {}).get("error") or {}
        detalle = err.get("error_user_msg") or err.get("message") or r.text[:300]
    except ValueError:
        detalle = r.text[:300]
    return _tapar(f"{paso}: HTTP {r.status_code} — {detalle}")


def _transitorio(r: httpx.Response) -> bool:
    """¿Es un bache de Meta que vale la pena reintentar?"""
    if r.status_code in _HTTP_TRANSITORIO:
        return True
    try:
        err = (r.json() or {}).get("error") or {}
    except ValueError:
        return False
    return bool(err.get("is_transient")) or err.get("code") in (1, 2, 4, 17, 32, 341)


# =============================================================================
# El .mp4 en una URL publica (Instagram no recibe el archivo: lo va a buscar)
# =============================================================================

def _token_github() -> str:
    global _token_gh
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or _token_gh
    if tok:
        return tok
    # En una maquina local: la cuenta con la que se hace push (colaboradora del repo).
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                             timeout=20)
        _token_gh = out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        _token_gh = ""
    if _token_gh:
        _ocultar.append(_token_gh)
    return _token_gh


def subir_a_release(mp4: Path, nombre: str) -> str:
    """Sube el .mp4 como asset del Release `reels-policiales` y devuelve su URL publica.

    Mismo patron que `utils/video_host.py` del bot. Los assets los barre
    `limpieza.limpiar_release()` a las 24 h: para entonces Instagram ya tiene su copia.
    """
    tok = _token_github()
    if not tok:
        raise FalloRed("no hay GITHUB_TOKEN (ni sesion de `gh`) para subir el video")
    repo = os.environ.get("GITHUB_REPOSITORY") or REPO
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    datos = mp4.read_bytes()
    ultimo = ""
    for intento in range(3):
        if intento:
            _dormir(5 * intento)
        try:
            r = _pedir("GET", f"{GITHUB_API}/repos/{repo}/releases/tags/{TAG_RELEASE}",
                       tok, headers=h)
            if r.status_code == 404:
                r = _pedir("POST", f"{GITHUB_API}/repos/{repo}/releases", tok, headers=h,
                           json={"tag_name": TAG_RELEASE, "prerelease": True,
                                 "name": "Reels de policiales (temporal)",
                                 "body": "Videos que Instagram va a buscar al publicar. "
                                         "Se borran solos a las 24 h."})
            if r.status_code >= 400:
                ultimo = f"release: HTTP {r.status_code} {r.text[:200]}"
                if r.status_code in _HTTP_TRANSITORIO:
                    continue
                break
            rel = r.json()
            for a in rel.get("assets", []):       # GitHub no admite dos con el mismo nombre
                if a.get("name") == nombre:
                    _pedir("DELETE", f"{GITHUB_API}/repos/{repo}/releases/assets/{a['id']}",
                           tok, headers=h)
            up = _pedir("POST", f"{GITHUB_UPLOADS}/repos/{repo}/releases/{rel['id']}/assets",
                        tok, headers={**h, "Content-Type": "video/mp4"},
                        params={"name": nombre}, content=datos)
            if up.status_code < 400:
                url = up.json()["browser_download_url"]
                # Instagram la baja SIN credenciales. Si nosotros tampoco podemos, el
                # contenedor va a terminar en ERROR y conviene saberlo aca, no despues.
                prueba = _pedir("HEAD", url)
                if prueba.status_code >= 400:
                    raise FalloRed(f"el video subio pero su URL no es publica "
                                   f"(HTTP {prueba.status_code}): ¿el repo dejo de ser publico?")
                return url
            ultimo = f"subida: HTTP {up.status_code} {up.text[:200]}"
            if up.status_code not in _HTTP_TRANSITORIO:
                break
        except _Cortado as e:
            ultimo = str(e)
    raise FalloRed(_tapar(f"no se pudo subir el video a GitHub — {ultimo}"))


# =============================================================================
# Instagram: reel de PRUEBA
# =============================================================================

def _estado_contenedor(cid: str, tok: str) -> tuple:
    """(status_code, status). `status` es donde Instagram explica QUE paso."""
    try:
        r = _pedir("GET", f"{GRAPH}/{cid}", tok, params={"fields": "status_code,status"})
    except _Cortado:
        return "", ""
    if r.status_code >= 400:
        return "", ""
    d = r.json() or {}
    return d.get("status_code") or "", d.get("status") or ""


def _contenedor_listo(uid: str, tok: str, params: dict) -> str:
    """Crea el contenedor y espera a que Instagram procese el video. Si termina en
    ERROR, crea uno NUEVO: el que fallo no se puede reusar."""
    ultimo = ""
    for i in range(len(ESPERAS_CONTENEDOR) + 1):
        if i:
            _dormir(ESPERAS_CONTENEDOR[i - 1])
        try:
            r = _pedir("POST", f"{GRAPH}/{uid}/media", tok, data=params)
        except _Cortado as e:
            # Un contenedor huerfano nunca se publica solo: repetir es inocuo.
            ultimo = str(e)
            continue
        if r.status_code >= 400:
            ultimo = _error(r, "crear el contenedor")
            if _transitorio(r):
                continue
            raise FalloRed(ultimo)
        cid = r.json()["id"]

        limite = _ahora() + timedelta(seconds=ESPERA_PROCESO)
        estado = detalle = ""
        while True:
            estado, det = _estado_contenedor(cid, tok)
            detalle = det or detalle
            if estado == "FINISHED":
                return cid
            if estado in ("ERROR", "EXPIRED"):
                break
            if _ahora() >= limite:
                raise FalloRed(f"Instagram no termino de procesar el video en "
                               f"{ESPERA_PROCESO // 60} min" + (f" — {detalle}" if detalle else ""))
            _dormir(5)
        ultimo = f"el contenedor quedo en {estado}" + (f" — {detalle}" if detalle else "")
    raise FalloRed(f"Instagram: {ultimo}")


def _clave_caption(texto: str) -> str:
    return " ".join((texto or "").split())[:80].lower()


def _buscar_media(uid: str, tok: str, caption: str) -> str:
    """El id del reel recien publicado, buscado por el arranque del texto. Puede no
    aparecer: no esta documentado que un reel de prueba figure en /media."""
    try:
        r = _pedir("GET", f"{GRAPH}/{uid}/media", tok,
                   params={"fields": "id,caption", "limit": 10})
        if r.status_code >= 400:
            return ""
        buscado = _clave_caption(caption)
        for m in (r.json() or {}).get("data") or []:
            if _clave_caption(m.get("caption") or "") == buscado:
                return m.get("id") or ""
    except (_Cortado, ValueError):
        pass
    return ""


def _publicar_contenedor(uid: str, tok: str, cid: str, caption: str) -> str:
    """media_publish. Antes de CADA reintento se mira si el anterior salio igual."""
    ultimo = ""
    for i in range(len(ESPERAS_PUBLICAR) + 1):
        if i:
            _dormir(ESPERAS_PUBLICAR[i - 1])
            if _estado_contenedor(cid, tok)[0] == "PUBLISHED":
                return _buscar_media(uid, tok, caption)     # el error era mentira
        try:
            r = _pedir("POST", f"{GRAPH}/{uid}/media_publish", tok,
                       data={"creation_id": cid})
        except _Cortado as e:
            ultimo = str(e)
            continue
        if r.status_code < 400:
            return (r.json() or {}).get("id") or ""
        ultimo = _error(r, "publicar")
        if not _transitorio(r):
            break

    # Ultima mirada antes de dar un veredicto: pudo haber salido en el intento que "fallo".
    _dormir(10)
    estado, _ = _estado_contenedor(cid, tok)
    if estado == "PUBLISHED":
        return _buscar_media(uid, tok, caption)
    if estado:
        raise FalloRed(f"Instagram: {ultimo}")     # el contenedor dice que NO salio
    raise SinConfirmar(f"Instagram: {ultimo} — y no se pudo leer si salio igual")


def publicar_instagram(pieza: dict, mp4: Path, nombre: str) -> dict:
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    url = subir_a_release(mp4, nombre)
    caption = texto_del_posteo(pieza, "instagram")
    params = IG.contenedor_reel(url, caption)      # ← la regla del reel de prueba
    cid = _contenedor_listo(uid, tok, params)
    media_id = _publicar_contenedor(uid, tok, cid, caption)
    return {"id": media_id or None, "prueba": json.loads(params.get("trial_params") or "null")}


# =============================================================================
# Facebook: reel NORMAL
# =============================================================================

def _estado_video_fb(vid: str, tok: str) -> dict:
    try:
        r = _pedir("GET", f"{GRAPH}/{vid}", tok, params={"fields": "status"})
    except _Cortado:
        return {}
    if r.status_code >= 400:
        return {}
    return (r.json() or {}).get("status") or {}


def publicar_facebook(pieza: dict, mp4: Path) -> dict:
    """/{page}/video_reels en tres pasos: inicio → subir el archivo → publicar."""
    pid = os.environ.get("FACEBOOK_PAGE_ID", "")
    tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    base = f"{GRAPH}/{pid}/video_reels"

    try:
        r = _pedir("POST", base, tok, data={"upload_phase": "start"})
    except _Cortado as e:
        raise FalloRed(f"Facebook (inicio): {e}")
    if r.status_code >= 400:
        raise FalloRed(_error(r, "Facebook (inicio)"))
    d = r.json() or {}
    vid = str(d["video_id"])
    destino = d.get("upload_url") or f"https://rupload.facebook.com/video-upload/{VERSION_GRAPH}/{vid}"

    # Subir el archivo se puede reintentar: todavia no hay nada publicado.
    datos = mp4.read_bytes()
    ultimo = ""
    for intento in range(3):
        if intento:
            _dormir(5 * intento)
        try:
            up = _pedir("POST", destino, headers={
                "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(datos))},
                content=datos)
        except _Cortado as e:
            ultimo = str(e)
            continue
        if up.status_code < 400:
            break
        ultimo = _error(up, "Facebook (subida)")
        if up.status_code not in _HTTP_TRANSITORIO:
            raise FalloRed(ultimo)
    else:
        raise FalloRed(ultimo)

    # Publicar NO se reintenta a ciegas: si la respuesta se pierde, el estado del
    # video es el que dice si salio.
    confirmado = False
    try:
        fin = _pedir("POST", base, tok, data={
            "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
            "description": texto_del_posteo(pieza, "facebook")})
        if fin.status_code < 400:
            confirmado = True
        elif not _transitorio(fin):
            raise FalloRed(_error(fin, "Facebook (publicar)"))
    except _Cortado:
        pass

    # Facebook contesta 200 al instante y DESPUES procesa: ahi puede fallar sin avisar.
    limite = _ahora() + timedelta(seconds=ESPERA_PROCESO)
    while _ahora() < limite:
        _dormir(10)
        st = _estado_video_fb(vid, tok)
        video = str(st.get("video_status") or "").lower()
        fase = st.get("publishing_phase") or {}
        publicacion = str(fase.get("status") or "").lower()
        salio = publicacion == "complete" or str(fase.get("publish_status") or "").lower() == "published"
        if salio or (confirmado and video in ("ready", "published")):
            return {"id": vid}
        if video in ("error", "expired") or publicacion in ("error", "failed"):
            raise FalloRed(f"Facebook: el reel fallo al procesarse ({st})")
    raise SinConfirmar(f"Facebook no confirmo el reel en {ESPERA_PROCESO // 60} min: "
                       f"puede aparecer igual (video {vid})")


# =============================================================================
# YouTube: Short en Radio del Centro
# =============================================================================

class SinCupoYouTube(FalloRed):
    """YouTube dijo que se agoto el cupo del dia: no se insiste hasta mañana."""


def _yt_error(r: httpx.Response, paso: str) -> str:
    try:
        err = (r.json() or {}).get("error") or {}
        razones = [e.get("reason") for e in err.get("errors") or [] if e.get("reason")]
        detalle = err.get("message") or r.text[:300]
    except (ValueError, AttributeError):
        razones, detalle = [], r.text[:300]
    msg = _tapar(f"{paso}: HTTP {r.status_code} — {detalle}")
    if {"quotaExceeded", "uploadLimitExceeded", "dailyLimitExceeded"} & set(razones):
        raise SinCupoYouTube(msg + " (cupo del dia agotado)")
    return msg


def _yt_sesion() -> str:
    """Token de acceso fresco, y la verificacion de que es del canal que corresponde.

    Se verifica el canal ANTES de subir nada porque una subida por API va al canal con
    el que se autorizo el token, sin preguntar. Si YT_TOKEN_JSON algun dia se cruza con
    el del diario (ya paso que los dos tokens convivan en el mismo .env), los policiales
    terminarian en el canal equivocado. Cuesta 1 unidad de cupo por pasada.
    """
    global _yt_acceso
    if _yt_acceso:
        return _yt_acceso
    try:
        info = json.loads(os.environ.get("YT_TOKEN_JSON") or "")
    except ValueError:
        raise FalloRed("YouTube: YT_TOKEN_JSON no es un JSON valido")
    try:
        r = _pedir("POST", info.get("token_uri") or "https://oauth2.googleapis.com/token", data={
            "client_id": info.get("client_id"), "client_secret": info.get("client_secret"),
            "refresh_token": info.get("refresh_token"), "grant_type": "refresh_token"})
    except _Cortado as e:
        raise FalloRed(f"YouTube (token): {e}")
    if r.status_code >= 400:
        raise FalloRed(_tapar(f"YouTube: no se pudo renovar el token — HTTP {r.status_code} "
                              f"{r.text[:200]}. Si dice invalid_grant, hay que re-autorizar."))
    acceso = r.json()["access_token"]
    _ocultar.append(acceso)

    esperado = os.environ.get("YT_CHANNEL_ID", "")
    try:
        c = _pedir("GET", f"{YT_API}/channels", acceso, params={"part": "id", "mine": "true"})
    except _Cortado as e:
        raise FalloRed(f"YouTube (canal): {e}")
    if c.status_code >= 400:
        raise FalloRed(_yt_error(c, "YouTube (canal)"))
    canales = [i.get("id") for i in (c.json() or {}).get("items") or []]
    if not esperado or esperado not in canales:
        raise FalloRed("YouTube: el token NO es del canal de Radio del Centro "
                       f"(YT_CHANNEL_ID). No se sube nada para no publicar en otro canal.")
    _yt_acceso = acceso
    return acceso


def _sin_angulos(texto: str) -> str:
    # YouTube rechaza el video entero si el titulo o la descripcion tienen < o >.
    return (texto or "").replace("<", "‹").replace(">", "›")


def metadatos_youtube(pieza: dict) -> dict:
    g = pieza.get("guion") or {}
    pueblo = _pueblo(pieza.get("localidad") or "")
    titulo = (g.get("titular") or "").strip()
    # La localidad en el titulo: en YouTube se busca por el nombre del pueblo, y el
    # titular muchas veces no lo dice porque la volanta ya lo decia en la placa.
    if pueblo and pueblo.lower() not in titulo.lower():
        titulo = f"{titulo} | {pueblo}"
    titulo = _sin_angulos(titulo)
    if len(titulo) > 100:                                   # tope duro de YouTube
        titulo = titulo[:99].rstrip() + "…"
    desc = _sin_angulos(texto_del_posteo(pieza, "youtube"))
    if "#shorts" not in desc.lower():
        desc = f"{desc}\n\n#Shorts"
    etiquetas, vistas = [], set()
    for t in re.findall(r"#(\w+)", desc) + [pueblo, "policiales", "Buenos Aires"]:
        if t and t.lower() not in vistas and t.lower() != "shorts":
            vistas.add(t.lower())
            etiquetas.append(t)
    while etiquetas and sum(len(t) + 1 for t in etiquetas) > 400:   # tope: 500 caracteres
        etiquetas.pop()
    return {
        "snippet": {"title": titulo, "description": desc[:5000], "tags": etiquetas,
                    "categoryId": YT_CATEGORIA, "defaultLanguage": "es",
                    "defaultAudioLanguage": "es"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                   "embeddable": True, "containsSyntheticMedia": False},
    }


def _yt_listo(v: dict) -> dict:
    vid = v["id"]
    privacidad = (v.get("status") or {}).get("privacyStatus")
    info = {"id": vid, "url": f"https://youtube.com/shorts/{vid}", "privacidad": privacidad}
    if privacidad and privacidad != "public":
        # Pasa si el proyecto de Google pierde la condicion que hoy deja subir publico.
        info["aviso"] = f"YouTube lo dejo {privacidad}, no publico"
    return info


def publicar_youtube(pieza: dict, mp4: Path) -> dict:
    """videos.insert con subida reanudable: se abre la sesion con los datos del video y
    despues se manda el archivo. El video recien EXISTE cuando termina la subida, asi
    que un corte en el medio se puede retomar sin riesgo de duplicarlo."""
    acceso = _yt_sesion()
    datos = mp4.read_bytes()
    n = len(datos)
    try:
        r = _pedir("POST", YT_UPLOAD, acceso,
                   params={"uploadType": "resumable", "part": "snippet,status"},
                   headers={"Content-Type": "application/json; charset=UTF-8",
                            "X-Upload-Content-Type": "video/mp4",
                            "X-Upload-Content-Length": str(n)},
                   content=json.dumps(metadatos_youtube(pieza)).encode("utf-8"))
    except _Cortado as e:
        raise FalloRed(f"YouTube (inicio): {e}")
    if r.status_code >= 400:
        raise FalloRed(_yt_error(r, "YouTube (inicio)"))
    sesion = r.headers.get("location") or ""
    if not sesion:
        raise FalloRed("YouTube (inicio): no devolvio la direccion de subida")

    desde, incompleto = 0, False
    for intento in range(4):
        if intento:
            _dormir(5 * intento)
            # Antes de mandar de nuevo, preguntar cuanto llego. Puede haber llegado todo
            # y haberse perdido solo la respuesta: ahi el video ya existe.
            try:
                st = _pedir("PUT", sesion, acceso, headers={"Content-Range": f"bytes */{n}"})
            except _Cortado:
                incompleto = False
                continue
            if st.status_code in (200, 201):
                return _yt_listo(st.json())
            if st.status_code != 308:
                raise FalloRed(_yt_error(st, "YouTube (estado de la subida)"))
            incompleto = True
            rango = st.headers.get("range") or ""          # "bytes=0-12345"
            desde = int(rango.rsplit("-", 1)[1]) + 1 if "-" in rango else 0
        cabeza = {"Content-Type": "video/mp4"}
        if desde:
            cabeza["Content-Range"] = f"bytes {desde}-{n - 1}/{n}"
        try:
            up = _pedir("PUT", sesion, acceso, headers=cabeza, content=datos[desde:])
        except _Cortado:
            continue
        if up.status_code in (200, 201):
            return _yt_listo(up.json())
        if up.status_code not in _HTTP_TRANSITORIO + (308,):
            raise FalloRed(_yt_error(up, "YouTube (subida)"))
    if incompleto:
        raise FalloRed("YouTube: la subida quedo incompleta despues de 4 intentos")
    raise SinConfirmar("YouTube: la subida se corto y no se pudo saber si termino")


# =============================================================================
# La tanda
# =============================================================================

def texto_del_posteo(pieza: dict, red: str) -> str:
    texto = (pieza.get("descripcion_tiktok") or "").strip()
    if red == "instagram" and len(texto) > MAX_CAPTION_IG:
        texto = texto[:MAX_CAPTION_IG - 1].rstrip() + "…"
    return texto


def _mp4(pieza: dict, carpeta: Path):
    archivo = ((pieza.get("video") or {}).get("archivo") or "")
    if not archivo:
        return None
    p = Path(archivo)
    if p.exists():
        return p
    # La ruta es de la maquina que armo el reel (puede ser una ruta de Windows leida en
    # Linux, o al reves): se busca el mismo archivo al lado del _lote.json.
    p = carpeta / re.split(r"[\\/]", archivo)[-1]
    return p if p.exists() else None


def elegibles(lote: dict, carpeta: Path) -> tuple:
    """(listas, salteadas): las piezas que se pueden publicar y las que no, con el motivo."""
    listas, salteadas = [], []
    for p in lote.get("piezas") or []:
        v = p.get("video") or {}
        motivo = ""
        if not p.get("apto_para_publicar"):
            motivo = "no apta: " + (p.get("por_que_no") or "sin motivo anotado")
        elif v.get("error"):
            motivo = "el video fallo al armarse"
        elif not texto_del_posteo(p, "facebook"):
            motivo = "no tiene texto para el posteo"
        elif not (DURACION_REEL[0] <= float(v.get("duracion") or 0) <= DURACION_REEL[1]):
            motivo = f"dura {v.get('duracion')} s (un reel va de {DURACION_REEL[0]} a {DURACION_REEL[1]})"
        mp4 = None if motivo else _mp4(p, carpeta)
        if not motivo and not mp4:
            motivo = "no esta el .mp4"
        if motivo:
            salteadas.append({"orden": p.get("orden"), "titular": (p.get("guion") or {}).get("titular"),
                              "motivo": motivo})
        else:
            listas.append((p, mp4))

    def _cuando(par):
        return (par[0].get("publicar_en") or "", par[0].get("orden") or 0)
    return sorted(listas, key=_cuando), salteadas


def _clave(pieza: dict) -> str:
    return pieza.get("url_original") or pieza.get("placa") or ""


def cargar_ledger() -> dict:
    if not LEDGER.exists():
        return {}
    try:
        d = json.loads(LEDGER.read_text(encoding="utf-8"))
    except ValueError as e:
        # Con la memoria rota no se sabe que ya salio: publicar igual puede duplicar
        # todo lo del dia. Mejor no publicar y que llegue el aviso.
        raise SystemExit(f"estado/publicados.json esta roto ({e}): no se publica nada.")
    corte = (_ahora() - timedelta(days=DIAS_LEDGER)).isoformat()
    return {k: v for k, v in d.items() if (v.get("ultimo") or "") >= corte}


def guardar_ledger(d: dict):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(LEDGER)


def faltantes(redes, publicar: bool) -> list:
    if not publicar:
        return []
    falta = []
    if "instagram" in redes:
        falta += [k for k in ("INSTAGRAM_USER_ID", "INSTAGRAM_ACCESS_TOKEN") if not os.environ.get(k)]
        if not _token_github():
            falta.append("GITHUB_TOKEN")
    if "facebook" in redes:
        falta += [k for k in ("FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN") if not os.environ.get(k)]
    if "youtube" in redes:
        falta += [k for k in ("YT_TOKEN_JSON", "YT_CHANNEL_ID") if not os.environ.get(k)]
    return falta


def _rechazar_tiktok(redes):
    """Defensa en profundidad: aunque alguien pida TikTok, no sale nada."""
    if "tiktok" in [r.lower() for r in redes] and not TIKTOK_ACTIVO:
        raise ValueError("TikTok esta DESACTIVADO hasta que TikTok apruebe el Direct Post: "
                         "no se publica ni se manda a borradores.")


def tope_youtube() -> int:
    try:
        return max(0, int(os.environ.get("YT_SHORTS_POR_DIA") or YT_SHORTS_POR_DIA_DEFAULT))
    except ValueError:
        return YT_SHORTS_POR_DIA_DEFAULT


def _youtube_de_hoy(ledger: dict) -> int:
    """Shorts de policiales ya subidos hoy (cuentan tambien los sin confirmar: pudieron
    haber gastado cupo)."""
    hoy = _ahora().date().isoformat()
    return sum(1 for e in ledger.values()
               if (e.get("youtube") or {}).get("estado") in ("ok", "sin_confirmar")
               and (e["youtube"].get("cuando") or "").startswith(hoy))


def _hora(texto):
    try:
        return datetime.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def _turno(pieza: dict, ultimo) -> datetime:
    """A que hora sale esta pieza: la agendada, pero nunca antes de ahora ni a menos de
    MINUTOS_ENTRE_POSTEOS de la anterior. La segunda condicion hace falta aunque el
    plan ya venga espaciado: si una pieza tarda en publicarse, la siguiente no puede
    salir pegada."""
    hora = max(_hora(pieza.get("publicar_en")) or _ahora(), _ahora())
    if ultimo:
        hora = max(hora, ultimo + timedelta(minutes=MINUTOS_ENTRE_POSTEOS))
    return hora


def _intentar(fn, *args) -> dict:
    """Una red nunca tumba a la otra: cualquier error queda anotado y se sigue."""
    try:
        return {"estado": "ok", **fn(*args)}
    except SinConfirmar as e:
        return {"estado": "sin_confirmar", "detalle": _tapar(e)}
    except SinCupoYouTube as e:
        return {"estado": "fallo", "detalle": _tapar(e), "sin_cupo": True}
    except FalloRed as e:
        return {"estado": "fallo", "detalle": _tapar(e)}
    except Exception as e:                    # un error de programacion tampoco
        return {"estado": "fallo", "detalle": _tapar(f"{type(e).__name__}: {e}")}


def _simular(red: str, pieza: dict, mp4: Path) -> dict:
    """Todo lo que se puede verificar sin publicar."""
    texto = texto_del_posteo(pieza, red)
    info = {"estado": "simulado", "kb": round(mp4.stat().st_size / 1024), "caracteres": len(texto)}
    if red == "instagram":
        params = IG.contenedor_reel("https://ejemplo.invalid/reel.mp4", texto)
        info["prueba"] = json.loads(params.get("trial_params") or "null")
    elif red == "youtube":
        info["titulo"] = metadatos_youtube(pieza)["snippet"]["title"]
    return info


def publicar_lote(carpeta: Path, redes=REDES, publicar: bool = False) -> dict:
    global _yt_acceso, _yt_sin_cupo
    _rechazar_tiktok(redes)
    # Y cualquier otra red que no este implementada, tambien antes de tocar nada.
    raras = [r for r in redes if r not in REDES]
    if raras:
        raise ValueError(f"redes desconocidas: {', '.join(raras)} (van: {', '.join(REDES)})")
    lote = json.loads((carpeta / "_lote.json").read_text(encoding="utf-8"))
    listas, salteadas = elegibles(lote, carpeta)
    ledger = cargar_ledger()
    informe = {"lote": carpeta.name, "modo": "publicar" if publicar else "simulacion",
               "redes": list(redes), "piezas": [], "salteadas": salteadas}
    _yt_acceso, _yt_sin_cupo = "", False
    yt_tope, yt_hoy, yt_pasada = tope_youtube(), _youtube_de_hoy(ledger), 0

    modo = "PUBLICANDO" if publicar else "SIMULACION — no se toca ninguna red"
    print(f"=== {modo} · lote {carpeta.name} · {len(listas)} pieza(s) · {', '.join(redes)} ===")
    if "youtube" in redes:
        print(f"  YouTube: tope {yt_tope} Short(s) por dia, ya subidos hoy {yt_hoy}")
    for s in salteadas:
        print(f"  salteada #{s['orden']}: {s['motivo']}")

    ultimo = None
    for pieza, mp4 in listas:
        clave = _clave(pieza)
        hecho = ledger.get(clave) or {}
        pendientes = [r for r in redes
                      if (hecho.get(r) or {}).get("estado") not in ("ok", "sin_confirmar")]
        g = pieza.get("guion") or {}
        pueblo = _pueblo(pieza.get("localidad") or "")
        fila = {"orden": pieza.get("orden"), "localidad": pueblo, "titular": g.get("titular")}

        # YouTube sin lugar hoy: se saca de esta pieza ANTES de decidir si hay que esperar
        # turno, para que una pieza que solo iba a YouTube no ocupe 5 minutos de la cola.
        # No se anota en la memoria: no es una falla, es el tope.
        sin_lugar = None
        if "youtube" in pendientes and (_yt_sin_cupo or yt_hoy + yt_pasada >= yt_tope):
            pendientes.remove("youtube")
            sin_lugar = {"estado": "cupo", "detalle":
                         "YouTube agoto su cupo en esta pasada" if _yt_sin_cupo else
                         f"ya van {yt_hoy + yt_pasada} Short(s) hoy (tope {yt_tope})"}

        if not pendientes:
            fila["resultado"] = "ya estaba publicada" if not sin_lugar else "solo faltaba YouTube"
            if sin_lugar:
                fila["youtube"] = sin_lugar
            informe["piezas"].append(fila)
            print(f"\n#{pieza.get('orden')} {pueblo} — {fila['resultado']}, se saltea")
            continue

        hora = _turno(pieza, ultimo)
        print(f"\n#{pieza.get('orden')} {hora:%H:%M} · {pueblo} — {g.get('titular')}")
        if publicar:
            falta = (hora - _ahora()).total_seconds()
            if falta > 0:
                print(f"  esperando {falta / 60:.1f} min (5 minutos entre posteos)…", flush=True)
                _dormir(falta)
            ultimo = _ahora()
        else:
            ultimo = hora
        fila["hora"] = ultimo.isoformat(timespec="minutes")

        for red in pendientes:
            if not publicar:
                res = _simular(red, pieza, mp4)
            elif red == "instagram":
                res = _intentar(publicar_instagram, pieza, mp4, f"{carpeta.name}_{mp4.name}")
            elif red == "facebook":
                res = _intentar(publicar_facebook, pieza, mp4)
            elif red == "youtube":
                res = _intentar(publicar_youtube, pieza, mp4)
                if res.pop("sin_cupo", False):
                    _yt_sin_cupo = True
            else:                                   # nunca un "else" que publique en algo
                raise ValueError(f"red sin implementar: {red}")
            if red == "youtube" and res.get("estado") in ("ok", "sin_confirmar", "simulado"):
                yt_pasada += 1
            fila[red] = res
            _mostrar(red, res)
            if publicar:
                res["cuando"] = _ahora().isoformat(timespec="seconds")
                e = ledger.setdefault(clave, {"titular": g.get("titular"), "localidad": pueblo})
                e[red] = res
                e["ultimo"] = res["cuando"]
                guardar_ledger(ledger)       # despues de CADA red: un corte no borra lo hecho
        if sin_lugar:
            fila["youtube"] = sin_lugar
            _mostrar("youtube", sin_lugar)
        informe["piezas"].append(fila)

    (carpeta / "_publicacion.json").write_text(
        json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    if publicar:
        salio = any((f.get(r) or {}).get("estado") == "ok" for f in informe["piezas"] for r in redes)
        if salio:
            lote["publicado"] = True
            lote["nota"] = "Publicado por reels.publicador: ver _publicacion.json."
            (carpeta / "_lote.json").write_text(json.dumps(lote, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
        if "instagram" in redes:
            # Los videos del Release ya no hacen falta pasadas las 24 h: Instagram
            # guarda su propia copia apenas procesa el contenedor.
            b = _barrer_release(1, repo=os.environ.get("GITHUB_REPOSITORY") or REPO,
                                tag=TAG_RELEASE, token=_token_github())
            if b.get("borrados"):
                print(f"\nRelease: {len(b['borrados'])} video(s) viejos borrados ({b['mb']} MB)")
    _resumen(informe)
    return informe


def _mostrar(red: str, res: dict):
    nombre = NOMBRE_RED[red]
    est = res.get("estado")
    if est == "simulado":
        if red == "instagram":
            extra = f" · reel de PRUEBA {res.get('prueba')}"
        elif red == "facebook":
            extra = " · reel NORMAL"
        else:
            extra = f" · Short publico en Radio del Centro: «{res.get('titulo')}»"
        print(f"  {nombre:<9} saldria{extra} · {res['kb']} KB · texto de {res['caracteres']} caracteres")
    elif est == "ok":
        aviso = f" ⚠ {res['aviso']}" if res.get("aviso") else ""
        print(f"  {nombre:<9} OK (id {res.get('id') or 'sin leer'}){aviso}")
    elif est == "cupo":
        print(f"  {nombre:<9} no va: {res.get('detalle')}")
    elif est == "sin_confirmar":
        print(f"  {nombre:<9} SIN CONFIRMAR — {res.get('detalle')}")
    else:
        print(f"  {nombre:<9} FALLO — {res.get('detalle')}")


def _resumen(informe: dict):
    """Cuenta final. Con fallas escribe informe_publicacion.md, que el workflow mete en
    el issue de aviso."""
    cuenta = {}
    for f in informe["piezas"]:
        for r in informe["redes"]:
            est = (f.get(r) or {}).get("estado")
            if est:
                cuenta[(r, est)] = cuenta.get((r, est), 0) + 1
    print("\n=== " + (" · ".join(f"{r} {e}: {n}" for (r, e), n in sorted(cuenta.items()))
                        or "nada para publicar en esta tanda") + " ===")

    malas = [(f, r) for f in informe["piezas"] for r in informe["redes"]
             if (f.get(r) or {}).get("estado") in ("fallo", "sin_confirmar")]
    lineas = [f"- **{r}** · #{f['orden']} {f.get('localidad')} — {f.get('titular')}: "
              f"{f[r]['estado']} — {f[r].get('detalle')}" for f, r in malas]
    if malas:
        (RAIZ / "informe_publicacion.md").write_text(
            "### Publicación en redes\n\n" + "\n".join(lineas) + "\n", encoding="utf-8")
    resumen_gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen_gh:
        with open(resumen_gh, "a", encoding="utf-8") as fh:
            fh.write(f"### Publicación ({informe['modo']})\n\n")
            for (r, e), n in sorted(cuenta.items()):
                fh.write(f"- {r}: {e} × {n}\n")
            fh.write("\n" + "\n".join(lineas) + "\n\n")


def main():
    ap = argparse.ArgumentParser(description="Publica una tanda de reels en Instagram (prueba), "
                                             "Facebook (normal) y YouTube (Short). Sin --publicar, simula.")
    ap.add_argument("--publicar", action="store_true",
                    help="publicar DE VERDAD. Sin esto no se toca ninguna red")
    ap.add_argument("--lote", help="carpeta de la tanda; por defecto, la ultima de salida_reels/")
    ap.add_argument("--redes", default=",".join(REDES),
                    help="instagram,facebook,youtube (default: las tres). TikTok esta desactivado")
    args = ap.parse_args()

    entorno.consola_utf8()
    entorno.cargar()
    redes = tuple(r.strip().lower() for r in args.redes.split(",") if r.strip())
    try:
        _rechazar_tiktok(redes)
    except ValueError as e:
        print(e)
        return 2
    raras = [r for r in redes if r not in REDES]
    if raras or not redes:
        print(f"Redes desconocidas: {', '.join(raras) or '(ninguna)'}. Van: {', '.join(REDES)}")
        return 2

    if args.lote:
        carpeta = Path(args.lote)
    else:
        lotes = sorted(p.parent for p in SALIDA_REELS.glob("*/_lote.json"))
        carpeta = lotes[-1] if lotes else None
    if not carpeta or not (carpeta / "_lote.json").exists():
        print("No hay tanda para publicar. Corré primero:  python -m reels.flujo --con-ia --cadencia")
        return 0

    falta = faltantes(redes, args.publicar)
    if falta:
        # Antes de tocar nada: sin esto la primera red podria salir y la segunda no.
        print(f"Faltan credenciales: {', '.join(falta)}. No se publica nada.")
        return 2

    informe = publicar_lote(carpeta, redes, args.publicar)
    malas = [1 for f in informe["piezas"] for r in redes
             if (f.get(r) or {}).get("estado") in ("fallo", "sin_confirmar")]
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
