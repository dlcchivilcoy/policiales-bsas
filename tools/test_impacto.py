# -*- coding: utf-8 -*-
"""El estilo «impacto» de los carruseles y portadas de agro (agro/impacto.py, 20/11/2026)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image  # noqa: E402

from agro import carrusel as CAR  # noqa: E402
from agro import impacto as I  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


chequear("la fuente Anton está en el repo", I.ANTON.is_file())
chequear("cifra corta: «60%»", I.cifra_corta("el 60% de la soja") == "60%")
chequear("cifra corta: «+50.000 ha»", I.cifra_corta("+50.000 hectáreas") == "+50.000 ha")
chequear("sin número no hay cifra", I.cifra_corta("muchas hectáreas") == "")
chequear("destacado: lo de después de los dos puntos",
         I.destacado_de("Pasturas polifíticas: cómo combinarlas") == "cómo combinarlas")
chequear("destacado: el que propone la IA si está en el título",
         I.destacado_de("Bunge y GDM crean Enerseed", "crean Enerseed") == "crean Enerseed")
chequear("destacado: el de la IA que no está en el título no va",
         I.destacado_de("Bunge y GDM crean Enerseed", "otra cosa") != "otra cosa")
m = I._marcas("LA SOJA RINDIÓ MÁS QUE EL PROMEDIO".split(), "más que el promedio".upper())
chequear("las palabras marcadas en verde son las del destacado", m == [False, False, False, True, True, True, True])


def redactar_falso(system, material, max_tokens=0):
    return ({"gancho": "La soja rindió más que el promedio bonaerense",
             "diapositivas": [{"titulo": "Qué pasó", "texto": "La soja de la zona rindió 27,5 quintales por hectárea."},
                              {"titulo": "Los números", "texto": "Es más que el promedio de la provincia.",
                               "dato": "27,5 qq/ha", "dato_rotulo": "rinde promedio"},
                              {"titulo": "Qué viene", "texto": "La siembra de la nueva campaña ya arrancó en el partido."}],
             "pregunta": "¿Cuánto te rindió la soja?", "destacado": "más que el promedio",
             "cifra_tapa": "99%", "cifra_rotulo": "inventado", "etiqueta": "para guardar"}, "falsa")


g = {"titular": "La soja rindió más que el promedio", "bajada": "", "nota_web": "La soja de la zona rindió 27,5 qq/ha.",
     "datos_clave": ["27,5 qq/ha"], "volanta": "Rindes"}
c = CAR.contenido(g, {"titulo": "", "descripcion": ""}, "La soja rindió 27,5 quintales.", redactar=redactar_falso)
chequear("una cifra de tapa que no está en el material NO va", "cifra_tapa" not in c)
d = I.datos_tapa(g, c)
chequear("…y la tapa usa la cifra de una diapositiva que sí está", d["cifra"] == "27,5 qq" or d["cifra"].startswith("27,5"))
chequear("la etiqueta en mayúsculas", d["etiqueta"] == "PARA GUARDAR")

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    foto = t / "f.jpg"
    Image.new("RGB", (1600, 900), (90, 120, 60)).save(foto)
    archivos = CAR.armar(g, c, foto, t, "x", "grafito", "Foto: INTA")
    chequear(f"el carrusel sale con tapa, {len(c['diapositivas'])} láminas y cierre",
             len(archivos) == len(c["diapositivas"]) + 2 and all(Path(a).is_file() for a in archivos))
    chequear("todas en 4:5", all(Image.open(a).size == (1080, 1350) for a in archivos))
    tapa = Image.open(archivos[0]).convert("RGB")
    chequear("la tapa tiene la foto arriba y el fondo grafito abajo",
             tapa.getpixel((540, 200))[1] > 90 and sum(tapa.getpixel((20, 1330))) < 120)
    from agro import portada as POR
    p = POR.armar({"titular": "Trigo: récord en Chivilcoy", "volanta": "Cosecha"}, foto, t / "p.jpg", credito="INTA")
    chequear("la portada del reel también sale con el estilo nuevo", Image.open(p).size == (1080, 1350))
    os.environ["AGRO_CARRUSEL_ESTILO"] = "bot"
    chequear("AGRO_CARRUSEL_ESTILO=bot vuelve al diseño anterior", not I.activo())
    os.environ.pop("AGRO_CARRUSEL_ESTILO")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
