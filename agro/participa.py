# -*- coding: utf-8 -*-
"""LA HISTORIA QUE INVITA A PARTICIPAR (06/11/2026, pedido del editor: «sumar fotos y videos de seguidores […] hacelo
con historias generadas con IA»). Una por día: una pregunta a la gente del campo sobre una imagen generada con IA.

La pregunta la escribe la IA según la fecha y la lluvia prevista; si no contesta, sale una de RESPALDO. La imagen es
solo un fondo que ilustra: lo dice la placa y lo dicen los metadatos (reel_datos.marcar_ia). Nunca se presenta como
la foto de un seguidor.

La API de Instagram no permite stickers de encuesta ni de pregunta: se contesta respondiendo la historia, y esas
respuestas llegan a los mensajes de la cuenta. Publicar lo que manden es decisión del editor: acá no se automatiza.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from agro import diseno as D
from agro import historias as HI

MAX_PREGUNTA = 70
RECORDAR = 10                  # no repetir las últimas preguntas
INVITACION = "Respondé esta historia con tu foto o tu dato, y contanos de qué pueblo sos"
AVISO_IA = "Imagen ilustrativa generada con IA"
RESPALDO = (
    {"pregunta": "¿Cómo está tu lote esta semana?", "escena": "Rows of young soybean plants in dark soil in the Argentine pampas, morning light"},
    {"pregunta": "¿Cuánto llovió en tu campo?", "escena": "Rain gauge on a wooden fence post beside a green crop field under dark rain clouds, no numbers visible"},
    {"pregunta": "¿Cómo viene la siembra en tu zona?", "escena": "Planted furrows in dark soil stretching to the horizon in the pampas at sunrise"},
    {"pregunta": "¿Cómo está el trigo por tu zona?", "escena": "Golden wheat heads close up in a large field under a dramatic sky in the pampas"},
    {"pregunta": "¿Cómo viene la hacienda en tu campo?", "escena": "Black Angus cattle grazing on green pampas grassland at sunset"},
    {"pregunta": "¿Cómo quedaron los caminos rurales?", "escena": "Muddy dirt country road between green crop fields after the rain, puddles, wire fence"},
    {"pregunta": "¿Qué se está haciendo hoy en tu campo?", "escena": "Tractor far away working a wide field at dusk, unbranded, dust in the air"},
)
SYSTEM = """Sos quien maneja @diarioyradioagro, la cuenta del campo de Chivilcoy y su zona (provincia de Buenos
Aires). Escribí UNA pregunta para una historia de Instagram que invite a productores, contratistas y gente de campo a
contestar con una foto o un dato de lo que está pasando en su lugar.

Reglas:
- Una sola pregunta, en voseo, directa, de hasta 60 caracteres. Tiene que poder contestarla cualquiera que esté en el
  campo hoy. Que tenga que ver con la época del año y, si te lo indican, con la lluvia prevista. Usá palabras
  comunes (lote, campo, siembra, cosecha, hacienda, lluvia): nada rebuscado.
- No afirmes hechos ni des cifras, nombres, precios ni pronósticos: solo preguntá. Tampoco des por hecho cómo está
  el clima o el campo (nada de «con esta seca» o «con tanta agua»): cada zona está distinta, la pregunta es abierta.
- Nada de política, retenciones ni impuestos: tiene que ser fácil y amable de contestar.
- No repitas ninguna de las preguntas recientes.
- «escena»: una escena en INGLÉS para generar la imagen de fondo, del campo pampeano, que ilustre la pregunta:
  cultivos, suelo, cielo o animales. Sin máquinas de cerca (traen letras), sin personas de frente, sin carteles,
  sin textos, sin marcas, sin números.

