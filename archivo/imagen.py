# -*- coding: utf-8 -*-
"""La imagen de la pregunta del día: Cloudflare Workers AI (FLUX.1 schnell), GRATIS.

Decisión del editor (10/10/2026): «Cloudflare gratis». El plan gratis de Workers AI da 10.000 «neuronas» por
día; una imagen de 1024x1024 a 6 pasos usa ~80 (4,80 por cada cuadro de 512 + 9,60 por paso): alcanza
para más de 100 por día y acá se usa UNA.

Credenciales (del editor, en el .env y como secrets del repo): CF_ACCOUNT_ID y CF_API_TOKEN (un token de
«Workers AI»). Si faltan o Cloudflare falla, la pregunta sale igual con la placa propia del diario
(nacionales/placa.py): nunca se pierde el reel por la imagen.
"""
import base64
import io
import os
import time
from pathlib import Path

import httpx

MODELO = "@cf/black-forest-labs/flux-1-schnell"
URL = "https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/run/" + MODELO
PASOS = 6                   # 4 es el default; el máximo es 8
ESPERAS = (5, 20)
# FLUX no tiene «prompt negativo»: escribirle «no text» igual le mete la idea de letras, y el 10/10 dibujó
# «utuire careers» en una pregunta sobre el futuro laboral. El estilo pictórico y las superficies lisas
# alejan el texto; lo que se cuele lo agarra tiene_texto() y se pide otra (o va la placa).
ESTILO = (" Painterly gouache editorial illustration, vertical composition, warm palette with orange accents, "
          "soft natural light, clean uncluttered scene, plain blank surfaces, wordless.")
INTENTOS_SIN_TEXTO = 2      # imágenes de Cloudflare que se prueban antes de caer a la placa


def credenciales() -> tuple:
    return (os.environ.get("CF_ACCOUNT_ID") or "").strip(), (os.environ.get("CF_API_TOKEN") or "").strip()


def generar(prompt: str, destino: Path, pedir=None) -> dict:
    """{archivo, proveedor: «cloudflare»} o {motivo} si no se pudo. Nunca lanza ni muestra el token."""
    cuenta, token = credenciales()
    if not cuenta or not token:
        return {"motivo": "faltan CF_ACCOUNT_ID / CF_API_TOKEN"}
    if not (prompt or "").strip():
        return {"motivo": "la IA no dio la descripción de la imagen"}
    pedir = pedir or (lambda url, **kw: httpx.post(url, timeout=120, **kw))
    cuerpo = {"prompt": (prompt.strip() + ESTILO)[:2048], "steps": PASOS}
    ultimo = ""
    for intento in range(len(ESPERAS) + 1):
        if intento:
            time.sleep(ESPERAS[intento - 1])
        try:
            r = pedir(URL.format(cuenta=cuenta), headers={"Authorization": f"Bearer {token}"}, json=cuerpo)
        except httpx.HTTPError as e:
            ultimo = type(e).__name__
            continue
        if r.status_code != 200:
            try:
                errores = "; ".join(str(e.get("message")) for e in (r.json().get("errors") or []))
            except ValueError:
                errores = ""
            ultimo = f"HTTP {r.status_code}" + (f": {errores[:200]}" if errores else "")
            if r.status_code in (429, 500, 502, 503, 504):
                continue
            break
        try:
            datos = r.json()
            crudo = base64.b64decode((datos.get("result") or {}).get("image") or "")
        except (ValueError, TypeError):
            crudo = b""
        if len(crudo) < 10000:
            ultimo = "Cloudflare contestó sin imagen"
            continue
        try:
            from PIL import Image
            with Image.open(io.BytesIO(crudo)) as im:
                im.convert("RGB").save(destino, "JPEG", quality=92)
        except Exception as e:                    # noqa: BLE001
            ultimo = f"la imagen no se pudo abrir ({type(e).__name__})"
            continue
        return {"archivo": str(destino), "proveedor": "cloudflare", "modelo": MODELO}
    return {"motivo": f"Cloudflare: {ultimo}"}


LADO_MOTOR = 1350           # a esto se agranda una foto chica antes de sumarle grano


