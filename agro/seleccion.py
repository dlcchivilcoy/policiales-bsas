# -*- coding: utf-8 -*-
"""Selección editorial (puntos 6 y 7 del documento): solo score ≥ AGRO_SCORE_MIN (75), hasta
AGRO_MAX_DIA por día, con la mezcla por subtema y sin repetir el mismo tema seguido.

ARRANQUE (decisión del editor, 13/10/2026): 3 reels por día en 3 pasadas, 1 por pasada, en los
mejores horarios: AGRO_MAX_DIA=3, AGRO_POR_PASADA=1, AGRO_PASADAS="07:00,12:30,20:30". El documento
hablaba de 8-12 por día: se sube de a poco cambiando esas tres variables, sin tocar código.

La mezcla (AGRO_MEZCLA, editable) fija un TOPE por subtema dentro del cupo del día:
30 % agro, 20 % mercados, 20 % AgTech, 10 % maquinaria, 10 % ganadería, 10 % empresas.
Si un subtema no tiene candidatas, su lugar lo puede ocupar otra solo si es muy buena
(score ≥ mínimo + REFUERZO): mejor publicar menos que rellenar.

17/10/2026 (documento «ideas agro»): 3 REELS + 3 CARRUSELES por día → AGRO_MAX_DIA = 6 noticias (las
historias son de datos y no cuentan). El orden ya no es solo el puntaje: una noticia URGENTE (alerta
meteorológica, problema sanitario, cambio normativo relevante) va primero, y los 10 temas fundamentales
del documento suman un poco según su prioridad (clima primero, reglas y agenda al final). Para el
carrusel pesa además si la noticia se puede EXPLICAR (potencial_carrusel).

19/10/2026: 6 corridas con 1 reel + 1 carrusel cada una → AGRO_MAX_DIA = 12.

20/10/2026: 6 corridas con 5 reels cada una, cada reel de un sitio distinto → AGRO_MAX_DIA = 36 (30 y
margen para las que fallan al publicar) y AGRO_SCORE_MIN = 60: con 75 había corridas sin ninguna y la
mejor de cada sitio rara vez llega.

06/11/2026: 9 noticias por día → AGRO_MAX_DIA = 12 (9 y margen). La mezcla y el empuje siguen lo que se vio en
397 posteos (mediana de vistas): clima 248, sanidad 144, ganadería 114, contra precios 64 y campaña 56; por
subtema, ganadería 134 y mercados 71.
"""
import math
import os

# 20/11/2026: recalibrada con 15 días de métricas de Instagram (167 posteos, alcance mediano): clima y temporales 383,
# sucesos del campo (incendios, muertes, robos, lo insólito) 1.187, contra maquinaria/AgTech/empresas 39 y
# mercados/precios 57. Con 12 por día los topes eran 2 por cada uno de esos cuatro (hasta 8 de los que menos llegan);
# ahora 1 cada uno, y el resto para el campo y la ganadería.
MEZCLA_DEFECTO = {"agro": 45, "ganaderia": 30, "maquinaria": 7, "mercados": 6, "agtech": 6, "empresas": 6}
REFUERZO = 10
MAX_MISMO_TEMA = 2          # por día: el mismo cultivo, empresa o tema
MAX_CLIMA = 3               # por día, salvo una urgente: rinde más que el resto, pero 5 de 9 cansan (06/11/2026)


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int((os.environ.get(nombre) or "").strip()))
    except ValueError:
        return defecto


def score_min() -> int:
    return _entero("AGRO_SCORE_MIN", 60)


def max_dia() -> int:
    return _entero("AGRO_MAX_DIA", 16)                 # 20/11/2026: 12 noticias por día (y margen); antes 12


def por_pasada() -> int:
    return _entero("AGRO_POR_PASADA", 1) or 1


PASADAS_DEFECTO = "07:00,12:30,20:30"


def pasadas() -> list:
    """[(hora, minuto), …] de AGRO_PASADAS, ordenadas. Lo que no se entiende se saltea."""
    salida = []
    for parte in (os.environ.get("AGRO_PASADAS") or PASADAS_DEFECTO).split(","):
        h, _, m = parte.strip().partition(":")
        try:
            if 0 <= int(h) < 24 and 0 <= int(m or 0) < 60:
                salida.append((int(h), int(m or 0)))
        except ValueError:
            continue
    return sorted(set(salida)) or [(7, 0), (12, 30), (20, 30)]


