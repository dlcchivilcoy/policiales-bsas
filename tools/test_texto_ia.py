# -*- coding: utf-8 -*-
"""La descripción no sale con corchetes (12/10/2026): a veces la IA contesta una LISTA de
oraciones donde se pidió un texto, y se publicaba «['Una frase.', 'Otra.']». Sin red."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from reels import guion as G  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# El posteo real del 12/10 (Bragado, la Hilux de la Fiesta del Caballo), recortado.
FRASES = ["Delincuentes se llevaron una camioneta Toyota Hilux negra en Bragado durante la Fiesta del Caballo.",
          "El rodado había sido estacionado el sábado a las 21:30 en la calle Macaya.",
          "La denuncia quedó radicada en la UFIyJ N.º 2 del departamento judicial de Mercedes."]

chequear("una lista se une como texto", G.texto_ia(FRASES) == " ".join(FRASES))
chequear("una lista que llegó pegada como texto («['…', '…']») también se desarma",
         G.texto_ia(str(FRASES)) == " ".join(FRASES))
chequear("un texto con corchetes de verdad adentro no se toca",
         G.texto_ia("La causa [IPP 123] sigue abierta.") == "La causa [IPP 123] sigue abierta.")
chequear("vacío y None dan texto vacío", G.texto_ia(None) == "" and G.texto_ia([]) == "")

datos = {"volanta": "Bragado · Robo", "titular": "Robaron una camioneta durante la Fiesta del Caballo",
         "bajada": "Delincuentes se llevaron una Hilux estacionada en la calle Macaya.",
         "descripcion": FRASES, "nota_web": ["Primer párrafo de la nota. " + FRASES[0] + " " + FRASES[1],
                                             "Segundo párrafo de la nota. " + FRASES[2]],
         "hashtags": ["#RoboDeAutos"]}
salida = G._salida_ia(datos, "gemini:prueba", {"titulo": "Robo", "localidad": "Bragado"})
chequear("guion: la descripción en lista queda como texto, sin corchetes",
         "[" not in salida["descripcion"] and "'" not in salida["descripcion"][:2])
chequear("guion: la nota web en lista queda en párrafos", "[" not in salida["nota_web"]
         and salida["nota_web"].startswith("Primer párrafo") and "\n\nSegundo párrafo" in salida["nota_web"])
texto = G.descripcion_tiktok(salida, {"localidad": "Bragado"}, "www.diariolacampaña.com.ar")
chequear("el posteo sale en párrafos, sin corchetes ni comillas",
         "[" not in texto and "']" not in texto and texto.startswith("Delincuentes se llevaron")
         and "\n\nEl rodado" in texto)
viejo = G.descripcion_tiktok({"descripcion": str(FRASES), "hashtags": []}, {"localidad": "Bragado"})
chequear("y si algo llega con la lista pegada hasta el final, el posteo igual sale limpio",
         "[" not in viejo and viejo.startswith("Delincuentes"))

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
