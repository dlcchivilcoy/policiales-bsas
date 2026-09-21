# -*- coding: utf-8 -*-
"""Diccionario policial: primer filtro (gratis, sin IA) del pipeline hibrido.

Es GENEROSO a proposito: barato equivocarse dejando pasar de mas, porque despues
Claude confirma. Lo caro es descartar una nota buena, porque de ahi no vuelve.

Todos los terminos se comparan normalizados (minusculas, sin tildes), asi que no
hace falta listar "choco" y "chocó" por separado; de hecho los duplicados se
eliminan al cargar para que una misma palabra no sume el puntaje dos veces.
"""
import re
import unicodedata

# --- Nucleo: si aparece uno de estos, la nota es casi seguro policial -------------
FUERTES = [
    # robos y delitos contra la propiedad
    "robo", "robos", "robaron", "robado", "robados", "robada", "robadas",
    "hurto", "hurtaron", "asalto", "asaltaron", "asaltante",
    "entradera", "arrebato", "motochorro", "motochorros", "escruche", "abigeato",
    "estafa", "estafador", "defraudacion", "usurpacion",
    # homicidios y violencia
    "homicidio", "asesinato", "asesinaron", "asesinado", "crimen", "femicidio",
    "apuñalo", "apuñalado", "apuñalada", "puñalada", "balacera", "tiroteo",
    "baleado", "baleada", "acribillado", "lesiones graves", "golpiza",
    "violencia de genero", "violencia familiar",
    # armas y drogas
    "arma de fuego", "arma blanca", "narcotrafico", "narcomenudeo", "estupefacientes",
    "cocaina", "marihuana", "bunker narco", "desarmadero",
    # siniestros viales
    "siniestro vial", "siniestro de transito", "choque", "chocaron", "choco",
    "colision", "colisionaron", "vuelco", "volco", "volcaron", "despiste",
    "despistaron", "atropello", "atropellado", "atropellaron",
    "embistio", "embestido", "victima fatal", "victimas fatales", "murio en el acto",
    "accidente fatal", "accidente de transito", "tragico accidente",
    # incendios y emergencias
    "incendio", "incendios", "se incendio", "incendiaron", "incendiado",
    "principio de incendio", "explosion", "derrumbe",
    # policial / judicial
    "policial", "policiales", "detenido", "detenida", "detenidos", "detuvieron",
    "aprehendido", "aprehendida", "aprehendidos", "aprehendieron", "aprehension",
    "allanamiento", "allanamientos",
    "prision preventiva", "imputado", "fiscalia", "comisaria", "denuncia penal",
    "causa penal", "juzgado de garantias", "profugo", "secuestraron", "incautaron",
    "operativo policial", "condenado", "excarcelacion",
    # muertes no naturales
    "suicidio", "se quito la vida", "ahorcado", "sin vida", "cuerpo sin vida",
    "hallaron muerto", "hallaron muerta", "cadaver", "autopsia", "muerte dudosa",
    # personas
    "desaparecido", "desaparecida", "busqueda de persona", "secuestro", "rapto",
    "abuso sexual", "violacion", "amenazas", "acoso",
]

# --- Contexto: suman pero solos no alcanzan -------------------------------------
DEBILES = [
    "herido", "heridos", "herida", "hospital", "ambulancia", "same", "hospitalizado",
    "terapia intensiva", "victima", "victimas", "grave estado",
    "ruta", "autopista", "kilometro", "banquina", "cruce",
    "moto", "motociclista", "camioneta", "automovil", "vehiculo", "camion",
    "policia", "patrullero", "movil policial", "destacamento", "gendarmeria",
    "bomberos", "cuartel", "rescate", "llamas", "fiscal", "sumario",
    "investigacion", "testigo", "sospechoso", "banda", "delincuente", "delincuentes",
    "inseguridad", "damnificado", "denuncia", "agresion", "disparo", "disparos",
]

# --- Contexto que APAGA la nota: la palabra existe pero el tema no es policial ----
# Sin esto entran solas "se robó el show" (deportes), "homenaje a los bomberos"
# (comunidad) o "charla de seguridad vial" (institucional).
#
# Van en DOS listas porque no todos apagan igual:

# 1) Apagan SIEMPRE, incluso si el titular trae una palabra policial fuerte. Son
#    usos figurados o actos institucionales donde la palabra fuerte es justamente
#    la que esta de adorno.
APAGADORES_FUERTES = [
    "se robo el show", "robo la escena", "le robo el protagonismo", "robo de balones",
    "robo de pelota", "incendio de pasiones", "choque de opiniones",
    "homenaje", "aniversario", "desfile", "colecta", "rifa",
    "capacitacion", "simulacro", "taller", "charla", "jornada de concientizacion",
    "campaña de prevencion", "curso de primeros auxilios", "dia del bombero",
    "entrega de equipamiento", "acto oficial", "inauguro", "inauguracion",
    "accidente cerebrovascular",
]

