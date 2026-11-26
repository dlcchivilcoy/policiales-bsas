# -*- coding: utf-8 -*-
"""Los reels del finde (finde/), sin red: temas, verificación, selección, subtítulos y la corrida de publicación.

    python tools/test_finde.py
"""
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from finde import corrida as C  # noqa: E402
from finde import temas as T  # noqa: E402
from finde import video as V  # noqa: E402
from finde import voz as VZ  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- opciones -------------------------------------------------------------------------------------------
op, ok = T.opciones_de(68.4, 1, pos=2)
chequear("opciones: tres, la correcta donde se pidió", len(op) == 3 and ok == 2 and op[2] == "68,4 %")
op, ok = T.opciones_de(95.0, 1, pos=2)
chequear("opciones: nunca pasan de 100 %", all(float(o.split()[0].replace(",", ".")) <= 100 for o in op)
         and op[ok] == "95,0 %")
op, ok = T.opciones_de(4.0, 0, pos=0, unidad="", paso=4, tope=40)
chequear("opciones: nunca bajo cero", all(int(o) >= 0 for o in op) and op[ok] == "4")
chequear("la respuesta no cae siempre en el mismo lugar",
         len({T.posicion(k) for k in list(T.TEMAS_SABADO) + list(T.TEMAS_DOMINGO)}) == 3)
chequear("campañas leídas por la voz", T.leer_campana("2022/23") == "2022-2023")

# --- fichas con datos de mentira ------------------------------------------------------------------------
NOMBRES = {"chivilcoy": "Chivilcoy", "bragado": "Bragado", "alberti": "Alberti", "suipacha": "Suipacha",
           "mercedes": "Mercedes", "navarro": "Navarro"}


def censo_falso():
    c = {}
    for i, (s, n) in enumerate(NOMBRES.items()):
        h = 10000 + 1000 * i
        c[s] = {"nombre": n, "hogares": h, "gas_red": h * (0.68 - 0.04 * i), "garrafa": h * 0.26, "gas_tubo": 10,
                "cocina_electricidad": 10, "lena": 1, "cocina_otro": 1, "hogares_t": h, "propia": h * 0.65,
                "escritura": h * 0.5, "alquilada": h * (0.22 + 0.01 * i), "cedida": 1, "prestada": 1,
                "otra_tenencia": 1, "pob2010": 60000, "pob2022": 66000 + 100 * i, "var_pob": 10 + i,
                "mayores65": {1980: 12.0, 2001: 14.0, 2022: 15.0 + i}, "hogares_cloacas": h, "cloaca": h * 0.75,
                "hogares_agua": h, "agua_red": h * 0.8, "hogares_internet": h, "internet": h * 0.81}
    c["_fuentes"] = {}
    return c


fs = T.disponibles("sabado", censo=censo_falso(), log=lambda *a: None)
chequear("sábado: los siete temas del censo salen con datos completos", set(fs) == set(T.TEMAS_SABADO))
g = fs["gas_red"]
chequear("gas: la correcta es el dato de Chivilcoy", g["opciones"][g["correcta"]] == "68,0 %")
chequear("gas: dice «partido» y el año", "partido" in g["narracion"]["revelacion"] and "2022" in
         g["narracion"]["revelacion"])
chequear("gas: cinco hashtags y fuente con dirección", len(g["hashtags"]) == 5 and g["fuentes"][0]["url"].startswith(
    "https://www.indec.gob.ar/"))
mala = dict(g, respuesta=dict(g["respuesta"], numero=70.0))
chequear("verificar: la respuesta tiene que coincidir con el mapa", any("no coincide" in p for p in T.verificar(mala)))
mala = dict(g, opciones=["1 %", "1 %", "2 %"])
chequear("verificar: tres opciones distintas", any("opciones" in p for p in T.verificar(mala)))
mala = dict(g, narracion=dict(g["narracion"], revelacion="En Chivilcoy el 68 %", mapa="Primero."))
chequear("verificar: el censo es del partido", any("partido" in p for p in T.verificar(mala)))

AF = {"traido": "2026-11-20", "fuente": "ArgenFields", "partidos": {
    s: {"partido": n, "productividad": 62 - 3 * i, "puesto": 18, "de": 121, "productividad_provincia": 45,
        "clase_1_3": 63 - i, "franco_limosa": 98.6, "limitantes": [["Exceso de agua o anegamiento", 64 - i]],
        "rindes": {"soja": {"promedio": 27.5, "peor": ["2022/23", 15.8 - i], "mejor": ["2014/15", 41.5],
                            "serie": [[f"20{10 + k}/{11 + k}", 30.0 + k, 1] for k in range(12)]}},
        "emergencias": {"total": 5 + i, "lista": [{"desde": "01/2009", "hasta": "12/2009", "motivo": "sequía"},
                                                  {"desde": "01/2017", "hasta": "12/2017", "motivo": "inundación"},
                                                  {"desde": "01/2023", "hasta": "06/2023", "motivo": "sequía"}]}}
    for i, (s, n) in enumerate(NOMBRES.items())}}
