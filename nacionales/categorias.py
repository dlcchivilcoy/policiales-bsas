# -*- coding: utf-8 -*-
"""Categorías de VARIEDAD dentro de nacionales (PDF «Prompt integral», etapa 4; rehecho el 18/10/2026 a
pedido del editor): deportes, espectáculos, cine y series, internacionales, virales e IA aplicada a
comercios y emprendedores.

Pedido del 18/10 (en sus palabras): «virales como reels sí o sí video; deportes, espectáculos, IA o
internacionales: si son fotos, como carrusel explicativo para generar retención, y si hay video, como
reels», «la foto y los videos originales en todas, sin generarlas con IA» y cupo propio de ~10 por día.
Y el mismo día: «scrapeá TODOS los portales del PDF y hacé un sistema de scoring para poner las notas
que tengan más impacto viral… respetando el ranking de sitios por categoría».

Fuentes: TODOS los portales del PDF que dejan leer (nacionales/portales.py, con su orden por
categoría; probados el 18/10/2026, ver data/registro_fuentes.json). Puntaje: nacionales/impacto.py
(jerarquía de la fuente según el PDF + cobertura en varios portales + «más leídas» + búsquedas en
Google + Google News + YouTube + actualidad), con las señales de nacionales/senales.py.

Cupo (desde el 18/10/2026 a la noche, la FILA de 15 minutos de reels/turnos.py): cada categoría tiene un
tope POR PASADA (NAC_PASADA_<CATEGORIA>): deportes 2, espectáculos 2, mundo 2, virales 1, cine y series
1, tecnología 1; y uno POR DÍA de seguridad (NAC_CUPO_<CATEGORIA>): 10, 10, 10, 4, 4 y 3. En cada turno
va la categoría con el tema más fuerte (menos 12 puntos por pieza que ya salió en la pasada), nunca la
misma que el turno anterior.

Formato (nacionales/pasada.py): con VIDEO original en la nota → REEL; sin video → CARRUSEL explicativo
con la foto original; un VIRAL sin video no sale.
"""
import os
import re

from nacionales import filtro as F
from nacionales.infobae import ruta

from nacionales import impacto as IM
from nacionales import portales as PO

# Cuánto atrás se mira: deportes, espectáculos e internacionales son del día; los estrenos se anuncian
# con días de anticipación; los virales y las guías de IA no vencen en horas.
HORAS_VENTANA = {"deportes": 24, "espectaculos": 24, "internacionales": 24, "cine_series": 72,
                 "virales": 72, "tecnologia_ia": 96}
# Las guías de los blogs de IA (Zapier, HubSpot, n8n…) no vencen en días: publican una o dos por semana.
HORAS_BLOG = 14 * 24


def ventana(n: dict, cat: str = "") -> float:
    """Horas hacia atrás que se miran para esta nota."""
    return HORAS_BLOG if n.get("es_blog") else HORAS_VENTANA.get(cat or de_que_categoria(n), 24)

ARGENTINA = F.rx(["argentina", "argentino", "argentinos", "argentinas", "seleccion", "scaloni", "messi",
                  "afa", "liga profesional", "copa argentina", "torneo clausura", "torneo apertura",
                  "boca", "river", "racing", "independiente", "san lorenzo", "estudiantes", "gimnasia",
                  "velez", "huracan", "lanus", "banfield", "talleres", "belgrano", "rosario central",
                  "newells", "colon", "union", "argentinos juniors", "platense", "tigre", "defensa y justicia",
                  "libertadores", "sudamericana", "colapinto", "pumas", "leonas", "los pumas", "las leonas",
                  "dibu", "mastantuono", "franco colapinto", "tenista argentino", "cerundolo", "etcheverry"])
EN_VIVO = F.rx(["en vivo", "minuto a minuto", "en directo", "live", "como ver", "a que hora juega",
                "donde ver", "formaciones", "apuestas", "pronostico", "quiniela", "horoscopo"])
TELESHOW_FUERA = F.rx(["fotos:", "la foto de", "el look", "outfit", "sugestiva", "picante",
                       "chicana", "indirecta", "palito", "letal", "filoso", "filosa"])
