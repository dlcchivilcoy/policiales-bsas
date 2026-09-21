# -*- coding: utf-8 -*-
"""Orquestador: recorre los 55 medios, filtra policiales y escribe la salida.

    listar notas  ->  filtro por diccionario  ->  detalle  ->  Claude confirma  ->  CSV/JSON

Uso:
    venv\\Scripts\\python.exe -m scraper.run                  # todo, ultimas 24h
    venv\\Scripts\\python.exe -m scraper.run --horas 48
    venv\\Scripts\\python.exe -m scraper.run --localidad Junin,Bragado
    venv\\Scripts\\python.exe -m scraper.run --sin-ia         # solo diccionario (gratis)
    venv\\Scripts\\python.exe -m scraper.run --sin-navegador  # saltea los 4 sitios lentos

El cuerpo de la nota se usa SOLO para clasificar y NO se guarda: la salida lleva
titular, link, fecha y un resumen propio generado por la IA. Es el mismo criterio
que sigue NoticIAs Chivilcoy por la Ley 11.723.
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import fetch
from scraper.medios import MEDIOS, LOCALIDADES
from scraper.keywords import puntuar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "salida")
HILOS = 8
LIMITE_POR_MEDIO = 40


def _cargar_env():
    """Lee el .env del proyecto si existe, sin pisar lo que ya este en el entorno."""
    ruta = os.path.join(RAIZ, ".env")
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _es_reciente(publicado, horas):
    """Sin fecha devuelve True: preferimos revisar una nota vieja de mas antes que
    perder una de hoy porque el medio no publica la fecha."""
    if not publicado:
        return True
    try:
        d = datetime.fromisoformat(publicado.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d >= datetime.now(timezone.utc) - timedelta(hours=horas)
    except Exception:
        return True


def recolectar(medio, horas, usar_navegador):
    """Lista las notas de un medio y se queda con las que huelen a policial."""
    nav = medio["navegador"] and usar_navegador
    url = medio["seccion"] or medio["base"]
    rss = medio["seccion_rss"] or (None if medio["seccion"] else medio["rss"])

    try:
        notas = fetch.listar_notas(url, rss, LIMITE_POR_MEDIO, permitir_navegador=nav)
    except Exception as e:
        return medio, [], f"{type(e).__name__}: {e}"

    candidatas = []
    for n in notas:
        if not _es_reciente(n.get("publicado"), horas):
            continue
        p = puntuar(n["titulo"], n.get("copete", ""))
        # Si el medio tiene seccion propia de policiales, el tema ya viene acotado:
        # ahi el diccionario solo tiene que descartar lo obviamente ajeno, no exigir
        # que el titular repita palabras del rubro ("Lo condenaron a 8 años" no las
        # tiene y es policial). Sin seccion, el diccionario decide solo.
        #
        # Pero esa confianza vale SOLO si la seccion se leyo por RSS, donde el feed
        # trae los items de la seccion y nada mas. Cuando hay que raspar el HTML de
        # la pagina de la seccion, entra tambien lo que la rodea — el menu, la
        # columna de "ultimas noticias", el pie — y ahi el rubro ya no esta acotado:
        # la seccion de policiales de Suipacha Hoy devolvio 14 de 14, con Milei y el
        # paro universitario adentro. Con HTML, decide el diccionario.
        seccion_confiable = bool(medio["seccion"]) and bool(medio["seccion_rss"])
        entra = p["probable"] or (seccion_confiable and p["score"] > -5)
        if entra:
            n.update({"localidad_medio": medio["localidad"], "medio": medio["nombre"],
                      "dominio": medio["dominio"], "score_keywords": p["score"],
                      "aciertos": p["aciertos"][:6]})
            candidatas.append(n)
    return medio, candidatas, None


def completar_detalle(nota):
    """Baja la nota para tener cuerpo y fecha reales. El cuerpo alimenta a la IA
    y despues se descarta: no se guarda en la salida.

    Ojo: aca NO se usa el navegador aunque el medio lo necesite para listar. El
    respaldo levanta un Chrome por llamada, asi que bajar 16 notas de un sitio
    bloqueado costaba 16 arranques de navegador y se comia la corrida entera.
    Para esas notas alcanza con el titular y el copete del listado: el diccionario
    ya puntuo con el titulo y Claude clasifica bien con titulo + copete.
    """
    if nota.get("copete") and nota.get("publicado"):
        nota["cuerpo"] = nota["copete"]
        return nota
    d = fetch.detalle(nota["url"], permitir_navegador=False)
    if not d["ok"]:
        nota["url_muerta"] = True
        nota["cuerpo"] = nota.get("copete", "")
        return nota
    nota["cuerpo"] = d["cuerpo"] or nota.get("copete", "")
    nota["publicado"] = nota.get("publicado") or d["publicado"]
    nota["imagen"] = nota.get("imagen") or d["imagen"]
    return nota


def escribir(notas, etiqueta):
    os.makedirs(SALIDA, exist_ok=True)
    base = os.path.join(SALIDA, f"policiales_{etiqueta}")

    campos = ["localidad", "localidad_medio", "medio", "dominio", "tipo", "gravedad",
              "victimas", "detenidos", "titulo", "resumen", "publicado", "url",
              "imagen", "score_keywords"]
    with open(base + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for n in notas:
            w.writerow(n)

    # El cuerpo original no se persiste (Ley 11.723): queda el resumen propio.
    limpias = [{k: v for k, v in n.items() if k not in ("cuerpo", "copete")} for n in notas]
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"generado": datetime.now(timezone.utc).isoformat(),
                   "total": len(limpias), "notas": limpias}, f,
                  ensure_ascii=False, indent=2)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# CLAUSULA DE COSTO — no sacar sin entender lo que se esta activando
# ─────────────────────────────────────────────────────────────────────────────
# El clasificador de IA de este scraper manda TODAS las notas del dia (~340) al modelo
# en lotes de 8 para confirmar cuales son policiales. Medido el 2026-09-21:
#
#     US$ 0,0106 por lote x 42 lotes = US$ 0,45 por pasada
#     x 90 pasadas al mes           = US$ 41 POR MES
#
# Y no hace falta: de esas 340 notas, solo 5 terminan en un reel. Gastar IA clasificando
# las otras 335 es tirar plata. El diccionario de palabras clave (scraper/keywords.py)
# filtra gratis y da 28/28 en su banco de pruebas; la IA se usa SOLO en los 5 guiones
# (reels/guion.py), que salen US$1,25 al mes — o $0 con el cupo gratis de Gemini.
#
# Por eso esta apagado POR DEFECTO y encenderlo pide DOS gestos deliberados: el flag
# --con-ia y la variable de entorno de abajo. Un flag suelto se copia y se pega sin
# pensar; una variable de entorno con este nombre, no.
GUARDA_IA = "CLASIFICADOR_IA_AUTORIZADO"

AVISO_IA = """
================================================================================
  FRENO DE COSTO — el clasificador de IA del scraper esta desactivado
