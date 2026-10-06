# -*- coding: utf-8 -*-
"""Qué notas de Infobae van, y en qué orden. Sin IA: reglas y la cobertura del propio Infobae.

Criterio del editor (06/10/2026): «noticias nacionales/provinciales/regionales que tengan que
ver con Chivilcoy por afectación directa o indirecta» (Ruta 5, Zona Fría, servicios, ANSES,
PAMI, IOMA, paros, aumentos, salud, dólar, medidas de gobierno…) y, después de ver la lista
de prueba, también «internas políticas, juicios, y cuestiones de relevancia como la
peregrinación a Luján, noticias que sean populares o que generen viralización».

Cómo se decide:
1. Lo que NO va nunca: otras secciones (deportes, espectáculos, el exterior), la Ciudad de
   Buenos Aires sola (subte, colectivos porteños), lo local de otras provincias, la salud
   «de revista» (estudios y dietas de afuera), y la calle Chivilcoy de Floresta.
2. Un puntaje por lo que le toca al vecino de Chivilcoy: nombrar a Chivilcoy o a la Ruta 5
   pesa más que una medida provincial, y eso más que la política en general.
3. POPULARIDAD sin IA: cuántas notas le dedica Infobae al mismo tema. Un tema con cinco notas
   en un día (la peregrinación a Luján, el DNU 70, el paro de la CGT) es lo que todo el mundo
   está leyendo. Cada nota de más del mismo tema suma.
Después, la IA del guion pone su «potencial viral» y con eso se eligen los posteos de
Facebook (nacionales/pasada.py).
"""
import math
import re
import unicodedata

from nacionales.infobae import ruta


def norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


def rx(terminos) -> re.Pattern:
    alt = "|".join(sorted((re.escape(norm(x)) for x in terminos), key=len, reverse=True))
    return re.compile(r"\b(?:" + alt + r")\b")


# --- Lo que le pega directo a Chivilcoy -------------------------------------------------------
# Solo nombres que no son apellidos comunes: «Benítez» o «Gorostiaga» daban falsos positivos.
CHIVILCOY = rx(["chivilcoy", "chivilcoyano", "chivilcoyanos", "chivilcoyense", "moquehua",
                "ramon biaus", "emilio ayarza"])
# «Chivilcoy» también es una calle porteña: «Avenida Gaona y Chivilcoy» (Floresta) metió dos
# choques porteños en la lista de prueba.
# Ojo: «San Pedro y Chivilcoy» es una lista de municipios; «Avenida Gaona y Chivilcoy», una esquina.
CALLE = re.compile(r"\b(?:calle|avenida|av\.?|esquina)\s+chivilcoy\b"
                   r"|\bchivilcoy\s+(?:al\s+)?\d{2,5}\b"
                   r"|\b(?:calle|avenida|av\.?|esquina|cruce de|interseccion de)\s+(?:[a-z0-9.]+\s+){1,3}y\s+chivilcoy\b")
BARRIOS_PORTENOS = rx(["floresta", "villa devoto", "villa del parque", "monte castro", "velez sarsfield",
                       "villa santa rita", "agronomia", "villa mitre", "flores", "caba", "barrio porteno"])


def nombra_chivilcoy(texto: str) -> list:
    """Las oraciones que hablan de la CIUDAD de Chivilcoy (no de la calle porteña: «Gaona y
    Chivilcoy», en Floresta, metió dos choques porteños en la lista de prueba)."""
    salida = []
    for o in re.split(r"(?<=[.!?])\s+", texto or ""):
        n = norm(o)
        if CHIVILCOY.search(CALLE.sub(" ", n)) and not BARRIOS_PORTENOS.search(n):
            salida.append(o)
    return salida
RUTAS = rx(["ruta 5", "ruta nacional 5", "autovia 5", "ruta provincial 30", "ruta 30",
            "ruta provincial 51", "ruta 51", "zona fria", "tren a bragado"])
