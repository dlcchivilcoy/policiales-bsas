# -*- coding: utf-8 -*-
"""AGRO / AgTech (@diarioyradioagro) — una pasada: arma la pieza y, con --publicar, la publica.

    venv\\Scripts\\python.exe -m agro.pasada --publicar       # PUBLICA (memoria real: estado/agro.json)
    venv\\Scripts\\python.exe -m agro.pasada                  # una pasada completa (simulada)
    venv\\Scripts\\python.exe -m agro.pasada --piezas 2       # arma como mucho 2 piezas (para probar)
    venv\\Scripts\\python.exe -m agro.pasada --sin-reel       # solo portadas (más rápido)
    venv\\Scripts\\python.exe -m agro.pasada --olvidar        # borra la memoria de la simulación

Circuito (documento «Proyecto Agro», 13/10/2026):
  CAPTURA (RSS) → DUPLICADOS (URL/título/huella + parecido + IA) → SCORE IA (solo título y bajada)
  → SELECCIÓN (≥ AGRO_SCORE_MIN, AGRO_MAX_DIA por día, mezcla por subtema) → TEXTO COMPLETO solo de
  las elegidas → REDACCIÓN (título, bajada, Instagram, web, guion del reel) → IMAGEN (foto de fuente
  oficial/prensa, si no IA) → PORTADA 9:16 → REEL → PLAN DE PUBLICACIÓN SIMULADO → informe HTML.

Sin --publicar NO publica. Con --publicar (activado el 14/10/2026) cada pieza apta y sin revisión
pendiente sale por agro/publicar.py: Short en Radio del Centro, nota en la sección Campo de la web y
reel en Facebook e Instagram de @diarioyradioagro con las credenciales AGRO_* (nunca las del diario).
Una pieza que queda retenida para revisión NO se publica: su lugar lo toma la siguiente.
Memorias separadas: la real en estado/agro.json (la commitea la nube), la de la simulación en
salida_agro/memoria_sim.json (fuera de git).
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import entorno  # noqa: E402
from agro import captura as CA  # noqa: E402
from agro import dedup as DD  # noqa: E402
from agro import fuentes as FU  # noqa: E402
from agro import guion as GU  # noqa: E402
from agro import imagen as IMG  # noqa: E402
from agro import informe as INF  # noqa: E402
from agro import portada as POR  # noqa: E402
from agro import scoring as SC  # noqa: E402
from agro import seleccion as SE  # noqa: E402
from reels import web as WEB  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salida_agro"
MEMORIA = SALIDA / "memoria_sim.json"
MEMORIA_REAL = RAIZ / "estado" / "agro.json"
TZ_AR = timezone(timedelta(hours=-3))
DIAS_MEMORIA = 7
DIAS_INDICE = 10                  # lo visto se recuerda 10 días (más que la ventana más larga, la de la Bolsa: 7)
DIAS_REPETIDA = 3                 # contra lo elegido estos días se busca la misma noticia
MINUTOS_ENTRE = 30                # si una pasada arma más de una pieza, entre una y otra
PENDIENTE_HORAS = 36              # una buena que no entró espera a las pasadas siguientes este tiempo
TOLERANCIA_MIN = 60               # una pasada que arranca hasta 1 h después de su horario es «esa»
MAX_REEMPLAZOS = 3                # piezas frenadas (copia, IA) que se reponen con la siguiente, por pasada

# Tableros automáticos («Precio del maíz en Rosario hoy 13 octubre 2026», «Dólar blue hoy…», «Clima
# en San Luis hoy…», «Riesgo país hoy 9 de octubre»): no son noticias, se descartan antes de gastar IA.
TABLERO = re.compile(r"\b(hoy|cotiza\w*|precio\w*)\b.*\b\d{1,2}\s+(de\s+)?(enero|febrero|marzo|abril|mayo|junio|"
                     r"julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b", re.I)


def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads((ruta or MEMORIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar(mem: dict, ahora: datetime, ruta: Path = None):
    ruta = ruta or MEMORIA
    mem["actualizado"] = datetime.now(TZ_AR).isoformat(timespec="seconds")   # tools/guardar_estado.combinar_agro
    limite = (ahora - timedelta(days=DIAS_MEMORIA)).isoformat()
    mem["elegidas"] = [p for p in mem.get("elegidas", []) if p.get("cuando", "") >= limite]
    DD.olvidar_viejas(mem, (ahora - timedelta(days=DIAS_INDICE)).strftime("%Y-%m-%d"))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=1), encoding="utf-8")


def es_tablero(n: dict) -> bool:
    return bool(TABLERO.search(n["titulo"]))


def turno(ahora: datetime) -> datetime:
    """El horario de pasada (AGRO_PASADAS) al que corresponde esta corrida: el que acaba de
    empezar (hasta TOLERANCIA_MIN después) o, si no, el próximo (mañana si ya pasaron todos)."""
    hoy = [ahora.replace(hour=h, minute=m, second=0, microsecond=0) for h, m in SE.pasadas()]
    for t in hoy:
        if t - timedelta(minutes=5) <= ahora <= t + timedelta(minutes=TOLERANCIA_MIN):
            return t
    futuros = [t for t in hoy if t > ahora]
    return futuros[0] if futuros else hoy[0] + timedelta(days=1)


def plan_horario(ahora: datetime, k: int) -> datetime:
    """Cuándo saldría la pieza k de esta pasada: en su turno (y 30 min entre una y otra)."""
    return turno(ahora) + timedelta(minutes=MINUTOS_ENTRE * k)


def pasada(max_piezas: int = 0, con_reel: bool = True, horas: int = 48, log=print, publicar: bool = False,
           publicador=None, fuera_de_cupo: bool = False) -> Path:
    entorno.cargar()
    t_ini = time.time()
    _log = log

    def log(msg):                                      # con los segundos desde que arrancó
        _log(f"[{time.time() - t_ini:5.0f} s] {msg}")
    ahora = datetime.now(TZ_AR)
    carpeta = SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = MEMORIA_REAL if publicar else MEMORIA
    mem = cargar(ruta_mem)
    mem.setdefault("scores", {})
    if publicar:
        con_reel = True                                # sin reel no hay qué publicar
        if publicador is None:
            from agro import publicar as PUB
            publicador = PUB.publicar
    conteos, descartadas = {}, []

    def descartar(n, motivo, s=None):
        descartadas.append({"fuente": n["fuente"], "titulo": n["titulo"], "url": n["url"], "motivo": motivo,
                            "score": (s or {}).get("ai_score", ""), "subtema": (s or {}).get("subtema", ""),
                            "explicacion": (s or {}).get("explicacion", ""), "dobles": (s or {}).get("dobles")})

    log(f"[agro] pasada {'REAL' if publicar else 'SIMULADA'} {ahora:%d/%m %H:%M} → {carpeta}")
    if publicar and not fuera_de_cupo:
        # Una publicación por horario: la corrida de respaldo (20 min después) o un doble disparo no
        # publican dos veces; fuera de los horarios de AGRO_PASADAS no se publica (salvo a mano,
        # con --fuera-de-cupo).
        t = turno(ahora)
        ya = [p for p in mem.get("elegidas", []) if p.get("turno") == t.isoformat() and p.get("publicado")]
        motivo = (f"fuera de horario: la próxima pasada es la de {t:%d/%m %H:%M}" if t > ahora + timedelta(minutes=5)
                  else f"la pasada de las {t:%H:%M} ya publicó: «{ya[0]['titular']}»" if ya else "")
        if motivo:
            log(f"No se publica: {motivo}")
            inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "conteos": {"No se publicó": motivo}, "fuentes": [],
                   "piezas": [], "descartadas": [], "grupos_duplicados": [], "publicar": publicar,
                   "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": horas}}
            (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding="utf-8")
            return INF.escribir(inf, carpeta)
    log("1) Captura")
    notas, inf_fuentes = CA.capturar(FU.activas(), ahora, horas_max=horas, log=log)
    conteos["Capturadas"] = len(notas)

    log("2) Duplicados exactos y tableros automáticos")
    nuevas = []
    for n in notas:
        motivo = DD.ya_vista(n, mem)
        if motivo:
            continue                                   # ya pasó por el circuito: ni se informa
        if es_tablero(n):
            descartar(n, "tablero automático (cotización, clima o dólar del día): no es una noticia")
            DD.anotar(n, mem)
            continue
        nuevas.append(n)
        DD.anotar(n, mem)
    conteos["Nuevas"] = len(nuevas)

    log(f"3) Agrupando {len(nuevas)} nuevas (palabras + IA)")
    limite = (ahora - timedelta(days=DIAS_REPETIDA)).isoformat()
    previas = [{"id": p["id"], "titulo": p["titulo_original"], "descripcion": p.get("descripcion", ""),
                "fuente": p.get("fuente", ""), "url": p.get("url", "")}
               for p in mem.get("elegidas", []) if p.get("cuando", "") >= limite]
    # Las pendientes (buenas que no entraron en una pasada anterior) también cuentan: si una nueva
    # cuenta lo mismo, ya está representada y espera su turno.
    lim_pend = (ahora - timedelta(hours=PENDIENTE_HORAS)).isoformat()
    ya_elegidas = {p["id"] for p in mem.get("elegidas", [])}
    pendientes = [p for p in mem.get("pendientes", []) if p.get("cuando", "") >= lim_pend and p["id"] not in ya_elegidas]
    previas += [{"id": p["id"], "titulo": p["rep"]["titulo"], "descripcion": p["rep"].get("descripcion", ""),
                 "fuente": p["rep"].get("fuente", ""), "url": p["rep"].get("url", "")} for p in pendientes]
    ag = DD.agrupar(nuevas, previas)
    if ag["ia"] is not True and ag["ia"] is not None:
        log(f"   la IA no agrupó ({ag['ia']}): quedan solo los grupos por palabras")
    for n in nuevas:
        if n["id"] in ag["repetidas"]:
            descartar(n, f"misma noticia que una ya elegida o pendiente: «{ag['repetidas'][n['id']]['titulo'][:80]}»")
    grupos = ag["grupos"]
    conteos["Noticias distintas"] = len(grupos)
    conteos["Agrupadas como duplicado"] = sum(len(g) - 1 for g in grupos) + len(ag["repetidas"])

    log(f"4) Puntaje de {len(grupos)} noticias (IA, título y bajada)")
    reps = [DD.representante(g) for g in grupos]
    puntajes = SC.puntuar(reps, mem["scores"], log=log)
    candidatos = []
    for g, r in zip(grupos, reps):
        s = puntajes.get(r["id"])
        if not s:
            descartar(r, "la IA no le puso puntaje (se reintenta la próxima pasada)")
            for n in g:                                # que vuelva a entrar la próxima vez
                mem.setdefault("indice", {"url": {}, "titulo": {}, "hash": {}})["url"].pop(n["canonical_url"], None)
                mem["indice"]["titulo"].pop(n["titulo_norm"], None)
                mem["indice"]["hash"].pop(n["hash"], None)
            continue
        candidatos.append({"id": r["id"], "rep": r, "grupo": g, "score": s, "cuando": ahora.isoformat(timespec="minutes")})
    conteos["Puntuadas"] = len(candidatos)
    candidatos += [dict(p, pendiente=True) for p in pendientes]
    conteos["Pendientes de pasadas anteriores"] = len(pendientes)
    conteos[f"Con ≥ {SE.score_min()}"] = sum(1 for c in candidatos if c["score"]["ai_score"] >= SE.score_min())

    log("5) Selección editorial")
    hoy = ahora.strftime("%Y-%m-%d")
    # Las frenadas (NO APTA) y las retenidas para revisión no ocupan lugar en el cupo del día.
    de_hoy = [p for p in mem.get("elegidas", []) if p.get("cuando", "").startswith(hoy)
              and p.get("apta", True) and not p.get("revision") and not p.get("fuera_de_cupo")]
    elegidos, desc = SE.elegir(candidatos, de_hoy)
    for c, motivo in desc:
        descartar(c["rep"], motivo, c["score"])
    por_cli = bool(max_piezas)
    max_piezas = max_piezas or SE.por_pasada()
    if len(elegidos) > max_piezas:
        for c in elegidos[max_piezas:]:
            descartar(c["rep"], f"límite de prueba de esta pasada (--piezas {max_piezas})" if por_cli else
                      f"queda pendiente para la próxima pasada ({max_piezas} por pasada)", c["score"])
        elegidos = elegidos[:max_piezas]
    conteos["Elegidas"] = len(elegidos)

    piezas, cola, probadas, reemplazos = [], list(elegidos), set(), 0

    def reponer(motivo_caida):
        """Si una pieza se frenó, su lugar lo toma la mejor de las que quedaron afuera, con las
        mismas reglas (score, mezcla, temas). Hasta MAX_REEMPLAZOS por pasada."""
        nonlocal reemplazos
        if reemplazos >= MAX_REEMPLAZOS:
            return
        ocupados = de_hoy + [{"score": p["score"]} for p in piezas
                             if p["guion"]["apta"] and not p["guion"]["requires_review"]] + \
            [{"score": x["score"]} for x in cola]
        pool = [x for x in candidatos if x["id"] not in probadas and all(x["id"] != y["id"] for y in cola)]
        nuevo, _ = SE.elegir(pool, ocupados)
        if not nuevo:
            return
        reemplazos += 1
        cola.append(nuevo[0])
        descartadas[:] = [d for d in descartadas if d["url"] != nuevo[0]["rep"]["url"]]
        log(f"   reemplazo ({motivo_caida}): entra {nuevo[0]['score']['ai_score']} · {nuevo[0]['rep']['titulo'][:60]}")

    k = -1
    while cola:
        c = cola.pop(0)
        k += 1
        probadas.add(c["id"])
        rep, s = c["rep"], c["score"]
        otras = [n for n in c["grupo"] if n["id"] != rep["id"]]
        log(f"6) [{k + 1}/{k + 1 + len(cola)}] {s['ai_score']} · {s['subtema']} · {rep['titulo'][:70]}")
        completo = CA.completar(rep)
        try:
            g = GU.generar(rep, completo.get("cuerpo", ""), otras, s)
        except Exception as e:                         # noqa: BLE001
            descartar(rep, f"la IA no pudo redactar ({type(e).__name__})", s)
            reponer("la IA no redactó")
            continue
        if not g["apta"]:
            reponer(g.get("motivo") or "no apta")
        elif publicar and g["requires_review"]:
            reponer("retenida para revisión")
        base = carpeta / f"{k + 1:02d}_{WEB.slugify(g['titular'] or rep['titulo'], 40)}"
        pieza = {"id": rep["id"], "rep": rep, "grupo": c["grupo"], "score": s, "guion": g}
        if g["apta"]:
            pieza["imagen"] = IMG.elegir(rep, completo.get("imagen", ""), g["prompt_imagen"],
                                         base.with_name(base.name + "_imagen.jpg"), subtema=s.get("subtema", ""))
            ia = pieza["imagen"]["origen"] == "ia"
            credito = pieza["imagen"].get("credito", "")
            pieza["portada"] = str(POR.armar(g, pieza["imagen"].get("archivo"), base.with_name(base.name + "_portada.jpg"),
                                             ia=ia, credito=credito))
            if con_reel:
                try:
                    t0 = time.time()
                    pieza["reel"] = GU_reel(g, pieza["imagen"].get("archivo"), base.with_suffix(".mp4"), ia, credito)
                    log(f"   reel {pieza['reel']['duracion']:.0f} s, {pieza['reel']['peso_kb']} KB ({time.time() - t0:.0f} s)")
                except Exception as e:                 # noqa: BLE001 — la portada queda igual
                    pieza["reel"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                    log(f"   el reel falló: {pieza['reel']['error']}")
                    if publicar:
                        reponer("el reel falló")
        slug = WEB.slugify(g.get("titulo_web") or g["titular"], 70)
        url_web = f"https://{WEB.SITIO}/n/{slug}"
        pieza["textos"] = {"Instagram (reel)": GU.texto_red(g, "instagram"),
                           "Facebook (reel)": GU.texto_red(g, "facebook", url_web),
                           "YouTube Shorts": f"{g['titular']}\n\n{GU.texto_red(g, 'youtube', url_web)}",
                           f"Web: {g.get('titulo_web')}": g.get("nota_web", "")}
        if g["requires_review"] or not g["apta"]:
            estado = "RETENIDA para revisión" if g["requires_review"] else "NO APTA"
            pieza["plan"] = {"Estado": estado, "Motivo": g.get("motivo_revision") or g.get("motivo")}
        else:
            hora = plan_horario(ahora, len([p for p in piezas if "Hora" in (p.get("plan") or {})]))
            pieza["plan"] = {"Hora": f"{hora:%d/%m %H:%M}", "YouTube Shorts": "reel + título + link a la nota",
                             "Web (sección Agro)": url_web, "Facebook @diarioyradioagro": "reel + texto + link",
                             "Instagram @diarioyradioagro": "reel + texto + 5 hashtags",
                             "Publicación automática": "SÍ" if publicar else "APAGADA (simulación)"}
        piezas.append(pieza)
        anotada = {
            "id": rep["id"], "cuando": ahora.isoformat(timespec="minutes"), "titulo_original": rep["titulo"],
            "descripcion": rep.get("descripcion", "")[:300], "fuente": rep["fuente"], "url": rep["url"],
            "titular": g["titular"], "score": s, "apta": g["apta"], "revision": g["requires_review"],
            "fuera_de_cupo": fuera_de_cupo, "turno": turno(ahora).isoformat() if publicar else ""}
        mem.setdefault("elegidas", []).append(anotada)
        if publicar and "Hora" in pieza["plan"] and (pieza.get("reel") or {}).get("archivo"):
            # Se anota ANTES de publicar: si la corrida se corta en el medio, la próxima no la repite.
            anotada["publicado"] = {"estado": "publicando"}
            guardar(mem, ahora, ruta_mem)
            log("   publicando…")
            res = publicador(pieza, log=log)
            anotada["publicado"] = pieza["publicado"] = res
            ok = [r for r, v in res.items() if isinstance(v, dict) and not v.get("error")]
            pieza["plan"]["Publicado en"] = ", ".join(ok) or "ninguna red"
            for r, v in res.items():
                if isinstance(v, dict) and v.get("error"):
                    pieza["plan"][f"Falló {r}"] = v["error"]
            guardar(mem, ahora, ruta_mem)
    conteos["Piezas armadas"] = sum(1 for p in piezas if p["guion"]["apta"])
    conteos["Reemplazos"] = reemplazos
    conteos["Retenidas para revisión"] = sum(1 for p in piezas if p["guion"]["requires_review"])

    # Las buenas que no se probaron esperan a las pasadas siguientes (hasta PENDIENTE_HORAS).
    mem["pendientes"] = [{k: c[k] for k in ("id", "rep", "grupo", "score", "cuando")}
                         for c in candidatos
                         if c["score"]["ai_score"] >= SE.score_min() and c["id"] not in probadas][:40]
    conteos["Quedan pendientes"] = len(mem["pendientes"])
    if publicar:
        conteos["Publicadas"] = sum(1 for p in piezas if p.get("publicado"))
    guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "conteos": conteos, "fuentes": inf_fuentes, "piezas": piezas,
           "descartadas": sorted(descartadas, key=lambda d: -(d["score"] or 0) if isinstance(d["score"], int) else 0),
           "grupos_duplicados": [{"notas": g, "como": ag["como"]} for g in grupos if len(g) > 1],
           "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": horas},
           "publicar": publicar}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    ruta = INF.escribir(inf, carpeta)
    log(f"Listo: {ruta}")
    return ruta


def GU_reel(g, imagen, salida, ia, credito=""):
    from agro import reel as RE
    return RE.armar(g, imagen, salida, ia=ia, credito=credito)


def main():
    entorno.consola_utf8()
    ap = argparse.ArgumentParser(description="Agro: arma la pieza; con --publicar, la publica")
    ap.add_argument("--publicar", action="store_true", help="publica de verdad (memoria estado/agro.json)")
    ap.add_argument("--fuera-de-cupo", action="store_true",
                    help="una corrida a mano que no ocupa lugar de las 3 del día (la primera, del 14/10)")
    ap.add_argument("--piezas", type=int, default=0, help="arma como mucho N piezas (0 = las que elija)")
    ap.add_argument("--sin-reel", action="store_true", help="solo portadas")
    ap.add_argument("--horas", type=int, default=48, help="antigüedad máxima de las notas")
    ap.add_argument("--olvidar", action="store_true", help="borra la memoria de la simulación y sale")
    a = ap.parse_args()
    if a.olvidar:
        MEMORIA.unlink(missing_ok=True)
        print("Memoria de la simulación borrada.")
        return 0
    ruta = pasada(a.piezas, not a.sin_reel, a.horas, publicar=a.publicar, fuera_de_cupo=a.fuera_de_cupo)
    inf = json.loads((ruta.parent / "informe.json").read_text(encoding="utf-8"))
    fallas = [f"{p['guion']['titular']}: {r}" for p in inf["piezas"] for r, v in (p.get("publicado") or {}).items()
              if isinstance(v, dict) and v.get("error")]
    if fallas:
        print("FALLARON:\n- " + "\n- ".join(fallas))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
