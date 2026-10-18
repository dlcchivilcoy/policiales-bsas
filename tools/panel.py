# -*- coding: utf-8 -*-
"""Panel editorial (17/10/2026, PDF «Prompt integral» §32-33, etapa 7) → estado/panel_editorial.md.

Una sola página para revisar sin leer registros técnicos: cada pasada con su cupo de policiales (de
3), qué entró y a cuántos km, qué quedó afuera y por qué, cómo salió en cada destino, lo que espera
por el intercalado, las nacionales por categoría, el volumen de la semana por destino y las métricas
a edad fija. Lo arma el workflow al final de cada pasada (y se puede correr a mano):

    venv\\Scripts\\python.exe tools\\panel.py            # además mide las piezas que cumplen 24 h
    venv\\Scripts\\python.exe tools\\panel.py --sin-medir
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")
from reels import auditoria as AU, cupo as CUPO, metricas as ME   # noqa: E402

ESTADO = RAIZ / "estado"
SALIDA = ESTADO / "panel_editorial.md"
TZ_AR = timezone(timedelta(hours=-3))
ICONO = {"ok": "✅", "sin_confirmar": "❔", "simulado": "🧪", "espera": "⏳", "omitida": "—", "cupo": "🚫",
         "fallo": "❌", "rechazado": "⛔", "apagada": "·"}
NOMBRE = {"youtube": "YouTube", "web": "Web", "facebook": "Facebook", "fb_youtube": "FB enlace",
          "instagram": "Instagram", "tiktok_buzon": "TikTok (buzón)"}


def _leer(nombre: str, defecto):
    try:
        return json.loads((ESTADO / nombre).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def _celda(r: dict) -> str:
    if not r:
        return "·"
    est = r.get("estado") or ""
    det = (r.get("detalle") or "").replace("|", "/")
    return f"{ICONO.get(est, est)} {det[:60]}".strip()


def seccion_pasadas(aud: dict, hoy: str) -> list:
    md = [f"## Hoy ({hoy})", ""]
    pasadas = sorted((k for k in (aud.get("pasadas") or {}) if k.startswith(hoy)), reverse=True)
    if not pasadas:
        return md + ["_Todavía no hay pasadas registradas hoy._", ""]
    for pid in pasadas:
        p = aud["pasadas"][pid]
        arm, pub, nac = p.get("armado") or {}, p.get("publicacion") or {}, p.get("nacionales") or {}
        md.append(f"### {pid[11:]} — {pub.get('reservadas', 0) or 0} de {pub.get('maximo', CUPO.maximo())} "
                  f"hechos policiales")
        if arm:
            md.append(f"Notas policiales leídas: {arm.get('notas_scrapeadas', 0)} · fuera del radio: "
                      f"{len(arm.get('fuera_de_radio') or [])} · ubicación pendiente: "
                      f"{len(arm.get('pendientes_ubicacion') or [])} · repetidas: {len(arm.get('repetidas') or [])} · "
                      f"armadas: {len(arm.get('armadas') or [])}")
        if pub.get("piezas"):
            md += ["", "| Hecho | Lugar | YouTube | Web | Facebook | Instagram |", "|---|---|---|---|---|---|"]
            for f in pub["piezas"]:
                dst = f.get("destinos") or {}
                lugar = f"{f.get('localidad') or ''}" + (f" ({f['km']} km)" if f.get("km") is not None else "")
                md.append(f"| {(f.get('titular') or '')[:70]} | {lugar} | {_celda(dst.get('youtube'))} | "
                          f"{_celda(dst.get('web'))} | {_celda(dst.get('facebook') or dst.get('fb_youtube'))} | "
                          f"{_celda(dst.get('instagram'))} |")
        if pub.get("salteadas"):
            md += ["", "**No salieron en esta pasada:**"]
            md += [f"- {(s.get('titular') or '')[:80]} — {s.get('motivo')}" for s in pub["salteadas"][:12]]
        if arm.get("fuera_de_radio"):
            md += ["", "**Fuera del radio de 100 km:**"]
            por = Counter(f"{x.get('localidad')} ({x.get('km')} km)" for x in arm["fuera_de_radio"])
            md.append("- " + " · ".join(f"{k} ×{v}" for k, v in por.most_common()))
        if arm.get("pendientes_ubicacion"):
            md += ["", "**Ubicación sin resolver (no salen solas):**"]
            md += [f"- {(x.get('titulo') or '')[:80]} — {x.get('motivo')}" for x in arm["pendientes_ubicacion"][:8]]
        if nac.get("piezas"):
            md += ["", "**Nacionales y categorías:**"]
            md += [f"- [{x.get('categoria')}] {(x.get('titular') or '')[:80]} — "
                   + " ".join(f"{NOMBRE.get(r, r)} {ICONO.get(e, e)}" for r, e in (x.get("destinos") or {}).items())
                   for x in nac["piezas"]]
        md.append("")
    return md


def seccion_volumen(pol: dict, nac: dict, ahora: datetime) -> list:
    desde = ahora - timedelta(days=7)
    cuenta = Counter()
    for fuente, regs in (("Policiales", pol), ("Nacionales", (nac or {}).get("piezas") or {})):
        for e in regs.values():
            if not isinstance(e, dict):
                continue
            for red in ("youtube", "web", "facebook", "fb_youtube", "instagram"):
                r = e.get(red)
                if isinstance(r, dict) and r.get("estado") in ("ok", "sin_confirmar"):
                    t = ME._utc(r.get("cuando"))
                    if t and t >= desde:
                        cuenta[(fuente, red)] += 1
    md = ["## Últimos 7 días: volumen por destino", "",
          "| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |", "|---|---:|---:|---:|---:|---:|"]
    for fuente in ("Policiales", "Nacionales"):
        md.append(f"| {fuente} | " + " | ".join(str(cuenta[(fuente, r)]) for r in
                                                   ("youtube", "web", "facebook", "fb_youtube", "instagram")) + " |")
    md += ["", "Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día "
           "(1 de las categorías nuevas); X y TikTok en el "
           "[panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).",
           "Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.", ""]
    return md


def _n(v) -> str:
    return "s/d" if v is None else f"{v:g}"


def seccion_metricas(met: dict, ahora: datetime) -> list:
    res = ME.resumen(met, 7, ahora)
    md = ["## Métricas a 24-72 h de publicadas (últimos 7 días)", ""]
    if not res:
        md.append("_Todavía no hay piezas medidas (se miden al cumplir 24 h)._")
    for destino, r in res.items():
        md += [f"### {NOMBRE.get(destino, destino)} — {r['n']} piezas · mediana vistas {_n(r['vistas'])} · "
               f"mediana likes {_n(r['likes'])}", ""]
        for por, grupos in r["por"].items():
            if not grupos:
                continue
            md.append(f"- **Por {por}:** " + " · ".join(
                f"{k}: {v['n']}" + (f", vistas {v['vistas']:g}" if v["vistas"] is not None else "")
                + (f", likes {v['likes']:g}" if v["likes"] is not None else "")
                + (" ⚠️muestra chica" if v["n"] < ME.MUESTRA_MINIMA else "")
                for k, v in sorted(grupos.items())))
        md.append("")
    md += [f"_No disponible: {met.get('no_disponible') or ME.NO_DISPONIBLE}_",
           "_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._", ""]
    return md


def seccion_shorts(pol: dict, nac: dict) -> list:
    c = Counter()
    rech = []
    for regs in (pol, (nac or {}).get("piezas") or {}):
        for e in regs.values():
            yt = (e or {}).get("youtube") if isinstance(e, dict) else None
            if isinstance(yt, dict) and yt.get("id"):
                if yt.get("verificado"):
                    c[yt["verificado"]] += 1
                elif yt.get("estado") == "ok":
                    # «subida» la tienen los subidos desde el control (17/10); los de antes no se verifican.
                    c["subido, se verifica en la pasada siguiente" if yt.get("subida") else "anterior al control"] += 1
                else:
                    c[yt.get("estado")] += 1
                if yt.get("estado") == "rechazado":
                    rech.append(f"- {e.get('titular') or ''}: {yt.get('detalle')}")
    return ["## Shorts en Radio del Centro (memoria de 5-7 días)", "",
            " · ".join(f"{k}: {v}" for k, v in c.most_common()) or "_sin datos_", *rech[:10], ""]


CONTROLES = """## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_VARIEDAD_POR_PASADA`, `NAC_CUPO_<CATEGORIA>` — categorías nuevas.
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
"""


def armar(medir: bool = True) -> str:
    ahora = datetime.now(timezone.utc)
    pol = _leer("publicados.json", {})
    nac = _leer("nacionales.json", {})
    if medir:
        try:
            from reels import publicador as PUB
            import entorno
            entorno.cargar()
            tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
            ptok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "") or tok

            def pedir_meta(url, params):
                token = tok if "like_count" in params.get("fields", "") else ptok     # Instagram / Facebook
                r = PUB._pedir("GET", url, token, params=params)
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}")
                return r.json() or {}

            def pedir_yt(ids):
                acceso = PUB._yt_sesion()
                out = {}
                for i in range(0, len(ids), 50):
                    r = PUB._pedir("GET", f"{PUB.YT_API}/videos", acceso,
                                   params={"part": "statistics", "id": ",".join(ids[i:i + 50])})
                    out.update({v["id"]: v.get("statistics") or {} for v in (r.json() or {}).get("items") or []})
                return out
            res = ME.medir(pol, (nac or {}).get("piezas") or {}, pedir_meta, pedir_yt, ahora)
            print(f"Métricas: {res['medidas']} pieza(s) medidas" + (f"; fallas: {res['fallas'][:3]}" if res["fallas"] else ""))
        except Exception as e:                       # noqa: BLE001 — el panel sale igual
            print(f"Métricas: no se pudieron medir ({type(e).__name__}: {e})")
    hoy = ahora.astimezone(TZ_AR).date().isoformat()
    md = [f"# Panel editorial — Diario y Radio",
          f"Actualizado: {ahora.astimezone(TZ_AR):%d/%m/%Y %H:%M} (hora AR). Se rehace al final de cada pasada.", "",
          "Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar", ""]
    md += seccion_pasadas(AU.cargar(ESTADO / "auditoria.json"), hoy)
    md += seccion_volumen(pol, nac, ahora)
    md += seccion_metricas(ME.cargar(ESTADO / "metricas.json"), ahora)
    md += seccion_shorts(pol, nac)
    md.append(CONTROLES)
    texto = "\n".join(md)
    SALIDA.write_text(texto, encoding="utf-8")
    return texto


if __name__ == "__main__":
    print(armar(medir="--sin-medir" not in sys.argv)[:1500])
