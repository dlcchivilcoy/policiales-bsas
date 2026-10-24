# -*- coding: utf-8 -*-
"""EL POSTEO DE DATOS de cada mañana, a las 5, en colab entre @diarioyradioagro y @diarioyradio.

23/10/2026 (pedido del editor: «hacer un reel con todas las placas de las historias en 4:5, que vayan pasando
cada 5 segundos, y que salga la publicación como colab todos los días a las 5 am»): un reel.

24/10/2026 (pedido del editor: «agregá el mapa de dónde va a llover al posteo diario e incluí a Chivilcoy como
centro del mapa; ese reel transformalo en carrusel y continuá con el sistema de colaboración; ponele etiqueta
de IA; que aumente el SEO y la tasa de retención, con una portada que llame la atención con toda la
información crucial para el agro»): ahora es un CARRUSEL 4:5 (AGRO_DATOS_FORMATO=reel vuelve al reel):

    1  PORTADA: una frase que engancha (la alerta, la lluvia que llega o el mayor movimiento del día) y el
       tablero: soja, maíz y trigo en Rosario, dólar mayorista, soja en Chicago y la lluvia en Chivilcoy, sobre
       una imagen del campo generada con IA (el banco revisado de agro/marca/banco).
    2  EL MAPA de dónde va a llover, con Chivilcoy en el centro (agro/mapa_lluvia.py).
    3… las alertas del SMN que tocan la zona, el clima, la pizarra de Rosario, el dólar y Chicago (las placas
       de las historias, en 4:5).
    ú  EL CIERRE: guardalo, compartilo y seguinos (lo que más pesa en la retención de un carrusel).

Instagram: en @diarioyradioagro con @diarioyradio de COLABORADOR (`collaborators`) y la invitación aceptada
sola con la cuenta del diario (publicar.aceptar_colab). Si la colab no se puede, sale igual en agro.
Facebook no tiene colab: sale como álbum en las DOS páginas (AGRO_REEL_DATOS_FB_DIARIO=0 deja solo agro).

ETIQUETA DE IA: la API de Instagram no tiene un botón para eso. Meta pone «Información de IA» cuando la imagen
trae los metadatos estándar de la industria (IPTC DigitalSourceType); cada diapositiva los lleva (marcar_ia) y
el texto lo dice («Portada ilustrada con una imagen generada con IA»).

Las placas de datos dicen la fecha del dato y la fuente; si un dato no es de hoy, lo dicen («Último dato
disponible»). AGRO_REEL_DATOS cambia la hora (o "0" lo apaga: agro/agenda.py).
"""
import json
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

SEG_POR_PLACA = 5
FPS = 30
TIPOS = ("clima", "granos", "dolar", "chicago")
MAX_ALERTAS = 2
HASHTAGS = "#Agro #CampoArgentino #Chivilcoy #Mercados #Clima"
HASHTAGS_CARRUSEL = ("#Agro #CampoArgentino #Chivilcoy #PrecioDeLaSoja #PizarraRosario #DolarHoy #Lluvias "
                     "#PronosticoDelTiempo #Granos #Mercados")
FONDO_IA = ("agro", "mercados")                # carpetas del banco de imágenes IA para la portada
IPTC_IA = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
XMP_IA = ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
          '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
          '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/">'
          f'<Iptc4xmpExt:DigitalSourceType>{IPTC_IA}</Iptc4xmpExt:DigitalSourceType>'
          '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>').encode("utf-8")


