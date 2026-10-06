# -*- coding: utf-8 -*-
"""Noticias nacionales (nacionales/), sin red: filtro, guion, placa propia, topes y carrusel.

    venv\\Scripts\\python.exe tools\\test_nacionales.py

Las redes, la IA y el motor de video se reemplazan: lo que se prueba es qué se elige, qué se
publica, dónde y cuántas veces.
"""
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")     # la consola de Windows es cp1252
from PIL import Image

from nacionales import filtro as F, guion as NG, infobae as IB, pasada as PA, placa as P
from reels import publicador as PUB, web as WEB
from tools import guardar_estado as GE

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


AHORA = time.time()


def nota(titulo, seccion="politica", cuerpo="", horas=1, slug=None):
    return {"url": f"https://www.infobae.com/{seccion}/2026/10/06/{slug or abs(hash(titulo)) % 10**8}/",
            "seccion_feed": seccion, "titulo": titulo, "resumen": "", "cuerpo": cuerpo or titulo,
            "fecha": AHORA - horas * 3600}


# --- 1. Filtro ------------------------------------------------------------------------------
p = F.puntuar(nota("Choque en Floresta", "sociedad", "Ocurrió en Avenida Gaona y Chivilcoy, en Floresta."), AHORA)
chequear("filtro: la calle Chivilcoy de Floresta NO es Chivilcoy", p[1] != "Chivilcoy")
p = F.puntuar(nota("Los municipios con más presión tributaria", "politica",
                   "La lista. Al tope aparecen San Pedro y Chivilcoy (0,75%)."), AHORA)
chequear("filtro: Chivilcoy en el cuerpo de la nota la pone primera", p[0] == 100 and p[1] == "Chivilcoy")
chequear("filtro: la Ruta 5 es directa", F.puntuar(nota("Amparo para la autovía de la Ruta 5"), AHORA)[1] == "directa")
chequear("filtro: el subte porteño queda afuera",
         F.puntuar(nota("Paro en la línea A del subte", "sociedad"), AHORA)[0] == 0)
chequear("filtro: lo local de otra provincia queda afuera",
         F.puntuar(nota("Santa Fe prohibió a los cuidacoches", "sociedad"), AHORA)[0] == 0)
chequear("filtro: el exterior sin la Argentina queda afuera",
         F.puntuar(nota("Bolsonaro ganó en Brasil", "politica"), AHORA)[0] == 0)
chequear("filtro: el exterior CON la Argentina entra",
         F.puntuar(nota("Qué impacto tendrá en la Argentina el resultado de Brasil", "politica"), AHORA)[0] > 0)
chequear("filtro: las internas políticas entran (pedido del 06/10)",
         F.puntuar(nota("Crece la puja por la sucesión de Kicillof entre los intendentes"), AHORA)[0] >= F.UMBRAL)
chequear("filtro: los juicios entran",
         F.puntuar(nota("Juicio de los Cuadernos: siguen declarando los testigos", "judiciales"), AHORA)[0] >= F.UMBRAL)
chequear("filtro: ANSES va por el bolsillo",
         F.puntuar(nota("ANSES: cuándo cobro en octubre si mi DNI termina en 4", "economia"), AHORA)[1] == "bolsillo")
chequear("filtro: la salud de revista de afuera queda afuera",
         F.puntuar(nota("Chía con agua o leche: qué cambia en la saciedad", "salud"), AHORA)[0] == 0)
chequear("filtro: lo de hace dos días ya no", F.puntuar(nota("ANSES: cuándo cobro", "economia", horas=40), AHORA)[0] == 0)

lujan = [nota(t, "sociedad", slug=f"lujan{i}") for i, t in enumerate([
    "Peregrinación a Luján: miles de fieles marchan hacia la Basílica",
    "Peregrinación a Luján en vivo: los peregrinos llegan a la Basílica",
    "Peregrinación a Luján: el operativo y las recomendaciones para los peregrinos",
    "Peregrinación a Luján: las mejores fotos de la caminata hacia la Basílica"])]
