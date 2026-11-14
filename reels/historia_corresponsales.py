# -*- coding: utf-8 -*-
"""HISTORIA DIARIA DE LAS 10:00 PARA EL PROGRAMA DE CORRESPONSALES (15/11/2026, pedido del usuario).

Todos los días a las 10:00, en Instagram y Facebook de @diarioyradio, una historia 9:16 que invita a mandar
fotos, videos o audios al bot de WhatsApp de corresponsales (2346-533450), para generar interacción:

- Una PREGUNTA distinta cada día («¿Viste algo raro en la calle?», «¿Sufriste algún robo?», «¿Presenciaste un
  accidente?»…, PREGUNTAS), que aparece palabra por palabra.
- De fondo, una IMAGEN GENERADA CON IA en 9:16 que ilustra la pregunta (Cloudflare Workers AI: Lucid Origin y,
  si falla, Phoenix; Gemini mira que no tenga letras). Pedido del usuario: la placa NO dice «imagen generada
  con IA». Si no sale ninguna imagen, va solo el fondo naranja.
- La estética de la historia de los entrevistados de la radio (social_publisher/historia_entrevistados.py):
  isologo y logo en blanco arriba, píldoras blancas con letras naranjas, «pop» al aparecer, texto tipeado como
  máquina de escribir y una flecha sutil hacia la caja de «Enviar mensaje».
- La IMAGEN COMPLETA, sin velo naranja (pedidos del 15/11/2026): TODO el texto arriba, debajo del logo —la
  etiqueta y la pregunta en blanco, la tarjeta, el número y el premio— y la imagen abajo, sin que nada tape el
  sujeto. Gemini ubica el sujeto en la imagen generada y la imagen se acomoda (se baja, se achica o se corre)
  para que quede entero debajo del texto; lo que sobra arriba se rellena con la misma imagen desenfocada.
- Los sonidos se generan acá.

Corre con `python -m reels.historia_corresponsales [--publicar]` (nacionales.yml, modo «corresponsales», que
dispara cron-job.org a las 10:00). HIST_CORRESPONSALES=0 la apaga. Los sábados y domingos el mismo video sale
además como REEL en Instagram y Facebook (HIST_CORRESPONSALES_REEL, ver `dias_reel`).
"""
from __future__ import annotations

import argparse
import base64
import io
import math
import os
import subprocess
import tempfile
import wave
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AR = timezone(timedelta(hours=-3))
W, H, FPS, SR = 1080, 1920, 30, 44100
NARANJA = (253, 133, 17)
NARANJA_HONDO = (214, 80, 4)
GRAFITO = (28, 29, 34)
BLANCO = (255, 255, 255)
NUMERO = "2346-533450"
ETIQUETA = "PROGRAMA DE CORRESPONSALES"
RENGLONES_CTA = ("Mandanos tu video, foto, audio y contanos", "tu noticia por WhatsApp al número")
TEXTO_CTA = " ".join(RENGLONES_CTA)
PREMIO = "Tu noticia puede tener premio"
RESPONDE = "o respondé esta historia"
CPS = 17
DUR_POP = 0.38
Y_LOGO = 160

# (pregunta, escena en inglés para la imagen). Una por día, en orden; da la vuelta.
PREGUNTAS = (
    ("¿Viste algo raro en la calle?",
     "a neighbor on a quiet small-town Argentine street at dusk holding up a smartphone to record something, warm streetlights"),
    ("¿Alguna novedad en tu barrio?",
     "two neighbors talking on the sidewalk in front of low houses in a small Argentine town, morning light, trees"),
    ("¿Tenés una noticia para contarnos?",
     "close-up of hands holding a smartphone typing a message, cozy cafe table by a window, morning light"),
    ("¿Tenés algún reclamo?",
     "a residential street in a small Argentine town with big potholes full of rainwater, cloudy day"),
    ("¿Sufriste algún robo?",
     "a worried woman looking at a forced open front door of a modest house at dusk, dramatic light"),
    ("¿Presenciaste un accidente?",
     "two cars after a minor collision on a small-town avenue, people standing around, daylight, realistic"),
    ("¿Hay un pozo, una luz rota o basura en tu cuadra?",
     "a dark residential street corner at night with a broken streetlight and garbage bags on the curb"),
    ("¿Pasó algo en tu escuela o en tu club?",
     "children playing football on a neighborhood club field in a small town, afternoon golden light"),
    ("¿Viste un incendio o un operativo?",
     "a column of grey smoke rising over rooftops of a small town at dusk, people watching from a distance"),
    ("¿Hay algo en tu barrio que tengamos que contar?",
     "a small-town neighborhood fair at night with string lights, food stalls and families walking"),
    ("¿Se cortó la luz o el agua en tu zona?",
     "a row of houses at night in total darkness, candlelight glowing in a window, small town"),
    ("¿Viste un animal suelto o perdido?",
     "a friendly lost dog sitting alone on a sidewalk of a small-town street, soft morning light"),
    ("¿Te pasó algo en la ruta o en el tránsito?",
     "a two-lane rural road at the entrance of a small Argentine town, cars and a truck, golden hour"),
    ("¿Hay algo que quieras que investiguemos?",
     "a person at a kitchen table at night looking at a smartphone with concern, warm lamp light"),
)
# El motivo, ABAJO (15/11/2026, pedido del usuario: todo el texto arriba y la imagen abajo, sin que el texto
# tape el sujeto): la mitad de arriba, tranquila (cielo, pared). Igual se ubica el sujeto con Gemini y se acomoda
# la imagen (ubicar_sujeto / componer), porque la IA no siempre hace caso.
ESTILO = (" Cinematic realistic photograph, vertical composition with the main subject clearly visible in the LOWER "
          "half of the frame, the upper half calm and simple (open sky or a plain wall), shallow depth of field, "
          "natural colors with warm tones, plain walls and blank surfaces, wordless scene.")
