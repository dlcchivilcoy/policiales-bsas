# -*- coding: utf-8 -*-
"""LOS INFORMES DE LA FUNDACIÓN FADA en reels largos para @diarioyradioagro (26/11/2026).

Pedido del editor: «agregá esta página (https://fundacionfada.org/) para generar informes en reels interactivos para
diarioyradioagro» y después «en la pestaña de informes hacen cada 5 días informes con material audiovisual y texto,
podés usarlo para generar reels más extensos, utilizando todo el material posible, estirarlo hasta lo que más da un
reel (3 minutos); armalos y publicalos cada vez que sacan un informe nuevo».

De dónde sale: el listado https://fundacionfada.org/informes/ (el sitio es WordPress, pero sus tipos propios no salen
por la API ni por el RSS). De cada informe nuevo se junta TODO el material de texto:
  - la página del informe (título, fecha y descripción);
  - el PDF del informe (Google Drive o Dropbox): el resumen ejecutivo y lo que siga, hasta MATERIAL_MAX caracteres;
  - la gacetilla del mismo tema (https://fundacionfada.org/gacetillas/), con los números destacados.
Las gráficas y los videos de FADA quedan afuera: el reel es nuestro, con sus datos y la fuente a la vista.

El reel (motor de finde/video.py, la estética que eligió el editor: video del campo de fondo, pastilla con punto,
número gigante, voz y subtítulos): pregunta con tres opciones → la cifra → de 5 a 10 BLOQUES con los demás datos del
informe (un número cada uno, o una lista corta) → la pregunta para los comentarios → la placa final de agro. Hasta
~3 minutos (DURACION_MAX); Instagram lo toma como reel y Facebook, pasados los 90 s, como video de la página.

La IA (Gemini) arma la ficha SOLO con el material y después se controla: cada número de la respuesta, de los bloques,
de la narración y del texto del posteo tiene que estar en el material (`numeros_ausentes`); el bloque que no pasa se
saca y, si no queda lo mínimo, el informe se descarta y queda anotado. Las estimaciones y propuestas de FADA se
atribuyen («según FADA»).

Dónde y cuándo: Instagram y Facebook de @diarioyradioagro (sin colaboración), los DOMINGOS (FADA_DIAS_SEMANA) desde las
16:50: los informes de la semana (FADA_DIAS, 7), hasta FADA_POR_DIA (2), separados por ESPACIO_MIN (35) minutos. AGRO_FADA=0 lo apaga; AGRO_FADA_VENTANA («16:30-18:00»). Memoria: estado/agro_fada.json. Workflow:
.github/workflows/agro_fada.yml.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TZ_AR = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).resolve().parent.parent
MEMORIA = RAIZ / "estado" / "agro_fada.json"
SALIDA = RAIZ / "salida_agro"
INFORMES = "https://fundacionfada.org/informes/"
GACETILLAS = ("https://fundacionfada.org/gacetillas/", "https://fundacionfada.org/gacetillas/page/2/")
UA = {"User-Agent": "Mozilla/5.0 (compatible; DiarioLaCampana-agro/1.0; +https://www.xn--diariolacampaa-2nb.com.ar)"}
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
VIDEOS = ("campo", "cosecha", "trigo", "maiz", "ganado", "tambo", "maquinaria", "lluvia", "girasol", "pulverizacion")
MATERIAL_MAX = 14000          # caracteres del PDF que se le pasan a la IA (el resumen ejecutivo y lo que sigue)
DURACION_MAX = 170.0          # segundos (Instagram: un reel «de los largos»; el editor pidió hasta 3 minutos)
SEG_POR_PALABRA = 0.45        # para estimar cuánto dura cada bloque (sin voz, a ritmo de lectura)


def _var(nombre: str, defecto: str = "") -> str:
    return (os.environ.get(nombre) or defecto).strip()


def activo() -> bool:
    return _var("AGRO_FADA", "1") != "0"


def dias_max() -> int:
    try:
        return int(_var("FADA_DIAS", "7"))
    except ValueError:
        return 7


def dias_semana() -> set:
    """Los días que se fija si hay informes (0 = lunes … 6 = domingo). FADA_DIAS_SEMANA, de fábrica «6»."""
    try:
        return {int(x) for x in _var("FADA_DIAS_SEMANA", "6").split(",") if x.strip()}
    except ValueError:
        return {6}


def por_dia() -> int:
    try:
        return max(1, int(_var("FADA_POR_DIA", "2")))
    except ValueError:
        return 2


ESPACIO_MIN = 35              # entre dos informes del mismo domingo


def ventana(dia: date) -> tuple:
    a, b = _var("AGRO_FADA_VENTANA", "16:30-18:30").split("-")
    f = lambda s: datetime.combine(dia, datetime.strptime(s.strip(), "%H:%M").time(), TZ_AR)  # noqa: E731
    return f(a), f(b)


def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads((ruta or MEMORIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"informes": {}}


def guardar(mem: dict, ruta: Path = None) -> None:
    ruta = ruta or MEMORIA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    for k, _ in sorted(mem.get("informes", {}).items(), key=lambda kv: kv[1].get("cuando") or "")[:-200]:
        mem["informes"].pop(k, None)
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Consulta
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _get(url: str, binario: bool = False):
    import httpx
    r = httpx.get(url, headers=UA, timeout=90, follow_redirects=True)
    r.raise_for_status()
    return r.content if binario else r.content.decode("utf-8-sig", "replace")


def _plano(crudo: str) -> str:
    sin = re.sub(r"<script.*?</script>|<style.*?</style>", " ", crudo, flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", sin)).replace("﻿", "").split())


def _links(pagina: str, seccion: str) -> list:
    salida = []
    for u, slug in re.findall(rf'href="(https://fundacionfada\.org/{seccion}/([^"#?/]+)/)"', pagina):
        if slug not in ("feed", "page") and u not in salida:
            salida.append(u)
    return salida


def listar(get=None) -> list:
    """Las direcciones de los informes del listado (los más nuevos primero)."""
    return _links((get or _get)(INFORMES), "informes")


def _fecha(texto: str):
    m = re.search(r"(\d{1,2}) (" + "|".join(MESES) + r"),? (\d{4})", (texto or "").lower())
    if not m:
        return None
    try:
        return date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
    except ValueError:
        return None


def _titulo(crudo: str, plano: str) -> str:
    t = re.search(r"<title>(.*?)</title>", crudo, re.S)
    t = html.unescape(t.group(1)).split("|")[0].split(" – ")[0].strip() if t else ""
    if t and "Fundación FADA" not in t:
        return t
    m = re.search(r"Sumate (?:Informe|Gacetilla) (.+?) \d{1,2} (?:" + "|".join(MESES) + ")", plano)
    return m.group(1).strip() if m else t


def url_pdf(crudo: str) -> str:
    """La descarga directa del PDF del informe (Google Drive o Dropbox), o ""."""
    m = re.search(r'https://drive\.google\.com/file/d/([\w-]+)', crudo)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r'(https://www\.dropbox\.com/scl/fi/[^"\s]+?\.pdf[^"\s]*)', crudo)
    if m:
        u = html.unescape(m.group(1))
        u = re.sub(r"([?&])dl=0", r"\1dl=1", u)
        return u if "dl=1" in u else u + ("&" if "?" in u else "?") + "dl=1"
    return ""


def texto_pdf(url: str, get=None) -> str:
    """El texto del PDF, sin el índice, hasta MATERIAL_MAX caracteres ("" si no se pudo)."""
    if not url:
        return ""
    try:
        datos = (get or (lambda u: _get(u, binario=True)))(url)
        if not datos[:5].startswith(b"%PDF"):
            return ""
        from pypdf import PdfReader
        paginas = [(p.extract_text() or "") for p in PdfReader(io.BytesIO(datos)).pages]
    except Exception:                                # noqa: BLE001 — sin PDF, con la página y la gacetilla
        return ""
    texto = " ".join(" ".join(paginas).split())
    texto = re.sub(r"\.{4,}\s*\d+", " ", texto)       # las líneas de puntos del índice
    i = texto.lower().find("resumen ejecutivo", texto.lower().find("resumen ejecutivo") + 20)
    return texto[i if i > 0 else 0:][:MATERIAL_MAX]


def _palabras(t: str) -> set:
    from finde import datos as DA
    return {p for p in re.findall(r"[a-z0-9]+", DA.plano(t)) if len(p) > 3}


def gacetilla_de(titulo: str, get=None) -> str:
    """El texto de la gacetilla del mismo tema (la que comparte más palabras del título), o ""."""
    get = get or _get
    claves = _palabras(titulo)
    mejor, puntos = None, 0
    for u in GACETILLAS:
        try:
            for link in _links(get(u), "gacetillas"):
                n = len(claves & _palabras(link.rstrip("/").split("/")[-1].replace("-", " ")))
                if n > puntos:
                    mejor, puntos = link, n
        except Exception:                            # noqa: BLE001
            continue
    if not mejor or puntos < 1:
        return ""
    try:
        plano = _plano(get(mejor))
    except Exception:                                # noqa: BLE001
        return ""
    i = plano.find("Compartir en redes sociales")
    cuerpo = plano[i + 27:] if i >= 0 else plano
    for corte in ("Paquete de este informe", "Infografías de este Estudio", "Etiquetas:"):
        cuerpo = cuerpo.split(corte)[0]
    return re.sub(r"https?://\S+", " ", cuerpo)[:2500]


def leer(url: str, get=None) -> dict:
    """{url, slug, titulo, fecha, pagina, pdf, gacetilla, material}: todo el texto del informe."""
    get = get or _get
    crudo = get(url)
    plano = _plano(crudo)
    titulo = _titulo(crudo, plano)
    i = plano.find("Compartir en redes sociales")
    pagina = plano[i + 27:].split("Links #FADA")[0].split("Etiquetas:")[0][:1500] if i >= 0 else ""
    pdf = url_pdf(crudo)
    g = {"url": url, "slug": url.rstrip("/").split("/")[-1], "titulo": titulo,
         "fecha": _fecha(plano[max(0, i - 200):i + 5] if i >= 0 else plano[:3000]) or _fecha(plano),
         "pagina": pagina, "pdf": pdf}
    return g


def material(g: dict, get=None, get_pdf=None) -> str:
    g["texto_pdf"] = texto_pdf(g.get("pdf") or "", get_pdf)
    g["gacetilla"] = gacetilla_de(g["titulo"], get)
    partes = [f"INFORME: {g['titulo']} ({g.get('fecha')})", g.get("pagina") or "",
              "GACETILLA:\n" + g["gacetilla"] if g["gacetilla"] else "",
              "INFORME (PDF):\n" + g["texto_pdf"] if g["texto_pdf"] else ""]
    g["material"] = "\n\n".join(p for p in partes if p)
    return g["material"]


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Verificación de números
# ─────────────────────────────────────────────────────────────────────────────────────────────
def numeros(texto: str) -> set:
    """Los números de un texto, como floats («$58» → 58, «23%» → 23, «4,5» → 4.5, «1.234» → 1234)."""
    salida = set()
    for crudo in re.findall(r"\d[\d.,]*", texto or ""):
        t = crudo.rstrip(".,")
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
            t = t.replace(".", "")
        elif "," in t:
            t = t.replace(".", "").replace(",", ".")
        try:
            salida.add(float(t))
        except ValueError:
            continue
    return salida


def numeros_ausentes(textos: list, fuente: str, permitidos=()) -> list:
    """Los números de `textos` que no están en la fuente (ni en `permitidos`)."""
    hay = numeros(fuente) | {float(x) for x in permitidos}
    faltan = []
    for t in textos:
        for n in numeros(t):
            if not any(abs(n - h) < 0.051 for h in hay):
                faltan.append(f"{n:g} («{str(t)[:60]}»)")
    return faltan


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La ficha (IA + controles)
# ─────────────────────────────────────────────────────────────────────────────────────────────
SISTEMA = """Sos editor de datos de @diarioyradioagro (Chivilcoy, provincia de Buenos Aires). Te paso TODO el material
de un informe de la Fundación FADA (la página, la gacetilla y el texto del PDF). Armá UN reel largo, de pregunta y
respuesta y después los datos más fuertes del informe, para productores y gente del campo.