suelto = nota("Renunció el interventor del ENACOM y el Gobierno designó a su sucesor", slug="enacom")
policial_chico = nota("Robaron una moto en Quilmes", "sociedad/policiales", slug="moto")
c = F.candidatas(lujan + [suelto, policial_chico], AHORA)
tema_lujan = [x for x in c if "Luján" in x["titulo"]]
chequear("cobertura: cuatro notas del mismo tema son UNA candidata", len(tema_lujan) == 1)
chequear("cobertura: ...y el tema grande pasa adelante del suelto",
         tema_lujan and tema_lujan[0]["cobertura"] == 4 and c[0] is tema_lujan[0])
chequear("cobertura: un policial de otro lado sin repercusión no entra",
         not any("Quilmes" in x["titulo"] for x in c))
chequear("ya contado: el mismo tema no se repite",
         F.ya_contado(lujan[1], [{"titulo": "x", "tema": tema_lujan[0]["tema"]}]) != "")
chequear("ya contado: otro tema sí sale",
         F.ya_contado(suelto, [{"titulo": "x", "tema": tema_lujan[0]["tema"]}]) == "")
chequear("filtro: «San Pedro y Chivilcoy» es la ciudad, «Avenida Gaona y Chivilcoy» la calle",
         F.nombra_chivilcoy("Aparecen San Pedro y Chivilcoy.") and
         not F.nombra_chivilcoy("Chocó en Avenida Gaona y Chivilcoy, en Floresta."))

# --- 2. Infobae --------------------------------------------------------------------------------
xml = """<?xml version="1.0"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Título de prueba</title><link>https://www.infobae.com/politica/2026/10/06/nota/</link>
<pubDate>Tue, 06 Oct 2026 12:00:00 +0000</pubDate><description>Resumen</description>
<content:encoded><![CDATA[<p>Primer párrafo.</p><p>Segundo.</p>]]></content:encoded></item>
<item><title>Otra</title><link>https://otro.sitio/nota</link></item></channel></rss>"""
ns = IB.notas_del_feed(xml, "politica")
chequear("Infobae: lee título, texto completo y fecha del feed",
         len(ns) == 1 and ns[0]["cuerpo"] == "Primer párrafo. Segundo." and ns[0]["fecha"] > 0)
chequear("Infobae: la foto ni se guarda (placa propia)", "imagen" not in ns[0])

# --- 3. Guion -----------------------------------------------------------------------------------
BUENO = {"apta": True, "seccion": "Economía", "volanta": "ANSES", "titular": "Los jubilados cobran con bono en octubre",
         "bajada": "El organismo confirmó el calendario.", "descripcion": "Uno. Dos.", "hashtags": ["#Jubilados", "#ANSES"],
         "potencial_viral": 8, "titulo_web": "ANSES: cuándo cobran los jubilados en octubre",
         "nota_web": ("Párrafo uno con datos del calendario de pagos de la ANSES para este mes. " * 3 + "\n\n") * 3}
pedidos = []


def redactar_falso(respuestas):
    def r(system, material):
        pedidos.append((system, material))
        return dict(respuestas.pop(0)), "falso"
    return r


n_anses = nota("ANSES: cuándo cobro en octubre si mi DNI termina en 4", "economia",
               "El calendario de pagos de la ANSES para octubre arranca el lunes con los DNI terminados en cero.")
g = NG.generar(n_anses, redactar_falso([BUENO]))
chequear("guion: sale apto con sus campos", g["apta"] and g["viral"] == 8 and g["seccion"] == "Economía")
chequear("guion: el material NO nombra a Infobae", "infobae" not in pedidos[-1][1].lower())
calcado = dict(BUENO, bajada="El calendario de pagos de la ANSES para octubre arranca el lunes con los DNI terminados en cero.")
pedidos.clear()
g = NG.generar(n_anses, redactar_falso([calcado, BUENO]))
chequear("guion: si calca el original, pide una segunda versión y queda la buena",
         len(pedidos) == 2 and "SEGUNDO PEDIDO" in pedidos[1][0] and g["copia"]["racha"] < 10)
