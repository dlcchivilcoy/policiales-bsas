# -*- coding: utf-8 -*-
"""¿El video del reel es de la nota? (reels/control_video.py, 14/11/2026), sin red ni IA de verdad.

Los casos son los de verdad: los tres reels de prueba que salieron con el video de otra nota (11, 12 y
13/11/2026) y los buenos de esos mismos días.

    venv\\Scripts\\python.exe tools\\test_control_video.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.pop("VIDEO_CONTROL", None)

from reels import control_video as CV  # noqa: E402
from nacionales import portales as PO  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. Palabras: lo seguro de un lado y del otro -------------------------------------------------------
MALOS = [
    ("Cambió Buenos Aires por las Sierras de Córdoba y construyó su propia casa sustentable",
     "Una mujer dejó la gran ciudad para instalarse en las sierras cordobesas donde construyó su vivienda ecológica.",
     "La jornada de entrenamientos de la selección argentina, con Dibu Martínez. Los dirigidos por Lionel "
     "Scaloni practicaron de cara a los amistosos"),
    ("Un bebé de 11 meses fue rescatado tras ser enterrado vivo en una jaula para perros",
     "El niño fue hallado con vida en un bosque de Batesburg-Leesville. Su padre fue arrestado. Las "
     "autoridades dieron detalles del operativo.",
     "El médico de la selección argentina habló sobre el estado de Dibu Martínez. Daniel Martínez brindó "
     "detalles de la recuperación del arquero"),
]
for titulo, texto, video in MALOS:
    p = CV.parecido(titulo, texto, video)
    chequear(f"palabras: «{titulo[:45]}…» con un video de la Selección → es de otra nota", p["veredicto"] == "no")

BUENOS = [
    ("Un tucán rescatado volvió a vivir en su hábitat natural tras recuperarse de una fractura",
     "Un ave silvestre fue liberada en Costa Rica.",
     "Un tucán rescatado regresó a la naturaleza tras una rehabilitación"),
    ("INAH rechaza veto a Tío Cardef en Museo Nacional de Antropología", "El influencer denunció…",
     "Tío Cardef acusa al INAH de vertarlo de museo"),
    ("La historia de Marta, la mujer con parálisis que habló ante el Papa",
     "Marta dio su testimonio frente a León XIV.", "El emocionante testimonio de Marta"),
]
for titulo, texto, video in BUENOS:
    chequear(f"palabras: «{titulo[:45]}…» con su video → es de la nota, sin gastar la IA",
             CV.parecido(titulo, texto, video)["veredicto"] == "si")

p = CV.parecido("Un récord Guinness y 50 maratones en 22 días: la hazaña de William Goodge",
                "El atleta compartió en redes sociales cada segundo de la travesía.",
                "El joven matemático Aaryan Nitin Shukla muestra en vivo su capacidad para resolver cálculos en "
                "cuestión de segundos. El joven compartió en redes sociales")
chequear("palabras: las maratones con el matemático comparten solo palabras sueltas («redes», «segundo») → duda, "
         "que mire la IA", p["veredicto"] == "duda" and p["titulo"] == 0)
chequear("palabras: un video sin título → duda", CV.parecido("Choque en la ruta 5", "texto", "")["veredicto"] == "duda")


# --- 2. controlar(): la IA mira lo dudoso; sin la IA, del lado seguro --------------------------------
class _Motor:
    def duration_seconds(self, clip):
        return 30.0


from reels import reel_bot as R  # noqa: E402
_motor_antes, _cuadro_antes = R.motor, R.cuadro_de_video
R.motor = lambda: _Motor()


def _cuadro(clip, salida, segundo=0.5):
    Path(salida).write_bytes(b"\xff\xd8jpg")
    return Path(salida)


R.cuadro_de_video = _cuadro
import tempfile  # noqa: E402
tmp = Path(tempfile.mkdtemp())
clip = tmp / "clip.mp4"
clip.write_bytes(b"video")

vistas = []


def ia_no(imgs, titulo, bajada, nombre, texto):
    vistas.append(len(imgs))
    return {"corresponde": False, "que_muestra": "un joven resolviendo cálculos frente a una cámara"}


def ia_si(imgs, titulo, bajada, nombre, texto):
    vistas.append(len(imgs))
    return {"corresponde": True, "que_muestra": "un corredor en una ruta"}


def ia_caida(*a):
    raise RuntimeError("se agotaron las claves")


r = CV.controlar(clip, "Un récord Guinness y 50 maratones en 22 días", "", "El atleta compartió en redes sociales",
                 "El joven matemático Aaryan Shukla resuelve cálculos en segundos. Compartió en redes sociales",
                 carpeta=tmp, mirar_fn=ia_no)
chequear("controlar: lo dudoso lo mira la IA con 3 cuadros; si dice que es otra cosa, el video no va",
         r["ok"] is False and r["via"] == "ia" and vistas == [3] and "otra cosa" in r["motivo"])
r = CV.controlar(clip, "Choque en la ruta 5", "Dos autos chocaron de frente", "", "", carpeta=tmp, mirar_fn=ia_si)
chequear("controlar: sin título del video (policiales), la IA dice que corresponde → va", r["ok"] and r["via"] == "ia")
r = CV.controlar(clip, "Choque en la ruta 5", "", "", "", carpeta=tmp, mirar_fn=ia_caida)
chequear("controlar: si la IA no contesta y no hay con qué comparar, el video no va (del lado seguro)",
         r["ok"] is False and "ia_error" in r)
r = CV.controlar(clip, "Rescataron a una yegua atada a un carro", "",
                 "La yegua llegó al Hospital Jaulas Vacías de Pelitos en el Corazón, donde la operaron del intestino",
                 "Hospital Jaulas Vacías - Pelitos en el Corazón", carpeta=tmp, mirar_fn=ia_caida)
chequear("controlar: sin la IA, lo dudoso que comparte mucho con el texto va igual",
         r["ok"] and r["via"] == "palabras (sin la IA)")
vistas.clear()
r = CV.controlar(clip, *MALOS[1][:2][:1], "", MALOS[1][1], MALOS[1][2], carpeta=tmp, mirar_fn=ia_si)
chequear("controlar: lo seguro por palabras no gasta la IA (el bebé con el médico de la Selección: no va)",
         r["ok"] is False and r["via"] == "palabras" and vistas == [])
os.environ["VIDEO_CONTROL"] = "0"
chequear("controlar: VIDEO_CONTROL=0 lo apaga", CV.controlar(clip, *MALOS[1][:1], "", "", MALOS[1][2])["ok"])
os.environ.pop("VIDEO_CONTROL")
R.motor, R.cuadro_de_video = _motor_antes, _cuadro_antes


# --- 3. La elección entre los videos de JW de la página --------------------------------------------------
class _JW:
    datos = {
        "DIBU0001": {"title": "El médico de la selección argentina habló sobre el estado de Dibu Martínez",
                     "playlist": [{"duration": 154, "description": "Daniel Martínez brindó detalles de la recuperación",
                                   "sources": [{"type": "video/mp4", "file": "https://cdn/dibu.mp4", "height": 720,
                                                "width": 1280}]}]},
        "BEBE0002": {"title": "Rescatan a un bebé enterrado vivo en una jaula para perros",
                     "playlist": [{"duration": 40, "sources": [{"type": "video/mp4", "file": "https://cdn/bebe.mp4",
                                                                "height": 720, "width": 1280}]}]},
    }

    def get(self, url):
        i = url.rsplit("/", 1)[1]
        return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: self.datos[i]})()


TIT = "Un bebé de 11 meses fue rescatado tras ser enterrado vivo en una jaula para perros"
TXT = "El niño fue hallado con vida en un bosque. Su padre fue arrestado. Las autoridades dieron detalles."
chequear("JW: si en la página solo está el video de la Selección, NO hay video (antes ganaba el primero)",
         PO.video_jw(["DIBU0001"], TIT, _JW(), TXT) == "")
e = PO.elegir_jw(["DIBU0001", "BEBE0002"], TIT, _JW(), TXT)
chequear("JW: con los dos, gana el de la nota aunque esté segundo, y queda su título para el control",
         e.get("file") == "https://cdn/bebe.mp4" and "bebé" in e.get("nombre", ""))

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
