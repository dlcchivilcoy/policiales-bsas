# -*- coding: utf-8 -*-
"""El reel agro en 4:5 (1080x1350) con la estética de los reels 4:5 de policiales (agro/diseno.py).

Pedido del editor (17/10/2026): reels 4:5, estilo policiales, con la imagen o el video de la fuente.
Arriba la imagen a todo el ancho (con un acercamiento lento) o el video de la fuente (sin su sonido);
abajo la línea naranja y el bloque blanco o grafito —se alternan de un posteo al otro— con la marca.
En el bloque el texto cambia por tramos, con un fundido corto:

    0-5 s     LA PORTADA: volanta + el texto SEO de la miniatura en letra grande, ya visible en el
              primer cuadro (sin fundido: es el que toman Facebook y YouTube si no hay portada)
    5-9,5 s   QUÉ PASÓ
    9,5-14,5  LOS DATOS (aparecen de a uno)
    14,5-19   POR QUÉ IMPORTA
    19-22     CIERRE: el logo, DIARIO Y RADIO AGRO, @diarioyradioagro

Sin voz (la locución queda para más adelante). CON VIDEO de la fuente (31/10/2026, pedido del editor: «poner
videos en reels, de máximo 1 minuto y medio»): el reel dura lo que el video —entero y CON su sonido—; el
último texto (POR QUÉ IMPORTA) queda hasta que termina y después va el cierre. Los cuadros se dibujan con PIL y van por un caño a
ffmpeg (el de imageio-ffmpeg, el mismo que usa policiales).
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from agro import diseno as D

FPS = 24
TRAMOS = (("titular", 5.0), ("que_paso", 4.5), ("datos", 5.0), ("por_que_importa", 4.5), ("cierre", 3.0))
FUNDIDO = 0.25          # segundos de entrada de cada texto
ZOOM = 0.08             # cuánto se acerca la imagen en todo el reel
ROTULOS = {"que_paso": "QUÉ PASÓ", "datos": "LOS DATOS", "por_que_importa": "POR QUÉ IMPORTA"}
PROPORCION = 4 / 3      # la imagen arriba: 1080x810 (lo que da FLUX/klein y las fotos apaisadas)


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _capa_tramo(plan: dict, guion: dict, tramo: str) -> list:
    """[(desde_seg, capa RGBA)]: lo que se dibuja en el bloque durante el tramo. Los datos son
    varias capas que se suman de a una."""
    t = D.TEMAS[plan["tema"]]
    y0, y1 = plan["zona"]
    if tramo == "titular":
        capa = Image.new("RGBA", (D.W, plan["alto"]), (0, 0, 0, 0))
        D.texto_titular(capa, plan)
        return [(0.0, capa)]
    rot = ROTULOS[tramo]
    f_rot = D.fuente("bold", D.VOLANTA[0])
    alto_util = y1 - y0 - f_rot.size - D.GAP_VOLANTA
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    if tramo == "datos":
        datos = (guion.get("reel") or {}).get("datos") or guion.get("datos_clave", [])[:3]
        datos = [d for d in datos if d][:3] or [guion.get("bajada", "")]
        # Una sola letra para todos los datos: la más grande en la que entran los tres juntos.
        for tam in range(50, 29, -2):
            f = D.fuente("medium", tam)
            bloques = [D.renglones(medir, d, f, D.ANCHO - 44) for d in datos]
            alto = sum(D.alto_texto(f, len(b), 1.18) for b in bloques) + 22 * (len(bloques) - 1)
            if alto <= alto_util and all(len(b) <= 3 for b in bloques):
                break
        capas, y = [], y0 + f_rot.size + D.GAP_VOLANTA
        cada = 5.0 / max(1, len(bloques))
        for i, b in enumerate(bloques):
            capa = Image.new("RGBA", (D.W, plan["alto"]), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            if i == 0:
                d.text((D.X, y0), rot, font=f_rot, fill=t["volanta"])
            d.ellipse((D.X, y + f.size * 0.32, D.X + 18, y + f.size * 0.32 + 18), fill=t["verde"])
            y = D.escribir(d, D.X + 44, y, b, f, t["titular"], 1.18) + 22
            capas.append((i * cada * 0.7, capa))
        return capas
    texto = (guion.get("reel") or {}).get(tramo) or (guion.get("bajada", "") if tramo == "que_paso" else "")
    capa = Image.new("RGBA", (D.W, plan["alto"]), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.text((D.X, y0), rot, font=f_rot, fill=t["volanta"])
    f, r = D.ajustar(d, texto, "medium", 58, 34, D.ANCHO, 5, alto_max=alto_util, salto=1.18)
    D.escribir(d, D.X, y0 + f_rot.size + D.GAP_VOLANTA, r, f, t["titular"], 1.18)
    return [(0.0, capa)]


def cierre(tema: str, frase: str = "", alto: int = D.H45) -> Image.Image:
    """La placa de cierre 4:5 de agro: logo grande, el nombre, el usuario y una frase."""
    t = D.TEMAS[tema]
    lienzo = Image.new("RGBA", (D.W, alto), t["fondo"] + (255,))
    iso = D.isologo(300)
    y = round(alto * 0.20)
    lienzo.alpha_composite(iso, ((D.W - iso.width) // 2, y))
    d = ImageDraw.Draw(lienzo)

    def centrado(texto, f, yy, c):
        d.text(((D.W - d.textlength(texto, font=f)) / 2, yy), texto, font=f, fill=c)
    y += iso.height + 50
    centrado("DIARIO Y RADIO", D.fuente("bold", 60), y, t["titular"])
    centrado("AGRO", D.fuente("bold", 60), y + 70, t["verde"])
    d.rectangle(((D.W - 120) // 2, y + 168, (D.W + 120) // 2, y + 176), fill=D.NARANJA)
    centrado(D.USUARIO, D.fuente("bold", 44), y + 205, t["volanta"])
    if frase:
        f, r = D.ajustar(d, frase, "regular", 38, 28, D.W - 2 * D.X, 2)
        for i, linea in enumerate(r):
            centrado(linea, f, y + 290 + i * round(f.size * 1.3), t["texto"])
    return lienzo


def _cuadros_video(clip, w: int, h: int, total: float):
    """Generador de cuadros RGB (PIL) del video de la fuente, cubriendo w×h, sin sonido; si es más
    corto que el reel se repite."""
    cmd = [_ffmpeg(), "-loglevel", "error", "-stream_loop", "-1", "-i", str(clip), "-t", f"{total:.2f}",
           "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-an", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    tam = w * h * 3
    ultimo = None
    try:
        while True:
            crudo = proc.stdout.read(tam)
            if len(crudo) < tam:
                break
            ultimo = Image.frombytes("RGB", (w, h), crudo)
            yield ultimo
    finally:
        proc.kill()
    while ultimo is not None:                  # por si ffmpeg cortó antes: el último cuadro quieto
        yield ultimo


def _medir(clip) -> tuple:
    """(duración en segundos, ¿tiene sonido?) del video de la fuente."""
    try:
        from reels import reel_bot as R
        m = R.motor()
        return float(m.duration_seconds(clip) or 0), bool(m.has_audio(clip))
    except Exception:                                  # noqa: BLE001 — sin medirlo, va como antes
        return 0.0, False


def tramos_para(dur_video: float = 0) -> tuple:
    """Los tramos del reel. Con un video más largo que los textos, el último texto se estira hasta que el
    video termina (el video va entero)."""
    textos = sum(d for n, d in TRAMOS if n != "cierre")
    if dur_video <= textos:
        return TRAMOS
    extra = dur_video - textos
    return tuple((n, d + extra) if n == "por_que_importa" else (n, d) for n, d in TRAMOS)


def armar(guion: dict, imagen, salida: Path, origen: str = "ia", credito: str = "", clip=None,
          tema: str = "blanco") -> dict:
    """El .mp4 4:5 y un .jpg del primer tramo al lado (la portada). `origen`: el de la imagen
    («fuente», «recreada», «ia», «video») para la leyenda. Lanza si ffmpeg falla."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    dur_video, con_sonido = _medir(clip) if clip else (0.0, False)
    tramos = tramos_para(dur_video)
    total = sum(s for _, s in tramos)
    cuadros = round(total * FPS)
    plan = D.plan_bloque(guion.get("volanta"), D.texto_portada(guion), tema, round(D.W / PROPORCION),
                         tope=D.PORTADA)
    hm = plan["alto_imagen"]
    base = D.base_bloque(plan)
    leyenda = D.texto_leyenda("video" if clip else origen, credito)
    capas = {nombre: _capa_tramo(plan, guion, nombre) for nombre, _ in tramos if nombre != "cierre"}
    placa = cierre(tema, (guion.get("reel") or {}).get("cierre", "")).convert("RGB")
    foto = Image.open(imagen).convert("RGB") if (imagen and not clip) else None
    video = _cuadros_video(clip, D.W, hm, total) if clip else None
    # El sonido: el del video de la fuente (y silencio en el cierre) o, sin video, silencio.
    sonido = (["-i", str(clip), "-map", "0:v", "-map", "1:a:0", "-af", "apad", "-t", f"{total:.2f}"]
              if con_sonido else
              ["-f", "lavfi", "-t", str(total), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
               "-shortest"])
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{D.W}x{D.H45}", "-r", str(FPS), "-i", "-", *sonido,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "24",
           "-c:a", "aac", "-b:a", "96k" if con_sonido else "64k", "-movflags", "+faststart", str(salida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    vista = ultimo_rgb = None
    seg_imagen = total - tramos[-1][1]
    try:
        for k in range(cuadros):
            seg = k / FPS
            acum, tramo, t = 0.0, tramos[-1][0], 0.0
            for nombre, dur in tramos:
                if seg < acum + dur:
                    tramo, t = nombre, seg - acum
                    break
                acum += dur
            if video is not None:
                arriba = next(video)
            if tramo == "cierre":
                a = min(1.0, t / FUNDIDO)
                cuadro = placa if (a >= 1 or ultimo_rgb is None) else Image.blend(ultimo_rgb, placa, a)
            else:
                lienzo = base.copy()
                if video is not None:
                    lienzo.paste(arriba, (0, 0))
                elif foto is not None:
                    avance = seg / seg_imagen
                    lienzo.paste(D.cubrir(foto, D.W, hm, zoom=1 + ZOOM * avance, dx=0.3 * avance - 0.15,
                                          rapido=True), (0, 0))
                D.leyenda(lienzo, leyenda, hm)
                for desde, capa in capas[tramo]:
                    ti = t - desde
                    if ti < 0:
                        continue
                    a = 1.0 if (tramo == "titular" and desde == 0) else min(1.0, ti / FUNDIDO)
                    if a < 1:
                        capa = capa.copy()
                        capa.putalpha(capa.getchannel("A").point(lambda v, a=a: round(v * a)))
                    lienzo.alpha_composite(capa)
                cuadro = lienzo.convert("RGB")
                ultimo_rgb = cuadro
            if vista is None and tramo == "titular":
                vista = cuadro.copy()
            proc.stdin.write(cuadro.tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not salida.exists():
            raise RuntimeError(f"ffmpeg: {err[-300:]}")
    finally:
        if proc.poll() is None:
            proc.kill()
    jpg = salida.with_suffix(".jpg")
    if vista is not None:
        vista.save(jpg, "JPEG", quality=90)
    return {"archivo": str(salida), "duracion": total, "peso_kb": round(salida.stat().st_size / 1024),
            "ancho": D.W, "alto": D.H45, "vista": str(jpg) if jpg.exists() else None, "tema": tema,
            "con_video": bool(clip), "con_sonido": con_sonido}
