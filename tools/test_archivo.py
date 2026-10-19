# -*- coding: utf-8 -*-
"""Reels de prueba del Archivo Literario y la pregunta del día (10/10/2026). Sin red, sin IA, sin motor."""
import base64
import io
import json
import os
# Las pruebas de siempre corren con las imágenes IA prendidas; la regla del 18/10/2026 (sin IA, sin foto
# real no sale) se prueba al final con ARCHIVO_IMAGEN_IA=0.
os.environ["ARCHIVO_IMAGEN_IA"] = "1"
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from archivo import elegir as E  # noqa: E402
from archivo import fuente as F  # noqa: E402
from archivo import guion as AG  # noqa: E402
from archivo import imagen as IM  # noqa: E402
from archivo import pasada as AP  # noqa: E402
from archivo import preguntas as PR  # noqa: E402
from tools import guardar_estado as GE  # noqa: E402

fallas, total = [], 0
TZ = timezone(timedelta(hours=-3))


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# ── Lectura de las efemérides ────────────────────────────────────────────────────────────────
texto = "\n".join([
    "1 de febrero de 1884: Creación de la Escuela primaria Nro. 7 “Juana Paula Manso”, de nuestra ciudad.",
    "11 y 12 de febrero de 1933: Inauguración del campo de deportes del Centro Unión Empleados de Comercio.",
    "El 12 de febrero de 1984, falleció en París el célebre escritor Julio Florencio Cortázar, que vivió aquí.",
    "Los días 11 y 12 de febrero de 1948, en la firma “Vallerga y Ferro”, se hizo la primera exposición.",
    "Febrero 1 de 1868 – Fundación de la Escuela Nro. 4 Manuel Villarino en el pueblo de Chivilcoy.",
    "El domingo 22 de octubre de 1854, se fundó el centro de población, a través de una comisión de vecinos.",
    "Los 63 años, el 15 de junio de 1961, de la creación de la Escuela de Educación Media de Moquehuá.",
    "El 2 de abril, se conmemora el 37 aniversario de la recuperación de las Islas Malvinas por las FFAA.",
    "Sucedió un 7 de febrero…",
    "Hechos del mes de Febrero",
])
hechos = F.hechos_del_texto(texto)
fechas = {(h["dia"], h["mes"], h["anio"]) for h in hechos}
chequear("lista mensual «1 de febrero de 1884: …»", (1, 2, 1884) in fechas)
chequear("«11 y 12 de febrero de 1933»: cuenta para los DOS días", {(11, 2, 1933), (12, 2, 1933)} <= fechas)
chequear("nota «El 12 de febrero de 1984, falleció…»", (12, 2, 1984) in fechas)
chequear("«Los días 11 y 12 de febrero de 1948, …»", {(11, 2, 1948), (12, 2, 1948)} <= fechas)
chequear("«Febrero 1 de 1868 – …» (mes adelante)", (1, 2, 1868) in fechas)
chequear("con día de la semana: «El domingo 22 de octubre de 1854, …»", (22, 10, 1854) in fechas)
chequear("«Los 63 años, el 15 de junio de 1961, de la creación…»", (15, 6, 1961) in fechas)
chequear("sin año («El 2 de abril, se conmemora el 37 aniversario…») queda afuera: el aniversario está viejo",
         not any(h["mes"] == 4 for h in hechos))
chequear("un subtítulo («Sucedió un 7 de febrero…») no es un hecho", not any(h["dia"] == 7 for h in hechos))

misma = [{"dia": 11, "mes": 10, "anio": 1948, "post": 1,
          "texto": "El 11 de octubre de 1948, en el local de la firma de remates “Vallerga y Ferro”, se realizó "
                   "la primera Exposición Ganadera de la Asociación Rural de Chivilcoy, presidida por Dante Catáneo."},
         {"dia": 11, "mes": 10, "anio": 1948, "post": 2,
          "texto": "El 11 de octubre de 1948, la firma “Vallerga y Ferro” fue sede de la primera Exposición "
                   "Ganadera de la Asociación Rural, con Dante Catáneo al frente."},
         {"dia": 11, "mes": 10, "anio": 2001, "post": 3,
          "texto": "El 11 de octubre de 2001, se efectuó la inauguración de la sala del Bingo Chivilcoy, en San Martín."},
         {"dia": 11, "mes": 10, "anio": 2005, "post": 4,
          "texto": "El 11 de octubre de 2005, a la edad de 79 años, resolvió poner fin a su existencia el médico."}]