PRIMER_DIA = date(2026, 11, 15)  # ese día va la primera pregunta de la lista
MODELOS_IMAGEN = ("@cf/leonardo/lucid-origin", "@cf/leonardo/phoenix-1.0")


def activo() -> bool:
    return (os.environ.get("HIST_CORRESPONSALES") or "1").strip() != "0"


# EL REEL DE LOS SÁBADOS Y DOMINGOS (14/11/2026, pedido del usuario: «agregar para sábado/domingo a las 10am reel
# de la historia del bot»): esos días el mismo video sale ADEMÁS como reel en Instagram y Facebook. Días con
# HIST_CORRESPONSALES_REEL (0=lunes … 6=domingo, separados por coma; por defecto «5,6»); «no» lo apaga.
WHATSAPP_LINK = "https://wa.me/542346533450"
HASHTAGS = "#Chivilcoy #Corresponsales #DiarioLaCampaña #RadioDelCentro #Noticias"


def dias_reel() -> set:
    crudo = (os.environ.get("HIST_CORRESPONSALES_REEL") or "5,6").strip().lower()
    if crudo in ("0", "no", "off", "ninguno"):
        return set()
    return {int(x) for x in crudo.replace(" ", "").split(",") if x.isdigit() and int(x) <= 6}


def lleva_reel(dia: date) -> bool:
    return dia.weekday() in dias_reel()


def texto_reel(pregunta: str, red: str) -> str:
    """El texto del reel. En Instagram, sin links (regla del diario); en Facebook, con el link al WhatsApp."""
    wa = f"\n👉 {WHATSAPP_LINK}" if red == "facebook" else ""
    return (f"📲 {pregunta} Contanos.\n\n"
            f"Mandanos tu video, foto o audio con tu noticia por WhatsApp al {NUMERO}.{wa}\n\n"
            f"Sumate al Programa de Corresponsales de Diario La Campaña: tu noticia puede tener premio.\n\n"
            f"{HASHTAGS}")


def _reel_instagram(url: str, caption: str, portada_ms: int) -> dict:
    from reels import instagram as IG
    from reels import publicador as PB
    uid = os.environ.get("INSTAGRAM_USER_ID", "")
    tok = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    params = IG.contenedor_reel(url, caption, prueba=False)
    params["thumb_offset"] = str(max(0, int(portada_ms)))     # la portada: con todo el texto a la vista
    cid = PB._contenedor_listo(uid, tok, params)
    return {"id": PB._publicar_contenedor(uid, tok, cid, caption) or None}


def _reel_facebook(mp4: Path, caption: str) -> dict:
    from reels import publicador as PB
    return PB._publicar_facebook({"descripcion_tiktok": caption}, Path(mp4))


