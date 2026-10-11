# -*- coding: utf-8 -*-
"""Reels de DECLARACIÓN en policiales (10/10/2026): el audio de la nota del medio + su foto. Sin red ni IA
(el armado del reel sí corre el motor de verdad)."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import httpx  # noqa: E402

from reels import declaracion as DE  # noqa: E402
from reels import reel_bot as R  # noqa: E402
from scraper import fetch  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


BASE = "https://medio.com.ar/policiales/nota-1"

# ── El audio en la página ────────────────────────────────────────────────────────────────────
def pagina(cabeza="", cuerpo="", encabezado=""):
    return (f"<html><head>{cabeza}</head><body><header>{encabezado}</header>"
            f"<article><p>El comisario habló sobre el operativo.</p>{cuerpo}</article></body></html>")


def detalle_de(html):
    viejo = fetch.obtener_html
    fetch.obtener_html = lambda url, permitir, timeout: (html, None)
    try:
        return fetch.detalle(BASE)
    finally:
        fetch.obtener_html = viejo


chequear("og:audio de la nota", detalle_de(pagina(
    cabeza='<meta property="og:audio" content="/audios/declaracion.mp3">'))["audio"]
         == "https://medio.com.ar/audios/declaracion.mp3")
chequear("el reproductor de WordPress en el cuerpo (<audio><source>)", detalle_de(pagina(
    cuerpo='<audio class="wp-audio-shortcode"><source src="https://medio.com.ar/up/comisario.m4a?_=1"></audio>'))
         ["audio"] == "https://medio.com.ar/up/comisario.m4a?_=1")
chequear("un enlace a un .ogg en el cuerpo", detalle_de(pagina(
    cuerpo='<p>Escuchá: <a href="/media/fiscal.ogg">audio</a></p>'))["audio"] == "https://medio.com.ar/media/fiscal.ogg")
chequear("la radio en vivo del encabezado NO es el audio de la nota", detalle_de(pagina(
    encabezado='<audio src="https://stream.radio.com/vivo.mp3"></audio>'))["audio"] is None)
chequear("un stream sin extensión no cuenta", detalle_de(pagina(
    cuerpo='<audio src="https://stream.radio.com/live"></audio>'))["audio"] is None)
chequear("un iframe de SoundCloud no se baja (como YouTube)", detalle_de(pagina(
    cuerpo='<iframe src="https://w.soundcloud.com/player/?url=x"></iframe>'))["audio"] is None)
chequear("sin audio: None y el resto igual", detalle_de(pagina())["audio"] is None
         and detalle_de(pagina())["ok"] is True)

# ── Bajar el audio ───────────────────────────────────────────────────────────────────────────
tmp = Path(tempfile.mkdtemp(prefix="test_decl_"))


def cliente(headers, cuerpo=b"x" * 2000, codigo=200):
    return httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(codigo, headers=headers, content=cuerpo)))


def falla_con(headers, cuerpo=b"x" * 2000, codigo=200):
    try:
        DE.bajar_audio("https://medio.com.ar/a.mp3", tmp / "a.mp3", cliente(headers, cuerpo, codigo))
        return ""
    except DE.DeclaracionError as e:
        return str(e)


chequear("se baja un audio con su tamaño",
         falla_con({"content-type": "audio/mpeg", "content-length": "2000"}) == ""
         and (tmp / "a.mp3").stat().st_size == 2000)
chequear("sin tamaño declarado (una radio en vivo): no", "tamaño" in falla_con({"content-type": "audio/mpeg"}, b""))
chequear("más de 25 MB: no", "pesa" in falla_con({"content-type": "audio/mpeg",
                                                  "content-length": str(30 * 1024 * 1024)}))
chequear("una página HTML en lugar del audio: no", "no es un audio" in falla_con(
    {"content-type": "text/html", "content-length": "2000"}))
chequear("un 404: no", "HTTP 404" in falla_con({"content-length": "10"}, b"x" * 10, 404))

# ── Transcribir y planear (IA de mentira) ────────────────────────────────────────────────────
m = R.motor()
voz = tmp / "voz.m4a"
subprocess.run([m._ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
                "sine=frequency=200:duration=10,volume='0.5+0.5*sin(2*PI*t*1.5)':eval=frame",
                "-c:a", "aac", str(voz)], check=True)
segmentos_ok = {"segmentos": [{"desde": 0, "hasta": 4.5, "texto": "Detuvimos a dos personas en el barrio"},
                              {"desde": 4.5, "hasta": 9.8, "texto": "y secuestramos una moto robada"}]}


class Resp:
    def __init__(self, codigo, datos):
        self.status_code, self._d = codigo, datos

    def json(self):
        return self._d


visto = {}


def gemini_falso(url, json=None, headers=None):
    visto["partes"] = json["contents"][0]["parts"]
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": __import__("json").dumps(segmentos_ok)}]}}]})


os.environ.setdefault("GEMINI_API_KEY", "clave-de-prueba")
segs = DE.transcribir(voz, m._ffmpeg(), pedir=gemini_falso)
chequear("transcribir: el audio va EN LÍNEA como mp3 chico y vuelven los segmentos con tiempos",
         visto["partes"][0]["inline_data"]["mime_type"] == "audio/mp3" and len(segs) == 2
         and segs[1]["desde"] == 4.5)


def ia(plan):
    return lambda system, material: (plan, "falsa")


nota = {"audio": "https://medio.com.ar/a.mp3", "texto_completo": "Declaró el comisario Juan Pérez, de la Comisaría 1ª."}
guion = {"titular": "Detuvieron a dos personas y secuestraron una moto"}
plan_ok = {"hay_declaracion": True, "nombre": "Juan Pérez", "cargo": "Comisario de la Comisaría 1ª",
           "frases": [{"desde": 0, "texto": "Dos detenidos en el barrio"}, {"desde": 4.5, "texto": "Secuestraron una moto robada"}],
           "tramo": {"desde": 0, "hasta": 10}}
bajador = lambda url, destino: Path(shutil.copy2(voz, destino))  # noqa: E731
decl = DE.preparar(nota, guion, tmp, "p1", redactar=ia(plan_ok), transcriptor=lambda a, f: segs, bajador=bajador)
chequear("preparar: quién habla, cargo, frases y tramo", decl["nombre"] == "Juan Pérez"
         and decl["cargo"].startswith("Comisario") and len(decl["frases"]) == 2 and decl["duracion_audio"] > 9)


def no_sale(**kw):
    try:
        DE.preparar(nota, guion, tmp, "p2", bajador=bajador, **kw)
        return ""
    except DE.DeclaracionError as e:
        return str(e)


chequear("si la IA dice que no es una declaración (un detenido, un menor…): no sale",
         "detenido" in no_sale(redactar=ia({"hay_declaracion": False, "motivo": "habla un detenido"}),
                               transcriptor=lambda a, f: segs))
chequear("si no se sabe quién habla: no sale", "quién habla" in no_sale(
    redactar=ia({"hay_declaracion": True, "nombre": ""}), transcriptor=lambda a, f: segs))
chequear("si en el audio no se entiende a nadie: no sale", "no se entiende" in no_sale(
    redactar=ia(plan_ok), transcriptor=lambda a, f: []))
corto = tmp / "corto.m4a"
subprocess.run([m._ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=duration=3", "-c:a", "aac", str(corto)],
               check=True)
try:
    DE.preparar(nota, guion, tmp, "p3", redactar=ia(plan_ok), transcriptor=lambda a, f: segs,
                bajador=lambda u, d: Path(shutil.copy2(corto, d)))
    motivo_corto = ""
except DE.DeclaracionError as e:
    motivo_corto = str(e)
chequear("un audio de 3 segundos: no sale", "dura" in motivo_corto)


# ── Texto del posteo ─────────────────────────────────────────────────────────────────────────
desc = "Detuvieron a dos personas.\n\n📲 Más noticias en www.diario.com.ar\n\n#policiales #chivilcoy"
con = DE.caption_con_escucha(desc, "Juan Pérez")
chequear("el posteo invita a escuchar a quien habla, antes del link y los hashtags",
         con.split("\n\n")[1] == "🎧 Escuchá las declaraciones de Juan Pérez." and con.endswith("#chivilcoy"))
chequear("sin nombre, el posteo queda igual", DE.caption_con_escucha(desc, "") == desc)

# ── El reel, con el motor de verdad ──────────────────────────────────────────────────────────
from PIL import Image  # noqa: E402
foto = tmp / "foto.jpg"
Image.new("RGB", (1600, 900), (90, 100, 120)).save(foto)
vid = R.armar_declaracion(decl, tmp / "decl.mp4", foto=foto, respaldo=guion["titular"])
chequear("armar_declaracion: foto apaisada → reel 4:5 con sonido, frases y placa",
         (vid["ancho"], vid["alto"]) == (1080, 1350) and m.has_audio(vid["archivo"])
         and len(vid["declaracion"]["frases"]) == 2 and vid["placa"])
try:
    R.armar_declaracion(decl, tmp / "x.mp4")
    chequear("sin foto ni video: ReelError", False)
except R.ReelError:
    chequear("sin foto ni video: ReelError", True)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
