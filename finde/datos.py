# -*- coding: utf-8 -*-
"""CONSULTA: los datos oficiales, con caché y la dirección exacta de cada archivo.

- INDEC, Censo Nacional de Población, Hogares y Viviendas 2022, resultados definitivos: los cuadros de la Provincia de
  Buenos Aires por partido (Excel en indec.gob.ar/ftp/cuadros/poblacion/, publicados en la página del Censo 2022:
  https://www.indec.gob.ar/indec/web/Nivel4-Tema-2-41-165). Dos formas: una hoja con todos los partidos (gas, tenencia,
  población, mayores de 65) o una hoja por partido (cloacas, agua, internet).
- ArgenFields (agro/datos/argenfields.json, la copia que ya usa agro): suelos, lluvias, rindes, emergencias.

La caché vive en salida_finde/cache (30 días): una corrida no vuelve a bajar lo que ya tiene. Si un archivo no baja,
el tema que lo necesita queda afuera (temas.py elige otro).
"""
from __future__ import annotations

import time
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salida_finde"
CACHE = SALIDA / "cache"
CACHE_DIAS = 30
UA = {"User-Agent": "Mozilla/5.0 (compatible; DiarioLaCampana-datos/1.0; +https://www.xn--diariolacampaa-2nb.com.ar)"}
BASE_INDEC = "https://www.indec.gob.ar/ftp/cuadros/poblacion/c2022_bsas_{}.xlsx"
PAGINA_CENSO = "https://www.indec.gob.ar/indec/web/Nivel4-Tema-2-41-165"
CENSO = "INDEC, Censo Nacional de Población, Hogares y Viviendas 2022 (resultados definitivos)"

# clave: (archivo, nombre del cuadro para citarlo)
CUADROS = {
    "gas": ("hogares_c4_2", "Cuadro 4.2. Total de hogares, por combustible utilizado principalmente para cocinar, "
                            "según partido. Año 2022"),
    "tenencia": ("hogares_c6_2", "Cuadro 6.2. Total de hogares, por régimen de tenencia y regularidad de la propiedad "
                                 "para la vivienda propia, según partido. Año 2022"),
    "poblacion": ("est_c1_2", "Cuadro 1.2. Total de población, variación absoluta y variación relativa, por partido. "
                              "Años 2010 y 2022"),
    "mayores": ("est_c7_2", "Cuadro 7.2. Porcentaje de población de 65 años y más, por partido. Censos 1970-2022"),
    "cloacas": ("hogares_c3_2", "Cuadro 3.2.N. Total de hogares, por ubicación del baño o letrina, según desagüe y "
                                "descarga de agua del inodoro, de cada partido. Año 2022"),
    "agua": ("hogares_c2_2", "Cuadro 2.2.N. Total de hogares, por provisión del agua, según procedencia del agua, de "
                             "cada partido. Año 2022"),
    "internet": ("hogares_c7_2", "Cuadro 7.2.N. Total de hogares, por tenencia de internet en la vivienda, según "
                                 "tenencia de celular con internet, de cada partido. Año 2022"),
}


def plano(t) -> str:
    """Sin tildes, sin espacios duros, en minúscula (para comparar textos del Excel)."""
    t = unicodedata.normalize("NFKD", str(t or "")).replace("\xa0", " ")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).lower().split())


def slug(nombre: str) -> str:
    return "-".join(plano(nombre).split())


def url_cuadro(clave: str) -> str:
    return BASE_INDEC.format(CUADROS[clave][0])


def bajar(clave: str, get=None, carpeta: Path = None, hoy: date = None) -> Path:
    """El Excel del cuadro (de la caché si tiene menos de CACHE_DIAS). Lanza si no baja."""
    carpeta = carpeta or CACHE
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{CUADROS[clave][0]}.xlsx"
    if destino.exists() and time.time() - destino.stat().st_mtime < CACHE_DIAS * 86400:
        return destino
    if get is None:
        import httpx                                 # el de requirements.txt (en la nube no hay `requests`)
        get = lambda u, **k: httpx.get(u, follow_redirects=True, **k)  # noqa: E731
    r = get(url_cuadro(clave), headers=UA, timeout=90)
    if r.status_code != 200:
        raise ValueError(f"{clave}: el INDEC respondió {r.status_code}")
    if not r.content.startswith(b"PK"):
        raise ValueError(f"{clave}: el INDEC no devolvió un Excel")
    destino.write_bytes(r.content)
    return destino


def _num(x):
    return x if isinstance(x, (int, float)) else None


def tabla_partidos(archivo: Path) -> dict:
    """Cuadro de una sola hoja con un partido por renglón: {slug: (nombre, [valores numéricos…])}."""
    salida = {}
    import openpyxl
    wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[2]]
        for r in ws.iter_rows(values_only=True):
            if not r or not isinstance(r[0], str) or not r[0].strip().startswith("06") or len(r[0].strip()) != 5:
                continue
            nombre = str(r[1] or "").replace("\xa0", " ").strip()
            salida[slug(nombre)] = (nombre, [c for c in r[2:]])
    finally:
        wb.close()
    return salida


