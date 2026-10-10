# -*- coding: utf-8 -*-
"""El Archivo Literario Municipal de Chivilcoy (archivoliterariochivilcoy.com), por la API de WordPress.

El sitio es un WordPress con la API pública abierta y un robots.txt que permite todo. Tiene ~2.200
posts y ~1.000 páginas: listas mensuales de efemérides («1 de febrero de 1884: Creación de la Escuela
Nro. 7…»), notas de un hecho («El 7 de febrero de 1980, hubo de abrir sus puertas la pizzería…»),
147 «Personajes chivilcoyanos» y evocaciones de la historia local («Las primeras proyecciones
cinematográficas, en Chivilcoy (1907)»).

Para no bajar 15 MB en cada pasada, lo que sale de leer TODO el sitio queda en `archivo/indice.json`
(se arma con `python -m archivo.fuente --indice` y va en el repo): los hechos fechados, los personajes
y las curiosidades, con el link y la foto destacada de cada post. En la pasada se suma lo publicado
después de armarlo (1 pedido) y se baja solo el post elegido y su foto.
"""
import argparse
import html
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "https://www.archivoliterariochivilcoy.com/wp-json/wp/v2"
RAIZ = Path(__file__).resolve().parent.parent
INDICE = Path(__file__).resolve().parent / "indice.json"
TZ_AR = timezone(timedelta(hours=-3))

CAT_EFEMERIDES = 9
CAT_PERSONAJES = 10
CAT_LUNFARDO = 20

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
_MES = "|".join(MESES) + "|setiembre"
TEXTO_HECHO = 700           # caracteres que se guardan de cada hecho en el índice

# El arranque de un hecho fechado, con los formatos que usa el sitio:
#   «1 de febrero de 1884: …»   «11 y 12 de febrero de 1933: …»   «El 12 de febrero de 1984, falleció…»
#   «Los días 11 y 12 de febrero de 1933, …»   «Febrero 1 de 1868 – …»   «- 3 de octubre de 1868 …»
#   «El domingo 22 de octubre de 1854, se fundó…»   «Los 63 años, el 15 de junio de 1961, de la creación…»
_VINETA = r"^[\s\-–—•*·»>]*"
_SEMANA = r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
_DIA_MES_ANIO = re.compile(
    _VINETA + r"(?:los\s+\d{1,3}\s+a[ñn]os,?\s+)?"
    r"(?:(?:el|los\s+d[ií]as|un|una|sucedi[oó]\s+(?:el|un)|aquel)\s+)?(?:" + _SEMANA + r"\s+)?"
    r"(?P<dia>\d{1,2})(?:º|°)?(?:\s*(?:y|al|-|–)\s*(?P<dia2>\d{1,2}))?\s+de\s+(?P<mes>" + _MES + r")"
    r"(?:\s*(?:de|del|,)\s*(?:a[ñn]o\s+)?(?P<anio>1[5-9]\d\d|20\d\d))?\b\s*[:,.\-–—]?\s*(?P<resto>.*)$",
    re.IGNORECASE)
_MES_DIA_ANIO = re.compile(
    _VINETA + r"(?P<mes>" + _MES + r")\s+(?P<dia>\d{1,2})(?:º|°)?(?:\s*(?:y|-|–)\s*(?P<dia2>\d{1,2}))?"
    r"\s*(?:de|,)\s*(?P<anio>1[5-9]\d\d|20\d\d)\b\s*[:,.\-–—]?\s*(?P<resto>.*)$",
    re.IGNORECASE)

# Lo que no va en un reel de prueba que busca gente nueva: crímenes y tragedias (de eso ya se ocupa
# policiales) y lo que el propio sitio escribe en clave de opinión.
_SOMBRIO = re.compile(r"\b(?:homicid|asesin|crimen|criminal|terroris|desaparecid|secuestr|violaci|suicid|"
                      r"sangrient|masacre|fusilam|tortur|apu[ñn]al|baleado|tragedia|tr[aá]gic|accidente|"
                      r"poner fin a su (?:existencia|vida)|quit[oó] la vida|quitarse la vida|la ni[ñn]a\b|"
                      r"el ni[ñn]o\b|los restos)", re.IGNORECASE)
# Posts que son avisos o despedidas recientes, no historia para contar.
_DESPEDIDA = re.compile(r"^(?:falleci|sepelio|adi[oó]s|necrol|condolencias|el pr[oó]ximo|invitaci|convocatoria)",
                        re.IGNORECASE)
