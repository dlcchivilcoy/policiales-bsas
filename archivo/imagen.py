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
ESTILO = (" Vertical editorial illustration, contemporary magazine style, warm palette with orange accents, "
          "soft light, rich detail. No text, no letters, no words, no logos, no watermark, no recognizable faces.")


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


def imagen_pregunta(prompt: str, seccion: str, destino: Path, semilla: int = 0, pedir=None) -> dict:
    """La imagen de la pregunta: Cloudflare, y si no, la placa propia con la palabra de la sección."""
    destino = Path(destino)
    r = generar(prompt, destino, pedir)
    if r.get("archivo"):
        return r
    from nacionales import placa as P
    archivo = P.guardar_fondo(seccion or "Chivilcoy", destino.with_name(destino.stem + "_placa.jpg"),
                              semilla=semilla, etiqueta="Chivilcoy")
    return {"archivo": str(archivo), "proveedor": "placa", "motivo": r.get("motivo")}