# Lo que suma cada tema fundamental al ORDEN (no al puntaje), según las vistas reales (06/11/2026).
# 20/11/2026: recalibrado (ver MEZCLA_DEFECTO): clima empuja más; precios, campaña y mercados del mundo restan.
EMPUJE_TEMA = {"clima": 15, "sanidad": 5, "ganaderia": 5, "tecnologia": 0, "costos": 0, "reglas": 0, "dolar": 0,
               "internacional": -3, "precios": -4, "campana": -2}
URGENTE_TOLERANCIA = 10     # una urgente entra aunque le falten hasta 10 puntos para el mínimo
BONO_ZONA = 8               # una nota de un diario de la zona sale antes (ordena; el mínimo se mira igual)


def bono_video() -> int:
    """Puntos de prioridad para la nota que trae un video corto propio (31/10/2026, pedido del editor:
    «priorizar notas con videos y poner videos en reels»). AGRO_BONO_VIDEO; 0 lo apaga."""
    return _entero("AGRO_BONO_VIDEO", 15)


def prioridad(s: dict, formato: str = "reel") -> tuple:
    """La clave de orden de una candidata: (urgente, puntaje + empuje del tema [+ carrusel] [+ video], comercial).
    El bono del video ordena, no salva: el mínimo de puntaje se sigue mirando sobre ai_score."""
    valor = s["ai_score"] + EMPUJE_TEMA.get(s.get("tema_doc") or "", 0)
    if s.get("de_zona"):
        valor += BONO_ZONA
    if s.get("policial_rural"):
        valor += BONO_POLICIAL_RURAL
    if formato == "carrusel":
        valor += 2 * (s.get("potencial_carrusel", 5) - 5)
        if s.get("con_video") and not s.get("urgente") and (os.environ.get("AGRO_GRILLA") or "1").strip() != "0":
            valor -= RESERVA_VIDEO                     # 16/11/2026: la que trae video espera el turno de reel
    elif s.get("con_video"):
        valor += bono_video()
        if s.get("policial_rural"):
            valor += BONO_POLICIAL_VIDEO               # 17/11/2026: un policial con video por turno de reel
    return (bool(s.get("urgente")), valor, s.get("commercial_score", 0))


# 17/11/2026 (pedido del editor: «tratá de subir un policial con video por corrida normal para el feed»): en un turno
# de reel, el policial del campo que trae video va primero (salvo una alerta urgente) y entra con
# AGRO_POLICIAL_VIDEO_TOLERANCIA puntos menos que el mínimo (en vez de AGRO_VIDEO_TOLERANCIA).
BONO_POLICIAL_VIDEO = 40


def policial_video_tolerancia() -> int:
    try:
        return max(0, int(os.environ.get("AGRO_POLICIAL_VIDEO_TOLERANCIA") or 20))
    except ValueError:
        return 20


# 16/11/2026 (pedido del editor: «priorizá encontrar noticias con videos para armar reels»). En la grilla intercalada
# (agro/agenda.py) los turnos de carrusel dejan para el reel siguiente la nota que trae video, y en un turno de reel
# una nota con video entra con hasta VIDEO_TOLERANCIA puntos menos que el mínimo.
RESERVA_VIDEO = 40


def video_tolerancia() -> int:
    try:
        return max(0, int(os.environ.get("AGRO_VIDEO_TOLERANCIA") or 10))
    except ValueError:
        return 10


def minimo_de(s: dict, minimo: int, formato: str) -> int:
    """El puntaje mínimo de ESA candidata: más bajo si trae video y el turno es de reel."""
    if formato == "reel" and s.get("con_video"):
        return minimo - max(video_tolerancia(), policial_video_tolerancia() if s.get("policial_rural") else 0)
    return minimo


# 16/11/2026 (pedido del editor: «priorizá videos de policiales en el campo» y «contenido variado en el feed, también
# innovaciones tecnológicas»):
# - un policial del campo (agro/fuentes.es_policial_rural: abigeato, robos en campos, incendios rurales) va antes;
# - si en el día todavía no salió nada de tecnología o maquinaria, desde el tercer posteo una de esas entra con
#   INNOVACION_TOLERANCIA puntos menos y va adelante (el puntaje de la IA no premia la innovación: sin esto casi
#   nunca llegaba al mínimo);
# - el mismo subtema que el último posteo va un poco atrás (VARIEDAD), para que el feed no repita.
BONO_POLICIAL_RURAL = 20    # 20/11/2026: de 12 a 20 (los sucesos del campo, 1.187 de alcance mediano)
INNOVACION = ("agtech", "maquinaria")
BONO_INNOVACION = 15
VARIEDAD = 8


def innovacion_tolerancia() -> int:
    return _entero("AGRO_INNOVACION_TOLERANCIA", 15) if (os.environ.get("AGRO_INNOVACION_TOLERANCIA") or "").strip() != "0" else 0


