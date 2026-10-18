# -*- coding: utf-8 -*-
"""Puntaje de IMPACTO de 0 a 100 (pedido del editor del 18/10/2026): qué tema tiene más impacto viral,
interacción y búsquedas, con la importancia de cada portal según el ORDEN del PDF.

Se calcula por TEMA (las notas de todos los portales sobre lo mismo, nacionales/filtro.agrupar):

  Jerarquía de la fuente (orden del PDF)      0-20   la mejor fuente del tema en esa categoría
  Cobertura en varios portales                0-20   cuántos medios distintos lo cubren (los nuestros
                                                     y los que junta Google News)
  Lectores («más leídas» de los portales)     0-20   en qué puesto está en Cronista, La Nación,
                                                     Ámbito y Clarín
  Búsquedas en Google (SEO)                   0-15   si coincide con una búsqueda en tendencia en la
                                                     Argentina, según su volumen
  Agenda de Google News                       0-10   en qué puesto lo pone Google News
  Interacción en YouTube                      0-10   video en tendencia sobre el tema: vistas, me gusta
                                                     y comentarios
  Actualidad                                  0-5    recién publicado = 5; baja hasta el fin de la ventana
  Interés editorial                           0-10   lo de siempre: protagonista argentino, Chivilcoy,
                                                     estreno con fecha…

Los filtros obligatorios van ANTES y un puntaje alto nunca los salta (PDF, apartado 15): vigencia,
«en vivo», galerías, deporte sin argentinos, el viral sin su video, lo ya publicado.
Cada componente guarda su razón («3.º más leída de Ámbito», «búsqueda en tendencia: "racing" 20.000+»).
"""
import math
import os
import re

from nacionales import filtro as F
from nacionales import portales as PO

PUNTAJE_COBERTURA = {1: 0, 2: 8, 3: 12, 4: 15, 5: 17, 6: 19}


def minimo() -> int:
    try:
        return int(os.environ.get("NAC_IMPACTO_MINIMO") or 15)
    except ValueError:
        return 15


def palabras(texto: str) -> set:
    """Las palabras con contenido, sin tildes ni mayúsculas, en singular."""
    salida = set()
    for w in re.findall(r"[a-z0-9]+", F.norm(texto or "")):
        if (len(w) < 4 and not w.isdigit()) or w in F._VACIAS or w in F._GENERICOS or re.fullmatch(r"(19|20)\d\d", w):
            continue
        salida.add(F._raiz(w))
    return salida


def se_parecen(a: set, b: set, minimo_comun: int = 3, proporcion: float = 0.5) -> bool:
    comun = len(a & b)
    return bool(a and b) and comun >= minimo_comun and comun >= proporcion * min(len(a), len(b))


def _nombre(medio: str) -> str:
    return re.sub(r"[^a-z0-9]", "", F.norm(medio))


def puntos_fuente(fuente: str, cat: str) -> float:
    """20 la primera del orden del PDF, 6 la última; 4 una fuente fuera del orden."""
    orden = PO.ranking(cat)
    if fuente not in orden:
        return 4.0
    if len(orden) == 1:
        return 20.0
    return round(20 - orden.index(fuente) * 14 / (len(orden) - 1), 1)


