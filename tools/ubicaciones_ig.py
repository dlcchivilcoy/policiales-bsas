# -*- coding: utf-8 -*-
"""Cargar y validar los location_id de Instagram de cada localidad (reels/ubicaciones.json).

    venv\\Scripts\\python.exe tools\\ubicaciones_ig.py                          # la tabla
    venv\\Scripts\\python.exe tools\\ubicaciones_ig.py --poner chacabuco=108... "fuente=buscador de IG"
    venv\\Scripts\\python.exe tools\\ubicaciones_ig.py --validar                # contra la API

Cómo se valida SIN crear nada: se pide un contenedor con una URL que no es una imagen y el location_id.
Instagram revisa la ubicación ANTES de bajar la imagen: si el ID no es de un lugar contesta «location_id
is not a valid location page ID»; si lo es, falla recién al bajar la imagen. En ningún caso queda un
contenedor. Ojo: esto prueba que es UN lugar, no cuál; el nombre se confirma al sacarlo del buscador
(el 12/10 Wikidata daba como «Luján» la ID de Villa Luján, Tucumán).

De dónde salen (12/10/2026): con la sesión de Instagram abierta en el navegador,
`/api/v1/fbsearch/places/?query=<ciudad>` (header X-IG-App-ID) da por cada lugar su `pk` de Instagram y
su `facebook_places_id`. SOLO sirve el facebook_places_id: los pk cortos de Instagram (p. ej. 238764192)
la API los rechaza. Se toma el del lugar categoría «Ciudad» con más publicaciones (el primero del
directorio público /explore/locations/c<N>/) y se confirman las coordenadas.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import httpx  # noqa: E402

import entorno  # noqa: E402
from reels import ubicaciones as UB  # noqa: E402

GRAPH = "https://graph.facebook.com/v26.0"
NO_IMAGEN = "https://example.com/no-es-una-imagen.txt"


def es_lugar(location_id: str, uid: str, tok: str, pedir=None) -> tuple:
    """(True/False/None, detalle). None = no se pudo saber (red, token)."""
    pedir = pedir or (lambda url, **kw: httpx.post(url, timeout=60, **kw))
    try:
        r = pedir(f"{GRAPH}/{uid}/media", headers={"Authorization": f"Bearer {tok}"},
                  data={"image_url": NO_IMAGEN, "caption": "validación de ubicación (no se publica)",
                        "location_id": location_id})
    except httpx.HTTPError as e:
        return None, type(e).__name__
    try:
        err = (r.json() or {}).get("error") or {}
    except ValueError:
        err = {}
    msg = str(err.get("message") or "")
    if "location" in msg.lower():
        return False, msg[:120]
    if r.status_code == 200:
        return True, "creó un contenedor (no debería con esa URL), igual la ubicación es válida"
    if err.get("code") in (190, 10, 200) or "token" in msg.lower():
        return None, msg[:120]
    return True, msg[:80]


def main():
    entorno.cargar()
    tabla = UB.cargar()
    args = sys.argv[1:]
    if "--poner" in args:
        i = args.index("--poner")
        k, _, v = args[i + 1].partition("=")
        k = UB.clave(k)
        if k not in tabla or not v.strip().isdigit():
            raise SystemExit(f"localidad «{k}» desconocida o ID no numérico")
        tabla[k].update(id=v.strip(), valido=None)
        for extra in args[i + 2:]:
            if extra.startswith("fuente="):
                tabla[k]["fuente"] = extra.split("=", 1)[1]
    if "--validar" in args:
        uid, tok = os.environ.get("INSTAGRAM_USER_ID", ""), os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        for k, d in tabla.items():
            if not d.get("id"):
                continue
            ok, det = es_lugar(d["id"], uid, tok)
            if ok is not None:
                d["valido"] = ok
            print(f"{'OK ' if ok else ('MAL' if ok is False else '¿? ')} {d['nombre']:<22} {d['id']:<18} {det}")
    UB.ARCHIVO.write_text(json.dumps(tabla, ensure_ascii=False, indent=2), encoding="utf-8")
    con = sum(1 for d in tabla.values() if d.get("id") and d.get("valido") is not False)
    print(f"\n{con} de {len(tabla)} localidades con ubicación.")
    if "--validar" not in args and "--poner" not in args:
        for k, d in tabla.items():
            print(f"  {d['nombre']:<22} {d.get('id') or '—':<18} {d.get('fuente', '')}")


if __name__ == "__main__":
    main()
