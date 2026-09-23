# -*- coding: utf-8 -*-
"""Lee el .env del proyecto.

Por que es un modulo aparte y no una funcion suelta: esto ya existia adentro de
scraper/run.py y reels/flujo.py no lo tenia. El resultado fue que --con-ia no podia
funcionar NUNCA en una maquina local —no habia quien leyera el archivo con las
claves— y el sintoma era un "la IA fallo: RuntimeError" que no decia nada.

Y no se notaba, porque en GitHub Actions las claves llegan como variables de
entorno del workflow y ahi anda. O sea: el camino que genera el material
publicable solo se podia probar en produccion. Teniendolo en un solo lugar, el que
se olvide de llamarlo es un bug visible y no una diferencia silenciosa entre la
notebook y la nube.
"""
import os

RAIZ = os.path.dirname(os.path.abspath(__file__))


def cargar(ruta: str = None) -> int:
    """Mete en os.environ lo que haya en el .env. Devuelve cuantas variables cargo.

    No pisa lo que ya este definido: en la nube manda el entorno del workflow, y un
    .env que se colara nunca tiene que ganarle.
    """
    ruta = ruta or os.path.join(RAIZ, ".env")
    if not os.path.exists(ruta):
        return 0
    puestas = 0
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not v:                      # los huecos del template no cuentan
                continue
            if k not in os.environ:
                os.environ[k] = v
                puestas += 1
    return puestas


def consola_utf8():
    """Pone la salida de la consola en UTF-8.

    En Windows la consola habla cp1252, que no tiene ni los simbolos que usamos ni
    —lo peor— forma de fallar en silencio: imprimir un "advertencia" corta la
    corrida entera con UnicodeEncodeError. Paso de verdad: el primer aviso que
    genero el sistema tumbo la generacion de reels justo cuando habia algo
    importante para avisar.

    Ademas es la razon por la que los acentos salian rotos ("Junin" por "Junin"):
    no era el dato, era el terminal. En Linux, que ya es UTF-8, esto no hace nada.
    """
    import sys
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
