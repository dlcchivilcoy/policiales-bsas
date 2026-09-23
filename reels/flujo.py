# -*- coding: utf-8 -*-
"""FASE 1 — genera los reels y muestra qué se publicaría. NO PUBLICA NADA.

    nota scrapeada → guion → placa 1080x1920 → descripción SEO → carpeta de revisión

No importa `platforms.tiktok` ni ninguna credencial de red social: en esta fase la
publicación está fuera del alcance a propósito. El paso de subida se agrega cuando
digas, y en su momento va a ser a BORRADORES, no directo (ver README_REELS.md).

Uso:
    venv\\Scripts\\python.exe -m reels.flujo                    # top 5 del último scrapeo
    venv\\Scripts\\python.exe -m reels.flujo --cuantos 3
    venv\\Scripts\\python.exe -m reels.flujo --localidad Junin
    venv\\Scripts\\python.exe -m reels.flujo --con-ia           # guion redactado por Claude
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reels import guion as G
from reels import marca as M
from reels import placa as P
from reels import video as V
from reels import limpieza as L
from reels import ledger as LD
from scraper import fetch

import entorno

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_REELS = RAIZ / "salida_reels"
SITIO = "www.diariolacampaña.com.ar"   # la web del diario, donde se manda a la gente

# Prioridad de tipos: qué hecho rinde más en un reel. Un homicidio o un siniestro fatal
# paran el scroll; una causa judicial en trámite, no. Se usa para ELEGIR cuáles de las
# ~300 notas del día merecen reel, que es la decisión de fondo de todo esto.
PESO_TIPO = {
    "homicidio": 100, "accidente_vial": 90, "incendio": 85, "narcotrafico": 80,
    "robo": 75, "violencia_genero": 70, "desaparicion": 70, "muerte_dudosa": 65,
    "abuso_sexual": 60, "operativo_policial": 55, "estafa": 50, "suicidio": 30,
    "judicial": 40, "otro_policial": 35,
}
PESO_GRAVEDAD = {"fatal": 40, "grave": 25, "media": 10, "leve": 0}


def _ultimo_scrapeo() -> Path | None:
    archivos = sorted(glob.glob(str(RAIZ / "salida" / "policiales_*.json")))
    return Path(archivos[-1]) if archivos else None


def _puntaje(nota: dict) -> float:
    """Cuánto merece un reel esta nota."""
    p = PESO_TIPO.get(nota.get("tipo") or "otro_policial", 35)
    p += PESO_GRAVEDAD.get(nota.get("gravedad") or "media", 10)
    p += min((nota.get("score_keywords") or 0), 24)      # el diccionario ya midió intensidad
    if nota.get("imagen"):
        p += 30      # sin foto el reel queda pobre: la que tiene imagen va primero
    if (nota.get("victimas") or 0) > 0:
        p += 15
    return p


# Puntaje mínimo para entrar en la segunda vuelta. El umbral del diccionario es 5 y
# sirve para "revisá esto"; para OCUPAR un lugar en la tanda hace falta más margen.
UMBRAL_RELLENO = 8

# Cuánto del titular más corto tiene que estar contenido en el otro para darlos por el
# mismo hecho, entre notas de la MISMA localidad. 0,40 salió de medir el caso real:
# el par de Bragado da 0,43 y dos hechos distintos de una misma localidad rara vez
# pasan de 0,25.
CONTENCION_MISMA_LOCALIDAD = 0.40


def elegir(notas: list, cuantos: int, localidad: str = "") -> list:
    """Las mejores `cuantos` notas para hacer reel, sin repetir localidad si se puede.

    Repartir por localidad no es un capricho estético: tres reels seguidos de Junín
    dejan sin cobertura a las otras 27 y el feed se vuelve monotemático.
    """
    if localidad:
        pedidas = {x.strip().lower() for x in localidad.split(",")}
        notas = [n for n in notas
                 if (n.get("localidad_medio") or "").lower() in pedidas
                 or (n.get("localidad") or "").lower() in pedidas]

    ordenadas = sorted(notas, key=_puntaje, reverse=True)
    elegidas, vistas = [], set()
    for n in ordenadas:                      # primera vuelta: una por localidad
        # La del HECHO, no la del medio. Esto además resuelve solo un problema que el
        # parecido de titulares no alcanzaba a resolver: cuando dos medios de pueblos
        # distintos cubren el MISMO hecho, los titulares pueden no parecerse en nada
        # —«Dictan prisión preventiva al edil libertario» y «Prisión preventiva para
        # el concejal de Bragado acusado de vender drogas» comparten tres palabras—
        # pero los dos son de Bragado, y la regla de una por localidad deja pasar uno
        # solo. Repartiendo por el medio, los dos entraban como localidades distintas.
        loc = (n.get("localidad") or n.get("localidad_medio") or "").lower()
        if loc in vistas:
            continue
        vistas.add(loc)
        elegidas.append(n)
        if len(elegidas) >= cuantos:
            return elegidas
    # Segunda vuelta: completar con una segunda nota de alguna localidad ya usada.
    # Acá hay que ser MÁS exigente que en la primera, no menos, porque lo que entra
    # es lo que quedó abajo en el orden. Sin esto, pedir 14 reels un día que hay 11
    # notas buenas metía las tres peores: en la prueba del 22/09 entró «Presentaron
    # la obra Infancias Robadas en la Casa de la Cultura» —que pasó el diccionario
    # porque la OBRA se llama «Robadas»— y el mismo hecho de Bragado dos veces.
    from reels import ledger as _LD
    huellas = [_LD._huella(n) for n in elegidas]

    for n in ordenadas:
        if len(elegidas) >= cuantos:
            break
        if n in elegidas:
            continue

        # (a) Solo lo que el diccionario dio por policial con holgura. Lo que entró
        #     raspando el umbral no merece un lugar cuando ya hay material mejor.
        if (n.get("score_keywords") or 0) < UMBRAL_RELLENO:
            continue

        # (b) Y que no sea un hecho que ya está en la tanda. Dos medios distintos
        #     titulan el mismo hecho muy distinto —«Dictan prisión preventiva al edil
        #     libertario Díaz» y «Prisión preventiva para el concejal de Bragado
        #     acusado de vender drogas» comparten tres palabras de trece— así que el
        #     parecido general no alcanza. Lo que sí discrimina es que esas tres
        #     palabras son las DISTINTIVAS: acá se mide cuánto del titular más corto
        #     está contenido en el otro, y solo entre notas de la misma localidad,
        #     donde dos hechos del mismo día que comparten casi todo el vocabulario
        #     casi siempre son el mismo hecho contado dos veces.
        h = _LD._huella(n)
        loc_n = (n.get("localidad") or n.get("localidad_medio") or "").lower()
        repetida = False
        for m, hm in zip(elegidas, huellas):
            loc_m = (m.get("localidad") or m.get("localidad_medio") or "").lower()
            if _LD._se_parecen(h, hm):
                repetida = True
                break
            if loc_n and loc_n == loc_m and len(h) >= 4 and len(hm) >= 4:
                contencion = len(h & hm) / min(len(h), len(hm))
                if contencion >= CONTENCION_MISMA_LOCALIDAD:
                    repetida = True
                    break
        if repetida:
            continue

        elegidas.append(n)
        huellas.append(h)
    return elegidas


def _bajar_foto(url: str, destino: Path) -> Path | None:
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if r.status_code >= 400 or not r.content:
            return None
        destino.write_bytes(r.content)
        return destino
    except Exception:
        return None


# Tope de descarga del video. Un clip de nota local pesa 2-15 MB; arriba de esto
# suele ser una pelicula entera mal enlazada o un stream, y no vale la pena esperarlo
# para despues usar 8 segundos.
MAX_VIDEO_MB = 60


def _bajar_video(url: str, destino: Path) -> Path | None:
    """Baja el video de la nota, si pesa lo razonable.

    Se descarga por trozos y mirando el tamaño a medida que entra, porque el
    Content-Length miente o no viene: sin el corte, una URL mal puesta puede tener
    a la corrida bajando cientos de megas.
    """
    if not url:
        return None
    try:
        tope = MAX_VIDEO_MB * 1024 * 1024
        with httpx.stream("GET", url, timeout=60, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as r:
            if r.status_code >= 400:
                return None
            total = 0
            with open(destino, "wb") as fh:
                for trozo in r.iter_bytes(65536):
                    total += len(trozo)
                    if total > tope:
                        fh.close()
                        destino.unlink(missing_ok=True)
                        return None
                    fh.write(trozo)
        return destino if total > 10240 else None     # menos de 10 KB no es un video
    except Exception:
        destino.unlink(missing_ok=True)
        return None


def _slug(texto: str, n: int = 40) -> str:
    limpio = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower())
    return limpio.strip("-")[:n] or "nota"


def material(nota: dict) -> dict:
    """Vuelve a bajar la nota para tener CUERPO con el que redactar.

    El scrapeo no guarda el texto original (Ley 11.723, mismo criterio que NoticIAs):
    en la salida quedan titular, link y fecha. Pero para escribir una bajada y un pie
    que no repitan el titular hace falta el cuerpo, así que se baja acá, se usa para
    redactar, y NO se persiste: a la carpeta de revisión solo va el texto propio.
    """
    if nota.get("resumen"):
        return nota
    d = fetch.detalle(nota.get("url") or "", permitir_navegador=False)
    if not d.get("ok"):
        return nota
    # og:description primero: es el resumen que escribio el medio, corto y del tema. El
    # volcado del cuerpo se usa solo si no hay, porque en varios sitios trae la nota de
    # al lado y la bajada termina hablando de otra cosa.
    texto = d.get("descripcion") or ""
    if len(texto) < 80 and d.get("cuerpo"):
        texto = d["cuerpo"]
    return dict(nota, cuerpo=texto[:1500]) if texto else nota


def procesar(nota: dict, carpeta: Path, usar_ia: bool, idx: int,
             hacer_video: bool = True, preferir: str = "") -> dict:
    """Una nota → guion + placa + descripción. Devuelve el informe de la pieza."""
    # La imagen PRIMERO y el guion después, aunque parezca al revés. Si la nota se
    # queda sin imagen, la pieza no se arma; redactando antes se habría gastado una
    # llamada a la IA para un guion que nadie va a usar.
    #
    # El VIDEO tiene prioridad sobre la foto: un reel con imágenes en movimiento
    # retiene mucho más que una foto quieta con zoom. Si el medio publicó uno propio,
    # ese va al reel y la foto queda de respaldo.
    tmp_dir = Path(tempfile.gettempdir())
    clip = _bajar_video(nota.get("video") or "", tmp_dir / f"reel_clip_{idx}.mp4")

    tmp = tmp_dir / f"reel_foto_{idx}.jpg"
    foto = None
    if clip:
        # La placa se compone sobre una imagen: de ahí salen el color del fondo y la
        # altura de la caja. Con video, esa imagen es un cuadro del propio clip, así
        # el fondo combina con lo que se ve moverse.
        foto = V.primer_cuadro(clip, tmp)
    if not foto:
        foto = _bajar_foto(nota.get("imagen") or "", tmp)

    # El filtro de la tanda mira que la nota DECLARE una imagen; esto comprueba que la
    # imagen realmente se pueda bajar. Un enlace roto o un 403 dejan la placa igual de
    # vacía que no tener foto, así que la pieza no se arma.
    if not foto and not clip:
        return {"orden": idx, "descartada": True,
                "por_que_no": "La imagen que declara la nota no se pudo bajar.",
                "localidad": nota.get("localidad_medio"), "medio": nota.get("medio"),
                "titulo": nota.get("titulo"), "url_original": nota.get("url")}

    nota = material(nota)
    g = G.generar(nota, usar_ia=usar_ia, preferir=preferir, sitio=SITIO)

    nombre = f"{idx:02d}_{_slug(nota.get('localidad_medio'))}_{_slug(g['titular'], 30)}"
    img = carpeta / f"{nombre}.jpg"
    informe = P.componer(g, foto, img, capas=hacer_video)
    if clip:
        informe["clip"] = str(clip)
    avisos = P.auditar(informe)
    # Que el hecho sea de otra localidad que la del medio no rompe la pieza, pero hay
    # que verlo: cambia la volanta, el hashtag y el "Más noticias de" del posteo.
    if g.get("aviso_localidad"):
        avisos.append(g["aviso_localidad"])

    vid = None
    if hacer_video:
        try:
            vid = V.armar(informe, carpeta / f"{nombre}.mp4")
        except V.FfmpegError as e:
            vid = {"error": str(e)}

    # El camino SIN IA copia oraciones del medio tal cual y arma el zocalo truncando el
    # titular. Sirve para VER el flujo, no para publicar: publicar texto copiado del medio
    # de origen es otra cosa que resumirlo con palabras propias. Queda marcado en el JSON
    # para que ningun paso posterior lo tome por publicable.
    # Dos condiciones, y las dos hacen falta. La primera es QUIEN lo escribio: por
    # reglas no es publicable, porque la bajada repite oraciones del medio de origen.
    objeciones = []
    if not g.get("via", "").startswith(("claude", "gemini")):
        objeciones.append(
            "Guion armado por reglas: la bajada reproduce oraciones del medio de origen y "
            "el zocalo es un recorte del titular. Hay que generarlo con --con-ia.")

    # La segunda es QUE dice. Un campo vacio deja un hueco en la placa, y como no hay
    # nadie revisando antes de que salga, el hueco se publica. Paso de verdad en una
    # corrida: la bajada salio en blanco y la pieza no objeto nada. El guion por IA
    # cae a los campos del guion por reglas cuando el modelo deja uno vacio, asi que
    # el agujero llega igual aunque haya escrito la IA.
    for campo, minimo in (("titular", 15), ("volanta", 3), ("bajada", 25), ("zocalo", 3)):
        if len((g.get(campo) or "").strip()) < minimo:
            objeciones.append(f"El campo '{campo}' quedo vacio o demasiado corto: "
                              f"en la placa se ve como un hueco.")

    apto = not objeciones
    pieza = {
        "orden": idx,
        "apto_para_publicar": apto,
        "por_que_no": " ".join(objeciones),
        "localidad": nota.get("localidad_medio"),
        "medio": nota.get("medio"),
        "tipo": nota.get("tipo") or g.get("tipo") or "(sin clasificar)",
        "gravedad": nota.get("gravedad") or "(sin clasificar)",
        "puntaje": round(_puntaje(nota), 1),
        "url_original": nota.get("url"),
        "tenia_foto": bool(foto),
        "tenia_video": bool(clip),
        "guion": {k: g[k] for k in ("volanta", "titular", "bajada", "zocalo", "pie", "via")},
        "descripcion_tiktok": g["descripcion_final"],
        "placa": str(img),
        "video": vid,
        "fondo": informe.get("fondo"),
        "y_imagen": informe.get("y_img"),
        "avisos": avisos,
    }
    (carpeta / f"{nombre}.json").write_text(
        json.dumps(pieza, ensure_ascii=False, indent=2), encoding="utf-8")
    return pieza


def main():
    ap = argparse.ArgumentParser(description="FASE 1 — genera reels de policiales. NO publica.")
    ap.add_argument("--cuantos", type=int, default=5)
    ap.add_argument("--localidad", help="filtra por localidad (separadas por coma)")
    ap.add_argument("--con-ia", action="store_true",
                    help="el guion lo redacta la IA (Gemini gratis si hay claves; si no, Claude)")
    ap.add_argument("--proveedor", choices=["gemini", "claude"], default="",
                    help="forzar proveedor. Vacío = Gemini si hay claves (gratis)")
    ap.add_argument("--sin-ledger", action="store_true",
                    help="ignorar la memoria y permitir repetir notas ya usadas")
    ap.add_argument("--entrada", help="JSON de scrapeo; por defecto, el último de salida/")
    ap.add_argument("--sin-video", action="store_true",
                    help="solo la placa fija, sin armar el .mp4 (más rápido para revisar)")
    ap.add_argument("--conservar-dias", type=int, default=L.DIAS_RETENCION,
                    help=f"cuántos días de corridas guardar (default {L.DIAS_RETENCION}; 0 = no limpiar)")
    args = ap.parse_args()

    # Las claves, antes de cualquier otra cosa. Sin esto --con-ia no puede andar en
    # una maquina local: en la nube las pone el workflow, pero aca las tiene el .env
    # y hasta ahora no habia quien lo leyera. El sintoma era un "la IA fallo:
    # RuntimeError" que no explicaba nada.
    entorno.consola_utf8()
    cargadas = entorno.cargar()
    if args.con_ia and not cargadas:
        print("(no se leyo ninguna clave del .env; se usa lo que haya en el entorno)")

    faltan = M.faltantes()
    if faltan:
        print(f"OJO: faltan assets de marca: {', '.join(faltan)}")

    entrada = Path(args.entrada) if args.entrada else _ultimo_scrapeo()
    if not entrada or not entrada.exists():
        print("No hay salida de scrapeo. Corré primero:  python -m scraper.run --sin-ia")
        return 1

    notas = json.loads(entrada.read_text(encoding="utf-8"))["notas"]
    print(f"=== FASE 1 — generación de reels (NO se publica nada) ===")
    print(f"Entrada: {entrada.name} ({len(notas)} notas policiales)")

    # Sin imagen ni video no hay reel que valga. La placa queda con media pantalla
    # vacía —se ve como un armado a medio hacer— y el .mp4 pesa 330 KB contra 800 de
    # una con foto, porque es casi todo fondo liso. En la tanda del 22/09 pasó en 3
    # de 14 y las tres salieron marcadas listas para publicar.
    #
    # Se descartan ACÁ, antes de elegir, y no al final: así no ocupan uno de los
    # lugares de la tanda ni gastan una llamada a la IA para un guion que no se usa.
    # De qué localidad es cada hecho, antes de repartir. Sin esto, una nota de
    # Pergamino publicada por un medio de Chacabuco ocupa el lugar de Chacabuco.
    notas = [dict(n, localidad=G.localidad_de_la_nota(n)[0]) for n in notas]

    con_material = [n for n in notas if (n.get("imagen") or n.get("video"))]
    sin_material = len(notas) - len(con_material)
    if sin_material:
        print(f"{sin_material} nota(s) descartadas por no tener ni foto ni video.")
    notas = con_material
    if not notas:
        print("Ninguna nota de la tanda trae imagen: no hay nada que armar.")
        return 0
    print()

    # Memoria entre pasadas: las tres corridas del dia miran ventanas que se superponen,
    # asi que sin esto la nota fuerte de la manana volveria a salir a la tarde y a la noche.
    if args.sin_ledger:
        # --sin-ledger apaga la MEMORIA entre pasadas, no el dedup de esta tanda. Son
        # dos cosas distintas y confundirlas se vio en la vista previa del 22/09: la
        # misma nota del femicidio de Pergamino salio dos veces, una por el medio de
        # Chacabuco y otra por el de Pergamino, y la prision preventiva del concejal de
        # Bragado tambien, desde 9 de Julio y desde Carlos Casares. Cuatro de catorce
        # piezas eran dos hechos repetidos.
        print("--sin-ledger: no se consulta la memoria de pasadas anteriores "
              "(el dedup dentro de esta tanda sigue activo).")
        candidatas, repetidas = LD.filtrar_tanda(notas)
        if repetidas:
            print(f"{repetidas} nota(s) salteadas por ser el mismo hecho que otra de "
                  f"esta misma tanda.")
    else:
        candidatas, repetidas = LD.filtrar(notas)
        print(f"Memoria: {LD.resumen()}" +
              (f" — {repetidas} nota(s) ya tuvieron reel y se saltean" if repetidas else ""))

    elegidas = elegir(candidatas, args.cuantos, args.localidad or "")
    if not elegidas:
        print("No quedan notas nuevas para hacer reel (o ninguna coincide con el filtro).")
        return 0

    sello = datetime.now().strftime("%Y-%m-%d_%H%M")
    carpeta = SALIDA_REELS / sello
    carpeta.mkdir(parents=True, exist_ok=True)

    piezas, descartadas = [], []
    for i, nota in enumerate(elegidas, 1):
        print(f"[{i}/{len(elegidas)}] {nota.get('localidad_medio', '?')} — "
              f"{(nota.get('titulo') or '')[:58]}")
        pieza = procesar(nota, carpeta, args.con_ia, i, hacer_video=not args.sin_video,
                         preferir=args.proveedor)
        if pieza.get("descartada"):
            # No se le hizo guion ni placa: no hay nada que mostrar más que el motivo.
            descartadas.append(pieza)
            print(f"      DESCARTADA — {pieza['por_que_no']}\n")
            continue
        piezas.append(pieza)
        g = pieza["guion"]
        print(f"      volanta : {g['volanta']}")
        print(f"      titular : {g['titular']}")
        print(f"      bajada  : {g['bajada'][:74]}")
        print(f"      zócalo  : {g['zocalo']}   (guion vía: {g['via']})")
        print(f"      foto    : {'sí' if pieza['tenia_foto'] else 'NO — placa sin imagen'}")
        v = pieza.get("video")
        if v and not v.get("error"):
            print(f"      video   : {v['duracion']}s · {v['peso_kb']} KB · {'+'.join(v['tramos'])}")
        elif v:
            print(f"      video   : FALLÓ — {v['error'][:60]}")
        if pieza["avisos"]:
            for a in pieza["avisos"]:
                print(f"      ⚠ {a}")
        print()

    (carpeta / "_lote.json").write_text(json.dumps({
        "generado": datetime.now().isoformat(),
        "entrada": str(entrada),
        "publicado": False,
        "nota": "FASE 1: piezas generadas para revisión. No se subió nada a ninguna red.",
        "piezas": piezas,
        # Las que no llegaron a armarse quedan anotadas igual: una nota que desaparece
        # sin dejar rastro es indistinguible de una que nunca existió.
        "descartadas": descartadas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.sin_ledger:
        # Se anota DESPUES de que las piezas salieron, no antes: si la corrida se cae a la
        # mitad, las notas que no llegaron a tener reel tienen que poder reintentarse.
        #
        # Se casa por URL y no con zip(elegidas, piezas). Desde que una nota puede
        # descartarse, las dos listas ya no van en paralelo: el zip emparejaría cada
        # nota con la pieza de OTRA y el ledger anotaría como hechas notas que no se
        # hicieron — que además se perderían para siempre, porque el ledger no las
        # volvería a ofrecer.
        hechas = {p.get("url_original") for p in piezas if p.get("placa")}
        con_pieza = [n for n in elegidas if n.get("url") in hechas]
        total = LD.registrar(con_pieza)
        print(f"Memoria actualizada: {len(con_pieza)} nota(s) anotadas, {total} en total")

    # Los intermedios de ffmpeg ya no sirven: el .mp4 está armado. Se borran acá y no al
    # otro día, que son ~2 MB por pasada sin ninguna razón para sobrevivir al video.
    if not args.sin_video:
        inter = L.borrar_intermedios(carpeta)
        if inter["borrados"]:
            print(f"Intermedios de ffmpeg borrados: {len(inter['borrados'])} archivos, "
                  f"{inter['mb']} MB liberados")

    if args.conservar_dias > 0:
        barrido = L.barrer(args.conservar_dias)
        if barrido["mb_total"]:
            print(f"Limpieza: {barrido['mb_total']} MB de corridas con más de "
                  f"{args.conservar_dias} día(s)")

    if descartadas:
        print(f"{len(descartadas)} nota(s) descartadas al armar (imagen que no bajó):")
        for d in descartadas:
            print(f"   - {str(d.get('localidad'))[:14]:<14} {str(d.get('titulo'))[:56]}")

    print(f"=== {len(piezas)} placas en {carpeta} ===")
    print("No se publicó nada. Revisá las imágenes y los .json antes del próximo paso.")
    sin_ia = [p for p in piezas if not p["apto_para_publicar"]]
    if sin_ia:
        print(f"\nOJO: {len(sin_ia)} de {len(piezas)} piezas se armaron POR REGLAS, no con IA.")
        print("Sirven para ver la estética y el flujo, pero NO son publicables: la bajada")
        print("reproduce oraciones del medio de origen en vez de resumirlas con palabras")
        print("propias. Para material publicable hace falta --con-ia y una clave: GEMINI_API_KEY")
        print("(gratis, el mismo pool que usa el bot) o, si no, ANTHROPIC_API_KEY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
