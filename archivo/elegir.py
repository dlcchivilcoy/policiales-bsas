# -*- coding: utf-8 -*-
"""Qué se cuenta hoy en el reel del Archivo Literario.

Prioridad (plan aprobado por el editor, 10/10/2026):
1. EFEMÉRIDE de HOY («Un día como hoy…»): los hechos del índice con el día y el mes de hoy.
2. Si hoy no hay ninguna que sirva: un PERSONAJE chivilcoyano.
3. Si tampoco: una CURIOSIDAD de la historia local.

Sin repetir nada usado en DIAS_SIN_REPETIR, ni el mismo personaje (ni su post) en
DIAS_MISMO_PERSONAJE. Se prefiere lo que tiene foto propia: la foto destacada de un post DEDICADO
a ese hecho o esa persona. La foto de una lista mensual NO sirve: es la «estampa de la historia»
del mes, de otro tema.
"""
import hashlib
import re
from datetime import datetime, timedelta

from archivo import fuente as F

DIAS_SIN_REPETIR = 365
DIAS_MISMO_PERSONAJE = 60
CANDIDATAS = 5              # efemérides de hoy que se le muestran a la IA para que elija
BUSCAR_FOTO = 6             # a cuántas de las mejores se les busca foto (cada una, 1-3 pedidos)
FOTO_MIN = (400, 300)       # lado mayor, lado menor

_POSITIVO = re.compile(r"\b(?:fund|cre[oóa]|creaci|inaugur|naci[oó]|nacimiento|visit|apertura|abri[oó]|aparici|"
                       r"primer|estren|lleg[oó]|llegada|exposici|campe[oó]n|r[eé]cord|premi|piedra fundamental|"
                       r"habilit|bautiz|impuso|impusieron)", re.IGNORECASE)
_LISTA = re.compile(r"del mes de|efem[eé]rides|hechos del mes|en la historia|distintos episodios|sucedi[oó]|"
                    r"historia chivilcoyana:|recordaciones|evocaciones del mes", re.IGNORECASE)


def _sha(texto: str) -> str:
    return hashlib.sha1(F.norm(texto).encode("utf-8")).hexdigest()[:8]


def clave_hecho(h: dict) -> str:
    return f"h:{h['anio']}-{h['mes']:02d}-{h['dia']:02d}:{_sha(h['textos'][0][:160])}"


def clave_post(post_id) -> str:
    return f"p:{post_id}"


def _usado(usados: dict, clave: str, dias: int, hoy: datetime) -> bool:
    cuando = usados.get(clave)
    if not cuando:
        return False
    try:
        return datetime.fromisoformat(cuando).date() > (hoy - timedelta(days=dias)).date()
    except ValueError:
        return False


def puntaje(h: dict, anio_hoy: int) -> int:
    texto = " ".join(h["textos"])
    hace = anio_hoy - h["anio"]
    p = 3 if _POSITIVO.search(h["textos"][0][:260]) else 0
    if hace > 0 and hace % 100 == 0:
        p += 6
    elif hace > 0 and hace % 50 == 0:
        p += 4
    elif hace > 0 and hace % 25 == 0:
        p += 3
    elif hace > 0 and hace % 10 == 0:
        p += 1
    if hace < 15:
        p -= 2                    # todavía es noticia reciente, no «historia»
    p += 1 if len(h["textos"][0]) > 220 else 0
    p += min(2, len(h["posts"]) - 1)          # lo contaron varios posts: es un hecho importante
    if re.search(r"\b(?:intendente|comisionado)\b", texto, re.IGNORECASE) and not _POSITIVO.search(texto):
        p -= 1                    # una asunción o un acto de gobierno: rinde poco en redes
    return p


def _comparte_nombres(titulo: str, nombres: list, minimo: int = 2) -> bool:
    t = F.norm(titulo)
    return sum(1 for n in nombres if re.search(r"\b" + re.escape(F.norm(n)) + r"\b", t)) >= minimo


MAX_FECHAS_DEDICADO = 3     # un post con más hechos fechados que esto es una recopilación


def es_dedicado(h: dict, texto: str) -> bool:
    """¿El post cuenta ESE hecho y no es una recopilación? Tiene que nombrar la fecha exacta (día, mes y
    año) y tener pocos hechos fechados: la foto destacada de una recopilación es de otro tema (el 10/10
    salió una foto del personal del Archivo para la fundación de 1854)."""
    fechas = {(x["dia"], x["mes"], x["anio"]) for x in F.hechos_del_texto(texto)}
    if len(fechas) > MAX_FECHAS_DEDICADO:
        return False
    if (h["dia"], h["mes"], h["anio"]) in fechas:
        return True
    plano = F.norm(texto)
    return bool(re.search(rf"\b{h['dia']}\s+de\s+{F.MESES[h['mes'] - 1]}\b", plano)) and str(h["anio"]) in plano


