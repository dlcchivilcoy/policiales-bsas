# -*- coding: utf-8 -*-
"""Los DATOS del campo para las historias y el carrusel de los sábados (documento «ideas agro» del
editor, 17/10/2026): granos, dólar, Chicago, clima y alertas. Todo de fuentes públicas y sin IA.

Cada dato sale con su FECHA, su FUENTE, el MERCADO o lugar, la MONEDA y la UNIDAD (lo pide el
documento). Lo que no se pudo leer hoy se muestra como «último dato disponible» con la fecha que
tiene: nunca un dato viejo presentado como nuevo.

  granos  → Cámara Arbitral de Cereales de Rosario (precios de pizarra; «(E)» = estimativo)
  dólar   → BCRA, mayorista de referencia Com. A 3500 (API pública) y Banco Nación, billete y divisa
  Chicago → futuros de CBOT/CME (soja, maíz y trigo), el contrato más cercano, leído de Yahoo Finance
  clima   → SMN: pronóstico a 5 días por estación (datos abiertos) y alertas vigentes (CAP)

La memoria (`mem["mercado"]`) guarda cada dato por fecha: de ahí salen la variación contra la rueda
anterior y la comparación semanal.
"""
import io
import re
import zipfile
from datetime import date, datetime, timedelta, timezone
from html import unescape

import httpx

TZ_AR = timezone(timedelta(hours=-3))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0 Safari/537.36"}
DIAS_HISTORIA = 40

URL_CAC = "https://www.cac.bcr.com.ar/es/precios-de-pizarra"
URL_BNA = "https://www.bna.com.ar/Personas"
URL_A3500 = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/5"
URL_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
URL_SMN_PRON = "https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=pron5d"
URL_SMN_CAP = "https://ssl.smn.gob.ar/CAP/AR.php"

GRANOS = ("soja", "maiz", "trigo", "girasol", "sorgo")
NOMBRE = {"soja": "Soja", "maiz": "Maíz", "trigo": "Trigo", "girasol": "Girasol", "sorgo": "Sorgo"}

# Chicago: centavos de dólar por bushel → dólares por tonelada (bushels por tonelada de cada grano).
BUSHELS_T = {"soja": 36.7437, "maiz": 39.3683, "trigo": 36.7437}
CHICAGO = {"soja": ("ZS", "FHKNQUX"), "maiz": ("ZC", "HKNUZ"), "trigo": ("ZW", "HKNUZ")}
MESES_CME = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
MES_CORTO = ("", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

# Estaciones del pronóstico del SMN en la región pampeana (nombre del archivo → nombre, lat, lon).
# Las de ZONA son las más cercanas a Chivilcoy (el SMN no tiene estación en Chivilcoy).
ESTACIONES = {
    "NUEVE_DE_JULIO": ("9 de Julio", -35.45, -60.88), "JUNIN_AERO": ("Junín", -34.55, -60.93),
    "PEHUAJO_AERO": ("Pehuajó", -35.87, -61.90), "BOLIVAR_AERO": ("Bolívar", -36.19, -61.07),
    "LAS_FLORES_AERO": ("Las Flores", -36.05, -59.10), "EZEIZA_AERO": ("Ezeiza", -34.82, -58.53),
    "TRENQUE_LAUQUEN": ("Trenque Lauquen", -35.97, -62.73), "AZUL_AERO": ("Azul", -36.84, -59.88),
    "TANDIL_AERO": ("Tandil", -37.24, -59.23), "TRES_ARROYOS": ("Tres Arroyos", -38.33, -60.25),
    "CORONEL_SUAREZ_AERO": ("Cnel. Suárez", -37.45, -61.88), "BAHIA_BLANCA_AERO": ("Bahía Blanca", -38.73, -62.17),
    "DOLORES_AERO": ("Dolores", -36.35, -57.73), "ROSARIO_AERO": ("Rosario", -32.92, -60.78),
    "VENADO_TUERTO": ("Venado Tuerto", -33.67, -61.97), "MARCOS_JUAREZ_AERO": ("Marcos Juárez", -32.70, -62.15),
    "LABOULAYE_AERO": ("Laboulaye", -34.13, -63.37), "RIO_CUARTO_AERO": ("Río Cuarto", -33.08, -64.27),
    "GENERAL_PICO_AERO": ("General Pico", -35.70, -63.75), "SANTA_ROSA_AERO": ("Santa Rosa", -36.57, -64.27),
    "PARANA_AERO": ("Paraná", -31.78, -60.48), "RAFAELA_AERO": ("Rafaela", -31.28, -61.50),
}
ZONA = ("NUEVE_DE_JULIO", "JUNIN_AERO", "BOLIVAR_AERO", "LAS_FLORES_AERO", "PEHUAJO_AERO")
CHIVILCOY = (-34.90, -60.02)
# Puntos para saber si una alerta del SMN toca la zona: Chivilcoy y las estaciones de la zona.
PUNTOS_ZONA = [("Chivilcoy",) + CHIVILCOY] + [(ESTACIONES[e][0],) + ESTACIONES[e][1:] for e in ZONA]
NIVEL_ALERTA = {"Minor": "amarilla", "Moderate": "amarilla", "Severe": "naranja", "Extreme": "roja"}


def _cliente(get=None):
    return get or (lambda url, **kw: httpx.get(url, headers=UA, timeout=30, follow_redirects=True, **kw))


def ahora() -> datetime:
    return datetime.now(TZ_AR)


def numero(texto) -> float | None:
    """«$350.450,00» → 350450.0 · «1485,00» → 1485.0 · «1509.0000» → 1509.0 · «S/C» → None."""
    t = re.sub(r"[^\d.,-]", "", str(texto or ""))
    if not re.search(r"\d", t):
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def _plano(html: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html or "")).split())