def para_el_motor(ruta, mirar=None) -> dict:
    """Que el motor de reels la tome como FOTO y no como afiche: {archivo, ajustada}.

    El detector de afiches del motor mira rellenos lisos. Las fotos viejas del Archivo (retratos en
    blanco y negro con fondo parejo, escaneos chicos) y algunas ilustraciones dan «afiche», y a un
    afiche el motor NO le pone texto (salió así el retrato de Federico Soarez, 10/10). Solo en ese
    caso se agranda a LADO_MOTOR y se le suma un grano suave (el mismo de la placa propia): con eso
    ya da foto. La imagen no se recorta ni se le tapa nada."""
    from PIL import Image
    from nacionales import placa as P
    ruta = Path(ruta)
    if mirar is None:
        import tempfile
        from reels import reel_bot as R

        def mirar(p):
            with tempfile.TemporaryDirectory(prefix="mirar_") as tmp:
                return R.motor()._mirar_foto(Path(p), Path(tmp), "archivo")[1]
    try:
        if not mirar(ruta):
            return {"archivo": str(ruta), "ajustada": False}
        with Image.open(ruta) as im:
            im = im.convert("RGB")
            if max(im.size) < LADO_MOTOR:
                k = LADO_MOTOR / max(im.size)
                im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
            destino = ruta.with_name(ruta.stem + "_grano.jpg")
            P._grano(im, 7, 9).save(destino, "JPEG", quality=92)
        return {"archivo": str(destino), "ajustada": True}
    except Exception:                          # noqa: BLE001 — ante la duda, la original
        return {"archivo": str(ruta), "ajustada": False}


_PREGUNTA_TEXTO = ("¿Esta imagen tiene letras, palabras, números o pseudo-texto (garabatos que imitan escritura) "
                   "en cualquier parte: carteles, pantallas, papeles, etiquetas? Devolvé SOLO el JSON "
                   '{"texto": true} o {"texto": false}.')


def tiene_texto(ruta) -> bool | None:
    """Gemini mira la imagen: True si ve letras o pseudo-texto, False si no, None si no pudo mirar."""
    import httpx as _httpx
    from reels import ia
    try:
        datos = base64.b64encode(Path(ruta).read_bytes()).decode()
    except OSError:
        return None
    cuerpo = {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "image/jpeg", "data": datos}},
                                                      {"text": _PREGUNTA_TEXTO}]}],
              "generationConfig": {"maxOutputTokens": 50, "responseMimeType": "application/json"}}
    for modelo in ia.MODELOS_GEMINI:
        for clave in ia._claves_gemini():
            try:
                r = _httpx.post(ia.URL_GEMINI.format(modelo=modelo), json=cuerpo, timeout=60,
                                headers={"x-goog-api-key": clave, "Content-Type": "application/json"})
                if r.status_code != 200:
                    continue
                texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return bool(ia._parsear(texto).get("texto"))
            except Exception:                  # noqa: BLE001 — se prueba la siguiente clave o modelo
                continue
    return None


def imagen_pregunta(prompt: str, seccion: str, destino: Path, semilla: int = 0, pedir=None, mirar=None) -> dict:
    """La imagen de la pregunta: Cloudflare (sin letras: si Gemini ve texto se pide otra, hasta
    INTENTOS_SIN_TEXTO), y si no, la placa propia con la palabra de la sección."""
    destino = Path(destino)
    mirar = mirar or tiene_texto
    r, motivos = {}, []
    for intento in range(INTENTOS_SIN_TEXTO):
        r = generar(prompt, destino, pedir)
        if not r.get("archivo"):
            motivos.append(r.get("motivo") or "sin imagen")
            break
        if not mirar(r["archivo"]):          # False (sin letras) o None (no se pudo mirar): sirve
            r["intentos"] = intento + 1
            return r
        motivos.append("Cloudflare dibujó letras")
        r = {}
    from nacionales import placa as P
    archivo = P.guardar_fondo(seccion or "Chivilcoy", destino.with_name(destino.stem + "_placa.jpg"),
                              semilla=semilla, etiqueta="Chivilcoy")
    return {"archivo": str(archivo), "proveedor": "placa", "motivo": "; ".join(motivos)}
