# -*- coding: utf-8 -*-
"""Reels de datos de la zona (agro/reel_zona.py, 20/11/2026): temas, rotación, ventana de 11 a 12:30, colab y la
lluvia que no se repite a la tarde. Sin red: el armado del video se reemplaza por uno falso."""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agro import publicar as PUB  # noqa: E402
from agro import reel_clima as RC  # noqa: E402
from agro import reel_zona as RZ  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


TZ = timezone(timedelta(hours=-3))
AF = RZ.datos_argenfields()
HOY = datetime(2026, 11, 20, 11, 10, tzinfo=TZ)

# ── Los datos y los temas ──
chequear("la copia de ArgenFields trae Chivilcoy y sus vecinos", len(AF.get("partidos") or {}) >= 10)
disp = RZ.temas_disponibles(AF, HOY.date())
chequear(f"hay temas con datos ({len(disp)})", {"trigo_zona", "soja_zona", "tierra", "gemelas", "sequias"} <= set(disp))
t = disp["trigo_zona"]
chequear("el trigo: Chivilcoy primero de la zona → el gancho pregunta quién tiene el mejor",
         t["gancho"].startswith("¿Quién tiene el mejor trigo"))
barras = next(d for k, d in t["diapositivas"] if k == "barras")
chequear("el ranking va de mayor a menor", [v for _, v in barras["filas"]] == sorted([v for _, v in barras["filas"]],
                                                                                    reverse=True))
chequear("cada tema arranca con la info (mapa, gráfico o lista) con el gancho, sin portada de video",
         all(x["diapositivas"][0][0] in ("mapa", "barras", "serie", "lista") and x["diapositivas"][0][1].get("titulo")
             == x["gancho"] for x in disp.values()))
chequear("…y termina con el cierre", all(x["diapositivas"][-1][0] == "cierre" for x in disp.values()))
chequear("los rankings de la zona arrancan con el mapa", disp["trigo_zona"]["diapositivas"][0][0] == "mapa"
         and disp["tierra"]["diapositivas"][0][0] == "mapa")
viejo = dict(AF, traido="2026-08-01")
chequear("El Niño no va con datos de hace más de 45 días", RZ.tema_nino(viejo, HOY.date()) is None)
chequear("los números con coma y sin «,0»", RZ._coma(27.5) == "27,5" and RZ._coma(50.0) == "50"
         and RZ._coma(41037, 0) == "41.037")

# ── La rotación ──
mem = {"reels": []}
chequear("con lluvia fuerte prevista, el tema es la lluvia", RZ.elegir_tema(mem, disp, HOY.date(), 25.0) == "lluvia")
primero = RZ.elegir_tema(mem, disp, HOY.date(), 1.0)
chequear(f"con poca lluvia va otro tema ({primero})", primero not in (None, "lluvia"))
vistos = []
for k in range(len(RZ.ORDEN) + 1):
    dia = HOY.date() + timedelta(days=k)
    c = RZ.elegir_tema(mem, disp, dia, 0)
    vistos.append(c)
    mem["reels"].append({"dia": dia.isoformat(), "tema": c, "publicado": {"instagram": {"id": "1"}}})
chequear("en 10 días no se repite ningún tema", len(set(v for v in vistos[:10] if v)) == len([v for v in vistos[:10] if v]))

# ── La corrida (con el video falso) ──
armados, publicados = [], []


def armar_falso(tema, salida, videos=None):
    armados.append(tema["tema"])
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_bytes(b"x")
    jpg = Path(salida).with_suffix(".jpg")
    jpg.write_bytes(b"x")
    return {"archivo": str(salida), "duracion": 20.0, "peso_kb": 1, "vista": str(jpg), "alto": 1350}


def publicador_falso(p, log=print):
    publicados.append(p)
    return {"instagram": {"id": "ig1", "colab": "si"}, "facebook": {"id": "fb1"}, "facebook_diario": {"id": "fb2"},
            "colab": {"estado": "aceptada"}}


