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
from functools import lru_cache
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


LEMA = ("CAMPO", "MERCADOS", "CLIMA")


def _espaciado(d, texto: str, f, ancho: float) -> tuple:
    """Las letras de `texto` repartidas para ocupar `ancho` (como «RADIO DEL CENTRO» en la placa del diario)."""
    anchos = [d.textlength(c, font=f) for c in texto]
    paso = (ancho - sum(anchos)) / max(1, len(texto) - 1)
    return anchos, paso


def _icono(nombre: str, alto: int, color) -> Image.Image:
    im = Image.open(D.MARCA / nombre).convert("RGBA")
    im = im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)
    tinta = Image.new("RGBA", im.size, tuple(color) + (255,))
    tinta.putalpha(im.getchannel("A"))
    return tinta


# La placa final animada de los reels de datos (agro/movimiento.py, 20/11/2026): cuándo entra cada parte (segundos).
CIERRE_ISO, CIERRE_NOMBRE, CIERRE_RAYA, CIERRE_FRASE, CIERRE_USUARIO = 0.0, 0.3, 0.55, 0.65, 0.95
CIERRE_TECLA = 0.04          # entre letra y letra del usuario
CIERRE_ICONOS = CIERRE_USUARIO + len(D.USUARIO) * CIERRE_TECLA + 0.1
CIERRE_DURACION = 3.4


@lru_cache(maxsize=16)
def _partes(tema: str, frase: str, alto: int) -> tuple:
    """(fondo, [(nombre, sprite RGBA, (x, y))]): cada parte de la placa en su capa, para poder animarlas."""
    t = D.TEMAS[tema]
    partes = []
    cx = D.W / 2

    def capa():
        lienzo = Image.new("RGBA", (D.W, alto), (0, 0, 0, 0))
        return lienzo, ImageDraw.Draw(lienzo)

    def guardar(nombre, lienzo):
        caja = lienzo.getbbox()
        if caja:
            partes.append((nombre, lienzo.crop(caja), caja[:2]))

    def centrado(d, texto, f, yy, c):
        d.text((cx - d.textlength(texto, font=f) / 2, yy), texto, font=f, fill=c)

    # El lema, con puntos naranjas entre las palabras.
    lz, d = capa()
    f_l = D.fuente("bold", 36)
    trozos = [(w, d.textlength(w, font=f_l) + 4 * (len(w) - 1)) for w in LEMA]
    sep = 70
    x = cx - (sum(a for _, a in trozos) + sep * (len(trozos) - 1)) / 2
    y_lema = round(alto * 0.10)
    for i, (w, a) in enumerate(trozos):
        xx = x
        for c in w:
            d.text((xx, y_lema), c, font=f_l, fill=t["titular"])
            xx += d.textlength(c, font=f_l) + 4
        x += a
        if i < len(trozos) - 1:
            d.ellipse((x + sep / 2 - 8, y_lema + 14, x + sep / 2 + 8, y_lema + 30), fill=D.ACENTO)
            x += sep
    guardar("lema", lz)

    iso = D.isologo(round(alto * 0.22))
    y = round(alto * 0.205)
    partes.append(("iso", iso, (round(cx - iso.width / 2), y)))
    y += iso.height + round(alto * 0.045)

    # DIARIO Y RADIO (negra) y abajo A G R O en verde, espaciada al mismo ancho.
    lz, d = capa()
    f1 = D.fuente("negra", 100)
    ancho1 = d.textlength("DIARIO Y RADIO", font=f1)
    if ancho1 > D.W - 2 * D.X:
        f1 = D.fuente("negra", int(100 * (D.W - 2 * D.X) / ancho1))
        ancho1 = d.textlength("DIARIO Y RADIO", font=f1)
    centrado(d, "DIARIO Y RADIO", f1, y, t["titular"])
    y += round(f1.size * 1.12)
    f2 = D.fuente("bold", round(f1.size * 0.62))
    anchos, paso = _espaciado(d, "AGRO", f2, ancho1 * 0.46)
    xx = cx - ancho1 * 0.23
    for c, a in zip("AGRO", anchos):
        d.text((xx, y), c, font=f2, fill=t["verde"])
        xx += a + paso
    guardar("nombre", lz)
    y += round(f2.size * 1.5)
    lz, d = capa()
    d.rectangle((cx - 65, y, cx + 65, y + 7), fill=D.ACENTO)
    guardar("raya", lz)
    y += 45

    # La frase (o «Seguinos en redes»), el usuario grande y los íconos.
    lz, d = capa()
    f, r = D.ajustar(d, frase or "Seguinos en redes", "medium", 46, 32, D.W - 2 * D.X, 2)
    for linea in r:
        centrado(d, linea, f, y, t["texto"])
        y += round(f.size * 1.25)
    guardar("frase", lz)
    y += 14
    lz, d = capa()
    try:
        from PIL import ImageFont
        f_u = ImageFont.truetype(str(D.MARCA / "Anton-Regular.ttf"), 104)
        if d.textlength(D.USUARIO, font=f_u) > D.W - 2 * D.X:
            f_u = ImageFont.truetype(str(D.MARCA / "Anton-Regular.ttf"),
                                     int(104 * (D.W - 2 * D.X) / d.textlength(D.USUARIO, font=f_u)))
    except OSError:
        f_u = D.fuente("negra", 80)
    x_u = cx - d.textlength(D.USUARIO, font=f_u) / 2
    d.text((x_u, y), D.USUARIO, font=f_u, fill=t["titular"])
    # Hasta dónde llega cada letra (para tipearlo): x de corte, relativa al sprite.
    cortes = [d.textlength(D.USUARIO[:k + 1], font=f_u) for k in range(len(D.USUARIO))]
    caja = lz.getbbox()
    if caja:
        partes.append(("usuario", lz.crop(caja), caja[:2]))
        partes.append(("cortes", tuple(round(x_u + c - caja[0]) + 4 for c in cortes), (0, 0)))
    y += round(f_u.size * 1.75)
    try:
        iconos = [_icono(n, 66, t["titular"]) for n in ("icono_ig.png", "icono_fb.png")]
        gap = 70
        x = cx - (sum(i.width for i in iconos) + gap * (len(iconos) - 1)) / 2
        for k, ic in enumerate(iconos):
            partes.append((f"icono{k}", ic, (round(x), min(y, alto - 120))))
            x += ic.width + gap
    except OSError:
        pass
    return t["fondo"], tuple(partes)