g = NG.generar(n_anses, redactar_falso([dict(BUENO, titular="Según Infobae, los jubilados cobran"),
                                        dict(BUENO, titular="Según Infobae, cobran")]))
chequear("guion: si nombra a Infobae no se publica", not g["apta"])
g = NG.generar(n_anses, redactar_falso([dict(BUENO, nota_web="corta")]))
chequear("guion: sin nota de la web no se publica (Facebook no tendría a dónde mandar)", not g["apta"])
pedidos.clear()
n_chivi = nota("Presión tributaria", "politica", "Arranque. " * 200 + "Al tope aparecen San Pedro y Chivilcoy (0,75%).")
NG.generar(n_chivi, redactar_falso([BUENO]))
chequear("guion: el dato de Chivilcoy (lejos del arranque) le llega a la IA",
         "Lo que dice de Chivilcoy" in pedidos[-1][1] and "0,75%" in pedidos[-1][1])
txt = NG.texto_posteo(dict(BUENO, hashtags=["#Jubilados"]), "https://x/n/a")
chequear("guion: el texto de YouTube cierra con el link de la nota y los hashtags",
         "📲 Leé la nota completa: https://x/n/a" in txt and txt.rstrip().endswith("#Argentina"))

# --- 4. Placa propia ------------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp(prefix="nac_"))
f1 = P.fondo("Economía", (1080, 1920), 7)
chequear("placa: el fondo es 9:16 y siempre igual para la misma pieza",
         f1.size == (1080, 1920) and f1.tobytes()[:5000] == P.fondo("Economía", (1080, 1920), 7).tobytes()[:5000])
from reels import reel_bot as R
P.guardar_fondo("Política", tmp / "f.jpg")
chequear("placa: el motor la toma como FOTO, no como afiche (si no, no le pone el titular)",
         not R.motor()._es_grafica(tmp / "f.jpg", tmp))
s = P.slide("Política", "Interna", "Un titular de prueba para la diapositiva", tmp / "s.jpg", sitio="x", idx=2, total=5)
chequear("placa: la diapositiva es 4:5 (Instagram pide la misma proporción en todo el carrusel)",
         Image.open(s).size == (1080, 1350))
t = P.portada_carrusel(["Uno", "Dos", "Tres"], datetime(2026, 10, 6, 22), tmp / "t.jpg")
chequear("placa: la tapa del carrusel también es 4:5", Image.open(t).size == (1080, 1350))
chequear("placa: la imagen de la web es 1200x675",
         Image.open(P.portada_web("Salud", "Dengue", "Titular", tmp / "w.jpg")).size == (1200, 675))
chequear("placa: la fecha en castellano", P.fecha_larga(datetime(2026, 10, 6)) == "martes 6 de octubre")

# --- 5. La pasada, con todo reemplazado --------------------------------------------------------
AR = timezone(timedelta(hours=-3))
estado_tmp = tmp / "estado"
PA.MEMORIA = estado_tmp / "nacionales.json"
PA.SALIDA = tmp / "salida"
reloj = {"ahora": datetime(2026, 10, 6, 12, 5, tzinfo=AR)}
PA._ahora = lambda: reloj["ahora"]
dormido = []
PA._dormir = lambda s: dormido.append(s) or reloj.__setitem__("ahora", reloj["ahora"] + timedelta(seconds=s))
llamadas = []


def armar_reel(guion, salida, foto=None, clip=None):
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_bytes(b"mp4")
    return {"archivo": str(salida), "duracion": 12.9, "placa": None}


R.armar = armar_reel
PUB.publicar_youtube = lambda pieza, mp4, meta=None: llamadas.append(("youtube", meta["snippet"]["description"])) or {
    "id": f"yt{len(llamadas)}", "url": "https://youtube.com/shorts/x"}
PUB.subir_a_release = lambda ruta, nombre: llamadas.append(("release", nombre)) or f"https://gh/{nombre}"
web_falla = {"si": False}