CINE_SERIES = F.rx(["estreno", "estrena", "estrenos", "netflix", "disney", "max", "prime video", "hbo",
                    "paramount", "apple tv", "star+", "cines", "cine", "pelicula", "peliculas", "serie",
                    "series", "temporada", "documental", "taquilla", "oscar", "trailer", "tráiler"])
VIDEOJUEGOS = F.rx(["videojuego", "videojuegos", "gamer", "playstation", "xbox", "nintendo", "steam"])
# Internacionales de Infobae «América» trae mucho de cada país (contratos laborales en Panamá…): entra lo
# que es un gran tema o le toca a la Argentina; La Nación «El mundo» ya viene curado.
GRAN_TEMA = F.rx(["estados unidos", "trump", "casa blanca", "papa", "leon xiv", "vaticano", "rusia", "putin",
                  "ucrania", "israel", "gaza", "hamas", "iran", "china", "brasil", "lula", "chile", "uruguay",
                  "paraguay", "bolivia", "venezuela", "maduro", "mexico", "espana", "europa", "onu", "otan",
                  "guerra", "elecciones", "terremoto", "huracan", "tsunami", "atentado", "argentina",
                  "argentinos", "milei", "mundial", "nobel"])
IA = F.rx(["inteligencia artificial", "ia", "chatgpt", "gemini", "copilot", "claude", "openai", "chatbot",
           "chatbots", "agente de ia", "agentes de ia", "ia generativa",
           # los blogs, en inglés
           "ai", "artificial intelligence", "gpt", "llm", "agent", "agents", "automation", "automate",
           "automations", "workflow", "workflows"])
# El uso PRÁCTICO para un comercio, un emprendedor o una oficina, en el TÍTULO (no «las empresas» en
# general: así entraban OpenAI y una billetera cripto, o un informe sobre América Latina).
NEGOCIO = F.rx(["pymes", "pyme", "comercios", "comerciante", "comerciantes", "emprendedor",
                "emprendedores", "emprendimiento", "emprendimientos", "pequenas empresas", "pequena empresa",
                "ventas", "vender", "clientes", "atencion al cliente", "whatsapp", "excel", "planillas",
                "hojas de calculo", "correos", "productividad", "facturacion", "tienda online", "e-commerce",
                "comercio electronico", "marketing", "automatizar", "automatizacion", "tareas", "oficina",
                "como usar", "paso a paso", "trucos", "shopify", "mercado libre", "vendedores", "tiendas",
                # en inglés
                "small business", "business", "customers", "customer", "sales", "ecommerce", "crm",
                "email", "emails", "spreadsheet", "spreadsheets", "productivity", "support", "team", "teams",
                "marketers", "how to", "guide", "examples", "tips", "tools", "apps", "software",
                "assistant", "assistants", "chatbot", "chatbots", "beginner", "workplace", "work",
                "meeting", "meetings", "prospecting", "leads", "lead", "tickets", "store", "stores",
                "shop", "merchants", "commerce"])

# «cupo»: tope por DÍA (de seguridad); «pasada»: tope por PASADA (la fila de 15 minutos, 18/10/2026).
CATEGORIAS = {
    "deportes": {"nombre": "Deportes", "cupo": 10, "pasada": 2, "web": "094f631e-1b56-485f-8777-6e167802455e"},
    # Las tres siguientes se crearon en Wix y en diario_web el 17/10/2026 (diario_web 4689c1a).
    "espectaculos": {"nombre": "Espectáculos", "cupo": 10, "pasada": 2, "web": "973d6c3f-8893-4d88-92fe-78c91ab6d1ce"},
    "cine_series": {"nombre": "Cine y series", "cupo": 4, "pasada": 1, "web": "03a75413-7258-4eca-b163-2f931193635c"},
    "tecnologia_ia": {"nombre": "Tecnología", "cupo": 3, "pasada": 1, "web": "5b9d1e36-6d94-48ab-b5f6-6f9cb1b8fcaf"},
    # Las dos siguientes, el 18/10/2026 (secciones Mundo y Virales).
    "internacionales": {"nombre": "Mundo", "cupo": 10, "pasada": 2, "web": "0e9c99fe-f2e1-4ca5-b5c6-c175cb191aee"},
    "virales": {"nombre": "Virales", "cupo": 4, "pasada": 1, "web": "95f4a5db-061c-407d-8b06-7fc9378741e8"},
}
NACIONALES_ID = "b646fede-00cb-4f10-aca5-56fdda96094a"
# Rutas de Infobae por categoría (para notas viejas sin «categoria», y para las pruebas).
_RUTAS = {"deportes": ("/deportes/",), "espectaculos": ("/teleshow/",),
          "cine_series": ("/que-puedo-ver/", "/malditos-nerds/"), "tecnologia_ia": ("/tecno/",),
          "virales": ("/virales/",)}


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.environ.get(nombre) or defecto))
    except ValueError:
        return defecto