def falta_innovacion(de_hoy: list) -> bool:
    return len(de_hoy) >= 2 and innovacion_tolerancia() > 0 and not any(
        (p.get("score") or {}).get("subtema") in INNOVACION for p in de_hoy)


def mezcla() -> dict:
    """AGRO_MEZCLA="agro:30,mercados:20,…" o la del documento."""
    crudo = (os.environ.get("AGRO_MEZCLA") or "").strip()
    if not crudo:
        return dict(MEZCLA_DEFECTO)
    m = {}
    for parte in crudo.split(","):
        k, _, v = parte.partition(":")
        try:
            m[k.strip().lower()] = max(0, int(v))
        except ValueError:
            continue
    return m or dict(MEZCLA_DEFECTO)


def topes(cupo_dia: int, m: dict = None) -> dict:
    m = m or mezcla()
    total = sum(m.values()) or 1
    # Hacia arriba (17/10/2026): con 6 por día, «20 % mercados» daba 1 y una tarde de pendientes de
    # mercados y ganadería dejó el carrusel de las 13:00 sin nada.
    return {k: max(1, math.ceil(cupo_dia * v / total)) for k, v in m.items()}


# 20/11/2026 (pedido del editor: «fijate qué formato es más óptimo según la temática y adaptá la temática al formato
# más adecuado»). El turno ya no es reel o carrusel por alternancia fija: lo decide la mejor nota disponible.
#   REEL: lo que se MIRA (necesita video propio): clima y temporales (lo que más rinde en la cuenta), ganadería,
#         maquinaria y tecnología en acción, policiales del campo, lo que no se explica en láminas.
#   CARRUSEL: lo que se EXPLICA y se GUARDA: precios, dólar, costos, leyes e impuestos, avance de campaña, mercados
#         del mundo, sanidad (cómo prevenir), guías; y toda nota sin video propio.
# Para que el feed siga intercalado, nunca más de DOS seguidos del mismo formato si el otro tiene una nota que
# vale al menos el 80 % de la mejor. AGRO_FORMATO_TEMA=0 vuelve a la alternancia fija.
TEMAS_REEL = ("clima", "ganaderia", "tecnologia")
SUBTEMAS_REEL = ("ganaderia", "maquinaria", "agtech")
TEMAS_CARRUSEL = ("precios", "dolar", "costos", "reglas", "campana", "internacional", "sanidad")
SEGUIDOS_MAX = 2


def formato_tema() -> bool:
    return (os.environ.get("AGRO_FORMATO_TEMA") or "1").strip() != "0"


def formato_ideal(s: dict) -> str:
    """«reel» o «carrusel» según el tema de la nota (y si trae video propio)."""
    if s.get("con_video"):
        if (s.get("tema_doc") in TEMAS_REEL or s.get("subtema") in SUBTEMAS_REEL or s.get("policial_rural")
                or s.get("urgente") or s.get("potencial_carrusel", 5) < 6):
            return "reel"
        if s.get("tema_doc") in TEMAS_CARRUSEL:
            return "carrusel"
        return "reel"
    return "carrusel"


def formato_turno(candidatos: list, nominal: str, ultimos: list, minimo: int = None) -> tuple:
    """(formato, motivo) del turno. `candidatos`: [{"score": {...}}]; `ultimos`: los formatos del feed de hoy, del
    más viejo al más nuevo. Sin candidatas que pasen el mínimo, el nominal de la agenda."""
    if not formato_tema():
        return nominal, "alternancia fija"
    minimo = score_min() if minimo is None else minimo
    mejor = {}
    for c in candidatos:
        sc = c.get("score") or {}
        f = formato_ideal(sc)
        if sc.get("ai_score", 0) < minimo_de(sc, minimo, f) and not (sc.get("urgente") and sc.get("ai_score", 0)
                                                                     >= minimo - URGENTE_TOLERANCIA):
            continue
        v = prioridad(sc, f)
        if f not in mejor or v > mejor[f][0]:
            mejor[f] = (v, (sc.get("titulo") or c.get("id") or "")[:50])
    if not mejor:
        return nominal, "sin notas que pasen el mínimo"
    elegido = max(mejor, key=lambda f: mejor[f][0])
    otro = "carrusel" if elegido == "reel" else "reel"
    seguidos = len(ultimos) >= SEGUIDOS_MAX and all(u == elegido for u in ultimos[-SEGUIDOS_MAX:])
    if seguidos and otro in mejor and mejor[otro][0][1] >= 0.8 * mejor[elegido][0][1]:
        return otro, f"{SEGUIDOS_MAX} {elegido}s seguidos: va {otro}"
    return elegido, f"la mejor nota es para {elegido}"


