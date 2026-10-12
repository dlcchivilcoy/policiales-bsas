# -*- coding: utf-8 -*-
"""El RELEVAMIENTO de lo que ya se subió, para no repetir un hecho (pedido del editor, 12/10/2026).

Lo que pasaba: el mismo hecho salía dos veces porque lo publicaban dos medios distintos, cada uno
con su título. El único control antes de escribir comparaba los títulos de los MEDIOS (60 % de
palabras iguales) y nada más después. Ejemplos reales:
  · «Robaron más de 100 placas de bronce del Cementerio Judío de Carlos Casares» (La Trocha,
    11/10) y «Robo de más de un centenar de placas de bronce» (Diario Junín, 12/10): el segundo
    título no dice ni cementerio ni Carlos Casares;
  · la camioneta de bomberos de Cañuelas, con el MISMO titular nuestro, dos veces en 3 horas;
  · el fuego de una camioneta en la Ruta 5 (Bragado / 9 de Julio), los dos detenidos por
    allanamientos en Bragado, la rueda de camión de la Ruta 46, los cuatro muertos de Bolívar…

Cómo se decide ahora, contra TODO lo publicado (estado/publicados.json, que ya guardaba el titular
de cada posteo y ahora además la bajada, el pueblo del hecho y el título del medio) y contra lo que
ya se armó en la misma pasada:
  1. misma nota (la misma dirección o el mismo número de nota del medio) → repetida;
  2. casi las mismas palabras (raíces, sin los nombres de los pueblos) y el mismo pueblo o un
     número en común (la ruta 191, las 100 placas — «centenar» cuenta como 100), en 3 días →
     repetida, sin preguntarle a nadie;
  3. parecido a medias → se le pregunta a la IA, con fechas, lugares y textos, si es el MISMO
     hecho concreto. Si la IA no contesta, se juega a no repetir: con 60 % de parecido en 3
     días, repetida.
Se usa en dos lugares: en flujo.procesar, apenas la IA escribió el guion (antes de armar el reel),
y en el publicador, antes de subir a cualquier red.
"""
import math
import re
from datetime import datetime, timedelta

from reels import ledger as LD

DIAS = 10                     # hasta cuánto hacia atrás se mira
DIAS_SEGURO = 3               # la decisión sin IA, solo entre hechos de estos días
CONTIENE_SEGURO = 0.7         # parte de las raíces del texto más corto que está en el otro
CONTIENE_IA = 0.4             # desde acá, se le pregunta a la IA
CONTIENE_IA_MISMO_PUEBLO = 0.25
CONTIENE_SIN_IA = 0.6         # si la IA no contesta
MAX_CANDIDATAS = 6

_GENERICAS = LD._VACIAS | {"contra", "luego", "tras", "durante", "segun", "habria", "estaba",
                           "estan", "esta", "tiene", "hacia", "ante", "otro", "otra", "este"}
_NUMEROS = {"dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
            "ocho": "8", "nueve": "9", "diez": "10", "once": "11", "doce": "12", "veinte": "20",
            "cien": "100", "centenar": "100", "centenares": "100", "mil": "1000"}


def _pueblos() -> frozenset:
    try:
        from reels.ubicaciones import cargar
        nombres = [d.get("nombre", "") for d in cargar().values()]
    except Exception:                                            # noqa: BLE001
        nombres = []
    return frozenset(w for n in nombres for w in re.findall(r"[a-z]+", LD._norm(n)) if len(w) >= 4)


_PUEBLOS = _pueblos()


def raices(texto: str) -> frozenset:
    """Las palabras con contenido, recortadas a 5 letras («robaron»/«robo» no, pero «placas»/
    «placa», «choque»/«chocó» sí), sin tildes, sin relleno y sin los nombres de los pueblos (el
    pueblo se mira aparte: dos hechos distintos del mismo pueblo no tienen que parecerse)."""
    out = set()
    for p in re.findall(r"[a-z]+", LD._norm(texto)):
        if len(p) < 4 or p in _GENERICAS or p in _PUEBLOS or p in _NUMEROS:
            continue
        out.add(p[:5])
    return frozenset(out)


def numeros(texto: str) -> set:
    t = LD._norm(texto)
    out = set(re.findall(r"\b\d{1,4}\b", t))
    out |= {v for k, v in _NUMEROS.items() if re.search(rf"\b{k}\b", t)}
    return out


def pueblo(texto: str) -> str:
    from reels.ubicaciones import clave
    return clave(texto or "")


