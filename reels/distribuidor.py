# -*- coding: utf-8 -*-
"""Buzón para el distribuidor central de X y TikTok (vive en el repo social_publisher).

Policiales NO publica en X ni en TikTok: al final de cada pasada deja acá TODAS las piezas
aptas, con su video en el Release público, y el distribuidor elige las de más potencial
(hasta 12 por día en cada red), las programa en Buffer y evita repetir el mismo hecho.

Archivo: estado/buzon_distribuidor.json  →  {"actualizado": ISO, "eventos": [...]}
Solo guarda las últimas 48 h (los videos del Release se borran a las 24 h; el distribuidor
no publica una pieza policial con más de 18 h).

Interruptor: variable DISTRIBUIDOR_POLICIALES=0 (repo o entorno) apaga el buzón.
Nunca corta la pasada: si algo falla, IG/FB/YouTube/web ya salieron igual.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUZON = RAIZ / "estado" / "buzon_distribuidor.json"
HORAS = 48
# Lo que el distribuidor toma como URGENTE: alto potencial y recién publicado por el medio.
URGENTE_VIRAL = 9
URGENTE_HORAS = 3


def activo() -> bool:
    return (os.environ.get("DISTRIBUIDOR_POLICIALES") or "1").strip().lower() not in ("0", "no", "false", "off")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def leer() -> dict:
    try:
        d = json.loads(BUZON.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {"eventos": []}
    except (OSError, ValueError):
        return {"eventos": []}


def combinar(nuestro: dict, remoto: dict) -> dict:
    """Unión por id (para tools/guardar_estado.py): nunca se pierde un evento anotado."""
    por_id = {e.get("id"): e for e in (remoto or {}).get("eventos") or [] if isinstance(e, dict)}
    for e in (nuestro or {}).get("eventos") or []:
        if isinstance(e, dict):
            por_id.setdefault(e.get("id"), e)
    corte = _iso(_ahora() - timedelta(hours=HORAS))
    eventos = sorted((e for e in por_id.values() if (e.get("generado") or "") >= corte),
                     key=lambda e: e.get("generado") or "")
    return {"actualizado": max((nuestro or {}).get("actualizado") or "",
                               (remoto or {}).get("actualizado") or ""),
            "eventos": eventos}


def evento(pieza: dict, video_url: str, url_web: str, url_youtube: str, clave: str) -> dict:
    g = pieza.get("guion") or {}
    v = pieza.get("video") or {}
    viral = int(pieza.get("viral") or 5)
    publicado = pieza.get("publicado") or ""
    try:
        edad_h = (_ahora() - datetime.fromisoformat(publicado.replace("Z", "+00:00"))).total_seconds() / 3600
    except (ValueError, AttributeError):
        edad_h = 99
    titular = (g.get("titular") or "").strip()
    volanta = (g.get("volanta") or "").strip()
    return {
        "id": f"policiales:{clave}",
        "origen": "policiales",
        "tipo": "video",
        "generado": _iso(_ahora()),
        "titulo": titular,
        # La bajada ya viene escrita para redes (≤280, cerrada en punto, sin inventar).
        "descripcion": (g.get("bajada") or "").strip(),
        # TikTok: la descripción que el sistema ya arma para TikTok (con sus hashtags).
        "texto_tiktok": (pieza.get("descripcion_tiktok") or "").strip(),
        "video_url": video_url,
        "duracion_seg": v.get("duracion"),
        "nota_url": url_web or "",
        "youtube_url": url_youtube or "",
        "prioridad": max(1, min(10, viral)),
        "urgente": viral >= URGENTE_VIRAL and edad_h <= URGENTE_HORAS,
        "localidad": pieza.get("localidad_hecho") or pieza.get("localidad") or "",
        "volanta": volanta,
        "categoria": pieza.get("tipo") or "",
        "plataformas": ["x", "tiktok"],
    }


def dejar(listas: list, ledger: dict, carpeta: Path, subir, repo: str, tag: str,
          clave_de, existe=None) -> dict:
    """Deja en el buzón las piezas de la pasada. `subir(mp4, nombre) -> url` sube al Release
    si el video no está (Instagram ya pudo haberlo subido con el mismo nombre)."""
    if not activo():
        return {"buzon": "apagado"}
    d = leer()
    ya = {e.get("id") for e in d.get("eventos") or []}
    nuevos, fallas = 0, 0
    for pieza, mp4 in listas:
        clave = clave_de(pieza)
        if not clave or f"policiales:{clave}" in ya:
            continue
        nombre = f"{carpeta.name}_{mp4.name}"
        url = f"https://github.com/{repo}/releases/download/{tag}/{nombre}"
        try:
            if not (existe and existe(url)):
                url = subir(mp4, nombre)
        except Exception as e:  # noqa: BLE001
            print(f"  distribuidor: no pude subir el video de #{pieza.get('orden')} ({e}); se saltea")
            fallas += 1
            continue
        hecho = ledger.get(clave) or {}
        url_web = (hecho.get("web") or {}).get("url") or ""
        yt = hecho.get("youtube") or {}
        url_yt = (yt.get("url") or "") if yt.get("estado") == "ok" else ""
        d.setdefault("eventos", []).append(evento(pieza, url, url_web, url_yt, clave))
        nuevos += 1
    if nuevos:
        d["actualizado"] = _iso(_ahora())
        d = combinar(d, {})
        BUZON.parent.mkdir(parents=True, exist_ok=True)
        BUZON.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDistribuidor X/TikTok: {nuevos} pieza(s) al buzón" + (f", {fallas} sin video" if fallas else ""))
    return {"buzon": nuevos, "fallas": fallas}
