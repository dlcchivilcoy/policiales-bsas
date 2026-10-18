# -*- coding: utf-8 -*-
"""NOTICIAS NACIONALES: Infobae → nota en la web, Short, posteo en Facebook y carrusel nocturno.

    venv\\Scripts\\python.exe -m nacionales.pasada                      # SIMULA (arma, no publica)
    venv\\Scripts\\python.exe -m nacionales.pasada --publicar
    venv\\Scripts\\python.exe -m nacionales.pasada --publicar --esperar-carrusel 22:00
    venv\\Scripts\\python.exe -m nacionales.pasada --publicar --solo-carrusel

Pedido del editor (06/10/2026), en sus palabras:
- «noticias nacionales/provinciales/regionales que tengan que ver con Chivilcoy por afectación
  directa o indirecta», y también «internas políticas, juicios, y cuestiones de relevancia como
  peregrinación a Luján, noticias que sean populares o que generen viralización».
- Instagram: «un carrusel nocturno a las 22hs agrupando todo lo que encuentres», con un título
  con buen SEO → «Noticias nacionales de hoy».
- Facebook: «publicaciones separadas con link a la nota rearmada a mi web» (no reels: «la idea
  sería no saturar con reels»).
- YouTube: «shorts individuales».
- La foto (07/10): la de la nota de Infobae —en el Short, la placa de Facebook, la web y el
  carrusel—, SALVO que el epígrafe diga que es de una agencia (AP, AFP, Reuters, EFE, Getty…:
  facturan cada foto usada). Esas, y las notas sin foto, salen con la placa propia (placa.py).

Cómo queda, por pasada (corre en las mismas pasadas que policiales, en un trabajo aparte):
1. Infobae (nacionales/infobae.py) → filtro y orden por relevancia y cobertura (filtro.py).
2. Hasta NAC_POR_PASADA notas nuevas (3), sin pasar de NAC_POR_DIA (12) ni repetir un tema de
   las últimas 24 h. Guion con la IA (guion.py); la que no sirve queda anotada y no se reintenta.
3. Por pieza, en orden: Short en YouTube (con el link de su nota) → nota en la web (sección
   Nacionales y portada, con el Short adentro) → Facebook, SOLO las más virales: hasta
   NAC_FB_POR_PASADA (2) y NAC_FB_POR_DIA (8). Es un posteo con la PLACA y el link a la nota:
   Facebook no lee bien la foto de una nota de Wix recién publicada (memoria del bot, «FB
   previsualización misma foto») y si se postea solo el link sale con una foto equivocada.
   30 minutos entre pieza y pieza (eran 5; pedido del editor del 13/10/2026, como policiales).
4. Desde las 22 (la pasada de las 21:05 espera con --esperar-carrusel 22:00), el carrusel de
   Instagram con lo que salió desde el carrusel anterior: hasta 10 diapositivas, una por nota y
   la primera es la portada (desde el 12/10 no hay tapa con la lista de titulares). Estilo
   portal en grafito (placa.slide_carrusel): las fotos horizontales alternan dos estilos con la
   foto arriba y las demás van a sangre con el titular en una caja que no tapa caras. Es un
   posteo NORMAL del feed: los «reels de prueba» de Instagram son solo para reels.

La memoria vive en estado/nacionales.json (se commitea como la de policiales).
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import entorno
from nacionales import categorias as CAT
from nacionales import filtro as F
from nacionales import guion as NG
from nacionales import impacto as IM
from nacionales import infobae as IB
from nacionales import placa as P
from nacionales import portales as PO
from nacionales import senales as SE
from reels import distribuidor as DIST
from reels import publicador as PUB
from reels import web as WEB

RAIZ = Path(__file__).resolve().parent.parent
MEMORIA = RAIZ / "estado" / "nacionales.json"
SALIDA = RAIZ / "salida_nacionales"
TZ_AR = timezone(timedelta(hours=-3))
DIAS_MEMORIA = 7
SECCION_WEB = f"https://{WEB.SITIO}/seccion/nacionales"

POR_PASADA = 3
POR_DIA = 12
FB_POR_PASADA = 2
FB_POR_DIA = 8
CARRUSEL_MAX = 10           # diapositivas, una por nota (el tope de Instagram; sin tapa desde el 12/10)
CARRUSEL_MIN = 2
HORA_CARRUSEL = (22, 0)
MINUTOS_ENTRE_PIEZAS = 30     # entre un Short y el siguiente (13/10/2026; eran 5), como policiales
HORAS_TEMA = 24             # un tema ya contado no se repite en este lapso
MAX_ESPERA_CARRUSEL = 100   # minutos: más que esto no se espera (la pasada vendría muy atrasada)


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int((os.environ.get(nombre) or "").strip()))
    except ValueError:
        return defecto


def _ahora() -> datetime:
    return datetime.now(TZ_AR)


def _dormir(segundos: float):
    time.sleep(segundos)


# =============================================================================
# Memoria
# =============================================================================

def cargar() -> dict:
    try:
        d = json.loads(MEMORIA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    for k in ("piezas", "descartadas", "carruseles"):
        d.setdefault(k, {})
    return d


def guardar(mem: dict):
    limite = (_ahora() - timedelta(days=DIAS_MEMORIA)).isoformat(timespec="seconds")
    for k in ("piezas", "descartadas"):
        mem[k] = {u: v for u, v in mem[k].items() if (v.get("cuando") or "") >= limite}
    dia_limite = (_ahora() - timedelta(days=DIAS_MEMORIA)).date().isoformat()
    mem["carruseles"] = {d: v for d, v in mem["carruseles"].items() if d >= dia_limite}
    mem["actualizado"] = _ahora().isoformat(timespec="seconds")
    MEMORIA.parent.mkdir(parents=True, exist_ok=True)
    MEMORIA.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")


def _ok(red: dict) -> bool:
    return isinstance(red, dict) and red.get("estado") in ("ok", "sin_confirmar")


def de_hoy(mem: dict, dia: str) -> list:
    return [p for p in mem["piezas"].values() if p.get("dia") == dia]


# =============================================================================
# Elegir
# =============================================================================

def elegir(candidatas: list, mem: dict, cupo: int, ahora: datetime) -> list:
    """Las candidatas que van en esta pasada: nuevas, sin descartar y de un tema no contado."""
    desde = (ahora - timedelta(hours=HORAS_TEMA)).isoformat(timespec="seconds")
    hechas = [{"titulo": p.get("titular"), "tema": p.get("tema") or []}
              for p in mem["piezas"].values() if (p.get("cuando") or "") >= desde]
    salida = []
    for c in candidatas:
        if len(salida) >= cupo:
            break
        if c["url"] in mem["piezas"] or c["url"] in mem["descartadas"]:
            continue
        if F.ya_contado(c, hechas + [{"titulo": x["titulo"], "tema": x["tema"]} for x in salida]):
            continue
        salida.append(c)
    return salida


def para_facebook(piezas: list, mem: dict, dia: str) -> set:
    """Las URLs de las piezas que van a Facebook: las más virales de la pasada, con tope."""
    hechas_hoy = sum(1 for p in de_hoy(mem, dia) if _ok(p.get("facebook")))
    cupo = min(_entero("NAC_FB_POR_PASADA", FB_POR_PASADA), _entero("NAC_FB_POR_DIA", FB_POR_DIA) - hechas_hoy)
    orden = sorted(piezas, key=lambda p: (-(p["guion"].get("viral") or 0), -(p["nota"].get("puntos") or 0)))
    return {p["nota"]["url"] for p in orden[:max(0, cupo)]}


# =============================================================================
# Armar
# =============================================================================

def _semilla(url: str) -> int:
    return int(hashlib.sha1(url.encode("utf-8")).hexdigest()[:8], 16)


def foto_de_la_nota(nota: dict, destino: Path) -> dict:
    """La foto de la nota de Infobae, si se puede usar (decisión del editor, 07/10: la original,
    SALVO las de agencia). Devuelve {archivo, url, credito} o {motivo} si va la placa propia."""
    from reels.flujo import FOTO_MIN_LADO_MAYOR, FOTO_MIN_LADO_MENOR, _bajar_foto, _tamanio
    url = nota.get("imagen") or ""
    if not url:
        return {"motivo": "la nota no trae foto"}
    epigrafe, leido = IB.credito_foto(nota["url"])
    credito = " ".join(f"{nota.get('credito_feed') or ''} {epigrafe}".split())
    if not leido:
        return {"motivo": "no se pudo leer de quién es la foto", "url": url}
    agencia = IB.es_de_agencia(credito)
    if agencia:
        return {"motivo": f"foto de agencia ({agencia})", "url": url, "credito": credito}
    if not _bajar_foto(url, Path(destino)):
        return {"motivo": "la foto no se pudo bajar", "url": url, "credito": credito}
    t = _tamanio(Path(destino))
    if not t or max(t) < FOTO_MIN_LADO_MAYOR or min(t) < FOTO_MIN_LADO_MENOR:
        Path(destino).unlink(missing_ok=True)
        return {"motivo": f"la foto es muy chica ({t})", "url": url, "credito": credito}
    return {"archivo": str(destino), "url": url, "credito": credito}


def armar(nota: dict, carpeta: Path, redactar=None, leer_pagina=None) -> dict:
    """Guion + Short + placa de Facebook + imagen de la web. Lanza si la IA no contesta.

    Variedad (deportes, espectáculos, mundo, virales, cine y series, IA; 18/10/2026): se lee la página de
    la nota para el VIDEO y la FOTO originales. Con video → REEL con ese video; sin video → CARRUSEL
    explicativo con la foto original; un VIRAL sin su video no sale (ni se gasta la IA)."""
    variedad = bool(nota.get("categoria"))
    medios = {}
    if variedad:
        leer = leer_pagina or CAT.leer_pagina
        medios = dict(leer(nota["url"]))
        if not nota.get("imagen") and medios.get("imagen"):
            nota = dict(nota, imagen=medios["imagen"])
        # Los portales cuyo RSS trae solo el titular (Ámbito, Clarín, Olé, ESPN…): el texto de la página.
        if len(medios.get("texto") or "") > len(nota.get("cuerpo") or "") and len(nota.get("cuerpo") or "") < 1500:
            nota = dict(nota, cuerpo=medios["texto"])
        # Sin video en esta nota: el mismo tema en otro portal puede traer el suyo (18/10/2026).
        for otra in ([] if medios.get("video") else (nota.get("otras_urls") or [])[:3]):
            try:
                v = (leer(otra) or {}).get("video")
            except Exception:                        # noqa: BLE001 — una página que no anda no frena
                v = ""
            if v:
                medios["video"], medios["video_de"] = v, otra
                break
        if nota.get("categoria") == "virales" and not medios.get("video"):
            return {"nota": nota, "url_original": nota["url"],
                    "guion": {"apta": False, "motivo": "viral sin el video original en la nota"}}
    g = NG.generar(nota, redactar)
    pieza = {"nota": nota, "guion": g, "url_original": nota["url"],
             "web": {"titulo": g["titulo_web"], "cuerpo": g["nota_web"]}}
    if not g["apta"]:
        return pieza
    carpeta.mkdir(parents=True, exist_ok=True)
    base = carpeta / WEB.slugify(g["titular"], 50)
    semilla = _semilla(nota["url"])
    from reels import reel_bot as R
    pieza["foto"] = foto_de_la_nota(nota, base.with_name(base.name + "_foto.jpg"))
    foto = pieza["foto"].get("archivo")
    imagen = foto or P.guardar_fondo(g["seccion"], base.with_name(base.name + "_fondo.jpg"), semilla=semilla)
    clip = None
    if medios.get("video"):
        from reels.flujo import _bajar_video
        clip = _bajar_video(medios["video"], base.with_name(base.name + "_original.mp4"))
        if clip:
            pieza["video_original"] = medios["video"]
    if nota.get("categoria") == "virales" and not clip:
        g.update(apta=False, motivo="viral: el video original no se pudo bajar")
        return pieza
    guion_reel = {"volanta": g["volanta"], "titular": g["titular"], "bajada": g["bajada"]}
    # Bloque blanco o grafito si sale 4:5, alternado con el reel anterior (12/10/2026).
    tema = R.proximo_tema()
    try:
        pieza["video"] = R.armar(guion_reel, base.with_suffix(".mp4"), foto=None if clip else imagen,
                                 clip=clip, tema=tema)
    except R.ReelError:
        if not clip or nota.get("categoria") == "virales":
            raise
        clip = None                                   # el video no anduvo: la pieza sigue con la foto
        pieza["video"] = R.armar(guion_reel, base.with_suffix(".mp4"), foto=imagen, tema=tema)
    R.anotar_tema(pieza["video"].get("tema", ""))
    pieza["placa"] = pieza["video"].get("placa")
    if variedad:
        pieza["formato"] = "reel" if clip else "carrusel"
        if not clip:
            laminas = g.get("laminas") or []
            total = 1 + len(laminas)
            if total >= 3:
                pieza["slides"] = [str(P.slide_carrusel(
                    g["seccion"], g["volanta"], g["titular"], g.get("bajada") or "",
                    base.with_name(base.name + "_c01.jpg"), sitio=WEB.SITIO, idx=1, total=total,
                    semilla=semilla, foto=foto))]
                for i, l in enumerate(laminas, 2):
                    pieza["slides"].append(str(P.lamina_texto(
                        g["seccion"], l["titulo"], l["texto"], base.with_name(base.name + f"_c{i:02d}.jpg"),
                        idx=i, total=total, foto=foto, sitio=WEB.SITIO, semilla=semilla)))
            else:
                pieza["formato"] = "imagen"           # la IA no escribió láminas: una sola placa
    # La placa del posteo de Facebook: la misma del carrusel (estilo portal en grafito, 12/10),
    # sin número ni flecha porque es un posteo suelto.
    pieza["slide"] = str(P.slide_carrusel(g["seccion"], g["volanta"], g["titular"], g.get("bajada") or "",
                                          base.with_name(base.name + "_facebook.jpg"), sitio=WEB.SITIO,
                                          semilla=semilla, foto=foto))
    pieza["portada_web"] = str(P.portada_web(g["seccion"], g["volanta"], g["titular"],
                                             base.with_name(base.name + "_web.jpg"), semilla=semilla))
    # Para revisar después qué se publicó y con qué texto (va al artefacto de la corrida).
    guardable = {k: v for k, v in pieza.items() if k != "nota"}
    guardable["nota"] = {k: nota.get(k) for k in ("url", "titulo", "puntos", "nivel", "cobertura", "motivos", "otras")}
    base.with_suffix(".json").write_text(json.dumps(guardable, ensure_ascii=False, indent=2), encoding="utf-8")
    return pieza


# =============================================================================
# Publicar
# =============================================================================

def url_web_prevista(pieza: dict) -> str:
    """El link de la nota ANTES de crearla: el slug es fijo (título + marca de la URL original).
    Así el Short ya sale con el link a su nota."""
    return WEB.link(WEB.slug_de(pieza))


def meta_youtube(pieza: dict, url_web: str) -> dict:
    g = pieza["guion"]
    titulo = PUB._sin_angulos(g["titular"])
    if len(titulo) > 100:
        titulo = titulo[:99].rstrip() + "…"
    desc = PUB._sin_angulos(NG.texto_posteo(g, url_web, WEB.SITIO))
    if "#shorts" not in desc.lower():
        desc += "\n\n#Shorts"
    etiquetas = []
    for t in [h.lstrip("#") for h in g.get("hashtags") or []] + [g.get("seccion") or "", "Noticias nacionales",
                                                                 "Argentina", "Buenos Aires"]:
        if t and t.lower() not in {e.lower() for e in etiquetas}:
            etiquetas.append(t)
    return {"snippet": {"title": titulo, "description": desc[:5000], "tags": etiquetas[:12],
                        "categoryId": PUB.YT_CATEGORIA, "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True,
                       "containsSyntheticMedia": False}}


def _yt_cambiar_descripcion(video_id: str, meta: dict):
    """Si la nota de la web no salió, el Short no puede quedar con un link roto: va el de la sección."""
    acceso = PUB._yt_sesion()
    r = PUB._pedir("PUT", f"{PUB.YT_API}/videos", acceso, params={"part": "snippet"},
                   json={"id": video_id, "snippet": meta["snippet"]})
    if r.status_code >= 400:
        raise PUB.FalloRed(PUB._yt_error(r, "YouTube (cambiar la descripción)"))


def texto_facebook(pieza: dict, url_web: str) -> str:
    """Una oración para el título y otra para el enlace (como los enlaces de los Shorts, 03/10)."""
    titular = " ".join(pieza["guion"]["titular"].split()).rstrip(" .")
    return f"{titular}.\n\n📲 Leé la nota completa: {url_web}"


def publicar_foto_facebook(jpg: Path, mensaje: str) -> dict:
    pid = os.environ.get("FACEBOOK_PAGE_ID", "")
    tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    try:
        r = PUB._pedir("POST", f"{PUB.GRAPH}/{pid}/photos", tok, data={"message": mensaje, "published": "true"},
                       files={"source": (Path(jpg).name, Path(jpg).read_bytes(), "image/jpeg")})
    except PUB._Cortado as e:
        raise PUB.SinConfirmar(f"Facebook (posteo con la placa): {e}")    # pudo haber salido: no se reintenta
    if r.status_code >= 400:
        raise PUB.FalloRed(PUB._error(r, "Facebook (posteo con la placa)"))
    d = r.json() or {}
    return {"id": str(d.get("post_id") or d.get("id") or "")}


def _resultado(fn, *args) -> dict:
    cuando = _ahora().isoformat(timespec="seconds")
    try:
        return dict(fn(*args) or {}, estado="ok", cuando=cuando)
    except PUB.SinConfirmar as e:
        return {"estado": "sin_confirmar", "error": PUB._tapar(e), "cuando": cuando}
    except Exception as e:                           # noqa: BLE001 — se anota y se sigue
        return {"estado": "fallo", "error": PUB._tapar(f"{type(e).__name__}: {e}")[:400], "cuando": cuando}


def publicar_pieza(pieza: dict, a_facebook: bool, publicar: bool) -> dict:
    """YouTube → web → Facebook. Devuelve {red: resultado}."""
    mp4 = Path(pieza["video"]["archivo"])
    cat = pieza["nota"].get("categoria") or ""        # deportes, espectáculos… (17/10/2026)
    url_prev = url_web_prevista(pieza)
    meta = meta_youtube(pieza, url_prev)
    res = {}
    if not publicar:
        res["youtube"] = {"estado": "simulado", "titulo": meta["snippet"]["title"]}
        res["web"] = {"estado": "simulado", "url": url_prev}
        if a_facebook:
            res["facebook"] = {"estado": "simulado", "texto": texto_facebook(pieza, url_prev)}
        if cat and instagram_activo():
            res["instagram"] = {"estado": "simulado", "formato": pieza.get("formato"),
                                "laminas": len(pieza.get("slides") or [])}
        return res

    res["youtube"] = _resultado(PUB.publicar_youtube, pieza, mp4, meta)
    yt_id = res["youtube"].get("id") if _ok(res["youtube"]) else ""

    def _web():
        nombre = f"nacional_{hashlib.sha1(pieza['url_original'].encode()).hexdigest()[:10]}_web.jpg"
        placa_web = lambda: PUB.subir_a_release(Path(pieza["portada_web"]), nombre)   # noqa: E731
        foto = (pieza.get("foto") or {})
        # La foto de la nota (Wix la importa de Infobae); la placa propia si no hay foto usable o
        # si Wix no la deja importar.
        pieza["imagen_url"] = foto.get("url") if foto.get("archivo") else placa_web()
        return WEB.publicar(lambda m, u, **kw: PUB._pedir(m, u, "", **kw), pieza, yt_id or "",
                            placa_web if foto.get("archivo") else "",
                            categorias=[CAT.seccion_web(cat) if cat else WEB.NACIONALES_ID,
                                        WEB.NACIONALES_AUTO_ID])
    res["web"] = _resultado(_web) if WEB.activa() else {"estado": "apagada"}
    url_web = res["web"].get("url") if _ok(res["web"]) else ""
    if yt_id and not url_web:
        meta_sec = meta_youtube(pieza, SECCION_WEB)
        res["youtube"]["descripcion"] = _resultado(_yt_cambiar_descripcion, yt_id, meta_sec)["estado"]

    if a_facebook:
        # Sin nota en la web no hay a dónde mandar a la gente: el posteo lleva la sección.
        res["facebook"] = _resultado(publicar_foto_facebook, Path(pieza["slide"]),
                                     texto_facebook(pieza, url_web or SECCION_WEB))
    # Instagram (18/10/2026): las de variedad salen en el feed — REEL con el video original, o CARRUSEL
    # explicativo con la foto original. Las nacionales generales siguen yendo al carrusel de las 22.
    if cat and instagram_activo():
        caption = NG.texto_posteo(pieza["guion"], url_web or url_prev, WEB.SITIO)[:2200]
        marca = hashlib.sha1(pieza["url_original"].encode()).hexdigest()[:10]
        if pieza.get("formato") == "reel":
            res["instagram"] = dict(_resultado(publicar_reel_instagram, mp4, caption, marca), formato="reel")
        elif pieza.get("formato") == "carrusel":
            res["instagram"] = dict(_resultado(publicar_carrusel, pieza["slides"], caption, f"var_{marca}"),
                                    formato="carrusel")
        else:
            res["instagram"] = dict(_resultado(publicar_imagen_instagram, Path(pieza["slide"]), caption, marca),
                                    formato="imagen")
    return res


def instagram_activo() -> bool:
    """NAC_INSTAGRAM=0 apaga el Instagram de la variedad (el carrusel de las 22 sigue)."""
    return (os.environ.get("NAC_INSTAGRAM") or "1").strip() != "0"


def publicar_reel_instagram(mp4: Path, caption: str, marca: str) -> dict:
    from reels import instagram as IG
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    url = PUB.subir_a_release(mp4, f"variedad_{marca}_{mp4.name}")
    cid = PUB._contenedor_listo(uid, tok, IG.contenedor_reel(url, caption, prueba=False))
    return {"id": PUB._publicar_contenedor(uid, tok, cid, caption) or None}


def publicar_imagen_instagram(jpg: Path, caption: str, marca: str) -> dict:
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    url = PUB.subir_a_release(jpg, f"variedad_{marca}.jpg")
    cid = PUB._contenedor_listo(uid, tok, {"image_url": url, "caption": caption})
    return {"id": PUB._publicar_contenedor(uid, tok, cid, caption) or None}


# =============================================================================
# Carrusel de Instagram (22 h)
# =============================================================================

def para_el_carrusel(mem: dict) -> list:
    """Lo publicado desde el último carrusel (con su nota en la web), de lo más viral a lo menos."""
    ya = {u for c in mem["carruseles"].values() if _ok(c) for u in c.get("piezas") or []}
    # Las categorías nuevas (deportes, espectáculos…) no van al carrusel «Noticias nacionales de hoy».
    listas = [(u, p) for u, p in mem["piezas"].items() if u not in ya and _ok(p.get("web"))
              and not p.get("categoria")]
    listas.sort(key=lambda x: (-(x[1].get("viral") or 0), -(x[1].get("puntos") or 0), x[1].get("cuando") or ""))
    return listas[:CARRUSEL_MAX]


def caption_carrusel(titulares: list, cuando: datetime) -> str:
    numeros = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣")
    lista = "\n".join(f"{numeros[i]} {t.rstrip(' .')}" for i, t in enumerate(titulares[:9]))
    texto = (f"Noticias nacionales de hoy, {P.fecha_larga(cuando)} de {cuando.year}: lo más importante "
             f"de la Argentina y de la provincia de Buenos Aires en un solo resumen.\n\n{lista}\n\n"
             f"📲 Leelas completas en {WEB.SITIO}, sección Nacionales.\n\n"
             "#NoticiasNacionales #NoticiasDeHoy #ResumenDeNoticias #Argentina #ProvinciaDeBuenosAires #Chivilcoy")
    return texto[:PUB.MAX_CAPTION_IG]


def publicar_carrusel(jpgs: list, caption: str, marca: str) -> dict:
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    hijos = []
    for i, j in enumerate(jpgs):
        url = PUB.subir_a_release(Path(j), f"nacionales_{marca}_{i:02d}.jpg")
        hijos.append(PUB._contenedor_listo(uid, tok, {"image_url": url, "is_carousel_item": "true"}))
    padre = PUB._contenedor_listo(uid, tok, {"media_type": "CAROUSEL", "children": ",".join(hijos),
                                             "caption": caption})
    return {"id": PUB._publicar_contenedor(uid, tok, padre, caption) or None, "diapositivas": len(jpgs)}


def carrusel(mem: dict, publicar: bool, carpeta: Path, ahora: datetime) -> dict:
    dia = ahora.date().isoformat()
    if _ok(mem["carruseles"].get(dia)):
        return {"estado": "ya_estaba"}
    elegidas = para_el_carrusel(mem)
    if len(elegidas) < CARRUSEL_MIN:
        return {"estado": "omitido", "motivo": f"hay {len(elegidas)} nota(s) para el carrusel"}
    total = len(elegidas)
    from reels.flujo import _bajar_foto
    carpeta.mkdir(parents=True, exist_ok=True)
    fotos = []
    for i, (u, p) in enumerate(elegidas, 1):
        foto = None
        if p.get("foto_url"):                        # la misma que salió en su pieza
            foto = _bajar_foto(p["foto_url"], carpeta / f"carrusel_{i:02d}_foto.jpg")
        fotos.append(foto)
    estilos = P.estilos_carrusel(fotos)
    jpgs = []
    for i, ((u, p), foto, estilo) in enumerate(zip(elegidas, fotos, estilos), 1):
        jpgs.append(P.slide_carrusel(p.get("seccion") or "Nacionales", p.get("volanta") or "", p["titular"],
                                     p.get("bajada") or "", carpeta / f"carrusel_{i:02d}.jpg", sitio=WEB.SITIO,
                                     idx=i, total=total, semilla=_semilla(u), foto=foto, estilo=estilo))
    caption = caption_carrusel([p["titular"] for _, p in elegidas], ahora)
    if not publicar:
        return {"estado": "simulado", "diapositivas": len(jpgs), "caption": caption,
                "archivos": [str(j) for j in jpgs]}
    res = _resultado(publicar_carrusel, jpgs, caption, ahora.strftime("%Y%m%d"))
    res["piezas"] = [u for u, _ in elegidas]
    mem["carruseles"][dia] = res
    return res


# =============================================================================
# La pasada
# =============================================================================

def _hora_del_carrusel(esperar: str = "") -> datetime:
    hh, mm = (int(x) for x in esperar.split(":")) if esperar else HORA_CARRUSEL
    return _ahora().replace(hour=hh, minute=mm, second=0, microsecond=0)


def elegir_variedad(notas_var: list, mem: dict, dia: str, ahora: datetime, cupo: int, senales: dict = None,
                    ranking: dict = None) -> list:
    """Candidatas de las categorías nuevas (nacionales/categorias.py) por IMPACTO (18/10/2026): primero
    la categoría con el tema más fuerte (menos lo que ya salió hoy de ella), y dentro de cada una las
    mejores notas nuevas (hasta 3, porque la que la IA descarta deja lugar a la siguiente). `ranking`,
    si viene, se llena con las 3 mejores de cada categoría (para el informe)."""
    if cupo <= 0 or not notas_var:
        return []
    por_cat = CAT.candidatas(notas_var, ahora.timestamp(), senales)
    if ranking is not None:
        for c, lista in por_cat.items():
            ranking[c] = [{"impacto": x["impacto"], "titulo": x["titulo"], "fuentes": x.get("fuentes") or [],
                           "razones": x.get("impacto_razones") or [], "url": x["url"]} for x in lista[:3]]
    ultimas = {}
    for p in mem["piezas"].values():
        c = p.get("categoria")
        if c and (p.get("cuando") or "") > ultimas.get(c, ""):
            ultimas[c] = p.get("cuando") or ""
    salida = []
    for cat in CAT.orden_por_impacto(por_cat, de_hoy(mem, dia), ultimas):
        salida += elegir(por_cat.get(cat) or [], mem, 3, ahora)
    return salida


def pasada(publicar: bool, cuantos: int = 0, solo_carrusel: bool = False, esperar_carrusel: str = "",
           con_carrusel: bool = True, redactar=None, notas=None, notas_variedad=None,
           leer_pagina=None, senales=None) -> dict:
    notas_inyectadas = notas
    mem = cargar()
    ahora = _ahora()
    dia = ahora.date().isoformat()
    carpeta = SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    informe = {"cuando": ahora.isoformat(timespec="seconds"), "publicar": publicar, "piezas": [],
               "descartadas": [], "fallas": []}

    if publicar:
        # Los Shorts de pasadas anteriores: ¿YouTube los terminó de procesar? (17/10/2026)
        for aviso in PUB.verificar_shorts(mem["piezas"]):
            informe.setdefault("avisos", []).append(aviso)

    if not solo_carrusel:
        if notas is None:
            notas, fallas = IB.bajar()
            # Una sección caída es un aviso, no una falla: las otras alcanzan.
            informe.setdefault("avisos", []).extend(f"Infobae {f}" for f in fallas)
            if not notas:
                raise RuntimeError("Infobae no devolvió ninguna nota: " + "; ".join(fallas))
        cands = F.candidatas(notas, ahora.timestamp())
        informe["candidatas"] = len(cands)
        # Señales de impacto (18/10/2026): más leídas, búsquedas de Google, Google News y YouTube. Una
        # sola vez por pasada; en las pruebas, solo lo que se le pasa.
        if senales is None:
            senales = SE.juntar() if notas_inyectadas is None else SE.vacias()
            informe.setdefault("avisos", []).extend(f"señal {f}" for f in senales.get("fallas") or [])
        informe["senales"] = {k: len(senales.get(k) or []) for k in ("mas_leidas", "tendencias", "google_news",
                                                                      "youtube")}
        if notas_inyectadas is None:
            # Nacionales generales: Ámbito, El Cronista, La Nación y Clarín dan la cobertura del tema.
            otras, fallas_otras, _ = PO.bajar(PO.FUENTES_NACIONALES)
            informe["avisos"].extend(f"nacionales {f}" for f in fallas_otras)
            cands = IM.realzar_generales(cands, otras, senales, ahora.timestamp())
        # Las 12 por día son de las nacionales generales: la variedad tiene su cupo propio (18/10/2026).
        hechas = len([p for p in de_hoy(mem, dia) if not p.get("categoria")])
        cupo = min(cuantos or _entero("NAC_POR_PASADA", POR_PASADA), _entero("NAC_POR_DIA", POR_DIA) - hechas)
        # Variedad (deportes, espectáculos, mundo, virales, cine y series, IA): CUPO PROPIO desde el
        # 18/10/2026 (pedido del editor: ~10 por día), aparte de las nacionales generales. Como mucho
        # NAC_VARIEDAD_POR_PASADA (2) por pasada, de categorías distintas, y cada una con su tope por día.
        if notas_variedad is None:
            notas_variedad = []
            if notas_inyectadas is None:             # en las pruebas, solo lo que se le pasa
                notas_variedad, fallas_var, conteo = CAT.bajar()
                informe.setdefault("avisos", []).extend(f"portal {f}" for f in fallas_var)
                informe["fuentes_variedad"] = conteo
        n_var = CAT.por_pasada()
        variedad = []
        informe["ranking_variedad"] = {}
        for c in elegir_variedad(notas_variedad, mem, dia, ahora, n_var, senales, informe["ranking_variedad"]):
            if len(variedad) >= n_var:
                break
            if any(v["nota"].get("categoria") == c["categoria"] for v in variedad):
                continue
            try:
                pieza = armar(c, carpeta, redactar, leer_pagina)
            except Exception as e:                   # noqa: BLE001 — la IA o el motor: se sigue con otra
                informe["fallas"].append(f"no se pudo armar «{c['titulo'][:60]}»: {type(e).__name__}: {e}"[:300])
                continue
            if not pieza["guion"]["apta"]:
                informe["descartadas"].append({"titulo": c["titulo"], "motivo": pieza["guion"]["motivo"],
                                               "categoria": c["categoria"]})
                if publicar:
                    mem["descartadas"][c["url"]] = {"motivo": pieza["guion"]["motivo"],
                                                    "cuando": ahora.isoformat(timespec="seconds")}
                continue
            variedad.append(pieza)
        informe["variedad"] = [{"categoria": v["nota"]["categoria"], "titulo": v["guion"]["titular"],
                                "formato": v.get("formato")} for v in variedad]
        armadas = []
        # Se piden de a una, de la más relevante a la menos, hasta llenar el cupo: la que la IA
        # descarta deja lugar a la siguiente.
        for c in elegir(cands, mem, max(0, cupo) * 3, ahora):
            if len(armadas) >= cupo:
                break
            try:
                pieza = armar(c, carpeta, redactar)
            except Exception as e:                   # noqa: BLE001 — la IA o el motor: se sigue con otra
                informe["fallas"].append(f"no se pudo armar «{c['titulo'][:60]}»: {type(e).__name__}: {e}"[:300])
                continue
            g = pieza["guion"]
            if not g["apta"]:
                informe["descartadas"].append({"titulo": c["titulo"], "motivo": g["motivo"]})
                if publicar:
                    mem["descartadas"][c["url"]] = {"motivo": g["motivo"], "cuando": ahora.isoformat(timespec="seconds")}
                continue
            armadas.append(pieza)
        # La variedad va intercalada con las nacionales: segunda, cuarta… (nunca dos seguidas si hay con qué).
        for i, v in enumerate(variedad):
            armadas.insert(min(1 + 2 * i, len(armadas)), v)

        fb = para_facebook(armadas, mem, dia)
        ultimo = None
        for i, pieza in enumerate(armadas):
            if ultimo is not None and publicar:
                # Desde que ARRANCÓ la anterior: lo que tardó en subir ya cuenta en los 30 minutos.
                falta = (ultimo + timedelta(minutes=MINUTOS_ENTRE_PIEZAS) - _ahora()).total_seconds()
                if falta > 0:
                    _dormir(falta)
            # Con la variedad la tanda de las 21:05 dura hasta las 23 (18/10/2026): el carrusel de las
            # 22 sale a su hora, en el medio, con lo publicado hasta ahí (el resto va al de mañana).
            if con_carrusel and "carrusel" not in informe and _ahora() >= _hora_del_carrusel(esperar_carrusel):
                informe["carrusel"] = carrusel(mem, publicar, carpeta, _ahora())
            ultimo = _ahora()
            nota, g = pieza["nota"], pieza["guion"]
            res = publicar_pieza(pieza, nota["url"] in fb, publicar)
            # TikTok por Buffer (17/10/2026, etapa 6): el video va al buzón del distribuidor, que lo
            # intercala con el resto. Solo si salió la nota (a X llega como nota de la web).
            if publicar and _ok(res.get("web")):
                yt = res.get("youtube") or {}
                mp4 = Path(pieza["video"]["archivo"])
                nombre = f"nacional_{hashlib.sha1(nota['url'].encode()).hexdigest()[:10]}_{mp4.name}"
                ev_id = DIST.dejar_nacional(pieza, mp4, res["web"].get("url") or "",
                                            yt.get("url") or "" if _ok(yt) else "",
                                            PUB.subir_a_release, nombre)
                res["tiktok_buzon"] = ({"estado": "ok", "id": ev_id} if ev_id else
                                       {"estado": "omitida", "detalle": "no se pudo dejar en el buzón"})
            fila = {"titulo_original": nota["titulo"], "titular": g["titular"], "volanta": g["volanta"],
                    "categoria": nota.get("categoria") or "", "formato": pieza.get("formato") or "",
                    "medio_origen": PO.fuente_de(nota) if nota.get("categoria") else (nota.get("medio") or ""),
                    "video_original": pieza.get("video_original") or "",
                    "impacto": nota.get("impacto"), "impacto_razones": nota.get("impacto_razones") or [],
                    "fuentes": nota.get("fuentes") or [],
                    "bajada": g.get("bajada") or "", "seccion": g["seccion"], "tema": nota.get("tema") or [], "viral": g["viral"],
                    "puntos": nota.get("puntos"), "nivel": nota.get("nivel"), "cobertura": nota.get("cobertura"),
                    "dia": dia, "cuando": _ahora().isoformat(timespec="seconds"), "via": g.get("via"),
                    "copia": (g.get("copia") or {}).get("racha"),
                    # La foto, para el carrusel de las 22 (otra corrida: se vuelve a bajar).
                    "foto_url": (pieza.get("foto") or {}).get("url") if (pieza.get("foto") or {}).get("archivo") else "",
                    "foto": (pieza.get("foto") or {}).get("credito") or (pieza.get("foto") or {}).get("motivo"),
                    **res}
            informe["piezas"].append(fila)
            for red, r in res.items():
                if r.get("estado") == "fallo":
                    informe["fallas"].append(f"{red}: «{g['titular'][:50]}»: {r.get('error')}")
            if publicar:
                mem["piezas"][nota["url"]] = fila
                guardar(mem)                         # tras cada pieza: un corte no borra lo hecho

    if con_carrusel and "carrusel" not in informe:
        objetivo = _ahora().replace(hour=HORA_CARRUSEL[0], minute=HORA_CARRUSEL[1], second=0, microsecond=0)
        if esperar_carrusel:
            hh, mm = (int(x) for x in esperar_carrusel.split(":"))
            objetivo = _ahora().replace(hour=hh, minute=mm, second=0, microsecond=0)
            falta = (objetivo - _ahora()).total_seconds()
            if 0 < falta <= MAX_ESPERA_CARRUSEL * 60:
                print(f"Esperando hasta las {esperar_carrusel} para el carrusel ({falta / 60:.0f} min)…")
                if publicar:
                    _dormir(falta)
        if solo_carrusel or _ahora() >= objetivo:
            informe["carrusel"] = carrusel(mem, publicar, carpeta, _ahora())
            if informe["carrusel"].get("estado") == "fallo":
                informe["fallas"].append(f"carrusel: {informe['carrusel'].get('error')}")
    if publicar:
        guardar(mem)
        if informe["piezas"] or informe["descartadas"]:
            from reels import auditoria as AU
            AU.anotar("nacionales", {
                "candidatas": informe.get("candidatas"),
                "piezas": [{"titular": p.get("titular"), "categoria": p.get("categoria") or "general",
                            "seccion": p.get("seccion"), "viral": p.get("viral"),
                            "destinos": {r: (p.get(r) or {}).get("estado")
                                         for r in ("youtube", "web", "facebook", "tiktok_buzon") if p.get(r)}}
                           for p in informe["piezas"]],
                "descartadas": [{"titulo": d.get("titulo"), "motivo": d.get("motivo"),
                                 "categoria": d.get("categoria") or "general"} for d in informe["descartadas"]],
            })
    return informe


def resumen(inf: dict) -> str:
    l = [f"### Nacionales ({'PUBLICADO' if inf['publicar'] else 'simulación'}) — {inf['cuando']}", ""]
    if "candidatas" in inf:
        l.append(f"Candidatas de Infobae: {inf['candidatas']} · piezas: {len(inf['piezas'])} · "
                 f"descartadas por la IA: {len(inf['descartadas'])}")
        l.append("")
    for p in inf["piezas"]:
        redes = " · ".join(f"{k} {v.get('estado')}" for k, v in p.items()
                           if isinstance(v, dict) and "estado" in v)
        l.append(f"- **{p['titular']}** ({p['seccion']}, viral {p['viral']}, {p['nivel']}) — {redes}")
    for d in inf["descartadas"]:
        l.append(f"- ~~{d['titulo'][:90]}~~ — {d['motivo']}")
    if inf.get("ranking_variedad"):
        l.append("\n**Ranking de impacto (variedad):**")
        for cat, lista in inf["ranking_variedad"].items():
            for x in lista:
                l.append(f"- {cat} · **{x['impacto']}** · {x['titulo'][:80]} — {'; '.join(x['razones'][:4])}")
    if inf.get("senales"):
        l.append(f"\nSeñales: {inf['senales']}; notas por portal: {inf.get('fuentes_variedad') or {}}")
    if inf.get("carrusel"):
        c = inf["carrusel"]
        l.append(f"\nCarrusel de Instagram: {c.get('estado')} {c.get('motivo') or ''}"
                 f"{' (' + str(c.get('diapositivas')) + ' diapositivas)' if c.get('diapositivas') else ''}")
    for a in inf.get("avisos") or []:
        l.append(f"- (aviso) {a}")
    if inf["fallas"]:
        l.append("\n**Fallas:**")
        l += [f"- {f}" for f in inf["fallas"]]
    return "\n".join(l)


def main():
    entorno.consola_utf8()
    entorno.cargar()
    ap = argparse.ArgumentParser(description="Noticias nacionales: Infobae → web, Shorts, Facebook y carrusel.")
    ap.add_argument("--publicar", action="store_true", help="publicar de verdad (sin esto, simula)")
    ap.add_argument("--cuantos", type=int, default=0, help="piezas en esta pasada (0 = NAC_POR_PASADA)")
    ap.add_argument("--solo-carrusel", action="store_true", help="solo el carrusel (aunque no sean las 22)")
    ap.add_argument("--sin-carrusel", action="store_true")
    ap.add_argument("--esperar-carrusel", default="", help="HH:MM: esperar hasta esa hora para el carrusel")
    a = ap.parse_args()
    inf = pasada(a.publicar, a.cuantos, a.solo_carrusel, a.esperar_carrusel, not a.sin_carrusel)
    texto = resumen(inf)
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    # Falla la corrida (y llega el mail de GitHub) solo si algo NO salió: no por una nota descartada.
    return 1 if inf["fallas"] and a.publicar else 0


if __name__ == "__main__":
    sys.exit(main())
