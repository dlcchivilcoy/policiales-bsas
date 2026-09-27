# -*- coding: utf-8 -*-
"""La noticia del momento primero (reels/frescura.py). Sin red.

Nació el 27/09/2026: «sea cual sea la temática, que sea la última del día, del momento».
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from reels import frescura as FR

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


chequear("sin zona se toma como UTC (como feedparser)",
         FR.publicado_utc({"publicado": "2026-09-27T15:10:00"}) == "2026-09-27T15:10+00:00")
chequear("con zona argentina se pasa a UTC",
         FR.publicado_utc({"publicado": "2026-09-27T12:10:00-03:00"}) == "2026-09-27T15:10+00:00")
chequear("con Z también", FR.publicado_utc({"publicado": "2026-09-27T15:10:00Z"}) == "2026-09-27T15:10+00:00")
chequear("vacía o rota: sin hora, sin romper",
         FR.publicado_utc({}) == "" and FR.publicado_utc({"publicado": "ayer"}) == "")

ed = FR.edades([{"publicado": "2026-09-27T13:00:00+00:00"}, {"publicado": "2026-09-27T15:00:00Z"},
                {"publicado": "2026-09-27T12:30:00-03:00"}, {}])
chequear("edades: relativas a la más nueva (la de 12:30 AR = 15:30 UTC)",
         ed[:3] == [2.5, 0.5, 0.0])
chequear("edades: la sin hora cuenta como de 6 h antes (más vieja que las de la pasada)",
         ed[3] == 6.0 and ed[3] > max(ed[:3]))
chequear("edades: si ninguna tiene hora, todas iguales (lotes viejos)", FR.edades([{}, {}]) == [0.0, 0.0])

notas = [{"id": 1, "publicado": "2026-09-27T13:00:00"}, {"id": 2},
         {"id": 3, "publicado": "2026-09-27T15:00:00"}, {"id": 4, "publicado": "2026-09-27T14:00:00"}]
chequear("ordenar: la más nueva primero y las sin hora al final",
         [n["id"] for n in FR.ordenar(notas)] == [3, 4, 1, 2])

chequear("hace(): minutos y horas legibles",
         FR.hace(10 / 60) == "10 min más vieja que la más nueva"
         and FR.hace(2.1667) == "2,2 h más vieja que la más nueva")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
