# -*- coding: utf-8 -*-
"""Los reels de los informes de FADA (agro/fada.py), sin red: lectura, control de números, ficha y la corrida.

    python tools/test_fada.py
"""
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from agro import fada as F  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- números -------------------------------------------------------------------------------------------
chequear("números: $58, 23%, 4,5 y 1.234", F.numeros("$58 de cada $100, 23% y 4,5 millones, 1.234 t") ==
         {58.0, 100.0, 23.0, 4.5, 1234.0})
fuente = "9 de cada 10 cargas viajan por ruta. Transportar granos es 36% más caro que en EEUU y 10% más que en Brasil."
chequear("un número que está pasa", F.numeros_ausentes(["El 36% más caro"], fuente) == [])
chequear("un número inventado no pasa", len(F.numeros_ausentes(["Es 45% más caro"], fuente)) == 1)

# --- lectura de páginas --------------------------------------------------------------------------------
PAGINA = ('<html><title>Logística agroindustrial – Fundación FADA</title><body>Sumate Informe Logística '
          'agroindustrial 25 noviembre, 2026 Compartir en redes sociales Descargar: '
          '<a href="https://drive.google.com/file/d/ABC_123/view?usp=drive_link">Informe</a> Links #FADAenlos medios '
          '</body></html>')
LISTADO = ('<a href="https://fundacionfada.org/informes/feed/">x</a>'
           '<a href="https://fundacionfada.org/informes/logistica-agroindustrial/">a</a>'
           '<a href="https://fundacionfada.org/informes/logistica-agroindustrial/">a</a>'
           '<a href="https://fundacionfada.org/informes/monitor-ganadero-2026/">b</a>')
chequear("listado: sin repetidos ni el feed", [u.split("/")[-2] for u in F.listar(lambda u: LISTADO)] ==
         ["logistica-agroindustrial", "monitor-ganadero-2026"])
g = F.leer("https://fundacionfada.org/informes/logistica-agroindustrial/", lambda u: PAGINA)
chequear("informe: título, fecha y PDF de Drive", g["titulo"] == "Logística agroindustrial"
         and g["fecha"] == date(2026, 11, 25) and g["pdf"].endswith("export=download&id=ABC_123"))
chequear("PDF de Dropbox con su clave y dl=1",
         F.url_pdf('href="https://www.dropbox.com/scl/fi/xyz/Informe.pdf?rlkey=k1&amp;st=s&amp;dl=0"')
         == "https://www.dropbox.com/scl/fi/xyz/Informe.pdf?rlkey=k1&st=s&dl=1")

# --- la ficha ----------------------------------------------------------------------------------------------
g.update(material=fuente + " Combinar camión y ferrocarril puede bajar 30% el costo del flete. El 70% de la red vial "
                           "está en estado regular o malo. +75% de la Red Vial son caminos de tierra.", slug="logistica")
BUENA = {"apta": True, "titulo": "Cómo viajan los granos", "volanta": "LOGÍSTICA · FADA",
         "pregunta": "¿Cuántas de cada 10 cargas viajan por ruta?", "gancho": "¿Cuántas cargas viajan por ruta?",
         "respuesta": {"numero": 9, "dec": 0, "unidad": "", "texto": "de cada 10 cargas viajan por ruta"},
         "revelacion": "Nueve de cada 10 cargas viajan por ruta.",
         "bloques": [{"volanta": "EEUU", "numero": 36, "unidad": "%", "texto": "más caro que en Estados Unidos",
                      "narracion": "Transportar granos acá es 36% más caro que en Estados Unidos."},
                     {"volanta": "TREN", "numero": 30, "unidad": "%", "texto": "menos de flete con camión y tren",
                      "narracion": "Según FADA, combinar camión y tren puede bajar 30% el flete."},
                     {"volanta": "RUTAS", "numero": 70, "unidad": "%", "texto": "de la red vial, regular o mala",
                      "narracion": "El 70% de la red vial está regular o mala."},
                     {"volanta": "INVENTO", "numero": 45, "unidad": "%", "texto": "dato inventado",
                      "narracion": "Un 45% que no está."},
                     {"volanta": "BRASIL", "titulo": "Más caro que", "filas": [["EEUU", "36%"], ["Brasil", "10%"]],
                      "narracion": "Contra Brasil, 10% más caro."}],
         "cierre": "¿Por dónde sacás la cosecha?", "caption": ["9 de cada 10 cargas viajan por ruta.", "Inventado 99%."],
         "hashtags": ["#Agro", "#Logistica"], "video": "cosecha"}
