# -*- coding: utf-8 -*-
"""EL MAPA DE LLUVIA con Chivilcoy en el centro (pedido del editor, 24/10/2026: «agregá el mapa de dónde va a
llover al posteo diario e incluí a Chivilcoy como centro del mapa»).

    python -m agro.mapa_lluvia --base       arma el fondo (partidos del IGN) una vez; va al repo
    python -m agro.mapa_lluvia              prueba: baja el pronóstico y deja la placa en salida_agro/

Un cuadrado de ~235 km de lado con Chivilcoy en el medio (CAJA). La lluvia es la ACUMULADA prevista para las
próximas HORAS (72) en una grilla de puntos (cada ~22 km) del pronóstico de MET Norway (el instituto
meteorológico noruego: modelo global ECMWF, gratis y con uso comercial permitido citando la fuente; el mismo
que usa el clima del diario). Entre los puntos se interpola y se pinta por franjas de milímetros.

El fondo (los partidos, del IGN vía georef) no cambia: se arma con --base y queda en agro/marca/.
Sobre la lluvia: los límites de los partidos, los anillos de 50 y 100 km y las ciudades de la zona.
"""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from agro import diseno as D

TZ_AR = timezone(timedelta(hours=-3))
CENTRO = (-34.897, -60.019)                    # Chivilcoy (georef)
MEDIO_LAT, MEDIO_LON = 1.05, 1.28              # ~117 km para cada lado (a esta latitud, un cuadrado)
CAJA = (CENTRO[1] - MEDIO_LON, CENTRO[1] + MEDIO_LON, CENTRO[0] - MEDIO_LAT, CENTRO[0] + MEDIO_LAT)
LADO = 900                                     # px del mapa
FONDO_PNG = D.MARCA / "mapa_chivilcoy_fondo.png"
LIMITES_PNG = D.MARCA / "mapa_chivilcoy_limites.png"
GEOJSON = "https://infra.datos.gob.ar/georef/departamentos.geojson"
URL_MET = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
UA = "DiarioLaCampana/1.0 https://www.xn--diariolacampaa-2nb.com.ar/clima"
NODOS = 11                                     # puntos por lado adentro de la caja (+1 de margen a cada lado)
HORAS = 72
KM_POR_GRADO = 111.32

# Las ciudades del mapa (cabeceras de partido y los pueblos de Chivilcoy), con su centroide de georef.
LOCALIDADES = (
    ("Bragado", -35.116, -60.490), ("9 de Julio", -35.444, -60.883), ("Suipacha", -34.769, -59.687),
    ("Mercedes", -34.651, -59.431), ("Alberti", -35.032, -60.280), ("Chacabuco", -34.642, -60.471),
    ("25 de Mayo", -35.434, -60.173), ("Navarro", -35.006, -59.278), ("Lobos", -35.185, -59.098),
    ("Junín", -34.594, -60.946), ("Luján", -34.567, -59.115), ("Saladillo", -35.640, -59.778),
    ("Carmen de Areco", -34.377, -59.823), ("S. A. de Giles", -34.442, -59.448), ("Salto", -34.292, -60.255),
    ("Los Toldos", -35.000, -61.039), ("Roque Pérez", -35.401, -59.335), ("Gral. Las Heras", -34.927, -58.947),
    ("Rojas", -34.200, -60.729), ("Arrecifes", -34.068, -60.109), ("S. A. de Areco", -34.244, -59.474),
    ("N. de la Riestra", -35.273, -59.776), ("Moquehuá", -35.092, -59.776), ("Gorostiaga", -34.839, -59.866),
)
# Franjas de lluvia (mm acumulados): desde, color. Debajo de medio milímetro no se pinta.
FRANJAS = ((0.5, (190, 226, 255)), (2, (140, 196, 252)), (5, (90, 160, 246)), (10, (50, 118, 230)),
           (20, (36, 76, 196)), (40, (122, 62, 204)), (60, (196, 52, 170)))


def _xy(lon: float, lat: float, lado: int = LADO) -> tuple:
    lon0, lon1, lat0, lat1 = CAJA
    return (lon - lon0) / (lon1 - lon0) * lado, (lat1 - lat) / (lat1 - lat0) * lado


