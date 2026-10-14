# -*- coding: utf-8 -*-
"""Verifica que la cuenta AGRO (@diarioyradioagro) quede bien enganchada a la API de Meta.

SOLO LEE: no publica, no crea contenedores, no cambia nada en las cuentas.

Que comprueba, con las variables AGRO_* del .env:
  - el token: que sea valido, de la app "diario", de tipo PAGE, con los permisos de
    publicar, y hasta cuando dura (y el acceso a datos, que vence aparte);
  - la pagina: cual es de verdad (la saca del token, no de lo que diga el .env), su
    usuario, y que tenga un Instagram profesional vinculado;
  - el Instagram: su usuario y que la API lo deje publicar (content_publishing_limit);
  - la SALVAGUARDA: que nada de eso sea @diarioyradio. Las credenciales agro van
    aparte justamente para que una noticia agro no pueda salir en la cuenta del diario.

Uso:
    venv\\Scripts\\python.exe tools\\verificar_cuenta_agro.py
    venv\\Scripts\\python.exe tools\\verificar_cuenta_agro.py --guardar-ids
    venv\\Scripts\\python.exe tools\\verificar_cuenta_agro.py --principal

--guardar-ids  anota en el .env AGRO_FACEBOOK_PAGE_ID y AGRO_INSTAGRAM_USER_ID si
               estan vacios (los IDs no son secretos; los tokens no se tocan).
--principal    corre los mismos chequeos sobre la cuenta del diario (FACEBOOK_*): tiene
               que FALLAR. Sirve para probar que la salvaguarda funciona.

Nunca imprime un token: los valores se tapan en cualquier mensaje.
"""
import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import entorno  # noqa: E402

GRAPH = "https://graph.facebook.com/v26.0"
APP_DIARIO = "983887861017378"
# La cuenta del diario (@diarioyradio). Fijas a proposito: aunque el .env se mezcle,
# estos IDs nunca pueden pasar como cuenta agro.
PRINCIPAL_PAGINA = "1456376377985890"
PRINCIPAL_IG = "17841405971293744"
PERMISOS = ("pages_show_list", "pages_read_engagement", "pages_manage_posts",
            "instagram_basic", "instagram_content_publish", "business_management")
USUARIO_DEFECTO = "diarioyradioagro"
DIAS_AVISO = 30

OK, FALLA, AVISO = "ok", "falla", "aviso"
MARCA = {OK: "✅", FALLA: "❌", AVISO: "⚠️ "}


def _tapar(texto, secretos):
    texto = str(texto)
    for s in secretos:
        if s and len(s) > 8:
            texto = texto.replace(s, "***")
    return texto


def _pedidor(secretos):
    """Un GET a la Graph API con el token en el ENCABEZADO (nunca en la URL)."""
    import httpx
    cliente = httpx.Client(timeout=30)

    def pedir(ruta, token, **params):
        try:
            r = cliente.get(f"{GRAPH}/{ruta}", params=params,
                            headers={"Authorization": f"Bearer {token}"})
            datos = r.json()
        except Exception as e:  # noqa: BLE001 — se informa y se sigue
            return {"error": {"message": _tapar(f"{type(e).__name__}: {e}", secretos)}}
        if isinstance(datos, dict) and "error" in datos:
            err = datos["error"] or {}
            datos["error"] = {"message": _tapar(err.get("message", ""), secretos),
                              "code": err.get("code")}
        return datos
    return pedir


def credenciales(principal=False):
    """Las cuatro variables de la cuenta a revisar. El token de IG cae al de la pagina:
    con un token de pagina tambien se opera el Instagram vinculado."""
    p = "" if principal else "AGRO_"
    page_tok = os.environ.get(f"{p}FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    return {
        "page_id": os.environ.get(f"{p}FACEBOOK_PAGE_ID", "").strip(),
        "page_tok": page_tok,
        "ig_id": os.environ.get(f"{p}INSTAGRAM_USER_ID", "").strip(),
        "ig_tok": os.environ.get(f"{p}INSTAGRAM_ACCESS_TOKEN", "").strip() or page_tok,
        "ig_tok_propio": bool(os.environ.get(f"{p}INSTAGRAM_ACCESS_TOKEN", "").strip()),
    }


