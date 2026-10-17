# -*- coding: utf-8 -*-
"""Las HISTORIAS de @diarioyradioagro (documento «ideas agro» del editor, 17/10/2026): placas 9:16 con
datos, sin IA, en tres tandas por día.

    «El campo hoy» (07:00): clima de la zona, granos, dólar y lo que tenés que saber
    mediodía (14:00): «Tu zona en el mapa» (lluvias), Chicago y la novedad del día
    «Así cerró el mercado» (19:00): pizarra de Rosario, dólar y Chicago al cierre
    Sábados y domingos (sin mercados): clima, mapa, «Los números de la semana», el resumen del día.

Una ALERTA del SMN que toca la zona va PRIMERO en la tanda que sigue (el documento: «el orden cambia
ante una noticia urgente»).

Cada placa dice la FECHA del dato, la FUENTE, el mercado o lugar, la MONEDA y la UNIDAD. Si el dato no
es de hoy, lo dice: «Último dato disponible: 15/10» (nunca un dato viejo presentado como nuevo).

ZONA SEGURA (pedido del editor, 17/10/2026: «centrar todo para que no se tape con los marcos de las
redes, el texto del margen inferior y los logos; compactar»): todo —la marca, la sección, el título, los
datos y la fuente de abajo— se arma como UN bloque compacto y se centra entre SEGURA[0] y SEGURA[1]:
arriba quedan libres las barras de progreso, la foto y el nombre de la cuenta; abajo, la caja de
respuesta, el corazón y el avión de Instagram y Facebook. Si un bloque no entra, se achica entero.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from agro import diseno as D
from agro import mercado as M

W, H = 1080, 1920
TEMA = D.TEMAS["grafito"]
FONDO = (24, 26, 30)
TARJETA = (38, 41, 47)
SUBE, BAJA, IGUAL = (110, 190, 80), (232, 96, 86), (170, 175, 182)
SEGURA = (290, 1580)          # la franja libre de los marcos de Instagram y Facebook (de 1920)
Y_PIE = 1150                  # hasta dónde llenar con datos dentro del bloque (después va el pie)
ALTO_BLOQUE = 2400            # el lienzo de trabajo del bloque (se recorta a lo dibujado)
MAPA = D.MARCA / "mapa_pampa.png"
MAPA_GEOJSON = "https://infra.datos.gob.ar/georef/provincias.geojson"
MAPA_CAJA = (-65.3, -56.7, -39.4, -30.5)        # lon mín, lon máx, lat mín, lat máx
MAPA_ANCHO = 960
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")

# Qué va en cada tanda. Una tanda de historias sale toda junta (es una secuencia que se mira seguida).
PLAN_SEMANA = {"manana": ("clima", "granos", "dolar", "titulares"),
               "mediodia": ("mapa", "chicago", "novedad"),
               "cierre": ("granos", "dolar", "chicago")}
PLAN_FINDE = {"manana": ("clima", "mapa", "titulares", "novedad"),
              "mediodia": ("semana_granos", "semana_dolar", "novedad"),
              "cierre": ("semana_chicago", "clima_manana", "resumen")}
SECCION = {"manana": "EL CAMPO HOY", "mediodia": "AGRO AL MEDIODÍA", "cierre": "ASÍ CERRÓ EL MERCADO"}
MAX_ALERTAS = 2


def plan(bloque: str, dia: date) -> tuple:
    return (PLAN_FINDE if dia.weekday() >= 5 else PLAN_SEMANA).get(bloque, ())


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month]}"


def pesos(v, dec: int = 0) -> str:
    if v is None:
        return "—"
    t = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return t


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Piezas comunes
# ─────────────────────────────────────────────────────────────────────────────────────────────
def lienzo() -> tuple:
    """El lienzo TRANSPARENTE del bloque: se dibuja desde y=0 y `guardar` lo centra en la zona segura."""
    im = Image.new("RGBA", (W, ALTO_BLOQUE), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def fondo() -> Image.Image:
    """El fondo 9:16: grafito, una franja naranja fina arriba y el isologo grande, apenas visible."""
    im = Image.new("RGBA", (W, H), FONDO + (255,))
    ImageDraw.Draw(im).rectangle((0, 0, W, 8), fill=D.NARANJA)
    marca = D.isologo(900)
    marca.putalpha(marca.getchannel("A").point(lambda a: round(a * 0.05)))
    im.alpha_composite(marca, (W - marca.width + 260, H - marca.height - 120))
    return im


def encabezado(im, d, seccion: str, titulo: str, sub: str = "") -> int:
    """La marca, la sección en una caja naranja, el título y la bajada. Devuelve el y libre."""
    lg = D.lockup("grafito", 60)
    im.alpha_composite(lg, (D.X, 0))
    f = D.fuente("bold", 28)
    w = d.textlength(seccion, font=f)
    y = lg.height + 22
    d.rectangle((D.X, y, D.X + w + 32, y + 48), fill=D.NARANJA_CAJA)
    d.text((D.X + 16, y + 8), seccion, font=f, fill=D.BLANCO)
    y += 48 + 18
    ft, rt = D.ajustar(d, titulo, "bold", 70, 48, W - 2 * D.X, 2)
    y = D.escribir(d, D.X, y, rt, ft, D.BLANCO) + 10
    if sub:
        fs, rs = D.ajustar(d, sub, "regular", 32, 26, W - 2 * D.X, 2)
        y = D.escribir(d, D.X, y, rs, fs, (200, 204, 210), 1.22)
    return y + 26


def pie(d, fuente: str, detalle: str = ""):
    """La fuente, el detalle y el usuario, PEGADOS debajo de lo último que se dibujó (no al fondo de la
    pantalla, donde lo tapan la caja de respuesta y los botones)."""
    y = (d._image.getbbox() or (0, 0, 0, 0))[3] + 28
    d.line((D.X, y, W - D.X, y), fill=(70, 74, 82), width=2)
    y += 18
    for texto in (f"Fuente: {fuente}", detalle):
        if texto:
            fx, r = D.ajustar(d, texto, "regular", 26, 22, W - 2 * D.X, 2)
            y = D.escribir(d, D.X, y, r, fx, (165, 170, 178), 1.22) + 4
    d.text((D.X, y + 8), D.USUARIO, font=D.fuente("bold", 28), fill=D.VERDE)


def flecha(d, x: int, y: int, var, tam: int = 30, texto: str = "") -> int:
    """La variación con su triángulo (dibujado: la tipografía no trae ▼) y su color. Devuelve el ancho."""
    if var is None:
        return 0
    sube, baja = var > 0.005, var < -0.005
    color = SUBE if sube else BAJA if baja else IGUAL
    v = abs(var)
    t = texto or ((f"{v:.2f}%" if v < 0.1 else f"{v:.1f}%").replace(".", ",") if (sube or baja) else "0%")
    f = D.fuente("bold", tam)
    lado = round(tam * 0.62)
    cy = y + round(tam * 0.62)
    if sube:
        d.polygon([(x, cy + lado // 2), (x + lado, cy + lado // 2), (x + lado / 2, cy - lado // 2)], fill=color)
    elif baja:
        d.polygon([(x, cy - lado // 2), (x + lado, cy - lado // 2), (x + lado / 2, cy + lado // 2)], fill=color)
    else:
        d.rectangle((x, cy - 6, x + lado, cy - 2), fill=color)
        d.rectangle((x, cy + 2, x + lado, cy + 6), fill=color)
    d.text((x + lado + 10, y), t, font=f, fill=color)
    return round(lado + 10 + d.textlength(t, font=f))


def tarjeta(d, y: int, alto: int):
    d.rounded_rectangle((D.X - 24, y, W - D.X + 24, y + alto), radius=22, fill=TARJETA)


def componer(bloque: Image.Image) -> Image.Image:
    """El bloque dibujado, recortado a lo que tiene y CENTRADO (vertical) en la zona segura del fondo
    9:16. Si es más alto que la zona, se achica entero."""
    caja = bloque.getbbox() or (0, 0, W, 1)
    bloque = bloque.crop((0, 0, W, caja[3]))
    alto_zona = SEGURA[1] - SEGURA[0]
    if bloque.height > alto_zona:
        k = alto_zona / bloque.height
        bloque = bloque.resize((round(W * k), alto_zona), Image.LANCZOS)
    im = fondo()
    im.alpha_composite(bloque, ((W - bloque.width) // 2, SEGURA[0] + (alto_zona - bloque.height) // 2))
    return im


def guardar(im, destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    componer(im).convert("RGB").save(destino, "JPEG", quality=92)
    return destino


def _dia(fecha: str) -> date | None:
    try:
        return date.fromisoformat(fecha)
    except (TypeError, ValueError):
        return None


def rotulo_fecha(fecha: str, hoy: date, dato: str = "Dato") -> str:
    """«Dato de hoy, 17/10» o «Último dato disponible: 15/10»."""
    d = _dia(fecha)
    if not d:
        return "Sin dato disponible"
    if d == hoy:
        return f"{dato} de hoy, {M.fecha_corta(fecha)}"
    return f"Último dato disponible: {DIAS[d.weekday()]} {M.fecha_corta(fecha)}"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Las placas
# ─────────────────────────────────────────────────────────────────────────────────────────────
def placa_clima(datos: dict, destino: Path, hoy: date, seccion: str = "EL CAMPO HOY", dia: date = None) -> Path | None:
    dia = dia or hoy
    pron = datos.get("pronostico") or {}
    filas = [(M.ESTACIONES[e][0], pron[e][dia.isoformat()]) for e in M.ZONA if dia.isoformat() in (pron.get(e) or {})]
    if not filas:
        return None
    im, d = lienzo()
    titulo = "El clima hoy en la zona" if dia == hoy else "El clima de mañana en la zona"
    y = encabezado(im, d, seccion, titulo, fecha_larga(dia).capitalize() + " · máxima / mínima, lluvia y viento")
    alto = 132
    for nombre, v in filas:
        tarjeta(d, y, alto - 14)
        d.text((D.X + 6, y + 16), nombre, font=D.fuente("bold", 38), fill=D.BLANCO)
        d.text((D.X + 6, y + 66), f"Viento hasta {v['viento']} km/h", font=D.fuente("regular", 26), fill=(170, 175, 182))
        t = f"{round(v['max'])}° / {round(v['min'])}°"
        f = D.fuente("negra", 52)
        d.text((540, y + 28), t, font=f, fill=D.NARANJA)
        mm = f"{pesos(v['mm'], 1) if v['mm'] else '0'} mm"
        fm = D.fuente("bold", 38)
        d.text((W - D.X - d.textlength(mm, font=fm), y + 36), mm, font=fm, fill=(120, 180, 255) if v["mm"] else IGUAL)
        y += alto
    # Lo que viene: lluvia acumulada de los próximos días en la zona (promedio de las estaciones).
    dias = sorted({f for e in M.ZONA for f in (pron.get(e) or {}) if f >= dia.isoformat()})[:5]
    if dias and y < Y_PIE - 120:
        total = [sum((pron.get(e) or {}).get(f, {}).get("mm", 0) for f in dias) for e in M.ZONA if pron.get(e)]
        prom = sum(total) / len(total) if total else 0
        texto = (f"Próximos {len(dias)} días: {pesos(prom, 0)} mm de lluvia en promedio en la zona"
                 if prom >= 1 else f"Próximos {len(dias)} días: sin lluvias importantes en la zona")
        fx, r = D.ajustar(d, texto, "medium", 32, 26, W - 2 * D.X, 2)
        D.escribir(d, D.X, y + 8, r, fx, D.BLANCO, 1.22)
    pie(d, "SMN, pronóstico por modelo para cada estación (9 de Julio, Junín, Bolívar, Las Flores, Pehuajó)",
        "El SMN no tiene estación en Chivilcoy: van las cinco más cercanas. °C, mm y km/h.")
    return guardar(im, destino)


def placa_granos(datos: dict, mem: dict, destino: Path, hoy: date, seccion: str) -> Path | None:
    p = datos.get("pizarra")
    if not p:
        return None
    im, d = lienzo()
    titulo = "Así cerró la pizarra de Rosario" if seccion == SECCION["cierre"] and p["fecha"] == hoy.isoformat() \
        else "Precios de pizarra en Rosario"
    y = encabezado(im, d, seccion, titulo, rotulo_fecha(p["fecha"], hoy) + " · pesos y dólares por tonelada")
    previo = M.anterior(mem, "pizarra", p["fecha"])
    alto = 148
    for grano in ("soja", "maiz", "trigo", "girasol", "sorgo"):
        v = (p.get("productos") or {}).get(grano)
        if not v or y > Y_PIE - alto:
            continue
        tarjeta(d, y, alto - 14)
        d.text((D.X + 6, y + 18), M.NOMBRE[grano], font=D.fuente("bold", 40), fill=D.BLANCO)
        if v.get("estimado"):
            d.text((D.X + 6, y + 72), "estimativo (E)", font=D.fuente("regular", 24), fill=(170, 175, 182))
        precio = f"${pesos(v['ars'])}"
        f = D.fuente("negra", 54)
        x = W - D.X - d.textlength(precio, font=f)
        d.text((x, y + 12), precio, font=f, fill=D.NARANJA)
        usd = f"US$ {pesos(v.get('usd'), 2)}" if v.get("usd") else ""
        fu = D.fuente("medium", 28)
        var = None
        if previo:
            var = M.variacion(v["ars"], ((previo[1].get("productos") or {}).get(grano) or {}).get("ars"))
        xu = W - D.X - d.textlength(usd, font=fu)
        d.text((xu, y + 80), usd, font=fu, fill=(200, 204, 210))
        if var is not None:
            flecha(d, 360, y + 78, var, 28)
        elif v.get("direccion"):
            # Sin la rueda anterior en la memoria, solo el sentido que marca la Cámara (sin el número).
            flecha(d, 360, y + 78, {"sube": 1, "baja": -1}.get(v["direccion"], 0), 28,
                   {"sube": "sube", "baja": "baja"}.get(v["direccion"], "sin cambios"))
        y += alto
    detalle = (f"Pizarra: entrega inmediata, pago contado, zona Rosario. Variación contra la rueda del "
               f"{M.fecha_corta(previo[0])}." if previo else "Pizarra: entrega inmediata, pago contado, zona Rosario.")
    if p.get("tc"):
        detalle += f" Dólares al tipo de cambio BNA divisa comprador (${pesos(p['tc'], 2)})."
    pie(d, f"Cámara Arbitral de Cereales de Rosario · {M.fecha_corta(p['fecha'])}", detalle)
    return guardar(im, destino)


def placa_dolar(datos: dict, mem: dict, destino: Path, hoy: date, seccion: str) -> Path | None:
    may, bna = datos.get("mayorista"), datos.get("bna")
    if not may and not bna:
        return None
    im, d = lienzo()
    fecha = (may or {}).get("fecha") or ((bna or {}).get("billete") or {}).get("fecha", "")
    titulo = "Así cerró el dólar" if seccion == SECCION["cierre"] and fecha == hoy.isoformat() else "El dólar para el campo"
    y = encabezado(im, d, seccion, titulo, rotulo_fecha(fecha, hoy) + " · pesos por dólar")
    if may:
        prev = M.anterior(mem, "a3500", may["fecha"])
        tarjeta(d, y, 196)
        d.text((D.X + 6, y + 18), "Mayorista de referencia", font=D.fuente("bold", 38), fill=D.BLANCO)
        d.text((D.X + 6, y + 64), f"BCRA, Com. A 3500 · {M.fecha_corta(may['fecha'])}", font=D.fuente("regular", 26),
               fill=(170, 175, 182))
        d.text((D.X + 6, y + 100), f"${pesos(may['valor'], 2)}", font=D.fuente("negra", 64), fill=D.NARANJA)
        if prev:
            flecha(d, W - D.X - 190, y + 124, M.variacion(may["valor"], prev[1].get("valor")), 32)
        y += 212
    for clave, nombre in (("billete", "Banco Nación · billete"), ("divisa", "Banco Nación · divisa")):
        v = (bna or {}).get(clave)
        if not v:
            continue
        tarjeta(d, y, 168)
        d.text((D.X + 6, y + 18), nombre, font=D.fuente("bold", 38), fill=D.BLANCO)
        d.text((D.X + 6, y + 64), f"{M.fecha_corta(v['fecha'])}" + (f" · {bna.get('hora')} h" if bna.get("hora") else ""),
               font=D.fuente("regular", 26), fill=(170, 175, 182))
        for i, (rot, val) in enumerate((("Compra", v["compra"]), ("Venta", v["venta"]))):
            x = D.X + 6 + i * 430
            d.text((x, y + 112), rot, font=D.fuente("regular", 26), fill=(170, 175, 182))
            d.text((x + 116, y + 100), f"${pesos(val, 2)}", font=D.fuente("negra", 44), fill=D.BLANCO)
        y += 184
    if y < Y_PIE - 150:
        texto = ("El mayorista es la referencia de las exportaciones de granos y de los insumos importados: "
                 "fertilizantes, fitosanitarios y repuestos.")
        fx, r = D.ajustar(d, texto, "regular", 29, 24, W - 2 * D.X, 3)
        D.escribir(d, D.X, y + 4, r, fx, (200, 204, 210), 1.25)
    pie(d, "BCRA (API de estadísticas) y Banco Nación", "Variación contra la rueda anterior.")
    return guardar(im, destino)


def placa_chicago(datos: dict, destino: Path, hoy: date, seccion: str) -> Path | None:
    c = datos.get("chicago") or {}
    if not c:
        return None
    im, d = lienzo()
    fecha = max(v["fecha"] for v in c.values())
    cerrado = seccion == SECCION["cierre"]
    titulo = "Así cerró Chicago" if cerrado else "Chicago hoy"
    sub = (rotulo_fecha(fecha, hoy, "Cierre") if cerrado else rotulo_fecha(fecha, hoy, "Operación")) + \
        " · dólares por tonelada"
    y = encabezado(im, d, seccion, titulo, sub)
    for grano in ("soja", "maiz", "trigo"):
        v = c.get(grano)
        if not v:
            continue
        tarjeta(d, y, 168)
        d.text((D.X + 6, y + 20), M.NOMBRE[grano], font=D.fuente("bold", 42), fill=D.BLANCO)
        d.text((D.X + 6, y + 78), f"Contrato {v['contrato']} · {pesos(v['cent_bu'], 2)} ¢/bushel",
               font=D.fuente("regular", 26), fill=(170, 175, 182))
        precio = f"US$ {pesos(v['usd_t'], 1)}"
        f = D.fuente("negra", 54)
        d.text((W - D.X - d.textlength(precio, font=f), y + 16), precio, font=f, fill=D.NARANJA)
        if v.get("cambio_pct") is not None:
            flecha(d, W - D.X - 160, y + 100, v["cambio_pct"], 30)
        y += 184
    if y < Y_PIE - 150:
        texto = ("Chicago marca el precio internacional de la soja, el maíz y el trigo: lo que pasa ahí se "
                 "traslada a los precios que se pagan en Rosario.")
        fx, r = D.ajustar(d, texto, "regular", 29, 24, W - 2 * D.X, 3)
        D.escribir(d, D.X, y + 4, r, fx, (200, 204, 210), 1.25)
    pie(d, "CBOT / CME Group (vía Yahoo Finance)",
        "Futuros del contrato más cercano. Centavos de dólar por bushel convertidos a dólares por tonelada.")
    return guardar(im, destino)


def _xy(lon: float, lat: float, ancho: int = MAPA_ANCHO) -> tuple:
    lon0, lon1, lat0, lat1 = MAPA_CAJA
    k = ancho / (lon1 - lon0)
    import math
    ky = k / math.cos(math.radians((lat0 + lat1) / 2))
    return (lon - lon0) * k, (lat1 - lat) * ky


def armar_mapa_base(geojson: Path = None, log=print) -> Path:
    """El mapa de la región pampeana (provincias del IGN, vía georef) como PNG: se arma una vez y va
    al repo (`python -m agro.historias --mapa`)."""
    import httpx
    if geojson and Path(geojson).exists():
        datos = json.loads(Path(geojson).read_text(encoding="utf-8"))
    else:
        datos = httpx.get(MAPA_GEOJSON, timeout=60, follow_redirects=True).json()
    _, alto = _xy(MAPA_CAJA[0], MAPA_CAJA[2])
    im = Image.new("RGBA", (MAPA_ANCHO, round(alto)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in datos["features"]:
        g = f["geometry"]
        polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        bsas = (f["properties"].get("nombre") or "").startswith("Buenos Aires")
        for poli in polis:
            for k, anillo in enumerate(poli):
                pts = [_xy(x, y) for x, y in anillo]
                d.polygon(pts, fill=((52, 56, 63, 255) if bsas else (42, 45, 51, 255)) if k == 0 else (0, 0, 0, 0),
                          outline=(92, 97, 106, 255))
    MAPA.parent.mkdir(parents=True, exist_ok=True)
    im.save(MAPA)
    log(f"mapa: {MAPA} ({im.width}x{im.height})")
    return MAPA


def _color_mm(mm: float) -> tuple:
    for tope, color in ((1, (120, 125, 133)), (10, (130, 190, 255)), (25, (64, 140, 245)), (50, (40, 90, 220))):
        if mm < tope:
            return color
    return (150, 70, 210)


def placa_mapa(datos: dict, destino: Path, hoy: date, seccion: str) -> Path | None:
    pron = datos.get("pronostico") or {}
    dias = sorted({f for v in pron.values() for f in v if f >= hoy.isoformat()})[:5]
    if not dias or not MAPA.exists():
        return None
    im, d = lienzo()
    desde, hasta = date.fromisoformat(dias[0]), date.fromisoformat(dias[-1])
    y = encabezado(im, d, seccion if seccion != SECCION["mediodia"] else "TU ZONA EN EL MAPA",
                   "¿Dónde va a llover?",
                   f"Lluvia prevista del {DIAS[desde.weekday()][:3]} {desde.day} al {DIAS[hasta.weekday()][:3]} "
                   f"{hasta.day}/{hasta.month}, en milímetros")
    base = Image.open(MAPA).convert("RGBA")
    escala = min(1.0, (Y_PIE + 60 - y) / base.height)
    if escala < 1:
        base = base.resize((round(base.width * escala), round(base.height * escala)), Image.LANCZOS)
    x0 = (W - base.width) // 2
    im.alpha_composite(base, (x0, y))
    dd = ImageDraw.Draw(im)
    puntos = []
    for e, (nombre, lat, lon) in M.ESTACIONES.items():
        if e not in pron:
            continue
        mm = sum(pron[e].get(f, {}).get("mm", 0) for f in dias)
        px, py = _xy(lon, lat)
        puntos.append((x0 + px * escala, y + py * escala, mm, nombre, e in M.ZONA))
    for px, py, mm, nombre, zona in sorted(puntos, key=lambda p: p[2]):
        r = 16 + min(30, mm * 0.6)
        dd.ellipse((px - r, py - r, px + r, py + r), fill=_color_mm(mm) + (235,), outline=(255, 255, 255, 200), width=2)
        t = pesos(mm, 0)
        f = D.fuente("bold", 26 if r < 26 else 30)
        dd.text((px - dd.textlength(t, font=f) / 2, py - f.size * 0.62), t, font=f, fill=D.BLANCO)
        if zona:
            fn = D.fuente("medium", 24)
            dd.text((px + r + 6, py - 14), nombre, font=fn, fill=(225, 228, 233), stroke_width=3, stroke_fill=FONDO)
    cx, cy = _xy(M.CHIVILCOY[1], M.CHIVILCOY[0])
    cx, cy = x0 + cx * escala, y + cy * escala
    dd.regular_polygon((cx, cy, 13), 4, rotation=45, fill=D.NARANJA, outline=D.BLANCO)
    dd.text((cx - 150, cy + 10), "Chivilcoy", font=D.fuente("bold", 28), fill=D.NARANJA, stroke_width=3, stroke_fill=FONDO)
    pie(d, f"SMN, pronóstico por modelo para cada estación · emitido el {M.fecha_corta(hoy.isoformat())}",
        "Lluvia acumulada prevista en milímetros. El tamaño y el color del círculo crecen con la lluvia.")
    return guardar(im, destino)


def placa_alerta(alerta: dict, destino: Path, hoy: date) -> Path:
    im, d = lienzo()
    color = {"roja": (214, 48, 49), "naranja": (235, 130, 30), "amarilla": (240, 200, 40)}.get(alerta["nivel"], (240, 200, 40))
    y = encabezado(im, d, "ALERTA DEL SMN", f"Alerta {alerta['nivel']} por {alerta['evento'].lower()}",
                   "Para la zona: " + ", ".join(alerta.get("lugares") or []))
    d.rounded_rectangle((D.X - 24, y, W - D.X + 24, y + 14), radius=7, fill=color)
    y += 38

    def hora(t):
        try:
            x = datetime.fromisoformat(t)
            return f"{DIAS[x.weekday()]} {x.day}/{x.month} a las {x:%H:%M}"
        except ValueError:
            return t
    for rot, val in (("Desde", hora(alerta.get("desde", ""))), ("Hasta", hora(alerta.get("hasta", "")))):
        d.text((D.X, y), rot, font=D.fuente("regular", 30), fill=(170, 175, 182))
        d.text((D.X + 140, y - 4), val, font=D.fuente("bold", 36), fill=D.BLANCO)
        y += 56
    fx, r = D.ajustar(d, alerta.get("descripcion", ""), "regular", 34, 26, W - 2 * D.X, 9)
    D.escribir(d, D.X, y + 12, r, fx, (225, 228, 233), 1.28)
    pie(d, "Servicio Meteorológico Nacional (alertas vigentes)", "Seguí las actualizaciones en smn.gob.ar.")
    return guardar(im, destino)


def placa_titulares(items: list, destino: Path, hoy: date, seccion: str, titulo: str) -> Path | None:
    """items: [{titular, volanta, imagen}] de lo nuestro ya publicado."""
    if not items:
        return None
    im, d = lienzo()
    y = encabezado(im, d, seccion, titulo, fecha_larga(hoy).capitalize())
    for i, it in enumerate(items[:4]):
        if y > Y_PIE - 180:
            break
        tarjeta(d, y, 196)
        x = D.X + 6
        if it.get("imagen") and Path(it["imagen"]).exists():
            foto = D.cubrir(Image.open(it["imagen"]).convert("RGB"), 200, 164)
            mascara = Image.new("L", foto.size, 0)
            ImageDraw.Draw(mascara).rounded_rectangle((0, 0, *foto.size), radius=16, fill=255)
            im.paste(foto, (x - 6, y + 16), mascara)
            x += 218
        d.text((x, y + 18), (it.get("volanta") or "Agro").upper(), font=D.fuente("bold", 24), fill=D.NARANJA)
        ft, rt = D.ajustar(d, it["titular"], "bold", 38, 28, W - D.X - x, 3, alto_max=130)
        D.escribir(d, x, y + 54, rt, ft, D.BLANCO, 1.12)
        y += 212
    pie(d, "@diarioyradioagro", "Las notas completas, en diariolacampaña.com.ar, sección Agro.")
    return guardar(im, destino)


def placa_novedad(item: dict, destino: Path, hoy: date, seccion: str) -> Path | None:
    """La pieza que acaba de salir (reel o carrusel) con su portada 4:5, para llevar al perfil."""
    if not item or not item.get("portada") or not Path(item["portada"]).exists():
        return None
    im, d = lienzo()
    carrusel = item.get("formato") == "carrusel"
    y = encabezado(im, d, seccion, "Nuevo carrusel en el perfil" if carrusel else "Nuevo reel en el perfil", "")
    port = Image.open(item["portada"]).convert("RGB")
    ancho = W - 2 * D.X
    port = port.resize((ancho, round(port.height * ancho / port.width)), Image.LANCZOS)
    if y + port.height > Y_PIE - 90:
        port = port.resize((round(port.width * (Y_PIE - 90 - y) / port.height), Y_PIE - 90 - y), Image.LANCZOS)
    mascara = Image.new("L", port.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, *port.size), radius=26, fill=255)
    im.paste(port, ((W - port.width) // 2, y), mascara)
    t = "Deslizá e informate en el carrusel" if carrusel else "Miralo completo en el perfil"
    f = D.fuente("bold", 36)
    d.text(((W - d.textlength(t, font=f)) / 2, y + port.height + 22), t, font=f, fill=D.VERDE)
    pie(d, "@diarioyradioagro", "")
    return guardar(im, destino)


def placa_semana(mem: dict, clave: str, destino: Path, hoy: date, seccion: str) -> Path | None:
    """«Los números de la semana»: el último dato contra el de hace una semana."""
    filas, fuente, fecha = [], "", ""
    if clave == "granos":
        serie = (mem.get("mercado") or {}).get("pizarra") or {}
        if not serie:
            return None
        fecha = max(serie)
        previo = M.anterior(mem, "pizarra", fecha, dias=7)
        for g in ("soja", "maiz", "trigo", "girasol"):
            v = (serie[fecha].get("productos") or {}).get(g)
            if v:
                ant = ((previo[1].get("productos") or {}).get(g) or {}).get("ars") if previo else None
                filas.append((M.NOMBRE[g], f"${pesos(v['ars'])}", M.variacion(v["ars"], ant), "por tonelada"))
        fuente = "Cámara Arbitral de Cereales de Rosario (pizarra)"
        titulo = "Los granos en la semana"
    elif clave == "dolar":
        serie = (mem.get("mercado") or {}).get("a3500") or {}
        if not serie:
            return None
        fecha = max(serie)
        previo = M.anterior(mem, "a3500", fecha, dias=7)
        filas.append(("Mayorista BCRA", f"${pesos(serie[fecha]['valor'], 2)}",
                      M.variacion(serie[fecha]["valor"], previo[1]["valor"] if previo else None), "pesos por dólar"))
        bna = (mem.get("mercado") or {}).get("bna") or {}
        if bna:
            fb = max(bna)
            pb = M.anterior(mem, "bna", fb, dias=7)
            filas.append(("BNA billete (venta)", f"${pesos(bna[fb]['billete']['venta'], 2)}",
                          M.variacion(bna[fb]["billete"]["venta"], pb[1]["billete"]["venta"] if pb else None),
                          "pesos por dólar"))
        fuente = "BCRA (Com. A 3500) y Banco Nación"
        titulo = "El dólar en la semana"
    else:
        fuente = "CBOT / CME Group (vía Yahoo Finance), contrato más cercano"
        titulo = "Chicago en la semana"
        for g in ("soja", "maiz", "trigo"):
            serie = (mem.get("mercado") or {}).get(f"chicago_{g}") or {}
            if not serie:
                continue
            f = max(serie)
            fecha = max(fecha, f)
            previo = M.anterior(mem, f"chicago_{g}", f, dias=7)
            filas.append((M.NOMBRE[g], f"US$ {pesos(serie[f]['usd_t'], 1)}",
                          M.variacion(serie[f]["usd_t"], previo[1]["usd_t"] if previo else None), "por tonelada"))
    if not filas:
        return None
    im, d = lienzo()
    y = encabezado(im, d, "LOS NÚMEROS DE LA SEMANA", titulo,
                   f"Último dato: {M.fecha_corta(fecha)} · variación contra una semana antes")
    for nombre, valor, var, unidad in filas:
        tarjeta(d, y, 160)
        d.text((D.X + 6, y + 20), nombre, font=D.fuente("bold", 40), fill=D.BLANCO)
        d.text((D.X + 6, y + 74), unidad, font=D.fuente("regular", 26), fill=(170, 175, 182))
        f = D.fuente("negra", 52)
        d.text((W - D.X - d.textlength(valor, font=f), y + 16), valor, font=f, fill=D.NARANJA)
        if var is not None:
            flecha(d, W - D.X - 170, y + 94, var, 30)
        y += 176
    pie(d, fuente, f"Dato del {M.fecha_corta(fecha)}.")
    return guardar(im, destino)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La tanda
# ─────────────────────────────────────────────────────────────────────────────────────────────
def armar_tanda(bloque: str, datos: dict, mem: dict, carpeta: Path, momento: datetime, recientes: list,
                novedad: dict = None, alertas_ya: set = None) -> list:
    """[{tipo, archivo, clave}] de la tanda `bloque`, en orden: las alertas nuevas primero."""
    hoy = momento.date()
    seccion = SECCION.get(bloque, "EL CAMPO HOY")
    carpeta = Path(carpeta)
    salida = []
    for a in (datos.get("alertas") or [])[:MAX_ALERTAS]:
        clave = f"alerta|{a['evento']}|{a['nivel']}|{a['desde']}"
        if clave in (alertas_ya or set()):
            continue
        salida.append({"tipo": "alerta", "clave": clave,
                       "archivo": str(placa_alerta(a, carpeta / f"historia_{len(salida):02d}_alerta.jpg", hoy))})
    for tipo in plan(bloque, hoy):
        destino = carpeta / f"historia_{len(salida):02d}_{tipo}.jpg"
        if tipo == "clima":
            r = placa_clima(datos, destino, hoy, seccion)
        elif tipo == "clima_manana":
            r = placa_clima(datos, destino, hoy, seccion, dia=hoy + timedelta(days=1))
        elif tipo == "granos":
            r = placa_granos(datos, mem, destino, hoy, seccion)
        elif tipo == "dolar":
            r = placa_dolar(datos, mem, destino, hoy, seccion)
        elif tipo == "chicago":
            r = placa_chicago(datos, destino, hoy, seccion)
        elif tipo == "mapa":
            r = placa_mapa(datos, destino, hoy, seccion)
        elif tipo == "titulares":
            r = placa_titulares(recientes, destino, hoy, seccion, "Lo que tenés que saber")
        elif tipo == "resumen":
            r = placa_titulares(recientes, destino, hoy, seccion, "Hoy en Diario y Radio Agro")
        elif tipo == "novedad":
            r = placa_novedad(novedad, destino, hoy, seccion)
        elif tipo.startswith("semana_"):
            r = placa_semana(mem, tipo.split("_", 1)[1], destino, hoy, seccion)
        else:
            r = None
        if r:
            salida.append({"tipo": tipo, "archivo": str(r), "clave": tipo})
    return salida


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    if "--mapa" in sys.argv:
        armar_mapa_base(sys.argv[sys.argv.index("--mapa") + 1] if len(sys.argv) > sys.argv.index("--mapa") + 1 else None)