REGION = rx(["alberti", "bragado", "suipacha", "chacabuco", "25 de mayo", "navarro",
             "nueve de julio", "9 de julio", "mercedes", "junin"])
BONAERENSE = rx(["provincia de buenos aires", "bonaerense", "bonaerenses", "kicillof", "pba"])

# --- Provincia: organismos y servicios que usa el vecino ----------------------------------------
PROVINCIA = rx(["ioma", "arba", "suteba", "udocba", "cicop", "banco provincia", "cuenta dni", "vtv",
                "eden", "absa", "camuzzi", "boleto estudiantil", "impuesto inmobiliario",
                "inmobiliario rural", "docentes bonaerenses", "estatales bonaerenses",
                "hospitales bonaerenses", "policia bonaerense", "escuelas bonaerenses",
                "municipios bonaerenses", "intendentes bonaerenses", "pueblos bonaerenses",
                "productores bonaerenses", "interior bonaerense"])

# --- El bolsillo y los trámites -------------------------------------------------------------------
# FUERTES: con estar en el título alcanza.
FUERTES = rx([
    "anses", "jubilacion", "jubilaciones", "jubilados", "jubilado", "haber minimo", "aguinaldo",
    "auh", "asignacion universal", "asignaciones familiares", "suaf", "puam", "pnc",
    "pensiones no contributivas", "pami", "progresar", "monotributo", "monotributistas",
    "salario minimo", "paro general", "feriado", "feriados", "fin de semana largo",
    "vacunacion", "calendario de vacunacion", "dengue", "gripe", "influenza", "bronquiolitis",
    "sarampion", "licencia de conducir", "tarifa de luz", "tarifas de luz", "tarifa de gas",
    "tarifas de gas", "boleta de luz", "boletas de luz", "boleta de gas", "boletas de gas",
    "factura de luz", "factura de gas", "subsidios a la energia", "subsidios energeticos",
    "precio de la nafta", "aumento de la nafta", "aumentan los combustibles", "suben los combustibles",
    "garrafa", "garrafas", "canasta basica", "creditos hipotecarios", "credito hipotecario",
    "seguro de desempleo", "retenciones", "derechos de exportacion", "prepagas",
])
# DEBILES: pasan solo si el título además le habla al bolsillo (cuánto, cuándo, aumenta…).
DEBILES = rx(["dolar", "inflacion", "ipc", "precios", "tarifa", "tarifas", "nafta", "naftas",
              "combustible", "combustibles", "plazo fijo", "creditos", "credito", "prestamos",
              "alquiler", "alquileres", "salarios", "paritaria", "paritarias", "paro", "cgt",
              "huelga", "medicamentos", "vacuna", "vacunas", "hospital", "hospitales", "obra social",
              "obras sociales", "becas", "beca", "ganancias", "bienes personales", "arca", "empleo",
              "desempleo", "despidos", "colectivos", "peajes", "peaje", "soja", "trigo", "maiz",
              "cosecha", "siembra", "productores", "tamberos", "discapacidad", "empleados publicos",
              "estatales", "cursos", "oficios", "empleadores", "pymes", "comercios", "escuelas",
              "docentes", "clases", "medicos", "residentes", "salud publica"])
SERVICIO = rx(["cuanto", "cuanta", "cuantos", "cuando", "hasta cuando", "como acceder", "como inscribirse",
               "como anotarse", "como tramitar", "como cobrar", "como pedir", "como sacar", "quienes",
               "prepara un decreto", "decreto", "retiros voluntarios", "prestaciones", "gratis", "gratuito",
               "gratuitos", "gratuita", "controles gratuitos", "que cambia", "que pasa",
               "aumenta", "aumentan", "aumento", "aumentos", "sube", "suben", "suba", "baja", "bajan",
               "nuevo", "nueva", "nuevos", "nuevas", "desde hoy", "desde el lunes", "desde manana",
               "a partir", "confirmo", "confirman", "oficial", "oficializo", "anuncio", "anunciaron",
               "lanzo", "lanzaron", "cronograma", "fecha", "requisitos", "dato de", "indec", "fue de",
               "se dispara", "alerta", "advierten", "cuidado", "cortes", "corte", "medida de fuerza",
               "elimina", "eliminan", "habilita", "habilitan", "vence", "vencimiento"])
