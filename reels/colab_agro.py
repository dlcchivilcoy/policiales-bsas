"""Lo del campo que publica @diarioyradio sale también como COLABORACIÓN con @diarioyradioagro.

Pedido del editor (27/10/2026): «las notas relacionadas al campo, ya sean del bot, carruseles del diario,
policiales o lo que fuese, subirlas también como colaboración a @diarioyradioagro». Es el mismo criterio
que social_publisher/utils/colab_agro.py (el bot y el carrusel del diario); acá lo usan policiales y
nacionales (reels/publicador.publicar_instagram y nacionales/pasada).

Instagram: el contenedor del reel, carrusel o foto lleva `collaborators=["diarioyradioagro"]` y, al salir,
la cuenta de agro ACEPTA la invitación (`/collaboration_invites`, API de dic-2025). Si no se puede al
momento, la corrida de agro barre las invitaciones pendientes de @diarioyradio (`aceptar_pendientes`).
Las historias no admiten colab.

¿Qué es «del campo»? El diccionario de la sección Agro de la web (social_publisher/utils/secciones.py,
_CAMPO_FUERTE) sin las palabras que también viven fuera del agro («productora» de música, «rendimiento»
escolar, «cultivo» de marihuana, «hectárea», «chacra», «sembrar», «faena»). Una firme alcanza: el texto
del posteo es corto (titular + bajada).

COLAB_AGRO=0 lo apaga.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata

CUENTA_AGRO = "diarioyradioagro"
CUENTA_DIARIO = "diarioyradio"
DIARIO_IG = "17841405971293744"
ESPERAS_ACEPTAR = (5, 10, 20, 30, 60)

# Copia de social_publisher/utils/secciones._CAMPO_FUERTE sin las ambiguas. «xxx-» = por prefijo.
FIRMES = (
    "agropecuari-", "agroindustri-", "agricultura", "agricol-", "ganader-", "soja",
    "maiz", "trigo", "girasol", "cebada", "sorgo", "cosecha-", "cosechador-",
    "siembra", "retenciones", "senasa", "carbap", "inta",
    "sociedad rural", "asociacion rural", "expo rural", "exposicion rural",
    "bovino-", "vacuno-", "rodeo-", "tambo-", "forraj-", "silaje",
    "mercado de hacienda", "remate de hacienda", "remate ganadero", "abigeato",
    "silobolsa", "fitosanitari-", "agroquimic-", "maleza-", "apicultura", "colmena-",
    "cerealera-", "acopiador-", "campana gruesa", "campana fina", "caminos rurales",
    "escuela agraria", "emergencia agropecuaria", "frigorific-", "lecheria",
    "pulverizacion", "genetica animal",
)


def activo() -> bool:
    return (os.environ.get("COLAB_AGRO") or "1").strip().lower() not in ("0", "false", "no", "off")


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _hay(texto: str, terminos) -> list:
    out = []
    for t in terminos:
        raiz = t[:-1] if t.endswith("-") else t
        fin = "" if t.endswith("-") else r"(?![a-z0-9])"
        if re.search(rf"(?<![a-z0-9]){re.escape(raiz)}{fin}", texto):
            out.append(t)
    return out


def es_del_campo(texto: str) -> bool:
    return bool(_hay(_norm(texto), FIRMES))


def colaborador_para(texto: str, uid: str) -> str:
    """«diarioyradioagro» si este posteo de @diarioyradio es del campo; "" si no corresponde (otra cuenta,
    apagado o no es del campo)."""
    if not activo() or (uid or "").strip() != (os.environ.get("DIARIO_IG_ID") or DIARIO_IG):
        return ""
    return CUENTA_AGRO if es_del_campo(texto) else ""


def con_colab(params: dict, colaborador: str) -> dict:
    return dict(params, collaborators=json.dumps([colaborador])) if colaborador else params


def contenedor(crear, params: dict, colaborador: str, log=print) -> tuple:
    """(id, colaborador que quedó): primero con la colab y, si Instagram no la toma, sin ella."""
    if not colaborador:
        return crear(params), ""
    from reels import publicador as PB
    try:
        return crear(con_colab(params, colaborador)), colaborador
    except PB.FalloRed as e:
        log(f"  (Instagram no tomó la colab con @{colaborador}: {str(e)[:140]}; sale sin colab)")
        return crear(params), ""


def _agro() -> tuple:
    """(uid, token) de @diarioyradioagro, o ("", "") si en esta corrida no están."""
    try:
        from agro import publicar as PUB
        c = PUB.credenciales()
        return c["INSTAGRAM_USER_ID"], c["INSTAGRAM_ACCESS_TOKEN"]
    except Exception:  # noqa: BLE001 — SalvaguardaAgro o faltan las AGRO_*
        return "", ""


def aceptar(media_id: str, log=print, esperas=ESPERAS_ACEPTAR) -> str:
    """Con la cuenta de agro acepta la invitación en `media_id`. Nunca lanza: "aceptada", "pendiente" o
    "sin credenciales" (queda para el barrido de la corrida de agro)."""
    from reels import publicador as PB
    uid, tok = _agro()
    if not (uid and tok and media_id):
        log("  colab agro: sin las claves de agro en esta corrida; la acepta la corrida de agro")
        return "sin credenciales"
    ultimo = ""
    for espera in (0,) + tuple(esperas):
        if espera:
            PB._dormir(espera)
        try:
            r = PB._pedir("GET", f"{PB.GRAPH}/{uid}/collaboration_invites", tok)
        except Exception as e:  # noqa: BLE001
            ultimo = type(e).__name__
            continue
        if r.status_code >= 400:
            ultimo = PB._error(r, "invitaciones de colab")
            continue
        ids = {str(x.get("media_id") or "") for x in (r.json() or {}).get("data") or []}
        if str(media_id) not in ids:
            ultimo = "la invitación todavía no aparece"
            continue
        r = PB._pedir("POST", f"{PB.GRAPH}/{uid}/collaboration_invites", tok,
                      data={"media_id": str(media_id), "accept": "true"})
        if r.status_code < 400 and (r.json() or {}).get("success", True):
            log(f"  colab: @{CUENTA_AGRO} aceptó")
            return "aceptada"
        ultimo = PB._error(r, "aceptar la colab")
    log(f"  colab: no se pudo aceptar al momento ({ultimo}); la acepta la corrida de agro")
    return "pendiente"


def aceptar_pendientes(log=print) -> int:
    """Barrido (corrida de agro): acepta las invitaciones a colaborar que mandó @diarioyradio. Las de
    OTRAS cuentas no se tocan (en la cuenta quedan invitaciones viejas de cuando era @radiodelcentro).
    Devuelve cuántas aceptó; nunca lanza."""
    if not activo():
        return 0
    from reels import publicador as PB
    uid, tok = _agro()
    if not (uid and tok):
        return 0
    try:
        r = PB._pedir("GET", f"{PB.GRAPH}/{uid}/collaboration_invites", tok)
        if r.status_code >= 400:
            log(f"   colab: no pude leer las invitaciones ({PB._error(r, 'invitaciones')})")
            return 0
        n = 0
        for inv in (r.json() or {}).get("data") or []:
            if (inv.get("media_owner_username") or "").lower() != CUENTA_DIARIO:
                continue
            a = PB._pedir("POST", f"{PB.GRAPH}/{uid}/collaboration_invites", tok,
                          data={"media_id": str(inv.get("media_id")), "accept": "true"})
            if a.status_code < 400:
                n += 1
                log(f"   colab: aceptada la de @{CUENTA_DIARIO} «{(inv.get('caption') or '')[:60]}»")
            time.sleep(1)
        return n
    except Exception as e:  # noqa: BLE001
        log(f"   colab: el barrido falló ({type(e).__name__}: {str(e)[:120]})")
        return 0
