# -*- coding: utf-8 -*-
"""Memoria de qué notas ya se convirtieron en reel.

El problema que resuelve: las tres pasadas del día (10, 17 y 20) miran ventanas de horas
que se superponen, y una nota fuerte de la mañana sigue estando en el listado a la tarde.
Sin memoria, el sistema haría el MISMO reel tres veces.

Por qué hace falta un archivo y no alcanza con la ventana de horas: en GitHub Actions cada
corrida arranca en una máquina nueva y vacía. Lo que la pasada de las 10 escribió en disco
no existe a las 17. La única forma de que se acuerde es guardar el dato FUERA del
contenedor — acá, commiteado al propio repo, que es lo más simple que funciona y además
queda auditable (se ve en el historial qué se publicó cada día).

Se poda solo: las entradas de más de `DIAS_MEMORIA` días se borran, así el archivo no
crece para siempre. 15 reels por día × 30 días son ~450 líneas, nada.
"""
import json
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "estado" / "reels_hechos.json"

# Cuántos días se recuerda una nota. Tiene que ser MAYOR que la ventana más larga del
# scraper (12 h) con margen de sobra: si fuera igual, una nota del borde podría volver a
# entrar justo cuando se la olvidó.
DIAS_MEMORIA = 5


def _cargar() -> dict:
    if not ARCHIVO.exists():
        return {}
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8")).get("hechos", {})
    except Exception:
        # Un archivo corrupto no puede frenar la corrida: se arranca de cero y se
        # reescribe. Lo peor que pasa es que se repita un reel una vez.
        return {}


def _clave(nota: dict) -> str:
    """La URL sin la barra final. Es el mismo criterio de dedup que usa el scraper."""
    return (nota.get("url") or "").rstrip("/")


def ya_hecha(nota: dict, hechos: dict = None) -> bool:
    hechos = _cargar() if hechos is None else hechos
    return _clave(nota) in hechos


def filtrar(notas: list) -> tuple:
    """Saca las que ya tuvieron reel. Devuelve (pendientes, cuántas se saltearon)."""
    hechos = _cargar()
    pendientes = [n for n in notas if _clave(n) and _clave(n) not in hechos]
    return pendientes, len(notas) - len(pendientes)


def registrar(notas: list) -> int:
    """Anota las notas que acaban de tener reel y poda lo viejo. Devuelve cuántas quedaron
    en memoria."""
    hechos = _cargar()
    ahora = time.time()
    for n in notas:
        k = _clave(n)
        if k:
            hechos[k] = {
                "cuando": ahora,
                "localidad": n.get("localidad") or n.get("localidad_medio") or "",
                "titular": (n.get("titulo") or "")[:110],
            }

    corte = ahora - DIAS_MEMORIA * 86400
    hechos = {k: v for k, v in hechos.items()
              if isinstance(v, dict) and v.get("cuando", 0) >= corte}

    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO.write_text(json.dumps(
        {"actualizado": time.strftime("%Y-%m-%d %H:%M:%S"),
         "dias_memoria": DIAS_MEMORIA,
         "hechos": hechos}, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(hechos)


def resumen() -> str:
    hechos = _cargar()
    if not hechos:
        return "sin memoria previa"
    return f"{len(hechos)} notas recordadas (últimos {DIAS_MEMORIA} días)"
