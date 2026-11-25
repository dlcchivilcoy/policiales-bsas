# -*- coding: utf-8 -*-
"""Pruebas sin red (25/11/2026): la grilla del día de agro (agro/agenda.py) y el margen entre posteos.

    python tools/test_agro_grilla_dia.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for v in ("AGRO_GRILLA_DIA", "AGRO_CORRIDAS", "AGRO_AGENDA", "AGRO_VIRALES", "AGRO_PRUEBA_TANDAS", "AGRO_PARTICIPA",
          "AGRO_REEL_DATOS", "AGRO_INTERVALO_MIN", "AGRO_POR_CORRIDA", "AGRO_HISTORIAS_DATOS", "AGRO_MARGEN_MIN"):
    os.environ.pop(v, None)

from agro import agenda as AG  # noqa: E402
from agro import publicar as PUB  # noqa: E402
from agro import seleccion as SE  # noqa: E402

bien = mal = 0
TZ = timezone(timedelta(hours=-3))


def chequear(nombre, cond):
    global bien, mal
    if cond:
        bien += 1
    else:
        mal += 1
        print("FALLA:", nombre)


ag = AG.agenda()
feed = [(h * 60 + m, t) for h, m, t in ag if AG.cuenta_para_el_margen(t)]
# Los de workflow propio, en sus huecos: 11:25 la zona y 12:40 la Provincia (o el perfil).
todo = sorted([t for t, _ in feed] + [11 * 60 + 25, 12 * 60 + 40])
tipos = [t for _, t in feed]
chequear("26 posteos por día (12 noticias, 11 virales, El campo hoy, zona y Provincia)",
         len(todo) == 26 and tipos.count("viral") == 11 and sum(t in ("reel", "carrusel") for t in tipos) == 12
         and tipos.count("reel_datos") == 1)
huecos = [b - a for a, b in zip(todo, todo[1:])]
chequear("entre posteo y posteo, de 35 a 40 minutos", min(huecos) >= 35 and max(huecos) <= 40)
chequear("de 07:00 a 22:50", todo[0] == 7 * 60 and todo[-1] == 22 * 60 + 50)
chequear("noticia y viral alternados (nunca dos virales seguidos)",
         all(not (a == "viral" and b == "viral") for a, b in zip(tipos, tipos[1:])))
franjas = [SE.franja_de(datetime(2026, 11, 26, t // 60, t % 60)) for t, x in feed if x in ("reel", "carrusel")]
chequear("4 noticias de mañana, 4 de tarde y 4 de noche",
         (franjas.count("manana"), franjas.count("tarde"), franjas.count("noche")) == (4, 4, 4))

# Cada corrida espera como mucho 80 minutos (la máquina corta a los 150 y se saltea lo que pasa de 120).
largos = []
for h, m in AG.corridas():
    ini, ok, turnos = AG.corrida(datetime(2026, 11, 26, h, m, tzinfo=TZ))
    largos.append((turnos[-1][0] - ini).total_seconds() / 60 if turnos else 0)
chequear("9 corridas (8 de noticias + la de El campo hoy) y ninguna espera más de 80 min",
         len(AG.corridas()) == 9 and max(largos) <= 80 and all(x >= 0 for x in largos))
chequear("El campo hoy a las 08:15", AG.hora_reel_datos() == (8, 15))
chequear("las historias para participar quedan adentro de una corrida",
         AG.horas_participa() == [(11, 0), (14, 0), (19, 0), (21, 45)])
chequear("ningún horario queda fuera de una corrida",
         all(AG.inicio_corrida(datetime(2026, 11, 26, h, m, tzinfo=TZ)) is not None for h, m, _ in ag))
chequear("los virales cuentan para el margen; las historias no",
         AG.cuenta_para_el_margen("viral") and not AG.cuenta_para_el_margen("participa")
         and AG.intervalo_min() == 30)

os.environ["AGRO_GRILLA_DIA"] = "0"
chequear("AGRO_GRILLA_DIA=0: la agenda de antes", AG.corridas_noticias()[1] == (10, 0) and AG.intervalo_min() == 90
         and not AG.cuenta_para_el_margen("viral") and AG.hora_reel_datos() == (8, 0))
os.environ.pop("AGRO_GRILLA_DIA")

# El margen de lo que sale fuera de la grilla (vigía del tiempo, zona, Provincia).
ahora = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
dormido = []
s = PUB.esperar_margen(log=lambda *a: None, leer=lambda: ahora - timedelta(minutes=5), dormir=dormido.append,
                       ahora=ahora)
chequear("el último salió hace 5 min: espera 15", round(s / 60) == 15 and dormido == [s])
s = PUB.esperar_margen(log=lambda *a: None, leer=lambda: ahora - timedelta(minutes=45), dormir=dormido.append,
                       ahora=ahora)
chequear("hace 45 min: no espera", s == 0)
s = PUB.esperar_margen(log=lambda *a: None, leer=lambda: None, dormir=dormido.append, ahora=ahora)
chequear("sin poder leer Instagram: no frena", s == 0)
os.environ["AGRO_MARGEN_MIN"] = "0"
chequear("AGRO_MARGEN_MIN=0 lo apaga", PUB.esperar_margen(leer=lambda: ahora, ahora=ahora) == 0)
os.environ.pop("AGRO_MARGEN_MIN")

print(f"--- {bien}/{bien + mal} correctos ---")
sys.exit(1 if mal else 0)
