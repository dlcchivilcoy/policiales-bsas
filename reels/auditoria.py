# -*- coding: utf-8 -*-
"""Registro de auditoría por pasada (17/10/2026, PDF «Prompt integral» §32, etapa 7).

Lo que la persona que revisa necesita sin tener que leer los registros técnicos: qué se miró, qué
entró y por qué, qué quedó afuera y por qué (radio, ubicación dudosa, repetido, cupo, intercalado) y
cómo salió en cada destino. Lo escriben el flujo (armado), el publicador (publicación) y nacionales;
lo lee tools/panel.py para armar estado/panel_editorial.md.

estado/auditoria.json → {"pasadas": {"2026-10-17T12:05": {"armado": {...}, "publicacion": {...},
"nacionales": {...}}}}. Guarda DIAS días; tools/guardar_estado.py lo combina por pasada y parte.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reels import cupo as CUPO

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "estado" / "auditoria.json"
DIAS = 8
TZ_AR = timezone(timedelta(hours=-3))
MAX_LISTA = 40                 # por parte: alcanza para una pasada y no infla el repo


def pasada_actual() -> str:
    return CUPO.pasada_id(CUPO.PASADAS_AR, datetime.now(TZ_AR))


def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads((ruta or ARCHIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pasadas": {}}


def anotar(parte: str, datos: dict, pid: str = "", ruta: Path = None) -> str:
    """Guarda `datos` como la parte `parte` (armado, publicacion, nacionales) de la pasada. Si la
    misma parte ya estaba (una corrida repetida), las listas se suman y los números se pisan."""
    ruta = ruta or ARCHIVO
    pid = pid or pasada_actual()
    d = cargar(ruta)
    p = d.setdefault("pasadas", {}).setdefault(pid, {})
    previa = p.get(parte) or {}
    nueva = dict(previa)
    for k, v in datos.items():
        if isinstance(v, list) and isinstance(previa.get(k), list):
            vistos = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in previa[k]}
            nueva[k] = (previa[k] + [x for x in v if json.dumps(x, sort_keys=True, ensure_ascii=False)
                                     not in vistos])[-MAX_LISTA:]
        else:
            nueva[k] = v[-MAX_LISTA:] if isinstance(v, list) else v
    nueva["cuando"] = datetime.now(TZ_AR).isoformat(timespec="seconds")
    p[parte] = nueva
    limite = (datetime.now(TZ_AR) - timedelta(days=DIAS)).strftime("%Y-%m-%dT%H:%M")
    d["pasadas"] = {k: v for k, v in d["pasadas"].items() if k >= limite}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return pid


def combinar(nuestro: dict, remoto: dict) -> dict:
    """Para tools/guardar_estado.py: por pasada y por parte gana la más nueva («cuando»): el trabajo
    de policiales y el de nacionales escriben partes distintas de la misma pasada."""
    out = {"pasadas": {}}
    for fuente in (remoto or {}, nuestro or {}):
        for pid, partes in (fuente.get("pasadas") or {}).items():
            destino = out["pasadas"].setdefault(pid, {})
            for parte, v in (partes or {}).items():
                if parte not in destino or (v.get("cuando") or "") >= (destino[parte].get("cuando") or ""):
                    destino[parte] = v
    return out
