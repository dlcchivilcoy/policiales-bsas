# -*- coding: utf-8 -*-
"""Las fuentes de agro. Cada una es un dict: si una cambia o se cae, se apaga sola esa.

Campos:
  nombre   cómo se la nombra en el informe (nunca en lo que se publica)
  base     el sitio (para robots.txt)
  rss      uno o más feeds; se prefiere SIEMPRE el RSS a leer el HTML (pedido del documento)
  tipo     «medio» (otro diario: su foto NO se usa), «oficial» (INTA, Secretaría, BCR: su foto y sus
           datos sí) o «prensa» (gacetillas de empresas para difusión: su foto sí)
  activa   False la deja afuera sin borrarla

Relevado el 13/10/2026 (los cuatro con RSS y robots.txt que permite leerlos):
  TodoAgro         /feed/ · ~1 nota por día, 10 en el feed
  Infocampo        /feed/ · ~16 en el feed, varias por día
  Agrositio        sin /feed/: tiene RSS por sección (rss.php?area=…), 25 por feed
  Bichos de Campo  /feed/ · 10 en el feed, varias por día

Oficiales, sumadas el 13/10/2026 (su foto y sus datos SÍ se usan; un dato sensible de una fuente
oficial no pide revisión):
  INTA             INTA Informa (intainforma.inta.gob.ar/feed/), el portal de noticias del INTA:
                   1-2 por día, con foto. Es más completo y más rápido que el RSS de
                   argentina.gob.ar/inta/noticias (las mismas notas, sin foto y medio día después).
  Bolsa de Comercio de Rosario
                   SIN RSS: se leen sus páginas del Informativo Semanal (análisis de granos,
                   hacienda, economía; sale los viernes) y de GEA (el informe semanal de cultivos de la
                   zona núcleo, los jueves). El «comentario diario del mercado» NO entra: cada día el
                   mismo título, es más planilla que noticia.
  Secretaría de Agricultura
                   argentina.gob.ar/economia/agricultura/noticias/rss: 1-2 por semana (exportaciones,
                   aperturas de mercados, estadísticas), con foto. Ventana de 4 días (publica poco).

Sumada el 13/10/2026 (medio):
  LA NACION Campo  RSS de la sección (arc/outboundfeeds): ~10 por día, con foto (no se usa: es otro
                   medio). Su «Tecnología para el campo» no tiene feed propio y entra por acá.

Internacionales, sumadas el 13/10/2026 (medios en INGLÉS: la pieza sale en castellano y conectada con
el productor argentino; su foto no se usa):
  AgFunderNews     /feed · inversión y startups AgTech, ~2 por día
  Future Farming   /rss/ · maquinaria, robótica y agricultura de precisión, ~1 por día
  CropLife         /feed/ · «Smart Tech»: protección de cultivos, nutrición, precisión, ~1-2 por día
  `idioma` / `pais`: «en» / «INT» para estas (el resto, «es» / «AR»).

Sumada el 13/10/2026 (medio): Agroclave ahora publica DENTRO de La Capital de Rosario (su portada
  linkea a lacapital.com.ar/agro/…). El RSS de esa sección (rss/agro.xml) existe pero viene VACÍO:
  se lee el sitemap de noticias de La Capital (sitemap-news.xml, el de Google News: título y fecha
  exactos) filtrado a /agro/. ~2-3 notas por día.
  `sitemaps` + `patron`: para un sitio con sitemap de noticias y sin RSS que sirva.

  `foto`: False = su imagen no se usa aunque sea oficial (la Bolsa: placas de 500 px con texto).
  `horas`: ventana propia de una fuente semanal (la Bolsa: 7 días, hasta el número siguiente; el resto, la de la pasada).
  Campos para un sitio sin RSS: `portadas` (páginas a leer) + `patron` (qué links son notas).
  `solo_campo` + `localidad`: un diario local que publica de todo; solo entra lo que habla del campo.
"""
import os
import re
import unicodedata

