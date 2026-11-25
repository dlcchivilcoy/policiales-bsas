# -*- coding: utf-8 -*-
"""LOS REELS CON DATOS OFICIALES DE LA PROVINCIA DE BUENOS AIRES, con Chivilcoy en el centro (25/11/2026).

Pedido del editor: «agregá para @diarioyradioagro datos oficiales de la provincia de Buenos Aires para hacer reels con
videos interactivos; usá la temática de las transferencias para el distrito de Chivilcoy; siempre quiero análisis de
datos con mapas teniendo a mi ciudad Chivilcoy como referencia central, y con eso armá notas; podés usar otras
temáticas económicas y también lo agroindustrial, empresas, pymes, comercios».

De dónde salen: el catálogo de datos abiertos de la Provincia (https://catalogo.datos.gba.gob.ar, API de CKAN). Cada
corrida busca en el catálogo el CSV vigente de cada base (los nombres de archivo cambian todos los meses) y se queda con
Chivilcoy y sus 9 partidos vecinos (los del mapa de agro/mapa_zona.py):

  - transferencias-municipios: lo que la Provincia gira cada mes a cada municipio, por concepto (coparticipación,
    Fondo Educativo, Fondo de Fortalecimiento…) y los tributos descentralizados (el Inmobiliario Rural y los Ingresos
    Brutos de los pequeños contribuyentes, que cobran los municipios). Se actualiza todos los meses.
  - poblacion: las proyecciones por partido (para el «por habitante»).
  - ganado: existencias de bovinos y porcinos por partido (una vez por año).
  - estimaciones-agro: producción de los cultivos por partido y campaña.

Las bases de empresas por sector y el PBG del catálogo son de toda la provincia (sin partidos): no hay mapa posible y
no se usan.

Temas (cada uno: mapa de la zona → ranking → el número de Chivilcoy → cierre, y un texto tipo nota):
  transferencias, transferencias_suba, coparticipacion, inmobiliario_rural, pequenos_contribuyentes, bovinos,
  porcinos, granos.
Un mes nuevo de transferencias sale primero; si no, el tema usado hace más tiempo (nunca antes de DIAS_SIN_REPETIR).

Dónde y cuándo: un reel por día en @diarioyradioagro (Instagram y Facebook, sin colab), en la grilla del día
(agro/agenda.py, GRILLA_DIA): 12:40, salvo martes y viernes (ese lugar es del perfil productivo, agro/perfil.py).
Interruptores: AGRO_PBA=0 lo apaga; AGRO_PBA_VENTANA («12:30-13:30»); AGRO_PBA_DIAS (días de la semana, 0 = lunes).
Memoria: estado/agro_pba.json. Workflow: .github/workflows/agro_pba.yml (cron-job.org a la hora; respaldo de GitHub).
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from agro import reel_zona as RZ

TZ_AR = RZ.TZ_AR
RAIZ = Path(__file__).resolve().parent.parent
MEMORIA = RAIZ / "estado" / "agro_pba.json"
CATALOGO = "https://catalogo.datos.gba.gob.ar/api/3/action/package_show"
DIAS_SIN_REPETIR = 10
ORDEN = ("transferencias", "inmobiliario_rural", "granos", "coparticipacion", "pequenos_contribuyentes", "bovinos",
         "transferencias_suba", "porcinos")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")
FUENTE_ECONOMIA = "Fuente: Ministerio de Economía de la Provincia de Buenos Aires (datos abiertos)"
FUENTE_PBA = "Fuente: Provincia de Buenos Aires, datos abiertos (catalogo.datos.gba.gob.ar)"
# (paquete del catálogo, palabras que tiene que tener el nombre del recurso CSV)
BASES = {
    "transferencias": ("transferencias-municipios", ("mensual", "transferencias")),
    "tributos": ("transferencias-municipios", ("mensual", "tributos")),
    "poblacion": ("poblacion", ("poblaci",)),
    "bovinos": ("ganado", ("bovino", "nueva serie")),
    "porcinos": ("ganado", ("porcino",)),
    "agricola": ("estimaciones-agro", ("estimaciones",)),
}
CULTIVOS_GRANOS = ("Soja total", "Maíz", "Trigo total", "Girasol", "Cebada total", "Sorgo")
# Los nombres cortos de los conceptos (las láminas y el texto).
CORTO = {"Coparticipación Bruta": "Coparticipación", "Fondo Financiamiento Educativo": "Fondo Educativo",
         "Fondo Fortalecimiento Recursos Municipales": "Fortalecimiento municipal",
         "Fondo Fortalecimiento Fiscal Municipal": "Fortalecimiento fiscal", "Juegos de Azar": "Juegos de azar",
         "Fondo Inclusión Social": "Inclusión social", "Fondo Fortalecimiento Programas Sociales": "Programas sociales",
         "Fondos Saneamiento Ambiental": "Saneamiento ambiental",
         "Descentralización Tributaria": "Descentralización tributaria"}
INMOBILIARIO = ("Inmobiliario Rural Libre Disponibilidad", "Inmobiliario Rural Fondo Compensador")
PEQUENOS = "Ingresos Brutos Pequeños Contribuyentes"


def _var(nombre: str, defecto: str) -> str:
    return (os.environ.get(nombre) or defecto).strip()


def activo() -> bool:
    return _var("AGRO_PBA", "1") != "0"


def dias() -> set:
    """Días de la semana (0 = lunes) en que sale. Martes y viernes no: a esa hora va el perfil productivo."""
    try:
        return {int(x) for x in _var("AGRO_PBA_DIAS", "0,2,3,5,6").split(",") if x.strip()}
    except ValueError:
        return {0, 2, 3, 5, 6}


def ventana(dia) -> tuple:
    txt = _var("AGRO_PBA_VENTANA", "12:30-13:30")
    try:
        a, b = [datetime.combine(dia, datetime.strptime(x.strip(), "%H:%M").time(), TZ_AR) for x in txt.split("-")]
        return a, b
    except ValueError:
        return (datetime.combine(dia, datetime.strptime("12:30", "%H:%M").time(), TZ_AR),
                datetime.combine(dia, datetime.strptime("13:30", "%H:%M").time(), TZ_AR))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Los datos
# ─────────────────────────────────────────────────────────────────────────────────────────────
def slug(nombre: str) -> str:
    """«San Andrés de Giles» → «san-andres-de-giles» (las claves del mapa de la zona)."""
    t = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode().lower().strip()
    return "-".join(t.split())


def zona() -> list:
    from agro import mapa_zona as MZ
    return list(MZ.poligonos().keys()) or ["chivilcoy"]


def _get(url: str, params: dict = None, timeout: int = 120):
    import requests
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (datos abiertos)"})
    r.raise_for_status()
    return r


def url_csv(paquete: str, palabras: tuple, get=None) -> str:
    """El CSV más nuevo del paquete cuyo nombre tiene todas las `palabras`."""
    get = get or _get
    res = get(CATALOGO, {"id": paquete}).json()["result"]["resources"]
    buenos = [r for r in res if (r.get("format") or "").upper() == "CSV"
              and all(p in (r.get("name") or "").lower() for p in palabras)]
    if not buenos:
        return ""
    buenos.sort(key=lambda r: r.get("last_modified") or r.get("created") or "")
    return buenos[-1]["url"]


def _filas(texto: str) -> list:
    return list(csv.DictReader(io.StringIO(texto.lstrip("﻿"))))


def _num(x) -> float:
    try:
        return float(str(x).strip() or 0)
    except ValueError:
        return 0.0


def leer(textos: dict) -> dict:
    """De los CSV (texto) a lo que usan los temas. Solo la zona, salvo los totales provinciales de coparticipación."""
    z = set(zona())
    d = {"nombres": {}, "transf": {}, "trib": {}, "copart_prov": {}, "copart": {}, "poblacion": {}, "bovinos": {},
         "porcinos": {}, "granos": {}}
    for r in _filas(textos.get("transferencias") or ""):
        s, anio, mes = slug(r.get("municipio_nombre")), int(_num(r.get("anio"))), int(_num(r.get("mes")))
        monto = _num(r.get("monto"))
        if r.get("concepto") == "Coparticipación Bruta":
            d["copart_prov"][anio] = d["copart_prov"].get(anio, 0) + monto
            if s in z:
                d["copart"].setdefault(s, {})[anio] = d["copart"].get(s, {}).get(anio, 0) + monto
        if s in z:
            d["nombres"][s] = r.get("municipio_nombre")
            c = d["transf"].setdefault((anio, mes), {}).setdefault(s, {})
            c[r["concepto"]] = c.get(r["concepto"], 0) + monto
    for r in _filas(textos.get("tributos") or ""):
        s = slug(r.get("nombre_municipio") or r.get("municipio_nombre"))
        if s in z:
            c = d["trib"].setdefault((int(_num(r.get("anio"))), int(_num(r.get("mes")))), {}).setdefault(s, {})
            c[r["concepto"]] = c.get(r["concepto"], 0) + _num(r.get("monto"))
    for r in _filas(textos.get("poblacion") or ""):
        s = slug(r.get("municipio_nombre"))
        if s in z:
            anios = sorted(k for k in r if k and k.isdigit() and _num(r[k]))
            if anios:
                d["poblacion"][s] = _num(r[anios[-1]])
    for clave in ("bovinos", "porcinos"):
        for r in _filas(textos.get(clave) or ""):
            s = slug(r.get("municipio_nombre"))
            if s in z and _num(r.get("stock")):
                d[clave].setdefault(s, {})[int(_num(r.get("anio")))] = _num(r.get("stock"))
    for r in _filas(textos.get("agricola") or ""):
        s = slug(r.get("municipio_nombre"))
        if s in z and r.get("cultivo") in CULTIVOS_GRANOS:
            g = d["granos"].setdefault(s, {}).setdefault(r["campania"], {})
            g[r["cultivo"]] = _num(r.get("produccion"))
    return d


def traer(get=None, log=print) -> dict:
    """Baja las bases del catálogo. Una base que no contesta deja sin sus temas, no frena a las demás."""
    get = get or _get
    textos = {}
    for clave, (paquete, palabras) in BASES.items():
        try:
            url = url_csv(paquete, palabras, get)
            if url:
                textos[clave] = get(url, timeout=180).content.decode("utf-8-sig", "replace")
        except Exception as e:                             # noqa: BLE001
            log(f"   datos de la Provincia ({clave}): {type(e).__name__}: {str(e)[:150]}")
    return leer(textos)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Cuentas
# ─────────────────────────────────────────────────────────────────────────────────────────────
def nombre(d: dict, s: str) -> str:
    return d["nombres"].get(s) or s.replace("-", " ").title()


def ultimo_mes(d: dict, clave: str = "transf", hoy=None) -> tuple | None:
    """El último (año, mes) con datos de Chivilcoy. Los meses del futuro no cuentan: la base de tributos trae
    noviembre y diciembre de «2027» (mal fechados, 25/11/2026)."""
    hoy = hoy or datetime.now(TZ_AR).date()
    meses = [k for k, v in d[clave].items() if sum((v.get("chivilcoy") or {}).values()) > 0
             and k <= (hoy.year, hoy.month)]
    return max(meses) if meses else None


def acumulado(d: dict, clave: str, anio: int, hasta_mes: int, conceptos=None) -> dict:
    """{slug: suma de enero a `hasta_mes`} (de los `conceptos`, o de todos)."""
    salida = {}
    for mes in range(1, hasta_mes + 1):
        for s, c in (d[clave].get((anio, mes)) or {}).items():
            salida[s] = salida.get(s, 0) + sum(v for k, v in c.items() if conceptos is None or k in conceptos)
    return salida


def area_ha(s: str) -> float:
    """La superficie del partido, en hectáreas, del contorno del mapa (proyección equirectangular)."""
    from agro import mapa_zona as MZ
    p = MZ.poligonos().get(s) or {}
    total = 0.0
    for anillo in p.get("anillos") or []:
        if len(anillo) < 3:
            continue
        lat0 = sum(y for _, y in anillo) / len(anillo)
        kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57
        pts = [(x * kx, y * ky) for x, y in anillo]
        total += abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
    return total * 100                                     # km² → ha


def ranking(d: dict, valores: dict) -> list:
    return sorted(((nombre(d, s), v) for s, v in valores.items() if v is not None), key=lambda f: -f[1])


def puesto(filas: list) -> int:
    return next((i + 1 for i, (n, _) in enumerate(filas) if n == "Chivilcoy"), 0)


def _millones(x: float) -> str:
    m = x / 1e6
    return RZ._coma(m, 0 if m >= 100 else 1) + " millones"


def _pesos(x: float) -> str:
    return "$" + RZ._coma(x, 0)


def _mes(anio: int, mes: int) -> str:
    return f"{MESES[mes - 1]} de {anio}"


def _promedio(valores: dict, sin: str = "") -> float:
    v = [x for k, x in valores.items() if k != sin and x]
    return sum(v) / len(v) if v else 0.0


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Los temas
# ─────────────────────────────────────────────────────────────────────────────────────────────
def tema_transferencias(d: dict) -> dict | None:
    um = ultimo_mes(d)
    if not um or not d["poblacion"]:
        return None
    anio, mes = um
    datos_mes = d["transf"][um]
    total = {s: sum(c.values()) for s, c in datos_mes.items()}
    por_hab = {s: total[s] / d["poblacion"][s] for s in total if d["poblacion"].get(s)}
    if len(por_hab) < 5 or "chivilcoy" not in por_hab:
        return None
    filas = ranking(d, por_hab)
    p = puesto(filas)
    chiv = datos_mes["chivilcoy"]
    comp = sorted(chiv.items(), key=lambda kv: -kv[1])
    tot = total["chivilcoy"] or 1
    gancho = "¿Cuánta plata le giró la Provincia a cada municipio de la zona?"
    prom = _promedio(por_hab, "chivilcoy")
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Pesos por habitante transferidos en {_mes(anio, mes)}",
                  "valores": por_hab, "dec": 0, "unidad": ""}),
        ("barras", {"titulo": "Transferencias por habitante", "sub": f"{_mes(anio, mes)} · en miles de pesos",
                    "filas": [(n, v / 1000) for n, v in filas], "dec": 1}),
        ("video", {"volanta": "CHIVILCOY", "numero": tot / 1e6, "dec": 0, "unidad": " millones",
                   "texto": f"recibió de la Provincia en {MESES[mes - 1]}: {_pesos(por_hab['chivilcoy'])} por "
                            f"habitante, puesto {p} de {len(filas)} en la zona.", "video": "campo"}),
        ("lista", {"titulo": "¿De dónde vino esa plata?", "sub": f"Chivilcoy, {_mes(anio, mes)}",
                   "filas": [(CORTO.get(k, k), f"{RZ._coma(100 * v / tot, 0 if v / tot >= .1 else 1)} %")
                             for k, v in comp[:6]]}),
        RZ._cierre("¿En qué se nota en tu ciudad? Contanos en los comentarios"),
    ]
    copa = chiv.get("Coparticipación Bruta", 0)
    texto = [f"🏛️ {gancho} En {_mes(anio, mes)}, la Provincia de Buenos Aires le transfirió a Chivilcoy "
             f"${_millones(tot)}: {_pesos(por_hab['chivilcoy'])} por habitante, puesto {p} de {len(filas)} entre los "
             f"partidos de la zona (el promedio de los vecinos fue {_pesos(prom)}).",
             f"La mayor parte es la coparticipación: ${_millones(copa)}, el {RZ._coma(100 * copa / tot, 0)} % del total. "
             f"Le siguen " + ", ".join(f"{CORTO.get(k, k).lower().replace('fondo educativo', 'el Fondo Educativo')} "
                                    f"(${_millones(v)})" for k, v in comp[1:4]) + ".",
             "Partido por partido, por habitante: " + ", ".join(f"{n} {_pesos(v)}" for n, v in filas) + ".",
             "📲 ¿En qué se nota esa plata en tu ciudad? Contanos en los comentarios."]
    return {"tema": "transferencias", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "fuente": FUENTE_ECONOMIA, "informe": f"{anio}-{mes:02d}",
            "hashtags": ["#Chivilcoy", "#Coparticipación", "#Municipios", "#ProvinciaDeBuenosAires"]}


def tema_transferencias_suba(d: dict) -> dict | None:
    um = ultimo_mes(d)
    if not um:
        return None
    anio, mes = um
    ahora_ = acumulado(d, "transf", anio, mes)
    antes = acumulado(d, "transf", anio - 1, mes)
    var = {s: 100 * (ahora_[s] / antes[s] - 1) for s in ahora_ if antes.get(s)}
    if len(var) < 5 or "chivilcoy" not in var:
        return None
    filas = ranking(d, var)
    p = puesto(filas)
    periodo = f"enero a {MESES[mes - 1]}" if mes > 1 else "enero"
    gancho = "¿A qué municipio de la zona le crecieron más los fondos de la Provincia?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Suba de las transferencias, {periodo} de {anio} contra {anio - 1}",
                  "valores": var, "dec": 0, "unidad": " %", "signo": True}),
        ("barras", {"titulo": "Suba de las transferencias", "sub": f"{periodo}, {anio} contra {anio - 1} · en %, "
                                                                 f"pesos corrientes", "filas": filas, "dec": 0,
                    "unidad": "%", "signo": True}),
        ("video", {"volanta": "CHIVILCOY", "numero": var["chivilcoy"], "dec": 0, "unidad": " %",
                   "texto": f"más que en {anio - 1}, de {periodo}: ${_millones(ahora_['chivilcoy'])} contra "
                            f"${_millones(antes['chivilcoy'])}. Puesto {p} de {len(filas)}.", "video": "campo"}),
        RZ._cierre("Guardalo y compartilo con alguien de tu ciudad"),
    ]
    texto = [f"📈 {gancho} De {periodo} de {anio}, Chivilcoy recibió de la Provincia ${_millones(ahora_['chivilcoy'])}, "
             f"un {RZ._coma(var['chivilcoy'], 0)} % más que en el mismo período de {anio - 1} "
             f"(${_millones(antes['chivilcoy'])}). Es el puesto {p} de {len(filas)} en la zona.",
             "Partido por partido: " + ", ".join(f"{n} {RZ._numero_txt(v, 0, True)} %" for n, v in filas) + ".",
             "Son pesos corrientes: la comparación sirve para ver a quién le creció más, no descuenta la inflación.",
             "📲 ¿Se nota en las obras y los servicios de tu ciudad? Contanos en los comentarios."]
    return {"tema": "transferencias_suba", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "fuente": FUENTE_ECONOMIA, "hashtags": ["#Chivilcoy", "#Municipios", "#ProvinciaDeBuenosAires"]}


def tema_coparticipacion(d: dict) -> dict | None:
    chiv = d["copart"].get("chivilcoy") or {}
    anios = sorted(a for a in chiv if d["copart_prov"].get(a))
    if len(anios) < 6:
        return None
    por_mil = {a: 1000 * chiv[a] / d["copart_prov"][a] for a in anios}
    ult = anios[-1]
    mapa = {s: 1000 * v[ult] / d["copart_prov"][ult] for s, v in d["copart"].items() if v.get(ult)}
    filas = ranking(d, mapa)
    serie = [(str(a), round(por_mil[a], 2)) for a in anios[-15:]]
    mejor = max(serie, key=lambda x: x[1])[0]
    peor = min(serie, key=lambda x: x[1])[0]
    desde = int(serie[0][0])
    gancho = "¿Cuánto le toca a Chivilcoy de cada $1.000 de coparticipación?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"De cada $1.000 coparticipados a los municipios, {ult}",
                  "valores": mapa, "dec": 2}),
        ("serie", {"titulo": "Chivilcoy, año por año", "sub": "pesos de cada $1.000 de coparticipación provincial",
                   "serie": serie, "mejor": mejor, "peor": peor}),
        ("video", {"volanta": "CHIVILCOY", "numero": por_mil[ult], "dec": 2, "unidad": " de $1.000",
                   "texto": f"de la coparticipación de los municipios bonaerenses fue para Chivilcoy en {ult} "
                            f"(en {desde}: {RZ._coma(por_mil[desde], 2)}).", "video": "campo"}),
        RZ._cierre("¿Sabías cómo se reparte? Contanos en los comentarios"),
    ]
    texto = [f"🏛️ {gancho} En {ult}, de cada $1.000 que la Provincia de Buenos Aires coparticipó a los municipios, "
             f"{RZ._coma(por_mil[ult], 2)} fueron para Chivilcoy; en {desde}, {RZ._coma(por_mil[desde], 2)}.",
             f"El año más alto de la serie fue {mejor} ({RZ._coma(por_mil[int(mejor)], 2)}) y el más bajo, {peor} "
             f"({RZ._coma(por_mil[int(peor)], 2)}). El reparto lo fija el coeficiente de cada municipio (población, "
             f"superficie, salud y otros indicadores).",
             "En la zona, de cada $1.000: " + ", ".join(f"{n} {RZ._coma(v, 2)}" for n, v in filas) + ".",
             "📲 ¿Sabías cómo se reparte la coparticipación? Contanos en los comentarios."]
    return {"tema": "coparticipacion", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "fuente": FUENTE_ECONOMIA, "hashtags": ["#Chivilcoy", "#Coparticipación", "#ProvinciaDeBuenosAires"]}


def tema_inmobiliario_rural(d: dict) -> dict | None:
    um = ultimo_mes(d, "trib")
    if not um:
        return None
    anio, mes = um
    tot = acumulado(d, "trib", anio, mes, INMOBILIARIO)
    tot = {s: v for s, v in tot.items() if v}
    por_ha = {s: v / area_ha(s) for s, v in tot.items() if area_ha(s)}
    if len(tot) < 5 or "chivilcoy" not in tot:
        return None
    filas_ha = ranking(d, por_ha)
    filas = ranking(d, {s: v / 1e6 for s, v in tot.items()})
    periodo = f"enero a {MESES[mes - 1]} de {anio}" if mes > 1 else f"enero de {anio}"
    gancho = "¿Cuánto recaudó cada municipio de la zona por el Inmobiliario Rural?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Millones de pesos, {periodo}",
                  "valores": {s: v / 1e6 for s, v in tot.items()}, "dec": 0}),
        ("barras", {"titulo": "Por hectárea del partido", "sub": f"pesos por hectárea · {periodo}",
                    "filas": filas_ha, "dec": 0}),
        ("video", {"volanta": "CHIVILCOY", "numero": tot["chivilcoy"] / 1e6, "dec": 0, "unidad": " millones",
                   "texto": f"por el Inmobiliario Rural de {periodo}: {_pesos(por_ha.get('chivilcoy', 0))} por hectárea "
                            f"del partido, puesto {puesto(filas_ha)} de {len(filas_ha)}.", "video": "campo"}),
        RZ._cierre("¿Cómo viene el impuesto en tu campo? Contanos en los comentarios"),
    ]
    texto = [f"🌾 {gancho} De {periodo}, Chivilcoy recaudó ${_millones(tot['chivilcoy'])} por el impuesto "
             f"Inmobiliario Rural que la Provincia descentralizó en los municipios (libre disponibilidad y fondo "
             f"compensador): puesto {puesto(filas)} de {len(filas)} en la zona.",
             f"Por hectárea del partido son {_pesos(por_ha.get('chivilcoy', 0))}. "
             "En la zona, por hectárea: " + ", ".join(f"{n} {_pesos(v)}" for n, v in filas_ha) + ".",
             "📲 ¿Cómo viene el impuesto en tu campo? Contanos en los comentarios."]
    return {"tema": "inmobiliario_rural", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "fuente": FUENTE_ECONOMIA, "hashtags": ["#Chivilcoy", "#InmobiliarioRural", "#Campo", "#Agro"]}


def tema_pequenos_contribuyentes(d: dict) -> dict | None:
    um = ultimo_mes(d, "trib")
    if not um or not d["poblacion"]:
        return None
    anio, mes = um
    tot = {s: v for s, v in acumulado(d, "trib", anio, mes, (PEQUENOS,)).items() if v}
    por_hab = {s: v / d["poblacion"][s] for s, v in tot.items() if d["poblacion"].get(s)}
    if len(por_hab) < 5 or "chivilcoy" not in por_hab:
        return None
    filas = ranking(d, por_hab)
    p = puesto(filas)
    periodo = f"enero a {MESES[mes - 1]} de {anio}" if mes > 1 else f"enero de {anio}"
    gancho = "Comercios y pymes: ¿dónde se mueve más la economía chica de la zona?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Pesos por habitante, {periodo}",
                  "valores": por_hab, "dec": 0}),
        ("barras", {"titulo": "Ingresos Brutos de los pequeños", "sub": f"pesos por habitante · {periodo}",
                    "filas": filas, "dec": 0}),
        ("video", {"volanta": "CHIVILCOY", "numero": tot["chivilcoy"] / 1e6, "dec": 1, "unidad": " millones",
                   "texto": f"pagaron los pequeños contribuyentes de Ingresos Brutos de {periodo}: "
                            f"{_pesos(por_hab['chivilcoy'])} por habitante, puesto {p} de {len(filas)}.",
                   "video": "campo"}),
        RZ._cierre("¿Tenés un comercio o una pyme? Contanos cómo viene"),
    ]
    texto = [f"🏪 {gancho} El régimen simplificado de Ingresos Brutos (comercios, emprendimientos y pymes chicas) lo "
             f"cobran los municipios. De {periodo}, en Chivilcoy fueron ${_millones(tot['chivilcoy'])}: "
             f"{_pesos(por_hab['chivilcoy'])} por habitante, puesto {p} de {len(filas)} en la zona.",
             "Partido por partido, por habitante: " + ", ".join(f"{n} {_pesos(v)}" for n, v in filas) + ".",
             "📲 ¿Tenés un comercio o una pyme? Contanos cómo viene el año en los comentarios."]
    return {"tema": "pequenos_contribuyentes", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "fuente": FUENTE_ECONOMIA, "hashtags": ["#Chivilcoy", "#Pymes", "#Comercio", "#Economía"]}


def _tema_stock(d: dict, clave: str, especie: str, emoji: str, video: str) -> dict | None:
    chiv = d[clave].get("chivilcoy") or {}
    if len(chiv) < 5:
        return None
    ult = max(chiv)
    mapa = {s: v[ult] for s, v in d[clave].items() if v.get(ult)}
    if len(mapa) < 5:
        return None
    filas = ranking(d, mapa)
    p = puesto(filas)
    serie_ = sorted(chiv.items())[-15:]
    en_miles = max(mapa.values()) >= 20000
    div, dec, uni = (1000, 0, " mil") if en_miles else (1, 0, "")
    serie = [(str(a), round(v / div, 1)) for a, v in serie_]
    mejor = max(serie, key=lambda x: x[1])[0]
    peor = min(serie, key=lambda x: x[1])[0]
    primero = serie_[0]
    cambio = 100 * (chiv[ult] / primero[1] - 1) if primero[1] else 0
    gancho = f"¿Dónde hay más {especie} en la zona?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Cabezas de {especie} por partido, {ult}" + (" (en miles)" if en_miles
                                                                                         else ""),
                  "valores": {s: v / div for s, v in mapa.items()}, "dec": dec}),
        ("serie", {"titulo": f"Los {especie} de Chivilcoy, año por año", "sub": "cabezas" + (" (miles)" if en_miles
                                                                                             else ""),
                   "serie": serie, "mejor": mejor, "peor": peor}),
        ("video", {"volanta": "CHIVILCOY", "numero": chiv[ult] / div, "dec": dec, "unidad": uni,
                   "texto": f"cabezas de {especie} en {ult}: puesto {p} de {len(filas)} en la zona; "
                            f"{RZ._numero_txt(cambio, 0, True)} % contra {primero[0]}.", "video": video}),
        RZ._cierre("¿Tenés hacienda? Contanos en los comentarios"),
    ]
    texto = [f"{emoji} {gancho} Chivilcoy tenía {RZ._coma(chiv[ult], 0)} cabezas de {especie} en {ult}: puesto {p} de "
             f"{len(filas)} entre los partidos de la zona, {RZ._numero_txt(cambio, 0, True)} % contra {primero[0]}.",
             f"El año con más fue {mejor} y el de menos, {peor}.",
             "Partido por partido: " + ", ".join(f"{n} {RZ._coma(v, 0)}" for n, v in filas) + ".",
             "📲 ¿Tenés hacienda? Contanos de qué partido sos en los comentarios."]
    return {"tema": clave, "gancho": gancho, "diapositivas": diap, "texto": texto, "fuente": FUENTE_PBA,
            "hashtags": ["#Chivilcoy", "#Ganadería", "#Campo", "#Agro"]}


def tema_bovinos(d: dict) -> dict | None:
    return _tema_stock(d, "bovinos", "vacunos", "🐄", "ganado")


def tema_porcinos(d: dict) -> dict | None:
    return _tema_stock(d, "porcinos", "cerdos", "🐖", "campo")


def _campana_completa(g: dict) -> bool:
    return bool(g.get("Soja total") and g.get("Maíz"))


def tema_granos(d: dict) -> dict | None:
    chiv = d["granos"].get("chivilcoy") or {}
    camps = sorted(c for c, g in chiv.items() if _campana_completa(g))
    if len(camps) < 6:
        return None
    ult = camps[-1]
    tot = {s: sum(g.get(ult, {}).values()) / 1000 for s, g in d["granos"].items() if _campana_completa(g.get(ult, {}))}
    if len(tot) < 5:
        return None
    filas = ranking(d, tot)
    serie = [(c, round(sum(chiv[c].values()) / 1000, 0)) for c in camps[-15:]]
    mejor = max(serie, key=lambda x: x[1])[0]
    peor = min(serie, key=lambda x: x[1])[0]
    comp = sorted(chiv[ult].items(), key=lambda kv: -kv[1])
    total_ult = sum(chiv[ult].values())
    gancho = "¿Qué partido de la zona produce más granos?"
    diap = [
        ("mapa", {"titulo": gancho, "sub": f"Miles de toneladas de granos, campaña {ult}", "valores": tot, "dec": 0}),
        ("serie", {"titulo": "Chivilcoy, campaña por campaña", "sub": "miles de toneladas de granos",
                   "serie": serie, "mejor": mejor, "peor": peor}),
        ("lista", {"titulo": f"¿Qué produjo Chivilcoy en la {ult}?", "sub": "toneladas",
                   "filas": [(k.replace(" total", ""), RZ._coma(v, 0)) for k, v in comp if v][:6]}),
        RZ._cierre("¿Cómo te fue en tu campo? Contanos en los comentarios"),
    ]
    texto = [f"🌾 {gancho} En la campaña {ult}, Chivilcoy produjo {RZ._coma(total_ult, 0)} toneladas de granos: puesto "
             f"{puesto(filas)} de {len(filas)} en la zona (sumando soja, maíz, trigo, girasol, cebada y sorgo).",
             "Lo que más: " + ", ".join(f"{k.replace(' total', '').lower()} {RZ._coma(v, 0)} t" for k, v in comp[:3])
             + f". La mejor campaña de la serie fue la {mejor} y la peor, la {peor}"
             + (" (la de la sequía)." if peor == "2022/23" else "."),
             "En la zona, miles de toneladas: " + ", ".join(f"{n} {RZ._coma(v, 0)}" for n, v in filas) + ".",
             "📲 ¿Cómo te fue en tu campo? Contanos en los comentarios."]
    return {"tema": "granos", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "fuente": "Fuente: Provincia de Buenos Aires, datos abiertos (estimaciones agrícolas)",
            "hashtags": ["#Chivilcoy", "#Granos", "#Cosecha", "#Campo", "#Agro"]}


TEMAS = {"transferencias": tema_transferencias, "transferencias_suba": tema_transferencias_suba,
         "coparticipacion": tema_coparticipacion, "inmobiliario_rural": tema_inmobiliario_rural,
         "pequenos_contribuyentes": tema_pequenos_contribuyentes, "bovinos": tema_bovinos,
         "porcinos": tema_porcinos, "granos": tema_granos}


def temas_disponibles(d: dict, log=print) -> dict:
    salida = {}
    for clave, fn in TEMAS.items():
        try:
            t = fn(d)
        except Exception as e:                             # noqa: BLE001 — un tema roto no frena a los demás
            log(f"   tema {clave}: {type(e).__name__}: {e}")
            t = None
        if t:
            salida[clave] = t
    return salida


def elegir_tema(mem: dict, disponibles: dict, hoy) -> str | None:
    """Un mes nuevo de transferencias va primero; si no, el tema usado hace más tiempo (no antes de 10 días)."""
    usos = RZ.ultimo_uso(mem)
    tr = disponibles.get("transferencias")
    informes = [r.get("informe") or "" for r in mem.get("reels") or [] if r.get("tema") == "transferencias"
                and r.get("publicado")]
    if tr and (max(informes) if informes else "") < tr.get("informe", ""):
        return "transferencias"
    limite = (hoy - timedelta(days=DIAS_SIN_REPETIR)).isoformat()
    libres = [t for t in ORDEN if t in disponibles and usos.get(t, "") < limite]
    if not libres:
        return None
    return min(libres, key=lambda t: (usos.get(t, ""), ORDEN.index(t)))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La corrida
# ─────────────────────────────────────────────────────────────────────────────────────────────
def pieza(tema: dict, reel: dict, texto: str, horario: datetime) -> dict:
    p = RZ.pieza(tema, reel, texto, horario)
    p["id"] = f"pba-{tema['tema']}-{horario:%Y%m%d%H%M}"
    p["rep"]["fuente"] = "Provincia de Buenos Aires"
    p["guion"]["volanta"] = "Datos de la Provincia"
    p["colab_diario"] = False
    return p


def publicar(p: dict, log=print, publicar_reel=None) -> dict:
    from agro import publicar as PUB
    PUB.esperar_margen(log=log)                           # 25/11/2026: que no caiga pegado a otro posteo
    publicar_reel = publicar_reel or PUB.publicar_reel
    return publicar_reel(p, None, ("facebook", "instagram"), log=log, portada_url=PUB._subir_portada(p))


def corrida(publicar_: bool, tema_pedido: str = "", ahora: datetime = None, ruta_mem: Path = None, datos: dict = None,
            log=print, publicador=None, videos_fn=None) -> dict:
    ahora = ahora or datetime.now(TZ_AR)
    hoy = ahora.date()
    dia = hoy.isoformat()
    mem = RZ.cargar(ruta_mem or MEMORIA)
    inf = {"cuando": ahora.isoformat(timespec="minutes"), "publicar": publicar_, "estado": ""}
    if not activo():
        inf["estado"] = "apagado"
        return inf
    if publicar_ and not tema_pedido:
        if hoy.weekday() not in dias():
            inf["estado"] = "otro_dia"
            log("Reel de la Provincia: hoy no sale (es el día del perfil productivo)")
            return inf
        desde, hasta = ventana(hoy)
        if not (desde <= ahora <= hasta):
            inf["estado"] = "fuera_de_hora"
            log(f"Reel de la Provincia: {ahora:%H:%M} está fuera de {desde:%H:%M}-{hasta:%H:%M}; no se hace nada")
            return inf
        if RZ.ya_hoy(mem, dia):
            inf["estado"] = "ya_salio"
            log("Reel de la Provincia: el de hoy ya salió")
            return inf
    d = datos if datos is not None else traer(log=log)
    disponibles = temas_disponibles(d, log)
    clave = tema_pedido or elegir_tema(mem, disponibles, hoy)
    inf["tema"] = clave
    log(f"Reel de la Provincia de {dia}: tema «{clave}» (temas con datos: {len(disponibles)})")
    tema = disponibles.get(clave) if clave else None
    if not tema:
        inf["estado"] = "sin_tema" if not clave else "sin_datos"
        return inf
    if publicar_:
        anotado = {"dia": dia, "tema": clave, "informe": tema.get("informe", ""),
                   "cuando": ahora.isoformat(timespec="minutes"), "publicado": None}
        mem.setdefault("reels", []).append(anotado)
        RZ.guardar(mem, ruta_mem or MEMORIA)
    carpeta = RZ.SALIDA / f"pba_{ahora:%Y-%m-%d_%H%M}_{clave}"
    carpeta.mkdir(parents=True, exist_ok=True)
    videos = (videos_fn or RZ.videos_para)(tema, mem, ahora, carpeta, log)
    reel = RZ.armar(tema, carpeta / f"pba_{clave}.mp4", videos)
    texto = RZ.caption(tema, videos)
    p = pieza(tema, reel, texto, ahora)
    (carpeta / "texto.txt").write_text(texto, encoding="utf-8")
    inf["reel"] = p["reel"]
    inf["texto"] = texto
    log(f"   reel: {reel['duracion']:.0f} s, {reel['peso_kb']} KB → {reel['archivo']}")
    if not publicar_:
        inf["estado"] = "simulado"
        return inf
    res = (publicador or publicar)(p, log=log)
    anotado["publicado"] = {k: v for k, v in res.items() if k != "portada_url"}
    ok = [r for r in ("instagram", "facebook") if isinstance(res.get(r), dict) and res[r].get("id")]
    anotado["redes"] = ok
    RZ.guardar(mem, ruta_mem or MEMORIA)
    inf["estado"] = "ok" if ok else "fallo"
    inf["resultado"] = res
    return inf


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--tema", default="")
    ap.add_argument("--todos", action="store_true", help="arma todos los temas (simulando)")
    a = ap.parse_args()
    if a.todos:
        ahora = datetime.now(TZ_AR)
        d = traer()
        for clave in temas_disponibles(d):
            inf = corrida(False, clave, ahora=ahora, datos=d, ruta_mem=RZ.SALIDA / "pba_memoria_simulada.json")
            print(RZ.informe(inf).replace("Reel de datos de la zona", "Reel de la Provincia"))
        return
    inf = corrida(a.publicar, a.tema)
    print(RZ.informe(inf).replace("Reel de datos de la zona", "Reel de la Provincia"))
    if a.publicar and inf.get("estado") == "fallo":
        sys.exit(1)


if __name__ == "__main__":
    main()
