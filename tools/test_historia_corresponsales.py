# -*- coding: utf-8 -*-
"""La historia de las 10 del programa de corresponsales (reels/historia_corresponsales.py), sin red.

    venv\\Scripts\\python.exe tools\\test_historia_corresponsales.py
"""
import io
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image  # noqa: E402

from reels import historia_corresponsales as HC  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


chequear("la primera pregunta (15/11/2026) es «¿Viste algo raro en la calle?»",
         HC.pregunta_de(date(2026, 11, 15))[0] == "¿Viste algo raro en la calle?")
dias = [HC.pregunta_de(date(2026, 11, 15) + timedelta(days=k))[0] for k in range(len(HC.PREGUNTAS))]
chequear("una pregunta distinta cada día hasta dar la vuelta", len(set(dias)) == len(HC.PREGUNTAS))
chequear("el número del bot es el 2346-533450", HC.NUMERO == "2346-533450")
chequear("la placa no dice «imagen generada con IA»",
         not any("ia" in x.lower().split() or "generada" in x.lower()
                 for x in (HC.ETIQUETA, HC.TEXTO_CTA, HC.PREMIO, HC.RESPONDE)))


# --- la imagen: los modelos en orden, sin letras ------------------------------------------------
def _jpg(w, h):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (120, 80, 40)).save(b, "JPEG")
    return b.getvalue()


class _R:
    def __init__(self, status, contenido=b"", tipo="image/jpeg"):
        self.status_code, self.content, self.headers = status, contenido, {"content-type": tipo}

    def json(self):
        return {}


pedidos = []


def pedir_primero_falla(url, **kw):
    pedidos.append(url.rsplit("/", 1)[1])
    return _R(429) if "lucid" in url else _R(200, _jpg(768, 1344))


os.environ.setdefault("CF_ACCOUNT_ID", "x")
os.environ.setdefault("CF_API_TOKEN", "x")
tmp = Path(tempfile.mkdtemp())
r = HC.generar_imagen("a street", tmp / "a.jpg", pedir=pedir_primero_falla, mirar=lambda p: False, log=lambda *a: None)
chequear("si Lucid Origin no contesta, va Phoenix (9:16)", r and pedidos == ["lucid-origin", "phoenix-1.0"]
         and Image.open(r).size == (768, 1344))
vistas = []
r = HC.generar_imagen("a street", tmp / "b.jpg", pedir=lambda url, **kw: _R(200, _jpg(768, 1344)),
                      mirar=lambda p: vistas.append(p) or len(vistas) < 2, log=lambda *a: None)
chequear("si la imagen tiene letras se pide otra", r and len(vistas) == 2)
r = HC.generar_imagen("a street", tmp / "c.jpg", pedir=lambda url, **kw: _R(429), mirar=lambda p: False,
                      log=lambda *a: None)
chequear("sin ninguna imagen: \"\" (va el fondo naranja)", r == "")

# --- el plan: todo adentro de lo que se ve de la historia -----------------------------------------
for pregunta, _ in HC.PREGUNTAS:
    pl = HC.plan(pregunta)
    arriba = min(c[1] - sp.height / 2 for sp, c, _ in pl["piezas"])
    if not (arriba >= 280 and pl["y_premio"] < 1700 and pl["total"] <= 15):      # el logo termina en ~250
        chequear(f"«{pregunta}» entra en la zona segura y dura 15 s como mucho", False)
        break
else:
    chequear("todas las preguntas entran en la zona segura (debajo del logo, arriba de la caja de mensaje) y "
             "duran 15 s como mucho", True)

# --- el sujeto nunca queda debajo del texto (pedido del 15/11/2026) -------------------------------------
foto = Image.new("RGB", (768, 1344), (90, 120, 160))
y_libre = 950
bien = True
for caja in ((0.05, 0.3, 0.35, 0.7), (0.40, 0.2, 0.75, 0.8), (0.55, 0.1, 0.98, 0.9), (0.10, 0.1, 0.95, 0.9)):
    lienzo, (cx, cy) = HC.componer(foto, caja, y_libre)
    # Se reconstruye dónde quedó la caja: misma cuenta que componer.
    cubre = max(HC.W / 768, HC.H / 1344)
    esc = min(cubre, max(200, 1700 - y_libre - 48) / ((caja[2] - caja[0]) * 1344))
    h = 1344 * esc
    arriba = cy - (caja[2] - caja[0]) * h / 2
    abajo = cy + (caja[2] - caja[0]) * h / 2
    bien = bien and lienzo.size == (HC.W, HC.H) and arriba >= y_libre and abajo <= 1700 + 1
