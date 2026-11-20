# -*- coding: utf-8 -*-
"""LOS PERFILES PRODUCTIVOS de Chivilcoy y los partidos vecinos: carruseles informativos de @diarioyradioagro
(20/11/2026).

Pedido del editor: «carruseles informativos [como los de una inmobiliaria rural grande] … como para hacer para
Chivilcoy y alrededores». Se toma el formato del «valor de la tierra» de una zona, sin precios (no tenemos una
fuente confiable de valores por hectárea) y con lo que sí tenemos, de fuentes públicas vía ArgenFields (INTA,
Ministerio de Agricultura, NOAA, IGN): agro/datos/argenfields.json y los contornos de georef (agro/datos/partidos.json).

Estilo: foto aérea del campo oscurecida con un tinte verde y curvas de nivel, títulos centrados en Anton con la
palabra clave en dorado, el marcador de ubicación y una etiqueta con las hectáreas. Láminas:

    1. Tapa: el partido, «Buenos Aires», «Perfil productivo» y sus hectáreas.
    2. Dónde está: el mapa de la zona con el partido resaltado y a cuántos km queda de Buenos Aires.
    3. La tierra: índice de productividad, su puesto en la provincia y cuánto es clase I a III.
    4. El agua: lluvia media, balance, la limitante por exceso de agua y la última emergencia.
    5. Qué se siembra: los cultivos de la última campaña.
    6. Cuánto rinde: soja, trigo y maíz contra el promedio bonaerense.
    7. El Niño (si la copia es reciente).
    8. Cierre: «¿Tenés campo en …?» y la fuente.

Un partido por vez, Chivilcoy primero (estado/agro_perfil.json); martes y viernes a las 12:15 (workflow
agro_perfil.yml). Solo @diarioyradioagro, Instagram (carrusel) y Facebook (álbum). AGRO_PERFIL=0 lo apaga.

    python -m agro.perfil                     # simula el que toca
    python -m agro.perfil --partido bragado   # uno a elección (simulando)
    python -m agro.perfil --publicar
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import diseno as D  # noqa: E402
from agro import impacto as I  # noqa: E402
from agro import reel_zona as RZ  # noqa: E402

TZ_AR = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).resolve().parent.parent
MEMORIA = RAIZ / "estado" / "agro_perfil.json"
SALIDA = RAIZ / "salida_agro"
PARTIDOS = Path(__file__).resolve().parent / "datos" / "partidos.json"
W, H = D.W, D.H45
VERDE_NOCHE = (18, 34, 27)
DORADO = (232, 178, 70)
BLANCO = (255, 255, 255)
GRIS = (206, 212, 208)
TENUE = (140, 156, 148)
CABA = (-34.6037, -58.3816)
ORDEN = ("chivilcoy", "alberti", "bragado", "chacabuco", "suipacha", "25-de-mayo", "mercedes", "navarro",
         "san-andres-de-giles", "carmen-de-areco")
FUENTE = "Fuente: ArgenFields, con datos del INTA, el Ministerio de Agricultura y NOAA"


def activo() -> bool:
    return (os.environ.get("AGRO_PERFIL") or "1").strip() != "0"


def _sin_tildes(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def _coma(x, dec=1):
    return RZ._coma(x, dec)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El fondo: foto aérea + tinte + curvas de nivel
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _curvas(im: Image.Image, alfa: int = 26) -> None:
    """Curvas de nivel suaves (decorativas), como en las placas de campos."""
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for k in range(14):
        cx, cy = W * (0.2 + 0.6 * ((k * 37) % 10) / 10), H * (0.15 + 0.7 * ((k * 53) % 10) / 10)
        for r in range(40, 520, 46):
            pts = []
            for a in range(0, 361, 8):
                ang = math.radians(a)
                rr = r * (1 + 0.18 * math.sin(3 * ang + k) + 0.08 * math.cos(5 * ang + k * 2))
                pts.append((cx + rr * math.cos(ang), cy + rr * 0.72 * math.sin(ang)))
            d.line(pts, fill=(230, 220, 190, alfa), width=2)
    im.alpha_composite(capa)


def fondo(foto=None, oscuro: int = 150) -> Image.Image:
    im = Image.new("RGBA", (W, H), VERDE_NOCHE + (255,))
    if foto and Path(str(foto)).is_file():
        f = ImageOps.fit(Image.open(foto).convert("RGB"), (W, H), Image.LANCZOS, centering=(0.5, 0.5))
        im.paste(f, (0, 0))
        im.alpha_composite(Image.new("RGBA", (W, H), VERDE_NOCHE + (oscuro,)))
    _curvas(im)
    return im


def _marca_pie(im: Image.Image, y: int = H - 120) -> None:
    lg = D.lockup("grafito", 64)
    im.alpha_composite(lg, ((W - lg.width) // 2, y))


def _centrado(d, y, texto, f, color):
    d.text(((W - d.textlength(texto, font=f)) / 2, y), texto, font=f, fill=color)


def _titulo(im, y: int, texto: str, dorado: str = "", tope: int = 104, piso: int = 60, renglones: int = 3) -> int:
    """El título centrado en Anton, con `dorado` en dorado. Devuelve la y de abajo."""
    d = ImageDraw.Draw(im)
    f, r, pal = I.ajustar(d, texto, W - 180, renglones, tope, piso)
    marca = I._marcas(pal, dorado.upper())
    esp = d.textlength(" ", font=f)
    alto = round(f.size * 1.04)
    for linea in r:
        ancho = sum(d.textlength(p, font=f) for p, _ in linea) + esp * (len(linea) - 1)
        x = (W - ancho) / 2
        for p, i in linea:
            d.text((x, y), p, font=f, fill=DORADO if marca[i] is True else BLANCO)   # el perfil: blanco y dorado
            x += d.textlength(p, font=f) + esp
        y += alto
    return y + round(f.size * 0.2)


def _pin(d, cx, cy, h=86, color=BLANCO):
    r = h * 0.36
    d.ellipse((cx - r, cy - h + 0, cx + r, cy - h + 2 * r), outline=color, width=6)
    d.line((cx - r * 0.86, cy - h + r * 1.5, cx, cy, cx + r * 0.86, cy - h + r * 1.5), fill=color, width=6)
    d.ellipse((cx - r * 0.34, cy - h + r * 0.66, cx + r * 0.34, cy - h + r * 1.34), outline=color, width=5)


def _pastilla(d, cy, texto, f=None):
    f = f or D.fuente("bold", 34)
    w = d.textlength(texto, font=f) + 56
    d.rounded_rectangle(((W - w) / 2, cy, (W + w) / 2, cy + 62), radius=31, fill=DORADO)
    _centrado(d, cy + 12, texto, f, VERDE_NOCHE)


def _guardar(im, destino) -> str:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return str(destino)


def _numero_grande(d, y, numero: str, unidad: str = "", tam: int = 190) -> int:
    f = I.anton(tam)
    fu = D.fuente("bold", 52)
    ancho = d.textlength(numero, font=f) + (d.textlength(" " + unidad, font=fu) if unidad else 0)
    x = (W - ancho) / 2
    d.text((x, y), numero, font=f, fill=DORADO)
    if unidad:
        d.text((x + d.textlength(numero, font=f) + 14, y + tam * 0.72), unidad, font=fu, fill=BLANCO)
    return y + f.getbbox(numero)[3] + 22


def _parrafo(d, y, texto, f=None, color=GRIS, ancho=W - 200, salto=58) -> int:
    f = f or D.fuente("regular", 40)
    for linea in D.renglones(d, texto, f, ancho):
        _centrado(d, y, linea, f, color)
        y += salto
    return y


def _pie(im, i, n, fuente: str = FUENTE):
    d = ImageDraw.Draw(im)
    f = D.fuente("regular", 22)
    _centrado(d, H - 54, fuente, f, TENUE)
    _centrado(d, 60, f"{i}/{n}", D.fuente("bold", 28), TENUE)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El mapa de la zona con el partido resaltado
# ─────────────────────────────────────────────────────────────────────────────────────────────
def mapa(slug: str, lado: int = 860) -> Image.Image:
    try:
        polis = json.loads(PARTIDOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        polis = {}
    clave = slug.replace("-", " ")
    todos = [(k, a) for k, v in polis.items() for a in v["anillos"]]
    im = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    if not todos:
        return im
    xs = [x for _, a in todos for x, _ in a]
    ys = [y for _, a in todos for _, y in a]
    lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
    k_lon = math.cos(math.radians((lat0 + lat1) / 2))
    escala = (lado - 60) / max((lon1 - lon0) * k_lon, lat1 - lat0)
    ox = (lado - (lon1 - lon0) * k_lon * escala) / 2
    oy = (lado - (lat1 - lat0) * escala) / 2

    def p(lon, lat):
        return ox + (lon - lon0) * k_lon * escala, oy + (lat1 - lat) * escala
    d = ImageDraw.Draw(im)
    for k, a in todos:
        d.polygon([p(x, y) for x, y in a], fill=(DORADO + (215,)) if k == clave else (255, 255, 255, 22),
                  outline=(255, 255, 255, 170))
    f = D.fuente("bold", 26)
    for k, v in polis.items():
        a = max(v["anillos"], key=len)
        cx, cy = p(sum(x for x, _ in a) / len(a), sum(y for _, y in a) / len(a))
        nombre = v["nombre"]
        color = VERDE_NOCHE if k == clave else (235, 238, 236)
        f_k = D.fuente("bold", 30) if k == clave else f
        d.text((cx - d.textlength(nombre, font=f_k) / 2, cy - 16), nombre, font=f_k, fill=color)
    return im


def centroide(slug: str) -> tuple | None:
    try:
        v = json.loads(PARTIDOS.read_text(encoding="utf-8"))[slug.replace("-", " ")]
    except (OSError, ValueError, KeyError):
        return None
    a = max(v["anillos"], key=len)
    return sum(y for _, y in a) / len(a), sum(x for x, _ in a) / len(a)


def km_a_caba(slug: str) -> int | None:
    c = centroide(slug)
    if not c:
        return None
    la1, lo1, la2, lo2 = map(math.radians, (c[0], c[1], *CABA))
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(a)) / 10) * 10


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Las láminas
# ─────────────────────────────────────────────────────────────────────────────────────────────
def laminas(p: dict, foto, carpeta: Path, credito: str = "") -> list:
    nombre = p.get("partido") or p["slug"]
    n_partido = nombre.upper()
    archivos = []
    pasos = []

    def tapa():
        # 20/11/2026 (el editor: «no inventes una portada con fotos… directo a la info con el mapa… con el título
        # con SEO y buen hook»): la tapa es el mapa con el partido resaltado y el título con la palabra clave primero.
        im = fondo(None)
        d = ImageDraw.Draw(im)
        y = _titulo(im, 96, f"Campo en {nombre}: lo que tenés que saber", f"Campo en {nombre}", 92, 60, 3)
        _centrado(d, y + 14, "Suelo, agua, siembra y rindes del partido", D.fuente("medium", 38), GRIS)
        y += 20
        alto = H - (y + 60) - 190
        m = mapa(p["slug"], min(860, alto))
        im.alpha_composite(m, ((W - m.width) // 2, y + 50))
        yb = y + 60 + m.height
        datos = [f"{_coma(p['hectareas'], 0)} ha"] if p.get("hectareas") else []
        km = km_a_caba(p["slug"])
        if datos:
            _pastilla(d, yb, datos[0])
        if km:
            _centrado(d, yb + 78, f"A unos {km} km de la Ciudad de Buenos Aires", D.fuente("medium", 32), GRIS)
        return im
    pasos.append(tapa)

    if p.get("productividad"):
        def tierra():
            im = fondo(None)
            d = ImageDraw.Draw(im)
            y = _titulo(im, 150, "La calidad de la tierra", "tierra", 96, 60, 2)
            y = _numero_grande(d, y + 30, str(p["productividad"]), "/100")
            y = _parrafo(d, y, f"Índice de productividad del suelo (INTA): puesto {p.get('puesto')} de "
                               f"{p.get('de')} partidos bonaerenses. El promedio de la provincia es "
                               f"{p.get('productividad_provincia')}.")
            if p.get("clase_1_3"):
                y = _numero_grande(d, y + 50, f"{p['clase_1_3']}%", "", 130)
                _parrafo(d, y - 10, "de la superficie es clase I a III: apta para agricultura, con limitaciones de "
                                    "leves a moderadas.")
            return im
        pasos.append(tierra)

    if p.get("lluvia"):
        def agua():
            im = fondo(None)
            d = ImageDraw.Draw(im)
            y = _titulo(im, 150, "El agua", "agua", 110, 60, 1)
            y = _numero_grande(d, y + 20, _coma(p["lluvia"], 0), "mm/año")
            y = _parrafo(d, y, f"llueven en promedio. El balance hídrico es de {_coma(p.get('balance'), 0)} mm por "
                               "año: la lluvia menos lo que pierden el suelo y los cultivos.")
            agua_ex = next((v for k, v in p.get("limitantes") or [] if k.lower().startswith("exceso de agua")), None)
            if agua_ex:
                y = _numero_grande(d, y + 40, f"{agua_ex:.0f}%", "", 120)
                y = _parrafo(d, y - 10, "del partido tiene como limitante el exceso de agua o el anegamiento.")
            em = (p.get("emergencias") or {}).get("lista") or []
            if em:
                _parrafo(d, y + 30, f"Última emergencia agropecuaria: {em[0]['desde']} – {em[0]['hasta']}, por "
                                    f"{em[0]['motivo']}.", D.fuente("medium", 34), DORADO, salto=48)
            return im
        pasos.append(agua)

    cultivos = [(c, v) for c, v in p.get("cultivos_hoy") or [] if v and v >= 1]
    if cultivos:
        def siembra():
            im = fondo(None)
            d = ImageDraw.Draw(im)
            y = _titulo(im, 150, "Qué se siembra", "siembra", 100, 60, 1)
            if p.get("sembrado"):
                _centrado(d, y + 10, f"En la campaña 2024/25 se sembró el {p['sembrado']}% del partido",
                          D.fuente("medium", 38), GRIS)
            y += 110
            tope = max(v for _, v in cultivos)
            for c, v in cultivos[:4]:
                d.text((110, y), c, font=D.fuente("bold", 48), fill=BLANCO)
                txt = f"{_coma(v)}%"
                f = I.anton(64)
                d.text((W - 110 - d.textlength(txt, font=f), y - 12), txt, font=f, fill=DORADO)
                d.rounded_rectangle((110, y + 70, 110 + (W - 220) * v / tope, y + 90), radius=10, fill=DORADO)
                d.rounded_rectangle((110, y + 70, W - 110, y + 90), radius=10, outline=(110, 130, 120))
                y += 150
            _parrafo(d, y + 20, "Mapa Nacional de Cultivos del INTA.", D.fuente("regular", 28), TENUE)
            return im
        pasos.append(siembra)

    rindes = [(c, (p.get("rindes") or {}).get(c)) for c in ("soja", "trigo", "maiz")]
    rindes = [(c, r) for c, r in rindes if r and r.get("promedio")]
    if len(rindes) >= 2:
        def rinde():
            im = fondo(None)
            d = ImageDraw.Draw(im)
            y = _titulo(im, 150, "Cuánto rinde", "rinde", 100, 60, 1)
            _centrado(d, y + 6, "Promedio de las últimas cinco campañas", D.fuente("medium", 36), GRIS)
            y += 110
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(capa)
            for k in range(len(rindes)):
                yy = y + k * 230
                dc.rounded_rectangle((90, yy, W - 90, yy + 200), radius=24, fill=(255, 255, 255, 20),
                                     outline=(255, 255, 255, 60), width=2)
            im.alpha_composite(capa)
            d = ImageDraw.Draw(im)
            for c, r in rindes:
                d.text((140, y + 36), RZ.NOMBRE_CULTIVO[c].capitalize(), font=D.fuente("bold", 52), fill=BLANCO)
                vs = r.get("vs_provincia")
                txt_vs = ("igual que la provincia" if not vs else
                          f"{abs(vs)}% {'más' if vs > 0 else 'menos'} que la provincia")
                d.text((140, y + 112), txt_vs, font=D.fuente("medium", 32),
                       fill=DORADO if (vs or 0) > 0 else GRIS)
                num = _coma(r["promedio"])
                f = I.anton(110)
                fu = D.fuente("bold", 34)
                x = W - 140 - d.textlength("qq/ha", font=fu)
                d.text((x, y + 116), "qq/ha", font=fu, fill=GRIS)
                d.text((x - 16 - d.textlength(num, font=f), y + 30), num, font=f, fill=DORADO)
                y += 230
            return im
        pasos.append(rinde)

    e = p.get("enso") or {}
    if e.get("estado") in ("El Niño", "La Niña") and (e.get("tabla") or {}).get("soja"):
        def nino():
            im = fondo(None)
            d = ImageDraw.Draw(im)
            k = "nino" if e["estado"] == "El Niño" else "nina"
            y = _titulo(im, 150, f"Hoy hay {e['estado']}", e["estado"], 100, 60, 2)
            v = e["tabla"]["soja"][k]
            y = _numero_grande(d, y + 20, f"{v:+.0f}%".replace("-", "−"), "")
            _parrafo(d, y, f"se apartó de su tendencia el rinde de la soja de {nombre} en los años de {e['estado']} "
                           "desde 1980. Es un promedio histórico, no un pronóstico.")
            return im
        pasos.append(nino)

    def cierre():
        im = fondo(None)
        d = ImageDraw.Draw(im)
        y = _titulo(im, 330, f"¿Tenés campo en {nombre}?", nombre, 110, 64, 3)
        _parrafo(d, y + 20, "Contanos cómo viene tu campaña en los comentarios. Guardalo y compartilo.",
                 D.fuente("medium", 42), GRIS, salto=60)
        _marca_pie(im, H - 300)
        _centrado(d, H - 210, D.USUARIO, D.fuente("bold", 40), DORADO)
        return im
    pasos.append(cierre)

    n = len(pasos)
    for i, fn in enumerate(pasos, 1):
        im = fn()
        if 1 < i:
            _pie(im, i, n)
        archivos.append(_guardar(im, Path(carpeta) / f"perfil_{p['slug']}_c{i:02d}.jpg"))
    return archivos


def caption(p: dict, credito: str = "") -> str:
    nombre = p.get("partido") or p["slug"]
    partes = [f"📍 {nombre}: perfil productivo del partido."]
    datos = []
    if p.get("productividad"):
        datos.append(f"Su suelo tiene un índice de productividad de {p['productividad']}/100 (puesto {p.get('puesto')} "
                     f"de {p.get('de')} en la provincia)")
    if p.get("lluvia"):
        datos.append(f"llueven {_coma(p['lluvia'], 0)} mm por año")
    soja = ((p.get("rindes") or {}).get("soja") or {}).get("promedio")
    if soja:
        datos.append(f"la soja rinde {_coma(soja)} qq/ha de promedio")
    if datos:
        partes.append("; ".join(datos) + ".")
    partes.append(f"📲 ¿Tenés campo en {nombre}? Contanos cómo viene tu campaña en los comentarios. Guardalo y "
                  "compartilo.")
    partes.append(FUENTE + " (argenfields.com). Son promedios del partido: cada lote es distinto.")
    if credito:
        partes.append(f"📷 Imagen ilustrativa: {credito}.")
    tag = "#" + "".join(w.capitalize() for w in _sin_tildes(nombre).replace("25", "Veinticinco").split())
    partes.append(f"{tag} #Campo #Agro #Suelo #BuenosAires")
    return "\n\n".join(partes)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La foto (un cuadro de un video aéreo del banco) y la corrida
# ─────────────────────────────────────────────────────────────────────────────────────────────
def foto_aerea(carpeta: Path, usados: dict, ahora: datetime, log=print) -> tuple:
    from agro import banco_video as BVI
    v = RZ.elegir_video("cosecha", usados, ahora) or RZ.elegir_video("campo", usados, ahora)
    if not v:
        return None, ""
    BVI.anotar(usados, v, ahora)
    clip = BVI.bajar(v, Path(carpeta) / f"banco_{v['archivo']}")
    if not clip:
        return None, ""
    jpg = Path(carpeta) / "foto_aerea.jpg"
    subprocess.run([RZ._ffmpeg(), "-loglevel", "error", "-y", "-ss", "6", "-i", str(clip), "-frames:v", "1",
                    str(jpg)], check=False)
    return (jpg if jpg.is_file() else None), BVI.credito(v)


def cargar(ruta=None) -> dict:
    try:
        return json.loads(Path(ruta or MEMORIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"hechos": []}


def guardar(mem, ruta=None):
    ruta = Path(ruta or MEMORIA)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=1), encoding="utf-8")


def siguiente(mem: dict, af: dict) -> str | None:
    """El partido que toca: el que nunca salió, en ORDEN; si salieron todos, el que salió hace más tiempo."""
    hechos = {h["slug"]: h["cuando"] for h in mem.get("hechos") or [] if h.get("publicado")}
    disponibles = [s for s in ORDEN if s in (af.get("partidos") or {})]
    nuevos = [s for s in disponibles if s not in hechos]
    if nuevos:
        return nuevos[0]
    return min(disponibles, key=lambda s: hechos.get(s, "")) if disponibles else None


def corrida(publicar: bool, slug: str = "", ahora: datetime = None, ruta_mem=None, af=None, log=print,
            publicador=None, foto_fn=None) -> dict:
    ahora = ahora or datetime.now(TZ_AR)
    inf = {"cuando": ahora.isoformat(timespec="minutes"), "estado": ""}
    if not activo():
        inf["estado"] = "apagado"
        return inf
    mem = cargar(ruta_mem)
    af = af if af is not None else RZ.datos_argenfields()
    # Fuera de 12:00-13:30 no publica (el respaldo de GitHub puede llegar con horas de atraso). 20/11/2026: de las
    # 17:30 a las 12:15, porque a las 17:30 ahora sale una noticia.
    if publicar and not slug and not (ahora.hour == 12 or (ahora.hour == 13 and ahora.minute <= 30)):
        inf["estado"] = "fuera_de_hora"
        return inf
    if publicar and not slug and any(h.get("dia") == ahora.date().isoformat() and h.get("publicado")
                                     for h in mem.get("hechos") or []):
        inf["estado"] = "ya_salio"
        return inf
    slug = slug or siguiente(mem, af)
    p = (af.get("partidos") or {}).get(slug or "")
    if not p:
        inf["estado"] = "sin_datos"
        return inf
    inf["partido"] = slug
    carpeta = SALIDA / f"perfil_{ahora:%Y-%m-%d_%H%M}_{slug}"
    carpeta.mkdir(parents=True, exist_ok=True)
    usados = mem.setdefault("banco_usados", {})
    # Sin foto de relleno (20/11/2026): todo es mapa y datos.
    foto, credito = (foto_fn(carpeta, usados, ahora, log) if foto_fn else (None, ""))
    archivos = laminas(p, foto, carpeta, credito)
    texto = caption(p, credito)
    (carpeta / "texto.txt").write_text(texto, encoding="utf-8")
    inf.update(archivos=archivos, texto=texto)
    log(f"Perfil de {p.get('partido')}: {len(archivos)} láminas → {carpeta}")
    if not publicar:
        inf["estado"] = "simulado"
        return inf
    anotado = {"slug": slug, "dia": ahora.date().isoformat(), "cuando": ahora.isoformat(timespec="minutes"),
               "publicado": None}
    mem.setdefault("hechos", []).append(anotado)
    guardar(mem, ruta_mem)
    pieza = {"id": f"perfil-{slug}-{ahora:%Y%m%d}", "datos": True, "formato": "carrusel",
             "guion": {"titular": f"{p.get('partido')}: perfil productivo", "bajada": "", "descripcion": texto,
                       "hashtags": [], "volanta": "Perfil productivo"},
             "carrusel": {"archivos": archivos, "caption": texto}, "portada": archivos[0]}
    if publicador is None:
        from agro import publicar as PUB
        publicador = PUB.publicar_carrusel
    res = publicador(pieza, log=log)
    ok = [r for r in ("instagram", "facebook") if isinstance(res.get(r), dict) and res[r].get("id")]
    anotado["publicado"] = {r: res[r] for r in ok} or None
    guardar(mem, ruta_mem)
    inf["estado"] = "ok" if ok else "fallo"
    inf["resultado"] = res
    return inf


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--partido", default="")
    a = ap.parse_args()
    inf = corrida(a.publicar, a.partido)
    print(f"## Perfil productivo ({inf.get('cuando')})\n\n- Estado: {inf.get('estado')}\n- Partido: {inf.get('partido')}")
    for red, v in (inf.get("resultado") or {}).items():
        if isinstance(v, dict):
            print(f"- {red}: {v.get('id') or v.get('error')}")
    if inf.get("texto"):
        print("\n```\n" + inf["texto"] + "\n```")
    if a.publicar and inf.get("estado") == "fallo":
        sys.exit(1)


if __name__ == "__main__":
    main()
