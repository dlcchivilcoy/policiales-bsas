# -*- coding: utf-8 -*-
"""Cercanía a Chivilcoy: qué hechos van primero (pedido del editor, 27/09/2026).

El diario es de Chivilcoy y su público también. Un robo en Chacabuco o un vuelco en la
Ruta 5 a la altura de Suipacha le interesa mucho más que un hecho igual de grave en
Trenque Lauquen, a 300 km. Las localidades prioritarias las eligió el editor: las más
cercanas y con más movimiento en las redes.

NO es un filtro: las demás localidades siguen saliendo (a YouTube, todas). Es un empujón
en las dos decisiones que sí recortan:
- al elegir los pocos reels por pasada que van a Facebook e Instagram (publicador), y
- al armar la tanda (flujo): van primero y entra una segunda nota del mismo pueblo con
  menos exigencia que para el resto.
"""
import re
import unicodedata

# Claves sin tildes, como en scraper/localidades.py.
PRIORITARIAS = ("junin", "chacabuco", "bragado", "mercedes", "suipacha", "alberti", "25 de mayo")

# Puntos que se le SUMAN al viral de la IA (escala 1 a 10) al elegir para Facebook e
# Instagram. Con 2, una nota de Chacabuco de viral 7 le gana a una de Pergamino de 8,
# pero un homicidio lejano de 9 le sigue ganando a una detención cercana de 6.
BONO_LOCALIDAD = 2
BONO_CHIVILCOY = 2     # el texto nombra a Chivilcoy o a un chivilcoyano
BONO_RUTA_5 = 1        # la ruta que usan todos los días en Chivilcoy
BONO_MAXIMO = 3

# Sobre el texto ya sin tildes: «Nº» queda «no» y «N°» queda «n°».
_RUTA_5 = re.compile(r"\brutas? (?:nacional )?(?:(?:nro|no|n|numero)[°.]* ?)?5\b|\brn ?5\b")
_CHIVILCOY = re.compile(r"\bchivilcoy")


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).split())


def es_prioritaria(localidad: str) -> bool:
    return _plano(localidad) in PRIORITARIAS


def bono(localidad: str, texto: str = "") -> int:
    """Puntos de cercanía (0 a BONO_MAXIMO) de un hecho de `localidad` contado en `texto`."""
    plano = _plano(texto)
    b = BONO_LOCALIDAD if es_prioritaria(localidad) else 0
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
    """Para una pieza ya armada (publicador): la localidad del hecho y lo que se publica."""
    g = pieza.get("guion") or {}
    texto = " ".join([g.get("volanta") or "", g.get("titular") or "", g.get("bajada") or "",
                      (pieza.get("web") or {}).get("cuerpo") or ""])
    return bono(pieza.get("localidad_hecho") or pieza.get("localidad") or "", texto)
