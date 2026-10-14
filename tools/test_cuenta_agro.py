# -*- coding: utf-8 -*-
"""Verificador de la cuenta agro @diarioyradioagro (13/10/2026). Sin red: la Graph API es de mentira."""
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from tools import verificar_cuenta_agro as V  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


AHORA = datetime(2026, 10, 13, tzinfo=timezone.utc)
EN_90_DIAS = int(datetime(2027, 1, 11, tzinfo=timezone.utc).timestamp())
PAG, IG = "101271341650483", "17841427698320458"
TOK = "EAAtokenagro1234567890"


def graph(pagina=PAG, ig=IG, usuario="diarioyradioagro", tipo="PAGE", app=V.APP_DIARIO,
          scopes=V.PERMISOS, vinculado=True, limite_ok=True):
    """Una Graph API de mentira con la forma de las respuestas de verdad."""
    pedidos = []

    def pedir(ruta, token, **params):
        pedidos.append((ruta, token, params))
        if ruta == "debug_token":
            return {"data": {"is_valid": True, "app_id": app, "type": tipo, "scopes": list(scopes),
                             "expires_at": 0, "data_access_expires_at": EN_90_DIAS,
                             "profile_id": pagina}}
        if ruta in ("me", pagina):
            d = {"id": pagina, "name": "Diario y Radio Agro", "username": usuario,
                 "followers_count": 1200}
            if vinculado:
                d["instagram_business_account"] = {"id": ig, "username": usuario}
            return d
        if ruta == ig:
            return {"id": ig, "username": usuario, "followers_count": 3400, "media_count": 210}
        if ruta == f"{ig}/content_publishing_limit":
            if not limite_ok:
                return {"error": {"message": "Unsupported get request"}}
            return {"data": [{"quota_usage": 0, "config": {"quota_total": 100}}]}
        return {"error": {"message": f"ruta inesperada {ruta}"}}
    return pedir, pedidos


def cred(page_id=PAG, ig_id=IG, tok=TOK):
    return {"page_id": page_id, "page_tok": tok, "ig_id": ig_id, "ig_tok": tok, "ig_tok_propio": False}


DIARIO = {"page_id": V.PRINCIPAL_PAGINA, "page_tok": "EAAtokendeldiario99999", "ig_id": V.PRINCIPAL_IG,
          "ig_tok": "EAAtokendeldiario99999", "ig_tok_propio": True}


def estados(res):
    return [e for e, _ in res]


def textos(res):
    return " | ".join(t for _, t in res)


# --- Todo bien
pedir, pedidos = graph()
res = V.evaluar(cred(), V.relevar(pedir, cred()), DIARIO, ahora=AHORA)
chequear("cuenta agro bien armada: sin fallas ni avisos", estados(res) and set(estados(res)) == {V.OK})
chequear("todos los pedidos son de lectura conocida (debug, me, ig, cupo)",
         {p[0] for p in pedidos} == {"debug_token", "me", IG, f"{IG}/content_publishing_limit"})
chequear("informa el cupo de publicación", "usado 0 de 100" in textos(res))

# --- Salvaguarda: la cuenta del diario nunca pasa por agro
pedir, _ = graph(pagina=V.PRINCIPAL_PAGINA, ig=V.PRINCIPAL_IG, usuario="diarioyradio")
c = cred(page_id="", ig_id="")
res = V.evaluar(c, V.relevar(pedir, c), DIARIO, ahora=AHORA)
chequear("token de la página del diario: salta la salvaguarda de página",
         any(e == V.FALLA and "DIARIO" in t and "pagina" in t for e, t in res))
chequear("…y la de Instagram", any(e == V.FALLA and "DIARIO" in t and "Instagram" in t for e, t in res))
c = cred(tok=DIARIO["page_tok"])
pedir, _ = graph()
res = V.evaluar(c, V.relevar(pedir, c), DIARIO, ahora=AHORA)
chequear("mismo token que @diarioyradio: falla aunque la página parezca agro",
         any(e == V.FALLA and "MISMO" in t for e, t in res))

