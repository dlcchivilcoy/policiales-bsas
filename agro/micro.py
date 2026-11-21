# -*- coding: utf-8 -*-
"""MICRO ANIMACIONES de las placas de datos en los reels de @diarioyradioagro (21/11/2026).

Pedido del editor: «hacé el resumen con animaciones en el reel, no simplemente un zoom de toda la placa, sino que la
placa tenga micro animaciones». Antes cada placa del reel «El campo hoy» se veía quieta con un acercamiento lento.
Ahora entra por partes: se compara la placa terminada con su fondo vacío, se encuentran las FRANJAS con contenido
(la marca, la caja de la sección, cada renglón del título, cada tarjeta, la referencia, el pie) y, dentro de cada
franja, los BLOQUES separados por aire (las dos tarjetas de una fila, las palabras de un título grande). Cada bloque
sube y aparece con un pequeño rebote, en cascada de arriba abajo, con un «pop» de sonido por franja.

Sirve para cualquier placa de la que se tenga el fondo: las del resumen (agro/historias.py las deja anotadas al
guardarlas), la tapa del resumen (el fondo es la misma tapa sin tablero) y las láminas del perfil productivo
(agro/perfil.py). Lo que necesita una animación propia (el mapa de lluvias, el mapa del partido) va como ESPECIAL:
una caja y una función que lo dibuja según el avance; si `continuo`, se sigue moviendo después de entrar (el pulso
sobre Chivilcoy).

AGRO_MICRO=0 vuelve a la placa quieta con acercamiento (y AGRO_REEL_MOVIMIENTO=0 apaga todo el movimiento).
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageFilter

UMBRAL = 26          # diferencia mínima (suma de R, G y B) para que un píxel sea contenido y no fondo
HUECO_V = 8          # filas vacías que separan dos franjas
HUECO_H = 22         # columnas vacías que separan dos bloques de una misma franja
ENTRADA = 0.42       # lo que tarda cada bloque en subir y aparecer
PASO = 0.14          # entre franja y franja
PRESUPUESTO = 1.8    # todas las franjas arrancan dentro de este tiempo (si son muchas, la cascada va más rápido)
SUBIDA = 30          # px que sube cada bloque


def activo() -> bool:
    from agro import movimiento as MV
    return MV.activo() and (os.environ.get("AGRO_MICRO") or "1").strip() != "0"


def _ease_out(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def _ease_back(x: float) -> float:
    if x <= 0:
        return 0.0                                   # exacto: la fórmula da 1e-16 y «aparecería» algo invisible
    x = min(1.0, x)
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


def _tramos(v: np.ndarray, hueco: int) -> list:
    """[(desde, hasta)] de los índices True de `v`, uniendo los que están a menos de `hueco` de distancia."""
    idx = np.flatnonzero(v)
    if not idx.size:
        return []
    salida, a, b = [], int(idx[0]), int(idx[0])
    for i in idx[1:]:
        i = int(i)
        if i - b > hueco:
            salida.append((a, b + 1))
            a = i
        b = i
    salida.append((a, b + 1))
    return salida


def contenido(final: Image.Image, fondo: Image.Image, umbral: int = UMBRAL) -> np.ndarray:
    """La máscara (alto × ancho, bool) de lo que la placa tiene encima del fondo."""
    a = np.asarray(final.convert("RGB"), dtype=np.int16)
    b = np.asarray(fondo.convert("RGB").resize(final.size), dtype=np.int16)
    return np.abs(a - b).sum(axis=2) > umbral


def franjas(mascara: np.ndarray, hueco_v: int = HUECO_V, hueco_h: int = HUECO_H, desde_y: int = 0) -> list:
    """[[(x0, y0, x1, y1) por bloque] por franja], de arriba abajo. Descarta el ruido (manchitas de JPEG)."""
    m = mascara.copy()
    m[:desde_y] = False
    salida = []
    for y0, y1 in _tramos(m.any(axis=1), hueco_v):
        bloques = []
        for x0, x1 in _tramos(m[y0:y1].any(axis=0), hueco_h):
            if m[y0:y1, x0:x1].sum() >= 30:
                bloques.append((x0, y0, x1, y1))
        if bloques:
            salida.append(bloques)
    return salida


def _cruza(a: tuple, caja: tuple) -> bool:
    x, y, w, h = caja
    return not (a[2] <= x or a[0] >= x + w or a[3] <= y or a[1] >= y + h)


class Animacion:
    """fn(t) → la placa en el segundo t (RGB). `tiempos`: cuándo arranca cada franja (para el sonido)."""

    def __init__(self, final: Image.Image, fondo: Image.Image, inicio: float = 0.15, especiales=(),
                 presupuesto: float = PRESUPUESTO, umbral: int = UMBRAL):
        self.final = final.convert("RGB")
        self.fondo = fondo.convert("RGB").resize(self.final.size)
        m = contenido(self.final, self.fondo, umbral)
        grupos = franjas(m)
        paso = min(PASO, presupuesto / max(1, len(grupos)))
        mascara = Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(5))
        self.especiales = [dict(e, t0=None) for e in especiales]
        self.piezas, self.tiempos = [], []
        t = inicio
        for g in grupos:
            sub = min(0.05, 0.3 / len(g))
            arranco = False
            for j, caja in enumerate(g):
                esp = next((e for e in self.especiales if _cruza(caja, e["caja"])), None)
                if esp is not None:                           # lo dibuja el especial (el mapa), no el recorte
                    if esp["t0"] is None:
                        esp["t0"] = t
                    continue
                self.piezas.append((t + j * sub, caja, self.final.crop(caja), mascara.crop(caja)))
                arranco = True
            if arranco or any(e["t0"] == t for e in self.especiales):
                self.tiempos.append(round(t, 3))
            t += paso
        for e in self.especiales:                             # un especial que no tocó ninguna franja: al final
            if e["t0"] is None:
                e["t0"] = t
        fin = [t0 + ENTRADA for t0, *_ in self.piezas] + [e["t0"] + e.get("dur", 2.4) for e in self.especiales]
        self.fin = max(fin) if fin else 0.0
        self.continuo = any(e.get("continuo") for e in self.especiales)

    def __call__(self, t: float) -> Image.Image:
        if t >= self.fin and not self.continuo:
            return self.final
        im = self.fondo.copy()
        for t0, caja, recorte, mascara in self.piezas:
            p = (t - t0) / ENTRADA
            if p <= 0:
                continue
            if p >= 1:
                im.paste(recorte, caja[:2], mascara)
                continue
            a = _ease_out(p)
            dy = round((1 - _ease_back(p)) * SUBIDA)
            im.paste(recorte, (caja[0], caja[1] + dy), mascara.point(lambda v, a=a: round(v * a)))
        for e in self.especiales:
            if t < e["t0"]:
                continue
            capa = e["fn"]((t - e["t0"]) / e.get("dur", 2.4))
            x, y, w, h = e["caja"]
            if capa.size != (w, h):
                capa = capa.resize((w, h), Image.BILINEAR)
            im.paste(capa.convert("RGB"), (x, y), capa.getchannel("A") if capa.mode == "RGBA" else None)
        return im


def eventos(tiempos: list, s0: float = 0.0) -> list:
    """Los sonidos de una placa animada: un pop por franja (el tono sube de a poco), como las filas de los reels."""
    from agro import movimiento as MV
    return [(s0 + t, MV.pop(1.0 + 0.04 * i) * 0.8, 0.32) for i, t in enumerate(tiempos[:12])]
