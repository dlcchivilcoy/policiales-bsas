# -*- coding: utf-8 -*-
"""Pruebas sin red (25/11/2026): los reels con datos oficiales de la Provincia (agro/reel_pba.py).

    python tools/test_reel_pba.py
"""
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for v in ("AGRO_PBA", "AGRO_PBA_DIAS", "AGRO_PBA_VENTANA"):
    os.environ.pop(v, None)

from agro import reel_pba as P  # noqa: E402

bien = mal = 0


def chequear(nombre, cond):
    global bien, mal
    if cond:
        bien += 1
    else:
        mal += 1
        print("FALLA:", nombre)


ZONA = [("06224", "Chivilcoy"), ("06021", "Alberti"), ("06112", "Bragado"), ("06854", "25 de Mayo"),
        ("06714", "San Andrés de Giles"), ("06210", "Chacabuco"), ("06763", "Suipacha")]
OTRO = ("06441", "La Plata")

chequear("slug como el del mapa", P.slug("San Andrés de Giles") == "san-andres-de-giles"
         and P.slug("25 de Mayo") == "25-de-mayo")
chequear("la zona del mapa tiene a Chivilcoy", "chivilcoy" in P.zona() and len(P.zona()) == 10)

# Transferencias: 2025 y 2026 (enero a agosto), cada partido con un monto distinto; La Plata fuera de la zona.
tr = ["anio,mes,municipio_id,municipio_nombre,concepto,monto"]
for anio, k in ((2025, 1.0), (2026, 1.4)):
    for mes in range(1, 9):
        for i, (cod, nom) in enumerate(ZONA + [OTRO]):
            base = (100 + 10 * i) * 1e6 * k
            tr.append(f"{anio},{mes},{cod},{nom},Coparticipación Bruta,{base}")
            tr.append(f"{anio},{mes},{cod},{nom},Fondo Financiamiento Educativo,{base * 0.1}")
for anio in range(2018, 2025):
    for cod, nom in ZONA + [OTRO]:
        tr.append(f"{anio},1,{cod},{nom},Coparticipación Bruta,{1e6 * (2 if nom == 'La Plata' else 1)}")
trib = ["anio,mes,id_municipio,nombre_municipio,concepto,monto"]
for mes in range(1, 9):
    for i, (cod, nom) in enumerate(ZONA):
        trib.append(f"2026,{mes},{cod},{nom},Inmobiliario Rural Libre Disponibilidad,{(5 + i) * 1e6}")
        trib.append(f"2026,{mes},{cod},{nom},Inmobiliario Rural Fondo Compensador,{(3 + i) * 1e6}")
        trib.append(f"2026,{mes},{cod},{nom},Ingresos Brutos Pequeños Contribuyentes,{(1 + i) * 1e6}")
for cod, nom in ZONA:                                      # el error de la base: «2027»
    trib.append(f"2027,12,{cod},{nom},Inmobiliario Rural Libre Disponibilidad,999999999")
pob = ["municipio_id,municipio_nombre,2024,2025,,"] + [f"{c},{n},{60000 + 1000 * i},{61000 + 1000 * i},,"
                                                        for i, (c, n) in enumerate(ZONA)]
bov = ["anio,municipio_id,municipio_nombre,stock"] + [f"{a},{c},{n},{80000 + 500 * a % 7 + 1000 * i}"
                                                       for a in range(2015, 2024) for i, (c, n) in enumerate(ZONA)]
agr = ["cultivo,campania,municipio_id,municipio_nombre,superficie_sembrada,superficie_cosechada,produccion,rendimiento"]
for k, camp in enumerate(["2017/18", "2018/19", "2019/20", "2020/21", "2021/22", "2022/23", "2023/24", "2024/25"]):
    for i, (c, n) in enumerate(ZONA):
        seca = 0.3 if camp == "2022/23" else 1
        agr += [f"Soja total,{camp},{c},{n},1,1,{(200000 + 1000 * i) * seca},1",
                f"Maíz,{camp},{c},{n},1,1,{(150000 + k * 1000) * seca},1",
                f"Soja 1ra,{camp},{c},{n},1,1,999999,1"]
agr.append("Trigo total,2025/26,06224,Chivilcoy,1,1,200000,1")      # campaña sin terminar: no cuenta

d = P.leer({"transferencias": "\n".join(tr), "tributos": "\n".join(trib), "poblacion": "\n".join(pob),
            "bovinos": "\n".join(bov), "agricola": "\n".join(agr)})
chequear("solo la zona (La Plata afuera de los mapas)", "la-plata" not in d["copart"] and "chivilcoy" in d["copart"])
chequear("la población del último año", d["poblacion"]["chivilcoy"] == 61000)
chequear("último mes de transferencias: agosto de 2026", P.ultimo_mes(d, hoy=date(2026, 11, 25)) == (2026, 8))
chequear("los meses del futuro («2027») no cuentan", P.ultimo_mes(d, "trib", hoy=date(2026, 11, 25)) == (2026, 8))

