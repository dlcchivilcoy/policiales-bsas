# -*- coding: utf-8 -*-
"""El circuito agro en simulación (13/10/2026). Sin red: la IA, los feeds y las imágenes son de mentira.

    venv\\Scripts\\python.exe tools\\test_agro.py
"""
import os
# Las pruebas de siempre corren con las imágenes IA prendidas; la regla del 18/10/2026 (sin IA, sin foto
# real no sale) se prueba al final con AGRO_IMAGEN_IA=0.
os.environ["AGRO_IMAGEN_IA"] = "1"
import sys
# Las pruebas de selección fijan el mínimo viejo (75): prueban la mecánica, no el valor (desde el
# 20/10/2026 el de fábrica es 60; se prueba más abajo).
os.environ["AGRO_SCORE_MIN"] = "75"
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from agro import captura as CA  # noqa: E402
from agro import dedup as DD  # noqa: E402
from agro import guion as GU  # noqa: E402
from agro import imagen as IMG  # noqa: E402
from agro import pasada as PA  # noqa: E402
from agro import scoring as SC  # noqa: E402
from agro import seleccion as SE  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


def nota(i, titulo, desc="", fuente="Infocampo", tipo="medio"):
    url = f"https://www.infocampo.com.ar/nota-{i}/"
    return {"id": CA.id_de(url), "fuente": fuente, "tipo_fuente": tipo, "url": url,
            "canonical_url": CA.canonica(url), "titulo": titulo, "titulo_norm": CA.normalizar_titulo(titulo),
            "descripcion": desc, "hash": CA.huella(titulo, desc), "publicado": "2026-10-13T10:00:00-03:00"}


# --- captura ---------------------------------------------------------------------------------
chequear("canonica saca rastreadores, www y barra final",
         CA.canonica("https://WWW.Infocampo.com.ar/nota/?utm_source=fb&id=3&fbclid=x#arriba")
         == "https://infocampo.com.ar/nota?id=3")
chequear("normalizar_titulo sin tildes ni signos",
         CA.normalizar_titulo("¡Récord de exportación de maíz!") == "record de exportacion de maiz")
chequear("misma URL con y sin utm → mismo id",
         CA.id_de("https://a.com/x?utm_medium=rss") == CA.id_de("https://www.a.com/x/"))

# --- tableros automáticos --------------------------------------------------------------------
for t, esperado in (("Precio del Trigo en Rosario hoy 13 octubre 2026", True),
                    ("Dólar BLUE HOY: a cuánto cotiza el 13 octubre 2026", True),
                    ("Clima en San Luis hoy 13 octubre 2026", True),
                    ("Riesgo país hoy 9 de octubre", True),
                    ("Soja en Chicago: cae a US$ 12,82 por bushel", False),
                    ("Retenciones: la recaudación saltó 49,5% real en septiembre", False)):
    chequear(f"tablero {esperado}: {t}", PA.es_tablero({"titulo": t}) is esperado)

# --- duplicados ------------------------------------------------------------------------------
mem = {}
a = nota(1, "El INTA investiga la mostaza para reducir agroquímicos", "Ensayos con mostaza como cultivo de servicio")
chequear("nota nueva no está vista", DD.ya_vista(a, mem) == "")
DD.anotar(a, mem)
chequear("misma URL → vista", DD.ya_vista(dict(a), mem) != "")
otra_url = dict(a, canonical_url="https://otro.com/x", hash="zzz")
chequear("mismo título en otra URL → vista", "título" in DD.ya_vista(otra_url, mem))

viejo = {"indice": {"url": {"u1": "2026-09-30", "u2": "2026-10-12"}, "titulo": {}, "hash": {"h1": "2026-09-30", "h2": "2026-10-12"}},
         "scores": {"h1": {"ai_score": 80}, "h2": {"ai_score": 70}}}
DD.olvidar_viejas(viejo, "2026-10-03")
chequear("el índice y los puntajes olvidan lo de hace más de 10 días",
         list(viejo["indice"]["url"]) == ["u2"] and list(viejo["scores"]) == ["h2"])
chequear("anotar guarda la fecha en que se vio la nota",
         DD.anotar(dict(a, capturado="2026-10-13T10:00-03:00"), m2 := {}) is None and set(m2["indice"]["url"].values()) == {"2026-10-13"})
b = nota(2, "Mostaza contra los agroquímicos: el INTA investiga una alternativa",
         "El INTA ensaya la mostaza como cultivo de servicio para reducir agroquímicos", "Agrositio")
c = nota(3, "Pick-ups chinas: radiografía por marca y modelo", "El mercado de camionetas chinas acelera")
d = nota(4, "Remolacha forrajera: buena calidad nutricional y menor costo", "Para la hacienda en invierno")
r = DD.agrupar([a, b, c, d], [], usar_ia=False)
juntos = [g for g in r["grupos"] if len(g) == 2]
chequear("las dos de la mostaza se agrupan por palabras",
         len(juntos) == 1 and {n["id"] for n in juntos[0]} == {a["id"], b["id"]})
chequear("las otras quedan solas", len(r["grupos"]) == 3)


def ia_agrupa(system, material, **kw):
    return {"grupos": [[1, 2]]}, "falsa"


r = DD.agrupar([c, d], [], redactar=ia_agrupa, usar_ia=True)
chequear("sin parecido por palabras la IA ni se consulta", len(r["grupos"]) == 2 and r["ia"] is None)
r = DD.agrupar([b], [a], usar_ia=False)
chequear("la misma noticia ya elegida otro día → repetida", b["id"] in r["repetidas"] and not r["grupos"])
chequear("representante: oficial antes que medio",
         DD.representante([a, dict(b, tipo_fuente="oficial")])["id"] == b["id"])

# --- puntaje ---------------------------------------------------------------------------------
s = SC.limpiar({"impacto_economico": 99, "interes_productores": "12", "innovacion": -4, "cercania_argentina": 10,
                "cercania_pba": 10, "potencial_reel": 7.6, "conversacion": None, "potencial_comercial": 10,
                "commercial_score": 140, "subtema": "Ganadería", "sensible": "sí", "ambito": "Internacional"})
chequear("limpiar aplica los topes y suma", s["impacto_economico"] == 20 and s["innovacion"] == 0
         and s["potencial_reel"] == 8 and s["ai_score"] == 20 + 12 + 0 + 10 + 10 + 8 + 0 + 10)
chequear("limpiar: commercial ≤ 100, subtema sin tilde, sensible y ámbito",
         s["commercial_score"] == 100 and s["subtema"] == "ganaderia" and s["sensible"]
         and s["ambito"] == "internacional")
chequear("subtema desconocido → agro", SC.limpiar({"subtema": "deportes"})["subtema"] == "agro")

pedidos = []


def ia_puntua(system, material, **kw):
    pedidos.append(material)
    return {"notas": [{"n": 1, "impacto_economico": 20, "subtema": "agro"},
                      {"n": 3, "impacto_economico": 5, "subtema": "mercados"}]}, "falsa"


cache = {}
p = SC.puntuar([a, c, d], cache, redactar=ia_puntua, log=lambda m: None)
chequear("puntuar: la nota que la IA no devolvió queda sin puntaje", set(p) == {a["id"], d["id"]})
p2 = SC.puntuar([a, d], cache, redactar=ia_puntua, log=lambda m: None)
chequear("puntuar: lo ya puntuado sale del caché sin llamar a la IA",
         len(pedidos) == 1 and all(v.get("cache") for v in p2.values()))



def puntaje_ia(total):
    """Un puntaje de la IA que suma `total` (repartido en los criterios, sin pasar los topes)."""
    d, resto = {}, total
    for c, tope in SC.CRITERIOS.items():
        d[c] = min(tope, resto)
        resto -= d[c]
    return d


llamadas_p = []


def ia_doble(por_vuelta):
    """La IA de mentira: en cada llamada devuelve, para cada nota, el total que diga `por_vuelta`
    según su título y el número de vuelta (1ª o 2ª vez que la ve)."""
    vistas = {}

    def redactar(system, material, **kw):
        llamadas_p.append(material)
        notas = []
        for i, bloque in enumerate(material.split("\n\n")):
            titulo = bloque.split("Título: ")[1].split("\n")[0]
            vistas[titulo] = vistas.get(titulo, 0) + 1
            notas.append(dict(puntaje_ia(por_vuelta[titulo][vistas[titulo] - 1]), n=i + 1, subtema="agro",
                              sensible=vistas[titulo] == 2 and titulo == "Cerca"))
        return {"notas": notas}, "falsa"
    return redactar


lejos, cerca_ = nota(60, "Lejos", "x"), nota(61, "Cerca", "y")
llamadas_p.clear()
cache2 = {}
p = SC.puntuar([lejos, cerca_], cache2, redactar=ia_doble({"Lejos": [92], "Cerca": [78, 60]}),
               log=lambda m: None, minimo=75, margen=10)
chequear("doble puntaje: solo la que quedó cerca del corte (78) se vuelve a puntuar, sola en otra tanda",
         len(llamadas_p) == 2 and "Cerca" in llamadas_p[1] and "Lejos" not in llamadas_p[1])
chequear("doble puntaje: 78 y 60 → se promedia criterio por criterio (69, queda afuera)",
         p[cerca_["id"]]["dobles"] == [78, 60] and p[cerca_["id"]]["ai_score"] == 69)
chequear("doble puntaje: la de 92 no cambia ni se repite", p[lejos["id"]]["ai_score"] == 92
         and "dobles" not in p[lejos["id"]])
chequear("doble puntaje: «sensible» si cualquiera de las dos vueltas lo vio", p[cerca_["id"]]["sensible"])
llamadas_p.clear()
SC.puntuar([lejos, cerca_], cache2, redactar=ia_doble({"Lejos": [92], "Cerca": [78, 60]}),
           log=lambda m: None, minimo=75, margen=10)
chequear("doble puntaje: lo ya promediado sale del caché sin otra llamada", not llamadas_p)
cache3 = {cerca_["hash"]: dict(SC.limpiar(puntaje_ia(80)), via="vieja")}
llamadas_p.clear()
p = SC.puntuar([cerca_], cache3, redactar=ia_doble({"Cerca": [70]}), log=lambda m: None, minimo=75, margen=10)
chequear("doble puntaje: un puntaje viejo del caché cerca del corte recibe su segunda vuelta",
         len(llamadas_p) == 1 and p[cerca_["id"]]["dobles"] == [80, 70] and p[cerca_["id"]]["ai_score"] == 75)
llamadas_p.clear()
SC.puntuar([cerca_], {}, redactar=ia_doble({"Cerca": [78]}), log=lambda m: None, minimo=75, margen=0)
chequear("doble puntaje: margen 0 (AGRO_DOBLE_MARGEN=0) lo apaga", len(llamadas_p) == 1)

# --- selección -------------------------------------------------------------------------------


def cand(i, score, sub, tema="", com=0):
    return {"id": str(i), "score": {"ai_score": score, "commercial_score": com, "subtema": sub, "tema": tema}}


os.environ.pop("AGRO_MEZCLA", None)
chequear("topes de la mezcla del documento con 10 por día",
         SE.topes(10) == {"agro": 3, "mercados": 2, "agtech": 2, "maquinaria": 1, "ganaderia": 1, "empresas": 1})
os.environ["AGRO_MEZCLA"] = "agro:50,mercados:50"
chequear("AGRO_MEZCLA se puede editar", SE.topes(4) == {"agro": 2, "mercados": 2})
os.environ.pop("AGRO_MEZCLA")
el, desc = SE.elegir([cand(1, 90, "mercados"), cand(2, 88, "mercados"), cand(3, 80, "mercados"),
                      cand(4, 74, "agro"), cand(5, 86, "mercados")], [], cupo_dia=10, minimo=75)
ids = [c["id"] for c in el]
chequear("tope de mercados (2) + refuerzo para la de 86, no para la de 80",
         sorted(ids) == ["1", "2", "5"])
chequear("la de 74 se descarta por score", any(c["id"] == "4" and "74 < 75" in m for c, m in desc))
el, desc = SE.elegir([cand(1, 90, "agro", "soja"), cand(2, 89, "agtech", "soja"), cand(3, 88, "mercados", "soja")],
                     [], cupo_dia=10, minimo=75)
chequear("no más de 2 del mismo tema por día", len(el) == 2 and "soja" in desc[0][1])
el, _ = SE.elegir([cand(1, 90, "agro"), cand(2, 89, "agtech")], [cand(9, 80, "agro")] * 9, cupo_dia=10, minimo=75)
chequear("respeta el cupo del día contando lo ya elegido", len(el) == 1)
orden = SE.ordenar_variado([cand(1, 90, "agro"), cand(2, 89, "agro"), cand(3, 80, "mercados")], [])
chequear("no salen dos del mismo subtema seguidos", [c["id"] for c in orden] == ["1", "3", "2"])

# --- guion -----------------------------------------------------------------------------------
chequear("recortar_palabras no deja un conector colgado",
         GU.recortar_palabras("La soja argentina lidera el mercado de la exportación mundial", 8)
         == "La soja argentina lidera el mercado")