GOBIERNO_PBA = rx(["kicillof", "provincia de buenos aires", "gobierno bonaerense", "legislatura bonaerense",
                   "bonaerense", "bonaerenses"])
MEDIDA_PBA = re.compile(r"\b(anuncio|lanzo|lanzaron|oficializo|decreto|aumento|aumenta|paga|pagara|"
                        r"cobran|nuevo|nueva)\b")
ESTAFA = rx(["estafa", "estafas", "cuento del tio", "phishing", "fraude", "fraudes"])
ALERTA = rx(["cuidado", "alerta", "advierten", "como evitar", "como detectar", "modalidad", "nueva estafa"])
ALERTA_CLIMA = rx(["alerta meteorologica", "alertas meteorologicas", "alerta amarilla", "alerta naranja",
                   "alerta roja", "alerta por tormentas", "alerta por vientos", "alerta por lluvias"])

# --- Lo que no va -------------------------------------------------------------------------------
SOLO_AMBA = rx(["caba", "ciudad de buenos aires", "porteno", "portenos", "portena", "subte", "subtes",
                "jorge macri", "amba", "ciudad autonoma", "conurbano", "la matanza", "quilmes",
                "tren sarmiento", "linea sarmiento", "linea roca", "tren roca", "linea mitre",
                "linea san martin", "linea belgrano", "linea urquiza", "linea a", "linea b", "linea c",
                "linea d", "linea e", "linea h", "premetro", "monumental", "nordelta", "punta lara",
                "la plata", "palermo", "floresta", "barrio porteno", "legislatura portena"])
OTRAS = rx(["cordoba", "santa fe", "rosario", "mendoza", "tucuman", "salta", "jujuy", "chubut",
            "neuquen", "rio negro", "misiones", "corrientes", "entre rios", "chaco", "formosa",
            "santiago del estero", "catamarca", "la rioja", "san juan", "san luis", "la pampa",
            "santa cruz", "tierra del fuego", "mar del plata", "bahia blanca", "zonas calidas",
            "gobernadores del norte", "villa la angostura", "anelo"])
EXTERIOR = rx(["brasil", "chile", "uruguay", "paraguay", "bolivia", "peru", "venezuela", "estados unidos",
               "eeuu", "ee.uu", "espana", "francia", "reino unido", "israel", "gaza", "hamas", "ucrania",
               "rusia", "china", "mexico", "colombia", "vaticano", "wall street", "bolsonaro", "lula",
               "trump", "europa", "malvinas", "paris"])
# Si el título además habla de la Argentina, lo de afuera sí importa («qué impacto tendrá en
# la Argentina el resultado de Brasil», «la visita del Papa al país»).
ARGENTINA = rx(["argentina", "argentino", "argentinos", "argentinas", "pais", "milei", "caputo",
                "gobierno", "casa rosada", "ministerio de salud", "anmat", "bonaerense", "provincia"])
# El ruido de la city (riesgo país, bonos, Wall Street) no se comparte: solo si el tema es grande.
MERCADOS = rx(["riesgo pais", "bonos", "acciones", "wall street", "merval", "adr", "adrs", "bandas cambiarias",
               "base monetaria", "dividendos", "reservas del bcra", "licitacion del tesoro", "carry trade",
               "colocacion de deuda", "fmi"])
SECCIONES_OK = ("/politica/", "/economia/", "/sociedad/", "/judiciales/", "/salud/")