def formato() -> str:
    """«carrusel» (desde el 24/10/2026) o «reel» (AGRO_DATOS_FORMATO=reel, el de antes)."""
    return "reel" if (os.environ.get("AGRO_DATOS_FORMATO") or "").strip().lower() == "reel" else "carrusel"


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def placas(datos: dict, mem: dict, carpeta: Path, momento: datetime) -> list:
    """[{tipo, archivo (4:5)}] en el orden del posteo: las alertas primero, después clima, granos, dólar y
    Chicago. Lo que no tiene dato no va."""
    from agro import historias as HI
    hoy = momento.date()
    carpeta = Path(carpeta)
    salida = []
    for a in (datos.get("alertas") or [])[:MAX_ALERTAS]:
        r = HI.placa_alerta(a, carpeta / f"dato_{len(salida):02d}_alerta.jpg", hoy)
        salida.append({"tipo": "alerta", "archivo": str(HI.ruta_45(r))})
    for tipo in TIPOS:
        destino = carpeta / f"dato_{len(salida):02d}_{tipo}.jpg"
        r = {"clima": lambda: HI.placa_clima(datos, destino, hoy, "EL CAMPO HOY"),
             "granos": lambda: HI.placa_granos(datos, mem, destino, hoy, "EL CAMPO HOY"),
             "dolar": lambda: HI.placa_dolar(datos, mem, destino, hoy, "EL CAMPO HOY"),
             "chicago": lambda: HI.placa_chicago(datos, destino, hoy, "EL CAMPO HOY")}[tipo]()
        if r:
            salida.append({"tipo": tipo, "archivo": str(HI.ruta_45(r))})
    return salida


