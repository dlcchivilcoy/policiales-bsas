# -*- coding: utf-8 -*-
"""Orquestador: recorre los 55 medios, filtra policiales y escribe la salida.

    listar notas  ->  filtro por diccionario  ->  detalle  ->  Claude confirma  ->  CSV/JSON

Uso:
    venv\\Scripts\\python.exe -m scraper.run                  # todo, las notas de HOY
    venv\\Scripts\\python.exe -m scraper.run --ventana 48     # una ventana de horas, para probar
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


# Argentina es UTC-3 todo el ano: no tiene horario de verano desde 2009, asi que
# alcanza con un offset fijo y no hace falta una libreria de zonas horarias.
TZ_AR = timezone(timedelta(hours=-3))


def _momento(publicado):
    """La fecha/hora de una nota como datetime con zona, o None si no se sabe.

    Las fechas sin zona se toman como UTC porque asi las entrega feedparser, que es
    de donde vienen casi todas: normaliza el pubDate del RSS a UTC y devuelve un
    struct_time sin tzinfo. Tomarlas como hora argentina correria todo 3 horas."""
    if not publicado:
        return None
    try:
        d = datetime.fromisoformat(str(publicado).replace("Z", "+00:00"))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    except Exception:
        return None


def _hoy_ar():
    return datetime.now(TZ_AR).date()


def _en_ventana(publicado, ventana, sin_fecha=True):
    """¿La nota entra en la ventana pedida?

    `ventana` es "hoy" (el dia calendario argentino, que es lo que se usa en las 3
    pasadas) o un numero de horas hacia atras, util para probar.

    `sin_fecha` es lo que se contesta cuando la nota no trae fecha. En el listado se
    dice True a proposito: hay medios que no publican la fecha ahi, y perder una nota
    de hoy es peor que revisar una vieja de mas. Despues de bajar la nota se dice
    False, porque a esa altura ya no hay excusa: si sigue sin fecha no hay forma de
    probar que es de hoy, y el sistema publica sin que nadie lo mire."""
    d = _momento(publicado)
    if d is None:
        return sin_fecha
    if ventana == "hoy":
        return d.astimezone(TZ_AR).date() == _hoy_ar()
    return d >= datetime.now(timezone.utc) - timedelta(hours=int(ventana))


def _describir_ventana(ventana):
    return "las notas de HOY" if ventana == "hoy" else f"las ultimas {ventana}h"


def _listar(url, rss, limite, nav):
    """Lista de una fuente sin dejar que un fallo tumbe al medio entero."""
    try:
        return fetch.listar_notas(url, rss, limite, permitir_navegador=nav), None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def recolectar(medio, ventana, usar_navegador):
    """Lista las notas de un medio y se queda con las que huelen a policial.

    Mira DOS fuentes y no una:

      - la seccion de policiales, que viene acotada al rubro; y
      - la home / ultimas noticias, que es donde esta la actualidad.

    Las dos, siempre, aunque el medio tenga seccion. La razon es que en estos
    diarios la seccion se actualiza tarde y a mano: la nota sale primero en la
    portada y recien despues alguien la categoriza, si se acuerda. Un medio puede
    tener la seccion de policiales parada hace una semana y estar publicando un
    choque hace media hora en la home. Mirando solo la seccion, ese choque no
    existe.

    La contracara es que la home trae de todo. Por eso el rubro lo decide el
    diccionario para lo que viene de la home, y la regla blanda —dejar pasar con
    puntaje bajo porque la seccion ya acota el tema— se aplica solo a lo que vino
    de una seccion leida por RSS.
    """
    nav = medio["navegador"] and usar_navegador
    fuentes, errores = [], []

    if medio["seccion"]:
        notas_sec, err = _listar(medio["seccion"], medio["seccion_rss"],
                                 LIMITE_POR_MEDIO, nav)
        # La seccion se da por confiable solo si la leimos por RSS. Raspando el HTML
        # de la pagina entran tambien el menu y la columna de "ultimas noticias".
        confiable = bool(medio["seccion_rss"])
        fuentes.append(("seccion", notas_sec, confiable))
        if err:
            errores.append(f"seccion: {err}")

    notas_home, err = _listar(medio["base"], medio["rss"], LIMITE_POR_MEDIO, nav)
    fuentes.append(("home", notas_home, False))
    if err:
        errores.append(f"home: {err}")

    # Una nota que esta en las dos fuentes se queda con la version de la seccion,
    # que es la que trae la marca de confiable.
    notas, vistas = [], set()
    for via, lista, confiable in fuentes:
        for n in lista:
            clave = (n.get("url") or "").rstrip("/")
            if not clave or clave in vistas:
                continue
            vistas.add(clave)
            n["via_listado"] = via
            n["seccion_confiable"] = confiable
            notas.append(n)

    # Solo es un fallo del medio si NINGUNA fuente trajo nada.
    err = "; ".join(errores) if (errores and not notas) else None
    if err:
        return medio, [], err

    candidatas = []
    for n in notas:
        if not _en_ventana(n.get("publicado"), ventana, sin_fecha=True):
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
        entra = p["probable"] or (n.get("seccion_confiable") and p["score"] > -5)
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


DIAGNOSTICO = os.path.join(RAIZ, "estado", "ultima_corrida.json")


def guardar_diagnostico(ventana, medios, candidatas, finales):
    """Deja por escrito como le fue a cada medio en esta pasada.

    Es lo que lee salud.py para decidir si avisar. Va en estado/ y no en salida/
    porque salida/ se borra y esto tiene que sobrevivir entre pasadas: un medio que
    falla una vez es ruido de red, uno que falla seis pasadas seguidas esta muerto y
    hay que enterarse. El historial queda ademas en los commits del ledger."""
    try:
        os.makedirs(os.path.dirname(DIAGNOSTICO), exist_ok=True)
        with open(DIAGNOSTICO, "w", encoding="utf-8") as f:
            json.dump({
                "cuando": datetime.now(timezone.utc).isoformat(),
                "cuando_ar": datetime.now(TZ_AR).strftime("%Y-%m-%d %H:%M"),
                "ventana": ventana,
                "candidatas": candidatas,
                "finales": finales,
                "medios": sorted(medios, key=lambda m: (m["localidad"], m["nombre"])),
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Un diagnostico que no se pudo escribir no puede tumbar la corrida.
        print(f"(no se pudo guardar el diagnostico: {e})")


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
    # "hoy" es el default a proposito: las 3 pasadas tienen que traer la actualidad
    # del dia y nada mas. Un numero de horas sirve para probar sin esperar al dia
    # siguiente, pero no es lo que corre en la nube.
    ap.add_argument("--ventana", default="hoy",
                    help='"hoy" (default) o un numero de horas hacia atras')
    ap.add_argument("--horas", type=int, default=None,
                    help="atajo viejo: equivale a --ventana N")
    ap.add_argument("--localidad", help="lista separada por comas; vacio = todas")
    # OJO: la IA del scraper esta APAGADA por defecto, a proposito. Ver GUARDA_IA abajo.
    ap.add_argument("--con-ia", action="store_true",
                    help="clasificar las notas con IA. CUESTA ~US$41/MES: leer la advertencia")
    ap.add_argument("--sin-ia", action="store_true",
                    help="(ya no hace falta: es el comportamiento por defecto)")
    ap.add_argument("--sin-navegador", action="store_true", help="saltea los sitios que necesitan Playwright")
    ap.add_argument("--limite-ia", type=int, default=400, help="tope de notas a mandar a Claude")
    args = ap.parse_args()

    ventana = args.ventana
    if args.horas is not None:          # el flag viejo sigue andando
        ventana = str(args.horas)
    if ventana != "hoy":
        try:
            int(ventana)
        except ValueError:
            print(f'--ventana tiene que ser "hoy" o un numero de horas, no {ventana!r}')
            return 1

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

    print(f"=== Policiales — {len(medios)} medios, {_describir_ventana(ventana)} ===")
    print(f"    (hoy en Argentina es {_hoy_ar().isoformat()})\n")
    t0 = time.time()

    # 1) Listar y filtrar por diccionario
    candidatas, fallos, diagnostico = [], [], []
    with ThreadPoolExecutor(max_workers=HILOS) as ex:
        futuros = {ex.submit(recolectar, m, ventana, usar_navegador): m for m in medios}
        for i, fut in enumerate(as_completed(futuros), 1):
            medio, notas, err = fut.result()
            if err:
                fallos.append((medio["dominio"], err))
            diagnostico.append({"dominio": medio["dominio"], "nombre": medio["nombre"],
                                "localidad": medio["localidad"],
                                "candidatas": len(notas), "error": err})
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
    # la fecha, y ahi se los deja pasar a proposito para no perder una nota de hoy.
    # La fecha REAL recien aparece aca, al bajar la nota. Sin este corte, el archivo
    # de una seccion paginada entra entero: la primera corrida de Minuto Arrecifes
    # metio 24 notas, la mas vieja de agosto de 2022, y el sistema las habria tratado
    # como policiales del dia. Un reel de un choque de hace tres anos publicado como
    # noticia de hoy.
    #
    # Aca `sin_fecha=False`: la que sigue sin fecha despues de bajarla se cae. Es lo
    # contrario de lo que hace el listado, y es a proposito. Nadie mira esto antes de
    # que salga publicado, asi que una nota que no puede probar que es de hoy no
    # entra. Se pierde alguna nota buena de un medio que no fecha nada; se evita
    # publicar una vieja como si fuera de hoy, que es mucho peor.
    antes = len(unicas)
    unicas = [n for n in unicas if _en_ventana(n.get("publicado"), ventana,
                                               sin_fecha=False)]
    if len(unicas) < antes:
        cual = "de hoy" if ventana == "hoy" else f"de las ultimas {ventana}h"
        print(f"{antes - len(unicas)} notas descartadas al conocerse su fecha real: "
              f"no son {cual}")

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

    guardar_diagnostico(ventana, diagnostico, len(candidatas), len(finales))

    print(f"\n=== {len(finales)} notas policiales en {time.time() - t0:.0f}s ===")
    print(f"  {base}.csv\n  {base}.json")
    if fallos:
        print(f"\n{len(fallos)} medios fallaron:")
        for dom, err in fallos:
            print(f"   - {dom}: {err[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
