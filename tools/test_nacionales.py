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

# Las pruebas de las secciones 1-10 son de la mecánica de antes (carrusel en generales, IA, espectáculos…):
# corren con «todo reel» apagado; la agenda del 20/10/2026 (sección 11) lo prende.
os.environ["NAC_TODO_REEL"] = "0"

from nacionales import filtro as F, guion as NG, infobae as IB, pasada as PA, placa as P
from reels import publicador as PUB, turnos as TURNOS, web as WEB

# Las pruebas de la fila y del cupo usan la grilla completa de pasadas de antes (09:05 a 23:35): prueban
# la mecánica, no los horarios. Los horarios reales viven en reels/cupo.py (19/10/2026: 18:05 y 23:35).
from reels import cupo as _CUPO  # noqa: E402
_CUPO.PASADAS_AR = ((9, 5), (12, 5), (15, 5), (18, 5), (21, 5), (23, 35))
_CUPO.PASADAS_FINDE = ()
from reels import turnos as _TUR  # noqa: E402
_TUR.MINUTOS, _TUR.DEMORA_PRIMERO, _TUR.SEPARACION = 15, 15, 2
PUB.PASADAS_AR = _CUPO.PASADAS_AR
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
            "fecha": AHORA - horas * 3600,
            # Desde el 18/10/2026 una nota sin foto usable ni video no sale: todas traen una por defecto.
            "imagen": f"https://www.infobae.com/resizer/v2/{slug or abs(hash(titulo)) % 10**8}.jpg"}


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
xml = """<?xml version="1.0"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>Título de prueba</title><link>https://www.infobae.com/politica/2026/10/06/nota/</link>
<pubDate>Tue, 06 Oct 2026 12:00:00 +0000</pubDate><description>Resumen</description>
<content:encoded><![CDATA[<p>Primer párrafo.</p><p>Segundo.</p>]]></content:encoded>
<media:content url="https://www.infobae.com/resizer/v2/FOTO.jpg?auth=x" type="image/jpeg"/>
<media:credit role="author" scheme="urn:ebu">Agustin Marcarian</media:credit></item>
<item><title>Otra</title><link>https://otro.sitio/nota</link></item></channel></rss>"""
ns = IB.notas_del_feed(xml, "politica")
chequear("Infobae: lee título, texto completo y fecha del feed",
         len(ns) == 1 and ns[0]["cuerpo"] == "Primer párrafo. Segundo." and ns[0]["fecha"] > 0)
chequear("Infobae: guarda la foto y el crédito del feed (07/10)",
         ns[0]["imagen"].endswith("FOTO.jpg?auth=x") and ns[0]["credito_feed"] == "Agustin Marcarian")
chequear("agencias: Reuters, AP, EFE, NA en el epígrafe",
         all(IB.es_de_agencia(t) for t in ("(Foto: Reuters)", "Javier Milei (AP)", "(Foto AP/Ettore Chiereguini)",
                                           "REUTERS/Agustin Marcarian", "Foto de archivo EFE", "(NA)")))
chequear("agencias: oficiales, capturas y palabras parecidas NO",
         not any(IB.es_de_agencia(t) for t in ("(Fotos: Consejo de la Magistratura)", "(Prensa ANSES)",
                                               "El NAP del gobierno", "El APOYO de la gente", "Captura de video",
                                               "Una EFEméride", "")))

# --- 3. Guion -----------------------------------------------------------------------------------
BUENO = {"apta": True, "seccion": "Economía", "volanta": "ANSES", "titular": "Los jubilados cobran con bono en octubre",
         "bajada": "El organismo confirmó el calendario.", "descripcion": "Uno. Dos.", "hashtags": ["#Jubilados", "#ANSES"],
         "potencial_viral": 8, "titulo_web": "ANSES: cuándo cobran los jubilados en octubre",
         "nota_web": ("Párrafo uno con datos del calendario de pagos de la ANSES para este mes. " * 3 + "\n\n") * 3,
         # Las láminas del carrusel de Instagram (las generales también van, desde el 18/10/2026).
         "laminas": [{"titulo": f"Lámina {i}", "texto": "Texto explicativo de la lámina con los datos del hecho."}
                     for i in range(1, 5)]}
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
cap_ig = PA.caption_instagram(dict(BUENO, hashtags=["#Jubilados"]))
chequear("Instagram: el texto lleva la web y NUNCA el link de la nota (pedido del 18/10/2026)",
         "📲 Más noticias en www.diariolacampaña.com.ar" in cap_ig and "/n/" not in cap_ig and "http" not in cap_ig)
g_lam = NG.generar(n_anses, redactar_falso([dict(BUENO, laminas=[]), {"laminas": BUENO["laminas"]}]))
chequear("guion: una general sin láminas las pide aparte (va a Instagram como carrusel desde el 18/10/2026)",
         len(g_lam["laminas"]) == 4)

# --- 4. Placa propia ------------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp(prefix="nac_"))
f1 = P.fondo("Economía", (1080, 1920), 7)
chequear("placa: el fondo es 9:16 y siempre igual para la misma pieza",
         f1.size == (1080, 1920) and f1.tobytes()[:5000] == P.fondo("Economía", (1080, 1920), 7).tobytes()[:5000])
from reels import reel_bot as R
P.guardar_fondo("Política", tmp / "f.jpg")
chequear("placa: el motor la toma como FOTO, no como afiche (si no, no le pone el titular)",
         not R.motor()._es_grafica(tmp / "f.jpg", tmp))
s = P.slide_carrusel("Política", "Interna", "Un titular de prueba para el posteo", "", tmp / "s.jpg", sitio="x")
chequear("placa: la de Facebook es la del carrusel, 4:5, sin número ni flecha",
         Image.open(s).size == (1080, 1350))
c1 = P.slide_carrusel("Economía", "Dólar", "Una nota sin foto en el carrusel", "", tmp / "c1.jpg", sitio="x",
                      idx=1, total=3)
chequear("placa: la diapositiva del carrusel también es 4:5 (sin foto, sobre el fondo propio)",
         Image.open(c1).size == (1080, 1350))
apaisada, parada = tmp / "apaisada.jpg", tmp / "parada.jpg"
Image.new("RGB", (1600, 900), (90, 90, 90)).save(apaisada)
Image.new("RGB", (900, 1200), (90, 90, 90)).save(parada)
chequear("placa: las horizontales alternan A y B; las verticales y las sin foto, caja (C)",
         P.estilos_carrusel([apaisada, parada, apaisada, None, apaisada]) == ["A", "C", "B", "C", "A"])
c2 = P.slide_carrusel("Política", "Interna", "Titular", "Bajada de la nota", tmp / "c2.jpg", foto=apaisada,
                      idx=2, total=3, estilo="B")
chequear("placa: la diapositiva con foto horizontal es 4:5 y el fondo del panel es grafito",
         Image.open(c2).size == (1080, 1350)
         and max(abs(a - b) for a, b in zip(Image.open(c2).convert("RGB").getpixel((540, 1000)), P.GRAFITO)) < 6)
chequear("placa: la imagen de la web es 1200x675",
         Image.open(P.portada_web("Salud", "Dengue", "Titular", tmp / "w.jpg")).size == (1200, 675))
chequear("placa: la fecha en castellano", P.fecha_larga(datetime(2026, 10, 6)) == "martes 6 de octubre")

# --- 5. La pasada, con todo reemplazado --------------------------------------------------------
AR = timezone(timedelta(hours=-3))
estado_tmp = tmp / "estado"
PA.MEMORIA = estado_tmp / "nacionales.json"
PA.DIST.BUZON = estado_tmp / "buzon_distribuidor.json"      # nunca el buzón real
from reels import auditoria as AU
AU.ARCHIVO = estado_tmp / "auditoria.json"                    # ni la auditoría real
PA.SALIDA = tmp / "salida"
reloj = {"ahora": datetime(2026, 10, 6, 12, 5, tzinfo=AR)}
PA._ahora = lambda: reloj["ahora"]
dormido = []
PA._dormir = lambda s: dormido.append(s) or reloj.__setitem__("ahora", reloj["ahora"] + timedelta(seconds=s))
llamadas = []


fotos_reel = {}


