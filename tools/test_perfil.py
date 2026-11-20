# -*- coding: utf-8 -*-
"""Los perfiles productivos de los partidos (agro/perfil.py, 20/11/2026)."""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agro import perfil as PF  # noqa: E402
from agro import reel_zona as RZ  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


TZ = timezone(timedelta(hours=-3))
AF = RZ.datos_argenfields()
chequear("los contornos de los 10 partidos están", len(__import__("json").loads(PF.PARTIDOS.read_text(encoding="utf-8"))) == 10)
chequear("Chivilcoy queda a unos 150-170 km de Buenos Aires", 140 <= (PF.km_a_caba("chivilcoy") or 0) <= 170)
chequear("el primero es Chivilcoy", PF.siguiente({"hechos": []}, AF) == "chivilcoy")
mem = {"hechos": [{"slug": "chivilcoy", "cuando": "2026-11-20T17:30", "publicado": {"instagram": {"id": "1"}}}]}
chequear("después, Alberti", PF.siguiente(mem, AF) == "alberti")

publicados = []


def publicador(pieza, log=print):
    publicados.append(pieza)
    return {"instagram": {"id": "ig"}, "facebook": {"id": "fb"}}


with tempfile.TemporaryDirectory() as d:
    ruta = Path(d) / "agro_perfil.json"
    PF.SALIDA = Path(d) / "salida"          # que la prueba no deje carpetas en salida_agro
    kw = dict(ruta_mem=ruta, af=AF, log=lambda *a: None, publicador=publicador, foto_fn=lambda *a: (None, ""))
    inf = PF.corrida(True, ahora=datetime(2026, 11, 24, 23, 40, tzinfo=TZ), **kw)
    chequear("a las 23:40 (respaldo atrasado) no publica", inf["estado"] == "fuera_de_hora" and not publicados)
    inf = PF.corrida(True, ahora=datetime(2026, 11, 24, 17, 30, tzinfo=TZ), **kw)
    chequear("a las 17:30 publica el de Chivilcoy", inf["estado"] == "ok" and inf["partido"] == "chivilcoy")
    p = publicados[0]
    chequear("es un carrusel de datos (sin web) con 5 a 7 láminas", p["datos"] and 5 <= len(p["carrusel"]["archivos"]) <= 7)
    chequear("el texto cita la fuente y no lleva link de nota",
             "ArgenFields" in p["carrusel"]["caption"] and "/n/" not in p["carrusel"]["caption"])
    inf = PF.corrida(True, ahora=datetime(2026, 11, 24, 17, 50, tzinfo=TZ), **kw)
    chequear("el mismo día no sale otro", inf["estado"] == "ya_salio" and len(publicados) == 1)
    inf = PF.corrida(True, ahora=datetime(2026, 11, 27, 17, 30, tzinfo=TZ), **kw)
    chequear("el viernes sale el siguiente (Alberti)", inf.get("partido") == "alberti")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