REGLAS DURAS:
- Usá SOLO números que aparezcan TAL CUAL en el material. No calcules, no redondees, no conviertas, no inventes.
- Lo que es estimación, proyección, propuesta u opinión de FADA va atribuido («según FADA», «FADA estima»).
- Las comparaciones van con el MISMO sentido y las mismas palabras del material: si dice «36% más caro que en EEUU»,
  es «36% más caro»; NUNCA la des vuelta («EEUU 36% más barato» es FALSO: no es la misma cuenta).
- "unidad" es solo "%", "" o una palabra («millones», «toneladas»); nunca signos sueltos como "+".
- Español rioplatense, claro y periodístico. Sin emojis.
- Si el material no trae números útiles, devolvé "apta": false con el motivo.

Devolvé SOLO este JSON:
{"apta": true, "motivo": "",
 "titulo": "título corto para la portada, máximo 30 caracteres",
 "volanta": "TEMA EN MAYÚSCULAS · FADA (máximo 34 caracteres)",
 "pregunta": "la pregunta en pantalla, máximo 110 caracteres",
 "gancho": "la pregunta para narrar, máximo 12 palabras",
 "respuesta": {"numero": 58, "dec": 0, "unidad": "%" o "" o " millones" etc., "texto": "qué es ese número, máximo 60 caracteres"},
 "revelacion": "una oración para narrar la respuesta, con el número",
 "bloques": [
   {"volanta": "SUBTEMA EN MAYÚSCULAS", "numero": 36, "dec": 0, "unidad": "%", "texto": "qué es, máximo 70 caracteres",
    "narracion": "una o dos oraciones para narrar este dato"},
   {"volanta": "SUBTEMA", "titulo": "título de la lista, máximo 40 caracteres", "filas": [["etiqueta", "valor con unidad"], ["…", "…"]],
    "narracion": "una o dos oraciones"}
 ],
 "cierre": "una pregunta para los comentarios relacionada con el informe, máximo 70 caracteres",
 "caption": ["párrafo 1 con el dato principal y la fuente", "párrafo 2", "párrafo 3 con lo que propone o advierte FADA"],
 "hashtags": ["#Agro", "...", "cinco en total"],
 "video": "uno de: campo, cosecha, trigo, maiz, ganado, tambo, maquinaria, lluvia, girasol, pulverizacion"}
