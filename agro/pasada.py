# -*- coding: utf-8 -*-
"""AGRO / AgTech (@diarioyradioagro) — una corrida de la agenda: con --publicar, publica todo lo de la
corrida (reel, una hora después el carrusel, y las historias si tocan), esperando cada horario.

    venv\\Scripts\\python.exe -m agro.pasada --publicar               # PUBLICA la corrida (estado/agro.json)
    venv\\Scripts\\python.exe -m agro.pasada --tipo reel              # simula un reel
    venv\\Scripts\\python.exe -m agro.pasada --tipo carrusel          # simula un carrusel
    venv\\Scripts\\python.exe -m agro.pasada --tipo historias --bloque cierre   # simula una tanda de historias
    venv\\Scripts\\python.exe -m agro.pasada --olvidar                # borra la memoria de la simulación

La agenda (agro/agenda.py, pedido del editor del 19/10/2026): 6 corridas por día (7, 10, 13, 16, 18 y 21 h),
cada una con 1 reel y 1 carrusel intercalados y 1 h entre posteo y posteo, + 3 tandas de historias.

REEL y CARRUSEL (documento «Proyecto Agro», 13/10/2026, y «ideas agro», 17/10/2026):
  CAPTURA (RSS) → DUPLICADOS (URL/título/huella + parecido + IA) → SCORE IA (título y bajada) →
  SELECCIÓN (≥ AGRO_SCORE_MIN, AGRO_MAX_DIA por día, urgentes primero, temas fundamentales, mezcla) →
  TEXTO COMPLETO solo de la elegida → REDACCIÓN (título, bajada, Instagram, web, guion) → IMAGEN (foto
  oficial con crédito, foto de medio RECREADA con IA, o IA) → REEL 4:5 o CARRUSEL «deslizá e informate».
  Los sábados, el primer carrusel es «Los números de la semana» (solo datos).
HISTORIAS: datos de granos, dólar, Chicago y clima (agro/mercado.py), sin IA (agro/historias.py).

Sin --publicar NO publica. Una pieza retenida para revisión NO se publica: su lugar lo toma la siguiente.
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
from agro import agenda as AG  # noqa: E402
from agro import captura as CA  # noqa: E402
from agro import dedup as DD  # noqa: E402
from agro import diseno as DIS  # noqa: E402
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
PENDIENTE_HORAS = 36              # una buena que no entró espera a las corridas siguientes este tiempo
MAX_REEMPLAZOS = 3                # piezas frenadas (copia, IA) que se reponen con la siguiente, por corrida

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
    mem["historias"] = {k: v for k, v in (mem.get("historias") or {}).items() if k >= limite}
    DD.olvidar_viejas(mem, (ahora - timedelta(days=DIAS_INDICE)).strftime("%Y-%m-%d"))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def es_tablero(n: dict) -> bool:
    return bool(TABLERO.search(n["titulo"]))


def turno(ahora: datetime):
    """(horario, tipo, en_horario) de la agenda (agro/agenda.py)."""
    return AG.turno(ahora)


def corrida(ahora: datetime):
    """(inicio, en_horario, [(horario, tipo), …]) de la corrida de `ahora` (agro/agenda.py)."""
    return AG.corrida(ahora)


def _ahora() -> datetime:
    return datetime.now(TZ_AR)


_dormir = time.sleep


def _esperar(hasta: datetime, log=print):
    """Duerme hasta `hasta` (la corrida espera el horario de su segundo posteo)."""
    falta = (hasta - _ahora()).total_seconds()
    if falta > 0:
        log(f"Esperando hasta las {hasta:%H:%M} ({falta / 60:.0f} min)…")
        _dormir(falta)


def _guardar_en_la_nube(log=print):
    """En la nube, entre un posteo y el siguiente, la memoria se sube al repo: si la máquina se cae
    mientras espera, el respaldo de 20 min después ya sabe lo que salió y no lo repite."""
    import os
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    for k, v in (("GIT_AUTHOR_NAME", "github-actions[bot]"), ("GIT_COMMITTER_NAME", "github-actions[bot]"),
                 ("GIT_AUTHOR_EMAIL", "41898282+github-actions[bot]@users.noreply.github.com"),
                 ("GIT_COMMITTER_EMAIL", "41898282+github-actions[bot]@users.noreply.github.com")):
        os.environ.setdefault(k, v)
    try:
        from tools import guardar_estado as GE
        msg = f"Agro de {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC [skip ci]"
        log(f"   memoria: {GE.guardar(msg, solo=['agro.json'])}")
    except Exception as e:                             # noqa: BLE001 — el paso final de la corrida la guarda igual
        log(f"   memoria: no se pudo subir ahora ({type(e).__name__}: {str(e)[:120]})")


def tema_siguiente(mem: dict) -> str:
    """El bloque del próximo posteo 4:5 (blanco o grafito): el otro del último que salió."""
    return DIS.tema_siguiente(mem.get("tema_ultimo", ""))


def ya_publicado(mem: dict, horario: datetime, tipo: str):
    """Lo que ya salió (o está saliendo) en ese horario, o None."""
    iso = horario.isoformat()
    if tipo == "historias":
        h = (mem.get("historias") or {}).get(iso)
        return h if h and h.get("publicado") else None
    return next((p for p in mem.get("elegidas", []) if p.get("turno") == iso and p.get("publicado")), None)


def _informe_vacio(carpeta: Path, ahora: datetime, motivo: str, publicar: bool, horas: int = 48) -> Path:
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "conteos": {"No se publicó": motivo}, "fuentes": [],
           "piezas": [], "descartadas": [], "grupos_duplicados": [], "publicar": publicar,
           "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": horas}}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding="utf-8")
    return INF.escribir(inf, carpeta)


def correr(publicar: bool = False, tipo: str = "", bloque: str = "", momento: datetime = None, log=print,
           publicador=None, fuera_de_cupo: bool = False, max_piezas: int = 0, con_reel: bool = True,
           horas: int = 48) -> Path:
    """La corrida del horario: con --publicar, todo lo de la corrida (correr_corrida); si no, una pieza
    de lo que toca a esta hora o de lo que pida `tipo` (simulación, o fuera de cupo)."""
    entorno.cargar()
    ahora = momento or _ahora()
    if publicar and not fuera_de_cupo:
        return correr_corrida(log=log, publicador=publicador, ahora=ahora, max_piezas=max_piezas,
                              con_reel=con_reel, horas=horas)
    carpeta = SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    carpeta.mkdir(parents=True, exist_ok=True)
    horario, tipo_ag, en_horario = turno(ahora)
    tipo = tipo or tipo_ag
    if not en_horario:
        horario = ahora.replace(second=0, microsecond=0)
    return _un_turno(publicar, tipo, horario, ahora, carpeta, bloque=bloque, log=log, publicador=publicador,
                     fuera_de_cupo=fuera_de_cupo, max_piezas=max_piezas, con_reel=con_reel, horas=horas)


def correr_corrida(log=print, publicador=None, ahora: datetime = None, max_piezas: int = 0,
                   con_reel: bool = True, horas: int = 48) -> list:
    """Publica la corrida de `ahora`, horario por horario y esperando cada uno (19/10/2026: reel, una
    hora después el carrusel; las historias en su horario). Lo que ya salió no se repite: el respaldo
    de 20 min después o un doble disparo no publican dos veces. Fuera de horario no publica nada (a
    mano: --fuera-de-cupo). Devuelve las rutas de los informes."""
    ahora = ahora or _ahora()
    inicio, en_horario, turnos = corrida(ahora)
    if not en_horario:
        carpeta = SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
        carpeta.mkdir(parents=True, exist_ok=True)
        log(f"No se publica: fuera de horario (la próxima corrida: {inicio:%d/%m %H:%M})")
        return [_informe_vacio(carpeta, ahora, f"fuera de horario: la próxima corrida es la de las "
                                               f"{inicio:%d/%m %H:%M}", True, horas)]
    log(f"[agro] CORRIDA de las {inicio:%H:%M}: " + ", ".join(f"{t:%H:%M} {tipo}" for t, tipo in turnos))
    rutas, errores, ultimo_feed, quedan = [], [], None, len(turnos)
    for horario, tipo in turnos:
        quedan -= 1
        ya = ya_publicado(cargar(MEMORIA_REAL), horario, tipo)
        if ya:
            que = ya.get("titular") or f"{len(ya.get('items') or [])} historias"
            log(f"{horario:%H:%M} {tipo}: ya publicó ({que})")
            if tipo != "historias":
                ultimo_feed = horario
            continue
        objetivo = horario
        if tipo != "historias" and ultimo_feed:
            # Una hora entre posteo y posteo del feed, aunque el primero haya salido tarde.
            objetivo = max(objetivo, ultimo_feed + timedelta(minutes=AG.MARGEN_MIN))
        _esperar(objetivo, log)
        momento = _ahora()
        if tipo != "historias":
            ultimo_feed = momento
        carpeta = SALIDA / f"{momento:%Y-%m-%d_%H%M}_{tipo}"
        carpeta.mkdir(parents=True, exist_ok=True)
        try:
            rutas.append(_un_turno(True, tipo, horario, momento, carpeta, log=log, publicador=publicador,
                                   max_piezas=max_piezas, con_reel=con_reel, horas=horas))
        except Exception as e:                         # noqa: BLE001 — una falla no se lleva el resto de la corrida
            log(f"{horario:%H:%M} {tipo}: FALLÓ ({type(e).__name__}: {str(e)[:200]})")
            errores.append(f"{horario:%H:%M} {tipo}: {type(e).__name__}: {str(e)[:200]}")
            continue
        if quedan:
            _guardar_en_la_nube(log)
    if errores:                                        # al final: que la corrida avise (issue)
        raise RuntimeError("; ".join(errores))
    if not rutas:
        carpeta = SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
        carpeta.mkdir(parents=True, exist_ok=True)
        rutas.append(_informe_vacio(carpeta, ahora, f"la corrida de las {inicio:%H:%M} ya publicó todo", True, horas))
    return rutas


def _un_turno(publicar: bool, tipo: str, horario: datetime, ahora: datetime, carpeta: Path, bloque: str = "",
              log=print, publicador=None, fuera_de_cupo: bool = False, max_piezas: int = 0,
              con_reel: bool = True, horas: int = 48) -> Path:
    """Una cosa de la agenda: una tanda de historias, el carrusel de los números o una pieza."""
    if tipo == "historias":
        return pasada_historias(publicar=publicar, horario=horario, bloque=bloque or AG.bloque(horario), log=log,
                                publicador=publicador, carpeta=carpeta, ahora=ahora)
    if tipo == "numeros" or (tipo == "carrusel" and AG.es_primer_carrusel_del_sabado(horario) and not max_piezas):
        return pasada_numeros(publicar=publicar, horario=horario, log=log, publicador=publicador,
                              carpeta=carpeta, ahora=ahora)
    return pasada(max_piezas, con_reel, horas, log=log, publicar=publicar, publicador=publicador,
                  fuera_de_cupo=fuera_de_cupo, formato=tipo or "reel", horario=horario, ahora=ahora, carpeta=carpeta)


def _con_reloj(log):
    t_ini = time.time()

    def _log(msg):                                     # con los segundos desde que arrancó
        log(f"[{time.time() - t_ini:5.0f} s] {msg}")
    return _log


def pasada(max_piezas: int = 0, con_reel: bool = True, horas: int = 48, log=print, publicar: bool = False,
           publicador=None, fuera_de_cupo: bool = False, formato: str = "reel", horario: datetime = None,
           ahora: datetime = None, carpeta: Path = None) -> Path:
    """Un reel o un carrusel de una noticia (por defecto 1, AGRO_POR_PASADA)."""
    entorno.cargar()
    log = _con_reloj(log)
    ahora = ahora or datetime.now(TZ_AR)
    horario = horario or ahora.replace(second=0, microsecond=0)
    carpeta = carpeta or SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = MEMORIA_REAL if publicar else MEMORIA
    mem = cargar(ruta_mem)
    mem.setdefault("scores", {})
    carrusel = formato == "carrusel"
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

    log(f"[agro] {formato.upper()} {'REAL' if publicar else 'SIMULADO'} {ahora:%d/%m %H:%M} → {carpeta}")
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
    # Las pendientes (buenas que no entraron en una corrida anterior) también cuentan: si una nueva
    # cuenta lo mismo, ya está representada y espera su turno.
    lim_pend = (ahora - timedelta(hours=PENDIENTE_HORAS)).isoformat()
    ya_elegidas = {p["id"] for p in mem.get("elegidas", [])}
    pendientes = [p for p in mem.get("pendientes", []) if p.get("cuando", "") >= lim_pend and p["id"] not in ya_elegidas]
    if pendientes and previas:
        # Una pendiente pudo quedar afuera de su grupo cuando se capturó: se la vuelve a comparar con lo
        # elegido estos días (17/10/2026: casi sale dos veces la noticia de los chips del Senasa).
        rp = DD.agrupar([p["rep"] for p in pendientes], previas)
        for p in [p for p in pendientes if p["rep"]["id"] in rp["repetidas"]]:
            descartar(p["rep"], f"pendiente que repite una ya elegida: «{rp['repetidas'][p['rep']['id']]['titulo'][:80]}»",
                      p["score"])
            pendientes.remove(p)
    previas += [{"id": p["id"], "titulo": p["rep"]["titulo"], "descripcion": p["rep"].get("descripcion", ""),
                 "fuente": p["rep"].get("fuente", ""), "url": p["rep"].get("url", "")} for p in pendientes]
    ag = DD.agrupar(nuevas, previas) if nuevas else {"grupos": [], "repetidas": {}, "como": {}, "ia": None}
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
    puntajes = SC.puntuar(reps, mem["scores"], log=log) if reps else {}
    candidatos = []
    for g, r in zip(grupos, reps):
        s = puntajes.get(r["id"])
        if not s:
            descartar(r, "la IA no le puso puntaje (se reintenta la próxima corrida)")
            for n in g:                                # que vuelva a entrar la próxima vez
                mem.setdefault("indice", {"url": {}, "titulo": {}, "hash": {}})["url"].pop(n["canonical_url"], None)
                mem["indice"]["titulo"].pop(n["titulo_norm"], None)
                mem["indice"]["hash"].pop(n["hash"], None)
            continue
        candidatos.append({"id": r["id"], "rep": r, "grupo": g, "score": s, "cuando": ahora.isoformat(timespec="minutes")})
    conteos["Puntuadas"] = len(candidatos)
    candidatos += [dict(p, pendiente=True) for p in pendientes]
    conteos["Pendientes de corridas anteriores"] = len(pendientes)
    conteos[f"Con ≥ {SE.score_min()}"] = sum(1 for c in candidatos if c["score"]["ai_score"] >= SE.score_min())

    log(f"5) Selección editorial ({formato})")
    hoy = ahora.strftime("%Y-%m-%d")
    # Las frenadas (NO APTA) y las retenidas para revisión no ocupan lugar en el cupo del día.
    de_hoy = [p for p in mem.get("elegidas", []) if p.get("cuando", "").startswith(hoy)
              and p.get("apta", True) and not p.get("revision") and not p.get("fuera_de_cupo")]
    elegidos, desc = SE.elegir(candidatos, de_hoy, formato=formato)
    if not elegidos and any("tope de" in m for _, m in desc):
        # Antes que dejar el horario vacío, se repite subtema con una que pase el mínimo.
        elegidos, desc = SE.elegir(candidatos, de_hoy, formato=formato, relajar=True)
        if elegidos:
            log(f"   sin variedad de temas: entra igual la mejor ({elegidos[0]['score']['subtema']})")
    for c, motivo in desc:
        descartar(c["rep"], motivo, c["score"])
    por_cli = bool(max_piezas)
    max_piezas = max_piezas or SE.por_pasada()
    if len(elegidos) > max_piezas:
        for c in elegidos[max_piezas:]:
            descartar(c["rep"], f"límite de prueba de esta corrida (--piezas {max_piezas})" if por_cli else
                      f"queda pendiente para la próxima corrida ({max_piezas} por corrida)", c["score"])
        elegidos = elegidos[:max_piezas]
    conteos["Elegidas"] = len(elegidos)

    piezas, cola, probadas, reemplazos = [], list(elegidos), set(), 0

    def reponer(motivo_caida):
        """Si una pieza se frenó, su lugar lo toma la mejor de las que quedaron afuera, con las
        mismas reglas (score, mezcla, temas). Hasta MAX_REEMPLAZOS por corrida."""
        nonlocal reemplazos
        if reemplazos >= MAX_REEMPLAZOS:
            return
        ocupados = de_hoy + [{"score": p["score"]} for p in piezas
                             if p["guion"]["apta"] and not p["guion"]["requires_review"]] + \
            [{"score": x["score"]} for x in cola]
        pool = [x for x in candidatos if x["id"] not in probadas and all(x["id"] != y["id"] for y in cola)]
        nuevo, _ = SE.elegir(pool, ocupados, formato=formato)
        if not nuevo:
            nuevo, _ = SE.elegir(pool, ocupados, formato=formato, relajar=True)
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
        base_previa = carpeta / f"{k + 1:02d}_previa"
        imagen_previa = None
        if not IMG.ia_activa():
            # Con AGRO_IMAGEN_IA=0 la foto se mira ANTES del guion: sin la original la pieza no sale.
            carpeta.mkdir(parents=True, exist_ok=True)
            imagen_previa = IMG.elegir(rep, completo.get("imagen", ""), "", base_previa.with_name(
                base_previa.name + "_imagen.jpg"), subtema=s.get("subtema", ""))
            if not imagen_previa.get("archivo"):
                descartar(rep, imagen_previa.get("motivo") or "sin foto real", s)
                reponer("sin foto real")
                continue
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
        pieza = {"id": rep["id"], "rep": rep, "grupo": c["grupo"], "score": s, "guion": g, "formato": formato}
        tema = tema_siguiente(mem)
        if g["apta"]:
            pieza["imagen"] = imagen_previa or IMG.elegir(rep, completo.get("imagen", ""), g["prompt_imagen"],
                                                          base.with_name(base.name + "_imagen.jpg"),
                                                          subtema=s.get("subtema", ""))
            origen = pieza["imagen"]["origen"]
            credito = pieza["imagen"].get("credito", "")
            leyenda = DIS.texto_leyenda(origen, credito)
            if carrusel:
                from agro import carrusel as CAR
                try:
                    cont = CAR.contenido(g, rep, completo.get("cuerpo", ""), log=log)
                    pieza["carrusel"] = {"contenido": cont, "archivos": CAR.armar(
                        g, cont, pieza["imagen"].get("archivo"), carpeta, base.name, tema, leyenda),
                        "caption": CAR.caption(g), "tema": tema}
                    pieza["portada"] = pieza["carrusel"]["archivos"][0]
                    log(f"   carrusel: {len(pieza['carrusel']['archivos'])} diapositivas ({cont.get('via')})")
                except Exception as e:                 # noqa: BLE001
                    pieza["carrusel"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                    log(f"   el carrusel falló: {pieza['carrusel']['error']}")
                    if publicar:
                        reponer("el carrusel falló")
            else:
                pieza["portada"] = str(POR.armar(g, pieza["imagen"].get("archivo"),
                                                 base.with_name(base.name + "_portada.jpg"),
                                                 credito=credito, origen=origen, tema=tema))
                if con_reel:
                    clip = _clip_de_la_fuente(rep, completo, base)
                    try:
                        t0 = time.time()
                        pieza["reel"] = GU_reel(g, pieza["imagen"].get("archivo"), base.with_suffix(".mp4"), origen,
                                                credito, clip=clip, tema=tema)
                        log(f"   reel {pieza['reel']['duracion']:.0f} s, {pieza['reel']['peso_kb']} KB "
                            f"({'con el video de la fuente, ' if clip else ''}{time.time() - t0:.0f} s)")
                    except Exception as e:             # noqa: BLE001 — la portada queda igual
                        pieza["reel"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                        log(f"   el reel falló: {pieza['reel']['error']}")
                        if publicar:
                            reponer("el reel falló")
        slug = WEB.slugify(g.get("titulo_web") or g["titular"], 70)
        url_web = f"https://{WEB.SITIO}/n/{slug}"
        if carrusel:
            from agro import carrusel as CAR
            pieza["textos"] = {"Instagram (carrusel)": CAR.caption(g),
                               "Facebook (fotos + link)": GU.texto_red(g, "facebook", url_web),
                               f"Web: {g.get('titulo_web')}": g.get("nota_web", "")}
        else:
            pieza["textos"] = {"Instagram (reel)": GU.texto_red(g, "instagram"),
                               "Facebook (reel)": GU.texto_red(g, "facebook", url_web),
                               "YouTube Shorts": f"{g['titular']}\n\n{GU.texto_red(g, 'youtube', url_web)}",
                               f"Web: {g.get('titulo_web')}": g.get("nota_web", "")}
        listo = bool((pieza.get("carrusel") or {}).get("archivos")) if carrusel else bool((pieza.get("reel") or {}).get("archivo"))
        if g["requires_review"] or not g["apta"]:
            estado = "RETENIDA para revisión" if g["requires_review"] else "NO APTA"
            pieza["plan"] = {"Estado": estado, "Motivo": g.get("motivo_revision") or g.get("motivo")}
        elif carrusel:
            pieza["plan"] = {"Hora": f"{horario:%d/%m %H:%M}", "Web (sección Agro)": url_web,
                             "Instagram @diarioyradioagro": f"carrusel de {len((pieza.get('carrusel') or {}).get('archivos') or [])} diapositivas + texto + hashtags",
                             "Facebook @diarioyradioagro": "las diapositivas como fotos + texto + link a la nota",
                             "Publicación automática": "SÍ" if publicar else "APAGADA (simulación)"}
        else:
            pieza["plan"] = {"Hora": f"{horario:%d/%m %H:%M}", "YouTube Shorts": "reel 4:5 + título + link a la nota",
                             "Web (sección Agro)": url_web, "Facebook @diarioyradioagro": "reel + texto + link",
                             "Instagram @diarioyradioagro": "reel 4:5 + texto + 5 hashtags",
                             "Publicación automática": "SÍ" if publicar else "APAGADA (simulación)"}
        piezas.append(pieza)
        anotada = {
            "id": rep["id"], "cuando": ahora.isoformat(timespec="minutes"), "titulo_original": rep["titulo"],
            "descripcion": rep.get("descripcion", "")[:300], "fuente": rep["fuente"], "url": rep["url"],
            "titular": g["titular"], "volanta": g.get("volanta", ""), "score": s, "apta": g["apta"],
            "revision": g["requires_review"], "fuera_de_cupo": fuera_de_cupo, "formato": formato,
            "turno": horario.isoformat() if publicar else ""}
        mem.setdefault("elegidas", []).append(anotada)
        if "Hora" in pieza["plan"] and listo:
            mem["tema_ultimo"] = tema
        if publicar and "Hora" in pieza["plan"] and listo:
            # Se anota ANTES de publicar: si la corrida se corta en el medio, la próxima no la repite.
            anotada["publicado"] = {"estado": "publicando"}
            guardar(mem, ahora, ruta_mem)
            log("   publicando…")
            res = publicador(pieza, log=log)
            anotada["portada_url"] = res.pop("portada_url", "") if isinstance(res, dict) else ""
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

    # Las buenas que no se probaron esperan a las corridas siguientes (hasta PENDIENTE_HORAS).
    mem["pendientes"] = [{k: c[k] for k in ("id", "rep", "grupo", "score", "cuando")}
                         for c in candidatos
                         if c["score"]["ai_score"] >= SE.score_min() and c["id"] not in probadas][:40]
    conteos["Quedan pendientes"] = len(mem["pendientes"])
    if publicar:
        conteos["Publicadas"] = sum(1 for p in piezas if p.get("publicado"))
    guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": formato, "conteos": conteos, "fuentes": inf_fuentes,
           "piezas": piezas,
           "descartadas": sorted(descartadas, key=lambda d: -(d["score"] or 0) if isinstance(d["score"], int) else 0),
           "grupos_duplicados": [{"notas": g, "como": ag["como"]} for g in grupos if len(g) > 1],
           "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": horas},
           "publicar": publicar}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    ruta = INF.escribir(inf, carpeta)
    log(f"Listo: {ruta}")
    return ruta


def _clip_de_la_fuente(rep: dict, completo: dict, base: Path):
    """El video de la nota, SOLO si la fuente es oficial o de prensa (INTA, Secretaría, BCR): el de un
    medio no se usa (no se puede recrear con IA y Meta detecta los videos de otros). None si no hay."""
    url = completo.get("video") or ""
    if not url or rep.get("tipo_fuente") not in ("oficial", "prensa"):
        return None
    try:
        from reels.flujo import _bajar_video
        clip = _bajar_video(url, base.with_name(base.name + "_clip.mp4"))
    except Exception:                                  # noqa: BLE001
        return None
    try:
        from reels import reel_bot as R
        return clip if clip and R.motor().duration_seconds(clip) >= 4 else None
    except Exception:                                  # noqa: BLE001
        return None


def GU_reel(g, imagen, salida, origen="ia", credito="", clip=None, tema="blanco"):
    from agro import reel as RE
    return RE.armar(g, imagen, salida, origen=origen, credito=credito, clip=clip, tema=tema)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Historias y el carrusel de los números de la semana
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _publicadas(mem: dict, desde: datetime) -> list:
    """Lo nuestro publicado desde `desde`, de lo más nuevo a lo más viejo."""
    lim = desde.isoformat(timespec="minutes")
    sal = [p for p in mem.get("elegidas", []) if p.get("cuando", "") >= lim and p.get("apta", True)
           and not p.get("revision") and p.get("publicado") and p["publicado"].get("estado") != "publicando"
           and any(isinstance(v, dict) and not v.get("error") for v in p["publicado"].values())]
    return sorted(sal, key=lambda p: p.get("turno") or p.get("cuando", ""), reverse=True)


def _bajar(url: str, destino: Path) -> str:
    if not url:
        return ""
    try:
        from reels.flujo import _bajar_foto
        return str(destino) if _bajar_foto(url, destino) else ""
    except Exception:                                  # noqa: BLE001
        return ""


def pasada_historias(publicar: bool, horario: datetime, bloque: str, log=print, publicador=None,
                     carpeta: Path = None, ahora: datetime = None) -> Path:
    from agro import historias as HI
    from agro import mercado as M
    log = _con_reloj(log)
    ahora = ahora or datetime.now(TZ_AR)
    carpeta = carpeta or SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    ruta_mem = MEMORIA_REAL if publicar else MEMORIA
    mem = cargar(ruta_mem)
    log(f"[agro] HISTORIAS «{bloque}» {'REALES' if publicar else 'SIMULADAS'} {ahora:%d/%m %H:%M} → {carpeta}")
    datos = M.leer_todo(mem, momento=ahora, log=log)
    hechas = _publicadas(mem, ahora - timedelta(hours=24))
    recientes = []
    for i, p in enumerate(hechas[:4]):
        recientes.append({"titular": p["titular"], "volanta": p.get("volanta", ""),
                          "imagen": _bajar(p.get("portada_url", ""), carpeta / f"reciente_{i}.jpg")})
    hoy = [p for p in hechas if (p.get("turno") or p.get("cuando", ""))[:10] == ahora.date().isoformat()]
    novedad = None
    if hoy:
        n = hoy[0]
        novedad = {"titular": n["titular"], "formato": n.get("formato", "reel"),
                   "portada": _bajar(n.get("portada_url", ""), carpeta / "novedad.jpg")}
    if bloque == "cierre" and ahora.weekday() >= 5:
        recientes = [r for r, p in zip(recientes, hechas) if p in hoy] or recientes
    alertas_ya = {i.get("clave") for h in (mem.get("historias") or {}).values()
                  if h.get("dia") == ahora.date().isoformat() for i in h.get("items") or []}
    tanda = HI.armar_tanda(bloque, datos, mem, carpeta, ahora, recientes, novedad, alertas_ya)
    log(f"   {len(tanda)} historias: {', '.join(t['tipo'] for t in tanda)}")
    registro = {"dia": ahora.date().isoformat(), "bloque": bloque, "items": [dict(t) for t in tanda]}
    mem.setdefault("historias", {})
    if publicar and tanda:
        if publicador is None:
            from agro import publicar as PUB
            publicador = PUB.publicar_historias
        registro["publicado"] = {"estado": "publicando"}
        mem["historias"][horario.isoformat()] = registro
        guardar(mem, ahora, ruta_mem)
        res = publicador(tanda, log=log)
        registro["publicado"] = {"estado": "listo", "resultado": res}
        for item, r in zip(registro["items"], res.get("items") or []):
            item["publicado"] = r
    else:
        mem["historias"][horario.isoformat()] = dict(registro, simulado=True) if not publicar else registro
    for it in registro["items"]:
        it.pop("archivo", None) if publicar else None
    guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "historias", "bloque": bloque,
           "conteos": {"Historias": len(tanda),
                       "Publicadas": sum(1 for t in registro["items"] if t.get("publicado") and not
                                         any((v or {}).get("error") for v in t["publicado"].values()))
                       if publicar else 0},
           "historias": tanda, "fuentes": [], "piezas": [], "descartadas": [], "grupos_duplicados": [],
           "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": 0}, "publicar": publicar,
           "resultado": registro.get("publicado")}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)


def pasada_numeros(publicar: bool, horario: datetime, log=print, publicador=None, carpeta: Path = None,
                   ahora: datetime = None) -> Path:
    """Sábado: el carrusel «Los números de la semana» (solo datos, sin IA)."""
    from agro import carrusel as CAR
    from agro import mercado as M
    log = _con_reloj(log)
    ahora = ahora or datetime.now(TZ_AR)
    carpeta = carpeta or SALIDA / ahora.strftime("%Y-%m-%d_%H%M")
    ruta_mem = MEMORIA_REAL if publicar else MEMORIA
    mem = cargar(ruta_mem)
    log(f"[agro] CARRUSEL «Los números de la semana» {'REAL' if publicar else 'SIMULADO'} {ahora:%d/%m %H:%M}")
    datos = M.leer_todo(mem, momento=ahora, log=log)
    tema = tema_siguiente(mem)
    # La tapa es una imagen IA del banco: con AGRO_IMAGEN_IA=0 este carrusel no sale y va uno de noticia.
    imagen = IMG.del_banco("mercados", ahora.date().isoformat()) if IMG.ia_activa() else ""
    r = CAR.numeros_semana(mem, datos, carpeta, ahora.date(), imagen, tema) if imagen else None
    if not r:
        log("   sin foto real para la tapa o sin datos suficientes: va un carrusel de noticia")
        guardar(mem, ahora, ruta_mem)
        return pasada(log=log, publicar=publicar, publicador=publicador, formato="carrusel", horario=horario,
                      ahora=ahora, carpeta=carpeta)
    g = {"titular": r["titular"], "volanta": "Los números de la semana", "bajada": "", "descripcion": r["caption"],
         "hashtags": [], "titulo_web": "", "nota_web": "", "apta": True, "requires_review": False}
    pieza = {"id": f"semana-{ahora:%Y%m%d}", "rep": {"url": "", "fuente": "datos", "titulo": r["titular"]},
             "grupo": [], "score": {"ai_score": "", "subtema": "mercados", "tema": "números de la semana"},
             "guion": g, "formato": "carrusel", "datos": True, "portada": r["archivos"][0],
             "carrusel": {"archivos": r["archivos"], "caption": r["caption"], "contenido": r["contenido"], "tema": tema},
             "plan": {"Hora": f"{horario:%d/%m %H:%M}", "Instagram": "carrusel de datos",
                      "Facebook": "las diapositivas como fotos"}}
    anotada = {"id": pieza["id"], "cuando": ahora.isoformat(timespec="minutes"), "titulo_original": r["titular"],
               "fuente": "datos", "url": "", "titular": r["titular"], "volanta": "Los números de la semana",
               "score": pieza["score"], "apta": True, "revision": False, "fuera_de_cupo": True, "formato": "carrusel",
               "turno": horario.isoformat() if publicar else ""}
    mem.setdefault("elegidas", []).append(anotada)
    mem["tema_ultimo"] = tema
    if publicar:
        if publicador is None:
            from agro import publicar as PUB
            publicador = PUB.publicar
        anotada["publicado"] = {"estado": "publicando"}
        guardar(mem, ahora, ruta_mem)
        res = publicador(pieza, log=log)
        anotada["portada_url"] = res.pop("portada_url", "") if isinstance(res, dict) else ""
        anotada["publicado"] = pieza["publicado"] = res
    guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "carrusel", "conteos": {"Diapositivas": len(r["archivos"])},
           "fuentes": [], "piezas": [], "carrusel_datos": pieza, "descartadas": [], "grupos_duplicados": [],
           "config": {"score_min": SE.score_min(), "max_dia": SE.max_dia(), "horas": 0}, "publicar": publicar}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)


def main():
    entorno.consola_utf8()
    ap = argparse.ArgumentParser(description="Agro: la corrida del horario; con --publicar, la publica")
    ap.add_argument("--publicar", action="store_true", help="publica de verdad (memoria estado/agro.json)")
    ap.add_argument("--tipo", choices=AG.TIPOS + ("numeros",), default="",
                    help="qué armar (simulación o --fuera-de-cupo); «numeros» = el carrusel «Los números de la semana»")
    ap.add_argument("--bloque", choices=AG.BLOQUES, default="", help="qué tanda de historias (simulación)")
    ap.add_argument("--fuera-de-cupo", action="store_true",
                    help="una corrida a mano que no ocupa lugar en la agenda del día")
    ap.add_argument("--piezas", type=int, default=0, help="arma como mucho N piezas (0 = las que elija)")
    ap.add_argument("--sin-reel", action="store_true", help="solo portadas")
    ap.add_argument("--horas", type=int, default=48, help="antigüedad máxima de las notas")
    ap.add_argument("--olvidar", action="store_true", help="borra la memoria de la simulación y sale")
    a = ap.parse_args()
    if a.olvidar:
        MEMORIA.unlink(missing_ok=True)
        print("Memoria de la simulación borrada.")
        return 0
    if a.fuera_de_cupo and not a.tipo:
        ap.error("--fuera-de-cupo necesita --tipo")
    ruta = correr(publicar=a.publicar, tipo=a.tipo, bloque=a.bloque, fuera_de_cupo=a.fuera_de_cupo,
                  max_piezas=a.piezas, con_reel=not a.sin_reel, horas=a.horas)
    fallas = []
    for r in (ruta if isinstance(ruta, list) else [ruta]):
        inf = json.loads((r.parent / "informe.json").read_text(encoding="utf-8"))
        fallas += [f"{p['guion']['titular']}: {red}" for p in inf["piezas"]
                   for red, v in (p.get("publicado") or {}).items() if isinstance(v, dict) and v.get("error")]
        for h in (inf.get("resultado") or {}).get("resultado", {}).get("items", []) if inf.get("resultado") else []:
            fallas += [f"historia: {red}: {v['error']}" for red, v in (h or {}).items()
                       if isinstance(v, dict) and v.get("error")]
    if fallas:
        print("FALLARON:\n- " + "\n- ".join(fallas))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
