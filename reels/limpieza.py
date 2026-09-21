# -*- coding: utf-8 -*-
"""Borrado automático para que el sistema no se sature ni cueste de más.

Hay basura de DOS clases y se tratan distinto:

  1. INTERMEDIOS — las capas que usa ffmpeg (`_texto.png`, `_foto.jpg`, `_fondo.png`).
     Dejan de servir en el momento en que el .mp4 quedó armado. Se borran ahí mismo, no
     al otro día: son ~2 MB por pasada y no hay ninguna razón para que sobrevivan un
     segundo al video.

  2. PIEZAS VIEJAS — las carpetas de corridas anteriores y los .json/.csv del scrapeo.
     Se borran por antigüedad, con `DIAS_RETENCION` días de gracia.

Sin nada de esto, con 3 pasadas por día y 5 reels cada una, son ~9 MB por pasada →
**unos 810 MB por mes**. Con la limpieza puesta, lo que queda en disco es lo del día.

Correr a mano:
    venv\\Scripts\\python.exe -m reels.limpieza            # deja 1 día
    venv\\Scripts\\python.exe -m reels.limpieza --dias 3
    venv\\Scripts\\python.exe -m reels.limpieza --simular  # dice qué borraría, sin borrar
"""
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_REELS = RAIZ / "salida_reels"
SALIDA_SCRAPER = RAIZ / "salida"

DIAS_RETENCION = 1          # el reel de hoy y nada más
SUFIJOS_INTERMEDIOS = ("_texto.png", "_foto.jpg", "_fondo.png")


def _mb(n_bytes: int) -> float:
    return round(n_bytes / 1024 / 1024, 2)


# =============================================================================
# 1) Intermedios: se borran apenas el video quedó armado
# =============================================================================

def borrar_intermedios(carpeta: Path, simular: bool = False) -> dict:
    """Borra las capas que ffmpeg ya consumió. Se llama al final de cada pieza.

    Solo borra si el .mp4 correspondiente EXISTE: si el video falló, las capas son lo
    único que queda para diagnosticar por qué, y tirarlas sería quedarse sin evidencia.
    """
    borrados, liberado = [], 0
    for archivo in sorted(Path(carpeta).glob("*")):
        if not archivo.name.endswith(SUFIJOS_INTERMEDIOS):
            continue
        base = archivo.name
        for suf in SUFIJOS_INTERMEDIOS:
            if base.endswith(suf):
                base = base[: -len(suf)]
                break
        if not (archivo.parent / f"{base}.mp4").exists():
            continue                      # el video no salió: las capas se conservan
        liberado += archivo.stat().st_size
        borrados.append(archivo.name)
        if not simular:
            archivo.unlink(missing_ok=True)
    return {"borrados": borrados, "mb": _mb(liberado)}


# =============================================================================
# 2) Piezas viejas: por antigüedad
# =============================================================================

def _antiguedad_dias(ruta: Path) -> float:
    return (time.time() - ruta.stat().st_mtime) / 86400


def _peso(ruta: Path) -> int:
    if ruta.is_file():
        return ruta.stat().st_size
    return sum(f.stat().st_size for f in ruta.rglob("*") if f.is_file())


def limpiar_carpeta(base: Path, dias: int, patron: str = "*",
                    simular: bool = False) -> dict:
    """Borra lo que haya en `base` con más de `dias` días. Devuelve el informe."""
    if not base.exists():
        return {"borrados": [], "mb": 0.0}
    borrados, liberado = [], 0
    for item in sorted(base.glob(patron)):
        try:
            if _antiguedad_dias(item) <= dias:
                continue
            liberado += _peso(item)
            borrados.append(item.name)
            if not simular:
                shutil.rmtree(item) if item.is_dir() else item.unlink(missing_ok=True)
        except OSError as e:
            print(f"  [!] no pude borrar {item.name}: {e}")
    return {"borrados": borrados, "mb": _mb(liberado)}


# =============================================================================
# 3) Assets del Release de GitHub (cuando el sistema corra en la nube)
# =============================================================================

