# -*- coding: utf-8 -*-
"""La imagen de cada pieza (punto 14 del documento y decisión del editor del 13/10/2026: «mixto»).

  - Fuente OFICIAL o de PRENSA (INTA, Secretaría, gacetillas de fabricantes para difusión): se usa
    su foto, con el crédito («Foto: INTA»), SI es una foto de verdad: de al menos MIN_ANCHO px y sin
    letras. La Bolsa de Comercio de Rosario publica placas y gráficos de 500 px con texto: su fuente
    lleva `"foto": False` y va directo a la IA.
  - Fuente que es OTRO MEDIO: su foto NO se republica (derechos). Va una imagen ilustrativa generada
    con IA (Cloudflare FLUX, gratis: la misma cuenta del Archivo) con la leyenda que lo avisa.
  - Fuente que es OTRO MEDIO, desde el 17/10/2026 (pedido del editor: «tratar de utilizar la imagen de la
    fuente; podés modificarla con IA para evitar el copyright»): su foto se RECREA con IA (Cloudflare
    FLUX.2 klein, que edita a partir de una imagen): la misma escena y el mismo sujeto, con otro encuadre,
    otro ángulo y otra luz, sin letras ni logos. Queda una imagen nueva, fiel a la noticia, con la leyenda
    «Imagen generada con IA». La foto original nunca se publica.
  - NUNCA sale la portada con el logo suelto (pedido del editor, 13/10/2026). Si la IA dibuja letras
    o no contesta: (1) la escena de la nota, dos intentos; (2) una ESCENA SEGURA del subtema, sin
    máquinas, carteles ni edificios (lo que trae letras); (3) una imagen del BANCO: fotos IA ya
    revisadas, varias por subtema, en agro/marca/banco/ (se arman con `python -m agro.imagen --banco`).

La URL de la foto original se guarda siempre (trazabilidad), aunque no se use.

FOTO ORIGINAL PRIMERO (18/10/2026, pedido del editor: «lo de agro activalo, pero tratá de usar la imagen
original si podés, siempre»). La foto del OTRO MEDIO se usa TAL CUAL si sirve (bajó, tamaño, sin letras y
no es de una agencia que factura cada foto: AP, AFP, Reuters, EFE…), con su crédito. Solo si no sirve se
recrea con IA y después se sigue como arriba (escena, escena segura, banco).

AGRO_IMAGEN_IA=0 apaga la IA: solo la foto original; sin ella la pieza no sale (agro/pasada.py la repone
y deja afuera antes del puntaje lo que solo cuentan otros medios sin foto).
"""
import base64
import io
import os
import time
from pathlib import Path

import httpx

MODELO_RECREAR = "@cf/black-forest-labs/flux-2-klein-4b"   # ~130 neuronas por imagen 1024x768
URL_CF = "https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/run/"
MIN_ANCHO_RECREAR = 400     # más chica no sirve ni de referencia
RECREAR = ("Recreate this news photograph as a NEW original photo of the same scene: the same place, the same kind "
           "of subject and the same elements, seen from a slightly different camera angle and framing, with different "
           "light. Do NOT add people, animals, vehicles or objects that are not in the original. If there are people, "
           "give them different faces and clothes. Realistic and natural, like a press photo taken by another "
           "photographer. Remove every text, letter, number, logo, watermark, label, sign and screen with writing.")
RECREAR_2 = ("Photograph the same subject and setting from a different side, natural daylight, realistic editorial "
             "photo, without adding anything new. Absolutely no text, letters, numbers, logos, tags with writing or signs.")


