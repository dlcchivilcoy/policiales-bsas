# -*- coding: utf-8 -*-
"""LA AGENDA DE NACIONALES: qué sale en cada corrida (pedido del editor del 20/10/2026).

Las nacionales tienen sus corridas propias (no van en las pasadas de policiales). TODO sale como REEL con
el video original de la nota: sin video, la nota no sale (ni como carrusel).

    días              corridas            qué sale en cada corrida
    lunes a viernes   18 · 21             2 generales, 1 viral, 1 mundo
    sábado/domingo    10 · 14 · 18 · 21   6 de: viral, mundo, IA, general, deporte, cine/serie,
                                          espectáculo — 1 de cada una, las 6 más virales

«Mundo» = internacionales virales con video de algo policial o de violencia/conflicto (es_mundo).

(Historia: el 19/10 a la mañana, 10 · 18 · 21 con todo junto; a la tarde, 11 · 12 · 16 · 18 · 21; a la
noche, solo 18 y 21 con 2 por categoría y 1 reel + 1 carrusel. El 20/10, esta agenda.)

Ritmo: un posteo cada 30 minutos, también el finde. El primero a los 15 minutos del horario. Las corridas
van de a una (grupo de concurrencia): si la anterior todavía publica, la que sigue arranca cuando termina
y corre sus turnos desde ese momento (nunca dos posteos de nacionales a la misma hora).

Los policiales siguen con sus pasadas (reels/turnos.py).
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

TZ_AR = timezone(timedelta(hours=-3))
CORRIDAS_SEMANA = ((18, 0), (21, 0))
CORRIDAS_FINDE = ((10, 0), (14, 0), (18, 0), (21, 0))
CORRIDAS = CORRIDAS_SEMANA                     # (compatibilidad: las de todos los días)
DEMORA_PRIMERO = 15
MINUTOS_SEMANA = 30
MINUTOS_FINDE = 30
FIN_DE_SEMANA = (5, 6)                 # sábado, domingo
GENERALES = ""                         # la «categoría» de las nacionales generales

# Lunes a viernes, en cada corrida: {categoría: cuántas}.
SEMANA = {GENERALES: 2, "virales": 1, "internacionales": 1}
# Sábado y domingo: 1 de cada categoría, y en total las POR_CORRIDA_FINDE más virales.
FINDE = {"virales": 1, "internacionales": 1, "tecnologia_ia": 1, GENERALES: 1, "deportes": 1,
         "cine_series": 1, "espectaculos": 1}
POR_CORRIDA_FINDE = 6
# Todo sale SOLO como reel con el video de la nota (NAC_TODO_REEL=0 vuelve a dejar el carrusel en
# generales, IA, espectáculos, cine y deportes).
SOLO_REEL = {"virales", "internacionales"}     # estas, siempre (desde el 19/10/2026)


def solo_reel(cat: str) -> bool:
    """¿La categoría sale solo como reel con su video? Desde el 20/10/2026, todas."""
    if cat in SOLO_REEL:
        return True
    return (os.environ.get("NAC_TODO_REEL") or "1").strip() != "0" and cat in (set(FINDE) | set(SEMANA))

# MUNDO: internacionales con algo policial o de violencia / conflicto (pedido del 20/10/2026).
_MUNDO = re.compile(
    r"\b(polic[ií]a\w*|crimen\w*|criminal\w*|asesin\w*|homicid\w*|femicid\w*|masacre\w*|matanza\w*|"
    r"dispar\w*|tirote\w*|balacer\w*|balead\w*|armad[oa]s?|arma de fuego|ataque\w*|atac[oóa]\w*|"
    r"bomb\w*|explosi\w*|explot\w*|guerra\w*|conflicto\w*|enfrentamiento\w*|choques? con|militar\w*|"
    r"ej[eé]rcito\w*|misil\w*|drones?|invasi\w*|violen\w*|protesta\w*|disturbio\w*|manifestant\w*|"
    r"represi\w*|saque\w*|toque de queda|detenid\w*|deten\w*|arrest\w*|captur\w*|secuestr\w*|rob[oó]\w*|"
    r"asalt\w*|narco\w*|c[aá]rtel\w*|pandill\w*|terroris\w*|reh[eé]n\w*|golpe de estado|apu[nñ]al\w*|"
    r"agresi\w*|agred\w*|golpiz\w*|pelea\w*|mot[ií]n\w*|vandal\w*|incendi\w* intencional|fuga de presos|"
    r"tiroteo|persecuci\w*|operativo\w*|redada\w*|fusil\w*|francotirador\w*|linchamiento\w*)\b", re.I)


def es_mundo(c: dict) -> bool:
    """¿Una nota internacional entra en «mundo»? Algo policial o de violencia/conflicto en el título, la
    bajada o el arranque del cuerpo."""
    texto = " ".join(str(c.get(k) or "") for k in ("titulo", "bajada", "descripcion"))
    texto += " " + str(c.get("cuerpo") or "")[:500]
    return bool(_MUNDO.search(texto))


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.environ.get(nombre) or defecto))
    except ValueError:
        return defecto


def es_finde(cuando: datetime) -> bool:
    return cuando.weekday() in FIN_DE_SEMANA


def corridas_del_dia(cuando: datetime) -> tuple:
    return CORRIDAS_FINDE if es_finde(cuando) else CORRIDAS_SEMANA


def _candidatas(ahora: datetime, dias) -> list:
    out = []
    for d in dias:
        dia = ahora + timedelta(days=d)
        out += [dia.replace(hour=h, minute=m, second=0, microsecond=0) for h, m in corridas_del_dia(dia)]
    return out


def corrida(ahora: datetime) -> datetime:
    """El horario de la corrida a la que pertenece `ahora`: la última que ya empezó (con 10 minutos de
    margen por si cron-job.org dispara antes). Un día hábil antes de las 18, la de las 21 del día anterior."""
    return max(c for c in _candidatas(ahora, (-1, 0)) if c <= ahora + timedelta(minutes=10))


def siguiente(inicio: datetime) -> datetime:
    return min(c for c in _candidatas(inicio, (0, 1)) if c > inicio)


def topes(inicio: datetime) -> dict:
    """{categoría: cuántas en esta corrida} (NAC_AGENDA_<CAT> cambia las de lunes a viernes)."""
    if (inicio.hour, inicio.minute) not in corridas_del_dia(inicio):
        return {}
    if es_finde(inicio):
        return dict(FINDE)
    salida = {}
    for cat, defecto in SEMANA.items():
        n = _entero(f"NAC_AGENDA_{(cat or 'GENERALES').upper()}", defecto)
        if n:
            salida[cat] = n
    return salida


def maximo(inicio: datetime):
    """Cuántos posteos como mucho en la corrida (el finde, las 6 más virales); None = la suma de los topes."""
    return _entero("NAC_POR_CORRIDA_FINDE", POR_CORRIDA_FINDE) if es_finde(inicio) else None


def tope_del_dia(cat: str, cuando: datetime) -> int:
    """Lo más que puede salir de `cat` en el día."""
    dia = cuando.replace(hour=0, minute=0)
    return sum(topes(dia.replace(hour=h, minute=m)).get(cat, 0) for h, m in corridas_del_dia(cuando))


def minutos(inicio: datetime) -> int:
    """Cada cuánto sale un posteo: 30 minutos (también el finde, desde el 20/10/2026)."""
    if es_finde(inicio):
        return _entero("NAC_MINUTOS_FINDE", MINUTOS_FINDE) or MINUTOS_FINDE
    return _entero("NAC_MINUTOS", MINUTOS_SEMANA) or MINUTOS_SEMANA


def turnos(inicio: datetime, cuantos: int, holgura: int = 0, ahora: datetime = None) -> list:
    """Los horarios de los posteos de la corrida: `cuantos` con su espaciado y `holgura` turnos más, por si
    alguno queda vacío. El primero a los 15 minutos del horario o, si la corrida arrancó tarde (esperó a la
    anterior), 5 minutos después de arrancar."""
    paso = minutos(inicio)
    t0 = inicio + timedelta(minutes=DEMORA_PRIMERO)
    if ahora is not None and ahora + timedelta(minutes=5) > t0:
        t0 = (ahora + timedelta(minutes=5)).replace(second=0, microsecond=0)
    return [t0 + timedelta(minutes=paso * k) for k in range(max(0, cuantos + holgura))]


def corrida_id(inicio: datetime) -> str:
    """El id de la corrida para la fila de turnos (reels/turnos.py): «2026-10-19T10:00»."""
    return inicio.strftime("%Y-%m-%dT%H:%M")