T = P.temas_disponibles(d, log=lambda *a: None)
chequear("los temas con datos (sin porcinos: no hay base)",
         {"transferencias", "transferencias_suba", "coparticipacion", "inmobiliario_rural", "pequenos_contribuyentes",
          "bovinos", "granos"} <= set(T) and "porcinos" not in T)
t = T["transferencias"]
chequear("transferencias: arranca con el mapa (Chivilcoy en el centro) y cierra",
         t["diapositivas"][0][0] == "mapa" and "chivilcoy" in t["diapositivas"][0][1]["valores"]
         and t["diapositivas"][-1][0] == "cierre" and t["informe"] == "2026-08")
chequear("transferencias: el número de Chivilcoy en millones del mes",
         abs(t["diapositivas"][2][1]["numero"] - 154) < 0.01)   # 140 + 10 % del Fondo Educativo
chequear("el texto es una nota: Chivilcoy, el puesto, los vecinos y la fuente",
         "Chivilcoy" in t["texto"][0] and "puesto" in t["texto"][0] and "Alberti" in t["texto"][2]
         and "Ministerio de Economía" in t["fuente"])
chequear("suba interanual: +40 % (pesos corrientes, lo aclara)",
         abs(T["transferencias_suba"]["diapositivas"][2][1]["numero"] - 40) < 0.01
         and "inflación" in " ".join(T["transferencias_suba"]["texto"]))
co = T["coparticipacion"]
chequear("coparticipación: de cada $1.000, contra el total de la provincia (con La Plata)",
         co["diapositivas"][1][0] == "serie" and 0 < co["diapositivas"][2][1]["numero"] < 1000)
chequear("Inmobiliario Rural: suma los dos conceptos y por hectárea del mapa",
         abs(T["inmobiliario_rural"]["diapositivas"][2][1]["numero"] - 64) < 0.01
         and T["inmobiliario_rural"]["diapositivas"][1][1]["titulo"] == "Por hectárea del partido")
chequear("pequeños contribuyentes: comercios y pymes", "pymes" in T["pequenos_contribuyentes"]["gancho"].lower())
g = T["granos"]
chequear("granos: solo los totales (no «Soja 1ra») y la última campaña completa",
         g["diapositivas"][0][1]["sub"].endswith("2024/25") and abs(g["diapositivas"][0][1]["valores"]["chivilcoy"]
                                                                     - 357) < 0.5)
chequear("granos: la peor, la sequía", "sequía" in g["texto"][1])

# Cuál sale: un mes nuevo de transferencias primero; después, el usado hace más tiempo.
hoy = date(2026, 11, 26)
chequear("mes nuevo → transferencias", P.elegir_tema({"reels": []}, T, hoy) == "transferencias")
usado = {"reels": [{"dia": "2026-11-20", "tema": "transferencias", "informe": "2026-08", "publicado": {"x": 1}}]}
chequear("ya salió ese mes → otro tema", P.elegir_tema(usado, T, hoy) not in ("transferencias", None))
todos = {"reels": [{"dia": "2026-11-2" + str(i % 6), "tema": k, "informe": "2026-08", "publicado": {"x": 1}}
                   for i, k in enumerate(T)]}
chequear("todos usados hace menos de 10 días → no sale nada", P.elegir_tema(todos, T, hoy) is None)

# La corrida: días, ventana y que no repite.
with tempfile.TemporaryDirectory() as tmp:
    mem = Path(tmp) / "pba.json"
    martes = datetime(2026, 11, 24, 12, 40, tzinfo=P.TZ_AR)
    chequear("martes: es el día del perfil, no sale", P.corrida(True, ahora=martes, ruta_mem=mem, datos=d,
                                                                 log=lambda *a: None)["estado"] == "otro_dia")
    tarde = datetime(2026, 11, 26, 16, 0, tzinfo=P.TZ_AR)
    chequear("fuera de 12:30-13:30 no publica", P.corrida(True, ahora=tarde, ruta_mem=mem, datos=d,
                                                           log=lambda *a: None)["estado"] == "fuera_de_hora")
    os.environ["AGRO_PBA"] = "0"
    chequear("AGRO_PBA=0 lo apaga", P.corrida(True, ahora=martes, ruta_mem=mem, datos=d)["estado"] == "apagado")
    os.environ.pop("AGRO_PBA")
    import json
    mem.write_text(json.dumps({"reels": [{"dia": "2026-11-26", "tema": "granos", "publicado": {"x": 1}}]}),
                   encoding="utf-8")
    jueves = datetime(2026, 11, 26, 12, 41, tzinfo=P.TZ_AR)
    chequear("el de hoy ya salió: el respaldo no repite",
             P.corrida(True, ahora=jueves, ruta_mem=mem, datos=d, log=lambda *a: None)["estado"] == "ya_salio")

print(f"--- {bien}/{bien + mal} correctos ---")
sys.exit(1 if mal else 0)
