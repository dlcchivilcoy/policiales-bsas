# -*- coding: utf-8 -*-
"""¿El video del reel es de ESTA nota? (14/11/2026)

Por qué existe: la página de una nota de Infobae, La Nación o Clarín trae, además del video de la nota, los
de OTRAS notas (los «relacionados» del reproductor). Se elegía el que más palabras compartía con el título, y
si ninguno compartía nada, el primero de la página. Así salieron tres reels de prueba con el video
equivocado: la casa sustentable en Córdoba con el entrenamiento de la Selección (11/11), el bebé rescatado
en Carolina del Sur con el médico de la Selección hablando de Dibu (12/11) y las 50 maratones con un joven
matemático de la India (13/11).

Dos controles, de lo barato a lo caro:

1. PALABRAS (`parecido`): el título y la descripción del video contra el título y el texto de la nota.
   Si comparten palabras del título, el video es de la nota y no se gasta la IA; si no comparten nada (o
   una sola palabra suelta), es de otra nota y se descarta.
2. LA IA MIRA (`mirar`): en lo dudoso —el video sin título, o con pocas palabras en común—, Gemini ve
   tres cuadros del video con el título de la nota y dice si corresponden. Si la IA no contesta, decide el
   control de palabras, del lado seguro.

`controlar()` junta los dos y devuelve {"ok", "motivo", "via", ...}: si "ok" es False, el reel no lleva
ese video (las virales no salen; los policiales salen con la foto).
"""
import os
import re
import tempfile
from pathlib import Path

# El video con este título comparte palabras con el título de la nota: es de la nota.
SEGURO_TITULO = 2           # dos palabras del título…
SEGURO_TITULO_Y_TEXTO = (1, 2)   # …o una del título y dos del texto
# Sin la IA, lo dudoso pasa solo si comparte bastante con el texto.
SIN_IA_TEXTO = 4

SISTEMA = (
    "Sos el control de calidad de un diario. Te paso cuadros de un video y la noticia que lo va a "
    "acompañar en un reel. Decí si el video es de ESTA noticia: muestra el hecho, las personas, el lugar, "
    "el animal o el tema de la noticia. También corresponde si muestra a los MISMOS protagonistas o la "
    "misma historia en otro momento (imágenes de archivo, el antes o el después). NO corresponde si es de "
    "OTRA noticia: otro tema, otras personas, otro animal u otro lugar (por ejemplo fútbol o la Selección "
    "en una noticia de un rescate, o un concurso de cálculo en una noticia de maratones). Una persona "
    "hablando a cámara o un estudio de TV corresponden si el zócalo, el texto en pantalla o lo que se ve "
    "tienen que ver con la noticia. Tiene que ser el MISMO hecho, no uno parecido: mirá el título que le puso "
    "el medio al video, los zócalos y los carteles. Si cuentan otro lugar, otra fecha u otras personas, NO "
    "corresponde aunque el tema se parezca (granizo en Corrientes para una noticia del granizo en el AMBA, un "
    "baile ante el Papa en Perú para una noticia del Papa con Cáritas, otro viajero para una noticia de "
    "jubilados en motorhome, el discurso de una política para una noticia de una inventora). Ante la duda, NO. "
    "Respondé SOLO un JSON: "
    '{"corresponde": true o false, "que_muestra": "qué se ve, en una frase", "motivo": "por qué, en una frase"}'
)


def estricto() -> bool:
    """20/11/2026 (el editor: «hay algunos que no tienen relación entre el video y el texto»): salieron el granizo
    del AMBA con el de Corrientes, el Papa con Cáritas con un baile en Perú, la inventora del «Baño Calientito» con
    una política mexicana. Las palabras en común («Papa», «granizo») los daban por buenos sin mirar. En modo
    estricto la IA mira SIEMPRE los cuadros, y si no contesta solo pasa el video cuyo título coincide de verdad.
    VIDEO_CONTROL_ESTRICTO=0 vuelve al control de antes (las palabras deciden solas cuando coinciden)."""
    return (os.environ.get("VIDEO_CONTROL_ESTRICTO") or "1").strip() != "0"


def activo() -> bool:
    """VIDEO_CONTROL=0 apaga el control (vuelve a usar el video sin mirar)."""
    return (os.environ.get("VIDEO_CONTROL") or "1").strip() != "0"


def _palabras(texto: str) -> set:
    from nacionales import impacto as IM
    return IM.palabras(texto or "")