_NO_ES_HISTORIA = re.compile(r"lunfard|demo\b|customizer|contacto|entradas blog|blog archivo|inico|"
                             r"\bweb\b|gu[ií]a para conocer|archivo literario|biblioteca virtual|"
                             r"formato digital|descargar|fasc[ií]culo|antolog[ií]a|programa televisivo",
                             re.IGNORECASE)


class FuenteError(Exception):
    pass


def _cliente() -> httpx.Client:
    return httpx.Client(timeout=60, follow_redirects=True,
                        headers={"User-Agent": "DiarioLaCampana-Reels/1.0"})


def _get(cli: httpx.Client, ruta: str, **params):
    ultimo = ""
    for intento in range(3):
        if intento:
            time.sleep(5 * intento)
        try:
            r = cli.get(f"{BASE}/{ruta}", params=params)
        except httpx.HTTPError as e:
            ultimo = f"{type(e).__name__}: {e}"
            continue
        if r.status_code == 200:
            return r
        ultimo = f"HTTP {r.status_code}"
        if r.status_code not in (429, 500, 502, 503, 504):
            break
    raise FuenteError(f"el Archivo no contestó ({ruta}): {ultimo}")


# =============================================================================
# Texto
# =============================================================================

def texto_plano(h: str) -> str:
    """El HTML de WordPress a renglones de texto (un párrafo o un ítem por renglón)."""
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</div>|</figcaption>|</tr>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h).replace("\xa0", " ")
    renglones = [" ".join(r.split()) for r in h.split("\n")]
    return "\n".join(r for r in renglones if r)


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def titulo(p: dict) -> str:
    t = p.get("title") or ""
    t = t.get("rendered") or "" if isinstance(t, dict) else str(t)      # /search lo da como texto
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", t)).split())


def _mes(nombre: str) -> int:
    n = norm(nombre)
    return 9 if n == "setiembre" else MESES.index(n) + 1


def hechos_del_texto(texto: str) -> list:
    """Cada renglón que arranca con una fecha completa (día, mes y AÑO): {dia, mes, anio, texto}.
    Los que no dicen el año («El 2 de abril, se conmemora el 37 aniversario…») quedan afuera: el
    aniversario está contado desde el año en que se escribió y en un reel quedaría mal."""
    salida = []
    for renglon in (texto or "").split("\n"):
        r = renglon.strip()
        if len(r) < 25:
            continue
        m = _DIA_MES_ANIO.match(r) or _MES_DIA_ANIO.match(r)
        if not m or not m.group("anio"):
            continue
        dia, mes, anio = int(m.group("dia")), _mes(m.group("mes")), int(m.group("anio"))
        if not 1 <= dia <= 31:
            continue
        resto = m.group("resto").strip(" .:-–—,")
        if len(resto) < 20:
            continue                 # un subtítulo («Sucedió un 7 de febrero…»), no un hecho
        salida.append({"dia": dia, "mes": mes, "anio": anio, "texto": r[:TEXTO_HECHO]})
        if m.group("dia2"):
            d2 = int(m.group("dia2"))
            if 1 <= d2 <= 31 and d2 != dia:
                salida.append({"dia": d2, "mes": mes, "anio": anio, "texto": r[:TEXTO_HECHO]})
    return salida


_GENERICAS = set("""chivilcoy chivilcoyano chivilcoyana chivilcoyanos nuestra nuestro ciudad partido escuela
primaria nro don dona doctor dr dra profesor profesora senor senora fundacion creacion nacimiento fallecimiento
inauguracion apertura aparicion grafica diario periodico club centro calle avenida plaza local localidad
lugareno hombre publico enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre
diciembre""".split())


def palabras_clave(texto: str) -> set:
    """Las palabras con peso de un texto (para juntar el mismo hecho contado en dos posts)."""
    return {w for w in re.findall(r"[a-zñ]{4,}", norm(texto)) if w not in _GENERICAS}


def nombres_propios(texto: str) -> list:
    """Las palabras en mayúscula que no arrancan oración (para buscar el post de ese personaje)."""
    sin_fecha = re.sub(r"^[^:,]*\d{4}\s*[:,.\-–—]\s*", "", texto or "")
    vistos, salida = set(), []
    for w in re.findall(r"(?<![.!?]\s)(?<!^)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñü]{2,})", sin_fecha):
        n = norm(w)
        if n in _GENERICAS or n in vistos or n in ("el", "la", "los", "las", "del", "con", "por", "una"):
            continue
        vistos.add(n)
        salida.append(w)
    return salida


# =============================================================================
# Índice
# =============================================================================