def recrear(foto, destino: Path, contexto: str = "", pedir=None, variante: int = 0) -> dict:
    """Una imagen NUEVA de la misma escena a partir de la foto de la fuente (Cloudflare FLUX.2 klein):
    {archivo} o {motivo}. Nunca lanza ni muestra el token."""
    cuenta = (os.environ.get("CF_ACCOUNT_ID") or "").strip()
    token = (os.environ.get("CF_API_TOKEN") or "").strip()
    if not cuenta or not token:
        return {"motivo": "faltan CF_ACCOUNT_ID / CF_API_TOKEN"}
    from PIL import Image
    try:
        with Image.open(foto) as im:
            im = im.convert("RGB")
    except Exception:                                      # noqa: BLE001
        return {"motivo": "la foto de la fuente no se pudo abrir"}
    if im.width < MIN_ANCHO_RECREAR:
        return {"motivo": f"la foto de la fuente es muy chica ({im.width} px)"}
    from agro import diseno as D
    im = D.cubrir(im, 1024, 768) if im.width / im.height < 1.6 else D.cubrir(im, 1024, 768, zoom=1.0)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    prompt = (RECREAR if variante == 0 else RECREAR_2) + (f" Scene: {contexto[:400]}" if contexto else "")
    pedir = pedir or (lambda url, **kw: httpx.post(url, timeout=120, **kw))
    ultimo = ""
    for intento, espera in enumerate((0, 8, 25)):
        if espera:
            time.sleep(espera)
        try:
            r = pedir(URL_CF.format(cuenta=cuenta) + MODELO_RECREAR, headers={"Authorization": f"Bearer {token}"},
                      files={"prompt": (None, prompt), "input_image_0": ("fuente.jpg", buf.getvalue(), "image/jpeg"),
                             "width": (None, "1024"), "height": (None, "768")})
        except httpx.HTTPError as e:
            ultimo = type(e).__name__
            continue
        if r.status_code != 200:
            ultimo = f"HTTP {r.status_code}"
            if r.status_code in (429, 500, 502, 503, 504):
                continue
            break
        try:
            crudo = base64.b64decode((r.json().get("result") or {}).get("image") or "")
            with Image.open(io.BytesIO(crudo)) as nueva:
                Path(destino).parent.mkdir(parents=True, exist_ok=True)
                nueva.convert("RGB").save(destino, "JPEG", quality=92)
            return {"archivo": str(destino), "modelo": MODELO_RECREAR}
        except Exception:                                  # noqa: BLE001
            ultimo = "Cloudflare contestó sin imagen"
    return {"motivo": f"Cloudflare (recrear): {ultimo}"}


MIN_ANCHO = 900         # una foto más chica se ve borrosa a 1080 de ancho
BANCO = Path(__file__).resolve().parent / "marca" / "banco"

# Escenas sin nada que suela traer letras (máquinas de cerca, carteles, envases, edificios).
SEGURAS = {
    "agro": ["Wide view of a green soybean field with trifoliate leaves in the pampas at golden hour",
             "Golden wheat field with heads of grain under a dramatic sky in the Argentine pampas",
             "Rows of young corn plants in dark fertile soil, low angle, morning light, no ears yet"],
    "mercados": ["Close-up of a pile of golden soybeans and corn kernels, soft daylight",
                 "Close-up of golden wheat grains heaped in a wooden bowl, soft window light",
                 "Long white silo bags lying in a harvested field under a blue sky, seen from far"],
    "agtech": ["Close-up of a soil moisture sensor probe in a green crop field, morning dew",
               "Agricultural drone flying over a green crop field, seen from below, blue sky",
               "Close-up of healthy soybean leaves with water droplets, macro, natural light"],
    "maquinaria": ["Silhouette of a combine harvester far away on the horizon of a golden wheat field at sunset, dust in the air, backlit",
                   "Wide shot of a large tractor far away working a field at dawn, unbranded",
                   "Seeding disc and furrow in dark soil, extreme close-up of a planter row unit, no markings, warm light"],
    "ganaderia": ["Herd of black Angus cattle grazing on green pampas grassland, soft light",
                  "Hereford cattle walking on a dirt path in the pampas at sunset",
                  "Close-up of a calf resting in green pasture, shallow depth of field"],
    "empresas": ["Aerial view of patchwork crop fields in the Argentine pampas, green and golden tones",
                 "Grain silos seen from far across a wheat field at sunset, no markings",
                 "Lone tree in the middle of a vast soybean field under a dramatic sky"],
}

ESTILO = (" Realistic modern editorial photograph for an agribusiness and agtech news outlet, natural "
          "daylight, cinematic composition, shallow depth of field, rich but natural colors, wide "
          "horizontal composition with the subject in the middle band of the frame, no people "
          "facing the camera, no logos, no brand names, plain surfaces, wordless.")


