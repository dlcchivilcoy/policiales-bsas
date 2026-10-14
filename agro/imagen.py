# -*- coding: utf-8 -*-
"""La imagen de cada pieza (punto 14 del documento y decisión del editor del 13/10/2026: «mixto»).

  - Fuente OFICIAL o de PRENSA (INTA, Secretaría, gacetillas de fabricantes para difusión): se usa
    su foto, con el crédito («Foto: INTA»), SI es una foto de verdad: de al menos MIN_ANCHO px y sin
    letras. La Bolsa de Comercio de Rosario publica placas y gráficos de 500 px con texto: su fuente
    lleva `"foto": False` y va directo a la IA.
  - Fuente que es OTRO MEDIO: su foto NO se republica (derechos). Va una imagen ilustrativa generada
    con IA (Cloudflare FLUX, gratis: la misma cuenta del Archivo) con la leyenda que lo avisa.
  - NUNCA sale la portada con el logo suelto (pedido del editor, 13/10/2026). Si la IA dibuja letras
    o no contesta: (1) la escena de la nota, dos intentos; (2) una ESCENA SEGURA del subtema, sin
    máquinas, carteles ni edificios (lo que trae letras); (3) una imagen del BANCO: fotos IA ya
    revisadas, varias por subtema, en agro/marca/banco/ (se arman con `python -m agro.imagen --banco`).

La URL de la foto original se guarda siempre (trazabilidad), aunque no se use.
"""
from pathlib import Path

MIN_ANCHO = 900         # una foto más chica se ve borrosa a 1080 de ancho
BANCO = Path(__file__).resolve().parent / "marca" / "banco"

# Escenas sin nada que suela traer letras (máquinas de cerca, carteles, envases, edificios).
SEGURAS = {
    "agro": ["Wide view of a green soybean field with trifoliate leaves in the pampas at golden hour",
             "Golden wheat field with heads of grain under a dramatic sky in the Argentine pampas",
             "Rows of young corn plants in dark fertile soil, low angle, morning light"],
    "mercados": ["Close-up of a pile of golden soybeans and corn kernels, soft daylight",
                 "Close-up of golden wheat grains heaped in a wooden bowl, soft window light",
                 "Long white silo bags lying in a harvested field under a blue sky, seen from far"],
    "agtech": ["Close-up of a soil moisture sensor probe in a green crop field, morning dew",
               "Agricultural drone flying over a green crop field, seen from below, blue sky",
               "Close-up of healthy soybean leaves with water droplets, macro, natural light"],
    "maquinaria": ["Silhouette of a combine harvester far away on the horizon of a golden wheat field at sunset, dust in the air, backlit",
                   "Wide shot of a large tractor far away working a field at dawn, unbranded",
                   "Seeding disc and furrow in dark soil, extreme close-up of a planter row unit, no markings, warm light"],
    "ganaderia": ["Herd of black Angus cattle grazing on green pampas grassland, soft light",
                  "Hereford cattle walking on a dirt path in the pampas at sunset",
                  "Close-up of a calf resting in green pasture, shallow depth of field"],
    "empresas": ["Aerial view of patchwork crop fields in the Argentine pampas, green and golden tones",
                 "Grain silos seen from far across a wheat field at sunset, no markings",
                 "Lone tree in the middle of a vast soybean field under a dramatic sky"],
}

ESTILO = (" Realistic modern editorial photograph for an agribusiness and agtech news outlet, natural "
          "daylight, cinematic composition, shallow depth of field, rich but natural colors, wide "
          "vertical-friendly framing with the subject in the upper-middle of the frame, no people "
          "facing the camera, no logos, no brand names, plain surfaces, wordless.")


def _ancho(ruta) -> int:
    try:
        from PIL import Image
        with Image.open(ruta) as im:
            return im.width
    except Exception:                                      # noqa: BLE001
        return 0


def _al_azar(lista: list, semilla: str):
    import hashlib
    return lista[int(hashlib.sha1((semilla or "x").encode()).hexdigest(), 16) % len(lista)]


def del_banco(subtema: str, semilla: str) -> str:
    """Una imagen del banco del subtema (o de cualquiera si ese no tiene), elegida por `semilla`
    para que no salga siempre la misma."""
    for carpeta in ([BANCO / subtema] if subtema else []) + [BANCO]:
        fotos = sorted(carpeta.rglob("*.jpg")) if carpeta.exists() else []
        if fotos:
            return str(_al_azar(fotos, semilla))
    return ""


