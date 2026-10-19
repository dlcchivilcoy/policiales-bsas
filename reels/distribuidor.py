# -*- coding: utf-8 -*-
"""Buzón para el distribuidor central de X y TikTok (vive en el repo social_publisher).

Desde el 17/10/2026 también las piezas de NACIONALES y de sus categorías (deportes,
espectáculos…), solo para TikTok (`evento_nacional`): a X ya llegan como notas de la web.

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

import hashlib
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
        # Radio de 100 km (17/10/2026): el distribuidor descarta por su cuenta lo que no lo cumpla.
        "distancia_km": (pieza.get("geo") or {}).get("distancia_km"),
        "radio_ok": bool((pieza.get("geo") or {}).get("elegible", True)),
        "plataformas": ["x", "tiktok"],
    }


def evento_nacional(pieza: dict, video_url: str, url_web: str, url_youtube: str) -> dict:
    """Una pieza de NACIONALES o de las categorías nuevas (deportes, espectáculos…) para TikTok
    (17/10/2026, PDF «Prompt integral» etapa 6). Desde el 19/10/2026 también a X, con su video: el
    distribuidor no repite la nota de la web de la misma noticia (x_sincro)."""
    g = pieza.get("guion") or {}
    nota = pieza.get("nota") or {}
    return {
        "id": f"nacionales:{hashlib.sha1((pieza.get('url_original') or '').encode()).hexdigest()[:16]}",
        "origen": "nacionales",
        "tipo": "video",
        "generado": _iso(_ahora()),
        "titulo": (g.get("titular") or "").strip(),
        "descripcion": (g.get("bajada") or "").strip(),
        "video_url": video_url,
        "duracion_seg": (pieza.get("video") or {}).get("duracion"),
        "nota_url": url_web or "",
        "youtube_url": url_youtube or "",
        "prioridad": max(1, min(10, int(g.get("viral") or 5))),
        "urgente": False,
        "volanta": (g.get("volanta") or "").strip(),
        "categoria": g.get("seccion") or "",          # «Deportes», «Cine y series», «Política»…
        "categoria_nacional": nota.get("categoria") or "",
        "hashtags": [h.lstrip("#") for h in g.get("hashtags") or []][:2],
        "plataformas": ["x", "tiktok"],
    }


# SINCRONIZADO CON X (19/10/2026): el distribuidor lee este archivo desde el repo cada 20 minutos. Antes se
# subía recién al final de la corrida (hasta 3 h después) y X salía desfasado; ahora, cada vez que se anota
# una pieza, el archivo se sube en el momento por la API de GitHub (combinando con lo que ya está allá).
API_GITHUB = "https://api.github.com"
RUTA_REPO = "estado/buzon_distribuidor.json"


def subir_al_repo(cliente=None) -> bool:
    """Sube el buzón al repo (contents API), unido con la versión remota. True si quedó arriba. Solo en
    GitHub Actions (con GITHUB_TOKEN y GITHUB_REPOSITORY); nunca lanza."""
    import base64
    tok, repo = os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", "")
    if cliente is None and (not (tok and repo) or os.environ.get("GITHUB_ACTIONS") != "true"):
        return False
    try:
        if cliente is None:
            import httpx
            cliente = httpx.Client(timeout=30, headers={"Authorization": f"Bearer {tok}",
                                                        "Accept": "application/vnd.github+json"})
        url = f"{API_GITHUB}/repos/{repo}/contents/{RUTA_REPO}"
        for _intento in range(4):
            r = cliente.get(url, params={"ref": "main"})
            sha, remoto = None, {}
            if r.status_code == 200:
                d = r.json()
                sha = d.get("sha")
                try:
                    remoto = json.loads(base64.b64decode(d.get("content") or "").decode("utf-8"))
                except ValueError:
                    remoto = {}
            unido = combinar(leer(), remoto)
            cuerpo = {"message": "Buzón del distribuidor (X y TikTok) [skip ci]", "branch": "main",
                      "content": base64.b64encode(json.dumps(unido, ensure_ascii=False, indent=2)
                                                  .encode("utf-8")).decode("ascii")}
            if sha:
                cuerpo["sha"] = sha
            p = cliente.put(url, json=cuerpo)
            if p.status_code in (200, 201):
                BUZON.parent.mkdir(parents=True, exist_ok=True)
                BUZON.write_text(json.dumps(unido, ensure_ascii=False, indent=2), encoding="utf-8")
                return True
            if p.status_code not in (409, 422):        # 409/422: otro trabajo lo cambió en el medio
                break
        return False
    except Exception as e:  # noqa: BLE001 — el buzón nunca frena la pasada
        print(f"  distribuidor: no pude subir el buzón al repo ({type(e).__name__}); va al final de la corrida")
        return False


def dejar_nacional(pieza: dict, mp4: Path, url_web: str, url_youtube: str, subir, nombre: str) -> str:
    """Deja una pieza de nacionales en el buzón (sube el video al Release). Devuelve el id, o ""
    si no se pudo (nunca frena la pasada)."""
    if not activo():
        return ""
    ev_id = evento_nacional(pieza, "", "", "")["id"]
    d = leer()
    if any(e.get("id") == ev_id for e in d.get("eventos") or []):
        return ev_id
    try:
        url = subir(mp4, nombre)
    except Exception as e:  # noqa: BLE001
        print(f"  distribuidor: no pude subir el video de «{(pieza.get('guion') or {}).get('titular')}» ({e})")
        return ""
    d.setdefault("eventos", []).append(evento_nacional(pieza, url, url_web, url_youtube))
    d["actualizado"] = _iso(_ahora())
    d = combinar(d, {})
    BUZON.parent.mkdir(parents=True, exist_ok=True)
    BUZON.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    subir_al_repo()                                   # X sale a la par de las otras redes
    return ev_id


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
        subir_al_repo()                               # X sale a la par de las otras redes
    print(f"\nDistribuidor X/TikTok: {nuevos} pieza(s) al buzón" + (f", {fallas} sin video" if fallas else ""))
    return {"buzon": nuevos, "fallas": fallas}
