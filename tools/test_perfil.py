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
    inf = PF.corrida(True, ahora=datetime(2026, 11, 24, 12, 15, tzinfo=TZ), **kw)
    chequear("a las 12:15 publica el de Chivilcoy", inf["estado"] == "ok" and inf["partido"] == "chivilcoy")
    p = publicados[0]
    # 21/11/2026: es un REEL animado (el mapa del partido se arma solo); el carrusel queda con AGRO_PERFIL_FORMATO.
    chequear("es un reel de datos, solo FB e IG, sin colab ni YouTube",
             p["datos"] and p["formato"] == "reel" and Path(p["reel"]["archivo"]).is_file()
             and tuple(p["redes"]) == ("facebook", "instagram") and not p["colab_diario"] and p["youtube"] is False)
    chequear("el reel dura entre 20 y 45 s y tiene sonido", 20 <= p["reel"]["duracion"] <= 45 and p["reel"]["con_sonido"])
    texto = p["guion"]["descripcion"]
    chequear("el texto cita la fuente y no lleva link de nota", "ArgenFields" in texto and "/n/" not in texto)
    an = PF.mapa_animado("chivilcoy", 400)
    chequear("el mapa animado arranca vacío y termina con Chivilcoy en naranja",
             an(0.0).getchannel("A").getbbox() is None
             and int((__import__("numpy").asarray(an(1.0))[:, :, :3] == PF.DORADO).all(axis=2).sum()) > 500)
    inf = PF.corrida(True, ahora=datetime(2026, 11, 24, 12, 40, tzinfo=TZ), **kw)
    chequear("el mismo día no sale otro", inf["estado"] == "ya_salio" and len(publicados) == 1)
    import os
    os.environ["AGRO_PERFIL_FORMATO"] = "carrusel"
    inf = PF.corrida(True, ahora=datetime(2026, 11, 27, 12, 15, tzinfo=TZ), **kw)
    os.environ.pop("AGRO_PERFIL_FORMATO")
    chequear("el viernes sale el siguiente (Alberti)", inf.get("partido") == "alberti")
    chequear("con AGRO_PERFIL_FORMATO=carrusel, el carrusel de 5 a 7 láminas",
             publicados[-1]["formato"] == "carrusel" and 5 <= len(publicados[-1]["carrusel"]["archivos"]) <= 7)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
