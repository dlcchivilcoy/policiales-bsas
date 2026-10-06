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
- Las fotos de Infobae NO se usan nunca: placa propia (nacionales/placa.py).

Cómo queda, por pasada (corre en las mismas pasadas que policiales, en un trabajo aparte):
1. Infobae (nacionales/infobae.py) → filtro y orden por relevancia y cobertura (filtro.py).
2. Hasta NAC_POR_PASADA notas nuevas (3), sin pasar de NAC_POR_DIA (12) ni repetir un tema de
   las últimas 24 h. Guion con la IA (guion.py); la que no sirve queda anotada y no se reintenta.
3. Por pieza, en orden: Short en YouTube (con el link de su nota) → nota en la web (sección
   Nacionales, fuera de la portada, con el Short adentro) → Facebook, SOLO las más virales: hasta
   NAC_FB_POR_PASADA (2) y NAC_FB_POR_DIA (8). Es un posteo con la PLACA y el link a la nota:
   Facebook no lee bien la foto de una nota de Wix recién publicada (memoria del bot, «FB
   previsualización misma foto») y si se postea solo el link sale con una foto equivocada.
   5 minutos entre pieza y pieza.
4. Desde las 22 (la pasada de las 21:05 espera con --esperar-carrusel 22:00), el carrusel de
   Instagram con lo que salió desde el carrusel anterior: tapa + hasta 9 diapositivas. Es un
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
from nacionales import filtro as F
from nacionales import guion as NG
from nacionales import infobae as IB
from nacionales import placa as P
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
CARRUSEL_MAX = 9            # diapositivas de notas (+ la tapa = 10, el tope de Instagram)
CARRUSEL_MIN = 2
HORA_CARRUSEL = (22, 0)
MINUTOS_ENTRE_PIEZAS = 5
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


def armar(nota: dict, carpeta: Path, redactar=None) -> dict:
    """Guion + Short + placa de Facebook + imagen de la web. Lanza si la IA no contesta."""
    g = NG.generar(nota, redactar)
    pieza = {"nota": nota, "guion": g, "url_original": nota["url"],
             "web": {"titulo": g["titulo_web"], "cuerpo": g["nota_web"]}}
    if not g["apta"]:
        return pieza
    carpeta.mkdir(parents=True, exist_ok=True)
    base = carpeta / WEB.slugify(g["titular"], 50)
    semilla = _semilla(nota["url"])
    from reels import reel_bot as R
    fondo = P.guardar_fondo(g["seccion"], base.with_name(base.name + "_fondo.jpg"), semilla=semilla)
    pieza["video"] = R.armar({"volanta": g["volanta"], "titular": g["titular"], "bajada": g["bajada"]},
                             base.with_suffix(".mp4"), foto=fondo)
    pieza["placa"] = pieza["video"].get("placa")
    pieza["slide"] = str(P.slide(g["seccion"], g["volanta"], g["titular"],
                                 base.with_name(base.name + "_facebook.jpg"), sitio=WEB.SITIO, semilla=semilla))
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
    url_prev = url_web_prevista(pieza)
    meta = meta_youtube(pieza, url_prev)
    res = {}
    if not publicar:
        res["youtube"] = {"estado": "simulado", "titulo": meta["snippet"]["title"]}
        res["web"] = {"estado": "simulado", "url": url_prev}
        if a_facebook:
            res["facebook"] = {"estado": "simulado", "texto": texto_facebook(pieza, url_prev)}
        return res

    res["youtube"] = _resultado(PUB.publicar_youtube, pieza, mp4, meta)
    yt_id = res["youtube"].get("id") if _ok(res["youtube"]) else ""

    def _web():
        nombre = f"nacional_{hashlib.sha1(pieza['url_original'].encode()).hexdigest()[:10]}_web.jpg"
        pieza["imagen_url"] = PUB.subir_a_release(Path(pieza["portada_web"]), nombre)
        return WEB.publicar(lambda m, u, **kw: PUB._pedir(m, u, "", **kw), pieza, yt_id or "",
                            categorias=[WEB.NACIONALES_ID, WEB.NACIONALES_AUTO_ID])
    res["web"] = _resultado(_web) if WEB.activa() else {"estado": "apagada"}
    url_web = res["web"].get("url") if _ok(res["web"]) else ""
    if yt_id and not url_web:
        meta_sec = meta_youtube(pieza, SECCION_WEB)
        res["youtube"]["descripcion"] = _resultado(_yt_cambiar_descripcion, yt_id, meta_sec)["estado"]

    if a_facebook:
        # Sin nota en la web no hay a dónde mandar a la gente: el posteo lleva la sección.
        res["facebook"] = _resultado(publicar_foto_facebook, Path(pieza["slide"]),
                                     texto_facebook(pieza, url_web or SECCION_WEB))
    return res


