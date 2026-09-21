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
        loc = (n.get("localidad_medio") or "").lower()
        if loc in vistas:
            continue
        vistas.add(loc)
        elegidas.append(n)
        if len(elegidas) >= cuantos:
            return elegidas
    for n in ordenadas:                      # segunda: completar si faltan
        if n not in elegidas:
            elegidas.append(n)
        if len(elegidas) >= cuantos:
            break
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
    nota = material(nota)
    g = G.generar(nota, usar_ia=usar_ia, preferir=preferir, sitio=SITIO)

    tmp = Path(tempfile.gettempdir()) / f"reel_foto_{idx}.jpg"
    foto = _bajar_foto(nota.get("imagen") or "", tmp)

    nombre = f"{idx:02d}_{_slug(nota.get('localidad_medio'))}_{_slug(g['titular'], 30)}"
    img = carpeta / f"{nombre}.jpg"
    informe = P.componer(g, foto, img, capas=hacer_video)
    avisos = P.auditar(informe)

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
    apto = g.get("via", "").startswith(("claude", "gemini"))
    pieza = {
        "orden": idx,
        "apto_para_publicar": apto,
        "por_que_no": "" if apto else (
            "Guion armado por reglas: la bajada reproduce oraciones del medio de origen y "
            "el zocalo es un recorte del titular. Hay que generarlo con --con-ia."),
        "localidad": nota.get("localidad_medio"),
        "medio": nota.get("medio"),
        "tipo": nota.get("tipo") or g.get("tipo") or "(sin clasificar)",
        "gravedad": nota.get("gravedad") or "(sin clasificar)",
        "puntaje": round(_puntaje(nota), 1),
        "url_original": nota.get("url"),
        "tenia_foto": bool(foto),
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

    faltan = M.faltantes()
    if faltan:
        print(f"OJO: faltan assets de marca: {', '.join(faltan)}")

    entrada = Path(args.entrada) if args.entrada else _ultimo_scrapeo()
    if not entrada or not entrada.exists():
        print("No hay salida de scrapeo. Corré primero:  python -m scraper.run --sin-ia")
        return 1

    notas = json.loads(entrada.read_text(encoding="utf-8"))["notas"]
    print(f"=== FASE 1 — generación de reels (NO se publica nada) ===")
    print(f"Entrada: {entrada.name} ({len(notas)} notas policiales)\n")

    # Memoria entre pasadas: las tres corridas del dia miran ventanas que se superponen,
    # asi que sin esto la nota fuerte de la manana volveria a salir a la tarde y a la noche.
    if args.sin_ledger:
        print("--sin-ledger: no se consulta la memoria de notas ya usadas.")
        candidatas = notas
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

    piezas = []
    for i, nota in enumerate(elegidas, 1):
        print(f"[{i}/{len(elegidas)}] {nota.get('localidad_medio', '?')} — "
              f"{(nota.get('titulo') or '')[:58]}")
        pieza = procesar(nota, carpeta, args.con_ia, i, hacer_video=not args.sin_video,
                         preferir=args.proveedor)
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
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.sin_ledger:
        # Se anota DESPUES de que las piezas salieron, no antes: si la corrida se cae a la
        # mitad, las notas que no llegaron a tener reel tienen que poder reintentarse.
        con_pieza = [n for n, p in zip(elegidas, piezas) if p.get("placa")]
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
