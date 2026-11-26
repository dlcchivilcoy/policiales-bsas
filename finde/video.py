# -*- coding: utf-8 -*-
"""GRÁFICOS, SONIDO Y RENDER: el reel 9:16 (1080 × 1920) de una ficha de finde/temas.py.

Dos estilos, tomados de las referencias que pasó el editor (26/11/2026):

  PAPEL (sábado, la ciudad) — como los Shorts de mapas de datos («El Mapa Lo Explica»): fondo claro de papel, las
  cifras y las palabras clave en una serif gruesa naranja (Fraunces), etiquetas en pastillas naranjas, el mapa claro
  con Chivilcoy remarcado, la comparación «Chivilcoy frente a…» en dos tarjetas (blanca y naranja) y los subtítulos
  en mayúscula negra con la palabra que se dice en una caja.

  CAMPO (domingo, el territorio) — como los reels de @agroempresario.oficial: un video del campo de fondo,
  oscurecido; el bloque alineado a la izquierda: una pastilla con un punto y el tema, el número GIGANTE en blanco con
  la unidad en color, una línea chica de contexto en gris y una barra de progreso fina abajo. En naranja (la marca del
  diario), no en verde.

Escenas (cada una dura lo que su narración, con un mínimo): gancho → opciones (con cuenta 3-2-1) → respuesta (la
correcta se pinta y el número cuenta hasta su valor) → mapa (con escala) → «frente a» (la comparación) → tu turno →
placa final. Siempre a la vista: la marca, la FUENTE con el año y los subtítulos, dentro de los márgenes seguros de
Instagram (arriba 150 px; abajo, desde los subtítulos, libre para los botones y el texto del posteo).

Sonido: la voz, una base musical suave que baja cuando habla y los efectos (soplido en cada pase, pops, tics de la
cuenta, campanita en la respuesta). Video H.264 + audio AAC.
"""
from __future__ import annotations

import math
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from agro import diseno as D
from agro import mapa_zona as MZ
from agro import movimiento as MV
from finde import voz as VZ

W, H = 1080, 1920
FPS = 30
SR = VZ.SR
X0, X1 = 80, 1000
Y_SUB = 1395                         # los subtítulos: arriba de los ~330 px de abajo que tapa Instagram
Y_BARRA = 1600                       # la barra de progreso fina (estilo campo)
NARANJA = (253, 133, 17)             # #FD8511, el del isologo
NARANJA_OSC = (214, 92, 14)          # sobre papel: la serif y las pastillas (contraste con texto blanco)
NEGRO = (26, 26, 29)
BLANCO = (255, 255, 255)
PAPEL = (245, 240, 231)
MARCA = Path(__file__).resolve().parent / "marca"
PLACA_FINAL = Path(__file__).resolve().parent.parent / "estetica_bot" / "placa_final.png"
ENTRADA_VOZ = 0.3
MINIMOS = {"gancho": 3.0, "opciones": 5.0, "revelacion": 4.0, "mapa": 5.5, "contexto": 4.4, "cierre": 3.6,
           "placa": 1.8, "bloque": 4.5}
CUENTA = 2.4
CARTAS_Y = (600, 820, 1040)          # las tres opciones

ESTILOS = {
    "papel": dict(texto=NEGRO, tenue=(112, 106, 98), acento=NARANJA_OSC, caja_sub=NEGRO, txt_caja=BLANCO,
                  mapa_fondo=(232, 224, 210), mapa_linea=(150, 141, 128), mapa_txt=NEGRO, mapa_lo=(238, 222, 196),
                  mapa_hi=(226, 98, 22), chiv_borde=NEGRO, sombra=False),
    "campo": dict(texto=BLANCO, tenue=(190, 192, 196), acento=NARANJA, caja_sub=NARANJA, txt_caja=NEGRO,
                  mapa_fondo=(52, 54, 60), mapa_linea=(18, 19, 22), mapa_txt=BLANCO, mapa_lo=(92, 66, 46),
                  mapa_hi=(253, 150, 40), chiv_borde=BLANCO, sombra=True),
}


def estilo_de(ficha: dict) -> str:
    """26/11/2026 (el editor, después de ver los dos de prueba): «armá todos con la estética del reel del suelo»:
    los dos días van en estilo CAMPO. El sábado no hay videos de la ciudad en el banco: va el fondo oscuro animado.
    FINDE_ESTILO=papel vuelve el sábado al estilo claro."""
    import os
    if ficha.get("dia") == "sabado" and (os.environ.get("FINDE_ESTILO") or "").strip() == "papel":
        return "papel"
    return "campo"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Tipografías y marca
# ─────────────────────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=32)
def serif(tam: int, peso: int = 800) -> ImageFont.FreeTypeFont:
    """Fraunces (OFL, finde/marca): la serif gruesa de las cifras del estilo papel."""
    try:
        f = ImageFont.truetype(str(MARCA / "Fraunces-Variable.ttf"), tam)
        try:
            ejes = f.get_variation_axes()
            valores = []
            for e in ejes:
                nombre = e.get("name", b"")
                nombre = nombre.decode() if isinstance(nombre, bytes) else str(nombre)
                if "eight" in nombre:
                    valores.append(peso)
                elif "ptical" in nombre:
                    valores.append(min(max(tam, e["minimum"]), e["maximum"]))
                else:
                    valores.append(e.get("default", e["minimum"]))
            f.set_variation_by_axes(valores)
        except (OSError, ValueError, KeyError):
            pass
        return f
    except OSError:
        return D.fuente("negra", tam)


@lru_cache(maxsize=32)
def sans(tam: int, peso: str = "bold") -> ImageFont.FreeTypeFont:
    return D.fuente(peso, tam)


@lru_cache(maxsize=32)
def gigante(tam: int) -> ImageFont.FreeTypeFont:
    """Los números enormes del estilo campo (Libre Franklin 800, como el «16.488» de la referencia)."""
    return D.fuente("negra", tam)


@lru_cache(maxsize=4)
def isologo(alto: int) -> Image.Image:
    """El isologo del diario (las tres C y el punto, #FD8511; la geometría de diario_web/public/logo-c.svg)."""
    anillos, punto, esc = ((387.5, 65), (267.5, 61), (151.0, 60)), 68, 4
    r_ext = anillos[0][0] + anillos[0][1] / 2
    lado = round(2 * r_ext * esc + 8)
    im = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = lado / 2
    for rm, w in anillos:
        re_ = (rm + w / 2) * esc
        d.arc((o - re_, o - re_, o + re_, o + re_), 45, 315, fill=NARANJA + (255,), width=round(w * esc))
    d.ellipse((o - punto * esc, o - punto * esc, o + punto * esc, o + punto * esc), fill=NARANJA + (255,))
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Utilidades de dibujo
# ─────────────────────────────────────────────────────────────────────────────────────────────
def capa(im):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    return ov, ImageDraw.Draw(ov)


def ease(x: float) -> float:
    return MV.ease_out(max(0.0, min(1.0, x)))


def rebote(x: float) -> float:
    return MV.ease_back(max(0.0, min(1.0, x)))


def plano(p: str) -> str:
    from finde import datos as DA
    return DA.plano(p).strip("¿?¡!.,:;")


def numero_txt(v: float, dec: int, signo: bool = False) -> str:
    from finde.temas import coma
    s = coma(abs(v) if signo else v, dec)
    return (("+" if v >= 0 else "−") + s) if signo else s