def km_a_px(km: float, lado: int = LADO) -> float:
    return km / (2 * MEDIO_LAT * KM_POR_GRADO) * lado


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El fondo (una vez)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def armar_base(geojson: Path = None, log=print) -> tuple:
    """Los partidos que tocan la caja: el relleno (FONDO_PNG) y los límites (LIMITES_PNG), por separado para
    que los límites queden ARRIBA de la lluvia."""
    import httpx
    if geojson and Path(geojson).exists():
        datos = json.loads(Path(geojson).read_text(encoding="utf-8"))
    else:
        datos = httpx.get(GEOJSON, timeout=120, follow_redirects=True).json()
    lon0, lon1, lat0, lat1 = CAJA
    m = 0.3
    fondo = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    limites = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    df, dl = ImageDraw.Draw(fondo), ImageDraw.Draw(limites)
    n = 0
    for f in datos["features"]:
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        anillos = [a for p in polis for a in p[:1]]
        if not any(lon0 - m <= x <= lon1 + m and lat0 - m <= y <= lat1 + m for a in anillos for x, y in a):
            continue
        n += 1
        for a in anillos:
            pts = [_xy(x, y) for x, y in a]
            df.polygon(pts, fill=(48, 52, 59, 255))
            dl.line(pts + pts[:1], fill=(120, 126, 136, 210), width=2)
    FONDO_PNG.parent.mkdir(parents=True, exist_ok=True)
    fondo.save(FONDO_PNG)
    limites.save(LIMITES_PNG)
    log(f"mapa de lluvia: {n} partidos → {FONDO_PNG.name}, {LIMITES_PNG.name}")
    return FONDO_PNG, LIMITES_PNG


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El pronóstico
# ─────────────────────────────────────────────────────────────────────────────────────────────
def puntos() -> tuple:
    """(lats, lons) de la grilla: NODOS adentro de la caja y uno más de margen a cada lado."""
    lon0, lon1, lat0, lat1 = CAJA
    dlat, dlon = (lat1 - lat0) / (NODOS - 1), (lon1 - lon0) / (NODOS - 1)
    lats = [round(lat1 - dlat * (i - 1), 4) for i in range(NODOS + 2)]      # de norte a sur
    lons = [round(lon0 + dlon * (j - 1), 4) for j in range(NODOS + 2)]      # de oeste a este
    return lats, lons


def _pedir_met(lat: float, lon: float, get=None) -> list:
    import httpx
    get = get or (lambda url, params: httpx.get(url, params=params, headers={"User-Agent": UA}, timeout=30))
    for intento in range(3):
        try:
            r = get(URL_MET, {"lat": f"{lat:.4f}", "lon": f"{lon:.4f}"})
            if r.status_code == 200:
                return r.json()["properties"]["timeseries"]
        except Exception:                                  # noqa: BLE001 — se reintenta
            pass
    return None


def sumar(serie: list, desde: datetime, hasta: datetime) -> tuple:
    """(mm totales entre desde y hasta, {fecha AR: mm}). Usa la lluvia de la hora siguiente donde la hay y
    la de las 6 horas siguientes donde el pronóstico ya va de a 6 horas (sin contar dos veces)."""
    total, por_dia = 0.0, {}
    cubierto = desde
    for p in serie or []:
        t = datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
        if t < cubierto or t >= hasta:
            continue
        datos = p.get("data") or {}
        for clave, horas in (("next_1_hours", 1), ("next_6_hours", 6)):
            mm = (((datos.get(clave) or {}).get("details") or {}).get("precipitation_amount"))
            if mm is not None:
                total += mm
                dia = t.astimezone(TZ_AR).date().isoformat()
                por_dia[dia] = por_dia.get(dia, 0.0) + mm
                cubierto = t + timedelta(hours=horas)
                break
    return total, por_dia


