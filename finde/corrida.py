# -*- coding: utf-8 -*-
"""LA CORRIDA de los reels del fin de semana: generar para revisar y publicar.

    python -m finde.corrida --generar [--dia sabado|domingo|finde] [--tema CLAVE] [--fecha AAAA-MM-DD]
    python -m finde.corrida --publicar [--dia sabado|domingo] [--tema CLAVE]

GENERAR (viernes a la noche, para revisar): elige el tema de cada día del próximo fin de semana, arma el reel y deja
la carpeta con los ocho entregables en salida_finde/<fecha>_<tema>/; anota el plan en estado/finde.json. El workflow
sube las carpetas como artefacto y abre un aviso (issue) para revisarlas.

PUBLICAR (sábado y domingo, cron-job.org a las 18:40): toma el tema del plan (o lo elige), lo vuelve a armar (mismo
resultado), espera a la hora (FINDE_HORA, «19:00») y lo publica: Instagram de @diarioyradioagro con @diarioyradio de
COLABORADOR (la colaboración se acepta sola con la cuenta del diario: es la dirección que anda; la inversa, Instagram
la rechaza desde el 19/11), y las páginas de Facebook de agro y del diario. Queda anotado ANTES de publicar: un
reintento no lo repite.

Interruptores: FINDE=0 apaga todo; la publicación necesita además la variable FINDE_PUBLICAR=1 del repo (o
publicar=si a mano): se habilita aparte de la generación. FINDE_VENTANA («18:30-20:30»): fuera de esa franja no
publica. FINDE_COLAB=0 sale sin colaboración. FINDE_FB_DIARIO=0 sin la copia en la página del diario.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from finde import datos as DA
from finde import temas as T

TZ_AR = timezone(timedelta(hours=-3))
RAIZ = DA.RAIZ
MEMORIA = RAIZ / "estado" / "finde.json"
HORA_DEFECTO = "19:00"
VENTANA_DEFECTO = "18:30-20:30"


def _var(nombre: str, defecto: str = "") -> str:
    return (os.environ.get(nombre) or defecto).strip()


def activo() -> bool:
    return _var("FINDE", "1") != "0"


def hora(dia: date) -> datetime:
    h, m = (int(x) for x in _var("FINDE_HORA", HORA_DEFECTO).split(":"))
    return datetime.combine(dia, datetime.min.time(), TZ_AR).replace(hour=h, minute=m)


def ventana(dia: date) -> tuple:
    a, b = _var("FINDE_VENTANA", VENTANA_DEFECTO).split("-")
    f = lambda s: datetime.combine(dia, datetime.strptime(s.strip(), "%H:%M").time(), TZ_AR)  # noqa: E731
    return f(a), f(b)


def cargar(ruta: Path = None) -> dict:
    try:
        return json.loads((ruta or MEMORIA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"historial": [], "plan": {}}


def guardar(mem: dict, ruta: Path = None) -> None:
    ruta = ruta or MEMORIA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    mem["historial"] = mem.get("historial", [])[-120:]
    ruta.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")


def proximo_finde(hoy: date) -> dict:
    """{"sabado": fecha, "domingo": fecha} del fin de semana que viene (el de hoy si ya es sábado o domingo)."""
    sab = hoy + timedelta(days=(5 - hoy.weekday()) % 7)
    if hoy.weekday() == 6:
        sab = hoy - timedelta(days=1)
    return {"sabado": sab, "domingo": sab + timedelta(days=1)}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Entregables
# ─────────────────────────────────────────────────────────────────────────────────────────────
def caption(f: dict) -> str:
    partes = list(f["caption"])
    fu = f["fuentes"][0]
    partes.append(f"📊 Fuente: {fu['fuente']}. Dato de {fu['anio_dato']}.")
    partes.append(" ".join(f["hashtags"]))
    return "\n\n".join(p for p in partes if p)


def guion(f: dict, reel: dict) -> str:
    esc = {n: (a, b) for n, a, b in reel.get("escenas") or []}
    renglones = [f"GUION — {f['titulo']} ({f['dia']}, tema «{f['clave']}»)", ""]
    for n in ("gancho", "opciones", "revelacion", "mapa", "contexto", "cierre"):
        a, b = esc.get(n, (0, 0))
        renglones.append(f"[{a:05.1f} s · {n.upper()} · {b:.1f} s] {f['narracion'].get(n, '')}")
    renglones += ["", f"Pregunta en pantalla: {f['pregunta']}",
                  "Opciones: " + " / ".join(f"{'ABC'[i]}) {o}" + (" ✔" if i == f['correcta'] else "")
                                            for i, o in enumerate(f['opciones'])),
                  f"Cierre: {f['cierre']}"]
    return "\n".join(renglones) + "\n"


def fuentes_md(f: dict) -> str:
    r = [f"# Fuentes — {f['titulo']}", ""]
    for fu in f["fuentes"]:
        r += [f"- **{fu['fuente']}**", f"  - Archivo: {fu['url']}"]
        if fu.get("cuadro"):
            r.append(f"  - Cuadro: {fu['cuadro']}")
        if fu.get("dato"):
            r.append(f"  - Dato: {fu['dato']}")
        r += [f"  - Página: {fu.get('pagina', '')}", f"  - Año del dato: {fu['anio_dato']}",
              f"  - Consultado: {fu.get('consultado', '')}", f"  - Cálculo: {fu['calculo']}"]
    r += ["", f"Territorio: {f['territorio']}. Comparación: los partidos de la zona, mismo indicador y período.",
          "Controles: " + ("ninguno falló." if not T.verificar(f) else "; ".join(T.verificar(f)))]
    return "\n".join(r) + "\n"


def historia_txt(f: dict) -> str:
    h = f["historia"]
    r = [f"HISTORIA COMPLEMENTARIA (encuesta para publicar a mano en Instagram)", "",
         f"Pregunta: {h['pregunta']}", "Opciones: " + " / ".join(h["opciones"])]
    if h.get("correcta") is not None:
        r.append(f"Respuesta correcta: {h['opciones'][h['correcta']]}")
    r += [f"Dato para la historia siguiente: {h['dato']}", "Sticker sugerido: «Encuesta» con las dos opciones; "
          "al otro día, la respuesta con el link al reel."]
    return "\n".join(r) + "\n"


def entregables(f: dict, carpeta: Path, reel: dict) -> list:
    (carpeta / "descripcion.txt").write_text(caption(f), encoding="utf-8")
    (carpeta / "guion.txt").write_text(guion(f, reel), encoding="utf-8")
    (carpeta / "fuentes.md").write_text(fuentes_md(f), encoding="utf-8")
    (carpeta / "historia.txt").write_text(historia_txt(f), encoding="utf-8")
    datos = {k: v for k, v in f.items()}
    datos["reel"] = reel
    (carpeta / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str),
                                        encoding="utf-8")
    return sorted(p.name for p in carpeta.iterdir() if p.is_file())


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Armar y publicar
# ─────────────────────────────────────────────────────────────────────────────────────────────
def fichas(dia: str, log=print) -> dict:
    if dia == "sabado":
        return T.disponibles("sabado", censo=DA.censo(DA.zona(), log=log), log=log)
    return T.disponibles("domingo", af=DA.argenfields(), log=log)


def armar(dia: str, fecha: date, mem: dict, tema: str = "", log=print, armar_video=None) -> dict:
    """{"ficha", "carpeta", "reel", "archivos"} del reel de ese día (o {"error"}). Deja el registro de la ejecución
    en la carpeta (registro.txt) y en salida_finde/registro.log."""
    lineas = []

    def anotar(*x):
        texto = " ".join(str(y) for y in x)
        lineas.append(f"{datetime.now(TZ_AR):%Y-%m-%d %H:%M:%S} {texto}")
        log(texto)

    a = _armar(dia, fecha, mem, tema, anotar, armar_video)
    DA.SALIDA.mkdir(parents=True, exist_ok=True)
    with open(DA.SALIDA / "registro.log", "a", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    if a.get("carpeta"):
        (a["carpeta"] / "registro.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
        a["archivos"] = sorted(set(a.get("archivos", [])) | {"registro.txt"})
    return a


def _armar(dia: str, fecha: date, mem: dict, tema: str, log, armar_video) -> dict:
    disponibles = fichas(dia, log)
    clave = tema or (mem.get("plan") or {}).get(fecha.isoformat()) or T.elegir(dia, disponibles,
                                                                                mem.get("historial", []), fecha)
    if not clave or clave not in disponibles:
        return {"error": f"sin tema verificable para el {dia} (pedido: {clave or '—'}; con datos: "
                         f"{', '.join(disponibles) or 'ninguno'})"}
    f = disponibles[clave]
    carpeta = DA.SALIDA / f"{fecha.isoformat()}_{clave}"
    log(f"Reel del {dia} {fecha:%d/%m}: «{f['titulo']}» ({clave}) → {carpeta}")
    if armar_video is None:
        from finde import video as V
        armar_video = V.armar
    reel = armar_video(f, carpeta, log=log)
    archivos = entregables(f, carpeta, reel)
    log(f"   listo: {reel['duracion']} s, {reel['peso_kb']} KB, voz {reel.get('voz')}; archivos: {', '.join(archivos)}")
    return {"ficha": f, "clave": clave, "carpeta": carpeta, "reel": reel, "archivos": archivos}


def pieza(a: dict, ahora: datetime) -> dict:
    f, reel = a["ficha"], a["reel"]
    texto = caption(f)
    g = {"titular": f["titulo"], "bajada": f["caption"][0][:200], "descripcion": texto, "hashtags": [],
         "titulo_web": "", "nota_web": "", "apta": True, "requires_review": False, "volanta": "Chivilcoy en datos"}
    return {"id": f"finde-{f['clave']}-{ahora:%Y%m%d}", "rep": {"url": "", "titulo": f["titulo"],
                                                                "fuente": f["fuentes"][0]["fuente"]},
            "grupo": [], "score": {"subtema": "agro", "tema_doc": "finde", "ai_score": 0}, "guion": g,
            "formato": "reel", "youtube": False, "redes": ("facebook", "instagram"),
            "reel": {"archivo": reel["archivo"], "vista": reel["portada"], "duracion": reel["duracion"],
                     "ancho": reel["ancho"], "alto": reel["alto"]},
            "portada": reel["portada"], "imagen": {"origen": "datos"},
            "colab_diario": _var("FINDE_COLAB", "1") != "0"}


def publicar(p: dict, log=print, publicar_reel=None, aceptar=None, fb_del_diario=None) -> dict:
    from agro import publicar as PUB
    from agro import reel_zona as RZ
    PUB.esperar_margen(log=log)
    publicar_reel = publicar_reel or PUB.publicar_reel
    res = publicar_reel(p, None, ("facebook", "instagram"), log=log, portada_url=PUB._subir_portada(p))
    ig = res.get("instagram") or {}
    if ig.get("id") and ig.get("colab") == "si":
        try:
            res["colab"] = (aceptar or PUB.aceptar_colab)(ig["id"], log=log)
        except Exception as e:                       # noqa: BLE001 — la colab se acepta a mano si hace falta
            res["colab"] = {"estado": "pendiente", "detalle": f"{type(e).__name__}: {str(e)[:200]}"}
    if _var("FINDE_FB_DIARIO", "1") != "0":
        try:
            res["facebook_diario"] = (fb_del_diario or RZ._facebook_diario)(p, log)
        except Exception as e:                       # noqa: BLE001
            res["facebook_diario"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook del diario FALLÓ: {res['facebook_diario']['error']}")
    return res


def generar(dias: list, hoy: date, tema: str = "", ruta_mem: Path = None, log=print, armar_fn=None) -> dict:
    mem = cargar(ruta_mem)
    fechas = proximo_finde(hoy)
    inf = {"modo": "generar", "piezas": []}
    for dia in dias:
        fecha = fechas[dia]
        a = (armar_fn or armar)(dia, fecha, mem, tema, log)
        if a.get("error"):
            log(f"   {a['error']}")
            inf["piezas"].append({"dia": dia, "fecha": fecha.isoformat(), "error": a["error"]})
            continue
        mem.setdefault("plan", {})[fecha.isoformat()] = a["clave"]
        mem["historial"].append({"fecha": fecha.isoformat(), "dia": dia, "clave": a["clave"], "estado": "generado",
                                 "carpeta": str(a["carpeta"].relative_to(RAIZ)) if str(a["carpeta"]).startswith(
                                     str(RAIZ)) else str(a["carpeta"]),
                                 "duracion": a["reel"]["duracion"], "voz": a["reel"].get("voz"),
                                 "cuando": datetime.now(TZ_AR).isoformat(timespec="minutes")})
        inf["piezas"].append({"dia": dia, "fecha": fecha.isoformat(), "clave": a["clave"],
                              "titulo": a["ficha"]["titulo"], "carpeta": str(a["carpeta"]),
                              "duracion": a["reel"]["duracion"], "archivos": a["archivos"]})
    guardar(mem, ruta_mem)
    return inf


def publicar_hoy(ahora: datetime, tema: str = "", ruta_mem: Path = None, log=print, armar_fn=None,
                 publicador=None, dormir=time.sleep, forzar: bool = False) -> dict:
    hoy = ahora.date()
    dia = T.DIAS.get(hoy.weekday())
    inf = {"modo": "publicar", "cuando": ahora.isoformat(timespec="minutes"), "estado": ""}
    if not dia and not forzar:
        inf["estado"] = "no_es_finde"
        return inf
    dia = dia or "sabado"
    if not forzar:
        desde, hasta = ventana(hoy)
        if not (desde <= ahora <= hasta):
            inf["estado"] = "fuera_de_hora"
            log(f"Reel del finde: {ahora:%H:%M} fuera de {desde:%H:%M}-{hasta:%H:%M}; no se hace nada")
            return inf
    mem = cargar(ruta_mem)
    if any(h.get("fecha") == hoy.isoformat() and h.get("estado") in ("publicando", "publicado")
           for h in mem.get("historial", [])):
        inf["estado"] = "ya_salio"
        log("Reel del finde: el de hoy ya salió (o se está publicando)")
        return inf
    a = (armar_fn or armar)(dia, hoy, mem, tema, log)
    if a.get("error"):
        inf["estado"] = "sin_tema"
        inf["error"] = a["error"]
        return inf
    registro = {"fecha": hoy.isoformat(), "dia": dia, "clave": a["clave"], "estado": "publicando",
                "cuando": ahora.isoformat(timespec="minutes"), "duracion": a["reel"]["duracion"]}
    mem["historial"].append(registro)                    # ANTES de publicar: un reintento no lo repite
    guardar(mem, ruta_mem)
    espera = (hora(hoy) - datetime.now(TZ_AR)).total_seconds()
    if espera > 0 and not forzar:
        log(f"   esperando {espera / 60:.0f} min a las {hora(hoy):%H:%M}…")
        dormir(espera)
    res = (publicador or publicar)(pieza(a, ahora), log=log)
    ok = [r for r in ("instagram", "facebook") if isinstance(res.get(r), dict) and res[r].get("id")]
    registro.update(estado="publicado" if ok else "fallo", redes=ok,
                    resultado={k: v for k, v in res.items() if k != "portada_url"})
    guardar(mem, ruta_mem)
    inf.update(estado="ok" if ok else "fallo", clave=a["clave"], redes=ok, carpeta=str(a["carpeta"]))
    return inf


def informe(inf: dict) -> str:
    r = [f"## Reels del finde — {inf['modo']}", ""]
    for p in inf.get("piezas") or []:
        r.append(f"- {p['dia']} {p['fecha']}: " + (p.get("error") or f"«{p['titulo']}» ({p['clave']}), "
                                                    f"{p['duracion']} s — {', '.join(p['archivos'])}"))
    if inf.get("estado"):
        r.append(f"- Estado: {inf['estado']} {inf.get('clave', '')} {inf.get('redes', '')} {inf.get('error', '')}")
    return "\n".join(r)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--generar", action="store_true")
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--dia", default="finde", choices=("sabado", "domingo", "finde"))
    ap.add_argument("--tema", default="")
    ap.add_argument("--fecha", default="")
    ap.add_argument("--ya", action="store_true", help="publicar sin esperar la hora ni mirar la franja")
    a = ap.parse_args()
    if not activo():
        print("FINDE=0: apagado.")
        return
    ahora = datetime.now(TZ_AR)
    if a.fecha:
        ahora = datetime.combine(date.fromisoformat(a.fecha), ahora.time(), TZ_AR)
    if a.publicar:
        inf = publicar_hoy(ahora, a.tema, forzar=a.ya)
    else:
        dias = ["sabado", "domingo"] if a.dia == "finde" else [a.dia]
        inf = generar(dias, ahora.date(), a.tema)
    print(informe(inf))
    if inf.get("estado") == "fallo":
        sys.exit(1)


if __name__ == "__main__":
    main()