def cupo_dia(cat: str) -> int:
    return _entero(f"NAC_CUPO_{cat.upper()}", CATEGORIAS[cat]["cupo"])


def tope_pasada(cat: str) -> int:
    return _entero(f"NAC_PASADA_{cat.upper()}", CATEGORIAS[cat]["pasada"])


def seccion_web(cat: str) -> str:
    """La categoría de Wix: la propia (o la cargada en WIX_CAT_<CATEGORIA>); si no hay, Nacionales."""
    return (os.environ.get(f"WIX_CAT_{cat.upper()}") or "").strip() or CATEGORIAS[cat]["web"] or NACIONALES_ID


def de_que_categoria(n: dict) -> str:
    if n.get("categoria") in CATEGORIAS:
        return n["categoria"]
    p = ruta(n.get("url"))
    for cat, rutas in _RUTAS.items():
        if p.startswith(rutas):
            return cat
    return ""


# =============================================================================
# Leer las fuentes
# =============================================================================

# Lo que en una sección general (sociedad, internacional, lo último) es un VIRAL: el título lo dice, o
# es un VIDEO de algo insólito, emotivo o gracioso. NUNCA un policial (PDF, apartado 11: un hecho
# policial lejano no se reclasifica como viral para saltar el radio de 100 km).
VIRAL = F.rx(["viral", "virales", "viralizo", "viralizado", "viralizada", "se viralizo", "se hizo viral",
              "furor en redes", "furor en las redes", "revoluciono las redes", "estallaron las redes",
              "explotaron las redes", "en tiktok", "tiktoker", "tiktokers", "influencer", "es tendencia"])
VIDEO = F.rx(["video", "videos", "filmo", "filmaron", "grabo", "grabaron", "registro el momento", "quedo filmado",
              "el momento en que", "captaron", "las imagenes"])
LLAMATIVO = F.rx(["insolito", "insolita", "increible", "sorprendente", "sorprendio", "conmovedor", "conmovio",
                  "emotivo", "emociono", "tierno", "gracioso", "divertido", "curioso", "furor", "redes",
                  "inesperado", "inesperada", "asombro", "hazana", "record", "guinness", "perrito", "gatito",
                  "mascota", "animal"])
POLICIAL = F.rx(["robo", "robaron", "asalto", "asaltaron", "delincuente", "delincuentes", "ladron", "ladrones",
                 "motochorro", "motochorros", "policia", "policial", "detenido", "detuvieron", "crimen",
                 "asesinato", "mato", "murio", "muerte", "muerto", "choque", "accidente", "tiroteo", "disparo",
                 "balazo", "violencia", "golpiza", "pelea", "agresion", "ataque", "abuso", "fiscal",
                 "camara de seguridad", "camaras de seguridad"])


def es_viral(titulo: str) -> bool:
    t = F.norm(titulo)
    return not POLICIAL.search(t) and bool(VIRAL.search(t) or (VIDEO.search(t) and LLAMATIVO.search(t)))


def clasificar(n: dict) -> dict:
    """La categoría de una nota según su fuente: «espectaculos+cine» se parte en cine y series o
    espectáculos; de las secciones «general» solo quedan los virales (lo demás queda sin categoría:
    no sale, pero cuenta para la cobertura del tema)."""
    cat, titulo = n.get("categoria"), F.norm(n.get("titulo"))
    if cat == "espectaculos+cine":
        cat = "cine_series" if CINE_SERIES.search(titulo) and not VIDEOJUEGOS.search(titulo) else "espectaculos"
    elif cat in ("general", "nacionales"):
        cat = "virales" if es_viral(n.get("titulo") or "") else ""
    return dict(n, categoria=cat, seccion_feed=cat or n.get("seccion_feed"))


