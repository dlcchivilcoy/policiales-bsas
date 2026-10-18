# -*- coding: utf-8 -*-
"""Categorías de VARIEDAD dentro de nacionales (PDF «Prompt integral», etapa 4; rehecho el 18/10/2026 a
pedido del editor): deportes, espectáculos, cine y series, internacionales, virales e IA aplicada a
comercios y emprendedores.

Pedido del 18/10 (en sus palabras): «virales como reels sí o sí video; deportes, espectáculos, IA o
internacionales: si son fotos, como carrusel explicativo para generar retención, y si hay video, como
reels», «la foto y los videos originales en todas, sin generarlas con IA», cupo propio de ~10 por día y
fuentes nuevas: La Nación, El Cronista, internacionales y los blogs de IA.

Fuentes (RSS probados el 18/10/2026, ver data/registro_fuentes.json): Infobae y La Nación (Arc, con el
texto completo), El Cronista (texto completo) y los blogs de Zapier, HubSpot y n8n (en inglés: la IA
del guion lo cuenta en castellano y atribuye todo a la empresa). TyC y ESPN no tienen RSS que funcione;
Clarín, Ámbito, Olé y BBC Mundo solo dan titulares (quedan para después).

Cupo PROPIO, aparte de las 12 nacionales del día: como mucho NAC_VARIEDAD_POR_PASADA (2) por pasada y
un tope por día de cada categoría (NAC_CUPO_<CATEGORIA>): deportes 2, espectáculos 2, internacionales 2,
virales 2, cine y series 1, tecnología 1 → ~10. Rota: va la categoría que hace más que no sale.

Formato (nacionales/pasada.py): con VIDEO original en la nota → REEL; sin video → CARRUSEL explicativo
con la foto original; un VIRAL sin video no sale.
"""
import calendar
import os
import re

import httpx

from nacionales import filtro as F
from nacionales.infobae import HEADERS, _texto, ruta

ARC = "https://www.{sitio}/arc/outboundfeeds/rss/category/{seccion}/?outputType=xml"
# (categoría, medio, feed). «medio» vacío = el blog de una empresa: el guion atribuye todo a ella.
FUENTES = (
    ("deportes", "Infobae", ARC.format(sitio="infobae.com", seccion="deportes")),
    ("deportes", "La Nación", ARC.format(sitio="lanacion.com.ar", seccion="deportes")),
    ("espectaculos", "Infobae", ARC.format(sitio="infobae.com", seccion="teleshow")),
    ("espectaculos", "La Nación", ARC.format(sitio="lanacion.com.ar", seccion="espectaculos")),
    ("cine_series", "Infobae", ARC.format(sitio="infobae.com", seccion="que-puedo-ver")),
    ("internacionales", "Infobae", ARC.format(sitio="infobae.com", seccion="america")),
    ("internacionales", "La Nación", ARC.format(sitio="lanacion.com.ar", seccion="el-mundo")),
    ("virales", "Infobae", ARC.format(sitio="infobae.com", seccion="virales")),
    ("tecnologia_ia", "Infobae", ARC.format(sitio="infobae.com", seccion="tecno")),
    ("tecnologia_ia", "El Cronista", "https://www.cronista.com/files/rss/news.xml"),
    ("tecnologia_ia", "", "https://zapier.com/blog/feeds/latest/"),
    ("tecnologia_ia", "", "https://blog.hubspot.com/marketing/rss.xml"),
    ("tecnologia_ia", "", "https://blog.n8n.io/rss/"),
)

# Cuánto atrás se mira: deportes, espectáculos e internacionales son del día; los estrenos se anuncian
# con días de anticipación; los virales y las guías de IA no vencen en horas.
HORAS_VENTANA = {"deportes": 24, "espectaculos": 24, "internacionales": 24, "cine_series": 72,
                 "virales": 72, "tecnologia_ia": 96}

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
                "marketers", "how to", "guide", "examples", "tips"])