def web_falsa(pedir, pieza, yt, foto_respaldo="", categorias=None):
    llamadas.append(("web", tuple(categorias or ()), yt))
    if web_falla["si"]:
        raise WEB.FalloWeb("Wix caído")
    slug = WEB.slug_de(pieza)
    return {"id": "w", "slug": slug, "url": WEB.link(slug)}


WEB.publicar = web_falsa
PA.publicar_foto_facebook = lambda jpg, msg: llamadas.append(("facebook", msg)) or {"id": "fb"}
PA._yt_cambiar_descripcion = lambda vid, meta: llamadas.append(("yt_desc", meta["snippet"]["description"]))
PUB._contenedor_listo = lambda uid, tok, params: llamadas.append(("ig_contenedor", params.get("media_type") or "hijo")) or "c"
PUB._publicar_contenedor = lambda uid, tok, cid, cap: llamadas.append(("ig_publicar", cap)) or "media"

notas = [nota(f"ANSES: cuándo cobran los jubilados con el bono {i}", "economia", slug=f"anses{i}") for i in range(1)] + [
    nota("Paro general: la CGT confirmó la fecha y qué servicios se ven afectados", "politica", slug="paro"),
    nota("Feriado del 12 de octubre: cuándo es el fin de semana largo", "sociedad", slug="lujan"),
    nota("Juicio de los Cuadernos: siguen declarando los testigos", "judiciales", slug="cuadernos"),
    nota("Crece la puja por la sucesión de Kicillof entre los intendentes", "politica", slug="interna")]
TODAS = list(notas)
virales = {"anses0": 9, "paro": 8, "lujan": 7, "cuadernos": 5, "interna": 4}


def redactar_por_nota(system, material):
    titulo = material.split("Titular original: ")[1].split("\n")[0]
    clave = next(n["url"].rstrip("/").rsplit("/", 1)[1] for n in TODAS if n["titulo"].startswith(titulo[:30]))
    return dict(BUENO, titular=titulo[:80], potencial_viral=virales[clave],
                titulo_web=f"{titulo[:60]} nota web"), "falso"


inf = PA.pasada(True, redactar=redactar_por_nota, notas=notas)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
redes = [l[0] for l in llamadas]
chequear("pasada: 3 piezas por pasada", len(inf["piezas"]) == 3 and len(mem["piezas"]) == 3)
chequear("pasada: orden por pieza YouTube → web → Facebook",
         redes[:3] == ["youtube", "release", "web"] and "facebook" in redes)
chequear("pasada: la nota va a Nacionales + la categoría que la saca de la portada",
         all(l[1] == (WEB.NACIONALES_ID, WEB.NACIONALES_AUTO_ID) for l in llamadas if l[0] == "web"))
chequear("pasada: la web lleva el Short adentro", all(l[2] for l in llamadas if l[0] == "web"))
chequear("pasada: Facebook solo 2 por pasada, las MÁS virales",
         redes.count("facebook") == 2 and {p["viral"] for p in inf["piezas"] if p.get("facebook")} == {9, 8})
desc_yt = [l[1] for l in llamadas if l[0] == "youtube"][0]
url_nota = [p["web"]["url"] for p in inf["piezas"]][0]
chequear("pasada: el Short sale con el link de SU nota (el slug se sabe antes)", url_nota in desc_yt)
chequear("pasada: el posteo de Facebook es título + link a la nota",
         all("📲 Leé la nota completa: https://www.diariolacampaña.com.ar/n/" in l[1] for l in llamadas if l[0] == "facebook"))
chequear("pasada: 5 minutos entre pieza y pieza", dormido == [300, 300])
chequear("pasada: a las 12 no hay carrusel", "carrusel" not in inf and not mem["carruseles"])

llamadas.clear()
reloj["ahora"] = datetime(2026, 10, 6, 15, 5, tzinfo=AR)
inf2 = PA.pasada(True, redactar=redactar_por_nota, notas=notas)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
chequear("pasada siguiente: no repite lo publicado y sigue con lo que quedaba",
         len(inf2["piezas"]) == 2 and len(mem["piezas"]) == 5)
