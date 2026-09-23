# -*- coding: utf-8 -*-
"""Revisa como salio la pasada y avisa cuando algo se rompio.

El problema que resuelve: este sistema corre solo tres veces por dia y no lo mira
nadie. Sin esto, un medio que cambia de CMS, una clave de Gemini vencida o un
ffmpeg que dejo de armar el video no se notan — simplemente dejan de salir reels,
en silencio, y uno se entera semanas despues.

Como avisa, sin gastar un peso:

  1. Si encuentra una FALLA, termina con codigo 1. Eso hace fallar el paso, y por
     lo tanto la corrida entera, y GitHub manda el mail de "workflow failed" solo,
     sin configurar nada ni pagar nada.
  2. El workflow, ante esa falla, abre (o comenta) un issue en el repo con este
     mismo informe. El issue usa el GITHUB_TOKEN que GitHub ya le da a la corrida:
     no hay secreto que cargar ni servicio de mail que contratar.

La diferencia entre FALLA y AVISO es si hay que hacer algo hoy. Que un pueblo
chico no tenga policiales un martes es normal y no se avisa; que doce medios
devuelvan error a la vez, no.

Correr:  python -m salud
"""
import glob
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.abspath(__file__))
DIAGNOSTICO = os.path.join(RAIZ, "estado", "ultima_corrida.json")
HISTORIAL = os.path.join(RAIZ, "estado", "salud.json")
TZ_AR = timezone(timedelta(hours=-3))

# ─── Umbrales ────────────────────────────────────────────────────────────────
# Estan todos juntos y con nombre para poder discutirlos sin leer el codigo.

# Que fracasen algunos medios es normal: son sitios chicos, se caen, cambian el
# certificado. Que fracase la mitad no es de los medios, es nuestro.
FRACCION_MEDIOS_CAIDOS = 0.40

# Un medio que falla una vez es ruido de red. Seis pasadas seguidas son dos dias:
# eso ya es el sitio, no la red.
PASADAS_CAIDO_PARA_FALLA = 6

# Un medio puede pasar una semana sin publicar un policial y ser normal en un
# pueblo de 10.000 habitantes. Tres semanas sin una sola candidata es otra cosa:
# suele ser que cambiaron el HTML y ya no le entendemos.
PASADAS_SIN_NADA_PARA_AVISO = 63        # 3 semanas x 3 pasadas por dia

# Cuantas localidades distintas tendria que tocar una pasada sana.
LOCALIDADES_MINIMAS = 3

MAX_PASADAS_GUARDADAS = 30


def _cargar(ruta, x_default):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return x_default


def _ultimo_lote():
    lotes = sorted(glob.glob(os.path.join(RAIZ, "salida_reels", "*", "_lote.json")))
    return _cargar(lotes[-1], {}) if lotes else {}