# --- Puntajes ------------------------------------------------------------------------------------
UMBRAL = 30                 # menos que esto no es candidata
BONO_COBERTURA = 8          # por cada nota de más que Infobae le dedica al mismo tema…
TOPE_COBERTURA = 4          # …hasta 4 (o sea, +32)
HORAS_VENTANA = 36          # lo de antes de ayer ya no es noticia del día


def puntuar(n: dict, ahora: float) -> tuple:
    """(puntos, nivel, motivos) de UNA nota, sin contar todavía la cobertura del tema."""
    if ahora - (n.get("fecha") or 0) > HORAS_VENTANA * 3600:
        return 0, "", ["vieja"]
    titulo, resumen = norm(n.get("titulo")), norm(n.get("resumen"))
    cabeza = f"{titulo} . {resumen}"
    todo = f"{cabeza} . {norm(n.get('cuerpo'))}"
    path = ruta(n.get("url"))
    policial = "/policiales/" in path

    if nombra_chivilcoy(f"{n.get('titulo')}. {n.get('resumen')} {n.get('cuerpo')}"):
        return 100, "Chivilcoy", ["nombra a Chivilcoy"]
    if not path.startswith(SECCIONES_OK):
        return 0, "", ["sección"]
    m = RUTAS.findall(cabeza)
    if m:
        return 90, "directa", [m[0]]
    m = REGION.findall(titulo)
    # La zona, si no es policial: los policiales de la zona ya entran por los medios locales.
    if m and not policial and BONAERENSE.search(todo):
        return 80, "región", [m[0]]

    afuera = EXTERIOR.search(titulo) and not ARGENTINA.search(titulo)
    if afuera:
        return 0, "", ["exterior"]
    if OTRAS.search(titulo) and not (PROVINCIA.search(titulo) or ARGENTINA.search(titulo)):
        return 0, "", ["otra provincia"]
    if SOLO_AMBA.search(titulo) and not PROVINCIA.search(titulo):
        return 0, "", ["AMBA"]
    if path.startswith("/salud/") and not ARGENTINA.search(cabeza):
        return 0, "", ["salud de afuera"]

    if ALERTA_CLIMA.search(titulo) and "buenos aires" in todo:
        return 45, "clima", ALERTA_CLIMA.findall(titulo)[:1]
    if policial:
        if ESTAFA.search(titulo) and ALERTA.search(cabeza):
            return 50, "estafas", ESTAFA.findall(titulo)[:1]
        # Un policial de otro lado entra solo si es un caso GRANDE (cobertura, más abajo).
        return 15, "policial", []

    p = sorted(set(PROVINCIA.findall(titulo)))
    f = sorted(set(FUERTES.findall(titulo)))
    d = sorted(set(DEBILES.findall(titulo)))
    s = sorted(set(SERVICIO.findall(titulo)))
    g = sorted(set(GOBIERNO_PBA.findall(titulo)))

    puntos, nivel, motivos = 0, "", []
    if p:
        puntos, nivel, motivos = 45, "provincia", p
    elif g and s and (f or d or MEDIDA_PBA.search(titulo)):
        puntos, nivel, motivos = 40, "provincia", g[:1] + s[:1]
    if f:
        puntos += 40 + 5 * min(len(f) - 1, 2)
        nivel = nivel or "bolsillo"
        motivos += f
    elif d and s:
        puntos += 30
        nivel = nivel or "bolsillo"
        motivos += d + s[:1]
    if puntos:
        return puntos + (5 if s else 0), nivel, motivos

    # Lo que no toca el bolsillo pero la gente sigue: la política (internas incluidas), los
    # juicios y los grandes temas de la sociedad. Entran con menos puntaje y los ordena la
    # cobertura: la interna del día con cinco notas pasa adelante de la que tiene una.
    if MERCADOS.search(titulo):
        return 10, "mercados", MERCADOS.findall(titulo)[:1]
    if path.startswith("/politica/"):
        return 30, "política", []
    if path.startswith("/judiciales/"):
        return 30, "justicia", []
    if path.startswith("/salud/"):
        return 25, "salud", []
    if path.startswith("/economia/"):
        return 20, "economía", []
    return 20, "sociedad", []


