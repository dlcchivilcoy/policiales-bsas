# -*- coding: utf-8 -*-
"""Trae de ArgenFields los datos de Chivilcoy y de sus partidos vecinos a agro/datos/argenfields.json (20/11/2026).

Los usan los reels de datos de la zona (agro/reel_zona.py). ArgenFields arma cada ficha con datos públicos (INTA,
Ministerio de Agricultura, NOAA, IGN) y pide citarla: «Fuente: ArgenFields, con datos del INTA y del Ministerio de
Agricultura». Son datos que cambian una vez por campaña (y El Niño, una vez por mes): se traen a mano, de vez en
cuando, con pausa entre página y página. La nube NO entra a ArgenFields: usa la copia del repo.

    venv\\Scripts\\python.exe tools\\traer_argenfields.py            # Chivilcoy + los vecinos de su ficha
    venv\\Scripts\\python.exe tools\\traer_argenfields.py --solo chivilcoy
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "agro" / "datos" / "argenfields.json"
BASE = "https://www.argenfields.com/zonas/buenos-aires/"
UA = "DiarioLaCampana-agro/1.0 (https://www.xn--diariolacampaa-2nb.com.ar)"
PAUSA = 3
CULTIVOS = ("Soja", "Trigo", "Maíz", "Cebada", "Girasol")


def _num(t: str) -> float | None:
    t = (t or "").strip().replace("−", "-").replace(".", "").replace(",", ".").replace("+", "")
    try:
        return float(t)
    except ValueError:
        return None


def _lineas(html: str) -> list:
    from bs4 import BeautifulSoup
    s = BeautifulSoup(html, "html.parser")
    main = s.find("main") or s
    return [x.strip() for x in main.get_text("\n", strip=True).split("\n") if x.strip()]


def _bloque(lin: list, desde: str, hasta: tuple) -> list:
    """Las líneas entre la que empieza con `desde` y la primera que empieza con alguna de `hasta`."""
    try:
        i = next(k for k, x in enumerate(lin) if x.startswith(desde))
    except StopIteration:
        return []
    salida = []
    for x in lin[i + 1:]:
        if any(x.startswith(h) for h in hasta):
            break
        salida.append(x)
    return salida


def _pares_pct(bloque: list) -> list:
    """[(nombre, %)] de una lista «nombre, 42%, nombre, 17%…»."""
    salida = []
    for a, b in zip(bloque, bloque[1:]):
        if re.fullmatch(r"-?[\d.,]+\s*%", b) and not re.fullmatch(r"-?[\d.,]+\s*%", a):
            salida.append((a, _num(b.rstrip("%"))))
    return salida


def _rindes(lin: list) -> dict:
    salida = {}
    for k, x in enumerate(lin):
        if x not in CULTIVOS or k + 3 >= len(lin) or "ha sembradas" not in lin[k + 1]:
            continue
        r = {"ha": _num(lin[k + 1].split(" ha")[0]), "promedio": _num(lin[k + 2])}
        # Hasta el próximo cultivo: «5% por encima del promedio…», «Mejor campaña…», la tabla.
        fin = next((j for j in range(k + 4, len(lin)) if lin[j] in CULTIVOS and j + 1 < len(lin)
                    and "ha sembradas" in lin[j + 1]), len(lin))
        tramo = lin[k + 3:fin]
        for t in tramo:
            m = re.match(r"(\d+)% por (encima|debajo) del promedio", t)
            if m:
                r["vs_provincia"] = int(m.group(1)) * (1 if m.group(2) == "encima" else -1)
            if t.startswith("En línea con el promedio"):
                r["vs_provincia"] = 0
            m = re.match(r"Buenos Aires, últimas cinco: ([\d.,]+)", t)
            if m:
                r["provincia"] = _num(m.group(1))
            m = re.match(r"Mejor campaña: (\S+) \(([\d.,]+) qq/ha\)\. Peor: (\S+) \(([\d.,]+) qq/ha\)", t)
            if m:
                r["mejor"] = [m.group(1), _num(m.group(2))]
                r["peor"] = [m.group(3), _num(m.group(4))]
        try:
            i = tramo.index("Sembrado (ha)")
            serie = []
            for j in range(i + 1, len(tramo) - 2, 3):
                if not re.fullmatch(r"\d{4}/\d{2}", tramo[j]):
                    break
                serie.append([tramo[j], _num(tramo[j + 1]), _num(tramo[j + 2])])
            r["serie"] = serie
        except ValueError:
            r["serie"] = []
        salida[x.lower().replace("í", "i")] = r
    return salida


def _enso(lin: list) -> dict:
    b = _bloque(lin, "El Niño y La Niña en", ("Relieve y clima",))
    if not b:
        return {}
    salida = {"texto": b[0]}
    m = re.search(r"Hoy hay (El Niño|La Niña|condiciones neutrales|neutral\w*)", b[0])
    salida["estado"] = m.group(1) if m else ""
    m = re.search(r"del (\d+ de \w+ de \d{4})", b[0])
    salida["aviso"] = m.group(1) if m else ""
    for t in b[1:4]:
        m = re.match(r"Último ONI \(([^)]+)\): ([+\-−]?[\d,]+) °C", t)
        if m:
            salida["oni"] = _num(m.group(2))
            salida["oni_tramo"] = m.group(1)
        m = re.search(r"quedó ([+\-−]?\d+) % contra su tendencia, y por debajo de ella en (\d+) de cada 10", t)
        if m:
            salida["soja_abajo_de_10"] = int(m.group(2))
    tabla = {}
    for k, x in enumerate(b):
        if x in CULTIVOS and k + 4 < len(b):
            tabla[x.lower().replace("í", "i")] = {"nino": _num(b[k + 1].rstrip("%").strip()),
                                                  "nino_n": _num(re.sub(r"\D", "", b[k + 2])),
                                                  "nina": _num(b[k + 3].rstrip("%").strip()),
                                                  "nina_n": _num(re.sub(r"\D", "", b[k + 4]))}
    salida["tabla"] = tabla
    return salida


def _emergencias(lin: list) -> dict:
    b = _bloque(lin, "Emergencias e inundaciones", ("InfoLEG", "Sus zonas gemelas"))
    if not b:
        return {}
    m = re.match(r"(\d+) emergencias?", b[0])
    lista, k = [], 1
    while k + 4 < len(b) + 1 and k < len(b):
        if k + 4 < len(b) + 1 and b[k + 1] == "–" and b[k + 3].startswith("Por "):
            lista.append({"desde": b[k], "hasta": b[k + 2], "motivo": b[k + 3][4:], "norma": b[k + 4]})
            k += 5
        else:
            k += 1
    return {"total": int(m.group(1)) if m else len(lista), "lista": lista}


def _gemelas(lin: list) -> list:
    b = _bloque(lin, "Sus zonas gemelas", ("Comparar ",))
    salida = []
    for k, x in enumerate(b):
        m = re.match(r"similitud (\d+)/100", x)
        if m and k >= 3:
            salida.append({"condado": b[k - 3], "estado": b[k - 1], "similitud": int(m.group(1))})
    return salida


def _vecinos(lin: list) -> list:
    b = _bloque(lin, "Partidos cercanos", ("Campos analizados", "Preguntas frecuentes"))
    if b[:4] != ["Partido", "Índice de productividad", "Lluvia (mm/año)", "Soja (qq/ha)"]:
        return []
    salida = []
    for k in range(4, len(b) - 3, 4):
        salida.append({"partido": b[k], "productividad": _num(b[k + 1]), "lluvia": _num(b[k + 2]),
                       "soja": _num(b[k + 3])})
    return salida


def parsear(html: str, slug: str) -> dict:
    lin = _lineas(html)
    texto = "\n".join(lin)
    d = {"slug": slug, "url": BASE + slug}
    m = re.search(r"Suelos, rindes y campos en (.+)", texto)
    d["partido"] = m.group(1).strip() if m else slug
    m = re.search(r"·\n([\d.]+) ha", texto)
    d["hectareas"] = _num(m.group(1)) if m else None
    m = re.search(r"El (\d+)% de la superficie relevada es de clase I a III", texto)
    d["clase_1_3"] = int(m.group(1)) if m else None
    m = re.search(r"Índice de productividad\n(\d+)\nsobre 100 · (\d+)º de (\d+) en la provincia", texto)
    if m:
        d["productividad"], d["puesto"], d["de"] = int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.search(r"promedio de Buenos Aires \((\d+)\)", texto)
    d["productividad_provincia"] = int(m.group(1)) if m else None
    m = re.search(r"Lluvia media\n([\d.]+)\nmm/año", texto)
    d["lluvia"] = _num(m.group(1)) if m else None
    m = re.search(r"Balance hídrico\n(-?[\d.]+)\nmm/año", texto)
    d["balance"] = _num(m.group(1)) if m else None
    m = re.search(r"se sembró el (\d+)% del partido", texto)
    d["sembrado"] = int(m.group(1)) if m else None
    d["clases"] = _pares_pct(_bloque(lin, "Capacidad de uso", ("Sobre la superficie",)))
    d["series"] = _pares_pct(_bloque(lin, "Series de suelo principales", ("Suelos dominantes",)))
    d["limitantes"] = _pares_pct(_bloque(lin, "Limitantes que declara la carta", ("Parte del partido",)))
    d["cultivos_hoy"] = _pares_pct(_bloque(lin, "Qué se siembra", ("Mapa Nacional",)))[:5]
    m = re.search(r"Franco limosa\n([\d,]+)%", texto)
    d["franco_limosa"] = _num(m.group(1)) if m else None
    m = re.search(r"Carbono orgánico\n(\d+)\s*t C/ha", texto)
    d["carbono"] = int(m.group(1)) if m else None
    m = re.search(r"Acopios de granos\n(\d+)\n(\d+) de más de ([\d.]+) t", texto)
    if m:
        d["acopios"], d["acopios_grandes"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"Altura sobre el mar\n(\d+)–(\d+)\nm; media (\d+) m", texto)
    if m:
        d["altura"] = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
    d["rindes"] = _rindes(lin)
    d["enso"] = _enso(lin)
    d["emergencias"] = _emergencias(lin)
    d["gemelas"] = _gemelas(lin)
    d["vecinos"] = _vecinos(lin)
    return d


def traer(slugs: list, get=None, log=print) -> dict:
    import httpx
    get = get or (lambda u: httpx.get(u, headers={"User-Agent": UA}, timeout=40, follow_redirects=True))
    salida = {}
    for i, slug in enumerate(slugs):
        if i:
            time.sleep(PAUSA)
        r = get(BASE + slug)
        if r.status_code != 200:
            log(f"{slug}: HTTP {r.status_code} (se deja la copia anterior)")
            continue
        salida[slug] = parsear(r.text, slug)
        d = salida[slug]
        log(f"{slug}: productividad {d.get('productividad')}, soja {(d['rindes'].get('soja') or {}).get('promedio')}, "
            f"{len(d['rindes'])} cultivos, {len(d['vecinos'])} vecinos")
    return salida


RINDES = DESTINO.with_name("rindes_zona.json")
CSV_RINDES = "https://www.argenfields.com/datos/argentina/rindes-{}.csv"
CULTIVOS_CSV = ("soja", "maiz", "trigo", "girasol", "cebada", "sorgo")


def traer_rindes(partidos: list, get=None, log=print) -> dict:
    """Los DATOS ABIERTOS de ArgenFields (CC BY 4.0, de las Estimaciones Agrícolas del Ministerio de Agricultura;
    https://www.argenfields.com/datos-abiertos): sembrado, cosechado, producción y rinde de cada campaña desde 1923,
    solo de los partidos de la zona. {slug: {cultivo: [[campaña, sembrada_ha, cosechada_ha, produccion_t, kg_ha]]}}."""
    import csv
    import io
    import httpx
    get = get or (lambda u: httpx.get(u, headers={"User-Agent": UA}, timeout=120, follow_redirects=True))
    quiero = {_sin_tildes(p).lower(): re.sub(r"[^a-z0-9]+", "-", _sin_tildes(p).lower()).strip("-") for p in partidos}
    salida = {}
    for i, cultivo in enumerate(CULTIVOS_CSV):
        if i:
            time.sleep(PAUSA)
        r = get(CSV_RINDES.format(cultivo))
        if r.status_code != 200:
            log(f"rindes de {cultivo}: HTTP {r.status_code}")
            continue
        n = 0
        for f in csv.DictReader(io.StringIO(r.text)):
            if f.get("provincia") != "Buenos Aires":
                continue
            slug = quiero.get(_sin_tildes(f.get("partido") or "").lower())
            if not slug:
                continue

            def num(k):
                try:
                    return float(f.get(k) or "")
                except ValueError:
                    return None
            salida.setdefault(slug, {}).setdefault(cultivo, []).append(
                [f["campania"], num("sembrada_ha"), num("cosechada_ha"), num("produccion_t"), num("rinde_kg_ha")])
            n += 1
        log(f"rindes de {cultivo}: {n} campañas de la zona")
    for cult in salida.values():
        for filas in cult.values():
            filas.sort(key=lambda x: x[0])
    return salida


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*")
    a = ap.parse_args()
    previo = json.loads(DESTINO.read_text(encoding="utf-8")) if DESTINO.exists() else {"partidos": {}}
    if a.solo:
        slugs = a.solo
    else:
        chiv = traer(["chivilcoy"])
        previo["partidos"].update(chiv)
        slugs = [re.sub(r"[^a-z0-9]+", "-", _sin_tildes(v["partido"]).lower()).strip("-")
                 for v in (chiv.get("chivilcoy") or {}).get("vecinos") or [] if v["partido"] != "Chivilcoy"]
    previo["partidos"].update(traer(slugs))
    previo["traido"] = datetime.now().strftime("%Y-%m-%d")
    previo["fuente"] = ("ArgenFields (www.argenfields.com), con datos del INTA, el Ministerio de Agricultura, "
                        "NOAA e IGN")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(previo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {DESTINO} ({len(previo['partidos'])} partidos)")
    if not a.solo:
        nombres = [v.get("partido") or s for s, v in previo["partidos"].items()]
        rindes = traer_rindes(nombres)
        if rindes:
            RINDES.write_text(json.dumps({"traido": previo["traido"], "licencia": "CC BY 4.0",
                                          "fuente": "ArgenFields, datos abiertos (https://www.argenfields.com/"
                                                    "datos-abiertos), con datos de Estimaciones Agrícolas del "
                                                    "Ministerio de Agricultura", "partidos": rindes},
                                         ensure_ascii=False, indent=0), encoding="utf-8")
            print(f"→ {RINDES} ({len(rindes)} partidos)")


def _sin_tildes(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


if __name__ == "__main__":
    main()