def evaluar(grupo: list, cat: str, senales: dict, ahora: float, ventana_h: float = 24, base: int = 0,
            principal: str = "") -> dict:
    """{impacto, senal, desglose, razones} de un TEMA. `senal` es lo que dice la gente (sin la jerarquía
    de la fuente ni el interés editorial): con eso se comparan temas de categorías distintas."""
    fuentes = []
    for n in grupo:
        f = PO.fuente_de(n)
        if f not in fuentes:
            fuentes.append(f)
    titulos = [palabras(n.get("titulo")) for n in grupo]
    urls = {n.get("url") for n in grupo}
    razones, d = [], {}

    # Jerarquía (orden del PDF): la de la nota que se cuenta (`principal`) o la mejor del tema.
    mejor = principal or (max(fuentes, key=lambda f: puntos_fuente(f, cat)) if fuentes else "")
    d["fuente"] = puntos_fuente(mejor, cat) if mejor else 0
    orden = PO.ranking(cat)
    if mejor in orden:
        razones.append(f"fuente: {mejor} ({orden.index(mejor) + 1}.º de {len(orden)} en el orden del PDF)")

    # Agenda de Google News (y los medios que Google junta en el tema)
    medios = {_nombre(f) for f in fuentes}
    d["agenda"] = 0
    for it in senales.get("google_news") or []:
        if any(se_parecen(t, palabras(g)) for t in titulos for g in it["titulos"]):
            medios |= {_nombre(m) for m in it["medios"]}
            p = round(10 * (1 - (it["puesto"] - 1) / max(1, it["de"])), 1)
            if p > d["agenda"]:
                d["agenda"] = p
                razones.append(f"Google News: {it['puesto']}.º de {it['de']} en «{it['seccion']}»")
    # Cobertura
    n_medios = len(medios - {""})
    d["cobertura"] = PUNTAJE_COBERTURA.get(n_medios, 20)
    if n_medios > 1:
        razones.append(f"cobertura: {n_medios} medios ({', '.join(fuentes[:6])})")

    # Lectores
    d["lectores"] = 0
    for x in senales.get("mas_leidas") or []:
        if x["url"] in urls or any(se_parecen(t, palabras(x["texto"])) for t in titulos):
            d["lectores"] += 11 - min(10, x["puesto"])
            razones.append(f"{x['puesto']}.º más leída de {x['medio']}")
    d["lectores"] = min(20, d["lectores"])

    # Búsquedas en Google (SEO). La búsqueda de DOS o más palabras tiene que estar entera en un título
    # («manchester united»); una sola palabra («serie a», «epicentro») es demasiado suelta: cuenta solo
    # si coincide con los titulares que Google asocia a esa búsqueda.
    d["busquedas"] = 0
    for t in senales.get("tendencias") or []:
        q = palabras(t["consulta"])
        por_consulta = len(q) >= 2 and any(q <= a for a in titulos)
        por_titulos = any(se_parecen(a, palabras(g)) for a in titulos for g in t.get("titulos") or [])
        if por_consulta or por_titulos:
            p = round(min(15, max(2, 3 * math.log10(max(10, t["trafico"])) - 3)), 1)
            if p > d["busquedas"]:
                d["busquedas"] = p
                razones.append(f"búsqueda en tendencia en Google: «{t['consulta']}» ({t['trafico']:,}+)".replace(",", "."))

    # Interacción en YouTube
    d["youtube"] = 0
    for v in senales.get("youtube") or []:
        if any(se_parecen(t, palabras(v["titulo"]), 2) for t in titulos):
            interaccion = (v["me_gusta"] + 3 * v["comentarios"]) / max(1, v["vistas"])
            p = round(min(10, max(1, 2 * math.log10(max(1, v["vistas"])) - 4 + min(2, 40 * interaccion))), 1)
            if p > d["youtube"]:
                d["youtube"] = p
                razones.append(f"YouTube en tendencia: «{v['titulo'][:50]}» ({v['vistas']:,} vistas, "
                               f"{v['me_gusta']:,} me gusta, {v['comentarios']:,} comentarios)".replace(",", "."))

    # Actualidad
    fecha = max((n.get("fecha") or 0) for n in grupo) if grupo else 0
    edad = (ahora - fecha) / 3600 if fecha else ventana_h
    d["actualidad"] = 5.0 if edad <= 3 else round(max(0.0, 5 * (1 - (edad - 3) / max(1, ventana_h - 3))), 1)

    d["editorial"] = max(0, min(10, base - 35)) if base else 0
    senal = sum(d[k] for k in ("cobertura", "lectores", "busquedas", "agenda", "youtube", "actualidad"))
    return {"impacto": int(round(min(100, senal + d["fuente"] + d["editorial"]))), "senal": round(senal, 1),
            "desglose": d, "razones": razones[:8]}


def realzar_generales(cands: list, otras: list, senales: dict, ahora: float, tope: int = 35) -> list:
    """Nacionales generales: Infobae arma las piezas; Ámbito, El Cronista, La Nación y Clarín (y las
    señales) suben a los temas que más se leen, se buscan y se cubren. Suma hasta `tope` puntos."""
    if not cands:
        return cands
    grupos = F.agrupar([dict(c, _cand=i) for i, c in enumerate(cands)] + list(otras))
    salida = list(cands)
    for g in grupos:
        for x in g:
            if "_cand" not in x:
                continue
            ev = evaluar(g, "nacionales", senales, ahora, ventana_h=F.HORAS_VENTANA)
            extra = min(tope, round(0.5 * (ev["senal"] - ev["desglose"]["actualidad"])))
            c = cands[x["_cand"]]
            salida[x["_cand"]] = dict(c, puntos=(c.get("puntos") or 0) + extra, impacto=ev["impacto"],
                                      impacto_razones=ev["razones"], impacto_extra=extra)
    return sorted(salida, key=lambda c: (-(c.get("puntos") or 0), -(c.get("fecha") or 0)))
