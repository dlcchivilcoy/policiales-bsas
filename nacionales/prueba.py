# -*- coding: utf-8 -*-
"""LAS CORRIDAS PROPIAS DE REELS DE PRUEBA EN INSTAGRAM (14/11/2026, pedido del editor).

«¿Qué medios scrappeás para los reels virales y policiales de prueba? No están saliendo 5 y 5 por día: hacé
2 corridas, una a las 18 para reels virales y una a las 20 para reels de prueba policiales.»

Hasta acá la fila de prueba vivía de lo que SOBRABA de otras corridas: las virales con Short de la de las 4
(entre 1 y 4 por día con el video de la nota) y los policiales con video de la de las 18:30, que casi nunca hay
porque los medios locales suben fotos. Ahora cada grupo tiene su corrida, que busca en ese momento:

- VIRALES (la dispara cron-job.org a las 17:35): los portales de variedad de siempre (Infobae, La Nación,
  Clarín, TN, Ámbito, El Cronista… con los virales que marca Gemini, nacionales/categorias.py). Primero la
  categoría virales y, si no alcanza, Mundo sin violencia. Turnos 18:00, 18:25, 18:50, 19:15 y 19:40.
- POLICIALES (cron-job.org a las 19:45): las secciones de policiales de los portales nacionales que SÍ suben
  video (TN, Infobae, Clarín y La Nación, FUENTES_POLICIALES), con prioridad a los hechos de la zona de
  Chivilcoy y después a los de la provincia de Buenos Aires. Turnos 20:00, 20:25, 20:50, 21:15 y 21:40.

Cada pieza: solo si la nota (o la misma noticia en otro portal) trae VIDEO y el video pasa el control de que
es de esa nota (reels/control_video.py, adentro de pasada.armar). La IA se gasta solo en las que tienen video.
Se publica como REEL DE PRUEBA (sin link, sin colab), de a una por turno; la corrida espera entre turnos. Si
arranca tarde, los turnos se corren (10 minutos como mínimo entre uno y otro) sin pasarse del fin de la franja.
Lo publicado queda en la memoria de nacionales (estado/nacionales.json), con «prueba»: el grupo; así no se
repite ni en estas corridas ni en las de nacionales.

`python -m nacionales.prueba --grupo virales|policiales [--publicar]`. NAC_PRUEBA_CUANTOS (5),
NAC_PRUEBA_PASO_MIN (25), NAC_PRUEBA_VIRALES_HORA (18:00), NAC_PRUEBA_POLICIALES_HORA (20:00).
"""
from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

from nacionales import agenda as AG
from nacionales import categorias as CAT
from nacionales import filtro as F
from nacionales import pasada as PA
from nacionales import portales as PO
from reels import publicador as PUB

TZ_AR = PA.TZ_AR
GRUPOS = {
    # grupo: (variable del primer turno, primer turno de fábrica, fin de la franja)
    "virales": ("NAC_PRUEBA_VIRALES_HORA", "18:00", "19:55"),
    "policiales": ("NAC_PRUEBA_POLICIALES_HORA", "20:00", "21:55"),
}
CUANTOS_DEFAULT = 5
PASO_MIN_DEFAULT = 25
PASO_MIN_TARDE = 10           # si la corrida arrancó tarde, lo mínimo entre dos reels
INTENTOS_MAX = 40             # notas que se miran como mucho (cada una lee su página; la IA, solo con video)
HORAS_POLICIALES = 18         # qué tan nuevo tiene que ser un policial

FUENTES_POLICIALES = (
    ("policiales", "TN", "rss", PO.TN.format("policiales"), {}),
    ("policiales", "Infobae", "rss", PO.INFOBAE("sociedad/policiales"), {}),
    ("policiales", "Clarín", "rss", PO.CLARIN.format("policiales"), {}),
    ("policiales", "La Nación", "rss", PO.LANACION("seguridad"), {}),
)
# A igual noticia, de qué portal se toma la nota: el que más seguido trae su propio video.
ORDEN_VIDEO = {"TN": 4, "Infobae": 3, "Clarín": 2, "La Nación": 1}


def _zona_cerca():
    from scraper.localidades import NOMBRES
    return F.rx(sorted(NOMBRES))


PROVINCIA = F.rx(["provincia de buenos aires", "bonaerense", "bonaerenses", "conurbano", "gran buenos aires",
                  "la plata", "mar del plata", "bahia blanca", "quilmes", "lomas de zamora", "la matanza",
                  "moreno", "merlo", "moron", "tigre", "pilar", "san isidro", "lanus", "avellaneda",
                  "florencio varela", "berazategui", "almirante brown", "esteban echeverria", "ezeiza",
                  "jose c. paz", "malvinas argentinas", "san martin", "tres de febrero", "hurlingham",
                  "ituzaingo", "escobar", "zarate", "campana", "olavarria", "tandil", "azul", "pergamino",
                  "san nicolas", "necochea", "san miguel", "vicente lopez", "san fernando", "berisso",
                  "ensenada", "general rodriguez", "marcos paz", "canuelas", "lobos", "navarro", "rosario"])


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int((os.environ.get(nombre) or "").strip() or defecto))
    except ValueError:
        return defecto


