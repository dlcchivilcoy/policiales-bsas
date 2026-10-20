# -*- coding: utf-8 -*-
"""Radio de 100 km y cupo de 3 por pasada (17/10/2026, PDF «Prompt integral»). Sin red.

Los límites matemáticos se prueban con datos controlados (un punto armado a 99, 100 y 101 km);
la integración, con localidades reales del catálogo Georef (data/localidades_geo.json).
"""
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
os.environ.pop("POLICE_RADIUS_KM", None)
os.environ.pop("MAX_POLICE_REELS_PER_PASS", None)
from reels import cupo as CUPO, flujo as F, geografia as GEO

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. Límites matemáticos, con datos controlados ------------------------------------------
lat0, lon0 = GEO.referencia()
KM_POR_GRADO = 6371.0088 * math.pi / 180


def punto_a(km):
    """Un lugar `km` al norte del centro de Chivilcoy."""
    return {"estado": "ok", "nombre": f"Prueba {km}", "partido": "Prueba", "lat": lat0 + km / KM_POR_GRADO,
            "lon": lon0, "distancia_km": round(km, 1), "precision": "localidad", "como": "dato de prueba"}


chequear("Haversine: un punto armado a 100 km mide 100,0", GEO.distancia_km(lat0 + 100 / KM_POR_GRADO, lon0) == 100.0)
chequear("a 99 km: elegible", GEO.evaluar(punto_a(99))["elegible"])
chequear("a 100 km: elegible (inclusive)", GEO.evaluar(punto_a(100))["elegible"])
chequear("a 100,1 km: fuera", GEO.evaluar(punto_a(100.1))["estado"] == "fuera_de_radio")
chequear("a 101 km: fuera, con el motivo", "fuera del radio" in GEO.evaluar(punto_a(101))["motivo"])
chequear("la gravedad o la viralidad no existen para el radio: evaluar() no las recibe",
         GEO.evaluar.__code__.co_argcount == 1)

# --- 2. Localidades reales del catálogo ------------------------------------------------------
ev = {k: GEO.de_localidad(k) for k in ("Chivilcoy", "9 de Julio", "Rojas", "Pergamino", "Junín", "Bragado",
                                      "Saladillo", "General Viamonte")}
chequear("Chivilcoy: 0 km, banda chivilcoy, proximidad 100",
         ev["Chivilcoy"]["distancia_km"] == 0 and ev["Chivilcoy"]["banda"] == "chivilcoy"
         and ev["Chivilcoy"]["proximidad"] == 100)
chequear("9 de Julio (99,4 km) entra", ev["9 de Julio"]["elegible"] and ev["9 de Julio"]["distancia_km"] == 99.4)
chequear("Rojas (101,6 km) queda afuera", ev["Rojas"]["estado"] == "fuera_de_radio")
chequear("Pergamino (122,9 km) queda afuera", ev["Pergamino"]["estado"] == "fuera_de_radio")
chequear("Bragado (49,3) es cercana; Junín (91,2), zona",
         ev["Bragado"]["banda"] == "cercana" and ev["Junín"]["banda"] == "zona")
chequear("Saladillo: la ciudad (85,3 km), que Georef solo trae como asentamiento",
         ev["Saladillo"]["distancia_km"] == 85.3)
chequear("General Viamonte del padrón = Los Toldos (93,6 km)",
         ev["General Viamonte"]["nombre"] == "Los Toldos" and ev["General Viamonte"]["elegible"])
chequear("un paraje del catálogo: Gorostiaga (partido de Chivilcoy)",
         GEO.evaluar(GEO.ubicar("Gorostiaga"))["partido"] == "Chivilcoy")
chequear("Moreno (fuera del padrón, 115,5 km) queda afuera",
         GEO.evaluar(GEO.ubicar("Moreno", "Moreno", "Buenos Aires"))["estado"] == "fuera_de_radio")

