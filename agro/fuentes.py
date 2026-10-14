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
"""

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


def activas() -> list:
    return [f for f in FUENTES if f.get("activa", True)]


def por_nombre(nombre: str) -> dict:
    return next((f for f in FUENTES if f["nombre"] == nombre), {})