def cuantos() -> int:
    return _entero("NAC_PRUEBA_CUANTOS", CUANTOS_DEFAULT)


def paso_min() -> int:
    return max(PASO_MIN_TARDE, _entero("NAC_PRUEBA_PASO_MIN", PASO_MIN_DEFAULT))


def _a_las(dia, hhmm: str) -> datetime:
    return datetime.combine(dia, datetime.strptime(hhmm, "%H:%M").time(), TZ_AR)


def franja(grupo: str, dia) -> tuple:
    """(primer turno, fin de la franja) de ese día."""
    var, fabrica, fin = GRUPOS[grupo]
    hhmm = (os.environ.get(var) or "").strip() or fabrica
    try:
        primero = _a_las(dia, hhmm)
    except ValueError:
        primero = _a_las(dia, fabrica)
    return primero, max(_a_las(dia, fin), primero + timedelta(minutes=paso_min() * (cuantos() - 1) + 5))


def turnos(grupo: str, ahora: datetime, n: int) -> list:
    """Los `n` turnos que todavía entran en la franja: cada `paso_min()` desde el primero; los que ya pasaron
    se corren a partir de ahora, con PASO_MIN_TARDE entre uno y otro."""
    primero, fin = franja(grupo, ahora.date())
    salida, previo = [], None
    for k in range(n):
        t = primero + timedelta(minutes=paso_min() * k)
        if t < ahora:
            t = ahora
        if previo and t < previo + timedelta(minutes=PASO_MIN_TARDE):
            t = previo + timedelta(minutes=PASO_MIN_TARDE)
        if t > fin:
            break
        salida.append(t)
        previo = t
    return salida


# =============================================================================
# Las candidatas
# =============================================================================

def candidatas_virales(ahora: datetime, notas=None) -> tuple:
    """([candidatas, de más a menos impacto], avisos): los virales y, detrás, Mundo sin violencia."""
    avisos = []
    if notas is None:
        notas, fallas, _ = CAT.bajar()
        avisos += [f"portal {f}" for f in fallas]
    por_cat = CAT.candidatas(notas, ahora.timestamp())
    virales = [dict(c, categoria="virales") for c in por_cat.get("virales") or []]
    mundo = [dict(c, categoria="internacionales") for c in por_cat.get("internacionales") or []
             if not AG.es_mundo(c)]
    return virales + mundo, avisos


def puntaje_policial(nota: dict, cobertura: int, ahora_ts: float) -> tuple:
    """(puntos, razones) de un policial: cuántos portales lo cuentan, si es de la zona o de la provincia y qué
    tan nuevo es."""
    texto = F.norm(f"{nota.get('titulo') or ''} {nota.get('resumen') or ''} {(nota.get('cuerpo') or '')[:800]}")
    puntos, razones = 10 * cobertura, [f"{cobertura} portal(es)"]
    if _zona_cerca().search(texto):
        puntos += 30
        razones.append("de la zona")
    elif PROVINCIA.search(texto):
        puntos += 15
        razones.append("de la provincia")
    horas = max(0.0, (ahora_ts - (nota.get("fecha") or 0)) / 3600)
    puntos += max(0, 10 - round(horas))
    return puntos, razones


def candidatas_policiales(ahora: datetime, notas=None) -> tuple:
    """([candidatas, de más a menos puntos], avisos): una por hecho (el mismo hecho en TN y en Infobae es UNA,
    y más fuerte), tomada del portal que más seguido trae video."""
    avisos = []
    if notas is None:
        notas, fallas, _ = PO.bajar(FUENTES_POLICIALES)
        avisos += [f"policiales {f}" for f in fallas]
    ts = ahora.timestamp()
    recientes = [n for n in notas if n.get("titulo") and ts - (n.get("fecha") or 0) <= HORAS_POLICIALES * 3600]
    salida = []
    for grupo in F.agrupar(recientes):
        mejor = max(grupo, key=lambda x: (ORDEN_VIDEO.get(PO.fuente_de(x), 0), bool(x.get("imagen")),
                                          len(x.get("cuerpo") or ""), x.get("fecha") or 0))
        puntos, razones = puntaje_policial(mejor, len(grupo), ts)
        otras = [x for x in grupo if x is not mejor]
        salida.append(dict(mejor, categoria="policiales", puntos=puntos, impacto=puntos, impacto_razones=razones,
                           cobertura=len(grupo), fuentes=list(dict.fromkeys(PO.fuente_de(x) for x in grupo)),
                           tema=sorted(F.palabras_tema(mejor)), otras=[x["titulo"] for x in otras][:4],
                           otras_urls=[x["url"] for x in otras][:4]))
    salida.sort(key=lambda c: (-c["puntos"], -(c.get("fecha") or 0)))
    return salida, avisos


