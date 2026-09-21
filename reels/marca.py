# -*- coding: utf-8 -*-
"""Identidad visual del reel. TODO lo de acá está copiado de `video.py` del repo
`dlcchivilcoy/social_publisher` — es la estética ya probada del bot de corresponsales,
no un diseño nuevo.

Se replica en vez de importarse porque aquel módulo arrastra `utils.config`,
`utils.logger` y el filtergraph de ffmpeg. Acá solo hace falta la GEOMETRÍA.

  ⚠️ Si allá se cambia una medida, hay que cambiarla acá. Cada constante lleva el
  comentario original que explica POR QUÉ vale lo que vale: son decisiones tomadas
  mirando reels reales en un celular, no números elegidos al azar.

ANATOMÍA DE LA PLACA (1080x1920, de arriba hacia abajo)

    ┌──────────────────────────────────────┐ y=0
    │   ZONA MUERTA: acá tapa la app       │
    │   (TikTok: «Siguiendo / Para vos»)   │ y=150  SEGURO_ARRIBA
    ├──────────────────────────────────────┤
    │ DIARIO LA CAMPAÑA | RADIO DEL   [C]  │ ← marca a la IZQUIERDA (gris, 28)
    │ @diarioyradio                        │   isologo a la DERECHA (150 de ancho)
    │                                      │
    │            VOLANTA                   │ ← NARANJA, centrada, 42 (mín. 30)
    │       TITULAR GRANDE EN              │ ← BLANCO, centrado, 88 (mín. 46), 3 renglones
    │       HASTA TRES RENGLONES           │
    │        Bajada en naranja, siempre    │ ← NARANJA, centrada, 44 (mín. 30), 3 renglones
    │        cerrada en punto.             │
    ├──────────────────────────────────────┤ y_img (nunca más abajo que 940)
    │                                      │
    │        FOTO / VIDEO A SANGRE         │ ← full bleed, se funde con el fondo
    │        (mínimo 980px de alto)        │   por arriba en 110px
    │                                      │
    ├──────────────────────────────────────┤
    │   Pie: primera oración de la nota    │ ← GRIS, solo si sobra hueco bajo una foto apaisada
    ├──────────────────────────────────────┤ y=1590  (1920 - BANDA_SEGURO)
    │   ZONA MUERTA: usuario, caption,     │
    │   botones de la app                  │
    └──────────────────────────────────────┘ y=1920

El color de fondo NO es fijo: se saca del propio video/foto y se apaga (luz 0.13,
saturación 0.26) para que la placa y la imagen se sientan la misma pieza.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA_DIR = RAIZ / "marca"

# --- Lienzo -------------------------------------------------------------------
W, H = 1080, 1920

# --- Assets (copiados del repo social_publisher) -------------------------------
LOGO_REEL = MARCA_DIR / "logo_reel.png"            # isotipo 'C' blanco, transparente
LOGO_REEL_NARANJA = MARCA_DIR / "logo_reel_naranja.png"
OVERLAY_REEL = MARCA_DIR / "overlay_reel.png"      # marco con caja de zócalo + barra web
FONDO_REEL = MARCA_DIR / "fondo_reel.png"          # degradado naranja que enmarca el video
PLACA_FINAL = MARCA_DIR / "placa_final.png"        # cierre "Seguinos en redes"
LOGO_MASTHEAD = MARCA_DIR / "logo.png"             # masthead horizontal del diario

FUENTE_ZOCALO = MARCA_DIR / "fonts" / "Montserrat-Bold.ttf"
# Tres tipografías, una por trabajo. Montserrat es LA MARCA y no se toca; el titular y el
# resumen usan otras porque tienen otro problema que resolver:
#   · el TITULAR tiene que entrar en pocos renglones → una angosta permite letra más grande;
#   · el RESUMEN se lee chico sobre una foto → una humanista aguanta mejor ese tamaño.
FUENTE_TITULAR = MARCA_DIR / "fonts" / "ArchivoNarrow-Variable.ttf"
FUENTE_RESUMEN = MARCA_DIR / "fonts" / "LibreFranklin-Variable.ttf"
# Son VARIABLES: un archivo con todos los pesos adentro. HAY QUE PEDIR LA INSTANCIA;
# si no, sale la Regular, demasiado fina para leerse sobre una foto. Y hay que pedirla
# tanto al MEDIR como al DIBUJAR: si se mide con una y se dibuja con otra, el texto no
# entra donde el cálculo dice que entra.
PESO_TITULAR = "SemiBold"
PESO_RESUMEN = "SemiBold"

# --- Colores de marca ---------------------------------------------------------
NARANJA = (247, 127, 0, 255)      # el naranja de la marca
BLANCO = (255, 255, 255, 255)
GRIS = (233, 236, 240, 255)       # la marca, apenas apagada
ZOCALO_COLOR = (247, 127, 0)

# --- Zonas que TAPAN las apps -------------------------------------------------
# Ningún texto se dibuja acá adentro. La imagen sí puede llegar: lo que molesta es que
# la app tape una PALABRA, no que tape un pedazo de foto.
#   · ARRIBA: en TikTok van las solapas «Siguiendo / Para vos».
#   · ABAJO: usuario, texto del posteo y botones.
#   · DERECHA: la columna de me gusta / comentar / compartir, desde la mitad del alto.
#     Arriba de eso la derecha está libre, y ahí es donde va el isologo.
SEGURO_ARRIBA = 150
BANDA_SEGURO = 330
SEGURO_DERECHA = 150
SEGURO_DERECHA_DESDE = 900

# --- Isologo ------------------------------------------------------------------
LOGO_ANCHO = 150
LOGO_MX = 72
LOGO_MY = SEGURO_ARRIBA
LOGO_A_LA_DERECHA = True          # pedido 2026-09-14

# --- Bloque de marca (texto) --------------------------------------------------
# Van uno DEBAJO del otro; el «|» separa renglones, no es un carácter a dibujar.
MARCA_TEXTO = "DIARIO LA CAMPAÑA|RADIO DEL CENTRO"
MARCA_USUARIO = "@diarioyradio"
PLACA_MARCA_TAM = 28

# --- Estilo «placa» -----------------------------------------------------------
# El texto va ARRIBA, en pocos renglones y grande, alternando NARANJA → BLANCO →
# NARANJA, y la imagen va FULL BLEED abajo, fundiéndose con el fondo por arriba.
#
# Por qué es así: los resúmenes reales tienen 255 caracteres de mediana. Medido sobre
# 269 notas, en 3 renglones NO entran a ningún cuerpo legible — a 34 entra entero el
# 14%, y para que entre la mayoría hay que bajar a 22, ilegible en un celular. El
# problema nunca fue el cuerpo: era el LARGO. Por eso va POCO texto y GRANDE, y lo que
# no entra se corta POR ORACIÓN.
PLACA_MX = 72                     # margen lateral del bloque de texto
PLACA_Y0 = SEGURO_ARRIBA          # dónde arranca la marca

PLACA_VOLANTA_TAM = 42
PLACA_VOLANTA_MIN = 30            # antes que cortarla con «…», la volanta se achica

PLACA_TITULAR_TAM = 88            # tope; baja solo si no entra
PLACA_TITULAR_MIN = 46
PLACA_TITULAR_RENGLONES = 3
PLACA_TITULAR_INTERLINEA = 1.08   # apretado, como la referencia

PLACA_BAJADA_TAM = 44
PLACA_BAJADA_MIN = 30
PLACA_BAJADA_RENGLONES = 3        # tres y no dos: con dos, una primera oración de largo
                                  # normal no entraba y salía cortada
PLACA_BAJADA_INTERLINEA = 1.26

PLACA_PIE_TAM = PLACA_BAJADA_TAM  # mismo cuerpo que la bajada: 30 contra 44 se leía como
PLACA_PIE_MIN = PLACA_BAJADA_MIN  # nota al pie, y esto es información de la noticia
PLACA_PIE_RENGLONES = 3
PLACA_PIE_MIN_ALTO = 60           # ni un renglón del cuerpo más chico entra: no se dibuja
PLACA_PIE_INTERLINEA = 1.24

PLACA_IMG_MIN = 980               # la imagen nunca ocupa menos que esto (51% del cuadro)
PLACA_FUNDIDO = 110               # px de transición fondo→imagen. Corto a propósito: con
                                  # 240 el desvanecido se comía los márgenes de la foto
PLACA_NOMBRE_COSTO = 8            # cuántos puntos de titular se resignan con tal de no
                                  # partir un nombre propio entre dos renglones

# Color sólido detrás del texto de arriba. Por default sale del PROPIO video o foto y se
# baja a un tono oscuro y apagado. Medido sobre 36 matices: en el PEOR caso (un amarillo)
# el blanco del titular queda en 14,5:1 de contraste y el naranja en 5,5:1 — los dos por
# encima del 4,5:1 que pide la norma. O sea: no hay color de imagen que deje texto ilegible.
PLACA_FONDO = (0x22, 0x25, 0x2B)
PLACA_FONDO_LUZ = 0.13
PLACA_FONDO_SAT = 0.26

# --- Zócalo (cuando el reel es un VIDEO con la caja del overlay) --------------
# Rectángulo ÚTIL de la caja negra del overlay, medido sobre el PNG en 1080x1920: la
# parte donde la caja es negra en TODAS sus filas, así el texto nunca se escapa por los
# bordes en diagonal. (x, y, ancho, alto).
ZOCALO_CAJA = (175, 1481, 670, 71)
ZOCALO_PALABRAS = 5               # tope de palabras del zócalo

# --- Video --------------------------------------------------------------------
PLACA_SEG = 5.0                   # cuánto dura la placa de cierre
FONDO_DIFUMINADO = 80


def faltantes() -> list:
    """Assets de marca que no están. Si devuelve algo, el reel sale sin esa pieza."""
    return [p.name for p in (LOGO_REEL, OVERLAY_REEL, FONDO_REEL, PLACA_FINAL,
                             FUENTE_TITULAR, FUENTE_RESUMEN, FUENTE_ZOCALO)
            if not p.exists()]