def hojas_partidos(archivo: Path) -> dict:
    """Cuadros con una hoja por partido: {slug: (nombre, [renglones sin celdas vacías])}. El partido sale del título
    («Provincia de Buenos Aires, Partido Chivilcoy.»)."""
    salida = {}
    import openpyxl
    wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    try:
        for n in wb.sheetnames[3:]:
            filas = [[c for c in r if c not in (None, "")] for r in wb[n].iter_rows(values_only=True)]
            titulo = " ".join(str(c) for r in filas[:3] for c in r).replace("\xa0", " ")
            if "Partido " not in titulo:
                continue
            nombre = titulo.split("Partido ", 1)[1].split(".")[0].strip()
            salida[slug(nombre)] = (nombre, filas)
    finally:
        wb.close()
    return salida


def _renglon(filas: list, empieza: str):
    """El primer renglón que empieza con `empieza` y trae números (los encabezados también dicen «Total»)."""
    for r in filas:
        if r and plano(r[0]).startswith(plano(empieza)) and any(_num(x) is not None for x in r[1:]):
            return r
    return None


def censo(zona: list, get=None, carpeta: Path = None, log=print) -> dict:
    """Los indicadores del censo de los partidos de `zona` (slugs): {slug: {...}} y {"_fuentes": {clave: url}}.
    Lo que no baja o no se entiende queda sin cargar (el tema que lo usa no sale)."""
    datos = {s: {} for s in zona}
    fuentes = {}

    def poner(clave, fn):
        try:
            archivo = bajar(clave, get=get, carpeta=carpeta)
            n = fn(archivo)
            if n:
                fuentes[clave] = url_cuadro(clave)
            log(f"   INDEC {clave}: {n} partidos de la zona")
        except Exception as e:                       # noqa: BLE001 — un cuadro caído no tumba los demás
            log(f"   INDEC {clave}: no se pudo ({type(e).__name__}: {str(e)[:120]})")

    def gas(a):
        n = 0
        for s, (nombre, v) in tabla_partidos(a).items():
            if s in datos and _num(v[0]):
                datos[s].update(nombre=nombre.replace("25 De Mayo", "25 de Mayo"), hogares=v[0], cocina_electricidad=v[1],
                                gas_red=v[2], gas_tubo=v[3], garrafa=v[4], lena=v[5], cocina_otro=v[6])
                n += 1
        return n

    def tenencia(a):
        n = 0
        for s, (nombre, v) in tabla_partidos(a).items():
            if s in datos and _num(v[0]):
                datos[s].update(hogares_t=v[0], propia=v[1], escritura=v[2], alquilada=v[6], cedida=v[7],
                                prestada=v[8], otra_tenencia=v[9])
                n += 1
        return n

    def poblacion(a):
        n = 0
        for s, (nombre, v) in tabla_partidos(a).items():
            if s in datos and _num(v[0]) and _num(v[1]):
                datos[s].update(pob2010=v[0], pob2022=v[1], var_pob=v[3])
                n += 1
        return n

    def mayores(a):
        n = 0
        anios = (1970, 1980, 1991, 2001, 2010, 2022)
        for s, (nombre, v) in tabla_partidos(a).items():
            if s in datos:
                serie = {an: x for an, x in zip(anios, v) if _num(x) is not None}
                if 2022 in serie:
                    datos[s]["mayores65"] = serie
                    n += 1
        return n

    def por_hoja(clave, etiqueta, campo, col=0):
        def fn(a):
            n = 0
            for s, (nombre, filas) in hojas_partidos(a).items():
                if s not in datos:
                    continue
                total = _renglon(filas, "Total")
                fila = _renglon(filas, etiqueta)
                if not total or not fila:
                    continue
                valores = [x for x in fila[1:] if _num(x) is not None]
                if valores and _num(total[1]):
                    datos[s][f"hogares_{clave}"] = total[1]
                    datos[s][campo] = valores[col]
                    n += 1
            return n
        return fn

    def internet(a):
        n = 0
        for s, (nombre, filas) in hojas_partidos(a).items():
            total = _renglon(filas, "Total")
            if s in datos and total and _num(total[1]) and _num(total[2]):
                datos[s].update(hogares_internet=total[1], internet=total[2])
                n += 1
        return n

    poner("gas", gas)
    poner("tenencia", tenencia)
    poner("poblacion", poblacion)
    poner("mayores", mayores)
    poner("cloacas", por_hoja("cloacas", "A red publica (cloaca)", "cloaca"))
    poner("agua", por_hoja("agua", "Red publica (agua corriente)", "agua_red"))
    poner("internet", internet)
    datos["_fuentes"] = fuentes
    return datos


def argenfields() -> dict:
    from agro import reel_zona as RZ
    return RZ.datos_argenfields()


def zona() -> list:
    from agro import reel_pba as PBA
    return PBA.zona()