chequear("hashtags: CamelCase sin tildes, sin repetir, hasta 5",
         GU._hashtags(["#Agro", "agro", "#Ganadería", "Campo Argentino", "#Soja", "#Maiz", "#Trigo"])
         == ["#Agro", "#Ganaderia", "#CampoArgentino", "#Soja", "#Maiz"])
chequear("se saca la lista suelta de palabras clave al final del texto de IG",
         GU._sin_lista_de_claves("Texto.\n\n¿Y vos qué pensás?\n\nagro, campo argentino, agricultura, productores, "
                                 "Argentina") == "Texto.\n\n¿Y vos qué pensás?")
chequear("un párrafo normal con comas no se toca",
         GU._sin_lista_de_claves("Hubo lluvias en Chivilcoy, Bragado, Alberti y 9 de Julio, con 40 mm en promedio "
                                 "según el SMN.") .startswith("Hubo lluvias"))
chequear("el prompt pide voseo, titular concreto y cifras en números sin cambiar el sentido",
         "VOSEO" in GU.SYSTEM_PROMPT and "nunca genérico" in GU.SYSTEM_PROMPT and "Un rango queda rango" in GU.SYSTEM_PROMPT)

CUERPO = ("La empresa Koppert lanzó dos packs biológicos para semillas de soja. Aceleran la emergencia al "
          "menos 3 días y suben el rendimiento promedio un 2% sobre los químicos, según más de 90 ensayos.")
BUENA = {"apta": True, "volanta": "AgTech", "titular": "Soja: biológicos de Koppert aceleran la emergencia 3 días",
         "bajada": "Los dos packs suben el rendimiento un 2% frente a los químicos tras 90 ensayos.",
         "descripcion": "Gancho.\n\nKoppert sumó dos packs para soja que adelantan 3 días la emergencia.\n\n"
                        "En más de 90 ensayos el rinde subió 2%.\n\n¿Lo probarías en tu lote?",
         "hashtags": ["#Agro", "#Soja", "#AgTech"], "datos_clave": ["3 días", "2%"],
         "titulo_web": "Biológicos en soja: adelantan la emergencia y suben el rinde",
         "nota_web": "Koppert sumó dos packs para soja.\n\nAdelantan 3 días la emergencia y suman 2% de rinde "
                     "en más de 90 ensayos.",
         "reel": {"gancho": "Más rinde en soja sin químicos", "que_paso": "Koppert lanzó dos packs",
                  "datos": ["3 días antes", "2% más de rinde"], "por_que_importa": "Más kilos por hectárea",
                  "cierre": "Más en la web"},
         "prompt_imagen": "soybean plants with trifoliate leaves", "datos_contradictorios": False}
llamadas = []


def ia_guion(respuestas):
    def redactar(system, material, **kw):
        llamadas.append(system)
        return respuestas[min(len(llamadas) - 1, len(respuestas) - 1)], "falsa"
    return redactar


rep = nota(5, "Koppert lanza packs biológicos para soja", "Tratamientos biológicos de semillas")
llamadas.clear()
g = GU.generar(rep, CUERPO, [], {"sensible": False}, redactar=ia_guion([BUENA]))
chequear("guion bueno: una sola llamada, apta y sin revisión",
         len(llamadas) == 1 and g["apta"] and not g["requires_review"])
llamadas.clear()
nombra = dict(BUENA, descripcion=BUENA["descripcion"] + "\n\nLo publicó Infocampo.")
g = GU.generar(rep, CUERPO, [], {"sensible": False}, redactar=ia_guion([nombra, nombra]))
chequear("nombrar al medio: se pide otra versión y si insiste queda NO apta",
         len(llamadas) == 2 and "Infocampo" in llamadas[1] and not g["apta"])
llamadas.clear()
larga = dict(BUENA, titular="Uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce")
g = GU.generar(rep, CUERPO, [], {"sensible": False}, redactar=ia_guion([larga, larga]))
chequear("titular largo: se pide otra versión y al final se recorta a 12",
         len(llamadas) == 2 and len(g["titular"].split()) <= 12)
# Copia que sobrevive al segundo pedido: se corrige SOLO el párrafo calcado.
from reels import guion as RG  # noqa: E402
ORIG = ("La empresa Koppert lanzó dos packs biológicos para semillas de soja que aceleran la emergencia "
        "al menos tres días y mejoran el rendimiento promedio frente a los tratamientos químicos tradicionales")
orig_pal = RG._palabras(ORIG)
g_c = dict(GU._salida(BUENA, "x"), datos_clave=["Koppert"],
           nota_web="Un párrafo propio sin problemas.\n\nLa empresa Koppert lanzó dos packs biológicos para semillas "
                    "de soja que aceleran la emergencia al menos tres días y mejoran el rendimiento promedio.")
c_c = RG.copia_del_original(g_c, orig_pal)
pedidos_p = []


def ia_parafrasis(respuestas):
    def redactar(system, material, **kw):
        pedidos_p.append(material)
        return {"parrafo": respuestas[min(len(pedidos_p) - 1, len(respuestas) - 1)]}, "falsa"
    return redactar


g2, c2, f2, n = GU.reparar_copia(g_c, c_c, orig_pal, [], ia_parafrasis(
    ["Koppert sumó al mercado dos opciones biológicas para tratar la semilla de soja: según la firma, "
     "la planta emerge tres días antes y rinde más que con los productos químicos de siempre."]))
chequear("copia: arranca calcada (más de 10 palabras)", c_c["racha"] >= RG.UMBRAL_COPIA and c_c["campo"] == "nota_web")
chequear("copia: se pide reescribir SOLO el párrafo calcado, con el fragmento a evitar",
         len(pedidos_p) == 1 and "Un párrafo propio" not in pedidos_p[0] and "FRAGMENTO A EVITAR" in pedidos_p[0])
chequear("copia: queda corregida y el párrafo propio intacto",
         c2["racha"] < RG.UMBRAL_COPIA and n == 1 and g2["nota_web"].startswith("Un párrafo propio sin problemas."))
pedidos_p.clear()
g3, c3, f3, n3 = GU.reparar_copia(dict(g_c, datos_clave=["Koppert", "tres días"]), c_c, orig_pal, [],
                                  ia_parafrasis(["Una empresa sumó dos opciones biológicas para la semilla de soja."]))
chequear("copia: un arreglo que pierde un dato se descarta (y se reintenta hasta 3 veces)",
         g3["nota_web"] == g_c["nota_web"] and n3 == GU.REPARACIONES)
g = GU.generar(rep, CUERPO, [], {"sensible": True}, redactar=ia_guion([BUENA]))
chequear("dato sensible de un medio → sale igual (20/10/2026: sin retención)", not g["requires_review"])
os.environ["AGRO_REVISION_SENSIBLE"] = "1"
g = GU.generar(rep, CUERPO, [], {"sensible": True}, redactar=ia_guion([BUENA]))
chequear("AGRO_REVISION_SENSIBLE=1: dato sensible de un medio → requiere revisión", g["requires_review"])
g = GU.generar(dict(rep, tipo_fuente="oficial"), CUERPO, [], {"sensible": True}, redactar=ia_guion([BUENA]))
chequear("dato sensible de una fuente oficial → no requiere revisión", not g["requires_review"])
os.environ.pop("AGRO_REVISION_SENSIBLE")
g = GU.generar(rep, CUERPO, [], {"sensible": False},
               redactar=ia_guion([dict(BUENA, datos_contradictorios=True, detalle_contradiccion="2% vs 3%")]))
chequear("fuentes que se contradicen → revisión con el detalle",
         g["requires_review"] and "2% vs 3%" in g["motivo_revision"])
g["hashtags"] = ["#Agro", "#Soja"]
fb = GU.texto_red(g, "facebook", "https://ejemplo.com/n/x")
chequear("Facebook lleva el link y los hashtags al final", fb.endswith("#Agro #Soja") and "https://ejemplo.com/n/x" in fb)
chequear("Instagram no lleva link", "https://" not in GU.texto_red(g, "instagram", "https://ejemplo.com/n/x"))
chequear("Shorts lleva #Shorts", GU.texto_red(g, "youtube").endswith("#Shorts"))