def con_alfa(c: tuple, a: float) -> tuple:
    return tuple(c[:3]) + (max(0, min(255, round(255 * a))),)


def pastilla(d, x, y, texto: str, f, fondo, color, anchor="l", borde=None, punto=False, alfa=1.0) -> tuple:
    """Una etiqueta redondeada; devuelve su caja."""
    w = d.textlength(texto, font=f) + 56 + (28 if punto else 0)
    h = round(f.size * 1.75)
    x0 = x if anchor == "l" else (x - w / 2 if anchor == "m" else x - w)
    if alfa <= 0:
        return (x0, y, x0 + w, y + h)
    if fondo is not None:
        d.rounded_rectangle((x0, y, x0 + w, y + h), h // 2, fill=con_alfa(fondo, alfa))
    if borde is not None:
        d.rounded_rectangle((x0, y, x0 + w, y + h), h // 2, outline=con_alfa(borde, alfa), width=3)
    xt = x0 + 28
    if punto:
        d.ellipse((xt, y + h / 2 - 8, xt + 16, y + h / 2 + 8), fill=con_alfa(NARANJA, alfa))
        xt += 28
    d.text((xt, y + h / 2), texto, font=f, fill=con_alfa(color, alfa), anchor="lm")
    return (x0, y, x0 + w, y + h)


def palabras_entran(im, texto: str, f, y: int, t: float, color, acento, resaltar=(), centrado=True, x=X0,
                    ancho=X1 - X0, paso=0.07, salto=1.06, sombra=False) -> int:
    """Escribe palabra por palabra (cada una sube y aparece); las de `resaltar` en el color de acento. Devuelve la y
    de abajo."""
    medir = ImageDraw.Draw(im)
    lineas = D.renglones(medir, texto, f, ancho)
    esp = medir.textlength(" ", font=f)
    ov, d = capa(im)
    clave = {plano(p) for p in resaltar}
    k, yy = 0, y
    for linea in lineas:
        xx = (W - medir.textlength(linea, font=f)) / 2 if centrado else x
        for p in linea.split():
            u = ease((t - k * paso) / 0.32)
            if u > 0:
                c = acento if plano(p) in clave else color
                pos = (xx, yy + round(40 * (1 - u)))
                if sombra:
                    d.text((pos[0] + 3, pos[1] + 4), p, font=f, fill=(0, 0, 0, round(150 * u)))
                d.text(pos, p, font=f, fill=con_alfa(c, u))
            xx += medir.textlength(p, font=f) + esp
            k += 1
        yy += round(f.size * salto)
    im.alpha_composite(ov)
    return yy


def particulas(im, centro, t: float, n: int = 28, semilla: int = 7):
    if t <= 0 or t > 1.1:
        return
    rng = np.random.default_rng(semilla)
    ov, d = capa(im)
    u = ease(t / 1.1)
    for i in range(n):
        ang, vel, r0 = rng.uniform(0, 2 * math.pi), rng.uniform(260, 620), rng.uniform(5, 14)
        x, y = centro[0] + math.cos(ang) * vel * u, centro[1] + math.sin(ang) * vel * u
        r = r0 * (1 - 0.6 * u)
        d.ellipse((x - r, y - r, x + r, y + r), fill=con_alfa(NARANJA if i % 3 else NEGRO, 1 - u))
    im.alpha_composite(ov)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Fondos
# ─────────────────────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _papel() -> Image.Image:
    """Papel crema con grano muy suave y un viñeteado."""
    rng = np.random.default_rng(5)
    base = np.ones((H, W, 3), dtype=np.float32) * np.array(PAPEL, dtype=np.float32)
    base += rng.normal(0, 3.2, (H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    base *= (1 - 0.10 * np.clip(r - 0.25, 0, 1))[..., None]
    return Image.fromarray(base.clip(0, 255).astype("uint8")).convert("RGBA")


@lru_cache(maxsize=1)
def _oscuro_base() -> Image.Image:
    """Sin video (el sábado): grafito con degradé y una grilla de puntos tenue."""
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.array([38, 40, 46], dtype=np.float32) * (1 - y) + np.array([12, 13, 16], dtype=np.float32) * y
    im = Image.fromarray(np.repeat(base, W, axis=1).clip(0, 255).astype("uint8")).convert("RGBA")
    d = ImageDraw.Draw(im)
    for yy in range(40, H, 48):
        for xx in range(24, W, 48):
            d.point((xx, yy), fill=(66, 69, 76, 255))
    return im


@lru_cache(maxsize=1)
def _halo() -> Image.Image:
    from PIL import ImageFilter
    lado = 1200
    m = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(m).ellipse((280, 280, lado - 280, lado - 280), fill=120)
    m = m.filter(ImageFilter.GaussianBlur(170))
    halo = Image.new("RGBA", (lado, lado), NARANJA + (0,))
    halo.putalpha(m)
    return halo


def _oscuro(t: float) -> Image.Image:
    """El fondo oscuro con un halo naranja que se mueve despacio (el movimiento que da el video los domingos)."""
    im = _oscuro_base().copy()
    capa_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    capa_.paste(_halo(), (round(W * 0.5 + 300 * math.sin(t * 0.33) - 600), round(H * 0.45 + 340 * math.cos(t * 0.25) - 600)))
    im.alpha_composite(capa_)
    return im


@lru_cache(maxsize=1)
def _oscurecer() -> Image.Image:
    """La capa negra sobre el video: pareja arriba y más densa abajo (donde va el texto)."""
    y = np.linspace(0, 1, H)[:, None]
    a = (0.48 + 0.32 * np.clip((y - 0.25) / 0.6, 0, 1)) * 255
    alfa = np.repeat(a, W, axis=1).astype("uint8")
    im = Image.new("RGBA", (W, H), (8, 9, 11, 0))
    im.putalpha(Image.fromarray(alfa))
    return im


class Fondo:
    """El fondo de cada cuadro: papel, o el video del campo (un clip que corre durante todo el reel)."""

    def __init__(self, estilo: str, clip: Path = None, total: float = 0.0):
        self.estilo, self.cuadros, self.t = estilo, None, 0.0
        if estilo == "campo" and clip:
            self.cuadros = cuadros_llenos(clip, total + 1)

    def cuadro(self, panel: float = 0.0) -> Image.Image:
        if self.estilo == "papel":
            return _papel().copy()
        cuadro = next(self.cuadros, None) if self.cuadros is not None else None
        self.t += 1 / FPS
        im = cuadro.convert("RGBA") if cuadro is not None else _oscuro(self.t)
        im.alpha_composite(_oscurecer())
        if panel > 0:                                   # escenas con mucho dato: más oscuro todavía
            im.alpha_composite(Image.new("RGBA", (W, H), (10, 11, 13, round(150 * panel))))
        return im

    def cerrar(self):
        if self.cuadros is not None:
            self.cuadros.close()


def cuadros_llenos(clip, total: float):
    """El video a pantalla completa (llena el 9:16 recortando los costados, como la referencia), en loop, levemente
    más lento para que se sienta calmo."""
    from agro import reel_zona as RZ
    vf = f"setpts=1.15*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    cmd = [RZ._ffmpeg(), "-loglevel", "error", "-stream_loop", "-1", "-i", str(clip), "-t", f"{total:.2f}", "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-an", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    tam, ultimo = W * H * 3, None
    try:
        while True:
            crudo = proc.stdout.read(tam)
            if len(crudo) < tam:
                break
            ultimo = Image.frombytes("RGB", (W, H), crudo)
            yield ultimo
    finally:
        proc.kill()
    while ultimo is not None:
        yield ultimo


def video_del_campo(ficha: dict, carpeta: Path, log=print):
    """Un clip ilustrativo del banco de agro según el tema: (ruta, crédito) o (None, "") y el fondo va liso."""
    try:
        from datetime import datetime

        from agro import banco_video as BVI
        from agro import reel_zona as RZ
        tag = ficha.get("video_tag") or {"soja_peor": "cosecha", "anegamiento": "lluvia",
                                          "emergencias": "cosecha"}.get(ficha["clave"], "campo")
        v = RZ.elegir_video(tag, {}, datetime.now())
        if not v:
            return None, ""
        clip = BVI.bajar(v, Path(carpeta) / f"fondo_{v['archivo']}")
        return (clip, BVI.credito(v)) if clip else (None, "")
    except Exception as e:                           # noqa: BLE001 — sin video, fondo liso
        log(f"   video de fondo: {type(e).__name__}: {e}")
        return None, ""


@lru_cache(maxsize=4)
def _cabecera(estilo: str, fuente: str, credito: str = "", marca: tuple = ("Chivilcoy", "en datos"),
              chip: str = "CHIVILCOY") -> Image.Image:
    s = ESTILOS[estilo]
    ov, d = capa(Image.new("RGBA", (W, H)))
    iso = isologo(58)
    ov.alpha_composite(iso, (X0, 64))
    f = sans(36, "bold")
    d.text((X0 + iso.width + 16, 93), marca[0], font=f, fill=s["texto"], anchor="lm")
    x = X0 + iso.width + 16 + d.textlength(marca[0] + " ", font=f)
    d.text((x, 93), marca[1], font=f, fill=s["acento"], anchor="lm")
    d.text((X0, 150), fuente, font=sans(25, "medium"), fill=s["tenue"])
    if credito:
        d.text((W - X0, 150), credito, font=sans(22, "regular"), fill=s["tenue"], anchor="ra")
    if estilo == "campo":
        pastilla(d, W - X0, 66, chip, sans(24, "bold"), None, BLANCO, anchor="r", borde=BLANCO)
    return ov


def progreso(im: Image.Image, avance: float, estilo: str):
    d = ImageDraw.Draw(im)
    a = max(0.0, min(1.0, avance))
    if estilo == "campo":                           # como la referencia: una línea fina abajo, dentro del margen
        d.rounded_rectangle((X0, Y_BARRA, X1, Y_BARRA + 6), 3, fill=(90, 92, 98, 255))
        d.rounded_rectangle((X0, Y_BARRA, X0 + max(6, (X1 - X0) * a), Y_BARRA + 6), 3, fill=NARANJA + (255,))
    else:
        d.rectangle((0, 0, W, 9), fill=(226, 218, 204, 255))
        d.rectangle((0, 0, round(W * a), 9), fill=NARANJA_OSC + (255,))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El mapa, claro u oscuro (con los contornos de agro/mapa_zona.py)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _mezcla(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def mapa(valores: dict, t: float, s: dict, fmt, lado_x=1000, lado_y=880, durar=1.4) -> Image.Image:
    im = Image.new("RGBA", (lado_x, lado_y), (0, 0, 0, 0))
    polis = MZ.poligonos()
    if not polis:
        return im
    p = MZ.proyeccion(lado_x, lado_y)
    d = ImageDraw.Draw(im)
    con = sorted([(v, k) for k, v in valores.items() if v is not None and k in polis])
    lo, hi = (con[0][0], con[-1][0]) if con else (0, 1)
    orden = {k: i for i, (_, k) in enumerate(con)}
    n = max(1, len(con))
    for k, v in polis.items():
        for a in v["anillos"]:
            pts = [p(x, y) for x, y in a]
            color = s["mapa_fondo"]
            if k in orden:
                aparece = max(0.0, min(1.0, (t - durar * orden[k] / n) / 0.35))
                tono = 0.0 if hi == lo else (valores[k] - lo) / (hi - lo)
                color = _mezcla(s["mapa_fondo"], _mezcla(s["mapa_lo"], s["mapa_hi"], tono), aparece)
            d.polygon(pts, fill=color + (255,))
            d.line(pts + [pts[0]], fill=s["mapa_linea"] + (255,), width=2)
    if "chivilcoy" in polis:
        for a in polis["chivilcoy"]["anillos"]:
            pts = [p(x, y) for x, y in a]
            d.line(pts + [pts[0]], fill=s["chiv_borde"] + (255,), width=6, joint="curve")
    for k, v in polis.items():
        a = max(v["anillos"], key=len)
        cx, cy = p(*MZ.centro(a))
        es = k == "chivilcoy"
        pts = [p(x, y) for x, y in a]
        area = abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2
        chico = area < lado_x * lado_y * 0.035
        f_n = sans(19 if chico else 25, "bold")
        if k in orden and t >= durar * orden[k] / n + 0.2:
            num = fmt(valores[k])
            tam = 46 if es else (28 if chico else 38)
            f_v = gigante(tam) if s["sombra"] else serif(tam, 800)
            if s["sombra"]:
                d.text((cx + 2, cy - 30 + 2), num, font=f_v, fill=(0, 0, 0, 190), anchor="ma")
            d.text((cx, cy - 30), num, font=f_v, fill=s["mapa_txt"] + (255,), anchor="ma")
            yn = cy + (10 if chico else 20)
        else:
            yn = cy - 12
        if s["sombra"]:
            d.text((cx + 2, yn + 2), v["nombre"], font=f_n, fill=(0, 0, 0, 190), anchor="ma")
        d.text((cx, yn), v["nombre"], font=f_n, fill=(NARANJA if (es and s["sombra"]) else s["mapa_txt"]) + (255,),
               anchor="ma")
    return im


def leyenda(im, m: dict, s: dict, y: int, t: float):
    vals = [x for x in m["valores"].values() if x is not None]
    lo, hi = min(vals), max(vals)
    u = ease((t - 1.6) / 0.5)
    if u <= 0:
        return
    ov, d = capa(im)
    x0, x1 = 230, 850
    for i in range(x1 - x0):
        d.line((x0 + i, y, x0 + i, y + 22), fill=con_alfa(_mezcla(s["mapa_lo"], s["mapa_hi"], i / (x1 - x0)), u))
    fmt = lambda v: numero_txt(v, m.get("dec", 0), m.get("signo")) + (m.get("unidad") or "")  # noqa: E731
    f = sans(28, "bold")
    d.text((x0 - 16, y + 11), fmt(lo), font=f, fill=con_alfa(s["texto"], u), anchor="rm")
    d.text((x1 + 16, y + 11), fmt(hi), font=f, fill=con_alfa(s["texto"], u), anchor="lm")
    d.text((W / 2, y + 44), m["leyenda"], font=sans(26, "regular"), fill=con_alfa(s["tenue"], u), anchor="mt")
    im.alpha_composite(ov)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Escenas: fn(im, t, ficha, pl) — pl lleva el estilo, la duración y lo calculado una vez
# ─────────────────────────────────────────────────────────────────────────────────────────────
def escena_gancho(im, t, f, pl):
    u = ease(t / 0.4)
    if pl["estilo"] == "papel":
        ov, d = capa(im)
        d.text((W / 2, 520 - 30 * (1 - u)), "LA PREGUNTA DEL FINDE", font=sans(34, "bold"),
               fill=con_alfa(NEGRO, u), anchor="mm")
        im.alpha_composite(ov)
        yy = palabras_entran(im, f["narracion"]["gancho"], serif(104), 590, t - 0.15, NEGRO, NARANJA_OSC,
                             pl["clave_gancho"])
        ov, d = capa(im)
        pastilla(d, W / 2, yy + 30, pl["fuente_corta"], sans(30, "bold"), None, NARANJA_OSC, anchor="m",
                 borde=NARANJA_OSC, alfa=ease((t - 0.9) / 0.4))
        im.alpha_composite(ov)
        return
    ov, d = capa(im)
    pastilla(d, X0, 520, "LA PREGUNTA DEL " + ("SÁBADO" if f.get("dia") == "sabado" else "DOMINGO"),
             sans(28, "bold"), None, BLANCO, borde=NARANJA, punto=True, alfa=u)
    im.alpha_composite(ov)
    palabras_entran(im, f["narracion"]["gancho"].upper(), MV.anton(118), 610, t - 0.15, BLANCO, NARANJA,
                    pl["clave_gancho"], centrado=False, sombra=True)


def _tarjetas(im, t, f, pl, revelar: float = -1.0):
    papel = pl["estilo"] == "papel"
    acento = NARANJA_OSC if papel else NARANJA
    for i, op in enumerate(f["opciones"]):
        u = rebote((t - 0.25 - 0.18 * i) / 0.5)
        if u <= 0:
            continue
        es = i == f["correcta"]
        ok = revelar >= 0 and es
        a = 1.0 - 0.6 * (0.0 if revelar < 0 or es else ease(revelar / 0.4))
        tarjeta = Image.new("RGBA", (920, 184), (0, 0, 0, 0))
        dt = ImageDraw.Draw(tarjeta)
        if ok:
            fondo, borde, txt, af = acento, acento, (BLANCO if papel else NEGRO), 1.0
        elif papel:
            fondo, borde, txt, af = BLANCO, NEGRO, NEGRO, 1.0
        else:
            fondo, borde, txt, af = (14, 15, 18), BLANCO, BLANCO, 0.72
        dt.rounded_rectangle((0, 0, 919, 183), 30, fill=con_alfa(fondo, a * af), outline=con_alfa(borde, a), width=4)
        dt.ellipse((30, 44, 126, 140), fill=con_alfa(BLANCO if ok else acento, a))
        dt.text((78, 92), "ABC"[i], font=MV.anton(58), fill=con_alfa(acento if ok else (BLANCO if papel else NEGRO), a),
                anchor="mm")
        fo = serif(84 if len(op) < 10 else 66) if papel else MV.anton(86 if len(op) < 10 else 68)
        dt.text((166, 92), op, font=fo, fill=con_alfa(txt, a), anchor="lm")
        if ok and revelar > 0.15:
            k = ease((revelar - 0.15) / 0.3)
            pts = [(800, 94), (828, 122), (880, 62)]
            dt.line(pts[:2] if k < 0.5 else pts, fill=con_alfa(txt, 1), width=14, joint="curve")
        esc = u * (1 + (0.05 * math.sin(min(1, revelar / 0.3) * math.pi) if ok else 0))
        MV.pop_sprite(im, tarjeta, (W / 2, CARTAS_Y[i] + 92), esc)


def _pregunta_arriba(im, f, pl):
    if pl["estilo"] == "papel":
        palabras_entran(im, f["pregunta"], serif(50, 700), 300, 99, NEGRO, NARANJA_OSC, pl["clave_gancho"])
    else:
        palabras_entran(im, f["pregunta"], sans(46, "bold"), 300, 99, BLANCO, NARANJA, pl["clave_gancho"],
                        centrado=False, sombra=True)


def escena_opciones(im, t, f, pl):
    _pregunta_arriba(im, f, pl)
    _tarjetas(im, t, f, pl)
    t0 = pl["dur"] - CUENTA - 0.1
    if t >= t0:
        k = t - t0
        n = 3 - int(k / (CUENTA / 3))
        if n >= 1:
            frac = (k % (CUENTA / 3)) / (CUENTA / 3)
            ov, d = capa(im)
            cx, cy, r = W / 2, 1300, 54
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(120, 120, 120, 90), width=10)
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (1 - frac),
                  fill=(NARANJA_OSC if pl["estilo"] == "papel" else NARANJA) + (255,), width=10)
            d.text((cx, cy), str(n), font=MV.anton(64), fill=pl["s"]["texto"] + (255,), anchor="mm")
            im.alpha_composite(ov)


def escena_revelacion(im, t, f, pl):
    r = f["respuesta"]
    if t < 1.0:
        _pregunta_arriba(im, f, pl)
        _tarjetas(im, 99, f, pl, revelar=t)
        particulas(im, (W / 2, CARTAS_Y[f["correcta"]] + 92), t - 0.1)
        return
    k = t - 1.0
    valor = r["numero"] * ease(k / 1.0)
    num = numero_txt(valor, r.get("dec", 0), r.get("signo"))
    final = numero_txt(r["numero"], r.get("dec", 0), r.get("signo"))
    unidad = (r.get("unidad") or "").strip()
    if pl["estilo"] == "papel":
        # Como la referencia: la cifra en serif naranja, la explicación en serif negra y una pastilla naranja.
        fn = serif(270 if len(final) <= 4 else 220, 850)
        fu = serif(120, 800)
        sprite = Image.new("RGBA", (W, 330), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sprite)
        wn = ds.textlength(final, font=fn)
        wu = ds.textlength(" " + unidad, font=fu) if unidad else 0
        x = (W - wn - wu) / 2
        ds.text((x + wn, 290), num, font=fn, fill=NARANJA_OSC + (255,), anchor="rs")
        if unidad:
            ds.text((x + wn + ds.textlength(" ", font=fu), 290), unidad, font=fu, fill=NARANJA_OSC + (255,),
                    anchor="ls")
        MV.pop_sprite(im, sprite, (W / 2, 690), max(0.01, rebote(k / 0.5)))
        particulas(im, (W / 2, 700), k - 0.05, n=30, semilla=11)
        yy = palabras_entran(im, r["texto"], serif(56, 600), 880, k - 0.45, NEGRO, NARANJA_OSC, ())
        ov, d = capa(im)
        pastilla(d, W / 2, yy + 30, pl["anio_txt"], sans(30, "bold"), NARANJA_OSC, BLANCO, anchor="m",
                 alfa=ease((k - 0.9) / 0.4))
        im.alpha_composite(ov)
        return
    # Campo: el bloque a la izquierda de la referencia (pastilla con punto, número gigante, unidad en color, línea).
    ov, d = capa(im)
    pastilla(d, X0, 470, pl["volanta"], sans(26, "bold"), None, BLANCO, borde=NARANJA, punto=True,
             alfa=ease(k / 0.3))
    im.alpha_composite(ov)
    pegado = unidad == "%"                           # «68,4%»: el signo al lado, en naranja y más chico
    fn = gigante(300 if len(final) <= 3 else 250 if len(final) <= 5 else 200)
    sprite = Image.new("RGBA", (W, 340), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sprite)
    ds.text((X0 - 8 + 4, 300 + 6), num, font=fn, fill=(0, 0, 0, 150), anchor="ls")
    ds.text((X0 - 8, 300), num, font=fn, fill=BLANCO + (255,), anchor="ls")
    if pegado:
        xf = X0 - 8 + ds.textlength(final, font=fn) + 10
        ds.text((xf, 300), "%", font=gigante(round(fn.size * 0.55)), fill=NARANJA + (255,), anchor="ls")
        unidad = ""
    u = ease(k / 0.35)
    if u > 0:
        sprite.putalpha(sprite.getchannel("A").point(lambda v: round(v * u)))
        im.alpha_composite(sprite, (round(-30 * (1 - u)), 540))
    yy = 900
    if unidad:
        palabras_entran(im, unidad.upper().replace("/100", "SOBRE 100"), MV.anton(110), yy - 30, k - 0.3, NARANJA,
                        NARANJA, (), centrado=False, sombra=True)
        yy += 120
    palabras_entran(im, r["texto"].upper(), sans(34, "bold"), yy + 20, k - 0.6, (205, 208, 213), NARANJA, (),
                    centrado=False, paso=0.04)


def escena_mapa(im, t, f, pl):
    m, s = f["mapa"], pl["s"]
    if pl["estilo"] == "papel":
        palabras_entran(im, m["titulo"], serif(70, 800), 240, t, NEGRO, NARANJA_OSC, ("zona",))
    else:
        palabras_entran(im, m["titulo"].upper(), MV.anton(80), 240, t, BLANCO, NARANJA, ("zona",), centrado=False,
                        sombra=True)
    fmt = lambda v: numero_txt(v, m.get("dec", 0), m.get("signo")) + (m.get("unidad") or "")  # noqa: E731
    mp = mapa(m["valores"], t, s, fmt)
    MV.pop_sprite(im, mp, (W / 2, 800), 1.0 + 0.05 * ease(t / max(1.0, pl["dur"])))
    leyenda(im, m, s, 1268, t)


def comparacion(f: dict) -> list:
    """[(nombre, valor)] Chivilcoy y el otro extremo de la zona (el último si Chivilcoy está primero)."""
    m = f["mapa"]
    vals = {k: v for k, v in m["valores"].items() if v is not None}
    nombres = {k: v["nombre"] for k, v in MZ.poligonos().items()}
    orden = sorted(vals, key=lambda k: -vals[k])
    otro = orden[-1] if orden and orden[0] == "chivilcoy" else (orden[0] if orden else None)
    fmt = lambda v: numero_txt(v, m.get("dec", 0), m.get("signo")) + (m.get("unidad") or "")  # noqa: E731
    salida = [("Chivilcoy", fmt(vals.get("chivilcoy", 0)))]
    if otro and otro != "chivilcoy":
        salida.append((nombres.get(otro, otro), fmt(vals[otro])))
    return salida


def _tarjetas_contexto(im, t, f, pl):
    """Sin mapa (los informes nacionales, agro/fada.py): hasta tres cifras en tarjetas que entran escalonadas."""
    ov, d = capa(im)
    pastilla(d, X0, 300, "PARA ENTENDERLO", sans(28, "bold"), None, BLANCO, borde=NARANJA, punto=True,
             alfa=ease(t / 0.3))
    im.alpha_composite(ov)
    for i, c in enumerate(f["contexto"][:3]):
        k = rebote((t - 0.3 - 0.45 * i) / 0.5)
        if k <= 0:
            continue
        tar = Image.new("RGBA", (920, 270), (0, 0, 0, 0))
        dt = ImageDraw.Draw(tar)
        dt.rounded_rectangle((0, 0, 919, 269), 32, fill=(14, 15, 18, 215), outline=(255, 255, 255, 255), width=3)
        dt.rectangle((0, 34, 10, 235), fill=NARANJA)
        fn = MV.anton(104 if len(c["numero"]) <= 10 else 80)
        caja = dt.textbbox((44, 24), c["numero"], font=fn)
        dt.text((44, 24), c["numero"], font=fn, fill=NARANJA)
        for j, linea in enumerate(D.renglones(dt, c["texto"], sans(36, "bold"), 830)[:2]):
            dt.text((46, caja[3] + 14 + j * 44), linea, font=sans(36, "bold"), fill=(232, 234, 238))
        MV.pop_sprite(im, tar, (W / 2, 520 + i * 300), k)


def escena_contexto(im, t, f, pl):
    """«Chivilcoy frente a…» (dos tarjetas, como la comparación de la referencia) y las cifras de contexto."""
    papel = pl["estilo"] == "papel"
    acento = NARANJA_OSC if papel else NARANJA
    if not f.get("mapa"):
        _tarjetas_contexto(im, t, f, pl)
        return
    comp = comparacion(f)
    y = 330
    for i, (nombre, valor) in enumerate(comp):
        u = rebote((t - 0.2 - 0.5 * i) / 0.5)
        if u > 0:
            tar = Image.new("RGBA", (900, 190), (0, 0, 0, 0))
            dt = ImageDraw.Draw(tar)
            naranja = i == 1
            fondo = acento if naranja else (BLANCO if papel else (14, 15, 18))
            txt = (BLANCO if papel else NEGRO) if naranja else (NEGRO if papel else BLANCO)
            dt.rounded_rectangle((0, 0, 899, 189), 30, fill=fondo + (255 if papel or naranja else 210,),
                                 outline=(NEGRO if papel else BLANCO) + (255,), width=4)
            dt.text((40, 95), nombre, font=sans(42, "bold"), fill=txt, anchor="lm")
            dt.text((860, 95), valor, font=serif(92, 850) if papel else MV.anton(96),
                    fill=txt if naranja else acento, anchor="rm")
            MV.pop_sprite(im, tar, (W / 2, y + 95 + i * 330), u)
        if i == 0 and len(comp) > 1:
            k = ease((t - 0.5) / 0.3)
            if k > 0:
                ov, d = capa(im)
                d.text((W / 2, y + 260), "frente a", font=serif(54, 400) if papel else sans(44, "bold"),
                       fill=con_alfa(pl["s"]["tenue"], k), anchor="mm")
                im.alpha_composite(ov)
    extras = [c for c in f["contexto"] if "Puesto" not in c["numero"]][:2]
    for j, c in enumerate(extras):
        k = ease((t - 1.3 - 0.4 * j) / 0.4)
        if k <= 0:
            continue
        ov, d = capa(im)
        texto = f"{c['numero']} · {c['texto']}"
        fp = sans(34 if len(texto) <= 40 else 28, "bold")
        pastilla(d, W / 2, 1010 + j * 110, texto, fp, acento if j == 0 else None,
                 (BLANCO if papel else NEGRO) if j == 0 else pl["s"]["texto"], anchor="m",
                 borde=None if j == 0 else pl["s"]["texto"], alfa=k)
        im.alpha_composite(ov)


def escena_bloque(im, t, f, pl):
    """Un dato más del informe (los reels largos de agro/fada.py): como la respuesta del estilo campo —pastilla con
    punto, número gigante que cuenta, unidad en naranja, texto— o una lista de filas (etiqueta y valor)."""
    b = pl["bloque"]
    ov, d = capa(im)
    pastilla(d, X0, 300, (b.get("volanta") or "EL DATO").upper()[:40], sans(26, "bold"), None, BLANCO, borde=NARANJA,
             punto=True, alfa=ease(t / 0.3))
    im.alpha_composite(ov)
    if b.get("filas"):
        palabras_entran(im, b.get("titulo") or "", MV.anton(80), 400, t, BLANCO, NARANJA, (), centrado=False,
                        sombra=True)
        for i, (etiqueta, valor) in enumerate(b["filas"][:5]):
            k = rebote((t - 0.5 - 0.35 * i) / 0.45)
            if k <= 0:
                continue
            tar = Image.new("RGBA", (920, 150), (0, 0, 0, 0))
            dt = ImageDraw.Draw(tar)
            dt.rounded_rectangle((0, 0, 919, 149), 28, fill=(14, 15, 18, 215), outline=(255, 255, 255, 255), width=3)
            dt.text((36, 75), str(etiqueta)[:30], font=sans(40, "bold"), fill=BLANCO, anchor="lm")
            dt.text((884, 75), str(valor)[:14], font=MV.anton(80), fill=NARANJA, anchor="rm")
            MV.pop_sprite(im, tar, (W / 2, 640 + i * 170), k)
        return
    num = b.get("numero")
    if num is None:
        palabras_entran(im, b.get("texto") or "", MV.anton(96), 420, t, BLANCO, NARANJA, (), centrado=False,
                        sombra=True)
        return
    dec, unidad = int(b.get("dec") or 0), (b.get("unidad") or "").strip()
    final = numero_txt(float(num), dec)
    actual = numero_txt(float(num) * ease(t / 0.9), dec)
    fn = gigante(300 if len(final) <= 3 else 250 if len(final) <= 5 else 200)
    sprite = Image.new("RGBA", (W, 340), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sprite)
    ds.text((X0 - 8 + 4, 306), actual, font=fn, fill=(0, 0, 0, 150), anchor="ls")
    ds.text((X0 - 8, 300), actual, font=fn, fill=BLANCO + (255,), anchor="ls")
    if unidad == "%":
        ds.text((X0 - 8 + ds.textlength(final, font=fn) + 10, 300), "%", font=gigante(round(fn.size * 0.55)),
                fill=NARANJA + (255,), anchor="ls")
        unidad = ""
    u = ease(t / 0.35)
    sprite.putalpha(sprite.getchannel("A").point(lambda v: round(v * u)))
    im.alpha_composite(sprite, (round(-30 * (1 - u)), 380))
    yy = 740
    if unidad:
        palabras_entran(im, unidad.upper(), MV.anton(100), yy - 20, t - 0.3, NARANJA, NARANJA, (), centrado=False,
                        sombra=True)
        yy += 110
    palabras_entran(im, (b.get("texto") or "").upper(), sans(38, "bold"), yy + 20, t - 0.5, (215, 218, 222), NARANJA,
                    (), centrado=False, paso=0.035)


def escena_cierre(im, t, f, pl):
    papel = pl["estilo"] == "papel"
    u = ease(t / 0.35)
    ov, d = capa(im)
    if papel:
        d.text((W / 2, 500), "TU TURNO", font=sans(36, "bold"), fill=con_alfa(NEGRO, u), anchor="mm")
    else:
        pastilla(d, X0, 480, "TU TURNO", sans(28, "bold"), None, BLANCO, borde=NARANJA, punto=True, alfa=u)
    im.alpha_composite(ov)
    if papel:
        yy = palabras_entran(im, f["cierre"], serif(96), 570, t - 0.2, NEGRO, NARANJA_OSC, pl["clave_cierre"])
    else:
        yy = palabras_entran(im, f["cierre"].upper(), MV.anton(104), 570, t - 0.2, BLANCO, NARANJA,
                             pl["clave_cierre"], centrado=False, sombra=True)
    k = ease((t - 1.1) / 0.4)
    if k > 0:
        ov, d = capa(im)
        pastilla(d, W / 2 if papel else X0, yy + 60, "Contanos en los comentarios", sans(40, "bold"),
                 NARANJA_OSC if papel else NARANJA, BLANCO if papel else NEGRO, anchor="m" if papel else "l", alfa=k)
        d.text((W / 2 if papel else X0, yy + 210), f.get("cuentas") or "@diarioyradio  ·  @diarioyradioagro",
               font=sans(32, "medium"),
               fill=con_alfa(pl["s"]["tenue"], k), anchor="mm" if papel else "lm")
        im.alpha_composite(ov)


@lru_cache(maxsize=2)
def _placa(tipo: str = "diario") -> Image.Image:
    if tipo == "agro":                              # la placa final de agro (4:5) sobre el negro del 9:16
        from agro import reel as RE
        im = Image.new("RGBA", (W, H), (32, 34, 38, 255))
        cierre = RE.cierre("grafito", "").convert("RGBA")
        im.alpha_composite(cierre, (0, (H - cierre.height) // 2))
        return im
    if PLACA_FINAL.exists():
        return Image.open(PLACA_FINAL).convert("RGBA").resize((W, H), Image.LANCZOS)
    im = Image.new("RGBA", (W, H), NEGRO + (255,))
    iso = isologo(360)
    im.alpha_composite(iso, ((W - iso.width) // 2, 700))
    return im


def escena_placa(im, t, f, pl):
    MV.pop_sprite(im, _placa(f.get("placa") or "diario"), (W / 2, H / 2), 1.04 - 0.04 * ease(t / 1.2))


ESCENAS = {"gancho": escena_gancho, "opciones": escena_opciones, "revelacion": escena_revelacion,
           "mapa": escena_mapa, "contexto": escena_contexto, "cierre": escena_cierre, "placa": escena_placa,
           "bloque": escena_bloque}
ORDEN = ("gancho", "opciones", "revelacion", "mapa", "contexto", "cierre", "placa")
PANEL = {"mapa": 1.0, "contexto": 0.6, "opciones": 0.4, "revelacion": 0.2}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Subtítulos (como la referencia: 2-3 palabras en mayúscula, la que se dice en una caja)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def bloques(palabras: list, t0: float, max_palabras: int = 3, max_letras: int = 20) -> list:
    """[(ini, fin, [(ini, fin, palabra)…])] en segundos del reel: de a pocas palabras, cortando en la puntuación."""
    salida, actual = [], []
    for ini, fin, p in palabras:
        actual.append((t0 + ini, t0 + fin, p))
        texto = " ".join(x[2] for x in actual)
        if len(actual) >= max_palabras or len(texto) >= max_letras or p[-1:] in ".,;:?!":
            salida.append(actual)
            actual = []
    if actual:
        salida.append(actual)
    out = []
    for i, b in enumerate(salida):
        fin = salida[i + 1][0][0] if i + 1 < len(salida) else b[-1][1] + 0.4
        out.append((b[0][0], min(fin, b[-1][1] + 0.9), b))
    return out


def dibujar_subtitulo(im, subs: list, t: float, s: dict):
    actual = next((x for x in subs if x[0] <= t < x[1]), None)
    if not actual:
        return
    ov, d = capa(im)
    palabras = [p.upper() for _, _, p in actual[2]]
    hablando = max((k for k, (ini, _f, _p) in enumerate(actual[2]) if ini <= t), default=None)
    tam = 62
    while True:
        f = sans(tam, "bold")
        esp = d.textlength(" ", font=f)
        anchos = [d.textlength(p, font=f) + 28 for p in palabras]
        total = sum(anchos) + esp * (len(palabras) - 1)
        if total <= 920 or tam <= 40:
            break
        tam -= 4
    u = ease((t - actual[0]) / 0.1)
    x = (W - total) / 2
    y = Y_SUB + 8 * (1 - u)
    for k, p in enumerate(palabras):
        if k == hablando:
            d.rounded_rectangle((x, y - 6, x + anchos[k], y + f.size + 18), 12, fill=con_alfa(s["caja_sub"], u))
            d.text((x + 14, y + 6), p, font=f, fill=con_alfa(s["txt_caja"], u))
        else:
            d.text((x + 14, y + 6), p, font=f, fill=con_alfa(s["texto"], u),
                   stroke_width=3 if s["sombra"] else 0, stroke_fill=(0, 0, 0, round(170 * u)))
        x += anchos[k] + esp
    im.alpha_composite(ov)


def srt(subs: list) -> str:
    def ts(seg):
        ms = round(seg * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{' '.join(p for _, _, p in ws)}\n"
                     for i, (a, b, ws) in enumerate(subs, 1))


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Sonido
# ─────────────────────────────────────────────────────────────────────────────────────────────
def efectos(planes: list, ficha: dict) -> list:
    ev = []
    for nombre, t0, dur in planes:
        if t0 > 0:
            ev.append((t0, MV.brisa(), 0.55))
        if nombre == "gancho":
            ev += [(t0 + 0.15 + 0.07 * k, MV.pop(1.0 + 0.05 * k), 0.3) for k in range(8)]
        elif nombre == "opciones":
            ev += [(t0 + 0.25 + 0.18 * i, MV.pop(0.9 + 0.12 * i), 0.6) for i in range(3)]
            c0 = t0 + dur - CUENTA - 0.1
            ev += [(c0 + i * CUENTA / 3, MV.tic(1.0 + 0.1 * i), 0.8) for i in range(3)]
        elif nombre == "revelacion":
            ev += [(t0 + 0.05, MV.pop(0.7), 0.8), (t0 + 0.12, MV.campanita(), 0.8)]
            ev += [(t0 + 1.0 + j * 0.06, MV.tic(0.9 + 0.03 * j), 0.22) for j in range(16)]
            ev.append((t0 + 2.0, MV.pop(0.8), 0.6))
        elif nombre == "mapa":
            ev += [(t0 + 0.2 + 1.4 * i / 10, MV.tic(0.8 + 0.04 * i), 0.3) for i in range(10)]
        elif nombre == "contexto":
            ev += [(t0 + 0.2 + 0.5 * i, MV.pop(1.1 + 0.05 * i), 0.55) for i in range(2)]
        elif nombre == "bloque":
            ev += [(t0 + j * 0.06, MV.tic(0.9 + 0.03 * j), 0.18) for j in range(14)]
            ev.append((t0 + 0.9, MV.pop(0.9), 0.5))
        elif nombre == "cierre":
            ev.append((t0 + 0.1, MV.pop(1.2), 0.5))
        elif nombre == "placa":
            ev.append((t0 + 0.3, MV.campanita(), 0.6))
    return ev


def mezcla(total: float, voces: list, ev: list) -> np.ndarray:
    """Voz adelante, efectos al medio y la base, que baja mientras se habla. Estéreo float32."""
    n = int(SR * total)
    voz = np.zeros(n)
    for t0, audio in voces:
        if audio is None:
            continue
        i = int(t0 * SR)
        m = min(audio.size, n - i)
        if m > 0:
            voz[i:i + m] += audio[:m]
    pico = float(np.max(np.abs(voz))) if n else 0.0
    hay_voz = pico > 0.01
    if hay_voz:
        voz = voz / pico * 0.92
    sfx = np.zeros(n + SR)
    for t0, sen, vol in ev:
        i = int(t0 * SR)
        if 0 <= i < sfx.size:
            m = min(sen.size, sfx.size - i)
            sfx[i:i + m] += sen[:m] * vol
    sfx = sfx[:n]
    sfx = sfx / (float(np.max(np.abs(sfx))) or 1.0) * (0.36 if hay_voz else 0.7)
    musica = MV.base_musical(total)[:n]
    musica = musica / (float(np.max(np.abs(musica))) or 1.0)
    if hay_voz:
        env = np.convolve(np.abs(voz), np.ones(4410) / 4410, mode="same")
        musica = musica * 0.17 * (1.0 - 0.6 * np.clip(env / (env.max() or 1) * 3, 0, 1))
    else:
        musica = musica * 0.3
    pista = np.tanh((voz + sfx + musica) * 1.6) / np.tanh(1.6) * 0.95
    fade = int(SR * 0.6)
    pista[-fade:] *= np.linspace(1, 0, fade)
    return np.stack([pista, pista], axis=1).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Armar
# ─────────────────────────────────────────────────────────────────────────────────────────────
RESALTAR = ("chivilcoy", "gas", "natural", "cloacas", "internet", "alquilan", "tierra", "soja", "agua", "campo",
            "crecio", "65", "emergencias", "agricultura", "cuadra", "barrio", "comentarios", "nota", "menos", "mas",
            "corriente", "casa", "sufre")


def resaltables(texto: str) -> tuple:
    claves = {plano(x) for x in RESALTAR}
    return tuple(p for p in texto.split() if plano(p) in claves)


def _volanta(f: dict) -> str:
    if f.get("volanta"):
        return f["volanta"]
    return {"gas_red": "GAS DE RED · CENSO 2022", "cloacas": "CLOACAS · CENSO 2022", "agua": "AGUA DE RED · CENSO 2022",
            "internet": "INTERNET EN CASA · CENSO 2022", "alquiler": "HOGARES INQUILINOS · CENSO 2022",
            "crecimiento": "POBLACIÓN 2010-2022 · INDEC", "mayores": "65 AÑOS O MÁS · CENSO 2022",
            "tierra": "ÍNDICE DE PRODUCTIVIDAD · INTA", "soja_peor": "RINDE ESTIMADO DE SOJA",
            "anegamiento": "LIMITANTE DEL SUELO · INTA", "aptitud": "TIERRA APTA PARA AGRICULTURA",
            "emergencias": "EMERGENCIAS AGROPECUARIAS"}.get(f["clave"], "EL DATO")


def sin_voz(texto: str, carpeta: Path, nombre: str) -> dict:
    """Sin narración (26/11/2026, los reels de FADA: «hacelo sin voz»): el texto va en los subtítulos, a ritmo de
    lectura (un poco más lento que la voz), con la música y los efectos."""
    texto = " ".join((texto or "").split())
    if not texto:
        return {"audio": None, "dur": 0.0, "palabras": [], "voz": "sin texto"}
    palabras, t = [], 0.0
    for p in texto.split():
        palabras.append((t, t + 0.4, p.strip("¿¡")))
        t += 0.42 + (0.25 if p[-1:] in ".,;:?!" else 0)
    return {"audio": None, "dur": t + 0.5, "palabras": palabras, "voz": "sin voz (a pedido)"}


def armar(ficha: dict, carpeta: Path, log=print, narrar=None, clip_fn=None) -> dict:
    """El reel completo: voz por escena, cuadros, sonido, MP4, portada JPG y subtítulos SRT."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    # 26/11/2026, el editor: «todos sin voz» → de fábrica sin narración; FINDE_CON_VOZ=1 la vuelve (salvo que la ficha
    # pida «sin_voz»).
    import os
    con_voz = (os.environ.get("FINDE_CON_VOZ") or "0").strip() == "1" and not ficha.get("sin_voz")
    narrar = narrar or (VZ.narrar if con_voz else sin_voz)
    estilo = estilo_de(ficha)
    s = ESTILOS[estilo]
    fu0 = ficha["fuentes"][0]
    fuente = ficha.get("fuente_txt") or ("Fuente: INDEC · Censo 2022" if ficha["dia"] == "sabado"
                                         else f"Fuente: ArgenFields · {fu0.get('anio_dato')}")
    pl_base = {"s": s, "estilo": estilo, "clave_gancho": resaltables(ficha["narracion"]["gancho"]),
               "clave_cierre": resaltables(ficha["cierre"]), "volanta": _volanta(ficha),
               "fuente_corta": "Censo 2022 · INDEC" if ficha["dia"] == "sabado" else "ArgenFields",
               "anio_txt": (ficha.get("anio_txt") or ("Censo 2022 · partido de Chivilcoy" if ficha["dia"] == "sabado"
                                                      else str(fu0.get("anio_dato") or ""))).strip()}
    planes, voces, subs, t, info_voz = [], [], [], 0.0, []
    escenas = []
    for n in ORDEN:
        if n == "mapa" and not ficha.get("mapa"):
            continue
        if n == "contexto":                          # los bloques (reels largos) van antes del contexto
            escenas += [("bloque", b) for b in ficha.get("bloques") or []]
            if not ficha.get("contexto"):
                continue
        escenas.append((n, None))
    bloque_de = []
    for nombre, bloque in escenas:
        texto = (bloque or {}).get("narracion", "") if nombre == "bloque" else (
            ficha["narracion"].get(nombre, "") if nombre != "placa" else "")
        nv = narrar(texto, carpeta / "voz", f"{nombre}_{len(planes):02d}") if texto else {"audio": None, "dur": 0.0, "palabras": [],
                                                                    "voz": "—"}
        info_voz.append(nv["voz"])
        corrido = 1.0 if nombre == "revelacion" else 0.0      # la voz de la respuesta, después de pintar la tarjeta
        dur = max(MINIMOS.get(nombre, 2.0), ENTRADA_VOZ + corrido + nv["dur"] + 0.45)
        if nombre == "opciones":
            dur = max(MINIMOS["opciones"], ENTRADA_VOZ + nv["dur"] + 0.3 + CUENTA)
        planes.append((nombre, t, dur))
        bloque_de.append(bloque)
        voces.append((t + ENTRADA_VOZ + corrido, nv["audio"]))
        subs += bloques(nv["palabras"], t + ENTRADA_VOZ + corrido)
        t += dur
    total = t
    log(f"   voz: {sorted(set(info_voz) - {'—'})}; estilo {estilo}; duración {total:.1f} s")
    clip, credito = (None, "")
    if estilo == "campo" and (ficha.get("dia") == "domingo" or ficha.get("video_tag")):  # el sábado, sin video
        clip, credito = (clip_fn or video_del_campo)(ficha, carpeta, log)
    wav = carpeta / "_mezcla.wav"
    MV.guardar_wav(mezcla(total, voces, efectos(planes, ficha)), wav)
    mp4 = carpeta / "reel.mp4"
    from agro import reel_zona as RZ
    cmd = [RZ._ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "medium", "-crf", "21", "-profile:v", "high", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    cabecera = _cabecera(estilo, fuente, "Video ilustrativo" if clip else "",
                         tuple(ficha.get("marca") or ("Chivilcoy", "en datos")), ficha.get("chip") or "CHIVILCOY")
    fondo = Fondo(estilo, clip, total)
    anterior = None
    try:
        for (nombre, t0, dur), bloque in zip(planes, bloque_de):
            pl = dict(pl_base, dur=dur, bloque=bloque)
            ultimo = None
            for k in range(round(dur * FPS)):
                tl = k / FPS
                tg = t0 + tl
                if nombre == "placa":
                    im = Image.new("RGBA", (W, H), NEGRO + (255,))
                else:
                    im = fondo.cuadro(PANEL.get(nombre, 0.0))
                    im.alpha_composite(cabecera)
                ESCENAS[nombre](im, tl, ficha, pl)
                if nombre != "placa":
                    dibujar_subtitulo(im, subs, tg, s)
                    progreso(im, tg / total, estilo)
                cuadro = im.convert("RGB")
                limpio = cuadro
                if anterior is not None and tl < MV.TRANSICION:
                    cuadro = MV.transicion(anterior, cuadro, tl)
                proc.stdin.write(cuadro.tobytes())
                ultimo = limpio
            anterior = ultimo
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not mp4.exists():
            raise RuntimeError(f"ffmpeg: {err[-400:]}")
    finally:
        fondo.cerrar()
        if proc.poll() is None:
            proc.kill()
        if wav.exists():
            wav.unlink()
        if clip and Path(clip).is_file() and Path(clip).parent == carpeta:
            Path(clip).unlink()                      # el video de fondo no es un entregable
    jpg = portada(ficha, carpeta / "portada.jpg", cabecera)
    (carpeta / "subtitulos.srt").write_text(srt(subs), encoding="utf-8")
    return {"archivo": str(mp4), "portada": str(jpg), "duracion": round(total, 1), "ancho": W, "alto": H,
            "peso_kb": round(mp4.stat().st_size / 1024), "voz": sorted(set(info_voz) - {"—"}), "estilo": estilo,
            "video_fondo": credito, "escenas": [(n, round(a, 2), round(b, 2)) for n, a, b in planes],
            "subtitulos": len(subs)}


def portada(ficha: dict, destino: Path, cabecera=None) -> Path:
    """La portada: el título corto y grande sobre el mapa (se lee en la grilla, que corta a 4:5)."""
    estilo = estilo_de(ficha)
    s = ESTILOS[estilo]
    im = _papel().copy() if estilo == "papel" else Image.new("RGBA", (W, H), (20, 21, 25, 255))
    m = ficha.get("mapa")
    if m:
        fmt = lambda v: numero_txt(v, m.get("dec", 0), m.get("signo")) + (m.get("unidad") or "")  # noqa: E731
        mp = mapa(m["valores"], 99, s, fmt)
        mp.putalpha(mp.getchannel("A").point(lambda v: round(v * 0.5)))
        im.alpha_composite(mp, ((W - 1000) // 2, 880))
    elif estilo == "campo":
        im = _oscuro(2.0)
    if cabecera is not None:
        im.alpha_composite(cabecera)
    ov, d = capa(im)
    pastilla(d, W / 2, 440, " ".join(ficha.get("marca") or ("Chivilcoy", "en datos")).upper(), sans(32, "bold"), NARANJA_OSC if estilo == "papel" else NARANJA,
             BLANCO if estilo == "papel" else NEGRO, anchor="m")
    im.alpha_composite(ov)
    if estilo == "papel":
        palabras_entran(im, ficha["titulo"], serif(132), 540, 99, NEGRO, NARANJA_OSC, resaltables(ficha["titulo"]))
    else:
        palabras_entran(im, ficha["titulo"].upper(), MV.anton(150), 540, 99, BLANCO, NARANJA,
                        resaltables(ficha["titulo"]), sombra=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return destino
