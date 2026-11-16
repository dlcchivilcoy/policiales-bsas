# -*- coding: utf-8 -*-
"""Los medios de la competencia (reels/competencia.py) y la volanta de la portada de policiales, sin red.

    venv\\Scripts\\python.exe tools\\test_competencia.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from reels import competencia as C  # noqa: E402
from reels import flujo as FL  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


SI = {
    "Fuente: La Razón": "La Razón de Chivilcoy",
    "Foto: Diario La Razón de Chivilcoy": "La Razón de Chivilcoy",
    "según informó el diario La Razón, el joven…": "La Razón de Chivilcoy",
    "(Foto: La Razón)": "La Razón de Chivilcoy",
    "https://www.larazondechivilcoy.com.ar/policiales/123": "La Razón de Chivilcoy",
    "Gentileza: La Gaceta del Oeste": "La Gaceta del Oeste",
    "https://dechivilcoy.com.ar/nota": "DeChivilcoy",
    "Imagen: Chivilcoy al Día": "Chivilcoy al Día",
}
chequear("encuentra a los cuatro medios por su nombre, su dominio o como fuente o crédito",
         all(C.en_texto(t) == m for t, m in SI.items()))
NO = ("La razón por la que chocó todavía se investiga", "Un joven de Chivilcoy murió en un choque",
      "Tenía razón el vecino: la luz estaba apagada", "Chivilcoy: el día después del temporal")
chequear("«la razón» suelta, «de Chivilcoy» o «Chivilcoy … día» no cuentan", not any(C.en_texto(t) for t in NO))
nota = {"url": "https://junin24.com/noticias/chivilcoy-un-joven", "titulo": "Chivilcoy: un joven murió",
        "cuerpo": "El hecho ocurrió el martes. Fuente: La Razón de Chivilcoy.", "imagen": "https://x/y.jpg"}
chequear("de_la_nota mira el texto completo de la nota", C.de_la_nota(nota) == "La Razón de Chivilcoy")

tmp = Path(tempfile.mkdtemp())
foto = tmp / "f.jpg"
foto.write_bytes(b"\xff\xd8\xff")
chequear("la marca «LA RAZON» en la imagen es La Razón de Chivilcoy",
         C.en_imagen([foto], preguntar=lambda r: {"medio": "LA RAZON"}) == "La Razón de Chivilcoy")
chequear("sin marca: nada", C.en_imagen([foto], preguntar=lambda r: {"medio": ""}) == "")
chequear("otro logo (TN) no cuenta", C.en_imagen([foto], preguntar=lambda r: {"medio": "TN"}) == "")
chequear("si la IA no contesta, la pieza sigue", C.en_imagen([foto], preguntar=lambda r: 1 / 0) == "")
chequear("sin imágenes no se pregunta", C.en_imagen([None, tmp / "no.jpg"], preguntar=lambda r: 1 / 0) == "")
os.environ["COMPETENCIA_IMAGEN"] = "0"
chequear("COMPETENCIA_IMAGEN=0 apaga el control de la imagen",
         C.en_imagen([foto], preguntar=lambda r: {"medio": "LA RAZON"}) == "")
os.environ.pop("COMPETENCIA_IMAGEN")

# --- la volanta de la portada de policiales -------------------------------------------------------------
v = FL.volanta_de_portada
chequear("«Junín: un repartidor…» con volanta que ya dice Junín: el título sin «Junín:» y con mayúscula",
         v("Violento asalto en Junín", "Junín: un repartidor se defendió") == ("Violento asalto en Junín",
                                                                              "Un repartidor se defendió"))
chequear("si la volanta no dice el lugar, el lugar va adelante en la volanta",
         v("Operativo antidrogas", "Chacabuco: detuvieron a un hombre") == ("Chacabuco · Operativo antidrogas",
                                                                            "Detuvieron a un hombre"))
chequear("sin «Lugar:» en el título, queda igual",
         v("Choque fatal en Alberti", "Murió un conductor en la Ruta 5") == ("Choque fatal en Alberti",
                                                                             "Murió un conductor en la Ruta 5"))
chequear("la volanta nunca termina en dos puntos", v("Chivilcoy:", "Un hecho")[0] == "Chivilcoy")
chequear("una frase larga antes de los dos puntos no es un lugar",
         v("Juicio", "El fiscal pidió una pena ejemplar para los acusados: 20 años")[1].startswith("El fiscal"))

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