# =============================================================================
# La corrida
# =============================================================================

def _tiene_video(c: dict, leer) -> bool:
    for u in [c["url"]] + list(c.get("otras_urls") or [])[:2]:
        try:
            if (leer(u) or {}).get("video"):
                return True
        except Exception:                            # noqa: BLE001 — una página que no anda no frena
            continue
    return False


def hechos_hoy(mem: dict, grupo: str, dia: str) -> int:
    return sum(1 for p in mem["piezas"].values()
               if p.get("prueba") == grupo and p.get("dia") == dia
               and (p.get("ig_prueba") or {}).get("estado") in ("ok", "sin_confirmar", "simulado"))


def publicar_prueba(pieza: dict, caption: str) -> dict:
    """Sube el video (y la portada) al Release y lo publica como reel de prueba."""
    marca = hashlib.sha1(pieza["url_original"].encode()).hexdigest()[:10]
    video = pieza.get("video") or {}
    subida = PA._resultado(PA.dejar_reel_prueba, Path(video["archivo"]), caption, marca, video.get("portada") or "")
    if subida.get("estado") != "ok":
        return subida
    res = PA._resultado(PA.publicar_reel_prueba_url, subida["video_url"], caption, subida.get("portada_url") or "")
    return dict(subida, **res)


def corrida(grupo: str, publicar: bool, notas=None, leer_pagina=None, redactar=None, ahora_fn=None,
            dormir=None, publicar_fn=None, guardia=None) -> dict:
    ahora_fn = ahora_fn or PA._ahora
    dormir = dormir or PA._dormir
    publicar_fn = publicar_fn or publicar_prueba
    ahora = ahora_fn()
    dia = ahora.date().isoformat()
    informe = {"modo": f"prueba_{grupo}", "cuando": ahora.isoformat(timespec="seconds"), "publicar": publicar,
               "piezas": [], "descartadas": [], "fallas": [], "avisos": []}
    mem = PA.cargar()
    faltan = cuantos() - hechos_hoy(mem, grupo, dia)
    plan = turnos(grupo, ahora, max(0, faltan))
    informe["turnos"] = [t.strftime("%H:%M") for t in plan]
    if not plan:
        informe["estado"] = "nada" if faltan <= 0 else "fuera_de_hora"
        return informe
    # Una sola corrida por día y grupo: la de cron-job.org o la de respaldo de GitHub, la primera que llega.
    if guardia is None and publicar and os.environ.get("GITHUB_ACTIONS") == "true":
        from reels import turnos as TURNOS
        guardia = TURNOS.Fila(f"prueba-{grupo}-{ahora:%Y%m%d}")
    if guardia is not None and not guardia.tomar(0, "nacionales", f"prueba_{grupo}"):
        informe["estado"] = "ya_corrio"
        return informe

    cands, avisos = (candidatas_virales if grupo == "virales" else candidatas_policiales)(ahora, notas)
    informe["avisos"] += avisos
    informe["candidatas"] = len(cands)
    cola = PA.elegir(cands, mem, len(cands), ahora)
    print(f"Reels de prueba de {grupo}: {len(cands)} candidatas, {len(cola)} nuevas; turnos "
          f"{', '.join(informe['turnos'])}", flush=True)
    paginas = {}

    def leer(url):
        if url not in paginas:
            paginas[url] = dict((leer_pagina or CAT.leer_pagina)(url) or {})
        return paginas[url]

    carpeta = PA.SALIDA / f"prueba_{grupo}_{ahora:%Y-%m-%d_%H%M}"
    contadas, intentos, ultimo = [], 0, None
    for turno in plan:
        pieza = c = None
        while cola and intentos < INTENTOS_MAX:
            c = cola.pop(0)
            intentos += 1
            if F.ya_contado(c, contadas):
                continue
            if not _tiene_video(c, leer):
                informe["descartadas"].append({"titulo": c["titulo"], "motivo": "sin video propio"})
                continue
            try:
                p = PA.armar(c, carpeta, redactar, leer)
            except Exception as e:                   # noqa: BLE001 — la IA o el video: se sigue con otra
                if PA.bloqueada_por_ia(e):
                    PA._descartar_bloqueada(c, mem, publicar, ahora, informe, e)
                else:
                    informe["fallas"].append(f"no se pudo armar «{c['titulo'][:60]}»: {type(e).__name__}: {e}"[:300])
                continue
            motivo = ("" if p["guion"].get("apta") and p.get("formato") == "reel" and p.get("video_original")
                      else (p["guion"].get("motivo") or (p.get("video_control") or {}).get("motivo")
                            or "sin el video de la nota"))
            if motivo:
                informe["descartadas"].append({"titulo": c["titulo"], "motivo": motivo})
                if publicar:
                    mem["descartadas"][c["url"]] = {"motivo": motivo, "cuando": ahora.isoformat(timespec="seconds")}
                continue
            pieza = p
            break
        if pieza is None:
            informe["avisos"].append(f"no hubo más notas con video: salieron {len(informe['piezas'])}")
            break
        # Esperar el turno (y nunca dos reels con menos de PASO_MIN_TARDE entre sí).
        objetivo = max(turno, ultimo + timedelta(minutes=PASO_MIN_TARDE)) if ultimo else turno
        espera = (objetivo - ahora_fn()).total_seconds()
        if espera > 0 and (publicar or dormir is not PA._dormir):     # simulando, no se espera de verdad
            print(f"  esperando {espera / 60:.1f} min al turno de las {objetivo:%H:%M}…", flush=True)
            dormir(espera)
        if publicar and ahora_fn() > franja(grupo, ahora.date())[1]:
            informe["avisos"].append("se terminó la franja")
            break
        caption = PA.caption_instagram(pieza["guion"])
        if not publicar:
            res = {"estado": "simulado", "texto": caption}
        elif (lugar := PA._lugar_ig()) and lugar[0] <= 0:
            informe["avisos"].append(f"la cuenta ya usó {lugar[1]} de sus {lugar[2]} posteos de 24 h")
            break
        else:
            res = publicar_fn(pieza, caption)
        res = dict(res, formato="reel de prueba", para=objetivo.strftime("%H:%M"),
                   cuando=res.get("cuando") or ahora_fn().isoformat(timespec="seconds"))
        registro = PA._registro(pieza, {"ig_prueba": res}, dia, objetivo.strftime("%H:%M"))
        registro["prueba"] = grupo
        informe["piezas"].append(registro)
        contadas.append({"titulo": pieza["guion"]["titular"], "tema": c.get("tema") or []})
        ultimo = ahora_fn()
        print(f"  [{grupo}] {registro['titular'][:70]}: {res.get('estado')} {res.get('id') or res.get('error') or ''}",
              flush=True)
        if publicar:
            mem["piezas"][c["url"]] = registro
            PA.guardar(mem)
            if res.get("estado") == "fallo" and PUB._es_tope_de_prueba(res.get("error")):
                informe["avisos"].append("Instagram no acepta más reels de prueba por hoy (tope de la API)")
                break
    if publicar:
        PA.guardar(mem)
    ok = sum(1 for p in informe["piezas"] if (p.get("ig_prueba") or {}).get("estado") in ("ok", "sin_confirmar",
                                                                                          "simulado"))
    informe["estado"] = "ok" if ok else "sin_piezas"
    return informe