def _fecha_dmy(t: str) -> str:
    d, m, a = t.split("/")
    return f"{int(a):04d}-{int(m):02d}-{int(d):02d}"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Granos: pizarra de Rosario
# ─────────────────────────────────────────────────────────────────────────────────────────────
def parsear_pizarra(html: str) -> dict | None:
    """{fecha, productos: {grano: {ars, usd, estimado, direccion}}, tc} o None."""
    m = re.search(r"Pizarra del d\S+\s+(\d{1,2}/\d{1,2}/\d{4})", _plano(html))
    if not m:
        return None
    productos = {}
    for bloque in re.findall(r'<div class="board board-(\w+)([^"]*)">(.*?)(?=<div class="board board-|</section|$)',
                             html, re.S):
        grano, clases, cuerpo = bloque
        grano = grano.lower()
        if grano not in GRANOS:
            continue
        precio = re.search(r'class="price[^"]*">(.*?)</div>', cuerpo, re.S)
        usd = re.search(r"US\$</strong>(.*?)</div>", cuerpo, re.S)
        ars_t, usd_t = _plano(precio.group(1)) if precio else "", _plano(usd.group(1)) if usd else ""
        estimado = "estimative" in clases or "(E)" in ars_t
        direccion = ("sube" if "arrow-up" in cuerpo else "baja" if "arrow-down" in cuerpo
                     else "igual" if re.search(r'direction[^>]*>\s*=', cuerpo) else "")
        ars = numero(ars_t.replace("(E)", "").replace("S/C", ""))
        if ars is None:
            continue
        productos[grano] = {"ars": ars, "usd": numero(usd_t.replace("(E)", "")), "estimado": estimado,
                            "direccion": direccion}
    if not productos:
        return None
    tc = re.search(r"Divisas Comprador\s+\d{1,2}/\d{1,2}/\d{4}:\s*\$\s*([\d.,]+)", _plano(html))
    return {"fecha": _fecha_dmy(m.group(1)), "productos": productos, "tc": numero(tc.group(1)) if tc else None,
            "fuente": "Cámara Arbitral de Cereales de Rosario", "mercado": "Rosario",
            "unidad": "por tonelada", "condicion": "pizarra: entrega inmediata, pago contado, zona Rosario"}