def limpiar_release(dias: int = DIAS_RETENCION, repo: str = "", tag: str = "reels-policiales",
                    token: str = "", simular: bool = False) -> dict:
    """Borra los assets del Release con más de `dias` días.

    En la nube el contenedor de Railway es EFÍMERO: lo que se escribe en disco desaparece
    cuando termina la corrida. Por eso los .mp4 que sí queremos conservar se suben como
    assets de un GitHub Release —el mismo patrón que ya usa `utils/video_host.py` en el
    bot— y ahí sí hay que barrer, porque los assets no vencen solos.

    Devuelve {'borrados': [...], 'mb': N} o {'error': '...'} si falta configuración.
    """
    token = token or os.environ.get("GITHUB_TOKEN", "")
    repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        return {"error": "faltan GITHUB_TOKEN y/o GITHUB_REPOSITORY", "borrados": [], "mb": 0.0}

    import httpx
    from datetime import datetime, timezone
    api = "https://api.github.com"
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    try:
        r = httpx.get(f"{api}/repos/{repo}/releases/tags/{tag}", headers=h, timeout=30)
        if r.status_code == 404:
            return {"borrados": [], "mb": 0.0, "nota": f"no existe el release «{tag}»"}
        r.raise_for_status()
        assets = r.json().get("assets", [])
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "borrados": [], "mb": 0.0}

    ahora = datetime.now(timezone.utc)
    borrados, liberado = [], 0
    for a in assets:
        try:
            creado = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if (ahora - creado).total_seconds() / 86400 <= dias:
            continue
        liberado += a.get("size", 0)
        borrados.append(a["name"])
        if not simular:
            try:
                httpx.delete(f"{api}/repos/{repo}/releases/assets/{a['id']}",
                             headers=h, timeout=30)
            except Exception as e:
                print(f"  [!] no pude borrar el asset {a['name']}: {e}")
    return {"borrados": borrados, "mb": _mb(liberado)}


# =============================================================================
# Barrido completo
# =============================================================================

def barrer(dias: int = DIAS_RETENCION, simular: bool = False,
           con_release: bool = False) -> dict:
    """La limpieza que corre al final de cada pasada."""
    # Intermedios de TODAS las corridas que sigan en disco, no solo la de recién: si una
    # pasada se cortó por la mitad (Railway la mató, se cayó la red), sus capas quedaron
    # ahí y nadie las iba a levantar.
    intermedios = {"borrados": [], "mb": 0.0}
    if SALIDA_REELS.exists():
        for corrida in SALIDA_REELS.iterdir():
            if corrida.is_dir():
                r = borrar_intermedios(corrida, simular)
                intermedios["borrados"] += r["borrados"]
                intermedios["mb"] = round(intermedios["mb"] + r["mb"], 2)

    informe = {
        "intermedios": intermedios,
        "reels": limpiar_carpeta(SALIDA_REELS, dias, "*", simular),
        "scrapeos": limpiar_carpeta(SALIDA_SCRAPER, dias, "policiales_*", simular),
    }
    # Restos de ffmpeg que hayan quedado de una corrida cortada por la mitad.
    tmp = SALIDA_REELS / "_tmp"
    if tmp.exists():
        informe["tmp"] = limpiar_carpeta(tmp.parent, -1, "_tmp", simular)
    if con_release:
        informe["release"] = limpiar_release(dias, simular=simular)
    informe["mb_total"] = round(sum(v.get("mb", 0) for v in informe.values()
                                    if isinstance(v, dict)), 2)
    return informe


def main():
    ap = argparse.ArgumentParser(description="Borra reels y scrapeos viejos para no saturar.")
    ap.add_argument("--dias", type=int, default=DIAS_RETENCION,
                    help=f"cuántos días conservar (default {DIAS_RETENCION})")
    ap.add_argument("--simular", action="store_true", help="decir qué borraría, sin borrar")
    ap.add_argument("--con-release", action="store_true",
                    help="barrer también los assets del Release de GitHub")
    args = ap.parse_args()

    modo = "SIMULACIÓN — no se borra nada" if args.simular else "BORRADO REAL"
    print(f"=== Limpieza [{modo}] — se conservan {args.dias} día(s) ===\n")

    antes = _mb(_peso(SALIDA_REELS)) + _mb(_peso(SALIDA_SCRAPER))
    informe = barrer(args.dias, args.simular, args.con_release)

    for clave in ("intermedios", "reels", "scrapeos", "tmp", "release"):
        r = informe.get(clave)
        if not r:
            continue
        if r.get("error"):
            print(f"{clave:<10} {r['error']}")
            continue
        n = len(r["borrados"])
        print(f"{clave:<10} {n:>3} elemento(s), {r['mb']:>7.2f} MB" +
              (f"   ({r['nota']})" if r.get("nota") else ""))
        for b in r["borrados"][:5]:
            print(f"           · {b}")
        if n > 5:
            print(f"           · … y {n - 5} más")

    print(f"\nLiberado: {informe['mb_total']:.2f} MB   (en disco había {antes:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