def pregunta_de(dia: date) -> tuple:
    return PREGUNTAS[(dia - PRIMER_DIA).days % len(PREGUNTAS)]


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La imagen con IA
# ─────────────────────────────────────────────────────────────────────────────────────────────
def generar_imagen(escena: str, destino: Path, pedir=None, mirar=None, log=print) -> str:
    """La escena en 9:16 (768x1344), sin letras. "" si ningún modelo la dio."""
    import httpx
    from archivo import imagen as IM
    cuenta, tok = IM.credenciales()
    if not cuenta or not tok:
        log("   imagen IA: faltan CF_ACCOUNT_ID / CF_API_TOKEN")
        return ""
    pedir = pedir or (lambda url, **kw: httpx.post(url, timeout=180, **kw))
    mirar = IM.tiene_texto if mirar is None else mirar
    prompt = (escena + ESTILO)[:1500]
    for modelo in MODELOS_IMAGEN:
        for intento in range(2):
            try:
                r = pedir(f"https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/run/{modelo}",
                          headers={"Authorization": f"Bearer {tok}"},
                          json={"prompt": prompt, "width": 768, "height": 1344})
                if r.status_code != 200:
                    log(f"   imagen IA ({modelo}): HTTP {r.status_code}")
                    break
                tipo = r.headers.get("content-type") or ""
                crudo = r.content if tipo.startswith("image/") else base64.b64decode(
                    ((r.json() or {}).get("result") or {}).get("image") or "")
                with Image.open(io.BytesIO(crudo)) as im:
                    im.convert("RGB").save(destino, "JPEG", quality=93)
            except Exception as e:  # noqa: BLE001 — se prueba otra vez u otro modelo
                log(f"   imagen IA ({modelo}): {type(e).__name__}")
                continue
            if mirar and mirar(str(destino)):
                log(f"   imagen IA ({modelo}): tiene letras, otra")
                continue
            return str(destino)
    # Último recurso, el modelo barato de siempre (FLUX schnell, solo cuadrada): la franja vertical del medio.
    r = IM.generar(escena, destino, pedir=pedir, estilo=ESTILO)
    if r.get("archivo") and not (mirar and mirar(r["archivo"])):
        with Image.open(r["archivo"]) as im:
            im = im.convert("RGB")
            ancho = round(im.height * 9 / 16)
            x = (im.width - ancho) // 2
            im.crop((x, 0, x + ancho, im.height)).save(destino, "JPEG", quality=93)
        log("   imagen IA: va la de FLUX schnell (recortada a 9:16)")
        return str(destino)
    log(f"   imagen IA (FLUX schnell): {r.get('motivo') or 'tiene letras'}")
    return ""


CAJA_POR_DEFECTO = (0.45, 0.15, 0.95, 0.85)     # (arriba, izquierda, abajo, derecha) de 0 a 1: lo que se pidió


def ubicar_sujeto(ruta: str, preguntar=None, log=print) -> tuple:
    """Dónde está el sujeto u objeto principal de la imagen: (arriba, izquierda, abajo, derecha) de 0 a 1. Lo mira
    Gemini; si no contesta, se supone que hizo caso al pedido (la mitad de abajo)."""
    try:
        if preguntar is None:
            from reels import ia
            def preguntar(imagen):                 # noqa: E306
                crudo, _ = ia.redactar_gemini(
                    "Sos un editor de fotos. Devolvé SOLO un JSON.",
                    "Marcá el sujeto u objeto principal de esta imagen (la persona, el animal, el objeto o la escena "
                    "que cuenta algo) con una sola caja que lo contenga entero. Respondé {\"caja\": [ymin, xmin, "
                    "ymax, xmax]} en una escala de 0 a 1000.", max_tokens=200,
                    imagenes=[("image/jpeg", Path(imagen).read_bytes())])
                return ia._parsear(crudo)
        caja = [float(v) / 1000 for v in (preguntar(ruta) or {}).get("caja")]
        y0, x0, y1, x1 = (min(1.0, max(0.0, v)) for v in caja)
        if y1 - y0 < 0.05 or x1 - x0 < 0.05:
            raise ValueError("caja vacía")
        return (y0, x0, y1, x1)
    except Exception as e:  # noqa: BLE001
        log(f"   sujeto: no se pudo ubicar ({type(e).__name__}); se supone abajo")
        return CAJA_POR_DEFECTO