# --- 3. Ambigüedad, otra provincia, ubicación desconocida o imprecisa → PENDIENTE ------------
chequear("«San José» (11 en la provincia) sin partido: pendiente",
         GEO.evaluar(GEO.ubicar("San José"))["estado"] == "pendiente")
chequear("…con el partido (General Viamonte): resuelve a 76,9 km",
         GEO.evaluar(GEO.ubicar("San José", "General Viamonte"))["distancia_km"] == 76.9)
chequear("otra provincia (Rosario, Santa Fe): fuera, aunque el nombre no esté en el catálogo",
         GEO.evaluar(GEO.ubicar("Rosario", "", "Santa Fe"))["estado"] == "fuera_de_radio")
chequear("un lugar que no está en el catálogo: pendiente, no adentro",
         GEO.evaluar(GEO.ubicar("Villa Inventada"))["estado"] == "pendiente")
chequear("solo el partido y su cabecera cerca del límite (9 de Julio): pendiente",
         GEO.evaluar(GEO.ubicar("", "9 de Julio"))["estado"] == "pendiente")
chequear("solo el partido y su cabecera lejos del límite (Bragado): elegible",
         GEO.evaluar(GEO.ubicar("", "Bragado"))["elegible"])

# --- 4. El lugar que lee la IA, con controles ------------------------------------------------
texto = "Robaron en una vivienda de Chacabuco; los detenidos fueron trasladados a Moreno."
chequear("la IA dice Chacabuco (está en la nota): elegible",
         GEO.evaluar(GEO.lugar_de_la_ia({"localidad": "Chacabuco", "certeza": "explicita"}, texto))["elegible"])
chequear("la IA dice un lugar que NO está en la nota: pendiente",
         GEO.evaluar(GEO.lugar_de_la_ia({"localidad": "Mercedes", "certeza": "explicita"}, texto))["estado"]
         == "pendiente")
chequear("la IA dice «desconocida»: pendiente",
         GEO.evaluar(GEO.lugar_de_la_ia({"localidad": "", "certeza": "desconocida"}, texto))["estado"] == "pendiente")
chequear("inferida: «en nuestra ciudad» de un medio de Bragado → Bragado",
         GEO.evaluar(GEO.lugar_de_la_ia({"localidad": "Bragado", "certeza": "inferida"},
                                        "Robo en un comercio de nuestra ciudad", "Bragado"))["elegible"])
chequear("la IA con la provincia equivocada (Mercedes, Corrientes): fuera",
         GEO.evaluar(GEO.lugar_de_la_ia({"localidad": "Mercedes", "provincia": "Corrientes"},
                                        "Choque en Mercedes, Corrientes"))["estado"] == "fuera_de_radio")

# --- 5. Prefiltro antes de gastar: la sede del medio no alcanza para incluir ni para excluir ---
lejana = {"titulo": "Robaron una moto en el centro", "localidad_medio": "Pergamino"}
chequear("medio de Pergamino sin ninguna localidad cercana en la nota: se descarta antes del guion",
         GEO.prefiltro(lejana, "Pergamino") is not None)
chequear("…pero si la nota nombra a Salto (70,7 km), sigue: el guion decide el lugar",
         GEO.prefiltro(dict(lejana, resumen="El hecho ocurrió en Salto, en la calle Mitre."), "Pergamino") is None)
chequear("…y una mención incidental lejana (un vecino de Rojas) no la salva",
         GEO.prefiltro(dict(lejana, resumen="El acusado es un vecino de Rojas."), "Pergamino") is not None)
chequear("medio de Bragado: nunca se descarta en el prefiltro", GEO.prefiltro({"titulo": "x"}, "Bragado") is None)

