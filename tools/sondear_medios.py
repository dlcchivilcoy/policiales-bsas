# -*- coding: utf-8 -*-
"""Sonda de flujo policial. Para cada candidato mide, con datos reales y no con
intuicion, cuanto sirve como fuente:

  - si el sitio esta vivo (probando https/http y con/sin www)
  - si tiene seccion propia de policiales, que es la via preferida
  - si hay RSS (barato) o hay que raspar HTML (caro)
  - cuantas notas publica por dia y que porcentaje son policiales
  - FLUJO POLICIAL/DIA = policiales / dias cubiertos  <- de aca salen los 2 elegidos

Correr:  venv\\Scripts\\python.exe tools\\sondear_medios.py
Salida:  data/sondeo.json  +  tabla por consola
"""
import sys, os, json, time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import fetch
from scraper.keywords import puntuar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HILOS = 12
LIMITE_NOTAS = 40
# El respaldo con navegador es lento: se enciende con --navegador y solo vale la
# pena en la ronda de repesca sobre los medios que HTTP no pudo leer.
USAR_NAVEGADOR = "--navegador" in sys.argv


def _dias_cubiertos(notas):
    """Cuantos dias abarca el listado. Sirve para pasar de 'N notas en el listado' a
    'N notas por dia', que es lo unico comparable entre un medio que publica 5 por
    dia y otro cuyo feed guarda un mes de archivo."""
    fechas = []
    for n in notas:
        if not n.get("publicado"):
            continue
        try:
            d = datetime.fromisoformat(n["publicado"].replace("Z", "+00:00"))
            fechas.append(d.replace(tzinfo=None))
        except Exception:
            pass
    if len(fechas) < 2:
        return None
    return max((max(fechas) - min(fechas)).total_seconds() / 86400, 0.5)


def _analizar(notas):
    pol = []
    for n in notas:
        p = puntuar(n["titulo"], n.get("copete", ""))
        if p["probable"]:
            pol.append((p["score"], n["titulo"]))
    return pol


def sondear(localidad, dominio):
    r = {"localidad": localidad, "dominio": dominio, "base": None, "vivo": False,
         "rss": None, "metodo": None, "seccion_policial": None, "seccion_rss": None,
         "n_notas": 0, "n_policiales": 0, "pct_policial": 0.0, "dias": None,
         "notas_dia": None, "flujo_policial_dia": None, "ultima": None,
         "ejemplos": [], "error": None}

    base, motivo = fetch.resolver_base(dominio)
    if not base:
        r["error"] = motivo
        return r
    r["base"] = base
    r["vivo"] = True

    try:
        # 1) Seccion de policiales: es la via preferida si existe.
        sec = fetch.descubrir_seccion_policial(base, permitir_navegador=USAR_NAVEGADOR)
        notas_sec = []
        if sec:
            r["seccion_policial"] = sec["url"]
            r["seccion_rss"] = sec["rss"]
            notas_sec = fetch.listar_notas(sec["url"], sec["rss"], LIMITE_NOTAS,
                                          permitir_navegador=USAR_NAVEGADOR)

        # 2) Feed general: sirve igual para medir ritmo de publicacion y como
        #    respaldo cuando no hay seccion.
        rss = fetch.descubrir_rss(base)
        r["rss"] = rss
        notas_gen = fetch.listar_notas(base, rss, LIMITE_NOTAS,
                                      permitir_navegador=USAR_NAVEGADOR)

        # La fuente que se va a usar de verdad es la seccion si trae material.
        usar_seccion = len(notas_sec) >= 3
        notas = notas_sec if usar_seccion else notas_gen
        if not notas:
            r["error"] = "sin notas detectadas"
            return r

        r["metodo"] = ("seccion-" + notas[0]["metodo"]) if usar_seccion else notas[0]["metodo"]
        r["n_notas"] = len(notas)

        pol = _analizar(notas)
        r["n_policiales"] = len(pol)
        r["pct_policial"] = round(len(pol) / len(notas) * 100, 1)
        r["ejemplos"] = [t for _, t in sorted(pol, reverse=True)[:3]]

        dias = _dias_cubiertos(notas)
        r["dias"] = round(dias, 1) if dias else None
        if dias:
            r["notas_dia"] = round(len(notas) / dias, 1)
            r["flujo_policial_dia"] = round(len(pol) / dias, 2)
        else:
            # Sin fechas (tipico del raspado HTML) no se puede anualizar la tasa:
            # dejamos el conteo crudo en vez de inventar un promedio que no medimos.
            r["flujo_policial_dia"] = None

        fechas = [n["publicado"] for n in notas if n.get("publicado")]
        r["ultima"] = max(fechas) if fechas else None
    except Exception as e:
        r["error"] = f"{type(e).__name__}: {e}"
    return r


def main():
    with open(os.path.join(RAIZ, "data", "candidatos.json"), encoding="utf-8") as f:
        cands = json.load(f)
    solo = None
    if "--solo" in sys.argv:
        solo = {x.strip().lower() for x in sys.argv[sys.argv.index("--solo") + 1].split(",")}
    tareas = [(loc, dom) for loc, doms in cands.items()
              if not loc.startswith("_") and (not solo or loc.lower() in solo)
              for dom in doms]
    print(f"Sondeando {len(tareas)} candidatos en {len(cands) - 1} localidades "
          f"con {HILOS} hilos...\n")

    t0, resultados = time.time(), []
    with ThreadPoolExecutor(max_workers=3 if USAR_NAVEGADOR else HILOS) as ex:
        futuros = {ex.submit(sondear, loc, dom): (loc, dom) for loc, dom in tareas}
        for i, fut in enumerate(as_completed(futuros), 1):
            loc, dom = futuros[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"localidad": loc, "dominio": dom, "vivo": False, "error": str(e)}
            resultados.append(res)
            marca = "SEC" if (res.get("metodo") or "").startswith("seccion") else \
                    ("x" if not res.get("vivo") else (res.get("metodo") or "?"))
            print(f"[{i:>3}/{len(tareas)}] {marca:<5} {dom[:34]:<34} "
                  f"notas={res.get('n_notas', 0):<3} pol={res.get('n_policiales', 0):<3} "
                  f"{res.get('error') or ''}")

    resultados.sort(key=lambda r: (r["localidad"], -(r.get("n_policiales") or 0),
                                   -(r.get("flujo_policial_dia") or 0)))
    nombre = "sondeo_repesca.json" if (USAR_NAVEGADOR or "--solo" in sys.argv) else "sondeo.json"
    salida = os.path.join(RAIZ, "data", nombre)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"generado": datetime.now(timezone.utc).isoformat(),
                   "resultados": resultados}, f, ensure_ascii=False, indent=2)
    con_notas = sum(1 for r in resultados if r.get("n_notas"))
    con_sec = sum(1 for r in resultados if r.get("seccion_policial"))
    print(f"\nListo en {time.time() - t0:.0f}s — {con_notas}/{len(tareas)} con notas, "
          f"{con_sec} con seccion de policiales")
    print(f"-> {salida}")


if __name__ == "__main__":
    main()