juntos = F.juntar_hechos(misma)
chequear("el mismo hecho contado en dos posts se junta en uno (con los dos posts)",
         any(h["anio"] == 1948 and h["posts"] == [1, 2] for h in juntos) and len(juntos) == 3)
chequear("lo sombrío (un suicidio contado con eufemismo) queda marcado",
         [h["sombrio"] for h in juntos if h["anio"] == 2005] == [True])

# ── Elegir ───────────────────────────────────────────────────────────────────────────────────
HOY = datetime(2026, 10, 11, 13, 30, tzinfo=TZ)
ind = {"hechos": juntos, "posts": {"1": {"id": 1, "titulo": "Efemérides chivilcoyanas del mes de octubre", "foto": 9},
                                   "2": {"id": 2, "titulo": "Pinceladas de la Asociación Rural: Vallerga y Ferro, "
                                                            "Dante Catáneo", "foto": 10}},
       "personajes": [{"id": 50, "titulo": "Pascual Contursi", "foto": 5}, {"id": 51, "titulo": "Sin foto", "foto": 0}],
       "curiosidades": [{"id": 60, "titulo": "Las primeras proyecciones de cine (1907)", "foto": 6},
                        {"id": 61, "titulo": "Efemérides chivilcoyanas del mes de mayo", "foto": 7}]}
leidos = {2: {"id": 2, "titulo": "Pinceladas", "foto": 10,
              "texto": "El 11 de octubre de 1948 se hizo la primera Exposición Ganadera en Vallerga y Ferro."}}
media = lambda mid: {"url": f"https://archivo/foto{mid}.jpg", "ancho": 900, "alto": 700}  # noqa: E731
leer = lambda pid: leidos[pid]  # noqa: E731
sin_busqueda = lambda q: []  # noqa: E731
tipo, cands = E.elegir(ind, {}, HOY, buscar=sin_busqueda, media=media, leer=leer)
chequear("hoy hay efeméride: va la efeméride", tipo == "efemeride")
chequear("lo sombrío nunca es candidato", all(c["hecho"]["anio"] != 2005 for c in cands))
chequear("la foto sale del post DEDICADO, no de la lista mensual",
         cands[0]["hecho"]["anio"] == 1948 and cands[0]["dedicado"]["post"] == 2)
usados = {E.clave_hecho(c["hecho"]): "2026-01-05" for c in cands}
tipo, cands2 = E.elegir(ind, usados, HOY, buscar=sin_busqueda, media=media, leer=leer)
chequear("lo usado en los últimos 365 días no se repite: pasa a un personaje con foto",
         tipo == "personaje" and cands2 and cands2[0]["post"]["id"] == 50)
usados[E.clave_post(50)] = "2026-09-01"
tipo, cands3 = E.elegir(ind, usados, HOY, buscar=sin_busqueda, media=media, leer=leer)
chequear("sin efeméride ni personaje: una curiosidad (no una lista mensual)",
         tipo == "curiosidad" and [c["post"]["id"] for c in cands3] == [60])
viejo = {E.clave_hecho(c["hecho"]): "2025-10-01" for c in cands}
chequear("pasado el año, la efeméride vuelve", E.elegir(ind, viejo, HOY, buscar=sin_busqueda, media=media,
                                                         leer=leer)[0] == "efemeride")

h48 = next(h for h in juntos if h["anio"] == 1948)
recopilacion = "\n".join(f"El {d} de octubre de {1900 + d}, pasó algo importante en la ciudad." for d in range(1, 8))
chequear("una recopilación (muchas fechas) no es post dedicado: su foto es de otro tema",
         not E.es_dedicado(h48, recopilacion + "\nEl 11 de octubre de 1948 se hizo la exposición."))
