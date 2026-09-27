# -*- coding: utf-8 -*-
"""Arma el reel con el MOTOR DEL BOT DEL DIARIO: la misma estetica que sus reels.

Pedido del editor (26/09/2026): «actualizar la estetica de los reels que tiene el bot para
los reels de policiales». El motor vive en estetica_bot/ copiado TAL CUAL del bot
(tools/traer_estetica_bot.py); este modulo es lo unico propio de policiales: que texto
va, cuanto dura y cuanto pesa.

Que hace el motor, segun la FORMA de la foto (decidido en el bot el 25 y 26/09):
- vertical: la imagen en los 3/4 de abajo a todo el ancho, recortada desde abajo para no
  cortar cabezas; arriba marca, volanta de un renglon y titular en dos; sin bajada.
- horizontal (y cuadrada): entera, titular hasta 3 renglones y la bajada DEBAJO.
- afiche: a cuadro completo, solo marca e isologo.
Google Sans a la izquierda, volanta naranja, titular y bajada blancos, fondo carbon con
humo, isologo a la derecha y la placa de cierre «Seguinos en redes».
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTETICA = RAIZ / "estetica_bot"

# Cuanto dura el reel de una FOTO: 8 s de nota + los 5 s de la placa de cierre del bot.
# El bot usa 30 s para sus foto-notas; un policial breve con una foto quieta 25 s se
# abandona antes de terminar. Antes de adoptar el motor del bot los de policiales duraban
# 10,4 s (8 + 3 de una placa de cierre mas corta).
SEG_REEL_FOTO = 13.0
# Si el medio publico un video propio: hasta cuanto se usa, SIN audio (es audio de otro
# medio: musica, locucion; no se republica).
SEG_REEL_VIDEO = 15.0

# Las perillas del motor que policiales fija. Solo se ponen si no vienen del entorno.
PERILLAS = {
    # Igual que el .env del bot en produccion (unica perilla REEL_ que tiene cambiada).
    "REEL_FONDO": "0",
    # Peso: decision del editor para policiales del 25/09 (piezas livianas). El bot usa
    # CRF 26 / 3500k; con una foto quieta la diferencia no se ve en un celular.
    "REEL_CRF": "32",
    "REEL_MAXRATE": "1500k",
}

_motor = None


class ReelError(Exception):
    """El motor no pudo armar el reel."""


def motor():
    """El video.py del bot, importado desde estetica_bot/."""
    global _motor
    if _motor is None:
        for k, v in PERILLAS.items():
            os.environ.setdefault(k, v)
        if str(ESTETICA) not in sys.path:
            sys.path.insert(0, str(ESTETICA))
        import video as m                     # ← estetica_bot/video.py (el del bot)
        _motor = m
    return _motor


def origen() -> str:
    """De que commit del bot es el motor (queda anotado en cada pieza)."""
    try:
        for linea in (ESTETICA / "ORIGEN.txt").read_text(encoding="utf-8").splitlines():
            if linea.startswith("commit del bot:"):
                return linea.split(":", 1)[1].strip()
    except OSError:
        pass
    return "?"


def faltantes() -> list:
    """Lo que falta para armar reels con la estetica del bot."""
    necesarios = ["video.py", "story_image.py", "logo_reel.png", "placa_final.png",
                  "fonts/GoogleSans-Variable.ttf"]
    return [n for n in necesarios if not (ESTETICA / n).exists()]


def _textos(guion: dict) -> dict:
    # La bajada de policiales es el «resumen» del bot: va debajo de una foto apaisada.
    return {"volanta": (guion.get("volanta") or "").strip(),
            "titular": (guion.get("titular") or "").strip(),
            "resumen": (guion.get("bajada") or "").strip()}


def cuadro_de_video(clip: Path, salida: Path):
    """Un cuadro del video del medio, para saber que se puede usar. None si no."""
    try:
        return motor().frame_at(clip, 0.5, salida)
    except Exception:
        return None


def placa_fija(guion: dict, foto, salida: Path) -> Path:
    """Solo el cuadro compuesto, sin armar el video (la vista rapida de `--sin-video`).

    Es el mismo cuadro que va en el reel, salvo el isologo, que el motor pega recien al
    armar el video. Usa piezas internas del motor (`_mirar_foto`, `_placa_de_foto`): si un
    cambio del bot las renombra, tools/test_estetica.py lo avisa.
    """
    m = motor()
    from PIL import Image
    t = _textos(guion)
    with tempfile.TemporaryDirectory(prefix="placa_") as tmp:
        img, grafica = m._mirar_foto(Path(foto), Path(tmp), "fija")
        plan = m.plan_placa(t["volanta"], t["titular"], t["resumen"], img.width, img.height,
                            grafica=grafica, modo_texto="")
        fondo_png = m.fondo_placa_png(Path(tmp) / "fondo.png")
        fondo = (Image.open(fondo_png).convert("RGB") if fondo_png else
                 Image.new("RGB", (1080, 1920), m._rgb_de(m._color_fondo(""))))
        return m._placa_de_foto(img, plan, fondo, Path(salida))


def armar(guion: dict, salida: Path, foto=None, clip=None) -> dict:
    """El .mp4 del reel y su cuadro fijo (.jpg al lado, para la galeria).

    El motor deja archivos de trabajo al lado de su salida (fondos, mascaras, bases): se lo
    hace trabajar en una carpeta temporal y solo se trae el .mp4 terminado.
    """
    m = motor()
    salida = Path(salida)
    if not foto and not clip:
        raise ReelError("no hay ni foto ni video")
    with tempfile.TemporaryDirectory(prefix="reel_") as tmp:
        destino = Path(tmp) / salida.name
        try:
            if clip:
                m.to_vertical_reel(Path(clip), destino, audio=False, max_seconds=SEG_REEL_VIDEO,
                                   overlay=False, **_textos(guion))
            else:
                # La foto se copia a la carpeta de trabajo: el motor escribe al lado.
                propia = Path(tmp) / f"foto{Path(foto).suffix or '.jpg'}"
                shutil.copy2(foto, propia)
                m.foto_a_reel([propia], destino, seg=SEG_REEL_FOTO, overlay=False,
                              **_textos(guion))
        except Exception as e:
            raise ReelError(f"{type(e).__name__}: {e}") from e
        if not destino.exists() or destino.stat().st_size < 10240:
            raise ReelError("el motor no dejo un .mp4 valido")
        salida.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destino), str(salida))

    jpg = salida.with_suffix(".jpg")
    try:
        # Un segundo adentro: la pieza ya compuesta, con marca e isologo.
        m.frame_at(salida, 1.0, jpg)
    except Exception:
        pass
    return {
        "archivo": str(salida),
        "duracion": round(float(m.duration_seconds(salida)), 1),
        "peso_kb": round(salida.stat().st_size / 1024),
        "tramos": ["nota", "cierre"],
        "con_foto": not clip,
        "con_video": bool(clip),
        "placa": str(jpg) if jpg.exists() else None,
        "estetica": f"bot {origen()}",
    }
