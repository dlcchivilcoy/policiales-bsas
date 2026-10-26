# -*- coding: utf-8 -*-
"""LA AGENDA DE NACIONALES: qué sale en cada corrida.

24/10/2026 (v8, pedido del editor): DOS corridas por día, todos los días (también sábado y domingo):

    04:00  SOLO WEB: 5 notas de cada categoría —política, economía y sociedad (las nacionales generales),
           espectáculos, cine y series, tecnología/IA, mundo y virales—, como nota de la web y nada más
           (sin redes, sin Short). NAC_WEB_<CATEGORIA> cambia cuántas.
           Desde el 25/10/2026 (v11), además, las 10 GENERALES más importantes del día para Chivilcoy (los
           «puntos» de nacionales/filtro.py), las que antes subía la corrida de las 22; NAC_WEB_GENERALES
           cambia cuántas. Van al final: las que ya salieron en política, economía o sociedad no se repiten.
    22:00  APAGADA desde el 25/10/2026 (pedido del editor; ni cron-job.org ni respaldo). Era
           UN CARRUSEL en Instagram (y el mismo álbum en Facebook) con las 10 noticias generales más
           importantes del día, las que más le tocan a Chivilcoy (los «puntos» de nacionales/filtro.py):
           las de la web de las 4 y las nuevas de la noche, que también quedan como nota en la web.
           NAC_CARRUSEL_NOTAS cambia cuántas.

En sus palabras: «que la corrida de nacionales (política, economía, sociedad) cargue solo 1 carrusel a las
22 hs con las 10 noticias más importantes del día, que traten de tener relevancia para la actualidad de
Chivilcoy»; «para el fin de semana, que se deshabiliten los posteos de espectáculos, cine y series,
tecnología/IA, mundo y virales para mis redes, que solo corran para web»; «habilitar scraping y posteo solo
como noticia para mi web todos los días haciendo una corrida a las 4 am». Deportes ya no sale (no está en la
lista). Los policiales van aparte (reels/cupo.py: 17 y 20).

Lo de abajo es la historia (v1 a v7), con lo que sigue sirviendo a las pasadas sin agenda.

Las nacionales tienen sus corridas propias (no van en las pasadas de policiales). TODO sale como REEL con
el video original de la nota: sin video, la nota no sale (ni como carrusel).

    días              corridas            qué sale en cada corrida
    lunes a viernes   18 · 21             2 de política y 2 de economía nacional (reel con imagen)
    sábado/domingo    10 · 14 · 18 · 21   6 de: viral, mundo, IA, general, deporte, cine/serie,
                                          espectáculo — 1 de cada una, las 6 más virales

«Mundo» = internacionales virales con video de algo policial o de violencia/conflicto (es_mundo). Desde el
20/10/2026 a la noche, SOLO el sábado y el domingo («la categoría mundo dejala solo para fin de semana»).

Las generales de lunes a viernes (pedido del 20/10/2026, noche: «3 generales: 1 política, 1 economía, 1
sociedad, y un viral; todo que sea reel y, si se puede, con video mejor»): la fila de las generales se parte
por la sección de Infobae (subgeneral: política + judiciales, economía, y sociedad + salud). Todo sale como
REEL: con el video de la nota si alguna de las mejores lo trae; si no, reel con la foto de la nota
(reel_con_foto). El viral, como siempre, solo con su video.

21/10/2026 (pedido del editor: «las corridas de nacionales sean reels solo de política y economía a nivel
nacional de lunes a viernes, y que el reel se haga solo con imagen, no con video»): de lunes a viernes, 2 de
política (sección /politica/ de Infobae) y 2 de economía (/economia/), solo de alcance NACIONAL (nada de
Chivilcoy, la región ni la provincia), y el reel se arma SIEMPRE con la foto de la nota, nunca con su video.
Sin viral, sin sociedad y sin mundo entre semana. NAC_AGENDA_POLITICA / NAC_AGENDA_ECONOMIA cambian cuántas.

(Historia: el 19/10 a la mañana, 10 · 18 · 21 con todo junto; a la tarde, 11 · 12 · 16 · 18 · 21; a la
noche, solo 18 y 21 con 2 por categoría y 1 reel + 1 carrusel. El 20/10, esta agenda.)

Ritmo: un posteo cada 30 minutos, también el finde. El primero a los 15 minutos del horario. Las corridas
van de a una (grupo de concurrencia): si la anterior todavía publica, la que sigue arranca cuando termina
y corre sus turnos desde ese momento (nunca dos posteos de nacionales a la misma hora).

Los policiales siguen con sus pasadas (reels/turnos.py).
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

TZ_AR = timezone(timedelta(hours=-3))
CORRIDA_WEB = (4, 0)
CORRIDA_CARRUSEL = (22, 0)
CORRIDAS_SEMANA = (CORRIDA_WEB, CORRIDA_CARRUSEL)          # v8 (24/10/2026): las mismas todos los días
CORRIDAS_FINDE = CORRIDAS_SEMANA
CORRIDAS = CORRIDAS_SEMANA                     # (compatibilidad: las de todos los días)
DEMORA_PRIMERO = 15
MINUTOS_SEMANA = 30
MINUTOS_FINDE = 30
FIN_DE_SEMANA = (5, 6)                 # sábado, domingo
GENERALES = ""                         # la «categoría» de las nacionales generales

SUBGENERALES = ("politica", "economia", "sociedad")
# La corrida web de las 4 (24/10/2026): {categoría: cuántas notas}. «internacionales» es Mundo.
WEB = {"politica": 5, "economia": 5, "sociedad": 5, "espectaculos": 5, "cine_series": 5, "tecnologia_ia": 5,
       "internacionales": 5, "virales": 5}
# 25/10/2026 (v11, «sumá a la corrida de las 04 las notas generales del día que subía la de las 22, solo a la
# web»): además de WEB, las WEB_GENERALES de más puntos para Chivilcoy, también lo provincial y lo regional.
WEB_GENERALES = 10
CARRUSEL_NOTAS = 10
# Lo que NO es de alcance nacional (nacionales/filtro.py, «nivel»): lo local, la región y la provincia.
NIVELES_NO_NACIONALES = {"Chivilcoy", "directa", "región", "provincia"}
GENERALES_TODAS = (GENERALES,) + SUBGENERALES        # las que se ordenan por «puntos» (no por impacto)
# Lunes a viernes, en cada corrida: {categoría: cuántas}. Mundo, solo el finde (20/10/2026, noche).
SEMANA = {"politica": 2, "economia": 2}              # 21/10/2026: solo política y economía nacional
# Sábado y domingo: 1 de cada categoría, y en total las POR_CORRIDA_FINDE más virales.
FINDE = {"virales": 1, "internacionales": 1, "tecnologia_ia": 1, GENERALES: 1, "deportes": 1,
         "cine_series": 1, "espectaculos": 1}
POR_CORRIDA_FINDE = 6
# Todo sale SOLO como reel con el video de la nota (NAC_TODO_REEL=0 vuelve a dejar el carrusel en
# generales, IA, espectáculos, cine y deportes).
SOLO_REEL = {"virales", "internacionales"}     # estas, siempre (desde el 19/10/2026)


def solo_reel(cat: str) -> bool:
    """¿La categoría sale solo como reel con su video? Desde el 20/10/2026, todas."""
    if cat in SOLO_REEL:
        return True
    return (os.environ.get("NAC_TODO_REEL") or "1").strip() != "0" and cat in (set(FINDE) | set(SEMANA))

def reel_con_foto(cat: str) -> bool:
    """¿Sale como reel con la FOTO de la nota (nunca con su video)? Las generales de lunes a viernes."""
    return cat in SUBGENERALES


def subgeneral(c: dict, solo_nacional: bool = True) -> str:
    """«politica», «economia» o «sociedad»: la sección de Infobae de una nacional general. Lo que no es de
    alcance nacional (Chivilcoy, la región, la provincia: NIVELES_NO_NACIONALES) da "" y no entra, salvo
    con solo_nacional=False (la web de las 4: lo de la provincia y la región también va)."""
    from urllib.parse import urlparse
    if solo_nacional and (c.get("nivel") or "") in NIVELES_NO_NACIONALES:
        return ""
    p = urlparse(c.get("url") or "").path
    if p.startswith("/politica/"):
        return "politica"
    if p.startswith("/economia/"):
        return "economia"
    return "sociedad"


# MUNDO: internacionales con algo policial o de violencia / conflicto (pedido del 20/10/2026).
_MUNDO = re.compile(
    r"\b(polic[ií]a\w*|crimen\w*|criminal\w*|asesin\w*|homicid\w*|femicid\w*|masacre\w*|matanza\w*|"
    r"dispar\w*|tirote\w*|balacer\w*|balead\w*|armad[oa]s?|arma de fuego|ataque\w*|atac[oóa]\w*|"
    r"bomb\w*|explosi\w*|explot\w*|guerra\w*|conflicto\w*|enfrentamiento\w*|choques? con|militar\w*|"
    r"ej[eé]rcito\w*|misil\w*|drones?|invasi\w*|violen\w*|protesta\w*|disturbio\w*|manifestant\w*|"
    r"represi\w*|saque\w*|toque de queda|detenid\w*|deten\w*|arrest\w*|captur\w*|secuestr\w*|rob[oó]\w*|"
    r"asalt\w*|narco\w*|c[aá]rtel\w*|pandill\w*|terroris\w*|reh[eé]n\w*|golpe de estado|apu[nñ]al\w*|"
    r"agresi\w*|agred\w*|golpiz\w*|pelea\w*|mot[ií]n\w*|vandal\w*|incendi\w* intencional|fuga de presos|"
    r"tiroteo|persecuci\w*|operativo\w*|redada\w*|fusil\w*|francotirador\w*|linchamiento\w*)\b", re.I)


def es_mundo(c: dict) -> bool:
    """¿Una nota internacional entra en «mundo»? Algo policial o de violencia/conflicto en el título, la
    bajada o el arranque del cuerpo."""
    texto = " ".join(str(c.get(k) or "") for k in ("titulo", "bajada", "descripcion"))
    texto += " " + str(c.get("cuerpo") or "")[:500]
    return bool(_MUNDO.search(texto))


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.environ.get(nombre) or defecto))
    except ValueError:
        return defecto


def es_finde(cuando: datetime) -> bool:
    return cuando.weekday() in FIN_DE_SEMANA


def corridas_del_dia(cuando: datetime) -> tuple:
    return CORRIDAS_FINDE if es_finde(cuando) else CORRIDAS_SEMANA


def _candidatas(ahora: datetime, dias) -> list:
    out = []
    for d in dias:
        dia = ahora + timedelta(days=d)
        out += [dia.replace(hour=h, minute=m, second=0, microsecond=0) for h, m in corridas_del_dia(dia)]
    return out


def corrida(ahora: datetime) -> datetime:
    """El horario de la corrida a la que pertenece `ahora`: la última que ya empezó (con 10 minutos de
    margen por si cron-job.org dispara antes). Un día hábil antes de las 18, la de las 21 del día anterior."""
    return max(c for c in _candidatas(ahora, (-1, 0)) if c <= ahora + timedelta(minutes=10))


def siguiente(inicio: datetime) -> datetime:
    return min(c for c in _candidatas(inicio, (0, 1)) if c > inicio)


def modo(inicio: datetime) -> str:
    """«web» (la de las 4), «carrusel» (la de las 22) o "" (un horario que no es de la agenda)."""
    hm = (inicio.hour, inicio.minute)
    if hm not in corridas_del_dia(inicio):
        return ""
    return {CORRIDA_WEB: "web", CORRIDA_CARRUSEL: "carrusel"}.get(hm, "")


def topes(inicio: datetime) -> dict:
    """{categoría: cuántas en esta corrida}. v8: a las 4, WEB (NAC_WEB_<CAT>) y, desde la v11, las generales
    (NAC_WEB_GENERALES); a las 22, las generales del carrusel (NAC_CARRUSEL_NOTAS)."""
    if (inicio.hour, inicio.minute) not in corridas_del_dia(inicio):
        return {}
    if modo(inicio) == "web":
        salida = {}
        for cat, defecto in WEB.items():
            n = _entero(f"NAC_WEB_{cat.upper()}", defecto)
            if n:
                salida[cat] = n
        n = _entero("NAC_WEB_GENERALES", WEB_GENERALES)
        if n:
            salida[GENERALES] = n
        return salida
    if modo(inicio) == "carrusel":
        return {GENERALES: min(10, _entero("NAC_CARRUSEL_NOTAS", CARRUSEL_NOTAS))}
    if es_finde(inicio):
        return dict(FINDE)
    salida = {}
    for cat, defecto in SEMANA.items():
        n = _entero(f"NAC_AGENDA_{(cat or 'GENERALES').upper()}", defecto)
        if n:
            salida[cat] = n
    return salida


def maximo(inicio: datetime):
    """Cuántos posteos como mucho en la corrida; None = la suma de los topes (siempre, desde la v8)."""
    if modo(inicio):
        return None
    return _entero("NAC_POR_CORRIDA_FINDE", POR_CORRIDA_FINDE) if es_finde(inicio) else None


def tope_del_dia(cat: str, cuando: datetime) -> int:
    """Lo más que puede salir de `cat` en el día."""
    dia = cuando.replace(hour=0, minute=0)
    return sum(topes(dia.replace(hour=h, minute=m)).get(cat, 0) for h, m in corridas_del_dia(cuando))


def minutos(inicio: datetime) -> int:
    """Cada cuánto sale un posteo: 30 minutos (también el finde, desde el 20/10/2026)."""
    if es_finde(inicio):
        return _entero("NAC_MINUTOS_FINDE", MINUTOS_FINDE) or MINUTOS_FINDE
    return _entero("NAC_MINUTOS", MINUTOS_SEMANA) or MINUTOS_SEMANA


def turnos(inicio: datetime, cuantos: int, holgura: int = 0, ahora: datetime = None) -> list:
    """Los horarios de los posteos de la corrida: `cuantos` con su espaciado y `holgura` turnos más, por si
    alguno queda vacío. El primero a los 15 minutos del horario o, si la corrida arrancó tarde (esperó a la
    anterior), 5 minutos después de arrancar."""
    paso = minutos(inicio)
    t0 = inicio + timedelta(minutes=DEMORA_PRIMERO)
    if ahora is not None and ahora + timedelta(minutes=5) > t0:
        t0 = (ahora + timedelta(minutes=5)).replace(second=0, microsecond=0)
    return [t0 + timedelta(minutes=paso * k) for k in range(max(0, cuantos + holgura))]


def corrida_id(inicio: datetime) -> str:
    """El id de la corrida para la fila de turnos (reels/turnos.py): «2026-10-19T10:00»."""
    return inicio.strftime("%Y-%m-%dT%H:%M")