def armar_video(archivos: list, destino: Path, seg: float = SEG_POR_PLACA) -> Path:
    """Las placas una detrás de otra, `seg` segundos cada una, 1080x1350, con una pista muda."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_ffmpeg(), "-loglevel", "error", "-y"]
    for a in archivos:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{seg}", "-i", str(a)]
    total = seg * len(archivos)
    cmd += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    escalas = "".join(f"[{i}:v]scale=1080:1350,setsar=1,format=yuv420p[v{i}];" for i in range(len(archivos)))
    unir = "".join(f"[v{i}]" for i in range(len(archivos))) + f"concat=n={len(archivos)}:v=1:a=0[v]"
    cmd += ["-filter_complex", escalas + unir, "-map", "[v]", "-map", f"{len(archivos)}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(destino)]
    subprocess.run(cmd, check=True, capture_output=True)
    return destino


def caption(momento: datetime, tipos: list) -> str:
    from agro import historias as HI
    que = {"alerta": "alertas del SMN", "clima": "el clima", "granos": "la soja, el trigo y el maíz en Rosario",
           "dolar": "el dólar", "chicago": "Chicago"}
    lista = []
    for t in tipos:
        if que.get(t) and que[t] not in lista:
            lista.append(que[t])
    cuerpo = ", ".join(lista[:-1]) + (f" y {lista[-1]}" if len(lista) > 1 else (lista[0] if lista else ""))
    return (f"📊 EL CAMPO HOY · {HI.fecha_larga(momento.date()).capitalize()}\n\n"
            f"Arrancá el día con los datos: {cuerpo}.\n\n"
            f"Deslizá y mirá placa por placa. Cada dato dice su fuente y su fecha.\n\n{HASHTAGS}")


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El carrusel (24/10/2026)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _pct(v) -> str:
    v = abs(v)
    return (f"{v:.2f}%" if v < 0.1 else f"{v:.1f}%").replace(".", ",")


def tablero(datos: dict, mem: dict, lluvia: dict) -> list:
    """Los datos de la portada: [{rotulo, valor, var (%) | None, nota, grano, donde}], en orden, hasta 6."""
    from agro import historias as HI
    from agro import mercado as M
    salida = []
    p = datos.get("pizarra") or {}
    previo = M.anterior(mem, "pizarra", p["fecha"]) if p.get("fecha") else None
    for grano in ("soja", "maiz", "trigo"):
        v = (p.get("productos") or {}).get(grano)
        if not v or not v.get("ars"):
            continue
        var = M.variacion(v["ars"], ((previo[1].get("productos") or {}).get(grano) or {}).get("ars")) if previo else None
        salida.append({"rotulo": f"{M.NOMBRE[grano].upper()} ROSARIO", "nombre": f"{M.NOMBRE[grano]} en Rosario",
                       "valor": f"${HI.pesos(v['ars'])}", "var": var, "nota": "por tonelada", "grano": grano,
                       "donde": "en Rosario", "fecha": p.get("fecha")})
    may = datos.get("mayorista") or {}
    if may.get("valor"):
        prev = M.anterior(mem, "a3500", may["fecha"])
        salida.append({"rotulo": "DÓLAR MAYORISTA", "nombre": "Dólar mayorista", "valor": f"${HI.pesos(may['valor'], 2)}",
                       "var": M.variacion(may["valor"], prev[1].get("valor")) if prev else None, "nota": "BCRA A3500",
                       "grano": "dolar", "donde": "", "fecha": may.get("fecha")})
    c = (datos.get("chicago") or {}).get("soja")
    if c and c.get("usd_t"):
        salida.append({"rotulo": "SOJA CHICAGO", "nombre": "Soja en Chicago", "valor": f"US$ {HI.pesos(c['usd_t'], 0)}",
                       "var": c.get("cambio_pct"), "nota": "por tonelada", "grano": "soja", "donde": "en Chicago",
                       "fecha": c.get("fecha")})
    mm = (lluvia or {}).get("chivilcoy_total")
    if mm is not None:
        salida.append({"rotulo": "LLUVIA EN CHIVILCOY", "nombre": "Lluvia en Chivilcoy",
                       "valor": f"{mm:.0f} mm" if mm >= 1 else "0 mm",
                       "var": None, "nota": f"próximas {(lluvia or {}).get('horas', 72)} horas", "grano": "lluvia",
                       "donde": ""})
    return salida[:6]


def gancho(datos: dict, tablero_: list, lluvia: dict) -> str:
    """La frase de la portada: la alerta, si hay; la lluvia que llega a Chivilcoy (5 mm o más); el mayor
    movimiento de precios (1% o más; en pasado: a las 5 los precios son del último cierre); si no, la de
    siempre."""
    alertas = datos.get("alertas") or []
    if alertas:
        a = alertas[0]
        return f"Alerta {a['nivel']} por {a['evento'].lower()} en la zona"
    mm = (lluvia or {}).get("chivilcoy_total")
    if mm and mm >= 5:
        return f"Llegan {mm:.0f} mm de lluvia a Chivilcoy"
    articulo = {"soja": "La soja", "maiz": "El maíz", "trigo": "El trigo", "dolar": "El dólar mayorista"}
    movs = [t for t in tablero_ if t.get("var") is not None and t["grano"] in articulo and abs(t["var"]) >= 1]
    if movs:
        t = max(movs, key=lambda x: abs(x["var"]))
        return f"{articulo[t['grano']]} {'subió' if t['var'] > 0 else 'bajó'} {_pct(t['var'])} {t['donde']}".strip()
    return "Lo que tenés que saber del campo hoy"


def cierres(tab: list) -> str:
    """«Últimos cierres: Rosario 22/10 · dólar 23/10 · Chicago 23/10» (nunca un dato viejo como de hoy)."""
    from agro import mercado as M
    partes = []
    for t in tab:
        if not t.get("fecha"):
            continue
        quien = {"dolar": "dólar"}.get(t["grano"]) or ("Chicago" if "CHICAGO" in t["rotulo"] else "Rosario")
        texto = f"{quien} {M.fecha_corta(t['fecha'])}"
        if texto not in partes:
            partes.append(texto)
    return ("Últimos cierres: " + " · ".join(partes)) if partes else ""


def _fondo_ia(hoy: date) -> str:
    from agro import imagen as IMG
    k = hoy.toordinal() % len(FONDO_IA)
    for sub in FONDO_IA[k:] + FONDO_IA[:k]:
        r = IMG.del_banco(sub, hoy.isoformat())
        if r:
            return r
    return ""


def portada(datos: dict, mem: dict, lluvia: dict, destino: Path, momento: datetime) -> Path:
    """La tapa del carrusel (4:5): la frase que engancha, el tablero de 6 datos y «deslizá»."""
    from agro import diseno as D
    from agro import historias as HI
    hoy = momento.date()
    W, H = HI.W, HI.H45
    im = Image.new("RGBA", (W, H), HI.FONDO + (255,))
    foto = _fondo_ia(hoy)
    if foto:
        im.alpha_composite(D.cubrir(Image.open(foto).convert("RGB"), W, H).convert("RGBA"))
    # Un velo oscuro que crece hacia abajo: la foto se ve arriba y los datos se leen abajo.
    velo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dv = ImageDraw.Draw(velo)
    for y in range(H):
        a = 125 + round(110 * min(1, max(0, (y - 120) / (H * 0.55))))
        dv.line((0, y, W, y), fill=HI.FONDO + (a,))
    im.alpha_composite(velo)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 10), fill=D.NARANJA)
    lg = D.lockup("grafito", 64)
    im.alpha_composite(lg, (D.X, 48))
    y = 48 + lg.height + 26
    caja = f"EL CAMPO HOY · {HI.fecha_larga(hoy).upper()}"
    fc = D.fuente("bold", 28)
    d.rectangle((D.X, y, D.X + d.textlength(caja, font=fc) + 32, y + 48), fill=D.NARANJA_CAJA)
    d.text((D.X + 16, y + 8), caja, font=fc, fill=D.BLANCO)
    y += 48 + 22
    tab = tablero(datos, mem, lluvia)
    ft, rt = D.ajustar(d, gancho(datos, tab, lluvia), "negra", 84, 56, W - 2 * D.X, 3)
    y = D.escribir(d, D.X, y, rt, ft, D.BLANCO) + 8
    fs, rs = D.ajustar(d, "Precios, dólar y lluvias para arrancar el día", "medium", 34, 28, W - 2 * D.X, 1)
    y = D.escribir(d, D.X, y, rs, fs, (225, 228, 233)) + 6
    if cierres(tab):
        fq, rq = D.ajustar(d, cierres(tab), "regular", 26, 22, W - 2 * D.X, 1)
        y = D.escribir(d, D.X, y, rq, fq, (190, 195, 202))
    y += 24
    # El tablero, en 2 columnas, apoyado abajo.
    gap, alto = 22, 168
    ancho = (W - 2 * D.X - gap) // 2
    filas = max(1, (len(tab) + 1) // 2)
    y_tab = max(y, H - 140 - filas * alto - (filas - 1) * gap)
    for k, t in enumerate(tab):
        x = D.X + (k % 2) * (ancho + gap)
        yy = y_tab + (k // 2) * (alto + gap)
        d.rounded_rectangle((x, yy, x + ancho, yy + alto), radius=20, fill=(20, 22, 26, 225))
        d.rectangle((x, yy + 18, x + 6, yy + alto - 18), fill=D.NARANJA)
        d.text((x + 26, yy + 18), t["rotulo"], font=D.fuente("bold", 24), fill=(175, 180, 188))
        fv = D.fuente("negra", 50 if len(t["valor"]) <= 10 else 42)
        d.text((x + 26, yy + 54), t["valor"], font=fv, fill=(120, 180, 255) if t["grano"] == "lluvia" else D.NARANJA)
        if t.get("var") is not None:
            HI.flecha(d, x + 26, yy + 120, t["var"], 26)
        else:
            d.text((x + 26, yy + 124), t["nota"], font=D.fuente("regular", 24), fill=(175, 180, 188))
    # «Deslizá» con su flecha (dibujada: la tipografía no trae flechas).
    yd = H - 100
    fd, rd = D.ajustar(d, "DESLIZÁ: MAPA DE LLUVIAS, PIZARRA, DÓLAR Y CHICAGO", "negra", 32, 22,
                       W - 2 * D.X - 70, 1)
    d.text((D.X, yd), rd[0], font=fd, fill=D.BLANCO)
    xa = D.X + d.textlength(rd[0], font=fd) + 18
    d.polygon([(xa, yd + 4), (xa + 30, yd + 19), (xa, yd + 34)], fill=D.NARANJA)
    if foto:
        d.text((D.X, H - 48), "Imagen de fondo generada con IA", font=D.fuente("regular", 20), fill=(160, 165, 172))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return destino


def cierre(destino: Path, momento: datetime) -> Path:
    """La última diapositiva: guardalo, compartilo y seguinos (la retención de un carrusel)."""
    from agro import diseno as D
    from agro import historias as HI
    W, H = HI.W, HI.H45
    im = Image.new("RGBA", (W, H), HI.FONDO + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 10), fill=D.NARANJA)
    marca = D.isologo(320)
    im.alpha_composite(marca, ((W - marca.width) // 2, 160))
    y = 160 + marca.height + 60
    for texto, peso, tam, color in (
            ("Todos los días a las 5, los datos del campo antes de arrancar", "negra", 58, D.BLANCO),
            ("Guardá este posteo y compartilo con quien trabaja en el campo", "medium", 36, (225, 228, 233))):
        f, r = D.ajustar(d, texto, peso, tam, 30, W - 2 * D.X, 3)
        for renglon in r:
            d.text(((W - d.textlength(renglon, font=f)) / 2, y), renglon, font=f, fill=color)
            y += round(f.size * 1.18)
        y += 34
    y += 20
    for cuenta, color in (("@diarioyradioagro", D.VERDE), ("@diarioyradio", D.NARANJA)):
        f = D.fuente("bold", 40)
        d.text(((W - d.textlength(cuenta, font=f)) / 2, y), cuenta, font=f, fill=color)
        y += 58
    f = D.fuente("regular", 28)
    sitio = "www.diariolacampaña.com.ar"
    d.text(((W - d.textlength(sitio, font=f)) / 2, H - 120), sitio, font=f, fill=(170, 175, 182))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return destino


def marcar_ia(jpg) -> Path:
    """Los metadatos IPTC que Meta lee para poner «Información de IA» (DigitalSourceType)."""
    jpg = Path(jpg)
    with Image.open(jpg) as im:
        im = im.convert("RGB")
    im.save(jpg, "JPEG", quality=92, xmp=XMP_IA)
    return jpg


def caption_carrusel(momento: datetime, datos: dict, tab: list) -> str:
    """El texto: arranca con lo que se busca (precio de granos, dólar y lluvia en Chivilcoy), repite los datos
    de la portada, invita a deslizar y a guardar, dice qué es IA y de dónde sale cada dato. Sin links."""
    from agro import historias as HI
    lineas = [f"🌾 EL CAMPO HOY · {HI.fecha_larga(momento.date()).capitalize()}: precio de la soja, el maíz y el "
              f"trigo, dólar y lluvias en Chivilcoy y la zona", ""]
    for a in (datos.get("alertas") or [])[:MAX_ALERTAS]:
        lineas.append(f"⚠️ Alerta {a['nivel']} por {a['evento'].lower()}")
    for t in tab:
        var = ""
        if t.get("var") is not None:
            signo = "▲" if t["var"] > 0.005 else "▼" if t["var"] < -0.005 else "="
            var = f" ({signo} {_pct(t['var'])})"
        icono = {"lluvia": "🌧️", "dolar": "💵"}.get(t["grano"], "📈" if "CHICAGO" in t["rotulo"] else "🌱")
        nota = "" if t["grano"] == "dolar" else f" {t['nota']}"
        lineas.append(f"{icono} {t['nombre']}: {t['valor']}{nota}{var}")
    if cierres(tab):
        lineas.append(f"🗓️ {cierres(tab)}")
    lineas += ["", "👉 Deslizá: el mapa de dónde va a llover (con Chivilcoy en el centro), la pizarra de Rosario, "
                   "el dólar y Chicago.",
               "📌 Guardalo para tenerlo a mano y compartilo con quien trabaja en el campo.", "",
               "Portada ilustrada con una imagen generada con IA. Datos: SMN, MET Norway, Cámara Arbitral de "
               "Cereales de Rosario, BCRA, Banco Nación y CME Group.", "", HASHTAGS_CARRUSEL]
    return "\n".join(lineas)[:2200]


def _album_facebook(jpgs: list, mensaje: str) -> dict:
    """Un posteo de Facebook con varias fotos, en la página de las credenciales del entorno."""
    from reels import publicador as PB
    pid = os.environ.get("FACEBOOK_PAGE_ID", "")
    tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    ids = []
    for j in jpgs:
        r = PB._pedir("POST", f"{PB.GRAPH}/{pid}/photos", tok, data={"published": "false"},
                      files={"source": (Path(j).name, Path(j).read_bytes(), "image/jpeg")})
        if r.status_code >= 400:
            raise PB.FalloRed(PB._error(r, "Facebook (foto del álbum)"))
        ids.append(str((r.json() or {}).get("id") or ""))
    data = {"message": mensaje}
    for i, fid in enumerate(ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": fid})
    r = PB._pedir("POST", f"{PB.GRAPH}/{pid}/feed", tok, data=data)
    if r.status_code >= 400:
        raise PB.FalloRed(PB._error(r, "Facebook (álbum)"))
    return {"id": str((r.json() or {}).get("id") or ""), "fotos": len(ids)}


def fb_diario() -> bool:
    return (os.environ.get("AGRO_REEL_DATOS_FB_DIARIO") or "1").strip() != "0"


def _colab_y_diario(salida: dict, publicar_fb_diario, log) -> dict:
    """Lo que sigue a Instagram y al Facebook de agro: aceptar la colab con la cuenta del diario y el
    Facebook del diario."""
    from agro import publicar as PUB
    ig = salida.get("instagram") or {}
    if ig.get("id") and ig.get("colab") != "no":
        try:
            salida["colab"] = PUB.aceptar_colab(ig["id"], log=log)
        except Exception as e:                             # noqa: BLE001
            salida["colab"] = {"estado": "pendiente", "detalle": f"{type(e).__name__}: {str(e)[:200]}"}
    if fb_diario():
        try:
            PUB.credenciales_diario()
            salida["facebook_diario"] = publicar_fb_diario()
            log(f"   Facebook @diarioyradio: {salida['facebook_diario'].get('id')}")
        except Exception as e:                             # noqa: BLE001
            salida["facebook_diario"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook @diarioyradio FALLÓ: {salida['facebook_diario']['error']}")
    return salida


def _contenedor_colab(uid: str, tok: str, params: dict, log) -> tuple:
    """(id del contenedor, con colab sí/no): primero con @diarioyradio de colaborador y, si Instagram no lo
    toma, sin colab."""
    from agro import publicar as PUB
    from reels import publicador as PB
    colab = PUB.usuario_diario()
    try:
        return PB._contenedor_listo(uid, tok, dict(params, collaborators=json.dumps([colab]))), True
    except PB.FalloRed as e:
        log(f"   Instagram no tomó la colab ({str(e)[:150]}): sale solo en @diarioyradioagro")
        return PB._contenedor_listo(uid, tok, params), False


def publicar_carrusel(jpgs: list, texto: str, log=print) -> dict:
    """Instagram (agro, con @diarioyradio de colaborador) y Facebook (álbum en agro y en el diario). Nunca
    lanza por una red: {red: {"id"…} | {"error"…}}."""
    from agro import publicar as PUB
    from reels import publicador as PB
    salida = {}
    marca = datetime.now().strftime("%Y%m%d")
    with PUB.credenciales_agro():
        uid, tok = os.environ["INSTAGRAM_USER_ID"], os.environ["INSTAGRAM_ACCESS_TOKEN"]
        try:
            hijos = []
            for i, j in enumerate(jpgs):
                url = PB.subir_a_release(Path(j), f"agro_datos_{marca}_{i:02d}.jpg")
                hijos.append(PB._contenedor_listo(uid, tok, {"image_url": url, "is_carousel_item": "true"}))
            cid, con_colab = _contenedor_colab(uid, tok, {"media_type": "CAROUSEL", "children": ",".join(hijos),
                                                          "caption": texto}, log)
            mid = PB._publicar_contenedor(uid, tok, cid, texto) or None
            colab = PUB.usuario_diario()
            salida["instagram"] = {"id": mid, "colab": f"@{colab}" if con_colab else "no", "diapositivas": len(jpgs)}
            log(f"   Instagram: {mid} ({len(jpgs)} diapositivas; colab con @{colab}: {'sí' if con_colab else 'no'})")
        except Exception as e:                             # noqa: BLE001
            salida["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Instagram FALLÓ: {salida['instagram']['error']}")
        try:
            salida["facebook"] = _album_facebook(jpgs, texto)
            log(f"   Facebook agro: {salida['facebook'].get('id')}")
        except Exception as e:                             # noqa: BLE001
            salida["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook agro FALLÓ: {salida['facebook']['error']}")
    return _colab_y_diario(salida, lambda: _album_facebook(jpgs, texto), log)


def publicar(mp4: Path, texto: str, portada: Path, log=print) -> dict:
    """EL REEL (hasta el 24/10/2026; AGRO_DATOS_FORMATO=reel): Instagram (agro, con @diarioyradio de
    colaborador) y Facebook (agro y diario). Nunca lanza por una red: {red: {"id"…} | {"error"…}}."""
    from agro import publicar as PUB
    from reels import instagram as IG
    from reels import publicador as PB
    salida = {}
    pp = {"descripcion_tiktok": texto, "video": {"alto": 1350}, "guion": {"titular": "El campo hoy", "bajada": ""}}
    nombre = f"agro_datos_{mp4.parent.name}.mp4"
    with PUB.credenciales_agro():
        uid, tok = os.environ["INSTAGRAM_USER_ID"], os.environ["INSTAGRAM_ACCESS_TOKEN"]
        try:
            url = PB.subir_a_release(mp4, nombre)
            portada_url = PB.subir_a_release(portada, f"agro_datos_{mp4.parent.name}_portada.jpg") if portada else ""
            params = IG.contenedor_reel(url, texto, prueba=False, portada=portada_url)
            cid, con_colab = _contenedor_colab(uid, tok, params, log)
            mid = PB._publicar_contenedor(uid, tok, cid, texto) or None
            colab = PUB.usuario_diario()
            salida["instagram"] = {"id": mid, "colab": f"@{colab}" if con_colab else "no"}
            log(f"   Instagram: {mid} (colab con @{colab}: {'sí' if con_colab else 'no'})")
        except Exception as e:                             # noqa: BLE001
            salida["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Instagram FALLÓ: {salida['instagram']['error']}")
        try:
            salida["facebook"] = PB.publicar_facebook(pp, mp4)
            log(f"   Facebook agro: {salida['facebook'].get('id')}")
        except Exception as e:                             # noqa: BLE001
            salida["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook agro FALLÓ: {salida['facebook']['error']}")
    return _colab_y_diario(salida, lambda: PB.publicar_facebook(pp, mp4), log)


def armar_carrusel(datos: dict, mem: dict, carpeta: Path, momento: datetime, lluvia=None, log=print) -> tuple:
    """([{tipo, archivo}] del carrusel, el pronóstico de lluvia usado). `lluvia`: el de agro/mapa_lluvia (si no
    viene, se baja; sin él, no van el mapa ni la lluvia de la portada)."""
    from agro import historias as HI
    from agro import mapa_lluvia as ML
    carpeta = Path(carpeta)
    if lluvia is None:
        try:
            lluvia = ML.lluvia(log=log)
        except Exception as e:                             # noqa: BLE001 — sin mapa, el resto sale igual
            log(f"   mapa de lluvia: no se pudo ({type(e).__name__}: {e})")
    lista = [{"tipo": "portada", "archivo": str(portada(datos, mem, lluvia, carpeta / "dato_portada.jpg", momento))}]
    if lluvia:
        r = ML.placa(lluvia, carpeta / "dato_mapa.jpg", momento.date())
        if r:
            lista.append({"tipo": "mapa", "archivo": str(HI.ruta_45(r))})
    lista += placas(datos, mem, carpeta, momento)
    lista.append({"tipo": "cierre", "archivo": str(cierre(carpeta / "dato_cierre.jpg", momento))})
    lista = lista[:9] + lista[-1:] if len(lista) > 10 else lista       # el tope de Instagram, con el cierre
    for p in lista:
        marcar_ia(p["archivo"])
    return lista, lluvia


def pasada(publicar: bool, horario: datetime, log=print, publicador=None, carpeta: Path = None,
           ahora: datetime = None, lluvia=None) -> Path:
    """El turno del posteo de datos (agro/pasada.py → _un_turno). `publicador`, si viene, reemplaza a
    publicar_carrusel (o a publicar, con AGRO_DATOS_FORMATO=reel)."""
    from agro import informe as INF
    from agro import mercado as M
    from agro import pasada as PA
    ahora = ahora or datetime.now(PA.TZ_AR)
    carpeta = Path(carpeta or PA.SALIDA / ahora.strftime("%Y-%m-%d_%H%M_reel_datos"))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = PA.MEMORIA_REAL if publicar else PA.MEMORIA
    mem = PA.cargar(ruta_mem)
    es_carrusel = formato() == "carrusel"
    log(f"[agro] {'CARRUSEL' if es_carrusel else 'REEL'} DE DATOS {'REAL' if publicar else 'SIMULADO'} "
        f"{ahora:%d/%m %H:%M} → {carpeta}")
    datos = M.leer_todo(mem, momento=ahora, log=log)
    if es_carrusel:
        lista, lluvia = armar_carrusel(datos, mem, carpeta, ahora, lluvia, log)
        de_datos = [p for p in lista if p["tipo"] not in ("portada", "cierre")]
    else:
        lista = de_datos = placas(datos, mem, carpeta, ahora)
    log(f"   {len(lista)} diapositivas: {', '.join(p['tipo'] for p in lista)}")
    registro = {"dia": ahora.date().isoformat(), "placas": [p["tipo"] for p in lista],
                "formato": "carrusel" if es_carrusel else "reel"}
    if de_datos:
        if es_carrusel:
            tab = tablero(datos, mem, lluvia)
            texto = caption_carrusel(ahora, datos, tab)
            registro["gancho"] = gancho(datos, tab, lluvia)
        else:
            mp4 = armar_video([p["archivo"] for p in lista], carpeta / "reel_datos.mp4")
            texto = caption(ahora, [p["tipo"] for p in lista])
            log(f"   reel: {len(lista) * SEG_POR_PLACA} s")
        (carpeta / "texto.txt").write_text(texto, encoding="utf-8")
        if publicar:
            registro["publicado"] = {"estado": "publicando"}
            mem.setdefault("reel_datos", {})[horario.isoformat()] = registro
            PA.guardar(mem, ahora, ruta_mem)
            if es_carrusel:
                res = (publicador or publicar_carrusel)([p["archivo"] for p in lista], texto, log=log)
            else:
                res = (publicador or publicar_reel)(mp4, texto, Path(lista[0]["archivo"]), log=log)
            registro["publicado"] = res
    mem.setdefault("reel_datos", {})[horario.isoformat()] = registro if publicar else dict(registro, simulado=True)
    lim = (ahora - timedelta(days=PA.DIAS_MEMORIA)).isoformat()
    mem["reel_datos"] = {k: v for k, v in mem["reel_datos"].items() if k >= lim}
    PA.guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "carrusel de datos" if es_carrusel else "reel de datos",
           "conteos": {"Diapositivas": len(lista)}, "historias": lista, "fuentes": [], "piezas": [],
           "descartadas": [], "grupos_duplicados": [], "config": {"score_min": "—", "max_dia": "—", "horas": 0},
           "publicar": publicar, "resultado": registro.get("publicado")}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)


publicar_reel = publicar