def bajar(fuentes=None, cliente=None) -> tuple:
    """(notas, fallas, conteo por fuente) de todos los portales de variedad, ya clasificadas."""
    notas, fallas, conteo = PO.bajar(PO.FUENTES if fuentes is None else fuentes, cliente)
    # Una nota que vino por dos lados (el RSS general de El Cronista está en IA y en virales): queda una,
    # la que tiene categoría.
    salida = {}
    for n in map(clasificar, notas):
        if n["url"] not in salida or (n["categoria"] and not salida[n["url"]]["categoria"]):
            salida[n["url"]] = n
    return list(salida.values()), fallas, conteo


# =============================================================================
# Elegir
# =============================================================================

MUNDO_CURADO = {"La Nación", "TN", "Clarín", "Infobae"}


def puntuar(n: dict, ahora: float) -> tuple:
    """(puntos, motivo) de una nota de variedad. 0 = no va."""
    cat = de_que_categoria(n)
    if not cat:
        return 0, "otra sección"
    if ahora - (n.get("fecha") or 0) > ventana(n, cat) * 3600:
        return 0, "vieja"
    titulo, cabeza = F.norm(n.get("titulo")), F.norm(f"{n.get('titulo')} . {n.get('resumen')}")
    if EN_VIVO.search(titulo):
        return 0, "cobertura en vivo o servicio de horarios: el resultado todavía no es final"
    if cat == "deportes":
        if not ARGENTINA.search(cabeza):
            return 0, "deporte sin protagonista argentino"
        return 40 + (10 if F.CHIVILCOY.search(F.norm(n.get("cuerpo"))) else 0), "deporte argentino"
    if cat == "espectaculos":
        if TELESHOW_FUERA.search(titulo):
            return 0, "galería o farándula sin noticia"
        return 35, "espectáculos"
    if cat == "cine_series":
        if not CINE_SERIES.search(cabeza) or VIDEOJUEGOS.search(titulo):
            return 0, "no es cine ni series"
        return 35 + (10 if re.search(r"\bestren", titulo) else 0), "cine y series"
    if cat == "internacionales":
        # La Nación, TN, Clarín e Infobae eligen su sección Mundo para el público argentino (y ahí están
        # los videos que se viralizan, 18/10/2026): no hace falta que sea un «gran tema».
        if n.get("medio") not in MUNDO_CURADO and not GRAN_TEMA.search(cabeza):
            return 0, "noticia local de otro país, sin relevancia acá"
        return 35 + (10 if F.ARGENTINA.search(titulo) else 0), "internacional"
    if cat == "virales":
        if POLICIAL.search(titulo):
            return 0, "policial: no se pasa a viral (radio de 100 km)"
        return 35, "viral (sale solo si la nota trae su video)"
    if cat == "tecnologia_ia":
        if not IA.search(titulo if n.get("es_blog") else cabeza):
            return 0, "tecnología sin IA"
        if not NEGOCIO.search(titulo):
            return 0, "IA sin aplicación para comercios, empresas o el trabajo"
        return 40, "IA aplicada"
    return 0, ""


