# -*- coding: utf-8 -*-
"""REELS DE PRUEBA del Archivo Literario y la PREGUNTA DEL DÍA (Instagram, 2 por día).

    venv\\Scripts\\python.exe -m archivo.pasada --tipo efemeride               # SIMULA (arma, no publica)
    venv\\Scripts\\python.exe -m archivo.pasada --tipo pregunta --publicar

Pedido del editor (10/10/2026): «2 reels de prueba por día en 2 pasadas en el mejor horario … Uno tiene
que ser sobre efemérides/personajes/curiosidades sobre Chivilcoy, y el otro autogenerado con imagen y texto
que genere preguntas a la gente … utilizar mi estética y logos e info». Decidió también: imagen de la
pregunta con Cloudflare gratis, SIN nombrar la fuente y graduación automática (SS_PERFORMANCE).

Horarios (elegidos con los `online_followers` de @diarioyradio, picos 12-13 y 19-22, y lejos de las
pasadas de policiales de 12:05 y 21:05):
- 13:30 → efeméride de HOY del Archivo («Un día como hoy…»); si hoy no hay, un personaje o una curiosidad.
- 20:30 → la pregunta del día.

Cada pieza: guion con la IA → foto (la del post dedicado del Archivo; la de Cloudflare para la pregunta; la
placa propia si no hay) → reel con el motor del bot (estilo corresponsal, marca e isologo) → Instagram como
REEL DE PRUEBA (`trial_params`, lo ven primero los que no siguen la cuenta y, si anda, pasa solo al feed).
Una por tipo por día: la memoria (estado/archivo.json) frena a la corrida de respaldo.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import entorno  # noqa: E402
from archivo import elegir as E  # noqa: E402
from archivo import fuente as F  # noqa: E402
from archivo import guion as AG  # noqa: E402
from archivo import imagen as IM  # noqa: E402
from archivo import preguntas as PR  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
MEMORIA = RAIZ / "estado" / "archivo.json"
SALIDA = RAIZ / "salida_archivo"
TZ_AR = timezone(timedelta(hours=-3))
TIPOS = ("efemeride", "pregunta")
DIAS_USADOS = 400
DIAS_PUBLICACIONES = 30
PREGUNTAS_GUARDADAS = 200
INTENTOS_POR_DIA = 3        # publicaciones fallidas del mismo tipo en el día antes de rendirse
EXITO = ("ok", "sin_confirmar")


class PasadaError(Exception):
    pass


def _ahora() -> datetime:
    return datetime.now(TZ_AR)


# =============================================================================
# Memoria
# =============================================================================

def cargar() -> dict:
    try:
        d = json.loads(MEMORIA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d.setdefault("usados", {})
    d.setdefault("preguntas", [])
    d.setdefault("publicaciones", {})
    return d


def guardar(mem: dict, ahora: datetime = None):
    ahora = ahora or _ahora()
    limite = (ahora - timedelta(days=DIAS_USADOS)).date().isoformat()
    mem["usados"] = {k: v for k, v in mem["usados"].items() if (v or "") >= limite}
    mem["preguntas"] = mem["preguntas"][-PREGUNTAS_GUARDADAS:]
    limite = (ahora - timedelta(days=DIAS_PUBLICACIONES)).date().isoformat()
    mem["publicaciones"] = {k: v for k, v in mem["publicaciones"].items() if k[:10] >= limite}
    mem["actualizado"] = ahora.isoformat(timespec="seconds")
    MEMORIA.parent.mkdir(parents=True, exist_ok=True)
    MEMORIA.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")


def clave_del_dia(ahora: datetime, tipo: str) -> str:
    return f"{ahora.date().isoformat()}:{tipo}"


def ya_salio(mem: dict, ahora: datetime, tipo: str) -> dict:
    p = mem["publicaciones"].get(clave_del_dia(ahora, tipo)) or {}
    return p if p.get("estado") in EXITO else {}


# =============================================================================
# Armar
# =============================================================================

def _semilla(texto: str) -> int:
    return int(hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8], 16)


def _foto_usable(url: str, destino: Path, bajar=None) -> str:
    """Baja la foto y la devuelve si tiene tamaño para un reel; '' si no."""
    if not url:
        return ""
    if not (bajar or F.bajar_foto)(url, destino):
        return ""
    try:
        from PIL import Image
        with Image.open(destino) as im:
            ancho, alto = im.size
    except Exception:                          # noqa: BLE001
        return ""
    if max(ancho, alto) < E.FOTO_MIN[0] or min(ancho, alto) < E.FOTO_MIN[1]:
        return ""
    return str(destino)


def candidata_del_texto(g: dict, cands: list) -> int:
    """El número (1..n) de la candidata de la que habla el guion. La IA dice cuál eligió, pero a veces
    escribe sobre otro año (el 22/10 «eligió» un acto de 1936 y contó la fundación de 1854, con la foto
    del acto): manda el AÑO que aparece en el titular o la descripción. 0 si no aparece ninguno."""
    texto = f"{g.get('titular')} {g.get('descripcion')}"
    anios = [c["hecho"]["anio"] for c in cands]
    elegido = min(max(1, g.get("elegido") or 1), len(cands))
    if str(anios[elegido - 1]) in texto:
        return elegido
    for i, a in enumerate(anios, 1):
        if str(a) in texto:
            return i
    return 0


def guion_archivo(ahora: datetime, mem: dict, redactar=None, ind=None, cli=None, buscar=None, media=None,
                  leer=None) -> dict:
    """Elige qué contar y lo redacta. {tipo, guion, volanta, foto_url, usados, fuente} o PasadaError.
    Si la IA dice que la efeméride no sirve, prueba con un personaje y después con una curiosidad."""
    ind = ind or F.indice_al_dia()
    usados = mem["usados"]
    intentos = []
    tipo, cands = E.elegir(ind, usados, ahora, cli, buscar, media, leer)
    if tipo == "efemeride":
        intentos.append(("efemeride", cands))
        intentos.append(("personaje", E.personaje(ind, usados, ahora)))
    elif tipo == "personaje":
        intentos.append(("personaje", cands))
    intentos.append(("curiosidad", E.curiosidad(ind, usados, ahora)))
    motivos = []
    for tipo, cands in intentos:
        if not cands:
            continue
        if tipo == "efemeride":
            textos = {c["dedicado"]["post"]: c["dedicado"].get("texto") or ""
                      for c in cands if (c.get("dedicado") or {}).get("post")}
            material, originales = AG.material_efemerides(cands, ahora, textos)
            g = AG.redactar_con_control(AG.SYSTEM_PROMPT, material, originales, tipo, redactar)
            n = candidata_del_texto(g, cands)
            c = cands[(n or g["elegido"] or 1) - 1] if (n or g["elegido"] or 1) <= len(cands) else cands[0]
            h = c["hecho"]
            # Sin el año de la candidata en el texto no se sabe de qué habla: va sin su foto.
            ded = (c.get("dedicado") or {}) if n else {}
            claves = [c["clave"]] + ([E.clave_post(ded["post"])] if ded.get("post") else [])
            salida = {"tipo": tipo, "guion": g, "volanta": AG.volanta(tipo, ahora.day, ahora.month),
                      "foto_url": (ded.get("foto") or {}).get("url") or "", "usados": claves,
                      "fuente": {"fecha": AG.fecha_larga(h["dia"], h["mes"], h["anio"]), "hace": c["hace"],
                                 "posts": h["posts"], "dedicado": ded.get("post"),
                                 "candidatas": len(cands), "coincide_anio": bool(n)}}
        else:
            post = None
            for c in cands:
                try:
                    post = F.post_completo(c["post"]["id"], cli)
                    break
                except F.FuenteError:
                    continue
            if not post:
                continue
            g = AG.redactar_con_control(AG.SYSTEM_PROMPT, AG.material_post(post, ahora),
                                        [post["titulo"] + " " + post["texto"][:AG.MATERIAL_POST]], tipo, redactar)
            foto = F.url_foto(post.get("foto"), cli) if post.get("foto") else {}
            salida = {"tipo": tipo, "guion": g, "volanta": AG.volanta(tipo), "foto_url": foto.get("url") or "",
                      "usados": [E.clave_post(post["id"])],
                      "fuente": {"post": post["id"], "titulo": post["titulo"]}}
        if g["apta"] and not g["bloqueado"]:
            return salida
        motivos.append(f"{tipo}: " + ("calcaba el material" if g["bloqueado"] else g.get("motivo") or "no apta"))
    raise PasadaError("no hubo nada del Archivo para contar hoy — " + "; ".join(motivos or ["sin candidatas"]))


def armar(tipo: str, ahora: datetime, mem: dict, carpeta: Path, redactar=None, **kw) -> dict:
    """La pieza completa: guion, foto, reel y texto del posteo."""
    from reels import reel_bot as R
    carpeta.mkdir(parents=True, exist_ok=True)
    base = carpeta / f"{ahora:%Y%m%d}_{tipo}"
    if tipo == "pregunta":
        cat, tema = PR.tema_del_dia(PR.temario(), mem["preguntas"], ahora)
        q = PR.generar(cat, tema, mem["preguntas"], redactar)
        if not q["apta"]:
            raise PasadaError(f"la IA no dio una pregunta que sirva («{q.get('pregunta')}»)")
        img = IM.imagen_pregunta(q["image_prompt"], q["seccion"], base.with_name(base.name + "_imagen.jpg"),
                                 semilla=_semilla(q["pregunta"]), pedir=kw.get("pedir_imagen"),
                                 mirar=kw.get("mirar_texto"))
        pieza = {"tipo": "pregunta", "guion": q, "volanta": AG.volanta("pregunta"), "imagen": img,
                 "usados": [], "fuente": {"categoria": cat, "tema": tema}}
        foto = img["archivo"]
    else:
        pieza = guion_archivo(ahora, mem, redactar, kw.get("ind"), kw.get("cli"), kw.get("buscar"), kw.get("media"),
                              kw.get("leer"))
        foto = _foto_usable(pieza["foto_url"], base.with_name(base.name + "_foto.jpg"), kw.get("bajar"))
        if not foto:
            from nacionales import placa as P
            palabra = {"efemeride": "Efemérides", "personaje": "Personajes"}.get(pieza["tipo"], "Historia")
            foto = str(P.guardar_fondo(palabra, base.with_name(base.name + "_placa.jpg"),
                                       semilla=_semilla(pieza["guion"]["titular"]), etiqueta="Chivilcoy"))
        pieza["imagen"] = {"archivo": foto, "proveedor": "archivo" if pieza["foto_url"] and "placa" not in foto
                           else "placa"}
    if pieza["imagen"].get("proveedor") != "placa":       # la placa propia ya trae su grano
        ajuste = IM.para_el_motor(foto, kw.get("mirar"))
        foto = ajuste["archivo"]
        pieza["imagen"]["ajustada"] = ajuste["ajustada"]
    g = pieza["guion"]
    pieza["caption"] = AG.caption(g["descripcion"], g["hashtags"])
    # Bloque blanco o grafito si sale 4:5, alternado con el reel anterior (12/10/2026).
    pieza["video"] = R.armar({"volanta": pieza["volanta"], "titular": g["titular"], "bajada": g["bajada"]},
                             base.with_suffix(".mp4"), foto=foto, tema=R.proximo_tema())
    R.anotar_tema(pieza["video"].get("tema", ""))
    guardable = {k: v for k, v in pieza.items()}
    base.with_suffix(".json").write_text(json.dumps(guardable, ensure_ascii=False, indent=2, default=str),
                                         encoding="utf-8")
    return pieza


# =============================================================================
# Publicar
# =============================================================================

def publicar_reel_prueba(mp4: Path, jpg, caption: str, marca: str) -> dict:
    """Reel de PRUEBA en Instagram, con su portada. {id, prueba}. Lanza FalloRed / SinConfirmar."""
    from reels import instagram as IG
    from reels import publicador as PUB
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    url = PUB.subir_a_release(Path(mp4), f"archivo_{marca}.mp4")
    portada = PUB.subir_a_release(Path(jpg), f"archivo_{marca}.jpg") if jpg and Path(jpg).is_file() else ""
    params = IG.contenedor_reel(url, caption, prueba=True, portada=portada)
    cid = PUB._contenedor_listo(uid, tok, params)
    media_id = PUB._publicar_contenedor(uid, tok, cid, caption)
    return {"id": media_id or None, "prueba": json.loads(params["trial_params"])}


def pasada(tipo: str, publicar: bool, ahora: datetime = None, publicador=None, **kw) -> dict:
    ahora = ahora or _ahora()
    mem = cargar()
    clave = clave_del_dia(ahora, tipo)
    previo = mem["publicaciones"].get(clave) or {}
    inf = {"tipo": tipo, "dia": ahora.date().isoformat(), "publicar": publicar}
    if publicar and ya_salio(mem, ahora, tipo):
        inf["estado"] = "ya_salio"
        inf["detalle"] = f"ya salió hoy ({previo.get('estado')}, {previo.get('cuando')})"
        return inf
    if publicar and (previo.get("intentos") or 0) >= INTENTOS_POR_DIA:
        inf["estado"] = "rendido"
        inf["detalle"] = f"ya falló {previo['intentos']} veces hoy; vuelve mañana"
        return inf
    if publicar:
        from reels import publicador as PUB
        lugar = PUB._lugar_en_instagram()
        if lugar is not None and lugar[0] <= 0:
            inf["estado"] = "sin_lugar"
            inf["detalle"] = f"Instagram sin lugar: {lugar[1]}/{lugar[2]} posteos en 24 h"
            return inf

    pieza = armar(tipo, ahora, mem, SALIDA / ahora.strftime("%Y-%m-%d"), **kw)
    g = pieza["guion"]
    inf.update(titular=g["titular"], caption=pieza["caption"], imagen=pieza["imagen"].get("proveedor"),
               motivo_imagen=pieza["imagen"].get("motivo"), video=pieza["video"]["archivo"],
               placa=pieza["video"].get("placa"), copia=g.get("copia", {}).get("racha"),
               faltan_datos=g.get("faltan_datos"), fuente=pieza.get("fuente"), subtipo=pieza["tipo"])
    if not publicar:
        inf["estado"] = "simulado"
        return inf

    registro = {"titular": g["titular"], "subtipo": pieza["tipo"], "cuando": _ahora().isoformat(timespec="seconds"),
                "intentos": (previo.get("intentos") or 0) + 1, "fuente": pieza.get("fuente")}
    from reels import publicador as PUB
    try:
        res = (publicador or publicar_reel_prueba)(Path(pieza["video"]["archivo"]), pieza["video"].get("placa"),
                                                   pieza["caption"], f"{ahora:%Y%m%d}_{tipo}")
        registro.update(estado="ok", id=res.get("id"), prueba=res.get("prueba"))
    except PUB.SinConfirmar as e:
        registro.update(estado="sin_confirmar", detalle=str(e)[:300])
    except Exception as e:                     # noqa: BLE001 — se anota y avisa; el respaldo reintenta
        registro.update(estado="error", detalle=f"{type(e).__name__}: {e}"[:300])
    mem["publicaciones"][clave] = registro
    if registro["estado"] in EXITO:
        hoy = ahora.date().isoformat()
        for k in pieza.get("usados") or []:
            mem["usados"][k] = hoy
        if tipo == "pregunta":
            mem["preguntas"].append({"dia": hoy, "pregunta": g["pregunta"], "categoria": g.get("categoria"),
                                     "tema": g.get("tema")})
    guardar(mem, ahora)
    inf.update(estado=registro["estado"], id=registro.get("id"), detalle=registro.get("detalle"))
    return inf


def resumen(inf: dict) -> str:
    nombres = {"efemeride": "Archivo Literario", "pregunta": "Pregunta del día"}
    lineas = [f"## {nombres.get(inf['tipo'], inf['tipo'])} — {inf['dia']}", "",
              f"- Estado: **{inf.get('estado')}**" + (f" — {inf['detalle']}" if inf.get("detalle") else "")]
    if inf.get("titular"):
        lineas += [f"- Tipo: {inf.get('subtipo')}", f"- Titular: {inf['titular']}",
                   f"- Imagen: {inf.get('imagen')}" + (f" ({inf['motivo_imagen']})" if inf.get("motivo_imagen") else ""),
                   f"- Fuente interna (no se publica): {json.dumps(inf.get('fuente'), ensure_ascii=False)}"]
        if inf.get("copia") is not None:
            lineas.append(f"- Copia máxima: {inf['copia']} palabras seguidas")
        if inf.get("faltan_datos"):
            lineas.append(f"- Datos que no quedaron: {', '.join(inf['faltan_datos'])}")
        if inf.get("id"):
            lineas.append(f"- Instagram: reel de prueba {inf['id']}")
        lineas += ["", "```", inf.get("caption") or "", "```"]
    return "\n".join(lineas)


def main():
    entorno.consola_utf8()
    entorno.cargar()
    ap = argparse.ArgumentParser(description="Reels de prueba del Archivo Literario y la pregunta del día")
    ap.add_argument("--tipo", choices=TIPOS + ("auto",), default="auto",
                    help="auto: antes de las 17 (hora argentina) la efeméride, después la pregunta")
    ap.add_argument("--publicar", action="store_true", help="sin esto, arma y simula")
    a = ap.parse_args()
    ahora = _ahora()
    tipo = a.tipo if a.tipo != "auto" else ("efemeride" if ahora.hour < 17 else "pregunta")
    try:
        inf = pasada(tipo, a.publicar, ahora)
    except (PasadaError, F.FuenteError) as e:
        print(f"## {tipo} — {ahora.date()}\n\n- Estado: **error** — {e}")
        return 1
    print(resumen(inf))
    return 1 if inf.get("estado") == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
