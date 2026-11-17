# -*- coding: utf-8 -*-
"""VIRALES DEL CAMPO como REELS DE PRUEBA en @diarioyradioagro (16/11/2026).

Pedido del editor: «virales relacionados al campo, pero esos subilos como reels de prueba». Un reel de prueba de
Instagram lo ven solo los que NO siguen la cuenta: sirve para llegar a gente nueva sin cargarle el feed a los
seguidores (por eso no cuenta en la grilla reel/carrusel, no va a Facebook ni a historias).

De dónde: los portales de variedad de nacionales (nacionales/categorias.bajar: TN, Infobae, Clarín, La Nación…),
lo que es del campo (animales de granja, tractores, cosechas, gauchos, tambos — CAMPO_VIRAL, o las palabras firmes
del campo) de las últimas HORAS, primero lo de la sección virales. Solo si la nota trae su PROPIO video (el lector de
nacionales: TN, JW Player con control de que sea de la nota), de 4 a 90 s, y no es de un medio de la competencia.
El texto lo escribe el guion de agro; el reel es el 4:5 de agro con el video entero y su sonido.

Horarios: AGRO_VIRALES («12:15,20:45»; "0" los apaga). Uno por horario, si hay. Memoria: mem["virales"] (las URL
publicadas, para no repetir) y mem["historias"][horario] con bloque «viral» (así el respaldo no lo repite).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

HORAS = 36
REVISAR = 12
# Lo del campo que se VE en un video: animales de granja, máquinas, gente de campo. En minúscula a propósito (se
# busca sin pasar a minúscula): «Cordero» o «Toro» con mayúscula son apellidos o marcas. «Vaca Muerta» no.
CAMPO_VIRAL = re.compile(
    r"\b(vacas?(?! muerta)|toros?|terner[oa]s?|novill[oa]s?|caballos?|yeguas?|potrill[oa]s?|ovejas?|corderos?|cabras?|"
    r"chanchos?|cerdos?|lechones?|gallinas?|pollitos?|granjas?|granjer[oa]s?|tractor(es)?|cosechadoras?|sembradoras?|"
    r"gauchos?|tambos?|tamber[oa]s?|apicultor\w*|colmenas?|abejas?|chacras?|peon(es)? rural(es)?|arreos?|jineteadas?|"
    r"domadores?|productor(es)? rural(es)?|productor(es)? agropecuari[oa]s?|ganado|ganader[oa]s?|"
    r"campo argentino|vida en el campo|en el campo)\b")
# Que sea un VIRAL: la sección de virales del portal, o el título lo cuenta como tal.
VIRAL = re.compile(r"\b(video|viral\w*|insolit\w*|increibl\w*|impactant\w*|emotiv\w*|conmovedor\w*|sorprend\w*|curios\w*|"
                   r"asombr\w*|tierno|redes|tiktok|instagram|furor|reproducciones|se volvio|enternec\w*|hilarante|"
                   r"inesperad\w*|rescat\w*|momento en que|asi fue|mira)\b", re.I)
NO_CAMPO = re.compile(r"campo de (juego|futbol|deportes|batalla|concentraci)|cancha|mundial|seleccion|elecciones|"
                      r"partido|torneo|goles?\b", re.I)


def _sin_tildes(t: str) -> str:
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()


def _norm(t: str) -> str:
    return _sin_tildes(t).lower()


def es_viral_del_campo(nota: dict) -> bool:
    """Un viral (sección virales o título de viral) que muestra algo del campo."""
    texto = _sin_tildes(f"{nota.get('titulo') or ''}. {nota.get('resumen') or ''}")
    if NO_CAMPO.search(texto):
        return False
    campo = CAMPO_VIRAL.search(texto[:1].lower() + texto[1:])     # la primera palabra del título, en minúscula
    return bool(campo) and (nota.get("categoria") == "virales" or bool(VIRAL.search(texto)))


def horas_virales() -> list:
    import os
    crudo = (os.environ.get("AGRO_VIRALES") or "12:15,20:45").strip()
    if crudo.lower() in ("0", "no", "off"):
        return []
    salida = []
    for parte in crudo.split(","):
        h, _, m = parte.strip().partition(":")
        try:
            if 0 <= int(h) < 24 and 0 <= int(m or 0) < 60:
                salida.append((int(h), int(m or 0)))
        except ValueError:
            continue
    return sorted(set(salida))


def candidatas(ahora: datetime, notas=None, mem: dict = None, log=print) -> list:
    """Las notas del campo de los portales de variedad, sin las ya publicadas: primero las de virales, después las
    más nuevas."""
    if notas is None:
        from nacionales import categorias as CAT
        notas, fallas, _ = CAT.bajar()
        if fallas:
            log(f"   virales: no contestaron {len(fallas)} portales")
    mem = mem or {}
    vistas = set((mem.get("virales") or {})) | {p.get("url") for p in mem.get("elegidas") or []}
    ts = ahora.timestamp()
    salida = [n for n in notas if n.get("url") and n["url"] not in vistas and n.get("titulo")
              and (not n.get("fecha") or ts - n["fecha"] <= HORAS * 3600) and es_viral_del_campo(n)]
    salida.sort(key=lambda n: (n.get("categoria") == "virales", n.get("fecha") or 0), reverse=True)
    return salida


def _clip(url_video: str, destino: Path):
    from agro import pasada as PA
    return PA._clip_de_la_fuente({}, {"video": url_video, "video_seg": 0}, destino)


def elegir(cands: list, carpeta: Path, leer=None, bajar=None, log=print):
    """(nota, ficha, clip) de la primera candidata con video propio corto que no sea de la competencia, o None."""
    from nacionales import portales as PO
    from reels import competencia as COMP
    leer = leer or PO.leer
    bajar = bajar or _clip
    for i, n in enumerate(cands[:REVISAR]):
        if COMP.de_la_nota(n):
            continue
        try:
            ficha = leer(n["url"]) or {}
        except Exception:                                  # noqa: BLE001
            continue
        if not ficha.get("video") or COMP.de_la_nota({**n, "cuerpo": ficha.get("texto", "")}):
            continue
        clip = bajar(ficha["video"], carpeta / f"viral_{i:02d}_clip.mp4")
        if clip:
            return n, ficha, clip
    return None


def publicar_prueba(mp4: Path, caption: str, portada: str, marca: str) -> dict:
    """El reel de PRUEBA en el Instagram de agro (solo lo ven los que no siguen la cuenta)."""
    import os
    from agro import publicar as PUB
    from reels import instagram as IG
    from reels import publicador as PB
    url = PB.subir_a_release(Path(mp4), f"agro_viral_{marca}.mp4")
    portada_url = ""
    if portada and Path(portada).is_file():
        try:
            portada_url = PB.subir_a_release(Path(portada), f"agro_viral_{marca}.jpg")
        except Exception:                                  # noqa: BLE001
            portada_url = ""
    with PUB.credenciales_agro():
        uid, tok = os.environ.get("INSTAGRAM_USER_ID", ""), os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        params = IG.contenedor_reel(url, caption, prueba=True, portada=portada_url)
        try:
            cid = PB._contenedor_listo(uid, tok, params)
        except PB.FalloRed:
            params.pop("cover_url", None)
            cid = PB._contenedor_listo(uid, tok, params)
        return {"instagram_prueba": {"id": PB._publicar_contenedor(uid, tok, cid, caption) or None}}


def pasada(publicar: bool, horario: datetime, log=print, publicador=None, carpeta: Path = None, ahora: datetime = None,
           notas=None, leer=None, bajar=None, generar=None, armar_reel=None) -> Path:
    from agro import captura as CA
    from agro import guion as GU
    from agro import informe as INF
    from agro import pasada as PA
    from agro import seleccion as SE
    ahora = ahora or datetime.now(PA.TZ_AR)
    carpeta = Path(carpeta or PA.SALIDA / ahora.strftime("%Y-%m-%d_%H%M_viral"))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = PA.MEMORIA_REAL if publicar else PA.MEMORIA
    mem = PA.cargar(ruta_mem)
    conteos = {}
    log(f"[agro] VIRAL DEL CAMPO (reel de prueba) {'REAL' if publicar else 'SIMULADO'} {ahora:%d/%m %H:%M}")
    cands = candidatas(ahora, notas, mem, log)
    conteos["Virales del campo encontrados"] = len(cands)
    log(f"   {len(cands)} notas del campo en los portales")
    elegida = elegir(cands, carpeta, leer, bajar, log) if cands else None
    entrada = {"bloque": "viral", "items": []}
    if not elegida:
        conteos["No se publicó"] = "ninguna trae video propio corto"
        log("   ninguna trae video propio: no sale")
    else:
        n, ficha, clip = elegida
        rep = {"id": CA.id_de(n["url"]), "titulo": n["titulo"], "descripcion": n.get("resumen") or "", "url": n["url"],
               "fuente": n.get("fuente") or "", "tipo_fuente": "medio"}
        s = {"subtema": "agro", "ai_score": SE.score_min(), "tema_doc": "viral", "explicacion": "viral del campo"}
        g = (generar or GU.generar)(rep, ficha.get("texto") or n.get("cuerpo") or "", [], s)
        if not g.get("apta"):
            conteos["No se publicó"] = f"el guion no la dio por apta ({g.get('motivo')})"
        else:
            imagen = PA._bajar(ficha.get("imagen") or n.get("imagen") or "", carpeta / "viral_foto.jpg") or None
            reel = (armar_reel or PA.GU_reel)(g, imagen, carpeta / "viral.mp4", "video", n.get("fuente") or "", clip=clip,
                                              tema=PA.tema_siguiente(mem))
            caption = GU.texto_red(g, "instagram")
            item = {"titular": g["titular"], "url": n["url"], "fuente": n.get("fuente"), "reel": reel.get("archivo"),
                    "duracion": reel.get("duracion")}
            entrada["items"].append(item)
            conteos["Reel"] = f"{g['titular']} ({n.get('fuente')}, {reel.get('duracion', 0):.0f} s)"
            log(f"   reel de prueba: {g['titular']} ({reel.get('duracion', 0):.0f} s)")
            (carpeta / "texto_viral.txt").write_text(caption, encoding="utf-8")
            mem.setdefault("virales", {})[n["url"]] = ahora.isoformat(timespec="minutes")
            if publicar:
                entrada["publicado"] = {"estado": "publicando"}
                mem.setdefault("historias", {})[horario.isoformat()] = entrada
                PA.guardar(mem, ahora, ruta_mem)
                try:
                    res = (publicador or publicar_prueba)(Path(reel["archivo"]), caption, reel.get("vista") or "",
                                                          rep["id"])
                except Exception as e:                     # noqa: BLE001
                    res = {"instagram_prueba": {"error": f"{type(e).__name__}: {str(e)[:200]}"}}
                entrada["publicado"] = res
                conteos["Publicado"] = json.dumps(res, ensure_ascii=False)[:200]
                log(f"   Instagram (prueba): {res}")
    if publicar and not entrada.get("publicado"):
        entrada["publicado"] = {"omitido": conteos.get("No se publicó", "")}   # el respaldo no lo vuelve a buscar
    if publicar:
        mem.setdefault("historias", {})[horario.isoformat()] = entrada
    limite = (ahora - timedelta(days=10)).isoformat()
    mem["virales"] = {k: v for k, v in (mem.get("virales") or {}).items() if v >= limite}
    PA.guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "viral del campo (reel de prueba)", "conteos": conteos,
           "fuentes": [], "piezas": [], "descartadas": [], "grupos_duplicados": [], "publicar": publicar,
           "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": HORAS}}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)