def componer(foto: Image.Image, caja: tuple, y_libre: int, y_fin: int = 1700, margen: int = 24) -> tuple:
    """La foto en la pantalla, con el sujeto ENTERO entre `y_libre` (debajo del texto) y `y_fin` (arriba de la
    caja de mensaje de Instagram). Devuelve (imagen W×H, centro del sujeto en la pantalla). Si para que entre hay
    que achicarla o bajarla, lo que queda vacío se rellena con la misma foto, desenfocada y oscurecida."""
    iw, ih = foto.size
    y0, x0, y1, x1 = caja
    cubre = max(W / iw, H / ih)
    alto_libre = max(200, y_fin - y_libre - 2 * margen)
    alto_suj = (y1 - y0) * ih
    esc = min(cubre, alto_libre / max(1.0, alto_suj))            # se achica solo si el sujeto no entra
    w, h = round(iw * esc), round(ih * esc)
    cx_suj, cy_suj = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h
    # Horizontal: el sujeto al centro, sin dejar bordes si la foto cubre el ancho.
    dx = W / 2 - cx_suj
    if w >= W:
        dx = min(0, max(W - w, dx))
    else:
        dx = (W - w) / 2
    # Vertical: el sujeto entre y_libre y y_fin; si se puede, que la foto llegue hasta abajo.
    arriba_suj, abajo_suj = y0 * h, y1 * h
    dy_min = y_libre + margen - arriba_suj                        # el sujeto no sube por encima del texto
    dy_max = y_fin - margen - abajo_suj                           # ni baja hasta la caja de mensaje
    dy = max(dy_min, min(dy_max, H - h))                          # pegada abajo si se puede
    lienzo = _cubrir(foto, W, H).filter(ImageFilter.GaussianBlur(28))
    lienzo = Image.blend(lienzo, Image.new("RGB", (W, H), (0, 0, 0)), 0.35)
    chica = foto.resize((w, h), Image.LANCZOS)
    if w < W or dy > 0 or dy + h < H:
        # Bordes suaves para que no se note el corte con el relleno.
        borde = 60
        m = np.ones((h, w), np.float32)
        if dy > 0:
            m[:borde, :] *= np.linspace(0, 1, borde)[:, None]
        if dy + h < H:
            m[-borde:, :] *= np.linspace(1, 0, borde)[:, None]
        if w < W:
            m[:, :borde] *= np.linspace(0, 1, borde)[None, :]
            m[:, -borde:] *= np.linspace(1, 0, borde)[None, :]
        mascara = Image.fromarray((m * 255).astype(np.uint8), "L")
        lienzo.paste(chica, (round(dx), round(dy)), mascara)
    else:
        lienzo.paste(chica, (round(dx), round(dy)))
    return lienzo, (dx + cx_suj, dy + cy_suj)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Sonidos (los mismos de la historia de los entrevistados)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _t(seg: float) -> np.ndarray:
    return np.arange(int(SR * seg)) / SR


def sonido_pop(tono: float = 1.0) -> np.ndarray:
    t = _t(0.11)
    f = (820 * tono) * np.exp(-t * 28) + 190 * tono
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    clic = np.random.default_rng(int(tono * 1000)).normal(0, 1, t.size) * np.exp(-t * 900) * 0.35
    return (s + clic) * np.minimum(1, t / 0.002)


def sonido_tecla(rng) -> np.ndarray:
    t = _t(0.06)
    ruido = np.diff(np.concatenate([[0], rng.normal(0, 1, t.size)]))
    clac = ruido * np.exp(-t * rng.uniform(170, 230)) * 0.55
    golpe = np.sin(2 * np.pi * rng.uniform(140, 190) * t) * np.exp(-t * 70) * 0.5
    return (clac + golpe) * rng.uniform(0.75, 1.0)


def sonido_campanita() -> np.ndarray:
    t = _t(0.9)
    s = (np.sin(2 * np.pi * 2093 * t) + 0.45 * np.sin(2 * np.pi * 4186 * t) + 0.2 * np.sin(2 * np.pi * 3136 * t))
    return s * np.exp(-t * 5.5) * np.minimum(1, t / 0.003) * 0.5


def sonido_brisa(seg: float = 0.35) -> np.ndarray:
    t = _t(seg)
    suave = np.convolve(np.random.default_rng(7).normal(0, 1, t.size), np.ones(40) / 40, mode="same")
    return suave * np.sin(np.pi * np.clip(t / seg, 0, 1)) ** 2 * 0.9


def mezclar(eventos: list, duracion: float) -> np.ndarray:
    pista = np.zeros(int(SR * duracion) + SR)
    for seg, senal, vol in eventos:
        i = int(seg * SR)
        if 0 <= i < pista.size:
            n = min(senal.size, pista.size - i)
            pista[i:i + n] += senal[:n] * vol
    pista = pista[:int(SR * duracion)]
    pista = pista / (float(np.max(np.abs(pista))) or 1.0) * 0.85
    fade = int(SR * 0.4)
    pista[-fade:] *= np.linspace(1, 0, fade)
    return np.stack([pista, pista], axis=1).astype(np.float32)


def guardar_wav(pista: np.ndarray, destino: Path) -> Path:
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(pista, -1, 1) * 32767).astype("<i2").tobytes())
    return destino


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Dibujo
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _S():
    from nacionales import placa as P
    return P._story_image()


def _ease_back(x: float) -> float:
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def escala_pop(t: float, t0: float, dur: float = DUR_POP) -> float:
    return 0.0 if t < t0 else _ease_back(min(1.0, (t - t0) / dur))