chequear("un post que no nombra la fecha del hecho no es dedicado",
         not E.es_dedicado(h48, "La Asociación Rural y la firma Vallerga y Ferro, una historia de décadas."))
chequear("el que nombra la fecha exacta sí", E.es_dedicado(h48, leidos[2]["texto"]))

c1 = {"hecho": {"anio": 1936}, "dedicado": {"post": 1}}
c2 = {"hecho": {"anio": 1854}, "dedicado": {"post": 2}}
chequear("si la IA «elige» una candidata y escribe sobre el año de otra, manda el año del texto",
         AP.candidata_del_texto({"elegido": 1, "titular": "En 1854, Chivilcoy nacía", "descripcion": ""},
                                [c1, c2]) == 2)
chequear("sin ningún año de las candidatas en el texto: 0 (va sin foto)",
         AP.candidata_del_texto({"elegido": 1, "titular": "Chivilcoy celebra", "descripcion": ""}, [c1, c2]) == 0)

# ── Guion ────────────────────────────────────────────────────────────────────────────────────
tags = AG.hashtags("efemeride", ["#Ganadería", "campo", "#extra", "#chivilcoy"])
chequear("EXACTAMENTE 5 hashtags, los 3 fijos primero",
         tags == ["#chivilcoy", "#diariolacampaña", "#radiodelcentro", "#ganaderia", "#campo"])
chequear("si la IA no da temáticos, van los del tipo",
         AG.hashtags("pregunta", []) == ["#chivilcoy", "#diariolacampaña", "#radiodelcentro", "#preguntadeldia",
                                         "#vecinos"])
chequear("caption: descripción + los 5 hashtags", AG.caption("Hola.", tags).endswith("#ganaderia #campo")
         and AG.caption("Hola.", tags).count("#") == 5)
chequear("volanta de la efeméride con la fecha de hoy", AG.volanta("efemeride", 22, 10) == "UN DÍA COMO HOY · 22 DE OCTUBRE")

original = ("El 11 de octubre de 1948 en el local de la firma de remates de hacienda Vallerga y Ferro se llevó a cabo "
            "la primera y promisoria Exposición Ganadera de la Asociación Rural")
llamadas = []


def ia_que_calca(system, material):
    llamadas.append(system)
    if len(llamadas) == 1:
        return ({"titular": "La primera Exposición Ganadera", "bajada": "Algo.",
                 "descripcion": "En el local de la firma de remates de hacienda Vallerga y Ferro se llevó a cabo la "
                                "primera y promisoria Exposición Ganadera.", "datos_clave": [],
                 "hashtags": ["#campo", "#rural"]}, "falsa")
    return ({"titular": "En 1948, Chivilcoy tuvo su primera muestra ganadera", "bajada": "Fue en Vallerga y Ferro.",
             "descripcion": "Un día como hoy, en 1948, Chivilcoy estrenaba su muestra ganadera. ¿Lo sabías?",
             "datos_clave": ["11 de octubre de 1948", "Vallerga y Ferro"], "hashtags": ["#campo", "#rural"]}, "falsa")


g = AG.redactar_con_control(AG.SYSTEM_PROMPT, "material", [original], "efemeride", ia_que_calca)
chequear("si calca el material, se pide una segunda versión y queda la que no calca",
         len(llamadas) == 2 and "SEGUNDO PEDIDO" in llamadas[1] and g["copia"]["racha"] < 10 and not g["bloqueado"])
chequear("el prompt prohíbe nombrar la fuente (decisión del editor)", "NUNCA digas de dónde sale" in AG.SYSTEM_PROMPT)