def resumen(inf: dict) -> str:
    renglones = [f"## Reels de prueba — {inf['modo'].replace('prueba_', '')} ({inf['cuando'][:16]})", "",
                 f"- Estado: {inf.get('estado')}", f"- Turnos: {', '.join(inf.get('turnos') or []) or '—'}",
                 f"- Candidatas: {inf.get('candidatas', '—')}"]
    for p in inf["piezas"]:
        r = p.get("ig_prueba") or {}
        renglones.append(f"- {r.get('para')} · {p.get('titular')} · {r.get('estado')} {r.get('id') or r.get('error') or ''}")
    if inf["descartadas"]:
        renglones += ["", f"Descartadas: {len(inf['descartadas'])}"]
        renglones += [f"- {d['titulo'][:80]}: {d['motivo'][:100]}" for d in inf["descartadas"][:15]]
    for t in ("avisos", "fallas"):
        if inf.get(t):
            renglones += ["", t.capitalize() + ":"] + [f"- {x}" for x in inf[t]]
    return "\n".join(renglones)


def main():
    ap = argparse.ArgumentParser(description="Corrida propia de reels de prueba en Instagram")
    ap.add_argument("--grupo", choices=sorted(GRUPOS), required=True)
    ap.add_argument("--publicar", action="store_true")
    a = ap.parse_args()
    import entorno
    entorno.cargar()
    entorno.consola_utf8()
    inf = corrida(a.grupo, a.publicar)
    print(resumen(inf))


if __name__ == "__main__":
    main()