def cierre(tema: str, frase: str = "", alto: int = D.H45, t: float = None) -> Image.Image:
    """La placa de cierre 4:5 de agro. 20/11/2026 (el editor: «actualizá el logo e isologo de la placa final»): la
    misma diagramación que la placa final del diario (estetica_bot/placa_final_4x5.png): arriba el lema, el
    isologo NUEVO (las C del diario con el brote de agro), DIARIO Y RADIO / A G R O, la rayita naranja, la frase
    (o «Seguinos en redes»), el usuario grande y los íconos de las redes donde está agro (Instagram y Facebook).

    `t` (segundos desde que empieza la placa): la versión ANIMADA de los reels de datos (agro/movimiento.py): el
    isologo rebota, el nombre sube, la raya crece, el usuario se tipea y los íconos hacen pop. Sin `t`, completa."""
    from agro import movimiento as MV
    fondo, partes = _partes(tema, frase or "", alto)
    lienzo = Image.new("RGBA", (D.W, alto), fondo + (255,))
    cortes = next((p[1] for p in partes if p[0] == "cortes"), ())
    for nombre, sp, (x, y) in partes:
        if nombre == "cortes":
            continue
        if t is None:
            lienzo.alpha_composite(sp, (x, y))
            continue
        centro = (x + sp.width / 2, y + sp.height / 2)
        if nombre == "lema":
            u = MV.ease_out(t / 0.4)
            MV.pop_sprite(lienzo, sp, (centro[0], centro[1] - 20 * (1 - u)), 1.0, u)
        elif nombre == "iso":
            MV.pop_sprite(lienzo, sp, centro, MV.ease_back((t - CIERRE_ISO) / 0.5) if t > CIERRE_ISO else 0)
        elif nombre in ("nombre", "frase"):
            t0 = CIERRE_NOMBRE if nombre == "nombre" else CIERRE_FRASE
            u = MV.ease_out((t - t0) / 0.35)
            MV.pop_sprite(lienzo, sp, (centro[0], centro[1] + 30 * (1 - u)), 1.0, u)
        elif nombre == "raya":
            u = MV.ease_out((t - CIERRE_RAYA) / 0.3)
            if u > 0:
                w = max(1, round(sp.width * u))
                lienzo.alpha_composite(sp.crop(((sp.width - w) // 2, 0, (sp.width + w) // 2, sp.height)),
                                       (x + (sp.width - w) // 2, y))
        elif nombre == "usuario":
            k = int((t - CIERRE_USUARIO) / CIERRE_TECLA) + 1 if t >= CIERRE_USUARIO else 0
            if k >= len(cortes):
                lienzo.alpha_composite(sp, (x, y))
            elif k > 0:
                lienzo.alpha_composite(sp.crop((0, 0, min(sp.width, cortes[k - 1]), sp.height)), (x, y))
        elif nombre.startswith("icono"):
            t0 = CIERRE_ICONOS + 0.12 * int(nombre[-1])
            MV.pop_sprite(lienzo, sp, centro, MV.ease_back((t - t0) / 0.35) if t > t0 else 0)
    return lienzo


def eventos_cierre(t0: float) -> list:
    """Los sonidos de la placa final animada, desde el segundo `t0` del reel."""
    from agro import movimiento as MV
    ev = [(t0 + CIERRE_ISO + 0.05, MV.pop(0.8), 0.7), (t0 + CIERRE_NOMBRE, MV.brisa(0.3), 0.35)]
    ev += [(t0 + CIERRE_USUARIO + k * CIERRE_TECLA, MV.tecla(k), 0.5) for k in range(len(D.USUARIO))]
    ev += [(t0 + CIERRE_ICONOS + 0.12 * k, MV.pop(1.3 + 0.2 * k), 0.5) for k in range(2)]
    ev.append((t0 + CIERRE_ICONOS + 0.35, MV.campanita(), 0.45))
    return ev


def _cuadros_video(clip, w: int, h: int, total: float):
    """Generador de cuadros RGB (PIL) del video de la fuente en w×h, sin sonido; si es más corto que el reel
    se repite. 20/11/2026 (el editor: «que no salgan mal cortados los videos que scrappees»): el video va
    ENTERO, achicado y centrado sobre sí mismo desenfocado; solo si su forma es casi la del recuadro (se
    perdería ≤ RECORTE_MAX por lado) se lo recorta para llenarlo. AGRO_VIDEO_ENTERO=0 vuelve a recortar siempre."""
    cmd = [_ffmpeg(), "-loglevel", "error", "-stream_loop", "-1", "-i", str(clip), "-t", f"{total:.2f}",
           "-vf", filtro_encuadre(clip, w, h), "-f", "rawvideo", "-pix_fmt", "rgb24", "-an", "-"]
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


RECORTE_MAX = 0.06       # hasta 6 % del ancho (o del alto) por lado se puede recortar para llenar


def _tamano(clip) -> tuple:
    """(ancho, alto, recorte) del contenido del video: sin las barras negras que traiga pegadas (recorte =
    «crop=…,» para ffmpeg, o ""). (0, 0, "") si no se puede medir."""
    try:
        from reels import reel_bot as R
        V = R.motor()
        r = V.detectar_recorte(Path(clip))
        if r:
            return r[0], r[1], f"crop={r[0]}:{r[1]}:{r[2]}:{r[3]},"
        w, h = V._dimensiones(Path(clip))
        return w, h, ""
    except Exception:                                  # noqa: BLE001
        return (0, 0, "")


def filtro_encuadre(clip, w: int, h: int, tamano=None) -> str:
    """El filtro de ffmpeg que pone el video en w×h: entero sobre sí mismo desenfocado, o recortado si casi
    no pierde nada."""
    import os
    cubrir = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    if (os.environ.get("AGRO_VIDEO_ENTERO") or "1").strip() == "0":
        return f"{cubrir},fps={FPS}"
    vw, vh, sin_barras = tamano or _tamano(clip)
    if not vw or not vh:
        return f"{cubrir},fps={FPS}"
    ar_v, ar_r = vw / vh, w / h
    perdida = 1 - min(ar_v, ar_r) / max(ar_v, ar_r)            # lo que se va (sumando los dos lados)
    if perdida <= 2 * RECORTE_MAX:
        return f"{sin_barras}{cubrir},fps={FPS}"
    return (f"{sin_barras}split[a][b];[a]{cubrir},boxblur=24:3,colorchannelmixer=rr=0.55:gg=0.55:bb=0.55[fondo];"
            f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[frente];"
            f"[fondo][frente]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}")


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
    leyenda = D.texto_leyenda(origen if origen == "ilustrativo" else ("video" if clip else origen), credito)
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
