# -*- coding: utf-8 -*-
"""Instagram: TODO lo automatico sale como REEL DE PRUEBA. Este modulo NO publica.

Decidido por el editor el 2026-09-26. Un reel de prueba ("trial reel") se muestra
primero SOLO a gente que no sigue la cuenta. Asi un reel armado sin revision
humana —que es como sale todo lo automatico— no le llega de entrada al publico propio
del diario.

Graduacion AUTOMATICA (SS_PERFORMANCE), pedida por el editor el mismo 26/09: si al
reel le va bien con los no seguidores, Instagram lo pasa solo al feed de
@diarioyradio y ahi lo ven los seguidores. El que no funciona queda en prueba.

Esto esta en la API oficial, no es un truco: `POST /{ig-user-id}/media` acepta
`trial_params` con `media_type=REELS`.
https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media

Por que vive aca y no en el publicador: el publicador todavia no existe, y la regla
tiene que estar desde antes. El publicador arma el contenedor con `contenedor_reel()`
y no le pasa parametros por su cuenta: si la regla dependiera de que el que escriba
el publicador se acuerde de agregar un campo, se olvida.

Lo que la API NO da, y hay que saber:
- No hay forma de graduar un reel por API ni de leer si esta en prueba. Con
  SS_PERFORMANCE decide Instagram con su propia vara: la API no expone el umbral.
- Rige solo para Instagram. La pagina de Facebook es otra llamada, con otras reglas.
"""
import json

# True = todo lo que sube el sistema es reel de prueba. Pasarlo a False es decision
# del editor, no un ajuste tecnico: los reels le llegarian directo a los seguidores.
SOLO_REELS_DE_PRUEBA = True

# "MANUAL": queda en prueba hasta que el editor lo gradue desde la app. Nunca le llega
#           a los seguidores solo.
# "SS_PERFORMANCE": Instagram lo gradua solo si le va bien con los no seguidores.
#           Deja de ser "solo de prueba": el que anda, termina en el feed de todos.
GRADUACION = "SS_PERFORMANCE"

_GRADUACIONES = ("MANUAL", "SS_PERFORMANCE")


def contenedor_reel(video_url: str, caption: str) -> dict:
    """Los parametros del `POST /{ig-user-id}/media` para un reel. Sin red, sin token.

    `video_url` tiene que ser publica: Instagram va a buscar el archivo, no lo recibe.
    """
    if not video_url or not video_url.startswith("https://"):
        raise ValueError("Instagram necesita una URL https publica del video")
    params = {"media_type": "REELS", "video_url": video_url, "caption": caption or ""}
    if SOLO_REELS_DE_PRUEBA:
        if GRADUACION not in _GRADUACIONES:
            # Un valor mal escrito no puede terminar en un reel publicado normal:
            # la API lo rechazaria, o peor, alguien "arregla" el error sacando el campo.
            raise ValueError(f"GRADUACION invalida: {GRADUACION!r}")
        # La Graph API recibe los objetos anidados como JSON dentro del formulario.
        params["trial_params"] = json.dumps({"graduation_strategy": GRADUACION})
    return params