================================================================================
  Pediste --con-ia. Eso manda las ~340 notas del dia al modelo y cuesta cerca de
  US$ 41 POR MES con las 3 pasadas diarias.

  Casi seguro NO es lo que queres: de esas 340 notas solo 5 terminan en un reel.
  El diccionario de palabras clave ya filtra gratis, y la IA que SI hace falta es
  la de los guiones (reels/flujo.py --con-ia), que sale US$1,25/mes o $0 con el
  cupo gratis de Gemini.

  Si igual lo necesitas (por ejemplo para medir la precision del diccionario en
  una corrida puntual), autorizalo a mano en ESA corrida:

      set CLASIFICADOR_IA_AUTORIZADO=1        (Windows)
      export CLASIFICADOR_IA_AUTORIZADO=1     (Linux/Mac)

  No lo pongas en el .env ni en los secrets del repo: la idea es que sea una
  decision por corrida y no un default que despues nadie recuerda haber activado.
================================================================================
"""


def main():
    ap = argparse.ArgumentParser(description="Scraper de policiales — 28 localidades bonaerenses")
    ap.add_argument("--horas", type=int, default=24, help="antiguedad maxima (default 24)")
    ap.add_argument("--localidad", help="lista separada por comas; vacio = todas")
    # OJO: la IA del scraper esta APAGADA por defecto, a proposito. Ver GUARDA_IA abajo.
    ap.add_argument("--con-ia", action="store_true",
                    help="clasificar las notas con IA. CUESTA ~US$41/MES: leer la advertencia")
    ap.add_argument("--sin-ia", action="store_true",
                    help="(ya no hace falta: es el comportamiento por defecto)")
    ap.add_argument("--sin-navegador", action="store_true", help="saltea los sitios que necesitan Playwright")
    ap.add_argument("--limite-ia", type=int, default=400, help="tope de notas a mandar a Claude")
    args = ap.parse_args()

    _cargar_env()

    # La clausula: --con-ia solo corre si ademas esta la autorizacion explicita.
    if args.con_ia and os.environ.get(GUARDA_IA, "").strip() not in ("1", "si", "true", "yes"):
        print(AVISO_IA)
        return 1

    usar_navegador = not args.sin_navegador

    medios = MEDIOS
    if args.localidad:
        pedidas = {x.strip().lower() for x in args.localidad.split(",")}
        medios = [m for m in MEDIOS if m["localidad"].lower() in pedidas]
        if not medios:
            print(f"Ninguna localidad coincide. Disponibles:\n  " +
                  "\n  ".join(LOCALIDADES))
            return 1

    print(f"=== Policiales — {len(medios)} medios, ultimas {args.horas}h ===\n")
    t0 = time.time()

    # 1) Listar y filtrar por diccionario
    candidatas, fallos = [], []
    with ThreadPoolExecutor(max_workers=HILOS) as ex:
        futuros = {ex.submit(recolectar, m, args.horas, usar_navegador): m for m in medios}
        for i, fut in enumerate(as_completed(futuros), 1):
            medio, notas, err = fut.result()
            if err:
                fallos.append((medio["dominio"], err))
            candidatas += notas
            print(f"[{i:>2}/{len(medios)}] {medio['localidad'][:18]:<18} "
                  f"{medio['nombre'][:26]:<26} {len(notas):>3} candidatas "
                  f"{'  ' + err[:30] if err else ''}")

    print(f"\n{len(candidatas)} candidatas tras el diccionario "
          f"({time.time() - t0:.0f}s)")
    if not candidatas:
        print("Nada para procesar.")
        return 0

    # Dedup: los medios regionales cubren varias localidades y repiten la misma nota.
    vistas, unicas = set(), []
    for n in candidatas:
        clave = n["url"].rstrip("/")
        if clave in vistas:
            continue
        vistas.add(clave)
        unicas.append(n)
    if len(unicas) < len(candidatas):
        print(f"{len(candidatas) - len(unicas)} duplicadas por URL descartadas")

    # 2) Detalle (para que la IA juzgue con el cuerpo y no solo con el titular)
    print(f"\nBajando el detalle de {len(unicas)} notas...")
    with ThreadPoolExecutor(max_workers=HILOS) as ex:
        list(ex.map(completar_detalle, unicas))
    unicas = [n for n in unicas if not n.get("url_muerta")]

    # Segundo filtro por fecha, y no sobra. En el listado hay medios que no publican
    # la fecha (tipico del raspado HTML), y `_es_reciente` los deja pasar a proposito
    # para no perder una nota de hoy. La fecha REAL recien aparece aca, al bajar la
    # nota. Sin este corte, el archivo de una seccion paginada entra entero: la
    # primera corrida de Minuto Arrecifes metio 24 notas, la mas vieja de agosto de
    # 2022, y el sistema las habria tratado como policiales de las ultimas 72 horas.
    # Un reel de un choque de hace tres anos publicado como noticia de hoy.
    antes = len(unicas)
    unicas = [n for n in unicas if _es_reciente(n.get("publicado"), args.horas)]
    if len(unicas) < antes:
        print(f"{antes - len(unicas)} notas descartadas por viejas al conocerse su "
              f"fecha real (el listado no la traia)")

    # 3) Confirmacion con IA — APAGADA por defecto (ver GUARDA_IA arriba)
    if not args.con_ia:
        print("\nSin clasificador de IA (es el default, y es gratis): la salida es la del "
              "diccionario.")
        finales = unicas
        for n in finales:
            n.setdefault("tipo", "")
            n.setdefault("gravedad", "")
            n.setdefault("resumen", "")
            n.setdefault("localidad", n["localidad_medio"])
    else:
        from scraper import clasificador
        aClasificar = sorted(unicas, key=lambda n: -n["score_keywords"])[:args.limite_ia]
        print(f"\nConfirmando {len(aClasificar)} notas con Claude "
              f"({clasificador.MODELO})...")
        try:
            clasificador.clasificar(aClasificar)
        except RuntimeError as e:
            # No escribimos nada: una salida sin confirmar tiene la misma pinta
            # que una confirmada y despues no hay como distinguirlas.
            print(f"\nERROR: {e}")
            print("No se genero archivo. Corre SIN --con-ia si igual queres la "
                  "salida del diccionario, que va a traer falsos positivos.")
            return 1
        descartadas = [n for n in aClasificar if n.get("es_policial") is False]
        sin_confirmar = [n for n in aClasificar if n.get("sin_confirmar")]
        finales = [n for n in aClasificar if n.get("es_policial") is not False]
        print(f"Claude descarto {len(descartadas)} falsos positivos "
              f"({len(finales)} quedan)")
        if sin_confirmar:
            print(f"OJO: {len(sin_confirmar)} notas quedaron SIN confirmar por la IA "
                  f"(marcadas con sin_confirmar=true en el JSON).")
        for n in finales:
            if not n.get("localidad"):
                n["localidad"] = n["localidad_medio"]

    finales.sort(key=lambda n: (n.get("localidad_medio", ""), n.get("publicado") or ""))
    etiqueta = datetime.now().strftime("%Y-%m-%d_%H%M")
    base = escribir(finales, etiqueta)

    print(f"\n=== {len(finales)} notas policiales en {time.time() - t0:.0f}s ===")
    print(f"  {base}.csv\n  {base}.json")
    if fallos:
        print(f"\n{len(fallos)} medios fallaron:")
        for dom, err in fallos:
            print(f"   - {dom}: {err[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
