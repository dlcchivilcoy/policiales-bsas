# -*- coding: utf-8 -*-
"""LAS HISTORIAS QUE INVITAN A PARTICIPAR (06/11/2026, pedido del editor: «sumar fotos y videos de seguidores […] hacelo
con historias generadas con IA»): una pregunta sobre una imagen generada con IA.

07/11/2026 («más historias interactivas por día para el productor agropecuario y para varios profesionales
relacionados al agro: maquinistas rurales, trabajadores lácteos, contratistas rurales, inmobiliarias, etc.»): varias
por día (agenda.horas_participa), cada una para un oficio, según ROTACION. La placa dice para quién es, y la pregunta
puede traer respuestas de una palabra (lo más parecido a una encuesta que deja la API).

La pregunta la escribe la IA según el oficio, la fecha y, al productor, la lluvia prevista; si no contesta, sale una
de la lista del oficio. La imagen es solo un fondo que ilustra: lo dice la placa y lo dicen los metadatos
(reel_datos.marcar_ia). Nunca se presenta como la foto de un seguidor.

La API de Instagram no permite stickers de encuesta ni de pregunta: se contesta respondiendo la historia, y esas
respuestas llegan a los mensajes de la cuenta. Publicar lo que manden es decisión del editor: acá no se automatiza.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from agro import diseno as D
from agro import historias as HI

MAX_PREGUNTA = 70
MAX_OPCION = 16
RECORDAR = 40                  # no repetir las preguntas de los últimos 10 días
INVITACION = "Respondé esta historia con tu foto o tu dato, y contanos de qué pueblo sos"
AVISO_IA = "Imagen ilustrativa generada con IA"
# La IA dibuja tractores verdes y amarillos que parecen de una marca real (simulación del 07/11/2026).
SIN_MARCAS = ("Any machinery or vehicle must appear only as a tiny dark silhouette far away on the horizon, never close up, "
              "never green and yellow. No logos, no brands, no letters.")
_CANTIDAD = ["Mucho", "Normal", "Poco"]
_ESTADO = ["Bien", "Regular", "Mal"]
PUBLICOS = {
    "agricultura": {
        "etiqueta": "PARA PRODUCTORES",
        "quienes": "productores agrícolas (soja, maíz, trigo, girasol, cebada)",
        "temas": "siembra, cosecha, estado de los lotes, lluvia, malezas, plagas, caminos",
        "lluvia": True,
        "respaldo": (
            {"pregunta": "¿Cómo está tu lote esta semana?", "opciones": _ESTADO, "escena": "Rows of young soybean plants in dark soil in the Argentine pampas, morning light"},
            {"pregunta": "¿Cuánto llovió en tu campo?", "de_lluvia": True, "escena": "Rain gauge on a wooden fence post beside a green crop field under dark rain clouds, no numbers visible"},
            {"pregunta": "¿Cómo viene la siembra en tu zona?", "opciones": ["Adelantada", "Normal", "Atrasada"], "escena": "Planted furrows in dark soil stretching to the horizon in the pampas at sunrise"},
            {"pregunta": "¿Cómo está el trigo por tu zona?", "opciones": _ESTADO, "escena": "Golden wheat heads close up in a large field under a dramatic sky in the pampas"},
            {"pregunta": "¿Cómo quedaron los caminos rurales?", "opciones": _ESTADO, "escena": "Muddy dirt country road between green crop fields after the rain, puddles, wire fence"},
            {"pregunta": "¿Qué se está haciendo hoy en tu campo?", "escena": "Tractor far away working a wide field at dusk, unbranded, dust in the air"},
        ),
    },
    "ganaderia": {
        "etiqueta": "PARA GANADEROS",
        "quienes": "productores ganaderos (cría, recría, engorde)",
        "temas": "estado de la hacienda, pasturas, agua, sanidad, servicio y parición, verdeos",
        "respaldo": (
            {"pregunta": "¿Cómo viene la hacienda en tu campo?", "opciones": _ESTADO, "escena": "Black Angus cattle grazing on green pampas grassland at sunset"},
            {"pregunta": "¿Cómo están las pasturas por tu zona?", "opciones": _ESTADO, "escena": "Lush green pasture with a wire fence and distant cattle under a wide pampas sky"},
            {"pregunta": "¿Cómo está el agua para la hacienda?", "opciones": _ESTADO, "escena": "Cattle drinking at a round water trough beside a windmill in the pampas, late afternoon"},
        ),
    },
    "tambos": {
        "etiqueta": "PARA TAMBEROS Y ORDEÑADORES",
        "quienes": "tamberos y quienes trabajan en el tambo (ordeñadores, guacheras)",
        "temas": "ordeñe, producción de leche, guachera, alimentación de las vacas, rutina diaria",
        "respaldo": (
            {"pregunta": "¿Cómo viene la producción en tu tambo?", "opciones": ["Subiendo", "Igual", "Bajando"], "escena": "Holstein dairy cows walking along a dirt lane toward a rural milking shed at dawn"},
            {"pregunta": "¿A qué hora arrancás el primer ordeñe?", "escena": "Holstein cows waiting in a rural milking yard before sunrise, soft light, no people"},
            {"pregunta": "¿Qué es lo más difícil del trabajo en el tambo?", "escena": "Stainless steel milking equipment in a clean rural milking parlor, cows in the background, no people"},
        ),
    },
    "lacteos": {
        "etiqueta": "PARA TRABAJADORES LÁCTEOS",
        "quienes": "quienes trabajan en usinas lácteas, queserías y fábricas de dulce de leche",
        "temas": "lo que se elabora, el oficio del quesero, la rutina de la planta, los productos que más salen",
        "respaldo": (
            {"pregunta": "¿Qué se está elaborando hoy en tu planta?", "escena": "Rows of artisan cheese wheels aging on wooden shelves in a dairy cellar, warm light, no labels"},
            {"pregunta": "¿Qué queso sale más en tu fábrica?", "escena": "Fresh cheese wheels on a stainless steel table in a small dairy factory, no people, no labels"},
            {"pregunta": "¿Cómo viene el trabajo en la planta?", "opciones": _CANTIDAD, "escena": "Stainless steel milk vats and pipes inside a dairy plant, clean and bright, no people, no labels"},
        ),
    },
    "contratistas": {
        "etiqueta": "PARA CONTRATISTAS RURALES",
        "quienes": "contratistas rurales (siembra, pulverización, cosecha, enrollado, picado)",
        "temas": "las labores de la semana, por dónde andan trabajando, cuánto trabajo hay, la campaña",
        "respaldo": (
            {"pregunta": "¿Qué labor estás haciendo esta semana?", "escena": "Agricultural machinery far away working a huge field at golden hour, unbranded, dust in the air"},
            {"pregunta": "¿Cómo viene el trabajo esta campaña?", "opciones": _CANTIDAD, "escena": "Combine harvester far away in a golden wheat field under a wide sky, unbranded, seen from a distance"},
            {"pregunta": "¿Por qué pueblo andás trabajando hoy?", "escena": "Dirt rural road with a distant tractor crossing the pampas at sunrise, unbranded"},
        ),
    },
    "maquinistas": {
        "etiqueta": "PARA MAQUINISTAS RURALES",
        "quienes": "maquinistas rurales: los que manejan tractor, cosechadora, sembradora o pulverizadora",
        "temas": "la máquina que manejan, las jornadas, lo que revisan antes de salir, la vida arriba de la máquina",
        "respaldo": (
            {"pregunta": "¿Qué máquina estás manejando esta semana?", "escena": "Tractor silhouette far away on a field at sunset, unbranded, big orange sky over the pampas"},
            {"pregunta": "¿Qué es lo primero que revisás antes de arrancar?", "escena": "Close view of a large tractor tire on dark soil at dawn, no logos, no letters"},
            {"pregunta": "¿Qué es lo más difícil arriba de la máquina?", "escena": "Combine harvester working far away at night with its lights on in a wheat field, unbranded"},
        ),
    },
    "agronomos": {
        "etiqueta": "PARA INGENIEROS AGRÓNOMOS",
        "quienes": "ingenieros agrónomos y técnicos que recorren lotes",
        "temas": "malezas, plagas, enfermedades, lo que ven al recorrer los lotes, las consultas que reciben",
        "respaldo": (
            {"pregunta": "¿Qué maleza te está dando más trabajo?", "escena": "Green weed growing between young soybean rows in dark soil, close up, morning light"},
            {"pregunta": "¿Qué plaga estás viendo en los lotes?", "escena": "Close up of a green soybean leaf with small insect bite marks, natural light, field background"},
            {"pregunta": "¿Qué consulta te hacen más esta semana?", "escena": "Green crop rows seen from above stretching to the horizon in the pampas, soft morning light"},
        ),
    },
    "veterinarios": {
        "etiqueta": "PARA VETERINARIOS RURALES",
        "quienes": "veterinarios rurales",
        "temas": "lo que más están atendiendo, sanidad, vacunación, tacto, recorridas por los campos",
        "respaldo": (
            {"pregunta": "¿Qué es lo que más estás atendiendo esta semana?", "escena": "Cattle in a wooden corral on a pampas ranch at morning, dust in the light, no people"},
            {"pregunta": "¿Qué le recomendás hoy a quien tiene hacienda?", "escena": "Hereford cows and calves resting under trees on a pampas ranch, afternoon light"},
            {"pregunta": "¿Por qué pueblos andás recorriendo?", "escena": "Long dirt road between wire fences and cattle fields in the pampas, late afternoon"},
        ),
    },
    "transporte": {
        "etiqueta": "PARA CAMIONEROS DEL CAMPO",
        "quienes": "camioneros que llevan cereal, hacienda o leche",
        "temas": "los caminos, lo que están llevando, las esperas para descargar, las rutas",
        "respaldo": (
            {"pregunta": "¿Cómo están los caminos por donde andás?", "opciones": _ESTADO, "escena": "Long rural road across the pampas with a distant unbranded truck and a dust trail, late afternoon"},
            {"pregunta": "¿Qué estás llevando esta semana?", "opciones": ["Cereal", "Hacienda", "Leche"], "escena": "Unbranded grain truck far away beside grain silos on the pampas at sunset, no letters"},
            {"pregunta": "¿Cómo viene la espera para descargar?", "opciones": ["Larga", "Normal", "Corta"], "escena": "Row of metal grain silos against a dramatic sky in the pampas, no letters, no logos"},
        ),
    },
    "inmobiliarias": {
        "etiqueta": "PARA INMOBILIARIAS RURALES",
        "quienes": "inmobiliarias rurales y corredores de campos",
        "temas": "qué se busca, cómo se mueven los alquileres y las ventas de campos, qué pregunta la gente. Sin pedir valores",
        "respaldo": (
            {"pregunta": "¿Cómo se mueven los alquileres de campos por tu zona?", "opciones": _CANTIDAD, "escena": "Aerial view of pampas farmland divided in green and golden plots by wire fences, soft light"},
            {"pregunta": "¿Qué se busca más por tu zona?", "opciones": ["Comprar", "Alquilar"], "escena": "Old farm gate open onto a dirt path and a wide green field in the pampas, sunset"},
            {"pregunta": "¿Qué es lo primero que pregunta quien busca un campo?", "escena": "Row of tall eucalyptus trees beside a wide green field in the pampas, morning light"},
        ),
    },
    "talleres": {
        "etiqueta": "PARA TALLERES Y METALÚRGICAS",
        "quienes": "talleres de maquinaria agrícola y metalúrgicas del campo",
        "temas": "los arreglos que llegan, las máquinas que entran, cuánto trabajo hay, el oficio",
        "respaldo": (
            {"pregunta": "¿Qué arreglo te llega más esta semana?", "escena": "Mechanic tools on a metal workbench in a rural machinery workshop, warm light, no logos, no people"},
            {"pregunta": "¿Qué máquina entra más a tu taller?", "escena": "Large tractor tires and steel parts inside a rural workshop, warm light, no logos, no letters"},
            {"pregunta": "¿Cómo viene el trabajo en el taller?", "opciones": _CANTIDAD, "escena": "Sparks from welding in a dark rural metal workshop, seen from a distance, no faces, no logos"},
        ),
    },
    "peones": {
        "etiqueta": "PARA PEONES Y ENCARGADOS",
        "quienes": "peones rurales y encargados de campo",
        "temas": "la tarea del día, la recorrida, los animales, lo que les gusta del trabajo de campo",
        "respaldo": (
            {"pregunta": "¿Qué trabajo te toca hoy en el campo?", "escena": "Horse saddled beside a wire fence on a pampas ranch at dawn, no people"},
            {"pregunta": "¿A qué hora arrancaste hoy?", "escena": "Sunrise over a wet pampas field with a wire fence and a gate, mist in the air"},
            {"pregunta": "¿Qué es lo que más te gusta del trabajo de campo?", "escena": "Horses grazing in a wide green field at sunset in the Argentine pampas"},
        ),
    },
    "consignatarios": {
        "etiqueta": "PARA CONSIGNATARIOS Y REMATADORES",
        "quienes": "consignatarios de hacienda y rematadores de ferias",
        "temas": "cómo viene la entrada de hacienda, qué categorías se piden, cómo estuvo el último remate. Sin pedir valores",
        "respaldo": (
            {"pregunta": "¿Cómo viene la entrada de hacienda?", "opciones": _CANTIDAD, "escena": "Cattle in wooden pens at a rural livestock auction yard seen from above, no people, no signs"},
            {"pregunta": "¿Qué categoría se está pidiendo más?", "escena": "Young steers standing in a wooden corral at a rural livestock market, soft light, no people"},
            {"pregunta": "¿Cómo estuvo el último remate?", "opciones": _ESTADO, "escena": "Empty wooden livestock auction pens at sunset on the pampas, dust in the light, no signs"},
        ),
    },
    "acopios": {
        "etiqueta": "PARA ACOPIOS Y AGRONOMÍAS",
        "quienes": "acopios, cooperativas y agronomías que venden insumos",
        "temas": "el movimiento de la semana, lo que más piden los productores, las consultas que reciben",
        "respaldo": (
            {"pregunta": "¿Qué es lo que más te están pidiendo?", "escena": "Close up of soybean and corn grains in a heap, warm natural light, no letters"},
            {"pregunta": "¿Cómo viene el movimiento en tu acopio?", "opciones": _CANTIDAD, "escena": "Metal grain silos at a country cooperative under a blue sky, no letters, no logos"},
            {"pregunta": "¿Qué consulta te hacen más los productores?", "escena": "Grain flowing down a metal chute into a pile, warm light, no letters, no people"},
        ),
    },
}
# Una vuelta cada 4 días con 4 historias por día: la primera de cada día, siempre para productores.
ROTACION = ("agricultura", "contratistas", "tambos", "inmobiliarias",
            "ganaderia", "maquinistas", "agronomos", "transporte",
            "agricultura", "veterinarios", "lacteos", "talleres",
            "ganaderia", "peones", "consignatarios", "acopios")
SYSTEM = """Sos quien maneja @diarioyradioagro, la cuenta del campo de Chivilcoy y su zona (provincia de Buenos
Aires). Escribí UNA pregunta para una historia de Instagram dirigida a la gente del oficio que te indican, que los
invite a contestar con una foto o un dato de lo que está pasando en su trabajo o en su lugar.

