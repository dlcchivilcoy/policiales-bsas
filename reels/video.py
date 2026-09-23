# -*- coding: utf-8 -*-
"""Arma el .mp4 vertical 1080x1920 del reel, sin audio.

La pieza tiene dos tramos:

  1. LA NOTA — el fondo de color, la foto con un zoom lento encima y la capa de texto
     QUIETA por delante. El texto no se mueve: si se animara la placa entera, el titular
     escalaría con la foto y se leería mal.
  2. EL CIERRE — `placa_final.png`, la misma que usa el bot de corresponsales.

Entre los dos va un fundido corto.

Usa el ffmpeg de `imageio-ffmpeg`, con la versión FIJADA en requirements. No es un
capricho: ese paquete trae adentro el binario con el que se arman los videos, y con «>=»
cada despliegue podía traer un ffmpeg distinto —otros filtros, otros valores por
defecto— y romper los reels sin que nadie tocara una línea. Es de lo más difícil de
diagnosticar que hay: el código está igual, el repo está igual, y ayer andaba.
"""
import subprocess
from pathlib import Path

from reels import marca as M

FPS = 30
SEG_NOTA = 8.0          # cuánto dura el tramo de la nota
SEG_CIERRE = 3.0        # cuánto dura la placa de cierre
FUNDIDO = 0.6           # el fundido entre los dos tramos
ZOOM_MAX = 1.12         # hasta dónde llega el acercamiento lento
TIMEOUT = 300

# Control de tasa. Sin esto, libx264 deja un reel de 1080x1920 en más de 20 MB, que tarda
# una eternidad en abrirse desde el celular para revisarlo — y es lo mismo que después
# sube a la red, donde igual lo vuelven a comprimir. CRF 26 con techo de 3,5 Mb/s lo baja
# a menos de la mitad sin diferencia visible en un teléfono. (Mismos valores que video.py
# en social_publisher.)
CRF = "26"
MAXRATE = "3500k"
BUFSIZE = "7000k"


class FfmpegError(RuntimeError):
    """ffmpeg no pudo armar el video. El mensaje lleva el motivo que se pudo leer."""


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"          # en la nube puede venir del sistema


def _motivo(stderr: str) -> str:
    """La línea útil del vómito de ffmpeg, para que el error diga algo."""
    for linea in reversed((stderr or "").strip().splitlines()):
        l = linea.strip()
        if l and not l.startswith(("frame=", "size=", "[libx264", "video:", "  ")):
            return l[:200]
    return ""


def _correr(cmd: list, paso: str) -> None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise FfmpegError(f"{paso}: ffmpeg pasó los {TIMEOUT}s y lo corté") from None
    if r.returncode != 0:
        raise FfmpegError(f"{paso}: {_motivo(r.stderr)}")


def _salida(cmd: list) -> list:
    """Los parámetros de codificación, iguales para todos los tramos."""
    return cmd + [
        "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", CRF, "-maxrate", MAXRATE, "-bufsize", BUFSIZE,
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]


def _tramo_nota(informe: dict, salida: Path, seg: float) -> Path:
    """El tramo de la nota: fondo + foto con zoom lento + texto quieto encima."""
    ff = ffmpeg_exe()
    cuadros = int(seg * FPS)
    fondo = informe.get("capa_fondo")
    texto = informe.get("capa_texto")
    foto = informe.get("capa_foto")
    alto_img = int(informe.get("alto_imagen") or M.PLACA_IMG_MIN)
    y_img = int(informe.get("y_img") or (M.H - alto_img))

    if not texto or not Path(texto).exists():
        raise FfmpegError("falta la capa de texto: hay que componer la placa con capas=True")

    clip = informe.get("clip")
    if clip and Path(clip).exists():
        # Video de verdad en lugar de la foto con zoom. El clip se recorta a la caja
        # de la imagen igual que lo haria una foto: se agranda hasta tapar la caja y
        # se corta lo que sobra, asi nunca quedan bandas negras a los costados.
        #
        # -stream_loop -1 es para los clips CORTOS: si el medio subio 4 segundos y el
        # tramo dura 8, sin esto el video se congela en el ultimo cuadro y parece que
        # se colgo. Loopeando, sigue en movimiento hasta el final.
        #
        # Sin audio (-an) a proposito: el cierre es una placa muda, y pegar un tramo
        # con sonido a uno sin sonido deja el reel con audio a la mitad. Es una
        # decision a revisar el dia que se quiera aprovechar el sonido original.
        entradas = ["-stream_loop", "-1", "-t", f"{seg:.3f}", "-i", str(clip),
                    "-loop", "1", "-t", f"{seg:.3f}", "-i", str(fondo),
                    "-loop", "1", "-t", f"{seg:.3f}", "-i", str(texto)]
        filtro = (
            f"[0:v]scale={M.W}:{alto_img}:force_original_aspect_ratio=increase,"
            f"crop={M.W}:{alto_img},fps={FPS},setsar=1,setpts=PTS-STARTPTS[mov];"
            f"[1:v]scale={M.W}:{M.H},setsar=1[bg];"
            f"[bg][mov]overlay=0:{y_img}:shortest=1[conf];"
            f"[conf][2:v]overlay=0:0[out]"
        )
        cmd = _salida([ff, "-y", *entradas, "-filter_complex", filtro,
                       "-map", "[out]", "-an", "-t", f"{seg:.3f}"]) + [str(salida)]
        _correr(cmd, "tramo de la nota (con video)")
        return salida

    if foto and Path(foto).exists():
        # zoompan trabaja sobre UNA imagen y saca `d` cuadros de ella, acercándose de a
        # poco. Se parte de la foto al doble de tamaño para que el acercamiento no la
        # deje blanda. `x`/`y` mantienen el centro fijo: un zoom que además se desplaza
        # marea en un reel de 8 segundos.
        entradas = ["-i", str(foto), "-loop", "1", "-t", f"{seg:.3f}", "-i", str(fondo),
                    "-loop", "1", "-t", f"{seg:.3f}", "-i", str(texto)]
        filtro = (
            f"[0:v]zoompan=z='min(zoom+{(ZOOM_MAX - 1) / cuadros:.6f},{ZOOM_MAX})'"
            f":d={cuadros}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s={M.W}x{alto_img}:fps={FPS},setsar=1[mov];"
            f"[1:v]scale={M.W}:{M.H},setsar=1[bg];"
            f"[bg][mov]overlay=0:{y_img}:shortest=1[conf];"
            f"[conf][2:v]overlay=0:0[out]"
        )
    else:
        # Sin foto no hay nada que animar: queda el fondo liso con el texto.
        entradas = ["-loop", "1", "-t", f"{seg:.3f}", "-i", str(fondo),
                    "-loop", "1", "-t", f"{seg:.3f}", "-i", str(texto)]
        filtro = (f"[0:v]scale={M.W}:{M.H},setsar=1[bg];"
                  f"[bg][1:v]overlay=0:0[out]")

    cmd = _salida([ff, "-y", *entradas, "-filter_complex", filtro,
                   "-map", "[out]", "-t", f"{seg:.3f}"]) + [str(salida)]
    _correr(cmd, "tramo de la nota")
    return salida