def ia_activa() -> bool:
    """La IA como respaldo de la foto original (prendida; AGRO_IMAGEN_IA=0 la apaga)."""
    return (os.environ.get("AGRO_IMAGEN_IA") or "1").strip() != "0"


def foto_original(rep: dict, url: str, destino: Path, bajar, mirar) -> dict:
    """La foto ORIGINAL de la nota de otro medio, tal cual: {archivo, origen «fuente», credito} o {motivo}."""
    from nacionales import infobae as IB
    import re
    agencia = IB.es_de_agencia(rep.get("credito_foto") or "")
    m = re.search(r"(?<![a-z])(afp|reuters|efe|getty(?:images)?|bloomberg|xinhua|apimages|ap-?photo|shutterstock|"
                  r"istock|europapress|anadolu)(?![a-z])", (url or "").lower())
    agencia = agencia or (m.group(1) if m else "")
    if agencia:
        return {"motivo": f"la foto original es de agencia ({agencia})"}
    foto = destino.with_name(destino.stem + "_original.jpg")
    if not bajar(url, foto):
        return {"motivo": "la foto original no se pudo bajar"}
    if _ancho(foto) < MIN_ANCHO:
        return {"motivo": f"la foto original es chica ({_ancho(foto)} px)"}
    if mirar(str(foto)):
        return {"motivo": "la foto original tiene letras (placa o gráfico)"}
    return {"archivo": str(foto), "origen": "fuente", "credito": rep.get("fuente", ""),
            "motivo": "foto original de la nota"}


def _ancho(ruta) -> int:
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            return im.width
    except Exception:                                      # noqa: BLE001
        return 0


def _al_azar(lista: list, semilla: str):
    import hashlib
    return lista[int(hashlib.sha1((semilla or "x").encode()).hexdigest(), 16) % len(lista)]


def del_banco(subtema: str, semilla: str) -> str:
    """Una imagen del banco del subtema (o de cualquiera si ese no tiene), elegida por `semilla`
    para que no salga siempre la misma."""
    for carpeta in ([BANCO / subtema] if subtema else []) + [BANCO]:
        fotos = sorted(carpeta.rglob("*.jpg")) if carpeta.exists() else []
        if fotos:
            return str(_al_azar(fotos, semilla))
    return ""


