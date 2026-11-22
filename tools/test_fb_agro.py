# -*- coding: utf-8 -*-
"""Pruebas sin red del tope del Facebook de agro (22/11/2026): solo videos, máximo por día, reserva para lo propio.

    python tools/test_fb_agro.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import publicar as PUB  # noqa: E402

bien = mal = 0


def chequear(nombre, cond):
    global bien, mal
    if cond:
        bien += 1
    else:
        mal += 1
        print("FALLA:", nombre)


for k in ("AGRO_FB_MAX_DIA", "AGRO_FB_RESERVA", "AGRO_FB_CARRUSEL"):
    os.environ.pop(k, None)

chequear("tope por defecto 6", PUB.fb_tope() == 6)
chequear("reserva por defecto 2", PUB.fb_reserva() == 2)
chequear("carruseles fuera de FB por defecto", PUB.fb_carruseles() is False)
chequear("con lugar", PUB.lugar_facebook(contar=lambda: 3) is None)
chequear("lleno", "omitido" in (PUB.lugar_facebook(contar=lambda: 6) or {}))
chequear("lleno de más", "omitido" in (PUB.lugar_facebook(contar=lambda: 9) or {}))
chequear("sin leer la página no frena", PUB.lugar_facebook(contar=lambda: None) is None)
chequear("viral con reserva: 3 entra", PUB.lugar_facebook(reserva=2, contar=lambda: 3) is None)
chequear("viral con reserva: 4 no entra", "omitido" in (PUB.lugar_facebook(reserva=2, contar=lambda: 4) or {}))
chequear("el motivo dice la reserva", "reservados" in PUB.lugar_facebook(reserva=2, contar=lambda: 5)["omitido"])

os.environ["AGRO_FB_MAX_DIA"] = "0"
chequear("0 = sin tope", PUB.lugar_facebook(contar=lambda: 50) is None)
os.environ["AGRO_FB_MAX_DIA"] = "x"
chequear("valor roto = 6", PUB.fb_tope() == 6)
os.environ["AGRO_FB_MAX_DIA"] = "10"
chequear("tope configurable", PUB.lugar_facebook(contar=lambda: 9) is None)
os.environ["AGRO_FB_CARRUSEL"] = "1"
chequear("AGRO_FB_CARRUSEL=1 los vuelve", PUB.fb_carruseles() is True)
for k in ("AGRO_FB_MAX_DIA", "AGRO_FB_CARRUSEL"):
    os.environ.pop(k, None)

# El carrusel no toca Facebook: se simula todo lo de afuera.
import types  # noqa: E402

llamadas = []
falso_pb = types.SimpleNamespace(subir_a_release=lambda p, n: f"https://x/{n}")
falso_web = types.SimpleNamespace(activa=lambda: False, faltantes=lambda: [])
sys.modules["reels.publicador"] = falso_pb
sys.modules["reels.web"] = falso_web
import reels  # noqa: E402
reels.publicador, reels.web = falso_pb, falso_web
PUB._carrusel_instagram = lambda urls, cap: llamadas.append("ig") or {"id": "ig1"}
PUB._fotos_facebook = lambda urls, msg: llamadas.append("fb") or {"id": "fb1"}
PUB.historias_de_carruseles = lambda: False


class _Cred:
    def __enter__(self):
        return {}

    def __exit__(self, *a):
        return False


PUB.credenciales_agro = _Cred
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    jpgs = []
    for i in range(3):
        j = Path(tmp) / f"{i}.jpg"
        j.write_bytes(b"x")
        jpgs.append(str(j))
    pieza = {"id": "p1", "datos": True, "guion": {"titular": "t"}, "carrusel": {"archivos": jpgs, "caption": "c"}}
    s = PUB.publicar_carrusel(pieza, log=lambda *a: None)
    chequear("carrusel sale en IG", s.get("instagram", {}).get("id") == "ig1")
    chequear("carrusel no llama a FB", "fb" not in llamadas)
    chequear("FB queda omitido, no error", "omitido" in s.get("facebook", {}) and "error" not in s["facebook"])

print(f"--- {bien}/{bien + mal} correctos ---")
sys.exit(1 if mal else 0)
