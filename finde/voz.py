# -*- coding: utf-8 -*-
"""VOZ: la narración de cada escena con una voz neural en español rioplatense (edge-tts, sin clave), con el tiempo
de cada palabra para los subtítulos sincronizados.

FINDE_VOZ elige la voz (es-AR-TomasNeural de fábrica; es-AR-ElenaNeural es la otra) y FINDE_VOZ_VELOCIDAD el ritmo
(«+8%»). FINDE_VOZ=0 la apaga. Si el servicio no responde, la escena queda SIN VOZ y con los tiempos estimados (el
reel sale igual, con música y subtítulos, y el informe lo dice): nunca se frena una corrida por la voz.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
VOZ_DEFECTO = "es-AR-TomasNeural"
VELOCIDAD_DEFECTO = "+8%"
SEG_POR_PALABRA = 0.36            # para estimar cuando no hay voz
TOPE_SEG = 45                     # lo máximo que se espera una respuesta del servicio de voz


def voz() -> str:
    return (os.environ.get("FINDE_VOZ") or VOZ_DEFECTO).strip()


def activa() -> bool:
    return voz() != "0"


def _ffmpeg() -> str:
    from agro import reel_zona as RZ
    return RZ._ffmpeg()


async def _hablar(texto: str, destino: Path) -> list:
    import edge_tts
    c = edge_tts.Communicate(texto, voz(), rate=os.environ.get("FINDE_VOZ_VELOCIDAD") or VELOCIDAD_DEFECTO,
                             boundary="WordBoundary")
    marcas = []
    with open(destino, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                ini = ch["offset"] / 1e7
                marcas.append((ini, ini + ch["duration"] / 1e7, ch["text"]))
    return marcas


def leer_wav(ruta: Path) -> np.ndarray:
    with wave.open(str(ruta), "rb") as w:
        datos = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        if w.getnchannels() == 2:
            datos = datos.reshape(-1, 2).mean(axis=1)
    return datos


def _plano(p: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", p.lower())
    return "".join(c for c in t if c.isalnum())


def alinear(marcas: list, texto: str) -> list:
    """Las palabras de la voz vienen sin puntuación («cuadra» en vez de «cuadra?»): se les pone la del guion, para
    que los subtítulos corten en las comas y los puntos y muestren el texto como está escrito."""
    tokens = texto.split()
    salida, j = [], 0
    for ini, fin, p in marcas:
        q = _plano(p)
        k = j
        while k < len(tokens) and q and q not in _plano(tokens[k]) and k < j + 3:
            k += 1
        if k < len(tokens) and q and q in _plano(tokens[k]):
            salida.append((ini, fin, tokens[k].strip("¿¡")))
            j = k + 1
        else:
            salida.append((ini, fin, p))
    return salida


def estimar(texto: str) -> list:
    """Los tiempos de cada palabra sin voz (un ritmo de lectura parejo)."""
    salida, t = [], 0.0
    for p in texto.split():
        d = SEG_POR_PALABRA + (0.18 if p[-1:] in ".,;:?!" else 0)
        salida.append((t, t + SEG_POR_PALABRA * 0.9, p.strip("¿¡")))
        t += d
    return salida


def narrar(texto: str, carpeta: Path, nombre: str, hablar=None) -> dict:
    """{"audio": np.ndarray mono 44,1 kHz o None, "dur": segundos, "palabras": [(ini, fin, palabra)], "voz": …}."""
    texto = " ".join((texto or "").split())
    if not texto:
        return {"audio": None, "dur": 0.0, "palabras": [], "voz": "sin texto"}
    if not activa():
        p = estimar(texto)
        return {"audio": None, "dur": p[-1][1] + 0.3, "palabras": p, "voz": "apagada"}
    carpeta.mkdir(parents=True, exist_ok=True)
    mp3, wav = carpeta / f"{nombre}.mp3", carpeta / f"{nombre}.wav"
    try:
        marcas = None
        for intento in (1, 2):
            try:
                # 26/11/2026: un pedido de voz quedó colgado 38 min sin responder; ahora cada uno tiene un tope y
                # se reintenta una vez. Si tampoco anda, la escena va sin voz (con los tiempos estimados).
                marcas = (hablar or (lambda t, d: asyncio.run(asyncio.wait_for(_hablar(t, d), TOPE_SEG))))(texto, mp3)
                break
            except (asyncio.TimeoutError, TimeoutError):
                if intento == 2:
                    raise
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", str(SR), str(wav)],
                       check=True)
        audio = leer_wav(wav)
        if audio.size < SR * 0.3 or not marcas:
            raise RuntimeError("la voz vino vacía")
        return {"audio": audio, "dur": audio.size / SR, "palabras": alinear(marcas, texto), "voz": voz()}
    except Exception as e:                           # noqa: BLE001 — sin voz, el reel sale igual
        p = estimar(texto)
        return {"audio": None, "dur": p[-1][1] + 0.3, "palabras": p, "voz": f"sin voz ({type(e).__name__}: {e})"[:160]}
