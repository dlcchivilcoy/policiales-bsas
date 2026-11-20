# -*- coding: utf-8 -*-
"""EL REEL DEL CLIMA de @diarioyradioagro (16/11/2026).

Pedido del editor: «un ecosistema lo más intercalado posible: un reel, un carrusel» y priorizar los reels. El clima
es lo que más rinde en la cuenta (alertas, lluvia, temporal: entre 500 y 1.100 de alcance contra ~100 de lo demás).
Cuando se espera lluvia en la zona, UNO de los turnos de reel de la tarde (desde AGRO_CLIMA_DESDE, 13:00) que no tenga
una noticia con video propio sale como este reel: el mapa de lluvia con Chivilcoy en el centro (agro/mapa_lluvia.py)
moviéndose cada 6 horas durante los próximos 3 días, el acumulado de Chivilcoy que va sumando, los pueblos con más
lluvia prevista y el cierre. Sin IA: los números son del pronóstico de MET Norway (modelo ECMWF, CC BY 4.0).

Una vez por día. Solo si en Chivilcoy se esperan al menos AGRO_CLIMA_MIN_MM (3) en 72 h. AGRO_CLIMA_REEL=0 lo apaga.
Sale en Instagram y Facebook (y como historia, como todos los reels); no va a la web ni a YouTube.
"""
from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from agro import diseno as D
from agro import mapa_lluvia as ML

TZ_AR = timezone(timedelta(hours=-3))
TRAMO_H = 6
TRAMOS = ML.HORAS // TRAMO_H                      # 12
FPS = 24
SEG_TRAMO = 1.1
FUNDIDO = 0.35
SEG_PUEBLOS = 4.5
SEG_CIERRE = 2.5
LADO_MAPA = 960
Y_MAPA = 236
WHATSAPP = "2346-533450"
DIAS_CORTOS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


def activo() -> bool:
    return (os.environ.get("AGRO_CLIMA_REEL") or "1").strip() != "0"


def minimo_mm() -> float:
    try:
        return float(os.environ.get("AGRO_CLIMA_MIN_MM") or 3)
    except ValueError:
        return 3.0


def desde_hora() -> tuple:
    h, _, m = (os.environ.get("AGRO_CLIMA_DESDE") or "13:00").partition(":")
    try:
        return int(h), int(m or 0)
    except ValueError:
        return 13, 0


def ya_hoy(mem: dict, ahora: datetime) -> bool:
    hoy = ahora.strftime("%Y-%m-%d")
    if any(p.get("formato") == "clima" and (p.get("cuando") or "").startswith(hoy) and p.get("publicado")
           for p in mem.get("elegidas") or []):
        return True
    # 20/11/2026: si el reel de datos de la zona de las 11 fue el de la lluvia, la tarde no lo repite.
    from agro import reel_zona as RZ
    return RZ.lluvia_hoy(hoy)


def toca(mem: dict, horario: datetime) -> bool:
    """¿Este turno de reel puede ser el del clima? (sin mirar todavía el pronóstico)."""
    return activo() and (horario.hour, horario.minute) >= desde_hora() and not ya_hoy(mem, horario)


def lluvia_chivilcoy(ahora: datetime, get=None) -> float | None:
    """Los mm previstos en Chivilcoy en 72 h (un pedido): el filtro antes de pedir toda la grilla."""
    serie = ML._pedir_met(*ML.CENTRO, get=get)
    if not serie:
        return None
    desde = ahora.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return ML.sumar(serie, desde, desde + timedelta(hours=ML.HORAS))[0]


def datos(ahora: datetime, get=None, log=print) -> dict | None:
    """{tramos: [{desde, hasta, grilla, chivilcoy}], grilla (total), chivilcoy, chivilcoy_total, horas} o None."""
    desde = ahora.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    lats, lons = ML.puntos()
    tareas = [(la, lo) for la in lats for lo in lons]
    with ThreadPoolExecutor(max_workers=6) as ex:
        series = list(ex.map(lambda t: ML._pedir_met(t[0], t[1], get), tareas))
    if sum(1 for s in series if s is None) > len(tareas) // 4:
        log("   reel del clima: MET Norway no contestó; no va")
        return None
    centro = ML._pedir_met(*ML.CENTRO, get=get)
    tramos = []
    for i in range(TRAMOS):
        d0, d1 = desde + timedelta(hours=TRAMO_H * i), desde + timedelta(hours=TRAMO_H * (i + 1))
        valores = [ML.sumar(s, d0, d1)[0] if s is not None else 0.0 for s in series]
        grilla = [valores[k * len(lons):(k + 1) * len(lons)] for k in range(len(lats))]
        tramos.append({"desde": d0.isoformat(), "hasta": d1.isoformat(), "grilla": grilla,
                       "chivilcoy": ML.sumar(centro, d0, d1)[0] if centro else 0.0})
    total = [[sum(t["grilla"][a][b] for t in tramos) for b in range(len(lons))] for a in range(len(lats))]
    hasta = desde + timedelta(hours=ML.HORAS)
    tot_c, dias_c = ML.sumar(centro, desde, hasta) if centro else (sum(t["chivilcoy"] for t in tramos), {})
    return {"tramos": tramos, "grilla": total, "chivilcoy": dias_c, "chivilcoy_total": tot_c, "horas": ML.HORAS,
            "desde": desde.isoformat(), "hasta": hasta.isoformat()}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El dibujo
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _etiqueta(tramo: dict) -> str:
    """«mar 18 · 15 a 21 h»."""
    a = datetime.fromisoformat(tramo["desde"]).astimezone(TZ_AR)
    b = datetime.fromisoformat(tramo["hasta"]).astimezone(TZ_AR)
    return f"{DIAS_CORTOS[a.weekday()]} {a.day} · {a.hour} a {b.hour} h"


