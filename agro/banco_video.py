# -*- coding: utf-8 -*-
"""EL BANCO DE VIDEOS ILUSTRATIVOS de agro (16/11/2026).

Pedido del editor: «un ecosistema lo más intercalado posible: un reel, un carrusel» y «priorizá encontrar noticias
con videos para armar reels». El sondeo de ese día mostró que los medios de campo casi nunca alojan su video: lo
suben a YouTube, que desde la nube no se baja. Entonces el turno de reel sin video propio usa un VIDEO
ILUSTRATIVO real (una cosechadora, un rodeo, un lote de soja) debajo del texto de la noticia, con la leyenda
«Video ilustrativo» y el crédito del autor.

Los videos son de Wikimedia Commons con licencia libre (CC0, dominio público, CC BY o CC BY-SA; nunca NC ni ND).
La licencia pide nombrar al autor y la licencia: va en la leyenda del reel y en el texto del posteo.

    venv\\Scripts\\python.exe -m agro.banco_video --armar            # arma el banco (local, una vez; ~20 min)
    venv\\Scripts\\python.exe -m agro.banco_video --armar --tag soja  # completa un tema
    venv\\Scripts\\python.exe -m agro.banco_video --subir            # sube los .mp4 al Release agro-banco-video

Cada video: un tramo de hasta 20 s, 1080x810 (la parte de arriba del reel 4:5), sin sonido, que Gemini miró en
tres cuadros (escena del campo que podría ser de la región pampeana, del tema pedido, sin textos, logos
sobreimpresos ni marcas de agua, sin animales faenados). El índice (autor, licencia, link) va al repo en
agro/marca/banco_video.json; los .mp4, al Release `agro-banco-video` (el repo es público: se bajan sin clave).
En la nube, `elegir` busca el tema de la noticia (palabras del texto, si no el subtema) y no repite un video
dentro de DIAS_SIN_REPETIR días (mem["banco_usados"]). AGRO_BANCO_VIDEO=0 lo apaga (sin video, carrusel).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agro import diseno as D  # noqa: E402

INDICE = D.MARCA / "banco_video.json"
LOCAL = Path(__file__).resolve().parent.parent / "salida_agro" / "banco_video"
RELEASE = "agro-banco-video"
REPO = "dlcchivilcoy/policiales-bsas"
URL_RELEASE = f"https://github.com/{REPO}/releases/download/{RELEASE}/{{}}"
API = "https://commons.wikimedia.org/w/api.php"
UA = "DiarioLaCampana-agro/1.0 (https://www.xn--diariolacampaa-2nb.com.ar)"
ANCHO, ALTO = 1080, 810
SEG = 20
DIAS_SIN_REPETIR = 4
POR_TAG = 6

# tema: (búsquedas en Commons, palabras de la noticia que lo piden, qué tiene que verse — para Gemini)
TAGS = {
    "cosecha": (("combine harvester field", "grain harvest combine", "harvester unloading grain cart"),
                ("cosech", "trilla", "cosechadora"), "una cosechadora trabajando en un lote"),
    "soja": (("soybean field", "soybean harvest", "soybeans", "soybean plants", "soy field"), ("soja", "soyero", "poroto"), "un lote de soja"),
    "maiz": (("corn field", "maize field", "corn harvest"), ("maiz", "maices", "choclo", "silo de maiz"),
             "un lote de maíz"),
    "trigo": (("wheat field", "wheat harvest", "barley field"), ("trigo", "cebada", "fina", "cultivos de invierno"),
              "un lote de trigo o cebada"),
    "girasol": (("sunflower field",), ("girasol",), "un lote de girasol"),
    "siembra": (("tractor seeding", "planter tractor field", "seed drill tractor"), ("siembra", "sembr", "sembradora"),
                "un tractor sembrando"),
    "pulverizacion": (("crop sprayer", "agricultural sprayer tractor", "agricultural drone spraying"),
                      ("pulveriz", "fitosanit", "herbicida", "fungicida", "insecticida", "plaga", "chicharrita"),
                      "una pulverizadora o un dron fumigando un cultivo"),
    "maquinaria": (("tractor field", "tractor plowing", "agricultural machinery", "tractor driving farm"),
                   ("tractor", "maquinaria", "maquina", "implemento", "fierros", "sembradoras", "metalmecanic"),
                   "un tractor o máquina agrícola trabajando"),
    "ganado": (("cattle grazing", "beef cattle herd", "cattle pasture", "cows field"),
               ("ganad", "hacienda", "vacun", "novillo", "terner", "vaquillona", "rodeo", "feedlot", "carne", "remate",
                "invernada", "cria"), "vacas o novillos en el campo"),
    "tambo": (("dairy cows", "milking parlor", "dairy farm"), ("tambo", "leche", "lacteo", "tambero"),
              "vacas lecheras o un tambo"),
    "lluvia": (("rain on field", "storm clouds farmland", "rain farm", "thunderstorm clouds plains"),
               ("lluvia", "llovi", "tormenta", "precipitacion", "alerta", "temporal", "nubes", "humedad"),
               "lluvia o nubes de tormenta sobre el campo"),
    "granizo": (("hail", "hailstorm", "hail storm", "hailstones"), ("granizo", "piedra"), "granizo cayendo"),
    "inundacion": (("flooded field", "flood farmland", "flooded farm"), ("inund", "anegad", "crecida", "agua en los campos",
                                                                        "excesos hidricos"), "un campo inundado"),
    "sequia": (("drought field", "drought corn", "drought crops", "drought farm", "dry cracked soil",
                "dry farmland", "dust farm field"), ("sequia", "seca", "deficit hidrico", "falta de agua"),
               "un campo seco o tierra agrietada"),
    "tecnologia": (("agricultural drone", "drone spraying crops", "farm drone", "agricultural robot", "farm robot",
                    "precision agriculture", "autonomous tractor"),
                   ("dron", "drone", "robot", "inteligencia artificial", "satelit", "agricultura de precision", "digital",
                    "agtech", "software", "sensor", "autonom"), "tecnología en el campo: drones, robots, sensores o máquinas modernas trabajando un cultivo"),
    "granos": (("grain silo", "grain bin", "grain elevator", "grain truck", "grain cart", "grain truck unloading",
                "grain silo bags", "corn grain"),
               ("acopio", "silo", "granos", "puerto", "export", "camion", "flete", "precio", "mercado", "rosario"),
               "silos, granos o camiones de granos"),
    "campo": (("farm landscape aerial", "farm fields drone", "crop field aerial", "agricultural landscape",
               "countryside field aerial", "farmland drone", "rural landscape fields", "prairie"), (),
              "un paisaje de campo de cultivo o de llanura"),
}
POR_SUBTEMA = {"agro": "campo", "mercados": "granos", "agtech": "tecnologia", "maquinaria": "maquinaria",
               "ganaderia": "ganado", "empresas": "campo"}
# Lo que tiene que decir el título o la descripción del archivo en Commons (la búsqueda trae de todo).
EXIGE = {"cosecha": r"combine|harvest", "soja": r"soybean|soya|soy ?(field|crop|plant|harvest)", "maiz": r"\bcorn|maize", "trigo": r"wheat|barley",
         "girasol": r"sunflower", "siembra": r"seed|planter|planting|sowing|drill", "pulverizacion": r"spray",
         "maquinaria": r"tractor|machiner|plow|plough", "ganado": r"cattle|\bcows?\b|beef|herd|steer|heifer",
         "tambo": r"dairy|milk", "lluvia": r"\brain|storm|cloud|thunder", "granizo": r"\bhail",
         "inundacion": r"flood", "sequia": r"drought|\bdry\b|cracked", "tecnologia": r"drone|robot|precision|autonomous",
         "granos": r"grain|silo|elevator", "campo": r"farm|field|countryside|pasture|agricultur|prairie|pampa"}
LICENCIAS_OK = re.compile(r"^(cc0|cc[- ]by(-sa)?( \d\.\d)?|public domain|pd\b|cc[- ]by[- ]sa)", re.I)
NO_VA = re.compile(r"slaughter|abattoir|kill|vegan|protest|cruelty|blood|accident|crash|war\b", re.I)


def activo() -> bool:
    """APAGADO desde el 17/11/2026 (pedido del editor: «poner siempre los videos y fotos originales de las notas
    con cita, para no optar por las imágenes ilustrativas»): el turno de reel sin video de la nota sale con el
    reel del clima o como carrusel con la foto original. AGRO_BANCO_VIDEO=1 lo vuelve a prender."""
    return (os.environ.get("AGRO_BANCO_VIDEO") or "0").strip() != "0"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def cargar_indice(ruta: Path = None) -> list:
    try:
        return json.loads((ruta or INDICE).read_text(encoding="utf-8")).get("videos") or []
    except (OSError, ValueError):
        return []


def tags_de(texto: str, subtema: str = "") -> list:
    """Los temas del banco que pide la noticia, del más al menos nombrado; al final el del subtema y «campo»."""
    t = _norm(texto)
    cuenta = []
    for tag, (_b, palabras, _v) in TAGS.items():
        n = sum(len(re.findall(rf"\b{re.escape(p)}", t)) for p in palabras)
        if n:
            cuenta.append((n, tag))
    orden = [tag for _n, tag in sorted(cuenta, key=lambda x: -x[0])]
    for extra in (POR_SUBTEMA.get(subtema or "", "campo"), "campo"):
        if extra not in orden:
            orden.append(extra)
    return orden


def elegir(texto: str, subtema: str, usados: dict, ahora: datetime, indice: list = None) -> dict | None:
    """El video del banco para la noticia: del primer tema que tenga uno sin usar en DIAS_SIN_REPETIR días (si
    todos se usaron, el usado hace más tiempo). None si el banco está vacío o apagado."""
    if not activo():
        return None
    indice = cargar_indice() if indice is None else indice
    if not indice:
        return None
    limite = (ahora - timedelta(days=DIAS_SIN_REPETIR)).isoformat()
    permitidos = tags_de(texto, subtema)
    for tag in permitidos:
        del_tag = [v for v in indice if v.get("tag") == tag]
        libres = [v for v in del_tag if (usados or {}).get(v["archivo"], "") < limite]
        if libres:
            # Entre los libres, primero el de más impacto (los viejos, sin puntaje, cuentan como 5).
            return sorted(libres, key=lambda v: ((usados or {}).get(v["archivo"], ""), -(v.get("impacto") or 5)))[0]
    # Todos los de esos temas se usaron hace poco: el usado hace más tiempo, pero SIEMPRE de esos temas (16/11: una
    # alerta de tormenta salió con una cosechadora porque el banco no tenía lluvia y se tomaba cualquiera).
    posibles = [v for v in indice if v.get("tag") in permitidos]
    return min(posibles, key=lambda v: (usados or {}).get(v["archivo"], "")) if posibles else None


def anotar(usados: dict, video: dict, ahora: datetime) -> None:
    usados[video["archivo"]] = ahora.isoformat(timespec="minutes")
    limite = (ahora - timedelta(days=30)).isoformat()
    for k in [k for k, v in usados.items() if v < limite]:
        usados.pop(k)


def credito(video: dict) -> str:
    """«Autor · CC BY-SA 4.0 · Wikimedia Commons»."""
    autor = " ".join(re.sub(r"<[^>]+>", " ", video.get("autor") or "").split())[:60] or "autor desconocido"
    return f"{autor} · {video.get('licencia') or 'licencia libre'} · Wikimedia Commons"


def linea_caption(video: dict) -> str:
    return f"🎥 Video ilustrativo: {credito(video)} ({video.get('fuente', '')})".strip()


def bajar(video: dict, destino: Path, get=None) -> Path | None:
    """El .mp4 del Release (o la copia local, si se armó en esta máquina). None si no se pudo."""
    local = LOCAL / video["archivo"]
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if local.is_file():
        destino.write_bytes(local.read_bytes())
        return destino
    try:
        import httpx
        r = (get or (lambda u: httpx.get(u, timeout=60, follow_redirects=True)))(URL_RELEASE.format(video["archivo"]))
        if r.status_code != 200 or len(r.content) < 20000:
            return None
        destino.write_bytes(r.content)
        return destino
    except Exception:                                      # noqa: BLE001 — sin el video, carrusel
        return None


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Armado del banco (local)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _api(params: dict) -> dict:
    import httpx
    r = httpx.get(API, params={**params, "format": "json"}, headers={"User-Agent": UA}, timeout=40)
    r.raise_for_status()
    return r.json()


def _buscar(q: str, n: int = 30) -> list:
    d = _api({"action": "query", "list": "search", "srsearch": f"{q} filetype:video", "srnamespace": 6, "srlimit": n})
    return [x["title"] for x in d.get("query", {}).get("search", [])]


def _info(titulos: list) -> list:
    d = _api({"action": "query", "titles": "|".join(titulos[:40]), "prop": "videoinfo",
              "viprop": "url|size|mediatype|extmetadata|derivatives"})
    salida = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        vi = (p.get("videoinfo") or [{}])[0]
        if not vi:
            continue
        meta = vi.get("extmetadata") or {}
        val = lambda k: (meta.get(k) or {}).get("value") or ""  # noqa: E731
        salida.append({"titulo": p["title"], "ancho": vi.get("width") or 0, "alto": vi.get("height") or 0,
                       "seg": float(vi.get("duration") or 0), "url": vi.get("url"), "pagina": vi.get("descriptionurl"),
                       "derivados": vi.get("derivatives") or [], "licencia": re.sub(r"<[^>]+>", "", val("LicenseShortName")),
                       "autor": re.sub(r"<[^>]+>", " ", val("Artist")).strip(), "desc": re.sub(r"<[^>]+>", " ", val("ImageDescription"))[:300]})
    return salida


def _fuente_de(info: dict) -> str:
    """El derivado de 720p (o el que más se acerque sin pasarse de 1080), o el original."""
    mejores = []
    for d in info["derivados"]:
        alto = d.get("height") or 0
        if 700 <= alto <= 1080 and (d.get("src") or "").startswith("http"):
            mejores.append((abs(alto - 720), d["src"]))
    return min(mejores)[1] if mejores else info["url"]


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


MAX_MB = 250
MAX_SEG_BAJADA = 300      # un archivo que tarda más de 5 minutos se saltea


def _descargar(url: str, destino: Path) -> bool:
    """El archivo entero, en UN pedido y con el User-Agent que pide Wikimedia (ffmpeg leyendo la URL hacía muchos
    pedidos con rangos y Commons contestaba 429). Con pausa y reintento si igual contesta 429."""
    import time
    import httpx
    for intento in range(4):
        time.sleep(3 + 20 * intento)
        try:
            with httpx.stream("GET", url, headers={"User-Agent": UA}, timeout=120, follow_redirects=True) as r:
                if r.status_code == 429:
                    continue
                if r.status_code >= 400:
                    return False
                total = 0
                limite = time.time() + MAX_SEG_BAJADA     # 17/11: Commons a veces manda a 20 KB/s y no termina nunca
                with open(destino, "wb") as fh:
                    for trozo in r.iter_bytes(1 << 16):
                        total += len(trozo)
                        if total > MAX_MB * 1024 * 1024 or time.time() > limite:
                            fh.close()
                            destino.unlink(missing_ok=True)
                            return False
                        fh.write(trozo)
            return total > 100000
        except Exception:                                  # noqa: BLE001
            destino.unlink(missing_ok=True)
    return False


def _cortar(url: str, desde: float, seg: float, destino: Path) -> bool:
    crudo = destino.with_suffix(".bajado")
    if not _descargar(url, crudo):
        return False
    try:
        return _cortar_local(str(crudo), desde, seg, destino)
    finally:
        crudo.unlink(missing_ok=True)


def _cortar_local(url: str, desde: float, seg: float, destino: Path) -> bool:
    cmd = [_ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{desde:.1f}", "-i", url, "-t", f"{seg:.1f}",
           "-an", "-vf", f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},fps=24",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "26", "-movflags", "+faststart",
           str(destino)]
    try:
        subprocess.run(cmd, check=True, timeout=240)
    except Exception:                                      # noqa: BLE001
        destino.unlink(missing_ok=True)
        return False
    return destino.is_file() and destino.stat().st_size > 50000


def _cuadros(mp4: Path, seg: float) -> list:
    sal = []
    for i, t in enumerate((1.0, seg / 2, max(1.5, seg - 1.5))):
        jpg = mp4.with_name(f"{mp4.stem}_{i}.jpg")
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{t:.1f}", "-i", str(mp4), "-frames:v", "1",
                        "-q:v", "4", str(jpg)], check=False, timeout=60)
        if jpg.is_file():
            sal.append(jpg)
    return sal


SISTEMA = (
    "Mirás tres cuadros de un video que va a ilustrar una noticia del campo argentino (región pampeana). "
    "Respondé SOLO con JSON: {\"apto\": true|false, \"motivo\": \"por qué no, si no\", \"describe\": \"qué se ve, en "
    "castellano, 12 palabras\", \"impacto\": 1-10}. «impacto» es cuánto frenaría a alguien que pasa el dedo por "
    "Instagram: 9-10 acción fuerte y de cerca (granizo cayendo, una cosechadora llenando la tolva en primer plano, "
    "un dron pasando sobre el cultivo, un rodeo corriendo); 5-6 algo que se mueve pero lejos; 1-3 un plano quieto "
    "o aburrido. Es APTO solo si: es una filmación real (no animación ni gráfico), nítida y con buena "
    "luz; muestra lo que se pide; podría ser un campo de Argentina (no arrozales, nieve, selva, montañas ni pueblos de "
    "Asia o África); NO tiene textos, subtítulos, logos sobreimpresos ni marcas de agua; NO muestra animales muertos, "
    "faena, sangre ni accidentes; las personas, si aparecen, están lejos o de espaldas.")


def _mirar(cuadros: list, pedido: str) -> dict:
    from reels import ia as IA
    partes = [("image/jpeg", Path(c).read_bytes()) for c in cuadros]
    crudo, _via = IA.redactar_gemini(SISTEMA, f"Lo que tiene que verse: {pedido}.", max_tokens=300, imagenes=partes)
    return IA._parsear(crudo) or {}


def _impacto(veredicto: dict) -> int:
    try:
        return max(0, min(10, int(round(float(veredicto.get("impacto") or 0)))))
    except (TypeError, ValueError):
        return 0


def impacto_min() -> int:
    """17/11/2026 (pedido del editor: «el que tenga más chance de viralizar»): al armar, solo entra el video con
    impacto ≥ AGRO_BANCO_IMPACTO (7). "0" acepta todo."""
    try:
        return int(os.environ.get("AGRO_BANCO_IMPACTO") or 7)
    except ValueError:
        return 7


def armar(tags: list = None, por_tag: int = POR_TAG, log=print) -> list:
    if not os.environ.get("GEMINI_API_KEY"):
        import entorno
        entorno.cargar()
    LOCAL.mkdir(parents=True, exist_ok=True)
    indice = cargar_indice()
    usados_titulos = {v["titulo"] for v in indice}
    for tag in tags or list(TAGS):
        busquedas, _p, pedido = TAGS[tag]
        tiene = sum(1 for v in indice if v["tag"] == tag)
        log(f"== {tag}: ya hay {tiene}")
        titulos = []
        for q in busquedas:
            try:
                titulos += [t for t in _buscar(q) if t not in titulos]
            except Exception as e:                         # noqa: BLE001
                log(f"   búsqueda «{q}» falló: {e}")
        infos = []
        for i in range(0, len(titulos), 40):
            try:
                infos += _info(titulos[i:i + 40])
            except Exception as e:                         # noqa: BLE001
                log(f"   info falló: {e}")
        for info in infos:
            if tiene >= por_tag:
                break
            if info["titulo"] in usados_titulos or NO_VA.search(info["titulo"] + " " + info["desc"]):
                continue
            if not re.search(EXIGE.get(tag, "."), f"{info['titulo']} {info['desc']}", re.I):
                continue
            if not LICENCIAS_OK.search(info["licencia"]) or re.search(r"\b(nc|nd)\b", info["licencia"], re.I):
                continue
            if max(info["ancho"], info["alto"]) < 1280 or info["ancho"] < info["alto"] or not (8 <= info["seg"] <= 3600):
                continue
            seg = min(SEG, info["seg"] - 1)
            desde = max(0.0, min(info["seg"] * 0.3, info["seg"] - seg - 0.5))
            n = tiene + 1
            archivo = f"bv_{tag}_{n:02d}.mp4"
            while any(v["archivo"] == archivo for v in indice):
                n += 1
                archivo = f"bv_{tag}_{n:02d}.mp4"
            mp4 = LOCAL / archivo
            if not _cortar(_fuente_de(info), desde, seg, mp4):
                log(f"   ✗ {info['titulo'][5:70]}: no se pudo cortar")
                continue
            cuadros = _cuadros(mp4, seg)
            try:
                veredicto = _mirar(cuadros, pedido)
            except Exception as e:                         # noqa: BLE001
                veredicto = {"apto": False, "motivo": f"la IA no contestó ({type(e).__name__})"}
            for c in cuadros:
                c.unlink(missing_ok=True)
            usados_titulos.add(info["titulo"])
            impacto = _impacto(veredicto)
            if veredicto.get("apto") and impacto < impacto_min():
                veredicto = dict(veredicto, apto=False, motivo=f"poco impacto para un reel ({impacto}/10)")
            if not veredicto.get("apto"):
                log(f"   ✗ {info['titulo'][5:70]}: {str(veredicto.get('motivo'))[:90]}")
                mp4.unlink(missing_ok=True)
                continue
            tiene += 1
            indice.append({"archivo": archivo, "tag": tag, "titulo": info["titulo"], "autor": info["autor"][:120],
                           "licencia": info["licencia"], "fuente": info["pagina"], "seg": round(seg, 1),
                           "describe": str(veredicto.get("describe") or "")[:160], "impacto": impacto})
            log(f"   ✓ {archivo} [{impacto}/10]: {veredicto.get('describe')} ({info['licencia']}, {info['autor'][:40]})")
            INDICE.write_text(json.dumps({"actualizado": datetime.now().isoformat(timespec="minutes"),
                                          "videos": indice}, ensure_ascii=False, indent=1), encoding="utf-8")
    return indice


def subir(log=print) -> None:
    """Sube al Release los .mp4 del índice que están en esta máquina (gh, con la sesión del usuario)."""
    archivos = [str(LOCAL / v["archivo"]) for v in cargar_indice() if (LOCAL / v["archivo"]).is_file()]
    if subprocess.run(["gh", "release", "view", RELEASE, "-R", REPO], capture_output=True).returncode != 0:
        subprocess.run(["gh", "release", "create", RELEASE, "-R", REPO, "--title", "Banco de videos ilustrativos de agro",
                        "--notes", "Tramos de videos de Wikimedia Commons con licencia libre (autor y licencia en "
                                   "agro/marca/banco_video.json). Los usa agro/banco_video.py. No borrar.",
                        "--prerelease"], check=True)
    for i in range(0, len(archivos), 20):
        subprocess.run(["gh", "release", "upload", RELEASE, "-R", REPO, "--clobber", *archivos[i:i + 20]], check=True)
    log(f"subidos {len(archivos)} videos")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--armar", action="store_true")
    ap.add_argument("--tag", action="append")
    ap.add_argument("--por-tag", type=int, default=POR_TAG)
    ap.add_argument("--subir", action="store_true")
    a = ap.parse_args()
    if a.armar:
        armar(a.tag, a.por_tag)
    if a.subir:
        subir()


if __name__ == "__main__":
    main()