def _cubrir(im: Image.Image, w: int, h: int) -> Image.Image:
    esc = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * esc), math.ceil(im.height * esc)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def fondo_naranja() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W * 0.5) / (W * 0.85)) ** 2 + ((yy - H * 0.42) / (H * 0.62)) ** 2)
    a = np.clip(d, 0, 1)[..., None]
    img = np.array((255, 158, 38), np.float32) * (1 - a) + np.array((226, 88, 6), np.float32) * a
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def velo(y_libre: int) -> Image.Image:
    """Una sombra oscura y suave SOLO detrás del texto de arriba (hasta `y_libre`) y un poco en el borde de abajo
    (la flecha). La foto se ve entera y la zona del sujeto no se toca."""
    y = np.arange(H, dtype=np.float32)[:, None]
    arriba = np.clip(1 - (y - y_libre * 0.55) / (y_libre * 0.55), 0, 1) ** 1.2 * 0.62
    abajo = np.clip((y - 1740) / 180, 0, 1) ** 1.5 * 0.45
    capa = np.zeros((H, W, 4), np.float32)
    capa[..., 3] = np.broadcast_to(np.maximum(arriba, abajo) * 255, (H, W))
    return Image.fromarray(capa.astype(np.uint8), "RGBA")


def _blanquear(im: Image.Image) -> Image.Image:
    b = Image.new("RGBA", im.size, (255, 255, 255, 255))
    b.putalpha(im.getchannel("A"))
    return b


def capa_logo() -> Image.Image:
    S = _S()
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lock = _blanquear(S._lockup_marca(360))
    iso = S._iso(False)
    iso_w = round(iso.width * lock.height / iso.height) if iso else 0
    x = (W - (iso_w + 22 + lock.width)) // 2
    if iso:
        capa.alpha_composite(iso.convert("RGBA").resize((iso_w, lock.height), Image.LANCZOS), (x, Y_LOGO))
    capa.alpha_composite(lock, (x + iso_w + 22, Y_LOGO))
    return capa


def _sprite(texto: str, fuente, color, pill=None, pad=(30, 14), sombra=False) -> Image.Image:
    m = ImageDraw.Draw(Image.new("L", (1, 1)))
    x0, y0, x1, y1 = m.textbbox((0, 0), texto, font=fuente)
    if pill:
        im = Image.new("RGBA", (x1 - x0 + 2 * pad[0], y1 - y0 + 2 * pad[1]), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=im.height // 2, fill=pill)
        d.text((pad[0] - x0, pad[1] - y0), texto, font=fuente, fill=color)
        return im
    asc, desc = fuente.getmetrics()
    im = Image.new("RGBA", (x1 - x0 + 24, asc + desc + 24), (0, 0, 0, 0))
    if sombra:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).text((12 - x0, 16 + asc), texto, font=fuente, fill=(90, 30, 0, 150), anchor="ls")
        im.alpha_composite(s.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).text((12 - x0, 12 + asc), texto, font=fuente, fill=color, anchor="ls")
    return im


def _pegar(capa: Image.Image, im: Image.Image, centro: tuple, escala: float, alfa: float = 1.0):
    if escala <= 0 or alfa <= 0:
        return
    if abs(escala - 1) > 0.002:
        im = im.resize((max(1, round(im.width * escala)), max(1, round(im.height * escala))), Image.BILINEAR)
    if alfa < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v, a=alfa: int(v * a)))
    capa.alpha_composite(im, (round(centro[0] - im.width / 2), round(centro[1] - im.height / 2)))


