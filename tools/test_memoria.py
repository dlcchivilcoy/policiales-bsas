# -*- coding: utf-8 -*-
"""La memoria reconoce la MISMA nota aunque el medio cambie cómo escribe la dirección.

Nació el 28/09/2026: Diario Junín publicó «.../102628_dos-juninenses-de-23-y-24-aos-...» a la
tarde y «...-anos-...» a la noche; la memoria comparaba la dirección exacta y el hecho salió
dos veces en YouTube. Sin red.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from reels import ledger as LD

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


I = LD.identidad
DJ = "https://www.diariojunin.com/noticias/"
chequear("Diario Junín: «aos» y «anos» son la misma nota (el caso del 27/09)",
         I(DJ + "102628_dos-juninenses-de-23-y-24-aos-aprehendidos.html")
         == I(DJ + "102628_dos-juninenses-de-23-y-24-anos-aprehendidos.html") == "diariojunin.com#102628")
chequear("...pero dos números distintos son dos notas", I(DJ + "102627_lluvias.html") != I(DJ + "102628_x.html"))
chequear("/nota/7457/titulo -> el número", I("https://noticiasruta5.com/nota/7457/una-avioneta") == "noticiasruta5.com#7457")
chequear("/345553-titulo -> el número",
         I("https://www.diariodemocracia.com/policiales/345553-allanamiento") == "diariodemocracia.com#345553")
chequear("con o sin www, http o https, con o sin barra final: la misma",
         I("http://diariojunin.com/noticias/102628_a/") == I("https://www.diariojunin.com/noticias/102628_b"))
chequear("el mismo número en OTRO medio es otra nota",
         I("https://a.com/nota/7457/x") != I("https://b.com/nota/7457/x"))
F = "https://www.latrochadigital.com.ar/2026/09/27/"
chequear("las que van por fecha (/2026/09/27/titulo) NO toman el año como número",
         I(F + "temporal-en-bragado") != I(F + "choque-en-junin")
         and I(F + "temporal-en-bragado") == I(F + "temporal-en-bragado/"))
chequear("una fecha pegada (20260927-titulo) tampoco es un número de nota",
         I("https://m.com/20260927-robo") != I("https://m.com/20260927-choque"))
chequear("número al final del título (titulo-123456.html)",
         I("https://m.com/policiales/robo-en-el-centro-123456.html") == I("https://m.com/policiales/otro-titulo-123456.html"))
chequear("vacía no rompe", I("") == "" and I(None) == "")

# --- filtrar() con la memoria de verdad (en un archivo temporal) -------------------------
tmp = Path(tempfile.mkdtemp(prefix="memoria_"))
original = LD.ARCHIVO
try:
    LD.ARCHIVO = tmp / "reels_hechos.json"
    LD.registrar([{"url": DJ + "102628_dos-juninenses-de-23-y-24-aos-aprehendidos.html",
                   "titulo": "Dos jóvenes aprehendidos tras allanamientos por venta de estupefacientes"}])
    nueva = {"url": DJ + "102628_dos-juninenses-de-23-y-24-anos-aprehendidos.html",
             "titulo": "Dos juninenses de 23 y 24 años aprehendidos por venta de estupefacientes"}
    otra = {"url": DJ + "102630_volco-un-acoplado.html", "titulo": "Volcó un acoplado sobre la Ruta Nacional 3"}
    pendientes, salteadas = LD.filtrar([nueva, otra])
    chequear("filtrar(): la misma nota con otra dirección se saltea", pendientes == [otra] and salteadas == 1)
    chequear("ya_hecha() también la reconoce", LD.ya_hecha(nueva) and not LD.ya_hecha(otra))
    unicas, rep = LD.filtrar_tanda([nueva, dict(nueva, url=nueva["url"].replace("anos", "aos"), titulo="Otro título"), otra])
    chequear("filtrar_tanda(): dentro de la misma tanda tampoco entra dos veces", len(unicas) == 2 and rep == 1)
finally:
    LD.ARCHIVO = original
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
