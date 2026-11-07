# -*- coding: utf-8 -*-
"""Policiales en Facebook: link a la nota en vez del carrusel; Instagram no cambia (6/11/2026). Sin red."""
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from reels import publicador as PUB

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


FOTO = "https://static.wixstatic.com/media/82cea5_abc~mv2.jpg"
PAGINA = f'<html><head><meta property="og:image" content="{FOTO}"></head></html>'
URL = "https://www.diariolacampaña.com.ar/n/chivilcoy-un-hecho-abc123"
LINK = "https://www.xn--diariolacampaa-2nb.com.ar/n/chivilcoy-un-hecho-abc123"


class Resp:
    def __init__(self, status=200, datos=None, text=""):
        self.status_code, self.datos, self.text = status, datos or {}, text

    def json(self):
        return self.datos


class Facebook:
    """La web y Facebook de mentira. `vistas`: la foto que dice ver en cada lectura de la nota."""

    def __init__(self, vistas=(FOTO,), pagina=PAGINA, feed_link=200, web=200):
        self.vistas, self.pagina, self.feed_link, self.web = list(vistas), pagina, feed_link, web
        self.lecturas, self.feed, self.fotos = 0, [], 0

    def __call__(self, metodo, url, token="", **kw):
        data = kw.get("data") or {}
        if metodo == "GET":
            return Resp(self.web, text=self.pagina)
        if url.endswith(".0/") or data.get("scrape"):
            vista = self.vistas[min(self.lecturas, len(self.vistas) - 1)]
            self.lecturas += 1
            if vista is None:
                return Resp(400, {"error": {"message": "Invalid parameter", "error_user_msg": "objeto inválido"}})
            return Resp(200, {"image": [{"url": vista}]})
        if url.endswith("/photos"):
            self.fotos += 1
            return Resp(200, {"id": f"foto{self.fotos}"})
        if url.endswith("/feed"):
            self.feed.append(data)
            if "link" in data and self.feed_link >= 400:
                return Resp(self.feed_link, {"error": {"message": "no se pudo"}})
            return Resp(200, {"id": f"posteo{len(self.feed)}"})
        raise AssertionError(f"pedido inesperado: {metodo} {url}")


esperas = []
PUB._dormir = esperas.append
TEXTO = ("Detuvieron a dos jóvenes en Chivilcoy.\n\nLa policía secuestró un arma.\n\n"
         "📲 Más noticias de Chivilcoy en www.diariolacampaña.com.ar\n\n#Chivilcoy #Policiales")


def correr(fb, tmp, url=URL):
    with mock.patch.object(PUB, "_pedir", fb):
        return PUB._publicar_red("facebook", PIEZA, Path(tmp) / "01.mp4", Path(tmp), url)