CATEGORIAS = {
    "deportes": {"nombre": "Deportes", "cupo": 2, "web": "094f631e-1b56-485f-8777-6e167802455e"},
    # Las tres siguientes se crearon en Wix y en diario_web el 17/10/2026 (diario_web 4689c1a).
    "espectaculos": {"nombre": "Espectáculos", "cupo": 2, "web": "973d6c3f-8893-4d88-92fe-78c91ab6d1ce"},
    "cine_series": {"nombre": "Cine y series", "cupo": 1, "web": "03a75413-7258-4eca-b163-2f931193635c"},
    "tecnologia_ia": {"nombre": "Tecnología", "cupo": 1, "web": "5b9d1e36-6d94-48ab-b5f6-6f9cb1b8fcaf"},
    # Las dos siguientes, el 18/10/2026 (secciones Mundo y Virales).
    "internacionales": {"nombre": "Mundo", "cupo": 2, "web": "0e9c99fe-f2e1-4ca5-b5c6-c175cb191aee"},
    "virales": {"nombre": "Virales", "cupo": 2, "web": "95f4a5db-061c-407d-8b06-7fc9378741e8"},
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


def por_pasada() -> int:
    return _entero("NAC_VARIEDAD_POR_PASADA", 2)


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

def _imagen(e) -> str:
    for m in (e.get("media_content") or []) + (e.get("media_thumbnail") or []):
        if (m.get("url") or "").startswith("http") and "video" not in (m.get("type") or ""):
            return m["url"].strip()
    for l in e.get("links") or []:
        if (l.get("type") or "").startswith("image/") and (l.get("href") or "").startswith("http"):
            return l["href"]
    return ""


def notas_del_feed(xml: str, cat: str, medio: str) -> list:
    """Las notas de UN feed, sin red (se prueba solo)."""
    import feedparser
    salida = []
    for e in feedparser.parse(xml).entries:
        url = (e.get("link") or "").split("?")[0]
        if not url.startswith("https://"):
            continue
        cuerpo = _texto((e.get("content") or [{}])[0].get("value", "")) or _texto(e.get("summary") or "")
        fecha = e.get("published_parsed") or e.get("updated_parsed")
        salida.append({"url": url, "seccion_feed": cat, "categoria": cat, "medio": medio, "es_blog": not medio,
                       "titulo": " ".join((e.get("title") or "").split()), "resumen": _texto(e.get("summary") or "")[:600],
                       "cuerpo": cuerpo, "fecha": calendar.timegm(fecha) if fecha else 0, "imagen": _imagen(e),
                       "credito_feed": " ".join(str(e.get("credit") or "").split())})
    return salida


def bajar(fuentes=FUENTES, cliente=None) -> tuple:
    """(notas, fallas). Una fuente que no contesta no frena las otras."""
    cliente = cliente or httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
    notas, vistas, fallas = [], set(), []
    for cat, medio, url in fuentes:
        try:
            r = cliente.get(url)
            r.raise_for_status()
        except Exception as e:                       # noqa: BLE001
            fallas.append(f"{medio or url}: {type(e).__name__}: {str(e)[:100]}")
            continue
        for n in notas_del_feed(r.text, cat, medio):
            if n["url"] not in vistas:
                vistas.add(n["url"])
                notas.append(n)
    return notas, fallas


# =============================================================================
# Elegir
# =============================================================================

def puntuar(n: dict, ahora: float) -> tuple:
    """(puntos, motivo) de una nota de variedad. 0 = no va."""
    cat = de_que_categoria(n)
    if not cat:
        return 0, "otra sección"
    if ahora - (n.get("fecha") or 0) > HORAS_VENTANA.get(cat, 24) * 3600:
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
        if n.get("medio") != "La Nación" and not GRAN_TEMA.search(cabeza):
            return 0, "noticia local de otro país, sin relevancia acá"
        return 35 + (10 if F.ARGENTINA.search(titulo) else 0), "internacional"
    if cat == "virales":
        return 35, "viral (sale solo si la nota trae su video)"
    if cat == "tecnologia_ia":
        if not IA.search(titulo if n.get("es_blog") else cabeza):
            return 0, "tecnología sin IA"
        if not NEGOCIO.search(titulo):
            return 0, "IA sin aplicación para comercios, empresas o el trabajo"
        return 40, "IA aplicada"
    return 0, ""


def candidatas(notas: list, ahora: float) -> dict:
    """{categoría: [candidatas, de mejor a peor]}: una por tema, con la cobertura sumada (el mismo tema
    en Infobae y en La Nación es UNA candidata, y más fuerte)."""
    recientes = []
    for n in notas:
        p, motivo = puntuar(n, ahora)
        if p > 0:
            recientes.append(dict(n, puntos_base=p, nivel=de_que_categoria(n), motivos=[motivo]))
    salida = {cat: [] for cat in CATEGORIAS}
    for grupo in F.agrupar(recientes):
        mejor = max(grupo, key=lambda x: (x["puntos_base"], bool(x.get("imagen")), x.get("fecha") or 0))
        cobertura = len(grupo)
        puntos = mejor["puntos_base"] + F.BONO_COBERTURA * min(cobertura - 1, F.TOPE_COBERTURA)
        salida[mejor["nivel"]].append(dict(mejor, categoria=mejor["nivel"], puntos=puntos, cobertura=cobertura,
                                           tema=sorted(F.palabras_tema(mejor)),
                                           otras=[x["titulo"] for x in grupo if x is not mejor][:4],
                                           otras_urls=[x["url"] for x in grupo if x is not mejor][:4]))
    for cat in salida:
        salida[cat].sort(key=lambda x: (-x["puntos"], -(x.get("fecha") or 0)))
    return salida


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
# directo. Los posteos de TikTok, Instagram o X embebidos NO: viven en esas plataformas.
_LD_VIDEO = re.compile(r'"contentUrl"\s*:\s*"(https://[^"]+?\.mp4[^"]*)"')
_JW_MP4 = re.compile(r'https://cdn\.jwplayer\.com/videos/[\w-]+\.mp4')
_OG_IMG = re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"|'
                     r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"')


def medios_de_la_pagina(html: str) -> dict:
    """{video, imagen} de la página de la nota, sin red (se prueba solo)."""
    video = (_LD_VIDEO.findall(html) or _JW_MP4.findall(html) or [""])[0].replace("\\u002F", "/")
    og = _OG_IMG.search(html)
    imagen = (og.group(1) or og.group(2)).replace("&amp;", "&") if og else ""
    return {"video": video, "imagen": imagen}


def leer_pagina(url: str, cliente=None) -> dict:
    """{video, imagen} de la nota (un pedido). Vacío si la página no contesta."""
    cliente = cliente or httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
    try:
        r = cliente.get(url)
        r.raise_for_status()
    except Exception:                                 # noqa: BLE001
        return {"video": "", "imagen": ""}
    return medios_de_la_pagina(r.text)


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