# ── Pregunta del día ─────────────────────────────────────────────────────────────────────────
temas = PR.temario()
chequear("el banco del starter da 20 categorías de 10 temas", len(temas) == 20 and all(len(t) == 10 for t in temas.values()))
cat, tema = PR.tema_del_dia(temas, [], HOY)
hechas = [{"categoria": cat, "tema": tema, "pregunta": "¿Cuál es el mejor barrio para vivir en Chivilcoy?"}]
cat2, _ = PR.tema_del_dia(temas, hechas, HOY)
chequear("una categoría no se repite dentro de los 7 días", cat2 != cat)
mismos = [{"categoria": cat, "tema": t} for t in temas[cat][:3]]
chequear("dentro de la categoría, el primer tema que no salió",
         PR.tema_del_dia({cat: temas[cat]}, mismos, HOY) == (cat, temas[cat][3]))
chequear("una pregunta casi igual a una ya hecha se detecta",
         bool(PR.repetida("¿Cuál es el mejor barrio de Chivilcoy para vivir?", hechas)))
chequear("una distinta pasa", not PR.repetida("¿Qué comida no puede faltar en un domingo chivilcoyano?", hechas))
respuestas = iter([{"pregunta": "¿Cuál es el mejor barrio para vivir en Chivilcoy?", "bajada": "Contanos."},
                   {"pregunta": "Qué plaza de Chivilcoy es la más linda", "bajada": "Dejá tu respuesta.",
                    "hashtags": ["#plazas"], "image_prompt": "a park at sunset"}])
q = PR.generar(cat, tema, hechas, lambda s, m: (next(respuestas), "falsa"))
chequear("si sale repetida se pide otra; la nueva queda con ¿…?",
         q["apta"] and q["pregunta"] == "¿Qué plaza de Chivilcoy es la más linda?" and q["titular"] == q["pregunta"])

# ── Imagen ───────────────────────────────────────────────────────────────────────────────────
tmp = Path(tempfile.mkdtemp(prefix="test_archivo_"))
for k in ("CF_ACCOUNT_ID", "CF_API_TOKEN"):
    os.environ.pop(k, None)
pedidos = []
r = IM.imagen_pregunta("a park", "Plazas", tmp / "img.jpg", pedir=lambda *a, **k: pedidos.append(1),
                       mirar=lambda p: False)
chequear("sin la clave de Cloudflare: placa propia, sin llamar a nadie",
         r["proveedor"] == "placa" and not pedidos and Path(r["archivo"]).is_file())
os.environ.update(CF_ACCOUNT_ID="cuenta", CF_API_TOKEN="secreto123")


class Resp:
    def __init__(self, codigo, datos):
        self.status_code, self._d = codigo, datos

    def json(self):
        return self._d


from PIL import Image  # noqa: E402
buf = io.BytesIO()
Image.effect_noise((1024, 1024), 60).convert("RGB").save(buf, "JPEG", quality=95)
foto_b64 = base64.b64encode(buf.getvalue()).decode()
visto = {}


def cloudflare_ok(url, headers=None, json=None):
    visto.update(url=url, auth=headers.get("Authorization"), cuerpo=json)
    return Resp(200, {"success": True, "result": {"image": foto_b64}})


r = IM.imagen_pregunta("a park at sunset", "Plazas", tmp / "cf.jpg", pedir=cloudflare_ok, mirar=lambda p: False)
chequear("Cloudflare: guarda la imagen", r["proveedor"] == "cloudflare" and Path(r["archivo"]).is_file())
chequear("la imagen de la pregunta va HORIZONTAL 4:3 (el reel sale 4:5, como policiales)",
         Image.open(r["archivo"]).size == (1024, 768) and "horizontal" in visto["cuerpo"]["prompt"])
placa = IM.imagen_pregunta("a park", "Plazas", tmp / "pl.jpg", pedir=lambda *a, **k: Resp(401, {}),
                           mirar=lambda p: False)
chequear("la placa propia de respaldo también es horizontal",
         placa["proveedor"] == "placa" and Image.open(placa["archivo"]).size == IM.PLACA_HORIZONTAL)
chequear("Cloudflare: modelo FLUX schnell, la cuenta en la URL y el token en el encabezado",
         visto["url"].endswith("/accounts/cuenta/ai/run/@cf/black-forest-labs/flux-1-schnell")
         and visto["auth"] == "Bearer secreto123" and "wordless" in visto["cuerpo"]["prompt"]
         and "no text" not in visto["cuerpo"]["prompt"].lower())
