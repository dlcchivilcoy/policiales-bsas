# -*- coding: utf-8 -*-
"""Quién redacta el guion. Por defecto **Gemini gratis**; Claude queda de respaldo.

Por qué Gemini y no Claude, si el resto del proyecto usa Claude: porque redactar 450
guiones por mes con Haiku cuesta ~US$1,25 y con el cupo gratis de Gemini cuesta **$0**.
Para un texto de 350 tokens que después revisás igual, no hay razón para pagarlo.

El pool de claves es el MISMO que ya tenés armado en `utils/gemini.py` del bot: cada
clave es de un proyecto distinto de Google AI Studio y **cada proyecto tiene su propio
cupo gratis**, así que sumar claves suma cupo. Se leen solas del entorno con los mismos
nombres (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`, …), o sea que el `.env` que ya tenés sirve
tal cual.

Ante un 429 (cupo agotado de UNA clave) se rota a la siguiente; si se acabaron todas, se
baja de modelo, que tiene su propio cupo. Es la misma estrategia del bot, y por la misma
razón: esperar sobre un proyecto saturado no lo desatasca; probar otro proyecto, sí.
"""
import json
import os
import re
import time

# Alias que se auto-actualizan y SÍ tienen cupo gratis. Ojo con pinear una versión: el
# 2026-08-27 `gemini-2.5-flash` quedó retirado de golpe (404 «no longer available to new
# users») y el bot se quedó sin camino. Los alias evitan eso.
# NO usar `gemini-3.8-flash` acá: ese es el modelo PAGO del bot (US$0,75/1M de entrada).
MODELO_GEMINI = "gemini-flash-latest"
MODELO_GEMINI_RESPALDO = "gemini-flash-lite-latest"
MODELO_CLAUDE = "claude-haiku-4-5-20251001"

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class SinProveedor(RuntimeError):
    """No hay ninguna credencial cargada: ni Gemini ni Claude."""


def _claves_gemini() -> list:
    """Las claves del pool, en orden, sin repetir. Mismos nombres que usa el bot, así el
    `.env` se comparte sin tocar nada."""
    fijas = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4",
             "GEMINI_API_KEY_RADIO", "GEMINI_API_KEY_RADIO_2", "GEMINI_API_KEY_RADIO_3"]
    # Cualquier GEMINI_API_KEY* que no esté en la lista se engancha sola: para sumar cupo
    # alcanza con crear otra clave en otro proyecto y cargarla como GEMINI_API_KEY_5.
    extra = sorted(n for n in os.environ
                   if n.startswith("GEMINI_API_KEY") and n not in fijas)
    vistas, salida = set(), []
    for nombre in fijas + extra:
        k = (os.environ.get(nombre) or "").strip()
        if k and k not in vistas:
            vistas.add(k)
            salida.append(k)
    return salida


def proveedor_disponible() -> str:
    """'gemini', 'claude' o '' si no hay ninguna credencial."""
    if _claves_gemini():
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return ""


# =============================================================================
# Gemini
# =============================================================================

def _pedir_gemini(system: str, material: str, clave: str, modelo: str,
                  timeout: int = 90) -> str:
    import httpx
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": material}]}],
        "generationConfig": {
            "temperature": 0.3,
            # 900 era poco y cortaba. El guion completo son volanta + titular +
            # bajada de hasta 280 caracteres + zocalo + pie + una descripcion de
            # cuatro parrafos + hashtags; en castellano eso pasa holgado los 900
            # tokens. Cuando se pasaba, la respuesta volvia cortada a mitad de una
            # cadena, el JSON no parseaba y la pieza caia a reglas — justo en las
            # notas mas importantes, que son las que tienen mas para contar.
            #
            # Subirlo no cuesta nada: es un TECHO, no un cargo. Se paga lo que el
            # modelo escribe, y escribe lo mismo que antes.
            "maxOutputTokens": 2000,
            # Se pide JSON de verdad, no «un JSON dentro de un bloque de código». Ahorra
            # el limpiado de ```json y los cortes a mitad de llave.
            "responseMimeType": "application/json",
        },
    }
    r = httpx.post(URL_GEMINI.format(modelo=modelo), json=payload, timeout=timeout,
                   headers={"x-goog-api-key": clave, "Content-Type": "application/json"})
    if r.status_code == 429:
        raise _Cuota(f"429 en {modelo}")
    r.raise_for_status()
    datos = r.json()
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Gemini devolvió algo inesperado: {str(datos)[:200]}")


