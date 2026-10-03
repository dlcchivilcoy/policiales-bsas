# -*- coding: utf-8 -*-
"""Genera los reels de una tanda y muestra qué se publicaría. ESTE PASO NO PUBLICA NADA.

    nota scrapeada → guion → reel 1080x1920 con el motor del bot → descripción → carpeta

El reel lo arma el MOTOR DEL BOT DEL DIARIO (estetica_bot/, vía reels/reel_bot.py), así
sale con su misma estética. Publicar es otro paso: reels/publicador.py.

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
from reels import cercania as CER
from reels import frescura as FR
from reels import guion as G
from reels import ilustrativa as IL
from reels import marcas as MAR
from reels import reel_bot as R
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
    # Pedido del editor (27/09): las alertas meteorológicas generan mucho tráfico.
    "alerta_meteorologica": 85,
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
    if nota.get("video"):
        p += 45      # y el VIDEO del medio más todavía (pedido del editor, 27/09)
    if (nota.get("victimas") or 0) > 0:
        p += 15
    # Cercanía a Chivilcoy (reels/cercania.py): hasta +30, así las cercanas se arman y se
    # publican primero en cada pasada.
    p += 10 * CER.bono_nota(nota)
    return p


# Puntaje mínimo para entrar en la segunda vuelta. El umbral del diccionario es 5 y
# sirve para "revisá esto"; para OCUPAR un lugar en la tanda hace falta más margen.
UMBRAL_RELLENO = 8
# Para las localidades prioritarias (y los hechos en la Ruta 5 o con Chivilcoy), la vara
# de la segunda nota es más baja, a pedido del editor (27/09): en el scrapeo de ese día
# quedaban afuera «Mercedes: la fiesta de estudiantes dejó un apuñalado» o «Escalofriante
# caso en Chacabuco», que el diccionario puntuó 6. Lo que no es policial lo frena igual
# el filtro de temario de la IA (guion.fuera_de_temario).
UMBRAL_RELLENO_CERCANAS = 6

# Cuánto del titular más corto tiene que estar contenido en el otro para darlos por el
# mismo hecho, entre notas de la MISMA localidad. 0,40 salió de medir el caso real:
# el par de Bragado da 0,43 y dos hechos distintos de una misma localidad rara vez
# pasan de 0,25.
CONTENCION_MISMA_LOCALIDAD = 0.40


# ─────────────────────────────────────────────────────────────────────────────
# CADENCIA DE PUBLICACION
# ─────────────────────────────────────────────────────────────────────────────
# Cinco minutos entre posteo y posteo. No es una preferencia estetica: subir cinco
# videos seguidos en el mismo minuto es el patron mas facil de reconocer que tiene
# una cuenta automatizada, y las redes lo tratan como spam mucho antes de mirar el
# contenido. Espaciarlos es lo que hace que una tanda parezca una redaccion
# trabajando y no un script vaciando una cola.
#
# El plan se calcula ACA, al armar la tanda, aunque todavia no exista el paso que
# publica. Dos razones: queda escrito en el lote —o sea que la pasada deja dicho a
# que hora va cada pieza, y se puede revisar antes— y el dia que se conecte TikTok
# el publicador solo tiene que leer `publicar_en`, no volver a decidir nada.
MINUTOS_ENTRE_POSTEOS = 5


def plan_de_publicacion(piezas: list, desde=None, minutos: int = MINUTOS_ENTRE_POSTEOS):
    """Le pone hora de publicacion a cada pieza, separadas `minutos` entre si.

    Solo entran las APTAS: una pieza con objeciones no ocupa un lugar en la cola.
    Si se le diera hora igual, el publicador tendria que acordarse de saltearla, y
    esa es justo la clase de detalle que se olvida.

    Devuelve la cantidad de piezas agendadas. Modifica las piezas en el lugar.
    """
    from datetime import timedelta
    desde = desde or datetime.now()
    agendadas = 0
    for p in piezas:
        if not p.get("apto_para_publicar"):
            p["publicar_en"] = None
            continue
        p["publicar_en"] = (desde + timedelta(minutes=minutos * agendadas)).isoformat(
            timespec="minutes")
        agendadas += 1
    return agendadas


# Qué pasó en el armado, SIEMPRE, aunque no se arme nada: lo lee salud.py. Sin esto, «36
# notas y 0 reels» no distinguía «no había nada nuevo» de «se rompió»: el 28/09 quedaban 2
# notas nuevas con la foto rota en el medio y la pasada salió como falla, culpando a
# Gemini o ffmpeg.
RESUMEN_PASADA = SALIDA_REELS / "_ultima_pasada.json"


def _resumen_pasada(sin_material: int = 0, ya_hechas: int = 0, nuevas: int = 0,
                    piezas: int = 0, descartadas=()):
    RESUMEN_PASADA.parent.mkdir(parents=True, exist_ok=True)
    RESUMEN_PASADA.write_text(json.dumps({
        "cuando": datetime.now().isoformat(timespec="seconds"),
        "sin_material": sin_material, "ya_hechas": ya_hechas, "nuevas": nuevas,
        "piezas": piezas, "descartadas": list(descartadas)}, ensure_ascii=False, indent=2),
        encoding="utf-8")


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
        umbral = UMBRAL_RELLENO_CERCANAS if CER.bono_nota(n) else UMBRAL_RELLENO
        if (n.get("score_keywords") or 0) < umbral:
            continue

        h = _LD._huella(n)
        # Si entra por la vara baja de las cercanas, el titular tiene que poder compararse
        # con los demás: «PRISIÓN PREVENTIVA PARA DÍAZ» (3 palabras útiles) repetía un
        # hecho ya elegido y el control de abajo no lo veía por corto.
        if (n.get("score_keywords") or 0) < UMBRAL_RELLENO and len(h) < 4:
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


_error_foto = ""       # por qué no bajó la última foto (para el motivo del descarte)


def _bajar_foto(url: str, destino: Path) -> Path | None:
    global _error_foto
    _error_foto = ""
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if r.status_code >= 400 or not r.content:
            _error_foto = f"HTTP {r.status_code}" if r.status_code >= 400 else "vino vacía"
            return None
        destino.write_bytes(r.content)
        return destino
    except Exception as e:
        _error_foto = type(e).__name__
        return None


# Una foto más chica que esto se ve pixelada estirada a 1080 de ancho, y se descarta
# (pedido del editor, 27/09: el reel de Chacabuco salió con una de 72x72, la miniatura que
# da el RSS de Blogger). Las de hoy iban de 442x248 a 1672x941.
FOTO_MIN_LADO_MAYOR = 400
FOTO_MIN_LADO_MENOR = 200


def _tamanio(ruta: Path):
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            return im.size
    except Exception:
        return None


def _foto_usable(nota: dict, destino: Path) -> tuple:
    """(ruta, url, motivo): la foto de la nota si tiene tamaño para un reel.

    Primero la de la nota con la URL mejorada (fetch.mejorar_imagen pide el tamaño
    original a WordPress, los CDN y Blogger). Si igual es chica, la foto principal de la
    página (og:image), que suele ser la grande. Si ninguna sirve: (None, "", motivo)."""
    probadas, motivo = set(), ""
    candidatas = [nota.get("imagen")]
    for i in range(2):
        for url in candidatas:
            url = fetch.mejorar_imagen(url or "")
            if not url or url in probadas:
                continue
            probadas.add(url)
            if not _bajar_foto(url, destino):
                motivo = motivo or ("La imagen que declara la nota no se pudo bajar"
                                    + (f" ({_error_foto})." if _error_foto else "."))
                continue
            t = _tamanio(destino)
            if t and max(t) >= FOTO_MIN_LADO_MAYOR and min(t) >= FOTO_MIN_LADO_MENOR:
                return destino, url, ""
            motivo = (f"La foto es demasiado chica ({t[0]}x{t[1]}): se vería pixelada."
                      if t else "La imagen que declara la nota no se pudo abrir.")
        if i == 0:                               # segunda vuelta: la foto de la página
            d = fetch.detalle(nota.get("url") or "", permitir_navegador=False)
            candidatas = [d.get("imagen")] if d.get("ok") else []
    destino.unlink(missing_ok=True)
    return None, "", motivo or "La nota no trae imagen."


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


# Sin marcas de medio en el reel (pedido del editor, 03/10/2026). Ver reels/marcas.py.
SEGUNDOS_CUADROS_MARCA = (0.5, 3.0)   # el logo de un video suele estar fijo: dos cuadros alcanzan
MAX_ALTERNATIVAS = 3                  # fotos de otros medios a probar antes de la ilustrativa


def _clip_sin_marca(clip: Path, tmp_dir: Path, idx: int) -> tuple:
    """(clip o None, aviso, ¿tenía marca?). Mira dos cuadros del video en una sola consulta."""
    cuadros = [c for c in (R.cuadro_de_video(clip, tmp_dir / f"reel_marca_{idx}_{k}.jpg", s)
                           for k, s in enumerate(SEGUNDOS_CUADROS_MARCA)) if c]
    if not MAR.activo():
        return clip, "", False
    r = MAR.revisar(cuadros)
    if r["marca"]:
        return None, f"El video del medio trae una marca ({r['que']}): no se usa.", True
    if r["marca"] is None:
        return clip, f"No se pudo revisar si el video trae marca: {r['que']}.", False
    return clip, "", False


def _imagen_sin_marca(nota: dict, foto, url: str, tmp_dir: Path, idx: int) -> tuple:
    """(foto, url, ¿ilustrativa?, avisos): la imagen del reel, sin la marca de ningún medio.

    1. La foto de la nota, si no trae marca (o si no se pudo revisar: el control es un
       filtro y no deja la pasada sin reels).
    2. La foto de la MISMA noticia publicada por otro medio (`alternativas`, ver
       _con_alternativas), solo si se confirmó que no trae marca.
    3. Una imagen ilustrativa propia (reels/ilustrativa.py).
    `foto` llega en None cuando la nota no tenía foto y el video se cayó por la marca."""
    avisos = []
    if foto:
        if not MAR.activo():
            return foto, url, False, []
        r = MAR.revisar([foto])
        if r["marca"] is None:
            return foto, url, False, [f"No se pudo revisar si la foto trae marca: {r['que']}."]
        if not r["marca"]:
            return foto, url, False, []
        avisos.append(f"La foto del medio trae una marca ({r['que']}): no se usa.")
    for k, alt in enumerate((nota.get("alternativas") or [])[:MAX_ALTERNATIVAS]):
        otra, otra_url, _ = _foto_usable(alt, tmp_dir / f"reel_foto_{idx}_alt{k}.jpg")
        if otra and MAR.revisar([otra])["marca"] is False:
            avisos.append(f"Va la foto de la misma noticia publicada por "
                          f"{alt.get('medio') or 'otro medio'}, que no trae marca.")
            return otra, otra_url, False, avisos
    ilus = IL.generar(nota.get("tipo") or G.inferir_tipo(nota),
                      tmp_dir / f"reel_ilustrativa_{idx}.jpg", semilla=nota.get("url") or "")
    avisos.append("Ninguna imagen de la noticia está libre de marca: va una imagen ilustrativa.")
    return ilus, "", True, avisos


def _con_alternativas(candidatas: list, notas: list) -> list:
    """A cada candidata le anota las OTRAS versiones del mismo hecho (otros medios, con su
    foto): si la foto de la elegida trae el logo de su medio, de ahí sale una limpia. Mismo
    criterio de «mismo hecho» que la memoria (ledger._se_parecen sobre el titular)."""
    versiones = [(n, LD._huella(n), LD.identidad(LD._clave(n))) for n in notas if n.get("imagen")]
    salida = []
    for c in candidatas:
        hc, ic = LD._huella(c), LD.identidad(LD._clave(c))
        alt = [{"imagen": n["imagen"], "url": n.get("url"), "medio": n.get("medio")}
               for n, h, i in versiones
               if i != ic and n["imagen"] != c.get("imagen") and LD._se_parecen(hc, h)]
        salida.append(dict(c, alternativas=alt) if alt else c)
    return salida


def procesar(nota: dict, carpeta: Path, usar_ia: bool, idx: int,
             hacer_video: bool = True, preferir: str = "") -> dict:
    """Una nota → guion + placa + descripción. Devuelve el informe de la pieza."""
    # La imagen PRIMERO y el guion después, aunque parezca al revés. Si la nota se
    # queda sin imagen, la pieza no se arma; redactando antes se habría gastado una
    # llamada a la IA para un guion que nadie va a usar.
    #
    # El VIDEO tiene prioridad sobre la foto: un reel con imágenes en movimiento
    # retiene mucho más que una foto quieta. Si el medio publicó uno propio,
    # ese va al reel y la foto queda de respaldo.
    tmp_dir = Path(tempfile.gettempdir())
    clip = _bajar_video(nota.get("video") or "", tmp_dir / f"reel_clip_{idx}.mp4")

    tmp = tmp_dir / f"reel_foto_{idx}.jpg"
    foto = None
    if clip and not R.cuadro_de_video(clip, tmp_dir / f"reel_cuadro_{idx}.jpg"):
        clip = None          # un video del que no sale ni un cuadro no se puede usar
    # Ni el video ni la foto pueden llevar el logo del medio (pedido del editor, 03/10):
    # la imagen con marca no se usa —no se borra ni se tapa la marca— y se busca otra.
    avisos_imagen, clip_con_marca = [], False
    if clip:
        clip, aviso, clip_con_marca = _clip_sin_marca(clip, tmp_dir, idx)
        if aviso:
            avisos_imagen.append(aviso)
    # La foto se baja igual aunque haya video: si el motor no puede con el clip, el
    # reel se arma con la foto en vez de perder la pieza.
    foto, imagen_usada, sin_foto = _foto_usable(nota, tmp)
    ilustrativa = False
    if foto or clip_con_marca:
        foto, imagen_usada, ilustrativa, avs = _imagen_sin_marca(nota, foto, imagen_usada,
                                                                 tmp_dir, idx)
        avisos_imagen += avs

    # El filtro de la tanda mira que la nota DECLARE una imagen; esto comprueba que la
    # imagen realmente se pueda bajar y tenga tamaño. Un enlace roto, un 403 o una
    # miniatura de 72x72 dejan la placa igual de mal que no tener foto: no se arma.
    if not foto and not clip:
        return {"orden": idx, "descartada": True,
                "por_que_no": sin_foto,
                "localidad": nota.get("localidad_medio"), "medio": nota.get("medio"),
                "titulo": nota.get("titulo"), "url_original": nota.get("url")}

    nota = material(nota)
    g = G.generar(nota, usar_ia=usar_ia, preferir=preferir, sitio=SITIO)

    nombre = f"{idx:02d}_{_slug(nota.get('localidad_medio'))}_{_slug(g['titular'], 30)}"
    img = carpeta / f"{nombre}.jpg"
    avisos = list(avisos_imagen)
    # Que el hecho sea de otra localidad que la del medio no rompe la pieza, pero hay
    # que verlo: cambia la volanta, el hashtag y el "Más noticias de" del posteo.
    if g.get("aviso_localidad"):
        avisos.append(g["aviso_localidad"])

    # El reel y su cuadro fijo los arma el MOTOR DEL BOT (reels/reel_bot.py): la misma
    # estética que los reels del diario, decidida en el bot. El .jpg queda al lado del .mp4.
    vid = None
    # Lo que la IA dijo que no es policial no se va a publicar: no vale la pena armarle
    # el video (ni subirlo como artefacto). Queda el JSON con el motivo.
    if hacer_video and not g.get("fuera_de_temario"):
        try:
            vid = R.armar(g, carpeta / f"{nombre}.mp4", foto=None if clip else foto, clip=clip)
        except R.ReelError as e:
            vid = {"error": str(e)}
            if clip and foto:
                try:
                    vid = R.armar(g, carpeta / f"{nombre}.mp4", foto=foto)
                    avisos.append(f"El video del medio no se pudo usar ({e}); va la foto.")
                except R.ReelError as e2:
                    vid = {"error": str(e2)}
    elif foto:
        try:
            R.placa_fija(g, foto, img)
        except Exception as e:
            avisos.append(f"No se pudo armar la vista fija: {type(e).__name__}: {e}")

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
    # (El zócalo ya no se chequea: la estética del bot no lo dibuja.)
    for campo, minimo in (("titular", 15), ("volanta", 3), ("bajada", 25)):
        if len((g.get(campo) or "").strip()) < minimo:
            objeciones.append(f"El campo '{campo}' quedo vacio o demasiado corto: "
                              f"en la placa se ve como un hueco.")

    # La tercera: que SEA del temario. El diccionario del scraper deja pasar notas que no
    # son policiales (el 27/09, una alerta meteorológica); la IA, que lee la nota entera
    # para redactar, lo decide en la misma llamada. Ver guion.fuera_de_temario().
    if g.get("fuera_de_temario"):
        objeciones.append(f"No es del temario de policiales (según la IA): "
                          f"{g['fuera_de_temario']}")

    # La cuarta: que no se note la copia (pedido del editor, 03/10). guion.guion_ia ya le
    # pidió a la IA que reescribiera lo calcado; si aun así quedó una frase larga del medio,
    # no sale. Un tramo más corto o el nombre del medio quedan como aviso.
    copia = g.get("copia") or {}
    if copia.get("racha", 0) >= G.UMBRAL_COPIA_BLOQUEO:
        objeciones.append(f"El {copia['campo']} copia {copia['racha']} palabras seguidas de la "
                          f"nota original («{copia['tramo'][:90]}»), aun después de pedir que "
                          f"lo reescriba.")
    elif copia.get("racha", 0) >= G.UMBRAL_COPIA:
        avisos.append(f"El {copia['campo']} repite {copia['racha']} palabras seguidas del "
                      f"original: «{copia['tramo'][:90]}».")
    if copia.get("nombra_medio"):
        avisos.append("El texto nombra al medio de origen.")

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
        "imagen_ilustrativa": ilustrativa,
        "guion": {k: g[k] for k in ("volanta", "titular", "bajada", "zocalo", "pie", "via")},
        "copia": copia,
        "descripcion_tiktok": g["descripcion_final"],
        # Para la nota de la web (reels/web.py) y para elegir qué va a Instagram.
        "viral": g.get("viral", 5),
        "web": {"titulo": g.get("titulo_web") or g["titular"],
                "cuerpo": g.get("nota_web") or g["bajada"]},
        # Solo la imagen que se REVISÓ: nunca la de la nota a ciegas, que puede traer el logo
        # del medio. Vacía (imagen ilustrativa, o la foto no bajó), la nota de la web lleva
        # el cuadro del propio reel (publicador._paso_web).
        "imagen_url": imagen_usada or "",
        "localidad_hecho": g.get("localidad_hecho") or nota.get("localidad") or "",
        # Hora de publicación en el medio (UTC): Facebook e Instagram llevan la del momento.
        "publicado": FR.publicado_utc(nota),
        "placa": str(img),
        "video": vid,
        "estetica": f"bot {R.origen()}",
        "avisos": avisos,
    }
    # La ruta queda guardada porque este archivo se reescribe mas tarde, cuando se
    # calcula el plan de publicacion: la hora de cada pieza se sabe recien al final,
    # con la tanda entera armada, y tiene que quedar tambien en el .json de la pieza
    # y no solo en el lote.
    pieza["_json"] = str(carpeta / f"{nombre}.json")
    (carpeta / f"{nombre}.json").write_text(
        json.dumps(pieza, ensure_ascii=False, indent=2), encoding="utf-8")
    return pieza


def main():
    ap = argparse.ArgumentParser(description="FASE 1 — genera reels de policiales. NO publica.")
    ap.add_argument("--cuantos", type=int, default=5,
                    help="cuántos reels generar; 0 = TODAS las notas que sirvan (sin tope)")
    ap.add_argument("--localidad", help="filtra por localidad (separadas por coma)")
    ap.add_argument("--con-ia", action="store_true",
                    help="el guion lo redacta la IA (Gemini gratis si hay claves; si no, Claude)")
    ap.add_argument("--proveedor", choices=["gemini", "claude"], default="",
                    help="forzar proveedor. Vacío = Gemini si hay claves (gratis)")
    ap.add_argument("--cadencia", action="store_true",
                    help=f"agendar las piezas cada {MINUTOS_ENTRE_POSTEOS} min "
                         f"(para la automatizacion; en una corrida manual no hace falta)")
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

    faltan = R.faltantes()
    if faltan:
        print(f"OJO: al motor de reels del bot le falta: {', '.join(faltan)}. "
              f"Traelo con  venv\\Scripts\\python.exe tools\\traer_estetica_bot.py")

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
        _resumen_pasada(sin_material=sin_material)
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

    # Las otras versiones de cada hecho, para tener una foto sin marca de respaldo.
    candidatas = _con_alternativas(candidatas, notas)

    # 0 = sin tope, decidido por el editor el 27/09/2026: ni por pueblo ni por día. Lo
    # único que sigue afuera es lo que elegir() descarta por calidad (lo que entró
    # raspando el diccionario) y el mismo hecho contado dos veces.
    cuantos = args.cuantos if args.cuantos > 0 else len(candidatas)
    elegidas = elegir(candidatas, cuantos, args.localidad or "")
    if not elegidas:
        print("No quedan notas nuevas para hacer reel (o ninguna coincide con el filtro).")
        _resumen_pasada(sin_material=sin_material, ya_hechas=repetidas)
        return 0
    # Se arman y se publican en orden de llegada al medio, la más nueva primero (pedido
    # del editor, 27/09): lo del momento sale al principio de la pasada.
    elegidas = FR.ordenar(elegidas)

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
        print(f"      viral   : {pieza.get('viral')}/10 · web: {pieza['web']['titulo'][:62]}")
        print(f"      foto    : {'sí' if pieza['tenia_foto'] else 'no'}"
              f"{' · video del medio' if pieza['tenia_video'] else ''}")
        v = pieza.get("video")
        if v and not v.get("error"):
            print(f"      video   : {v['duracion']}s · {v['peso_kb']} KB · {'+'.join(v['tramos'])}")
        elif v:
            print(f"      video   : FALLÓ — {v['error'][:60]}")
        if not pieza["apto_para_publicar"]:
            print(f"      NO SE PUBLICA — {pieza['por_que_no'][:110]}")
        if pieza["avisos"]:
            for a in pieza["avisos"]:
                print(f"      ⚠ {a}")
        print()

    # La cadencia NO se aplica en las corridas manuales, que es como corre esto hoy:
    # una vista previa se mira toda junta, y ponerle horarios a algo que se revisa a
    # mano solo confunde. Los 5 minutos son para el dia que exista el paso que publica
    # solo — ahi la automatizacion pasa --cadencia y cada pieza sale con su hora.
    agendadas = plan_de_publicacion(piezas) if args.cadencia else 0
    for pz in piezas:                       # que la hora quede tambien en cada pieza
        ruta = pz.pop("_json", None)
        if ruta:
            Path(ruta).write_text(json.dumps(pz, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    if agendadas:
        ultima = max(p["publicar_en"] for p in piezas if p.get("publicar_en"))
        print(f"Plan de publicación: {agendadas} pieza(s), una cada "
              f"{MINUTOS_ENTRE_POSTEOS} minutos, la última {ultima[11:]}.")

    (carpeta / "_lote.json").write_text(json.dumps({
        "generado": datetime.now().isoformat(),
        "entrada": str(entrada),
        "publicado": False,
        "nota": "FASE 1: piezas generadas para revisión. No se subió nada a ninguna red.",
        "minutos_entre_posteos": MINUTOS_ENTRE_POSTEOS,
        "piezas": piezas,
        # Las que no llegaron a armarse quedan anotadas igual: una nota que desaparece
        # sin dejar rastro es indistinguible de una que nunca existió.
        "descartadas": descartadas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    _resumen_pasada(sin_material=sin_material, ya_hechas=repetidas, nuevas=len(elegidas),
                    piezas=len(piezas), descartadas=[d.get("por_que_no") or "" for d in descartadas])

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
