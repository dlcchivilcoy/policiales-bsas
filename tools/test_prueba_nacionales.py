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
# 17/11: 11 por día; los policiales completan lo que no encontraron los virales
_dia = DIA.isoformat()
_mem_v = lambda n: {"piezas": {f"v{i}": {"prueba": "virales", "dia": _dia, "ig_prueba": {"estado": "ok"}}  # noqa: E731
                               for i in range(n)}}
chequear("11 por día: con 5 virales, los policiales hacen 6", PR.cuantos_de("policiales", _mem_v(5), _dia) == 6)
chequear("si los virales encontraron 3, los policiales intentan 8",
         PR.cuantos_de("policiales", _mem_v(3), _dia) == 8)
chequear("24/11/2026: los virales bajan a 3 (rinden 382 de mediana contra 1.329 de los policiales)",
         PR.cuantos_de("virales", _mem_v(0), _dia) == 3)
import time as _time  # noqa: E402
_ts = _time.time()
_p = lambda t: PR.puntaje_policial({"titulo": t, "resumen": "", "fecha": _ts}, 1, _ts)[0]  # noqa: E731
chequear("gancho: el hecho filmado por una cámara de seguridad suma",
         _p("Una cámara de seguridad registró el robo a un kiosco") > _p("Robaron un kiosco"))
chequear("gancho: una modalidad llamativa (falsos operarios) suma",
         _p("Detuvieron a falsos operarios que robaban cables") > _p("Detuvieron a operarios que robaban cables"))
chequear("el trámite judicial resta", _p("Inician los alegatos por el crimen") < _p("Investigan el crimen"))
import os as _os  # noqa: E402
_os.environ["NAC_PRUEBA_GANCHOS"] = "0"
chequear("NAC_PRUEBA_GANCHOS=0 los apaga", _p("Inician los alegatos por el crimen") == _p("Investigan el crimen"))
_os.environ.pop("NAC_PRUEBA_GANCHOS")
_v, _ = PR.candidatas_virales(a("17:35"), notas=[])
chequear("sin internacionales de fábrica (lista vacía no rompe)", _v == [])
chequear("el sexto policial entra en la franja (22:05)",
         hh(PR.turnos("policiales", a("19:45"), 6, 6)) == ["20:00", "20:25", "20:50", "21:15", "21:40", "22:05"])
os.environ["NAC_PRUEBA_TOTAL"] = "0"
chequear("NAC_PRUEBA_TOTAL=0: 5 y 5 como antes", PR.cuantos_de("policiales", _mem_v(5), _dia) == 5)
os.environ.pop("NAC_PRUEBA_TOTAL")

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


os.environ["NAC_PRUEBA_TOTAL"] = "0"       # este bloque prueba la corrida con los 5 de fábrica
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
os.environ.pop("NAC_PRUEBA_TOTAL")
mem["piezas"].clear()
inf3 = PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x"},
                  ahora_fn=lambda: reloj[0], dormir=dormir, publicar_fn=publicar_falso, guardia=g)
chequear("la guardia: la corrida de respaldo no publica si ya corrió la de cron-job.org", inf3["estado"] == "ya_corrio")

# 20/11/2026: el respaldo de GitHub llegó a las 00:46; no tiene que tomar la guardia del día ni esperar 19 h.
mem["piezas"].clear()
publicados.clear()
reloj[0] = a("00:46")
g_temprano, durmio = Guardia(), []
inf_t = PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x"},
                   ahora_fn=lambda: reloj[0], dormir=lambda s: durmio.append(s), publicar_fn=publicar_falso,
                   guardia=g_temprano)
chequear("la corrida que llega a las 00:46 termina «temprano», sin esperar ni publicar",
         inf_t["estado"] == "temprano" and not durmio and not publicados)
chequear("…y deja libre la guardia del día para la de la noche", not g_temprano.tomada)
reloj[0] = a("19:45")
chequear("la de las 19:45 (15 min antes) sí corre",
         PR.corrida("policiales", True, notas=muchas, leer_pagina=lambda u: {"video": "x"},
                    ahora_fn=lambda: reloj[0], dormir=dormir, publicar_fn=publicar_falso,
                    guardia=g_temprano)["estado"] not in ("temprano", "ya_corrio") and g_temprano.tomada)

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

# ---- 17/11: el reel de prueba también sale en Facebook ----
import tempfile as _tf  # noqa: E402
from pathlib import Path  # noqa: E402
_mp4 = Path(_tf.mkdtemp()) / "r.mp4"
_mp4.write_bytes(b"x" * 10)
_pz = {"video": {"archivo": str(_mp4), "duracion": 30}, "formato": "carrusel", "guion": {"titular": "T"}}
_vistos = []
r_fb = PR.publicar_facebook(_pz, "Texto IG", lugar=lambda: (5, 25),
                            publicar_fn=lambda p, m, u: _vistos.append((p["descripcion_tiktok"], p["formato"], m)) or {"id": "9"})
chequear("Facebook: sale como reel con el texto de Instagram", r_fb.get("estado") == "ok" and r_fb.get("id") == "9"
         and _vistos == [("Texto IG", "reel", _mp4)])
r_cupo = PR.publicar_facebook(_pz, "x", lugar=lambda: (25, 25), publicar_fn=lambda *a: _vistos.append(1))
chequear("Facebook: con la página en el tope de 24 h no publica", r_cupo["estado"] == "cupo" and len(_vistos) == 1)
r_err = PR.publicar_facebook(_pz, "x", lugar=lambda: None, publicar_fn=lambda *a: 1 / 0)
chequear("Facebook: si falla queda anotado y no rompe", r_err["estado"] == "fallo")
os.environ["NAC_PRUEBA_FB"] = "0"
chequear("NAC_PRUEBA_FB=0 lo apaga", not PR.prueba_a_facebook())
os.environ.pop("NAC_PRUEBA_FB")
chequear("viene prendido", PR.prueba_a_facebook())

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
