# -*- coding: utf-8 -*-
"""Radio policial estricto de 100 km desde Chivilcoy (pedido del editor, 17/10/2026).

El PDF «Prompt integral Diarioyradio» fija dos reglas para policiales que prevalecen sobre lo
anterior: un radio ESTRICTO de 100 km en línea recta desde el centro de Chivilcoy y, dentro del
radio, primero Chivilcoy y después lo más cercano. Medido el 17/10: el 31 % de lo publicado
desde el 27/09 (138 de 440 piezas) era de más lejos — Pergamino, Bolívar, Las Flores, Cañuelas…

- Las coordenadas salen del catálogo `data/localidades_geo.json` (Georef/INDEC, se rehace con
  `tools/catalogo_localidades.py`), nunca de memoria.
- Cuenta el lugar del HECHO, no la sede del medio ni el domicilio de la víctima. Lo lee la IA del
  guion (`lugar_del_hecho`); antes del guion solo se descarta lo que con seguridad es lejano.
- Ubicación desconocida, ambigua (dos lugares homónimos lejos entre sí) o imprecisa cerca del
  límite → PENDIENTE: no entra en la selección automática.
- Otra provincia → fuera: la más cercana (CABA) está a 139,7 km (lo guarda el catálogo).
- No hay excepción por gravedad, popularidad ni urgencia.

Variables: POLICE_RADIUS_KM (100), POLICE_BANDA_CERCANA_KM (50).
"""
from __future__ import annotations

import json
import math
import os
import unicodedata
from functools import lru_cache
from pathlib import Path

from reels import ubicaciones as UB

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "data" / "localidades_geo.json"

# Dos asentamientos con el mismo nombre a más de esto entre sí son lugares DISTINTOS: sin el
# partido no se puede saber cuál es (en el catálogo hay 11 «San José» y 4 «La Unión»).
KM_HOMONIMOS = 15
# Si solo se sabe el PARTIDO (no la localidad), la cabecera no alcanza cerca del límite: un paraje
# del mismo partido puede quedar del otro lado. Con el partido solo, entra hasta RADIO - esto.
MARGEN_PARTIDO_KM = 20

# Clave del padrón (scraper/localidades.py, sin tildes) → (nombre en Georef, partido): la ciudad
# cabecera, sin ambigüedad. Las que no están acá se llaman igual que en Georef.
PADRON = {
    "general viamonte": ("Los Toldos", "General Viamonte"),
    "bolivar": ("San Carlos de Bolívar", "Bolívar"),
    "san miguel del monte": ("San Miguel del Monte", "Monte"),
    "florentino ameghino": ("Florentino Ameghino", "Florentino Ameghino"),
}

PROVINCIA_BA = {"buenos aires", "provincia de buenos aires", "pba", "bs as", "bs. as.", "bsas", ""}


def radio_km() -> float:
    try:
        return float(os.environ.get("POLICE_RADIUS_KM") or 100)
    except ValueError:
        return 100.0


def banda_cercana_km() -> float:
    try:
        return float(os.environ.get("POLICE_BANDA_CERCANA_KM") or 50)
    except ValueError:
        return 50.0


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.replace(",", " ").replace(".", " ").split())


def haversine(a, b) -> float:
    r = 6371.0088
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


@lru_cache(maxsize=1)
def catalogo() -> dict:
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    col = datos["columnas"]
    filas = [dict(zip(col, f)) for f in datos["asentamientos"]]
    por_nombre: dict = {}
    for f in filas:
        por_nombre.setdefault(_plano(f["nombre"]), []).append(f)
    datos["por_nombre"] = por_nombre
    return datos


def referencia() -> tuple:
    r = catalogo()["referencia"]
    return r["lat"], r["lon"]


def distancia_km(lat: float, lon: float) -> float:
    return round(haversine(referencia(), (lat, lon)), 1)


def _es_del_padron(clave: str) -> bool:
    from scraper.localidades import NOMBRES
    return clave in NOMBRES or clave == "chivilcoy"


def _lejos_entre_si(cands: list) -> bool:
    return any(haversine((a["lat"], a["lon"]), (b["lat"], b["lon"])) > KM_HOMONIMOS
               for i, a in enumerate(cands) for b in cands[i + 1:])


def _mejor(cands: list) -> dict:
    """Entre asentamientos homónimos y cercanos (la «Entidad» y la «Localidad simple» de la misma
    ciudad), la localidad."""
    orden = {"Localidad simple": 0, "Componente de localidad compuesta": 1, "Entidad": 2, "Paraje": 3}
    return min(cands, key=lambda c: orden.get(c["categoria"], 9))


