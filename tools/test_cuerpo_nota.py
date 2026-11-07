# -*- coding: utf-8 -*-
"""El texto que lee la IA es el de LA nota, no el de la noticia del costado (6/11/2026). Sin red.

Las páginas de abajo copian cómo están armadas las reales: Semanario de Junín y junin24 tienen más de
10 <article> por página y el primero es una tarjetita de otra noticia.
"""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from reels import flujo as F, guion as G, ia
from scraper import fetch

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


def detalle_de(html):
    with mock.patch.object(fetch, "obtener_html", lambda *a, **k: (html, None)):
        return fetch.detalle("https://medio.com.ar/nota")


CUERPO_BEBA = ("<p>Una denuncia por abuso sexual infantil conmocionó a Chivilcoy, donde una beba de nueve meses "
               "fue internada en el Hospital Municipal.</p><p>La madre advirtió las lesiones y apuntó contra el "
               "padre biológico, según consta en la denuncia radicada en la comisaría.</p>"
               "<p>La fiscalía ordenó las primeras medidas y la causa quedó bajo investigación.</p>")
TARJETA = '<article class="noticia-18"><h3>INVESTIGADOS</h3><a>Dos comisarios afrontan problemas con la Justicia</a></article>'
OG = ('<meta property="og:title" content="Chivilcoy: una beba fue internada con signos de abuso">'
      '<meta property="og:description" content="La madre llevó a la pequeña al Hospital.">')

d = detalle_de(f'<html><head>{OG}</head><body><header><h1>Chivilcoy: una beba fue internada con signos de abuso</h1></header>'
               f'<div class="col">{TARJETA}{TARJETA}</div><div class="wysiwyg">{CUERPO_BEBA}</div></body></html>')
chequear("la primera tarjetita del costado no le gana a la nota", d["cuerpo"].startswith("Una denuncia por abuso"))
chequear("y el texto de la tarjetita no se cuela", "comisarios" not in d["cuerpo"])

d = detalle_de(f'<html><head>{OG}</head><body><article class="principal"><h1>Chivilcoy: una beba</h1>{CUERPO_BEBA}'
               f'<div class="relacionadas">{TARJETA}</div></article></body></html>')
chequear("un <article> que sí contiene la nota se sigue usando", d["cuerpo"].startswith("Chivilcoy: una beba"))

d = detalle_de(f'<html><head>{OG}</head><body><div class="entry-content">{CUERPO_BEBA}</div>{TARJETA}</body></html>')
chequear("una clase de cuerpo conocida se sigue usando", d["cuerpo"].startswith("Una denuncia por abuso"))

d = detalle_de(f'<html><head>{OG}</head><body><div class="grilla">{CUERPO_BEBA}</div></body></html>')
chequear("sin <article> ni clase conocida, también encuentra los párrafos", d["cuerpo"].startswith("Una denuncia"))

d = detalle_de(f'<html><head>{OG}</head><body>{TARJETA}</body></html>')
chequear("si solo hay una tarjeta de otro tema, queda el resumen del medio",
         d["cuerpo"] == "La madre llevó a la pequeña al Hospital.")

d = detalle_de(f'<html><head>{OG}</head><body>{TARJETA}<div class="pie"><p>{"Todos los derechos reservados. " * 4}</p></div></body></html>')
chequear("un pie de copyright corto no pasa por la nota", d["cuerpo"] == "La madre llevó a la pequeña al Hospital.")

d = detalle_de('<html><head><title>El Medio</title></head><body><article>Texto cualquiera de la nota sin título.</article></body></html>')
chequear("con un título que no dice nada, no se descarta el texto", d["cuerpo"].startswith("Texto cualquiera"))

d = detalle_de(f'<html><head>{OG}<title>x</title></head><body><header><h1>Una beba fue internada en Chivilcoy</h1></header>'
               f'<article>{CUERPO_BEBA}</article></body></html>')
chequear("el título se lee aunque el <h1> esté en el encabezado", d["cuerpo"].startswith("Una denuncia"))

d = detalle_de("""<html><head><meta property="og:description" content="{{(desc_pagina)?desc_pagina:'Todas las noticias'}}"></head><body></body></html>""")
chequear("una plantilla sin completar no se toma por resumen", d["descripcion"] == "" and d["cuerpo"] == "")

# --- El control del guion ---
BIEN = "gemini:modelo"
nota_ddi = {"titulo": "La DDI Junín esclareció hurtos cometidos con inhibidores de señal tras un allanamiento"}
otro = {"via": BIEN, "titular": "Dos bicipolicías detuvieron a un ladrón en una fábrica abandonada",
        "bajada": "Estaban de franco y lo atraparon.", "descripcion": ""}
llamadas = []


def ia_que_dice(mismo):
    def redactar(sistema, material, preferir=""):
        llamadas.append(material)
        return {"mismo_hecho": mismo, "motivo": "uno es de hurtos y el otro de bicipolicías"}, "gemini"
    return redactar


def ia_caida(sistema, material, preferir=""):
    raise RuntimeError("sin cupo")


with mock.patch.object(ia, "redactar", ia_que_dice(False)):
    chequear("guion de otro hecho: se frena y dice por qué", "bicipolicías" in G.guion_de_otro_hecho(otro, nota_ddi))
with mock.patch.object(ia, "redactar", ia_que_dice(True)):
    chequear("pocas palabras en común pero la IA dice que es el mismo: sale", G.guion_de_otro_hecho(otro, nota_ddi) == "")
with mock.patch.object(ia, "redactar", ia_caida):
    chequear("sin nada en común y sin IA para confirmar: no sale", G.guion_de_otro_hecho(otro, nota_ddi) != "")
    parecido = dict(otro, bajada="Lo investigan por otros hurtos, estaba de franco.")
    chequear("con algo en común y sin IA para confirmar: sale", G.guion_de_otro_hecho(parecido, nota_ddi) == "")

llamadas.clear()
bueno = {"via": BIEN, "titular": "La DDI esclareció hurtos con inhibidores de señal en Junín", "bajada": "", "descripcion": ""}
with mock.patch.object(ia, "redactar", ia_que_dice(False)):
    chequear("si comparten palabras, no se gasta una consulta a la IA",
             G.guion_de_otro_hecho(bueno, nota_ddi) == "" and not llamadas)
    chequear("un guion por reglas no se controla", G.guion_de_otro_hecho(dict(otro, via="reglas"), nota_ddi) == "")
    chequear("un titular de dos palabras no se puede medir",
             G.guion_de_otro_hecho(otro, {"titulo": "Violento robo"}) == "")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
