# -*- coding: utf-8 -*-
"""Arma data/localidades_geo.json: el catálogo geográfico del filtro de 100 km (17/10/2026).

No es una lista de distancias de memoria: cada punto sale del Servicio de Normalización de Datos
Geográficos de Argentina (Georef, apis.datos.gob.ar), que publica los centroides del BAHRA/INDEC.
Se usa el recurso «asentamientos» y no «localidades» porque este último NO trae la ciudad de
Saladillo (sí sus localidades vecinas) y además suma los parajes rurales.

Guarda, para cada asentamiento de la provincia de Buenos Aires: nombre, partido, categoría,
coordenadas, id de Georef y la distancia en línea recta (Haversine) al centro de referencia de
Chivilcoy. Y la distancia mínima a cada provincia vecina, que justifica la regla «otra provincia =
fuera del radio».

Uso:  venv\\Scripts\\python.exe tools\\catalogo_localidades.py
"""
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "localidades_geo.json"
GEOREF = "https://apis.datos.gob.ar/georef/api"
FUENTE = "Georef (apis.datos.gob.ar/georef/api/asentamientos), BAHRA/INDEC"
# Provincias vecinas que podrían quedar cerca: CABA, Santa Fe, Entre Ríos, Córdoba, La Pampa.
VECINAS = {"02": "Ciudad Autónoma de Buenos Aires", "82": "Santa Fe", "30": "Entre Ríos",
           "14": "Córdoba", "42": "La Pampa"}


def haversine(a, b) -> float:
    r = 6371.0088
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def pedir(recurso: str, **params) -> dict:
    url = f"{GEOREF}/{recurso}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def main() -> int:
    ba = pedir("asentamientos", provincia="06", max=5000,
               campos="id,nombre,centroide,departamento.nombre,categoria")["asentamientos"]
    chiv = [a for a in ba if a["nombre"] == "Chivilcoy" and a["departamento"]["nombre"] == "Chivilcoy"
            and a["categoria"] == "Localidad simple"]
    if len(chiv) != 1:
        print(f"No se encontró UNA sola localidad Chivilcoy en Georef ({len(chiv)}): no se escribe nada.")
        return 1
    ref = (chiv[0]["centroide"]["lat"], chiv[0]["centroide"]["lon"])
    filas = []
    for a in ba:
        p = (a["centroide"]["lat"], a["centroide"]["lon"])
        filas.append([a["nombre"], a["departamento"]["nombre"], a["categoria"], round(p[0], 5),
                      round(p[1], 5), a["id"], round(haversine(ref, p), 1)])
    filas.sort(key=lambda f: f[6])
    vecinas = {}
    for cod, nombre in VECINAS.items():
        lista = pedir("asentamientos", provincia=cod, max=5000, campos="nombre,centroide")["asentamientos"]
        m = min(lista, key=lambda x: haversine(ref, (x["centroide"]["lat"], x["centroide"]["lon"])))
        vecinas[nombre] = {"mas_cercano": m["nombre"], "km": round(haversine(
            ref, (m["centroide"]["lat"], m["centroide"]["lon"])), 1)}
    datos = {
        "fuente": FUENTE,
        "consultado": date.today().isoformat(),
        "metodo": "Haversine (radio medio terrestre 6371,0088 km), línea recta, no por ruta",
        "referencia": {"nombre": "Chivilcoy", "id_georef": chiv[0]["id"], "lat": round(ref[0], 5),
                       "lon": round(ref[1], 5),
                       "que_es": "centroide de la localidad Chivilcoy (Georef): el centro de la ciudad"},
        "provincias_vecinas": vecinas,
        "columnas": ["nombre", "partido", "categoria", "lat", "lon", "id_georef", "km_a_chivilcoy"],
        "asentamientos": filas,
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("],[", "],\n["),
                      encoding="utf-8")
    print(f"{len(filas)} asentamientos bonaerenses; referencia {datos['referencia']}; vecinas {vecinas}")
    print(f"Escrito {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