# El flujo: con el guion de la IA, cuenta el lugar que leyó; sin IA, la localidad del padrón.
g_ia = {"localidad_hecho": "Bragado", "lugar_del_hecho": {"localidad": "Pergamino", "certeza": "explicita"}}
nota = {"titulo": "Choque fatal en Pergamino", "localidad": "Bragado", "localidad_medio": "Bragado"}
lugar, geo = F.lugar_del_hecho(g_ia, nota)
chequear("flujo: medio de Bragado que cuenta un choque en Pergamino → fuera (cuenta el HECHO)",
         geo["estado"] == "fuera_de_radio" and lugar["segun"] == "ia")
lugar, geo = F.lugar_del_hecho({"localidad_hecho": "Junín"}, {"localidad": "Junín"})
chequear("flujo: sin IA, la localidad del padrón", geo["elegible"] and lugar["segun"] == "padron")

# Lote viejo, de antes del cambio: el publicador evalúa la localidad del hecho de la pieza.
chequear("publicador: pieza vieja de Bolívar → fuera", not GEO.evaluar_pieza({"localidad_hecho": "Bolívar"})["elegible"])
chequear("publicador: la pieza nueva vuelve a medir sus coordenadas",
         GEO.evaluar_pieza({"lugar_hecho": dict(GEO.ubicar("Alberti"), distancia_km=3)})["distancia_km"] == 28.1)

# --- 6. El cupo de la pasada -------------------------------------------------------------------
PAS = ((9, 5), (12, 5), (15, 5), (18, 5), (21, 5), (23, 35))
CUPO.PASADAS_FINDE = ()          # el 17 y 18/10 son sábado y domingo: acá se prueba la grilla de siempre
AR = timezone(timedelta(hours=-3))
chequear("pasada: 12:20 es la de las 12:05", CUPO.pasada_id(PAS, datetime(2026, 10, 17, 12, 20, tzinfo=AR))
         == "2026-10-17T12:05")
chequear("pasada: 12:00 (arranca 5 min antes) también es la de las 12:05",
         CUPO.pasada_id(PAS, datetime(2026, 10, 17, 12, 0, tzinfo=AR)) == "2026-10-17T12:05")
chequear("pasada: 00:40 y 08:00 son la de las 23:35 del día anterior",
         CUPO.pasada_id(PAS, datetime(2026, 10, 18, 0, 40, tzinfo=AR)) == "2026-10-17T23:35"
         and CUPO.pasada_id(PAS, datetime(2026, 10, 18, 8, 0, tzinfo=AR)) == "2026-10-17T23:35")

tmp = Path(tempfile.mkdtemp(prefix="cupo_")) / "cupo.json"
CUPO.ARCHIVO = tmp
clave = lambda p: p["url_original"]
piezas = [{"url_original": f"https://m.test/{i}", "guion": {"titular": f"T{i}"}} for i in range(10)]
chequear("3 por defecto", CUPO.maximo() == 3 and CUPO.libres("P1") == 3)
r = CUPO.reservar("P1", piezas, clave)
chequear("10 candidatas → se reservan 3, nunca más", len(r) == 3 and CUPO.libres("P1") == 0)
r = CUPO.reservar("P1", piezas[:2] + piezas[5:], clave)
chequear("reintento de la misma pasada: no crece", len(r) == 3)
chequear("otra pasada tiene sus 3", CUPO.libres("P2") == 3)
a = {"pasadas": {"P1": {"reservas": [{"clave": "x"}, {"clave": "y"}]}}, "actualizado": "1"}
b = {"pasadas": {"P1": {"reservas": [{"clave": "y"}]}, "P0": {"reservas": [{"clave": "z"}]}}, "actualizado": "2"}
c = CUPO.combinar(a, b)
chequear("combinar (guardar_estado): unión sin duplicar",
         sorted(x["clave"] for x in c["pasadas"]["P1"]["reservas"]) == ["x", "y"] and "P0" in c["pasadas"])
os.environ["MAX_POLICE_REELS_PER_PASS"] = "0"
chequear("MAX_POLICE_REELS_PER_PASS=0 pausa los reels policiales", CUPO.libres("P9") == 0)
os.environ.pop("MAX_POLICE_REELS_PER_PASS")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