def candidatas(notas: list, ahora: float, senales: dict = None) -> dict:
    """{categoría: [candidatas, de más a menos IMPACTO]}: una por tema (el mismo tema en Infobae, Olé y
    TyC es UNA candidata, y más fuerte), contada desde la mejor fuente según el orden del PDF."""
    senales = senales or {}
    recientes = []
    for n in notas:
        cat = de_que_categoria(n)
        if ahora - (n.get("fecha") or 0) > ventana(n, cat) * 3600:
            continue
        p, motivo = puntuar(n, ahora)
        recientes.append(dict(n, puntos_base=p, nivel=cat, motivos=[motivo]))
    salida = {cat: [] for cat in CATEGORIAS}
    piso = IM.minimo()
    # Las guías de los blogs (en inglés) no se agrupan: compartían «best», «guide»… y se inflaba la
    # cobertura. Cada una es su propio tema.
    grupos = F.agrupar([x for x in recientes if not x.get("es_blog")])
    grupos += [[x] for x in recientes if x.get("es_blog")]
    for todas in grupos:
        grupo = [x for x in todas if x["puntos_base"] > 0]
        if not grupo:
            continue
        # La nota que se cuenta: la de la mejor fuente del orden del PDF; a igual fuente, con foto y
        # con más texto.
        mejor = max(grupo, key=lambda x: (IM.puntos_fuente(PO.fuente_de(x), x["nivel"]), bool(x.get("imagen")),
                                          len(x.get("cuerpo") or ""), x.get("fecha") or 0))
        cat = mejor["nivel"]
        ev = IM.evaluar(todas, cat, senales, ahora, ventana(mejor, cat), mejor["puntos_base"],
                        principal=PO.fuente_de(mejor))
        if ev["impacto"] < piso:
            continue
        otras = sorted((x for x in todas if x is not mejor),
                       key=lambda x: -IM.puntos_fuente(PO.fuente_de(x), cat))
        salida[cat].append(dict(mejor, categoria=cat, puntos=ev["impacto"], impacto=ev["impacto"],
                                impacto_senal=ev["senal"], impacto_desglose=ev["desglose"],
                                impacto_razones=ev["razones"], cobertura=len(todas),
                                fuentes=list(dict.fromkeys(PO.fuente_de(x) for x in todas)),
                                tema=sorted(F.palabras_tema(mejor)),
                                otras=[x["titulo"] for x in otras][:4], otras_urls=[x["url"] for x in otras][:4]))
    for cat in salida:
        salida[cat].sort(key=lambda x: (-x["impacto"], -(x.get("fecha") or 0)))
    return salida


def orden_por_impacto(por_cat: dict, piezas_hoy: list, ultimas: dict) -> list:
    """Las categorías con cupo hoy, primero la que tiene el tema con más impacto (lo que dice la gente:
    lectores, búsquedas, cobertura, Google News, YouTube), menos 12 puntos por pieza que ya salió hoy de
    esa categoría. A igual impacto, la que hace más que no sale."""
    rotacion = orden_de_rotacion(piezas_hoy, ultimas)
    hechas = {}
    for p in piezas_hoy:
        if p.get("categoria"):
            hechas[p["categoria"]] = hechas.get(p["categoria"], 0) + 1
    mejor = {c: max((x.get("impacto_senal") or 0 for x in por_cat.get(c) or []), default=-1) for c in rotacion}
    return sorted((c for c in rotacion if por_cat.get(c)),
                  key=lambda c: (-(mejor[c] - 12 * hechas.get(c, 0)), rotacion.index(c)))


def orden_de_rotacion(piezas_hoy: list, ultimas: dict) -> list:
    """Las categorías con cupo hoy, la que hace más que no sale primero. `piezas_hoy`: las piezas de
    hoy de la memoria (con «categoria»); `ultimas`: {categoría: ISO de su última pieza, de cualquier día}."""
    hechas = {}
    for p in piezas_hoy:
        if p.get("categoria"):
            hechas[p["categoria"]] = hechas.get(p["categoria"], 0) + 1
    con_cupo = [c for c in CATEGORIAS if hechas.get(c, 0) < cupo_dia(c)]
    return sorted(con_cupo, key=lambda c: ultimas.get(c) or "")


# =============================================================================
# El video y la foto ORIGINALES de la nota (18/10/2026: «sin generarlas con IA»)
# =============================================================================
# El video que el propio portal sirve en su reproductor (JW Player en Infobae y La Nación): el MP4
# directo. Los posteos de TikTok, Instagram o X embebidos NO: viven en esas plataformas. Además, el
# TEXTO completo (para los portales cuyo RSS trae solo el titular: Ámbito, Clarín, Olé, ESPN, TyC…).
medios_de_la_pagina = PO.ficha
leer_pagina = PO.leer