def primer_cuadro(clip: Path, destino: Path) -> Path | None:
    """Saca un cuadro del clip para usarlo como si fuera la foto de la nota.

    Hace falta porque la placa se compone sobre una IMAGEN: de ahi salen el color
    dominante del fondo y la altura de la caja. Sin esto habria que duplicar toda esa
    logica para el caso del video.

    Se toma el segundo 1 y no el 0: el primer cuadro de un video suele ser negro o el
    fundido de entrada, y de un cuadro negro sale un fondo negro.
    """
    try:
        cmd = [ffmpeg_exe(), "-y", "-ss", "1", "-i", str(clip), "-frames:v", "1",
               "-q:v", "2", str(destino)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and destino.exists() and destino.stat().st_size > 0:
            return destino
        # Clip de menos de un segundo: se reintenta desde el principio.
        cmd[cmd.index("-ss") + 1] = "0"
        subprocess.run(cmd, capture_output=True, text=True)
        return destino if destino.exists() and destino.stat().st_size > 0 else None
    except Exception:
        return None


def _tramo_cierre(salida: Path, seg: float) -> Path | None:
    """La placa de cierre «Seguinos en redes»."""
    if not M.PLACA_FINAL.exists():
        return None
    cmd = _salida([ffmpeg_exe(), "-y", "-loop", "1", "-t", f"{seg:.3f}",
                   "-i", str(M.PLACA_FINAL),
                   "-vf", f"scale={M.W}:{M.H}:force_original_aspect_ratio=increase,"
                          f"crop={M.W}:{M.H},setsar=1"]) + [str(salida)]
    _correr(cmd, "placa de cierre")
    return salida


def _unir(nota: Path, cierre: Path, salida: Path, seg_nota: float, fundido: float) -> Path:
    """Une los dos tramos con un fundido. El fundido arranca `fundido` segundos antes de
    que termine el primero, así el total es la suma menos el fundido."""
    off = max(0.0, seg_nota - fundido)
    filtro = (f"[0:v][1:v]xfade=transition=fade:duration={fundido}:offset={off:.3f}[out]")
    cmd = _salida([ffmpeg_exe(), "-y", "-i", str(nota), "-i", str(cierre),
                   "-filter_complex", filtro, "-map", "[out]"]) + [str(salida)]
    _correr(cmd, "unión de los tramos")
    return salida


def armar(informe: dict, salida: Path, *, seg_nota: float = SEG_NOTA,
          seg_cierre: float = SEG_CIERRE, fundido: float = FUNDIDO) -> dict:
    """Arma el reel a partir del informe que devolvió `placa.componer(..., capas=True)`.

    Devuelve {archivo, duracion, peso_kb, tramos}.
    """
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.parent / "_tmp"
    tmp.mkdir(exist_ok=True)

    nota = _tramo_nota(informe, tmp / f"{salida.stem}_nota.mp4", seg_nota)
    cierre = _tramo_cierre(tmp / f"{salida.stem}_cierre.mp4", seg_cierre)

    if cierre:
        _unir(nota, cierre, salida, seg_nota, fundido)
        duracion = seg_nota + seg_cierre - fundido
        tramos = ["nota", "cierre"]
    else:
        nota.replace(salida)
        duracion = seg_nota
        tramos = ["nota"]

    for f in tmp.glob(f"{salida.stem}_*.mp4"):
        f.unlink(missing_ok=True)
    try:
        tmp.rmdir()
    except OSError:
        pass                      # quedan tramos de otras piezas: se limpian después

    return {
        "archivo": str(salida),
        "duracion": round(duracion, 2),
        "peso_kb": round(salida.stat().st_size / 1024) if salida.exists() else 0,
        "tramos": tramos,
        "con_foto": bool(informe.get("capa_foto")),
        "con_video": bool(informe.get("clip")),
    }


def duracion_de(mp4: Path) -> float:
    """Duración real del archivo, leída de ffmpeg. Sirve para verificar que salió lo que
    se pidió y no lo que uno cree que pidió."""
    r = subprocess.run([ffmpeg_exe(), "-i", str(mp4)], capture_output=True, text=True)
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", r.stderr or "")
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)