def ficha(titular: str, bajada: str = "", localidad: str = "", titulo_medio: str = "",
          url: str = "", cuando: str = "", resumen: str = "") -> dict:
    """Lo que se compara de un hecho."""
    return {"titular": titular or "", "bajada": bajada or "", "localidad": localidad or "",
            "titulo_medio": titulo_medio or "", "url": url or "", "cuando": cuando or "",
            "resumen": (resumen or "")[:400]}


def ficha_pieza(pieza: dict, cuando: str = "") -> dict:
    g = pieza.get("guion") or {}
    return ficha(g.get("titular"), g.get("bajada"), pieza.get("localidad_hecho") or pieza.get("localidad"),
                 pieza.get("titulo_medio") or "", pieza.get("url_original") or "",
                 cuando or datetime.now().isoformat(timespec="seconds"),
                 pieza.get("descripcion_tiktok") or "")


def cargar_publicados() -> dict:
    """estado/publicados.json ENTERO (el publicador lo carga podado a 5 días; acá hacen falta 10)."""
    import json
    archivo = LD.RAIZ / "estado" / "publicados.json"
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def de_publicados(ledger: dict = None, dias: int = DIAS, ahora: datetime = None) -> list:
    """Las fichas de lo que salió en alguna red en los últimos `dias` (estado/publicados.json)."""
    ahora = ahora or datetime.now()
    corte = ahora - timedelta(days=dias)
    out = []
    for url, e in (ledger or {}).items():
        if not isinstance(e, dict):
            continue
        if not any(isinstance(v, dict) and v.get("estado") in ("ok", "sin_confirmar") for v in e.values()):
            continue
        cuando = e.get("ultimo") or ""
        try:
            if datetime.fromisoformat(cuando[:19]) < corte:
                continue
        except ValueError:
            pass
        out.append(ficha(e.get("titular"), e.get("bajada"), e.get("localidad_hecho") or e.get("localidad"),
                         e.get("titulo_medio"), url, cuando))
    return out


def _texto(f: dict) -> str:
    return f"{f.get('titular', '')} {f.get('bajada', '')} {f.get('titulo_medio', '')}"


def _dias_entre(a: str, b: str) -> float:
    try:
        return abs((datetime.fromisoformat(a[:19]) - datetime.fromisoformat(b[:19])).total_seconds()) / 86400
    except (ValueError, TypeError):
        return 0.0


def pesos(fichas: list) -> dict:
    """Cuánto distingue cada raíz: lo rara que es entre todo lo publicado (IDF). «choque»,
    «ruta», «camioneta» o «detenido» están en medio corpus y casi no cuentan; «cementerio»,
    «bomberos» o «piedrazo» deciden. Sin esto, dos choques distintos en rutas distintas se
    parecían «67 %»."""
    df = {}
    for f in fichas:
        for r in raices(_texto(f)):
            df[r] = df.get(r, 0) + 1
    n = max(1, len(fichas))
    return {r: math.log((n + 1) / (c + 0.5)) for r, c in df.items()}


def parecido(nueva: dict, previa: dict, idf: dict = None) -> dict:
    """Las señales entre dos fichas: cuánto contiene (pesado por lo que distingue cada palabra),
    mismo pueblo, números en común, días."""
    a, b = raices(_texto(nueva)), raices(_texto(previa))
    idf = idf or {}
    tope = math.log(len(idf) + 2) if idf else 1.0

    def peso(conj):
        return sum(idf.get(r, tope) for r in conj)
    contiene = peso(a & b) / max(1e-9, min(peso(a), peso(b))) if (a and b) else 0.0
    pa, pb = pueblo(nueva.get("localidad")), pueblo(previa.get("localidad"))
    return {"contiene": round(contiene, 2), "palabras": min(len(a), len(b)),
            "mismo_pueblo": bool(pa) and pa == pb,
            "numeros": sorted(numeros(_texto(nueva)) & numeros(_texto(previa))),
            "dias": round(_dias_entre(nueva.get("cuando", ""), previa.get("cuando", "")), 1)}