# --- Problemas típicos de un token mal sacado
pedir, _ = graph(tipo="USER")
res = V.evaluar(cred(), V.relevar(pedir, cred()), DIARIO, ahora=AHORA)
chequear("token de usuario (no de página): falla", any(e == V.FALLA and "PAGINA" in t for e, t in res))
pedir, _ = graph(app="111")
res = V.evaluar(cred(), V.relevar(pedir, cred()), DIARIO, ahora=AHORA)
chequear("token de otra app: falla", any(e == V.FALLA and "otra app" in t for e, t in res))
pedir, _ = graph(scopes=V.PERMISOS[:3])
res = V.evaluar(cred(), V.relevar(pedir, cred()), DIARIO, ahora=AHORA)
chequear("faltan permisos de Instagram: falla y los nombra",
         any(e == V.FALLA and "instagram_content_publish" in t for e, t in res))
pedir, _ = graph(vinculado=False)
c = cred(ig_id="")
res = V.evaluar(c, V.relevar(pedir, c), DIARIO, ahora=AHORA)
chequear("página sin Instagram vinculado: falla", any(e == V.FALLA and "vinculado" in t for e, t in res))
pedir, _ = graph()
res = V.evaluar(cred(page_id="999"), V.relevar(pedir, cred(page_id="999")), DIARIO, ahora=AHORA)
chequear("ID de página del .env distinto al del token: falla", any(e == V.FALLA and "no coincide" in t for e, t in res))
pedir, _ = graph(limite_ok=False)
res = V.evaluar(cred(), V.relevar(pedir, cred()), DIARIO, ahora=AHORA)
chequear("sin acceso al cupo de publicación: falla", any(e == V.FALLA and "cupo" in t for e, t in res))

# --- Antes de renombrar: avisa, no falla
pedir, _ = graph(usuario="radiodelcentro")
res = V.evaluar(cred(), V.relevar(pedir, cred()), DIARIO, ahora=AHORA)
chequear("todavía @radiodelcentro: aviso (no falla)",
         V.FALLA not in estados(res) and any(e == V.AVISO and "radiodelcentro" in t for e, t in res))
chequear("sin token: una sola falla que dice qué cargar",
         V.evaluar(cred(tok=""), {}, DIARIO) == [(V.FALLA, V.evaluar(cred(tok=""), {}, DIARIO)[0][1])]
         and "AGRO_FACEBOOK_PAGE_ACCESS_TOKEN" in V.evaluar(cred(tok=""), {}, DIARIO)[0][1])

# --- IDs vacíos: se completan solos y sin tocar el resto del .env
pedir, _ = graph()
c = cred(page_id="", ig_id="")
res = V.evaluar(c, V.relevar(pedir, c), DIARIO, ahora=AHORA)
chequear("IDs vacíos: se deducen del token (aviso para guardarlos)",
         V.FALLA not in estados(res) and sum("--guardar-ids" in t for _, t in res) == 2)
with tempfile.TemporaryDirectory() as tmp:
    ruta = os.path.join(tmp, ".env")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# comentario\nFACEBOOK_PAGE_ID=123\nAGRO_FACEBOOK_PAGE_ID=\nAGRO_FACEBOOK_PAGE_ACCESS_TOKEN=x\n")
    puestas = V.guardar_ids(PAG, IG, ruta)
    txt = open(ruta, encoding="utf-8").read()
    chequear("guardar_ids completa el vacío y agrega el que falta",
             set(puestas) == {"AGRO_FACEBOOK_PAGE_ID", "AGRO_INSTAGRAM_USER_ID"}
             and f"AGRO_FACEBOOK_PAGE_ID={PAG}" in txt and f"AGRO_INSTAGRAM_USER_ID={IG}" in txt
             and "# comentario" in txt and "FACEBOOK_PAGE_ID=123" in txt and "ACCESS_TOKEN=x" in txt)

chequear("_tapar esconde los tokens", V._tapar(f"error con {TOK}", [TOK]) == "error con ***")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