def lluvia(ahora: datetime = None, horas: int = HORAS, get=None, log=print) -> dict | None:
    """{grilla [[mm]], desde, hasta, chivilcoy {fecha: mm}, chivilcoy_total} o None si el pronóstico no
    contestó (más de un cuarto de los puntos sin dato)."""
    ahora = ahora or datetime.now(timezone.utc)
    desde = ahora.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hasta = desde + timedelta(hours=horas)
    lats, lons = puntos()
    tareas = [(i, j, la, lo) for i, la in enumerate(lats) for j, lo in enumerate(lons)]
    with ThreadPoolExecutor(max_workers=6) as ex:
        series = list(ex.map(lambda t: _pedir_met(t[2], t[3], get), tareas))
    faltan = sum(1 for s in series if s is None)
    if faltan > len(tareas) // 4:
        log(f"   mapa de lluvia: MET Norway no contestó {faltan} de {len(tareas)} puntos; no va")
        return None
    grilla = [[None] * len(lons) for _ in lats]
    for (i, j, _la, _lo), s in zip(tareas, series):
        grilla[i][j] = sumar(s, desde, hasta)[0] if s is not None else None
    # Un punto sin dato toma el promedio de sus vecinos (o 0).
    for i in range(len(lats)):
        for j in range(len(lons)):
            if grilla[i][j] is None:
                vec = [grilla[a][b] for a in (i - 1, i, i + 1) for b in (j - 1, j, j + 1)
                       if 0 <= a < len(lats) and 0 <= b < len(lons) and grilla[a][b] is not None]
                grilla[i][j] = sum(vec) / len(vec) if vec else 0.0
    centro = _pedir_met(CENTRO[0], CENTRO[1], get)
    total_c, dias_c = sumar(centro, desde, hasta) if centro else (None, {})
    return {"grilla": grilla, "desde": desde.isoformat(), "hasta": hasta.isoformat(), "horas": horas,
            "chivilcoy": dias_c, "chivilcoy_total": total_c, "puntos": len(tareas), "sin_dato": faltan}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El dibujo
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _campo(grilla: list, lado: int = LADO):
    """La grilla interpolada (bilineal) a lado×lado px; los nodos 1..NODOS caen en los bordes de la caja."""
    import numpy as np
    g = np.array(grilla, dtype=float)
    paso = lado / (NODOS - 1)
    c = np.arange(lado) + 0.5
    fx = c / paso + 1                                       # columna fraccionaria en la grilla
    fy = c / paso + 1
    x0 = np.clip(np.floor(fx).astype(int), 0, g.shape[1] - 2)
    y0 = np.clip(np.floor(fy).astype(int), 0, g.shape[0] - 2)
    tx, ty = fx - x0, fy - y0
    X0, Y0 = np.meshgrid(x0, y0)
    TX, TY = np.meshgrid(tx, ty)
    a, b = g[Y0, X0], g[Y0, X0 + 1]
    c_, d = g[Y0 + 1, X0], g[Y0 + 1, X0 + 1]
    return (a * (1 - TX) + b * TX) * (1 - TY) + (c_ * (1 - TX) + d * TX) * TY


def capa_lluvia(grilla: list, lado: int = LADO) -> Image.Image:
    import numpy as np
    mm = _campo(grilla, lado)
    rgba = np.zeros((lado, lado, 4), dtype=np.uint8)
    for desde, color in FRANJAS:
        m = mm >= desde
        rgba[m, :3] = color
        rgba[m, 3] = 190
    return Image.fromarray(rgba, "RGBA").filter(ImageFilter.GaussianBlur(3))


def _rotulo(d, x, y, texto, f, color=(232, 235, 240)):
    d.text((x, y), texto, font=f, fill=color, stroke_width=4, stroke_fill=(24, 26, 30))


def dibujar_mapa(datos: dict, lado: int = LADO) -> Image.Image:
    """El cuadrado del mapa: fondo, lluvia, límites, anillos de 50 y 100 km, ciudades y Chivilcoy."""
    im = Image.new("RGBA", (lado, lado), (30, 33, 38, 255))
    for capa in (FONDO_PNG,):
        if capa.exists():
            im.alpha_composite(Image.open(capa).convert("RGBA").resize((lado, lado), Image.LANCZOS))
    im.alpha_composite(capa_lluvia(datos["grilla"], lado))
    if LIMITES_PNG.exists():
        im.alpha_composite(Image.open(LIMITES_PNG).convert("RGBA").resize((lado, lado), Image.LANCZOS))
    capa = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    cx, cy = _xy(CENTRO[1], CENTRO[0], lado)
    for km in (50, 100):
        r = km_a_px(km, lado)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 110), width=2)
        fk = D.fuente("medium", 22)
        _rotulo(d, cx - d.textlength(f"{km} km", font=fk) / 2, cy + r - 13, f"{km} km", fk, (220, 223, 228))
    f = D.fuente("medium", 23)
    for nombre, lat, lon in LOCALIDADES:
        x, y = _xy(lon, lat, lado)
        if not (12 < x < lado - 12 and 12 < y < lado - 12):
            continue
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(240, 242, 245, 255), outline=(24, 26, 30, 255), width=2)
        ancho = d.textlength(nombre, font=f)
        tx = x + 9 if x + 9 + ancho < lado - 6 else x - 9 - ancho
        _rotulo(d, tx, y - 14, nombre, f)
    d.regular_polygon((cx, cy, 17), 4, rotation=45, fill=D.NARANJA, outline=D.BLANCO, width=3)
    _rotulo(d, cx - d.textlength("CHIVILCOY", font=D.fuente("negra", 34)) / 2, cy - 62, "CHIVILCOY",
            D.fuente("negra", 34), D.NARANJA)
    im.alpha_composite(capa)
    mascara = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, lado - 1, lado - 1), radius=26, fill=255)
    im.putalpha(mascara)
    return im