def relevar(pedir, cred):
    """Junta todo lo que hace falta saber, con pedidos de solo lectura."""
    d = {}
    tok = cred["page_tok"]
    if not tok:
        return d
    d["debug"] = pedir("debug_token", tok, input_token=tok).get("data") or {}
    # Con un token de pagina, /me ES la pagina: asi se sabe cual es de verdad.
    d["me"] = pedir("me", tok, fields="id,name,username,link,followers_count,"
                                      "instagram_business_account{id,username}")
    pid = cred["page_id"] or (d["me"] or {}).get("id", "")
    if pid and pid != (d["me"] or {}).get("id"):
        d["pagina"] = pedir(pid, tok, fields="id,name,username,link,"
                                             "instagram_business_account{id,username}")
    else:
        d["pagina"] = d["me"]
    ig = ((d["pagina"] or {}).get("instagram_business_account") or {}).get("id", "")
    ig_id = cred["ig_id"] or ig
    if ig_id:
        d["ig"] = pedir(ig_id, cred["ig_tok"], fields="id,username,name,followers_count,media_count")
        d["limite"] = pedir(f"{ig_id}/content_publishing_limit", cred["ig_tok"],
                            fields="config,quota_usage")
        if cred["ig_tok_propio"] and cred["ig_tok"] != tok:
            d["debug_ig"] = pedir("debug_token", cred["ig_tok"],
                                  input_token=cred["ig_tok"]).get("data") or {}
    return d