# =============================================================================
# Carrusel de Instagram (22 h)
# =============================================================================

def para_el_carrusel(mem: dict) -> list:
    """Lo publicado desde el último carrusel (con su nota en la web), de lo más viral a lo menos."""
    ya = {u for c in mem["carruseles"].values() if _ok(c) for u in c.get("piezas") or []}
    listas = [(u, p) for u, p in mem["piezas"].items() if u not in ya and _ok(p.get("web"))]
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
    jpgs = [P.portada_carrusel([p["titular"] for _, p in elegidas], ahora, carpeta / "carrusel_00_tapa.jpg",
                               semilla=int(ahora.strftime("%Y%m%d")))]
    for i, (u, p) in enumerate(elegidas, 1):
        jpgs.append(P.slide(p.get("seccion") or "Nacionales", p.get("volanta") or "", p["titular"],
                            carpeta / f"carrusel_{i:02d}.jpg", sitio=WEB.SITIO, idx=i, total=total,
                            semilla=_semilla(u)))
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

def pasada(publicar: bool, cuantos: int = 0, solo_carrusel: bool = False, esperar_carrusel: str = "",
           con_carrusel: bool = True, redactar=None, notas=None) -> dict:
    mem = cargar()
    ahora = _ahora()
    dia = ahora.date().isoformat()
    carpeta = SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    informe = {"cuando": ahora.isoformat(timespec="seconds"), "publicar": publicar, "piezas": [],
               "descartadas": [], "fallas": []}

    if not solo_carrusel:
        if notas is None:
            notas, fallas = IB.bajar()
            # Una sección caída es un aviso, no una falla: las otras alcanzan.
            informe["avisos"] = [f"Infobae {f}" for f in fallas]
            if not notas:
                raise RuntimeError("Infobae no devolvió ninguna nota: " + "; ".join(fallas))
        cands = F.candidatas(notas, ahora.timestamp())
        informe["candidatas"] = len(cands)
        hechas = len(de_hoy(mem, dia))
        cupo = min(cuantos or _entero("NAC_POR_PASADA", POR_PASADA), _entero("NAC_POR_DIA", POR_DIA) - hechas)
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

        fb = para_facebook(armadas, mem, dia)
        for i, pieza in enumerate(armadas):
            if i and publicar:
                _dormir(MINUTOS_ENTRE_PIEZAS * 60)
            nota, g = pieza["nota"], pieza["guion"]
            res = publicar_pieza(pieza, nota["url"] in fb, publicar)
            fila = {"titulo_original": nota["titulo"], "titular": g["titular"], "volanta": g["volanta"],
                    "seccion": g["seccion"], "tema": nota.get("tema") or [], "viral": g["viral"],
                    "puntos": nota.get("puntos"), "nivel": nota.get("nivel"), "cobertura": nota.get("cobertura"),
                    "dia": dia, "cuando": _ahora().isoformat(timespec="seconds"), "via": g.get("via"),
                    "copia": (g.get("copia") or {}).get("racha"), **res}
            informe["piezas"].append(fila)
            for red, r in res.items():
                if r.get("estado") == "fallo":
                    informe["fallas"].append(f"{red}: «{g['titular'][:50]}»: {r.get('error')}")
            if publicar:
                mem["piezas"][nota["url"]] = fila
                guardar(mem)                         # tras cada pieza: un corte no borra lo hecho

    if con_carrusel:
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
