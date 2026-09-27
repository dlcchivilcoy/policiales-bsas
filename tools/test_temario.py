# -*- coding: utf-8 -*-
"""El filtro de temario: lo que la IA dice que no es policial no se publica. Sin red.

Nació el 27/09/2026, cuando salieron publicadas «Necrológicas de Chacabuco» y una alerta
meteorológica: el diccionario puntúa la página entera, con las notas del costado. (Las
alertas meteorológicas después pasaron a ser DEL temario, a pedido del editor.)
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from reels import flujo as F, guion as G, ia

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. Leer la respuesta de la IA ---------------------------------------------------
ft = G.fuera_de_temario
chequear("es del temario: no hay motivo", ft({"es_del_temario": True}) == "")
chequear("la IA no contestó el campo: la nota PASA (un olvido no cuesta un reel)", ft({}) == "")
chequear("no es del temario: devuelve el motivo que dio la IA",
         "fúnebres" in ft({"es_del_temario": False, "motivo": "Avisos fúnebres"}))
chequear("no es del temario y sin motivo: igual frena, con un motivo genérico",
         ft({"es_del_temario": False}) != "")
chequear("«false» como texto también frena", ft({"es_del_temario": "false"}) != "")
chequear("«true» como texto pasa", ft({"es_del_temario": "true"}) == "")
chequear("0 frena", ft({"es_del_temario": 0}) != "")

# --- 2. guion_ia lo deja en el guion -------------------------------------------------
respuesta = {"volanta": "Necrológicas de Chacabuco", "titular": "Los servicios fúnebres de la jornada en Chacabuco",
             "bajada": "Se informaron los sepelios del día en la ciudad y sus horarios.",
             "zocalo": "Servicios fúnebres", "pie": "Sepelio a las 16.",
             "descripcion": "Los sepelios del día.", "hashtags": ["#Chacabuco"]}
original = ia.redactar
try:
    ia.redactar = lambda *a, **k: (dict(respuesta, es_del_temario=False,
                                         motivo="avisos fúnebres"), "gemini:falso")
    g = G.guion_ia({"titulo": "Necrológicas de Chacabuco", "localidad": "chacabuco"})
    chequear("guion_ia: una necrológica sale marcada fuera de temario",
             "fúnebres" in g.get("fuera_de_temario", ""))
    ia.redactar = lambda *a, **k: (dict(respuesta, es_del_temario=True), "gemini:falso")
    g = G.guion_ia({"titulo": "Robaron una moto", "localidad": "junin"})
    chequear("guion_ia: la nota policial sale sin marca", g.get("fuera_de_temario") == "")
finally:
    ia.redactar = original

# --- 3. El flujo: no la publica y no le arma video -----------------------------------
armados = []
reemplazos = {
    "_bajar_video": lambda url, destino: None,
    "_bajar_foto": lambda url, destino: destino,
    "material": lambda nota: nota,
}
guardados = {k: getattr(F, k) for k in reemplazos}
armar, generar = F.R.armar, F.G.generar


def generar_falso(motivo):
    def _g(nota, **k):
        return {"volanta": "Necrológicas de Chacabuco", "titular": "Los servicios fúnebres de la jornada en Chacabuco",
                "bajada": "Se informaron los sepelios del día en la ciudad y sus horarios.",
                "zocalo": "Alerta", "pie": "Rige.", "via": "gemini:falso", "tipo": "otro_policial",
                "descripcion_final": "Texto", "fuera_de_temario": motivo}
    return _g


try:
    for k, v in reemplazos.items():
        setattr(F, k, v)
    F.R.armar = lambda g, salida, **k: armados.append(salida) or {"duracion": 13, "peso_kb": 120, "tramos": ["nota"]}
    carpeta = Path(tempfile.mkdtemp(prefix="temario_"))
    nota = {"titulo": "Necrológicas de Chacabuco", "localidad_medio": "Chacabuco",
            "url": "https://medio.test/alerta", "imagen": "https://medio.test/a.jpg"}

    F.G.generar = generar_falso("avisos fúnebres")
    p = F.procesar(nota, carpeta, True, 1)
    chequear("flujo: fuera de temario → NO apta para publicar", p["apto_para_publicar"] is False)
    chequear("flujo: el motivo queda escrito en por_que_no", "temario" in p["por_que_no"]
             and "fúnebres" in p["por_que_no"])
    chequear("flujo: no se le arma el video (no se va a publicar)", armados == [])

    F.G.generar = generar_falso("")
    p = F.procesar(dict(nota, url="https://medio.test/robo"), carpeta, True, 2)
    chequear("flujo: del temario → apta y con video", p["apto_para_publicar"] is True and len(armados) == 1)
finally:
    for k, v in guardados.items():
        setattr(F, k, v)
    F.R.armar, F.G.generar = armar, generar

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
