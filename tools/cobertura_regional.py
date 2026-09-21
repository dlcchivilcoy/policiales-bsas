# -*- coding: utf-8 -*-
"""Mide que localidades cubre de verdad cada medio regional.

Ocho de las 28 localidades no tienen dos medios propios con policiales constantes.
Antes de tapar el hueco con un medio regional elegido por intuicion, lo medimos:
recorremos varias paginas de la seccion de policiales de cada regional y contamos
cuantas veces nombra a cada localidad en el titular.

Correr:  venv\\Scripts\\python.exe tools\\cobertura_regional.py
Salida:  data/cobertura_regional.json
"""
import sys, os, json, re, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import fetch
from scraper.keywords import puntuar, normalizar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Medios que en el sondeo mostraron alcance mas amplio que su propia ciudad.
REGIONALES = [
    "diariodemocracia.com", "diarionucleo.com", "presentenoticias.com",
    "noticiasruta5.com", "infociudad.com.ar", "abcsaladillo.com.ar",
    "latrochadigital.com.ar", "infocanuelas.com", "casaresonline.com.ar",
    "unoarrecifes.com", "lapostadelnoroeste.com.ar", "cadenanueve.com",
    "elregionaldigital.com.ar", "infoecos.com.ar", "arecociudad.com.ar",
    "bragadoesnoticia.com.ar", "junindigital.com", "laopinion.com.ar",
]

LOCALIDADES = [
    "Suipacha", "Mercedes", "Lujan", "25 de Mayo", "Saladillo", "Alberti", "Bragado",
    "Chacabuco", "Junin", "Lincoln", "9 de Julio", "Carlos Casares", "Trenque Lauquen",
    "Bolivar", "Pehuajo", "Carmen de Areco", "San Andres de Giles",
    "San Antonio de Areco", "Salto", "Arrecifes", "Pergamino", "Rojas", "Lobos",
    "Canuelas", "San Miguel del Monte", "Las Flores", "Navarro", "Roque Perez",
]

# Como nombran los medios a cada localidad. Hace falta porque "Monte" o "Salto"
# sueltos dan falsos positivos, y "Giles" o "Areco" aparecen abreviados.
ALIAS = {
    "Lujan": ["lujan"],
    "25 de Mayo": ["25 de mayo", "veinticinco de mayo"],
    "Junin": ["junin"],
    "9 de Julio": ["9 de julio", "nueve de julio"],
    "Carlos Casares": ["carlos casares", "casares"],
    "Trenque Lauquen": ["trenque lauquen", "trenque"],
    "Bolivar": ["bolivar"],
    "Pehuajo": ["pehuajo"],
    "Carmen de Areco": ["carmen de areco"],
    "San Andres de Giles": ["san andres de giles", "giles"],
    "San Antonio de Areco": ["san antonio de areco", "areco"],
    "Salto": ["salto"],
    "Canuelas": ["canuelas"],
    "San Miguel del Monte": ["san miguel del monte", "monte"],
    "Las Flores": ["las flores"],
    "Roque Perez": ["roque perez"],
    "Navarro": ["navarro"],
    "Suipacha": ["suipacha"],
    "Alberti": ["alberti"],
    "Arrecifes": ["arrecifes"],
}
PAGINAS = 4   # cuantas paginas de la seccion recorrer


def _alias(loc):
    return [normalizar(a) for a in ALIAS.get(loc, [loc])]


def _menciona(titulo_norm, alias):
    return any(re.search(rf"(?<![a-z0-9ñ]){re.escape(a)}(?![a-z0-9ñ])", titulo_norm)
               for a in alias)


def recorrer(dominio):
    """Junta titulares de la seccion de policiales, paginando."""
    base, err = fetch.resolver_base(dominio)
    if not base:
        return dominio, base, [], err
    sec = fetch.descubrir_seccion_policial(base, permitir_navegador=True)
    if not sec:
        return dominio, base, [], "sin seccion"

    titulos, vistos = [], set()
    for pag in range(1, PAGINAS + 1):
        if sec["rss"]:
            url = sec["rss"] if pag == 1 else f"{sec['rss'].rstrip('/')}?paged={pag}"
        else:
            url = sec["url"] if pag == 1 else f"{sec['url'].rstrip('/')}/page/{pag}/"
        try:
            notas = fetch.listar_notas(url, sec["rss"] if pag == 1 else None,
                                       limite=40, permitir_navegador=True)
        except Exception:
            break
        nuevos = [n["titulo"] for n in notas if n["titulo"] not in vistos]
        if not nuevos:
            break
        vistos.update(nuevos)
        titulos += nuevos
    return dominio, base, titulos, None


def main():
    print(f"Recorriendo la seccion de policiales de {len(REGIONALES)} medios "
          f"regionales ({PAGINAS} paginas c/u)...\n")
    salida = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futuros = {ex.submit(recorrer, d): d for d in REGIONALES}
        for fut in as_completed(futuros):
            dominio, base, titulos, err = fut.result()
            norm = [normalizar(t) for t in titulos]
            policiales = [t for t in titulos if puntuar(t)["probable"]]
            cobertura = {}
            for loc in LOCALIDADES:
                al = _alias(loc)
                n = sum(1 for t in norm if _menciona(t, al))
                if n:
                    cobertura[loc] = n
            salida[dominio] = {
                "base": base, "error": err, "titulares": len(titulos),
                "policiales": len(policiales),
                "cobertura": dict(sorted(cobertura.items(), key=lambda x: -x[1])),
            }
            top = ", ".join(f"{k}:{v}" for k, v in list(salida[dominio]["cobertura"].items())[:6])
            print(f"{dominio:<28} titulares={len(titulos):<4} pol={len(policiales):<4} {top or (err or '-')}")

    ruta = os.path.join(RAIZ, "data", "cobertura_regional.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\n-> {ruta}")


if __name__ == "__main__":
    main()
