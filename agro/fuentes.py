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
    # 16/11/2026 (pedido del editor: «priorizá encontrar noticias con videos para armar reels; buscá también
    # tecnología aplicada al agro, maquinarias u otro rubro ligado al campo»). Sondeo de ese día: casi todos los
    # medios de campo suben sus videos a YouTube (Clarín Rural, Agrofy, EFE Agro, Maquinac, Agriland), que desde la
    # nube no se baja; TN aloja los suyos (se leen con nacionales/portales, como en nacionales). Se suman igual: más
    # noticias de campo, maquinaria y tecnología para los reels (con el video de la nota o con uno ilustrativo,
    # agro/banco_video.py). Descartados: Canal Rural (no contesta), Successful Farming, AgWeb, Farmers Weekly y
    # Agromaquinaria (403), La Voz Agro (403), EFE Agro (casi todo de España).
    {"nombre": "Clarín Rural", "base": "https://www.clarin.com", "rss": ["https://www.clarin.com/rss/rural/"],
     "tipo": "medio", "activa": True},
    {"nombre": "TN Campo", "base": "https://tn.com.ar",
     "rss": ["https://tn.com.ar/arc/outboundfeeds/rss/category/campo/?outputType=xml"], "tipo": "medio", "activa": True},
    {"nombre": "Agrofy News", "base": "https://news.agrofy.com.ar", "rss": ["https://news.agrofy.com.ar/rss.xml"],
     "tipo": "medio", "activa": True},
    {"nombre": "Maquinac", "base": "https://www.maquinac.com", "rss": ["https://www.maquinac.com/feed/"],
     "tipo": "medio", "activa": True},
    # 20/11/2026 (el editor: «y este https://agroempresario.com/»): sin RSS, con sitemap de noticias (robots.txt deja
    # todo). Publica también economía general y política provincial: solo entra lo que es del campo.
    {"nombre": "Agroempresario", "base": "https://agroempresario.com", "rss": [],
     "sitemaps": ["https://agroempresario.com/news-sitemap.xml/"], "patron": r"agroempresario\.com/publicacion/\d+/",
     "limite": 80, "tipo": "medio", "solo_campo": True, "activa": True},
    # 24/11/2026 (el editor: «este https://www.noticiasagropecuarias.com/»): WordPress con RSS al día (~10 notas por
    # día; robots.txt solo cierra /wp-admin/). Del campo casi todo (lácteos, carne, empresas del agro, cultivos); lo de
    # economía general lo baja el puntaje.
    {"nombre": "Noticias AgroPecuarias", "base": "https://www.noticiasagropecuarias.com",
     "rss": ["https://www.noticiasagropecuarias.com/feed/"], "tipo": "medio", "min_ancho": 480, "activa": True},
    # 24/11/2026 (el editor: «sumá las 5» que faltaban para el campo de Chivilcoy y su zona). Las oficiales e
    # institucionales que nombran partidos de la zona:
    #  - Ministerio de Desarrollo Agrario bonaerense: sin RSS ni og:*; se lee su página de noticias (`portadas`) y de
    #    cada nota el <title>, la description y la fecha del cuerpo (captura._metadatos). Emergencias, caminos rurales.
    #  - INTA Centro Regional Buenos Aires Norte (las agencias de la zona, Chivilcoy incluida): RSS propio.
    #  - Senasa: RSS; mucho es de otras provincias y lo baja el puntaje.
    #  - Municipalidad de Chivilcoy: RSS de WordPress; publica de todo → solo lo del campo o de una empresa del agro.
    # Afuera: el Informe Semanal de Estimaciones (MAGyP) es un PDF de datos, no noticias; y la Asociación Rural de
    # Chivilcoy publica solo en redes sociales (no se leen de forma automática).
    {"nombre": "Ministerio de Desarrollo Agrario PBA", "base": "https://www.gba.gob.ar", "rss": [],
     "portadas": ["https://www.gba.gob.ar/desarrollo_agrario/Noticias"],
     "patron": r"gba\.gob\.ar/desarrollo_agrario/Noticias/[^/?#]+$", "limite": 12, "horas": 168,
     "tipo": "oficial", "activa": True},
    {"nombre": "INTA Buenos Aires Norte", "base": "https://www.argentina.gob.ar",
     "rss": ["https://www.argentina.gob.ar/inta/cr-buenosaires-norte/noticias/rss"], "horas": 168,
     "tipo": "oficial", "activa": True},
    {"nombre": "Senasa", "base": "https://www.argentina.gob.ar",
     "rss": ["https://www.argentina.gob.ar/senasa/noticias/rss"], "horas": 96, "tipo": "oficial", "activa": True},
    {"nombre": "Municipalidad de Chivilcoy", "base": "https://www.chivilcoy.gov.ar",
     "rss": ["https://www.chivilcoy.gov.ar/feed/"], "tipo": "oficial", "solo_campo": True, "activa": True},
    # 24/11/2026 (el editor: «esta también https://agrobonaerense.com.ar/»): el campo de la provincia de Buenos Aires
    # (Chacabuco, la Rural, UATRE, seguro de desempleo rural). RSS en /rss (unas 3 notas por día), robots.txt solo
    # cierra /beta/, /banner y /resultados/. Fotos de 780 px: pasan el mínimo.
    {"nombre": "Agro Bonaerense", "base": "https://agrobonaerense.com.ar",
     "rss": ["https://agrobonaerense.com.ar/rss"], "tipo": "medio", "activa": True},
    # 16/11/2026 (pedido del editor: «priorizá videos que tengan que ver con policiales en el campo»): las secciones
    # de policiales de los portales que más seguido alojan su propio video (las mismas de nacionales/prueba.py), solo
    # lo que es del campo (abigeato, robos en campos, silobolsas, incendios rurales, accidentes con maquinaria).
    {"nombre": "TN Policiales", "base": "https://tn.com.ar",
     "rss": ["https://tn.com.ar/arc/outboundfeeds/rss/category/policiales/?outputType=xml"], "tipo": "medio",
     "solo_campo": True, "policial": True, "activa": True},
    {"nombre": "Infobae Policiales", "base": "https://www.infobae.com",
     "rss": ["https://www.infobae.com/arc/outboundfeeds/rss/category/sociedad/policiales/?outputType=xml"],
     "tipo": "medio", "solo_campo": True, "policial": True, "activa": True},
    {"nombre": "Clarín Policiales", "base": "https://www.clarin.com", "rss": ["https://www.clarin.com/rss/policiales/"],
     "tipo": "medio", "solo_campo": True, "policial": True, "activa": True},
    # 24/11/2026 (pedido del editor: empresas, fábricas y pymes del agro con conflictos, cierres o premios): secciones de
    # economía y un portal gremial. Publican de todo: SOLO entra lo que es de una empresa del agro con un hecho
    # (`solo_empresa`, es_empresa_agro). Verificadas el 24/11: Infobae 24 notas, elDiarioAR 20, LN 4, InfoGremiales 10.
    {"nombre": "Infobae Economía", "base": "https://www.infobae.com",
     "rss": ["https://www.infobae.com/arc/outboundfeeds/rss/category/economia/?outputType=xml"], "tipo": "medio",
     "solo_empresa": True, "activa": True},
    {"nombre": "LA NACION Economía", "base": "https://www.lanacion.com.ar",
     "rss": ["https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml"], "tipo": "medio",
     "solo_empresa": True, "activa": True},
    {"nombre": "elDiarioAR Economía", "base": "https://www.eldiarioar.com", "rss": ["https://www.eldiarioar.com/rss/economia"],
     "tipo": "medio", "solo_empresa": True, "activa": True},
    {"nombre": "InfoGremiales", "base": "https://www.infogremiales.com.ar", "rss": ["https://www.infogremiales.com.ar/feed/"],
     "tipo": "medio", "solo_empresa": True, "activa": True},
]


