# -*- coding: utf-8 -*-
"""Cercanía a Chivilcoy: qué hechos van primero dentro del radio de 100 km.

El diario es de Chivilcoy y su público también. Desde el 17/10/2026 (PDF «Prompt integral») la
prioridad sale de la DISTANCIA medida (reels/geografia.py, catálogo Georef), no de una lista de
pueblos elegidos a mano (la del 27/09 era Junín, Chacabuco, Bragado, Mercedes, Suipacha, Alberti
y 25 de Mayo). Bandas configurables, no cuotas:

- Chivilcoy: +3 · hasta 50 km (Alberti, Suipacha, Bragado): +2 · hasta el radio: +1.
- Lo que está fuera del radio ya no llega acá (lo saca geografia), pero por las dudas suma 0.
- Siguen sumando que el texto nombre a Chivilcoy o a un chivilcoyano (+2) y la Ruta 5 (+1).

NO es un filtro: es un empujón en las dos decisiones que recortan — qué notas se arman (flujo) y
qué reels salen en cada red (publicador). Nunca habilita un lugar fuera del radio ni un cuarto
reel en la pasada.
"""
import re
import unicodedata

from reels import geografia as GEO

BONO_BANDA = {"chivilcoy": 3, "cercana": 2, "zona": 1}
BONO_CHIVILCOY = 2     # el texto nombra a Chivilcoy o a un chivilcoyano
BONO_RUTA_5 = 1        # la ruta que usan todos los días en Chivilcoy
BONO_MAXIMO = 3
# Desde cuánto bono una nota es «cercana» para la vara más baja de la segunda nota (flujo).
BONO_CERCANA = 2

# Sobre el texto ya sin tildes: «Nº» queda «no» y «N°» queda «n°».
_RUTA_5 = re.compile(r"\brutas? (?:nacional )?(?:(?:nro|no|n|numero)[°.]* ?)?5\b|\brn ?5\b")
_CHIVILCOY = re.compile(r"\bchivilcoy")


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).split())


def bono_banda(localidad: str = "", evaluacion: dict = None) -> int:
    ev = evaluacion if evaluacion is not None else (GEO.de_localidad(localidad) if localidad else {})
    return BONO_BANDA.get(ev.get("banda") or "", 0) if ev.get("elegible") else 0


def bono(localidad: str, texto: str = "", evaluacion: dict = None) -> int:
    """Puntos de cercanía (0 a BONO_MAXIMO) de un hecho de `localidad` contado en `texto`."""
    plano = _plano(texto)
    b = bono_banda(localidad or "", evaluacion)
    if _CHIVILCOY.search(plano):
        b += BONO_CHIVILCOY
    if _RUTA_5.search(plano):
        b += BONO_RUTA_5
    return min(b, BONO_MAXIMO)


def bono_nota(nota: dict) -> int:
    """Para una nota scrapeada (flujo): la localidad del hecho y el titular + resumen."""
    texto = " ".join([nota.get("titulo") or "",
                      (nota.get("resumen") or nota.get("copete") or "")[:300]])
    return bono(nota.get("localidad") or nota.get("localidad_medio") or "", texto)


def bono_pieza(pieza: dict) -> int:
    """Para una pieza ya armada (publicador): el lugar del hecho evaluado y lo que se publica."""
    g = pieza.get("guion") or {}
    texto = " ".join([g.get("volanta") or "", g.get("titular") or "", g.get("bajada") or "",
                      (pieza.get("web") or {}).get("cuerpo") or ""])
    ev = pieza.get("geo") if isinstance(pieza.get("geo"), dict) else None
    return bono(pieza.get("localidad_hecho") or pieza.get("localidad") or "", texto, ev)