def revisar():
    """Devuelve (fallas, avisos, lineas_del_informe)."""
    corrida = _cargar(DIAGNOSTICO, {})
    historial = _cargar(HISTORIAL, {"medios": {}, "pasadas": []})
    lote = _ultimo_lote()

    fallas, avisos, informe = [], [], []

    if not corrida:
        return (["No hay diagnostico de la corrida: el scraper no llego a terminar."],
                [], ["Sin estado/ultima_corrida.json."])

    medios = corrida.get("medios", [])
    caidos = [m for m in medios if m.get("error")]
    piezas = lote.get("piezas", [])
    notas = corrida.get("finales", 0)
    localidades = len({m["localidad"] for m in medios if m.get("candidatas")})

    informe.append(f"**Pasada del {corrida.get('cuando_ar', '?')}** "
                   f"(ventana: {corrida.get('ventana', '?')})")
    informe.append("")
    informe.append(f"- {notas} notas policiales, de {localidades} localidades")
    informe.append(f"- {len(piezas)} reels armados")
    informe.append(f"- {len(caidos)} de {len(medios)} medios con error")

    # ── Lo que rompe la pasada ───────────────────────────────────────────────
    if notas == 0:
        fallas.append("La pasada no trajo NINGUNA nota policial. Con 59 medios y una "
                      "ventana de un dia, cero no es un dia tranquilo: es una falla.")

    if medios and len(caidos) / len(medios) >= FRACCION_MEDIOS_CAIDOS:
        fallas.append(f"{len(caidos)} de {len(medios)} medios fallaron "
                      f"({len(caidos) / len(medios):.0%}). Eso no son los sitios, "
                      f"es la red de la corrida o algo nuestro.")

    if notas > 0 and not piezas:
        fallas.append(f"Habia {notas} notas y no se armo ni un reel. Mirar el paso de "
                      f"los reels: suele ser la clave de Gemini o ffmpeg.")

    if 0 < localidades < LOCALIDADES_MINIMAS:
        avisos.append(f"Solo {localidades} localidad(es) con material. Para una tanda "
                      f"que reparte una por localidad, es poco.")

    # ── Historial por medio ──────────────────────────────────────────────────
    hist = historial.get("medios", {})
    for m in medios:
        h = hist.setdefault(m["dominio"], {"caido": 0, "sin_nada": 0, "nombre": m["nombre"],
                                           "localidad": m["localidad"]})
        h["nombre"], h["localidad"] = m["nombre"], m["localidad"]
        h["caido"] = h.get("caido", 0) + 1 if m.get("error") else 0
        h["sin_nada"] = 0 if m.get("candidatas") else h.get("sin_nada", 0) + 1
        h["ultimo_error"] = (m.get("error") or "")[:120]

    muertos = [(d, h) for d, h in hist.items() if h.get("caido", 0) >= PASADAS_CAIDO_PARA_FALLA]
    for d, h in sorted(muertos):
        fallas.append(f"{h['localidad']} — {h['nombre']} ({d}) falla hace "
                      f"{h['caido']} pasadas seguidas: {h.get('ultimo_error', '')}")

    mudos = [(d, h) for d, h in hist.items()
             if h.get("sin_nada", 0) >= PASADAS_SIN_NADA_PARA_AVISO]
    for d, h in sorted(mudos):
        avisos.append(f"{h['localidad']} — {h['nombre']} ({d}) no da una sola candidata "
                      f"hace {h['sin_nada']} pasadas. Revisar si cambio el sitio: "
                      f"tools/sondear_medios.py --solo {h['localidad']}")

    # ── Reels que salieron pero no sirven ────────────────────────────────────
    no_aptos = [p for p in piezas if not p.get("apto_para_publicar")]
    if piezas and len(no_aptos) == len(piezas):
        avisos.append(f"Los {len(piezas)} reels salieron marcados NO publicables. "
                      f"Motivo del primero: {no_aptos[0].get('por_que_no', '?')}")
    sin_foto = [p for p in piezas if not p.get("tenia_foto")]
    if sin_foto:
        avisos.append(f"{len(sin_foto)} de {len(piezas)} reels sin foto propia.")

    # ── Guardar el historial ─────────────────────────────────────────────────
    historial["medios"] = hist
    historial.setdefault("pasadas", []).append({
        "cuando": corrida.get("cuando_ar"),
        "notas": notas, "reels": len(piezas), "caidos": len(caidos),
        "fallas": len(fallas), "avisos": len(avisos),
    })
    historial["pasadas"] = historial["pasadas"][-MAX_PASADAS_GUARDADAS:]
    try:
        os.makedirs(os.path.dirname(HISTORIAL), exist_ok=True)
        with open(HISTORIAL, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)
    except Exception as e:
        avisos.append(f"No se pudo guardar el historial de salud: {e}")

    return fallas, avisos, informe


def main():
    import entorno
    entorno.consola_utf8()
    fallas, avisos, informe = revisar()

    lineas = list(informe)
    if fallas:
        lineas += ["", "### FALLAS", ""] + [f"- {f}" for f in fallas]
    if avisos:
        lineas += ["", "### Avisos", ""] + [f"- {a}" for a in avisos]
    if not fallas and not avisos:
        lineas += ["", "Todo en orden."]

    texto = "\n".join(lineas)
    print(texto)

    # El resumen que se ve en la pagina de la corrida, sin abrir los logs.
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        try:
            with open(resumen, "a", encoding="utf-8") as f:
                f.write("\n## Salud de la pasada\n\n" + texto + "\n")
        except Exception:
            pass

    # Y el informe que el workflow mete en el issue cuando algo se rompio.
    if fallas:
        try:
            with open(os.path.join(RAIZ, "informe_salud.md"), "w", encoding="utf-8") as f:
                f.write(texto + "\n")
        except Exception:
            pass
        print("\nHay fallas: la corrida termina en error a proposito, para que "
              "GitHub mande el aviso.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
