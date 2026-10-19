# -*- coding: utf-8 -*-
"""LA AGENDA DE NACIONALES: qué sale en cada corrida (pedido del editor, 19/10/2026).

Las nacionales dejan de ir en las pasadas de policiales (09:05 a 23:35) y tienen sus TRES corridas propias,
a las 10, a las 18 y a las 21 (hora argentina), con 2 posteos de cada categoría, intercalados:

    categoría                      días            corridas
    virales (solo con su video)    todos           10 · 18 · 21
    internacionales (solo video)   todos           10 · 18 · 21
    generales (política, economía) todos           18 · 21
    deportes, espectáculos, IA     sábado/domingo  10 · 18 · 21
    cine y series                  sábado/domingo  18 · 21

Ritmo: un posteo cada 30 minutos; los sábados y domingos, cada 15 (las corridas juntan más categorías). Si
igual no entran antes de la corrida siguiente, el espaciado se achica lo justo (nunca menos de
MINUTOS_MINIMO). El primer posteo sale a los 15 minutos del horario (tiempo para leer los portales).

Los policiales siguen con sus pasadas de siempre (reels/turnos.py).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

TZ_AR = timezone(timedelta(hours=-3))
CORRIDAS = ((10, 0), (18, 0), (21, 0))
POR_CATEGORIA = 2
DEMORA_PRIMERO = 15
MINUTOS_SEMANA = 30
MINUTOS_FINDE = 15
MINUTOS_MINIMO = 10
FIN_DE_SEMANA = (5, 6)                 # sábado, domingo
GENERALES = ""                         # la «categoría» de las nacionales generales

# categoría → (solo el finde, corridas en las que entra)
AGENDA = {
    "virales": (False, (10, 18, 21)),
    "internacionales": (False, (10, 18, 21)),
    GENERALES: (False, (18, 21)),
    "deportes": (True, (10, 18, 21)),
    "espectaculos": (True, (10, 18, 21)),
    "tecnologia_ia": (True, (10, 18, 21)),
    "cine_series": (True, (18, 21)),
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
    minutos de margen por si cron-job.org dispara antes). Antes de las 10, la de las 21 del día anterior."""
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


def minutos(inicio: datetime, cuantos: int) -> int:
    """Cada cuánto sale un posteo: 30 (15 el finde), achicado si no entran antes de la corrida siguiente."""
    base = _entero("NAC_MINUTOS_FINDE", MINUTOS_FINDE) if es_finde(inicio) else _entero("NAC_MINUTOS", MINUTOS_SEMANA)
    if cuantos <= 1:
        return base
    ventana = (siguiente(inicio) - inicio).total_seconds() / 60 - DEMORA_PRIMERO
    if inicio.hour == CORRIDAS[-1][0]:
        return base                     # la última del día no tiene a nadie atrás
    return max(MINUTOS_MINIMO, min(base, int(ventana // (cuantos - 1))))   # el último, antes de la siguiente


def turnos(inicio: datetime, cuantos: int, holgura: int = 0) -> list:
    """Los horarios de los posteos de la corrida: `cuantos` con su espaciado y `holgura` turnos más, por si
    alguno queda vacío (dos de la misma categoría nunca van seguidas: la segunda espera un turno). Ninguno
    después del arranque de la corrida siguiente."""
    paso = minutos(inicio, cuantos)
    t0 = inicio + timedelta(minutes=DEMORA_PRIMERO)
    limite = siguiente(inicio) if inicio.hour != CORRIDAS[-1][0] else inicio + timedelta(hours=12)
    return [t for t in (t0 + timedelta(minutes=paso * k) for k in range(max(0, cuantos + holgura))) if t < limite]


def corrida_id(inicio: datetime) -> str:
    """El id de la corrida para la fila de turnos (reels/turnos.py): «2026-10-19T10:00»."""
    return inicio.strftime("%Y-%m-%dT%H:%M")