FUENTES = [
    {"nombre": "TodoAgro", "base": "https://www.todoagro.com.ar",
     "rss": ["https://www.todoagro.com.ar/feed/"], "tipo": "medio", "activa": True},
    {"nombre": "Infocampo", "base": "https://www.infocampo.com.ar",
     "rss": ["https://www.infocampo.com.ar/feed/"], "tipo": "medio", "activa": True},
    {"nombre": "Agrositio", "base": "https://www.agrositio.com.ar",
     "rss": [f"https://www.agrositio.com.ar/rss/rss.php?area={a}"
             for a in ("destacadas", "granos", "hacienda", "economia")],
     "tipo": "medio", "activa": True},
    {"nombre": "Bichos de Campo", "base": "https://bichosdecampo.com",
     "rss": ["https://bichosdecampo.com/feed/"], "tipo": "medio", "activa": True},
    {"nombre": "LA NACION Campo", "base": "https://www.lanacion.com.ar",
     "rss": ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/campo/?outputType=xml"],
     "tipo": "medio", "activa": True},
    {"nombre": "Secretaría de Agricultura", "base": "https://www.argentina.gob.ar",
     "rss": ["https://www.argentina.gob.ar/economia/agricultura/noticias/rss"], "horas": 96,
     "tipo": "oficial", "activa": True},
    {"nombre": "Agroclave (La Capital)", "base": "https://www.lacapital.com.ar", "rss": [],
     "sitemaps": ["https://www.lacapital.com.ar/sitemap-news.xml"],
     "patron": r"lacapital\.com\.ar/agro/[\w-]+-n\d+\.html$", "tipo": "medio", "activa": True},
    {"nombre": "AgFunderNews", "base": "https://agfundernews.com", "rss": ["https://agfundernews.com/feed"],
     "tipo": "medio", "idioma": "en", "pais": "INT", "activa": True},
    {"nombre": "Future Farming", "base": "https://www.futurefarming.com", "rss": ["https://www.futurefarming.com/rss/"],
     "tipo": "medio", "idioma": "en", "pais": "INT", "activa": True},
    {"nombre": "CropLife", "base": "https://www.croplife.com", "rss": ["https://www.croplife.com/feed/"],
     "tipo": "medio", "idioma": "en", "pais": "INT", "activa": True},
    {"nombre": "INTA", "base": "https://intainforma.inta.gob.ar",
     "rss": ["https://intainforma.inta.gob.ar/feed/"], "tipo": "oficial", "activa": True},
    {"nombre": "Bolsa de Comercio de Rosario", "base": "https://www.bcr.com.ar", "rss": [],
     "portadas": ["https://www.bcr.com.ar/es/mercados/investigacion-y-desarrollo/informativo-semanal",
                  "https://www.bcr.com.ar/es/mercados/gea"],
     "patron": r"bcr\.com\.ar/es/mercados/(investigacion-y-desarrollo/informativo-semanal/"
               r"noticias-informativo-semanal|gea/seguimiento-de-cultivos/informe-semanal-zona-nucleo)/[\w-]+$",
     "horas": 168, "foto": False, "tipo": "oficial", "activa": True},
]


# MEDIOS DE LA ZONA (06/11/2026, pedido del editor: que sea la cuenta del campo de Chivilcoy y la zona; el 63 % de
# los seguidores es de Chivilcoy). Los diarios locales del padrón de policiales con RSS que funciona, SOLO lo que
# habla del campo (publican de todo). Traen poco pero es lo que ningún medio nacional cuenta: el pedido de
# emergencia agropecuaria de Lincoln, la Sociedad Rural de Roque Pérez. AGRO_MEDIOS_ZONA=0 los apaga.
ZONA = ("25 de Mayo", "9 de Julio", "Alberti", "Bolivar", "Bragado", "Carlos Casares", "Carmen de Areco", "Chacabuco",
        "General Arenales", "General Viamonte", "Junin", "Las Flores", "Lincoln", "Lobos", "Mercedes", "Navarro",
        "Pehuajo", "Rojas", "Roque Perez", "Saladillo", "Salto", "San Andres de Giles", "Suipacha")
# Además de las palabras firmes del campo de reels/colab_agro.py. «hacienda» no: también es la Secretaría de Hacienda.
MAS_CAMPO = ("granizo", "ganado", "novillo-", "ternero-", "productores rurales", "productor rural", "cuatrerismo")


def medios_zona_activos() -> bool:
    return (os.environ.get("AGRO_MEDIOS_ZONA") or "1").strip() != "0"


def de_la_zona() -> list:
    from scraper.medios import MEDIOS
    salida, vistos = [], set()
    for m in MEDIOS:
        if m["localidad"] not in ZONA or m.get("navegador") or not m.get("rss") or m["dominio"] in vistos:
            continue
        vistos.add(m["dominio"])
        salida.append({"nombre": m["nombre"], "base": m["base"], "rss": [m["rss"]], "tipo": "medio",
                       "localidad": m["localidad"], "solo_campo": True, "activa": True})
    return salida


def es_del_campo(texto: str) -> bool:
    from reels import colab_agro as CO
    t = CO._norm(texto)
    return bool(CO._hay(t, CO.FIRMES) or CO._hay(t, MAS_CAMPO))


PUEBLOS_ZONA = ("Chivilcoy", "Moquehuá", "Gobernador Ugarte", "Mechita", "Gorostiaga", "Ramón Biaus", "Emilio Ayarza",
                "Palemón Huergo", "Indacochea", "Benítez", "San Sebastián", "25 de Mayo", "9 de Julio", "Alberti", "Bragado",
                "Carlos Casares", "Carmen de Areco", "Chacabuco", "Junín", "Lobos", "Mercedes", "Navarro", "Rojas",
                "Roque Pérez", "Saladillo", "Salto", "San Andrés de Giles", "Suipacha")


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")


def nombra_la_zona(texto: str) -> bool:
    """¿La nota nombra un pueblo de la zona? No alcanza con que la publique un diario de acá: los diarios locales
    también levantan noticias nacionales. Distingue mayúsculas: «salto» o «lobos» en minúscula no son el pueblo."""
    t = _sin_tildes(texto)
    return any(re.search(rf"(?<!\w){re.escape(_sin_tildes(p))}(?!\w)", t) for p in PUEBLOS_ZONA)


def activas() -> list:
    return [f for f in FUENTES if f.get("activa", True)] + (de_la_zona() if medios_zona_activos() else [])


def por_nombre(nombre: str) -> dict:
    return next((f for f in FUENTES + de_la_zona() if f["nombre"] == nombre), {})
