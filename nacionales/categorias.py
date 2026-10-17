# -*- coding: utf-8 -*-
"""Categorías nuevas dentro de NACIONALES (pedido del editor, 17/10/2026, PDF «Prompt integral», etapa 4):
deportes, espectáculos, cine y series, e IA aplicada a comercios y emprendedores.

Con las fuentes que el sistema YA usa: los feeds RSS de sección de Infobae (robots.txt los permite;
sondeados el 17/10, ver data/registro_fuentes.json). Nada pago ni de otra fuente sin probar.
Las EFEMÉRIDES no van acá: las cubre todos los días el Archivo Literario (archivo/, 13:30,
«Un día como hoy» en Chivilcoy, verificadas contra el sitio del Archivo), que es mejor fuente para
un diario local que las efemérides generales.

Cómo entran, sin sumar carga (el PDF pide que lo nuevo REEMPLACE parte de lo repetitivo):
- Comparten el cupo de nacionales (3 por pasada, 12 por día). Como mucho NAC_VARIEDAD_POR_PASADA (1)
  pieza de estas categorías por pasada, y cada categoría tiene su tope por día (CUPO_DIA, variable
  NAC_CUPO_<CATEGORIA>). Se rota: va la categoría que hace más que no sale.
- Salen como cualquier nacional: Short, nota en la web (Deportes va a su sección; las demás a
  Nacionales hasta que existan sus secciones, variables WIX_CAT_<CATEGORIA>), Facebook si está entre
  las más virales y, por la nota de la web, X. NO van al carrusel «Noticias nacionales de hoy».

Filtros sin IA, por categoría; las reglas editoriales de cada una (resultado final o en juego, muerte
confirmada, plataforma y fecha del estreno, qué tarea resuelve la IA…) van en el guion (GUIAS).
"""
import os
import re

from nacionales import filtro as F
from nacionales.infobae import ruta

# Cuánto atrás se mira en cada categoría: deportes y espectáculos son del día; los estrenos se anuncian
# con días de anticipación (el feed de «Qué puedo ver» cubre más de un mes) y una herramienta de IA no
# vence en horas.
HORAS_VENTANA = {"deportes": 24, "espectaculos": 24, "cine_series": 72, "tecnologia_ia": 48}

ARGENTINA = F.rx(["argentina", "argentino", "argentinos", "argentinas", "seleccion", "scaloni", "messi",
                  "afa", "liga profesional", "copa argentina", "torneo clausura", "torneo apertura",
                  "boca", "river", "racing", "independiente", "san lorenzo", "estudiantes", "gimnasia",
                  "velez", "huracan", "lanus", "banfield", "talleres", "belgrano", "rosario central",
                  "newells", "colon", "union", "argentinos juniors", "platense", "tigre", "defensa y justicia",
                  "libertadores", "sudamericana", "colapinto", "pumas", "leonas", "los pumas", "las leonas"])
EN_VIVO = F.rx(["en vivo", "minuto a minuto", "en directo", "live", "como ver", "a que hora juega",
                "donde ver", "formaciones", "apuestas", "pronostico"])
TELESHOW_FUERA = F.rx(["horoscopo", "fotos:", "la foto de", "el look", "outfit", "sugestiva", "picante",
                       "chicana", "indirecta", "palito", "letal", "filoso", "filosa"])
CINE_SERIES = F.rx(["estreno", "estrena", "estrenos", "netflix", "disney", "max", "prime video", "hbo",
                    "paramount", "apple tv", "star+", "cines", "cine", "pelicula", "peliculas", "serie",
                    "series", "temporada", "documental", "taquilla", "oscar"])
VIDEOJUEGOS = F.rx(["videojuego", "videojuegos", "gamer", "playstation", "xbox", "nintendo", "steam"])
IA = F.rx(["inteligencia artificial", "ia", "chatgpt", "gemini", "copilot", "claude", "openai", "chatbot",
           "chatbots", "agente de ia", "agentes de ia", "ia generativa"])
# El uso PRÁCTICO para un comercio, un emprendedor o una oficina (no «las empresas» en general: así
# entraban OpenAI y una billetera cripto, o un informe sobre América Latina).
NEGOCIO = F.rx(["pymes", "pyme", "comercios", "comerciante", "comerciantes", "emprendedor",
                "emprendedores", "emprendimiento", "emprendimientos", "pequenas empresas", "pequena empresa",
                "ventas", "vender", "clientes", "atencion al cliente", "whatsapp", "excel", "planillas",
                "hojas de calculo", "correos", "productividad", "facturacion", "tienda online", "e-commerce",
                "comercio electronico", "marketing", "automatizar", "automatizacion", "tareas", "oficina",
                "como usar", "paso a paso", "trucos", "shopify", "mercado libre", "vendedores", "tiendas"])

