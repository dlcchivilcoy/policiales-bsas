# -*- coding: utf-8 -*-
"""La grilla intercalada de agro, el reel del clima, el banco de videos ilustrativos y los videos de las notas
(16/11/2026), sin red.

    venv\\Scripts\\python.exe tools\\test_agro_grilla.py
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
for k in ("AGRO_GRILLA", "AGRO_CLIMA_REEL", "AGRO_BANCO_VIDEO", "AGRO_AGENDA", "AGRO_POR_CORRIDA", "AGRO_INTERVALO_MIN"):
    os.environ.pop(k, None)
os.environ["AGRO_SCORE_MIN"] = "60"
os.environ.setdefault("VIDEO_CONTROL", "0")   # los videos de las pruebas son falsos (el control: test_control_video)
from agro import banco_video as _BV0  # noqa: E402
assert not _BV0.activo(), "el banco de video ilustrativo viene apagado (17/11)"
os.environ["AGRO_BANCO_VIDEO"] = "1"     # las pruebas del banco, con el banco prendido

from agro import agenda as AG  # noqa: E402
from agro import banco_video as BV  # noqa: E402
from agro import captura as CA  # noqa: E402
from agro import diseno as DIS  # noqa: E402
from agro import pasada as PA  # noqa: E402
from agro import reel_clima as RC  # noqa: E402
from agro import seleccion as SE  # noqa: E402
from tools import guardar_estado as GE  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


TZ = timezone(timedelta(hours=-3))

# --- la grilla -------------------------------------------------------------------------------------------
feed = [(f"{h:02d}:{m:02d}", t) for h, m, t in AG.agenda() if t in ("reel", "carrusel", "reel_datos")]
chequear("grilla (20/11/2026): 12 noticias, dos por corrida, intercaladas (el formato final lo decide el tema)",
         feed == [("07:00", "reel"), ("08:00", "reel_datos"), ("08:30", "reel"), ("10:00", "carrusel"),
                  ("11:30", "reel"), ("13:00", "carrusel"), ("14:30", "reel"), ("16:00", "carrusel"),
                  ("17:30", "reel"), ("18:00", "carrusel"), ("19:30", "reel"), ("21:00", "carrusel"),
                  ("22:30", "reel")])

# --- el formato según el tema (20/11/2026) ---------------------------------------------------------------
from agro import seleccion as SE  # noqa: E402


def _c(titulo, **sc):
    base = {"ai_score": 75, "subtema": "agro", "tema_doc": "", "potencial_carrusel": 5}
    base.update(sc)
    return {"id": titulo, "score": dict(base, titulo=titulo)}


chequear("formato ideal: clima con video → reel", SE.formato_ideal({"con_video": True, "tema_doc": "clima"}) == "reel")
chequear("formato ideal: precios con video → carrusel (se explica)",
         SE.formato_ideal({"con_video": True, "tema_doc": "precios", "potencial_carrusel": 8}) == "carrusel")
chequear("formato ideal: maquinaria con video → reel", SE.formato_ideal({"con_video": True, "subtema": "maquinaria"}) == "reel")
chequear("formato ideal: sin video → carrusel", SE.formato_ideal({"tema_doc": "clima"}) == "carrusel")
f, _m = SE.formato_turno([_c("lluvia", tema_doc="clima", con_video=True, ai_score=80), _c("soja", tema_doc="precios")],
                         "carrusel", [])
chequear("turno de carrusel con un temporal con video: sale reel", f == "reel")
f, _m = SE.formato_turno([_c("lluvia", tema_doc="clima", con_video=True, ai_score=80),
                          _c("soja", tema_doc="precios", ai_score=94)], "reel", ["reel", "reel"])
chequear("…pero después de dos reels seguidos, si hay un carrusel parejo (80 %), va carrusel", f == "carrusel")
f, _m = SE.formato_turno([_c("lluvia", tema_doc="clima", con_video=True, ai_score=80),
                          _c("soja", tema_doc="precios", ai_score=62)], "reel", ["reel", "reel"])
chequear("…y si el carrusel es mucho peor, sigue el reel", f == "reel")
f, _m = SE.formato_turno([_c("ley", tema_doc="reglas", ai_score=78)], "reel", [])
chequear("una ley sin video en turno de reel: carrusel", f == "carrusel")
f, _m = SE.formato_turno([_c("floja", ai_score=20)], "reel", [])
chequear("sin notas que pasen el mínimo: lo que dice la agenda", f == "reel")
os.environ["AGRO_FORMATO_TEMA"] = "0"
chequear("AGRO_FORMATO_TEMA=0: alternancia fija", SE.formato_turno([_c("lluvia", tema_doc="clima", con_video=True)],
                                                                  "carrusel", [])[0] == "carrusel")
os.environ.pop("AGRO_FORMATO_TEMA")
chequear("las historias para participar siguen igual", [f"{h:02d}:{m:02d}" for h, m, t in AG.agenda() if t == "participa"]
         == ["11:00", "14:00", "19:00", "21:30"])
os.environ["AGRO_GRILLA"] = "0"
chequear("AGRO_GRILLA=0: todos los turnos de noticias vuelven a «reel»",
         {t for *_x, t in AG.agenda() if t in ("reel", "carrusel")} == {"reel"})
os.environ.pop("AGRO_GRILLA")
sab = datetime(2026, 11, 21, 11, 30, tzinfo=TZ)
chequear("con la grilla, «Los números de la semana» no se prende solo el sábado", not AG.es_primer_carrusel_del_sabado(sab))

# --- la selección ----------------------------------------------------------------------------------------
con = {"ai_score": 70, "con_video": True, "subtema": "agro"}
sin = {"ai_score": 70, "subtema": "agro"}
chequear("en un turno de carrusel la nota con video queda para el reel",
         SE.prioridad(con, "carrusel")[1] < SE.prioridad(sin, "carrusel")[1])
chequear("en un turno de reel la nota con video va primero", SE.prioridad(con, "reel")[1] > SE.prioridad(sin, "reel")[1])
cands = [{"id": "v", "score": {"ai_score": 52, "con_video": True, "subtema": "agro", "tema": "a"}},
         {"id": "n", "score": {"ai_score": 52, "subtema": "ganaderia", "tema": "b"}}]
el, _d = SE.elegir(cands, [], formato="reel")
chequear("reel: con video entra con 52 (mínimo 60 menos 10 de tolerancia); sin video, no", [c["id"] for c in el] == ["v"])
el, _d = SE.elegir(cands, [], formato="carrusel")
chequear("carrusel: la tolerancia no corre", not el)

# --- el banco de videos ilustrativos ---------------------------------------------------------------------
chequear("tags_de: el granizo y el trigo de la noticia, después el subtema y «campo»",
         BV.tags_de("El granizo dañó el trigo en Chivilcoy: más granizo el jueves", "agro")[:2] == ["granizo", "trigo"]
         and BV.tags_de("x", "agro")[-1] == "campo")
chequear("tags_de: sin palabras, el del subtema (ganadería → ganado)", BV.tags_de("Una nota", "ganaderia")[0] == "ganado")
ahora = datetime(2026, 11, 16, 13, 0, tzinfo=TZ)
indice = [{"archivo": "bv_trigo_01.mp4", "tag": "trigo"}, {"archivo": "bv_trigo_02.mp4", "tag": "trigo"},
          {"archivo": "bv_campo_01.mp4", "tag": "campo", "autor": "<a>Juan Pérez</a>", "licencia": "CC BY-SA 4.0",
           "fuente": "https://commons.wikimedia.org/wiki/File:X.webm"}]
usados = {"bv_trigo_01.mp4": (ahora - timedelta(days=1)).isoformat()}
chequear("elegir: del tema de la noticia y sin repetir el usado ayer",
         BV.elegir("cosecha de trigo", "agro", usados, ahora, indice)["archivo"] == "bv_trigo_02.mp4")
usados["bv_trigo_02.mp4"] = (ahora - timedelta(hours=5)).isoformat()
chequear("elegir: si los del tema se usaron hace poco, pasa al tema siguiente",
         BV.elegir("cosecha de trigo", "agro", usados, ahora, indice)["archivo"] == "bv_campo_01.mp4")
chequear("elegir: banco vacío → None", BV.elegir("trigo", "agro", {}, ahora, []) is None)
os.environ["AGRO_BANCO_VIDEO"] = "0"
chequear("AGRO_BANCO_VIDEO=0 lo apaga", BV.elegir("trigo", "agro", {}, ahora, indice) is None)
os.environ["AGRO_BANCO_VIDEO"] = "1"
chequear("el crédito: autor sin HTML, licencia y Commons",
         BV.credito(indice[2]) == "Juan Pérez · CC BY-SA 4.0 · Wikimedia Commons")
g = PA.con_credito_ilustrativo({"descripcion": "Texto."}, indice[2])
chequear("el texto del posteo lleva el crédito una sola vez",
         g["descripcion"].count("Video ilustrativo") == 1 and PA.con_credito_ilustrativo(g, indice[2]) == g)
chequear("la leyenda del reel dice «Video ilustrativo»",
         DIS.texto_leyenda("ilustrativo", "Juan · CC BY 4.0").startswith("Video ilustrativo: Juan"))
u = {}
BV.anotar(u, indice[0], ahora)
chequear("anotar el uso", u == {"bv_trigo_01.mp4": ahora.isoformat(timespec="minutes")})

# --- el video de la nota con el lector de nacionales -----------------------------------------------------
tn = ('<script>Fusion.globalContent={"promo_items":{"basic":{"type":"custom_embed","subtype":"genoa","embed":'
      '{"config":{"content_type":"video","highQuality":"https://cdn.tn.com.ar/v/granizo.mp4"}}}},'
      '"content_elements":[]};Fusion.x=1;</script>')
chequear("video_de_portal: el video propio de TN", CA.video_de_portal(tn, {"titulo": "Granizo"}) ==
         "https://cdn.tn.com.ar/v/granizo.mp4")
jw = '<div data-mediaid="abcd1234"></div><script src="https://cdn.jwplayer.com/players/abcd1234-xyz.js"></script>'
llamado = []
res = CA.video_de_portal(jw, {"titulo": "Cosecha"}, elegir_jw=lambda ids, t, texto="": llamado.append(ids) or "https://j/x.mp4")
chequear("video_de_portal: los de JW pasan por el control de que sean de la nota", res in ("https://j/x.mp4", "")
         and (res == "" or llamado))
chequear("video_de_portal: sin video, vacío", CA.video_de_portal("<html></html>", {"titulo": "x"}) == "")

# --- revisar más notas sin volver a abrir las ya vistas ----------------------------------------------------
abiertas = []


def completar(rep):
    abiertas.append(rep["id"])
    return {"ok": True, "cuerpo": "x", "video": "https://v/1.mp4" if rep["id"] == "c2" else ""}


cs = [{"id": f"c{i}", "rep": {"id": f"c{i}"}, "score": {"ai_score": 70 - i, "subtema": "agro"}, "cuando": "2026-11-16T10:00"}
      for i in range(4)]
vistas = {"c0": "2026-11-16T09:00"}
n = PA.marcar_videos(cs, Path(tempfile.mkdtemp()), log=lambda m: None, completar=completar,
                     bajar=lambda rep, comp, base: Path(__file__), vistas=vistas)
chequear("marcar_videos: no abre la que ya se vio sin video y marca la que trae", "c0" not in abiertas and n == 1
         and cs[2]["score"].get("con_video"))
chequear("marcar_videos: las abiertas sin video quedan anotadas", {"c1", "c3"} <= set(vistas))

# --- la memoria en la nube ---------------------------------------------------------------------------------
junto = GE.combinar_agro({"sin_video": {"a": "1"}, "banco_usados": {"x.mp4": "2"}, "actualizado": "2"},
                         {"sin_video": {"b": "1"}, "banco_usados": {"y.mp4": "1"}, "actualizado": "1"})
chequear("guardar_estado junta las notas sin video y los videos usados",
         set(junto["sin_video"]) == {"a", "b"} and set(junto["banco_usados"]) == {"x.mp4", "y.mp4"})

# --- el reel del clima ------------------------------------------------------------------------------------
base_t = datetime(2026, 11, 16, 16, 0, tzinfo=timezone.utc)


class R:
    status_code = 200

    def __init__(self, lat):
        self.lat = float(lat)

    def json(self):
        serie = []
        for h in range(80):
            t = base_t + timedelta(hours=h)
            mm = 1.0 if 20 <= h < 30 and self.lat > -35.0 else 0.0
            serie.append({"time": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "data": {"next_1_hours": {"details": {"precipitation_amount": mm}}}})
        return {"properties": {"timeseries": serie}}


falso_get = lambda url, params: R(params["lat"])  # noqa: E731
d = RC.datos(base_t, get=falso_get, log=lambda m: None)
chequear("reel del clima: 12 tramos de 6 horas", len(d["tramos"]) == 12)
chequear("reel del clima: la lluvia cae en los tramos 4 y 5 (de las 20 a las 30 h)",
         d["tramos"][3]["chivilcoy"] > 0 and d["tramos"][0]["chivilcoy"] == 0 and round(d["chivilcoy_total"]) == 10)
texto = RC.caption(d, base_t.astimezone(TZ).date())
chequear("el texto invita a mandar el video por WhatsApp y aclara que es pronóstico",
         "2346-533450" in texto and "pronóstico" in texto and "En Chivilcoy" in texto)
mem = {"elegidas": []}
chequear("toca: desde las 13", not RC.toca(mem, datetime(2026, 11, 16, 10, 0, tzinfo=TZ))
         and RC.toca(mem, datetime(2026, 11, 16, 13, 0, tzinfo=TZ)))
mem["elegidas"].append({"formato": "clima", "cuando": "2026-11-16T13:00-03:00", "publicado": {"instagram": {"id": "1"}}})
chequear("toca: una sola vez por día", not RC.toca(mem, datetime(2026, 11, 16, 16, 0, tzinfo=TZ)))
chequear("clima_si_llueve: con 1 mm previsto no va",
         PA.clima_si_llueve(base_t, log=lambda m: None, chivilcoy=lambda a: 1.0, grilla=lambda a, log: d) is None)
chequear("clima_si_llueve: con 10 mm, los datos",
         PA.clima_si_llueve(base_t, log=lambda m: None, chivilcoy=lambda a: 10.0, grilla=lambda a, log: d) is d)
tmp = Path(tempfile.mkdtemp())
p = RC.pieza(d, datetime(2026, 11, 16, 13, 0, tzinfo=TZ), tmp)
chequear("la pieza del clima: reel 4:5 de ~20 s, solo Facebook e Instagram, sin YouTube",
         Path(p["reel"]["archivo"]).stat().st_size > 50000 and 18 <= p["reel"]["duracion"] <= 22
         and p["redes"] == ("facebook", "instagram") and p["youtube"] is False and Path(p["portada"]).is_file())
from PIL import Image  # noqa: E402
chequear("la portada del clima es 1080x1350", Image.open(p["portada"]).size == (1080, 1350))

# --- la historia para participar ------------------------------------------------------------------------
from agro import participa as PT  # noqa: E402
fondo = tmp / "f.jpg"
Image.new("RGB", (1080, 1920), (90, 120, 60)).save(fondo)
hist = PT.placa("¿Cuántos milímetros llovieron en tu campo esta semana?", str(fondo), tmp / "h.jpg",
                etiqueta="PARA PRODUCTORES", opciones=("Nada", "Poco", "Mucho"))
chequear("la historia para participar se arma con la invitación al WhatsApp", Path(hist).is_file()
         and "533450" in PT.INVITACION_VIDEO)
print(f"\n   (la portada del clima quedó en {p['portada']})")

# --- policiales del campo, innovación y variedad -----------------------------------------------------------
from agro import fuentes as FU  # noqa: E402
chequear("policial del campo: abigeato, robo en un campo, incendio rural",
         FU.es_policial_rural("Robaron 40 vacas de un campo en Alberti: investigan un caso de abigeato")
         and FU.es_policial_rural("Incendio rural: el fuego arrasó un lote de trigo en Bragado"))
chequear("no es policial del campo: un robo en la ciudad o una noticia de soja",
         not FU.es_policial_rural("Robaron una moto en Chacabuco") and not FU.es_policial_rural("Récord de soja en Chivilcoy"))
chequear("el policial del campo va antes",
         SE.prioridad({"ai_score": 62, "policial_rural": True}, "reel")[1] > SE.prioridad({"ai_score": 70}, "reel")[1])
de_hoy = [{"score": {"subtema": "agro"}}, {"score": {"subtema": "ganaderia"}}]
cands = [{"id": "tec", "score": {"ai_score": 48, "subtema": "agtech", "tema": "dron"}},
         {"id": "agr", "score": {"ai_score": 62, "subtema": "agro", "tema": "lluvia"}}]
el, _d = SE.elegir(cands, de_hoy, formato="carrusel")
chequear("innovación: si en el día no salió tecnología, desde el tercer posteo entra con 48 y va primero",
         [c["id"] for c in el][:1] == ["tec"])
el, _d = SE.elegir(cands, de_hoy[:1], formato="carrusel")
chequear("innovación: en el primer o segundo posteo del día, no", "tec" not in [c["id"] for c in el])
el, _d = SE.elegir(cands, de_hoy + [{"score": {"subtema": "maquinaria"}}], formato="carrusel")
chequear("innovación: si ya salió una de maquinaria, la de 48 no entra", "tec" not in [c["id"] for c in el])
cands = [{"id": "g", "score": {"ai_score": 70, "subtema": "ganaderia", "tema": "x"}},
         {"id": "m", "score": {"ai_score": 68, "subtema": "mercados", "tema": "y"}}]
el, _d = SE.elegir(cands, [{"score": {"subtema": "ganaderia"}}], formato="carrusel")
chequear("variedad: el mismo subtema que el último posteo va atrás", [c["id"] for c in el][0] == "m")

# --- virales del campo como reels de prueba ------------------------------------------------------------------
from agro import virales as VI  # noqa: E402
chequear("viral del campo: el video de una vaca en la ruta sí; Vaca Muerta, un temporal o un campo de juego no",
         VI.es_viral_del_campo({"titulo": "Una vaca se escapó y recorrió la ruta 5: el video"})
         and not VI.es_viral_del_campo({"titulo": "Vaca Muerta: nuevo récord de producción"})
         and not VI.es_viral_del_campo({"titulo": "Mega-granizo en Córdoba: alerta naranja"})
         and not VI.es_viral_del_campo({"titulo": "Invadió el campo de juego en el Mundial"}))
chequear("la agenda tiene los 11 reels de prueba: 3 a las 10, 3 a las 14, 3 a las 18 y 2 a las 22, fuera del feed",
         [(h, m) for h, m, t in AG.agenda() if t == "viral"] == [(10, 0), (10, 20), (10, 40), (14, 0), (14, 20), (14, 40),
                                                                (18, 0), (18, 20), (18, 40), (22, 0), (22, 20)]
         and "viral" in AG.FUERA_DEL_FEED)
os.environ["AGRO_VIRALES"] = "12:15,20:45"
chequear("AGRO_VIRALES (lista) manda sobre las tandas", VI.horas_virales() == [(12, 15), (20, 45)])
os.environ["AGRO_VIRALES"] = ""
os.environ["AGRO_PRUEBA_TANDAS"] = "09:00*2"
os.environ["AGRO_PRUEBA_PASO"] = "30"
chequear("AGRO_PRUEBA_TANDAS y AGRO_PRUEBA_PASO", VI.horas_virales() == [(9, 0), (9, 30)])
for _k in ("AGRO_VIRALES", "AGRO_PRUEBA_TANDAS", "AGRO_PRUEBA_PASO"):
    os.environ.pop(_k, None)
ahora_v = datetime(2026, 11, 16, 12, 15, tzinfo=TZ)
ts = ahora_v.timestamp()
notas_v = [{"url": "https://tn/a", "titulo": "El ternero que sigue a su dueño a todos lados", "fecha": ts - 3600,
            "categoria": "virales", "fuente": "TN"},
           {"url": "https://tn/b", "titulo": "Un tractor gigante en la ruta", "fecha": ts - 100 * 3600, "fuente": "TN"},
           {"url": "https://tn/c", "titulo": "Una cosechadora de 1950 volvió a trabajar", "fecha": ts - 7200,
            "fuente": "Infobae"},
           {"url": "https://tn/d", "titulo": "Video: vacas sueltas en la ruta. Fuente: La Razón de Chivilcoy", "fecha": ts - 60, "fuente": "X"},
           {"url": "https://tn/e", "titulo": "Elecciones en Chile", "fecha": ts - 60, "fuente": "X"}]
c_v = VI.candidatas(ahora_v, notas_v, {"virales": {"https://tn/c": "2026-11-15T12:00"}})
chequear("candidatas: lo del campo de las últimas 36 h, sin lo ya publicado",
         sorted(n["url"] for n in c_v) == ["https://tn/a", "https://tn/d"])
# 17/11: niveles (policial del campo > viral > otra del campo) y las más compartidas primero
_np = [{"url": "https://x/1", "titulo": "Récord de exportaciones de soja en Rosario", "fecha": ts - 600, "fuente": "Infobae"},
       {"url": "https://x/2", "titulo": "Cuatreros robaron 40 vacas de un campo en Chacabuco", "fecha": ts - 9000,
        "fuente": "La Capital"},
       {"url": "https://x/3", "titulo": "Cuatreros robaron 40 vacas de un campo en Chacabuco: hay detenidos",
        "fecha": ts - 8000, "fuente": "TN"},
       {"url": "https://x/4", "titulo": "Video: un ternero rescatado de un pozo se volvió viral", "fecha": ts - 300,
        "fuente": "TN", "categoria": "virales"}]
os.environ["AGRO_PRUEBA_ECONOMIA"] = "1"             # 24/11/2026: lo económico, de fábrica, ya no sale de prueba
_cp = VI.candidatas(ahora_v, _np, {})
chequear("niveles: primero el policial del campo, después el viral, después la otra nota del campo",
         [c["nivel"] for c in _cp] == [0, 1, 2])
os.environ.pop("AGRO_PRUEBA_ECONOMIA")
_cp = VI.candidatas(ahora_v, _np, {})
chequear("24/11/2026: de fábrica, las exportaciones de soja (económica) no salen como reel de prueba",
         [c["nivel"] for c in _cp] == [0, 1] and all("exportaciones" not in c["titulo"] for c in _cp))
_t = __import__("time").time()
chequear("24/11/2026: el granizo en el trigo suma más que un acto",
         VI.puntaje({"titulo": "El granizo arrasó lotes de trigo", "fecha": _t}, 1, _t)
         > VI.puntaje({"titulo": "Acto en la Sociedad Rural", "fecha": _t}, 1, _t))
chequear("lo de la sección internacionales no es del campo de acá",
         VI.nivel({"titulo": "Trump hablará sin rodeos con Xi", "categoria": "internacionales"}) is None
         and VI.nivel({"titulo": "Récord de soja en Rosario", "categoria": "economia"}) == 2)
chequear("el mismo hecho en dos portales es UNA candidata, del portal con video (TN), con la otra para buscar video",
         _cp[0]["url"] == "https://x/3" and _cp[0]["cobertura"] == 2 and _cp[0]["otras_urls"] == ["https://x/2"])
_lee = lambda u: {"video": "https://v.mp4", "titulo": "De TN"} if u == "https://x/3" else {"video": ""}  # noqa: E731
_el = VI.elegir([dict(_cp[0], url="https://x/2", fuente="La Capital", otras_urls=["https://x/3"])], tmp, leer=_lee,
                bajar=lambda u, d: Path(__file__))
chequear("sin video en la nota, lo busca en la misma noticia de otro portal (y el crédito es de ese portal)",
         _el and _el[0]["url"] == "https://x/3" and _el[0]["url_hecho"] == "https://x/2" and _el[0]["fuente"] != "La Capital")
_cv = VI.candidatas(ahora_v, _np, {"virales": {"https://x/2": "2026-11-16T10:00"}})
chequear("si el hecho ya salió (por cualquiera de sus notas), no vuelve", all(c["url"] not in ("https://x/2", "https://x/3")
                                                                             for c in _cv))
chequear("feed: el policial del campo con video va primero en un turno de reel y entra con 20 puntos menos",
         SE.prioridad({"ai_score": 60, "con_video": True, "policial_rural": True})[1]
         > SE.prioridad({"ai_score": 85, "con_video": True})[1]
         and SE.minimo_de({"con_video": True, "policial_rural": True}, 60, "reel") == 40
         and SE.minimo_de({"con_video": True}, 60, "reel") == 50)
el_v = VI.elegir(c_v[::-1], tmp, leer=lambda u: {"video": "https://v.mp4", "texto": "x"}, bajar=lambda u, d: Path(__file__))
chequear("elegir: salta la de la competencia y toma la que trae video", el_v and el_v[0]["url"] == "https://tn/a")
chequear("elegir: sin video, nada", VI.elegir(c_v, tmp, leer=lambda u: {"video": ""}, bajar=lambda u, d: None) is None)
PA.MEMORIA = tmp / "mem_sim.json"
PA.MEMORIA_REAL = tmp / "mem_real.json"
gen = lambda rep, cuerpo, otras, s: {"apta": True, "titular": "Un ternero fiel", "descripcion": "Texto viral.",  # noqa: E731
                                     "hashtags": ["#Campo"], "bajada": "b"}
arm = lambda g, img, sal, origen, credito, clip=None, tema="blanco": {"archivo": str(sal), "duracion": 30, "vista": ""}  # noqa: E731
subidos = []
r_v = VI.pasada(True, ahora_v, log=lambda m: None, carpeta=tmp / "v", ahora=ahora_v, notas=notas_v,
                leer=lambda u: {"video": "https://v.mp4", "texto": "x"}, bajar=lambda u, d: Path(__file__), generar=gen,
                armar_reel=arm, publicador=lambda mp4, cap, por, marca: subidos.append(cap) or {"instagram_prueba": {"id": "9"}},
                juez=lambda c, m, log=None: c)
mem_v = json.loads(PA.MEMORIA_REAL.read_text(encoding="utf-8"))
chequear("real: sale UN reel de prueba con el texto del guion y queda anotado (el respaldo no lo repite)",
         subidos == ["Texto viral.\n\n#Campo"] and "https://tn/a" in mem_v["virales"]
         and PA.ya_publicado(mem_v, ahora_v, "viral"))
subidos.clear()
VI.pasada(True, ahora_v.replace(hour=20, minute=45), log=lambda m: None, carpeta=tmp / "v2", ahora=ahora_v, notas=notas_v[:1],
          leer=lambda u: {"video": "https://v.mp4"}, bajar=lambda u, d: Path(__file__), generar=gen, armar_reel=arm,
          publicador=lambda *a: subidos.append(1) or {}, juez=lambda c, m, log=None: c)
chequear("el mismo viral no sale dos veces", not subidos)

# ---- 19/11: solo del campo (el juez de la IA y lo del exterior) y, sin video, el reel con la foto original ----
chequear("fuera: lo del exterior por la URL, el estadio de un club, el zoológico y el granizo de la ciudad",
         VI.nivel({"titulo": "Video: metieron un caballo a una peluquería",
                   "url": "https://www.infobae.com/colombia/2026/11/19/caballo"}) is None
         and VI.nivel({"titulo": "Club San Jorge vende su estadio y su predio", "resumen": "en el campo"}) is None
         and VI.nivel({"titulo": "Una hipopótama del zoológico se tragó un gorro: el video"}) is None
         and VI.nivel({"titulo": "Temporal con granizo sorprende al AMBA",
                       "url": "https://www.infobae.com/sociedad/2026/11/18/granizo"}) is None)
chequear("dentro: el granizo que rompe cultivos y el policial rural",
         VI.nivel({"titulo": "El granizo destruyó cultivos de trigo en Chivilcoy"}) == 2
         and VI.nivel({"titulo": "Cuatreros robaron 40 vacas de un campo en Chacabuco"}) == 0)
_cj = [{"url": "https://j/1", "titulo": "Remate de terneros en Alberti", "nivel": 2},
       {"url": "https://j/2", "titulo": "Un caballo baila en una fiesta", "nivel": 1},
       {"url": "https://j/3", "titulo": "Robo de hacienda en Bragado", "nivel": 0}]
_mj = {}
_pedidos = []
_red = lambda sys, mat: _pedidos.append(mat) or ({"notas": [{"n": 1, "campo": True}, {"n": 2, "campo": False, "motivo": "fiesta"},  # noqa: E731
                                                            {"n": 3, "campo": True}]}, "x")
chequear("juez: quedan solo las que la IA da por del campo, en el mismo orden",
         [c["url"] for c in VI.juzgar(_cj, _mj, redactar=_red, log=lambda m: None)] == ["https://j/1", "https://j/3"])
VI.juzgar(_cj, _mj, redactar=_red, log=lambda m: None)
chequear("juez: lo ya juzgado no se vuelve a preguntar", len(_pedidos) == 1)
def _sin_ia(sys, mat):
    raise RuntimeError("sin IA")
chequear("juez: si la IA no contesta, afuera los «virales» por un animal; quedan los de palabras firmes",
         [c["url"] for c in VI.juzgar(_cj, {}, redactar=_sin_ia, log=lambda m: None)] == ["https://j/1", "https://j/3"])
_cf = []
VI.elegir([{"url": "https://f/1", "titulo": "Remate en Alberti", "fuente": "Infobae"}], tmp,
          leer=lambda u: {"video": "", "imagen": "https://f/1.jpg"}, bajar=lambda u, d: None, con_foto=_cf)
chequear("elegir: sin video pero con foto, la anota para el reel con la foto", len(_cf) == 1 and _cf[0][0]["url"] == "https://f/1")
from PIL import Image as _Img  # noqa: E402
def _bf(u, d):
    _Img.new("RGB", (1200, 800), "green").save(d)
    return True
_ef = VI.elegir_foto(_cf, tmp, bajar=_bf, mirar=lambda r: False, log=lambda m: None)
chequear("elegir_foto: toma la foto original de la nota", _ef and Path(_ef[2]).is_file())
chequear("elegir_foto: la foto de agencia no sirve",
         VI.elegir_foto([({"url": "https://f/2", "titulo": "x"}, {"imagen": "https://img.afp.com/x.jpg"})], tmp,
                        bajar=_bf, mirar=lambda r: False, log=lambda m: None) is None)
subidos.clear()
_armados = []
_arm2 = lambda g, img, sal, origen, credito, clip=None, tema="blanco": _armados.append((img, origen, clip)) or {  # noqa: E731
    "archivo": str(sal), "duracion": 22, "vista": ""}
VI.pasada(True, ahora_v.replace(hour=14), log=lambda m: None, carpeta=tmp / "v3", ahora=ahora_v,
          notas=[{"url": "https://f/9", "titulo": "Remate récord de terneros en Alberti", "fecha": ts - 60, "fuente": "Infobae"}],
          leer=lambda u: {"video": "", "imagen": "https://f/9.jpg", "texto": "x"}, bajar=lambda u, d: None,
          generar=gen, armar_reel=_arm2, publicador=lambda *a: subidos.append(1) or {"instagram_prueba": {"id": "8"}},
          juez=lambda c, m, log=None: c, bajar_foto=_bf, mirar=lambda r: False)
chequear("sin video: sale el reel con la foto original (leyenda «Foto:», sin clip)",
         subidos == [1] and _armados and _armados[0][1] == "fuente" and _armados[0][2] is None and _armados[0][0])
os.environ["AGRO_PRUEBA_FOTO"] = "0"
subidos.clear()
VI.pasada(True, ahora_v.replace(hour=18), log=lambda m: None, carpeta=tmp / "v4", ahora=ahora_v,
          notas=[{"url": "https://f/10", "titulo": "Remate de vaquillonas en Bragado", "fecha": ts - 60, "fuente": "Infobae"}],
          leer=lambda u: {"video": "", "imagen": "https://f/10.jpg"}, bajar=lambda u, d: None, generar=gen,
          armar_reel=_arm2, publicador=lambda *a: subidos.append(1) or {}, juez=lambda c, m, log=None: c,
          bajar_foto=_bf, mirar=lambda r: False)
os.environ.pop("AGRO_PRUEBA_FOTO")
chequear("AGRO_PRUEBA_FOTO=0: sin video no sale nada", not subidos)

# ---- 17/11: el viral (reel de prueba de IG) sale también en el Facebook de agro ----
fb_v = []
r_fbv = VI.publicar_facebook(Path(__file__), "Texto viral", 1350, 40, "Tit", lugar=lambda: (3, 26),
                             publicar_fn=lambda p, m, u: fb_v.append((p["descripcion_tiktok"], p["formato"],
                                                                      p["video"]["duracion"])) or {"id": "7"})
chequear("viral: sale en el Facebook de agro como reel con el texto de Instagram",
         r_fbv == {"id": "7"} and fb_v == [("Texto viral", "reel", 40)])
chequear("viral: con la página en el tope no sale en Facebook",
         "omitido" in VI.publicar_facebook(Path(__file__), "x", lugar=lambda: (26, 26), publicar_fn=lambda *a: 1 / 0))
chequear("viral: si Facebook falla queda anotado", "error" in VI.publicar_facebook(
    Path(__file__), "x", lugar=lambda: None, publicar_fn=lambda *a: 1 / 0))
os.environ["AGRO_VIRALES_FB"] = "0"
chequear("AGRO_VIRALES_FB=0 lo apaga", not VI.a_facebook())
os.environ.pop("AGRO_VIRALES_FB")
chequear("viene prendido", VI.a_facebook())

# ---- 17/11: lo scrappeado sin imágenes IA; la nota con video usa un cuadro del video ----
from agro import imagen as IMG
_viejo = os.environ.pop("AGRO_IMAGEN_IA", None)
chequear("la IA de las portadas viene APAGADA (AGRO_IMAGEN_IA vacío)", not IMG.ia_activa())
os.environ["AGRO_IMAGEN_IA"] = "1"
chequear("AGRO_IMAGEN_IA=1 la vuelve a prender", IMG.ia_activa())
if _viejo is None:
    os.environ.pop("AGRO_IMAGEN_IA", None)
else:
    os.environ["AGRO_IMAGEN_IA"] = _viejo
r_sin = IMG.elegir({"id": "x", "tipo_fuente": "medio", "fuente": "TN"}, "https://foto.jpg", "una vaca",
                   tmp / "sin_ia.jpg", generar=lambda *a, **k: {"archivo": "no"}, bajar=lambda u, d: False,
                   mirar=lambda r: False, recrear_con=lambda *a, **k: {"archivo": "no"})
chequear("sin foto original usable no se genera nada con IA", r_sin.get("origen") == "ninguna" and not r_sin.get("archivo"))
vid = tmp / "prueba_cuadro.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25", "-t", "10",
                "-pix_fmt", "yuv420p", str(vid)], check=True)
cu = PA._cuadro_del_video(vid, tmp / "cuadro.jpg", mirar=lambda r: False)
chequear("la nota con video: la tapa es un cuadro del video", bool(cu) and Path(cu).is_file())
vistos = []
cu2 = PA._cuadro_del_video(vid, tmp / "cuadro2.jpg", mirar=lambda r: vistos.append(r) or len(vistos) < 3)
chequear("si el cuadro tiene zócalo prueba otro momento", bool(cu2) and len(vistos) == 3)
chequear("si todos tienen letras, ninguno", PA._cuadro_del_video(vid, tmp / "c3.jpg", mirar=lambda r: True) is None)

# 17/11: la máquina corta a los 150 min — ningún turno de la agenda puede quedar más lejos que eso
from agro import agenda as AG2  # noqa: E402
_lejos = []
for _h, _m in AG2.corridas():
    _ini, _, _ts = AG2.corrida(datetime(2026, 11, 18, _h, _m, tzinfo=PA.TZ_AR))
    _lejos += [f"{t:%H:%M}" for t, _ in _ts if (t - _ini).total_seconds() / 60 > PA.espera_max_min()]
chequear("todos los turnos de la agenda entran antes del corte de la máquina", _lejos == [])
_orig = (PA.corrida, PA._esperar, PA._un_turno, PA.cargar, PA.ya_publicado, PA._guardar_en_la_nube)
_hechos = []
try:
    _t0 = datetime(2026, 11, 17, 18, 0, tzinfo=PA.TZ_AR)
    PA.corrida = lambda ahora: (_t0, True, [(_t0, "carrusel"), (_t0.replace(hour=20, minute=45), "viral")])
    PA._esperar = lambda hasta, log=print: None
    PA._un_turno = lambda pub, tipo, *a, **k: _hechos.append(tipo) or "informe"
    PA.cargar = lambda *a, **k: {}
    PA.ya_publicado = lambda *a, **k: None
    PA._guardar_en_la_nube = lambda log=print: None
    try:
        PA.correr_corrida(log=lambda m: None, ahora=_t0)
        _error = ""
    except RuntimeError as e:
        _error = str(e)
    chequear("el turno que no llega antes del corte se saltea y se avisa (no mata la corrida)",
             _hechos == ["carrusel"] and "20:45 viral: salteado" in _error)
finally:
    PA.corrida, PA._esperar, PA._un_turno, PA.cargar, PA.ya_publicado, PA._guardar_en_la_nube = _orig

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