Reglas:
- Una sola pregunta, en voseo, directa, de hasta 60 caracteres. Tiene que poder contestarla cualquiera de ese oficio
  hoy, y tiene que ser de SU trabajo. Que tenga que ver con la época del año y, si te lo indican, con la lluvia
  prevista. Usá las palabras comunes del oficio: nada rebuscado.
- Escribí como habla la gente del campo, simple y concreto: sin metáforas ni adornos («rugiendo la máquina», no).
  No uses la palabra «hoy» salvo que haga falta, ni momentos del día («esta mañana»): la historia dura 24 horas. No
  empieces igual que las preguntas recientes.
- No afirmes hechos ni des cifras, nombres, marcas, precios ni pronósticos: solo preguntá. Tampoco des por hecho cómo
  está el clima o el campo (nada de «con esta seca» o «con tanta agua»): cada zona está distinta, la pregunta es abierta.
- Nada de política, retenciones, impuestos, sueldos, despidos ni conflictos gremiales: tiene que ser fácil y amable
  de contestar.
- No repitas ninguna de las preguntas recientes.
- «opciones»: si la pregunta se contesta con una palabra, 2 o 3 respuestas de una o dos palabras, para responder
  rápido. Solo respuestas generales que le sirvan a cualquiera («Mucho», «Normal», «Poco»; «Bien», «Regular», «Mal»;
  «Sí», «No»). Nunca nombres técnicos de plagas, productos o enfermedades: si la respuesta depende de eso, es
  abierta. Si la respuesta es abierta, una lista vacía.