miradas = iter([True, False])
r = IM.imagen_pregunta("a park", "Plazas", tmp / "cf3.jpg", pedir=cloudflare_ok, mirar=lambda p: next(miradas))
chequear("si Gemini ve letras en la imagen, se pide otra (y la segunda sirve)",
         r["proveedor"] == "cloudflare" and r["intentos"] == 2)
r = IM.imagen_pregunta("a park", "Plazas", tmp / "cf4.jpg", pedir=cloudflare_ok, mirar=lambda p: True)
chequear("si las dos traen letras: placa propia", r["proveedor"] == "placa" and "letras" in r["motivo"])
r = IM.imagen_pregunta("a park", "Plazas", tmp / "cf5.jpg", pedir=cloudflare_ok, mirar=lambda p: None)
chequear("si no se pudo mirar (Gemini caído), la imagen sirve igual", r["proveedor"] == "cloudflare")
r = IM.imagen_pregunta("x", "Plazas", tmp / "cf2.jpg", mirar=lambda p: False,
                       pedir=lambda *a, **k: Resp(401, {"errors": [{"message": "Authentication error"}]}))
chequear("Cloudflare con la clave mal: placa propia y el motivo, sin mostrar el token",
         r["proveedor"] == "placa" and "401" in r["motivo"] and "secreto123" not in r["motivo"])
chico = tmp / "chico.jpg"
Image.new("RGB", (425, 576), (200, 200, 200)).save(chico)
r = IM.para_el_motor(chico, mirar=lambda p: True)
chequear("una foto que el motor toma por afiche: se agranda y lleva grano (sin recortar)",
         r["ajustada"] and Image.open(r["archivo"]).size == (996, 1350))
chequear("una foto normal queda igual", IM.para_el_motor(chico, mirar=lambda p: False) == {"archivo": str(chico),
                                                                                         "ajustada": False})

# ── Pasada: una por tipo por día ─────────────────────────────────────────────────────────────
AP.MEMORIA = tmp / "estado" / "archivo.json"
from reels import publicador as PUB  # noqa: E402
PUB._lugar_en_instagram = lambda: (40, 35, 100)


def armar_falso(tipo, ahora, mem, carpeta, redactar=None, **kw):
    mp4 = tmp / f"{tipo}.mp4"
    mp4.write_bytes(b"0" * 20000)
    return {"tipo": "efemeride" if tipo == "efemeride" else "pregunta",
            "guion": {"titular": "En 1948, la primera exposición", "pregunta": "¿Qué plaza es la más linda?",
                      "categoria": "Espacios públicos", "tema": "las plazas", "copia": {"racha": 3}},
            "caption": "Texto.\n\n#chivilcoy #diariolacampaña #radiodelcentro #a #b", "imagen": {"proveedor": "archivo"},
            "video": {"archivo": str(mp4), "placa": None}, "usados": ["h:1948-10-11:abc", "p:2"],
            "fuente": {}}


_armar_real = AP.armar
AP.armar = armar_falso
inf = AP.pasada("efemeride", False, HOY)
chequear("simulada: no publica ni escribe memoria", inf["estado"] == "simulado" and not AP.MEMORIA.exists())
publicados = []
inf = AP.pasada("efemeride", True, HOY, publicador=lambda *a: publicados.append(a) or {"id": "M1", "prueba": {}})
mem = AP.cargar()
chequear("publicada: anota el reel y lo usado", inf["estado"] == "ok" and mem["usados"].get("p:2") == "2026-10-11"
         and mem["publicaciones"]["2026-10-11:efemeride"]["id"] == "M1")
inf = AP.pasada("efemeride", True, HOY + timedelta(hours=3), publicador=lambda *a: publicados.append(a))
chequear("el respaldo del mismo día no repite", inf["estado"] == "ya_salio" and len(publicados) == 1)