def _base(tema: dict) -> Image.Image:
    im = Image.new("RGB", (D.W, D.H45), tema["fondo"])
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, D.W, 8), fill=D.NARANJA)
    d.text((60, 44), "¿CUÁNDO LLUEVE EN LA ZONA?", font=D.fuente("negra", 60), fill=D.BLANCO)
    d.text((60, 120), "Lluvia prevista cada 6 horas · próximos 3 días", font=D.fuente("medium", 34),
           fill=tema["texto"])
    # Las franjas de milímetros.
    x, f = 60, D.fuente("medium", 24)
    for desde, color in ML.FRANJAS[1:6]:
        d.rounded_rectangle((x, 182, x + 34, 206), radius=6, fill=color)
        etq = f"{desde:g} mm"
        d.text((x + 42, 180), etq, font=f, fill=tema["texto"])
        x += 42 + d.textlength(etq, font=f) + 26
    return im


def _pie(im: Image.Image, tema: dict, i: int, tramo: dict, acumulado: float) -> None:
    d = ImageDraw.Draw(im)
    y = Y_MAPA + LADO_MAPA + 22
    ancho = (LADO_MAPA - (TRAMOS - 1) * 6) / TRAMOS
    for k in range(TRAMOS):
        x0 = 60 + k * (ancho + 6)
        d.rounded_rectangle((x0, y, x0 + ancho, y + 10), radius=5,
                            fill=D.NARANJA if k == i else (tema["linea"] if k > i else (120, 124, 132)))
    d.text((60, y + 26), _etiqueta(tramo), font=D.fuente("bold", 44), fill=D.BLANCO)
    txt = f"Chivilcoy: {acumulado:.0f} mm" if acumulado >= 1 else "Chivilcoy: 0 mm"
    f = D.fuente("negra", 44)
    d.text((D.W - 60 - d.textlength(txt, font=f), y + 26), txt, font=f, fill=(120, 180, 255))


def cuadro_mapa(datos_: dict, i: int, tema: dict, base: Image.Image, mapas: dict) -> Image.Image:
    if i not in mapas:
        mapas[i] = ML.dibujar_mapa({"grilla": datos_["tramos"][i]["grilla"]}, LADO_MAPA)
    im = base.copy()
    im.paste(mapas[i], (60, Y_MAPA), mapas[i])
    acum = sum(t["chivilcoy"] for t in datos_["tramos"][:i + 1])
    _pie(im, tema, i, datos_["tramos"][i], acum)
    return im