def elegir(rep: dict, cuerpo_imagen: str, prompt: str, destino: Path, generar=None, bajar=None,
           mirar=None, subtema: str = "", recrear_con=None) -> dict:
    """{archivo, origen: «fuente»|«recreada»|«ia»|«ninguna», url_original, motivo}. Primero la foto
    ORIGINAL (de la fuente oficial o del medio, tal cual); si no sirve, IA (recreada, escena, banco).
    Con AGRO_IMAGEN_IA=0, solo la original; si no hay, «ninguna» y la pieza no sale."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = cuerpo_imagen or rep.get("imagen_url") or ""
    salida = {"url_original": url}
    if mirar is None:
        from archivo import imagen as IM
        mirar = IM.tiene_texto
    from agro import fuentes as F
    usa_foto = F.por_nombre(rep.get("fuente", "")).get("foto", True)
    if rep.get("tipo_fuente") in ("oficial", "prensa") and not usa_foto:
        salida["motivo"] = "esta fuente publica placas y gráficos, no fotos"
    elif rep.get("tipo_fuente") in ("oficial", "prensa") and url:
        if bajar is None:
            from reels.flujo import _bajar_foto as bajar
        foto = destino.with_name(destino.stem + "_fuente.jpg")
        if not bajar(url, foto):
            salida["motivo"] = "la foto de la fuente no se pudo bajar"
        elif _ancho(foto) < MIN_ANCHO:
            salida["motivo"] = f"la foto de la fuente es chica ({_ancho(foto)} px)"
        elif mirar(str(foto)):
            salida["motivo"] = "la foto de la fuente tiene letras (placa o gráfico)"
        else:
            return dict(salida, archivo=str(foto), origen="fuente", credito=rep.get("fuente", ""),
                        motivo=f"foto de una fuente {rep['tipo_fuente']}")
    elif not url:
        salida["motivo"] = "la nota no trae foto"
    else:
        if bajar is None:
            from reels.flujo import _bajar_foto as bajar
        orig = foto_original(rep, url, destino, bajar, mirar)
        if orig.get("archivo"):
            return dict(salida, **orig)
        salida["motivo"] = orig["motivo"]
    if not ia_activa():
        return dict(salida, archivo=None, origen="ninguna",
                    motivo=f"sin foto real que se pueda usar ({salida.get('motivo') or 'sin foto'})")
    if url and rep.get("tipo_fuente") == "medio":
        # La foto del otro medio, RECREADA con IA (nunca la original). Dos intentos sin letras.
        if bajar is None:
            from reels.flujo import _bajar_foto as bajar
        foto = destino.with_name(destino.stem + "_fuente.jpg")
        recrear_con = recrear_con or recrear
        if not bajar(url, foto):
            salida["motivo"] = "la foto de la fuente no se pudo bajar"
        else:
            motivos_r = []
            for variante in (0, 1):
                r = recrear_con(foto, destino.with_name(f"{destino.stem}_recreada{variante}.jpg"), "",
                                variante=variante)
                if not r.get("archivo"):
                    motivos_r.append(r.get("motivo") or "no salió")
                    break
                if not mirar(r["archivo"]):
                    return dict(salida, archivo=r["archivo"], origen="recreada",
                                motivo="foto de la fuente recreada con IA (escena nueva, sin la original)")
                motivos_r.append("la recreación tiene letras")
            salida["motivo"] = "recreación de la foto: " + "; ".join(motivos_r)
    if generar is None:
        from archivo import imagen as IM
        generar = IM.generar
    motivos = [salida.get("motivo")] if salida.get("motivo") else []
    segura = _al_azar(SEGURAS.get(subtema) or SEGURAS["agro"], rep.get("id", ""))
    intentos = ((prompt, "la escena de la nota"), (prompt, "la escena de la nota"),
                (segura, "una escena segura del tema"))
    for k, (texto, cual) in enumerate(intentos):
        if not (texto or "").strip():
            continue
        r = generar(texto, destino.with_name(f"{destino.stem}_ia{k}.jpg"), estilo=ESTILO)
        if not r.get("archivo"):
            motivos.append(r.get("motivo") or "la IA no dio imagen")
            continue
        if not mirar(r["archivo"]):            # False o None (no se pudo mirar): sirve
            return dict(salida, archivo=r["archivo"], origen="ia",
                        motivo=f"imagen ilustrativa con IA ({cual})" + (f"; antes: {'; '.join(motivos)}" if motivos else ""))
        motivos.append("la IA dibujó letras")
    banco = del_banco(subtema, rep.get("id", ""))
    if banco:
        return dict(salida, archivo=banco, origen="ia",
                    motivo=f"imagen IA del banco ({subtema or 'general'}); antes: {'; '.join(motivos)}")
    return dict(salida, archivo=None, origen="ninguna", motivo="; ".join(motivos) or "sin imagen")


def armar_banco(log=print) -> int:
    """Genera y revisa (sin letras) las imágenes del banco: una por escena segura. Las que ya están
    no se rehacen. Devuelve cuántas hay en total."""
    from archivo import imagen as IM
    for sub, escenas in SEGURAS.items():
        carpeta = BANCO / sub
        carpeta.mkdir(parents=True, exist_ok=True)
        for k, escena in enumerate(escenas):
            destino = carpeta / f"{sub}_{k + 1}.jpg"
            if destino.exists():
                continue
            for _ in range(3):
                r = IM.generar(escena, destino, estilo=ESTILO)
                if r.get("archivo") and IM.tiene_texto(r["archivo"]) is False:
                    _achicar(destino)
                    log(f"  banco {sub} {k + 1}: ok")
                    break
                destino.unlink(missing_ok=True)
            else:
                log(f"  banco {sub} {k + 1}: no salió sin letras")
    return len(list(BANCO.rglob("*.jpg")))


def _achicar(ruta: Path):
    """JPG de calidad 85: el banco va al repo y no tiene que pesar de más."""
    from PIL import Image
    with Image.open(ruta) as im:
        im.convert("RGB").save(ruta, "JPEG", quality=85)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    import entorno
    entorno.cargar()
    if "--banco" in sys.argv:
        print(f"banco: {armar_banco()} imágenes en {BANCO}")
