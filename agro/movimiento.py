# -*- coding: utf-8 -*-
"""Movimiento y sonido de los reels de datos de agro (agro/reel_zona.armar: reel de la zona, vigía del tiempo y
«El campo hoy»).

Pedido del editor (20/11/2026): «mejores animaciones para los reels, estilo el de El Niño, con la estética
actualizada y el banco de sonidos de los resúmenes de las entrevistas de @diarioyradio, para darle más dinamismo
estético y sonoro». Lo que agrega:

  - TÍTULOS en Anton (la letra de los carruseles impacto), con la palabra clave en verde, que entran palabra por
    palabra (suben y aparecen, con un «pop» cada una);
  - TRANSICIONES: la diapositiva nueva entra desde abajo empujando a la anterior, con una franja naranja en el
    borde y un soplido;
  - una BARRA DE PROGRESO naranja arriba (cuánto falta: retiene) y el isologo chico abajo a la derecha;
  - los números cuentan con «tic» y cierran con un pop; las barras y las listas, un pop por fila;
  - la PLACA FINAL animada: el isologo rebota, el usuario se tipea con teclas y suena la campanita;
  - una BASE rítmica suave (bombo, hi-hat y un acorde) por debajo de los efectos.

Los sonidos son los mismos del reel de entrevistas del diario (social_publisher/historia_entrevistados.py:
pop, tecla, campanita y brisa), GENERADOS acá con numpy: nada de audio ajeno ni música con derechos.
AGRO_REEL_SONIDO=0 vuelve a los reels mudos; AGRO_REEL_MUSICA=0 deja los efectos sin la base;
AGRO_REEL_MOVIMIENTO=0 vuelve a los títulos y fundidos de antes.
"""
import os
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from agro import diseno as D

SR = 44100
TRANSICION = 0.42            # segundos que tarda la diapositiva nueva en entrar
PALABRA = 0.055              # entre palabra y palabra del título
SUBIDA = 0.28                # lo que tarda cada palabra en subir y aparecer
VERDE = (141, 205, 62)       # el verde de los carruseles impacto
BPM = 108


def _env(nombre: str, defecto: str = "1") -> bool:
    return (os.environ.get(nombre) or defecto).strip() != "0"


def activo() -> bool:
    return _env("AGRO_REEL_MOVIMIENTO")


def con_sonido() -> bool:
    return _env("AGRO_REEL_SONIDO")


def con_musica() -> bool:
    return _env("AGRO_REEL_MUSICA")


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Curvas
# ─────────────────────────────────────────────────────────────────────────────────────────────
def ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x: float) -> float:
    """Pasa un poco de 1 y vuelve (el rebote de un pop)."""
    x = min(1.0, max(0.0, x))
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Títulos: Anton, la palabra clave en verde, palabra por palabra
# ─────────────────────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=32)
def anton(tam: int):
    try:
        return ImageFont.truetype(str(D.MARCA / "Anton-Regular.ttf"), tam)
    except OSError:
        return D.fuente("negra", tam)


def plan_titulo(texto: str, ancho: int, max_renglones: int = 2, tope: int = 84, piso: int = 54,
                destacado: str = "") -> dict:
    """{f, renglones [[(palabra, verde)]], alto_renglon}: el título en mayúsculas lo más grande que entra."""
    from agro import impacto as I
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    f, r, palabras = I.ajustar(medir, texto, ancho, max_renglones, tope, piso)
    marca = I._marcas(palabras, destacado if destacado is not None else I.destacado_de(texto))
    return {"f": f, "renglones": [[(p, marca[i]) for p, i in linea] for linea in r], "salto": round(f.size * 1.04)}


def palabras_de(plan: dict) -> int:
    return sum(len(l) for l in plan["renglones"])


def dibujar_titulo(im: Image.Image, x: int, y: int, plan: dict, t: float, color=D.BLANCO, verde=VERDE) -> int:
    """Escribe el título con su entrada (t en segundos desde que empieza la diapositiva; t grande = quieto).
    Devuelve la y de abajo del último renglón."""
    f = plan["f"]
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    esp = d.textlength(" ", font=f)
    k = 0
    yy = y
    for linea in plan["renglones"]:
        xx = x
        for p, es_verde in linea:
            u = ease_out((t - k * PALABRA) / SUBIDA) if activo() else 1.0
            if u > 0:
                c = verde if es_verde else color
                d.text((xx, yy + round(28 * (1 - u))), p, font=f, fill=tuple(c[:3]) + (round(255 * u),))
            xx += d.textlength(p, font=f) + esp
            k += 1
        yy += plan["salto"]
    if im.mode == "RGBA":
        im.alpha_composite(capa)
    else:
        im.paste(capa, (0, 0), capa)
    return y + (len(plan["renglones"]) - 1) * plan["salto"] + f.getbbox("HÁGQ")[3]


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Marca y progreso
# ─────────────────────────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=4)
def _iso_chico(alto: int) -> Image.Image:
    return D.isologo(alto)