# --- imagen ----------------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    destino = Path(tmp) / "p_imagen.jpg"
    bajadas, generadas = [], []

    from PIL import Image as _Im
    ancho_foto = [1600]

    def bajar(url, ruta):
        bajadas.append(url)
        _Im.new("RGB", (ancho_foto[0], ancho_foto[0] * 2 // 3), (80, 120, 60)).save(ruta)
        return True

    def generar(prompt, ruta, estilo=None):
        generadas.append(estilo)
        Path(ruta).write_bytes(b"x")
        return {"archivo": str(ruta)}

    r = IMG.elegir(dict(rep, tipo_fuente="medio"), "https://foto/afp-medio.jpg", "soy", destino,
                   generar=generar, bajar=bajar, mirar=lambda f: False,
                   recrear_con=lambda *a, **k: {"motivo": "Cloudflare caído"})
    chequear("foto de AGENCIA de otro medio que no se pudo recrear: va IA (la de agencia nunca tal cual)",
             r["origen"] == "ia" and r["url_original"] == "https://foto/afp-medio.jpg" and "Cloudflare caído" in r["motivo"])
    chequear("la IA recibe el estilo agro", generadas and generadas[0] == IMG.ESTILO)
    bajadas.clear()
    r = IMG.elegir(dict(rep, tipo_fuente="oficial"), "https://foto/inta.jpg", "soy", destino,
                   generar=generar, bajar=bajar, mirar=lambda f: False)
    chequear("foto de fuente OFICIAL: se usa con el crédito",
             r["origen"] == "fuente" and bajadas == ["https://foto/inta.jpg"] and r["credito"] == rep["fuente"])
    ancho_foto[0] = 500
    r = IMG.elegir(dict(rep, tipo_fuente="oficial"), "https://foto/chica.jpg", "soy", destino,
                   generar=generar, bajar=bajar, mirar=lambda f: False)
    chequear("foto oficial chica (500 px) → IA", r["origen"] == "ia" and "chica" in r["motivo"])
    ancho_foto[0] = 1600
    r = IMG.elegir(dict(rep, tipo_fuente="oficial"), "https://foto/placa.jpg", "soy", destino,
                   generar=generar, bajar=bajar, mirar=lambda f: "_fuente" in str(f))
    chequear("foto oficial con letras (placa) → IA", r["origen"] == "ia" and "letras" in r["motivo"])
    bajadas.clear()
    r = IMG.elegir(dict(rep, tipo_fuente="oficial", fuente="Bolsa de Comercio de Rosario"), "https://bcr/x.png",
                   "soy", destino, generar=generar, bajar=bajar, mirar=lambda f: False)
    chequear("la Bolsa (foto: False) va directo a la IA sin bajar su placa", r["origen"] == "ia" and not bajadas)
    # Nunca el logo suelto: escena de la nota (2) → escena segura del tema (1) → banco.
    prompts = []

    def generar_p(prompt, ruta, estilo=None):
        prompts.append(prompt)
        Path(ruta).write_bytes(b"x")
        return {"archivo": str(ruta)}

    banco_real = IMG.BANCO
    IMG.BANCO = Path(tmp) / "banco"
    try:
        r = IMG.elegir(rep, "", "soy", destino, generar=generar_p, bajar=bajar,
                       mirar=lambda f: not str(f).endswith("_ia2.jpg"), subtema="ganaderia")
        chequear("letras dos veces → 3er intento con una escena segura del subtema, y sirve",
                 r["origen"] == "ia" and prompts[:2] == ["soy", "soy"] and prompts[2] in IMG.SEGURAS["ganaderia"]
                 and "escena segura" in r["motivo"])
        r = IMG.elegir(rep, "", "soy", destino, generar=generar_p, bajar=bajar, mirar=lambda f: True, subtema="ganaderia")
        chequear("todo con letras y banco vacío → recién ahí «ninguna»", r["origen"] == "ninguna")
        (IMG.BANCO / "ganaderia").mkdir(parents=True)
        (IMG.BANCO / "agro").mkdir(parents=True)
        for nombre in ("ganaderia/g1.jpg", "ganaderia/g2.jpg", "agro/a1.jpg"):
            (IMG.BANCO / nombre).write_bytes(b"x")
        r = IMG.elegir(rep, "", "soy", destino, generar=generar_p, bajar=bajar, mirar=lambda f: True, subtema="ganaderia")
        chequear("todo con letras → imagen del banco DEL SUBTEMA (nunca el logo suelto)",
                 r["origen"] == "ia" and "/ganaderia/" in Path(r["archivo"]).as_posix() and "banco" in r["motivo"])
        r = IMG.elegir(rep, "", "soy", destino, generar=lambda *a, **k: {"motivo": "Cloudflare caído"},
                       bajar=bajar, mirar=lambda f: False, subtema="maquinaria")
        chequear("la IA caída y el subtema sin banco → cualquier imagen del banco",
                 r["origen"] == "ia" and r["archivo"] and "Cloudflare caído" in r["motivo"])
    finally:
        IMG.BANCO = banco_real
    chequear("el banco real tiene imágenes de todos los subtemas",
             all(list((IMG.BANCO / sub).glob("*.jpg")) for sub in IMG.SEGURAS))

    # --- portada y reel (PIL + ffmpeg, sin red) -------------------------------------------------
    from PIL import Image
    from agro import portada as POR
    from agro import reel as REEL
    foto = Path(tmp) / "foto.jpg"
    Image.new("RGB", (1024, 1024), (90, 140, 60)).save(foto)
    g = dict(GU._salida(BUENA, "falsa"))
    for img, ia in ((foto, True), (None, False)):
        sal = Path(tmp) / f"portada_{bool(img)}.jpg"
        POR.armar(g, img, sal, ia=ia)
        with Image.open(sal) as im:
            chequear(f"portada 4:5 (1080x1350) {'con foto' if img else 'sin foto'}", im.size == (1080, 1350))
    tramos = REEL.TRAMOS
    REEL.TRAMOS = tuple((n, 0.25) for n, _ in tramos)          # un reel de 1,25 s para la prueba
    try:
        for tema in ("blanco", "grafito"):
            rr = REEL.armar(g, foto, Path(tmp) / f"reel_{tema}.mp4", origen="recreada", tema=tema)
            with Image.open(rr["vista"]) as im:
                chequear(f"reel 4:5 ({tema}) armado, con su portada 1080x1350",
                         Path(rr["archivo"]).stat().st_size > 1000 and abs(rr["duracion"] - 1.25) < 0.01
                         and im.size == (1080, 1350) and rr["tema"] == tema)
        # Con el video de la fuente (31/10/2026): el reel dura lo que el video + el cierre, y lleva su sonido.
        import subprocess as _sp
        _clip = Path(tmp) / "clip.mp4"
        _sp.run([REEL._ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24",
                 "-f", "lavfi", "-i", "sine=frequency=440", "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", str(_clip)], check=True)
        rv = REEL.armar(g, foto, Path(tmp) / "reel_video.mp4", origen="video", clip=_clip)
        from reels import reel_bot as _RB
        _dur = _RB.motor().duration_seconds(rv["archivo"])
        chequear("reel con video: dura el video entero + el cierre, con el sonido del video",
                 abs(rv["duracion"] - 3.25) < 0.01 and abs(_dur - 3.25) < 0.2 and rv["con_sonido"]
                 and _RB.motor().has_audio(rv["archivo"]))
        chequear("reel con video: el último texto se estira hasta que termina el video",
                 dict(REEL.tramos_para(3))["por_que_importa"] == 2.25 and REEL.tramos_para(0.5) == REEL.TRAMOS)
    finally:
        REEL.TRAMOS = tramos

# --- fuentes oficiales y sitios sin RSS -----------------------------------------------------------
from agro import fuentes as FU  # noqa: E402
chequear("Secretaría de Agricultura (oficial) y LA NACION Campo (medio) están",
         FU.por_nombre("Secretaría de Agricultura").get("tipo") == "oficial"
         and FU.por_nombre("LA NACION Campo").get("tipo") == "medio")
chequear("las internacionales (AgFunderNews, Future Farming, CropLife) están en inglés",
         all(FU.por_nombre(n).get("idioma") == "en" and FU.por_nombre(n).get("tipo") == "medio"
             for n in ("AgFunderNews", "Future Farming", "CropLife")))
chequear("el idioma de la fuente pasa a la nota",
         CA.normalizar({"url": "https://x.com/a", "titulo": "Robots"}, {"nombre": "X", "idioma": "en", "pais": "INT"},
                       "f", datetime(2026, 10, 13, tzinfo=CA.TZ_AR))["idioma"] == "en")
chequear("el guion pide escribir en castellano lo que viene en inglés", "en inglés" in GU.SYSTEM_PROMPT)
chequear("INTA y la Bolsa están, como oficiales",
         FU.por_nombre("INTA").get("tipo") == "oficial" and FU.por_nombre("Bolsa de Comercio de Rosario").get("tipo") == "oficial")


class _Resp:
    def __init__(self, texto, status=200):
        self.text, self.status_code = texto, status

    def raise_for_status(self):
        pass


PORTADA_BCR = ('<a href="/es/mercados/investigacion-y-desarrollo/informativo-semanal/noticias-informativo-semanal/feedlots-3">'
               '<a href="/es/mercados/investigacion-y-desarrollo/informativo-semanal/noticias-informativo-semanal/feedlots-3">'
               '<a href="/es/mercados/mercado-de-granos/comentario-del-mercado/comentario-del-mercado-local/comentario-1809">'
               '<a href="/es/sobre-bcr">')
NOTA_BCR = ('<meta property="og:title" content="FEEDLOTS: encierres r&eacute;cord" />'
            '<meta property="og:description" content="Ingresos estacionales" />'
            '<meta property="og:image" content="https://www.bcr.com.ar/x.png" />'
            '<meta property="article:published_time" content="08/10/2026" />'
            '<div class="field--name-body">' + "<p>" + "Un párrafo largo de la nota. " * 40 + "</p>" * 3 + "</div>"
            '<div class="menu"><p>Inicio</p></div>')
pedidas = []


def get_falso(url):
    pedidas.append(url)
    return _Resp(PORTADA_BCR if url.endswith("informativo-semanal") else NOTA_BCR)


CA._robots["https://www.bcr.com.ar"] = __import__("urllib.robotparser").robotparser.RobotFileParser()
CA._robots["https://www.bcr.com.ar"].parse([])
bcr = FU.por_nombre("Bolsa de Comercio de Rosario")
lista = CA.listar_portada("https://www.bcr.com.ar/es/mercados/investigacion-y-desarrollo/informativo-semanal",
                          bcr["patron"], get=get_falso)
chequear("Bolsa: solo los links del informativo, sin repetir (no el comentario diario ni el menú)",
         len(lista) == 1 and lista[0]["url"].endswith("/feedlots-3"))
chequear("Bolsa: título (sin entidades), resumen, foto y fecha de los metadatos",
         lista[0]["titulo"] == "FEEDLOTS: encierres récord" and lista[0]["copete"] == "Ingresos estacionales"
         and lista[0]["imagen"].endswith("x.png") and lista[0]["publicado"].startswith("2026-10-08"))
SITEMAP = ('<urlset><url><loc>https://www.lacapital.com.ar/agro/feedlots-record-n10286319.html</loc><news:news>'
           '<news:publication_date>2026-10-13T09:15:00Z</news:publication_date>'
           '<news:title>Los feedlots tienen un stock r&eacute;cord</news:title></news:news></url>'
           '<url><loc>https://www.lacapital.com.ar/politica/milei-viaja-n10286482.html</loc><news:news>'
           '<news:publication_date>2026-10-13T10:00:00Z</news:publication_date><news:title>Milei viaja</news:title>'
           '</news:news></url></urlset>')


def get_sitemap(url):
    return _Resp(SITEMAP if url.endswith(".xml") else NOTA_BCR)


CA._robots["https://www.lacapital.com.ar"] = CA._robots["https://www.bcr.com.ar"]
agc = FU.por_nombre("Agroclave (La Capital)")
lista = CA.listar_sitemap("https://www.lacapital.com.ar/sitemap-news.xml", agc["patron"], get=get_sitemap)
chequear("Agroclave: del sitemap de La Capital solo entra lo de /agro/, con título y fecha del sitemap",
         len(lista) == 1 and lista[0]["titulo"] == "Los feedlots tienen un stock récord"
         and lista[0]["publicado"] == "2026-10-13T09:15:00Z" and lista[0]["copete"] == "Ingresos estacionales")
chequear("cuerpo por párrafos: el bloque con más texto, no el menú",
         CA.cuerpo_por_parrafos(NOTA_BCR).startswith("Un párrafo largo") and "Inicio" not in CA.cuerpo_por_parrafos(NOTA_BCR))
c = CA.completar({"url": "https://www.bcr.com.ar/es/nota", "imagen_url": ""},
                 detalle=lambda u: {"ok": True, "cuerpo": "solo el resumen", "imagen": ""}, get=get_falso)
chequear("completar: si el extractor da solo el resumen, se usa el texto por párrafos", len(c["cuerpo"]) > 1000)


def listar_viejas(feed):
    return [{"titulo": "Informe semanal", "url": "https://www.bcr.com.ar/es/n1", "copete": "",
             "publicado": "2026-10-08T12:00:00"}]


for horas, entra in ((0, False), (168, True)):
    f = {"nombre": "X", "rss": ["https://www.bcr.com.ar/rss"], "tipo": "oficial", "horas": horas}
    ns, _ = CA.capturar([f], ahora=datetime(2026, 10, 13, 17, 0, tzinfo=CA.TZ_AR), horas_max=48,
                        listar=listar_viejas, log=lambda m: None)
    chequear(f"ventana propia de {horas} h: una nota de hace 5 días {'entra' if entra else 'no entra'}",
             bool(ns) is entra)

# --- pasada de punta a punta: una pieza frenada se repone con la siguiente ----------------------
with tempfile.TemporaryDirectory() as tmp:
    import json as _json
    PA.SALIDA, PA.MEMORIA = Path(tmp), Path(tmp) / "memoria.json"
    temas = {"Soja": ("agro", 90), "Trigo": ("mercados", 85), "Hacienda": ("ganaderia", 80), "Tractores": ("maquinaria", 60)}
    crudas = [nota(10 + i, f"{t} {extra}", f"Detalle {t.lower()} {extra}")
              for i, (t, extra) in enumerate((("Soja", "récord en Chivilcoy"), ("Trigo", "precios en alza"),
                                               ("Hacienda", "remate en Bragado"), ("Tractores", "ventas de septiembre")))]
    originales = {k: getattr(m, a) for k, (m, a) in {
        "cap": (CA, "capturar"), "comp": (CA, "completar"), "pun": (SC, "puntuar"), "gen": (GU, "generar"),
        "img": (IMG, "elegir"), "por": (PA.POR, "armar"), "reel": (PA, "GU_reel"), "ent": (PA.entorno, "cargar")}.items()}
    try:
        PA.entorno.cargar = lambda: None
        CA.capturar = lambda fuentes, ahora, horas_max, log: ([dict(n) for n in crudas], [])
        CA.completar = lambda rep: {"ok": True, "cuerpo": "cuerpo", "imagen": ""}

        def puntuar_falso(reps, cache, log):
            out = {}
            for r in reps:
                sub, sc = temas[r["titulo"].split()[0]]
                out[r["id"]] = dict(SC.limpiar({"subtema": sub}), ai_score=sc, tema=r["titulo"].split()[0].lower())
            return out
        SC.puntuar = puntuar_falso

        def generar_falso(rep, cuerpo, otras, s):
            g = GU._salida(dict(BUENA, titular=rep["titulo"]), "falsa")
            g.update(copia={"racha": 0}, faltan_datos=[], formato=[], requires_review=False, motivo_revision="")
            if rep["titulo"].startswith("Soja"):
                g.update(apta=False, motivo="calca 17 palabras seguidas del original")
            return g
        GU.generar = generar_falso
        IMG.elegir = lambda *a, **k: {"archivo": None, "origen": "ninguna", "motivo": "prueba"}
        PA.POR.armar = lambda *a, **k: Path(tmp) / "p.jpg"
        PA.GU_reel = lambda *a, **k: {"archivo": None, "duracion": 0, "peso_kb": 0}
        ruta = PA.pasada(max_piezas=2, con_reel=False, log=lambda m: None)
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        titulos = [p["guion"]["titular"] for p in inf["piezas"]]
        chequear("la pieza frenada por copia queda en el informe como NO APTA",
                 titulos[0].startswith("Soja") and not inf["piezas"][0]["guion"]["apta"])
        chequear("su lugar lo toma la siguiente mejor (la de 80, no la de 60)",
                 titulos == ["Soja récord en Chivilcoy", "Trigo precios en alza", "Hacienda remate en Bragado"]
                 and inf["conteos"]["Reemplazos"] == 1 and inf["conteos"]["Piezas armadas"] == 2)
        chequear("la que entró de reemplazo ya no figura como descartada",
                 not any(d["titulo"].startswith("Hacienda") for d in inf["descartadas"]))
        mem = _json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
        chequear("la frenada queda en memoria como no apta (no ocupa cupo del día)",
                 any(e["titular"].startswith("Soja") and e["apta"] is False for e in mem["elegidas"]))

        # Arranque real: 1 por pasada. La buena que no entró espera a la pasada siguiente.
        PA.MEMORIA.unlink()
        ruta = PA.pasada(con_reel=False, log=lambda m: None)
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        aptas = [p["guion"]["titular"] for p in inf["piezas"] if p["guion"]["apta"]]
        chequear("1 por pasada: Soja frenada → entra Trigo y nada más", aptas == ["Trigo precios en alza"])
        chequear("la de 80 (Hacienda) queda pendiente, no se pierde",
                 inf["conteos"]["Quedan pendientes"] == 1 and any(
                     "pendiente para la próxima corrida" in d["motivo"] for d in inf["descartadas"]))
        ruta = PA.pasada(con_reel=False, log=lambda m: None)
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        chequear("la pasada siguiente (sin notas nuevas) arma la pendiente",
                 [p["guion"]["titular"] for p in inf["piezas"]] == ["Hacienda remate en Bragado"]
                 and inf["conteos"]["Pendientes de corridas anteriores"] == 1 and inf["conteos"]["Quedan pendientes"] == 0)
        ruta = PA.pasada(con_reel=False, log=lambda m: None)
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        chequear("y la tercera no repite nada", not inf["piezas"])

        # Modo REAL con un publicador de mentira: la retenida para revisión no sale y se repone.
        PA.MEMORIA_REAL = Path(tmp) / "estado_agro.json"
        PA.GU_reel = lambda g, imagen, salida, origen="ia", credito="", clip=None, tema="blanco": (
            Path(salida).write_bytes(b"mp4") and None) or {"archivo": str(salida), "duracion": 22, "peso_kb": 1}
        gen_sim = GU.generar

        def generar_revision(rep, cuerpo, otras, s):
            g = gen_sim(rep, cuerpo, otras, s)
            if rep["titulo"].startswith("Trigo"):
                g.update(requires_review=True, motivo_revision="dato sensible sin fuente oficial")
            return g
        GU.generar = generar_revision
        publicadas, estado_al_publicar = [], []

        def publicador_falso(pieza, log=print):
            publicadas.append(pieza["guion"]["titular"])
            estado_al_publicar.append(_json.loads(PA.MEMORIA_REAL.read_text(encoding="utf-8")))
            return {"youtube": {"id": "yt1"}, "web": {"url": "https://x/n/a"}, "facebook": {"id": "fb1"},
                    "instagram": {"error": "FalloRed: prueba"}}
        corrida_real = PA.corrida
        # «estamos en horario»: una corrida con un solo reel, ahora
        PA.corrida = lambda ahora: (ahora.replace(second=0, microsecond=0), True,
                                    [(ahora.replace(second=0, microsecond=0), "reel")])
        ruta = PA.correr(log=lambda m: None, publicar=True, publicador=publicador_falso)[-1]
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        chequear("real: Soja (no apta) y Trigo (retenida) no salen; se publica Hacienda",
                 publicadas == ["Hacienda remate en Bragado"])
        chequear("real: se anota «publicando» en la memoria ANTES de publicar (un corte no la repite)",
                 any(e.get("publicado", {}).get("estado") == "publicando" for e in estado_al_publicar[0]["elegidas"]))
        mem_r = _json.loads(PA.MEMORIA_REAL.read_text(encoding="utf-8"))
        hac = next(e for e in mem_r["elegidas"] if e["titular"].startswith("Hacienda"))
        chequear("real: queda anotado qué red salió y cuál falló",
                 hac["publicado"]["facebook"] == {"id": "fb1"} and "error" in hac["publicado"]["instagram"]
                 and inf["conteos"]["Publicadas"] == 1)
        chequear("real: la memoria real es aparte de la simulación", PA.MEMORIA_REAL != PA.MEMORIA)
        # El respaldo de 20 min después (mismo turno) no publica otra vez.
        fijo = datetime.now(CA.TZ_AR).replace(second=0, microsecond=0)
        PA.corrida = lambda ahora: (fijo, True, [(fijo, "reel")])
        mem_t = _json.loads(PA.MEMORIA_REAL.read_text(encoding="utf-8"))
        for e in mem_t["elegidas"]:
            if e.get("publicado"):
                e["turno"] = fijo.isoformat()
        PA.MEMORIA_REAL.write_text(_json.dumps(mem_t), encoding="utf-8")
        publicadas.clear()
        ruta = PA.correr(log=lambda m: None, publicar=True, publicador=publicador_falso)[-1]
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        chequear("real: si ese horario ya publicó, el respaldo no publica otra",
                 not publicadas and "ya publicó" in inf["conteos"]["No se publicó"])
        PA.corrida = lambda ahora: (ahora.replace(second=0, microsecond=0) + timedelta(hours=3), False, [])
        ruta = PA.correr(log=lambda m: None, publicar=True, publicador=publicador_falso)[-1]
        inf = _json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
        chequear("real: fuera de horario no publica", not publicadas and "fuera de horario" in inf["conteos"]["No se publicó"])
        PA.corrida = corrida_real
    finally:
        GU.generar = originales["gen"]
        CA.capturar, CA.completar, SC.puntuar, GU.generar = originales["cap"], originales["comp"], originales["pun"], originales["gen"]
        IMG.elegir, PA.POR.armar, PA.GU_reel, PA.entorno.cargar = originales["img"], originales["por"], originales["reel"], originales["ent"]

# --- publicar: salvaguarda de credenciales --------------------------------------------------------
from agro import publicar as PUBA  # noqa: E402
_guardadas = {k: os.environ.get(k) for k in list(PUBA._CLAVES) + ["AGRO_FACEBOOK_PAGE_ID", "AGRO_INSTAGRAM_USER_ID",
                                                                  "AGRO_FACEBOOK_PAGE_ACCESS_TOKEN", "AGRO_INSTAGRAM_ACCESS_TOKEN"]}
try:
    os.environ.update({"INSTAGRAM_USER_ID": "17841405971293744", "INSTAGRAM_ACCESS_TOKEN": "tok-diario",
                       "FACEBOOK_PAGE_ID": "1456376377985890", "FACEBOOK_PAGE_ACCESS_TOKEN": "tok-diario",
                       "AGRO_FACEBOOK_PAGE_ID": "101271341650483", "AGRO_INSTAGRAM_USER_ID": "17841427698320458",
                       "AGRO_FACEBOOK_PAGE_ACCESS_TOKEN": "tok-agro", "AGRO_INSTAGRAM_ACCESS_TOKEN": ""})
    with PUBA.credenciales_agro():
        dentro = (os.environ["INSTAGRAM_USER_ID"], os.environ["FACEBOOK_PAGE_ID"], os.environ["INSTAGRAM_ACCESS_TOKEN"])
    chequear("mientras publica, los publicadores ven la cuenta AGRO (IG con el token de página)",
             dentro == ("17841427698320458", "101271341650483", "tok-agro"))
    chequear("al terminar, vuelven las del diario", os.environ["INSTAGRAM_USER_ID"] == "17841405971293744"
             and os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"] == "tok-diario")
    os.environ["AGRO_INSTAGRAM_USER_ID"] = "17841405971293744"
    try:
        PUBA.credenciales()
        chequear("salvaguarda: un ID agro igual al del diario NO publica", False)
    except PUBA.SalvaguardaAgro:
        chequear("salvaguarda: un ID agro igual al del diario NO publica", True)
    os.environ.update({"AGRO_INSTAGRAM_USER_ID": "17841427698320458", "AGRO_FACEBOOK_PAGE_ACCESS_TOKEN": "tok-diario"})
    try:
        PUBA.credenciales()
        chequear("salvaguarda: el token del diario puesto como agro NO publica", False)
    except PUBA.SalvaguardaAgro:
        chequear("salvaguarda: el token del diario puesto como agro NO publica", True)
finally:
    for k, v in _guardadas.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
pp = PUBA.pieza_publicador({"guion": dict(GU._salida(BUENA, "x"), titulo_web="Biológicos en soja"), "portada": "p.jpg",
                            "rep": {"url": "https://infocampo.com.ar/n1"}})
chequear("la web nunca usa la foto del otro medio y va a la sección Campo",
         pp["imagen_url"] == "" and pp["web"]["titulo"] == "Biológicos en soja" and PUBA.CAMPO_ID.startswith("0b4eafce"))

# --- la memoria agro en la nube: el trabajo de policiales no la pisa -----------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import guardar_estado as GE  # noqa: E402
viejo_ = {"indice": {"url": {"u1": "2026-10-13"}}, "scores": {"h1": {}},
          "elegidas": [{"id": "a", "cuando": "2026-10-14T07:00", "publicado": {"estado": "publicando"}}],
          "pendientes": [{"id": "p-viejo"}], "actualizado": "2026-10-14T07:01"}
nuevo_ = {"indice": {"url": {"u1": "2026-10-13", "u2": "2026-10-14"}}, "scores": {"h1": {}, "h2": {}},
          "elegidas": [{"id": "a", "cuando": "2026-10-14T07:00", "publicado": {"facebook": {"id": "1"}}},
                       {"id": "b", "cuando": "2026-10-14T12:30", "publicado": {"web": {"url": "x"}}}],
          "pendientes": [{"id": "p-nuevo"}], "actualizado": "2026-10-14T12:35"}
for nombre, (mio, remoto) in {"policiales con la copia vieja": (viejo_, nuevo_), "agro con la nueva": (nuevo_, viejo_)}.items():
    c_ = GE.COMBINAR["agro.json"](mio, remoto)
    chequear(f"combinar agro.json ({nombre}): no se pierde ni se des-publica nada",
             [e["id"] for e in c_["elegidas"]] == ["a", "b"] and c_["elegidas"][0]["publicado"] == {"facebook": {"id": "1"}}
             and set(c_["indice"]["url"]) == {"u1", "u2"} and set(c_["scores"]) == {"h1", "h2"}
             and c_["pendientes"] == [{"id": "p-nuevo"}])

# --- agenda (20/10/2026): 6 corridas de 5 reels, uno cada 20 min, cada uno de un sitio distinto ----
from agro import agenda as AG  # noqa: E402

for _k in ("AGRO_AGENDA", "AGRO_CORRIDAS", "AGRO_POR_CORRIDA", "AGRO_INTERVALO_MIN"):
    os.environ.pop(_k, None)
_ag = AG.agenda()
chequear("agenda: 30 reels, sin carruseles, y 3 tandas de historias",
         AG.cuantos("reel") == 30 and AG.cuantos("carrusel") == 0 and AG.cuantos("historias") == 3)
_feed = [h * 60 + m for h, m, t in _ag if t != "historias"]
chequear("agenda: al menos 20 minutos entre un reel y el siguiente", all(b - a >= 20 for a, b in zip(_feed, _feed[1:])))
chequear("corridas: la del reel de datos (05) y las de noticias 7, 10, 13, 16, 18 y 21",
         AG.corridas() == [(5, 0), (7, 0), (10, 0), (13, 0), (16, 0), (18, 0), (21, 0)]
         and AG.corridas_noticias() == [(7, 0), (10, 0), (13, 0), (16, 0), (18, 0), (21, 0)])
chequear("la corrida de las 05: solo el reel de datos", AG.corrida(datetime(2026, 10, 16, 5, 2, tzinfo=CA.TZ_AR))[2]
         == [(datetime(2026, 10, 16, 5, 0, tzinfo=CA.TZ_AR), "reel_datos")] and AG.cuantos("reel_datos") == 1)


def _t(h, m, dia=16):
    return datetime(2026, 10, dia, h, m, tzinfo=CA.TZ_AR)


def _hm(turnos):
    return [(f"{t:%H:%M}", tipo) for t, tipo in turnos]


def _reels(*horas):
    return [(h, "reel") for h in horas]


_c = AG.corrida(_t(7, 3))
chequear("la corrida de las 07: historias y 5 reels (07:00 a 08:20)",
         _c[:2] == (_t(7, 0), True)
         and _hm(_c[2]) == [("07:00", "historias")] + _reels("07:00", "07:20", "07:40", "08:00", "08:20"))
chequear("la de las 13: a las 14:00 primero las historias del mediodía y después el reel",
         _hm(AG.corrida(_t(13, 0))[2]) == _reels("13:00", "13:20", "13:40") + [("14:00", "historias")]
         + _reels("14:00", "14:20"))
chequear("la de las 16: 16:00 a 17:20 (no se mete en la de las 18)",
         _hm(AG.corrida(_t(16, 10))[2]) == _reels("16:00", "16:20", "16:40", "17:00", "17:20"))
chequear("la de las 21: 21:00 a 22:20", _hm(AG.corrida(_t(21, 39))[2]) == _reels("21:00", "21:20", "21:40", "22:00", "22:20"))
chequear("a las 10:45 ya no (40 min de tolerancia): la próxima es la de las 13",
         AG.corrida(_t(10, 45))[:2] == (_t(13, 0), False))
chequear("a las 23:00: la próxima es mañana a las 05 (el reel de datos)", AG.corrida(_t(23, 0))[:2] == (_t(5, 0, 17), False))
chequear("las tres tandas de historias: mañana, mediodía y cierre",
         [AG.bloque(_t(7, 0)), AG.bloque(_t(14, 0)), AG.bloque(_t(19, 0))] == ["manana", "mediodia", "cierre"])
chequear("el inicio de la corrida de un horario", AG.inicio_corrida(_t(14, 20)) == _t(13, 0)
         and AG.inicio_corrida(_t(13, 0)) == _t(13, 0) and AG.inicio_corrida(_t(4, 0)) is None)
os.environ["AGRO_AGENDA"] = "08:00 carrusel, 11:00 carrusel"
chequear("sábado: con carruseles en AGRO_AGENDA, el primero es «Los números de la semana»",
         AG.es_primer_carrusel_del_sabado(_t(8, 0, 17)) and not AG.es_primer_carrusel_del_sabado(_t(11, 0, 17))
         and not AG.es_primer_carrusel_del_sabado(_t(8, 0, 16)))
os.environ["AGRO_AGENDA"] = "06:30 historias, 10:00 reel, basura, 25:00 reel"
chequear("AGRO_AGENDA se puede cambiar (y lo que no se entiende se saltea)",
         AG.agenda() == [(6, 30, "historias"), (10, 0, "reel")])
os.environ.pop("AGRO_AGENDA")
os.environ["AGRO_CORRIDAS"] = "08:00, 20:00, x"
chequear("AGRO_CORRIDAS se puede cambiar", AG.corridas_noticias() == [(8, 0), (20, 0)]
         and AG.corridas() == [(5, 0), (8, 0), (20, 0)])
os.environ["AGRO_REEL_DATOS"] = "0"
chequear("AGRO_REEL_DATOS=0 apaga el reel de datos", AG.corridas() == [(8, 0), (20, 0)] and not AG.cuantos("reel_datos"))
os.environ["AGRO_REEL_DATOS"] = "04:30"
chequear("AGRO_REEL_DATOS cambia la hora", (4, 30) in AG.corridas())
os.environ.pop("AGRO_REEL_DATOS")
os.environ["AGRO_CORRIDAS"] = "16:00, 17:00"
chequear("los reels de una corrida no se pasan a la siguiente",
         [(h, m) for h, m, t in AG.agenda() if t == "reel"] == [(16, 0), (16, 20), (16, 40), (17, 0), (17, 20), (17, 40),
                                                                (18, 0), (18, 20)])
os.environ.pop("AGRO_CORRIDAS")
os.environ["AGRO_POR_CORRIDA"], os.environ["AGRO_INTERVALO_MIN"] = "3", "30"
chequear("AGRO_POR_CORRIDA y AGRO_INTERVALO_MIN: 3 reels cada 30 min",
         _hm(AG.corrida(_t(10, 0))[2]) == _reels("10:00", "10:30", "11:00") and AG.cuantos("reel") == 18)
os.environ.pop("AGRO_POR_CORRIDA"), os.environ.pop("AGRO_INTERVALO_MIN")
_smin = os.environ.pop("AGRO_SCORE_MIN")
chequear("de fábrica: hasta 36 por día (30 y margen), mínimo 60, una por horario",
         SE.max_dia() == 36 and SE.score_min() == 60 and SE.por_pasada() == 1)
os.environ["AGRO_SCORE_MIN"] = _smin

# --- un sitio distinto por reel dentro de la corrida; el Short, solo del primero -------------------
_iso = lambda h, m: _t(h, m).isoformat()  # noqa: E731
_mem_sit = {"elegidas": [
    {"turno": _iso(13, 0), "fuente": "Infocampo", "publicado": {"instagram": {"id": "1"}}},
    {"turno": _iso(13, 20), "fuente": "Agrositio", "publicado": {"instagram": {"id": "2"}}, "revision": True},
    {"turno": _iso(13, 20), "fuente": "INTA", "publicado": None},
    {"turno": _iso(10, 0), "fuente": "TodoAgro", "publicado": {"instagram": {"id": "3"}}},
    {"turno": _iso(13, 20), "fuente": "Bichos de Campo", "publicado": {"estado": "publicando"}},
    {"turno": "", "cuando": "basura", "fuente": "X", "publicado": {"a": 1}}]}
chequear("sitios de la corrida: solo lo que salió (o está saliendo) en ESTA corrida",
         PA.sitios_de_la_corrida(_mem_sit, _t(13, 40)) == {"Infocampo", "Bichos de Campo"}
         and PA.sitios_de_la_corrida(_mem_sit, _t(16, 0)) == set()
         and PA.sitios_de_la_corrida(_mem_sit, _t(13, 0)) == set())
chequear("YouTube: solo el primer reel de cada corrida (el cupo de la API es compartido)",
         [PA.con_youtube(_t(h, m)) for h, m in ((7, 0), (7, 20), (13, 0), (14, 0), (14, 20), (16, 0))]
         == [True, False, True, False, False, True])
os.environ["AGRO_UN_SITIO_POR_CORRIDA"] = "0"
chequear("AGRO_UN_SITIO_POR_CORRIDA=0 lo apaga", not PA.un_sitio_por_corrida())
os.environ.pop("AGRO_UN_SITIO_POR_CORRIDA")


# --- el reel de datos de las 05 y las historias de datos en @diarioyradio (23/10/2026) ---------------
from agro import reel_datos as RD  # noqa: E402
from agro import historias as _HI  # noqa: E402
from agro import publicar as _PUBd  # noqa: E402

with tempfile.TemporaryDirectory() as _tmpd:
    _b, _d = _HI.lienzo()
    _d.rectangle((0, 0, 500, 300), fill=(200, 100, 0, 255))
    _p = _HI.guardar(_b, Path(_tmpd) / "historia_00_x.jpg")
    from PIL import Image as _Im  # noqa: E402
    chequear("cada placa de historia sale también en 4:5 (1080x1350)",
             _Im.open(_p).size == (1080, 1920) and _Im.open(_HI.ruta_45(_p)).size == (1080, 1350))
    _v = RD.armar_video([_HI.ruta_45(_p), _HI.ruta_45(_p), _HI.ruta_45(_p)], Path(_tmpd) / "r.mp4")
    from reels import reel_bot as _Rb  # noqa: E402
    chequear("reel de datos: 5 segundos por placa (3 placas = 15 s), en 4:5",
             abs(_Rb.motor().duration_seconds(_v) - 15) < 0.3)
_cap = RD.caption(_t(5, 0), ["alerta", "clima", "granos", "dolar", "chicago"])
chequear("texto del reel de datos: qué trae, sin links",
         "alertas del SMN" in _cap and "soja, el trigo y el maíz" in _cap and "http" not in _cap and "/n/" not in _cap)
chequear("a @diarioyradio van solo las de datos (clima, alertas, granos, dólar, Chicago), no las noticias",
         {"clima", "alerta", "granos", "dolar", "chicago"} <= _PUBd.TIPOS_AL_DIARIO
         and not {"titulares", "novedad", "mapa", "resumen"} & _PUBd.TIPOS_AL_DIARIO)
_env0 = {k: os.environ.get(k) for k in ("INSTAGRAM_USER_ID", "FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN")}
os.environ.update(INSTAGRAM_USER_ID="17841427698320458", FACEBOOK_PAGE_ID="101271341650483", FACEBOOK_PAGE_ACCESS_TOKEN="t")
try:
    _PUBd.credenciales_diario()
    _salva = False
except _PUBd.SalvaguardaAgro:
    _salva = True
os.environ.update(INSTAGRAM_USER_ID="17841405971293744", FACEBOOK_PAGE_ID="1456376377985890")
chequear("salvaguarda: lo «del diario» tiene que ser @diarioyradio (con las de agro, no)",
         _salva and _PUBd.credenciales_diario()["INSTAGRAM_USER_ID"] == "17841405971293744")
from reels import publicador as _PBd  # noqa: E402


class _Rta:
    def __init__(self, cod, d):
        self.status_code, self._d = cod, d

    def json(self):
        return self._d


_pedidos = []
_vistas = {"n": 0}


def _pedir_falso(metodo, url, tok, **kw):
    _pedidos.append((metodo, url.rsplit("/", 1)[-1], kw.get("data")))
    if metodo == "GET":
        _vistas["n"] += 1
        return _Rta(200, {"data": [{"media_id": "999"}] if _vistas["n"] >= 2 else []})
    return _Rta(200, {"success": True})


_o = (_PBd._pedir, _PBd._dormir)
_PBd._pedir, _PBd._dormir = _pedir_falso, lambda s: None
try:
    _res = _PUBd.aceptar_colab("999", log=lambda m: None)
finally:
    _PBd._pedir, _PBd._dormir = _o
chequear("colab: espera a que aparezca la invitación y la acepta con la cuenta del diario",
         _res == {"estado": "aceptada"} and _pedidos[-1] == ("POST", "collaboration_invites",
                                                             {"media_id": "999", "accept": "true"}))
for _k, _v0 in _env0.items():
    if _v0 is None:
        os.environ.pop(_k, None)
    else:
        os.environ[_k] = _v0


# --- el posteo de datos de las 05 como CARRUSEL, con el mapa de lluvia y la etiqueta de IA (24/10/2026) ---
from agro import mapa_lluvia as ML  # noqa: E402
from datetime import timezone as _tzu  # noqa: E402

chequear("posteo de datos: de fábrica es carrusel (AGRO_DATOS_FORMATO=reel vuelve al reel)",
         RD.formato() == "carrusel")
os.environ["AGRO_DATOS_FORMATO"] = "reel"
chequear("AGRO_DATOS_FORMATO=reel", RD.formato() == "reel")
os.environ.pop("AGRO_DATOS_FORMATO")
_t0 = datetime(2026, 10, 24, 8, 0, tzinfo=_tzu.utc)
_serie = ([{"time": (_t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": {"next_1_hours": {"details": {"precipitation_amount": 1.0}},
                     "next_6_hours": {"details": {"precipitation_amount": 6.0}}}} for h in range(60)]
          + [{"time": (_t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "data": {"next_6_hours": {"details": {"precipitation_amount": 3.0}}}} for h in range(60, 96, 6)])
_tot, _dias = ML.sumar(_serie, _t0, _t0 + timedelta(hours=72))
chequear("mapa: la lluvia se suma de a una hora y, donde el pronóstico va de a 6, de a 6 (sin contar dos veces)",
         abs(_tot - (60 + 2 * 3)) < 1e-6 and abs(sum(_dias.values()) - _tot) < 1e-6)


class _RtaMet:
    status_code = 200

    def __init__(self, mm):
        self._mm = mm

    def json(self):
        return {"properties": {"timeseries": [
            {"time": (_t0 + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "data": {"next_1_hours": {"details": {"precipitation_amount": self._mm}}}} for h in range(72)]}}


_pedidos_met = []


def _get_met(url, params):
    _pedidos_met.append(params)
    return _RtaMet(0.5 if float(params["lon"]) < -60 else 0.0)      # llueve al oeste de Chivilcoy


_ll = ML.lluvia(ahora=_t0, get=_get_met, log=lambda m: None)
chequear("mapa: una grilla de puntos alrededor de Chivilcoy, con Chivilcoy en el centro",
         len(_ll["grilla"]) == ML.NODOS + 2 and _ll["sin_dato"] == 0
         and all(abs(v_ - ML.LADO / 2) < 1e-6 for v_ in ML._xy(ML.CENTRO[1], ML.CENTRO[0]))
         and all(len(p_["lat"].split(".")[1]) <= 4 for p_ in _pedidos_met))
chequear("mapa: Chivilcoy por día y en total (para la portada)", abs(_ll["chivilcoy_total"] - 36) < 1e-6)
_ll_vacia = ML.lluvia(ahora=_t0, get=lambda u, p: type("R", (), {"status_code": 503})(), log=lambda m: None)
chequear("mapa: si MET Norway no contesta, no hay mapa (y el carrusel sale igual)", _ll_vacia is None)
with tempfile.TemporaryDirectory() as _tmpm:
    _pm = ML.placa(_ll, Path(_tmpm) / "mapa.jpg", _t0.date())
    from PIL import Image as _Imm  # noqa: E402
    chequear("mapa: la placa sale en 9:16 y en 4:5", _Imm.open(_pm).size == (1080, 1920)
             and _Imm.open(_HI.ruta_45(_pm)).size == (1080, 1350))
    _datos_c = {"pizarra": {"fecha": "2026-10-22", "productos": {"soja": {"ars": 550000, "usd": 380},
                                                                   "trigo": {"ars": 300000}}},
                "mayorista": {"fecha": "2026-10-23", "valor": 1528.26},
                "chicago": {"soja": {"fecha": "2026-10-23", "usd_t": 462.0, "cambio_pct": -2.4, "contrato": "X",
                                     "cent_bu": 1258}},
                "alertas": [], "pronostico": {}}
    _tab = RD.tablero(_datos_c, {}, _ll)
    chequear("portada: el tablero con soja, trigo, dólar, Chicago y la lluvia en Chivilcoy",
             [t_["rotulo"] for t_ in _tab] == ["SOJA ROSARIO", "TRIGO ROSARIO", "DÓLAR MAYORISTA", "SOJA CHICAGO",
                                               "LLUVIA EN CHIVILCOY"])
    chequear("portada: el gancho es el mayor movimiento, en pasado (los precios son del último cierre)",
             RD.gancho(_datos_c, _tab, {"chivilcoy_total": 2}) == "La soja bajó 2,4% en Chicago")
    chequear("portada: con 5 mm o más, el gancho es la lluvia; con una alerta, la alerta",
             RD.gancho(_datos_c, _tab, {"chivilcoy_total": 18.2}) == "Llegan 18 mm de lluvia a Chivilcoy"
             and RD.gancho(dict(_datos_c, alertas=[{"nivel": "amarilla", "evento": "Tormentas"}]), _tab, None)
             == "Alerta amarilla por tormentas en la zona")
    chequear("portada: dice de qué día es cada cierre",
             RD.cierres(_tab) == "Últimos cierres: Rosario 22/10 · dólar 23/10 · Chicago 23/10")
    _orig_lluvia = ML.lluvia
    ML.lluvia = lambda **k: _ll
    try:
        _lista, _ = RD.armar_carrusel(_datos_c, {}, Path(_tmpm), datetime(2026, 10, 24, 5, 0, tzinfo=CA.TZ_AR),
                                      log=lambda m: None)
    finally:
        ML.lluvia = _orig_lluvia
    _tipos = [x["tipo"] for x in _lista]
    chequear("carrusel: portada, mapa, los datos y el cierre (hasta 10), todo en 4:5",
             _tipos[:2] == ["portada", "mapa"] and _tipos[-1] == "cierre" and "granos" in _tipos
             and len(_lista) <= 10 and all(_Imm.open(x["archivo"]).size == (1080, 1350) for x in _lista))
    chequear("etiqueta de IA: cada diapositiva lleva el metadato IPTC que lee Meta",
             all(RD.IPTC_IA.encode() in (_Imm.open(x["archivo"]).info.get("xmp") or b"") for x in _lista))
    _cap = RD.caption_carrusel(datetime(2026, 10, 24, 5, 0, tzinfo=CA.TZ_AR), _datos_c, _tab)
    chequear("texto del carrusel: arranca con lo que se busca, dice la IA y no lleva links",
             _cap.startswith("🌾 EL CAMPO HOY · Sábado 24 de octubre: precio de la soja")
             and "generada con IA" in _cap and "Soja en Chicago" in _cap and "http" not in _cap and "/n/" not in _cap)

    # Publicar: Instagram CAROUSEL con @diarioyradio de colaborador y álbum de Facebook en las dos páginas.
    _llam = []
    _o2 = (_PBd._contenedor_listo, _PBd._publicar_contenedor, _PBd.subir_a_release, _PBd._pedir, _PUBd.aceptar_colab,
           _PUBd.credenciales_agro)
    from contextlib import contextmanager as _cm  # noqa: E402

    @_cm
    def _cred_falsas():
        yield {}

    def _pedir_fb(metodo, url, tok, **kw):
        _llam.append(("fb", url.rsplit("/", 1)[-1]))
        return _Rta(200, {"id": "f1", "post_id": "p1"})

    _PBd._contenedor_listo = lambda uid, tok, params: _llam.append(("ig", params.get("media_type") or "hijo",
                                                                     params.get("collaborators"))) or "c"
    _PBd._publicar_contenedor = lambda uid, tok, cid, cap: "m1"
    _PBd.subir_a_release = lambda ruta, nombre: f"https://gh/{nombre}"
    _PBd._pedir = _pedir_fb
    _PUBd.aceptar_colab = lambda mid, log=print: {"estado": "aceptada"}
    _PUBd.credenciales_agro = _cred_falsas
    os.environ.update(INSTAGRAM_USER_ID="17841405971293744", FACEBOOK_PAGE_ID="1456376377985890",
                      FACEBOOK_PAGE_ACCESS_TOKEN="t", INSTAGRAM_ACCESS_TOKEN="t")
    try:
        _res = RD.publicar_carrusel([x["archivo"] for x in _lista], _cap, log=lambda m: None)
    finally:
        (_PBd._contenedor_listo, _PBd._publicar_contenedor, _PBd.subir_a_release, _PBd._pedir, _PUBd.aceptar_colab,
         _PUBd.credenciales_agro) = _o2
        for _k, _v0 in _env0.items():
            if _v0 is None:
                os.environ.pop(_k, None)
            else:
                os.environ[_k] = _v0
    _padre = [x for x in _llam if x[0] == "ig" and x[1] == "CAROUSEL"]
    chequear("publicar: un carrusel de Instagram con @diarioyradio de colaborador, y la colab aceptada",
             len(_padre) == 1 and '"diarioyradio"' in (_padre[0][2] or "")
             and sum(1 for x in _llam if x[0] == "ig" and x[1] == "hijo") == len(_lista)
             and _res["instagram"]["colab"] == "@diarioyradio" and _res["colab"]["estado"] == "aceptada")
    chequear("publicar: álbum de Facebook en agro y en el diario (fotos sin publicar + un posteo)",
             _res["facebook"]["fotos"] == len(_lista) and _res["facebook_diario"]["fotos"] == len(_lista)
             and sum(1 for x in _llam if x == ("fb", "feed")) == 2)

# --- la corrida: publica lo suyo y espera el horario siguiente -------------------------------------
_reloj = {"t": _t(7, 2)}
_hechos, _durmio = [], []


def _turno_falso(publicar, tipo, horario, ahora, carpeta, **kw):
    _hechos.append((tipo, f"{horario:%H:%M}", f"{ahora:%H:%M}"))
    _reloj["t"] += timedelta(minutes=6)                # lo que tarda armar y publicar
    m = PA.cargar(PA.MEMORIA_REAL)
    if tipo == "historias":
        m.setdefault("historias", {})[horario.isoformat()] = {"dia": f"{ahora:%Y-%m-%d}", "publicado": {"estado": "listo"}, "items": [1]}
    else:
        m.setdefault("elegidas", []).append({"turno": horario.isoformat(), "cuando": ahora.isoformat(), "publicado": {"x": 1}, "titular": tipo})
    PA.guardar(m, ahora, PA.MEMORIA_REAL)
    carpeta.mkdir(parents=True, exist_ok=True)
    return PA._informe_vacio(carpeta, ahora, "prueba", True)


def _dormir_falso(seg):
    _durmio.append(round(seg / 60))
    _reloj["t"] += timedelta(seconds=seg)


with tempfile.TemporaryDirectory() as _tmpc:
    _o = (PA.MEMORIA_REAL, PA.SALIDA, PA._un_turno, PA._ahora, PA._dormir, PA.entorno.cargar, PA._guardar_en_la_nube)
    try:
        PA.MEMORIA_REAL, PA.SALIDA = Path(_tmpc) / "agro.json", Path(_tmpc) / "salida"
        PA._un_turno, PA._ahora, PA._dormir = _turno_falso, lambda: _reloj["t"], _dormir_falso
        PA.entorno.cargar = lambda: None
        PA._guardar_en_la_nube = lambda log=print: None
        PA.correr(publicar=True, momento=_reloj["t"], log=lambda m: None)
        chequear("corrida de las 07: historias y 5 reels, 20 min entre uno y otro (corridos por la demora)",
                 _hechos == [("historias", "07:00", "07:02"), ("reel", "07:00", "07:08"), ("reel", "07:20", "07:28"),
                             ("reel", "07:40", "07:48"), ("reel", "08:00", "08:08"), ("reel", "08:20", "08:28")]
                 and _durmio == [14, 14, 14, 14])
        _hechos.clear()
        _reloj["t"] = _t(7, 22)
        PA.correr(publicar=True, momento=_reloj["t"], log=lambda m: None)
        chequear("el respaldo de las 07:20 no repite nada", _hechos == [])
        _hechos.clear(), _durmio.clear()
        _reloj["t"] = _t(10, 38)                       # arrancó tarde
        PA.correr(publicar=True, momento=_reloj["t"], log=lambda m: None)
        chequear("si arrancó tarde (10:38), cada reel espera sus 20 minutos enteros",
                 [h[2] for h in _hechos] == ["10:38", "10:58", "11:18", "11:38", "11:58"] and _durmio == [14, 14, 14, 14])
        _hechos.clear()
        _reloj["t"] = _t(13, 1)

        def _falla_reel(publicar, tipo, horario, ahora, carpeta, **kw):
            if tipo == "reel" and f"{horario:%H:%M}" == "13:00":
                raise RuntimeError("se cayó la red")
            return _turno_falso(publicar, tipo, horario, ahora, carpeta, **kw)
        PA._un_turno = _falla_reel
        try:
            PA.correr(publicar=True, momento=_reloj["t"], log=lambda m: None)
            _aviso = False
        except RuntimeError as e:
            _aviso = "se cayó la red" in str(e)
        chequear("si un reel falla, igual sale el resto de la corrida, y la corrida avisa al final",
                 _aviso and [h[0] for h in _hechos] == ["reel", "reel", "historias", "reel", "reel"])
    finally:
        (PA.MEMORIA_REAL, PA.SALIDA, PA._un_turno, PA._ahora, PA._dormir, PA.entorno.cargar,
         PA._guardar_en_la_nube) = _o

# --- prioridades del documento «ideas agro» -------------------------------------------------------
_s = SC.limpiar({"tema_doc": "Clima", "urgente": "sí", "potencial_carrusel": 14})
chequear("puntaje: tema fundamental, urgente y potencial de carrusel",
         _s["tema_doc"] == "clima" and _s["urgente"] is True and _s["potencial_carrusel"] == 10)


def _cand(i, sub, sc, **kw):
    return {"id": i, "score": dict(SC.limpiar(dict({"subtema": sub}, **kw)), ai_score=sc, tema=i)}


_el, _ = SE.elegir([_cand("a", "agro", 82, tema_doc="reglas"), _cand("b", "agro", 78, tema_doc="clima"),
                    _cand("c", "mercados", 68, urgente=True, tema_doc="sanidad")], [], cupo_dia=6)
chequear("una URGENTE va primero (aunque tenga 68) y clima (78) le gana a reglas (82)",
         [c["id"] for c in _el] == ["c", "b", "a"])
_x, _y = _cand("x", "agtech", 80, potencial_carrusel=10), _cand("y", "agtech", 84, potencial_carrusel=2)
chequear("para el carrusel pesa lo que se puede explicar; para el reel, el puntaje",
         SE.elegir([_x, _y], [], formato="carrusel")[0][0]["id"] == "x"
         and SE.elegir([_x, _y], [], formato="reel")[0][0]["id"] == "y")

_hoy6 = [{"score": dict(SC.limpiar({"subtema": s_}), tema=f"t{i_}")} for i_, s_ in enumerate(("ganaderia", "mercados", "ganaderia", "mercados"))]
_pend = [_cand("g", "ganaderia", 77), _cand("m", "mercados", 76)]
chequear("13:00 del 17/10: con solo ganadería y mercados pendientes y su tope lleno, el horario no queda vacío",
         SE.elegir(_pend, _hoy6, cupo_dia=6)[0] == [] and SE.elegir(_pend, _hoy6, cupo_dia=6, relajar=True)[0][0]["id"] == "g")
chequear("topes de la mezcla hacia arriba (6 por día: 2 de mercados)", SE.topes(6)["mercados"] == 2)
_hoy_tema = [{"score": dict(SC.limpiar({"subtema": "ganaderia"}), tema="trazabilidad bovina")}]
chequear("relajado, nunca entra otra del mismo tema que algo de hoy",
         SE.elegir([dict(_cand("t", "ganaderia", 80), score=dict(_cand("t", "ganaderia", 80)["score"], tema="trazabilidad bovina"))],
                   _hoy_tema, cupo_dia=6, relajar=True)[0] == [])

# --- datos: granos, dólar, Chicago, clima y alertas (sin red) -------------------------------------
from agro import mercado as M  # noqa: E402
from datetime import date  # noqa: E402

_cac = ('<h3>Precios Pizarra del día 15/10/2026</h3> <div class="board board-trigo "> <div class="price"> $350.450,00 '
        '</div> <strong>US$</strong> 233,01 </div> <span class="direction fa fa-arrow-up"></span> '
        '<div class="board board-girasol estimative"> <div class="price"> <span> S/C </span> '
        '<span class="price-sc-estimated"> (E) $797.120,00</span> </div> <strong>US$</strong> <span> (E) </span> 530,00 '
        '</div> <span class="direction nofont">=</span> TC BNA Divisas Comprador 15/10/2026: $ 1.504,00')
_p = M.parsear_pizarra(_cac)
chequear("pizarra de Rosario: fecha, pesos, dólares, sentido y estimativo",
         _p["fecha"] == "2026-10-15" and _p["productos"]["trigo"] == {"ars": 350450.0, "usd": 233.01, "estimado": False,
                                                                       "direccion": "sube"}
         and _p["productos"]["girasol"]["estimado"] and _p["productos"]["girasol"]["ars"] == 797120.0
         and _p["productos"]["girasol"]["direccion"] == "igual" and _p["tc"] == 1504.0)
_b = M.parsear_bna("Cotización Billetes Cotización Divisas 16/10/2026 Compra Venta Dolar U.S.A 1485,00 1535,00 Euro 1 2 "
                   "Hora Actualización: 17:00 16/10/2026 Compra Venta Dolar U.S.A 1509.0000 1518.0000")
chequear("Banco Nación: billete y divisa con fecha y hora",
         _b["billete"] == {"fecha": "2026-10-16", "compra": 1485.0, "venta": 1535.0}
         and _b["divisa"]["venta"] == 1518.0 and _b["hora"] == "17:00")
chequear("números con coma, con punto y sin cotización",
         (M.numero("$1.504,00"), M.numero("1509.0000"), M.numero("S/C")) == (1504.0, 1509.0, None))
chequear("Chicago: el contrato más cercano que no venció",
         M.contrato("soja", date(2026, 10, 17)) == ("ZSX26.CBT", "nov-26")
         and M.contrato("soja", date(2026, 11, 14)) == ("ZSF27.CBT", "ene-27")
         and M.contrato("maiz", date(2026, 10, 17)) == ("ZCZ26.CBT", "dic-26"))
_pron = M.parsear_pronostico(" JUNIN_AERO\n ====\n      FECHA *   TEMPERATURA\n ====\n"
                             "  17/OCT/2026 00Hs.         6.1       149 |  12         0.0 \n"
                             "  17/OCT/2026 03Hs.         4.2       157 |  11         1.5 \n"
                             "  18/OCT/2026 00Hs.         4.9       103 |  9         0.0 \n")
chequear("pronóstico del SMN por estación y por día",
         M.por_dia(_pron["JUNIN_AERO"])["2026-10-17"] == {"max": 6.1, "min": 4.2, "mm": 1.5, "viento": 12})
_cap = ('<alert><info><event>Tormentas</event><severity>Severe</severity><onset>2026-10-16T15:00:00-03:00</onset>'
        '<expires>{hasta}</expires><description>Tormentas fuertes.</description><area><polygon>-34.5,-60.5 -34.5,-59.5 '
        '-35.3,-59.5 -35.3,-60.5 -34.5,-60.5</polygon></area></info></alert>')


class _R:
    def __init__(self, texto):
        self.text, self.status_code = texto, 200


def _get_cap(hasta):
    def get(url, **kw):
        if url == M.URL_SMN_CAP:
            return _R('<a href="https://ssl.smn.gob.ar/feeds/CAP/xml_generados/a.xml">x</a>'
                      '<a href="https://ssl.smn.gob.ar/feeds/CAP/xml_generados/a.xml">y</a>')
        return _R(_cap.format(hasta=hasta))
    return get


_al = M.alertas(_get_cap("2026-10-16T23:00:00-03:00"), momento=_t(18, 0))
chequear("alerta del SMN que toca la zona: nivel, lugares y sin repetir",
         len(_al) == 1 and _al[0]["nivel"] == "naranja" and "Chivilcoy" in _al[0]["lugares"])
chequear("una alerta vencida no sale", M.alertas(_get_cap("2026-10-16T12:00:00-03:00"), momento=_t(18, 0)) == [])
_mem = {}
M.anotar(_mem, "pizarra", "2026-10-14", {"productos": {"soja": {"ars": 550000}}}, hoy=date(2026, 10, 16))
M.anotar(_mem, "pizarra", "2026-10-15", {"productos": {"soja": {"ars": 560000}}}, hoy=date(2026, 10, 16))
M.anotar(_mem, "pizarra", "2026-08-01", {"productos": {}}, hoy=date(2026, 10, 16))
chequear("la memoria del mercado: rueda anterior, semana y se olvida lo viejo",
         M.anterior(_mem, "pizarra", "2026-10-15")[0] == "2026-10-14" and M.anterior(_mem, "pizarra", "2026-10-15", dias=7) is None
         and "2026-08-01" not in _mem["mercado"]["pizarra"] and M.variacion(560000, 550000) == 1.82)

# --- historias ------------------------------------------------------------------------------------
from PIL import Image  # noqa: E402
from agro import historias as HI  # noqa: E402

_dia = {f"2026-10-{d}": {"max": 20.0, "min": 8.0, "mm": 3.0, "viento": 20} for d in (16, 17, 18, 19, 20)}
_datos = {"pizarra": _p, "mayorista": {"fecha": "2026-10-16", "valor": 1514.56}, "bna": _b,
          "chicago": {g: {"contrato": "nov-26", "cent_bu": 1261.25, "usd_t": 463.4, "cambio_pct": -0.5,
                          "fecha": "2026-10-16"} for g in ("soja", "maiz", "trigo")},
          "pronostico": {e: dict(_dia) for e in M.ESTACIONES}, "alertas": []}
with tempfile.TemporaryDirectory() as tmp:
    _foto = Path(tmp) / "portada.jpg"
    Image.new("RGB", (1080, 1350), (90, 140, 60)).save(_foto)
    _rec = [{"titular": "La siembra de soja arranca con 2% más de área", "volanta": "Agricultura", "imagen": str(_foto)}]
    _nov = {"titular": "x", "formato": "reel", "portada": str(_foto)}
    _tandas = {b: HI.armar_tanda(b, _datos, _mem, Path(tmp) / b, _t(7, 0), _rec, _nov) for b in AG.BLOQUES}
    chequear("un día hábil: 4 + 3 + 3 = 10 historias",
             [len(v) for v in _tandas.values()] == [4, 3, 3]
             and [h["tipo"] for h in _tandas["manana"]] == ["clima", "granos", "dolar", "titulares"]
             and [h["tipo"] for h in _tandas["mediodia"]] == ["mapa", "chicago", "novedad"])
    chequear("todas las historias son 1080x1920",
             all(Image.open(h["archivo"]).size == (1080, 1920) for v in _tandas.values() for h in v))
    from PIL import ImageChops
    _fondo = HI.fondo().convert("L")

    def _fuera_de_zona(ruta):
        """¿Hay algo dibujado (distinto del fondo) arriba o abajo de la zona segura?"""
        dif = ImageChops.difference(Image.open(ruta).convert("L"), _fondo).point(lambda v: 255 if v > 40 else 0)
        return bool(dif.crop((0, 0, 1080, HI.SEGURA[0])).getbbox() or dif.crop((0, HI.SEGURA[1], 1080, 1920)).getbbox())
    chequear("historias: nada (marca, texto, fuente) cae debajo de los marcos de Instagram y Facebook",
             not any(_fuera_de_zona(h["archivo"]) for v in _tandas.values() for h in v))
    _sab = HI.armar_tanda("manana", _datos, _mem, Path(tmp) / "sab", datetime(2026, 10, 17, 7, 0, tzinfo=CA.TZ_AR), _rec, _nov)
    chequear("sábado a la mañana: clima, mapa, lo que tenés que saber y la novedad (sin mercados)",
             [h["tipo"] for h in _sab] == ["clima", "mapa", "titulares", "novedad"])
    _datos["alertas"] = [{"evento": "Tormentas", "nivel": "naranja", "desde": "2026-10-16T15:00:00-03:00",
                          "hasta": "2026-10-16T23:00:00-03:00", "descripcion": "Tormentas fuertes.", "lugares": ["Chivilcoy"]}]
    _con = HI.armar_tanda("cierre", _datos, _mem, Path(tmp) / "al", _t(19, 0), _rec, _nov)
    chequear("una alerta del SMN va PRIMERA en la tanda", _con[0]["tipo"] == "alerta" and len(_con) == 4)
    _sin = HI.armar_tanda("cierre", _datos, _mem, Path(tmp) / "al2", _t(19, 0), _rec, _nov, alertas_ya={_con[0]["clave"]})
    chequear("y no se repite en la tanda siguiente", [h["tipo"] for h in _sin] == ["granos", "dolar", "chicago"])
    _datos["alertas"] = []
    chequear("rótulo de fecha: dato de hoy o «último dato disponible»",
             HI.rotulo_fecha("2026-10-16", date(2026, 10, 16)).startswith("Dato de hoy")
             and HI.rotulo_fecha("2026-10-15", date(2026, 10, 16)) == "Último dato disponible: jueves 15/10")

    # --- carrusel ---------------------------------------------------------------------------------
    from agro import carrusel as CAR
    chequear("cifras del carrusel: las del material pasan, las inventadas no",
             CAR.cifras_ajenas("Subió 45% y 1.200 toneladas", "subió un 45 % con 1200 toneladas") == []
             and CAR.cifras_ajenas("Llega al 30%", "subió un 45 %") == ["30"])
    _g = dict(GU._salida(BUENA, "falsa"))
    _rep = {"titulo": "Biológicos en soja", "descripcion": "Ensayo del INTA con 12% más de rinde", "url": "u"}

    def _redactar_carrusel(system, material, max_tokens=0):
        return {"gancho": "¿Sirven los biológicos en soja?",
                "diapositivas": [{"titulo": "Qué pasó", "texto": "Un ensayo midió el efecto de los biológicos."},
                                 {"titulo": "El número", "texto": "Más rinde en los lotes tratados.", "dato": "12%",
                                  "dato_rotulo": "más de rinde"},
                                 {"titulo": "Inventado", "texto": "Y bajó 37% el costo."},
                                 {"titulo": "Qué cambia", "texto": "Conviene probarlo en una franja del lote."}],
                "pregunta": "¿Los probaste?"}, "falsa"
    _c = CAR.contenido(_g, _rep, "", redactar=_redactar_carrusel)
    chequear("carrusel: la diapositiva con una cifra inventada se saca, las demás quedan",
             [d["titulo"] for d in _c["diapositivas"]] == ["Qué pasó", "El número", "Qué cambia"] and len(_c["quitadas"]) == 1)

    def _ia_caida(*a, **k):
        raise RuntimeError("sin cupo")
    _c2 = CAR.contenido(_g, _rep, "", redactar=_ia_caida)
    chequear("carrusel: con la IA caída se arma igual con el guion del reel",
             _c2["via"] == "guion del reel" and len(_c2["diapositivas"]) >= 2)
    _arch = CAR.armar(_g, _c, str(_foto), Path(tmp), "prueba", "grafito", "Imagen generada con IA")
    chequear("carrusel: tapa + 3 diapositivas + cierre, todas 4:5",
             len(_arch) == 5 and all(Image.open(a).size == (1080, 1350) for a in _arch))
    chequear("el texto del carrusel invita a deslizar", "Deslizá e informate" in CAR.caption(_g))
    _msem = {"mercado": {"pizarra": {"2026-10-09": {"productos": {"soja": {"ars": 540000}}},
                                     "2026-10-16": {"productos": {"soja": {"ars": 560000}}}},
                         "a3500": {"2026-10-09": {"valor": 1500.0}, "2026-10-16": {"valor": 1514.0}},
                         "chicago_soja": {"2026-10-09": {"usd_t": 470.0}, "2026-10-16": {"usd_t": 463.4}}}}
    _sem = CAR.numeros_semana(_msem, _datos, Path(tmp), date(2026, 10, 17), str(_foto))
    chequear("sábado: «Los números de la semana» con granos, Chicago, dólar y lluvias",
             _sem and len(_sem["archivos"]) == 6 and "+3,7%" in " ".join(
                 p for d in _sem["contenido"]["diapositivas"] for p in d.get("puntos", [])))

    # --- imagen: la foto de un medio se RECREA con IA ----------------------------------------------
    def _bajar(url, destino):
        Image.new("RGB", (1200, 800), (100, 120, 80)).save(destino)
        return destino
    _llamadas = []

    def _recrear(foto, destino, contexto="", variante=0):
        _llamadas.append(variante)
        Image.new("RGB", (1024, 768), (80, 120, 60)).save(destino)
        return {"archivo": str(destino)}
    _medio = {"id": "m1", "fuente": "Infocampo", "tipo_fuente": "medio"}
    _r = IMG.elegir(_medio, "https://x/reuters-foto.jpg", "soy", Path(tmp) / "im.jpg", bajar=_bajar, mirar=lambda f: False,
                    recrear_con=_recrear, generar=lambda *a, **k: {"motivo": "no se usa"})
    chequear("foto de agencia de un medio → recreada con IA (nunca tal cual)",
             _r["origen"] == "recreada" and "recreada" in _r["archivo"] and _llamadas == [0])
    _r = IMG.elegir(_medio, "https://x/reuters-foto.jpg", "soy", Path(tmp) / "im2.jpg", bajar=_bajar,
                    mirar=lambda f: "recreada" in f, recrear_con=_recrear,
                    generar=lambda texto, destino, estilo="": (Image.new("RGB", (64, 64)).save(destino) or {"archivo": str(destino)}))
    chequear("si la recreación trae letras dos veces → la escena con IA de siempre",
             _r["origen"] == "ia" and "recreación" in _r["motivo"])

    # --- historias en modo real: se anotan y el respaldo no las repite -------------------------------
    import json as _json2
    _orig = (PA.MEMORIA_REAL, M.leer_todo, PA.entorno.cargar, PA.corrida, PA.SALIDA, PA._ahora)
    try:
        PA.MEMORIA_REAL, PA.SALIDA = Path(tmp) / "agro_real.json", Path(tmp) / "salida"
        PA.entorno.cargar = lambda: None
        M.leer_todo = lambda mem, get=None, momento=None, log=print: _datos
        _pub = []

        def _publicador_hist(tanda, log=print):
            _pub.append([h["tipo"] for h in tanda])
            return {"items": [{"instagram": {"id": "i"}, "facebook": {"id": "f"}} for _ in tanda]}
        PA.corrida = lambda ahora: (_t(18, 0), True, [(_t(19, 0), "historias")])
        PA._ahora = lambda: _t(19, 5)
        PA.correr(publicar=True, publicador=_publicador_hist, momento=_t(19, 5), log=lambda m: None)
        _mr = _json2.loads(PA.MEMORIA_REAL.read_text(encoding="utf-8"))
        _h = _mr["historias"][_t(19, 0).isoformat()]
        chequear("historias reales: «Así cerró el mercado» publicada y anotada (sin rutas locales)",
                 _pub == [["granos", "dolar", "chicago"]] and _h["publicado"]["estado"] == "listo"
                 and all("archivo" not in i and i["publicado"]["instagram"] == {"id": "i"} for i in _h["items"]))
        PA._ahora = lambda: _t(19, 25)
        PA.correr(publicar=True, publicador=_publicador_hist, momento=_t(19, 25), log=lambda m: None)
        chequear("el respaldo de las 19:20 no las vuelve a publicar", len(_pub) == 1)
    finally:
        PA.MEMORIA_REAL, M.leer_todo, PA.entorno.cargar, PA.corrida, PA.SALIDA, PA._ahora = _orig

# --- publicar: reel en 9:16 para Facebook, portada para las historias ------------------------------
_pp = PUBA.pieza_publicador({"guion": dict(GU._salida(BUENA, "x")), "portada": "p.jpg", "rep": {"url": "u"},
                             "reel": {"alto": 1350}})
chequear("el reel 4:5 le avisa a Facebook su alto (va con bandas a 9:16)", _pp["video"]["alto"] == 1350)
_orig_pub = (PUBA.publicar_carrusel, PUBA.publicar_reel, PUBA._subir_portada)
try:
    PUBA.publicar_carrusel = lambda pieza, ya=None, log=print: {"instagram": {"id": "car"}}
    PUBA.publicar_reel = lambda pieza, ya=None, redes=None, log=print, portada_url="": {
        "instagram": {"id": "reel", "cover": portada_url}}
    PUBA._subir_portada = lambda pieza: "https://release/portada.jpg"
    chequear("publicar elige por formato y devuelve la portada subida",
             PUBA.publicar({"formato": "carrusel"})["instagram"]["id"] == "car"
             and PUBA.publicar({"formato": "reel"}) == {"instagram": {"id": "reel", "cover": "https://release/portada.jpg"},
                                                        "portada_url": "https://release/portada.jpg"})
finally:
    PUBA.publicar_carrusel, PUBA.publicar_reel, PUBA._subir_portada = _orig_pub

# --- la memoria agro en la nube: historias y mercado tampoco se pierden ----------------------------
_a = {"historias": {"h1": {"publicado": {"estado": "publicando"}}}, "mercado": {"pizarra": {"2026-10-15": {}}},
      "tema_ultimo": "blanco", "actualizado": "2026-10-16T08:00"}
_b2 = {"historias": {"h1": {"publicado": {"estado": "listo"}}, "h2": {"publicado": {"estado": "listo"}}},
       "mercado": {"pizarra": {"2026-10-16": {}}, "a3500": {"2026-10-16": {}}}, "tema_ultimo": "grafito",
       "actualizado": "2026-10-16T09:00"}
for _mio, _rem in ((_a, _b2), (_b2, _a)):
    _c3 = GE.COMBINAR["agro.json"](_mio, _rem)
    chequear("combinar agro.json: historias publicadas, datos del mercado y el tema del último posteo",
             _c3["historias"]["h1"]["publicado"]["estado"] == "listo" and set(_c3["historias"]) == {"h1", "h2"}
             and set(_c3["mercado"]["pizarra"]) == {"2026-10-15", "2026-10-16"} and _c3["tema_ultimo"] == "grafito")

# --- la miniatura con texto SEO (17/10/2026) ------------------------------------------------------
from agro import diseno as DIS  # noqa: E402
from reels import publicador as _PB  # noqa: E402

_gs = GU._salida(dict(BUENA, portada="Soja: arranca la siembra con 2% más de área en la zona núcleo hoy"), "x")
chequear("guion: el texto de la miniatura (hasta 9 palabras, palabra clave primero)",
         _gs["portada_seo"].startswith("Soja:") and len(_gs["portada_seo"].split()) <= 9)
chequear("sin texto de miniatura, va el titular", DIS.texto_portada({"titular": "Trigo en alza"}) == "Trigo en alza")
_pl = DIS.plan_bloque("Agricultura", "Soja: arranca la siembra", "blanco", 810, tope=DIS.PORTADA)
chequear("miniatura: letra más grande que el titular y la clave en naranja",
         _pl["f_tit"].size >= DIS.TITULAR[0] and _pl["clave"] == "Soja:"
         and DIS.plan_bloque("x", "Soja: algo", "blanco", 810)["clave"] == "")
_guard = (_PB.subir_a_release, _PB._contenedor_listo, _PB._publicar_contenedor)
try:
    _params = []
    _PB.subir_a_release = lambda f, n: "https://release/" + n
    _PB._contenedor_listo = lambda uid, tok, params: _params.append(dict(params)) or "c1"
    _PB._publicar_contenedor = lambda uid, tok, cid, cap: "m1"
    _r = PUBA._reel_instagram({"descripcion_tiktok": "texto"}, Path("x.mp4"), "agro_x.mp4", "https://release/portada.jpg")
    chequear("Instagram: el reel sale con la portada propia como miniatura (cover_url)",
             _params[0].get("cover_url") == "https://release/portada.jpg" and _r == {"id": "m1", "portada": "propia"})
finally:
    _PB.subir_a_release, _PB._contenedor_listo, _PB._publicar_contenedor = _guard

# --- Foto ORIGINAL primero (18/10/2026, «tratá de usar la imagen original si podés, siempre») -----------
with tempfile.TemporaryDirectory() as _t0:
    from PIL import Image as _Im0
    _gen0, _baj0 = [], []

    def _bajar0(url, ruta):
        _baj0.append(url)
        _Im0.new("RGB", (1200, 800), (80, 120, 60)).save(ruta)
        return True

    def _generar0(*a, **k):
        _gen0.append(a)
        return {"archivo": None, "motivo": "no se tenía que llamar"}

    _rep0 = {"id": "x", "fuente": "Infocampo", "titulo": "t", "tipo_fuente": "medio"}
    _r = IMG.elegir(_rep0, "https://foto/medio.jpg", "soy", Path(_t0) / "a.jpg", generar=_generar0,
                    bajar=_bajar0, mirar=lambda f: False, recrear_con=lambda *a, **k: _gen0.append(a) or {})
    chequear("original: la foto del otro medio va TAL CUAL, con su crédito, sin tocar la IA",
             _r["origen"] == "fuente" and _r["credito"] == "Infocampo" and "_original" in _r["archivo"] and not _gen0)
    _r = IMG.elegir(_rep0, "https://foto/reuters-soja.jpg", "soy", Path(_t0) / "b.jpg", generar=_generar0,
                    bajar=_bajar0, mirar=lambda f: False,
                    recrear_con=lambda f, d, c="", variante=0: (_Im0.new("RGB", (900, 600)).save(d), {"archivo": str(d)})[1])
    chequear("original: la de agencia (Reuters) no va tal cual: se recrea con IA",
             _r["origen"] == "recreada" and "agencia" not in (_r.get("credito") or ""))
    _r = IMG.elegir(_rep0, "https://foto/placa.jpg", "soy", Path(_t0) / "c.jpg", generar=_generar0,
                    bajar=_bajar0, mirar=lambda f: "_original" in f or "_fuente" in f,
                    recrear_con=lambda f, d, c="", variante=0: (_Im0.new("RGB", (900, 600)).save(d), {"archivo": str(d)})[1])
    chequear("original: con letras (placa del medio) → recién ahí la IA", _r["origen"] == "recreada")
    os.environ["AGRO_IMAGEN_IA"] = "0"
    _gen0.clear()
    _r = IMG.elegir(_rep0, "https://foto/placa.jpg", "soy", Path(_t0) / "d.jpg", generar=_generar0,
                    bajar=_bajar0, mirar=lambda f: True, recrear_con=lambda *a, **k: _gen0.append(a) or {})
    chequear("AGRO_IMAGEN_IA=0: sin original usable → «ninguna», nada de IA",
             _r["origen"] == "ninguna" and not _gen0)
    os.environ["AGRO_IMAGEN_IA"] = "1"


# 26/10/2026: media_publish de una historia contestó «No se encuentra el contenido multimedia…» (FalloRed):
# se arma un contenedor nuevo en vez de dejar la corrida en rojo; si sigue fallando, se avisa.
from reels import publicador as _PBh  # noqa: E402
_orig_h = (_PBh._contenedor_listo, _PBh._publicar_contenedor, _PBh._dormir)
_cont_h, _resp_h = [], []


def _publicar_h(uid, tok, cid, caption):
    r = _resp_h.pop(0)
    if isinstance(r, Exception):
        raise r
    return r


_PBh._contenedor_listo = lambda uid, tok, params: _cont_h.append(params) or f"c{len(_cont_h)}"
_PBh._publicar_contenedor = _publicar_h
_PBh._dormir = lambda s: None
_resp_h[:] = [_PBh.FalloRed("Instagram: publicar: HTTP 400 — No se encuentra el contenido multimedia"), "1789"]
chequear("historia IG: «no se encuentra el contenido» → contenedor nuevo y sale",
         PUBA._historia_instagram("https://x/h.jpg") == {"id": "1789"} and len(_cont_h) == 2)
_cont_h.clear()
_resp_h[:] = [_PBh.FalloRed("x")] * 3
try:
    PUBA._historia_instagram("https://x/h.jpg")
    _sigue = False
except _PBh.FalloRed:
    _sigue = True
chequear("historia IG: si falla las 3 veces, avisa (no se queda callada)", _sigue and len(_cont_h) == 3)
_cont_h.clear()
_resp_h[:] = [_PBh.SinConfirmar("y")]
try:
    PUBA._historia_instagram("https://x/h.jpg")
    _dup = False
except _PBh.SinConfirmar:
    _dup = len(_cont_h) == 1
chequear("historia IG: sin confirmar NO se repite (podría haber salido)", _dup)
_PBh._contenedor_listo, _PBh._publicar_contenedor, _PBh._dormir = _orig_h


# --- priorizar notas con video corto (31/10/2026) ---------------------------------------------------
_s = {"ai_score": 70, "subtema": "agro", "commercial_score": 1}
chequear("video: el bono suma a la prioridad del reel (no al carrusel)",
         SE.prioridad(dict(_s, con_video=True))[1] == SE.prioridad(_s)[1] + SE.bono_video()
         and SE.prioridad(dict(_s, con_video=True), "carrusel") == SE.prioridad(_s, "carrusel"))
_cands = [{"id": f"c{i}", "rep": {"url": f"u{i}"}, "score": dict(_s, ai_score=80 - i)} for i in range(4)]
_cands.append({"id": "baja", "rep": {"url": "ub"}, "score": dict(_s, ai_score=10)})
_vistas = []


def _completar_f(rep):
    _vistas.append(rep["url"])
    return {"ok": True, "cuerpo": "x", "video": "https://v/1.mp4" if rep["url"] in ("u1", "u2") else ""}


_bajados = []


def _bajar_f(rep, completo, base):
    _bajados.append(rep["url"])
    return base.with_suffix(".mp4") if rep["url"] == "u1" else None        # u2: video de más de 90 s


with tempfile.TemporaryDirectory() as _tv:
    os.environ["AGRO_VIDEO_REVISAR"] = "3"
    _n = PA.marcar_videos(_cands, Path(_tv), log=lambda *a: None, completar=_completar_f, bajar=_bajar_f)
    os.environ.pop("AGRO_VIDEO_REVISAR")
chequear("video: abre solo las mejores (AGRO_VIDEO_REVISAR) y nunca las de puntaje bajo",
         _vistas == ["u0", "u1", "u2"])
chequear("video: baja solo las que traen video y marca la que sirve (con el clip y la nota leída)",
         _n == 1 and _bajados == ["u1", "u2"] and _cands[1]["score"].get("con_video") and _cands[1]["clip"]
         and _cands[1]["completo"]["cuerpo"] == "x" and not _cands[2]["score"].get("con_video"))
_eleg, _ = SE.elegir([dict(c) for c in _cands[:3]], [], cupo_dia=10)
chequear("video: con el bono, la de video pasa adelante de una de más puntaje", _eleg[0]["id"] == "c1")
chequear("video: máximo 1 minuto y medio (AGRO_VIDEO_MAX_SEG)", PA.video_max_seg() == 90)
_ld = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"VideoObject",'
       '"name":"Granizo","embedUrl":"https://cdn.jwplayer.com/videos/abc-x.mp4","duration":"PT0M46S"}</script>')
chequear("video: el VideoObject del JSON-LD (LA NACION) da el .mp4 y su duración",
         CA.video_de_jsonld(_ld) == ("https://cdn.jwplayer.com/videos/abc-x.mp4", 46.0)
         and CA.video_de_jsonld("<html>sin video</html>") == ("", 0.0) and CA._segundos_iso("PT1M30S") == 90)
chequear("video: si el medio dice que dura más de 90 s, ni se baja",
         PA._clip_de_la_fuente({}, {"video": "https://x/v.mp4", "video_seg": 300}, Path("x")) is None)


print(f"\n{total - len(fallas)}/{total} bien")
sys.exit(1 if fallas else 0)
