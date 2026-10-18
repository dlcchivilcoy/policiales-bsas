# -*- coding: utf-8 -*-
"""Arma el reel con el MOTOR DEL BOT DEL DIARIO: la misma estetica que sus reels.

Pedido del editor (26/09/2026): «actualizar la estetica de los reels que tiene el bot para
los reels de policiales». El motor vive en estetica_bot/ copiado TAL CUAL del bot
(tools/traer_estetica_bot.py); este modulo es lo unico propio de policiales: que texto
va, cuanto dura y cuanto pesa.

ESTILO (desde el 03/10/2026, pedido del editor: «copiá los últimos lineamientos estéticos
para reels del bot»): el de los reels de WhatsApp del bot, `estilo="corresponsal"` del motor
(«prompt detallado para editar reels», 03/10):
- vertical o cuadrada: a sangre en 9:16, la volanta en una caja naranja #B35B18 en
  mayúsculas y el titular en una caja grafito abajo; si tapan una cara, suben. Sin bajada.
- horizontal: ENTERA, a todo el ancho, en un reel 4:5 (1080x1350). Desde el 12/10/2026 (pedido
  del editor, con dos reels de infobae de ejemplo) la imagen arranca en el borde de ARRIBA y
  debajo va una línea naranja y un BLOQUE con el isologo y el logo, la volanta naranja y el
  titular: blanco con titular grafito o grafito con titular blanco, ALTERNADOS de un posteo al
  otro (`proximo_tema` / `anotar_tema`, en estado/tema_reels.json).
- desde el 17/10/2026 las FOTOS verticales o 9:16 van igual que las horizontales: el bloque abajo
  con el texto, el logo y el isologo, y la foto ENTERA, achicada y centrada arriba (sobre sí misma
  desenfocada), en 9:16. Desde la misma noche, también los VIDEOS verticales. Marca e isologo de
  los cuadros a sangre, más abajo (Y 250) y más grandes: los tapaban los marcos de las apps.
- afiche: entero, solo la marca.
Marca arriba a la izquierda, isologo arriba a la derecha y la placa de cierre recortada al
cuadro. REEL_ESTILO_POLICIALES="" vuelve al estilo placa de antes (texto arriba, fondo carbón).

Facebook recibe el 4:5 en una copia 9:16 con bandas grafito (ver a_9x16_si_hace_falta).
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESTETICA = RAIZ / "estetica_bot"
# El tema del último reel 4:5 (bloque blanco o grafito): el próximo va con el otro. Lo comparten
# policiales, nacionales y el Archivo Literario (el motor es uno).
TEMAS = RAIZ / "estado" / "tema_reels.json"

# Cuanto dura el reel de una FOTO: 8 s de nota + los 5 s de la placa de cierre del bot.
# El bot usa 30 s para sus foto-notas; un policial breve con una foto quieta 25 s se
# abandona antes de terminar. Antes de adoptar el motor del bot los de policiales duraban
# 10,4 s (8 + 3 de una placa de cierre mas corta).
SEG_REEL_FOTO = 13.0
# Si el medio publico un video propio: va ENTERO y CON SU SONIDO (pedido del editor, 18/10/2026: «no
# saques el sonido ni cortes los videos de los reels si duran más de 30 segundos»). Antes: 15 s mudos.
# El único tope es el de Instagram para un reel por la API (15 min); REEL_VIDEO_MAX_SEG lo cambia.
SEG_REEL_VIDEO = float(os.environ.get("REEL_VIDEO_MAX_SEG") or 900)

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


def estilo() -> str:
    """El estilo del motor: «corresponsal» (el último del bot) salvo que el entorno diga otro."""
    return (os.environ.get("REEL_ESTILO_POLICIALES", "corresponsal") or "").strip()


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


def proximo_tema(archivo: Path = None) -> str:
    """El tema del bloque para el próximo reel 4:5: el otro del último anotado."""
    archivo = archivo or TEMAS
    try:
        ultimo = json.loads(archivo.read_text(encoding="utf-8")).get("ultimo", "")
    except (OSError, ValueError, AttributeError):
        ultimo = ""
    return motor().tema_siguiente(ultimo)


def anotar_tema(tema: str, archivo: Path = None) -> None:
    """Anota el tema del reel 4:5 que acaba de salir (solo si salió 4:5: `armar` lo devuelve)."""
    if not tema:
        return
    archivo = archivo or TEMAS
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps({"ultimo": tema, "cuando": time.time()}, ensure_ascii=False,
                                  indent=2), encoding="utf-8")


def origen() -> str:
    """De que commit del bot es el motor (queda anotado en cada pieza)."""
    try:
        for linea in (ESTETICA / "ORIGEN.txt").read_text(encoding="utf-8").splitlines():
            if linea.startswith("commit del bot:"):
                return linea.split(":", 1)[1].strip()
    except OSError:
        pass
    return "?"


def _parecido_a_placa(mp4: Path, segundo: float, placa: Path, tmp: Path) -> float:
    """Diferencia media (0-255) entre el cuadro del segundo `segundo` y la placa de cierre.
    Chica = es la placa. 255 si no se pudo leer el cuadro."""
    import subprocess
    from PIL import Image, ImageChops, ImageStat
    m = motor()
    cuadro = tmp / f"cuadro_{segundo:.2f}.jpg"
    subprocess.run([m._ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{segundo:.3f}", "-i", str(mp4),
                    "-frames:v", "1", "-q:v", "3", str(cuadro)], capture_output=True, timeout=60)
    if not cuadro.exists():
        return 255.0
    a = Image.open(cuadro).convert("L")
    # Desde el 13/10 el 4:5 tiene su propia placa (placa_final_4x5.png) en vez de la 9:16 recortada.
    placa_4x5 = Path(placa).with_name(Path(placa).stem + "_4x5.png")
    if a.height < a.width * 1.7 and placa_4x5.is_file():
        b = Image.open(placa_4x5).convert("L").resize(a.size)
    else:
        b = _placa_al_cuadro(Image.open(placa).convert("L"), a.size)
    tam = (54, max(1, round(54 * a.height / a.width)))
    return ImageStat.Stat(ImageChops.difference(a.resize(tam), b.resize(tam))).mean[0]


def _placa_al_cuadro(placa, tam: tuple):
    """La placa (9:16) recortada como la recorta el motor en un reel más bajo (el 4:5 de lo
    horizontal, desde el 03/10): de alto el del cuadro, a 0,42 de lo que sobra arriba."""
    ancho, alto = tam
    alto_placa = round(placa.width * alto / ancho)
    if alto_placa >= placa.height - 2:
        return placa
    y = round((placa.height - alto_placa) * 0.42)
    return placa.crop((0, y, placa.width, y + alto_placa))


def dimensiones(mp4: Path, cuadro: Path = None) -> tuple:
    """(ancho, alto) del reel, leídos de un cuadro. (0, 0) si no se pudo."""
    from PIL import Image
    try:
        if cuadro and Path(cuadro).is_file():
            with Image.open(cuadro) as im:
                return im.size
        with tempfile.TemporaryDirectory(prefix="dim_") as t:
            c = motor().frame_at(Path(mp4), 0.5, Path(t) / "c.jpg")
            with Image.open(c) as im:
                return im.size
    except Exception:
        return 0, 0


def a_9x16_si_hace_falta(mp4: Path, destino: Path, alto: int = 0):
    """Copia 9:16 con bandas grafito de un reel que no lo es (el 4:5), o None si ya es 9:16 o
    no se pudo. Para Facebook: sus reels por API son 9:16 y que tome un 4:5 no está probado
    (en el bot quedó «sin verificar real»); un rechazo dejaría sin Facebook a casi todas las
    notas, que traen fotos horizontales. Instagram y YouTube reciben el 4:5."""
    alto = alto or dimensiones(mp4)[1]
    if not alto or alto >= 1900:
        return None
    try:
        return motor().a_9x16(Path(mp4), Path(destino))
    except Exception:
        return None


# Por debajo de esto, el cuadro ES la placa (la placa contra sí misma ya codificada da
# muy poco; contra una nota, mucho más: ver tools/test_sin_placa.py).
UMBRAL_PLACA = 20.0


def sin_placa_final(mp4, destino) -> Path | None:
    """Copia del reel SIN la placa de cierre «Seguinos en redes», para YouTube.

    Pedido del editor (27/09/2026): YouTube elegía la placa como miniatura del Short y la
    grilla del canal quedaba toda igual. Sin la placa, cualquier cuadro que elija es la nota.

    La placa es el último tramo, de REEL_PLACA_SEG segundos (5), pegado aparte y con fundido
    de entrada: se corta justo antes. Antes de cortar se COMPRUEBA que el reel termine en la
    placa, porque el motor a veces la saca (escalón «sin la placa de cierre») y cortar a
    ciegas le comería 5 segundos a la nota. Devuelve la ruta, o None (subir el original)."""
    import subprocess
    m = motor()
    mp4, destino = Path(mp4), Path(destino)
    placa = m._asset("REEL_PLACA_FINAL", m.PLACA_FINAL)
    seg_placa = m._num("REEL_PLACA_SEG", m.PLACA_SEG)
    dur = m.duration_seconds(mp4)
    if not placa or seg_placa <= 0 or dur - seg_placa < 3:
        return None
    corte = dur - seg_placa
    with tempfile.TemporaryDirectory(prefix="placa_") as t:
        t = Path(t)
        if _parecido_a_placa(mp4, dur - 1.0, placa, t) >= UMBRAL_PLACA:
            return None                         # no termina en la placa: no se toca
        if _parecido_a_placa(mp4, max(0.0, corte - 0.5), placa, t) < UMBRAL_PLACA:
            return None                         # la placa arranca antes de lo esperado
    # Recodificado y no `-c copy`: copiando, ffmpeg se pasaba ~0,1 s y se colaban cuadros
    # del fundido a negro de la placa. Y 0,2 s antes del corte por la misma razón.
    corte -= 0.2
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([m._ffmpeg(), "-y", "-loglevel", "error", "-i", str(mp4), "-t", f"{corte:.3f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", m._cfg("REEL_CRF", "26"),
                        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", str(destino)],
                       capture_output=True, timeout=180)
    if r.returncode != 0 or not destino.exists() or abs(m.duration_seconds(destino) - corte) > 0.3:
        return None
    return destino


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


def cuadro_de_video(clip: Path, salida: Path, segundo: float = 0.5):
    """Un cuadro del video del medio, para saber que se puede usar. None si no."""
    try:
        cuadro = motor().frame_at(clip, segundo, salida)
        return cuadro if cuadro and Path(cuadro).is_file() else None
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
    if estilo():
        # El estilo nuevo compone cada cuadro con piezas propias (cajas, 4:5): la vista fija
        # sale de un reel corto de verdad, un segundo adentro, igual que el .jpg de armar().
        with tempfile.TemporaryDirectory(prefix="placa_") as tmp:
            propia = Path(tmp) / f"foto{Path(foto).suffix or '.jpg'}"
            shutil.copy2(foto, propia)
            corto = Path(tmp) / "vista.mp4"
            m.foto_a_reel([propia], corto, seg=7, overlay=False, estilo=estilo(), **t)
            return m.frame_at(corto, 1.0, Path(salida))
    with tempfile.TemporaryDirectory(prefix="placa_") as tmp:
        img, grafica = m._mirar_foto(Path(foto), Path(tmp), "fija")
        plan = m.plan_placa(t["volanta"], t["titular"], t["resumen"], img.width, img.height,
                            grafica=grafica, modo_texto="")
        fondo_png = m.fondo_placa_png(Path(tmp) / "fondo.png")
        fondo = (Image.open(fondo_png).convert("RGB") if fondo_png else
                 Image.new("RGB", (1080, 1920), m._rgb_de(m._color_fondo(""))))
        return m._placa_de_foto(img, plan, fondo, Path(salida))


def armar(guion: dict, salida: Path, foto=None, clip=None, tema: str = "", foto_tapa=None) -> dict:
    """El .mp4 del reel y su cuadro fijo (.jpg al lado, para la galeria). `tema`: el bloque del
    4:5 (blanco/grafito, ver `proximo_tema`); el dict devuelto dice en «tema» el que se usó, o ""
    si el reel salió 9:16. `foto_tapa`: la foto de la nota para la PORTADA cuando el reel es del video
    (si no, la portada sale de un cuadro del video).

    El motor deja archivos de trabajo al lado de su salida (fondos, mascaras, bases): se lo
    hace trabajar en una carpeta temporal y solo se trae el .mp4 terminado.
    """
    m = motor()
    salida = Path(salida)
    if not foto and not clip:
        raise ReelError("no hay ni foto ni video")
    m.tema_usado(reset=True)
    with tempfile.TemporaryDirectory(prefix="reel_") as tmp:
        destino = Path(tmp) / salida.name
        try:
            if clip:
                m.to_vertical_reel(Path(clip), destino, audio=True, max_seconds=SEG_REEL_VIDEO,
                                   overlay=False, estilo=estilo(), tema=tema, **_textos(guion))
            else:
                # La foto se copia a la carpeta de trabajo: el motor escribe al lado.
                propia = Path(tmp) / f"foto{Path(foto).suffix or '.jpg'}"
                shutil.copy2(foto, propia)
                m.foto_a_reel([propia], destino, seg=SEG_REEL_FOTO, overlay=False,
                              estilo=estilo(), tema=tema, **_textos(guion))
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
    ancho, alto = dimensiones(salida, jpg)
    return {
        "archivo": str(salida),
        "duracion": round(float(m.duration_seconds(salida)), 1),
        "peso_kb": round(salida.stat().st_size / 1024),
        "ancho": ancho,
        "alto": alto,
        "tramos": ["nota", "cierre"],
        "con_foto": not clip,
        "con_video": bool(clip),
        "placa": str(jpg) if jpg.exists() else None,
        "estetica": f"bot {origen()}",
        "tema": m.tema_usado(),
        "portada": portada(guion, salida, foto=foto or foto_tapa, clip=clip, tema=m.tema_usado() or tema),
    }


def portada(guion: dict, salida: Path, foto=None, clip=None, tema: str = "") -> str | None:
    """La MINIATURA del reel (reels/portada.py, 18/10/2026): la foto de la nota o, si el reel es del
    video del medio, un cuadro de ese video; con la volanta y el texto SEO. Queda al lado del .mp4
    («<nombre>_portada.jpg»). Nunca frena el reel: si algo falla, Instagram elige la suya."""
    from reels import portada as POR
    salida = Path(salida)
    destino = salida.with_name(salida.stem + "_portada.jpg")
    try:
        imagen = foto                              # la foto de la nota, si la hay, es la mejor tapa
        if clip and not imagen:
            try:
                seg = min(3.0, max(0.5, float(motor().duration_seconds(Path(clip))) * 0.3))
            except Exception:                      # noqa: BLE001
                seg = 1.0
            imagen = cuadro_de_video(Path(clip), salida.with_name(salida.stem + "_cuadro.jpg"), seg)
        if not imagen:
            return None
        return str(POR.armar(imagen, guion.get("volanta") or "", POR.texto(guion), destino,
                             "blanco" if tema == "blanco" else "grafito"))
    except Exception as e:                         # noqa: BLE001
        print(f"  (portada del reel: no se pudo armar: {type(e).__name__}: {e})")
        return None


def armar_declaracion(decl: dict, salida: Path, foto=None, clip=None, respaldo: str = "",
                      tema: str = "") -> dict:
    """El reel de DECLARACIÓN (estetica_bot/declaracion.py, 10/10/2026): el audio de la nota con su
    foto o su video (sin el sonido del video), el nombre, el cargo, las frases y el espectro.
    `decl` sale de reels/declaracion.preparar. Mismo dict que `armar`, con «declaracion»."""
    m = motor()
    if str(ESTETICA) not in sys.path:
        sys.path.insert(0, str(ESTETICA))
    import declaracion as D                     # ← estetica_bot/declaracion.py (el del bot)
    salida = Path(salida)
    if not foto and not clip:
        raise ReelError("no hay ni foto ni video")
    with tempfile.TemporaryDirectory(prefix="decl_") as tmp:
        visual = Path(clip or foto)
        propia = Path(tmp) / f"visual{visual.suffix or '.jpg'}"
        shutil.copy2(visual, propia)
        destino = Path(tmp) / salida.name
        try:
            info = D.reel(decl["audio"], propia, destino, nombre=decl.get("nombre", ""),
                          cargo=decl.get("cargo", ""), frases=decl.get("frases"), tramo=decl.get("tramo"),
                          es_foto=not clip, respaldo=respaldo, work_dir=Path(tmp), tema=tema)
        except Exception as e:
            raise ReelError(f"{type(e).__name__}: {e}") from e
        if not destino.exists() or destino.stat().st_size < 10240:
            raise ReelError("el motor no dejó un .mp4 válido")
        salida.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destino), str(salida))
    jpg = salida.with_suffix(".jpg")
    try:
        m.frame_at(salida, 1.0, jpg)
    except Exception:
        pass
    ancho, alto = dimensiones(salida, jpg)
    return {
        "archivo": str(salida),
        "duracion": round(float(m.duration_seconds(salida)), 1),
        "peso_kb": round(salida.stat().st_size / 1024),
        "ancho": ancho,
        "alto": alto,
        "tramos": ["declaracion", "cierre"],
        "con_foto": not clip,
        "con_video": bool(clip),
        "con_audio": True,
        "declaracion": {"nombre": decl.get("nombre"), "cargo": decl.get("cargo"),
                        "frases": info.get("frases"), "tramo": info.get("tramo")},
        "placa": str(jpg) if jpg.exists() else None,
        "estetica": f"bot {origen()}",
        "tema": info.get("tema", ""),
    }