def marca_pie(im: Image.Image, alto: int = 46, margen: int = 40, arriba: int = 24):
    """El isologo chico ARRIBA a la derecha (la estética nueva en cada diapositiva; abajo pisaba la fuente)."""
    iso = _iso_chico(alto)
    pos = (im.width - margen - iso.width, arriba)
    if im.mode == "RGBA":
        im.alpha_composite(iso, pos)
    else:
        im.paste(iso, pos, iso)


def progreso(im: Image.Image, avance: float, alto: int = 8):
    """La barra de progreso naranja arriba, sobre una pista oscura."""
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, alto), fill=(52, 55, 62))
    d.rectangle((0, 0, round(im.width * max(0.0, min(1.0, avance))), alto), fill=D.NARANJA)


def transicion(anterior: Image.Image, nueva: Image.Image, t: float) -> Image.Image:
    """La nueva entra desde abajo y empuja a la anterior hacia arriba (un poco oscurecida), con una franja
    naranja en el borde. Fuera de la transición devuelve `nueva`."""
    if t >= TRANSICION or anterior is None:
        return nueva
    if not activo():
        return Image.blend(anterior, nueva, t / TRANSICION)
    e = ease_out(t / TRANSICION)
    W, H = nueva.size
    y_nueva = round(H * (1 - e))
    cuadro = Image.new("RGB", (W, H), (0, 0, 0))
    vieja = anterior if e < 0.02 else Image.blend(anterior, Image.new("RGB", (W, H), (0, 0, 0)), 0.45 * e)
    cuadro.paste(vieja, (0, -round(H * 0.3 * e)))
    cuadro.paste(nueva, (0, y_nueva))
    if 0 < y_nueva < H:
        ImageDraw.Draw(cuadro).rectangle((0, y_nueva - 12, W, y_nueva), fill=D.NARANJA)
    return cuadro


def pop_sprite(im: Image.Image, sprite: Image.Image, centro: tuple, escala: float, alfa: float = 1.0):
    """Pega `sprite` (RGBA) escalado alrededor de `centro`."""
    if escala <= 0.01 or alfa <= 0:
        return
    w, h = max(1, round(sprite.width * escala)), max(1, round(sprite.height * escala))
    s = sprite.resize((w, h), Image.BILINEAR) if (w, h) != sprite.size else sprite
    if alfa < 1:
        s = s.copy()
        s.putalpha(s.getchannel("A").point(lambda v: round(v * alfa)))
    pos = (round(centro[0] - w / 2), round(centro[1] - h / 2))
    if im.mode == "RGBA":
        if pos[0] >= 0 and pos[1] >= 0 and pos[0] + w <= im.width and pos[1] + h <= im.height:
            im.alpha_composite(s, pos)
        else:                                           # se sale del borde: por una capa del tamaño de la imagen
            capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
            capa.paste(s, pos)
            im.alpha_composite(capa)
    else:
        im.paste(s, pos, s)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Sonidos (los del reel de entrevistas del diario, generados con numpy)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _t(seg: float) -> np.ndarray:
    return np.arange(int(SR * seg)) / SR


def pop(tono: float = 1.0) -> np.ndarray:
    """Un «pop» de burbuja: un tono que cae rápido, con un golpecito al principio."""
    t = _t(0.11)
    f = (820 * tono) * np.exp(-t * 28) + 190 * tono
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    clic = np.random.default_rng(int(tono * 1000)).normal(0, 1, t.size) * np.exp(-t * 900) * 0.35
    return (s + clic) * np.minimum(1, t / 0.002)


def tecla(semilla: int = 0) -> np.ndarray:
    """Una tecla de máquina de escribir: el clac seco y el golpe del tipo."""
    rng = np.random.default_rng(semilla)
    t = _t(0.06)
    ruido = np.diff(np.concatenate([[0], rng.normal(0, 1, t.size)]))
    clac = ruido * np.exp(-t * rng.uniform(170, 230)) * 0.55
    golpe = np.sin(2 * np.pi * rng.uniform(140, 190) * t) * np.exp(-t * 70) * 0.5
    return (clac + golpe) * rng.uniform(0.75, 1.0)