# MEDIOS DE LA ZONA (06/11/2026, pedido del editor: que sea la cuenta del campo de Chivilcoy y la zona; el 63 % de
# los seguidores es de Chivilcoy). Los diarios locales del padrón de policiales con RSS que funciona, SOLO lo que
# habla del campo (publican de todo). Traen poco pero es lo que ningún medio nacional cuenta: el pedido de
# emergencia agropecuaria de Lincoln, la Sociedad Rural de Roque Pérez. AGRO_MEDIOS_ZONA=0 los apaga.
ZONA = ("25 de Mayo", "9 de Julio", "Alberti", "Bolivar", "Bragado", "Carlos Casares", "Carmen de Areco", "Chacabuco",
        "General Arenales", "General Viamonte", "Junin", "Las Flores", "Lincoln", "Lobos", "Mercedes", "Navarro",
        "Pehuajo", "Rojas", "Roque Perez", "Saladillo", "Salto", "San Andres de Giles", "Suipacha")
# Además de las palabras firmes del campo de reels/colab_agro.py. «hacienda» no: también es la Secretaría de Hacienda.
MAS_CAMPO = ("granizo", "ganado", "novillo-", "ternero-", "productores rurales", "productor rural", "cuatrerismo",
             # 16/11/2026: los policiales del campo
             "faena clandestina", "robo de hacienda", "robo de ganado", "vacas robadas", "zona rural", "establecimiento rural",
             "campo de la zona", "maquinaria agricola", "tractor-", "quema de pastizales", "incendio rural", "cuatrero-")