RZ.armar = armar_falso
with tempfile.TemporaryDirectory() as d:
    ruta = Path(d) / "agro_zona.json"
    RZ.SALIDA = Path(d) / "salida"
    sin_lluvia = lambda ahora: 0.0
    kw = dict(ruta_mem=ruta, af=AF, lluvia_fn=sin_lluvia, publicador=publicador_falso,
              videos_fn=lambda *a, **k: {}, log=lambda *a: None)
    inf = RZ.corrida(True, ahora=datetime(2026, 11, 20, 9, 0, tzinfo=TZ), **kw)
    chequear("a las 9 no publica (fuera de la ventana)", inf["estado"] == "fuera_de_hora" and not publicados)
    inf = RZ.corrida(True, ahora=datetime(2026, 11, 21, 0, 45, tzinfo=TZ), **kw)
    chequear("el respaldo que llega a las 00:45 no publica", inf["estado"] == "fuera_de_hora" and not publicados)
    inf = RZ.corrida(True, ahora=HOY, **kw)
    chequear("a las 11:10 publica un reel", inf["estado"] == "ok" and len(publicados) == 1)
    p = publicados[0]
    chequear("la pieza pide la colab con el diario y va solo a Facebook e Instagram",
             p.get("colab_diario") is True and tuple(p["redes"]) == ("facebook", "instagram") and p["youtube"] is False)
    chequear("el texto cita la fuente y no lleva link de nota",
             "ArgenFields" in p["guion"]["descripcion"] and "/n/" not in p["guion"]["descripcion"])
    inf2 = RZ.corrida(True, ahora=HOY + timedelta(minutes=15), **kw)
    chequear("el respaldo de las 11:25 no repite", inf2["estado"] == "ya_salio" and len(publicados) == 1)
    mem_g = json.loads(ruta.read_text(encoding="utf-8"))
    chequear("queda anotado con las redes donde salió",
             mem_g["reels"][-1]["redes"] == ["instagram", "facebook", "facebook_diario"])
    os.environ["AGRO_ZONA"] = "0"
    chequear("AGRO_ZONA=0 apaga", RZ.corrida(True, ahora=HOY + timedelta(days=1), **kw)["estado"] == "apagado")
    os.environ.pop("AGRO_ZONA")

    # La lluvia de la mañana: la tarde no repite el reel del clima.
    ruta2 = Path(d) / "agro_zona_lluvia.json"
    RZ.guardar({"reels": [{"dia": "2026-11-20", "tema": "lluvia", "publicado": {"instagram": {"id": "1"}}}]}, ruta2)
    chequear("lluvia_hoy ve el reel de lluvia de la mañana", RZ.lluvia_hoy("2026-11-20", ruta2)
             and not RZ.lluvia_hoy("2026-11-21", ruta2))
    original = RZ.MEMORIA
    RZ.MEMORIA = ruta2
    chequear("…y el reel del clima de la tarde da el día por hecho",
             RC.ya_hoy({"elegidas": []}, datetime(2026, 11, 20, 16, 0, tzinfo=TZ)))
    chequear("…pero no el día siguiente", not RC.ya_hoy({"elegidas": []}, datetime(2026, 11, 21, 16, 0, tzinfo=TZ)))
    RZ.MEMORIA = original

# ── Instagram con colab (sin red) ──
from reels import publicador as PB  # noqa: E402

llamadas = []


def contenedor(uid, tok, params):
    llamadas.append(dict(params))
    if "collaborators" in params and rechazar[0]:
        raise PB.FalloRed("collaborators no permitido")
    return "c1"


rechazar = [False]
viejos = (PB.subir_a_release, PB._contenedor_listo, PB._publicar_contenedor, PB.texto_del_posteo)
PB.subir_a_release = lambda mp4, nombre: "https://x/v.mp4"
PB._contenedor_listo = contenedor
PB._publicar_contenedor = lambda uid, tok, cid, caption: "m1"
PB.texto_del_posteo = lambda pp, red: "texto"
r = PUB._reel_instagram({}, Path("v.mp4"), "v.mp4", "https://x/p.jpg", colab="diarioyradio")
chequear("Instagram: el contenedor lleva a @diarioyradio de colaborador",
         r["colab"] == "si" and json.loads(llamadas[0]["collaborators"]) == ["diarioyradio"])
rechazar[0] = True
llamadas.clear()
r = PUB._reel_instagram({}, Path("v.mp4"), "v.mp4", "https://x/p.jpg", colab="diarioyradio")
chequear("si Instagram rechaza la colab, sale igual solo en agro",
         r["id"] == "m1" and r["colab"] == "no" and "collaborators" not in llamadas[-1])
llamadas.clear()
r = PUB._reel_instagram({}, Path("v.mp4"), "v.mp4", "https://x/p.jpg")
chequear("sin colab (las noticias de agro), como siempre", "colab" not in r and "collaborators" not in llamadas[0])
PB.subir_a_release, PB._contenedor_listo, PB._publicar_contenedor, PB.texto_del_posteo = viejos

# ── Las placas se dibujan (sin video) ──
nino = RZ.tema_nino(dict(AF, traido="2026-11-20"), HOY.date())
if nino:
    b = next(d for k, d in nino["diapositivas"] if k == "barras")
    im = RZ.placa_barras(b, 3.0, RZ.FUENTE_CORTA)
    chequear("las barras con negativos (cebada en años de El Niño) se dibujan", im.size == (1080, 1350))
s = next(d for k, d in disp["trigo_historia"]["diapositivas"] if k == "serie")
chequear("la serie campaña por campaña se dibuja", RZ.placa_serie(s, 5.0, RZ.FUENTE_CORTA).size == (1080, 1350))

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