Entre 6 y 10 bloques, cada uno con un dato DISTINTO (mezclá: la mayoría con un número y 1 o 2 listas de 2 a 4 filas
cuando el informe compara cosas). Ordenalos para contar una historia: el problema, los números, la comparación, lo que
propone FADA."""


def _sentido_dado_vuelta(textos: list, fuente: str) -> list:
    """Las frases que dicen «más barato/menos» con un número que el material usa con «más caro/más» (o al revés):
    una comparación dada vuelta no es la misma cuenta (26/11/2026: «EEUU 36% más barato» por «36% más caro»)."""
    from finde import datos as DA
    src = DA.plano(fuente)
    malos = []
    opuestos = (("mas barato", "mas caro"), ("mas caro", "mas barato"), ("menos", "mas"))
    for t in textos:
        tt = DA.plano(t)
        for n in re.findall(r"\d+(?:[.,]\d+)?", tt):
            for dice, original in opuestos:
                if re.search(rf"{re.escape(n)}\s*%?\s*{dice}", tt) and not re.search(rf"{re.escape(n)}\s*%?\s*{dice}", src) \
                        and re.search(rf"{re.escape(n)}\s*%?\s*{original}", src):
                    malos.append(f"«{t[:60]}» da vuelta «{n} {original}»")
    return malos


def _unidad(u) -> str:
    u = str(u or "").strip()
    if "%" in u:
        return "%"
    return u.strip("+-*").strip()


def _controlar_bloque(b: dict, fuente: str) -> list:
    textos = [b.get("texto", ""), b.get("narracion", ""), b.get("titulo", "")]
    if b.get("numero") is not None:
        textos.append(str(b["numero"]))
    textos += [f"{e} {v}" for e, v in (b.get("filas") or [])]
    return numeros_ausentes(textos, fuente) + _sentido_dado_vuelta(textos, fuente)


def ficha(g: dict, redactar=None, log=print) -> dict:
    """La ficha del reel largo para finde/video.py, o {"error": motivo}."""
    from finde import temas as T
    if redactar is None:
        from reels import ia as IA
        redactar = lambda s, m: IA.redactar(s, m, max_tokens=4000)[0]  # noqa: E731
    fuente = g["material"]
    try:
        j = redactar(SISTEMA, fuente)
    except Exception as e:                           # noqa: BLE001
        return {"error": f"IA: {type(e).__name__}: {str(e)[:160]}"}
    if not j.get("apta", True):
        return {"error": f"la IA lo descartó: {j.get('motivo') or 'sin motivo'}"}
    r = j.get("respuesta") or {}
    try:
        numero, dec = float(r["numero"]), int(r.get("dec") or 0)
    except (KeyError, TypeError, ValueError):
        return {"error": "la respuesta no es un número"}
    unidad = _unidad(r.get("unidad"))
    pct = unidad == "%"
    op, ok = T.opciones_de(numero, dec, unidad=" %" if pct else unidad, tope=100.0 if pct else max(numero * 3, 10),
                           paso=max(1.0, round(abs(numero) * 0.35, dec)), pos=T.posicion(g["slug"]))
    narr = {"gancho": j.get("gancho") or j.get("pregunta"),
            "opciones": ("¿" + ", ".join(op[:-1]) + " o " + op[-1] + "?").replace(" %", " por ciento"),
            "revelacion": j.get("revelacion") or "",
            "cierre": (j.get("cierre") or "") + " Contanos en los comentarios."}
    principal = [str(numero), r.get("texto", ""), narr["gancho"], narr["revelacion"], j.get("pregunta", "")]
    faltan = numeros_ausentes(principal, fuente) + _sentido_dado_vuelta(principal, fuente)
    if faltan:
        return {"error": "la respuesta trae números que no están en el informe: " + "; ".join(faltan[:3])}
    bloques = []
    for b in j.get("bloques") or []:
        if not b.get("narracion") or not (b.get("numero") is not None or b.get("filas")):
            continue
        mal = _controlar_bloque(b, fuente)
        if mal:
            log(f"   bloque afuera ({b.get('volanta')}): números que no están en el informe: {'; '.join(mal[:2])}")
            continue
        b["unidad"] = _unidad(b.get("unidad"))
        if b.get("numero") is not None:
            try:
                b["numero"] = float(b["numero"])
            except (TypeError, ValueError):
                continue
        bloques.append(b)
    # Que entre en DURACION_MAX: unos 30 s fijos (pregunta, opciones, cierre) más lo que se tarda en narrar cada bloque.
    total, elegidos = 32.0, []
    for b in bloques:
        dur = max(4.5, len(b["narracion"].split()) * SEG_POR_PALABRA + 1.2)
        if total + dur > DURACION_MAX:
            break
        elegidos.append(b)
        total += dur
    if len(elegidos) < 3 or not narr["revelacion"] or not j.get("cierre"):
        return {"error": f"quedaron {len(elegidos)} bloques verificados (mínimo 3) o la ficha vino incompleta"}
    caption_ok = [p for p in (j.get("caption") or [])[:3] if not numeros_ausentes([p], fuente)]
    fecha = g.get("fecha")
    hashtags = [h if h.startswith("#") else "#" + h for h in (j.get("hashtags") or [])][:5]
    for h in ("#Agro", "#FADA", "#Campo", "#Agroindustria"):
        if len(hashtags) < 5 and h not in hashtags:
            hashtags.append(h)
    return {
        "clave": f"fada_{g['slug']}"[:60], "dia": "fada", "titulo": (j.get("titulo") or g["titulo"])[:40],
        "territorio": "Argentina", "pregunta": j.get("pregunta") or narr["gancho"], "opciones": op, "correcta": ok,
        "respuesta": {"numero": numero, "dec": dec, "unidad": unidad, "texto": r.get("texto") or ""},
        "bloques": elegidos, "contexto": [], "cierre": j.get("cierre"), "narracion": narr,
        "volanta": (j.get("volanta") or "INFORME FADA").upper()[:40],
        "fuente_txt": f"Fuente: Fundación FADA · {fecha:%d/%m/%Y}" if fecha else "Fuente: Fundación FADA",
        "anio_txt": f"Fundación FADA · {g['titulo'][:40]}", "marca": ("El campo", "en datos"), "chip": "ARGENTINA",
        "cuentas": "@diarioyradioagro", "placa": "agro",
        # 26/11/2026, el editor: «hacelo sin voz» (AGRO_FADA_VOZ=1 la vuelve).
        "sin_voz": _var("AGRO_FADA_VOZ", "0") != "1",
        "video_tag": j.get("video") if j.get("video") in VIDEOS else "campo",
        "fuentes": [{"fuente": "Fundación FADA", "url": g["url"], "pdf": g.get("pdf") or "",
                     "anio_dato": fecha.year if fecha else "", "consultado": date.today().isoformat(),
                     "calculo": "cifras tal como las publica FADA"}],
        "caption": caption_ok, "hashtags": hashtags,
        "historia": {"pregunta": j.get("pregunta") or "", "opciones": op[:2], "correcta": None,
                     "dato": f"{op[ok]} (Fundación FADA)"},
    }


def caption(f: dict) -> str:
    partes = list(f["caption"]) + [f"📊 Fuente: Fundación FADA, informe «{f['anio_txt'].split(' · ', 1)[-1]}».",
                                   f"💬 {f['cierre']}", " ".join(f["hashtags"])]
    return "\n\n".join(p for p in partes if p)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Publicar y la corrida
# ─────────────────────────────────────────────────────────────────────────────────────────────
def pieza(f: dict, reel: dict, ahora: datetime) -> dict:
    g = {"titular": f["titulo"], "bajada": (f["caption"] or [""])[0][:200], "descripcion": caption(f),
         "hashtags": [], "titulo_web": "", "nota_web": "", "apta": True, "requires_review": False,
         "volanta": "El campo en datos"}
    return {"id": f"fada-{f['clave']}-{ahora:%Y%m%d}", "rep": {"url": f["fuentes"][0]["url"], "titulo": f["titulo"],
                                                              "fuente": "Fundación FADA"},
            "grupo": [], "score": {"subtema": "agro", "tema_doc": "fada", "ai_score": 0}, "guion": g,
            "formato": "reel", "youtube": False, "redes": ("facebook", "instagram"),
            "reel": {"archivo": reel["archivo"], "vista": reel["portada"], "duracion": reel["duracion"],
                     "ancho": reel["ancho"], "alto": reel["alto"]},
            "portada": reel["portada"], "imagen": {"origen": "datos"}, "colab_diario": False}


def publicar(p: dict, log=print) -> dict:
    from agro import publicar as PUB
    PUB.esperar_margen(log=log)
    return PUB.publicar_reel(p, None, ("facebook", "instagram"), log=log, portada_url=PUB._subir_portada(p))


def pendientes(mem: dict, hoy: date, listar_fn=None, leer_fn=None, log=print) -> list:
    """Los informes nuevos (no vistos, de los últimos dias_max() días), del más nuevo al más viejo."""
    salida = []
    for url in (listar_fn or listar)():
        slug = url.rstrip("/").split("/")[-1]
        if slug in mem["informes"]:
            continue
        try:
            g = (leer_fn or leer)(url)
        except Exception as e:                       # noqa: BLE001
            log(f"   {slug}: no se pudo leer ({type(e).__name__})")
            continue
        if not g.get("fecha") or (hoy - g["fecha"]).days > dias_max():
            mem["informes"][slug] = {"estado": "viejo", "fecha": str(g.get("fecha")), "titulo": g.get("titulo"),
                                     "cuando": datetime.now(TZ_AR).isoformat(timespec="minutes")}
            continue
        salida.append(g)
    return sorted(salida, key=lambda g: g["fecha"], reverse=True)


def corrida(publicar_: bool, ahora: datetime = None, ruta_mem: Path = None, log=print, listar_fn=None,
            leer_fn=None, material_fn=None, redactar=None, armar_video=None, publicador=None,
            forzar: bool = False, dormir=None) -> dict:
    """26/11/2026, el editor: «el de FADA que se fije los domingos»: corre los días de FADA_DIAS_SEMANA (domingo) y
    publica los informes de la semana (FADA_DIAS, 7), hasta FADA_POR_DIA (2), separados por ESPACIO_MIN."""
    import time
    dormir = dormir or time.sleep
    ahora = ahora or datetime.now(TZ_AR)
    inf = {"cuando": ahora.isoformat(timespec="minutes"), "publicar": publicar_, "estado": "", "piezas": []}
    if not activo():
        inf["estado"] = "apagado"
        return inf
    if publicar_ and not forzar:
        if ahora.weekday() not in dias_semana():
            inf["estado"] = "otro_dia"
            return inf
        desde, hasta = ventana(ahora.date())
        if not (desde - timedelta(minutes=20) <= ahora <= hasta):
            inf["estado"] = "fuera_de_hora"
            return inf
    mem = cargar(ruta_mem)
    hoy = ahora.date().isoformat()
    hechos = sum(1 for v in mem["informes"].values()
                 if v.get("estado") in ("publicado", "publicando") and (v.get("cuando") or "")[:10] == hoy)
    if publicar_ and hechos >= por_dia():
        inf["estado"] = "ya_salio_hoy"
        return inf
    ultimo = None
    for g in pendientes(mem, ahora.date(), listar_fn, leer_fn, log):
        if publicar_ and hechos >= por_dia():
            log(f"   «{g['titulo']}» queda para otro día (tope de {por_dia()} por día)")
            break
        log(f"FADA: «{g['titulo']}» ({g['fecha']}) — PDF: {'sí' if g.get('pdf') else 'no'}")
        (material_fn or material)(g)
        log(f"   material: {len(g['material'])} caracteres (PDF {len(g.get('texto_pdf') or '')}, gacetilla "
            f"{len(g.get('gacetilla') or '')})")
        f = ficha(g, redactar, log)
        if f.get("error"):
            log(f"   descartado: {f['error']}")
            mem["informes"][g["slug"]] = {"estado": "descartado", "motivo": f["error"][:200], "fecha": str(g["fecha"]),
                                          "titulo": g["titulo"], "cuando": ahora.isoformat(timespec="minutes")}
            continue
        carpeta = SALIDA / f"fada_{ahora:%Y-%m-%d}_{g['slug'][:40]}"
        if armar_video is None:
            from finde import video as V
            armar_video = V.armar
        reel = armar_video(f, carpeta, log=log)
        (carpeta / "texto.txt").write_text(caption(f), encoding="utf-8")
        (carpeta / "ficha.json").write_text(json.dumps(f, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        pz = {"clave": f["clave"], "titulo": f["titulo"], "carpeta": str(carpeta), "duracion": reel["duracion"],
              "bloques": len(f["bloques"])}
        inf["piezas"].append(pz)
        if not publicar_:
            pz["texto"] = caption(f)
            inf["estado"] = "simulado"
            return inf
        if ultimo is not None:                        # entre dos informes del mismo día, al menos ESPACIO_MIN
            falta = ESPACIO_MIN * 60 - (time.monotonic() - ultimo)
            if falta > 0:
                log(f"   esperando {falta / 60:.0f} min para el siguiente…")
                dormir(falta)
        registro = {"estado": "publicando", "fecha": str(g["fecha"]), "titulo": f["titulo"],
                    "cuando": datetime.now(TZ_AR).isoformat(timespec="minutes") if not forzar
                    else ahora.isoformat(timespec="minutes"), "duracion": reel["duracion"]}
        registro["cuando"] = hoy + registro["cuando"][10:]
        mem["informes"][g["slug"]] = registro           # ANTES de publicar: un reintento no lo repite
        guardar(mem, ruta_mem)
        res = (publicador or publicar)(pieza(f, reel, ahora), log=log)
        ultimo = time.monotonic()
        ok = [r for r in ("instagram", "facebook") if isinstance(res.get(r), dict) and res[r].get("id")]
        registro.update(estado="publicado" if ok else "fallo", redes=ok,
                        resultado={k: v for k, v in res.items() if k != "portada_url"})
        guardar(mem, ruta_mem)
        pz["redes"] = ok
        hechos += 1
    guardar(mem, ruta_mem)
    if not inf["piezas"]:
        inf["estado"] = "sin_novedades"
    elif any(not p.get("redes") for p in inf["piezas"]):
        inf["estado"] = "fallo"
    else:
        inf["estado"] = "ok"
    return inf


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--ya", action="store_true", help="sin mirar la franja horaria")
    a = ap.parse_args()
    inf = corrida(a.publicar, forzar=a.ya)
    print(f"## Reel de FADA — {inf.get('estado')}\n")
    for pz in inf.get("piezas") or []:
        print(f"- «{pz['titulo']}» ({pz['clave']}): {pz['duracion']} s, {pz['bloques']} bloques, redes "
              f"{pz.get('redes', '—')} → {pz['carpeta']}")
    if inf.get("estado") == "fallo":
        sys.exit(1)


if __name__ == "__main__":
    main()