# =============================================================================
# Temas: varias notas sobre lo mismo
# =============================================================================

_VACIAS = set(norm(w) for w in """
a al ante bajo con contra de del desde durante e el en entre hacia hasta la las lo los mas o para
por que se sin sobre su sus tras un una unos unas y ya como cual cuales cuando donde quien quienes
este esta estos estas ese esa eso esos esas aquel otro otra otros otras muy tambien pero porque
fue son ser sera han hay tiene tienen hizo dijo afirmo aseguro sostuvo explico planteo hoy ayer
manana dia dias semana ano anos tras luego antes despues cada todo todos toda todas nuevo nueva
video vivo minuto como cuanto cuanta cuantos cuando quienes clave claves enero febrero marzo
abril mayo junio julio agosto septiembre setiembre octubre noviembre diciembre lunes martes
miercoles jueves viernes sabado domingo
""".split())


# Mayúscula pero no dicen de qué trata: están en cualquier nota de política o de la Justicia.
_GENERICOS = set(norm(w) for w in """
gobierno justicia argentina estado congreso senado diputados corte casacion presidente provincia
ciudad nacion pais camara ministerio ministro tribunal juez fiscal oficial video calendario usd
juan jose maria carlos luis jorge manuel pablo javier axel sergio mauricio patricia diego martin
alberto eduardo ricardo gustavo daniel fernando oscar hector miguel roberto ana laura sandra
""".split())


def _raiz(w: str) -> str:
    return w[:-1] if len(w) > 5 and w.endswith("s") else w     # «jubilados» y «jubilado», lo mismo


def palabras_tema(n: dict) -> set:
    """Las palabras que dicen DE QUÉ trata la nota: las del TÍTULO (el resumen diluía el
    parecido entre dos notas del mismo tema con cosas del contexto). Los NOMBRES PROPIOS
    («Salmain», «Bolsonaro», «CGT», «DNU») cuentan doble: van otra vez con «*» adelante."""
    titulo = n.get("titulo") or ""
    salida = set()
    for w in re.findall(r"[a-z0-9]+", norm(titulo)):
        if (len(w) < 4 and not w.isdigit()) or w in _VACIAS or re.fullmatch(r"(19|20)\d\d", w):
            continue
        salida.add(_raiz(w))
    for i, w in enumerate(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñü0-9]+", titulo)):
        propio = (i > 0 and w[:1].isupper()) or (len(w) >= 3 and w.isupper())
        if propio and norm(w) not in _VACIAS and norm(w) not in _GENERICOS and len(w) >= 3:
            salida.add("*" + _raiz(norm(w)))
    return salida


def _idf(conjuntos: list) -> dict:
    df = {}
    for c in conjuntos:
        for w in c:
            df[w] = df.get(w, 0) + 1
    n = max(1, len(conjuntos))
    return {w: math.log((n + 1) / (k + 0.5)) for w, k in df.items()}


def parecido(a: set, b: set, idf: dict) -> float:
    """0 a 1: cuánto del tema de la nota más corta está en la otra (palabras raras pesan más)."""
    if not a or not b:
        return 0.0
    comun = sum(idf.get(w, 1.0) for w in a & b)
    return comun / min(sum(idf.get(w, 1.0) for w in a), sum(idf.get(w, 1.0) for w in b))


MISMO_TEMA = 0.35
# Dos notas que comparten un nombre propio POCO común («Salmain», «Bolsonaro», «Wenance») son
# del mismo tema aunque el resto del título cambie, con tal de que algo más se parezca.
# «Milei» o «Kicillof» están en demasiadas notas para decir nada solos (su peso queda abajo).
PROPIO_RARO = 3.0
MISMO_TEMA_CON_PROPIO = 0.22


