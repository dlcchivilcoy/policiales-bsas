# -*- coding: utf-8 -*-
"""La volanta dice dónde OCURRIÓ el hecho, no la ciudad del medio (pedido del editor, 6/11/2026). Sin red.

Casos reales: la beba internada en Chivilcoy (medio de Junín) salió con volanta de Junín; la caída del
techo de la sede Chivilcoy de la Universidad Nacional de Luján salió con volanta de Luján; el asalto en
Solís quedó anotado como de Salto porque «asalto» contiene «salto».
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from reels import guion as G

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


def generar_con(respuesta, **nota):
    """generar() de verdad, con la respuesta de la IA armada a mano."""
    original = G.guion_ia
    G.guion_ia = lambda n, preferir="": dict(respuesta, descripcion="Texto del posteo.", hashtags=["#Policiales"])
    try:
        return G.generar(nota, sitio="sitio.com")
    finally:
        G.guion_ia = original


def lugar(localidad, certeza="explicita", partido="", provincia="Buenos Aires"):
    return {"localidad": localidad, "partido": partido, "provincia": provincia, "certeza": certeza}


# --- Antes de redactar: qué pueblo nombra la nota ---
chequear("un hecho de Chivilcoy contado por un medio de Junín es de Chivilcoy",
         G.localidad_de_la_nota({"titulo": "Chivilcoy: una beba fue internada", "localidad_medio": "Junín"})[0]
         == "Chivilcoy")
chequear("la Universidad Nacional de Luján no hace que el hecho sea de Luján",
         G.localidad_de_la_nota({"titulo": "Cayeron de un techo en la Universidad Nacional de Luján",
                                 "localidad_medio": "9 de Julio"})[0] == "9 de Julio")
chequear("la sede de Chivilcoy de la Universidad Nacional de Luján es de Chivilcoy",
         G.localidad_de_la_nota({"titulo": "Cayeron de un techo en la Universidad Nacional de Luján en Chivilcoy",
                                 "localidad_medio": "9 de Julio"})[0] == "Chivilcoy")
chequear("«asalto» no nombra a Salto",
         G.localidad_de_la_nota({"titulo": "Violento asalto a un comerciante",
                                 "localidad_medio": "San Andrés de Giles"})[0] == "San Andrés de Giles")
chequear("la DDI de Junín no hace que el hecho sea de Junín",
         G.localidad_de_la_nota({"titulo": "La DDI de Junín esclareció un robo en Chacabuco",
                                 "localidad_medio": "Bragado"})[0] == "Chacabuco")
chequear("nombrar dos pueblos no decide: queda la del medio",
         G.localidad_de_la_nota({"titulo": "Robaron en Chacabuco y cayeron en Junín",
                                 "localidad_medio": "Bragado"})[0] == "Bragado")

# --- Después de redactar: manda lo que la IA leyó en la nota ---
beba = {"titulo": "Una beba fue internada", "resumen": "Ingresó al Hospital Municipal de Chivilcoy.",
        "localidad_medio": "Junín"}
g = generar_con({"volanta": "Grave denuncia en Junín", "titular": "Beba internada por abuso",
                 "lugar_del_hecho": lugar("Chivilcoy", partido="Chivilcoy")}, **beba)
chequear("volanta con el pueblo del medio → se cambia por el del hecho", g["volanta"] == "Grave denuncia en Chivilcoy")
chequear("la etiqueta queda en el pueblo del hecho", g["localidad_hecho"] == "Chivilcoy")
chequear("el «Más noticias de» y el hashtag salen del pueblo del hecho",
         "Más noticias de Chivilcoy" in g["descripcion_final"] and "#Chivilcoy" in g["descripcion_final"]
         and "Junín" not in g["descripcion_final"])
chequear("queda el aviso de la corrección", "Chivilcoy" in g["aviso_localidad"])

unlu = {"titulo": "Dos jóvenes cayeron de un techo",
        "resumen": "Fue en la sede de la Universidad Nacional de Luján (UNLu) en Chivilcoy.",
        "localidad_medio": "9 de Julio"}
g = generar_con({"volanta": "Grave caída en Luján", "titular": "Un joven en terapia tras caer de un techo",
                 "lugar_del_hecho": lugar("Chivilcoy")}, **unlu)
chequear("la caída en la sede de la UNLu sale como de Chivilcoy",
         g["volanta"] == "Grave caída en Chivilcoy" and g["localidad_hecho"] == "Chivilcoy")

g = generar_con({"volanta": "Caída en la Universidad Nacional de Luján", "titular": "Un joven en terapia en Chivilcoy",
                 "lugar_del_hecho": lugar("Chivilcoy")}, **unlu)
chequear("el nombre de la universidad no se toca", g["volanta"] == "Caída en la Universidad Nacional de Luján")

g = generar_con({"volanta": "Junín: robo a una familia", "titular": "Robaron una casa",
                 "lugar_del_hecho": lugar("Chacabuco")},
                titulo="Robaron una casa", resumen="El hecho fue en Chacabuco.", localidad_medio="Junín")
chequear("el pueblo se cambia esté donde esté en la volanta", g["volanta"] == "Chacabuco: robo a una familia")

g = generar_con({"volanta": "Choque en la Ruta 5", "titular": "Un camión chocó a una máquina",
                 "lugar_del_hecho": lugar("Gowland", partido="Mercedes")},
                titulo="Choque en la Ruta 5", resumen="Ocurrió a la altura de Gowland.", localidad_medio="9 de Julio")
chequear("una volanta sin pueblo no se pisa", g["volanta"] == "Choque en la Ruta 5")
chequear("pero la etiqueta es la del hecho, no la del medio", g["localidad_hecho"] == "Gowland")

g = generar_con({"volanta": "Luces rojas en la ruta", "titular": "Un choque en Chacabuco",
                 "lugar_del_hecho": lugar("Chacabuco")},
                titulo="Un choque", resumen="Pasó en Chacabuco.", localidad_medio="Junín")
chequear("una palabra común no se confunde con un pueblo", g["volanta"] == "Luces rojas en la ruta")

# --- Cuándo NO se le hace caso a la IA ---
g = generar_con({"volanta": "Robo en Junín", "titular": "Robaron una casa",
                 "lugar_del_hecho": lugar("Junín", certeza="inferida")},
                titulo="Robaron una casa", resumen="Pasó en el barrio Belgrano.", localidad_medio="Junín")
chequear("medio local que habla de un barrio: sigue siendo de su ciudad",
         g["volanta"] == "Robo en Junín" and g["localidad_hecho"] == "Junín" and not g["aviso_localidad"])

g = generar_con({"volanta": "Robo en Junín", "titular": "Robaron una casa",
                 "lugar_del_hecho": lugar("Chacabuco")},
                titulo="Robaron una casa", resumen="Pasó en el barrio Belgrano.", localidad_medio="Junín")
chequear("un lugar que la nota no nombra no se acepta",
         g["volanta"] == "Robo en Junín" and g["localidad_hecho"] == "Junín")

g = generar_con({"volanta": "Robo en Junín", "titular": "Robaron una casa",
                 "lugar_del_hecho": lugar("la ciudad")},
                titulo="Robaron una casa", resumen="Pasó en la ciudad.", localidad_medio="Junín")
chequear("«la ciudad» no es un lugar", g["volanta"] == "Robo en Junín" and g["localidad_hecho"] == "Junín")

g = generar_con({"volanta": "Accidente en Junín", "titular": "Un piloto volcó",
                 "lugar_del_hecho": lugar("Sunchales", provincia="Santa Fe")},
                titulo="Un piloto volcó", resumen="Fue en Sunchales.", localidad_medio="Junín")
chequear("un hecho de otra provincia también dice dónde fue", g["volanta"] == "Accidente en Sunchales")

chequear("el prompt ya no manda a usar la localidad del material",
         "Usá la localidad que viene en el material" not in G.SYSTEM_PROMPT
         and "lugar_del_hecho" in G.SYSTEM_PROMPT.split("VOLANTA (el antetítulo naranja):")[1][:200])

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