# 2) Apagan SOLO si el titular no trae ninguna palabra policial fuerte. Marcan el
#    tema de la nota, no el uso de la palabra: un hecho policial puede pasar en un
#    partido de futbol y sigue siendo policial. Sin esta distincion, "Un joven fue
#    apuñalado tras un partido de futbol" quedaba en -2 y se perdia.
APAGADORES_CONTEXTO = [
    "gol", "goles", "torneo", "campeonato", "campeon", "hinchada", "futbol",
    "basquet", "sorteo", "acv",
]

APAGADORES = APAGADORES_FUERTES + APAGADORES_CONTEXTO

_MARCA = re.compile(r"[̀-ͯ]")


def normalizar(texto: str) -> str:
    """Minusculas y sin tildes, para que 'chocó' y 'choco' matcheen igual."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = _MARCA.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _dedup(terminos) -> list:
    """Saca duplicados por forma normalizada: 'robo' y 'robó' son el mismo termino
    y contarlos dos veces inflaba el score (asi se colaba 'se robó el show')."""
    vistos, out = set(), []
    for t in terminos:
        n = normalizar(t)
        if n and n not in vistos:
            vistos.add(n)
            out.append(n)
    return out


FUERTES_N = _dedup(FUERTES)
_F = set(FUERTES_N)
DEBILES_N = [d for d in _dedup(DEBILES) if d not in _F]
APAGADORES_FUERTES_N = _dedup(APAGADORES_FUERTES)
_AF = set(APAGADORES_FUERTES_N)
APAGADORES_CONTEXTO_N = [a for a in _dedup(APAGADORES_CONTEXTO) if a not in _AF]
APAGADORES_N = APAGADORES_FUERTES_N + APAGADORES_CONTEXTO_N

_PALABRA = "[a-z0-9ñ]"


def _contiene(texto_norm: str, termino_norm: str) -> bool:
    """Match por limite de palabra: evita que 'armado' dispare por 'arma'."""
    if " " in termino_norm:
        return termino_norm in texto_norm
    return re.search(rf"(?<!{_PALABRA}){re.escape(termino_norm)}(?!{_PALABRA})", texto_norm) is not None


# Pesos. El titulo manda: en el medio local el titular describe el hecho, mientras
# que el cuerpo arrastra menus, "notas relacionadas" y pie de pagina que ensucian.
P_FUERTE_TIT, P_FUERTE_CUE = 6, 2
P_DEBIL_TIT, P_DEBIL_CUE = 2, 1
P_APAGADOR_TIT, P_APAGADOR_CUE = 8, 3
UMBRAL = 5


def puntuar(titulo: str, cuerpo: str = "") -> dict:
    """Puntua cuanto 'huele a policial' una nota.

    Devuelve {score, aciertos, apagadores, probable}. `probable` es lo que decide
    si la nota sigue hacia Claude o se descarta sin gastar un token.
    """
    t = normalizar(titulo)
    c = normalizar(cuerpo[:3000])

    f_tit = [k for k in FUERTES_N if _contiene(t, k)]
    f_cue = [k for k in FUERTES_N if k not in f_tit and _contiene(c, k)]
    d_tit = [k for k in DEBILES_N if _contiene(t, k)]
    d_cue = [k for k in DEBILES_N if k not in d_tit and _contiene(c, k)]

    # Los apagadores de CONTEXTO se ignoran si el titular ya trae una palabra
    # policial fuerte: el tema de fondo puede ser un partido de futbol y el hecho
    # seguir siendo un apuñalamiento.
    apagadores = APAGADORES_N if not f_tit else APAGADORES_FUERTES_N
    a_tit = [k for k in apagadores if _contiene(t, k)]
    a_cue = [k for k in apagadores if k not in a_tit and _contiene(c, k)]

    score = (len(f_tit) * P_FUERTE_TIT + len(f_cue) * P_FUERTE_CUE
             + len(d_tit) * P_DEBIL_TIT + len(d_cue) * P_DEBIL_CUE
             - len(a_tit) * P_APAGADOR_TIT - len(a_cue) * P_APAGADOR_CUE)

    return {
        "score": score,
        "aciertos": f_tit + d_tit + f_cue[:5] + d_cue[:5],
        "apagadores": a_tit + a_cue,
        "probable": score >= UMBRAL,
    }


def es_probable_policial(titulo: str, cuerpo: str = "") -> bool:
    return puntuar(titulo, cuerpo)["probable"]