fd = T.disponibles("domingo", af=AF, log=lambda *a: None)
chequear("domingo: los cinco temas del campo", set(fd) == set(T.TEMAS_DOMINGO))
chequear("soja: se dice «estimado», no cosecha medida", "estimad" in fd["soja_peor"]["narracion"]["revelacion"])
chequear("anegamiento: aclara que es un riesgo, no una inundación ocurrida",
         "no una inundación" in fd["anegamiento"]["narracion"]["contexto"])
chequear("tierra: el índice se atribuye al INTA", "INTA" in fd["tierra"]["narracion"]["revelacion"])

# --- selección: ocho semanas sin repetir -----------------------------------------------------------------
hoy = date(2026, 11, 28)
chequear("sin historial: el primero del orden", T.elegir("sabado", fs, [], hoy) == T.ORDEN_SABADO[0])
hist = [{"clave": "gas_red", "fecha": "2026-11-21", "estado": "publicado"}]
chequear("lo que salió hace una semana no se repite", T.elegir("sabado", fs, hist, hoy) == T.ORDEN_SABADO[1])
hist = [{"clave": k, "fecha": f"2026-11-{10 + i:02d}", "estado": "publicado"} for i, k in enumerate(T.ORDEN_SABADO)]
chequear("si todos salieron hace poco, el más viejo", T.elegir("sabado", fs, hist, hoy) == T.ORDEN_SABADO[0])

# --- subtítulos -------------------------------------------------------------------------------------------
pal = VZ.alinear([(0, .3, "Ya"), (.3, .6, "llegó"), (.6, .9, "el"), (.9, 1.2, "gas"), (1.2, 1.5, "a"),
                  (1.5, 1.8, "tu"), (1.8, 2.1, "cuadra"), (2.4, 2.7, "Contanos")],
                 "¿Ya llegó el gas a tu cuadra? Contanos.")
chequear("la voz recupera la puntuación del guion", pal[6][2] == "cuadra?" and pal[0][2] == "Ya")
b = V.bloques(pal, 10.0)
chequear("subtítulos: cortan en el signo y van en tiempo del reel",
         [" ".join(p for _, _, p in x[2]) for x in b][-1] == "Contanos." and b[0][0] == 10.0)
chequear("SRT con el formato de siempre", V.srt(b).startswith("1\n00:00:10,000 --> "))
chequear("sin voz, tiempos estimados", len(VZ.estimar("uno dos tres.")) == 3)

# --- la corrida de publicación ---------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp())
mem = tmp / "finde.json"
sab = datetime(2026, 11, 28, 18, 40, tzinfo=C.TZ_AR)
armados, publicados, dormido = [], [], []


def armar_falso(dia, fecha, m, tema, log):
    armados.append((dia, fecha))
    f = fs["gas_red"] if dia == "sabado" else fd["tierra"]
    return {"ficha": f, "clave": f["clave"], "carpeta": tmp / "x", "reel": {
        "archivo": "r.mp4", "portada": "p.jpg", "duracion": 40.0, "ancho": 1080, "alto": 1920}, "archivos": []}


def publicador(p, log=print):
    publicados.append(p)
    return {"instagram": {"id": "IG1", "colab": "si"}, "facebook": {"id": "FB1"}}


inf = C.publicar_hoy(datetime(2026, 11, 28, 15, 0, tzinfo=C.TZ_AR), ruta_mem=mem, armar_fn=armar_falso,
                     publicador=publicador, dormir=dormido.append, log=lambda *a: None)
chequear("fuera de la franja no publica", inf["estado"] == "fuera_de_hora" and not publicados)
inf = C.publicar_hoy(datetime(2026, 11, 26, 19, 0, tzinfo=C.TZ_AR), ruta_mem=mem, armar_fn=armar_falso,
                     publicador=publicador, dormir=dormido.append, log=lambda *a: None)
chequear("un jueves no publica", inf["estado"] == "no_es_finde")
inf = C.publicar_hoy(sab, ruta_mem=mem, armar_fn=armar_falso, publicador=publicador, dormir=dormido.append,
                     log=lambda *a: None)
chequear("sábado 18:40: publica el de la ciudad en colab", inf["estado"] == "ok" and publicados[0]["colab_diario"]
         and publicados[0]["reel"]["alto"] == 1920)
chequear("…y anota el resultado", C.cargar(mem)["historial"][-1]["estado"] == "publicado")
inf = C.publicar_hoy(sab.replace(minute=55), ruta_mem=mem, armar_fn=armar_falso, publicador=publicador,
                     dormir=dormido.append, log=lambda *a: None)
chequear("el respaldo de las 18:55 no lo repite", inf["estado"] == "ya_salio" and len(publicados) == 1)
chequear("el texto lleva fuente con año y los hashtags", "Dato de 2022" in publicados[0]["guion"]["descripcion"]
         and "#ChivilcoyEnDatos" in publicados[0]["guion"]["descripcion"])
chequear("próximo finde desde un jueves", C.proximo_finde(date(2026, 11, 26)) ==
         {"sabado": date(2026, 11, 28), "domingo": date(2026, 11, 29)})
os.environ["FINDE_COLAB"] = "0"
chequear("FINDE_COLAB=0 sale sin colaboración", not C.pieza(armar_falso("sabado", hoy, {}, "", print), sab)
         ["colab_diario"])
os.environ.pop("FINDE_COLAB")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