def foto_para(h: dict, ind: dict, cli=None, buscar=None, media=None, leer=None) -> dict:
    """El post DEDICADO a ese hecho, con foto: {post, titulo, texto, foto: {url, ancho, alto}} o {}.

    Candidatos: los posts que cuentan el hecho y no son listas mensuales, y si no hay, los que da el
    buscador del sitio con los nombres propios del hecho. El título tiene que compartir nombres con el
    hecho y el texto tiene que nombrar su fecha exacta (es_dedicado)."""
    buscar = buscar or (lambda q: F.buscar_posts(q, cli))
    media = media or (lambda mid: F.url_foto(mid, cli))
    leer = leer or (lambda pid: F.post_completo(pid, cli))
    nombres = F.nombres_propios(h["textos"][0])
    minimo = 2 if len(nombres) >= 2 else 1
    if not nombres:
        return {}
    candidatos = []
    for pid in h["posts"]:
        p = (ind.get("posts") or {}).get(str(pid)) or {}
        if p and not _LISTA.search(p.get("titulo") or "") and _comparte_nombres(p["titulo"], nombres, minimo):
            candidatos.append(p["id"])
    if not candidatos:
        for r in buscar(" ".join(nombres[:3])) or []:
            if not _LISTA.search(F.titulo(r)) and _comparte_nombres(F.titulo(r), nombres, minimo):
                candidatos.append(r["id"])
    for pid in list(dict.fromkeys(candidatos))[:3]:
        try:
            post = leer(pid)
        except F.FuenteError:
            continue
        if not post.get("foto") or not es_dedicado(h, post.get("texto") or ""):
            continue
        f = media(post["foto"])
        if not f.get("url"):
            continue
        if f.get("ancho") and (max(f["ancho"], f["alto"]) < FOTO_MIN[0] or min(f["ancho"], f["alto"]) < FOTO_MIN[1]):
            continue
        return {"post": pid, "titulo": post.get("titulo") or "", "texto": post.get("texto") or "", "foto": f}
    return {}


def efemerides_de_hoy(ind: dict, usados: dict, hoy: datetime, cli=None, buscar=None, media=None,
                      leer=None) -> list:
    """Las candidatas de hoy, mejores primero, cada una con su foto si la tiene."""
    hechos = [h for h in F.efemerides_de(ind, hoy.day, hoy.month)
              if not h.get("sombrio") and h["anio"] < hoy.year
              and not _usado(usados, clave_hecho(h), DIAS_SIN_REPETIR, hoy)]
    hechos.sort(key=lambda h: -puntaje(h, hoy.year))
    salida = []
    for i, h in enumerate(hechos[:max(CANDIDATAS, BUSCAR_FOTO)]):
        c = {"tipo": "efemeride", "hecho": h, "clave": clave_hecho(h), "puntaje": puntaje(h, hoy.year),
             "hace": hoy.year - h["anio"]}
        if i < BUSCAR_FOTO:
            c["dedicado"] = foto_para(h, ind, cli, buscar, media, leer)
            if c["dedicado"] and _usado(usados, clave_post(c["dedicado"]["post"]), DIAS_MISMO_PERSONAJE, hoy):
                c["dedicado"] = {}
            if c["dedicado"].get("foto"):
                c["puntaje"] += 4
        salida.append(c)
    salida.sort(key=lambda c: -c["puntaje"])
    con_foto = [c for c in salida if (c.get("dedicado") or {}).get("foto")]
    # Con dos o más que tienen foto propia, van solo esas: el reel con la foto del hecho rinde
    # mucho más que con la placa.
    return (con_foto if len(con_foto) >= 2 else salida)[:CANDIDATAS]


def _rotar(lista: list, hoy: datetime, sal: str) -> list:
    """Un orden fijo para cada día (que dos corridas del mismo día elijan lo mismo)."""
    return sorted(lista, key=lambda p: hashlib.sha1(f"{sal}{hoy:%Y-%m-%d}{p['id']}".encode()).hexdigest())


def personaje(ind: dict, usados: dict, hoy: datetime) -> list:
    lista = [p for p in ind.get("personajes") or [] if p.get("foto")
             and not _usado(usados, clave_post(p["id"]), max(DIAS_MISMO_PERSONAJE, DIAS_SIN_REPETIR), hoy)]
    return [{"tipo": "personaje", "post": p, "clave": clave_post(p["id"])} for p in _rotar(lista, hoy, "per")[:3]]


def curiosidad(ind: dict, usados: dict, hoy: datetime) -> list:
    lista = [p for p in ind.get("curiosidades") or [] if p.get("foto") and not _LISTA.search(p["titulo"])
             and not _usado(usados, clave_post(p["id"]), DIAS_SIN_REPETIR, hoy)]
    return [{"tipo": "curiosidad", "post": p, "clave": clave_post(p["id"])} for p in _rotar(lista, hoy, "cur")[:3]]


def elegir(ind: dict, usados: dict, hoy: datetime, cli=None, buscar=None, media=None, leer=None) -> tuple:
    """(tipo, candidatas). tipo: «efemeride», «personaje» o «curiosidad»."""
    efe = efemerides_de_hoy(ind, usados, hoy, cli, buscar, media, leer)
    if efe:
        return "efemeride", efe
    per = personaje(ind, usados, hoy)
    if per:
        return "personaje", per
    return "curiosidad", curiosidad(ind, usados, hoy)