logs = []
f = F.ficha(g, redactar=lambda s, m: BUENA, log=logs.append)
chequear("ficha: sale con los bloques verificados", not f.get("error") and len(f["bloques"]) == 4)
chequear("el bloque con un número inventado queda afuera", all(b["volanta"] != "INVENTO" for b in f["bloques"])
         and any("INVENTO" in x for x in logs))
chequear("el párrafo del posteo con un número inventado se saca", f["caption"] == ["9 de cada 10 cargas viajan por ruta."])
chequear("la correcta está entre las opciones", f["opciones"][f["correcta"]] == "9")
chequear("marca de agro, sin colaboración y cinco hashtags", f["placa"] == "agro" and f["cuentas"] == "@diarioyradioagro"
         and len(f["hashtags"]) == 5 and f["video_tag"] == "cosecha")
mala = dict(BUENA, respuesta={"numero": 8, "dec": 0, "unidad": "", "texto": "x"}, revelacion="Ocho de cada 10.")
chequear("una respuesta que no está en el informe lo descarta", "error" in F.ficha(g, redactar=lambda s, m: mala))

# --- la corrida (26/11/2026: solo los domingos, hasta 2 informes de la semana) -----------------------------
tmp = Path(tempfile.mkdtemp())
mem = tmp / "fada.json"
publicados, dormido = [], []
informes = [dict(g, slug="logistica", fecha=date(2026, 11, 25), url="https://fundacionfada.org/informes/logistica/"),
            dict(g, slug="ganadero", fecha=date(2026, 11, 27), url="https://fundacionfada.org/informes/ganadero/"),
            dict(g, slug="tributario", fecha=date(2026, 11, 24), url="https://fundacionfada.org/informes/tributario/"),
            dict(g, slug="viejo", fecha=date(2026, 10, 1), url="https://fundacionfada.org/informes/viejo/")]
leer_fn = lambda u: next(x for x in informes if x["url"] == u)  # noqa: E731
kw = dict(ruta_mem=mem, log=lambda *a: None, listar_fn=lambda: [x["url"] for x in informes], leer_fn=leer_fn,
          material_fn=lambda x: x["material"], redactar=lambda s, m: BUENA, dormir=dormido.append,
          armar_video=lambda f_, c, log=print: (c.mkdir(parents=True, exist_ok=True) or
                                                {"archivo": "r.mp4", "portada": "p.jpg", "duracion": 120.0,
                                                 "ancho": 1080, "alto": 1920}),
          publicador=lambda p, log=print: publicados.append(p) or {"instagram": {"id": "1"}, "facebook": {"id": "2"}})
domingo = datetime(2026, 11, 29, 16, 45, tzinfo=F.TZ_AR)
chequear("un jueves no se fija", F.corrida(True, datetime(2026, 11, 26, 16, 45, tzinfo=F.TZ_AR), **kw)["estado"]
         == "otro_dia" and not publicados)
chequear("el domingo fuera de la franja no hace nada",
         F.corrida(True, domingo.replace(hour=10), **kw)["estado"] == "fuera_de_hora")
inf = F.corrida(True, domingo, **kw)
chequear("el domingo publica los dos más nuevos de la semana, en agro y sin colab",
         inf["estado"] == "ok" and [p["id"].split("_")[1].split("-")[0] for p in publicados] == ["ganadero", "logistica"]
         and all(p["colab_diario"] is False for p in publicados))
chequear("entre los dos espera su margen", len(dormido) == 1 and dormido[0] > 0)
m = F.cargar(mem)
chequear("el viejo queda anotado como viejo", m["informes"]["viejo"]["estado"] == "viejo")
chequear("el tercero no sale ese día (tope de 2)", "tributario" not in m["informes"])
chequear("el respaldo del mismo domingo no repite", F.corrida(True, domingo.replace(minute=59), **kw)["estado"]
         == "ya_salio_hoy" and len(publicados) == 2)
os.environ["FADA_DIAS_SEMANA"] = "3"
chequear("FADA_DIAS_SEMANA cambia el día", F.dias_semana() == {3})
os.environ.pop("FADA_DIAS_SEMANA")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
