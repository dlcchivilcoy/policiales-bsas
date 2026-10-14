# -*- coding: utf-8 -*-
"""El reel agro (punto 15 del documento): 1080x1920, ~19 s, sin voz (la locución queda preparada
para más adelante, punto 16). Misma diagramación que la portada: la imagen arriba con un
movimiento lento y el bloque grafito abajo, donde el texto cambia por tramos:

    0-3 s   GANCHO
    3-7 s   QUÉ PASÓ
    7-12 s  LOS DATOS (aparecen de a uno)
    12-16 s POR QUÉ IMPORTA (para el productor / Argentina)
    16-19 s CIERRE con el logo y @diarioyradioagro

Es un motor propio y chico a propósito: el del bot (estetica_bot/) lleva la marca del diario en sus
archivos, y agro tiene identidad propia. Los cuadros se dibujan con PIL y van por un caño a ffmpeg
(el de imageio-ffmpeg, el mismo que usa policiales).
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from agro import portada as P

FPS = 24
TRAMOS = (("gancho", 3.0), ("que_paso", 4.0), ("datos", 5.0), ("por_que_importa", 4.0), ("cierre", 3.0))
FUNDIDO = 0.35          # segundos de entrada de cada texto
ZOOM = 0.10             # cuánto se acerca la imagen en todo el reel


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _bloque_texto(d, guion: dict, tramo: str, t: float, y0: int) -> None:
    """El texto del tramo `tramo`, `t` segundos después de que empezó."""
    alfa = min(1.0, t / FUNDIDO)

    def color(c):
        return tuple(round(v * alfa + P.FONDO[i] * (1 - alfa)) for i, v in enumerate(c))
    ancho = P.W - 2 * P.MARGEN
    y = y0
    if tramo == "gancho":
        f, r = P.ajustar(d, guion["reel"]["gancho"] or guion["titular"], "titulo", 84, 56, ancho, 4)
        for linea in r:
            d.text((P.MARGEN, y), linea, font=f, fill=color(P.BLANCO))
            y += round(f.size * 1.12)
        return
    rotulo = {"que_paso": "QUÉ PASÓ", "datos": "LOS DATOS", "por_que_importa": "POR QUÉ IMPORTA"}[tramo]
    d.text((P.MARGEN, y), rotulo, font=P.fuente("titulo", 32), fill=color(P.NARANJA))
    y += 64
    if tramo == "datos":
        datos = guion["reel"]["datos"] or guion.get("datos_clave", [])[:3]
        cada = 5.0 / max(1, len(datos))
        for i, dato in enumerate(datos):
            ti = t - i * cada
            if ti < 0:
                break
            a = min(1.0, ti / FUNDIDO)
            f, r = P.ajustar(d, dato, "texto", 46, 34, ancho - 50, 3)
            d.ellipse((P.MARGEN, y + 16, P.MARGEN + 18, y + 34),
                      fill=tuple(round(v * a + P.FONDO[k] * (1 - a)) for k, v in enumerate(P.VERDE)))
            for linea in r:
                d.text((P.MARGEN + 44, y), linea,
                       font=f, fill=tuple(round(v * a + P.FONDO[k] * (1 - a)) for k, v in enumerate(P.BLANCO)))
                y += round(f.size * 1.25)
            y += 22
        return
    texto = guion["reel"][tramo] or (guion["bajada"] if tramo == "que_paso" else "")
    f, r = P.ajustar(d, texto, "texto", 54, 38, ancho, 5)
    for linea in r:
        d.text((P.MARGEN, y), linea, font=f, fill=color(P.BLANCO))
        y += round(f.size * 1.28)


def _cierre(guion: dict, t: float) -> Image.Image:
    lienzo = Image.new("RGBA", (P.W, P.H), P.FONDO + (255,))
    alfa = min(1.0, t / FUNDIDO)
    lg = P.logo(460)
    lg.putalpha(lg.getchannel("A").point(lambda a: round(a * alfa)))
    lienzo.alpha_composite(lg, ((P.W - lg.width) // 2, 470))
    d = ImageDraw.Draw(lienzo)

    def centrado(texto, f, y, c):
        d.text(((P.W - d.textlength(texto, font=f)) / 2, y), texto, font=f,
               fill=tuple(round(v * alfa + P.FONDO[i] * (1 - alfa)) for i, v in enumerate(c)))
    centrado("DIARIO Y RADIO", P.fuente("titulo", 56), 1010, P.BLANCO)
    centrado("AGRO", P.fuente("titulo", 56), 1078, P.NARANJA)
    centrado(P.USUARIO, P.fuente("titulo", 44), 1200, P.VERDE)
    if guion["reel"].get("cierre"):
        f, r = P.ajustar(d, guion["reel"]["cierre"], "texto", 40, 30, P.W - 2 * P.MARGEN, 2)
        for i, linea in enumerate(r):
            centrado(linea, f, 1330 + i * round(f.size * 1.3), P.GRIS)
    return lienzo


def armar(guion: dict, imagen, salida: Path, ia: bool = False, credito: str = "") -> dict:
    """El .mp4 y un .jpg del primer tramo al lado. Lanza si ffmpeg falla."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    total = sum(s for _, s in TRAMOS)
    cuadros = round(total * FPS)
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{P.W}x{P.H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-t", str(total), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "24",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(salida)]
    foto = Image.open(imagen).convert("RGB") if imagen else None
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vista = None
    try:
        for k in range(cuadros):
            seg = k / FPS
            acum, tramo, t = 0.0, TRAMOS[-1][0], 0.0
            for nombre, dur in TRAMOS:
                if seg < acum + dur:
                    tramo, t = nombre, seg - acum
                    break
                acum += dur
            if tramo == "cierre":
                cuadro = _cierre(guion, t)
            else:
                cuadro = Image.new("RGBA", (P.W, P.H), P.FONDO + (255,))
                avance = seg / max(1e-9, total - TRAMOS[-1][1])
                if foto:
                    cuadro.paste(P.imagen_arriba(foto, zoom=1 + ZOOM * avance, corrimiento=0.25 * avance - 0.12,
                                                 rapido=True), (0, 0))
                    P.fundido(cuadro, P.ALTO_IMAGEN - 420, P.ALTO_IMAGEN)
                P.cabecera(cuadro)
                d = ImageDraw.Draw(cuadro)
                y = P.ALTO_IMAGEN - 60
                y += P.etiqueta(d, P.MARGEN, y, guion.get("volanta")) + 40
                _bloque_texto(d, guion, tramo, t, y)
                P.pie(d, ia, credito)
            rgb = cuadro.convert("RGB")
            if vista is None and tramo == "gancho" and t >= 1.0:
                vista = rgb.copy()
            proc.stdin.write(rgb.tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not salida.exists():
            raise RuntimeError(f"ffmpeg: {err[-300:]}")
    finally:
        if proc.poll() is None:
            proc.kill()
    jpg = salida.with_suffix(".jpg")
    if vista is not None:
        vista.save(jpg, "JPEG", quality=88)
    return {"archivo": str(salida), "duracion": total, "peso_kb": round(salida.stat().st_size / 1024),
            "vista": str(jpg) if jpg.exists() else None}