def _parecido(a: set, b: set) -> float:
    return len(a & b) / max(1, min(len(a), len(b))) if a and b else 0.0


def juntar_hechos(hechos: list) -> list:
    """El mismo hecho aparece en la lista mensual y en la nota de ese día: se junta en uno, con
    el texto más largo adelante y la nota (si hay) como post propio."""
    grupos = {}
    for h in hechos:
        clave = (h["dia"], h["mes"], h["anio"])
        # Misma fecha y mismo año: alcanza con que el arranque se parezca o con 3 nombres propios
        # en común (el texto entero no sirve: cada post adorna distinto y diluye el parecido).
        pal = palabras_clave(h["texto"][:250])
        nom = {norm(n) for n in nombres_propios(h["texto"])}
        lista = grupos.setdefault(clave, [])
        for g in lista:
            if _parecido(pal, g["_pal"]) >= 0.3 or len(nom & g["_nom"]) >= 3:
                g["textos"].append(h["texto"])
                g["posts"].append(h["post"])
                g["_pal"] |= pal
                g["_nom"] |= nom
                break
        else:
            lista.append({**{k: h[k] for k in ("dia", "mes", "anio")}, "textos": [h["texto"]],
                          "posts": [h["post"]], "_pal": pal, "_nom": nom})
    salida = []
    for lista in grupos.values():
        for g in lista:
            g.pop("_pal")
            g.pop("_nom")
            vistos, textos = set(), []
            for t in sorted(g["textos"], key=len, reverse=True):
                if norm(t) not in vistos:
                    vistos.add(norm(t))
                    textos.append(t)
            g["textos"] = textos[:3]
            g["posts"] = list(dict.fromkeys(g["posts"]))[:6]
            g["sombrio"] = bool(_SOMBRIO.search(" ".join(textos)))
            salida.append(g)
    salida.sort(key=lambda g: (g["mes"], g["dia"], g["anio"]))
    return salida


def _post_resumido(p: dict, tipo: str) -> dict:
    return {"id": p["id"], "tipo": tipo, "titulo": titulo(p), "link": p.get("link") or "",
            "foto": p.get("featured_media") or 0, "fecha": (p.get("date") or "")[:10],
            "cats": p.get("categories") or []}


def armar_indice(posts: list, paginas: list) -> dict:
    """Todo lo que se usa del sitio, sin el texto completo de cada post."""
    hechos, personajes, curiosidades, todos = [], [], [], {}
    for tipo, lista in (("post", posts), ("pagina", paginas)):
        for p in lista:
            t = titulo(p)
            cats = p.get("categories") or []
            texto = texto_plano((p.get("content") or {}).get("rendered") or "")
            if CAT_LUNFARDO in cats or _NO_ES_HISTORIA.search(t):
                continue
            resumen = _post_resumido(p, tipo)
            todos[str(p["id"])] = resumen
            for h in hechos_del_texto(texto):
                hechos.append({**h, "post": p["id"]})
            if len(texto) < 600 or _SOMBRIO.search(t) or _DESPEDIDA.search(t):
                continue
            if CAT_PERSONAJES in cats:
                personajes.append(resumen)
            elif tipo == "pagina" or not re.search(r"del mes de|efem[eé]rides|hechos del mes|en la historia",
                                                   t, re.IGNORECASE):
                curiosidades.append(resumen)
    juntos = juntar_hechos(hechos)
    usados = {str(i) for h in juntos for i in h["posts"]}
    return {"armado": datetime.now(TZ_AR).isoformat(timespec="seconds"),
            "hechos": juntos, "personajes": personajes, "curiosidades": curiosidades,
            "posts": {k: v for k, v in todos.items() if k in usados}}


def bajar_todo(cli: httpx.Client = None) -> tuple:
    cli = cli or _cliente()
    salida = {}
    for tipo in ("posts", "pages"):
        todos, pagina = [], 1
        while True:
            r = _get(cli, tipo, per_page=100, page=pagina,
                     _fields="id,date,link,title,content,featured_media,categories")
            todos += r.json()
            if pagina >= int(r.headers.get("X-WP-TotalPages") or 1):
                break
            pagina += 1
        salida[tipo] = todos
    return salida["posts"], salida["pages"]


