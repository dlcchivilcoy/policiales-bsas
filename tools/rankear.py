# -*- coding: utf-8 -*-
"""Ordena el sondeo y elige los 2 medios por localidad.

Criterio, en orden:
  1. Que tenga SECCION de policiales. Es lo que mas importa: garantiza volumen
     constante del tema y evita gastar IA filtrando notas de otra cosa.
  2. Cuantas notas policiales trae el listado (volumen real medido).
  3. Que el listado tenga fechas (permite descartar notas viejas al ingerir).
  4. Que sea RSS y no raspado HTML (mas estable en el tiempo).

Correr:  venv\\Scripts\\python.exe tools\\rankear.py
Salida:  data/ranking.json  +  tabla por consola
"""
import sys, os, json

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


MIN_POLICIALES = 2   # por debajo de esto el medio no sirve como fuente del tema


def _es_oficial(dominio):
    """Sitios de municipio: publican gestion, obras y actos, no policiales.
    Sirven de relleno estadistico pero no como fuente del tema, asi que los
    sacamos en vez de dejar que ocupen un puesto por falta de competencia."""
    d = dominio.lower()
    return d.endswith(".gob.ar") or d.endswith(".gov.ar")


def puntaje(r):
    if not r.get("n_notas") or _es_oficial(r["dominio"]):
        return -1

    pol = r.get("n_policiales") or 0
    # Un medio que no muestra notas policiales no sirve, tenga la seccion que tenga.
    if pol < MIN_POLICIALES:
        return 0

    p = 0.0
    # El bono por seccion se paga solo si la seccion DE VERDAD trae policiales.
    # Sin esta condicion, una seccion con 3 notas y 0 policiales le ganaba a un
    # medio con 20 notas reales (pasaba en 25 de Mayo).
    if r.get("seccion_policial"):
        p += 100
    p += pol * 6
    p += (r.get("pct_policial") or 0) * 0.5
    if r.get("ultima"):
        p += 15                      # el listado trae fechas
    if r.get("rss") or r.get("seccion_rss"):
        p += 10                      # RSS aguanta mejor los rediseños del sitio
    if (r.get("flujo_policial_dia") or 0) > 0:
        p += min(r["flujo_policial_dia"] * 4, 40)
    return round(p, 1)


def main():
    with open(os.path.join(RAIZ, "data", "sondeo.json"), encoding="utf-8") as f:
        datos = json.load(f)

    por_loc = {}
    for r in datos["resultados"]:
        r["puntaje"] = puntaje(r)
        por_loc.setdefault(r["localidad"], []).append(r)

    ranking, sin_cubrir = {}, []
    for loc, rs in sorted(por_loc.items()):
        rs.sort(key=lambda x: -x["puntaje"])
        elegidos, dominios = [], set()
        for r in rs:
            if r["puntaje"] <= 0 or r["dominio"] in dominios:
                continue
            dominios.add(r["dominio"])
            elegidos.append(r)
            if len(elegidos) == 2:
                break
        ranking[loc] = elegidos
        if len(elegidos) < 2:
            sin_cubrir.append((loc, len(elegidos)))

        print(f"\n=== {loc.upper()}")
        for i, r in enumerate(rs[:5]):
            mark = "**" if i < len(elegidos) and r in elegidos else "  "
            via = "SECCION" if r.get("seccion_policial") else (r.get("metodo") or "-")
            estado = r.get("error") or ""
            print(f" {mark} {r['dominio'][:32]:<32} pts={r['puntaje']:>6} "
                  f"via={via:<12} notas={r.get('n_notas', 0):<3} pol={r.get('n_policiales', 0):<3} "
                  f"{('%.1f/dia' % r['flujo_policial_dia']) if r.get('flujo_policial_dia') else '':<9} {estado}")

    salida = os.path.join(RAIZ, "data", "ranking.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(ranking, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 78)
    total = sum(len(v) for v in ranking.values())
    print(f"Elegidos {total} medios en {len(ranking)} localidades")
    if sin_cubrir:
        print("Localidades sin 2 medios utilizables:")
        for loc, n in sin_cubrir:
            print(f"   - {loc}: {n}")
    print(f"-> {salida}")


if __name__ == "__main__":
    main()