def armar_reel(guion, salida, foto=None, clip=None, **k):
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_bytes(b"mp4")
    fotos_reel[guion["titular"][:20]] = str(foto)
    return {"archivo": str(salida), "duracion": 12.9, "placa": None}


# La foto: el epígrafe por URL y una descarga que deja una foto de verdad (la usa el compositor).
from reels import flujo as FL
FOTO_OK = tmp / "foto_ok.jpg"
Image.new("RGB", (1200, 800), (120, 90, 60)).save(FOTO_OK, "JPEG")
EPIGRAFES = {}
bajadas = []
IB.credito_foto = lambda url, cliente=None: (EPIGRAFES.get(url, ""), url not in ("ROTA",))


def bajar_falsa(url, destino):
    bajadas.append(url)
    shutil.copy(FOTO_OK, destino)
    return Path(destino)


FL._bajar_foto = bajar_falsa


R.armar = armar_reel
PUB.publicar_youtube = lambda pieza, mp4, meta=None: llamadas.append(("youtube", meta["snippet"]["description"])) or {
    "id": f"yt{len(llamadas)}", "url": "https://youtube.com/shorts/x"}
PUB.subir_a_release = lambda ruta, nombre: llamadas.append(("release", nombre)) or f"https://gh/{nombre}"
web_falla = {"si": False}


imagenes_web = {}


def web_falsa(pedir, pieza, yt, foto_respaldo="", categorias=None):
    llamadas.append(("web", tuple(categorias or ()), yt))
    imagenes_web[pieza["guion"]["titular"][:20]] = (pieza.get("imagen_url"), bool(foto_respaldo))
    if web_falla["si"]:
        raise WEB.FalloWeb("Wix caído")
    slug = WEB.slug_de(pieza)
    return {"id": "w", "slug": slug, "url": WEB.link(slug)}


WEB.publicar = web_falsa
PA.publicar_foto_facebook = lambda jpg, msg: llamadas.append(("facebook", msg)) or {"id": "fb"}
PA._yt_cambiar_descripcion = lambda vid, meta: llamadas.append(("yt_desc", meta["snippet"]["description"]))
PUB._contenedor_listo = lambda uid, tok, params: llamadas.append(("ig_contenedor", params.get("media_type") or "hijo")) or "c"
PUB._publicar_contenedor = lambda uid, tok, cid, cap: llamadas.append(("ig_publicar", cap)) or "media"
PA._lugar_ig = lambda: None                                     # el cupo de Instagram: sin red
PA._shorts_hoy = lambda mem, dia: 0

notas = [nota(f"ANSES: cuándo cobran los jubilados con el bono {i}", "economia", slug=f"anses{i}") for i in range(1)] + [
    nota("Paro general: la CGT confirmó la fecha y qué servicios se ven afectados", "politica", slug="paro"),
    nota("Feriado del 12 de octubre: cuándo es el fin de semana largo", "sociedad", slug="lujan"),
    nota("Juicio de los Cuadernos: siguen declarando los testigos", "judiciales", slug="cuadernos"),
    nota("Crece la puja por la sucesión de Kicillof entre los intendentes", "politica", slug="interna")]
TODAS = list(notas)
virales = {"anses0": 9, "paro": 8, "lujan": 7, "cuadernos": 5, "interna": 4}
# ANSES trae una foto oficial; el paro, una de Reuters (18/10/2026: sin foto usable la nota NO sale); las
# demás, fotos propias del portal.
notas[0]["imagen"] = "https://www.infobae.com/resizer/v2/ANSES.jpg"
EPIGRAFES[notas[0]["url"]] = "La ANSES confirmó el calendario (Prensa ANSES)"
notas[1]["imagen"] = "https://www.infobae.com/resizer/v2/PARO.jpg"
EPIGRAFES[notas[1]["url"]] = "La marcha de la CGT (Foto: Reuters)"
for _n in notas[2:]:
    EPIGRAFES[_n["url"]] = "(Foto: Infobae)"


def redactar_por_nota(system, material):
    titulo = material.split("Titular original: ")[1].split("\n")[0]
    clave = next(n["url"].rstrip("/").rsplit("/", 1)[1] for n in TODAS if n["titulo"].startswith(titulo[:30]))
    return dict(BUENO, titular=titulo[:80], potencial_viral=virales[clave],
                titulo_web=f"{titulo[:60]} nota web"), "falso"


inf = PA.pasada(True, redactar=redactar_por_nota, notas=notas)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
redes = [l[0] for l in llamadas]
chequear("pasada: 3 nacionales generales por pasada", len(inf["piezas"]) == 3 and len(mem["piezas"]) == 3)
sin_release = [r for r in redes if r != "release"]
chequear("pasada: orden por pieza YouTube → web → Facebook",
         sin_release[:3] == ["youtube", "web", "facebook"])
chequear("pasada: la nota va a Nacionales + la categoría interna de las automáticas",
         all(l[1] == (WEB.NACIONALES_ID, WEB.NACIONALES_AUTO_ID) for l in llamadas if l[0] == "web"))
chequear("pasada: la web lleva el Short adentro", all(l[2] for l in llamadas if l[0] == "web"))
chequear("pasada: Facebook solo 2 por pasada, de potencial viral 7 o más (18/10/2026: se decide en su turno)",
         redes.count("facebook") == 2 and all(p["viral"] >= 7 for p in inf["piezas"] if p.get("facebook")))
desc_yt = [l[1] for l in llamadas if l[0] == "youtube"][0]
url_nota = [p["web"]["url"] for p in inf["piezas"]][0]
chequear("pasada: el Short sale con el link de SU nota (el slug se sabe antes)", url_nota in desc_yt)
chequear("pasada: el posteo de Facebook es título + link a la nota",
         all("📲 Leé la nota completa: https://www.diariolacampaña.com.ar/n/" in l[1] for l in llamadas if l[0] == "facebook"))
chequear("fila: un turno cada 15 minutos desde las 12:20; dos generales nunca seguidas (la otra espera un turno)",
         dormido == [900] * 5 and [p["turno"] for p in inf["piezas"]] == ["12:20", "12:50", "13:20"]
         and inf["fila"]["turnos"][0] == "12:20" and len(inf["fila"]["turnos"]) == 12)
chequear("pasada: no hay carrusel de las 22 (apagado el 18/10/2026)", "carrusel" not in inf and not mem["carruseles"])
caps_ig = [l[1] for l in llamadas if l[0] == "ig_publicar"]
chequear("Instagram: las generales también salen, una por una, sin el link de la nota",
         len(caps_ig) == 3 and all("/n/" not in c and "www.diariolacampaña.com.ar" in c for c in caps_ig)
         and all((p.get("instagram") or {}).get("estado") == "ok" for p in inf["piezas"]))
t_anses, t_paro = notas[0]["titulo"][:20], notas[1]["titulo"][:20]
chequear("foto: la nota con foto oficial arma el Short con SU foto",
         fotos_reel.get(t_anses, "").endswith("_foto.jpg") and bajadas[:1] == [notas[0]["imagen"]])
chequear("foto: la de Reuters NO se baja ni se usa, y la nota NO sale (18/10/2026: sin foto no se publica)",
         t_paro not in fotos_reel and notas[1]["imagen"] not in bajadas and notas[1]["url"] not in mem["piezas"])
chequear("foto: todas las que salieron llevan una foto de verdad (nunca la placa propia)",
         fotos_reel and all(v.endswith("_foto.jpg") for v in fotos_reel.values()))
chequear("foto: la web importa la foto original y tiene la placa de respaldo",
         imagenes_web.get(t_anses) == (notas[0]["imagen"], True))
chequear("foto: la memoria guarda la foto (para el carrusel)",
         mem["piezas"][notas[0]["url"]]["foto_url"] == notas[0]["imagen"])
_sin = PA.armar(dict(nota("Una nota sin ninguna foto", "politica", slug="sinfoto"), imagen=""), tmp / "sinfoto",
                redactar=lambda *a: (_ for _ in ()).throw(AssertionError("no tenía que gastar la IA")),
                leer_pagina=lambda u: {})
chequear("foto: una nota sin foto usable ni video NO sale y no gasta la IA",
         _sin["guion"]["apta"] is False and "sin imagen" in _sin["guion"]["motivo"])
