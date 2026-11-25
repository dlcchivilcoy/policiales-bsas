# -*- coding: utf-8 -*-
"""EL INFORME SEMANAL DE ESTIMACIONES AGRÍCOLAS DEL MAGyP, PARA LA ZONA (24/11/2026).

Pedido del editor: sumar el informe semanal del Ministerio de Agricultura al reel de datos de la zona. Sale los jueves
(https://www.magyp.gob.ar/sitio/areas/estimaciones/estimaciones/informes/, un PDF por semana) y trae, por DELEGACIÓN,
el avance de la siembra y de la cosecha de cada cultivo (seis semanas, en %) y el estado de los lotes (estadio,
estado general, humedad). Chivilcoy está en la delegación BRAGADO (junto con Bragado, 9 de Julio, Alberti y
Suipacha): de cada tabla se toma esa fila. robots.txt del sitio solo cierra una carpeta de madera.

El PDF se lee con pypdf. Los títulos de las tablas vienen al final de cada página («AVANCE DE LA SIEMBRA DE GIRASOL»,
«HUMEDAD Y ESTADO DE LOS CULTIVOS … GIRASOL»). AGRO_MAGYP=0 lo apaga.
"""
from __future__ import annotations

import io
import os
import re
from datetime import date, datetime
from urllib.parse import quote, urljoin

LISTADO = "https://www.magyp.gob.ar/sitio/areas/estimaciones/estimaciones/informes/"
DELEGACION = "Bragado"
FUENTE = "Fuente: Estimaciones Agrícolas del MAGyP, delegación Bragado (incluye Chivilcoy)"
CULTIVOS = {"GIRASOL": "girasol", "MAIZ": "maíz", "MAÍZ": "maíz", "SOJA": "soja", "SORGO": "sorgo", "MANI": "maní",
            "MANÍ": "maní", "TRIGO": "trigo", "CEBADA": "cebada", "ARROZ": "arroz", "ALGODON": "algodón",
            "ALGODÓN": "algodón", "COLZA": "colza", "GARBANZO": "garbanzo", "LINO": "lino", "AVENA": "avena"}
ESTADIOS = ("emergencia", "crecimiento", "floración", "llenado", "madurez")
ESTADOS = ("muy bueno", "bueno", "regular", "malo")
HUMEDAD = {"A": "adecuada", "R": "regular", "E": "con exceso", "I": "inundación", "PS": "principio de sequía",
           "S": "sequía"}
DIAS_VIGENTE = 10


def activo() -> bool:
    return (os.environ.get("AGRO_MAGYP") or "1").strip() != "0"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Dónde está el último informe
# ─────────────────────────────────────────────────────────────────────────────────────────────
INFORME = re.compile(r'href="([^"]*Informe\s*Semanal\s*al\s*(\d{2})_(\d{2})_(\d{4})\.pdf)"', re.I)


def ultimo(html: str) -> tuple:
    """(url, fecha) del informe semanal más nuevo de la página del listado, o (None, None)."""
    mejor = (None, None)
    for ruta, d, m, a in INFORME.findall(html or ""):
        try:
            f = date(int(a), int(m), int(d))
        except ValueError:
            continue
        if mejor[1] is None or f > mejor[1]:
            mejor = (urljoin(LISTADO, quote(ruta, safe="/:%_.-")), f)
    return mejor


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Lo de la delegación en cada página
# ─────────────────────────────────────────────────────────────────────────────────────────────
NUM = re.compile(r"^\d{1,3}(?:\.\d{3})+$|^\d+(?:,\d+)?$")


def _numeros(tokens: list) -> list:
    return [t for t in tokens if NUM.match(t)]


def _pct(t: str) -> float:
    return float(t.replace(".", "").replace(",", ".")) if "," in t else float(t)


def _cultivo_de(texto: str, patron: str) -> str:
    m = re.search(patron, texto, re.I)
    if not m:
        return ""
    return CULTIVOS.get(m.group(1).upper(), m.group(1).lower())


