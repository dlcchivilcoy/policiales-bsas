# -*- coding: utf-8 -*-
"""LA AGENDA DE NACIONALES: qué sale en cada corrida (pedidos del editor del 19/10/2026).

Las nacionales tienen sus corridas propias (no van en las pasadas de policiales), con 2 posteos de cada
categoría, intercalados en categoría y en formato (1 reel y 1 carrusel cuando la categoría admite los dos):

    categoría                      días            corridas
    virales (solo con su video)    todos           18 · 21
    internacionales (solo video)   todos           18 · 21
    generales (política, economía) todos           18 · 21
    IA, espectáculos, cine y series sábado/domingo 18
    deportes                       sábado/domingo  21

(Historia del 19/10: a la mañana, 10 · 18 · 21 con todo junto; a la tarde, 11 · 12 · 16 · 18 · 21; a la
noche, tras un día con el cupo de Instagram lleno, el editor dejó solo 18 y 21.)

Ritmo: un posteo cada 30 minutos; los sábados y domingos, cada 15. El primero a los 15 minutos del horario.
Las corridas van de a una (grupo de concurrencia): si la anterior todavía publica, la que sigue arranca
cuando termina y corre sus turnos desde ese momento (nunca dos posteos de nacionales a la misma hora).

Los policiales siguen con sus pasadas (reels/turnos.py).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

TZ_AR = timezone(timedelta(hours=-3))
CORRIDAS = ((18, 0), (21, 0))
POR_CATEGORIA = 2
DEMORA_PRIMERO = 15
MINUTOS_SEMANA = 30
MINUTOS_FINDE = 15
FIN_DE_SEMANA = (5, 6)                 # sábado, domingo
GENERALES = ""                         # la «categoría» de las nacionales generales

# categoría → (solo el finde, corridas en las que entra)
AGENDA = {
    "virales": (False, (18, 21)),
    "internacionales": (False, (18, 21)),
    GENERALES: (False, (18, 21)),
    "tecnologia_ia": (True, (18,)),
    "espectaculos": (True, (18,)),
    "cine_series": (True, (18,)),
    "deportes": (True, (21,)),
}
# Solo como REEL con el video de la nota: sin video, no salen (ni como carrusel).
SOLO_REEL = {"virales", "internacionales"}


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.environ.get(nombre) or defecto))
    except ValueError:
        return defecto


def es_finde(cuando: datetime) -> bool:
    return cuando.weekday() in FIN_DE_SEMANA


def corrida(ahora: datetime) -> datetime:
    """El horario de la corrida a la que pertenece `ahora`: la última de CORRIDAS que ya empezó (con 10
    minutos de margen por si cron-job.org dispara antes). Antes de las 18, la de las 21 del día anterior."""
    candidatos = [ahora.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=d)
                  for d in (-1, 0) for h, m in CORRIDAS]
    return max(c for c in candidatos if c <= ahora + timedelta(minutes=10))


def siguiente(inicio: datetime) -> datetime:
    candidatos = [inicio.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=d)
                  for d in (0, 1) for h, m in CORRIDAS]
    return min(c for c in candidatos if c > inicio)


def topes(inicio: datetime) -> dict:
    """{categoría: cuántas en esta corrida} (2 cada una; NAC_AGENDA_<CAT> lo cambia)."""
    salida = {}
    for cat, (finde, horas) in AGENDA.items():
        if inicio.hour not in horas or (finde and not es_finde(inicio)):
            continue
        n = _entero(f"NAC_AGENDA_{(cat or 'GENERALES').upper()}", POR_CATEGORIA)
        if n:
            salida[cat] = n
    return salida


def tope_del_dia(cat: str, cuando: datetime) -> int:
    """Lo más que puede salir de `cat` en el día: 2 por cada corrida en la que entra."""
    finde, horas = AGENDA.get(cat, (False, ()))
    if finde and not es_finde(cuando):
        return 0
    return _entero(f"NAC_AGENDA_{(cat or 'GENERALES').upper()}", POR_CATEGORIA) * len(horas)


def minutos(inicio: datetime) -> int:
    """Cada cuánto sale un posteo: 30 minutos; los sábados y domingos, 15."""
    if es_finde(inicio):
        return _entero("NAC_MINUTOS_FINDE", MINUTOS_FINDE) or MINUTOS_FINDE
    return _entero("NAC_MINUTOS", MINUTOS_SEMANA) or MINUTOS_SEMANA


def turnos(inicio: datetime, cuantos: int, holgura: int = 0, ahora: datetime = None) -> list:
    """Los horarios de los posteos de la corrida: `cuantos` con su espaciado y `holgura` turnos más, por si
    alguno queda vacío (dos de la misma categoría nunca van seguidas: la segunda espera un turno). El primero
    a los 15 minutos del horario o, si la corrida arrancó tarde (esperó a la anterior), 5 minutos después de
    arrancar."""
    paso = minutos(inicio)
    t0 = inicio + timedelta(minutes=DEMORA_PRIMERO)
    if ahora is not None and ahora + timedelta(minutes=5) > t0:
        t0 = (ahora + timedelta(minutes=5)).replace(second=0, microsecond=0)
    return [t0 + timedelta(minutes=paso * k) for k in range(max(0, cuantos + holgura))]


def corrida_id(inicio: datetime) -> str:
    """El id de la corrida para la fila de turnos (reels/turnos.py): «2026-10-19T10:00»."""
    return inicio.strftime("%Y-%m-%dT%H:%M")
