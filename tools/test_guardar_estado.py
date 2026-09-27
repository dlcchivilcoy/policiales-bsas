# -*- coding: utf-8 -*-
"""Guardar la memoria sin choques (tools/guardar_estado.py). Con repos git de prueba,
sin tocar el real.

Reproduce el 27/09/2026: dos pasadas escriben estado/ a la vez, la segunda choca en
salud.json y con `git pull --rebase` se perdía TODA su memoria.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from tools import guardar_estado as GE

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. Combinar ----------------------------------------------------------------------
yt_ok = {"estado": "ok", "id": "A", "cuando": "2026-09-27T18:35:00"}
remoto = {"u1": {"titular": "uno", "youtube": yt_ok, "ultimo": "2026-09-27T18:35:00"}}
nuestro = {"u2": {"titular": "dos", "facebook": {"estado": "ok", "cuando": "2026-09-27T19:00:00"},
                  "ultimo": "2026-09-27T19:00:00"}}
c = GE.combinar_publicados(nuestro, remoto)
chequear("publicados: se suman las notas de las dos pasadas", set(c) == {"u1", "u2"})

nuestro = {"u1": {"instagram": {"estado": "ok", "cuando": "2026-09-27T19:10:00"},
                  "ultimo": "2026-09-27T19:10:00"}}
c = GE.combinar_publicados(nuestro, remoto)
chequear("publicados: en la misma nota se suman las redes",
         c["u1"]["youtube"]["id"] == "A" and c["u1"]["instagram"]["estado"] == "ok"
         and c["u1"]["ultimo"] == "2026-09-27T19:10:00" and c["u1"]["titular"] == "uno")

nuestro = {"u1": {"youtube": {"estado": "fallo", "cuando": "2026-09-27T20:00:00"}}}
c = GE.combinar_publicados(nuestro, remoto)
chequear("publicados: un «ok» no se pisa con una falla posterior", c["u1"]["youtube"]["id"] == "A")

remoto_f = {"u1": {"youtube": {"estado": "fallo", "cuando": "2026-09-27T20:00:00"}}}
c = GE.combinar_publicados({"u1": {"youtube": yt_ok}}, remoto_f)
chequear("publicados: un «ok» le gana a una falla aunque sea anterior", c["u1"]["youtube"]["estado"] == "ok")

h = GE.combinar_hechos({"hechos": {"b": {"cuando": 2}}, "actualizado": "x"},
                       {"hechos": {"a": {"cuando": 1}}, "actualizado": "viejo"})
chequear("reels_hechos: unión de las notas", set(h["hechos"]) == {"a", "b"} and h["actualizado"] == "x")


# --- 2. Guardar contra un repo real de prueba -------------------------------------------
def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout


def escribir(raiz, nombre, datos):
    (raiz / "estado").mkdir(exist_ok=True)
    (raiz / "estado" / nombre).write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


base = Path(tempfile.mkdtemp(prefix="guardar_"))
try:
    remoto_git = base / "remoto.git"
    git(base, "init", "--quiet", "--bare", "-b", "main", str(remoto_git))
    semilla = base / "semilla"
    git(base, "clone", "--quiet", str(remoto_git), str(semilla))
    for r in (semilla,):
        git(r, "config", "user.email", "t@t"); git(r, "config", "user.name", "t")
    escribir(semilla, "publicados.json", {})
    escribir(semilla, "reels_hechos.json", {"hechos": {}})
    escribir(semilla, "salud.json", {"medios": {"x": 0}})
    git(semilla, "add", "."); git(semilla, "commit", "--quiet", "-m", "inicio")
    git(semilla, "push", "--quiet", "origin", "HEAD:main")

    # Dos pasadas arrancan desde el MISMO commit (como la cancelada y la de las 15:05)
    a, b = base / "pasada_a", base / "pasada_b"
    for r in (a, b):
        git(base, "clone", "--quiet", str(remoto_git), str(r))
        git(r, "config", "user.email", "t@t"); git(r, "config", "user.name", "t")

    escribir(a, "salud.json", {"medios": {"x": 1}})
    escribir(a, "reels_hechos.json", {"hechos": {"nota_a": {"cuando": 1}}})
    escribir(a, "publicados.json", {"nota_a": {"youtube": {"estado": "ok", "cuando": "t1"}, "ultimo": "t1"}})
    chequear("la pasada A guarda", "guardada" in GE.guardar("A", raiz=a))

    escribir(b, "salud.json", {"medios": {"x": 5}})            # choca con A en salud.json
    escribir(b, "reels_hechos.json", {"hechos": {"nota_b": {"cuando": 2}}})
    escribir(b, "publicados.json", {"nota_b": {"youtube": {"estado": "ok", "cuando": "t2"}, "ultimo": "t2"}})
    chequear("la pasada B, que arrancó vieja y choca, guarda igual", "guardada" in GE.guardar("B", raiz=b))

    final = base / "final"
    git(base, "clone", "--quiet", str(remoto_git), str(final))
    pub = json.loads((final / "estado" / "publicados.json").read_text(encoding="utf-8"))
    hechos = json.loads((final / "estado" / "reels_hechos.json").read_text(encoding="utf-8"))["hechos"]
    salud = json.loads((final / "estado" / "salud.json").read_text(encoding="utf-8"))
    chequear("en el repo quedan las publicaciones de LAS DOS pasadas", set(pub) == {"nota_a", "nota_b"})
    chequear("...y las notas hechas de las dos", set(hechos) == {"nota_a", "nota_b"})
    chequear("salud.json queda el de la última pasada", salud == {"medios": {"x": 5}})
    chequear("sin cambios nuevos, no commitea de gusto", "al día" in GE.guardar("C", raiz=b))
finally:
    shutil.rmtree(base, ignore_errors=True)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