def falla(*a):
    raise PUB.FalloRed("Instagram: el contenedor quedó en ERROR")


for i in range(3):
    inf = AP.pasada("pregunta", True, HOY + timedelta(hours=7, minutes=i), publicador=falla)
chequear("si falla, se anota el intento y la pregunta NO queda como hecha",
         inf["estado"] == "error" and AP.cargar()["publicaciones"]["2026-10-11:pregunta"]["intentos"] == 3
         and not AP.cargar()["preguntas"])
inf = AP.pasada("pregunta", True, HOY + timedelta(hours=8), publicador=lambda *a: {"id": "X"})
chequear("después de 3 fallas en el día, se rinde hasta mañana", inf["estado"] == "rendido")


def sin_confirmar(*a):
    raise PUB.SinConfirmar("Instagram: 500 y no se pudo leer si salió")


inf = AP.pasada("pregunta", True, HOY + timedelta(days=1, hours=7), publicador=sin_confirmar)
chequear("«sin confirmar» cuenta como hecho (publicar dos veces es peor que perder uno)",
         inf["estado"] == "sin_confirmar" and AP.ya_salio(AP.cargar(), HOY + timedelta(days=1), "pregunta")
         and AP.cargar()["preguntas"][-1]["pregunta"] == "¿Qué plaza es la más linda?")
PUB._lugar_en_instagram = lambda: (0, 75, 100)
inf = AP.pasada("efemeride", True, HOY + timedelta(days=2), publicador=lambda *a: {"id": "Z"})
chequear("sin lugar en Instagram (cupo de 100 con la reserva del bot): no publica", inf["estado"] == "sin_lugar")

# ── Memoria entre trabajos ───────────────────────────────────────────────────────────────────
viejo = {"usados": {"p:1": "2026-10-01"}, "preguntas": [],
         "publicaciones": {"2026-10-11:efemeride": {"estado": "error", "cuando": "2026-10-11T13:31"}}}
nuevo = {"usados": {"p:1": "2026-10-01", "p:2": "2026-10-11"},
         "preguntas": [{"dia": "2026-10-11", "pregunta": "¿A?"}],
         "publicaciones": {"2026-10-11:efemeride": {"estado": "ok", "cuando": "2026-10-11T13:35"}}}
c = GE.combinar_archivo(viejo, nuevo)
chequear("la copia vieja que guarda policiales no pisa lo publicado por el Archivo",
         c["publicaciones"]["2026-10-11:efemeride"]["estado"] == "ok" and "p:2" in c["usados"]
         and len(c["preguntas"]) == 1)
chequear("archivo.json tiene combinador en guardar_estado", GE.COMBINAR.get("archivo.json") is GE.combinar_archivo)

# --- Sin imágenes hechas con IA (18/10/2026) -----------------------------------------------------------------
os.environ["ARCHIVO_IMAGEN_IA"] = "0"
_inf = AP.pasada("pregunta", False)
chequear("sin IA: la pregunta del día (su imagen era de FLUX) queda apagada, sin error",
         _inf["estado"] == "apagada")
_mem0 = {"usados": {}, "publicaciones": {}, "preguntas": []}
_dummy = Path(tempfile.mkdtemp())
_orig_guion = AP.guion_archivo
AP.guion_archivo = lambda *a, **k: {"tipo": "efemeride", "guion": {"titular": "t", "bajada": "b", "descripcion": "d",
                                                                     "hashtags": []},
                                     "volanta": "Un día como hoy", "foto_url": "https://x/f.jpg", "usados": []}
try:
    _armar_real("efemeride", datetime(2026, 10, 18, 13, 30, tzinfo=AP.TZ_AR), _mem0, _dummy,
                bajar=lambda url, destino: False)
    chequear("sin IA: la efeméride cuya foto no baja NO sale (antes iba la placa propia)", False)
except AP.SinFotoReal:
    chequear("sin IA: la efeméride cuya foto no baja NO sale (antes iba la placa propia)", True)
AP.guion_archivo = _orig_guion
os.environ["ARCHIVO_IMAGEN_IA"] = "1"

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
