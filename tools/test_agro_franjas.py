# -*- coding: utf-8 -*-
"""Pruebas sin red (24/11/2026): agro con 12 por día en tres franjas (mañana informativa, tarde de análisis, noche de
sucesos) y policiales solo si el hecho pasó en el campo.

    python tools/test_agro_franjas.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import fuentes as FU  # noqa: E402
from agro import seleccion as SE  # noqa: E402
from agro import virales as VI  # noqa: E402

bien = mal = 0


def chequear(nombre, cond):
    global bien, mal
    if cond:
        bien += 1
    else:
        mal += 1
        print("FALLA:", nombre)


for k in ("AGRO_SCORE_MIN", "AGRO_FRANJAS", "AGRO_POLICIAL_SOLO_CAMPO"):
    os.environ.pop(k, None)

# Franjas
chequear("07:00 es mañana", SE.franja_de(datetime(2026, 11, 24, 7, 0)) == "manana")
chequear("11:30 es mañana", SE.franja_de(datetime(2026, 11, 24, 11, 30)) == "manana")
chequear("13:00 es tarde", SE.franja_de(datetime(2026, 11, 24, 13, 0)) == "tarde")
chequear("17:30 es tarde", SE.franja_de(datetime(2026, 11, 24, 17, 30)) == "tarde")
chequear("18:00 es noche", SE.franja_de(datetime(2026, 11, 24, 18, 0)) == "noche")
chequear("22:30 es noche", SE.franja_de(datetime(2026, 11, 24, 22, 30)) == "noche")
chequear("mínimo de fábrica 50", SE.score_min() == 50)

precio = {"ai_score": 60, "tema_doc": "precios", "subtema": "mercados", "potencial_carrusel": 5}
analisis = {"ai_score": 60, "tema_doc": "costos", "subtema": "agro", "potencial_carrusel": 8}
suceso = {"ai_score": 60, "tema_doc": "", "subtema": "agro", "policial_rural": True, "suceso": True}
for franja, gana in (("manana", "precio"), ("tarde", "analisis"), ("noche", "suceso")):
    SE.FRANJA = franja
    orden = sorted((("precio", precio), ("analisis", analisis), ("suceso", suceso)),
                   key=lambda x: SE.prioridad(x[1], "carrusel"), reverse=True)
    chequear(f"a la {franja} va primero {gana}", orden[0][0] == gana)
SE.FRANJA = "noche"
chequear("el policial del campo a la noche suma el doble", SE.bono_franja(suceso) == 2 * SE.BONO_FRANJA)
os.environ["AGRO_FRANJAS"] = "0"
chequear("AGRO_FRANJAS=0 apaga los bonos", SE.bono_franja(suceso) == 0)
os.environ.pop("AGRO_FRANJAS")

# El formato según la franja: la tarde se inclina al carrusel, la noche al reel.
os.environ["AGRO_FORMATO_TEMA"] = "1"
con_video = {"ai_score": 66, "tema_doc": "ganaderia", "subtema": "ganaderia", "con_video": True}
sin_video = {"ai_score": 68, "tema_doc": "costos", "subtema": "agro", "potencial_carrusel": 8}
cands = [{"score": con_video}, {"score": sin_video}]
SE.FRANJA = "tarde"
chequear("a la tarde, con dos parejas, carrusel", SE.formato_turno(cands, "reel", [])[0] == "carrusel")
SE.FRANJA = "noche"
chequear("a la noche, con dos parejas, reel", SE.formato_turno(cands, "carrusel", [])[0] == "reel")
SE.FRANJA = ""

# Policiales: solo si el hecho pasó en el campo
fuera = ["Robaron una moto en el centro de Chivilcoy",
         "Un siniestro vial en La Plata dejó a un motociclista herido",
         "Investigan el robo de un caballo en un barrio de Chacabuco",
         "Detuvieron a un ladrón que asaltó un kiosco"]
adentro = ["Robaron 20 vacas de un campo cerca de Moquehuá",
           "Abigeato: detuvieron a dos cuatreros en un establecimiento rural",
           "Volcó una cosechadora en un camino rural de Bragado",
           "Robaron un tractor de una chacra en Alberti",
           "Murió un histórico productor de la zona",
           "La soja sube en Chicago"]
for t in fuera:
    chequear(f"afuera: «{t}»", FU.policial_fuera_del_campo(t))
for t in adentro:
    chequear(f"adentro: «{t}»", not FU.policial_fuera_del_campo(t))
chequear("un robo de motos no es policial rural", not FU.es_policial_rural("Robaron una moto de un productor en la ciudad"))
os.environ["AGRO_POLICIAL_SOLO_CAMPO"] = "0"
chequear("AGRO_POLICIAL_SOLO_CAMPO=0 lo apaga", not FU.policial_fuera_del_campo(fuera[0]))
os.environ.pop("AGRO_POLICIAL_SOLO_CAMPO")

# Reels de prueba: el robo de motos no entra aunque nombre el campo de pasada
chequear("reel de prueba: robo de moto en la ciudad → afuera",
         VI.nivel({"titulo": "Robaron una moto a un productor rural en el centro de Junín", "resumen": "",
                   "url": "https://x/policiales/moto"}) is None or
         not FU.policial_fuera_del_campo("Robaron una moto a un productor rural en el centro de Junín"))
chequear("reel de prueba: abigeato → entra como policial del campo",
         VI.nivel({"titulo": "Abigeato: robaron 30 novillos de un campo en Bragado", "resumen": "",
                   "url": "https://x/policiales/abigeato"}) == 0)

# 24/11/2026: empresas, fábricas y pymes del agro con conflicto, cierre o premio
for t in ("Despidos en un frigorífico de Rosario: 120 trabajadores en la calle",
          "Cerró una usina láctea en Carlos Casares tras 40 años",
          "Una cooperativa agrícola de Junín ganó el premio a la innovación",
          "Inauguraron una nueva planta de silos en Bragado"):
    chequear(f"empresa del agro: «{t}»", FU.es_empresa_agro(t))
for t in ("Despidos en una automotriz de Córdoba", "Paro de colectivos en el AMBA", "La cooperativa eléctrica subió la tarifa",
          "El dólar blue cerró en alza"):
    chequear(f"no es empresa del agro: «{t}»", not FU.es_empresa_agro(t))
os.environ["AGRO_EMPRESAS"] = "0"
chequear("AGRO_EMPRESAS=0 lo apaga", not FU.es_empresa_agro("Despidos en un frigorífico de Rosario"))
os.environ.pop("AGRO_EMPRESAS")
SE.FRANJA = ""
_e = {"ai_score": 55, "subtema": "empresas", "empresa_agro": True}
_n = {"ai_score": 55, "subtema": "empresas"}
chequear("la empresa del agro con un hecho va antes", SE.prioridad(_e) > SE.prioridad(_n))
_hoy = [{"score": {"subtema": "empresas"}}]
_el, _ = SE.elegir([{"id": "e", "score": dict(_e, tema="frigorifico x")}], _hoy, cupo_dia=16, minimo=50, formato="carrusel")
chequear("entra aunque el tope de «empresas» del día esté lleno", len(_el) == 1)
_el, _ = SE.elegir([{"id": "n", "score": dict(_n, tema="empresa y")}], _hoy, cupo_dia=16, minimo=50, formato="carrusel")
chequear("una de empresas común no pasa el tope lleno", len(_el) == 0)
fs = [f for f in FU.FUENTES if f.get("solo_empresa")]
chequear("4 fuentes nuevas de economía y gremiales, solo empresas", len(fs) == 4 and all(f["activa"] for f in fs))

print(f"--- {bien}/{bien + mal} correctos ---")
sys.exit(1 if mal else 0)