def cargar_indice() -> dict:
    try:
        return json.loads(INDICE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_indice(ind: dict):
    INDICE.write_text(json.dumps(ind, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def novedades(desde: str, cli: httpx.Client = None) -> list:
    """Los posts publicados después de `desde` (fecha ISO): 1 pedido. El sitio publica poco (el último
    es de agosto de 2025), así que el índice guardado casi siempre está completo."""
    cli = cli or _cliente()
    try:
        return _get(cli, "posts", after=desde[:19], per_page=100,
                    _fields="id,date,link,title,content,featured_media,categories").json()
    except (FuenteError, ValueError):
        return []


def indice_al_dia(bajar_novedades=None) -> dict:
    """El índice guardado (archivo/indice.json, va en el repo) + lo que se publicó después de armarlo.
    Lo nuevo se suma en memoria; para guardarlo, `python -m archivo.fuente --indice`."""
    ind = cargar_indice()
    if not ind.get("hechos"):
        raise FuenteError("falta archivo/indice.json: correr `python -m archivo.fuente --indice`")
    nuevos = (bajar_novedades or novedades)(ind.get("armado") or "2000-01-01")
    if nuevos:
        extra = armar_indice(nuevos, [])
        ind["hechos"] = ind["hechos"] + extra["hechos"]
        ind["personajes"] = ind.get("personajes", []) + extra["personajes"]
        ind["curiosidades"] = ind.get("curiosidades", []) + extra["curiosidades"]
        ind["posts"] = {**ind.get("posts", {}), **extra["posts"]}
    return ind


# =============================================================================
# Consultas
# =============================================================================

def efemerides_de(ind: dict, dia: int, mes: int) -> list:
    return [h for h in ind.get("hechos") or [] if h["dia"] == dia and h["mes"] == mes]


def post_completo(post_id: int, cli: httpx.Client = None) -> dict:
    """{id, titulo, link, texto, foto} de un post o página (prueba los dos)."""
    cli = cli or _cliente()
    for ruta in ("posts", "pages"):
        try:
            r = _get(cli, f"{ruta}/{post_id}", _fields="id,link,title,content,featured_media")
        except FuenteError:
            continue
        p = r.json()
        return {"id": p["id"], "titulo": titulo(p), "link": p.get("link") or "",
                "texto": texto_plano((p.get("content") or {}).get("rendered") or ""),
                "foto": p.get("featured_media") or 0}
    raise FuenteError(f"no está el post {post_id}")


def url_foto(media_id: int, cli: httpx.Client = None) -> dict:
    """{url, ancho, alto} de la foto destacada (la versión grande), o {} si no hay."""
    if not media_id:
        return {}
    cli = cli or _cliente()
    try:
        d = _get(cli, f"media/{media_id}", _fields="source_url,media_details,mime_type").json()
    except (FuenteError, ValueError):
        return {}
    if not str(d.get("mime_type") or "").startswith("image/"):
        return {}
    det = d.get("media_details") or {}
    return {"url": d.get("source_url") or "", "ancho": det.get("width") or 0, "alto": det.get("height") or 0}


def buscar_posts(consulta: str, cli: httpx.Client = None, cuantos: int = 10) -> list:
    cli = cli or _cliente()
    try:
        return _get(cli, "search", search=consulta, per_page=cuantos, _fields="id,title,subtype").json()
    except (FuenteError, ValueError):
        return []


def bajar_foto(url: str, destino: Path, cli: httpx.Client = None) -> bool:
    cli = cli or _cliente()
    try:
        r = cli.get(url)
    except httpx.HTTPError:
        return False
    if r.status_code != 200 or len(r.content) < 5000:
        return False
    Path(destino).write_bytes(r.content)
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Índice del Archivo Literario")
    ap.add_argument("--indice", action="store_true", help="bajar el sitio entero y rearmar archivo/indice.json")
    ap.add_argument("--desde", help="armar el índice desde un volcado local (JSON con posts y pages)")
    ap.add_argument("--dia", help="mostrar las efemérides de un día, DD/MM")
    a = ap.parse_args()
    if a.indice or a.desde:
        if a.desde:
            d = json.loads(Path(a.desde).read_text(encoding="utf-8"))
            ind = armar_indice(d["posts"], d["pages"])
        else:
            ind = armar_indice(*bajar_todo())
        guardar_indice(ind)
        dias = {(h["dia"], h["mes"]) for h in ind["hechos"] if not h["sombrio"]}
        print(f"{len(ind['hechos'])} hechos ({len(dias)} días del año con alguno), "
              f"{len(ind['personajes'])} personajes, {len(ind['curiosidades'])} curiosidades")
    if a.dia:
        dd, mm = (int(x) for x in a.dia.split("/"))
        for h in efemerides_de(cargar_indice(), dd, mm):
            print(("[X] " if h["sombrio"] else "    ") + f"{h['anio']}: {h['textos'][0][:150]}")


if __name__ == "__main__":
    main()