# Lo policial (delito, incendio, accidente) — con una palabra del campo, la nota es un POLICIAL DEL CAMPO.
POLICIAL = re.compile(r"\b(rob[oóa]\w*|hurt\w*|delincuent\w*|ladr[oó]n\w*|detenid\w*|deten[ce]\w*|allanamient\w*|"
                      r"abigeato|cuatrer\w*|faena clandestina|estaf\w*|incendi\w*|fuego|choque|choc[oó]|vuelc\w*|volc[oó]|"
                      r"accident\w*|muri[oó]|muert[eo]\w*|homicid\w*|asesin\w*|secuestr\w*|baleado|disparo\w*|"
                      r"usurpaci[oó]n|intrus\w*|polic[ií]a\w*)\b", re.I)


def es_policial_rural(texto: str) -> bool:
    """¿Es un policial del campo? Un delito, un incendio o un accidente, en una nota del campo."""
    return bool(POLICIAL.search(texto or "")) and es_del_campo(texto) and not policial_fuera_del_campo(texto)


# 24/11/2026 (el editor: «sacá los reels de prueba o carruseles o reels que sean policiales nada que ver con el agro,
# por ejemplo robo de motos, excepto que haya ocurrido en un campo»): un DELITO o un SINIESTRO solo entra a agro si
# el hecho pasó en el campo (un campo, una chacra, un tambo, un camino rural) o fue contra lo del campo (hacienda,
# maquinaria agrícola, silobolsas). Un caballo robado en un barrio, una moto robada o un choque en la ciudad: afuera.
# Lo que no es policial (una muerte por enfermedad, un incendio de pastizales sin delito) no se mira acá.
DELITO_O_SINIESTRO = re.compile(
    r"\b(rob[oóa]\w*|robad\w*|hurt\w*|delincuent\w*|ladr[oó]n\w*|motochorr\w*|asalt\w*|detenid\w*|aprehendid\w*|"
    r"allanamient\w*|estaf\w*|homicid\w*|asesin\w*|femicid\w*|secuestr\w*|baleado|balead\w*|disparo\w*|apu[nñ]al\w*|"
    r"choque|choc[oó]|chocaron|vuelc\w*|volc[oó]|accidente\w*|siniestro\w*|atropell\w*|motociclista\w*|"
    r"usurpaci[oó]n|intrus\w*|abigeato|cuatrer\w*|faena clandestina)\b", re.I)
HECHO_RURAL = re.compile(
    r"\b(campos?(?! de (?:deportes?|juegos?|f[uú]tbol|golf))|zona rural|[aá]mbito rural|rural(?:es)?|chacras?|"
    r"estancias?|establecimientos? (?:rural|rurales|agropecuari\w*|ganader\w*|agr[ií]col\w*)|tambos?|"
    r"camino(?:s)? (?:rural|rurales|vecinal|vecinales|de tierra)|paraje|abigeato|cuatrer\w*|faena clandestina|"
    r"hacienda|ganado|vacun\w*|vacas?|novill\w*|ternero\w*|toros?|ovejas?|ovin\w*|porcin\w*|cerdos?|"
    r"cosechadora\w*|sembradora\w*|pulverizadora\w*|tractor\w*|maquinaria agr[ií]cola|silo ?bolsas?|silos?|"
    r"agroqu[ií]mic\w*|fertilizante\w*|granos?|cereal\w*|productor(?:es)? (?:rural|rurales|agropecuari\w*)|"
    r"pe[oó]n|peones|trabajador(?:es)? rural(?:es)?|quinta\w*|lotes? (?:de|con) (?:soja|ma[ií]z|trigo|girasol))\b",
    re.I)