def pizarra(get=None) -> dict | None:
    try:
        r = _cliente(get)(URL_CAC)
        return parsear_pizarra(r.text) if r.status_code == 200 else None
    except httpx.HTTPError:
        return None


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Dólar: Banco Nación (billete y divisa) y BCRA (mayorista A 3500)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def parsear_bna(html: str) -> dict | None:
    t = _plano(html)
    filas = re.findall(r"(\d{1,2}/\d{1,2}/\d{4})\s+Compra\s+Venta\s+Dolar U\.S\.A\s+([\d.,]+)\s+([\d.,]+)", t)
    if not filas:
        return None
    hora = re.search(r"Hora Actualizaci\S+:\s*(\d{1,2}:\d{2})", t)
    salida = {"fuente": "Banco Nación", "hora": hora.group(1) if hora else ""}
    for nombre, (f, c, v) in zip(("billete", "divisa"), filas):
        salida[nombre] = {"fecha": _fecha_dmy(f), "compra": numero(c), "venta": numero(v)}
    return salida


def dolar(get=None, hoy: date = None) -> dict:
    """{bna: {...}|None, mayorista: {fecha, valor, serie: [(fecha, valor)…]}|None}."""
    get = _cliente(get)
    hoy = hoy or ahora().date()
    salida = {"bna": None, "mayorista": None}
    try:
        r = get(URL_BNA)
        if r.status_code == 200:
            salida["bna"] = parsear_bna(r.text)
    except httpx.HTTPError:
        pass
    for _ in range(2):                                   # la API del BCRA a veces tarda o corta: un reintento
        try:
            r = get(URL_A3500, params={"desde": (hoy - timedelta(days=14)).isoformat(), "hasta": hoy.isoformat()})
            if r.status_code == 200:
                serie = sorted(((d["fecha"], float(d["valor"])) for d in r.json()["results"][0]["detalle"]))
                if serie:
                    salida["mayorista"] = {"fecha": serie[-1][0], "valor": serie[-1][1], "serie": serie,
                                           "fuente": "BCRA (Com. A 3500)"}
                    break
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            continue
    return salida


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Chicago (CBOT): el contrato más cercano de soja, maíz y trigo
# ─────────────────────────────────────────────────────────────────────────────────────────────
def contrato(grano: str, hoy: date) -> tuple:
    """(símbolo de Yahoo, «nov-26»): el primer mes del ciclo del grano que todavía no venció (los
    contratos vencen el día hábil anterior al 15 del mes)."""
    raiz, ciclo = CHICAGO[grano]
    for k in range(0, 15):
        a = hoy.year + (hoy.month - 1 + k) // 12
        m = (hoy.month - 1 + k) % 12 + 1
        letra = next((l for l in ciclo if MESES_CME[l] == m), None)
        if not letra or date(a, m, 14) <= hoy:
            continue
        return f"{raiz}{letra}{a % 100:02d}.CBT", f"{MES_CORTO[m]}-{a % 100:02d}"
    return f"{raiz}=F", "más cercano"


