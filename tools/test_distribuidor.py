# -*- coding: utf-8 -*-
"""Pruebas del buzón para el distribuidor de X/TikTok (reels/distribuidor.py). Sin red."""
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reels import distribuidor as D  # noqa: E402

ok = mal = 0


def chequear(nombre, cond, detalle=""):
    global ok, mal
    ok, mal = (ok + 1, mal) if cond else (ok, mal + 1)
    print(("  ok   " if cond else "  MAL  ") + nombre + ("" if cond else f"  → {detalle}"))


tmp = Path(tempfile.mkdtemp())
D.BUZON = tmp / "buzon_distribuidor.json"
carpeta = tmp / "2026-10-11_1205"
carpeta.mkdir()
ahora = datetime.now(timezone.utc)


def pieza(n, viral=6, horas=1.0):
    mp4 = carpeta / f"reel_{n}.mp4"
    mp4.write_bytes(b"x")
    return ({"orden": n, "url_original": f"https://medio/{n}", "viral": viral,
             "publicado": (ahora - timedelta(hours=horas)).isoformat(),
             "guion": {"titular": f"Choque en Bragado {n}", "bajada": "Dos heridos leves.", "volanta": "BRAGADO"},
             "descripcion_tiktok": "Choque en Bragado. #Bragado #Policiales",
             "video": {"duracion": 42.0}, "localidad_hecho": "Bragado"}, mp4)


subidas = []
def subir(mp4, nombre):
    subidas.append(nombre)
    return f"https://github.com/r/p/releases/download/t/{nombre}"


listas = [pieza(1), pieza(2, viral=9, horas=1), pieza(3, viral=9, horas=8)]
ledger = {"https://medio/1": {"web": {"estado": "ok", "url": "https://www.diariolacampaña.com.ar/n/a"},
                              "youtube": {"estado": "ok", "url": "https://youtube.com/shorts/z"}}}
r = D.dejar(listas, ledger, carpeta, subir, "r/p", "t", lambda p: p["url_original"],
            existe=lambda u: u.endswith("reel_1.mp4"))
d = json.loads(D.BUZON.read_text(encoding="utf-8"))
ev = {e["id"]: e for e in d["eventos"]}
chequear("3 eventos", len(ev) == 3, list(ev))
chequear("reusa el video que ya subió Instagram", subidas == ["2026-10-11_1205_reel_2.mp4",
                                                              "2026-10-11_1205_reel_3.mp4"], subidas)
e1 = ev["policiales:https://medio/1"]
chequear("trae link de la nota y del Short", e1["nota_url"].endswith("/n/a") and "shorts" in e1["youtube_url"], e1)
chequear("usa la bajada y la descripción de TikTok", e1["descripcion"] == "Dos heridos leves." and
         "#Policiales" in e1["texto_tiktok"])
chequear("urgente: viral 9 y reciente", ev["policiales:https://medio/2"]["urgente"] is True)
chequear("no urgente: viral 9 pero de hace 8 h", ev["policiales:https://medio/3"]["urgente"] is False)
D.dejar(listas, ledger, carpeta, subir, "r/p", "t", lambda p: p["url_original"])
d2 = json.loads(D.BUZON.read_text(encoding="utf-8"))
chequear("otra pasada con lo mismo no duplica", len(d2["eventos"]) == 3, len(d2["eventos"]))
viejo = {"eventos": [{"id": "policiales:viejo", "generado": "2020-01-01T00:00:00.000Z"}]}
c = D.combinar(d2, viejo)
chequear("combinar: unión y poda de lo de más de 48 h", len(c["eventos"]) == 3 and
         all(e["id"] != "policiales:viejo" for e in c["eventos"]))
c2 = D.combinar({"eventos": [{"id": "a", "generado": D._iso(ahora)}]}, d2)
chequear("combinar: suma lo de la otra pasada", len(c2["eventos"]) == 4)
import os
os.environ["DISTRIBUIDOR_POLICIALES"] = "0"
chequear("interruptor apagado", D.dejar(listas, ledger, carpeta, subir, "r/p", "t",
                                        lambda p: p["url_original"]) == {"buzon": "apagado"})
print(f"\n--- {ok}/{ok + mal} correctos ---")
sys.exit(1 if mal else 0)