def _dia_corto(iso: str) -> str:
    from agro import historias as HI
    d = date.fromisoformat(iso)
    return f"{HI.DIAS[d.weekday()][:3]} {d.day}"


def texto_chivilcoy(datos: dict, hoy: date) -> str:
    """«En Chivilcoy: hoy 0 mm · dom 25: 12 mm · lun 26: 3 mm»."""
    dias = datos.get("chivilcoy") or {}
    if not dias:
        return ""
    partes = []
    for iso in sorted(dias)[:3]:
        mm = dias[iso]
        cuando = "hoy" if iso == hoy.isoformat() else _dia_corto(iso)
        partes.append(f"{cuando}: {('%.0f' % mm) if mm >= 1 else '0'} mm")
    return "En Chivilcoy: " + " · ".join(partes)


def placa(datos: dict, destino: Path, hoy: date, seccion: str = "EL CAMPO HOY") -> Path | None:
    """La placa del mapa (9:16 y, con historias.guardar, también 4:5). None si no hay datos."""
    if not datos or not datos.get("grilla"):
        return None
    from agro import historias as HI
    im, d = HI.lienzo()
    hasta = datetime.fromisoformat(datos["hasta"]).astimezone(TZ_AR)
    y = HI.encabezado(im, d, seccion, "¿Dónde va a llover?",
                      f"Lluvia acumulada prevista hasta el {HI.DIAS[hasta.weekday()]} {hasta.day} · "
                      f"Chivilcoy en el centro del mapa")
    txt = texto_chivilcoy(datos, hoy)
    if txt:
        f = D.fuente("bold", 32)
        w = d.textlength(txt, font=f)
        d.rounded_rectangle((D.X - 4, y - 6, D.X + w + 28, y + 50), radius=14, fill=(46, 92, 170, 255))
        d.text((D.X + 12, y + 4), txt, font=f, fill=D.BLANCO)
        y += 72
    lado = HI.W - 2 * (D.X - 24)
    mapa = dibujar_mapa(datos, lado)
    im.alpha_composite(mapa, (D.X - 24, y))
    y += lado + 22
    # La referencia de colores.
    fl = D.fuente("bold", 22)
    x = D.X - 24
    ancho = (lado - (len(FRANJAS) - 1) * 8) / len(FRANJAS)
    for k, (desde, color) in enumerate(FRANJAS):
        hasta_mm = FRANJAS[k + 1][0] if k + 1 < len(FRANJAS) else None
        rot = (f"{desde:g}–{hasta_mm:g}" if hasta_mm else f"+{desde:g}").replace(".", ",")
        d.rounded_rectangle((x, y, x + ancho, y + 40), radius=8, fill=color + (255,))
        tc = D.BLANCO if k >= 3 else (24, 26, 30)
        d.text((x + (ancho - d.textlength(rot, font=fl)) / 2, y + 7), rot, font=fl, fill=tc)
        x += ancho + 8
    d.text((D.X - 24, y + 48), "milímetros", font=D.fuente("regular", 22), fill=(170, 175, 182))
    HI.pie(d, f"MET Norway, pronóstico por modelo (ECMWF), CC BY 4.0 · {HI.M.fecha_corta(hoy.isoformat())}",
           f"Lluvia total prevista en las próximas {datos.get('horas', HORAS)} horas. Anillos: 50 y 100 km de "
           "Chivilcoy. Límites de partidos: IGN.")
    return HI.guardar(im, destino)


def main():
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    ap = argparse.ArgumentParser(description="El mapa de lluvia con Chivilcoy en el centro.")
    ap.add_argument("--base", action="store_true", help="armar el fondo (partidos del IGN) y guardarlo en agro/marca")
    a = ap.parse_args()
    if a.base:
        armar_base()
        return
    datos = lluvia()
    salida = Path(__file__).resolve().parent.parent / "salida_agro" / "mapa_lluvia_prueba.jpg"
    print(placa(datos, salida, datetime.now(TZ_AR).date()))


if __name__ == "__main__":
    main()