class _Cuota(RuntimeError):
    """Cupo agotado de ESA clave. Se rota, no se espera."""


def redactar_gemini(system: str, material: str) -> tuple:
    """Devuelve (texto, detalle). Rota claves ante 429 y después baja de modelo."""
    claves = _claves_gemini()
    if not claves:
        raise SinProveedor("no hay ninguna GEMINI_API_KEY en el entorno")

    ultimo = None
    for modelo in (MODELO_GEMINI, MODELO_GEMINI_RESPALDO):
        for i, clave in enumerate(claves, 1):
            try:
                texto = _pedir_gemini(system, material, clave, modelo)
                return texto, f"gemini:{modelo} (clave {i}/{len(claves)})"
            except _Cuota as e:
                ultimo = e
                continue                      # esta clave se quedó sin cupo: la siguiente
            except Exception as e:
                ultimo = e
                # Un 503 es saturación momentánea: una espera corta y se sigue, pero sin
                # insistir sobre el mismo proyecto.
                if "503" in str(e):
                    time.sleep(2)
                continue
    raise RuntimeError(f"se agotaron las {len(claves)} claves y los 2 modelos: {ultimo}")


# =============================================================================
# Claude (respaldo)
# =============================================================================

def redactar_claude(system: str, material: str) -> tuple:
    import anthropic
    clave = os.environ.get("ANTHROPIC_API_KEY", "")
    if not clave:
        raise SinProveedor("no hay ANTHROPIC_API_KEY en el entorno")
    cliente = anthropic.Anthropic(api_key=clave)
    msg = cliente.messages.create(
        model=MODELO_CLAUDE, max_tokens=900, system=system,
        messages=[{"role": "user", "content": material}],
    )
    return msg.content[0].text, f"claude:{MODELO_CLAUDE}"


# =============================================================================
# Entrada única
# =============================================================================

def redactar(system: str, material: str, preferir: str = "") -> tuple:
    """Redacta con lo que haya. Devuelve (dict_parseado, detalle_del_proveedor).

    `preferir` fuerza 'gemini' o 'claude'. Vacío = Gemini si hay claves (gratis), y si no,
    Claude.
    """
    orden = [preferir] if preferir else (["gemini", "claude"] if _claves_gemini()
                                         else ["claude"])
    errores = []
    for cual in orden:
        # Dos intentos con el MISMO proveedor antes de pasar al siguiente. Un JSON que
        # no parsea casi siempre es una respuesta que salio cortada o con una coma de
        # mas: es del intento, no del proveedor, y volver a pedirlo lo resuelve. Sin
        # esto, un tropiezo de formato hacia caer la pieza a reglas aunque la clave
        # estuviera perfecta.
        for intento in (1, 2):
            try:
                texto, detalle = (redactar_gemini(system, material) if cual == "gemini"
                                  else redactar_claude(system, material))
                return _parsear(texto), detalle
            except SinProveedor as e:
                errores.append(f"{cual}: {e}")
                break                     # sin credencial no hay segundo intento que valga
            except json.JSONDecodeError as e:
                errores.append(f"{cual}: intento {intento}: JSON cortado: {e}")
                continue
            except Exception as e:
                errores.append(f"{cual}: {type(e).__name__}: {e}")
                break
    raise RuntimeError(" | ".join(errores) or "no hay proveedor de IA configurado")


def _parsear(texto: str) -> dict:
    """Saca el JSON, tolerando ```json y texto colgado a los costados."""
    limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip())
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", limpio, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))