# 24/11/2026 (el editor: «considerá scrappear y armar reels/carruseles sobre fábricas, empresas, pymes ligadas al agro,
# ya sea porque hay conflictos laborales, cierres, o porque ganaron algún premio, o algo destacado»). Una nota es de
# una EMPRESA DEL AGRO con algo que contar si nombra una empresa del rubro (frigorífico, molino, aceitera, acopio,
# cooperativa, fábrica de maquinaria agrícola, semillera, usina láctea, feedlot, agroindustria…) Y un hecho: conflicto
# laboral, despidos, suspensiones, cierre, quiebra, reapertura, una planta nueva o un premio. AGRO_EMPRESAS=0 apaga.
EMPRESA_AGRO = re.compile(
    r"\b(frigor[ií]fic\w*|matadero\w*|molino\w*|molinera\w*|harinera\w*|fideer\w*|aceitera\w*|aceiteros?|"
    r"acopio\w*|acopiador\w*|cerealera\w*|cooperativa\w* (?:agr[ií]col\w*|agropecuari\w*|tambera\w*|rural\w*)|"
    r"semillera\w*|usina\w* l[aá]cte\w*|l[aá]cte[oa]s?|lechera\w*|tambo\w*|feedlot\w*|"
    r"agroindustri\w*|agroexportador\w*|agropecuaria [A-ZÁÉÍÓÚ]\w*|f[aá]brica\w* de (?:maquinaria|implementos|"
    r"sembradoras|cosechadoras|silos|alimento\w*|balanceado\w*)|fabricante\w* de (?:maquinaria|implementos)|"
    r"metal[uú]rgica\w* (?:agr[ií]cola\w*|rural\w*)|maquinaria agr[ií]cola|concesionari\w* (?:agr[ií]col\w*|de maquinaria)|"
    r"av[ií]cola\w*|granja\w* (?:av[ií]cola|porcina)|criadero\w*|planta de (?:silos|acopio|biodi[eé]sel|etanol|"
    r"bioetanol|alimento\w*|faena)|biodi[eé]sel|bioetanol|curtiembre\w*|yerbater\w*|algodoner\w*|ingenio\w* azucarer\w*|"
    r"empacador\w*|uatre|renatre|pyme\w* (?:agr\w*|rural\w*|del campo))\b", re.I)
EVENTO_EMPRESA = re.compile(
    r"\b(despid\w*|despidos|suspensi[oó]n\w*|suspend\w*|cesant\w*|retiro\w* voluntario\w*|cierr[ea]\w*|cerr[oó]|"
    r"cerraron|cierre\w*|quiebra\w*|concurso preventivo|vaciamiento|conflicto\w*|paro\w*|huelga\w*|"
    r"medidas? de fuerza|toma de (?:la )?planta|salarios? adeudad\w*|deuda\w* salarial\w*|crisis|reabri\w*|"
    r"reapertura|inaugur\w*|nueva planta|ampl[ií]a\w*|ampliaci[oó]n|premi[oa]\w*|galard[oó]n\w*|distinci[oó]n\w*|"
    r"distinguid\w*|reconocimiento\w*|ganador\w*|gan[oó]|r[eé]cord|certificaci[oó]n\w*|primera vez|"
    r"exporta por primera|aniversario|cumple \d+ a[nñ]os|\d+ a[nñ]os de historia)\b", re.I)


def empresas_activas() -> bool:
    return (os.environ.get("AGRO_EMPRESAS") or "1").strip() != "0"


def es_empresa_agro(texto: str) -> bool:
    """¿Es una noticia de una empresa, fábrica o pyme del agro con un hecho (conflicto, cierre, premio, planta)?"""
    if not empresas_activas():
        return False
    t = texto or ""
    return bool(EMPRESA_AGRO.search(t)) and bool(EVENTO_EMPRESA.search(t))


def policial_fuera_del_campo(texto: str) -> bool:
    """¿Es un delito o un siniestro que NO pasó en el campo? (24/11/2026) AGRO_POLICIAL_SOLO_CAMPO=0 lo apaga."""
    if (os.environ.get("AGRO_POLICIAL_SOLO_CAMPO") or "1").strip() == "0":
        return False
    t = texto or ""
    return bool(DELITO_O_SINIESTRO.search(t)) and not HECHO_RURAL.search(t)


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