chequear("el sujeto queda ENTERO debajo del texto y arriba de la caja de mensaje (arriba, al medio, abajo o "
         "enorme)", bien)
r = HC.ubicar_sujeto("x.jpg", preguntar=lambda _: {"caja": [520, 300, 900, 700]}, log=lambda *a: None)
chequear("ubicar_sujeto pasa la caja de Gemini (0 a 1000) a 0 a 1", r == (0.52, 0.3, 0.9, 0.7))
r = HC.ubicar_sujeto("x.jpg", preguntar=lambda _: 1 / 0, log=lambda *a: None)
chequear("si Gemini no contesta, se supone el sujeto abajo (lo que se pidió)", r == HC.CAJA_POR_DEFECTO)

# --- el reel de los sábados y domingos (pedido del 14/11/2026) --------------------------------------------
os.environ.pop("HIST_CORRESPONSALES_REEL", None)
chequear("sábado y domingo sale también como reel; de lunes a viernes, no",
         HC.lleva_reel(date(2026, 11, 14)) and HC.lleva_reel(date(2026, 11, 15))
         and not any(HC.lleva_reel(date(2026, 11, 16) + timedelta(days=k)) for k in range(5)))
os.environ["HIST_CORRESPONSALES_REEL"] = "no"
chequear("HIST_CORRESPONSALES_REEL=no apaga el reel", not HC.lleva_reel(date(2026, 11, 15)))
os.environ.pop("HIST_CORRESPONSALES_REEL", None)
ig, fb = HC.texto_reel("¿Viste algo raro?", "instagram"), HC.texto_reel("¿Viste algo raro?", "facebook")
chequear("el texto del reel: número en las dos redes, link de WhatsApp solo en Facebook",
         HC.NUMERO in ig and HC.NUMERO in fb and "http" not in ig and HC.WHATSAPP_LINK in fb)

from agro import publicar as AP  # noqa: E402
from reels import publicador as PB  # noqa: E402

hechos = []
AP.credenciales_diario = lambda: {}
PB.subir_a_release = lambda p, n: "https://x/" + n
PB._lugar_en_instagram = lambda: (50, 50, 100)
AP._historia_video_instagram = lambda url: hechos.append("historia ig") or {"id": "1"}
AP._historia_video_facebook = lambda mp4: hechos.append("historia fb") or {"id": "2"}
HC._reel_instagram = lambda url, cap, ms: hechos.append(("reel ig", ms > 0)) or {"id": "3"}
HC._reel_facebook = lambda mp4, cap: hechos.append("reel fb") or {"id": "4"}
HC.generar_imagen = lambda *a, **k: ""
HC.armar = lambda pregunta, imagen, salida, caja, log: Path(salida)
silencio = lambda *a: None  # noqa: E731
inf = HC.correr(True, date(2026, 11, 15), tmp / "dom", log=silencio)
chequear("domingo: historia en IG y FB y además el reel en IG (con portada) y FB",
         hechos == ["historia ig", "historia fb", ("reel ig", True), "reel fb"] and inf["estado"] == "publicada")
hechos.clear()
HC.correr(True, date(2026, 11, 16), tmp / "lun", log=silencio)
chequear("lunes: solo la historia", hechos == ["historia ig", "historia fb"])
hechos.clear()
HC._reel_instagram = lambda *a: 1 / 0
inf = HC.correr(True, date(2026, 11, 14), tmp / "sab", log=silencio)
chequear("si el reel falla, la historia queda publicada y la corrida no se pinta de rojo",
         inf["estado"] == "publicada" and "error" in inf["reel"]["instagram"] and hechos[-1] == "reel fb")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