# Lo que la IA tiene que respetar en cada categoría (se suma al prompt de nacionales).
_CARRUSEL = """
LAMINAS (para el carrusel explicativo de Instagram, por si la nota no trae video): de 4 a 6 objetos
{"titulo": "...", "texto": "..."} que cuenten la noticia en orden: 1) el hecho principal, 2) los datos
clave, 3) el contexto o por qué importa, 4) límites, dudas o qué falta saber, 5-6) cómo sigue o una
conclusión útil. Título de la lámina: máximo 45 caracteres. Texto: entre 18 y 40 palabras, frases
completas, sin repetir el titular. Mismas reglas de siempre: nada inventado, atribuido, sin calcar."""
GUIAS = {
    "deportes": """
CATEGORÍA DEPORTES (esta nota): la sección es «Deportes».
- Diferenciá SIEMPRE: resultado FINAL y partido en juego; negociación y contratación CONFIRMADA;
  convocatoria tentativa y oficial; horario original y reprogramación. Si el material no dice que
  algo está confirmado, escribilo como lo que es («negocia», «podría», «está en carpeta»).
- Fecha, competición y rival exactos, como en el material. Nada de apuestas ni pronósticos.
- APTA false si es una previa sin datos, un «en vivo» o un servicio de horarios.""",
    "espectaculos": """
CATEGORÍA ESPECTÁCULOS (esta nota): la sección es «Espectáculos».
- FALLECIMIENTOS: solo si el material dice QUIÉN lo confirmó (la familia, sus representantes, el
  canal, una institución). Si no hay confirmación atribuida, APTA false. Tono sobrio, sin morbo; la
  causa de muerte SOLO si el material la atribuye a una fuente, nunca la deduzcas. No confundas una
  muerte reciente con un homenaje o un aniversario.
- Nada de chismes sin fuente: lo que dijo alguien va atribuido y entre comillas como mucho una vez.
- Separaciones, embarazos o romances: solo lo que el protagonista o su entorno confirmó.""",
    "cine_series": """
CATEGORÍA CINE Y SERIES (esta nota): la sección es «Cine y series».
- Distinguí anuncio, tráiler, rodaje y ESTRENO. Plataforma o sala, PAÍS y FECHA tal cual el material.
- No afirmes que ya se puede ver en la Argentina si el material no lo dice: en ese caso, «se estrena
  el … en [plataforma]» sin sumar países. Si falta la fecha, decilo («todavía sin fecha»).
- Sin spoilers del final.""",
    "internacionales": """
CATEGORÍA MUNDO (esta nota): la sección es «Mundo».
- País y fecha del hecho, claros. Lo que dice cada gobierno o protagonista, atribuido.
- Si el material dice qué le toca a la Argentina o a los argentinos, va adelante.
- No traduzcas como investigación propia lo que es un cable: contalo como información.""",
    "virales": """
CATEGORÍA VIRALES (esta nota): la sección es «Virales». La pieza es un VIDEO que circula.
- Contá qué se ve, quién lo publicó, dónde y cuándo, SOLO con lo que dice el material.
- No afirmes como comprobado lo que el material presenta como versión o interpretación del video.
- Si es un video viejo que vuelve a circular, decilo. APTA false si el material no dice de dónde sale.""",
    "tecnologia_ia": """
CATEGORÍA TECNOLOGÍA / IA PARA COMERCIOS Y EMPRENDEDORES (esta nota): la sección es «Tecnología».
- Contá qué TAREA resuelve (atender clientes, vender, ordenar planillas, contestar correos…), para
  quién sirve, qué hace falta para usarla, qué LÍMITES tiene y si se sabe disponibilidad o precio.
- Lo que dice una empresa sobre su producto va ATRIBUIDO («según la empresa»): nunca como un hecho
  comprobado. NUNCA digas que lo probamos ni prometas ganancias o ahorros.
- Si el material está en inglés, escribí todo en castellano rioplatense neutro.
- Si es solo un anuncio de producto sin uso práctico para un comercio o un emprendedor, APTA false.""",
}
GUIAS = {k: v + _CARRUSEL for k, v in GUIAS.items()}
# Las nacionales generales también salen en Instagram (18/10/2026): sin video, con su carrusel explicativo.
GUIAS[""] = _CARRUSEL
