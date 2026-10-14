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
"""
import os

MEZCLA_DEFECTO = {"agro": 30, "mercados": 20, "agtech": 20, "maquinaria": 10, "ganaderia": 10, "empresas": 10}
REFUERZO = 10
MAX_MISMO_TEMA = 2          # por día: el mismo cultivo, empresa o tema


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int((os.environ.get(nombre) or "").strip()))
    except ValueError:
        return defecto


def score_min() -> int:
    return _entero("AGRO_SCORE_MIN", 75)


def max_dia() -> int:
    return _entero("AGRO_MAX_DIA", 3)


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
    return {k: max(1, round(cupo_dia * v / total)) for k, v in m.items()}


def elegir(candidatos: list, de_hoy: list, cupo_dia: int = None, minimo: int = None) -> tuple:
    """(elegidos, descartados_con_motivo). `candidatos`: [{"id", "score": {...}}, …] (un
    representante por grupo). `de_hoy`: lo ya elegido hoy (cuenta para cupo, mezcla y temas)."""
    cupo_dia = max_dia() if cupo_dia is None else cupo_dia
    minimo = score_min() if minimo is None else minimo
    tope = topes(cupo_dia)
    usados = {}
    temas = {}
    for p in de_hoy:
        s = p.get("score") or {}
        usados[s.get("subtema")] = usados.get(s.get("subtema"), 0) + 1
        if s.get("tema"):
            temas[s["tema"]] = temas.get(s["tema"], 0) + 1
    lugar = cupo_dia - len(de_hoy)
    orden = sorted(candidatos, key=lambda c: (c["score"]["ai_score"], c["score"]["commercial_score"]),
                   reverse=True)
    elegidos, descartados, reserva = [], [], []
    for c in orden:
        s = c["score"]
        if s["ai_score"] < minimo:
            descartados.append((c, f"score {s['ai_score']} < {minimo}"))
            continue
        if s.get("tema") and temas.get(s["tema"], 0) >= MAX_MISMO_TEMA:
            descartados.append((c, f"ya hay {MAX_MISMO_TEMA} del tema «{s['tema']}» hoy"))
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
        if s.get("tema"):
            temas[s["tema"]] = temas.get(s["tema"], 0) + 1
    for c in reserva:
        s = c["score"]
        if lugar > 0 and s["ai_score"] >= minimo + REFUERZO and temas.get(s.get("tema"), 0) < MAX_MISMO_TEMA:
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
        k = next((i for i, c in enumerate(pendientes) if c["score"]["subtema"] != ultimo), 0)
        c = pendientes.pop(k)
        salida.append(c)
        ultimo = c["score"]["subtema"]
    return salida
