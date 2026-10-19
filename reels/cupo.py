# -*- coding: utf-8 -*-
"""Cupo GLOBAL de reels policiales por pasada (pedido del editor, 17/10/2026, PDF «Prompt integral»).

Como mucho MAX_POLICE_REELS_PER_PASS (3) hechos distintos por pasada, sumando TODAS las redes: la
misma pieza en YouTube, web, Facebook, Instagram y el buzón de X/TikTok es un solo hecho. 0, 1 o 2
también están bien: nunca se completa la cuota.

La pasada es el HORARIO (PASADAS_AR, abajo), no la corrida: si la de las 12:05 se corta y la
corre el respaldo, o alguien la vuelve a lanzar a mano, sigue siendo la pasada de las 12:05 y
comparte los 3 lugares. Por eso las reservas quedan en estado/cupo_pasadas.json (se guarda con el
resto de estado/ y se combina por unión en tools/guardar_estado.py). Las corridas de policiales no
se superponen (grupo de concurrencia del workflow), así que leer-reservar-guardar no tiene carrera.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "estado" / "cupo_pasadas.json"
MAX_DEFAULT = 3
# Las pasadas de policiales, en hora argentina (cron-job.org, ver .github/workflows/reels.yml). Si
# cambian los horarios de cron-job.org, se cambian acá.
# 19/10/2026: el editor sacó la de las 09:05 (antes: (9, 5) primera).
PASADAS_AR = ((12, 5), (15, 5), (18, 5), (21, 5), (23, 35))
DIAS = 3                       # lo que se guarda: alcanza para auditar y no crece sin fin
TZ_AR = timezone(timedelta(hours=-3))
# Una corrida que arranca hasta 10 minutos ANTES de su horario es de ese horario.
TOLERANCIA_MIN = 10


def maximo() -> int:
    try:
        return max(0, int(os.environ.get("MAX_POLICE_REELS_PER_PASS") or MAX_DEFAULT))
    except ValueError:
        return MAX_DEFAULT


def pasada_id(pasadas_ar, ahora_ar: datetime = None) -> str:
    """El horario de la pasada a la que pertenece este momento: el último de `pasadas_ar`
    ((hora, minuto), hora argentina) que ya empezó. Antes de la primera del día, la última de ayer."""
    ahora = (ahora_ar or datetime.now(TZ_AR)).replace(tzinfo=None) + timedelta(minutes=TOLERANCIA_MIN)
    inicios = [ahora.replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(days=d)
               for d in (0, 1) for h, m in pasadas_ar]
    inicio = max(i for i in inicios if i <= ahora)
    return inicio.strftime("%Y-%m-%dT%H:%M")


def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads((ruta or ARCHIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pasadas": {}}


def guardar(datos: dict, ruta: Path = None):
    ruta = ruta or ARCHIVO
    limite = (datetime.now(TZ_AR) - timedelta(days=DIAS)).strftime("%Y-%m-%dT%H:%M")
    datos["pasadas"] = {k: v for k, v in (datos.get("pasadas") or {}).items() if k >= limite}
    datos["actualizado"] = datetime.now(TZ_AR).isoformat(timespec="seconds")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def reservadas(pid: str, datos: dict = None) -> list:
    datos = cargar() if datos is None else datos
    return [r["clave"] for r in ((datos.get("pasadas") or {}).get(pid) or {}).get("reservas") or []]


def libres(pid: str, datos: dict = None) -> int:
    return max(0, maximo() - len(reservadas(pid, datos)))


def reservar(pid: str, piezas: list, clave, ruta: Path = None) -> list:
    """Anota las piezas como reservadas en la pasada `pid` (las que ya estaban no cuentan dos veces)
    y devuelve TODAS las claves reservadas. Nunca pasa del máximo: lo que no entra no se anota."""
    datos = cargar(ruta)
    p = datos.setdefault("pasadas", {}).setdefault(pid, {"reservas": []})
    ya = {r["clave"] for r in p["reservas"]}
    for pieza in piezas:
        k = clave(pieza)
        if k in ya or len(p["reservas"]) >= maximo():
            continue
        geo = pieza.get("geo") or {}
        p["reservas"].append({
            "clave": k, "titular": (pieza.get("guion") or {}).get("titular"),
            "localidad": (geo.get("nombre") or pieza.get("localidad_hecho") or ""),
            "distancia_km": geo.get("distancia_km"), "precision": geo.get("precision"),
            "viral": pieza.get("viral"), "cuando": datetime.now(TZ_AR).isoformat(timespec="seconds")})
        ya.add(k)
    guardar(datos, ruta)
    return [r["clave"] for r in p["reservas"]]


def combinar(nuestro: dict, remoto: dict) -> dict:
    """Para tools/guardar_estado.py: unión de reservas por pasada (sin pasar del máximo)."""
    out = {"pasadas": {}}
    for pid in set((nuestro.get("pasadas") or {})) | set((remoto.get("pasadas") or {})):
        vistas, reservas = set(), []
        for fuente in (remoto, nuestro):
            for r in (((fuente.get("pasadas") or {}).get(pid) or {}).get("reservas") or []):
                if r.get("clave") not in vistas:
                    vistas.add(r.get("clave"))
                    reservas.append(r)
        out["pasadas"][pid] = {"reservas": reservas}
    out["actualizado"] = max(nuestro.get("actualizado") or "", remoto.get("actualizado") or "")
    return out
