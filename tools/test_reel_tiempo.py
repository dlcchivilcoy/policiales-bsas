# -*- coding: utf-8 -*-
"""La vigía del tiempo de agro (agro/reel_tiempo.py, 20/11/2026) con un pronóstico falso: qué reel toca, que no se
repita, el tope por día y la estimación de cuánto llovió. Sin red y sin armar el video."""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agro import reel_tiempo as RT  # noqa: E402

RT.SALIDA = Path(tempfile.mkdtemp()) / "salida"   # que la prueba no deje carpetas en salida_agro

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


TZ = timezone(timedelta(hours=-3))


def serie(desde_utc: datetime, lluvia=lambda t: 0.0, temp=lambda t: 22.0, tormenta=lambda t: False, horas=48):
    out = []
    for k in range(horas):
        t = desde_utc + timedelta(hours=k)
        out.append({"time": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "data": {"instant": {"details": {"air_temperature": temp(t), "wind_speed": 3.0}},
                             "next_1_hours": {"summary": {"symbol_code": "heavyrainandthunder" if tormenta(t)
                                                          else ("rain" if lluvia(t) else "cloudy")},
                                              "details": {"precipitation_amount": lluvia(t)}}}})
    return out


class Resp:
    def __init__(self, js):
        self.status_code, self._js = 200, js

    def json(self):
        return self._js


def get_de(**kw):
    def get(url, params):
        ahora = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=60)
        return Resp({"properties": {"timeseries": serie(ahora, horas=200, **kw)}})
    return get


armados, publicados = [], []


def armar_falso(tema, salida, videos=None):
    armados.append(tema["tema"])
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_bytes(b"x")
    Path(salida).with_suffix(".jpg").write_bytes(b"x")
    return {"archivo": str(salida), "duracion": 20.0, "peso_kb": 1, "vista": str(Path(salida).with_suffix(".jpg")),
            "alto": 1350}


def publicador_falso(p, log=print):
    publicados.append(p)
    return {"instagram": {"id": "ig"}, "facebook": {"id": "fb"}}


def correr(ahora, get, ruta, forzar=""):
    return RT.corrida(True, forzar, ahora=ahora, ruta_mem=ruta, get=get, log=lambda *a: None,
                      publicador=publicador_falso, armar=armar_falso, videos_fn=lambda *a, **k: {})


with tempfile.TemporaryDirectory() as d:
    ruta = Path(d) / "agro_tiempo.json"
    hoy = datetime.now(TZ).replace(hour=9, minute=5, second=0, microsecond=0)
    # Sin nada: no publica, pero anota la lluvia de las próximas horas.
    inf = correr(hoy, get_de(), ruta)
    chequear("sin lluvia ni calor: no publica nada", inf["estado"] == "nada" and not publicados)
    chequear("…y anota el registro de lluvia hora por hora", len(RT.cargar(ruta)["registro"]) >= 6)

    # Lluvia de 2 mm por hora entre las 15 y las 19 (hora argentina) con tormenta: el reel «a qué hora llueve».
    def lluvia(t):
        return 2.0 if 15 <= t.astimezone(TZ).hour < 19 and t.astimezone(TZ).date() == hoy.date() else 0.0
    con_lluvia = get_de(lluvia=lluvia, tormenta=lambda t: lluvia(t) > 0)
    inf = correr(hoy, con_lluvia, ruta)
    chequear("lluvia y tormenta a la tarde: sale «a qué hora llueve» a la mañana",
             inf["estado"] == "ok" and inf["tipo"] == "lluvia_horas" and len(publicados) == 1)
    chequear("el texto dice la hora y que es un pronóstico",
             "15 h" in publicados[0]["guion"]["descripcion"] and "MET Norway" in publicados[0]["guion"]["descripcion"])
    chequear("sale solo en @diarioyradioagro (sin colab)", publicados[0]["colab_diario"] is False)
    inf = correr(hoy + timedelta(hours=1), con_lluvia, ruta)
    chequear("una hora después no lo repite", inf["estado"] == "nada" and len(publicados) == 1)
    inf = correr(hoy.replace(hour=14, minute=30), con_lluvia, ruta)
    chequear("con la lluvia encima (menos de 2 h) tampoco", inf["estado"] == "nada")

    # La vigía corre cada hora mientras llueve; después de que paró, «cuánto llovió».
    for h in range(10, 22):
        correr(hoy.replace(hour=h), con_lluvia, ruta)
    mem = RT.cargar(ruta)
    llov = RT.llovido(mem, hoy.replace(hour=21, minute=10), 24)
    chequear(f"la estimación suma la lluvia de la tarde (~8 mm: {llov[0]:.1f})", 7.5 <= llov[0] <= 8.5)
    chequear("…y publicó «cuánto llovió» cuando paró", any(p["id"].startswith("tiempo-llovio") for p in publicados))
    chequear("tope: no más de 2 reels por día", len([p for p in publicados
                                                    if hoy.strftime("%Y%m%d") in p["id"]]) <= RT.TOPE_DIA)

with tempfile.TemporaryDirectory() as d:
    ruta = Path(d) / "agro_tiempo.json"
    publicados.clear()
    hoy = datetime.now(TZ).replace(hour=8, minute=5, second=0, microsecond=0)
    calor = get_de(temp=lambda t: 37.0 if 14 <= t.astimezone(TZ).hour <= 17 else 28.0)
    inf = correr(hoy, calor, ruta)
    chequear("máxima de 37°: sale el de calor a la mañana", inf.get("tipo") == "calor")
    chequear("…con la máxima en el título", "37°" in publicados[-1]["guion"]["titular"])

with tempfile.TemporaryDirectory() as d:
    ruta = Path(d) / "agro_tiempo.json"
    publicados.clear()
    tarde = datetime.now(TZ).replace(hour=19, minute=5, second=0, microsecond=0)
    frio = get_de(temp=lambda t: 1.0 if 4 <= t.astimezone(TZ).hour <= 7 else 9.0)
    inf = correr(tarde, frio, ruta)
    chequear("mínima de 1° a la madrugada: sale el de helada a la tarde", inf.get("tipo") == "helada")
    os.environ["AGRO_TIEMPO"] = "0"
    chequear("AGRO_TIEMPO=0 apaga", correr(tarde, frio, ruta)["estado"] == "apagado")
    os.environ.pop("AGRO_TIEMPO")

# El rayo y la placa de horas se dibujan.
h = [{"t": datetime.now(TZ) + timedelta(hours=k), "mm": k % 5, "tormenta": k == 3, "temp": 20 + k % 7} for k in range(24)]
chequear("la placa hora por hora se dibuja", RT.placa_horas(h, "X", "y", 3.0).size == (1080, 1350))
chequear("la temperatura hora por hora se dibuja", RT.placa_temperatura(h, "X", "y", 3.0, "max").size == (1080, 1350))

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