chequear("foto: si la página no deja leer el epígrafe, va la placa (ante la duda, sin foto)",
         "no se pudo leer" in PA.foto_de_la_nota({"url": "ROTA", "imagen": "https://x/f.jpg"}, tmp / "r.jpg")["motivo"])

llamadas.clear()
reloj["ahora"] = datetime(2026, 10, 6, 15, 5, tzinfo=AR)
inf2 = PA.pasada(True, redactar=redactar_por_nota, notas=notas)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
chequear("pasada siguiente: no repite lo publicado y sigue con lo que quedaba (el paro, sin foto, no sale)",
         len(inf2["piezas"]) == 1 and len(mem["piezas"]) == 4)
chequear("pasada siguiente: a Facebook solo las de potencial viral 7 o más (estas son 5 y 4)",
         [l[0] for l in llamadas].count("facebook") == 0)

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

# El carrusel de las 22: APAGADO desde el 18/10/2026 (las generales van una por una a Instagram).
llamadas.clear()
bajadas.clear()
reloj["ahora"] = datetime(2026, 10, 6, 21, 5, tzinfo=AR)
inf4 = PA.pasada(True, solo_carrusel=False, esperar_carrusel="22:00", redactar=redactar_por_nota, notas=notas)
chequear("carrusel: la pasada de las 21:05 ya no espera ni lo publica", "carrusel" not in inf4
         and reloj["ahora"].hour == 21)
# A mano (--solo-carrusel) todavía sale, por si se vuelve a prender.
reloj["ahora"] = datetime(2026, 10, 6, 22, 0, tzinfo=AR)
llamadas.clear()
inf4 = PA.pasada(True, solo_carrusel=True, redactar=redactar_por_nota, notas=notas)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
c = inf4.get("carrusel") or {}
chequear("carrusel a mano: se sigue pudiendo sacar", c.get("estado") == "ok")
hijos = [l for l in llamadas if l[0] == "ig_contenedor"]
chequear("carrusel: una diapositiva por nota con web, sin tapa (la de Wix caída no va)",
         len(hijos) == 4 + 1 and hijos[-1][1] == "CAROUSEL")
chequear("carrusel: cada diapositiva vuelve a bajar SU foto",
         bajadas == [n["imagen"] for n in notas if n is not notas[1]])
cap = [l[1] for l in llamadas if l[0] == "ig_publicar"][0]
chequear("carrusel: el texto arranca con «Noticias nacionales de hoy» (lo que se busca)",
         cap.startswith("Noticias nacionales de hoy, martes 6 de octubre de 2026"))
