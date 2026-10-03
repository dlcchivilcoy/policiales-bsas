# -*- coding: utf-8 -*-
"""Sin logos de medio en el reel: la imagen con marca NO se usa (no se borra ni se tapa la
marca) y va otra. Sin red: Gemini, las descargas y el motor se reemplazan.

Nació el 03/10/2026, a pedido del editor («sacá los logos en las fotos/videos que
encuentres»). Probado ese día con Gemini de verdad sobre 28 fotos de 28 medios: marcó 4
(el logo «BN» de Bragado Noticias, «Bi24» de Bragado Informa, la «C» de Cañuelas al día y
un aviso de Oeste Digital) y dejó limpias las fotos con el fondo oficial de la Policía.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from PIL import Image

from reels import flujo as F, ia, ilustrativa as IL, marcas as MAR, publicador as PUB
from reels import reel_bot as R

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


tmp = Path(tempfile.mkdtemp(prefix="marcas_"))


def foto(nombre, tam=(800, 600)):
    ruta = tmp / nombre
    Image.new("RGB", tam, (90, 90, 90)).save(ruta, "JPEG")
    return ruta


# --- 1. marcas.revisar: lo que contesta Gemini -----------------------------------------
llamadas = []
original_gemini = ia.redactar_gemini


def gemini(respuesta):
    def _g(system, material, imagenes=()):
        llamadas.append(len(imagenes))
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta, "gemini:falso"
    return _g


try:
    f = foto("una.jpg")
    ia.redactar_gemini = gemini('{"marca": true, "que": "logo BN arriba a la derecha"}')
    r = MAR.revisar([f])
    chequear("revisar: marca → True, con el qué", r["marca"] is True and "BN" in r["que"])
    chequear("revisar: a Gemini le llega la imagen", llamadas[-1] == 1)
    ia.redactar_gemini = gemini('{"marca": false, "que": ""}')
    chequear("revisar: limpia → False", MAR.revisar([f])["marca"] is False)
    ia.redactar_gemini = gemini('{"marca": "true", "que": "x"}')
    chequear("revisar: «true» como texto también es marca", MAR.revisar([f])["marca"] is True)
    ia.redactar_gemini = gemini('{"que": "no sé"}')
    chequear("revisar: sin el campo → None (no se sabe)", MAR.revisar([f])["marca"] is None)
    ia.redactar_gemini = gemini(RuntimeError("se agotaron las claves"))
    r = MAR.revisar([f])
    chequear("revisar: Gemini falla → None, con el motivo", r["marca"] is None and "claves" in r["que"])
    llamadas.clear()
    ia.redactar_gemini = gemini('{"marca": true}')
    chequear("revisar: dos cuadros de un video van en UNA consulta",
             MAR.revisar([f, foto("otra.jpg")])["marca"] is True and llamadas == [2])
    llamadas.clear()
    rota = tmp / "rota.jpg"
    rota.write_bytes(b"no es una imagen")
    chequear("revisar: imagen que no abre → None sin gastar una consulta",
             MAR.revisar([rota])["marca"] is None and llamadas == [])
    os.environ["MARCAS"] = "0"
    chequear("revisar: MARCAS=0 lo apaga sin consultar", MAR.revisar([f])["marca"] is None and llamadas == [])
    os.environ.pop("MARCAS")
finally:
    ia.redactar_gemini = original_gemini

# --- 2. La imagen ilustrativa -------------------------------------------------------------
a = IL.generar("accidente_vial", tmp / "a.jpg", semilla="https://medio.test/1")
b = IL.generar("accidente_vial", tmp / "b.jpg", semilla="https://medio.test/1")
c = IL.generar("accidente_vial", tmp / "c.jpg", semilla="https://medio.test/2")
chequear("ilustrativa: JPEG 1600x1200 (forma de foto de nota)", Image.open(a).size == (1600, 1200))
chequear("ilustrativa: misma nota, misma imagen", a.read_bytes() == b.read_bytes())
chequear("ilustrativa: otra nota, otra imagen", a.read_bytes() != c.read_bytes())
chequear("ilustrativa: el grupo sale del tipo de hecho",
         (IL.grupo("incendio"), IL.grupo("alerta_meteorologica"), IL.grupo("robo")) == ("fuego", "clima", "policial"))
banco_original = IL.BANCO
try:
    IL.BANCO = tmp / "banco"
    (IL.BANCO / "fuego").mkdir(parents=True)
    propia = foto("propia.jpg", (1000, 700))
    (IL.BANCO / "fuego" / "galpon.jpg").write_bytes(propia.read_bytes())
    d = IL.generar("incendio", tmp / "d.jpg", semilla="x")
    chequear("ilustrativa: si el editor cargó fotos propias en reels/banco/<grupo>, va una de esas",
             d.read_bytes() == propia.read_bytes())
finally:
    IL.BANCO = banco_original

# --- 3. Qué imagen va al reel ------------------------------------------------------------
veredictos = {}          # nombre de archivo → True / False / None
pedidos = []
reemplazos = {"_foto_usable": None}
original = {"revisar": MAR.revisar, "_foto_usable": F._foto_usable, "cuadro": R.cuadro_de_video}


def revisar_falso(rutas):
    pedidos.append([Path(r).name for r in rutas])
    v = [veredictos.get(Path(r).name.split("_alt")[0] if "_alt" not in Path(r).name else Path(r).name) for r in rutas]
    marca = True if True in v else (None if None in v and False not in v else False)
    return {"marca": marca, "que": "logo de prueba" if marca else ""}


def foto_usable_falsa(nota, destino):
    """La «descarga» copia el archivo de prueba que dice la nota."""
    origen = nota.get("imagen")
    if not origen:
        return None, "", "sin imagen"
    Path(destino).write_bytes(Path(origen).read_bytes())
    veredictos[Path(destino).name] = veredictos.get(Path(origen).name)
    return Path(destino), str(origen), ""


try:
    MAR.revisar, F._foto_usable = revisar_falso, foto_usable_falsa
    con_logo, limpia, otra_con_logo = foto("con_logo.jpg"), foto("limpia.jpg"), foto("otra_logo.jpg")
    veredictos.update({"con_logo.jpg": True, "limpia.jpg": False, "otra_logo.jpg": True})
    nota = {"url": "https://medio.test/robo", "titulo": "Robaron una moto en Junín", "tipo": "robo"}

    veredictos["propia.jpg"] = False
    f2, u, ilus, av = F._imagen_sin_marca(nota, limpia, "u-limpia", tmp, 1)
    chequear("foto limpia: va esa, sin avisos", f2 == limpia and u == "u-limpia" and not ilus and av == [])

    alt = dict(nota, alternativas=[{"imagen": str(otra_con_logo), "url": "https://otro.test/1", "medio": "Otro"},
                                   {"imagen": str(limpia), "url": "https://tercero.test/1", "medio": "Tercero"}])
    f2, u, ilus, av = F._imagen_sin_marca(alt, con_logo, "u-logo", tmp, 2)
    chequear("foto con logo: va la de OTRO medio que no tiene marca (la segunda; la primera también tenía)",
             u == str(limpia) and not ilus and any("Tercero" in x for x in av))

    sin_salida = dict(nota, alternativas=[{"imagen": str(otra_con_logo), "url": "https://otro.test/1", "medio": "Otro"}])
    f2, u, ilus, av = F._imagen_sin_marca(sin_salida, con_logo, "u-logo", tmp, 3)
    chequear("foto con logo y ninguna limpia: imagen ilustrativa, sin URL (la web usa el cuadro del reel)",
             ilus and u == "" and Path(f2).is_file() and Image.open(f2).size == (1600, 1200))

    veredictos["nose.jpg"] = None
    nose = foto("nose.jpg")
    f2, u, ilus, av = F._imagen_sin_marca(nota, nose, "u-nose", tmp, 4)
    chequear("no se pudo revisar: va la foto igual, con aviso (el control no deja la pasada sin reels)",
             f2 == nose and not ilus and any("No se pudo revisar" in x for x in av))

    f2, u, ilus, av = F._imagen_sin_marca(nota, None, "", tmp, 5)
    chequear("sin foto (el video se cayó por la marca) y sin alternativas: ilustrativa", ilus and Path(f2).is_file())

    pedidos.clear()
    os.environ["MARCAS"] = "0"
    f2, u, ilus, av = F._imagen_sin_marca(nota, con_logo, "u-logo", tmp, 6)
    chequear("MARCAS=0: va la foto del medio sin revisar", f2 == con_logo and pedidos == [])
    os.environ.pop("MARCAS")

    # El video: dos cuadros en una sola consulta.
    R.cuadro_de_video = lambda clip, salida, segundo=0.5: Path(foto(Path(salida).name).__str__())
    veredictos.update({"reel_marca_7_0.jpg": True, "reel_marca_7_1.jpg": False})
    pedidos.clear()
    clip, aviso, con_marca = F._clip_sin_marca(tmp / "clip.mp4", tmp, 7)
    chequear("video con logo en un cuadro: no se usa", clip is None and con_marca and "marca" in aviso
             and pedidos == [["reel_marca_7_0.jpg", "reel_marca_7_1.jpg"]])
    veredictos.update({"reel_marca_8_0.jpg": False, "reel_marca_8_1.jpg": False})
    clip, aviso, con_marca = F._clip_sin_marca(tmp / "clip.mp4", tmp, 8)
    chequear("video limpio: se usa", clip == tmp / "clip.mp4" and not con_marca and aviso == "")
finally:
    MAR.revisar, F._foto_usable, R.cuadro_de_video = original["revisar"], original["_foto_usable"], original["cuadro"]

# --- 4. Las otras versiones del mismo hecho ----------------------------------------------
n1 = {"url": "https://a.test/1", "titulo": "Choque fatal en la Ruta 188 entre un camión y una camioneta",
      "imagen": "https://a.test/1.jpg", "medio": "A"}
n2 = {"url": "https://b.test/9", "titulo": "Choque fatal entre un camión y una camioneta en la Ruta 188",
      "imagen": "https://b.test/9.jpg", "medio": "B"}
n3 = {"url": "https://c.test/5", "titulo": "Detuvieron a dos jóvenes por el robo de una moto en Junín",
      "imagen": "https://c.test/5.jpg", "medio": "C"}
n4 = dict(n2, url="https://d.test/2", medio="D", imagen="https://a.test/1.jpg")
salida = F._con_alternativas([n1, n3], [n1, n2, n3, n4])
chequear("alternativas: la misma noticia en otro medio queda anotada",
         [x["medio"] for x in salida[0].get("alternativas", [])] == ["B"])
chequear("alternativas: la misma FOTO en otro medio no cuenta (tendría el mismo logo)",
         all(x["imagen"] != n1["imagen"] for x in salida[0]["alternativas"]))
chequear("alternativas: un hecho distinto no tiene", "alternativas" not in salida[1])

# --- 5. procesar: la web nunca lleva una imagen sin revisar --------------------------------
reemplazos = {
    "_bajar_video": lambda url, destino: None,
    "material": lambda nota: nota,
}
guardados = {k: getattr(F, k) for k in reemplazos}
armar, generar = F.R.armar, F.G.generar
try:
    for k, v in reemplazos.items():
        setattr(F, k, v)
    MAR.revisar, F._foto_usable = revisar_falso, foto_usable_falsa
    F.R.armar = lambda g, salida, **k: {"duracion": 13, "peso_kb": 120, "tramos": ["nota"], "alto": 1350}
    F.G.generar = lambda nota, **k: {"volanta": "Robo en Junín", "titular": "Robaron una moto en pleno centro de Junín",
                                     "bajada": "La moto estaba estacionada frente a un comercio de la avenida.",
                                     "zocalo": "Robo", "pie": "x", "via": "gemini:falso", "tipo": "robo",
                                     "descripcion_final": "Texto", "fuera_de_temario": "", "copia": {}}
    carpeta = tmp / "lote"
    carpeta.mkdir()
    p = F.procesar({"url": "https://medio.test/a", "titulo": "Robo", "localidad_medio": "Junín",
                    "imagen": str(con_logo)}, carpeta, True, 1)
    chequear("procesar: foto con logo → ilustrativa, marcada, y la web sin URL de imagen",
             p["apto_para_publicar"] and p["imagen_ilustrativa"] is True and p["imagen_url"] == ""
             and any("ilustrativa" in x for x in p["avisos"]))
    p = F.procesar({"url": "https://medio.test/b", "titulo": "Robo", "localidad_medio": "Junín",
                    "imagen": str(limpia)}, carpeta, True, 2)
    chequear("procesar: foto limpia → esa misma, también para la web",
             p["imagen_ilustrativa"] is False and p["imagen_url"] == str(limpia))
finally:
    for k, v in guardados.items():
        setattr(F, k, v)
    F.R.armar, F.G.generar = armar, generar
    MAR.revisar, F._foto_usable = original["revisar"], original["_foto_usable"]

# --- 6. El estilo nuevo: Facebook en 9:16 y la placa recortada ---------------------------------
placa = Image.new("L", (1080, 1920), 0)
recorte = R._placa_al_cuadro(placa, (1080, 1350))
chequear("placa al cuadro: en un reel 4:5 se compara contra la placa recortada a 1080x1350",
         recorte.size == (1080, 1350))
chequear("placa al cuadro: en 9:16 queda entera", R._placa_al_cuadro(placa, (1080, 1920)).size == (1080, 1920))
chequear("a_9x16: un reel 9:16 no se toca", R.a_9x16_si_hace_falta(tmp / "x.mp4", tmp / "y.mp4", 1920) is None)

mp4 = tmp / "reel.mp4"
mp4.write_bytes(b"x")
convertidos = []
original_a9 = R.a_9x16_si_hace_falta
try:
    R.a_9x16_si_hace_falta = lambda src, dst, alto=0: convertidos.append(alto) or Path(dst)
    chequear("Facebook: un reel 4:5 sube en su copia 9:16",
             PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp).name == "reel.mp4"
             and PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp).parent == tmp and convertidos)
    convertidos.clear()
    chequear("Facebook: un reel 9:16 (o una pieza vieja sin medidas) sube tal cual",
             PUB._para_facebook({"video": {"alto": 1920}}, mp4, tmp / "otra") == mp4
             and PUB._para_facebook({"video": {}}, mp4, tmp / "otra") == mp4 and not convertidos)
    os.environ["FB_9X16"] = "0"
    chequear("Facebook: FB_9X16=0 sube siempre el original",
             PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp / "otra") == mp4)
    os.environ.pop("FB_9X16")
    R.a_9x16_si_hace_falta = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ffmpeg"))
    chequear("Facebook: si la copia falla, va el original (nunca frena la subida)",
             PUB._para_facebook({"video": {"alto": 1350}}, mp4, tmp / "otra") == mp4)
finally:
    R.a_9x16_si_hace_falta = original_a9

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
