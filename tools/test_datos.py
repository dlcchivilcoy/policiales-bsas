# -*- coding: utf-8 -*-
"""Que el guion no se coma los datos de la nota (pedido del editor, 10/10/2026: «no obviar
nombres, edades, lugares o info crucial»). Sin red: la IA y la descarga se reemplazan.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from reels import flujo as F, guion as G, ia

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. Qué falta --------------------------------------------------------------------------
g = {"titular": "Murió un hombre de 74 años en un choque en la Ruta 5",
     "bajada": "El conductor del Renault Logan fue trasladado al Hospital Municipal.",
     "descripcion": "", "titulo_web": "",
     "nota_web": "Un hombre de 74 años murió tras chocar su Ford Ka contra un Renault Logan en la Ruta "
                 "Nacional 5, a la altura del kilómetro 262.",
     "datos_clave": ["74 años", "Ford Ka y Renault Logan", "kilómetro 262", "Hospital Municipal",
                     "Juan Pérez", "kilómetro 263"]}
chequear("faltan: detecta el nombre que no está y el kilómetro equivocado",
         G.datos_faltantes(g) == ["Juan Pérez", "kilómetro 263"])
chequear("faltan: los vehículos en otro orden y con artículos cuentan como presentes",
         "Ford Ka y Renault Logan" not in G.datos_faltantes(g))
chequear("faltan: sin datos_clave no falta nada", G.datos_faltantes(dict(g, datos_clave=[])) == [])

# --- 1b. Los datos exactos no cuentan como copia --------------------------------------------
orig = G._palabras("El caso quedó en manos de la Fiscalía de Responsabilidad Penal Juvenil Nº 12 del "
                   "Departamento Judicial Junín, que imputó al joven por hurto agravado por escalamiento.")
pub = {"nota_web": "Interviene la Fiscalía de Responsabilidad Penal Juvenil Nº 12 del Departamento Judicial "
                   "Junín, que imputó al joven por hurto agravado por escalamiento."}
sin = G.copia_del_original(pub, orig)["racha"]
con = G.copia_del_original(dict(pub, datos_clave=["Fiscalía de Responsabilidad Penal Juvenil Nº 12",
                                                  "Departamento Judicial Junín",
                                                  "hurto agravado por escalamiento"]), orig)["racha"]
chequear(f"copia: el nombre de la fiscalía y la carátula no cuentan como copia ({sin} → {con})",
         sin >= 15 and con < 10)
largo = "que imputó al joven por hurto agravado por escalamiento y lo notificó en su casa"
chequear("copia: una oración entera listada como «dato» (más de 8 palabras) no se salva",
         G._sin_datos(G._palabras(largo), [largo]) == G._palabras(largo))

# --- 2. El segundo pedido, con la lista ---------------------------------------------------
pedidos = []
NOTA_WEB = ("Un hombre de 74 años murió en la Ruta 5. " * 4 + "\n\n") * 2


def redactar(respuestas):
    def r(system, material, preferir=""):
        pedidos.append((system, material))
        return dict(respuestas.pop(0)), "falso"
    return r


base = {"es_del_temario": True, "volanta": "Choque en 9 de Julio", "titular": "Murió un hombre en la Ruta 5",
        "bajada": "Fue en el kilómetro 262.", "zocalo": "Choque en Ruta 5", "pie": "x.",
        "descripcion": "Uno. Dos.", "hashtags": ["#Choque"], "potencial_viral": 8,
        "titulo_web": "9 de Julio: murió un hombre en la Ruta 5", "nota_web": NOTA_WEB,
        "datos_clave": ["74 años", "Ruta 5", "Carlos Gómez"]}
completa = dict(base, nota_web=NOTA_WEB + "\n\nEl conductor fue identificado como Carlos Gómez.")
nota = {"titulo": "Tragedia en la Ruta 5", "localidad_medio": "9 de julio", "localidad": "9 de julio",
        "resumen": "Un muerto en la Ruta 5.",
        "texto_completo": "Un hombre de 74 años, identificado como Carlos Gómez, murió esta madrugada en la "
                          "Ruta Nacional 5 al chocar su Ford Ka contra un Renault Logan."}
original = ia.redactar
try:
    ia.redactar = redactar([base, completa])
    out = G.guion_ia(nota)
    chequear("la IA recibe el TEXTO COMPLETO de la nota, no solo el resumen",
             "Carlos Gómez" in pedidos[0][1] and "Ford Ka" in pedidos[0][1])
    chequear("si se comió un dato, hay segundo pedido con la lista de lo que falta",
             len(pedidos) == 2 and "«Carlos Gómez»" in pedidos[1][0] and "iniciales de un menor de 18" in pedidos[1][0])
    chequear("...y queda la versión completa", out["faltan_datos"] == [] and "Carlos Gómez" in out["nota_web"])
    pedidos.clear()
    ia.redactar = redactar([completa])
    out = G.guion_ia(nota)
    chequear("si no falta nada, un solo pedido", len(pedidos) == 1 and out["datos_clave"] == base["datos_clave"])
    pedidos.clear()
    ia.redactar = redactar([base, base])
    out = G.guion_ia(nota)
    chequear("si el segundo pedido tampoco los pone, queda anotado lo que falta",
             out["faltan_datos"] == ["Carlos Gómez"])
finally:
    ia.redactar = original

# --- 3. flujo.material baja el texto completo aunque el RSS traiga resumen ------------------
original_detalle = F.fetch.detalle
try:
    F.fetch.detalle = lambda url, permitir_navegador=False: {
        "ok": True, "descripcion": "Corto.", "cuerpo": "El texto completo de la nota con todos los datos."}
    m = F.material({"url": "https://x", "resumen": "Resumen del RSS."})
    chequear("material: con resumen del RSS, igual trae el texto completo (y deja el resumen)",
             m["texto_completo"].startswith("El texto completo") and m["resumen"] == "Resumen del RSS.")
    m = F.material({"url": "https://x"})
    chequear("material: sin resumen, sigue como antes y además trae el texto completo",
             m["cuerpo"] and m["texto_completo"].startswith("El texto completo"))
    F.fetch.detalle = lambda url, permitir_navegador=False: {"ok": False}
    chequear("material: si la página no contesta, la nota sigue igual",
             F.material({"url": "https://x", "resumen": "R"}) == {"url": "https://x", "resumen": "R"})
finally:
    F.fetch.detalle = original_detalle

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