def elegir(candidatos: list, de_hoy: list, cupo_dia: int = None, minimo: int = None, formato: str = "reel",
           relajar: bool = False) -> tuple:
    """`relajar`: el horario se quedaría vacío → la reserva (tope del subtema lleno) entra con el mínimo,
    sin el refuerzo. La agenda pide 3 reels y 3 carruseles: mejor repetir subtema que no publicar."""
    """(elegidos, descartados_con_motivo). `candidatos`: [{"id", "score": {...}}, …] (un
    representante por grupo). `de_hoy`: lo ya elegido hoy (cuenta para cupo, mezcla y temas)."""
    cupo_dia = max_dia() if cupo_dia is None else cupo_dia
    minimo = score_min() if minimo is None else minimo
    tope = topes(cupo_dia)
    usados = {}
    temas = {}
    clima = 0
    for p in de_hoy:
        s = p.get("score") or {}
        usados[s.get("subtema")] = usados.get(s.get("subtema"), 0) + 1
        clima += s.get("tema_doc") == "clima"
        if s.get("tema"):
            temas[s["tema"]] = temas.get(s["tema"], 0) + 1
    lugar = cupo_dia - len(de_hoy)
    innovar = falta_innovacion(de_hoy)
    ultimo_sub = ((de_hoy[-1].get("score") or {}).get("subtema") if de_hoy else None)

    def clave(c):
        urg, valor, com = prioridad(c["score"], formato)
        sub = c["score"].get("subtema")
        if innovar and sub in INNOVACION:
            valor += BONO_INNOVACION
        if ultimo_sub and sub == ultimo_sub:
            valor -= VARIEDAD
        return urg, valor, com
    orden = sorted(candidatos, key=clave, reverse=True)
    elegidos, descartados, reserva = [], [], []
    for c in orden:
        s = c["score"]
        propio = minimo_de(s, minimo, formato) - (innovacion_tolerancia() if innovar and s.get("subtema") in INNOVACION else 0)
        if s["ai_score"] < propio and not (s.get("urgente") and s["ai_score"] >= propio - URGENTE_TOLERANCIA):
            descartados.append((c, f"score {s['ai_score']} < {propio}"))
            continue
        if s.get("tema") and temas.get(s["tema"], 0) >= MAX_MISMO_TEMA:
            descartados.append((c, f"ya hay {MAX_MISMO_TEMA} del tema «{s['tema']}» hoy"))
            continue
        # Una urgente puede pasarse por una: la IA marca como urgente más de lo que es.
        if s.get("tema_doc") == "clima" and clima >= MAX_CLIMA + bool(s.get("urgente")):
            descartados.append((c, f"ya hay {clima} de clima hoy"))
            continue
        if lugar <= 0:
            descartados.append((c, f"cupo del día lleno ({cupo_dia})"))
            continue
        if usados.get(s["subtema"], 0) >= tope.get(s["subtema"], 1):
            reserva.append(c)
            continue
        elegidos.append(c)
        lugar -= 1
        usados[s["subtema"]] = usados.get(s["subtema"], 0) + 1
        clima += s.get("tema_doc") == "clima"
        if s.get("tema"):
            temas[s["tema"]] = temas.get(s["tema"], 0) + 1
    for c in reserva:
        s = c["score"]
        # Relajado, nunca el mismo tema que algo de hoy (la misma noticia contada por otro medio).
        if lugar > 0 and s["ai_score"] >= minimo + (0 if relajar else REFUERZO)                 and temas.get(s.get("tema"), 0) < (1 if relajar else MAX_MISMO_TEMA):
            elegidos.append(c)
            lugar -= 1
            if s.get("tema"):
                temas[s["tema"]] = temas.get(s["tema"], 0) + 1
        else:
            descartados.append((c, f"tope de {s['subtema']} del día ({tope.get(s['subtema'], 1)}) "
                                   "y no llega al refuerzo"))
    return ordenar_variado(elegidos, de_hoy), descartados


def ordenar_variado(elegidos: list, de_hoy: list) -> list:
    """El orden de salida: nunca dos del mismo subtema seguidos si se puede evitar."""
    ultimo = (de_hoy[-1].get("score") or {}).get("subtema") if de_hoy else None
    pendientes, salida = list(elegidos), []
    while pendientes:
        # Una urgente no espera a que cambie el subtema: sale primero.
        k = next((i for i, c in enumerate(pendientes) if c["score"].get("urgente")), None)
        if k is None:
            k = next((i for i, c in enumerate(pendientes) if c["score"]["subtema"] != ultimo), 0)
        c = pendientes.pop(k)
        salida.append(c)
        ultimo = c["score"]["subtema"]
    return salida
