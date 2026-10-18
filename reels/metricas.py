# -*- coding: utf-8 -*-
"""Métricas a edad fija y resumen semanal por destino (17/10/2026, PDF «Prompt integral» §25, §33, etapa 7).

Cada pieza (policiales y nacionales) se mide UNA vez, cuando cumple entre HORAS_MIN y HORAS_MAX de
publicada: así se comparan publicaciones de la misma edad, no una de la mañana con una de hace tres
días. Se guarda en estado/metricas.json.

SOLO lo que la API deja leer hoy, sin inventar (verificado el 17/10/2026 con debug_token):
- Instagram: likes y comentarios. Alcance, reproducciones, guardados, compartidos y retención NO: el
  token de la página no tiene el permiso `instagram_manage_insights`.
- Facebook: reproducciones del reel (campo `views`), likes y comentarios. Alcance e insights NO: falta
  `read_insights`. Los posteos con placa de nacionales tampoco: falta `pages_read_user_content`.
- YouTube: vistas, likes y comentarios (videos.list statistics, 1 unidad cada 50).
- X y TikTok: los mide el distribuidor de social_publisher con lo que devuelve Buffer.
Cuando se sumen los permisos, se agregan esas métricas acá sin tocar lo demás.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "estado" / "metricas.json"
HORAS_MIN, HORAS_MAX = 24, 72
DIAS = 35
TZ_AR = timezone(timedelta(hours=-3))
GRAPH = "https://graph.facebook.com/v26.0"
NO_DISPONIBLE = ("Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso "
                 "instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos "
                 "con placa de nacionales (falta pages_read_user_content). "
                 "Web: vistas por nota — sin integración en este sistema.")
DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads((ruta or ARCHIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"piezas": {}}


def guardar(d: dict, ruta: Path = None):
    ruta = ruta or ARCHIVO
    limite = (datetime.now(timezone.utc) - timedelta(days=DIAS)).isoformat()
    d["piezas"] = {k: v for k, v in (d.get("piezas") or {}).items() if (v.get("publicado") or "") >= limite}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def _utc(texto: str, sin_zona_es_utc: bool = True):
    """La hora de la memoria: policiales la guarda sin zona (la de la nube, UTC); nacionales, con zona."""
    try:
        t = datetime.fromisoformat(texto or "")
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc if sin_zona_es_utc else TZ_AR)
    return t.astimezone(timezone.utc)


def franja(t_utc: datetime) -> str:
    h = t_utc.astimezone(TZ_AR).hour
    return "madrugada (0-6)" if h < 6 else "mañana (6-12)" if h < 12 else "tarde (12-18)" if h < 18 else "noche (18-24)"


def _pendientes(fuente: str, registros: dict, ya: dict, ahora: datetime) -> list:
    """(clave, entrada, publicado UTC) de lo que cumple la edad y todavía no se midió."""
    out = []
    for clave, e in registros.items():
        if not isinstance(e, dict):
            continue
        k = f"{fuente}:{clave}"
        if k in ya:
            continue
        horas = [_utc(r.get("cuando")) for r in e.values() if isinstance(r, dict)
                 and r.get("estado") in ("ok", "sin_confirmar") and r.get("cuando")]
        horas = [h for h in horas if h]
        if not horas:
            continue
        pub = min(horas)
        edad = (ahora - pub).total_seconds() / 3600
        if HORAS_MIN <= edad <= HORAS_MAX:
            out.append((k, e, pub))
    return out


def medir(registros_pol: dict, registros_nac: dict, pedir_meta, pedir_yt, ahora: datetime = None,
          ruta: Path = None) -> dict:
    """Toma la foto de lo que cumple la edad. `pedir_meta(url, params)` y `pedir_yt(ids)` son el
    acceso a las APIs (se reemplazan en las pruebas). Devuelve {"medidas": n, "fallas": [...]}."""
    ahora = ahora or datetime.now(timezone.utc)
    d = cargar(ruta)
    piezas = d.setdefault("piezas", {})
    pend = _pendientes("policiales", registros_pol, piezas, ahora) + _pendientes("nacionales", registros_nac, piezas, ahora)
    ids_yt = [str((e.get("youtube") or {}).get("id")) for _k, e, _p in pend
              if (e.get("youtube") or {}).get("estado") == "ok" and (e.get("youtube") or {}).get("id")]
    try:
        stats_yt = pedir_yt(ids_yt) if ids_yt else {}
    except Exception as ex:                                    # noqa: BLE001
        stats_yt, fallas = {}, [f"YouTube: {ex}"]
    else:
        fallas = []
    for k, e, pub in pend:
        nacional = k.startswith("nacionales:")
        fila = {"publicado": pub.isoformat(), "horas": round((ahora - pub).total_seconds() / 3600, 1),
                "capturado": ahora.isoformat(timespec="seconds"),
                "origen": "nacionales" if nacional else "policiales",
                "categoria": (e.get("categoria") or "general") if nacional else "policiales",
                "titular": e.get("titular") or "", "localidad": e.get("lugar_hecho") or e.get("localidad") or "",
                "km": e.get("distancia_km"), "franja": franja(pub), "dia": DIAS_SEMANA[pub.astimezone(TZ_AR).weekday()],
                "destinos": {}}
        ig = e.get("instagram") or {}
        if ig.get("estado") == "ok" and ig.get("id"):
            try:
                r = pedir_meta(f"{GRAPH}/{ig['id']}", {"fields": "like_count,comments_count"})
                fila["destinos"]["instagram"] = {"likes": r.get("like_count"), "comentarios": r.get("comments_count")}
            except Exception as ex:                            # noqa: BLE001
                fallas.append(f"Instagram {ig['id']}: {ex}")
        fb = e.get("facebook") or {}
        # Los posteos con placa de nacionales no se pueden leer (pages_read_user_content): solo los reels.
        if fb.get("estado") == "ok" and fb.get("id") and not nacional:
            campos = "likes.summary(true).limit(0),comments.summary(true).limit(0),views"
            try:
                r = pedir_meta(f"{GRAPH}/{fb['id']}", {"fields": campos})
                fila["destinos"]["facebook"] = {
                    "vistas": r.get("views"), "likes": ((r.get("likes") or {}).get("summary") or {}).get("total_count"),
                    "comentarios": ((r.get("comments") or {}).get("summary") or {}).get("total_count"),
                    "formato": "reel"}
            except Exception as ex:                            # noqa: BLE001
                fallas.append(f"Facebook {fb['id']}: {ex}")
        yt = e.get("youtube") or {}
        if str(yt.get("id")) in stats_yt:
            s = stats_yt[str(yt["id"])]
            fila["destinos"]["youtube"] = {"vistas": _int(s.get("viewCount")), "likes": _int(s.get("likeCount")),
                                           "comentarios": _int(s.get("commentCount"))}
        piezas[k] = fila
    d["no_disponible"] = NO_DISPONIBLE
    guardar(d, ruta)
    return {"medidas": len(pend), "fallas": fallas}


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# =============================================================================
# Resumen semanal
# =============================================================================
MUESTRA_MINIMA = 5


def _mediana(valores: list):
    v = [x for x in valores if isinstance(x, (int, float))]
    return statistics.median(v) if v else None


def resumen(d: dict, dias: int = 7, ahora: datetime = None) -> dict:
    """{destino: {por: {grupo: {n, mediana_vistas, mediana_likes}}}} de los últimos `dias`, por
    categoría, franja horaria, día y (policiales) banda de distancia."""
    ahora = ahora or datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=dias)).isoformat()
    filas = [f for f in (d.get("piezas") or {}).values() if (f.get("publicado") or "") >= desde]
    out = {}
    for destino in ("youtube", "facebook", "instagram"):
        con = [f for f in filas if destino in (f.get("destinos") or {})]
        if not con:
            continue
        grupos = {}
        for por, clave in (("categoría", lambda f: f.get("categoria")), ("franja", lambda f: f.get("franja")),
                           ("día", lambda f: f.get("dia")), ("distancia", _banda)):
            g = {}
            for f in con:
                k = clave(f)
                if k:
                    g.setdefault(k, []).append(f["destinos"][destino])
            grupos[por] = {k: {"n": len(v), "vistas": _mediana([x.get("vistas") for x in v]),
                               "likes": _mediana([x.get("likes") for x in v])} for k, v in g.items()}
        out[destino] = {"n": len(con), "vistas": _mediana([f["destinos"][destino].get("vistas") for f in con]),
                        "likes": _mediana([f["destinos"][destino].get("likes") for f in con]), "por": grupos}
    return out


def _banda(f: dict) -> str:
    if f.get("origen") != "policiales" or f.get("km") is None:
        return ""
    km = float(f["km"])
    return "Chivilcoy" if km < 5 else "hasta 50 km" if km <= 50 else "50 a 100 km"