def elegir(rep: dict, cuerpo_imagen: str, prompt: str, destino: Path, generar=None, bajar=None,
           mirar=None, subtema: str = "") -> dict:
    """{archivo, origen: «fuente»|«ia»|«ninguna», url_original, motivo}. «ninguna» solo si falla
    todo Y el banco está vacío."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    url = cuerpo_imagen or rep.get("imagen_url") or ""
    salida = {"url_original": url}
    if mirar is None:
        from archivo import imagen as IM
        mirar = IM.tiene_texto
    from agro import fuentes as F
    usa_foto = F.por_nombre(rep.get("fuente", "")).get("foto", True)
    if rep.get("tipo_fuente") in ("oficial", "prensa") and not usa_foto:
        salida["motivo"] = "esta fuente publica placas y gráficos, no fotos"
    elif rep.get("tipo_fuente") in ("oficial", "prensa") and url:
        if bajar is None:
            from reels.flujo import _bajar_foto as bajar
        foto = destino.with_name(destino.stem + "_fuente.jpg")
        if not bajar(url, foto):
            salida["motivo"] = "la foto de la fuente no se pudo bajar"
        elif _ancho(foto) < MIN_ANCHO:
            salida["motivo"] = f"la foto de la fuente es chica ({_ancho(foto)} px)"
        elif mirar(str(foto)):
            salida["motivo"] = "la foto de la fuente tiene letras (placa o gráfico)"
        else:
            return dict(salida, archivo=str(foto), origen="fuente", credito=rep.get("fuente", ""),
                        motivo=f"foto de una fuente {rep['tipo_fuente']}")
    if generar is None:
        from archivo import imagen as IM
        generar = IM.generar
    motivos = [salida.get("motivo")] if salida.get("motivo") else []
    segura = _al_azar(SEGURAS.get(subtema) or SEGURAS["agro"], rep.get("id", ""))
    intentos = ((prompt, "la escena de la nota"), (prompt, "la escena de la nota"),
                (segura, "una escena segura del tema"))
    for k, (texto, cual) in enumerate(intentos):
        if not (texto or "").strip():
            continue
        r = generar(texto, destino.with_name(f"{destino.stem}_ia{k}.jpg"), estilo=ESTILO)
        if not r.get("archivo"):
            motivos.append(r.get("motivo") or "la IA no dio imagen")
            continue
        if not mirar(r["archivo"]):            # False o None (no se pudo mirar): sirve
            return dict(salida, archivo=r["archivo"], origen="ia",
                        motivo=f"imagen ilustrativa con IA ({cual})" + (f"; antes: {'; '.join(motivos)}" if motivos else ""))
        motivos.append("la IA dibujó letras")
    banco = del_banco(subtema, rep.get("id", ""))
    if banco:
        return dict(salida, archivo=banco, origen="ia",
                    motivo=f"imagen IA del banco ({subtema or 'general'}); antes: {'; '.join(motivos)}")
    return dict(salida, archivo=None, origen="ninguna", motivo="; ".join(motivos) or "sin imagen")


def armar_banco(log=print) -> int:
    """Genera y revisa (sin letras) las imágenes del banco: una por escena segura. Las que ya están
    no se rehacen. Devuelve cuántas hay en total."""
    from archivo import imagen as IM
    for sub, escenas in SEGURAS.items():
        carpeta = BANCO / sub
        carpeta.mkdir(parents=True, exist_ok=True)
        for k, escena in enumerate(escenas):
            destino = carpeta / f"{sub}_{k + 1}.jpg"
            if destino.exists():
                continue
            for _ in range(3):
                r = IM.generar(escena, destino, estilo=ESTILO)
                if r.get("archivo") and IM.tiene_texto(r["archivo"]) is False:
                    _achicar(destino)
                    log(f"  banco {sub} {k + 1}: ok")
                    break
                destino.unlink(missing_ok=True)
            else:
                log(f"  banco {sub} {k + 1}: no salió sin letras")
    return len(list(BANCO.rglob("*.jpg")))


def _achicar(ruta: Path):
    """JPG de calidad 85: el banco va al repo y no tiene que pesar de más."""
    from PIL import Image
    with Image.open(ruta) as im:
        im.convert("RGB").save(ruta, "JPEG", quality=85)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    import entorno
    entorno.cargar()
    if "--banco" in sys.argv:
        print(f"banco: {armar_banco()} imágenes en {BANCO}")
