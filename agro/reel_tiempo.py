# -*- coding: utf-8 -*-
"""LOS REELS DEL TIEMPO EN CHIVILCOY, en @diarioyradioagro (20/11/2026).

Pedido del editor: «reels con secuencias animadas automáticamente para la cobertura y actualidad de Chivilcoy — de
cómo se prevé el avance de lluvias y tormentas o cómo se desplazan las precipitaciones — horarios — además reels
sobre saturación de suelos y situación de caminos rurales y campos después de las lluvias — resúmenes de cuántos mm
llovió, etc. … que se aplique primero a mi cuenta de diarioyradioagro».

Una VIGÍA que corre cada hora (6 a 22 h, workflow agro_tiempo.yml) mira el pronóstico de MET Norway (modelo ECMWF,
gratis y con uso comercial permitido citando la fuente: el mismo del mapa de lluvia) y, si pasa algo, publica:

  - «a qué hora llueve» (lluvia_horas): si en Chivilcoy se esperan ZONA_HORAS_MM (5) o más en las próximas 24 h, o
    tormenta. El mapa de la zona hora por hora (cómo avanza la lluvia), Chivilcoy hora por hora con los rayos de
    tormenta, el pronóstico pueblo por pueblo y el cierre. Una vez por día.
  - «cuánto llovió» (llovio): cuando terminó una lluvia de LLOVIO_MM (5) o más en las últimas 24 h. Los mm son una
    ESTIMACIÓN del modelo (se arma con lo que pronosticaba para cada hora, la vigía lo anota en la memoria): el reel
    lo dice y pide a los productores su pluviómetro y fotos de los caminos rurales y los lotes. Con 30 mm o más suma
    la placa de caminos rurales y campos anegados.
  - «calor» / «helada»: máxima de 35 °C o más hoy, o mínima de 2 °C o menos esta noche o mañana temprano. La
    temperatura hora por hora.

Como mucho TOPE_DIA (2) por día y nunca dos en menos de 3 horas. Solo @diarioyradioagro (Instagram y Facebook, y
como historia, como todos los reels de agro). Sin IA.

Fuentes que NO se usan (revisadas el 20/11/2026): RainViewer y Open-Meteo (gratis solo para uso no comercial),
Windy (API paga), SMN (sus datos abiertos no traen lluvia medida y el sitio frena a los programas), CONAE/SAOCOM
(«todos los derechos reservados»), ORA agua útil por cuartel (todavía sin datos de esta campaña: cuando salgan,
sirven para el reel de saturación de suelos).

    python -m agro.reel_tiempo                      # simula la vigía (anota, no publica)
    python -m agro.reel_tiempo --forzar lluvia_horas # arma ese reel aunque no toque (simulando)
    python -m agro.reel_tiempo --publicar           # en la nube

AGRO_TIEMPO=0 lo apaga; AGRO_TIEMPO_TIPOS="lluvia_horas,llovio,calor,helada" elige cuáles.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import diseno as D  # noqa: E402
from agro import mapa_lluvia as ML  # noqa: E402
from agro import reel_zona as RZ  # noqa: E402

TZ_AR = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).resolve().parent.parent
MEMORIA = RAIZ / "estado" / "agro_tiempo.json"
SALIDA = RAIZ / "salida_agro"
HORAS = 24
SEG_HORA = 0.55
LADO_MAPA = 960
Y_MAPA = 236
TOPE_DIA = 2
SEPARACION_H = 3
FUENTE_MET = "Pronóstico: MET Norway (modelo ECMWF), CC BY 4.0. Puede cambiar."
WHATSAPP = RZ.WHATSAPP
# Chivilcoy y sus pueblos (los de la vigía, que anota la lluvia de cada hora).
# Coordenadas: centroides de georef (apis.datos.gob.ar, localidades del partido de Chivilcoy).
LUGARES = (("Chivilcoy", *ML.CENTRO), ("Moquehuá", -35.092, -59.776), ("Gorostiaga", -34.839, -59.866),
           ("Ramón Biaus", -35.087, -59.924), ("San Sebastián", -34.943, -59.702), ("Emilio Ayarza", -34.744, -60.039),
           ("La Rica", -34.973, -59.861))
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
AMARILLO = (255, 214, 64)
AZUL = (64, 140, 245)


def _var(n, d):
    return (os.environ.get(n) or d).strip()


def activo() -> bool:
    return _var("AGRO_TIEMPO", "1") != "0"


def tipos() -> set:
    return {t.strip() for t in _var("AGRO_TIEMPO_TIPOS", "lluvia_horas,llovio,calor,helada").split(",") if t.strip()}


def _num(n, d):
    try:
        return float(_var(n, str(d)))
    except ValueError:
        return float(d)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Memoria: lo publicado y el registro de la lluvia hora por hora
# ─────────────────────────────────────────────────────────────────────────────────────────────
def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads(Path(ruta or MEMORIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"reels": [], "registro": {}}


def guardar(mem: dict, ruta: Path = None, ahora: datetime = None) -> None:
    ruta = Path(ruta or MEMORIA)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    mem["reels"] = (mem.get("reels") or [])[-60:]
    if ahora:                                              # el registro guarda 4 días
        limite = (ahora - timedelta(days=4)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H")
        mem["registro"] = {h: v for h, v in (mem.get("registro") or {}).items() if h >= limite}
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=1), encoding="utf-8")


def _hora(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def _mm_hora(p: dict):
    return (((p.get("data") or {}).get("next_1_hours") or {}).get("details") or {}).get("precipitation_amount")


def _simbolo(p: dict) -> str:
    return (((p.get("data") or {}).get("next_1_hours") or {}).get("summary") or {}).get("symbol_code") or ""


def _instante(p: dict) -> dict:
    return ((p.get("data") or {}).get("instant") or {}).get("details") or {}


def anotar(mem: dict, series: dict, ahora: datetime, horas: int = 6) -> None:
    """Para cada lugar, la lluvia que el pronóstico MÁS NUEVO da para cada hora (desde ahora y las `horas`
    siguientes). Las horas que ya pasaron quedan con lo último que se pronosticó para ellas: así se estima lo que
    llovió (no es una medición)."""
    reg = mem.setdefault("registro", {})
    desde = ahora.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for lugar, serie in series.items():
        for p in serie or []:
            t = datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
            if t < desde or t >= desde + timedelta(hours=horas):
                continue
            mm = _mm_hora(p)
            if mm is not None:
                reg.setdefault(_hora(t), {})[lugar] = round(mm, 2)


def llovido(mem: dict, ahora: datetime, horas: int = 24, lugar: str = "Chivilcoy") -> tuple:
    """(mm estimados en las últimas `horas`, horas con dato)."""
    reg = mem.get("registro") or {}
    total, con_dato = 0.0, 0
    for k in range(1, horas + 1):
        v = (reg.get(_hora(ahora - timedelta(hours=k))) or {}).get(lugar)
        if v is not None:
            total += v
            con_dato += 1
    return total, con_dato


def publicados_hoy(mem: dict, ahora: datetime) -> list:
    hoy = ahora.astimezone(TZ_AR).date().isoformat()
    return [r for r in mem.get("reels") or [] if r.get("dia") == hoy and r.get("publicado")]


def puede_publicar(mem: dict, ahora: datetime, tipo: str) -> str:
    """'' si puede; si no, el motivo."""
    hoy = publicados_hoy(mem, ahora)
    if any(r["tipo"] == tipo for r in hoy):
        return f"el de «{tipo}» ya salió hoy"
    if len(hoy) >= TOPE_DIA:
        return f"ya salieron {len(hoy)} hoy"
    if tipo == "llovio":
        ayer = [r for r in mem.get("reels") or [] if r.get("tipo") == "llovio" and r.get("publicado")
                and r.get("cuando", "") >= (ahora - timedelta(hours=20)).isoformat()]
        if ayer:
            return "ya salió un «cuánto llovió» en las últimas 20 h"
    for r in hoy:
        try:
            if ahora - datetime.fromisoformat(r["cuando"]) < timedelta(hours=SEPARACION_H):
                return f"salió otro hace menos de {SEPARACION_H} h"
        except (KeyError, ValueError):
            pass
    return ""


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El pronóstico
# ─────────────────────────────────────────────────────────────────────────────────────────────
def series_lugares(get=None) -> dict:
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda l: ML._pedir_met(l[1], l[2], get), LUGARES))
    return {l[0]: s for l, s in zip(LUGARES, res) if s}


def horas_chivilcoy(serie: list, ahora: datetime, horas: int = HORAS) -> list:
    """[{t (AR), mm, tormenta, temp, viento}] hora por hora desde ahora."""
    desde = ahora.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    salida = []
    for p in serie or []:
        t = datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
        if t < desde or t >= desde + timedelta(hours=horas):
            continue
        mm = _mm_hora(p)
        if mm is None:
            continue
        inst = _instante(p)
        salida.append({"t": t.astimezone(TZ_AR), "mm": mm, "tormenta": "thunder" in _simbolo(p),
                       "temp": inst.get("air_temperature"), "viento": round((inst.get("wind_speed") or 0) * 3.6)})
    return salida


def grilla_horaria(ahora: datetime, horas: int = HORAS, get=None, log=print) -> dict | None:
    """{tramos: [{t, grilla}], total (grilla), chivilcoy (lista horaria)} con la grilla de 13x13 puntos."""
    desde = ahora.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    lats, lons = ML.puntos()
    tareas = [(la, lo) for la in lats for lo in lons]
    with ThreadPoolExecutor(max_workers=6) as ex:
        series = list(ex.map(lambda t: ML._pedir_met(t[0], t[1], get), tareas))
    if sum(1 for s in series if s is None) > len(tareas) // 4:
        log("   MET Norway no contestó; no va")
        return None
    tramos = []
    for k in range(horas):
        d0 = desde + timedelta(hours=k)
        vals = [ML.sumar(s, d0, d0 + timedelta(hours=1))[0] if s is not None else 0.0 for s in series]
        tramos.append({"t": d0.astimezone(TZ_AR).isoformat(),
                       "grilla": [vals[i * len(lons):(i + 1) * len(lons)] for i in range(len(lats))]})
    total = [[sum(t["grilla"][a][b] for t in tramos) for b in range(len(lons))] for a in range(len(lats))]
    return {"tramos": tramos, "total": total}


def _ventana_fuerte(horas: list, ancho: int = 3) -> tuple:
    """(desde, hasta, mm) de las `ancho` horas seguidas con más lluvia."""
    mejor = (None, None, 0.0)
    for i in range(max(0, len(horas) - ancho + 1)):
        mm = sum(h["mm"] for h in horas[i:i + ancho])
        if mm > mejor[2]:
            mejor = (horas[i]["t"], horas[i + ancho - 1]["t"] + timedelta(hours=1), mm)
    return mejor


def _cuando(t: datetime, ahora: datetime) -> str:
    """«hoy», «esta noche», «mañana», «el jueves»."""
    dias = (t.date() - ahora.astimezone(TZ_AR).date()).days
    if dias == 0:
        return "esta noche" if t.hour >= 20 else "hoy"
    if dias == 1:
        return "esta madrugada" if t.hour < 6 and ahora.astimezone(TZ_AR).hour >= 18 else "mañana"
    return f"el {DIAS[t.weekday()]}"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Dibujos propios
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _rayo(d: ImageDraw.ImageDraw, x: float, y: float, h: float, color=AMARILLO) -> None:
    w = h * 0.55
    d.polygon([(x + w * 0.55, y), (x, y + h * 0.58), (x + w * 0.42, y + h * 0.58), (x + w * 0.2, y + h),
               (x + w, y + h * 0.36), (x + w * 0.55, y + h * 0.36), (x + w * 0.8, y)], fill=color)


def _encabezado(d, titulo: str, sub: str, tc: dict) -> None:
    d.rectangle((0, 0, D.W, 8), fill=D.ACENTO)
    f, r = D.ajustar(d, titulo, "negra", 60, 38, D.W - 120, 1)    # el gancho (SEO) en un renglón
    d.text((60, 44 + (60 - f.size) // 2), r[0] if r else titulo, font=f, fill=D.BLANCO)
    d.text((60, 120), sub, font=D.fuente("medium", 34), fill=tc["texto"])


def placa_pueblos(titulo: str, sub: str, puntos: list, t: float, pie: str) -> Image.Image:
    """El partido de Chivilcoy con una burbuja por pueblo que crece con los mm (agro/mapa_zona.py)."""
    from agro import mapa_zona as MZ
    tc = D.TEMAS["grafito"]
    im = Image.new("RGBA", (D.W, D.H45), tc["fondo"] + (255,))
    d = ImageDraw.Draw(im)
    _encabezado(d, titulo, sub, tc)
    m = MZ.pueblos(puntos, t, 1000, D.H45 - 300, fondo=tc["linea"])
    im.alpha_composite(m, ((D.W - m.width) // 2, 200))
    d.text((60, D.H45 - 56), pie, font=D.fuente("regular", 22), fill=tc["tenue"])
    return im


def cuadros_mapa(datos_: dict, horas: list, titulo: str):
    """fn(t) del mapa que avanza hora por hora (SEG_HORA cada una, con fundido)."""
    tc = D.TEMAS["grafito"]
    base = Image.new("RGB", (D.W, D.H45), tc["fondo"])
    d = ImageDraw.Draw(base)
    _encabezado(d, titulo, "Lluvia prevista hora por hora · próximas 24 horas", tc)
    x, f = 60, D.fuente("medium", 24)
    for desde, color in ML.FRANJAS[:6]:
        d.rounded_rectangle((x, 182, x + 34, 206), radius=6, fill=color)
        etq = f"{desde:g} mm"
        d.text((x + 42, 180), etq, font=f, fill=tc["texto"])
        x += 42 + d.textlength(etq, font=f) + 26
    mapas = {}
    n = len(datos_["tramos"])

    def cuadro(i: int) -> Image.Image:
        if i not in mapas:
            m = ML.dibujar_mapa({"grilla": datos_["tramos"][i]["grilla"]}, LADO_MAPA)
            im = base.copy()
            im.paste(m, (60, Y_MAPA), m)
            dd = ImageDraw.Draw(im)
            y = Y_MAPA + LADO_MAPA + 22
            ancho = (LADO_MAPA - (n - 1) * 3) / n
            for k in range(n):
                x0 = 60 + k * (ancho + 3)
                dd.rounded_rectangle((x0, y, x0 + ancho, y + 10), radius=4,
                                     fill=D.NARANJA if k == i else (tc["linea"] if k > i else (120, 124, 132)))
            t = datetime.fromisoformat(datos_["tramos"][i]["t"])
            dd.text((60, y + 26), f"{DIAS[t.weekday()][:3]} {t.day} · {t.hour:02d} h", font=D.fuente("bold", 46),
                    fill=D.BLANCO)
            h = horas[i] if i < len(horas) else None
            acum = sum(x["mm"] for x in horas[:i + 1])
            txt = f"Chivilcoy: {acum:.0f} mm" if acum >= 0.5 else "Chivilcoy: 0 mm"
            fn = D.fuente("negra", 46)
            xt = D.W - 60 - dd.textlength(txt, font=fn)
            dd.text((xt, y + 26), txt, font=fn, fill=(120, 180, 255))
            if h and h["tormenta"]:
                _rayo(dd, xt - 56, y + 26, 50)
            mapas[i] = im
        return mapas[i]

    def fn(t: float) -> Image.Image:
        i = min(n - 1, int(t / SEG_HORA))
        resto = t - i * SEG_HORA
        if i and resto < 0.18:
            return Image.blend(cuadro(i - 1), cuadro(i), resto / 0.18)
        return cuadro(i)
    return fn, n * SEG_HORA + 0.8


def placa_horas(horas: list, titulo: str, sub: str, t: float, pasado: bool = False) -> Image.Image:
    """Chivilcoy hora por hora: una columna por hora con los mm; un rayo si hay tormenta."""
    tc = D.TEMAS["grafito"]
    im = Image.new("RGB", (D.W, D.H45), tc["fondo"])
    d = ImageDraw.Draw(im)
    _encabezado(d, titulo, sub, tc)
    n = max(1, len(horas))
    base, techo = D.H45 - 300, 330
    x0, x1 = 70, D.W - 50
    paso = (x1 - x0) / n
    ancho = paso * 0.72
    tope = max([h["mm"] for h in horas] + [4.0])
    f_v, f_h = D.fuente("bold", 26), D.fuente("medium", 26)
    for i, h in enumerate(horas):
        crec = RZ._ease((t - 1.8 * i / n) / 0.4)
        if crec <= 0:
            continue
        xa = x0 + i * paso + (paso - ancho) / 2
        alto = (base - techo) * h["mm"] / tope * crec
        if h["mm"] >= 0.1:
            d.rounded_rectangle((xa, base - max(4, alto), xa + ancho, base), radius=5,
                                fill=AZUL if h["mm"] < 5 else (122, 62, 204))
            if h["mm"] >= 1:
                txt = f"{h['mm']:.0f}"
                d.text((xa + ancho / 2 - d.textlength(txt, font=f_v) / 2, base - alto - 34), txt, font=f_v,
                       fill=D.BLANCO)
        if h["tormenta"]:
            _rayo(d, xa + ancho / 2 - 14, base - alto - (80 if h["mm"] >= 1 else 50), 40)
        if h["t"].hour % 3 == 0:
            etq = f"{h['t'].hour}h"
            d.text((xa + ancho / 2 - d.textlength(etq, font=f_h) / 2, base + 14), etq, font=f_h, fill=tc["texto"])
            if h["t"].hour == 0 and i:
                d.line((xa - 2, techo - 20, xa - 2, base + 50), fill=tc["tenue"], width=2)
                d.text((xa + 4, techo - 30), DIAS[h["t"].weekday()][:3], font=f_h, fill=tc["tenue"])
    d.line((x0, base, x1, base), fill=tc["tenue"], width=2)
    total = sum(h["mm"] for h in horas)
    d.text((60, base + 70), f"{'Total estimado' if pasado else 'Total previsto'} en Chivilcoy: {total:.0f} mm",
           font=D.fuente("bold", 40), fill=(120, 180, 255))
    if any(h["tormenta"] for h in horas):
        _rayo(d, 60, base + 136, 34)
        d.text((92, base + 134), "tormenta posible", font=D.fuente("medium", 30), fill=AMARILLO)
    d.text((60, D.H45 - 56), "Estimado con el pronóstico de MET Norway (ECMWF): no es medición." if pasado
           else FUENTE_MET, font=D.fuente("regular", 22), fill=tc["tenue"])
    return im


def placa_temperatura(horas: list, titulo: str, sub: str, t: float, marca: str) -> Image.Image:
    """La temperatura hora por hora como línea, con la máxima (o la mínima) marcada."""
    tc = D.TEMAS["grafito"]
    im = Image.new("RGB", (D.W, D.H45), tc["fondo"])
    d = ImageDraw.Draw(im)
    _encabezado(d, titulo, sub, tc)
    pts = [h for h in horas if h.get("temp") is not None]
    if len(pts) < 2:
        return im
    lo, hi = min(p["temp"] for p in pts) - 2, max(p["temp"] for p in pts) + 2
    base, techo, x0, x1 = D.H45 - 300, 330, 80, D.W - 70
    xs = [x0 + (x1 - x0) * i / (len(pts) - 1) for i in range(len(pts))]
    ys = [base - (base - techo) * (p["temp"] - lo) / (hi - lo) for p in pts]
    hasta = max(2, int(len(pts) * RZ._ease(t / 2.2)))
    color = (240, 90, 60) if marca == "max" else (120, 190, 255)
    d.line(list(zip(xs[:hasta], ys[:hasta])), fill=color, width=8, joint="curve")
    f_h = D.fuente("medium", 26)
    for i, p in enumerate(pts):
        if p["t"].hour % 3 == 0:
            etq = f"{p['t'].hour}h"
            d.text((xs[i] - d.textlength(etq, font=f_h) / 2, base + 14), etq, font=f_h, fill=tc["texto"])
    k = max(range(len(pts)), key=lambda i: pts[i]["temp"]) if marca == "max" else \
        min(range(len(pts)), key=lambda i: pts[i]["temp"])
    if k < hasta:
        d.ellipse((xs[k] - 14, ys[k] - 14, xs[k] + 14, ys[k] + 14), fill=color, outline=D.BLANCO, width=3)
        txt = f"{pts[k]['temp']:.0f}°"
        fn = D.fuente("negra", 64)
        d.text((min(xs[k] - d.textlength(txt, font=fn) / 2, D.W - 60 - d.textlength(txt, font=fn)),
                ys[k] - (96 if marca == "max" else -24)), txt, font=fn, fill=D.BLANCO)
    d.line((x0, base, x1, base), fill=tc["tenue"], width=2)
    d.text((60, D.H45 - 56), FUENTE_MET, font=D.fuente("regular", 22), fill=tc["tenue"])
    return im


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Los temas: {tema, gancho, diapositivas, texto, hashtags}
# ─────────────────────────────────────────────────────────────────────────────────────────────
def tema_lluvia_horas(ahora: datetime, horas: list, datos_: dict) -> dict:
    total = sum(h["mm"] for h in horas)
    tormenta = any(h["tormenta"] for h in horas)
    t0, t1, mm_fuerte = _ventana_fuerte(horas)
    primera = next((h for h in horas if h["mm"] >= 0.3 or h["tormenta"]), None)
    cuando = _cuando(primera["t"], ahora) if primera else "hoy"
    gancho = (f"Tormenta en Chivilcoy: ¿a qué hora llega?" if tormenta else "¿A qué hora llueve en Chivilcoy?")
    fn_mapa, dur_mapa = cuadros_mapa(datos_, horas, gancho.upper())
    pueblos = ML.lluvia_por_pueblo({"grilla": datos_["total"], "chivilcoy_total": total})
    diap = [
        ("propia", {"fn": fn_mapa, "dur": dur_mapa, "titulo": gancho}),     # arranca con el mapa (20/11/2026)
        ("propia", {"fn": lambda t: placa_horas(horas, "CHIVILCOY, HORA POR HORA", "Milímetros previstos en cada hora",
                                                 t), "dur": 5.5}),
    ]
    if t0 and mm_fuerte >= 1:
        diap.append(("video", {"volanta": "LO MÁS FUERTE", "numero": round(mm_fuerte), "dec": 0, "unidad": "mm",
                               "texto": f"entre las {t0.hour} y las {t1.hour} h ({_cuando(t0, ahora)})"
                                        + (", con tormenta." if tormenta else "."), "video": "lluvia"}))
    if len(pueblos) > 3:
        diap.append(("barras", {"titulo": "Pueblo por pueblo", "sub": "mm previstos en las próximas 24 horas",
                                "filas": [(n, round(v, 1)) for n, v in pueblos[:9]], "dec": 0, "unidad": "mm"}))
    diap.append(RZ._cierre(f"¿Cuánto llovió en tu campo? Mandanos tu video al WhatsApp {WHATSAPP}"))
    texto = [f"{'⛈️' if tormenta else '🌧️'} {gancho} Se esperan {'unos ' if total >= 2 else 'alrededor de '}{total:.0f} mm en Chivilcoy en las próximas 24 "
             f"horas; empieza {cuando}" + (f" a las {primera['t'].hour} h" if primera else "") + "."
             + (f" Lo más fuerte, entre las {t0.hour} y las {t1.hour} h." if t0 and mm_fuerte >= 1 else ""),
             "Así se mueve la lluvia en la zona hora por hora: " + ", ".join(f"{n} {v:.0f} mm" for n, v in pueblos[1:5])
             + "." if len(pueblos) > 2 else "",
             f"📲 ¿Llovió en tu campo? Mandanos tu video o cuántos milímetros juntaste por WhatsApp al {WHATSAPP}.",
             "Es un pronóstico (MET Norway, modelo ECMWF, CC BY 4.0): puede cambiar y cada campo puede recibir distinto."]
    return {"tema": "lluvia_horas", "gancho": gancho, "diapositivas": diap, "texto": [x for x in texto if x],
            "hashtags": ["#Chivilcoy", "#Lluvia", "#Tormenta" if tormenta else "#Clima", "#Pronóstico", "#Campo"],
            "fuente": "Pronóstico: MET Norway (modelo ECMWF), CC BY 4.0"}


def tema_llovio(ahora: datetime, mem: dict) -> dict:
    reg = mem.get("registro") or {}
    horas = []
    for k in range(24, 0, -1):
        t = ahora - timedelta(hours=k)
        v = (reg.get(_hora(t)) or {}).get("Chivilcoy")
        horas.append({"t": t.astimezone(TZ_AR).replace(minute=0, second=0, microsecond=0), "mm": v or 0.0,
                      "tormenta": False})
    total = sum(h["mm"] for h in horas)
    pueblos = sorted([(n, llovido(mem, ahora, 24, n)[0]) for n, *_ in LUGARES], key=lambda f: -f[1])
    gancho = "¿Cuánto llovió en Chivilcoy?"
    lugares = {n: (la, lo) for n, la, lo in LUGARES}
    puntos = [(n, *lugares[n], v) for n, v in pueblos if n in lugares]
    diap = [
        ("propia", {"fn": lambda t: placa_pueblos(gancho.upper(), "Estimado en las últimas 24 horas, pueblo por pueblo",
                                                  puntos, t, "Estimado con el pronóstico de MET Norway (ECMWF): no es "
                                                  "medición."), "dur": 5.0, "titulo": gancho}),
        ("video", {"volanta": "ESTIMADO EN CHIVILCOY", "numero": round(total), "dec": 0, "unidad": "mm",
                   "texto": "en las últimas 24 horas (estimado con el pronóstico; no es una medición).",
                   "video": "lluvia"}),
        ("propia", {"fn": lambda t: placa_horas(horas, "ASÍ LLOVIÓ", "Milímetros estimados en cada hora", t, True),
                    "dur": 5.0}),
    ]
    if total >= _num("LLOVIO_CAMINOS_MM", 30):
        diap.append(("video", {"volanta": "CAMINOS RURALES Y LOTES", "titulo": "¿Cómo quedaron los caminos y los "
                               "campos de tu zona?", "video": "inundacion"}))
    diap.append(RZ._cierre(f"Mandanos fotos de tu pluviómetro, tu lote o tu camino al WhatsApp {WHATSAPP}"))
    texto = [f"🌧️ {gancho} {'Unos' if total >= 2 else 'Alrededor de'} {total:.0f} mm estimados en las últimas 24 horas en la ciudad; en los pueblos: "
             + ", ".join(f"{n} {v:.0f} mm" for n, v in pueblos if n != "Chivilcoy") + ".",
             "Es una estimación hecha con el pronóstico hora por hora (MET Norway, modelo ECMWF), no una medición: "
             "cada campo recibe distinto.",
             f"📲 ¿Cuánto marcó tu pluviómetro? ¿Cómo están los caminos rurales y los lotes? Mandanos fotos y videos "
             f"por WhatsApp al {WHATSAPP} y contanos de qué pueblo sos."]
    return {"tema": "llovio", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#Lluvia", "#CaminosRurales", "#Campo", "#Agro"],
            "fuente": "Estimado con el pronóstico de MET Norway (ECMWF), CC BY 4.0"}


def tema_temperatura(ahora: datetime, horas: list, marca: str) -> dict:
    pts = [h for h in horas if h.get("temp") is not None]
    k = max(pts, key=lambda h: h["temp"]) if marca == "max" else min(pts, key=lambda h: h["temp"])
    cuando = _cuando(k["t"], ahora)
    if marca == "max":
        gancho = f"Calor en Chivilcoy: {k['temp']:.0f}° {cuando}"
        consejo = "Si trabajás en el campo: hidratate, evitá el sol fuerte de 12 a 17 y cuidá a los animales: sombra y agua."
    else:
        gancho = f"{'Helada' if k['temp'] <= 0 else 'Frío intenso'} en Chivilcoy: {k['temp']:.0f}° {cuando}"
        consejo = "Atención con los cultivos sensibles, las huertas y los animales recién nacidos."
    diap = [
        ("propia", {"fn": lambda t: placa_temperatura(horas, gancho.upper(), "Temperatura prevista hora por hora", t,
                                                      marca), "dur": 5.5, "titulo": gancho}),
        ("video", {"volanta": "LA MÁXIMA" if marca == "max" else "LA MÍNIMA", "numero": round(k["temp"]), "dec": 0,
                   "unidad": "°C", "texto": f"a las {k['t'].hour} h ({cuando}). {consejo}",
                   "video": "ganado" if marca == "max" else "campo"}),
        RZ._cierre("Guardalo y compartilo con alguien del campo"),
    ]
    texto = [f"{'🌡️' if marca == 'max' else '🥶'} {gancho} ({k['t'].hour} h).", consejo,
             f"📲 ¿Cómo está tu campo? Contanos por WhatsApp al {WHATSAPP}.",
             "Pronóstico de MET Norway (modelo ECMWF), CC BY 4.0: puede cambiar."]
    return {"tema": "calor" if marca == "max" else "helada", "gancho": gancho, "diapositivas": diap, "texto": texto,
            "hashtags": ["#Chivilcoy", "#Calor" if marca == "max" else "#Helada", "#Clima", "#Campo"],
            "fuente": "Pronóstico: MET Norway (modelo ECMWF), CC BY 4.0"}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La vigía
# ─────────────────────────────────────────────────────────────────────────────────────────────
def que_toca(mem: dict, ahora: datetime, series: dict) -> list:
    """[(tipo, motivo)] en orden de prioridad."""
    salida = []
    chiv = series.get("Chivilcoy")
    if not chiv:
        return salida
    h24 = horas_chivilcoy(chiv, ahora, 24)
    total = sum(h["mm"] for h in h24)
    tormenta = any(h["tormenta"] for h in h24[:18])
    hora_ar = ahora.astimezone(TZ_AR).hour
    # Ya llovió y paró: el resumen.
    llov, con_dato = llovido(mem, ahora, 24)
    prox3 = sum(h["mm"] for h in h24[:3])
    ultimas2 = llovido(mem, ahora, 2)[0]                  # dos horas secas: paró
    if llov >= _num("LLOVIO_MM", 5) and con_dato >= 12 and prox3 < 0.3 and ultimas2 < 0.3 and 7 <= hora_ar <= 22:
        salida.append(("llovio", f"llovieron ~{llov:.0f} mm en 24 h y paró"))
    # Lo que viene: con al menos 2 h de anticipación a la primera lluvia.
    primera = next((i for i, h in enumerate(h24) if h["mm"] >= 0.3 or h["tormenta"]), None)
    if (total >= _num("ZONA_HORAS_MM", 5) or tormenta) and primera is not None and primera >= 2 and 6 <= hora_ar <= 21:
        salida.append(("lluvia_horas", f"{total:.0f} mm previstos en 24 h" + (" con tormenta" if tormenta else "")))
    hoy = [h for h in h24 if h["t"].date() == ahora.astimezone(TZ_AR).date() and h.get("temp") is not None]
    if hoy and max(h["temp"] for h in hoy) >= _num("CALOR_MAX", 35) and 7 <= hora_ar <= 11:
        salida.append(("calor", f"máxima de {max(h['temp'] for h in hoy):.0f}° hoy"))
    noche = [h for h in h24 if h.get("temp") is not None and (h["t"] - ahora.astimezone(TZ_AR)) <= timedelta(hours=16)
             and h["t"].hour <= 9]
    if noche and min(h["temp"] for h in noche) <= _num("HELADA_MIN", 2) and 17 <= hora_ar <= 21:
        salida.append(("helada", f"mínima de {min(h['temp'] for h in noche):.0f}°"))
    return [(t, m) for t, m in salida if t in tipos()]


def corrida(publicar: bool, forzar: str = "", ahora: datetime = None, ruta_mem: Path = None, get=None,
            log=print, publicador=None, armar=None, videos_fn=None) -> dict:
    ahora = ahora or datetime.now(TZ_AR)
    inf = {"cuando": ahora.isoformat(timespec="minutes"), "publicar": publicar, "estado": ""}
    if not activo():
        inf["estado"] = "apagado"
        return inf
    mem = cargar(ruta_mem)
    series = series_lugares(get)
    if not series.get("Chivilcoy"):
        inf["estado"] = "sin_pronostico"
        log("MET Norway no contestó")
        return inf
    anotar(mem, series, ahora)
    llov = llovido(mem, ahora, 24)
    log(f"Vigía del tiempo {ahora:%d/%m %H:%M}: estimado últimas 24 h en Chivilcoy {llov[0]:.1f} mm "
        f"({llov[1]} h con dato); previsto 24 h {sum(h['mm'] for h in horas_chivilcoy(series['Chivilcoy'], ahora)):.1f} mm")
    candidatos = [(forzar, "a pedido")] if forzar else que_toca(mem, ahora, series)
    elegido = None
    for tipo, motivo in candidatos:
        motivo_no = "" if forzar else puede_publicar(mem, ahora, tipo)
        if motivo_no:
            log(f"   {tipo}: toca ({motivo}) pero {motivo_no}")
            continue
        elegido = (tipo, motivo)
        break
    inf["candidatos"] = candidatos
    if not elegido:
        inf["estado"] = "nada"
        guardar(mem, ruta_mem, ahora)
        return inf
    tipo, motivo = elegido
    log(f"   → reel «{tipo}»: {motivo}")
    h24 = horas_chivilcoy(series["Chivilcoy"], ahora, 24)
    if tipo == "lluvia_horas":
        datos_ = grilla_horaria(ahora, HORAS, get, log)
        if not datos_:
            inf["estado"] = "sin_pronostico"
            guardar(mem, ruta_mem, ahora)
            return inf
        tema = tema_lluvia_horas(ahora, h24, datos_)
    elif tipo == "llovio":
        tema = tema_llovio(ahora, mem)
    else:
        tema = tema_temperatura(ahora, h24, "max" if tipo == "calor" else "min")
    carpeta = SALIDA / f"tiempo_{ahora:%Y-%m-%d_%H%M}_{tipo}"
    carpeta.mkdir(parents=True, exist_ok=True)
    videos = (videos_fn or RZ.videos_para)(tema, mem, ahora, carpeta, log)
    reel = (armar or RZ.armar)(tema, carpeta / f"tiempo_{tipo}.mp4", videos)
    texto = RZ.caption(tema, videos)
    (carpeta / "texto.txt").write_text(texto, encoding="utf-8")
    p = RZ.pieza(tema, reel, texto, ahora)
    p["id"] = f"tiempo-{tipo}-{ahora:%Y%m%d%H%M}"
    p["colab_diario"] = False                            # por ahora, solo @diarioyradioagro
    p["guion"]["volanta"] = "Clima"
    inf.update(tipo=tipo, reel=reel, texto=texto)
    log(f"   reel: {reel['duracion']:.0f} s, {reel['peso_kb']} KB → {reel['archivo']}")
    if not publicar:
        inf["estado"] = "simulado"
        guardar(mem, ruta_mem, ahora)
        return inf
    anotado = {"dia": ahora.astimezone(TZ_AR).date().isoformat(), "tipo": tipo,
               "cuando": ahora.isoformat(timespec="minutes"), "motivo": motivo, "publicado": None}
    mem.setdefault("reels", []).append(anotado)
    guardar(mem, ruta_mem, ahora)
    if publicador is None:
        from agro import publicar as PUB
        publicador = lambda pz, log=print: PUB.publicar_reel(pz, None, ("facebook", "instagram"), log=log,  # noqa: E731
                                                            portada_url=PUB._subir_portada(pz))
    res = publicador(p, log=log)
    ok = [r for r in ("instagram", "facebook") if isinstance(res.get(r), dict) and res[r].get("id")]
    anotado["publicado"] = {k: v for k, v in res.items() if k in ("instagram", "facebook")} if ok else None
    anotado["redes"] = ok
    guardar(mem, ruta_mem, ahora)
    inf["estado"] = "ok" if ok else "fallo"
    inf["resultado"] = res
    return inf


def informe(inf: dict) -> str:
    l = [f"## Vigía del tiempo ({inf.get('cuando')})", "", f"- Estado: {inf.get('estado')}",
         f"- Candidatos: {', '.join(f'{t} ({m})' for t, m in inf.get('candidatos') or []) or '—'}"]
    if inf.get("reel"):
        l.append(f"- Reel «{inf.get('tipo')}»: {inf['reel']['duracion']:.0f} s")
    for red, v in (inf.get("resultado") or {}).items():
        if red in ("instagram", "facebook") and isinstance(v, dict):
            l.append(f"- {red}: {v.get('id') or v.get('error')}")
    if inf.get("texto"):
        l += ["", "```", inf["texto"], "```"]
    return "\n".join(l)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--forzar", default="", help="lluvia_horas, llovio, calor o helada")
    a = ap.parse_args()
    inf = corrida(a.publicar, a.forzar)
    print(informe(inf))
    if a.publicar and inf.get("estado") == "fallo":
        sys.exit(1)


if __name__ == "__main__":
    main()