def leer_paginas(paginas: list) -> dict:
    """{"avance": [{cultivo, labor, sub, hectareas, pct, antes}], "estado": [{cultivo, estadio, estado, humedad}]}
    de las páginas (texto) del informe."""
    avance, estado = [], []
    for texto in paginas:
        texto = texto or ""
        m = re.search(r"AVANCE DE LA (SIEMBRA|COSECHA) DE ([A-ZÁÉÍÓÚÑ]+)", texto)
        if m:
            labor = m.group(1).lower()
            cultivo = CULTIVOS.get(m.group(2).upper(), m.group(2).lower())
            lineas = texto.splitlines()
            for k, lin in enumerate(lineas):
                tok = lin.split()
                if not tok or tok[0].lower() != DELEGACION.lower():
                    continue
                filas = [(tok[1:])]
                # Soja: «Bragado 1ª …» y en el renglón siguiente «2ª …».
                if len(tok) > 1 and tok[1] in ("1ª", "1°") and k + 1 < len(lineas):
                    filas.append(lineas[k + 1].split())
                for f in filas:
                    sub = f[0] if f and f[0] in ("1ª", "2ª", "1°", "2°") else ""
                    if labor == "cosecha" and len(f) > 1 and f[0] == "T." and f[1] == "pan":
                        sub, f = "pan", f[2:]
                    nums = _numeros(f[1:] if sub in ("1ª", "2ª", "1°", "2°") else f)
                    if not nums:
                        continue
                    ha = int(nums[0].replace(".", "")) if "," not in nums[0] else None   # la 1.ª columna: hectáreas
                    pcts = [_pct(x) for x in nums[1:7] if _pct(x) <= 100] if ha else []
                    avance.append({"cultivo": cultivo, "labor": labor, "sub": sub, "hectareas": ha,
                                   "pct": pcts[-1] if pcts else 0.0, "antes": pcts[-2] if len(pcts) > 1 else 0.0})
                break
            continue
        if "HUMEDAD Y ESTADO" in texto:
            cultivo = ""
            for nombre in CULTIVOS:
                if re.search(rf"(?m)^\s*{nombre}\s*$", texto):
                    cultivo = CULTIVOS[nombre]
                    break
            fila = re.search(rf"(?m)^\s*{DELEGACION.upper()}\s+(.+)$", texto)
            if not (cultivo and fila):
                continue
            tok = fila.group(1).split()
            vals = [0.0 if t == "-" else _pct(t) for t in tok[:9] if t == "-" or NUM.match(t)]
            if len(vals) < 9:
                continue
            hum = tok[9] if len(tok) > 9 else ""
            tope = max(vals[:5])
            estadio = " y ".join(ESTADIOS[i] for i in range(5) if tope and vals[i] == tope)
            est = ESTADOS[max(range(4), key=lambda i: vals[5 + i])] if any(vals[5:9]) else ""
            estado.append({"cultivo": cultivo, "estadio": estadio, "estado": est,
                           "humedad": " / ".join(HUMEDAD.get(h, h) for h in hum.split("/") if h)})
    return {"avance": avance, "estado": estado}


def leer_pdf(datos: bytes) -> dict:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(datos))
    return leer_paginas([(p.extract_text() or "") for p in r.pages])


def traer(get=None) -> dict | None:
    """{"fecha": "AAAA-MM-DD", "url", "avance", "estado"} del último informe, o None (apagado, sin red, sin datos)."""
    if not activo():
        return None
    if get is None:
        from scraper import fetch as FE
        get = FE.get
    r = get(LISTADO)
    url, fecha = ultimo(r.text)
    if not url:
        return None
    pdf = get(url)
    if pdf.status_code != 200 or not pdf.content[:5].startswith(b"%PDF"):
        return None
    datos = leer_pdf(pdf.content)
    if not datos["avance"] and not datos["estado"]:
        return None
    return dict(datos, fecha=fecha.isoformat(), url=url)


def vigente(info: dict | None, hoy) -> bool:
    if not info or not info.get("fecha"):
        return False
    return (hoy - datetime.strptime(info["fecha"], "%Y-%m-%d").date()).days <= DIAS_VIGENTE