CATEGORIAS = {
    "deportes": {"nombre": "Deportes", "feeds": ("deportes",), "rutas": ("/deportes/",), "cupo": 2,
                 "web": "094f631e-1b56-485f-8777-6e167802455e"},          # sección Deportes (existe)
    "espectaculos": {"nombre": "Espectáculos", "feeds": ("teleshow",), "rutas": ("/teleshow/",), "cupo": 2,
                     "web": ""},
    "cine_series": {"nombre": "Cine y series", "feeds": ("que-puedo-ver",),
                    "rutas": ("/que-puedo-ver/", "/malditos-nerds/"), "cupo": 1, "web": ""},
    "tecnologia_ia": {"nombre": "Tecnología", "feeds": ("tecno",), "rutas": ("/tecno/",), "cupo": 1, "web": ""},
}
FEEDS = tuple(f for c in CATEGORIAS.values() for f in c["feeds"])
NACIONALES_ID = "b646fede-00cb-4f10-aca5-56fdda96094a"


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.environ.get(nombre) or defecto))
    except ValueError:
        return defecto


def cupo_dia(cat: str) -> int:
    return _entero(f"NAC_CUPO_{cat.upper()}", CATEGORIAS[cat]["cupo"])


def por_pasada() -> int:
    return _entero("NAC_VARIEDAD_POR_PASADA", 1)


def seccion_web(cat: str) -> str:
    """La categoría de Wix: la propia si existe (o la cargada en WIX_CAT_<CATEGORIA>); si no, Nacionales."""
    return (os.environ.get(f"WIX_CAT_{cat.upper()}") or "").strip() or CATEGORIAS[cat]["web"] or NACIONALES_ID


def de_que_categoria(n: dict) -> str:
    p = ruta(n.get("url"))
    for cat, c in CATEGORIAS.items():
        if p.startswith(c["rutas"]):
            return cat
    return ""


def puntuar(n: dict, ahora: float) -> tuple:
    """(puntos, motivo) de una nota de las categorías nuevas. 0 = no va."""
    cat = de_que_categoria(n)
    if ahora - (n.get("fecha") or 0) > HORAS_VENTANA.get(cat, 24) * 3600:
        return 0, "vieja"
    titulo, cabeza = F.norm(n.get("titulo")), F.norm(f"{n.get('titulo')} . {n.get('resumen')}")
    if not cat:
        return 0, "otra sección"
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
    if cat == "tecnologia_ia":
        if not IA.search(cabeza):
            return 0, "tecnología sin IA"
        # En el TÍTULO: en el resumen aparecía «el regulador de comercio» o «gratis» de otra cosa.
        if not NEGOCIO.search(titulo):
            return 0, "IA sin aplicación para comercios, empresas o el trabajo"
        return 40, "IA aplicada"
    return 0, ""


def candidatas(notas: list, ahora: float) -> dict:
    """{categoría: [candidatas, de mejor a peor]}: una por tema, con la cobertura de Infobae sumada."""
    recientes = []
    for n in notas:
        p, motivo = puntuar(n, ahora)
        if p > 0:
            recientes.append(dict(n, puntos_base=p, nivel=de_que_categoria(n), motivos=[motivo]))
    salida = {cat: [] for cat in CATEGORIAS}
    for grupo in F.agrupar(recientes):
        mejor = max(grupo, key=lambda x: (x["puntos_base"], x.get("fecha") or 0))
        cobertura = len(grupo)
        puntos = mejor["puntos_base"] + F.BONO_COBERTURA * min(cobertura - 1, F.TOPE_COBERTURA)
        salida[mejor["nivel"]].append(dict(mejor, categoria=mejor["nivel"], puntos=puntos, cobertura=cobertura,
                                           tema=sorted(F.palabras_tema(mejor)),
                                           otras=[x["titulo"] for x in grupo if x is not mejor][:4]))
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


# Lo que la IA tiene que respetar en cada categoría (se suma al prompt de nacionales).
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
    "tecnologia_ia": """
CATEGORÍA TECNOLOGÍA / IA PARA COMERCIOS Y EMPRENDEDORES (esta nota): la sección es «Tecnología».
- Contá qué TAREA resuelve (atender clientes, vender, ordenar planillas, contestar correos…), para
  quién sirve, qué hace falta para usarla, qué LÍMITES tiene y si se sabe disponibilidad o precio.
- Lo que dice una empresa sobre su producto va ATRIBUIDO («según la empresa»): nunca como un hecho
  comprobado. NUNCA digas que lo probamos ni prometas ganancias o ahorros.
- Si es solo un anuncio de producto sin uso práctico para un comercio o un emprendedor, APTA false.""",
}