Contestá SOLO un JSON: {"pregunta": "...", "escena": "..."}"""


def recientes(mem: dict) -> list:
    return [i.get("pregunta") for _k, h in sorted((mem.get("historias") or {}).items())
            if h.get("bloque") == "participa" for i in h.get("items") or [] if i.get("pregunta")][-RECORDAR:]


def respaldo(ya: list, momento: datetime, lluvia_mm=None) -> dict:
    """Una de la lista: la de la lluvia si se espera lluvia; si no, siguiendo el calendario, sin repetir."""
    if lluvia_mm is not None and lluvia_mm >= 5 and RESPALDO[1]["pregunta"] not in ya:
        return RESPALDO[1]
    k = momento.date().toordinal()
    opciones = [RESPALDO[(k + i) % len(RESPALDO)] for i in range(len(RESPALDO))]
    return next((o for o in opciones if o["pregunta"] not in ya), opciones[0])


def texto_valido(d) -> bool:
    if not isinstance(d, dict):
        return False
    p, e = " ".join(str(d.get("pregunta") or "").split()), " ".join(str(d.get("escena") or "").split())
    return bool(p and e) and p.startswith("¿") and p.endswith("?") and p.count("?") == 1 and len(p) <= MAX_PREGUNTA \
        and not any(c.isdigit() for c in p)


def pregunta_del_dia(momento: datetime, ya: list, lluvia_mm=None, redactar=None, log=print) -> dict:
    """{pregunta, escena, via}. La IA, o la lista si no contesta o contesta algo que no sirve."""
    if redactar is None:
        from reels import ia
        redactar = ia.redactar
    material = (f"Fecha: {HI.fecha_larga(momento.date())}.\n"
                + (f"Lluvia prevista en Chivilcoy en las próximas 72 horas: {lluvia_mm:.0f} mm.\n" if lluvia_mm is not None else "")
                + "Preguntas recientes (no repetir): " + (" | ".join(ya) or "ninguna"))
    try:
        datos, via = redactar(SYSTEM, material, max_tokens=500)
        if texto_valido(datos) and " ".join(datos["pregunta"].split()) not in ya:
            return {"pregunta": " ".join(datos["pregunta"].split()), "escena": " ".join(datos["escena"].split()), "via": via}
        log("   la pregunta de la IA no sirve: va una de la lista")
    except Exception as e:                                 # noqa: BLE001 — sin IA, sale igual
        log(f"   la IA no escribió la pregunta ({type(e).__name__}): va una de la lista")
    return dict(respaldo(ya, momento, lluvia_mm), via="lista")


def imagen_de_fondo(escena: str, destino: Path, semilla: str, generar=None, mirar=None, log=print) -> str:
    """La escena generada con IA, sin letras; si no se puede, una del banco de imágenes IA ya revisadas."""
    from agro import imagen as IMG
    if generar is None:
        from archivo import imagen as IM
        generar = lambda p, d: IM.generar(p, d, estilo=IMG.ESTILO)      # noqa: E731
        mirar = mirar or IM.tiene_texto
    destino = Path(destino)
    for intento in range(2):
        r = generar(escena, destino)
        if r.get("archivo") and not (mirar and mirar(r["archivo"])):
            return r["archivo"]
        log(f"   imagen IA, intento {intento + 1}: {r.get('motivo') or 'tiene letras'}")
    return IMG.del_banco("agro", semilla)


def placa(pregunta: str, fondo: str, destino: Path) -> Path:
    """1080x1920, con todo adentro de la zona segura: lo tapan arriba la cuenta y abajo la caja de respuesta."""
    W, H = HI.W, HI.H
    im = Image.new("RGBA", (W, H), HI.FONDO + (255,))
    if fondo and Path(fondo).exists():
        im.alpha_composite(D.cubrir(Image.open(fondo).convert("RGB"), W, H).convert("RGBA"))
    velo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dv = ImageDraw.Draw(velo)
    for y in range(H):
        a = 70 + round(150 * min(1.0, max(0.0, (y - H * 0.28) / (H * 0.32))))
        dv.line((0, y, W, y), fill=HI.FONDO + (a,))
    im.alpha_composite(velo)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 8), fill=D.NARANJA)
    lg = D.lockup("grafito", 60)
    im.alpha_composite(lg, (D.X, HI.SEGURA[0]))
    # El bloque de texto se apoya sobre el final de la zona segura.
    ancho = W - 2 * D.X
    fp, rp = D.ajustar(d, pregunta, "negra", 112, 70, ancho, 4)
    fi, ri = D.ajustar(d, INVITACION, "medium", 44, 34, ancho, 3)
    fa = D.fuente("regular", 26)
    alto = 48 + 26 + round(len(rp) * fp.size * 1.14) + 34 + round(len(ri) * fi.size * 1.24) + 34 + 34
    y = HI.SEGURA[1] - alto
    caja = "PARTICIPÁ"
    fc = D.fuente("bold", 28)
    d.rectangle((D.X, y, D.X + d.textlength(caja, font=fc) + 32, y + 48), fill=D.NARANJA_CAJA)
    d.text((D.X + 16, y + 8), caja, font=fc, fill=D.BLANCO)
    y += 48 + 26
    y = D.escribir(d, D.X, y, rp, fp, D.BLANCO, 1.14) + 34
    y = D.escribir(d, D.X, y, ri, fi, (232, 235, 240), 1.24) + 34
    d.text((D.X, y), AVISO_IA, font=fa, fill=(190, 195, 202))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(destino, "JPEG", quality=92)
    return destino


def _lluvia_prevista(momento: datetime) -> float | None:
    """Los mm previstos en Chivilcoy para las próximas 72 horas, o None."""
    from datetime import timezone
    from agro import mapa_lluvia as ML
    serie = ML._pedir_met(*ML.CENTRO)
    if not serie:
        return None
    desde = momento.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return ML.sumar(serie, desde, desde + timedelta(hours=ML.HORAS))[0]


def pasada(publicar: bool, horario: datetime, log=print, publicador=None, carpeta: Path = None, ahora: datetime = None,
           lluvia_mm="leer", redactar=None, generar=None, mirar=None) -> Path:
    """El turno de la agenda. Se anota junto a las historias (estado/agro.json, «historias», bloque «participa»):
    guardar_estado ya las combina y el respaldo de las :20 no la repite."""
    from agro import informe as INF
    from agro import pasada as PA
    from agro import reel_datos as RD
    ahora = ahora or datetime.now(PA.TZ_AR)
    carpeta = Path(carpeta or PA.SALIDA / ahora.strftime("%Y-%m-%d_%H%M_participa"))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = PA.MEMORIA_REAL if publicar else PA.MEMORIA
    mem = PA.cargar(ruta_mem)
    log(f"[agro] HISTORIA PARA PARTICIPAR {'REAL' if publicar else 'SIMULADA'} {ahora:%d/%m %H:%M} → {carpeta}")
    if lluvia_mm == "leer":
        try:
            lluvia_mm = _lluvia_prevista(ahora)
        except Exception:                                  # noqa: BLE001 — sin el dato, pregunta igual
            lluvia_mm = None
    txt = pregunta_del_dia(ahora, recientes(mem), lluvia_mm, redactar, log)
    log(f"   «{txt['pregunta']}» ({txt['via']})")
    fondo = imagen_de_fondo(txt["escena"], carpeta / "participa_fondo.jpg", ahora.date().isoformat(), generar, mirar, log)
    archivo = RD.marcar_ia(placa(txt["pregunta"], fondo, carpeta / "historia_00_participa.jpg"))
    tanda = [{"tipo": "participa", "clave": "participa", "archivo": str(archivo), "pregunta": txt["pregunta"], "via": txt["via"]}]
    registro = {"dia": ahora.date().isoformat(), "bloque": "participa", "items": [dict(t) for t in tanda]}
    mem.setdefault("historias", {})
    if publicar:
        if publicador is None:
            from agro import publicar as PUB
            publicador = PUB.publicar_historias
        registro["publicado"] = {"estado": "publicando"}
        mem["historias"][horario.isoformat()] = registro
        PA.guardar(mem, ahora, ruta_mem)
        res = publicador(tanda, log=log)
        registro["publicado"] = {"estado": "listo", "resultado": res}
        for item, r in zip(registro["items"], res.get("items") or []):
            item["publicado"] = r
    else:
        mem["historias"][horario.isoformat()] = dict(registro, simulado=True)
    for it in registro["items"]:
        it.pop("archivo", None) if publicar else None
    PA.guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "historia para participar", "bloque": "participa",
           "conteos": {"Historias": 1}, "historias": tanda, "fuentes": [], "piezas": [], "descartadas": [],
           "grupos_duplicados": [], "config": {"score_min": "—", "max_dia": "—", "horas": 0}, "publicar": publicar,
           "resultado": registro.get("publicado")}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)
