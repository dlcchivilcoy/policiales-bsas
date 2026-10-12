# -*- coding: utf-8 -*-
"""Etiqueta de ubicación de los reels de Instagram según la localidad del hecho (12/10/2026). Sin red."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from reels import instagram as IG  # noqa: E402
from reels import publicador as PUB  # noqa: E402
from reels import ubicaciones as UB  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


chequear("clave: tildes, mayúsculas y «Ciudad de …, Buenos Aires»",
         UB.clave("Ciudad de Chacabuco, Buenos Aires") == "chacabuco"
         and UB.clave("San Andrés de Giles") == "san andres de giles" and UB.clave("JUNÍN") == "junin")
tabla = {"chacabuco": {"nombre": "Chacabuco", "id": "108000000000001"},
         "junin": {"nombre": "Junín", "id": "108000000000002", "valido": False},
         "lobos": {"nombre": "Lobos", "id": ""}}
chequear("la localidad del hecho da su location_id", UB.location_id("Chacabuco", tabla) == "108000000000001")
chequear("una ID marcada como no válida no se usa", UB.location_id("Junín", tabla) == "")
chequear("localidad sin ID o desconocida: sin ubicación", UB.location_id("Lobos", tabla) == ""
         and UB.location_id("Mar del Plata", tabla) == "")
chequear("la tabla del repo tiene las 34 localidades + Chivilcoy", len(UB.cargar()) == 35)

URL = "https://ejemplo.com/reel.mp4"
p = IG.contenedor_reel(URL, "x", ubicacion="108000000000001")
chequear("el contenedor lleva location_id", p.get("location_id") == "108000000000001")
chequear("sin ubicación no manda location_id", "location_id" not in IG.contenedor_reel(URL, "x"))
try:
    IG.contenedor_reel(URL, "x", ubicacion="Chacabuco")
    chequear("una ubicación que no es un número frena", False)
except ValueError:
    chequear("una ubicación que no es un número frena", True)

# Publicar: si Instagram rechaza la ubicación, el reel sale igual sin ella.
pedidos = []


def contenedor(uid, tok, params):
    pedidos.append(dict(params))
    if "location_id" in params:
        raise PUB.FalloRed("Instagram: (#100) Param location_id is not a valid location page ID")
    return "CID"


viejos = (PUB.subir_a_release, PUB._contenedor_listo, PUB._publicar_contenedor, UB.cargar)
PUB.subir_a_release = lambda mp4, nombre: "https://ejemplo.com/r.mp4"
PUB._contenedor_listo = contenedor
PUB._publicar_contenedor = lambda uid, tok, cid, caption: "MEDIA1"
UB.cargar = lambda: tabla
try:
    res = PUB.publicar_instagram({"localidad_hecho": "Chacabuco", "descripcion_tiktok": "Texto"}, Path("x.mp4"), "x")
    chequear("ubicación rechazada: se reintenta sin ella y el reel sale",
             res["id"] == "MEDIA1" and res["ubicacion"] is None and len(pedidos) == 2
             and "location_id" in pedidos[0] and "location_id" not in pedidos[1])
    pedidos.clear()
    PUB._contenedor_listo = lambda uid, tok, params: pedidos.append(dict(params)) or "CID"
    res = PUB.publicar_instagram({"localidad_hecho": "Chacabuco", "descripcion_tiktok": "Texto"}, Path("x.mp4"), "x")
    chequear("ubicación aceptada: sale con ella", res["ubicacion"] == "108000000000001"
             and pedidos[0].get("location_id") == "108000000000001")
    PUB._contenedor_listo = lambda uid, tok, params: (_ for _ in ()).throw(PUB.FalloRed("Instagram: video en ERROR"))
    try:
        PUB.publicar_instagram({"localidad_hecho": "Chacabuco"}, Path("x.mp4"), "x")
        chequear("otra falla (no de ubicación) no se esconde", False)
    except PUB.FalloRed:
        chequear("otra falla (no de ubicación) no se esconde", True)
finally:
    PUB.subir_a_release, PUB._contenedor_listo, PUB._publicar_contenedor, UB.cargar = viejos

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