def _lugar(fila: dict, precision: str, como: str) -> dict:
    return {"estado": "ok", "nombre": fila["nombre"], "partido": fila["partido"],
            "lat": fila["lat"], "lon": fila["lon"], "id_georef": fila["id_georef"],
            "distancia_km": fila["km_a_chivilcoy"], "precision": precision, "como": como}


def ubicar(localidad: str, partido: str = "", provincia: str = "") -> dict:
    """Dónde queda un lugar. `estado`: ok · otra_provincia · ambigua · desconocida."""
    prov = _plano(provincia)
    if prov not in PROVINCIA_BA and "buenos aires" not in prov:
        if "ciudad autonoma" in prov or prov in ("caba", "capital federal"):
            prov = "ciudad autonoma de buenos aires"
        km = {_plano(k): v["km"] for k, v in catalogo()["provincias_vecinas"].items()}.get(prov)
        return {"estado": "otra_provincia", "nombre": localidad, "provincia": provincia,
                "distancia_km": km, "precision": "provincia",
                "como": f"otra provincia ({provincia}): la más cercana a Chivilcoy, CABA, está a 139,7 km"}
    loc, part = _plano(localidad), _plano(partido)
    if not loc and not part:
        return {"estado": "desconocida", "como": "no se sabe dónde ocurrió"}
    por_nombre = catalogo()["por_nombre"]

    # Las localidades del padrón: su ciudad cabecera, con el alias de cómo la escribe la IA.
    clave = UB.clave(localidad) if loc else ""
    if clave and (clave in PADRON or clave in por_nombre):
        nombre, depto = PADRON.get(clave, (None, None))
        cands = por_nombre.get(_plano(nombre)) if nombre else por_nombre.get(clave)
        if not depto and _es_del_padron(clave):
            depto = clave            # «Las Flores» del padrón es la cabecera del partido Las Flores
        if cands and depto:
            cands = [c for c in cands if _plano(c["partido"]) == _plano(depto)] or cands
        if cands:
            if part:
                mismo = [c for c in cands if _plano(c["partido"]) == UB.clave(partido) or
                         _plano(c["partido"]) == part]
                cands = mismo or cands
            if _lejos_entre_si(cands):
                return {"estado": "ambigua", "nombre": localidad, "partido": partido,
                        "candidatos": [f"{c['nombre']} ({c['partido']}, {c['km_a_chivilcoy']} km)"
                                       for c in cands[:6]],
                        "como": f"hay {len(cands)} lugares llamados «{localidad}» en la provincia"}
            f = _mejor(cands)
            precision = "paraje" if f["categoria"] == "Paraje" else "localidad"
            return _lugar(f, precision, f"{precision} {f['nombre']} ({f['partido']})")
    if loc:
        return {"estado": "desconocida", "nombre": localidad, "partido": partido,
                "como": f"«{localidad}» no está en el catálogo de Georef de la provincia"}
    # Solo el partido: su cabecera, con el margen de imprecisión.
    cands = [c for c in por_nombre.get(UB.clave(partido)) or por_nombre.get(part) or []
             if _plano(c["partido"]) == part]
    if not cands:
        return {"estado": "desconocida", "partido": partido,
                "como": f"partido «{partido}» sin cabecera en el catálogo"}
    f = _mejor(cands)
    return _lugar(f, "partido", f"solo el partido {partido} (se mide su cabecera)")


def evaluar(lugar: dict) -> dict:
    """{elegible, estado, motivo, distancia_km, precision, banda, proximidad}.
    estado: elegible · fuera_de_radio · pendiente."""
    r = radio_km()
    base = {k: lugar.get(k) for k in ("nombre", "partido", "distancia_km", "precision", "como")}
    if lugar.get("estado") == "otra_provincia":
        return {**base, "elegible": False, "estado": "fuera_de_radio", "banda": "fuera", "proximidad": 0,
                "motivo": f"fuera del radio de {r:g} km: {lugar.get('como')}"}
    if lugar.get("estado") != "ok":
        return {**base, "elegible": False, "estado": "pendiente", "banda": "", "proximidad": 0,
                "motivo": f"pendiente, ubicación sin resolver: {lugar.get('como')}"
                          + (f" ({'; '.join(lugar['candidatos'])})" if lugar.get("candidatos") else "")}
    d = float(lugar["distancia_km"])
    if d > r:
        return {**base, "elegible": False, "estado": "fuera_de_radio", "banda": "fuera", "proximidad": 0,
                "motivo": f"fuera del radio: {lugar['nombre']} está a {d:g} km de Chivilcoy (máximo {r:g})"}
    if lugar.get("precision") == "partido" and d > r - MARGEN_PARTIDO_KM:
        return {**base, "elegible": False, "estado": "pendiente", "banda": "", "proximidad": 0,
                "motivo": f"pendiente: solo se sabe el partido ({lugar.get('partido')}) y su cabecera "
                          f"está a {d:g} km, demasiado cerca del límite de {r:g}"}
    return {**base, "elegible": True, "estado": "elegible", "banda": banda(d), "proximidad": proximidad(d),
            "motivo": f"{lugar['nombre']} a {d:g} km de Chivilcoy ({lugar.get('como')})"}