chequear("pasada siguiente: Facebook sigue eligiendo por viralidad (tope por día: 8)",
         [l[0] for l in llamadas].count("facebook") == 2)

# Si la web falla, el Short no puede quedar con un link roto.
llamadas.clear()
web_falla["si"] = True
reloj["ahora"] = datetime(2026, 10, 6, 18, 5, tzinfo=AR)
otra = [nota("Aumentan las tarifas de luz y gas desde noviembre: cuánto suben", "economia", slug="tarifas")]
TODAS += otra
virales["tarifas"] = 9
inf3 = PA.pasada(True, redactar=redactar_por_nota, notas=otra)
chequear("web caída: el Short cambia su link por el de la sección",
         any(l[0] == "yt_desc" and PA.SECCION_WEB in l[1] for l in llamadas))
chequear("web caída: Facebook manda a la sección, no a una nota que no existe",
         any(l[0] == "facebook" and PA.SECCION_WEB in l[1] for l in llamadas))
chequear("web caída: la falla queda en el informe (y la corrida avisa)", any("web" in f for f in inf3["fallas"]))
web_falla["si"] = False

# El carrusel de las 22.
llamadas.clear()
reloj["ahora"] = datetime(2026, 10, 6, 21, 5, tzinfo=AR)
inf4 = PA.pasada(True, solo_carrusel=False, esperar_carrusel="22:00", redactar=redactar_por_nota, notas=notas)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
c = inf4.get("carrusel") or {}
chequear("carrusel: la pasada de las 21:05 espera hasta las 22 y lo publica",
         c.get("estado") == "ok" and reloj["ahora"].hour == 22)
hijos = [l for l in llamadas if l[0] == "ig_contenedor"]
chequear("carrusel: tapa + una diapositiva por nota con web (la de Wix caída no va)",
         len(hijos) == 1 + 5 + 1 and hijos[-1][1] == "CAROUSEL")
cap = [l[1] for l in llamadas if l[0] == "ig_publicar"][0]
chequear("carrusel: el texto arranca con «Noticias nacionales de hoy» (lo que se busca)",
         cap.startswith("Noticias nacionales de hoy, martes 6 de octubre de 2026"))
llamadas.clear()
reloj["ahora"] = datetime(2026, 10, 6, 23, 35, tzinfo=AR)
inf5 = PA.pasada(True, redactar=redactar_por_nota, notas=notas)
chequear("carrusel: la pasada de las 23:35 no lo repite", (inf5.get("carrusel") or {}).get("estado") == "ya_estaba"
         and not any(l[0] == "ig_publicar" for l in llamadas))

# Simulación: no toca la memoria.
antes = PA.MEMORIA.read_text(encoding="utf-8")
llamadas.clear()
feriado = [nota("Aguinaldo de diciembre: cuándo se cobra y cómo se calcula", "economia", slug="feriado")]
TODAS += feriado
virales["feriado"] = 6
PA.pasada(False, redactar=redactar_por_nota, notas=feriado)
chequear("simulación: no publica nada ni anota", not llamadas and PA.MEMORIA.read_text(encoding="utf-8") == antes)

# --- 6. La memoria compartida con el trabajo de policiales ---------------------------------------
vieja = {"piezas": {"a": {"cuando": "2026-10-06T09:00"}}, "descartadas": {}, "carruseles": {}}
nueva = {"piezas": {"a": {"cuando": "2026-10-06T09:00"}, "b": {"cuando": "2026-10-06T12:00"}},
         "descartadas": {}, "carruseles": {"2026-10-06": {"estado": "ok", "cuando": "2026-10-06T22:01"}}}
m = GE.combinar_nacionales(vieja, nueva)
chequear("memoria: la copia VIEJA de policiales no pisa lo nuevo de nacionales",
         set(m["piezas"]) == {"a", "b"} and m["carruseles"])

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
