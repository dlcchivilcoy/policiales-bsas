# -*- coding: utf-8 -*-
"""Auditoría por pasada, métricas a edad fija y panel editorial (17/10/2026, etapa 7). Sin red."""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from reels import auditoria as AU, metricas as ME   # noqa: E402
from tools import panel as PA                       # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


tmp = Path(tempfile.mkdtemp(prefix="panel_"))
AU.ARCHIVO = tmp / "auditoria.json"

# --- 1. Auditoría ------------------------------------------------------------------------------
AU.anotar("armado", {"notas_scrapeadas": 30, "fuera_de_radio": [{"titulo": "A", "localidad": "Pergamino", "km": 122.9}]},
          pid="2026-10-10T12:05")
AU.anotar("armado", {"notas_scrapeadas": 31, "fuera_de_radio": [{"titulo": "A", "localidad": "Pergamino", "km": 122.9},
                                                                {"titulo": "B", "localidad": "Bolívar", "km": 178.3}]},
          pid="2026-10-10T12:05")
a = AU.cargar()["pasadas"]["2026-10-10T12:05"]["armado"]
chequear("una corrida repetida suma las listas sin duplicar y pisa los números",
         a["notas_scrapeadas"] == 31 and [x["titulo"] for x in a["fuera_de_radio"]] == ["A", "B"])
pol = {"pasadas": {"P": {"armado": {"cuando": "2026-10-17T12:10", "x": 1}}}}
nac = {"pasadas": {"P": {"nacionales": {"cuando": "2026-10-17T12:20", "y": 2}}}}
c = AU.combinar(pol, nac)
chequear("combinar: el trabajo de policiales y el de nacionales escriben partes distintas de la misma pasada",
         set(c["pasadas"]["P"]) == {"armado", "nacionales"})

# --- 2. Métricas a edad fija -----------------------------------------------------------------------
ahora = datetime(2026, 10, 17, 21, 0, tzinfo=timezone.utc)
hace = lambda h: (ahora - timedelta(hours=h)).replace(tzinfo=None).isoformat(timespec="seconds")   # noqa: E731
pol_ledger = {
    "u1": {"titular": "Choque en Bragado", "lugar_hecho": "Bragado", "distancia_km": 49.3,
           "instagram": {"estado": "ok", "id": "IG1", "cuando": hace(30)},
           "facebook": {"estado": "ok", "id": "FB1", "cuando": hace(30)},
           "youtube": {"estado": "ok", "id": "YT1", "cuando": hace(30)}},
    "u2": {"titular": "Recién salido", "youtube": {"estado": "ok", "id": "YT2", "cuando": hace(3)}},
    "u3": {"titular": "Muy viejo", "youtube": {"estado": "ok", "id": "YT3", "cuando": hace(100)}},
}
nac_mem = {"n1": {"titular": "Boca puntero", "categoria": "deportes",
                  "youtube": {"estado": "ok", "id": "YT4", "cuando": (ahora - timedelta(hours=26)).astimezone(
                      timezone(timedelta(hours=-3))).isoformat(timespec="seconds")},
                  "facebook": {"estado": "ok", "id": "PAG_POST", "cuando": hace(26)}}}
pedidos = []


def pedir_meta(url, params):
    pedidos.append((url, params["fields"]))
    if url.endswith("IG1"):
        return {"like_count": 7, "comments_count": 1}
    return {"views": 450, "likes": {"summary": {"total_count": 3}}, "comments": {"summary": {"total_count": 0}}}


res = ME.medir(pol_ledger, nac_mem, pedir_meta,
               lambda ids: {i: {"viewCount": "40", "likeCount": "2", "commentCount": "0"} for i in ids},
               ahora, tmp / "metricas.json")
met = ME.cargar(tmp / "metricas.json")
chequear("solo se miden las piezas de 24 a 72 h (ni la recién salida ni la vieja)",
         res["medidas"] == 2 and set(met["piezas"]) == {"policiales:u1", "nacionales:n1"})
p1 = met["piezas"]["policiales:u1"]["destinos"]
chequear("policiales: Instagram likes/comentarios, Facebook vistas y YouTube vistas",
         p1["instagram"] == {"likes": 7, "comentarios": 1} and p1["facebook"]["vistas"] == 450
         and p1["youtube"]["vistas"] == 40)
chequear("nacionales: el posteo con placa de Facebook NO se pide (falta pages_read_user_content)",
         "facebook" not in met["piezas"]["nacionales:n1"]["destinos"] and not any("PAG_POST" in u for u, _ in pedidos))
chequear("la pieza guarda franja, día, categoría y distancia para el resumen",
         met["piezas"]["policiales:u1"]["km"] == 49.3 and met["piezas"]["nacionales:n1"]["categoria"] == "deportes"
         and met["piezas"]["policiales:u1"]["franja"] and met["piezas"]["policiales:u1"]["dia"])
ME.medir(pol_ledger, nac_mem, pedir_meta, lambda ids: {}, ahora + timedelta(hours=1), tmp / "metricas.json")
chequear("cada pieza se mide UNA sola vez", len(pedidos) == 2)
chequear("lo no disponible queda escrito (no se inventa)", "instagram_manage_insights" in met["no_disponible"])
r = ME.resumen(met, 7, ahora)
chequear("resumen por destino con medianas y grupos",
         r["youtube"]["n"] == 2 and r["youtube"]["vistas"] == 40 and "categoría" in r["youtube"]["por"]
         and r["youtube"]["por"]["distancia"].get("hasta 50 km", {}).get("n") == 1)

# --- 3. Panel ---------------------------------------------------------------------------------------
PA.ESTADO = tmp
PA.SALIDA = tmp / "panel_editorial.md"
hoy = datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
AU.anotar("publicacion", {"maximo": 3, "reservadas": 2,
                          "piezas": [{"titular": "Choque en Bragado", "localidad": "Bragado", "km": 49.3,
                                      "destinos": {"youtube": {"estado": "ok"}, "instagram": {"estado": "espera",
                                                   "detalle": "intercalado: lo último ya es policial"}}}],
                          "salteadas": [{"titular": "Otro", "motivo": "no entra en la pasada: como mucho 3"}]},
          pid=f"{hoy}T12:05")
AU.anotar("armado", {"notas_scrapeadas": 20, "fuera_de_radio": [{"titulo": "X", "localidad": "Pergamino", "km": 122.9}]},
          pid=f"{hoy}T12:05")
shutil.copy(tmp / "metricas.json", tmp / "metricas.json.bak")
texto = PA.armar(medir=False)
chequear("panel: la pasada con su cupo usado de 3", "### 12:05 — 2 de 3 hechos policiales" in texto)
chequear("panel: lugar y km de cada hecho, y el intercalado a la vista",
         "Bragado (49.3 km)" in texto and "⏳ intercalado" in texto)
chequear("panel: lo que quedó afuera por radio, con la distancia", "Pergamino (122.9 km) ×1" in texto)
chequear("panel: los salteados con su motivo", "no entra en la pasada" in texto)
chequear("panel: métricas con lo no disponible explicado", "Métricas a 24-72 h" in texto and "No disponible" in texto)
chequear("panel: los controles (variables) para pausar sin tocar código", "MAX_POLICE_REELS_PER_PASS" in texto)

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