llamadas.clear()
reloj["ahora"] = datetime(2026, 10, 6, 23, 35, tzinfo=AR)
inf5 = PA.pasada(True, solo_carrusel=True, redactar=redactar_por_nota, notas=notas)
chequear("carrusel: no se repite en el día", (inf5.get("carrusel") or {}).get("estado") == "ya_estaba"
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

# --- 7. Categorías nuevas: deportes, espectáculos, cine y series, IA aplicada (17/10/2026) --------
from nacionales import categorias as CAT
T = AHORA


def nota_cat(titulo, seccion, slug, resumen="", horas=1):
    return dict(nota(titulo, seccion, slug=slug), resumen=resumen, fecha=T - horas * 3600)


pc = lambda n: CAT.puntuar(n, T)[0]   # noqa: E731
chequear("deportes: con un equipo o un jugador argentino, sí",
         pc(nota_cat("Boca le ganó a Racing y es puntero del Clausura", "deportes", "d1")) > 0)
chequear("deportes: sin protagonista argentino, no",
         pc(nota_cat("El Real Madrid goleó al Getafe en la Liga de España", "deportes", "d2")) == 0)
chequear("deportes: un «en vivo» no (el resultado todavía no es final)",
         pc(nota_cat("River vs Boca EN VIVO: minuto a minuto del superclásico", "deportes", "d3")) == 0)
chequear("espectáculos: una galería de fotos no",
         pc(nota_cat("Fotos: el look de los famosos en la alfombra roja", "teleshow", "e1")) == 0)
chequear("cine y series: un estreno suma más que otra nota de cine",
         pc(nota_cat("Netflix estrena en noviembre la serie de Mafalda", "que-puedo-ver", "c1"))
         > pc(nota_cat("Cómo se filmó la serie de Mafalda en Netflix", "que-puedo-ver", "c2")) > 0)
chequear("cine y series: un videojuego no",
         pc(nota_cat("El nuevo videojuego de Batman llega a PlayStation", "que-puedo-ver", "c3")) == 0)
chequear("IA: con un uso práctico para comercios en el título, sí",
         pc(nota_cat("Cómo usar la IA para responder clientes por WhatsApp en un comercio", "tecno", "t1")) > 0)
chequear("IA: una pelea entre empresas de IA, no",
         pc(nota_cat("OpenAI acusa a Apple de obtener información secreta con su IA", "tecno", "t2")) == 0)
chequear("cine y series mira 72 h (los estrenos se anuncian con días); deportes, 24",
         pc(nota_cat("Disney+ estrena la temporada final de la serie", "que-puedo-ver", "c4", horas=50)) > 0
         and pc(nota_cat("Boca le ganó a Racing en el Clausura", "deportes", "d4", horas=30)) == 0)
os.environ["NAC_CUPO_DEPORTES"] = "1"
chequear("rotación: sin cupo hoy, la categoría no va; la que hace más que no sale, primero",
         CAT.orden_de_rotacion([{"categoria": "deportes"}], {"espectaculos": "2026-10-07T10:00",
                                                             "cine_series": "2026-10-05T10:00"})
         == ["tecnologia_ia", "internacionales", "virales", "cine_series", "espectaculos"])
os.environ.pop("NAC_CUPO_DEPORTES")
chequear("web: cada categoría va a su sección (Deportes, Espectáculos, Cine y series, Tecnología)",
         CAT.seccion_web("deportes") == "094f631e-1b56-485f-8777-6e167802455e"
         and CAT.seccion_web("espectaculos") == "973d6c3f-8893-4d88-92fe-78c91ab6d1ce"
         and CAT.seccion_web("cine_series") == "03a75413-7258-4eca-b163-2f931193635c"
         and CAT.seccion_web("tecnologia_ia") == "5b9d1e36-6d94-48ab-b5f6-6f9cb1b8fcaf")
os.environ["WIX_CAT_ESPECTACULOS"] = "otra"
chequear("web: WIX_CAT_<CATEGORIA> la pisa", CAT.seccion_web("espectaculos") == "otra")
os.environ.pop("WIX_CAT_ESPECTACULOS")

# La pasada con variedad: la fila de 15 minutos, una categoría distinta en cada turno.
PA.MEMORIA = estado_tmp / "nacionales_cat.json"
reloj["ahora"] = datetime.fromtimestamp(T, AR)
# Desde acá la hora es la de verdad (las notas son de hace 1 h): la grilla, 12 turnos a partir de ahora.
TURNOS.grilla = lambda pid: [reloj["ahora"] + timedelta(minutes=15 * (k + 1)) for k in range(12)]
llamadas.clear()
sistemas = []


def redactar_cat(system, material):
    sistemas.append(system)
    titulo = material.split("Titular original: ")[1].split("\n")[0]
    return dict(BUENO, titular=titulo[:80], potencial_viral=5, titulo_web=f"{titulo[:60]} nota web"), "falso"


generales = [nota_cat("Aumentan las tarifas de luz y gas desde noviembre en todo el país", "economia", "g1"),
             nota_cat("La CGT anunció un paro general para fin de mes", "politica", "g2"),
             nota_cat("El Senado aprobó la ley de financiamiento universitario", "politica", "g3")]
variadas = [nota_cat("Boca le ganó a Racing y quedó puntero del Torneo Clausura", "deportes", "v1"),
            nota_cat("MasterChef Junior volvió a la pantalla con Vero Lozano", "teleshow", "v2")]
sin_pagina = lambda url: {"video": "", "imagen": ""}      # noqa: E731 — nunca la red en las pruebas
inf = PA.pasada(True, redactar=redactar_cat, notas=generales, notas_variedad=variadas, leer_pagina=sin_pagina)
cats = [p.get("categoria") for p in inf["piezas"]]
chequear("pasada: 3 nacionales + 2 de variedad (cupo propio, no le quita a las nacionales)",
         len(inf["piezas"]) == 5)
seguidas = [(a, b) for a, b in zip(inf["piezas"], inf["piezas"][1:])
            if (datetime.strptime(b["turno"], "%H:%M") - datetime.strptime(a["turno"], "%H:%M")).seconds == 900]
chequear("fila: nunca dos de la misma categoría en turnos seguidos",
         all((a.get("categoria") or "") != (b.get("categoria") or "") for a, b in seguidas)
         and sorted(cats, key=str) == sorted(["", "", "", "deportes", "espectaculos"], key=str))
chequear("fila: con variedad para alternar, las 5 salen en 5 turnos seguidos (cada 15 minutos)",
         cats[0::2] == ["", "", ""] or len(seguidas) == 4)
chequear("pasada: la nota de deportes va a la sección Deportes de la web",
         ("094f631e-1b56-485f-8777-6e167802455e", WEB.NACIONALES_AUTO_ID) in [l[1] for l in llamadas if l[0] == "web"])
chequear("guion: a la IA le llegan las reglas de la categoría (resultado final, confirmado…)",
         sum(1 for s in sistemas if "CATEGORÍA DEPORTES" in s) >= 1)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
chequear("guion: la sección la fija la categoría, no la IA",
         any(p.get("seccion") == "Deportes" and p.get("categoria") == "deportes" for p in mem["piezas"].values()))
buzon = json.loads(PA.DIST.BUZON.read_text(encoding="utf-8"))["eventos"]
chequear("Buffer: cada pieza publicada va al buzón como «nacionales», para X y TikTok (19/10/2026)",
         len([e for e in buzon if e["origen"] == "nacionales"]) >= 3
         and all(e["plataformas"] == ["x", "tiktok"] and e["video_url"].startswith("https://gh/") for e in buzon
                 if e["origen"] == "nacionales")
         and any(e.get("categoria") == "Deportes" for e in buzon))
# 18/10/2026: con VIDEO original → reel en Instagram; sin video → carrusel explicativo; viral sin video → no.
reloj["ahora"] += timedelta(hours=3)
FL._bajar_video = lambda url, destino: (Path(destino).write_bytes(b"video-original"), Path(destino))[1]
LAMINAS = [{"titulo": f"Lámina {i}", "texto": "Texto explicativo de la lámina con los datos del hecho y su contexto."}
           for i in range(1, 5)]


def redactar_lam(system, material):
    datos, via = redactar_cat(system, material)
    return dict(datos, laminas=LAMINAS), via


variadas2 = [dict(nota_cat("Elecciones en Estados Unidos: qué votan este martes", "america", "v3"), categoria="internacionales"),
             dict(nota_cat("El video del perro que aprendió a abrir la heladera", "virales", "v4"), categoria="virales"),
             dict(nota_cat("Cómo usar la IA para responder clientes por WhatsApp", "tecno", "v5"), categoria="tecnologia_ia")]
paginas = {variadas2[0]["url"]: {"video": "https://cdn.jwplayer.com/videos/abc.mp4", "imagen": ""},
           variadas2[1]["url"]: {"video": "", "imagen": ""}, variadas2[2]["url"]: {"video": "", "imagen": ""}}
antes_ia = len(sistemas)
llamadas.clear()
os.environ["NAC_VARIEDAD_POR_PASADA"] = "3"
inf2 = PA.pasada(True, redactar=redactar_lam, notas=[], notas_variedad=variadas2, leer_pagina=lambda u: paginas[u])
os.environ.pop("NAC_VARIEDAD_POR_PASADA")
por_cat = {p.get("categoria"): p for p in inf2["piezas"]}
chequear("viral SIN su video original: no sale, y no se gasta la IA",
         "virales" not in por_cat and any("virales sin el video original" in d["motivo"] for d in inf2["descartadas"]))
chequear("internacional CON video original: reel en Instagram con ese video",
         por_cat.get("internacionales", {}).get("formato") == "reel"
         and (por_cat["internacionales"].get("instagram") or {}).get("estado") == "ok"
         and por_cat["internacionales"].get("video_original") == "https://cdn.jwplayer.com/videos/abc.mp4")
chequear("IA sin video: carrusel explicativo (portada + 4 láminas) en Instagram",
         por_cat.get("tecnologia_ia", {}).get("formato") == "carrusel"
         and sum(1 for l in llamadas if l == ("ig_contenedor", "hijo")) >= 5
         and ("ig_contenedor", "CAROUSEL") in llamadas)
chequear("la IA se usó solo para las dos que salen", len(sistemas) - antes_ia == 2)
mem = json.loads(PA.MEMORIA.read_text(encoding="utf-8"))
chequear("carrusel «Noticias nacionales de hoy»: sin deportes ni espectáculos",
         not any(p.get("categoria") for _u, p in PA.para_el_carrusel(mem)))
print("   categorías de las pasadas:", cats, [p.get("categoria") for p in inf2["piezas"]])

# La fila compartida con policiales: los turnos que reservó policiales no los usa nacionales.
reloj["ahora"] += timedelta(hours=3)
PA.MEMORIA = estado_tmp / "nacionales_fila.json"
fila = TURNOS.Fila("2026-10-06T12:05", token="")
fila.tomar(1, "policiales", "policial", "Choque en la Ruta 5")
fila.tomar(4, "policiales", "policial", "Robo en Chivilcoy")
gen_f = [nota_cat("Aumentan las tarifas de luz y gas desde diciembre en todo el país", "economia", "f1"),
         nota_cat("La CGT anunció un nuevo paro general para diciembre", "politica", "f2")]
var_f = [nota_cat("River le ganó a Boca en el Monumental y es líder", "deportes", "fv1"),
         nota_cat("Murió un histórico conductor de la televisión argentina", "teleshow", "fv2")]
turnos_f = TURNOS.grilla("x")
inf_f = PA.pasada(True, redactar=redactar_lam, notas=gen_f, notas_variedad=var_f, leer_pagina=sin_pagina, fila=fila)
usados = [p["turno"] for p in inf_f["piezas"]]
chequear("fila: nacionales no usa los turnos de policiales y los demás salen cada 15 minutos",
         usados == [f"{turnos_f[k]:%H:%M}" for k in (0, 2, 3, 5)] and len(inf_f["fila"]["ajenos"]) == 2)
chequear("fila: cada turno de nacionales queda anotado en la fila con su categoría",
         {k: d["quien"] for k, d in fila.ocupados().items()} == {0: "nacionales", 1: "policiales", 2: "nacionales",
                                                                 3: "nacionales", 4: "policiales", 5: "nacionales"})

# --- 8. Todos los portales del PDF + puntaje de impacto (18/10/2026) -----------------------------
from nacionales import impacto as IM, portales as PO, senales as SE

chequear("ranking: el orden del PDF entre las ACTIVAS (EFE, Reuters y AP no leen: no ocupan lugar)",
         PO.ranking("internacionales") == ["BBC Mundo", "Infobae", "La Nación", "TN", "Clarín", "Ámbito"]
         and PO.ranking("deportes")[:5] == ["TyC Sports", "ESPN", "Olé", "AFA", "Liga Profesional"]
         and PO.ranking("tecnologia_ia")[:2] == ["Zapier", "Google Workspace"])
chequear("ranking: la primera del PDF vale más que la segunda, y así; una de afuera, casi nada",
         IM.puntos_fuente("TyC Sports", "deportes") == 20 > IM.puntos_fuente("ESPN", "deportes")
         > IM.puntos_fuente("Olé", "deportes") > IM.puntos_fuente("Ámbito", "deportes") == 6
         and IM.puntos_fuente("Página 12", "deportes") == 4)
chequear("fuente: sale del dominio si la nota no la trae",
         PO.fuente_de({"url": "https://www.ole.com.ar/boca/x.html"}) == "Olé"
         and PO.fuente_de({"url": "https://blog.hubspot.com/sales/x"}) == "HubSpot")
espn = json.dumps({"articles": [
    {"headline": "Vélez le ganó a Gimnasia", "description": "Partidazo en Liniers", "published": "2026-10-18T02:00:00Z",
     "images": [{"url": "https://a.espncdn.com/foto.jpg"}],
     "links": {"web": {"href": "https://www.espn.com.ar/futbol/argentina/nota/_/id/1/velez?x=1"}}},
    {"headline": "Clip", "links": {"web": {"href": "https://www.espn.com.ar/video/clip/_/id/2/clip"}}}]})
ne = PO.notas_espn(espn, "deportes", "ESPN")
chequear("ESPN: la API en JSON da titular, bajada, foto y link (los clips sueltos no)",
         len(ne) == 1 and ne[0]["titulo"] == "Vélez le ganó a Gimnasia" and ne[0]["imagen"].endswith("foto.jpg")
         and ne[0]["url"].endswith("/velez") and ne[0]["fecha"] > 0)
pagina = ('<html><head><meta property="og:title" content="Boca ganó el clásico | TyC Sports">'
          '<meta property="og:image" content="https://x/foto.jpg"><meta property="og:description" content="Bajada">'
          '<script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-10-18T10:00:00-03:00",'
          '"articleBody":"' + "Texto completo de la nota. " * 30 + '"}</script></head><body>'
          '<script>var v="https://cdn.jwplayer.com/videos/AbC123.mp4"</script></body></html>')
f = PO.ficha(pagina)
chequear("página: título sin el «| TyC Sports», foto, fecha, texto completo y el video del reproductor",
         f["titulo"] == "Boca ganó el clásico" and f["imagen"] == "https://x/foto.jpg" and f["fecha"] > 0
         and len(f["texto"]) > 500 and f["video"] == "https://cdn.jwplayer.com/videos/AbC123.mp4")
f2 = PO.ficha('<meta property="og:title" content="Primera C: se juega la permanencia"><p>Publicado el 14/10/2026</p>'
              '<article><p>' + "El partido se juega en Rosario y define quién se queda en la categoría. " * 3
              + '</p></article>')
chequear("página sin articleBody (Olé, BBC, AFA): los párrafos de la nota y la fecha dd/mm/aaaa",
         len(f2["texto"]) > 150 and datetime.fromtimestamp(f2["fecha"], AR).date().isoformat() == "2026-10-14")
chequear("listado (TyC, AFA, Shopify): los links de notas, en orden y sin repetir",
         PO.links_de_lista('<a href="/futbol/a-id1.html"></a><a href="/futbol/a-id1.html"></a>'
                           '<a href="https://www.tycsports.com/boca/b-id2.html"></a><a href="/x.html"></a>',
                           r'href="((?:https://www\.tycsports\.com)?/[a-z0-9-]+/[a-z0-9-]+-id\d+\.html)"',
                           "https://www.tycsports.com/", 10)
         == ["https://www.tycsports.com/futbol/a-id1.html", "https://www.tycsports.com/boca/b-id2.html"])
ml = SE.mas_leidas_de('<h2>Las más leídas</h2><div class="most-read__list">'
                      '<a href="https://www.ambito.com/deportes/dibu-martinez-fue-operado-tras-el-golpazo-n6334968">1</a>'
                      '<a href="https://www.ambito.com/economia/dolar-hoy-cuanto-cotiza-n6334993">2</a></div>',
                      "Ámbito", "https://www.ambito.com/", r"most-read__list", r'href="(https://www\.ambito\.com/[^"]+-n\d+)"', 10)
chequear("más leídas: el puesto y las palabras del link",
         [(x["puesto"], x["texto"]) for x in ml] == [(1, "dibu martinez fue operado tras el golpazo"),
                                                     (2, "dolar hoy cuanto cotiza")])
tr = SE.tendencias_de('<rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item><title>racing independiente</title>'
                      '<ht:approx_traffic>50.000+</ht:approx_traffic><ht:news_item><ht:news_item_title>Racing e Independiente'
                      ' juegan el clásico de Avellaneda</ht:news_item_title></ht:news_item></item></channel></rss>')
chequear("Google Trends: la búsqueda, su volumen y los titulares asociados",
         tr == [{"consulta": "racing independiente", "trafico": 50000,
                 "titulos": ["Racing e Independiente juegan el clásico de Avellaneda"]}])
gn = SE.google_news_de('<rss><channel><item><title>Operaron a Dibu Martínez - Olé</title><source>Olé</source>'
                       '<description>&lt;ol&gt;&lt;li&gt;&lt;a href="x"&gt;Operaron a Dibu Martínez&lt;/a&gt;&amp;nbsp;'
                       '&lt;font color="#6f6f6f"&gt;Olé&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="y"&gt;Dibu, operado'
                       '&lt;/a&gt;&lt;font color="#6f6f6f"&gt;TN&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description></item>'
                       '</channel></rss>', "deportes")
chequear("Google News: el puesto, los titulares y los medios del tema",
         gn and gn[0]["puesto"] == 1 and set(gn[0]["medios"]) == {"Olé", "TN"} and "Operaron a Dibu Martínez" in gn[0]["titulos"])

T8 = AHORA


def nv(titulo, fuente, cat="deportes", horas=1, url=None, **k):
    dom = {"TyC Sports": "tycsports.com", "Infobae": "infobae.com", "Olé": "ole.com.ar", "Clarín": "clarin.com",
           "La Nación": "lanacion.com.ar", "ESPN": "espn.com.ar", "Zapier": "zapier.com"}.get(fuente, "x.com")
    n = PO.nota_nueva(url or f"https://www.{dom}/{cat}/{abs(hash(titulo + fuente)) % 10**8}-id1.html", cat, fuente,
                      titulo, cuerpo=titulo, fecha=T8 - horas * 3600, imagen="https://x/f.jpg")
    return dict(n, **k)


dibu = [nv("Operaron a Dibu Martínez tras el golpazo en el Chelsea", "Infobae"),
        nv("Dibu Martínez fue operado tras el golpazo con el Chelsea", "TyC Sports"),
        nv("Dibu Martínez operado: el golpazo en el Chelsea", "Olé")]
solo = [nv("Lanús le ganó a Platense como visitante en el Torneo Clausura", "TyC Sports")]
senales = dict(SE.vacias(), mas_leidas=[{"medio": "Clarín", "puesto": 2, "url": "u",
                                         "texto": "operaron dibu martinez golpazo chelsea"}],
               tendencias=[{"consulta": "dibu martinez", "trafico": 20000, "titulos": []},
                           {"consulta": "serie a", "trafico": 200, "titulos": []}],
               youtube=[{"titulo": "Dibu Martínez: el golpazo en el Chelsea", "vistas": 900000, "me_gusta": 30000,
                         "comentarios": 2000}])
pc8 = CAT.candidatas(dibu + solo, T8, senales)["deportes"]
chequear("impacto: el mismo tema en 3 portales es UNA candidata, contada desde la mejor fuente del PDF (TyC)",
         len(pc8) == 2 and PO.fuente_de(pc8[0]) == "TyC Sports" and pc8[0]["cobertura"] == 3
         and set(pc8[0]["fuentes"]) == {"Infobae", "TyC Sports", "Olé"})
d8 = pc8[0]["impacto_desglose"]
chequear("impacto: cobertura + más leída + búsqueda en Google + YouTube suben al tema leído y buscado",
         pc8[0]["impacto"] > pc8[1]["impacto"] and d8["cobertura"] == 12 and d8["lectores"] == 9
         and d8["busquedas"] > 0 and d8["youtube"] > 0)
chequear("impacto: cada componente deja su razón",
         any("más leída de Clarín" in r for r in pc8[0]["impacto_razones"])
         and any("dibu martinez" in r for r in pc8[0]["impacto_razones"]))
chequear("impacto: los otros portales del tema quedan para buscar el video (por orden del PDF)",
         pc8[0]["otras_urls"][0] == dibu[2]["url"])
series = CAT.candidatas([nv("Netflix estrena la serie argentina de Mafalda", "Infobae", "cine_series")], T8, senales)
chequear("búsquedas: «serie a» (una sola palabra) no se pega a una nota de series",
         series["cine_series"][0]["impacto_desglose"]["busquedas"] == 0)
chequear("clasificar: espectáculos se parte en cine y series",
         CAT.clasificar(nv("Netflix estrena la serie de Mafalda", "Clarín", "espectaculos+cine"))["categoria"] == "cine_series"
         and CAT.clasificar(nv("Murió un actor de la tele", "Clarín", "espectaculos+cine"))["categoria"] == "espectaculos")
chequear("clasificar: de una sección general solo quedan los virales",
         CAT.clasificar(nv("El video viral del perro que abre la heladera", "Clarín", "general"))["categoria"] == "virales"
         and CAT.clasificar(nv("El insólito video del gato que toca el piano", "Clarín", "general"))["categoria"] == "virales"
         and CAT.clasificar(nv("Aumentan las tarifas de luz", "Clarín", "general"))["categoria"] == "")
chequear("clasificar: un policial NUNCA pasa a viral (PDF: no saltar el radio de 100 km)",
         CAT.clasificar(nv("El video viral del robo a un kiosco", "Clarín", "general"))["categoria"] == ""
         and CAT.puntuar(nv("Video viral: la cámara de seguridad captó el asalto", "Infobae", "virales"), T8)[0] == 0)
blogs = [nv("The best AI tools for small business customer support", "Zapier", "tecnologia_ia"),
         nv("How to use AI agents for customer support in a small business", "HubSpot", "tecnologia_ia")]
pb = CAT.candidatas(blogs, T8)["tecnologia_ia"]
chequear("blogs: cada guía es su propio tema (no se juntan por «best» o «guide»)", len(pb) == 2)
chequear("blogs: miran 14 días (una guía no vence en horas)",
         CAT.puntuar(nv("How to use AI to answer customers on WhatsApp", "Zapier", "tecnologia_ia", horas=24 * 10), T8)[0] > 0)
por = {"deportes": [{"impacto_senal": 40}], "espectaculos": [{"impacto_senal": 30}], "virales": []}
chequear("orden: primero la categoría con el tema de más impacto; sin candidatas, no va",
         CAT.orden_por_impacto(por, [], {}) == ["deportes", "espectaculos"])
chequear("orden: 12 puntos menos por pieza que ya salió hoy (para que haya variedad)",
         CAT.orden_por_impacto(por, [{"categoria": "deportes"}], {}) == ["espectaculos", "deportes"])

# Nacionales generales: Infobae arma; los otros 4 portales del PDF y las señales suben al tema grande.
gen = [dict(nota("Aumentan las tarifas de luz y gas desde noviembre", "economia"), puntos=50),
       dict(nota("El Senado aprobó la ley de financiamiento universitario", "politica"), puntos=55)]
otras_gen = [nv("Tarifas: aumentan la luz y el gas desde noviembre", "Clarín", "nacionales"),
             nv("Luz y gas: aumentan las tarifas desde noviembre", "La Nación", "nacionales")]
sen_gen = dict(SE.vacias(), mas_leidas=[{"medio": "Ámbito", "puesto": 1, "url": "u",
                                         "texto": "aumentan las tarifas de luz y gas desde noviembre"}])
rg = IM.realzar_generales(gen, otras_gen, sen_gen, T8)
chequear("nacionales generales: el tema que cubren 3 portales y es el más leído pasa adelante",
         rg[0]["titulo"].startswith("Aumentan las tarifas") and rg[0]["impacto_extra"] > 0
         and rg[1].get("impacto_extra", 0) == 0)

# La pasada: el tema de TyC sin video toma el VIDEO de otro portal y el TEXTO completo de su página.
reloj["ahora"] += timedelta(hours=3)
mat8 = []


def redactar_8(system, material):
    mat8.append(material)
    return redactar_lam(system, material)


tyc = nv("Messi hizo dos goles y el Inter Miami ganó el clásico de Florida", "TyC Sports", cuerpo="")
ib = nv("Messi y dos goles: Inter Miami ganó el clásico de Florida", "Infobae")
paginas8 = {tyc["url"]: {"video": "", "imagen": "", "texto": "TEXTO COMPLETO DE TYC. " * 40},
            ib["url"]: {"video": "https://cdn.jwplayer.com/videos/messi.mp4", "imagen": "", "texto": ""}}
os.environ["NAC_VARIEDAD_POR_PASADA"] = "1"
inf8 = PA.pasada(True, redactar=redactar_8, notas=[], notas_variedad=[tyc, ib], leer_pagina=lambda u: paginas8[u],
                 senales=SE.vacias())
os.environ.pop("NAC_VARIEDAD_POR_PASADA")
p8 = inf8["piezas"][0] if inf8["piezas"] else {}
chequear("pasada: la nota de TyC (1.ª del PDF) sale como reel con el video que trae Infobae del mismo tema",
         p8.get("medio_origen") == "TyC Sports" and p8.get("formato") == "reel"
         and p8.get("video_original") == "https://cdn.jwplayer.com/videos/messi.mp4")
chequear("pasada: el guion recibe el TEXTO completo de la página (el RSS traía solo el titular)",
         any("TEXTO COMPLETO DE TYC" in m for m in mat8))
chequear("pasada: la pieza guarda su impacto, sus razones y los portales del tema",
         p8.get("impacto") and p8.get("fuentes") == ["TyC Sports", "Infobae"])
chequear("pasada: el ranking de cada categoría queda en el informe", inf8.get("ranking_variedad", {}).get("deportes"))
chequear("guion: no nombrar el portal de origen, como palabra entera («Olé» no salta en «colegio»; la AFA "
         "es fuente oficial y se puede nombrar)",
         not NG._nombra_infobae({"nota_web": "El colegio y el boleto"}, "Olé")
         and NG._nombra_infobae({"nota_web": "Según Olé, se va"}, "Olé")
         and not NG._nombra_infobae({"nota_web": "Fondos de la Nación"}, "La Nación")
         and not NG._nombra_infobae({"nota_web": "La AFA confirmó la fecha"}, "AFA"))

# --- 9. Notas de LISTA: nunca la promesa sin la información (18/10/2026, el posteo de Netflix) -----------
chequear("lista: lo que promete el titular (con número, en letras o sin número)",
         NG.promesa_de_lista("Las cinco películas para maratonear este fin de semana en Netflix") == 5
         and NG.promesa_de_lista("Los 10 estrenos de la semana") == 10
         and NG.promesa_de_lista("Qué ver en Netflix: las mejores películas y series") == 3
         and NG.promesa_de_lista("Boca ganó 3 a 1") == 0 and NG.promesa_de_lista("Murieron dos personas") == 0)
PELIS = [{"nombre": f"Película {i}", "detalle": f"Drama de 2026, {90 + i} minutos."} for i in range(1, 6)]
n_lista = nota("Las cinco películas para maratonear este fin de semana en Netflix", "que-puedo-ver",
               "El catálogo suma cinco películas. " * 20, slug="pelis")
n_lista["categoria"] = "cine_series"
pedidos.clear()
g = NG.generar(n_lista, redactar_falso([dict(BUENO, lista=PELIS[:2]), dict(BUENO, lista=PELIS)]))
chequear("lista: si la pieza nombra menos de las que promete, pide otra versión con TODAS",
         g["apta"] and len(g["lista"]) == 5 and len(pedidos) == 2 and "FALTA LA LISTA" in pedidos[1][0])
g_mal = NG.generar(n_lista, redactar_falso([dict(BUENO, lista=[]), dict(BUENO, lista=PELIS[:1])]))
chequear("lista: si igual no las nombra, NO sale (mejor nada que la promesa vacía)",
         not g_mal["apta"] and "lista incompleta" in g_mal["motivo"])
cap_lista = PA.caption_instagram(g)
chequear("lista: el texto de Instagram las nombra todas, numeradas, con su dato (y sin link de la nota)",
         all(f"{v} Película {i}: Drama" in cap_lista for i, v in zip(range(1, 6), ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")))
         and "/n/" not in cap_lista)
pz = PA.armar(n_lista, tmp / "lista", redactar_falso([dict(BUENO, lista=PELIS)]),
              leer_pagina=lambda u: {"video": "https://cdn.jwplayer.com/videos/trailer.mp4", "texto": ""})
chequear("lista: sale como CARRUSEL, una lámina por elemento, aunque la nota traiga video",
         pz.get("formato") == "carrusel" and len(pz.get("slides") or []) == 6 and not pz.get("video_original"))

# --- 10. Videos que explotan en La Nación, Infobae, TN y Clarín (18/10/2026) --------------------------
from datetime import datetime as _dt
_hace = lambda h: _dt.fromtimestamp(T8 - h * 3600, timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: E731
yt_items = [
    {"id": "a", "snippet": {"title": "Crisis en Francia: protestas, saqueos y detenidos", "publishedAt": _hace(22)},
     "statistics": {"viewCount": "159000"}, "contentDetails": {"duration": "PT1M5S"}},
    {"id": "b", "snippet": {"title": "AVALANCHA EN CHILE: 4 MUERTOS Y 4 HERIDOS", "publishedAt": _hace(20)},
     "statistics": {"viewCount": "60000"}, "contentDetails": {"duration": "PT45S"}},
    {"id": "c", "snippet": {"title": "EN VIVO: Bolsonaro habla antes del debate", "publishedAt": _hace(2)},
     "statistics": {"viewCount": "3000"}, "contentDetails": {"duration": "P0D"}},
    {"id": "d", "snippet": {"title": "Un video viejo", "publishedAt": _hace(100)},
     "statistics": {"viewCount": "900000"}, "contentDetails": {"duration": "PT30S"}}]
vids = SE.videos_de(yt_items, "La Nación", T8)
chequear("videos: vistas por hora, segundos y solo los de las últimas 72 h",
         [v["id"] for v in vids] == ["a", "b", "c"] and vids[0]["por_hora"] == 7227 and vids[0]["segundos"] == 65
         and vids[2]["segundos"] == 0)
sen_v = dict(SE.vacias(), videos_medios=vids)
francia = [nv("Protestas en Francia: fuertes choques con la Policía y más de 150 detenidos", "La Nación",
              "internacionales")]
canada = [nv("Explosión en una base militar de Canadá: hay siete muertos y decenas de heridos", "Infobae",
             "internacionales")]
bolso = [nv("Lula y Flávio Bolsonaro, cara a cara en el debate", "Infobae", "internacionales")]
ev_f = IM.evaluar(francia, "internacionales", sen_v, T8)
chequear("videos: el tema de un video que explota suma fuerte (y deja la razón)",
         ev_f["desglose"]["video"] >= 18 and any("video que explota en La Nación" in r for r in ev_f["razones"]))
chequear("videos: «muertos» y «heridos» solos no hacen el mismo tema (Canadá no es la avalancha de Chile)",
         IM.evaluar(canada, "internacionales", sen_v, T8)["desglose"]["video"] == 0)
chequear("videos: un vivo no cuenta como video viral",
         IM.evaluar(bolso, "internacionales", sen_v, T8)["desglose"]["video"] == 0)
chequear("Mundo: TN es fuente (después de La Nación) y su sección no exige «gran tema»",
         PO.fuente_de({"url": "https://tn.com.ar/internacional/2026/10/18/x/"}) == "TN"
         and PO.ranking("internacionales").index("TN") == PO.ranking("internacionales").index("La Nación") + 1
         and CAT.puntuar(dict(nv("Un sacerdote murió aplastado por una cruz en Ecuador", "TN", "internacionales"),
                              medio="TN"), T8)[0] > 0)
tn_html = ('<script>Fusion.globalContent={"promo_items":{"basic":{"subtype":"genoa","embed":{"config":'
           '{"content_type":"video","highQuality":"https://vod.vodgc.net/gid1/vod/Artear/TN/1-14-abc_360P.mp4"}}}},'
           '"content_elements":[]};Fusion.globalContentConfig={};</script>'
           '<script>{"highQuality":"https://vod.vodgc.net/gid1/vod/Artear/TN/1-14-OTRA_360P.mp4"}</script>')
chequear("TN: el video PROPIO de la nota (el de su portada), no los de otras notas de la página",
         PO.ficha(tn_html)["video"].endswith("1-14-abc_360P.mp4"))


class _JW:
    """La API pública de JW: un «Loop» de 6 s de cabecera y el video de la nota, vertical."""
    datos = {"LOOP1234": {"title": "Loop. Un sacerdote murió aplastado por una cruz", "playlist": [
        {"duration": 6, "sources": [{"type": "video/mp4", "file": "https://cdn/loop.mp4", "width": 720, "height": 1280}]}]},
             "NOTA5678": {"title": "Un sacerdote murió aplastado por una cruz", "playlist": [
        {"duration": 31, "sources": [
            {"type": "video/mp4", "file": "https://cdn/180.mp4", "width": 180, "height": 320},
            {"type": "video/mp4", "file": "https://cdn/720.mp4", "width": 720, "height": 1280},
            {"type": "video/mp4", "file": "https://cdn/1080.mp4", "width": 1080, "height": 1920},
            {"type": "application/vnd.apple.mpegurl", "file": "https://cdn/x.m3u8"}]}]}}

    def get(self, url):
        i = url.rsplit("/", 1)[1]
        return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: self.datos[i]})()


chequear("JW: el video de la nota (no el «loop» de cabecera), en 720 del lado corto (vertical 720x1280)",
         PO.video_jw(["LOOP1234", "NOTA5678"], "Un sacerdote murió en misa aplastado por una cruz", _JW())
         == "https://cdn/720.mp4")

cola_m = [{"url": "italia", "impacto": 79}, {"url": "papa", "impacto": 76, "otras_urls": ["papa-tn"]},
          {"url": "cura", "impacto": 74}]
pag_m = {"italia": {}, "papa": {}, "papa-tn": {"video": "https://cdn/papa.mp4"}, "cura": {"video": "https://cdn/c.mp4"}}
chequear("Mundo: va primero el tema con VIDEO (aunque esté en otro portal) si está cerca del primero",
         PA.adelantar_con_video(cola_m, lambda c: True, pag_m.get) and [c["url"] for c in cola_m][0] == "papa")
cola_m2 = [{"url": "italia", "impacto": 79}, {"url": "cura", "impacto": 60}]
chequear("Mundo: ...pero no si está a más de 10 puntos",
         not PA.adelantar_con_video(cola_m2, lambda c: True, pag_m.get) and cola_m2[0]["url"] == "italia")

shutil.rmtree(tmp, ignore_errors=True)
# --- 11. La AGENDA propia de nacionales: 10, 18 y 21 (19/10/2026) ------------------------------------------
from nacionales import agenda as AGE
os.environ["NAC_TODO_REEL"] = "1"
_lun = lambda h, m=0: datetime(2026, 10, 19, h, m, tzinfo=AR)      # noqa: E731 — lunes
_sab = lambda h, m=0: datetime(2026, 10, 24, h, m, tzinfo=AR)      # noqa: E731 — sábado
chequear("agenda: lunes a las 18 y 21, 1 política, 1 economía, 1 sociedad y 1 viral; mundo no (20/10/2026)",
         AGE.topes(_lun(18)) == AGE.topes(_lun(21)) == {"politica": 1, "economia": 1, "sociedad": 1, "virales": 1})
chequear("agenda: la sección de cada general (judiciales con política, salud con sociedad)",
         [AGE.subgeneral({"url": f"https://www.infobae.com/{x}/2026/10/20/n/"}) for x in
          ("politica", "judiciales", "economia", "sociedad", "salud", "sociedad/policiales")]
         == ["politica", "politica", "economia", "sociedad", "sociedad", "sociedad"])
chequear("agenda: entre semana solo hay corridas a las 18 y a las 21",
         all(not AGE.topes(_lun(h)) for h in (10, 11, 12, 14, 16)))
chequear("agenda: el finde, 4 corridas (10, 14, 18 y 21) con 1 de cada una de las 7 categorías",
         all(AGE.topes(_sab(h)) == {c: 1 for c in ("virales", "internacionales", "tecnologia_ia", "", "deportes",
                                                    "cine_series", "espectaculos")} for h in (10, 14, 18, 21))
         and AGE.maximo(_sab(10)) == 6 and AGE.maximo(_lun(18)) is None)
chequear("agenda: a qué corrida pertenece cada hora (cron-job.org puede llegar unos minutos antes)",
         AGE.corrida(_lun(18, 7)) == _lun(18) and AGE.corrida(_lun(17, 55)) == _lun(18)
         and AGE.corrida(_lun(22, 30)) == _lun(21) and AGE.corrida(_lun(12)) == _lun(21) - timedelta(days=1)
         and AGE.corrida(_sab(10, 3)) == _sab(10) and AGE.corrida(_sab(13, 55)) == _sab(14)
         and AGE.corrida(_lun(10)) == datetime(2026, 10, 18, 21, 0, tzinfo=AR))
chequear("agenda: cada 30 min, también el finde; el primero a los 15 minutos",
         AGE.minutos(_lun(18)) == 30 and AGE.minutos(_sab(18)) == 30
         and AGE.turnos(_lun(18), 4) == [_lun(18, 15), _lun(18, 45), _lun(19, 15), _lun(19, 45)])
chequear("agenda: si la corrida arrancó tarde (esperó a la anterior), sus turnos corren desde que arranca",
         AGE.turnos(_lun(21), 2, ahora=_lun(21, 40)) == [_lun(21, 45), _lun(22, 15)])
chequear("agenda: tope del día (lunes: 2 de política, 2 virales, mundo 0; sábado: 4 de cada una)",
         AGE.tope_del_dia("virales", _lun(18)) == 2 and AGE.tope_del_dia("politica", _lun(18)) == 2
         and AGE.tope_del_dia("internacionales", _lun(18)) == 0 and AGE.tope_del_dia("internacionales", _sab(18)) == 4
         and AGE.tope_del_dia("deportes", _lun(18)) == 0 and AGE.tope_del_dia("deportes", _sab(18)) == 4)
chequear("agenda: TODO sale como reel con video (generales, IA, deportes… también)",
         all(AGE.solo_reel(c) for c in ("", "virales", "internacionales", "tecnologia_ia", "deportes",
                                        "cine_series", "espectaculos")))
chequear("mundo: internacionales con violencia, conflicto o algo policial, sí; lo demás, no",
         AGE.es_mundo({"titulo": "Francia: toques de queda tras violentas protestas y saqueos"})
         and AGE.es_mundo({"titulo": "Tiroteo en una escuela de Texas: hay tres heridos"})
         and AGE.es_mundo({"titulo": "Detuvieron al líder de un cártel narco en México"})
         and not AGE.es_mundo({"titulo": "El papa León XIV recibió a artistas en el Vaticano"})
         and not AGE.es_mundo({"titulo": "Elecciones en Estados Unidos: qué votan este martes"}))


def _nv(titulo, seccion, slug, cat, cuando):
    return dict(nota_cat(titulo, seccion, slug), categoria=cat, fecha=cuando.timestamp() - 3600)


VIDEO = {"video": "https://cdn.jwplayer.com/videos/v.mp4", "imagen": ""}
SIN = {"video": "", "imagen": ""}
# Lunes 18:00: 1 política, 1 economía, 1 sociedad y 1 viral, todo reel; mundo y deportes no (es lunes).
FOTO_OK.parent.mkdir(parents=True, exist_ok=True)
Image.new("RGB", (1200, 800), (120, 90, 60)).save(FOTO_OK, "JPEG")
PA.MEMORIA = estado_tmp / "nacionales_agenda.json"
reloj["ahora"] = _lun(18, 2)
_gen = [dict(nota_cat("Aumentan las tarifas de luz y gas desde noviembre en todo el país", "economia", "ag1"),
             fecha=_lun(17).timestamp()),
        dict(nota_cat("La CGT anunció un paro general para fin de mes", "politica", "ag2"), fecha=_lun(17).timestamp()),
        dict(nota_cat("El Senado aprobó la ley de financiamiento universitario", "politica", "ag3"),
             fecha=_lun(17).timestamp()),
        dict(nota_cat("Vacunación antigripal: amplían la campaña a los mayores de 50", "sociedad", "ag4"),
             fecha=_lun(17).timestamp())]
_var = [_nv("El video del perro que aprendió a abrir la heladera", "virales", "av1", "virales", _lun(18)),
        _nv("Elecciones en Estados Unidos: qué votan este martes", "america", "av2", "internacionales", _lun(18)),
        dict(_nv("Tiroteo en un shopping de Texas: hay tres heridos", "america", "av3", "internacionales", _lun(18)),
             medio="Infobae"),
        _nv("Boca le ganó a Racing y quedó puntero del Torneo Clausura", "deportes", "av4", "deportes", _lun(18))]
_pag = {n["url"]: VIDEO for n in _var + _gen}
_pag[_gen[2]["url"]] = SIN                                       # la del Senado, sin video
_pag[_gen[3]["url"]] = SIN                                       # la de sociedad, sin video
inf_a = PA.pasada(True, redactar=redactar_lam, notas=_gen, notas_variedad=_var, agenda=True,
                  leer_pagina=lambda u: _pag.get(u, SIN))
_cats = [p.get("categoria") for p in inf_a["piezas"]]
_titulos = " ".join(p["titulo_original"] for p in inf_a["piezas"])
_subs = sorted(p.get("subgeneral") or p.get("categoria") for p in inf_a["piezas"])
chequear("agenda lunes 18: 1 política, 1 economía, 1 sociedad y 1 viral; mundo y deportes no",
         _subs == ["economia", "politica", "sociedad", "virales"]
         and [p["turno"] for p in inf_a["piezas"]] == ["18:15", "18:45", "19:15", "19:45"])
if _subs != ["economia", "politica", "sociedad", "virales"]:
    print("   ", _subs, inf_a["descartadas"], inf_a["fallas"])
chequear("agenda: el lunes no sale mundo (ni el tiroteo)", "Tiroteo" not in _titulos and "Elecciones" not in _titulos)
chequear("agenda: todo sale como reel; de política, la que trae video (el paro) antes que el Senado sin video",
         all(p.get("formato") == "reel" for p in inf_a["piezas"]) and "CGT" in _titulos and "Senado" not in _titulos)
_soc = next((p for p in inf_a["piezas"] if p.get("subgeneral") == "sociedad"), {})
chequear("agenda: la general sin video sale igual como reel, con la foto de la nota",
         _soc.get("formato") == "reel" and not _soc.get("video_original"))

# Sábado 10:00: 7 categorías con video → salen las 6 más virales, 1 de cada una, cada 30 min.
PA.MEMORIA = estado_tmp / "nacionales_agenda_sab.json"
reloj["ahora"] = _sab(10, 1)
_finde = [_nv("Netflix estrena en noviembre la serie de Mafalda", "que-puedo-ver", "sf1", "cine_series", _sab(10)),
          _nv("Cómo se filmó El Eternauta, la serie más vista", "que-puedo-ver", "sf2", "cine_series", _sab(10)),
          _nv("El video del gato que toca el piano y enamoró a todos", "virales", "sf3", "virales", _sab(10)),
          dict(_nv("Bombardeo en Ucrania: decenas de muertos en Kiev", "mundo", "sf4", "internacionales", _sab(10)),
               medio="Infobae"),
          _nv("ChatGPT ya escribe y edita videos: cómo usarlo", "tecnologia", "sf5", "tecnologia_ia", _sab(10)),
          _nv("Boca le ganó a Racing y quedó puntero del Torneo Clausura", "deportes", "sf6", "deportes", _sab(10)),
          _nv("Wanda Nara habló de su separación en televisión", "teleshow", "sf7", "espectaculos", _sab(10))]
_gen_s = [dict(_gen[0], fecha=_sab(9).timestamp())]
_pag_s = {n["url"]: VIDEO for n in _finde + _gen_s}
inf_s = PA.pasada(True, redactar=redactar_lam, notas=_gen_s, notas_variedad=_finde, agenda=True,
                  leer_pagina=lambda u: _pag_s.get(u, SIN))
_cats_s = [p.get("categoria") for p in inf_s["piezas"]]
chequear("agenda sábado 10: 6 reels de 6 categorías distintas, cada 30 min",
         len(_cats_s) == 6 and len(set(_cats_s)) == 6
         and [p["turno"] for p in inf_s["piezas"]] == ["10:15", "10:45", "11:15", "11:45", "12:15", "12:45"]
         and all(p.get("formato") == "reel" for p in inf_s["piezas"]))
print("   agenda lunes:", list(zip([p["turno"] for p in inf_a["piezas"]], _cats)), "· sábado:", _cats_s)
os.environ["NAC_TODO_REEL"] = "0"

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
