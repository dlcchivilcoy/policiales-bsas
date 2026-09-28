# -*- coding: utf-8 -*-
"""El control de salud: «notas y cero reels» no siempre es una falla. Sin red.

Nació el 28/09/2026: la pasada de las 18:05 salió como FALLA («suele ser la clave de Gemini o
ffmpeg») y eran 2 notas nuevas con la foto rota en el medio; las otras 34 ya tenían reel o
no traían foto.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import salud as S

fallas_t, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas_t.append(nombre)


tmp = Path(tempfile.mkdtemp(prefix="salud_"))
originales = (S.DIAGNOSTICO, S.HISTORIAL, S.RESUMEN_PASADA, S._ultimo_lote)
try:
    S.DIAGNOSTICO, S.HISTORIAL = str(tmp / "ultima.json"), str(tmp / "salud.json")
    S.RESUMEN_PASADA = str(tmp / "_ultima_pasada.json")
    medios = [{"dominio": f"m{i}.com", "nombre": f"M{i}", "localidad": f"L{i % 5}", "candidatas": 2,
               "error": None} for i in range(20)]
    Path(S.DIAGNOSTICO).write_text(json.dumps({"medios": medios, "finales": 36, "cuando_ar": "hoy",
                                               "ventana": "hoy"}), encoding="utf-8")

    def correr(resumen, piezas=0):
        Path(S.HISTORIAL).unlink(missing_ok=True)
        Path(S.RESUMEN_PASADA).unlink(missing_ok=True)
        if resumen is not None:
            Path(S.RESUMEN_PASADA).write_text(json.dumps(resumen), encoding="utf-8")
        S._ultimo_lote = lambda: {"piezas": [{"apto_para_publicar": True, "tenia_foto": True}] * piezas}
        return S.revisar()

    f, a, i = correr({"nuevas": 2, "piezas": 0, "ya_hechas": 23, "sin_material": 10,
                      "descartadas": ["La imagen que declara la nota no se pudo bajar."] * 2})
    chequear("el caso del 28/09 (2 nuevas, fotos rotas): aviso, NO falla",
             not f and any("2 nota(s) nueva(s)" in x and "no se pudo bajar" in x for x in a))
    f, a, i = correr({"nuevas": 0, "piezas": 0, "ya_hechas": 30, "sin_material": 6})
    chequear("nada nuevo (todo ya tuvo reel): ni falla ni aviso, queda en el informe",
             not f and not any("nueva" in x for x in a) and any("Nada nuevo" in x for x in i))
    f, a, i = correr({"nuevas": 6, "piezas": 0, "descartadas": ["La imagen ... no se pudo bajar."] * 6})
    chequear("6 notas nuevas y ninguna armada: eso SÍ es una falla", any("6 nota(s) nueva(s)" in x for x in f))
    f, a, i = correr(None)
    chequear("si el armado no dejó su resumen (se cayó): falla", any("no llego a terminar" in x for x in f))
    f, a, i = correr({"nuevas": 3, "piezas": 3}, piezas=3)
    chequear("con reels armados no hay nada que decir", not f and not a)
finally:
    S.DIAGNOSTICO, S.HISTORIAL, S.RESUMEN_PASADA, S._ultimo_lote = originales
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n--- {total - len(fallas_t)}/{total} correctos ---")
sys.exit(1 if fallas_t else 0)