def _mismo_tema(a: set, b: set, idf: dict, fuerte_solo: bool = False) -> bool:
    p = parecido(a, b, idf)
    if p >= MISMO_TEMA:
        return True
    if fuerte_solo:
        return False
    raros = [w for w in a & b if w.startswith("*") and idf.get(w, 0) >= PROPIO_RARO]
    return bool(raros) and p >= MISMO_TEMA_CON_PROPIO


def agrupar(notas: list) -> list:
    """Listas de notas del MISMO tema (agrupamiento simple: cada nota se suma al primer grupo
    con el que se parece)."""
    conjuntos = [palabras_tema(n) for n in notas]
    idf = _idf(conjuntos)
    grupos = []                          # [(conjunto_unido, [índices])]
    for i, c in enumerate(conjuntos):
        for g in grupos:
            # Con la PRIMERA nota del grupo vale el parecido flojo (el nombre propio raro); con
            # las demás, solo el fuerte. Si no, se encadena: Brasil → Milei → el Gobierno → el
            # salario mínimo terminaron en un mismo «tema» de 16 notas.
            semilla, *resto = g[1]
            if _mismo_tema(c, conjuntos[semilla], idf) or any(
                    _mismo_tema(c, conjuntos[j], idf, fuerte_solo=True) for j in resto):
                g[1].append(i)
                g[0].update(c)
                break
        else:
            grupos.append((set(c), [i]))
    return [[notas[j] for j in g[1]] for g in grupos]


def candidatas(notas: list, ahora: float) -> list:
    """Una nota por tema (la de más puntaje), con la cobertura sumada, de mayor a menor.

    Cada candidata trae: puntos, nivel, motivos, cobertura (cuántas notas tiene su tema) y
    tema (las palabras del tema, para no repetirlo en otra pasada)."""
    # La cobertura se mide sobre TODO lo reciente, también lo que no va (la elección de Brasil
    # en la sección América cuenta para saber que el tema es grande).
    recientes = []
    for n in notas:
        if ahora - (n.get("fecha") or 0) > HORAS_VENTANA * 3600:
            continue
        p, nivel, motivos = puntuar(n, ahora)
        recientes.append(dict(n, puntos_base=p, nivel=nivel, motivos=motivos))
    salida = []
    for todas in agrupar(recientes):
        grupo = [x for x in todas if x["puntos_base"] > 0]
        if not grupo:
            continue
        mejor = max(grupo, key=lambda x: (x["puntos_base"], x.get("fecha") or 0))
        cobertura = len(todas)
        puntos = mejor["puntos_base"] + BONO_COBERTURA * min(cobertura - 1, TOPE_COBERTURA)
        # Un policial de otro lado o el ruido de la city solo entran si el tema es grande.
        if mejor["nivel"] in ("policial", "mercados") and cobertura < 3:
            continue
        if puntos < UMBRAL:
            continue
        salida.append(dict(mejor, puntos=puntos, cobertura=cobertura,
                           tema=sorted(palabras_tema(mejor)),
                           otras=[x["titulo"] for x in todas if x is not mejor][:4]))
    return sorted(salida, key=lambda x: (-x["puntos"], -(x.get("fecha") or 0)))


def ya_contado(candidata: dict, hechos: list, umbral: float = 0.55) -> str:
    """El título de una pieza YA hecha sobre el mismo tema, o "". Con un umbral más alto que el
    de agrupar: una novedad de un tema (el paro confirmado después del «podría haber paro»)
    tiene que poder salir."""
    a = set(candidata.get("tema") or palabras_tema(candidata))
    # Todas las palabras pesan igual (los nombres propios igual cuentan doble): un «idf» sacado
    # de dos o tres títulos castiga justo a las palabras compartidas, que son las que importan.
    for h in hechos:
        if parecido(a, set(h.get("tema") or []), {}) >= umbral:
            return h.get("titulo") or "(sin título)"
    return ""
