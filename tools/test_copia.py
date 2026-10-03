# -*- coding: utf-8 -*-
"""Que no se note la copia: sin la fuente y sin frases calcadas del medio. Sin red.

Nació el 03/10/2026, a pedido del editor: «sacá la fuente de las webs en los reels y
descripción y rearmá la info de tal manera que no se note la copia». Medido ese día sobre
9 reels publicados: 3 arrastraban tramos de 10 a 14 palabras iguales a la nota original.
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


# El caso real del 03/10 (La Opinión de Pergamino, el asalto al juez federal).
ORIGINAL = ("La pesquisa por el violento robo al magistrado federal sumó nuevos procedimientos en "
            "San Pedro, Río Tala y La Tosquera en busca de elementos sustraídos. Según informó "
            "la fiscalía, no hubo detenidos.")
NOTA = {"titulo": "Nuevos allanamientos por el asalto al juez", "resumen": ORIGINAL,
        "localidad": "pergamino", "localidad_medio": "Pergamino", "medio": "La Opinión (Pergamino)"}

COPIADO = {"es_del_temario": True, "volanta": "Investigación en Pergamino",
           "titular": "Nuevos allanamientos por el robo al juez federal",
           "bajada": "Hubo procedimientos en San Pedro, Río Tala y La Tosquera en busca de "
                     "elementos sustraídos al magistrado.",
           "zocalo": "Robo al juez", "pie": "Siguen los operativos.",
           "descripcion": "La causa sumó operativos en tres localidades.",
           "titulo_web": "Pergamino: nuevos allanamientos por el robo al juez federal",
           "nota_web": "La investigación sigue abierta y por ahora no hay personas detenidas. " * 5}
REESCRITO = dict(COPIADO, bajada="Los investigadores revisaron casas de tres pueblos de la zona "
                                 "para recuperar lo que se llevaron del domicilio del juez.")

# --- 1. Medir la copia --------------------------------------------------------------
orig = G._palabras(ORIGINAL)
n, tramo = G.tramo_copiado(COPIADO["bajada"], orig)
chequear("tramo_copiado: encuentra el tramo calcado (14 palabras)",
         n == 14 and tramo.startswith("procedimientos en san pedro rio tala"))
chequear("tramo_copiado: lo reescrito no tiene tramos largos", G.tramo_copiado(REESCRITO["bajada"], orig)[0] < 5)
chequear("tramo_copiado: ignora tildes y mayúsculas",
         G.tramo_copiado("SAN PEDRO, RÍO TALA y LA TOSQUERA", orig)[0] == 7)
c = G.copia_del_original(COPIADO, orig)
chequear("copia_del_original: dice el campo y el tramo", c["campo"] == "bajada" and c["racha"] == 14)

# --- 2. El nombre del medio --------------------------------------------------------
chequear("nombra_medio: «La Opinión (Pergamino)» es artículo + palabra: no se busca por código "
         "(lo frena el prompt)",
         not G._nombra_medio("Según publicó La Opinión, hubo allanamientos.", "La Opinión (Pergamino)"))
chequear("nombra_medio: «Diario Democracia» se detecta",
         G._nombra_medio("Lo publicó el Diario Democracia esta mañana.", "Diario Democracia"))
chequear("nombra_medio: «Junín Digital» se detecta",
         G._nombra_medio("Según informó Junín Digital, el conductor murió.", "Junín Digital"))
chequear("nombra_medio: «La Mañana» NO se busca (daría «durante la mañana»)",
         not G._nombra_medio("Ocurrió durante la mañana del sábado.", "La Mañana (25 de Mayo)"))
chequear("nombra_medio: un nombre de una palabra no se busca",
         not G._nombra_medio("Un vecino chacabuquero hizo la denuncia.", "Chacabuquero"))

# --- 3. La descripción del posteo -------------------------------------------------------
g = dict(REESCRITO, hashtags=["#Robo"], descripcion="Los investigadores revisaron casas de tres pueblos.")
desc = G.descripcion_tiktok(g, NOTA, sitio="www.diariolacampaña.com.ar")
chequear("descripción: sin «Fuente»", "Fuente" not in desc and "📰" not in desc)
chequear("descripción: sin el nombre del medio", "Opinión" not in desc)
chequear("descripción: sigue el link a la web y los hashtags",
         "Más noticias de Pergamino en www.diariolacampaña.com.ar" in desc and "#Pergamino" in desc)

# --- 4. guion_ia: material sin el medio y segundo pedido si copió --------------------------
pedidos = []
original_redactar = ia.redactar


def falso(*respuestas):
    cola = list(respuestas)

    def _r(system, material, preferir=""):
        pedidos.append((system, material))
        return dict(cola.pop(0) if len(cola) > 1 else cola[0]), "gemini:falso"
    return _r


try:
    ia.redactar = falso(REESCRITO)
    g = G.guion_ia(NOTA)
    chequear("guion_ia: al modelo NO le llega el nombre del medio",
             "Opinión" not in pedidos[0][1] and "Medio:" not in pedidos[0][1])
    chequear("guion_ia: texto propio → un solo pedido", len(pedidos) == 1 and g["copia"]["racha"] < G.UMBRAL_COPIA)

    pedidos.clear()
    ia.redactar = falso(COPIADO, REESCRITO)
    g = G.guion_ia(NOTA)
    chequear("guion_ia: copió → se pide de nuevo", len(pedidos) == 2)
    chequear("guion_ia: el segundo pedido muestra el tramo copiado (en el SYSTEM, no en el material)",
             "SEGUNDO PEDIDO" in pedidos[1][0] and "san pedro rio tala" in pedidos[1][0]
             and "SEGUNDO PEDIDO" not in pedidos[1][1])
    chequear("guion_ia: queda la versión reescrita", g["bajada"] == REESCRITO["bajada"])

    pedidos.clear()
    ia.redactar = falso(REESCRITO, COPIADO)
    g = G.guion_ia(dict(NOTA, medio="Junín Digital"))
    chequear("guion_ia: sin copia no hay segundo pedido aunque el medio tenga nombre largo", len(pedidos) == 1)

    pedidos.clear()
    nombra = dict(REESCRITO, descripcion="Según informó Junín Digital, hubo operativos.")
    ia.redactar = falso(nombra, REESCRITO)
    g = G.guion_ia(dict(NOTA, medio="Junín Digital"))
    chequear("guion_ia: nombró al medio → segundo pedido y queda la versión sin el nombre",
             len(pedidos) == 2 and "Nombraste al medio" in pedidos[1][0]
             and not g["copia"]["nombra_medio"])

    pedidos.clear()
    ia.redactar = falso(COPIADO, COPIADO)
    g = G.guion_ia(NOTA)
    chequear("guion_ia: si vuelve a copiar, queda anotado cuánto", g["copia"]["racha"] == 14)

    # Un campo que la IA deja vacío se rellena con el texto del medio: eso también se mide.
    pedidos.clear()
    vacio = dict(REESCRITO, bajada="")
    ia.redactar = falso(vacio, REESCRITO)
    g = G.guion_ia(NOTA)
    chequear("guion_ia: el relleno con texto del medio cuenta como copia y se pide de nuevo",
             len(pedidos) == 2 and g["bajada"] == REESCRITO["bajada"])
finally:
    ia.redactar = original_redactar

# --- 5. El titular recortado no queda colgando (caso real del 03/10) ----------------
largo = "Un joven murió y otros dos resultaron heridos tras un choque entre un camión y una camioneta"
chequear("titular recortado: no termina en «y una»",
         G._acortar(largo, 90) == "Un joven murió y otros dos resultaron heridos tras un choque entre un camión")
chequear("titular que entra: no se toca", G._acortar("Robaron una moto en Junín", 90) == "Robaron una moto en Junín")

# --- 6. El flujo: con 15 o más palabras calcadas no se publica -----------------------
reemplazos = {
    "_bajar_video": lambda url, destino: None,
    "_bajar_foto": lambda url, destino: destino,
    "_foto_usable": lambda nota, destino: (destino, nota.get("imagen") or "", ""),
    "material": lambda nota: nota,
}
guardados = {k: getattr(F, k) for k in reemplazos}
armar, generar = F.R.armar, F.G.generar


def generar_con(copia):
    def _g(nota, **k):
        return {"volanta": "Robo en Pergamino", "titular": "Allanamientos por el robo al juez federal",
                "bajada": "Los investigadores revisaron casas de tres pueblos de la zona.",
                "zocalo": "Robo", "pie": "Siguen.", "via": "gemini:falso", "tipo": "robo",
                "descripcion_final": "Texto", "fuera_de_temario": "", "copia": copia}
    return _g


try:
    for k, v in reemplazos.items():
        setattr(F, k, v)
    F.R.armar = lambda g, salida, **k: {"duracion": 13, "peso_kb": 120, "tramos": ["nota"]}
    carpeta = Path(tempfile.mkdtemp(prefix="copia_"))
    nota = {"titulo": "Allanamientos", "localidad_medio": "Pergamino",
            "url": "https://medio.test/juez", "imagen": "https://medio.test/a.jpg"}

    F.G.generar = generar_con({"racha": 16, "tramo": "la pesquisa por el violento robo",
                               "campo": "bajada", "nombra_medio": False})
    p = F.procesar(nota, carpeta, True, 1)
    chequear("flujo: 16 palabras calcadas → NO apta, con el motivo",
             p["apto_para_publicar"] is False and "copia 16 palabras" in p["por_que_no"])

    F.G.generar = generar_con({"racha": 11, "tramo": "en san pedro rio tala",
                               "campo": "nota_web", "nombra_medio": True})
    p = F.procesar(dict(nota, url="https://medio.test/juez2"), carpeta, True, 2)
    chequear("flujo: 11 palabras → sale, con aviso (y aviso si nombra al medio)",
             p["apto_para_publicar"] is True and any("11 palabras" in a for a in p["avisos"])
             and any("medio de origen" in a for a in p["avisos"]))
    chequear("flujo: la medición queda en la pieza", p.get("copia", {}).get("racha") == 11)
finally:
    for k, v in guardados.items():
        setattr(F, k, v)
    F.R.armar, F.G.generar = armar, generar

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