def parecido(titulo: str, texto: str, nombre_video: str) -> dict:
    """Cuántas palabras comparte el video (su título y descripción) con el título y con el texto de la nota,
    y qué dice eso: "si" (es de la nota), "no" (es de otra) o "duda" (que mire la IA)."""
    v = _palabras(nombre_video)
    t = len(_palabras(titulo) & v)
    x = len(_palabras(f"{titulo} {texto}") & v)
    if not v:
        veredicto = "duda"                           # el video no tiene título: no se puede comparar
    elif t >= SEGURO_TITULO or (t >= SEGURO_TITULO_Y_TEXTO[0] and x >= SEGURO_TITULO_Y_TEXTO[1]):
        veredicto = "si"
    elif t == 0 and x <= 1:
        veredicto = "no"
    else:
        veredicto = "duda"
    return {"titulo": t, "texto": x, "palabras_video": len(v), "veredicto": veredicto}


def cuadros(clip, carpeta=None, cuantos: int = 3) -> list:
    """Tres cuadros del video (al 20, 50 y 80 %), como JPG. [] si no se pueden sacar."""
    from reels import reel_bot as R
    carpeta = Path(carpeta or tempfile.gettempdir())
    try:
        dura = float(R.motor().duration_seconds(Path(clip)))
    except Exception:                                # noqa: BLE001
        dura = 0.0
    salida = []
    for i in range(cuantos):
        seg = max(0.5, dura * (0.2 + 0.6 * i / max(1, cuantos - 1))) if dura else 0.5 + 2 * i
        destino = carpeta / f"{Path(clip).stem}_control{i}.jpg"
        try:
            hecho = R.cuadro_de_video(Path(clip), destino, seg)
        except Exception:                            # noqa: BLE001
            hecho = None
        if hecho and Path(hecho).is_file():
            salida.append(Path(hecho))
    return salida


def mirar(imagenes: list, titulo: str, bajada: str = "", nombre_video: str = "", texto: str = "") -> dict:
    """Gemini mira los cuadros y dice si son de la nota. Lanza si la IA no contesta."""
    from reels import ia as IA
    material = (f"NOTICIA\nTítulo: {titulo}\nBajada: {bajada}\nTexto: {(texto or '')[:1200]}\n\n"
                f"VIDEO\nTítulo que le puso el medio: {nombre_video or '(sin título)'}\n"
                f"Arriba van {len(imagenes)} cuadros del video, en orden.")
    partes = [("image/jpeg", Path(i).read_bytes()) for i in imagenes]
    crudo, via = IA.redactar_gemini(SISTEMA, material, max_tokens=300, imagenes=partes)
    datos = IA._parsear(crudo)
    return {"corresponde": bool(datos.get("corresponde")), "que_muestra": str(datos.get("que_muestra") or "")[:200],
            "motivo": str(datos.get("motivo") or "")[:200], "via": via}


def controlar(clip, titulo: str, bajada: str = "", texto: str = "", nombre_video: str = "",
              carpeta=None, mirar_fn=None) -> dict:
    """¿Va este video con esta nota? {"ok", "motivo", "via", "parecido", "ia"?}."""
    if not activo():
        return {"ok": True, "via": "apagado (VIDEO_CONTROL=0)", "motivo": ""}
    p = parecido(titulo, texto, nombre_video)
    base = {"parecido": p, "video": (nombre_video or "")[:160]}
    duro = estricto()
    if p["veredicto"] == "si" and not duro:
        return dict(base, ok=True, via="palabras", motivo="")
    if p["veredicto"] == "no":
        return dict(base, ok=False, via="palabras",
                    motivo=f"el video es de otra nota («{(nombre_video or '')[:80]}»)")
    imgs = cuadros(clip, carpeta) if clip else []
    if imgs:
        try:
            r = (mirar_fn or mirar)(imgs, titulo, bajada, nombre_video, texto)
            ok = bool(r.get("corresponde"))
            return dict(base, ok=ok, via="ia", ia=r,
                        motivo="" if ok else f"la IA vio que el video es de otra cosa: {r.get('que_muestra') or r.get('motivo')}")
        except Exception as e:                       # noqa: BLE001 — sin la IA decide el control de palabras
            base["ia_error"] = re.sub(r"key=[^&\s]+", "key=…", str(e))[:160]
    ok = (p["veredicto"] == "si") if duro else (p["titulo"] >= 1 or p["texto"] >= SIN_IA_TEXTO)
    return dict(base, ok=ok, via="palabras (sin la IA)",
                motivo="" if ok else "no se pudo comprobar que el video sea de la nota")
