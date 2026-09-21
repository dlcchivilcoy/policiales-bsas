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
import re
import time
import unicodedata
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


# Palabras que aparecen en cualquier titular policial y no distinguen un hecho de
# otro. Si se dejan, dos choques distintos se parecen demasiado y el segundo se
# descarta por error.
_VACIAS = {
    "para", "como", "desde", "hasta", "sobre", "entre", "tras", "este", "esta",
    "estos", "estas", "pero", "porque", "cuando", "donde", "fueron", "fue",
    "habia", "hubo", "tenia", "sus", "una", "unos", "unas", "del", "los", "las",
    "que", "con", "por", "anos", "ano", "hoy", "ayer", "noche", "madrugada",
    "manana", "tarde", "local", "nuevo", "nueva", "gran", "toda", "todo",
}


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _huella(nota: dict) -> frozenset:
    """Las palabras con contenido del titular, sin tildes ni relleno.

    Para que sirve: la misma noticia sale en varios medios de la zona con titulares
    parecidos pero URLs distintas, asi que la URL sola no alcanza para no repetir.
    Un allanamiento en Chacabuco puede salir en Diario Democracia y en Chacabuco en
    Red el mismo dia, y son dos reels del mismo hecho."""
    palabras = re.findall(r"[a-z0-9]+", _norm(nota.get("titulo") or ""))
    return frozenset(p for p in palabras if len(p) >= 4 and p not in _VACIAS)


def _se_parecen(a: frozenset, b: frozenset, umbral: float = 0.6) -> bool:
    """Jaccard sobre las palabras con contenido.

    0,6 salio de mirar casos reales: dos versiones del mismo allanamiento comparten
    entre el 65% y el 80% de las palabras, y dos hechos distintos de la misma
    localidad rara vez pasan del 40%. Se pide ademas un minimo de 4 palabras a cada
    lado, porque con titulares muy cortos cualquier umbral da falsos positivos."""
    if len(a) < 4 or len(b) < 4:
        return False
    return len(a & b) / len(a | b) >= umbral


def _huellas_recordadas(hechos: dict) -> list:
    hs = []
    for v in hechos.values():
        if isinstance(v, dict):
            h = frozenset(v.get("huella") or ())
            if h:
                hs.append(h)
    return hs


def ya_hecha(nota: dict, hechos: dict = None) -> bool:
    hechos = _cargar() if hechos is None else hechos
    if _clave(nota) in hechos:
        return True
    h = _huella(nota)
    return any(_se_parecen(h, otra) for otra in _huellas_recordadas(hechos))


def filtrar(notas: list) -> tuple:
    """Saca las que ya tuvieron reel. Devuelve (pendientes, cuantas se saltearon).

    Filtra por dos motivos: la URL exacta —la misma nota que vuelve a aparecer en la
    pasada siguiente— y el parecido del titular, que es la unica forma de no hacer
    dos veces el mismo hecho cuando lo publicaron dos medios distintos.

    Tambien mira las notas ENTRE SI, no solo contra la memoria: en una misma pasada
    entran los dos medios de una localidad, y si los dos cubrieron el mismo choque
    hay que quedarse con uno solo."""
    hechos = _cargar()
    urls = set(hechos)
    huellas = _huellas_recordadas(hechos)

    pendientes = []
    for n in notas:
        k = _clave(n)
        if not k or k in urls:
            continue
        h = _huella(n)
        if any(_se_parecen(h, otra) for otra in huellas):
            continue
        huellas.append(h)      # las de esta misma tanda tampoco se repiten entre si
        urls.add(k)
        pendientes.append(n)
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
                # Ordenada para que el archivo sea estable entre corridas: si el
                # orden bailara, cada pasada generaria un diff aunque no cambie nada
                # y el commit del ledger seria puro ruido.
                "huella": sorted(_huella(n)),
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
