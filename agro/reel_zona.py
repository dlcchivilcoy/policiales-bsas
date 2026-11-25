# -*- coding: utf-8 -*-
"""LOS REELS DE DATOS DE LA ZONA, en colaboración @diarioyradioagro + @diarioyradio (20/11/2026).

Pedido del editor: «para mis 2 redes armame reels como el que me armaste de lluvias, usando la info que usaste y
también te podés basar en páginas como argenfields — es decir armar un reel con video o imagen que van pasando —
fijate también si podés hacerlo de otras temáticas que tengan potencial de viralidad — y estos reels subilos en
colaboración con ambas cuentas — además intentá subirlos entre las 11 y 12 del mediodía».

UN reel por día, entre las 11 y las 12 (cron-job.org 11:10 y respaldo de GitHub; pasadas las 12:30 no sale nada,
porque GitHub llega a atrasarse horas). Cada día un TEMA distinto:

  - lluvia: si en Chivilcoy se esperan al menos ZONA_LLUVIA_MM (10) en 72 h, el reel del mapa de lluvia (el de
    agro/reel_clima.py). Ese día la tarde ya no repite el reel del clima.
  - nino: El Niño / La Niña y lo que le hizo a los rindes de Chivilcoy y la zona (cada 10 días, mientras dure).
  - de ArgenFields (agro/datos/argenfields.json, tools/traer_argenfields.py): el ranking de la mejor tierra de la
    zona, dónde rinde más la soja / el trigo / el maíz, cada cultivo campaña por campaña, el suelo de Chivilcoy,
    las emergencias por sequía y las «gemelas» de Chivilcoy en Estados Unidos. Rotan: el usado hace más tiempo,
    nunca antes de DIAS_SIN_REPETIR días.

El video: diapositivas que pasan. Arriba, un video ilustrativo real del banco (agro/banco_video.py: Wikimedia
Commons, licencia libre, con crédito) y abajo el dato, con el número que va contando; los rankings y las series son
barras que crecen. Sin IA en ningún lado: los números son de ArgenFields (INTA, Ministerio de Agricultura, NOAA) y
del pronóstico de MET Norway. Se cita la fuente en el reel y en el texto.

Dónde sale: Instagram de @diarioyradioagro con @diarioyradio de COLABORADOR (la invitación la acepta sola la cuenta
del diario, agro/publicar.aceptar_colab) y Facebook en LAS DOS páginas (Facebook no tiene colab). Como todo reel de
agro, también como historia de agro. Sin web ni YouTube.

    python -m agro.reel_zona                    # simula: arma el reel de hoy en salida_agro/zona_*
    python -m agro.reel_zona --tema trigo_zona  # un tema a elección (simulando)
    python -m agro.reel_zona --todos            # arma TODOS los temas (para mirarlos)
    python -m agro.reel_zona --publicar         # en la nube

Memoria: estado/agro_zona.json. Interruptores: AGRO_ZONA=0 apaga todo; AGRO_ZONA_COLAB=0 sale solo en agro;
AGRO_ZONA_FB_DIARIO=0 no lo sube a la página del diario; AGRO_ZONA_VENTANA="11:00-12:30".
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import diseno as D  # noqa: E402

TZ_AR = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).resolve().parent.parent
DATOS = Path(__file__).resolve().parent / "datos" / "argenfields.json"
MEMORIA = RAIZ / "estado" / "agro_zona.json"
SALIDA = RAIZ / "salida_agro"
FPS = 24
FUNDIDO = 0.35
CONTAR = 1.1                 # segundos que tarda el número en llegar a su valor
CRECER = 1.4                 # segundos que tardan las barras en crecer
ALTO_VIDEO = 810             # 1080x810 arriba (los videos del banco vienen así)
DIAS_SIN_REPETIR = 10
DIAS_DATOS_VIEJOS = 45       # El Niño: si la copia de ArgenFields es más vieja, ese tema no va
WHATSAPP = "2346-533450"
FUENTE_CORTA = "Fuente: ArgenFields, con datos del INTA y del Ministerio de Agricultura"
CELESTE = (120, 180, 255)
GRIS_BARRA = (92, 98, 108)
ORDEN = ("trigo_zona", "soja_perdidas", "tierra", "trigo_campana", "soja_zona", "trigo_siglo", "gemelas",
         "maiz_perdidas", "sequias", "soja_campana", "maiz_zona", "maiz_siglo", "trigo_historia", "maiz_campana",
         "soja_historia", "suelo", "maiz_historia")
RINDES = Path(__file__).resolve().parent / "datos" / "rindes_zona.json"
FUENTE_ABIERTOS = "Fuente: ArgenFields, datos abiertos (CC BY 4.0), con datos de Estimaciones Agrícolas del MAGyP"
NOMBRE_CULTIVO = {"soja": "soja", "trigo": "trigo", "maiz": "maíz", "cebada": "cebada", "girasol": "girasol"}
VIDEO_CULTIVO = {"soja": "cosecha", "trigo": "trigo", "maiz": "maiz", "cebada": "trigo", "girasol": "girasol"}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Interruptores
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _var(nombre: str, defecto: str) -> str:
    return (os.environ.get(nombre) or defecto).strip()


def activo() -> bool:
    return _var("AGRO_ZONA", "1") != "0"


# 25/11/2026 (el editor: «sacá las colaboraciones automatizadas con la otra cuenta»): el reel de la zona sale solo en
# @diarioyradioagro, sin @diarioyradio de colaborador y sin la copia en la página de Facebook del diario.
# AGRO_ZONA_COLAB=1 y AGRO_ZONA_FB_DIARIO=1 los vuelven.
def con_colab() -> bool:
    return _var("AGRO_ZONA_COLAB", "0") == "1"


def fb_diario() -> bool:
    return _var("AGRO_ZONA_FB_DIARIO", "0") == "1"


def lluvia_min() -> float:
    try:
        return float(_var("ZONA_LLUVIA_MM", "10"))
    except ValueError:
        return 10.0


def ventana(dia) -> tuple:
    """(desde, hasta) de ese día: fuera de esto la corrida no publica."""
    txt = _var("AGRO_ZONA_VENTANA", "11:00-12:30")
    try:
        a, b = [datetime.combine(dia, datetime.strptime(x.strip(), "%H:%M").time(), TZ_AR) for x in txt.split("-")]
        return a, b
    except ValueError:
        return (datetime.combine(dia, datetime.strptime("11:00", "%H:%M").time(), TZ_AR),
                datetime.combine(dia, datetime.strptime("12:30", "%H:%M").time(), TZ_AR))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Memoria
# ─────────────────────────────────────────────────────────────────────────────────────────────
def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads(Path(ruta or MEMORIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"reels": []}


def guardar(mem: dict, ruta: Path = None) -> None:
    ruta = Path(ruta or MEMORIA)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    mem["reels"] = (mem.get("reels") or [])[-120:]
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=1), encoding="utf-8")


def ya_hoy(mem: dict, dia: str) -> bool:
    return any(r.get("dia") == dia and r.get("publicado") for r in mem.get("reels") or [])


def lluvia_hoy(dia: str, ruta: Path = None) -> bool:
    """¿El reel de la zona de hoy fue el de la lluvia? (agro/reel_clima.py no repite el reel del clima a la tarde)."""
    return any(r.get("dia") == dia and r.get("tema") == "lluvia" and r.get("publicado")
               for r in cargar(ruta).get("reels") or [])


def ultimo_uso(mem: dict) -> dict:
    salida = {}
    for r in mem.get("reels") or []:
        if r.get("publicado") or r.get("simulado_cuenta"):
            salida[r["tema"]] = max(salida.get(r["tema"], ""), r.get("dia", ""))
    return salida


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Los datos
# ─────────────────────────────────────────────────────────────────────────────────────────────
def datos_argenfields(ruta: Path = None) -> dict:
    try:
        return json.loads(Path(ruta or DATOS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"partidos": {}}


def _coma(x: float, dec: int = 1) -> str:
    """27.5 → «27,5»; 41037 → «41.037»."""
    if x is None:
        return "—"
    if dec == 0 or float(x).is_integer():
        return f"{round(x):,}".replace(",", ".")
    return f"{x:.{dec}f}".replace(".", ",")


def _nombre_partido(d: dict) -> str:
    return d.get("partido") or d.get("slug", "").replace("-", " ").title()


def _ranking(af: dict, clave) -> list:
    """[(partido, valor)] de mayor a menor, de los partidos con ese dato."""
    filas = []
    for p in (af.get("partidos") or {}).values():
        v = clave(p)
        if v is not None:
            filas.append((_nombre_partido(p), v))
    return sorted(filas, key=lambda f: -f[1])


def _puesto(filas: list, partido: str = "Chivilcoy") -> int:
    return next((i + 1 for i, (n, _) in enumerate(filas) if n == partido), 0)


def _rinde(p: dict, cultivo: str):
    return ((p.get("rindes") or {}).get(cultivo) or {}).get("promedio")


def _sequia(campana: str) -> bool:
    """¿Esa campaña fue la de la gran sequía? (emergencias por sequía de 2022 a 2024 en Chivilcoy)."""
    return campana in ("2022/23",)


ORDINAL = {1: "primera", 2: "segunda", 3: "tercera", 4: "cuarta", 5: "quinta"}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Los temas: cada uno devuelve {tema, gancho, volanta, diapositivas, texto, hashtags, videos} o None (sin datos)
# Diapositivas: ("video", {...}) dato sobre un video; ("barras", {...}) ranking; ("serie", {...}) campaña por
# campaña; ("lista", {...}) renglones; ("cierre", {...}).
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _cierre(frase: str) -> tuple:
    return ("cierre", {"frase": frase})


def tema_ranking_cultivo(af: dict, cultivo: str) -> dict | None:
    nombre = NOMBRE_CULTIVO[cultivo]
    el, del_ = ("la", "de la") if cultivo == "soja" else ("el", "del")
    filas = _ranking(af, lambda p: _rinde(p, cultivo))
    chiv = (af.get("partidos") or {}).get("chivilcoy") or {}
    r = (chiv.get("rindes") or {}).get(cultivo) or {}
    puesto = _puesto(filas)
    if len(filas) < 5 or not puesto or not r.get("promedio"):
        return None
    primero = filas[0][0]
    if puesto == 1:
        gancho = f"¿Quién tiene {el} mejor {nombre} de la zona?"
        remate = f"Chivilcoy, primero en {nombre}"
    else:
        gancho = f"¿Dónde rinde más {el} {nombre} en la zona?"
        remate = f"{primero} arriba; Chivilcoy, {puesto}.º de {len(filas)}"
    vs = r.get("vs_provincia")
    linea_vs = (f"{abs(vs)} % {'arriba' if vs > 0 else 'abajo'} del promedio bonaerense ({_coma(r.get('provincia'))})"
                if vs else f"en línea con el promedio bonaerense ({_coma(r.get('provincia'))})")
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Rinde promedio {del_} {nombre} · qq/ha · últimas cinco campañas",
                  "valores": {k: _rinde(x, cultivo) for k, x in (af.get("partidos") or {}).items()}, "dec": 1}),
        ("barras", {"titulo": f"Rinde promedio de {nombre}", "sub": "qq/ha · últimas cinco campañas, por partido",
                    "filas": filas, "dec": 1}),
        ("video", {"volanta": remate.upper(), "numero": r["promedio"], "dec": 1, "unidad": "qq/ha",
                   "texto": f"rinde promedio {del_} {nombre} en Chivilcoy: {linea_vs}.", "video": VIDEO_CULTIVO[cultivo]}),
    ]
    if r.get("mejor"):
        diap.append(("video", {"volanta": "LA MEJOR CAMPAÑA", "numero": r["mejor"][1], "dec": 1, "unidad": "qq/ha",
                               "texto": f"en la {r['mejor'][0]}. La peor: {r['peor'][0]}, con {_coma(r['peor'][1])} "
                                        f"qq/ha{' (la sequía)' if _sequia(r['peor'][0]) else ''}.",
                               "video": "cosecha"}))
    diap.append(_cierre(f"¿Cuánto te rindió {el} {nombre} este año? Contanos en los comentarios"))
    lista = ", ".join(f"{n} {_coma(v)}" for n, v in filas[:5])
    texto = [f"🌾 {gancho} El rinde promedio de las últimas cinco campañas, partido por partido (qq/ha): {lista}.",
             f"En Chivilcoy, {_coma(r['promedio'])} qq/ha: {linea_vs}."
             + (f" Su mejor campaña fue la {r['mejor'][0]} ({_coma(r['mejor'][1])} qq/ha)." if r.get("mejor") else ""),
             f"📲 ¿Cuánto te rindió? Contanos de qué pueblo sos en los comentarios o por WhatsApp al {WHATSAPP}."]
    return {"tema": f"{cultivo}_zona", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", f"#{nombre.capitalize().replace('í', 'i')}", "#Campo", "#Agro", "#Rindes"]}


def tema_historia(af: dict, cultivo: str) -> dict | None:
    nombre = NOMBRE_CULTIVO[cultivo]
    el, del_ = ("la", "de la") if cultivo == "soja" else ("el", "del")
    r = (((af.get("partidos") or {}).get("chivilcoy") or {}).get("rindes") or {}).get(cultivo) or {}
    serie = [s for s in r.get("serie") or [] if s[1]]
    if len(serie) < 8 or not r.get("mejor"):
        return None
    ultima = serie[-1]
    record = r["mejor"][0] == ultima[0]
    gancho = (f"¡Récord! {el.capitalize()} {nombre} de Chivilcoy, campaña por campaña" if record
              else f"{el.capitalize()} {nombre} de Chivilcoy, campaña por campaña")
    diap = [
        ("serie", {"titulo": gancho, "sub": f"Rinde {del_} {nombre} en Chivilcoy · qq/ha, campaña por campaña",
                   "serie": [(s[0], s[1]) for s in serie], "mejor": r["mejor"][0], "peor": r["peor"][0]}),
        ("video", {"volanta": "RÉCORD" if record else "LA MEJOR", "numero": r["mejor"][1], "dec": 1, "unidad": "qq/ha",
                   "texto": f"en la campaña {r['mejor'][0]}" + (": la última, la mejor de la serie." if record else "."),
                   "video": "cosecha"}),
        ("video", {"volanta": "LA PEOR", "numero": r["peor"][1], "dec": 1, "unidad": "qq/ha",
                   "texto": f"en la {r['peor'][0]}" + (", el año de la sequía." if _sequia(r["peor"][0]) else "."),
                   "video": "campo"}),
        _cierre("Guardalo y compartilo con alguien del campo"),
    ]
    texto = [f"📊 {gancho}: así rindió en el partido desde la {serie[0][0]} hasta la {ultima[0]}.",
             f"La mejor: {r['mejor'][0]}, {_coma(r['mejor'][1])} qq/ha. La peor: {r['peor'][0]}, "
             f"{_coma(r['peor'][1])} qq/ha. La última ({ultima[0]}): {_coma(ultima[1])} qq/ha, sobre "
             f"{_coma(ultima[2], 0)} hectáreas sembradas." if ultima[2] else "",
             "📲 ¿Cuál fue tu mejor campaña? Contanos en los comentarios."]
    return {"tema": f"{cultivo}_historia", "gancho": gancho, "diapositivas": diap, "texto": [t for t in texto if t],
            "hashtags": ["#Chivilcoy", f"#{nombre.capitalize().replace('í', 'i')}", "#Campo", "#Agro"]}


def tema_tierra(af: dict) -> dict | None:
    filas = _ranking(af, lambda p: p.get("productividad"))
    chiv = (af.get("partidos") or {}).get("chivilcoy") or {}
    if len(filas) < 5 or not chiv.get("productividad"):
        return None
    gancho = "¿Qué partido de la zona tiene la mejor tierra?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": "Índice de productividad del suelo (sobre 100, INTA)",
                  "valores": {k: x.get("productividad") for k, x in (af.get("partidos") or {}).items()}, "dec": 0}),
        ("barras", {"titulo": "Índice de productividad del suelo", "sub": "sobre 100 · carta de suelos del INTA",
                    "filas": filas, "dec": 0}),
        ("video", {"volanta": "CHIVILCOY", "numero": chiv["productividad"], "dec": 0, "unidad": "/100",
                   "texto": f"puesto {chiv.get('puesto')} de {chiv.get('de')} partidos bonaerenses (el promedio de la "
                            f"provincia es {chiv.get('productividad_provincia')}).", "video": "campo"}),
    ]
    if chiv.get("clase_1_3"):
        diap.append(("video", {"volanta": "TIERRA AGRÍCOLA", "numero": chiv["clase_1_3"], "dec": 0, "unidad": "%",
                               "texto": "de Chivilcoy es clase I a III: apta para agricultura, con limitaciones de "
                                        "leves a moderadas.", "video": "maquinaria"}))
    diap.append(_cierre("¿De qué partido sos? Contanos en los comentarios"))
    lista = ", ".join(f"{n} {v:.0f}" for n, v in filas)
    texto = [f"🌱 {gancho} El índice de productividad del suelo (sobre 100, INTA), partido por partido: {lista}.",
             f"Chivilcoy tiene {chiv['productividad']}: puesto {chiv.get('puesto')} de {chiv.get('de')} en la "
             f"provincia, que promedia {chiv.get('productividad_provincia')}.",
             "📲 ¿De qué partido sos? Contanos en los comentarios."]
    return {"tema": "tierra", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#Suelo", "#Campo", "#Agro"]}


def tema_nino(af: dict, hoy) -> dict | None:
    chiv = (af.get("partidos") or {}).get("chivilcoy") or {}
    e = chiv.get("enso") or {}
    tabla = e.get("tabla") or {}
    fase = e.get("estado") or ""
    if fase not in ("El Niño", "La Niña") or not tabla.get("soja"):
        return None
    try:
        if (hoy - datetime.strptime(af.get("traido") or "", "%Y-%m-%d").date()).days > DIAS_DATOS_VIEJOS:
            return None
    except ValueError:
        return None
    k = "nino" if fase == "El Niño" else "nina"
    gancho = f"Llegó {fase}: ¿qué le pasa al campo de Chivilcoy?"     # 20/11/2026: era «Hay El Niño» (sonaba forzado)
    filas = sorted([(NOMBRE_CULTIVO.get(c, c).capitalize(), v[k]) for c, v in tabla.items() if v.get(k) is not None],
                   key=lambda f: -f[1])
    soja = tabla["soja"][k]
    zona = _ranking(af, lambda p: (((p.get("enso") or {}).get("tabla") or {}).get("soja") or {}).get(k))
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Rinde de la soja en años de {fase}, contra su tendencia (desde 1980)",
                  "valores": {kk: (((x.get("enso") or {}).get("tabla") or {}).get("soja") or {}).get(k)
                              for kk, x in (af.get("partidos") or {}).items()},
                  "dec": 0, "unidad": "%", "signo": True, "divergente": True}),
        ("video", {"volanta": f"{fase.upper()} EN EL PACÍFICO", "numero": e.get("oni"), "dec": 1, "unidad": "°C",
                   "signo": True, "texto": f"el último ONI ({e.get('oni_tramo')}), el índice de NOAA: aviso de "
                                           f"{fase} del {e.get('aviso')}.", "video": "lluvia"}),
        ("barras", {"titulo": f"El rinde en años de {fase}", "sub": "Chivilcoy, contra su tendencia, desde 1980",
                    "filas": filas, "dec": 0, "unidad": "%", "signo": True}),
        ("video", {"volanta": "LA SOJA", "numero": soja, "dec": 0, "unidad": "%", "signo": True,
                   "texto": f"se apartó de su tendencia el rinde de la soja de Chivilcoy en los años de {fase}"
                            + (f"; igual quedó por debajo en {e['soja_abajo_de_10']} de cada 10."
                               if e.get("soja_abajo_de_10") is not None and k == "nino" else "."),
                   "video": "cosecha"}),
    ]
    del zona                                               # ya va en el mapa del principio
    diap.append(_cierre("Guardalo y compartilo con alguien del campo"))
    lista = ", ".join(f"{n.lower()} {v:+.0f} %".replace("+0 %", "0 %") for n, v in filas)
    texto = [f"🌊 {gancho} {e.get('texto') or ''}".strip(),
             f"En los años de {fase} desde 1980, el rinde en Chivilcoy quedó así contra su tendencia: {lista}.",
             "Es un promedio histórico, no un pronóstico: cada campaña depende de cuánto y cuándo llueva.",
             "📲 ¿Cómo viene tu campo? Contanos en los comentarios."]
    return {"tema": "nino", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#ElNiño" if k == "nino" else "#LaNiña", "#Clima", "#Campo", "#Agro"]}


def tema_suelo(af: dict) -> dict | None:
    c = (af.get("partidos") or {}).get("chivilcoy") or {}
    if not c.get("series") or not c.get("limitantes"):
        return None
    gancho = "¿Qué tierra pisás en Chivilcoy?"
    serie, pct = c["series"][0]
    agua = next((v for n, v in c["limitantes"] if n.lower().startswith("exceso de agua")), None)
    diap = [("barras", {"titulo": gancho, "sub": "Las series de suelo: % del partido · carta 1:50.000 del INTA",
                        "filas": c["series"][:6], "dec": 1, "unidad": "%", "resaltar": serie})]
    if c.get("franco_limosa"):
        diap.append(("video", {"volanta": "LA TEXTURA", "numero": c["franco_limosa"], "dec": 1, "unidad": "%",
                               "texto": "del partido es franco limosa en los primeros 15 cm.", "video": "maquinaria"}))
    if agua:
        diap.append(("video", {"volanta": "EL TALÓN DE AQUILES", "numero": agua, "dec": 0, "unidad": "%",
                               "texto": "del partido tiene como limitante el exceso de agua o el anegamiento.",
                               "video": "inundacion"}))
    if c.get("carbono"):
        diap.append(("video", {"volanta": "CARBONO", "numero": c["carbono"], "dec": 0, "unidad": "t/ha",
                               "texto": "de carbono orgánico en los primeros 30 cm del suelo.", "video": "campo"}))
    diap.append(_cierre("Guardalo y compartilo con alguien del campo"))
    texto = [f"🟫 {gancho} La serie que más se repite es la {serie}: el {_coma(pct)} % del partido.",
             (f"El {_coma(c['franco_limosa'])} % es franco limosa en superficie" if c.get("franco_limosa") else "")
             + (f" y el {agua:.0f} % tiene como limitante el exceso de agua." if agua else "."),
             "📲 ¿Cómo es el suelo de tu campo? Contanos en los comentarios."]
    return {"tema": "suelo", "gancho": gancho, "diapositivas": diap, "texto": [t for t in texto if t.strip(". ")],
            "hashtags": ["#Chivilcoy", "#Suelo", "#Campo", "#Agro"]}


def tema_sequias(af: dict) -> dict | None:
    c = (af.get("partidos") or {}).get("chivilcoy") or {}
    em = c.get("emergencias") or {}
    lista = em.get("lista") or []
    if len(lista) < 3:
        return None
    secas = [x for x in lista if "sequ" in x["motivo"]]
    gancho = "Las emergencias del campo de Chivilcoy"
    diap = [
        ("lista", {"titulo": gancho, "sub": f"{em.get('total') or len(lista)} emergencias agropecuarias declaradas: "
                                            "cuándo y por qué",
                   "filas": [(f"{x['desde']} – {x['hasta']}", x["motivo"].capitalize()) for x in lista]}),
    ]
    if secas:
        anios = sorted({int(x[k][-4:]) for x in secas for k in ("desde", "hasta") if x[k][-4:].isdigit()})
        peores = [NOMBRE_CULTIVO[cu] for cu, r in (c.get("rindes") or {}).items()
                  if cu in ("soja", "maiz", "trigo") and _sequia((r.get("peor") or [""])[0])]
        cuando = f"entre {anios[0]} y {anios[-1]}" if anios and anios[0] != anios[-1] else ""
        extra = (f": la de 2022/23 fue la peor campaña de {', '.join(peores[:-1]) + ' y ' + peores[-1] if len(peores) > 1 else peores[0]} "
                 "de la serie" if peores else "")
        diap.append(("video", {"volanta": "POR SEQUÍA", "numero": len(secas), "dec": 0, "unidad": f"de {len(lista)}",
                               "texto": f"fueron por sequía{', ' + cuando if cuando else ''}{extra}.",
                               "video": "cosecha"}))
    diap.append(_cierre("¿Cómo viene tu campo este año? Contanos en los comentarios"))
    texto = [f"☀️ {gancho}: {em.get('total') or len(lista)} declaradas que alcanzaron al partido, "
             f"{len(secas)} por sequía.",
             "; ".join(f"{x['desde']} a {x['hasta']}, por {x['motivo']} ({x['norma']})" for x in lista) + ".",
             "📲 ¿Cómo viene tu campo este año? Contanos en los comentarios."]
    return {"tema": "sequias", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#Sequía", "#Campo", "#Agro"],
            "fuente": "Fuente: ArgenFields, con datos de InfoLEG (Ministerio de Justicia)"}


def tema_gemelas(af: dict) -> dict | None:
    c = (af.get("partidos") or {}).get("chivilcoy") or {}
    g = c.get("gemelas") or []
    if len(g) < 2:
        return None
    gancho = "Chivilcoy tiene gemelas en Estados Unidos"
    diap = [
        ("lista", {"titulo": gancho, "sub": "Las zonas de EE.UU. con clima y suelo más parecidos (similitud sobre 100)",
                   "filas": [(f"{x['condado']}, {x['estado']}", f"{x['similitud']}/100") for x in g]}),
        ("video", {"volanta": f"{g[0]['condado'].upper()}, {g[0]['estado'].upper()}", "numero": g[0]["similitud"],
                   "dec": 0, "unidad": "/100", "texto": "de similitud con Chivilcoy en clima y suelo: de las zonas "
                                                       "de EE.UU., de las que más se le parecen.", "video": "cosecha"}),
    ]
    soja = _rinde(c, "soja")
    if soja:
        diap.append(("video", {"volanta": "Y ACÁ", "numero": soja, "dec": 1, "unidad": "qq/ha",
                               "texto": "rinde la soja en Chivilcoy, promedio de las últimas cinco campañas.",
                               "video": "cosecha"}))
    diap.append(_cierre("Compartilo con alguien del campo"))
    texto = [f"🇺🇸 {gancho}: las zonas de Estados Unidos con el clima y el suelo más parecidos son "
             + ", ".join(f"{x['condado']} ({x['estado']}, {x['similitud']}/100)" for x in g) + ".",
             "Illinois es el corazón del cinturón maicero y sojero de Estados Unidos.",
             "📲 ¿Sabías que se parecían tanto? Contanos en los comentarios."]
    return {"tema": "gemelas", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#Campo", "#Agro", "#Curiosidades"]}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 20/11/2026: con los DATOS ABIERTOS de ArgenFields (rindes, sembrado y cosechado de cada partido desde 1923; CC BY
# 4.0, agro/datos/rindes_zona.json, tools/traer_argenfields.py): quién rindió más la última campaña, cuánto se perdió
# (sembrado que no se cosechó) y cien años de un cultivo en Chivilcoy. Siempre se cita a ArgenFields.
# ─────────────────────────────────────────────────────────────────────────────────────────────
def datos_rindes(ruta: Path = None) -> dict:
    try:
        return json.loads(Path(ruta or RINDES).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"partidos": {}}


def _filas(dr: dict, slug: str, cultivo: str) -> list:
    return ((dr.get("partidos") or {}).get(slug) or {}).get(cultivo) or []


def _nombre_slug(af: dict, slug: str) -> str:
    return ((af.get("partidos") or {}).get(slug) or {}).get("partido") or slug.replace("-", " ").title()


def tema_campana(af: dict, dr: dict, cultivo: str, hoy) -> dict | None:
    """¿Quién rindió más en la última campaña? (mapa + ranking + Chivilcoy contra su promedio)."""
    nombre = NOMBRE_CULTIVO[cultivo]
    el, del_ = ("la", "de la") if cultivo == "soja" else ("el", "del")
    chiv = _filas(dr, "chivilcoy", cultivo)
    if not chiv or not chiv[-1][4]:
        return None
    camp = chiv[-1][0]
    if hoy.year - int(camp[:4]) > 2:                   # una campaña vieja no es noticia
        return None
    valores = {}
    for slug in (dr.get("partidos") or {}):
        f = [x for x in _filas(dr, slug, cultivo) if x[0] == camp and x[4]]
        if f:
            valores[slug] = round(f[0][4] / 100, 1)
    if len(valores) < 5 or "chivilcoy" not in valores:
        return None
    filas = sorted(((_nombre_slug(af, k), v) for k, v in valores.items()), key=lambda x: -x[1])
    puesto = next((i + 1 for i, (n, _) in enumerate(filas) if n == "Chivilcoy"), 0)
    previas = [x[4] / 100 for x in chiv[-6:-1] if x[4]]
    prom = sum(previas) / len(previas) if previas else None
    gancho = f"¿Quién rindió más {nombre} en la campaña {camp}?"
    diap = [("mapa", {"titulo": gancho, "sub": f"Rinde {del_} {nombre} en la campaña {camp}, qq/ha, partido por partido",
                      "valores": valores, "dec": 1}),
            ("barras", {"titulo": f"El ranking de la campaña {camp}", "sub": f"Rinde {del_} {nombre}, qq/ha",
                        "filas": filas, "dec": 1})]
    if prom:
        dif = round(100 * (valores["chivilcoy"] - prom) / prom)
        diap.append(("video", {"volanta": f"CHIVILCOY, {puesto}.º DE {len(filas)}", "numero": valores["chivilcoy"],
                               "dec": 1, "unidad": "qq/ha",
                               "texto": f"rindió {el} {nombre} en Chivilcoy en la {camp}: un {abs(dif)} % "
                                        f"{'más' if dif >= 0 else 'menos'} que el promedio de las cinco campañas "
                                        f"anteriores ({_coma(prom)}).", "video": VIDEO_CULTIVO[cultivo]}))
    diap.append(_cierre(f"¿Cuánto te rindió {el} {nombre} en la {camp}? Contanos en los comentarios"))
    texto = [f"🌾 {gancho} " + ", ".join(f"{n} {_coma(v)}" for n, v in filas[:5]) + " qq/ha.",
             f"Chivilcoy quedó {puesto}.º de {len(filas)} con {_coma(valores['chivilcoy'])} qq/ha.",
             "📲 ¿Cuánto te rindió? Contanos de qué pueblo sos en los comentarios."]
    return {"tema": f"{cultivo}_campana", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", f"#{nombre.capitalize().replace('í', 'i')}", "#Cosecha", "#Campo", "#Agro"],
            "fuente": FUENTE_ABIERTOS}


def tema_perdidas(af: dict, dr: dict, cultivo: str) -> dict | None:
    """La campaña de los últimos 15 años en la que más se sembró y no se cosechó en la zona, partido por partido."""
    nombre = NOMBRE_CULTIVO[cultivo]
    por_camp = {}
    for slug in (dr.get("partidos") or {}):
        for c, sem, cos, *_ in _filas(dr, slug, cultivo)[-15:]:
            if sem and cos is not None and sem > 0:
                por_camp.setdefault(c, {})[slug] = (sem, cos)
    if not por_camp:
        return None

    def perdida(d):
        s_, c_ = sum(v[0] for v in d.values()), sum(v[1] for v in d.values())
        return 1 - c_ / s_ if s_ else 0
    camp = max(por_camp, key=lambda c: perdida(por_camp[c]))
    d = por_camp[camp]
    if perdida(d) < 0.08 or len(d) < 5 or "chivilcoy" not in d:
        return None
    valores = {k: round(100 * (1 - cos / sem)) for k, (sem, cos) in d.items()}
    filas = sorted(((_nombre_slug(af, k), v) for k, v in valores.items()), key=lambda x: -x[1])
    sem_c, cos_c = d["chivilcoy"]
    sequia = camp == "2022/23"
    cuanto = "cuánta" if cultivo == "soja" else "cuánto"
    gancho = (f"La sequía {camp}: {cuanto} {nombre} no se pudo cosechar" if sequia else
              f"Campaña {camp}: {cuanto} {nombre} se perdió en la zona")
    diap = [("mapa", {"titulo": gancho, "sub": "% de lo sembrado que no se cosechó, partido por partido",
                      "valores": valores, "dec": 0, "unidad": "%", "paleta": "rojo"}),
            ("barras", {"titulo": "Lo que se perdió", "sub": f"% de lo sembrado con {nombre} que no se cosechó en la {camp}",
                        "filas": filas, "dec": 0, "unidad": "%"}),
            ("video", {"volanta": "EN CHIVILCOY", "numero": round(sem_c - cos_c), "dec": 0, "unidad": "ha",
                       "texto": f"de {nombre} sembradas no se cosecharon en la {camp}: el {valores['chivilcoy']} % "
                                f"de las {_coma(sem_c, 0)} ha.", "video": "campo"}),
            _cierre("¿Cómo te fue a vos esa campaña? Contanos en los comentarios")]
    texto = [f"📉 {gancho}. En Chivilcoy se sembraron {_coma(sem_c, 0)} ha y se cosecharon {_coma(cos_c, 0)}: "
             f"el {valores['chivilcoy']} % se perdió.",
             "En la zona: " + ", ".join(f"{n} {v} %" for n, v in filas[:5]) + ".",
             "📲 ¿Cómo te fue a vos? Contanos en los comentarios."]
    return {"tema": f"{cultivo}_perdidas", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#Sequía", f"#{nombre.capitalize().replace('í', 'i')}", "#Campo", "#Agro"],
            "fuente": FUENTE_ABIERTOS}


def tema_siglo(af: dict, dr: dict, cultivo: str) -> dict | None:
    """Casi cien años de un cultivo en Chivilcoy: el rinde promedio de cada década."""
    nombre = NOMBRE_CULTIVO[cultivo]
    el, del_ = ("la", "de la") if cultivo == "soja" else ("el", "del")
    filas = [x for x in _filas(dr, "chivilcoy", cultivo) if x[4]]
    if len(filas) < 50:
        return None
    decadas = {}
    for x in filas:
        decadas.setdefault(int(x[0][:4]) // 10 * 10, []).append(x[4] / 100)
    serie = [(f"{d}s", round(sum(v) / len(v), 1)) for d, v in sorted(decadas.items()) if len(v) >= 3]
    if len(serie) < 6:
        return None
    primera, ultima = serie[0], serie[-1]
    veces = ultima[1] / primera[1] if primera[1] else 0
    mejor = max(filas, key=lambda x: x[4])
    anios = int(filas[-1][0][:4]) - int(filas[0][0][:4])
    gancho = f"{anios} años de {nombre} en Chivilcoy: así cambió el rinde"
    diap = [("serie", {"titulo": gancho, "sub": f"Rinde promedio {del_} {nombre} por década, qq/ha",
                       "serie": serie, "mejor": max(serie, key=lambda x: x[1])[0],
                       "peor": min(serie, key=lambda x: x[1])[0]}),
            ("video", {"volanta": f"DE LOS {primera[0][:4]} A HOY", "numero": round(veces, 1), "dec": 1, "unidad": "veces",
                       "texto": f"más rinde {el} {nombre} en Chivilcoy: de {_coma(primera[1])} a {_coma(ultima[1])} "
                                "qq/ha de promedio.", "video": VIDEO_CULTIVO[cultivo]}),
            ("video", {"volanta": "EL RÉCORD", "numero": round(mejor[4] / 100, 1), "dec": 1, "unidad": "qq/ha",
                       "texto": f"en la campaña {mejor[0]}.", "video": "cosecha"}),
            _cierre("Guardalo y compartilo con alguien del campo")]
    texto = [f"📊 {gancho}. En los {primera[0][:4]} rendía {_coma(primera[1])} qq/ha de promedio; en los "
             f"{ultima[0][:4]}, {_coma(ultima[1])}: {_coma(veces)} veces más.",
             f"El récord: {_coma(mejor[4] / 100)} qq/ha en la campaña {mejor[0]}.",
             "📲 ¿Desde cuándo tu familia trabaja el campo? Contanos en los comentarios."]
    return {"tema": f"{cultivo}_siglo", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", f"#{nombre.capitalize().replace('í', 'i')}", "#Historia", "#Campo", "#Agro"],
            "fuente": FUENTE_ABIERTOS}


# 24/11/2026 (el editor: «sumá el informe semanal del MAGyP al reel de datos de la zona»): cómo vienen la siembra y la
# cosecha en la delegación Bragado (donde está Chivilcoy), con el avance de la semana y el estado de los lotes. Sale
# cuando hay un informe nuevo (los jueves) que todavía no se usó, antes que El Niño y que los temas de ArgenFields.
def _miles(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def tema_magyp(info: dict | None, hoy) -> dict | None:
    from agro import magyp as MG
    if not MG.vigente(info, hoy):
        return None
    filas_av = []
    for a in info.get("avance") or []:
        if not a.get("hectareas"):
            continue
        nombre = a["cultivo"].capitalize() + (f" de {a['sub']}" if a.get("sub") in ("1ª", "2ª") else "")
        etiqueta = f"{nombre} · {a['labor']}"
        if a["pct"] <= 0:
            valor = "sin arrancar"
        else:
            sube = a["pct"] - (a.get("antes") or 0)
            valor = f"{_coma(a['pct'], 0)} %" + (f" (+{_coma(sube, 0)})" if sube > 0 else "")
        filas_av.append((etiqueta, valor, a))
    activos = [f for f in filas_av if 0 < f[2]["pct"] < 100]
    if not activos and not info.get("estado"):
        return None
    fecha = datetime.strptime(info["fecha"], "%Y-%m-%d")
    al = f"{fecha.day}/{fecha.month}"
    hay_cosecha = any(f[2]["labor"] == "cosecha" and f[2]["pct"] > 0 for f in filas_av)
    gancho = "¿Cómo viene la cosecha en la zona?" if hay_cosecha else "¿Cómo viene la siembra en la zona?"
    # Primero lo que se está moviendo esta semana; después lo terminado y lo que no arrancó.
    filas_av.sort(key=lambda f: (not (0 < f[2]["pct"] < 100), -(f[2]["pct"] - (f[2].get("antes") or 0))))
    diap = [("lista", {"titulo": gancho, "sub": f"Zona de Chivilcoy, al {al} · (+) lo que avanzó en la semana",
                       "filas": [(e, v) for e, v, _ in filas_av[:7]]})]
    estado = info.get("estado") or []
    if estado:
        hum = sorted({e["humedad"] for e in estado if e.get("humedad")})
        diap.append(("lista", {"titulo": "Cómo están los lotes",
                               "sub": "Estado y momento del cultivo" + (f" · humedad: {', '.join(hum)}" if hum else ""),
                               "filas": [(e["cultivo"].capitalize(), f"{e['estado'] or '—'} · {e['estadio'] or '—'}")
                                         for e in estado[:6]]}))
    diap.append(_cierre("¿Cómo viene tu lote? Contanos en los comentarios"))
    resumen = ", ".join(f"{a['cultivo']}{(' de ' + a['sub']) if a.get('sub') in ('1ª', '2ª') else ''} "
                        f"{_coma(a['pct'], 0)} % {'sembrado' if a['labor'] == 'siembra' else 'cosechado'}"
                        for _e, _v, a in filas_av if a["pct"] > 0)
    texto = [f"🌱 {gancho} En la zona de Chivilcoy (delegación Bragado del Ministerio de Agricultura), al {al}: "
             f"{resumen}.",
             ("Los lotes: " + ", ".join(f"{e['cultivo']} {e['estado']}" for e in estado if e.get("estado")) + ".")
             if estado else "",
             "📲 ¿Cómo viene tu lote? Contanos de qué pueblo sos en los comentarios."]
    return {"tema": "magyp", "gancho": gancho, "diapositivas": diap, "texto": [t for t in texto if t],
            "hashtags": ["#Chivilcoy", "#Siembra", "#Campo", "#Agro", "#Bragado"], "fuente": MG.FUENTE,
            "informe": info["fecha"]}


def _info_magyp(log=print):
    from agro import magyp as MG
    if not MG.activo():
        return None
    try:
        return MG.traer()
    except Exception as e:                                 # noqa: BLE001 — sin el informe, los otros temas
        log(f"   informe del MAGyP: {type(e).__name__}: {e}")
        return None


def temas_disponibles(af: dict, hoy) -> dict:
    """{clave: tema} de los temas de ArgenFields que tienen datos hoy."""
    salida = {}
    dr = datos_rindes()
    for clave, fn in (("trigo_campana", lambda: tema_campana(af, dr, "trigo", hoy)),
                      ("soja_campana", lambda: tema_campana(af, dr, "soja", hoy)),
                      ("maiz_campana", lambda: tema_campana(af, dr, "maiz", hoy)),
                      ("soja_perdidas", lambda: tema_perdidas(af, dr, "soja")),
                      ("maiz_perdidas", lambda: tema_perdidas(af, dr, "maiz")),
                      ("trigo_siglo", lambda: tema_siglo(af, dr, "trigo")),
                      ("maiz_siglo", lambda: tema_siglo(af, dr, "maiz")),
                      ("trigo_zona", lambda: tema_ranking_cultivo(af, "trigo")),
                      ("soja_zona", lambda: tema_ranking_cultivo(af, "soja")),
                      ("maiz_zona", lambda: tema_ranking_cultivo(af, "maiz")),
                      ("trigo_historia", lambda: tema_historia(af, "trigo")),
                      ("soja_historia", lambda: tema_historia(af, "soja")),
                      ("maiz_historia", lambda: tema_historia(af, "maiz")),
                      ("tierra", lambda: tema_tierra(af)), ("nino", lambda: tema_nino(af, hoy)),
                      ("suelo", lambda: tema_suelo(af)), ("sequias", lambda: tema_sequias(af)),
                      ("gemelas", lambda: tema_gemelas(af)),
                      ("magyp", lambda: tema_magyp(_info_magyp(), hoy))):
        try:
            t = fn()
        except Exception as e:                             # noqa: BLE001 — un tema roto no frena a los demás
            print(f"   tema {clave}: {type(e).__name__}: {e}")
            t = None
        if t:
            salida[clave] = t
    return salida


def elegir_tema(mem: dict, disponibles: dict, hoy, lluvia_mm: float | None = None) -> str | None:
    """El tema de hoy: la lluvia si viene fuerte; si no, El Niño (cada DIAS_SIN_REPETIR días); si no, el de
    ArgenFields usado hace más tiempo (nunca antes de DIAS_SIN_REPETIR días)."""
    if lluvia_mm is not None and lluvia_mm >= lluvia_min():
        return "lluvia"
    usos = ultimo_uso(mem)
    # 24/11/2026: un informe semanal del MAGyP que todavía no salió va primero (es la novedad de la semana).
    mg = disponibles.get("magyp")
    if mg and usos.get("magyp", "") < mg.get("informe", ""):
        return "magyp"
    limite = (hoy - timedelta(days=DIAS_SIN_REPETIR)).isoformat()
    libres = [t for t in ("nino",) + ORDEN if t in disponibles and usos.get(t, "") < limite]
    if not libres:
        return None
    if "nino" in libres:
        return "nino"
    return min(libres, key=lambda t: (usos.get(t, ""), ORDEN.index(t)))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El dibujo
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _tema_color() -> dict:
    return D.TEMAS["grafito"]


def _sombra_texto(im: Image.Image, xy, texto, f, color=D.BLANCO):
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((xy[0] + 2, xy[1] + 2), texto, font=f, fill=(0, 0, 0, 200))
    capa = capa.filter(ImageFilter.GaussianBlur(3))
    ImageDraw.Draw(capa).text(xy, texto, font=f, fill=color + (255,) if len(color) == 3 else color)
    im.alpha_composite(capa)


def _numero_txt(valor: float, dec: int, signo: bool = False) -> str:
    t = _coma(valor, dec) if dec else f"{round(valor):,}".replace(",", ".")
    if signo and valor > 0:
        t = "+" + t
    return t.replace("-", "−")


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def capa_video(d: dict, t: float, credito: str, fuente: str) -> Image.Image:
    """La parte de abajo y los textos de una diapositiva de video (RGBA 1080x1350, arriba transparente)."""
    tc = _tema_color()
    im = Image.new("RGBA", (D.W, D.H45), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rectangle((0, ALTO_VIDEO, D.W, ALTO_VIDEO + D.LINEA), fill=D.ACENTO)
    dr.rectangle((0, ALTO_VIDEO + D.LINEA, D.W, D.H45), fill=tc["fondo"])
    # Arriba: la marca y el crédito del video.
    _sombra_texto(im, (40, 34), D.USUARIO, D.fuente("bold", 30))
    if credito:
        _sombra_texto(im, (40, ALTO_VIDEO - 44), f"Video ilustrativo: {credito}"[:95], D.fuente("regular", 22),
                      (235, 235, 235))
    y = ALTO_VIDEO + D.LINEA + 44
    aparece = _ease(t / 0.4)
    if d.get("volanta"):
        f = D.fuente("bold", 34)
        dr.text((D.X, y), d["volanta"], font=f, fill=tc["volanta"] + (round(255 * aparece),))
        y += 58
    if d.get("titulo"):                                    # la diapositiva del gancho
        f, renglones = D.ajustar(dr, d["titulo"], "negra", 82, 54, D.ANCHO, 3)
        for r in renglones:
            dr.text((D.X, y), r, font=f, fill=tc["titular"] + (round(255 * aparece),))
            y += round(f.size * 1.12)
    elif d.get("numero") is not None:
        valor = d["numero"] * _ease(t / CONTAR)
        # Mientras cuenta, con los mismos decimales que el número final (si no, «67,8» pisa la unidad de «95»).
        dec = 0 if float(d["numero"]).is_integer() else d.get("dec", 0)
        num = _numero_txt(round(valor, dec) if t < CONTAR else d["numero"], dec, d.get("signo"))
        f = D.fuente("negra", 150)
        from agro import movimiento as MV
        golpe = max(0.0, 1 - abs(t - CONTAR) / 0.2) if MV.activo() else 0.0
        if golpe > 0:                                      # el pop cuando llega a su valor
            sp = Image.new("RGBA", (round(dr.textlength(num, font=f)) + 20, 200), (0, 0, 0, 0))
            ImageDraw.Draw(sp).text((10, 0), num, font=f, fill=D.NARANJA)
            MV.pop_sprite(im, sp, (D.X - 6 + sp.width / 2 - 10, y - 18 + 100), 1 + 0.12 * golpe)
        else:
            dr.text((D.X - 6, y - 18), num, font=f, fill=D.NARANJA)
        if d.get("unidad"):
            fu = D.fuente("bold", 52)
            x = D.X + max(dr.textlength(_numero_txt(d["numero"], dec, d.get("signo")), font=f),
                          dr.textlength(num, font=f)) + 10
            dr.text((x, y + 72), d["unidad"], font=fu, fill=tc["titular"])
        y += 170
        f, renglones = D.ajustar(dr, d.get("texto", ""), "medium", 44, 32, D.ANCHO, 4)
        for r in renglones:
            dr.text((D.X, y), r, font=f, fill=tc["texto"] + (round(255 * aparece),))
            y += round(f.size * 1.25)
    dr.text((D.X, D.H45 - 50), fuente, font=D.fuente("regular", 22), fill=tc["tenue"])
    _pie(im)
    return im


RETRASO = 0.45               # con movimiento: las barras, columnas y filas arrancan cuando ya entró el título


def _retraso() -> float:
    from agro import movimiento as MV
    return RETRASO if MV.activo() else 0.0


@lru_cache(maxsize=32)
def _plan_titulo(titulo: str) -> dict:
    from agro import movimiento as MV
    return MV.plan_titulo(titulo, D.W - 190, 2, 84, 56)      # a la derecha va el isologo chico


def _mezcla_color(c1, c2, u: float) -> tuple:
    return tuple(round(a + (b - a) * u) for a, b in zip(c1[:3], c2[:3]))


def _encabezado(im, d: dict, tc: dict, t: float = 99.0) -> int:
    """El título de la diapositiva. Con movimiento (agro/movimiento.py, 20/11/2026): en Anton, la palabra clave en
    verde, entrando palabra por palabra; el subtítulo aparece después."""
    from agro import movimiento as MV
    dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, D.W, 8), fill=D.ACENTO)
    if not MV.activo():
        f, renglones = D.ajustar(dr, d["titulo"].upper(), "negra", 64, 44, D.W - 120, 2)
        y = 60
        for r in renglones:
            dr.text((60, y), r, font=f, fill=D.BLANCO)
            y += round(f.size * 1.1)
        if d.get("sub"):
            dr.text((60, y + 6), d["sub"], font=D.fuente("medium", 32), fill=tc["texto"])
            y += 52
        return y + 30
    y = MV.dibujar_titulo(im, 60, 50, _plan_titulo(d["titulo"]), t) + 16
    if d.get("sub"):
        u = MV.ease_out((t - 0.3) / 0.35)
        dr = ImageDraw.Draw(im)
        dr.text((60, y + 6), d["sub"], font=D.fuente("medium", 32), fill=_mezcla_color(tc["fondo"], tc["texto"], u))
        y += 52
    return y + 30


def _crecer(x: float) -> float:
    from agro import movimiento as MV
    return MV.ease_back(x) if (MV.activo() and x > 0) else _ease(x)


def _pie(im):
    from agro import movimiento as MV
    if MV.activo():
        MV.marca_pie(im, 52, 36, 34)


def placa_barras(d: dict, t: float, fuente: str) -> Image.Image:
    """El ranking: una barra por fila que crece; Chivilcoy (o `resaltar`) en naranja."""
    tc = _tema_color()
    im = Image.new("RGB", (D.W, D.H45), tc["fondo"])
    dr = ImageDraw.Draw(im)
    y = _encabezado(im, d, tc, t)
    dr = ImageDraw.Draw(im)
    filas = d["filas"][:10]
    resaltar = d.get("resaltar") or "Chivilcoy"
    alto_fila = min(96, (D.H45 - 90 - y) // max(1, len(filas)))
    tope = max(abs(v) for _, v in filas) or 1
    hay_neg = any(v < 0 for _, v in filas)
    x_nombre, x0, x1 = 60, 470, D.W - 190
    cero = x0 + (x1 - x0) * (0.35 if hay_neg else 0)
    # Sin negativos, la barra arranca en un piso por debajo del menor (no en 0): entre 36 y 41 qq/ha, con barras
    # desde 0 todas se ven iguales. El número va escrito en cada barra.
    minimo = min(v for _, v in filas)
    piso = 0.0 if hay_neg else max(0.0, minimo - (tope - minimo) * 0.5 - 1e-9) if tope > minimo else 0.0
    escala = (x1 - cero) / ((tope - piso) or 1)
    f_n = D.fuente("bold", min(40, alto_fila - 30))
    f_v = D.fuente("negra", min(44, alto_fila - 26))
    for i, (nombre, v) in enumerate(filas):
        crec = _crecer((t - _retraso() - 0.08 * i) / CRECER)
        yy = y + i * alto_fila
        es = nombre == resaltar
        color = D.NARANJA if es else (CELESTE if v >= 0 else D.ROJO)
        if not es and not hay_neg:
            color = GRIS_BARRA
        nom = nombre if dr.textlength(nombre, font=f_n) <= x0 - x_nombre - 20 else nombre[:16] + "…"
        dr.text((x_nombre, yy + (alto_fila - f_n.size) / 2 - 6), nom, font=f_n, fill=D.NARANJA if es else D.BLANCO)
        largo = ((v - piso) if v >= 0 else v) * escala * crec
        a, b = (cero, cero + largo) if largo >= 0 else (cero + largo, cero)
        if abs(largo) >= 2:
            dr.rounded_rectangle((a, yy + 14, b, yy + alto_fila - 14), radius=10, fill=color)
        if crec > 0.15:
            txt = _numero_txt(v, d.get("dec", 0), d.get("signo")) + (f" {d['unidad']}" if d.get("unidad") else "")
            xv = (b + 14) if v >= 0 else max(x0 - 10, a - 14 - dr.textlength(txt, font=f_v))
            if v >= 0:
                xv = min(xv, D.W - 40 - dr.textlength(txt, font=f_v))
            dr.text((xv, yy + (alto_fila - f_v.size) / 2 - 8), txt, font=f_v, fill=D.BLANCO)
    if hay_neg:
        dr.line((cero, y, cero, y + len(filas) * alto_fila), fill=tc["tenue"], width=2)
    dr.text((60, D.H45 - 56), fuente, font=D.fuente("regular", 22), fill=tc["tenue"])
    _pie(im)
    return im


def placa_serie(d: dict, t: float, fuente: str) -> Image.Image:
    """Campaña por campaña: columnas que aparecen de izquierda a derecha; la mejor en verde y la peor en rojo."""
    tc = _tema_color()
    im = Image.new("RGB", (D.W, D.H45), tc["fondo"])
    dr = ImageDraw.Draw(im)
    y = _encabezado(im, d, tc, t)
    dr = ImageDraw.Draw(im)
    serie = d["serie"]
    n = len(serie)
    base, techo = D.H45 - 250, y + 90
    x0, x1 = 60, D.W - 60
    paso = (x1 - x0) / n
    ancho = paso * 0.68
    tope = max(v for _, v in serie) or 1
    f_v = D.fuente("bold", 26 if n > 12 else 30)
    f_c = D.fuente("medium", 22 if n > 12 else 26)
    dur = 3.2
    for i, (camp, v) in enumerate(serie):
        crec = _ease((t - _retraso() - dur * i / n) / 0.5)
        if crec <= 0:
            continue
        xa = x0 + i * paso + (paso - ancho) / 2
        alto = (base - techo) * v / tope * crec
        color = D.VERDE if camp == d.get("mejor") else (D.ROJO if camp == d.get("peor") else GRIS_BARRA)
        if i == n - 1 and camp != d.get("mejor"):
            color = D.NARANJA
        dr.rounded_rectangle((xa, base - alto, xa + ancho, base), radius=6, fill=color)
        txt = _coma(v, 0) if v >= 100 else _coma(v, 1 if v < 10 else 0)
        dr.text((xa + ancho / 2 - dr.textlength(txt, font=f_v) / 2, base - alto - 34), txt, font=f_v, fill=D.BLANCO)
        etq = camp[2:]                                     # «2014/15» → «14/15»
        capa = Image.new("RGBA", (120, 40), (0, 0, 0, 0))
        ImageDraw.Draw(capa).text((0, 4), etq, font=f_c, fill=tc["texto"])
        capa = capa.rotate(60, expand=True)
        im.paste(capa, (round(xa + ancho / 2 - capa.width / 2 + 10), base + 10), capa)
    dr.line((x0, base, x1, base), fill=tc["tenue"], width=2)
    # Leyenda.
    yl = D.H45 - 100
    x = 60
    for etq, color in (("mejor", D.VERDE), ("peor", D.ROJO), ("la última", D.NARANJA)):
        dr.rounded_rectangle((x, yl + 6, x + 26, yl + 32), radius=6, fill=color)
        dr.text((x + 36, yl), etq, font=D.fuente("medium", 28), fill=tc["texto"])
        x += 36 + dr.textlength(etq, font=D.fuente("medium", 28)) + 40
    dr.text((60, D.H45 - 56), fuente, font=D.fuente("regular", 22), fill=tc["tenue"])
    _pie(im)
    return im


def placa_lista(d: dict, t: float, fuente: str) -> Image.Image:
    tc = _tema_color()
    im = Image.new("RGB", (D.W, D.H45), tc["fondo"])
    dr = ImageDraw.Draw(im)
    y = _encabezado(im, d, tc, t)
    dr = ImageDraw.Draw(im)
    filas = d["filas"][:7]
    alto = min(130, (D.H45 - 110 - y) // max(1, len(filas)))
    y += max(0, (D.H45 - 110 - y - alto * len(filas)) // 3)      # pocas filas: un poco más abajo, no pegadas arriba
    for i, (izq, der) in enumerate(filas):
        a = _ease((t - _retraso() - 0.25 * i) / 0.4)
        if a <= 0:
            continue
        dx = round(160 * (1 - a))                          # entra desde la derecha
        yy = y + i * alto
        dr.rounded_rectangle((60 + dx, yy, D.W - 60 + dx, yy + alto - 18), radius=18, fill=tc["linea"])
        f = D.fuente("bold", 40)
        dr.text((92 + dx, yy + (alto - 18) / 2 - 26), izq, font=f, fill=D.BLANCO)
        fd = D.fuente("negra", 40)
        color = D.NARANJA if "sequ" in str(der).lower() else CELESTE
        dr.text((D.W - 92 + dx - dr.textlength(str(der), font=fd), yy + (alto - 18) / 2 - 26), str(der), font=fd,
                fill=color)
    dr.text((60, D.H45 - 56), fuente, font=D.fuente("regular", 22), fill=tc["tenue"])
    _pie(im)
    return im


def placa_mapa(d: dict, t: float, fuente: str) -> Image.Image:
    """El mapa de la zona con el dato del tema (agro/mapa_zona.py): la primera diapositiva, con el gancho arriba."""
    from agro import mapa_zona as MZ
    tc = _tema_color()
    im = Image.new("RGBA", (D.W, D.H45), tc["fondo"] + (255,))
    dr = ImageDraw.Draw(im)
    y = _encabezado(im, d, tc, t)
    dr = ImageDraw.Draw(im)
    fmt = (lambda v: _numero_txt(v, d.get("dec", 0), d.get("signo")) + (d.get("unidad") or ""))
    alto = D.H45 - 70 - y
    m = MZ.dibujar(d["valores"], t, 980, alto, fmt=fmt, divergente=d.get("divergente", False), fondo=tc["linea"],
                  paleta=d.get("paleta", "verde"))
    im.alpha_composite(m, ((D.W - m.width) // 2, y))
    dr.text((60, D.H45 - 56), fuente, font=D.fuente("regular", 22), fill=tc["tenue"])
    _pie(im)
    return im.convert("RGB")


DURACION = {"mapa": 5.0, "video": 4.2, "barras": 6.0, "serie": 6.5, "lista": 5.0, "cierre": 2.6}
DURACION_GANCHO = 3.4                 # (ya no hay gancho con video: los reels arrancan con la info, 20/11/2026)


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def elegir_video(tag: str, usados: dict, ahora: datetime, indice: list = None) -> dict | None:
    """Un video del banco de ese tema (si no hay, de «campo»), el usado hace más tiempo. El banco está APAGADO para
    las NOTICIAS desde el 17/11 (ahí va el video original de la nota); en estos reels de datos no hay video
    original: van ilustrativos, rotulados como tales y con el crédito del autor."""
    from agro import banco_video as BVI
    indice = BVI.cargar_indice() if indice is None else indice
    for t in (tag, "campo"):
        del_tag = [v for v in indice if v.get("tag") == t]
        if del_tag:
            return min(del_tag, key=lambda v: ((usados or {}).get(v["archivo"], ""), -(v.get("impacto") or 5)))
    return None


def videos_para(tema: dict, mem: dict, ahora: datetime, carpeta: Path, log=print, bajar=None, elegir=None) -> dict:
    """{índice de diapositiva: (clip, crédito)} con un video DISTINTO del banco para cada diapositiva de video."""
    from agro import banco_video as BVI
    bajar = bajar or BVI.bajar
    elegir = elegir or (lambda tag, usados, ahora_: elegir_video(tag, usados, ahora_))
    usados = dict(mem.get("banco_usados") or {})
    salida = {}
    for i, (tipo, d) in enumerate(tema["diapositivas"]):
        if tipo != "video":
            continue
        v = elegir(d.get("video") or "campo", usados, ahora)
        if not v:
            continue
        BVI.anotar(usados, v, ahora)
        clip = bajar(v, Path(carpeta) / f"banco_{i:02d}_{v['archivo']}")
        if clip:
            salida[i] = (clip, BVI.credito(v), v)
        else:
            log(f"   el video {v['archivo']} no se pudo bajar")
    mem["banco_usados"] = usados
    return salida


def _fondo_sin_video() -> Image.Image:
    tc = _tema_color()
    im = Image.new("RGB", (D.W, ALTO_VIDEO), tc["linea"])
    iso = D.isologo(260)
    im.paste(iso, ((D.W - iso.width) // 2, (ALTO_VIDEO - iso.height) // 2), iso)
    return im


def eventos_sonido(planes: list) -> list:
    """Los efectos del reel, en el mismo ritmo que el dibujo (agro/movimiento.py): soplido en cada transición, un
    pop por palabra del título, por barra y por fila, tics mientras cuenta un número o aparecen columnas y partidos,
    y la placa final (teclas y campanita)."""
    from agro import movimiento as MV
    from agro import reel as RE
    ev, s0 = [], 0.0
    for idx, (tipo, d, dur, _vid) in enumerate(planes):
        if idx:
            ev.append((s0, MV.brisa(), 0.5))
        if (tipo in ("barras", "serie", "lista", "mapa") or (tipo == "video" and d.get("titulo"))) and d.get("titulo"):
            ev += MV.eventos_titulo(s0, MV.palabras_de(_plan_titulo(d["titulo"])))
        if tipo == "barras":
            ev += [(s0 + RETRASO + 0.08 * i, MV.pop(1.0 + 0.05 * i), 0.32) for i in range(len(d["filas"][:10]))]
        elif tipo == "lista":
            ev += [(s0 + RETRASO + 0.25 * i, MV.pop(1.1 + 0.05 * i), 0.4) for i in range(len(d["filas"][:7]))]
        elif tipo == "serie":
            n = len(d["serie"])
            ev += [(s0 + RETRASO + 3.2 * i / n, MV.tic(1 + 0.02 * i), 0.35) for i in range(n)]
        elif tipo == "mapa":
            n = len(d.get("valores") or {})
            ev += [(s0 + 0.2 + 1.6 * i / max(1, n), MV.tic(0.8 + 0.04 * i), 0.3) for i in range(n)]
        elif tipo == "video" and d.get("numero") is not None:
            ev += [(s0 + j * 0.065, MV.tic(0.9 + 0.03 * j), 0.25) for j in range(int(CONTAR / 0.065))]
            ev.append((s0 + CONTAR, MV.pop(0.9), 0.6))
        elif tipo == "cierre":
            ev += RE.eventos_cierre(s0)
        elif tipo == "propia" and d.get("pops"):           # las placas con micro animaciones (agro/micro.py)
            from agro import micro as MI
            ev += MI.eventos(d["pops"], s0)
        s0 += dur
    return ev


def armar(tema: dict, salida: Path, videos: dict = None) -> dict:
    """El .mp4 4:5 y su portada .jpg (la primera diapositiva ya completa). 20/11/2026 (agro/movimiento.py): con
    transiciones que empujan, barra de progreso, títulos que entran palabra por palabra, la placa final animada y
    SONIDO (los efectos del reel de entrevistas del diario y una base suave); AGRO_REEL_SONIDO=0 lo deja mudo."""
    from agro import movimiento as MV
    from agro import reel as RE
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    videos = videos or {}
    fuente = tema.get("fuente") or FUENTE_CORTA
    animado = MV.activo()
    planes = []
    for i, (tipo, d) in enumerate(tema["diapositivas"]):
        # «propia» (20/11/2026, agro/reel_tiempo.py): la diapositiva la dibuja d["fn"](t) durante d["dur"] segundos.
        dur = d["dur"] if tipo == "propia" else (DURACION_GANCHO if (tipo == "video" and d.get("titulo"))
                                                 else DURACION[tipo])
        if tipo == "cierre" and animado:
            dur = RE.CIERRE_DURACION
        planes.append((tipo, d, dur, videos.get(i)))
    total = sum(p[2] for p in planes)
    wav = salida.with_suffix(".wav")
    sonido = MV.con_sonido()
    if sonido:
        MV.guardar_wav(MV.mezclar(eventos_sonido(planes), total, MV.con_musica()), wav)
        audio = ["-i", str(wav)]
    else:
        audio = ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{D.W}x{D.H45}",
           "-r", str(FPS), "-i", "-", *audio, "-shortest",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k" if sonido else "64k", "-movflags", "+faststart", str(salida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    portada, previo, fin_anterior = None, None, None
    cierre = RE.cierre("grafito", "").convert("RGB")
    t_global = 0.0
    try:
        for tipo, d, dur, vid in planes:
            n = round(dur * FPS)
            if tipo == "cierre":
                cierre = RE.cierre("grafito", d.get("frase", "")).convert("RGB")
            cuadros_vid = RE._cuadros_video(vid[0], D.W, ALTO_VIDEO, dur + 0.5) if (tipo == "video" and vid) else None
            fondo_fijo = _fondo_sin_video() if (tipo == "video" and not vid) else None
            for k in range(n):
                t = k / FPS
                if tipo == "video":
                    arriba = next(cuadros_vid, None) if cuadros_vid else None
                    lienzo = Image.new("RGBA", (D.W, D.H45), (0, 0, 0, 255))
                    lienzo.paste(arriba if arriba is not None else fondo_fijo, (0, 0))
                    lienzo.alpha_composite(capa_video(d, t, vid[1] if vid else "", fuente))
                    cuadro = lienzo.convert("RGB")
                elif tipo == "barras":
                    cuadro = placa_barras(d, t, fuente)
                elif tipo == "serie":
                    cuadro = placa_serie(d, t, fuente)
                elif tipo == "lista":
                    cuadro = placa_lista(d, t, fuente)
                elif tipo == "propia":
                    cuadro = d["fn"](t).convert("RGB")
                elif tipo == "mapa":
                    cuadro = placa_mapa(d, t, fuente)
                elif animado:
                    cuadro = RE.cierre("grafito", d.get("frase", ""), t=t).convert("RGB")
                else:
                    cuadro = cierre
                limpio = cuadro
                if fin_anterior is not None and t < (MV.TRANSICION if animado else FUNDIDO):
                    cuadro = (MV.transicion(fin_anterior, cuadro, t) if animado
                              else Image.blend(fin_anterior, cuadro, t / FUNDIDO))
                if animado:
                    cuadro = cuadro.copy() if cuadro is limpio else cuadro
                    MV.progreso(cuadro, (t_global + t) / total)
                proc.stdin.write(cuadro.tobytes())
                previo = limpio
            t_global += n / FPS
            fin_anterior = previo
            if portada is None:                            # la portada: la primera diapositiva ya completa
                portada = previo.copy()
            if cuadros_vid is not None:
                cuadros_vid.close()
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not salida.exists():
            raise RuntimeError(f"ffmpeg: {err[-300:]}")
    finally:
        if proc.poll() is None:
            proc.kill()
        if wav.exists():
            try:
                wav.unlink()
            except OSError:
                pass
    jpg = salida.with_suffix(".jpg")
    (portada or previo).save(jpg, "JPEG", quality=90)
    return {"archivo": str(salida), "duracion": total, "peso_kb": round(salida.stat().st_size / 1024), "ancho": D.W,
            "alto": D.H45, "vista": str(jpg), "tema": "grafito", "con_video": bool(videos), "con_sonido": sonido}


def caption(tema: dict, videos: dict) -> str:
    partes = list(tema["texto"])
    fuente = tema.get("fuente") or FUENTE_CORTA
    partes.append(fuente + (" (argenfields.com)." if "ArgenFields" in fuente else "."))
    creditos = sorted({c for _clip, c, _v in (videos or {}).values()})
    if creditos:
        partes.append("🎥 Videos ilustrativos: " + "; ".join(creditos) + ".")
    partes.append(" ".join(tema.get("hashtags") or ["#Chivilcoy", "#Campo", "#Agro"]))
    return "\n\n".join(partes)


def pieza(tema: dict, reel: dict, texto: str, horario: datetime) -> dict:
    """La pieza con la forma que espera agro/publicar.publicar_reel (solo Facebook e Instagram)."""
    g = {"titular": tema["gancho"], "bajada": tema["texto"][0][:200], "descripcion": texto, "hashtags": [],
         "titulo_web": "", "nota_web": "", "apta": True, "requires_review": False, "volanta": "Datos de la zona"}
    return {"id": f"zona-{tema['tema']}-{horario:%Y%m%d%H%M}",
            "rep": {"url": "", "titulo": tema["gancho"], "fuente": "ArgenFields"}, "grupo": [],
            "score": {"subtema": "agro", "tema_doc": "zona", "ai_score": 0}, "guion": g, "formato": "reel",
            "youtube": False, "redes": ("facebook", "instagram"), "reel": reel, "portada": reel["vista"],
            "imagen": {"origen": "datos"}, "colab_diario": con_colab()}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Publicar: agro (IG con colab + FB) y la página de Facebook del diario
# ─────────────────────────────────────────────────────────────────────────────────────────────
def publicar(p: dict, log=print, publicar_reel=None, aceptar=None, fb_del_diario=None) -> dict:
    from agro import publicar as PUB
    publicar_reel = publicar_reel or PUB.publicar_reel
    res = publicar_reel(p, None, ("facebook", "instagram"), log=log, portada_url=PUB._subir_portada(p))
    ig = res.get("instagram") or {}
    if ig.get("id") and ig.get("colab") == "si":
        try:
            res["colab"] = (aceptar or PUB.aceptar_colab)(ig["id"], log=log)
        except Exception as e:                             # noqa: BLE001 — la colab se puede aceptar a mano
            res["colab"] = {"estado": "pendiente", "detalle": f"{type(e).__name__}: {str(e)[:200]}"}
    if fb_diario():
        try:
            res["facebook_diario"] = (fb_del_diario or _facebook_diario)(p, log)
        except Exception as e:                             # noqa: BLE001
            res["facebook_diario"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook del diario FALLÓ: {res['facebook_diario']['error']}")
    return res


def _facebook_diario(p: dict, log=print) -> dict:
    """El mismo reel en la página de Facebook de @diarioyradio (Facebook no tiene colab)."""
    from agro import publicar as PUB
    from reels import publicador as PB
    PUB.credenciales_diario()                              # salvaguarda: tienen que ser las del diario
    r = PB.publicar_facebook(PUB.pieza_publicador(p), Path(p["reel"]["archivo"]), "")
    r["miniatura"] = PUB._miniatura_facebook(r.get("id"), p.get("portada"))
    log(f"   Facebook @diarioyradio: video {r.get('id')}")
    return r


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La corrida
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _ahora() -> datetime:
    return datetime.now(TZ_AR)


def corrida(publicar_: bool, tema_pedido: str = "", ahora: datetime = None, ruta_mem: Path = None,
            af: dict = None, lluvia_fn=None, log=print, publicador=None, videos_fn=None) -> dict:
    ahora = ahora or _ahora()
    hoy = ahora.date()
    dia = hoy.isoformat()
    mem = cargar(ruta_mem)
    inf = {"cuando": ahora.isoformat(timespec="minutes"), "publicar": publicar_, "estado": ""}
    if not activo():
        inf["estado"] = "apagado"
        return inf
    if publicar_ and not tema_pedido:
        desde, hasta = ventana(hoy)
        if not (desde - timedelta(minutes=30) <= ahora <= hasta):
            inf["estado"] = "fuera_de_hora"
            log(f"Reel de la zona: {ahora:%H:%M} está fuera de {desde:%H:%M}-{hasta:%H:%M}; no se hace nada")
            return inf
        if ya_hoy(mem, dia):
            inf["estado"] = "ya_salio"
            log("Reel de la zona: el de hoy ya salió")
            return inf
    af = af if af is not None else datos_argenfields()
    disponibles = temas_disponibles(af, hoy)
    lluvia_mm = None
    if not tema_pedido or tema_pedido == "lluvia":
        try:
            from agro import reel_clima as RC
            lluvia_mm = (lluvia_fn or RC.lluvia_chivilcoy)(ahora)
        except Exception as e:                             # noqa: BLE001 — sin pronóstico, otro tema
            log(f"   pronóstico: {type(e).__name__}: {e}")
    clave = tema_pedido or elegir_tema(mem, disponibles, hoy, lluvia_mm)
    inf["tema"] = clave
    inf["lluvia_mm"] = lluvia_mm
    log(f"Reel de la zona de {dia}: tema «{clave}» (lluvia prevista en Chivilcoy: "
        f"{'—' if lluvia_mm is None else f'{lluvia_mm:.0f} mm'}; temas con datos: {len(disponibles)})")
    if not clave:
        inf["estado"] = "sin_tema"
        return inf
    if publicar_:
        _desde, hasta = ventana(hoy)
        # Para no publicar dos veces si la corrida se corta: queda anotado ANTES de publicar.
        anotado = {"dia": dia, "tema": clave, "cuando": ahora.isoformat(timespec="minutes"), "publicado": None}
        mem.setdefault("reels", []).append(anotado)
        guardar(mem, ruta_mem)
    carpeta = SALIDA / f"zona_{ahora:%Y-%m-%d_%H%M}_{clave}"
    carpeta.mkdir(parents=True, exist_ok=True)
    if clave == "lluvia":
        from agro import reel_clima as RC
        datos_ = RC.datos(ahora, log=log)
        if not datos_:
            inf["estado"] = "sin_datos"
            return inf
        p = RC.pieza(datos_, ahora, carpeta)
        p["id"] = f"zona-lluvia-{ahora:%Y%m%d%H%M}"
        p["colab_diario"] = con_colab()
        texto = p["guion"]["descripcion"]
    else:
        tema = disponibles.get(clave)
        if not tema:
            inf["estado"] = "sin_datos"
            log(f"   el tema «{clave}» no tiene datos")
            return inf
        videos = (videos_fn or videos_para)(tema, mem, ahora, carpeta, log)
        reel = armar(tema, carpeta / f"zona_{clave}.mp4", videos)
        texto = caption(tema, videos)
        p = pieza(tema, reel, texto, ahora)
    (carpeta / "texto.txt").write_text(texto, encoding="utf-8")
    inf["reel"] = p["reel"]
    inf["texto"] = texto
    log(f"   reel: {p['reel']['duracion']:.0f} s, {p['reel']['peso_kb']} KB → {p['reel']['archivo']}")
    if not publicar_:
        inf["estado"] = "simulado"
        return inf
    res = (publicador or publicar)(p, log=log)
    anotado["publicado"] = {k: v for k, v in res.items() if k != "portada_url"}
    ok = [r for r in ("instagram", "facebook", "facebook_diario") if isinstance(res.get(r), dict)
          and res[r].get("id")]
    anotado["redes"] = ok
    guardar(mem, ruta_mem)
    inf["estado"] = "ok" if ok else "fallo"
    inf["resultado"] = res
    return inf


def informe(inf: dict) -> str:
    l = [f"## Reel de datos de la zona ({inf.get('cuando')})", "", f"- Estado: {inf.get('estado')}",
         f"- Tema: {inf.get('tema') or '—'}"]
    if inf.get("reel"):
        l.append(f"- Reel: {inf['reel']['duracion']:.0f} s, {inf['reel']['peso_kb']} KB")
    res = inf.get("resultado") or {}
    for red in ("instagram", "facebook", "facebook_diario", "colab"):
        if red in res:
            v = res[red] or {}
            l.append(f"- {red}: {v.get('id') or v.get('estado') or v.get('error') or v}")
    if inf.get("texto"):
        l += ["", "```", inf["texto"], "```"]
    return "\n".join(l)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--tema", default="")
    ap.add_argument("--todos", action="store_true", help="arma todos los temas (simulando)")
    a = ap.parse_args()
    if a.todos:
        ahora = _ahora()
        af = datos_argenfields()
        for clave in temas_disponibles(af, ahora.date()):
            inf = corrida(False, clave, ahora=ahora, af=af, ruta_mem=SALIDA / "zona_memoria_simulada.json")
            print(informe(inf))
        return
    inf = corrida(a.publicar, a.tema)
    print(informe(inf))
    if a.publicar and inf.get("estado") == "fallo":
        sys.exit(1)


if __name__ == "__main__":
    main()