def campanita() -> np.ndarray:
    t = _t(0.9)
    s = np.sin(2 * np.pi * 2093 * t) + 0.45 * np.sin(2 * np.pi * 4186 * t) + 0.2 * np.sin(2 * np.pi * 3136 * t)
    return s * np.exp(-t * 5.5) * np.minimum(1, t / 0.003) * 0.5


def brisa(seg: float = 0.38) -> np.ndarray:
    """El soplido de la transición (un barrido de ruido que sube y baja)."""
    t = _t(seg)
    ruido = np.random.default_rng(7).normal(0, 1, t.size)
    suave = np.convolve(ruido, np.ones(32) / 32, mode="same")
    return suave * np.sin(np.pi * np.clip(t / seg, 0, 1)) ** 2 * 1.4


def tic(tono: float = 1.0) -> np.ndarray:
    """Un tic corto y agudo (los números que cuentan, las columnas que aparecen)."""
    t = _t(0.03)
    return np.sin(2 * np.pi * 2400 * tono * t) * np.exp(-t * 160) * 0.6


def base_musical(duracion: float, bpm: int = BPM) -> np.ndarray:
    """Una base suave y pareja: bombo en 1 y 3, hi-hat en las corcheas y un acorde que cambia cada compás
    (la-fa-do-sol). Va bajita, debajo de los efectos."""
    n = int(SR * duracion)
    pista = np.zeros(n)
    negra = 60 / bpm
    rng = np.random.default_rng(3)
    tb = _t(0.35)
    bombo = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-tb * 30)) / SR) * np.exp(-tb * 9)
    th = _t(0.05)
    hat = np.diff(np.concatenate([[0], rng.normal(0, 1, th.size)])) * np.exp(-th * 90) * 0.35
    k = 0
    while k * negra / 2 < duracion:
        i = int(k * negra / 2 * SR)
        if k % 4 == 0:
            pista[i:i + bombo.size] += bombo[:max(0, min(bombo.size, n - i))]
        if k % 2 == 1:
            pista[i:i + hat.size] += hat[:max(0, min(hat.size, n - i))] * (0.8 if k % 4 == 3 else 0.5)
        k += 1
    acordes = ((220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66))
    compas = negra * 4
    c = 0
    while c * compas < duracion:
        i0 = int(c * compas * SR)
        tt = _t(compas)
        env = np.minimum(1, tt / 0.25) * np.minimum(1, (compas - tt) / 0.3)
        pad = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) for f in acordes[c % 4])
        m = min(tt.size, n - i0)
        if m > 0:
            pista[i0:i0 + m] += (pad * env)[:m] * 0.07
        c += 1
    return pista * 0.55


def mezclar(eventos: list, duracion: float, musica: bool = True) -> np.ndarray:
    """[(segundo, señal, volumen)] (+ la base) → pista estéreo float32."""
    n = int(SR * duracion)
    pista = np.zeros(n + SR)
    for seg, senal, vol in eventos:
        i = int(seg * SR)
        if 0 <= i < pista.size:
            m = min(senal.size, pista.size - i)
            pista[i:i + m] += senal[:m] * vol
    pista = pista[:n]
    pico = float(np.max(np.abs(pista))) or 1.0
    pista = pista / pico * 0.8
    if musica:
        b = base_musical(duracion)
        pista = pista + b[:n] / (float(np.max(np.abs(b))) or 1.0) * 0.22
    pico = float(np.max(np.abs(pista))) or 1.0
    pista = pista / pico
    # Un compresor suave (saturación tanh): los efectos se escuchan sin subir los picos (Instagram normaliza).
    pista = np.tanh(pista * 2.4) / np.tanh(2.4) * 0.93
    fade = int(SR * 0.5)
    if pista.size > fade:
        pista[-fade:] *= np.linspace(1, 0, fade)
    return np.stack([pista, pista], axis=1).astype(np.float32)


def guardar_wav(pista: np.ndarray, destino: Path) -> Path:
    datos = (np.clip(pista, -1, 1) * 32767).astype("<i2")
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(datos.tobytes())
    return Path(destino)


def eventos_titulo(t0: float, n_palabras: int) -> list:
    return [(t0 + k * PALABRA, pop(1.0 + 0.06 * k), 0.45) for k in range(min(n_palabras, 10))]
