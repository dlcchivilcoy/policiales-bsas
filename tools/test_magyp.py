# -*- coding: utf-8 -*-
"""Pruebas sin red (24/11/2026): el informe semanal del MAGyP para el reel de datos de la zona.

    python tools/test_magyp.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import magyp as MG  # noqa: E402
from agro import reel_zona as RZ  # noqa: E402

bien = mal = 0


def chequear(nombre, cond):
    global bien, mal
    if cond:
        bien += 1
    else:
        mal += 1
        print("FALLA:", nombre)


# Páginas como las saca pypdf del informe del 19/11/2026 (recortadas).
GIRASOL = """22
ÁREA
A SEMBRAR
Hectáreas % % % % % %
Bolívar 76.000 1 3 24 33 46 91
Bragado 7.100 32 72 100 100 100
Junín 6.500 40 50
(*) Cifras Provisorias
AVANCE DE LA SIEMBRA DE GIRASOL
CAMPAÑA: 2026/2027 (*)
DELEGACIÓN
19/11"""
SOJA = """25
Hectáreas % % % % % %
Bragado 1ª 304.000 2 15 20 60
2ª 183.000
AVANCE DE LA SIEMBRA DE SOJA"""
MANI = """24
Bragado 600
AVANCE DE LA SIEMBRA DE MANÍ"""
TRIGO = """28
Bragado T. pan 171.000
AVANCE DE LA COSECHA DE TRIGO"""
ESTADO = """34
E C F L M MB B R M
BOLÍVAR - 5 50 45 - 90 10 - - E/A
BRAGADO - - 50 50 - - 100 - - A
HUMEDAD Y ESTADO DE LOS CULTIVOS
PROVINCIA DELEGACIÓN
TRIGO
Estadio Fenológico Estado General Humedad"""

d = MG.leer_paginas([GIRASOL, SOJA, MANI, TRIGO, ESTADO, "otra página sin tablas"])
av = {(a["cultivo"], a["sub"]): a for a in d["avance"]}
chequear("girasol: 7.100 ha, 100 % sembrado", av[("girasol", "")]["hectareas"] == 7100 and av[("girasol", "")]["pct"] == 100)
chequear("soja de 1.ª: 60 %, antes 20 %", av[("soja", "1ª")]["pct"] == 60 and av[("soja", "1ª")]["antes"] == 20)
chequear("soja de 2.ª: sin arrancar", av[("soja", "2ª")]["pct"] == 0 and av[("soja", "2ª")]["hectareas"] == 183000)
chequear("maní: 600 ha (número chico) sin arrancar", av[("maní", "")]["hectareas"] == 600 and av[("maní", "")]["pct"] == 0)
chequear("trigo: la cosecha de trigo pan", av[("trigo", "pan")]["labor"] == "cosecha" and av[("trigo", "pan")]["hectareas"] == 171000)
e = d["estado"][0]
chequear("trigo: bueno, floración y llenado (empate), humedad adecuada",
         e["cultivo"] == "trigo" and e["estado"] == "bueno" and e["estadio"] == "floración y llenado"
         and e["humedad"] == "adecuada")

html = ('<a href="/sitio/x/261112_Informe Semanal al 12_11_2026.pdf">a</a>'
        '<a href="/sitio/x/261119_ Informe Mensual al 19_11_2026.pdf">b</a>'
        '<a href="/sitio/x/261119_Informe Semanal al 19_11_2026.pdf">c</a>')
url, fecha = MG.ultimo(html)
chequear("el listado: el semanal más nuevo (no el mensual)", fecha == date(2026, 11, 19) and "Semanal" in url
         and "%20" in url)

info = dict(d, fecha="2026-11-19", url=url)
chequear("vigente 10 días", MG.vigente(info, date(2026, 11, 24)) and not MG.vigente(info, date(2026, 12, 5)))
t = RZ.tema_magyp(info, date(2026, 11, 24))
chequear("el tema arranca con la lista y el gancho, y cierra", t["diapositivas"][0][0] == "lista"
         and t["diapositivas"][0][1]["titulo"] == t["gancho"] and t["diapositivas"][-1][0] == "cierre")
filas = t["diapositivas"][0][1]["filas"]
chequear("primero lo que avanzó en la semana (soja +40)", filas[0] == ("Soja de 1ª · siembra", "60 % (+40)"))
chequear("cita al MAGyP y la delegación", "MAGyP" in t["fuente"] and "Chivilcoy" in t["fuente"])
chequear("sin informe vigente, no hay tema", RZ.tema_magyp(dict(info, fecha="2026-10-01"), date(2026, 11, 24)) is None)

# La prioridad: un informe nuevo va primero; uno ya usado, no.
disp = {"magyp": t, "tierra": {"tema": "tierra"}}
chequear("informe nuevo → sale el MAGyP", RZ.elegir_tema({"reels": []}, disp, date(2026, 11, 24), 0) == "magyp")
usado = {"reels": [{"dia": "2026-11-20", "tema": "magyp", "publicado": {"instagram": {"id": "1"}}}]}
chequear("ya usado esta semana → otro tema", RZ.elegir_tema(usado, disp, date(2026, 11, 24), 0) != "magyp")
chequear("con lluvia fuerte, primero la lluvia", RZ.elegir_tema({"reels": []}, disp, date(2026, 11, 24), 30.0) == "lluvia")

print(f"--- {bien}/{bien + mal} correctos ---")
sys.exit(1 if mal else 0)