def plan(pregunta: str) -> dict:
    """Dónde y cuándo va cada cosa. TODO el texto arriba, de arriba hacia abajo desde el logo; `y_libre` es donde
    termina (de ahí para abajo, la imagen sin tapar)."""
    S = _S()
    m = ImageDraw.Draw(Image.new("L", (1, 1)))
    # La pregunta, grande: lo más grande que entre en 3 renglones (2 si se puede).
    tam = 112
    while True:
        f = S._sans(tam, 800)
        renglones, actual = [], []
        for p in pregunta.split():
            prueba = " ".join(actual + [p])
            if actual and m.textlength(prueba, font=f) > W - 90:
                renglones.append(actual)
                actual = [p]
            else:
                actual.append(p)
        renglones.append(actual)
        if (len(renglones) <= 2 and tam <= 112) or (len(renglones) <= 3 and tam <= 88) or tam <= 72:
            break
        tam -= 2
    paso_r = round(tam * 1.08)
    # La tarjeta del tipeo.
    tt = 40
    while tt > 30 and max(m.textlength(r, font=S._franklin(tt, 800)) for r in RENGLONES_CTA) > W - 140 - 88:
        tt -= 1
    ft = S._franklin(tt, 800)
    alto_tarjeta = len(RENGLONES_CTA) * round(tt * 1.28) + 2 * 22
    numero = _sprite(NUMERO, S._sans(74, 800), NARANJA, pill=BLANCO, pad=(40, 14))
    premio = _sprite(PREMIO, S._sans(38, 700), BLANCO, sombra=True)
    # La etiqueta, en blanco como la pregunta (pedido del 15/11/2026).
    etiqueta = _sprite(ETIQUETA, S._sans(40, 800), BLANCO, sombra=True)
    y_etiqueta = 286 + etiqueta.height // 2
    y_preg_ini = y_etiqueta + etiqueta.height // 2 - 8
    y_tarjeta = y_preg_ini + len(renglones) * paso_r + 22
    y_numero = y_tarjeta + alto_tarjeta + 20 + numero.height // 2
    y_premio = y_numero + numero.height // 2 + 4 + premio.height // 2
    y_libre = y_premio + premio.height // 2
    # Tiempos.
    t = 0.45
    piezas = [(etiqueta, (W / 2, y_etiqueta), t)]
    t += 0.35
    esp = m.textlength(" ", font=f)
    y = y_preg_ini
    for r in renglones:
        sprites = [_sprite(p, f, BLANCO, sombra=True) for p in r]
        ancho = sum(sp.width - 24 for sp in sprites) + esp * (len(r) - 1)
        x = (W - ancho) / 2
        for sp in sprites:
            piezas.append((sp, (x + (sp.width - 24) / 2, y + paso_r / 2), t))
            x += sp.width - 24 + esp
            t += 0.12
        y += paso_r
    t_tarjeta = t + 0.35
    t_tipeo = t_tarjeta + 0.4
    t_fin_tipeo = t_tipeo + len(TEXTO_CTA) / CPS
    t_numero = t_fin_tipeo + 0.25
    t_premio = t_numero + 0.55
    t_flecha = t_premio + 0.5
    total = min(15.0, max(12.0, t_flecha + 4.0))
    return {"piezas": piezas, "fuente_tarjeta": ft, "tam_tarjeta": tt, "alto_tarjeta": alto_tarjeta,
            "y_tarjeta": y_tarjeta, "numero": numero, "y_numero": y_numero, "premio": premio, "y_premio": y_premio,
            "y_libre": y_libre, "t_tarjeta": t_tarjeta, "t_tipeo": t_tipeo, "t_fin_tipeo": t_fin_tipeo,
            "t_numero": t_numero, "t_premio": t_premio, "t_flecha": t_flecha, "total": total}