with tempfile.TemporaryDirectory() as tmp:
    slides = []
    for i in range(4):
        p = Path(tmp) / f"01_c{i}.jpg"
        p.write_bytes(b"jpg")
        slides.append(str(p))
    PIEZA = {"formato": "carrusel", "slides": slides, "descripcion_tiktok": TEXTO, "guion": {"titular": "Un hecho"}}

    chequear("el dominio va en punycode", PUB.link_para_facebook(URL) == LINK)
    chequear("un dominio sin Ñ no cambia", PUB.link_para_facebook("https://diario.com/n/x") == "https://diario.com/n/x")
    chequear("el texto es el primer párrafo, sin hashtags ni línea del sitio",
             PUB.texto_link_nota(PIEZA) == "Detuvieron a dos jóvenes en Chivilcoy.")
    chequear("sin texto, va el titular", PUB.texto_link_nota(dict(PIEZA, descripcion_tiktok="#Solo #Tags")) == "Un hecho")

    fb = Facebook()
    res = correr(fb, tmp)
    chequear("sale como link", res.get("estado") == "ok" and res.get("formato") == "link" and res.get("link") == LINK)
    chequear("un solo posteo, con el link y el texto corto, sin subir fotos",
             fb.feed == [{"link": LINK, "message": "Detuvieron a dos jóvenes en Chivilcoy."}] and fb.fotos == 0)

    fb = Facebook(vistas=(None, FOTO))
    esperas.clear()
    res = correr(fb, tmp)
    chequear("si la nota todavía no se deja leer, espera y vuelve a mirar", res.get("formato") == "link" and esperas == [20])

    otra = "https://static.wixstatic.com/media/82cea5_otra~mv2.jpg"
    fb = Facebook(vistas=(otra,))
    esperas.clear()
    res = correr(fb, tmp)
    chequear("con otra foto: sale el carrusel y queda anotado por qué",
             res.get("formato") == "carrusel" and fb.fotos == 4 and "foto" in res.get("sin_link", ""))
    chequear("y nunca publica el link", all("link" not in d for d in fb.feed) and esperas == [20, 60])
    chequear("el carrusel de respaldo lleva el link en el texto", URL in fb.feed[0]["message"])

    fb = Facebook(vistas=(None,))
    res = correr(fb, tmp)
    chequear("si Facebook rechaza la nota: carrusel", res.get("formato") == "carrusel" and "objeto" in res.get("sin_link", ""))

    fb = Facebook(pagina="<html></html>")
    res = correr(fb, tmp)
    chequear("nota sin foto: carrusel, sin preguntarle a Facebook", res.get("formato") == "carrusel" and fb.lecturas == 0)

    fb = Facebook(web=500)
    res = correr(fb, tmp)
    chequear("nota que no abre: carrusel", res.get("formato") == "carrusel" and "500" in res.get("sin_link", ""))

    fb = Facebook(feed_link=400)
    res = correr(fb, tmp)
    chequear("si Facebook no acepta el posteo del link: carrusel", res.get("formato") == "carrusel" and fb.fotos == 4)

    fb = Facebook()
    res = correr(fb, tmp, url="")
    chequear("sin nota en la web no hay link: carrusel", res.get("formato") == "carrusel" and fb.lecturas == 0)

    def cortado(metodo, url, token="", **kw):
        if url.endswith("/feed"):
            raise PUB._Cortado("sin respuesta")
        return Facebook()(metodo, url, token, **kw)

    with mock.patch.object(PUB, "_pedir", cortado):
        res = PUB._publicar_red("facebook", PIEZA, Path(tmp) / "01.mp4", Path(tmp), URL)
    chequear("corte al publicar: sin confirmar, no repite con el carrusel", res.get("estado") == "sin_confirmar")

    with mock.patch.dict(os.environ, {"POL_FB_LINK": "0"}):
        fb = Facebook()
        res = correr(fb, tmp)
    chequear("POL_FB_LINK=0 vuelve al carrusel", res.get("formato") == "carrusel" and fb.lecturas == 0)

    llamadas = []
    with mock.patch.object(PUB, "publicar_facebook", lambda *a: llamadas.append(a) or {"id": "reel"}):
        res = PUB._publicar_red("facebook", dict(PIEZA, formato="reel"), Path(tmp) / "01.mp4", Path(tmp), URL)
    chequear("lo que va como reel sigue como reel", res.get("id") == "reel" and len(llamadas) == 1)

    llamadas = []
    with mock.patch.object(PUB, "publicar_instagram", lambda *a: llamadas.append(a) or {"id": "ig", "formato": "carrusel"}), \
            mock.patch.object(PUB, "publicar_nota_facebook", lambda *a: llamadas.append("MAL") or {}):
        res = PUB._publicar_red("instagram", PIEZA, Path(tmp) / "01.mp4", Path(tmp), URL)
    chequear("Instagram sigue con su carrusel", res.get("formato") == "carrusel" and "MAL" not in llamadas)
    chequear("y el texto de Instagram no cambia: sin link a la nota", "/n/" not in PUB.texto_carrusel(PIEZA, "instagram"))

    with mock.patch.object(PUB, "_pedir", lambda *a, **k: (_ for _ in ()).throw(AssertionError("simular no toca la red"))):
        mp4 = Path(tmp) / "01.mp4"
        mp4.write_bytes(b"x")
        sim = PUB._simular("facebook", PIEZA, mp4, URL)
    chequear("simular muestra el link sin tocar la red", sim.get("formato") == "link" and sim.get("link") == LINK)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