SYSTEM_IA = """Sos el editor de una cuenta de noticias policiales de la provincia de Buenos Aires. Tu
trabajo es que NUNCA se publique dos veces el mismo hecho. Te paso una NOTA NUEVA y una lista de
notas YA PUBLICADAS (con su fecha y lugar). Decidí si la nueva cuenta el MISMO HECHO CONCRETO que
alguna de las publicadas.

Es el MISMO hecho: el mismo choque, robo, incendio, detención, allanamiento, muerte o alerta del
mismo día, aunque lo cuente otro medio, con otras palabras, con otro pueblo de referencia (el
medio de la ciudad vecina), con un dato más o menos, o un día después.
NO es el mismo: un hecho parecido en otro lugar o en otra fecha (otro choque en la misma ruta otro
día, otra alerta otro día), o un DESARROLLO NUEVO IMPORTANTE del caso que la publicada no tenía
(detuvieron al autor, murió un herido, identificaron a la víctima, hubo condena).

Contestá SOLO un JSON: {"repetida": true o false, "indice": número de la publicada igual o -1,
"motivo": "una oración"}"""


def _preguntar_ia(nueva: dict, candidatas: list) -> tuple:
    """(índice de la candidata igual o -1, motivo). Lanza si la IA no contesta."""
    from reels import ia

    def linea(f):
        return (f"fecha {f.get('cuando', '')[:16] or 's/d'} · lugar {f.get('localidad') or 's/d'}\n"
                f"   titular: {f.get('titular')}\n   bajada: {f.get('bajada') or '-'}"
                + (f"\n   título del medio: {f['titulo_medio']}" if f.get("titulo_medio") else ""))
    material = (f"NOTA NUEVA:\n{linea(nueva)}"
                + (f"\n   texto: {nueva['resumen']}" if nueva.get("resumen") else "")
                + "\n\nYA PUBLICADAS:\n"
                + "\n".join(f"[{i}] {linea(f)}" for i, f in enumerate(candidatas)))
    datos, _detalle = ia.redactar(SYSTEM_IA, material)
    i = int(datos.get("indice", -1)) if datos.get("repetida") else -1
    return (i if 0 <= i < len(candidatas) else -1), str(datos.get("motivo") or "")[:200]


def repetida(nueva: dict, previas: list, usar_ia: bool = True) -> dict | None:
    """La ficha publicada que cuenta el mismo hecho que `nueva` (con `motivo` y `como`), o None.
    `previas`: lo publicado (`de_publicados`) más lo armado en la misma pasada."""
    ident = LD.identidad((nueva.get("url") or "").rstrip("/"))
    dudosas = []
    for p in previas:
        if ident and LD.identidad((p.get("url") or "").rstrip("/")) == ident:
            return dict(p, motivo="es la misma nota", como="url")
    idf = pesos(list(previas) + [nueva])
    for p in previas:
        s = parecido(nueva, p, idf)
        if s["palabras"] < 3:
            continue
        if (s["dias"] <= DIAS_SEGURO and s["contiene"] >= CONTIENE_SEGURO and s["palabras"] >= 4
                and (s["mismo_pueblo"] or s["numeros"])):
            return dict(p, motivo=f"mismas palabras ({s['contiene']:.0%})"
                                  + (" y mismo pueblo" if s["mismo_pueblo"] else
                                     f" y el número {', '.join(s['numeros'])}"), como="texto")
        if s["dias"] <= DIAS and (s["contiene"] >= CONTIENE_IA
                                  or (s["mismo_pueblo"] and s["contiene"] >= CONTIENE_IA_MISMO_PUEBLO)):
            dudosas.append((s["contiene"] + (0.15 if s["mismo_pueblo"] else 0)
                            + (0.1 if s["numeros"] else 0), s, p))
    if not dudosas:
        return None
    dudosas.sort(key=lambda x: x[0], reverse=True)
    dudosas = dudosas[:MAX_CANDIDATAS]
    if usar_ia:
        try:
            i, motivo = _preguntar_ia(nueva, [p for _, _, p in dudosas])
            return dict(dudosas[i][2], motivo=f"la IA: {motivo}", como="ia") if i >= 0 else None
        except Exception:                                        # noqa: BLE001
            pass
    # Sin IA: solo lo muy parecido, del mismo pueblo o con un número en común, en el mismo día.
    # (Probado contra lo publicado: más suelto, junta choques distintos de la misma semana.)
    for _, s, p in dudosas:
        if (s["dias"] <= 1 and s["contiene"] >= CONTIENE_SIN_IA
                and (s["mismo_pueblo"] or s["numeros"])):
            return dict(p, motivo=f"parecido {s['contiene']:.0%} (sin IA para confirmar)", como="texto")
    return None


def motivo(rep: dict) -> str:
    """La línea para el informe: qué hecho ya estaba y por qué se lo reconoció."""
    return (f"repite un hecho ya publicado: «{(rep.get('titular') or '')[:70]}» "
            f"({(rep.get('cuando') or '')[:10]}; {rep.get('motivo', '')})")
