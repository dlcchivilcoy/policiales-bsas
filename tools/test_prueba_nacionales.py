# -*- coding: utf-8 -*-
"""Las corridas propias de reels de prueba (nacionales/prueba.py), sin red.

    venv\\Scripts\\python.exe tools\\test_prueba_nacionales.py
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("VIDEO_CONTROL", "0")

from nacionales import pasada as PA  # noqa: E402
from nacionales import prueba as PR  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


TZ = PR.TZ_AR
DIA = datetime(2026, 11, 16, tzinfo=TZ).date()


def a(hhmm):
    return datetime.combine(DIA, datetime.strptime(hhmm, "%H:%M").time(), TZ)


hh = lambda ts: [t.strftime("%H:%M") for t in ts]  # noqa: E731
chequear("virales: arranca 17:35 → 18:00, 18:25, 18:50, 19:15 y 19:40",
         hh(PR.turnos("virales", a("17:35"), 5)) == ["18:00", "18:25", "18:50", "19:15", "19:40"])
chequear("policiales: arranca 19:45 → 20:00, 20:25, 20:50, 21:15 y 21:40",
         hh(PR.turnos("policiales", a("19:45"), 5)) == ["20:00", "20:25", "20:50", "21:15", "21:40"])
chequear("si arranca tarde (18:30), se corren los turnos con 10 min como mínimo y sin pasar las 19:55",
         hh(PR.turnos("virales", a("18:30"), 5)) == ["18:30", "18:40", "18:50", "19:15", "19:40"])
chequear("si ya salieron 3 hoy, quedan 2 turnos", len(PR.turnos("virales", a("17:35"), 2)) == 2)
chequear("pasada la franja, no hay turnos", PR.turnos("virales", a("20:05"), 5) == [])

# --- las candidatas de policiales -----------------------------------------------------------------------
ts = a("19:45").timestamp()


def nota(url, titulo, fuente, horas=1, cuerpo=""):
    return {"url": url, "titulo": titulo, "fuente": fuente, "medio": fuente, "categoria": "policiales",
            "resumen": "", "cuerpo": cuerpo or titulo, "fecha": ts - horas * 3600, "imagen": "x.jpg"}


notas = [
    nota("https://www.infobae.com/sociedad/policiales/a", "Detuvieron a un ladrón tras una persecución en Palermo", "Infobae"),
    nota("https://tn.com.ar/policiales/b", "Asaltaron una joyería en Junín y se llevaron todo", "TN"),
    nota("https://www.clarin.com/policiales/c", "Persecución y choque en La Matanza: dos detenidos", "Clarín"),
    nota("https://www.infobae.com/sociedad/policiales/d", "Un caso de hace tres días en Córdoba", "Infobae", horas=40),
]
cands, _ = PR.candidatas_policiales(a("19:45"), notas)
chequear("policiales: primero el de la zona (Junín), después el de la provincia (La Matanza)",
         [c["url"][-1] for c in cands][:2] == ["b", "c"])
chequear("policiales: lo de hace más de 18 horas queda afuera", all(not c["url"].endswith("/d") for c in cands))
chequear("las fuentes de policiales son TN, Infobae, Clarín y La Nación",
         {f[1] for f in PR.FUENTES_POLICIALES} == {"TN", "Infobae", "Clarín", "La Nación"})

# --- la corrida, con el reloj, las páginas y la publicación de mentira ------------------------------------
reloj = [a("19:45")]
mem = {"piezas": {}, "descartadas": {}}
PA.cargar = lambda: mem
PA.guardar = lambda m: None
PA._lugar_ig = lambda: None
armadas = []


def armar_falso(c, carpeta, redactar=None, leer=None, solo_web=False):
    armadas.append(c["url"])
    return {"nota": dict(c), "url_original": c["url"], "formato": "reel", "video_original": "v.mp4",
            "video": {"archivo": "v.mp4", "portada": ""}, "foto": {},
            "guion": {"apta": True, "titular": c["titulo"], "volanta": "", "bajada": "", "seccion": "Policiales",
                      "viral": 6, "descripcion": "", "hashtags": []}}


PA.armar = armar_falso
PA.caption_instagram = lambda g: g["titular"]
publicados = []


def dormir(seg):
    reloj[0] += timedelta(seconds=seg)


def publicar_falso(pieza, caption):
    publicados.append((reloj[0].strftime("%H:%M"), pieza["url_original"]))
    return {"estado": "ok", "id": str(len(publicados)), "cuando": reloj[0].isoformat()}


TITULOS = ("Robaron un camión con mercadería en Avellaneda", "Cayó una banda narco que operaba en Rosario",
           "Incendio intencional en una fábrica de Pilar", "Estafa telefónica a jubilados en Mar del Plata",
           "Choque fatal sobre la ruta 2 cerca de Dolores", "Secuestraron armas en un allanamiento en Quilmes",
           "Motochorros asaltaron a un repartidor en Morón", "Detienen a un prófugo buscado por Interpol en Tigre")
muchas = [nota(f"https://tn.com.ar/policiales/n{i}", t, "TN") for i, t in enumerate(TITULOS)]
con_video = {n["url"] for n in muchas if not n["url"].endswith(("n1", "n4"))}


class Guardia:
    def __init__(self):
        self.tomada = False

    def tomar(self, *a):
        if self.tomada:
            return False
        self.tomada = True
        return True


g = Guardia()
inf = PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x" if u in con_video else ""},
                 ahora_fn=lambda: reloj[0], dormir=dormir, publicar_fn=publicar_falso, guardia=g)
chequear("salen 5 policiales, a las 20:00, 20:25, 20:50, 21:15 y 21:40",
         [h for h, _ in publicados] == ["20:00", "20:25", "20:50", "21:15", "21:40"])
chequear("las notas sin video no gastan la IA", not any(u.endswith(("n1", "n4")) for u in armadas))
chequear("quedan en la memoria como «prueba: policiales» y no se repiten",
         sum(1 for p in mem["piezas"].values() if p.get("prueba") == "policiales") == 5
         and len({u for _, u in publicados}) == 5)
reloj[0] = a("19:50")
publicados.clear()
inf2 = PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x"},
                  ahora_fn=lambda: reloj[0], dormir=dormir, publicar_fn=publicar_falso, guardia=Guardia())
chequear("si ya salieron las 5 del día, la segunda corrida no hace nada", inf2["estado"] == "nada" and not publicados)
mem["piezas"].clear()
inf3 = PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x"},
                  ahora_fn=lambda: reloj[0], dormir=dormir, publicar_fn=publicar_falso, guardia=g)
chequear("la guardia: la corrida de respaldo no publica si ya corrió la de cron-job.org", inf3["estado"] == "ya_corrio")

# Sin video en ninguna: no sale nada y lo avisa.
mem["piezas"].clear()
publicados.clear()
reloj[0] = a("17:35")
inf4 = PR.corrida("virales", True, notas=[], leer_pagina=lambda u: {},
                  ahora_fn=lambda: reloj[0], dormir=dormir, publicar_fn=publicar_falso, guardia=Guardia())
chequear("sin candidatas: no publica y queda «sin_piezas»", inf4["estado"] == "sin_piezas" and not publicados)

# Un tope de Instagram corta la corrida.
import reels.publicador as PUB  # noqa: E402
PUB._es_tope_de_prueba = lambda e: "tope" in str(e)
mem["piezas"].clear()
publicados.clear()
reloj[0] = a("19:45")
llamadas = []
inf5 = PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x"},
                  ahora_fn=lambda: reloj[0], dormir=dormir,
                  publicar_fn=lambda p, c: llamadas.append(1) or {"estado": "fallo", "error": "tope"},
                  guardia=Guardia())
chequear("si Instagram dice que llegó al tope de reels de prueba, la corrida para", len(llamadas) == 1)
print("\n" + PR.resumen(inf)[:400])

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