def banda(d: float) -> str:
    """Bandas de PRIORIDAD (no cuotas): chivilcoy · cercana (≤ 50 km) · zona (≤ radio) · fuera."""
    if d is None:
        return ""
    if d < 5:
        return "chivilcoy"
    if d <= banda_cercana_km():
        return "cercana"
    return "zona" if d <= radio_km() else "fuera"


def proximidad(d: float) -> int:
    """proximity_score 0-100: 100 en Chivilcoy, 0 en el borde del radio."""
    if d is None:
        return 0
    return max(0, round(100 * (1 - float(d) / radio_km())))


def de_localidad(localidad: str) -> dict:
    """Evaluación de una localidad del padrón o del catálogo, sin partido ni provincia."""
    return evaluar(ubicar(localidad))


def lugar_de_la_ia(lugar_ia: dict, material: str = "", localidad_medio: str = "") -> dict:
    """El lugar del hecho que leyó la IA, con controles: si dice «desconocida», si nombra un lugar
    que no aparece en la nota (y no es el pueblo del medio), queda pendiente."""
    lugar_ia = lugar_ia if isinstance(lugar_ia, dict) else {}
    loc = str(lugar_ia.get("localidad") or "").strip()
    part = str(lugar_ia.get("partido") or "").strip()
    prov = str(lugar_ia.get("provincia") or "").strip()
    certeza = _plano(str(lugar_ia.get("certeza") or ""))
    if certeza.startswith("descon") or (not loc and not part):
        return {"estado": "desconocida", "como": "la nota no dice dónde ocurrió el hecho",
                "segun": "ia", "certeza": certeza}
    plano = _plano(material)
    nombrado = any(x and _plano(x) in plano for x in (loc, part)) or \
        (loc and UB.clave(loc) == UB.clave(localidad_medio)) or \
        (loc and any(_plano(a) in plano for a, c in UB.ALIAS.items() if c == UB.clave(loc)))
    if not nombrado:
        return {"estado": "desconocida", "nombre": loc, "segun": "ia", "certeza": certeza,
                "como": f"la IA dijo «{loc}» pero ese lugar no aparece en la nota"}
    res = ubicar(loc, part, prov)
    res.update(segun="ia", certeza=certeza)
    return res


def prefiltro(nota: dict, localidad: str) -> dict | None:
    """Antes de gastar en guion y video: descarta SOLO lo que con seguridad es lejano. `localidad`
    es la que resolvió guion.localidad_de_la_nota (la nombrada en el titular o el arranque; si no,
    la del medio). Si es lejana pero la nota nombra alguna localidad del padrón dentro del radio, NO
    se descarta: el guion lee el lugar exacto. Devuelve la evaluación si se descarta, None si sigue."""
    ev = de_localidad(localidad)
    if ev["estado"] != "fuera_de_radio":
        return None
    texto = _plano(" ".join(str(nota.get(k) or "") for k in ("titulo", "resumen", "copete", "cuerpo"))[:3000])
    from scraper.localidades import NOMBRES
    for clave in NOMBRES:
        if f" {clave} " in f" {texto} " and de_localidad(clave)["elegible"]:
            return None
    return ev


def evaluar_pieza(pieza: dict) -> dict:
    """La evaluación al PUBLICAR: la que quedó en la pieza si tiene el lugar de la IA; si no (lotes
    viejos o guion por reglas), la localidad del hecho de la pieza."""
    lugar = pieza.get("lugar_hecho")
    if isinstance(lugar, dict) and lugar.get("estado"):
        if lugar.get("estado") == "ok":
            lugar = dict(lugar, distancia_km=distancia_km(lugar["lat"], lugar["lon"]))
        return evaluar(lugar)
    return de_localidad(pieza.get("localidad_hecho") or pieza.get("localidad") or "")