def dibujar_tarjeta(capa: Image.Image, pl: dict, letras: int, cursor: bool, escala: float):
    if escala <= 0:
        return
    tw, th = W - 140, pl["alto_tarjeta"]
    tarjeta = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(tarjeta)
    d.rounded_rectangle((0, 0, tw - 1, th - 1), radius=36, fill=(255, 255, 255, 250))
    f, paso = pl["fuente_tarjeta"], round(pl["tam_tarjeta"] * 1.28)
    y, hecho = 22, 0
    xc, yc = 44, y
    for r in RENGLONES_CTA:
        visibles = r[:max(0, letras - hecho)]
        ancho = d.textlength(r, font=f)
        x = (tw - ancho) / 2
        d.text((x, y), visibles, font=f, fill=GRAFITO)
        xc, yc = x + d.textlength(visibles, font=f), y
        if hecho + len(r) >= letras:
            break
        hecho += len(r) + 1
        y += paso
    if cursor:
        d.rounded_rectangle((xc + 4, yc + 4, xc + 10, yc + pl["tam_tarjeta"] + 6), radius=3, fill=NARANJA)
    sombra = Image.new("RGBA", (tw + 60, th + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((30, 40, tw + 30, th + 40), radius=36, fill=(110, 40, 0, 110))
    sombra = sombra.filter(ImageFilter.GaussianBlur(18))
    sombra.alpha_composite(tarjeta, (30, 30))
    _pegar(capa, sombra, (W / 2, pl["y_tarjeta"] + th / 2), escala)


def _bezier(p0, p1, p2, p3, n=50):
    out = []
    for i in range(n + 1):
        u = i / n
        a, b, c, d = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u ** 2 * (1 - u), u ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def dibujar_flecha(capa: Image.Image, avance: float, t: float):
    """Abajo, chiquita: «o respondé esta historia» y una flecha sutil hacia la caja de «Enviar mensaje»."""
    if avance <= 0:
        return
    S = _S()
    mece = math.sin(2 * math.pi * t / 1.3)
    d = ImageDraw.Draw(capa)
    a = int(235 * min(1.0, avance * 2))
    d.text((560, 1752), RESPONDE, font=S._sans(34, 600), fill=(255, 255, 255, a), anchor="lm")
    pts = _bezier((544, 1754), (440, 1750), (330, 1760), (232 - 7 * mece, 1800 + 7 * mece))
    k = max(2, int(len(pts) * min(1.0, avance)))
    d.line(pts[:k], fill=(255, 255, 255, 235), width=6, joint="curve")
    if avance >= 1:
        (xa, ya), (xb, yb) = pts[-4], pts[-1]
        ang = math.atan2(yb - ya, xb - xa)
        for s in (+1, -1):
            a2 = ang + math.pi + s * math.radians(32)
            d.line([(xb, yb), (xb + 34 * math.cos(a2), yb + 34 * math.sin(a2))], fill=(255, 255, 255, 235), width=6)


def armar(pregunta: str, imagen: str, salida: Path, caja: tuple = None, log=print) -> Path:
    """El .mp4 de la historia (unos 13 segundos). `caja`: dónde está el sujeto en la imagen (ubicar_sujeto)."""
    from reels import reel_bot as R
    salida = Path(salida)
    pl = plan(pregunta)
    total = pl["total"]
    if imagen and Path(imagen).exists():
        original = Image.open(imagen).convert("RGB")
        foto, centro = componer(original, caja or ubicar_sujeto(imagen, log=log), pl["y_libre"])
    else:
        foto, centro = fondo_naranja(), (W / 2, H / 2)                       # sin imagen: el naranja
    capa_velo = velo(pl["y_libre"])
    logo = capa_logo()
    rng = np.random.default_rng(3)
    ev = [(t0, sonido_pop(1.2), 0.3) for _, _, t0 in pl["piezas"]]
    ev.append((pl["t_tarjeta"], sonido_pop(0.8), 0.45))
    for i, ch in enumerate(TEXTO_CTA):
        if ch != " ":
            ev.append((pl["t_tipeo"] + i / CPS, sonido_tecla(rng), 0.5))
    ev.append((pl["t_numero"], sonido_pop(0.7), 0.85))
    ev.append((pl["t_numero"] + 0.05, sonido_campanita(), 0.35))
    ev.append((pl["t_premio"], sonido_pop(1.0), 0.4))
    ev.append((pl["t_flecha"], sonido_brisa(), 0.25))
    wav = guardar_wav(mezclar(ev, total), salida.with_suffix(".wav"))
    proc = subprocess.Popen(
        [R.motor()._ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "pipe:0", "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", str(salida)], stdin=subprocess.PIPE)
    try:
        for k in range(int(total * FPS)):
            t = k / FPS
            # La foto, con un zoom lento hacia el sujeto (sin moverlo de su lugar).
            z = 1 / (1 + 0.025 * (t / total))
            cw, ch = W * z, H * z
            x0 = centro[0] - (centro[0] * z)
            y0 = centro[1] - (centro[1] * z)
            cuadro = foto.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize(
                (W, H), Image.BILINEAR).convert("RGBA")
            cuadro.alpha_composite(capa_velo)
            a = min(1.0, t / 0.45)
            if a >= 1:
                cuadro.alpha_composite(logo)
            else:
                lg = logo.copy()
                lg.putalpha(lg.getchannel("A").point(lambda v, a=a: int(v * a)))
                cuadro.alpha_composite(lg, (0, round(-18 * (1 - a))))
            for sp, centro, t0 in pl["piezas"]:
                _pegar(cuadro, sp, centro, escala_pop(t, t0))
            letras = min(len(TEXTO_CTA), int(max(0.0, t - pl["t_tipeo"]) * CPS))
            cursor = (pl["t_tipeo"] <= t < pl["t_fin_tipeo"] or int(t * 2) % 2 == 0) and t < pl["t_numero"]
            dibujar_tarjeta(cuadro, pl, letras, cursor and t >= pl["t_tarjeta"] + 0.2, escala_pop(t, pl["t_tarjeta"]))
            # El número: entra con un pop y después «late» suave.
            s = escala_pop(t, pl["t_numero"], 0.45)
            if s > 0 and t > pl["t_numero"] + 0.45:
                s = 1 + 0.03 * math.sin(2 * math.pi * (t - pl["t_numero"]) / 1.1)
            _pegar(cuadro, pl["numero"], (W / 2, pl["y_numero"]), s)
            _pegar(cuadro, pl["premio"], (W / 2, pl["y_premio"]), escala_pop(t, pl["t_premio"]))
            dibujar_flecha(cuadro, (t - pl["t_flecha"]) / 0.55, t)
            falta = total - t
            if falta < 0.4:
                cuadro = Image.blend(cuadro, Image.new("RGBA", (W, H), NARANJA_HONDO + (255,)), 1 - falta / 0.4)
            proc.stdin.write(cuadro.convert("RGB").tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.wait()
    Path(wav).unlink(missing_ok=True)
    if proc.returncode != 0 or not salida.is_file():
        raise RuntimeError("ffmpeg no armó la historia de corresponsales")
    return salida


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La corrida de las 10
# ─────────────────────────────────────────────────────────────────────────────────────────────
def correr(publicar: bool, dia: date | None = None, carpeta: Path | None = None, log=print) -> dict:
    if not activo():
        log("Historia de corresponsales apagada (HIST_CORRESPONSALES=0).")
        return {"estado": "apagada"}
    dia = dia or datetime.now(AR).date()
    carpeta = Path(carpeta or tempfile.mkdtemp(prefix="hist_corr_"))
    carpeta.mkdir(parents=True, exist_ok=True)
    pregunta, escena = pregunta_de(dia)
    log(f"[corresponsales] historia de las 10 del {dia:%d/%m}: «{pregunta}»")
    imagen = generar_imagen(escena, carpeta / "fondo.jpg", log=log)
    log(f"   fondo: {'imagen IA' if imagen else 'naranja (sin imagen)'}")
    caja = ubicar_sujeto(imagen, log=log) if imagen else None
    if caja:
        log(f"   sujeto: de {caja[0]:.0%} a {caja[2]:.0%} del alto")
    mp4 = armar(pregunta, imagen, carpeta / f"historia_corresponsales_{dia:%Y%m%d}.mp4", caja, log)
    informe = {"estado": "simulada", "pregunta": pregunta, "imagen": bool(imagen), "archivo": str(mp4)}
    if lleva_reel(dia):
        log("   hoy también sale como reel en Instagram y Facebook")
    if not publicar:
        log(f"   (simulada) {mp4}")
        return informe
    from agro import publicar as AP
    from reels import publicador as PB
    AP.credenciales_diario()                         # que sean las de @diarioyradio, no otras
    url = PB.subir_a_release(mp4, mp4.name)
    lugar = PB._lugar_en_instagram()
    if lugar is None or lugar[0] >= 1:
        try:
            informe["instagram"] = AP._historia_video_instagram(url)
            log(f"   Instagram: OK {informe['instagram'].get('id')}")
        except Exception as e:  # noqa: BLE001
            informe["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Instagram: FALLÓ {informe['instagram']['error']}")
    else:
        informe["instagram"] = {"omitido": "sin cupo de Instagram"}
    try:
        informe["facebook"] = AP._historia_video_facebook(mp4)
        log(f"   Facebook: OK {informe['facebook'].get('id')}")
    except Exception as e:  # noqa: BLE001
        informe["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        log(f"   Facebook: FALLÓ {informe['facebook']['error']}")
    informe["estado"] = "publicada" if "id" in (informe.get("instagram") or {}) else "con_fallas"
    if lleva_reel(dia):
        # Una falla del reel no pinta de rojo la corrida: re-dispararla publicaría la historia otra vez.
        portada_ms = int(plan(pregunta)["total"] * 0.85 * 1000)
        reel = informe["reel"] = {}
        if lugar is None or lugar[0] >= 2:
            try:
                reel["instagram"] = _reel_instagram(url, texto_reel(pregunta, "instagram"), portada_ms)
                log(f"   Reel Instagram: OK {reel['instagram'].get('id')}")
            except Exception as e:  # noqa: BLE001
                reel["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                log(f"   Reel Instagram: FALLÓ {reel['instagram']['error']}")
        else:
            reel["instagram"] = {"omitido": "sin cupo de Instagram"}
        try:
            reel["facebook"] = _reel_facebook(mp4, texto_reel(pregunta, "facebook"))
            log(f"   Reel Facebook: OK {reel['facebook'].get('id')}")
        except Exception as e:  # noqa: BLE001
            reel["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Reel Facebook: FALLÓ {reel['facebook']['error']}")
    return informe


def main():
    ap = argparse.ArgumentParser(description="Historia de las 10 del programa de corresponsales")
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--dia", default="")
    ap.add_argument("--carpeta", default="")
    a = ap.parse_args()
    import entorno
    entorno.cargar()
    entorno.consola_utf8()
    dia = date.fromisoformat(a.dia) if a.dia else None
    inf = correr(a.publicar, dia, Path(a.carpeta) if a.carpeta else None)
    print(inf)
    if a.publicar and inf.get("estado") != "publicada":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