- «escena»: una escena en INGLÉS para generar la imagen de fondo, de la zona pampeana, que ilustre el oficio con el
  lugar de trabajo, el suelo, el cielo, los animales, las herramientas o los productos. Si hay máquinas, solo muy
  lejos y chiquitas. Sin personas de frente, sin carteles, sin textos, sin marcas, sin números.

Contestá SOLO un JSON: {"pregunta": "...", "opciones": ["..."], "escena": "..."}"""


def publico_de(horario: datetime) -> str:
    """El oficio de esa historia: sale del día y de la hora, así el respaldo de las :20 elige el mismo."""
    from agro import agenda as AG
    horas = AG.horas_participa() or [(horario.hour, horario.minute)]
    lugar = (horario.hour, horario.minute)
    i = horas.index(lugar) if lugar in horas else 0
    return ROTACION[(horario.date().toordinal() * len(horas) + i) % len(ROTACION)]


def limpiar_opciones(crudo) -> list:
    """2 o 3 respuestas cortas y sin cifras; cualquier otra cosa, ninguna: la pregunta queda abierta."""
    if not isinstance(crudo, (list, tuple)):
        return []
    o = [" ".join(str(x or "").split()) for x in crudo]
    return o if 2 <= len(o) <= 3 and all(x and len(x) <= MAX_OPCION and not any(c.isdigit() for c in x) for x in o) else []


def invitacion(opciones) -> str:
    if not opciones:
        return INVITACION
    return "Respondé esta historia: " + " · ".join(x.upper() for x in opciones) + ". Y contanos de qué pueblo sos"


def recientes(mem: dict) -> list:
    return [i.get("pregunta") for _k, h in sorted((mem.get("historias") or {}).items())
            if h.get("bloque") == "participa" for i in h.get("items") or [] if i.get("pregunta")][-RECORDAR:]


def respaldo(ya: list, momento: datetime, lluvia_mm=None, publico: str = "agricultura") -> dict:
    """Una de la lista del oficio: la de la lluvia si se espera lluvia; si no, siguiendo el calendario, sin repetir."""
    lista = PUBLICOS[publico]["respaldo"]
    if lluvia_mm is not None and lluvia_mm >= 5:
        de_lluvia = next((o for o in lista if o.get("de_lluvia") and o["pregunta"] not in ya), None)
        if de_lluvia:
            return de_lluvia
    k = momento.date().toordinal()
    candidatas = [lista[(k + i) % len(lista)] for i in range(len(lista))]
    return next((o for o in candidatas if o["pregunta"] not in ya), candidatas[0])


def texto_valido(d) -> bool:
    if not isinstance(d, dict):
        return False
    p, e = " ".join(str(d.get("pregunta") or "").split()), " ".join(str(d.get("escena") or "").split())
    return bool(p and e) and p.startswith("¿") and p.endswith("?") and p.count("?") == 1 and len(p) <= MAX_PREGUNTA \
        and not any(c.isdigit() for c in p)


def pregunta_del_dia(momento: datetime, ya: list, lluvia_mm=None, redactar=None, log=print, publico: str = "agricultura") -> dict:
    """{pregunta, opciones, escena, via, publico}. La IA, o la lista del oficio si no contesta o contesta algo que no sirve."""
    if redactar is None:
        from reels import ia
        redactar = ia.redactar
    p = PUBLICOS[publico]
    if not p.get("lluvia"):
        lluvia_mm = None                                   # a un quesero o a una inmobiliaria no le cambia la pregunta
    material = (f"Oficio: {p['quienes']}.\nTemas posibles: {p['temas']}.\n"
                f"Fecha: {HI.fecha_larga(momento.date())}.\n"
                + (f"Lluvia prevista en Chivilcoy en las próximas 72 horas: {lluvia_mm:.0f} mm.\n" if lluvia_mm is not None else "")
                + "Preguntas recientes (no repetir): " + (" | ".join(ya) or "ninguna"))
    try:
        datos, via = redactar(SYSTEM, material, max_tokens=500)
        if texto_valido(datos) and " ".join(datos["pregunta"].split()) not in ya:
            return {"pregunta": " ".join(datos["pregunta"].split()), "opciones": limpiar_opciones(datos.get("opciones")),
                    "escena": " ".join(datos["escena"].split()), "via": via, "publico": publico}
        log("   la pregunta de la IA no sirve: va una de la lista")
    except Exception as e:                                 # noqa: BLE001 — sin IA, sale igual
        log(f"   la IA no escribió la pregunta ({type(e).__name__}): va una de la lista")
    r = respaldo(ya, momento, lluvia_mm, publico)
    return {"pregunta": r["pregunta"], "opciones": list(r.get("opciones") or []), "escena": r["escena"], "via": "lista", "publico": publico}


def imagen_de_fondo(escena: str, destino: Path, semilla: str, generar=None, mirar=None, log=print) -> str:
    """La escena generada con IA, sin letras; si no se puede, una del banco de imágenes IA ya revisadas."""
    from agro import imagen as IMG
    if generar is None:
        from archivo import imagen as IM
        generar = lambda p, d: IM.generar(p, d, estilo=IMG.ESTILO)      # noqa: E731
        mirar = mirar or IM.tiene_texto
    destino = Path(destino)
    for intento in range(2):
        r = generar(escena, destino)
        if r.get("archivo") and not (mirar and mirar(r["archivo"])):
            return r["archivo"]
        log(f"   imagen IA, intento {intento + 1}: {r.get('motivo') or 'tiene letras'}")
    return IMG.del_banco("agro", semilla)


def placa(pregunta: str, fondo: str, destino: Path, etiqueta: str = "PARTICIPÁ", opciones=()) -> Path:
    """1080x1920, con todo adentro de la zona segura: lo tapan arriba la cuenta y abajo la caja de respuesta."""
    W, H = HI.W, HI.H
    im = Image.new("RGBA", (W, H), HI.FONDO + (255,))
    if fondo and Path(fondo).exists():
        im.alpha_composite(D.cubrir(Image.open(fondo).convert("RGB"), W, H).convert("RGBA"))
    velo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dv = ImageDraw.Draw(velo)
    for y in range(H):
        a = 70 + round(150 * min(1.0, max(0.0, (y - H * 0.28) / (H * 0.32))))
        dv.line((0, y, W, y), fill=HI.FONDO + (a,))
    im.alpha_composite(velo)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 8), fill=D.NARANJA)
    lg = D.lockup("grafito", 60)
    im.alpha_composite(lg, (D.X, HI.SEGURA[0]))
    # El bloque de texto se apoya sobre el final de la zona segura.
    ancho = W - 2 * D.X
    fp, rp = D.ajustar(d, pregunta, "negra", 112, 70, ancho, 4)
    fi, ri = D.ajustar(d, invitacion(opciones), "medium", 44, 34, ancho, 3)
    fa = D.fuente("regular", 26)
    fc = D.fuente("bold", 34)
    alto = 58 + 26 + round(len(rp) * fp.size * 1.14) + 34 + round(len(ri) * fi.size * 1.24) + 34 + 34
    y = HI.SEGURA[1] - alto
    d.rectangle((D.X, y, D.X + d.textlength(etiqueta, font=fc) + 36, y + 58), fill=D.NARANJA_CAJA)
    d.text((D.X + 18, y + 10), etiqueta, font=fc, fill=D.BLANCO)
    y += 58 + 26
    y = D.escribir(d, D.X, y, rp, fp, D.BLANCO, 1.14) + 34
    y = D.escribir(d, D.X, y, ri, fi, (232, 235, 240), 1.24) + 34
    d.text((D.X, y), AVISO_IA, font=fa, fill=(190, 195, 202))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return destino


def _lluvia_prevista(momento: datetime) -> float | None:
    """Los mm previstos en Chivilcoy para las próximas 72 horas, o None."""
    from datetime import timezone
    from agro import mapa_lluvia as ML
    serie = ML._pedir_met(*ML.CENTRO)
    if not serie:
        return None
    desde = momento.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return ML.sumar(serie, desde, desde + timedelta(hours=ML.HORAS))[0]


def pasada(publicar: bool, horario: datetime, log=print, publicador=None, carpeta: Path = None, ahora: datetime = None,
           lluvia_mm="leer", redactar=None, generar=None, mirar=None) -> Path:
    """El turno de la agenda. Se anota junto a las historias (estado/agro.json, «historias», bloque «participa»):
    guardar_estado ya las combina y el respaldo de las :20 no la repite."""
    from agro import informe as INF
    from agro import pasada as PA
    from agro import reel_datos as RD
    ahora = ahora or datetime.now(PA.TZ_AR)
    carpeta = Path(carpeta or PA.SALIDA / ahora.strftime("%Y-%m-%d_%H%M_participa"))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = PA.MEMORIA_REAL if publicar else PA.MEMORIA
    mem = PA.cargar(ruta_mem)
    log(f"[agro] HISTORIA PARA PARTICIPAR {'REAL' if publicar else 'SIMULADA'} {ahora:%d/%m %H:%M} → {carpeta}")
    if lluvia_mm == "leer":
        try:
            lluvia_mm = _lluvia_prevista(ahora)
        except Exception:                                  # noqa: BLE001 — sin el dato, pregunta igual
            lluvia_mm = None
    publico = publico_de(horario)
    txt = pregunta_del_dia(ahora, recientes(mem), lluvia_mm, redactar, log, publico)
    log(f"   {publico}: «{txt['pregunta']}» {txt['opciones'] or ''} ({txt['via']})")
    fondo = imagen_de_fondo(f"{txt['escena']}. {SIN_MARCAS}", carpeta / "participa_fondo.jpg", horario.isoformat(), generar, mirar, log)
    archivo = RD.marcar_ia(placa(txt["pregunta"], fondo, carpeta / "historia_00_participa.jpg",
                                 PUBLICOS[publico]["etiqueta"], txt["opciones"]))
    tanda = [{"tipo": "participa", "clave": "participa", "archivo": str(archivo), "pregunta": txt["pregunta"],
              "opciones": txt["opciones"], "publico": publico, "via": txt["via"]}]
    registro = {"dia": ahora.date().isoformat(), "bloque": "participa", "items": [dict(t) for t in tanda]}
    mem.setdefault("historias", {})
    if publicar:
        if publicador is None:
            from agro import publicar as PUB
            publicador = PUB.publicar_historias
        registro["publicado"] = {"estado": "publicando"}
        mem["historias"][horario.isoformat()] = registro
        PA.guardar(mem, ahora, ruta_mem)
        res = publicador(tanda, log=log)
        registro["publicado"] = {"estado": "listo", "resultado": res}
        for item, r in zip(registro["items"], res.get("items") or []):
            item["publicado"] = r
    else:
        mem["historias"][horario.isoformat()] = dict(registro, simulado=True)
    for it in registro["items"]:
        it.pop("archivo", None) if publicar else None
    PA.guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "historia para participar", "bloque": "participa",
           "conteos": {"Historias": 1}, "historias": tanda, "fuentes": [], "piezas": [], "descartadas": [],
           "grupos_duplicados": [], "config": {"score_min": "—", "max_dia": "—", "horas": 0}, "publicar": publicar,
           "resultado": registro.get("publicado")}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)