def chicago(get=None, hoy: date = None) -> dict:
    """{grano: {contrato, cent_bu, usd_t, cambio_pct, fecha, serie: [(fecha, usd_t)…]}} (vacío si no hay)."""
    get = _cliente(get)
    hoy = hoy or ahora().date()
    salida = {}
    for grano in CHICAGO:
        simbolo, nombre = contrato(grano, hoy)
        for s, n in ((simbolo, nombre), (f"{CHICAGO[grano][0]}=F", "")):
            try:
                r = get(URL_YAHOO.format(simbolo=s), params={"range": "1mo", "interval": "1d"})
                res = r.json()["chart"]["result"][0]
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
                continue
            meta = res.get("meta") or {}
            cierres = (res.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
            serie = [(datetime.fromtimestamp(t, TZ_AR).date().isoformat(), c)
                     for t, c in zip(res.get("timestamp") or [], cierres) if c]
            precio = meta.get("regularMarketPrice") or (serie[-1][1] if serie else None)
            if not precio:
                continue
            previo = serie[-2][1] if len(serie) > 1 else meta.get("chartPreviousClose")
            if not n:                                       # el continuo: el contrato sale de su nombre
                mm = re.search(r"(\w{3})-(\d{2,4})", meta.get("shortName") or "")
                n = f"{mm.group(1).lower()}-{mm.group(2)[-2:]}" if mm else "más cercano"
            k = BUSHELS_T[grano] / 100
            fecha = datetime.fromtimestamp(meta.get("regularMarketTime") or 0, TZ_AR).date().isoformat() \
                if meta.get("regularMarketTime") else (serie[-1][0] if serie else hoy.isoformat())
            salida[grano] = {"contrato": n, "cent_bu": round(precio, 2), "usd_t": round(precio * k, 1),
                             "cambio_pct": round((precio / previo - 1) * 100, 2) if previo else None,
                             "fecha": fecha, "serie": [(f, round(c * k, 1)) for f, c in serie],
                             "fuente": "CBOT/CME (vía Yahoo Finance)"}
            break
    return salida


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Clima: pronóstico del SMN por estación y alertas vigentes
# ─────────────────────────────────────────────────────────────────────────────────────────────
MESES_SMN = {m: i for i, m in enumerate(("ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT",
                                          "NOV", "DIC"), 1)}


def parsear_pronostico(texto: str) -> dict:
    """{ESTACION: [(datetime, temp, viento_kmh, mm)…]} del .txt del SMN (cada 3 horas)."""
    salida, actual = {}, None
    for linea in texto.splitlines():
        s = linea.strip()
        m = re.match(r"(\d{2})/([A-Z]{3})/(\d{4})\s+(\d{2})Hs\.\s+(-?[\d.]+)\s+\d+\s*\|\s*(\d+)\s+([\d.]+)", s)
        if m and actual:
            d, mes, a, h, temp, viento, mm = m.groups()
            try:
                cuando = datetime(int(a), MESES_SMN[mes], int(d), int(h), tzinfo=TZ_AR)
            except (KeyError, ValueError):
                continue
            salida[actual].append((cuando, float(temp), int(viento), float(mm)))
        elif re.fullmatch(r"[A-Z_]{4,40}", s):
            actual = s
            salida.setdefault(actual, [])
    return {k: v for k, v in salida.items() if v}


def por_dia(filas: list) -> dict:
    """{fecha: {max, min, mm, viento}} de las filas de una estación."""
    dias = {}
    for cuando, temp, viento, mm in filas:
        d = dias.setdefault(cuando.date().isoformat(), {"max": temp, "min": temp, "mm": 0.0, "viento": viento})
        d["max"], d["min"] = max(d["max"], temp), min(d["min"], temp)
        d["mm"] = round(d["mm"] + mm, 1)
        d["viento"] = max(d["viento"], viento)
    return dias


def pronostico(get=None) -> dict:
    """{ESTACION: {fecha: {...}}} de las estaciones de ESTACIONES (vacío si el SMN no contestó)."""
    try:
        r = _cliente(get)(URL_SMN_PRON)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        texto = z.read(z.namelist()[0]).decode("latin-1")
    except (httpx.HTTPError, zipfile.BadZipFile, IndexError, KeyError):
        return {}
    todo = parsear_pronostico(texto)
    return {e: por_dia(todo[e]) for e in ESTACIONES if e in todo}


def _dentro(lat: float, lon: float, poligono: list) -> bool:
    adentro, j = False, len(poligono) - 1
    for i, (yi, xi) in enumerate(poligono):
        yj, xj = poligono[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            adentro = not adentro
        j = i
    return adentro


def parsear_cap(xml: str) -> dict | None:
    """Una alerta CAP del SMN: {evento, nivel, desde, hasta, descripcion, poligonos}."""
    def campo(n):
        m = re.search(rf"<{n}>(.*?)</{n}>", xml, re.S)
        return unescape(m.group(1)).strip() if m else ""
    polis = []
    for p in re.findall(r"<polygon>(.*?)</polygon>", xml, re.S):
        try:
            polis.append([tuple(float(x) for x in par.split(",")) for par in p.split()])
        except ValueError:
            continue
    if not campo("event"):
        return None
    return {"evento": campo("event"), "nivel": NIVEL_ALERTA.get(campo("severity"), "amarilla"),
            "desde": campo("onset"), "hasta": campo("expires"), "descripcion": campo("description"),
            "poligonos": polis}


def alertas(get=None, momento: datetime = None) -> list:
    """Las alertas vigentes del SMN que tocan la ZONA: [{evento, nivel, desde, hasta, lugares}]."""
    get = _cliente(get)
    momento = momento or ahora()
    try:
        h = get(URL_SMN_CAP).text
    except httpx.HTTPError:
        return []
    vistas, salida = set(), []
    for url in dict.fromkeys(re.findall(r'href="(https://ssl\.smn\.gob\.ar/feeds/CAP/[^"]+\.xml)"', h)):
        try:
            a = parsear_cap(get(url).text)
        except httpx.HTTPError:
            continue
        if not a:
            continue
        try:
            if a["hasta"] and datetime.fromisoformat(a["hasta"]) < momento:
                continue
        except ValueError:
            pass
        lugares = [n for n, lat, lon in PUNTOS_ZONA if any(_dentro(lat, lon, p) for p in a["poligonos"])]
        clave = (a["evento"], a["nivel"], a["desde"])
        if lugares and clave not in vistas:
            vistas.add(clave)
            salida.append(dict({k: v for k, v in a.items() if k != "poligonos"}, lugares=lugares))
    orden = {"roja": 0, "naranja": 1, "amarilla": 2}
    return sorted(salida, key=lambda a: orden.get(a["nivel"], 3))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Memoria: cada dato por fecha, para la variación y la semana
# ─────────────────────────────────────────────────────────────────────────────────────────────
def anotar(mem: dict, clave: str, fecha: str, valor: dict, hoy: date = None):
    serie = mem.setdefault("mercado", {}).setdefault(clave, {})
    serie[fecha] = valor
    limite = ((hoy or ahora().date()) - timedelta(days=DIAS_HISTORIA)).isoformat()
    for f in [f for f in serie if f < limite]:
        del serie[f]


def anterior(mem: dict, clave: str, fecha: str, dias: int = 0):
    """(fecha, valor) del dato guardado más reciente ANTES de `fecha` (con `dias`: el más reciente
    de hace al menos esos días). None si no hay."""
    serie = (mem.get("mercado") or {}).get(clave) or {}
    tope = (date.fromisoformat(fecha) - timedelta(days=dias)).isoformat() if dias else fecha
    previas = sorted(f for f in serie if (f <= tope if dias else f < tope))
    return (previas[-1], serie[previas[-1]]) if previas else None


def variacion(actual, previo) -> float | None:
    try:
        return round((float(actual) / float(previo) - 1) * 100, 2) if previo else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def fecha_corta(fecha: str) -> str:
    try:
        d = date.fromisoformat(fecha)
    except (TypeError, ValueError):
        return fecha or ""
    return f"{d.day:02d}/{d.month:02d}"


def es_de_hoy(fecha: str, hoy: date = None) -> bool:
    return fecha == (hoy or ahora().date()).isoformat()


def leer_todo(mem: dict, get=None, momento: datetime = None, log=print) -> dict:
    """Lee todas las fuentes, anota lo que llegó en la memoria y devuelve lo de hoy (o el último
    dato disponible de cada cosa, de la memoria)."""
    momento = momento or ahora()
    hoy = momento.date()
    datos = {"momento": momento.isoformat(timespec="minutes")}
    p = pizarra(get)
    if p:
        anotar(mem, "pizarra", p["fecha"], p, hoy)
    datos["pizarra"] = p or _ultimo(mem, "pizarra")
    d = dolar(get, hoy)
    if d.get("bna"):
        anotar(mem, "bna", d["bna"]["billete"]["fecha"], d["bna"], hoy)
    if d.get("mayorista"):
        for f, v in d["mayorista"]["serie"]:
            anotar(mem, "a3500", f, {"fecha": f, "valor": v}, hoy)
    datos["bna"] = d.get("bna") or _ultimo(mem, "bna")
    datos["mayorista"] = d.get("mayorista") or _ultimo(mem, "a3500")
    c = chicago(get, hoy)
    for grano, v in c.items():
        for f, val in v.get("serie") or []:
            anotar(mem, f"chicago_{grano}", f, {"fecha": f, "usd_t": val}, hoy)
    datos["chicago"] = c
    datos["pronostico"] = pronostico(get)
    datos["alertas"] = alertas(get, momento)
    log(f"   datos: pizarra {(datos['pizarra'] or {}).get('fecha', '—')} · BNA "
        f"{((datos['bna'] or {}).get('billete') or {}).get('fecha', '—')} · A3500 "
        f"{(datos['mayorista'] or {}).get('fecha', '—')} · Chicago {len(c)} · SMN {len(datos['pronostico'])} "
        f"estaciones · alertas {len(datos['alertas'])}")
    return datos


def _ultimo(mem: dict, clave: str):
    serie = (mem.get("mercado") or {}).get(clave) or {}
    return serie[max(serie)] if serie else None