def placa_pueblos(datos_: dict, tema: dict) -> Image.Image:
    im = Image.new("RGB", (D.W, D.H45), tema["fondo"])
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, D.W, 8), fill=D.NARANJA)
    d.text((60, 70), "LO QUE SE ESPERA", font=D.fuente("negra", 64), fill=D.BLANCO)
    d.text((60, 150), "Milímetros previstos en los próximos 3 días", font=D.fuente("medium", 34), fill=tema["texto"])
    filas = ML.lluvia_por_pueblo(datos_)[:8]
    tope = max([mm for _, mm in filas] + [20.0])
    y = 250
    for nombre, mm in filas:
        d.rounded_rectangle((60, y, D.W - 60, y + 104), radius=18, fill=tema["linea"])
        chiv = nombre == "Chivilcoy"
        d.text((92, y + 28), nombre, font=D.fuente("bold", 44), fill=D.NARANJA if chiv else D.BLANCO)
        texto = f"{mm:.0f} mm" if mm >= 1 else "0 mm"
        f = D.fuente("negra", 48)
        d.text((D.W - 92 - d.textlength(texto, font=f), y + 24), texto, font=f,
               fill=(120, 180, 255) if mm >= 1 else tema["tenue"])
        if mm >= 1:
            d.rounded_rectangle((540, y + 44, 540 + max(12, round(220 * mm / tope)), y + 64), radius=10,
                                fill=(64, 140, 245))
        y += 120
    f = D.fuente("regular", 26)
    d.text((60, D.H45 - 110), "Pronóstico de MET Norway (modelo ECMWF), CC BY 4.0. Puede cambiar.", font=f,
           fill=tema["tenue"])
    d.text((60, D.H45 - 72), f"¿Llovió en tu campo? Mandá tu video al WhatsApp {WHATSAPP}", font=D.fuente("bold", 30),
           fill=D.NARANJA)
    return im


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def armar(datos_: dict, salida: Path, tema_nombre: str = "grafito") -> dict:
    """El .mp4 4:5 y su portada .jpg (el primer cuadro)."""
    from agro import reel as RE
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    tema = D.TEMAS["grafito"]
    base = _base(tema)
    mapas = {}
    pueblos = placa_pueblos(datos_, tema)
    cierre = RE.cierre(tema_nombre, "Seguinos para saber cuándo llueve en tu campo").convert("RGB")
    seg_mapas = TRAMOS * SEG_TRAMO
    total = seg_mapas + SEG_PUEBLOS + SEG_CIERRE
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{D.W}x{D.H45}",
           "-r", str(FPS), "-i", "-", "-f", "lavfi", "-t", f"{total:.2f}",
           "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "23",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(salida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    portada = None
    previo = None
    try:
        for k in range(round(total * FPS)):
            seg = k / FPS
            if seg < seg_mapas:
                i = min(TRAMOS - 1, int(seg / SEG_TRAMO))
                t = seg - i * SEG_TRAMO
                cuadro = cuadro_mapa(datos_, i, tema, base, mapas)
                if i and t < FUNDIDO:
                    cuadro = Image.blend(cuadro_mapa(datos_, i - 1, tema, base, mapas), cuadro, t / FUNDIDO)
            elif seg < seg_mapas + SEG_PUEBLOS:
                t = seg - seg_mapas
                cuadro = pueblos if t >= FUNDIDO else Image.blend(previo, pueblos, t / FUNDIDO)
            else:
                t = seg - seg_mapas - SEG_PUEBLOS
                cuadro = cierre if t >= FUNDIDO else Image.blend(pueblos, cierre, t / FUNDIDO)
            if portada is None:
                portada = cuadro.copy()
            previo = cuadro
            proc.stdin.write(cuadro.tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not salida.exists():
            raise RuntimeError(f"ffmpeg: {err[-300:]}")
    finally:
        if proc.poll() is None:
            proc.kill()
    jpg = salida.with_suffix(".jpg")
    portada.save(jpg, "JPEG", quality=90)
    return {"archivo": str(salida), "duracion": total, "peso_kb": round(salida.stat().st_size / 1024), "ancho": D.W,
            "alto": D.H45, "vista": str(jpg), "tema": tema_nombre, "con_video": False, "con_sonido": False}


def caption(datos_: dict, hoy) -> str:
    filas = [f for f in ML.lluvia_por_pueblo(datos_) if f[0] != "Chivilcoy" and f[1] >= 1][:4]
    pueblos = ", ".join(f"{n} {mm:.0f} mm" for n, mm in filas)
    partes = ["🌧️ ¿Cuándo llueve en Chivilcoy y la zona? Así se mueve la lluvia prevista para los próximos 3 días, "
              "cada 6 horas."]
    chiv = ML.texto_chivilcoy(datos_, hoy)
    if chiv:
        partes.append(chiv + ".")
    if pueblos:
        partes.append(f"Lo que más se espera en la zona: {pueblos}.")
    partes.append(f"📲 ¿Llovió en tu campo? Mandanos tu video o cuántos milímetros juntaste por WhatsApp al {WHATSAPP}, "
                  "y contanos de qué pueblo sos.")
    partes.append("Es un pronóstico (MET Norway, modelo ECMWF, CC BY 4.0): puede cambiar y cada campo puede recibir "
                  "distinto. Guardalo y compartilo con quien lo necesite.")
    partes.append("#Chivilcoy #Lluvia #Clima #Campo #Agro")
    return "\n\n".join(partes)


def pieza(datos_: dict, horario: datetime, carpeta: Path, tema: str = "grafito") -> dict:
    """La pieza con la forma que espera agro/publicar.publicar (reel; solo Facebook e Instagram)."""
    reel = armar(datos_, Path(carpeta) / f"clima_{horario:%Y%m%d_%H%M}.mp4", tema)
    texto = caption(datos_, horario.date())
    g = {"titular": "¿Cuándo llueve en la zona?", "bajada": "La lluvia prevista para los próximos 3 días en Chivilcoy "
         "y la zona.", "descripcion": texto, "hashtags": [], "titulo_web": "", "nota_web": "", "apta": True,
         "requires_review": False, "volanta": "Clima"}
    return {"id": f"clima-{horario:%Y%m%d%H%M}", "rep": {"url": "", "titulo": g["titular"], "fuente": "MET Norway"},
            "grupo": [], "score": {"subtema": "agro", "tema_doc": "clima", "ai_score": 0}, "guion": g, "formato": "reel",
            "youtube": False, "redes": ("facebook", "instagram"), "reel": reel, "portada": reel["vista"],
            "imagen": {"origen": "datos"}}