def _fecha(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def _revisar_token(dbg, nombre, ahora):
    res = []
    if not dbg:
        return [(FALLA, f"{nombre}: Meta no lo pudo leer (¿token mal copiado?)")]
    if not dbg.get("is_valid"):
        msg = ((dbg.get("error") or {}).get("message") or "sin detalle")
        return [(FALLA, f"{nombre}: NO es valido — {msg}")]
    res.append((OK, f"{nombre}: valido"))
    app = str(dbg.get("app_id", ""))
    res.append((OK, f"{nombre}: de la app «diario» ({app})") if app == APP_DIARIO else
               (FALLA, f"{nombre}: es de otra app ({app or '?'}), no de «diario» ({APP_DIARIO})"))
    tipo = (dbg.get("type") or "").upper()
    res.append((OK, f"{nombre}: tipo PAGE") if tipo == "PAGE" else
               (FALLA, f"{nombre}: es tipo {tipo or '?'}; tiene que ser de PAGINA "
                       "(Graph API Explorer → «Get Page Access Token»)"))
    faltan = [p for p in PERMISOS if p not in (dbg.get("scopes") or [])]
    res.append((OK, f"{nombre}: tiene los {len(PERMISOS)} permisos") if not faltan else
               (FALLA, f"{nombre}: faltan permisos: {', '.join(faltan)}"))
    vence = _fecha(dbg.get("expires_at"))
    if vence is None:
        res.append((OK, f"{nombre}: no vence"))
    else:
        dias = (vence - ahora).days
        res.append((AVISO if dias > DIAS_AVISO else FALLA,
                    f"{nombre}: vence el {vence:%d/%m/%Y} (en {dias} dias) — "
                    "conviene extenderlo o usar un System User"))
    datos = _fecha(dbg.get("data_access_expires_at"))
    if datos:
        dias = (datos - ahora).days
        res.append((OK if dias > DIAS_AVISO else AVISO,
                    f"{nombre}: acceso a datos hasta el {datos:%d/%m/%Y} (en {dias} dias)"))
    return res


def evaluar(cred, d, principal_env=None, usuario=USUARIO_DEFECTO, ahora=None):
    """[(estado, texto)]. Funcion pura: no hace pedidos, se prueba sin red."""
    ahora = ahora or datetime.now(timezone.utc)
    principal_env = principal_env or {}
    paginas_diario = {PRINCIPAL_PAGINA, principal_env.get("page_id", "")} - {""}
    igs_diario = {PRINCIPAL_IG, principal_env.get("ig_id", "")} - {""}
    res = []

    if not cred["page_tok"]:
        return [(FALLA, "Falta AGRO_FACEBOOK_PAGE_ACCESS_TOKEN en el .env "
                        "(cargalo con tools/cargar_credenciales.py)")]
    toks_diario = {principal_env.get("page_tok", ""), principal_env.get("ig_tok", "")} - {""}
    if cred["page_tok"] in toks_diario or (cred["ig_tok_propio"] and cred["ig_tok"] in toks_diario):
        res.append((FALLA, "SALVAGUARDA: el token agro es EL MISMO que el de @diarioyradio"))

    res += _revisar_token(d.get("debug"), "Token de la pagina", ahora)
    if d.get("debug_ig"):
        res += _revisar_token(d["debug_ig"], "Token de Instagram", ahora)

    # --- Pagina
    me = d.get("me") or {}
    pag = d.get("pagina") or {}
    if "error" in me:
        res.append((FALLA, f"No se pudo leer la pagina del token: {me['error'].get('message')}"))
        return res
    pid_real = str(me.get("id") or (d.get("debug") or {}).get("profile_id") or "")
    res.append((OK, f"El token es de la pagina «{me.get('name', '?')}» ({pid_real})"))
    if pid_real in paginas_diario:
        res.append((FALLA, "SALVAGUARDA: esa pagina es la del DIARIO (@diarioyradio), no la agro"))
    if cred["page_id"] and cred["page_id"] != pid_real:
        res.append((FALLA, f"AGRO_FACEBOOK_PAGE_ID ({cred['page_id']}) no coincide con la "
                           f"pagina del token ({pid_real})"))
    elif not cred["page_id"]:
        res.append((AVISO, "AGRO_FACEBOOK_PAGE_ID vacio: correr con --guardar-ids"))
    user_pag = (pag.get("username") or me.get("username") or "").lower()
    if user_pag == usuario:
        res.append((OK, f"Usuario de la pagina: @{user_pag}"))
    else:
        res.append((AVISO, f"Usuario de la pagina: @{user_pag or '(sin usuario)'} — todavia no "
                           f"es @{usuario} (¿falta renombrarla o aprobar el cambio?)"))
    if me.get("followers_count") is not None:
        res.append((OK, f"Seguidores de la pagina: {me['followers_count']}"))

    # --- Instagram
    vinculado = (pag.get("instagram_business_account") or {})
    if not vinculado.get("id"):
        res.append((FALLA, "La pagina NO tiene un Instagram profesional vinculado "
                           "(Configuracion de la pagina → Cuentas vinculadas)"))
    ig = d.get("ig") or {}
    if not ig:
        return res
    if "error" in ig:
        res.append((FALLA, f"No se pudo leer el Instagram: {ig['error'].get('message')}"))
        return res
    ig_real = str(ig.get("id", ""))
    if ig_real in igs_diario:
        res.append((FALLA, "SALVAGUARDA: ese Instagram es el del DIARIO (@diarioyradio)"))
    if vinculado.get("id") and vinculado["id"] != ig_real:
        res.append((FALLA, f"AGRO_INSTAGRAM_USER_ID ({ig_real}) no es el Instagram vinculado "
                           f"a la pagina ({vinculado['id']})"))
    elif vinculado.get("id"):
        res.append((OK, f"Instagram vinculado a la pagina: {ig_real} (cuenta profesional)"))
    if not cred["ig_id"]:
        res.append((AVISO, "AGRO_INSTAGRAM_USER_ID vacio: correr con --guardar-ids"))
    user_ig = (ig.get("username") or "").lower()
    if user_ig == usuario:
        res.append((OK, f"Usuario de Instagram: @{user_ig}"))
    else:
        res.append((AVISO, f"Usuario de Instagram: @{user_ig or '?'} — todavia no es @{usuario}"))
    if ig.get("followers_count") is not None:
        res.append((OK, f"Seguidores en Instagram: {ig['followers_count']} · "
                        f"publicaciones: {ig.get('media_count', '?')}"))

    lim = d.get("limite") or {}
    if "error" in lim:
        res.append((FALLA, "La API no deja consultar el cupo de publicacion de Instagram: "
                           f"{lim['error'].get('message')}"))
    elif lim.get("data"):
        fila = lim["data"][0]
        tope = (fila.get("config") or {}).get("quota_total", "?")
        res.append((OK, f"Instagram habilitado para publicar por API "
                        f"(usado {fila.get('quota_usage', 0)} de {tope} en 24 h)"))
    return res


def guardar_ids(page_id, ig_id, ruta=None):
    """Completa los IDs vacios en el .env, sin tocar ninguna otra linea."""
    ruta = ruta or os.path.join(RAIZ, ".env")
    nuevos = {"AGRO_FACEBOOK_PAGE_ID": page_id, "AGRO_INSTAGRAM_USER_ID": ig_id}
    nuevos = {k: v for k, v in nuevos.items() if v}
    with open(ruta, encoding="utf-8") as f:
        lineas = f.read().split("\n")
    vistas, puestas = set(), []
    for i, linea in enumerate(lineas):
        k, _, v = linea.strip().partition("=")
        if k.strip() in nuevos:
            vistas.add(k.strip())
            if not v.strip():
                lineas[i] = f"{k.strip()}={nuevos[k.strip()]}"
                puestas.append(k.strip())
    for k in nuevos:
        if k not in vistas:
            lineas.append(f"{k}={nuevos[k]}")
            puestas.append(k)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    return puestas


def main():
    entorno.consola_utf8()
    entorno.cargar()
    principal = "--principal" in sys.argv
    usuario = (os.environ.get("AGRO_USUARIO_ESPERADO") or USUARIO_DEFECTO).lstrip("@").lower()
    cred = credenciales(principal)
    diario = credenciales(principal=True)
    secretos = [cred["page_tok"], cred["ig_tok"], diario["page_tok"], diario["ig_tok"]]

    print(f"Cuenta revisada: {'DIARIO (prueba de la salvaguarda)' if principal else 'AGRO'}"
          f" · usuario esperado @{usuario}\n")
    datos = relevar(_pedidor(secretos), cred) if cred["page_tok"] else {}
    # Con --principal la cuenta revisada ES la del diario: la salvaguarda tiene que saltar.
    resultado = evaluar(cred, datos, principal_env={} if principal else diario, usuario=usuario)
    for estado, texto in resultado:
        print(f"  {MARCA[estado]} {_tapar(texto, secretos)}")

    fallas = [t for e, t in resultado if e == FALLA]
    avisos = [t for e, t in resultado if e == AVISO]
    print()
    if fallas:
        print(f"❌ NO lista para publicar por API: {len(fallas)} problema(s).")
    elif avisos:
        print(f"✅ Enganchada a la API, con {len(avisos)} aviso(s) para revisar.")
    else:
        print("✅ Lista para publicar por API (no se publico nada).")

    if "--guardar-ids" in sys.argv and not principal and not fallas:
        pid = str((datos.get("me") or {}).get("id") or "")
        igid = str((datos.get("ig") or {}).get("id") or "")
        puestas = guardar_ids(pid if not cred["page_id"] else "", igid if not cred["ig_id"] else "")
        print("IDs anotados en .env: " + (", ".join(puestas) if puestas else "ninguno (ya estaban)"))
    elif "--guardar-ids" in sys.argv:
        print("No se anotaron IDs: primero hay que resolver los problemas.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
