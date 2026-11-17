# -*- coding: utf-8 -*-
"""VIRALES DEL CAMPO como REELS DE PRUEBA en @diarioyradioagro (16/11/2026).

Pedido del editor: «virales relacionados al campo, pero esos subilos como reels de prueba». Un reel de prueba de
Instagram lo ven solo los que NO siguen la cuenta: sirve para llegar a gente nueva sin cargarle el feed a los
seguidores (por eso no cuenta en la grilla reel/carrusel, no va a historias). Desde el 17/11/2026 sale también en la página de Facebook de agro como reel normal (AGRO_VIRALES_FB).

De dónde: los portales de variedad de nacionales (nacionales/categorias.bajar: TN, Infobae, Clarín, La Nación…),
lo que es del campo (animales de granja, tractores, cosechas, gauchos, tambos — CAMPO_VIRAL, o las palabras firmes
del campo) de las últimas HORAS, primero lo de la sección virales. Solo si la nota trae su PROPIO video (el lector de
nacionales: TN, JW Player con control de que sea de la nota), de 4 a 90 s, y no es de un medio de la competencia.
El texto lo escribe el guion de agro; el reel es el 4:5 de agro con el video entero y su sonido.

Horarios: AGRO_VIRALES («12:15,20:45»; "0" los apaga). Uno por horario, si hay. Memoria: mem["virales"] (las URL
publicadas, para no repetir) y mem["historias"][horario] con bloque «viral» (así el respaldo no lo repite).

17/11/2026 — LOS 11 REELS DE PRUEBA DEL DÍA (pedido del editor: «policiales agro: subir reels con video y usar los 11
reels de prueba por día que permite Instagram; los más virales; 4 corridas a las 10, 14, 18 y 22, 3-3-3-2; si no hay
de Chivilcoy y alrededores, provinciales o nacionales, también Córdoba, Santa Fe, Entre Ríos»). Medido ese día: en
36 h, de 1.558 notas, 6 policiales del campo y NINGUNO con video propio; el editor eligió completar con «cualquier
nota del campo con video». Entonces:
- Horarios: AGRO_PRUEBA_TANDAS («10:00*3,14:00*3,18:00*3,22:00*2», cada AGRO_PRUEBA_PASO = 20 min). AGRO_VIRALES,
  si está, manda (lista de horarios como antes).
- Candidatas, en NIVELES: 1) policiales del campo, 2) virales del campo, 3) cualquier nota del campo. Dentro de cada
  nivel, las MÁS COMPARTIDAS: cuántos portales cuentan el mismo hecho (nacionales/filtro.agrupar), de la zona de
  Chivilcoy > provincia > Córdoba/Santa Fe/Entre Ríos > el resto, la sección virales y lo más nuevo.
- Fuentes: los portales de nacionales, sus secciones de policiales, TN Campo y Clarín Rural, y los diarios de Santa
  Fe, Entre Ríos y Córdoba con RSS (La Capital, Aire de Santa Fe, Uno Santa Fe, Uno Entre Ríos, Cba24n). Estos
  últimos casi nunca traen video propio (YouTube, que desde la nube no se baja): sirven para encontrar el hecho y
  contar la cobertura; el video sale del portal que lo tenga (se prueban las otras notas del mismo hecho).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

HORAS = 36
REVISAR = 25          # candidatas que se abren buscando video (17/11: la mayoría no trae)
TANDAS_DEFECTO = "10:00*3,14:00*3,18:00*3,22:00*2"
PASO_DEFECTO = 20
# Además de los portales de nacionales (categorias.bajar): (categoría, nombre, vía, url, extra) de nacionales/portales.
REGIONALES = (
    ("policiales", "La Capital", "rss", "https://www.lacapital.com.ar/rss/home.xml", {}),
    ("policiales", "Aire de Santa Fe", "rss", "https://www.airedesantafe.com.ar/rss/policiales.xml", {}),
    ("policiales", "Uno Santa Fe", "rss", "https://www.unosantafe.com.ar/rss/policiales.xml", {}),
    ("policiales", "Uno Entre Ríos", "rss", "https://www.unoentrerios.com.ar/rss/policiales.xml", {}),
    ("policiales", "Cba24n", "rss", "https://www.cba24n.com.ar/rss", {}),
)
REGION = re.compile(r"\b(cordob\w*|santa fe|santafesin\w*|rosario|rafaela|venado tuerto|reconquista|villa maria|"
                    r"rio cuarto|san francisco|marcos juarez|entre rios|entrerrian\w*|parana|concordia|gualeguay\w*|"
                    r"concepcion del uruguay|victoria|la pampa|pampean\w*)\b")
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


def _horas(crudo: str) -> list:
    salida = []
    for parte in crudo.split(","):
        h, _, m = parte.strip().partition(":")
        try:
            if 0 <= int(h) < 24 and 0 <= int(m or 0) < 60:
                salida.append((int(h), int(m or 0)))
        except ValueError:
            continue
    return salida


def horas_virales() -> list:
    """Los horarios de los reels de prueba: AGRO_VIRALES (lista) si está; si no, las tandas de AGRO_PRUEBA_TANDAS
    («10:00*3,…»: 3 reels desde las 10, uno cada AGRO_PRUEBA_PASO minutos)."""
    import os
    crudo = (os.environ.get("AGRO_VIRALES") or "").strip()
    if crudo.lower() in ("0", "no", "off"):
        return []
    if crudo:
        return sorted(set(_horas(crudo)))
    try:
        paso = max(5, int(os.environ.get("AGRO_PRUEBA_PASO") or PASO_DEFECTO))
    except ValueError:
        paso = PASO_DEFECTO
    salida = []
    for tanda in (os.environ.get("AGRO_PRUEBA_TANDAS") or TANDAS_DEFECTO).split(","):
        hora, _, cuantos = tanda.strip().partition("*")
        try:
            n = max(1, int(cuantos or 1))
        except ValueError:
            n = 1
        for h, m in _horas(hora)[:1]:
            for k in range(n):
                t = h * 60 + m + k * paso
                if t < 24 * 60:
                    salida.append((t // 60, t % 60))
    return sorted(set(salida))


SECCIONES_FUERA = {"internacionales"}


def nivel(nota: dict) -> int | None:
    """0 = policial del campo, 1 = viral del campo, 2 = otra nota del campo; None = no es del campo."""
    from agro import fuentes as FU
    texto = f"{nota.get('titulo') or ''}. {nota.get('resumen') or ''}"
    if re.search(NO_CAMPO, _sin_tildes(texto)):
        return None
    # 17/11: lo del exterior no es el campo de acá (la simulación trajo a Trump «sin rodeos», frigoríficos de
    # Centroamérica, la aduana de Guatemala).
    if (nota.get("categoria") or "") in SECCIONES_FUERA:
        return None
    if FU.es_policial_rural(texto):
        return 0
    if es_viral_del_campo(nota):
        return 1
    if FU.es_del_campo(texto):
        return 2
    return None


def puntaje(nota: dict, cobertura: int, ts: float) -> int:
    """Las más compartidas primero: portales que cuentan el hecho, cercanía (zona > provincia > Córdoba, Santa Fe,
    Entre Ríos), la sección virales y lo más nuevo."""
    from nacionales import prueba as NP
    from nacionales import filtro as F
    texto = F.norm(f"{nota.get('titulo') or ''} {nota.get('resumen') or ''}")
    puntos = 10 * cobertura
    if NP._zona_cerca().search(texto):
        puntos += 30
    elif NP.PROVINCIA.search(texto):
        puntos += 15
    elif REGION.search(_norm(texto)):
        puntos += 10
    if nota.get("categoria") == "virales":
        puntos += 10
    horas = max(0.0, (ts - (nota.get("fecha") or ts)) / 3600)
    return puntos + max(0, 10 - round(horas))


def _bajar_todo(log=print) -> list:
    from nacionales import categorias as CAT
    from nacionales import portales as PO
    from nacionales import prueba as NP
    notas, fallas, _ = CAT.bajar()
    extra = tuple(NP.FUENTES_POLICIALES) + (("campo", "TN", "rss", PO.TN.format("campo"), {}),
                                            ("campo", "Clarín", "rss", PO.CLARIN.format("rural"), {})) + REGIONALES
    mas, fallas2, _ = PO.bajar(extra)
    if fallas or fallas2:
        log(f"   reels de prueba: no contestaron {len(fallas) + len(fallas2)} fuentes")
    vistas, salida = set(), []
    for n in notas + mas:
        if n.get("url") and n["url"] not in vistas:
            vistas.add(n["url"])
            salida.append(n)
    return salida


def candidatas(ahora: datetime, notas=None, mem: dict = None, log=print) -> list:
    """Una por hecho, del campo, de las últimas HORAS y sin lo ya publicado (acá o en el feed): primero los policiales
    del campo, después los virales del campo, después cualquier nota del campo; dentro de cada nivel, las más
    compartidas. Cada una trae `otras_urls` (el mismo hecho en otros portales: ahí se busca el video si la elegida
    no lo tiene)."""
    from nacionales import filtro as F
    from nacionales import prueba as NP
    from nacionales import portales as PO
    if notas is None:
        notas = _bajar_todo(log)
    mem = mem or {}
    vistas = set((mem.get("virales") or {})) | {p.get("url") for p in mem.get("elegidas") or []}
    ts = ahora.timestamp()
    recientes = [n for n in notas if n.get("url") and n.get("titulo")
                 and (not n.get("fecha") or ts - n["fecha"] <= HORAS * 3600)]
    salida = []
    for grupo in F.agrupar(recientes):
        if any(n["url"] in vistas for n in grupo):
            continue                                   # ese hecho ya salió
        niveles = [nv for nv in (nivel(n) for n in grupo) if nv is not None]
        if not niveles:
            continue
        mejor = max(grupo, key=lambda x: (nivel(x) is not None, NP.ORDEN_VIDEO.get(PO.fuente_de(x), 0),
                                          x.get("categoria") == "virales", x.get("fecha") or 0))
        otras = [x["url"] for x in grupo if x is not mejor]
        salida.append(dict(mejor, nivel=min(niveles), cobertura=len(grupo), otras_urls=otras[:3],
                           puntos=puntaje(mejor, len(grupo), ts)))
    salida.sort(key=lambda c: (c["nivel"], -c["puntos"], -(c.get("fecha") or 0)))
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
        # La nota y, si no trae video, la misma noticia en otro portal (17/11/2026).
        for k, url in enumerate([n["url"]] + list(n.get("otras_urls") or [])[:2]):
            try:
                ficha = leer(url) or {}
            except Exception:                              # noqa: BLE001
                continue
            if not ficha.get("video") or COMP.de_la_nota({**n, "url": url, "cuerpo": ficha.get("texto", "")}):
                continue
            clip = bajar(ficha["video"], carpeta / f"viral_{i:02d}_{k}_clip.mp4")
            if clip:
                if url != n["url"]:                      # el crédito es del portal que tiene el video
                    n = dict(n, url=url, url_hecho=n["url"], fuente=PO.fuente_de({"url": url}),
                             titulo=ficha.get("titulo") or n["titulo"], resumen=ficha.get("resumen") or n.get("resumen"))
                return n, ficha, clip
    return None


def a_facebook() -> bool:
    """17/11/2026 (pedido del editor: «lo mismo para los reels de prueba de @diarioyradioagro, al Facebook de
    agro»): el viral sale también en la página de Facebook de agro, como reel NORMAL (la API de Facebook no
    tiene reels de prueba). AGRO_VIRALES_FB=0 lo apaga."""
    import os
    return (os.environ.get("AGRO_VIRALES_FB") or "1").strip() != "0"


def publicar_prueba(mp4: Path, caption: str, portada: str, marca: str, alto: int = 1350, duracion: float = 0,
                    titular: str = "") -> dict:
    """El reel de PRUEBA en el Instagram de agro (solo lo ven los que no siguen la cuenta) y el mismo reel en la
    página de Facebook de agro. Una falla en una red no frena la otra."""
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
    salida = {}
    with PUB.credenciales_agro():
        uid, tok = os.environ.get("INSTAGRAM_USER_ID", ""), os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        try:
            params = IG.contenedor_reel(url, caption, prueba=True, portada=portada_url)
            try:
                cid = PB._contenedor_listo(uid, tok, params)
            except PB.FalloRed:
                params.pop("cover_url", None)
                cid = PB._contenedor_listo(uid, tok, params)
            salida["instagram_prueba"] = {"id": PB._publicar_contenedor(uid, tok, cid, caption) or None}
        except Exception as e:                             # noqa: BLE001
            salida["instagram_prueba"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        if a_facebook():
            salida["facebook"] = publicar_facebook(Path(mp4), caption, alto, duracion, titular)
    return salida


def publicar_facebook(mp4: Path, caption: str, alto: int = 1350, duracion: float = 0, titular: str = "",
                      lugar=None, publicar_fn=None) -> dict:
    """El reel en la página de Facebook de AGRO (llamar adentro de credenciales_agro). Respeta el tope de reels de
    la página en 24 h."""
    from reels import publicador as PB
    try:
        hay = (lugar or PB._lugar_en_facebook)()
        if hay and hay[0] >= hay[1]:
            return {"omitido": f"la página ya tiene {hay[0]} reels en 24 h (tope {hay[1]})"}
        pieza = {"descripcion_tiktok": caption, "formato": "reel", "video": {"alto": alto, "duracion": duracion},
                 "guion": {"titular": titular, "bajada": ""}}
        return dict((publicar_fn or PB.publicar_facebook)(pieza, Path(mp4), "") or {})
    except Exception as e:                                 # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


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
    conteos["Notas del campo encontradas"] = len(cands)
    conteos["Policiales / virales / otras del campo"] = " / ".join(
        str(sum(1 for c in cands if c.get("nivel", 1) == k)) for k in (0, 1, 2))
    log(f"   {len(cands)} hechos del campo en los portales (policiales {sum(1 for c in cands if c.get('nivel', 1) == 0)})")
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
            if n.get("url_hecho"):                     # el hecho, aunque el video haya salido de otro portal
                mem["virales"][n["url_hecho"]] = ahora.isoformat(timespec="minutes")
            if publicar:
                entrada["publicado"] = {"estado": "publicando"}
                mem.setdefault("historias", {})[horario.isoformat()] = entrada
                PA.guardar(mem, ahora, ruta_mem)
                try:
                    if publicador:
                        res = publicador(Path(reel["archivo"]), caption, reel.get("vista") or "", rep["id"])
                    else:
                        res = publicar_prueba(Path(reel["archivo"]), caption, reel.get("vista") or "", rep["id"],
                                              alto=reel.get("alto") or 1350, duracion=reel.get("duracion") or 0,
                                              titular=g["titular"])
                except Exception as e:                     # noqa: BLE001
                    res = {"instagram_prueba": {"error": f"{type(e).__name__}: {str(e)[:200]}"}}
                entrada["publicado"] = res
                conteos["Publicado"] = json.dumps(res, ensure_ascii=False)[:200]
                log(f"   Instagram (prueba) y Facebook: {res}")
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
