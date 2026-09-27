# -*- coding: utf-8 -*-
"""El publicador contra un Meta, un YouTube y un GitHub FALSOS. No usa la red ni publica nada.

Cubre lo que no se puede probar publicando de a uno: el 500 mentiroso de Instagram,
el contenedor en ERROR, una red que falla sin tumbar a la otra, no repetir lo ya
publicado, los 5 minutos entre posteos, que ningun token termine en una URL, el tope
diario y el cupo agotado de YouTube, el token de otro canal, el lugar que se le deja al
bot en Instagram, y que TikTok no salga.
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
import httpx
from reels import publicador as PUB

fallas = []
total = 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


TOKENS = {"FACEBOOK_PAGE_ACCESS_TOKEN": "fb_token_secreto_123456",
          "INSTAGRAM_ACCESS_TOKEN": "ig_token_secreto_123456",
          "GITHUB_TOKEN": "gh_token_secreto_123456"}
YT_SECRETOS = {"client_secret": "yt_cliente_secreto_123456", "refresh_token": "yt_refresco_secreto_123456",
               "token": "yt_viejo_secreto_123456"}
YT_ACCESO = "ya29_acceso_secreto_123456"
os.environ.update(TOKENS)
os.environ.update({"FACEBOOK_PAGE_ID": "PAGINA", "INSTAGRAM_USER_ID": "IGUSER",
                   "GITHUB_REPOSITORY": "dlcchivilcoy/policiales-bsas",
                   "YT_CHANNEL_ID": "UCRADIO",
                   "YT_TOKEN_JSON": json.dumps({"client_id": "cliente.apps.googleusercontent.com",
                                                "token_uri": "https://oauth2.googleapis.com/token",
                                                **YT_SECRETOS})})
os.environ.pop("YT_SHORTS_POR_DIA", None)
os.environ.pop("IG_RESERVA_BOT", None)
os.environ["NOTAS_WEB"] = "0"          # la nota de la web se prueba aparte (sección 16)
os.environ.pop("IG_PRUEBA_POR_PASADA", None)
TODOS_LOS_SECRETOS = list(TOKENS.values()) + list(YT_SECRETOS.values()) + [YT_ACCESO]


class Reloj:
    """El tiempo solo avanza cuando el publicador duerme: las esperas no tardan."""
    def __init__(self):
        self.t = datetime(2026, 9, 26, 10, 0, 0)
        self.dormido = 0.0

    def ahora(self):
        return self.t

    def dormir(self, s):
        self.dormido += s
        self.t += timedelta(seconds=s)


class Meta:
    """Graph API + rupload + GitHub, con fallas a pedido."""
    def __init__(self, ig_publicar=None, ig_estados=None, fb_inicio=200,
                 yt_canal="UCRADIO", yt_sin_cupo=False, yt_cortes=0, ig_cupo=(4, 100), ig_tope_prueba=None, ig_recientes=None,
                 wix_falla=None, wix_existe="", wix_foto_falla=False):
        self.pedidos = []
        self.contenedores = []            # los params de cada POST /media
        self.publicar_llamadas = 0
        self.fb_finish = []
        self.ig_publicar = list(ig_publicar or [])     # respuestas de media_publish, en orden
        self.ig_estados = list(ig_estados or [])       # status_code sucesivos del contenedor
        self.fb_inicio = fb_inicio
        self.publicado = set()
        self.yt_canal = yt_canal          # de que canal es el token
        self.yt_sin_cupo = yt_sin_cupo    # YouTube contesta quotaExceeded
        self.yt_cortes = yt_cortes        # subidas que LLEGAN pero pierden la respuesta
        self.yt_inicios = []              # metadatos de cada sesion de subida abierta
        self.yt_videos = {}               # upload_id -> id del video creado
        self.ig_cupo = ig_cupo            # (usados, total) de Instagram; None = no se puede leer
        self.ig_tope_prueba = ig_tope_prueba  # reels de prueba que acepta antes de rebotar
        self.ig_recientes = list(ig_recientes or [])   # lo que ya está en el Instagram de la cuenta
        self.wix_falla = wix_falla        # paso de Wix que contesta 500 ("borrador")
        self.wix_existe = wix_existe      # slug que Wix dice que ya existe
        self.wix_foto_falla = wix_foto_falla
        self.wix_borradores = []          # el cuerpo de cada borrador creado
        self.wix_publicados = 0

    def _youtube(self, req, host, ruta, m):
        if host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": YT_ACCESO, "expires_in": 3599})
        if ruta == "/youtube/v3/channels":
            return httpx.Response(200, json={"items": [{"id": self.yt_canal}]})
        if ruta == "/upload/youtube/v3/videos" and m == "POST":
            if self.yt_sin_cupo:
                return httpx.Response(403, json={"error": {"code": 403, "message": "quota",
                                                           "errors": [{"reason": "quotaExceeded"}]}})
            self.yt_inicios.append(json.loads(req.content))
            uid = f"U{len(self.yt_inicios)}"
            return httpx.Response(200, headers={"location":
                f"https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id={uid}"})
        if ruta == "/upload/youtube/v3/videos" and m == "PUT":
            uid = req.url.params["upload_id"]
            if req.headers.get("content-range", "").startswith("bytes */"):      # ¿como quedo?
                if uid in self.yt_videos:
                    return httpx.Response(200, json={"id": self.yt_videos[uid],
                                                     "status": {"privacyStatus": "public"}})
                return httpx.Response(308)
            self.yt_videos[uid] = f"YT{len(self.yt_videos) + 1}"
            if self.yt_cortes:
                self.yt_cortes -= 1
                raise httpx.ReadTimeout("se corto", request=req)   # llego, pero sin respuesta
            return httpx.Response(200, json={"id": self.yt_videos[uid],
                                             "status": {"privacyStatus": "public"}})
        return None

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.pedidos.append(req)
        host, ruta, m = req.url.host, req.url.path, req.method
        if host.endswith("googleapis.com"):
            r = self._youtube(req, host, ruta, m)
            if r is not None:
                return r
        cuerpo = parse_qs(req.content.decode("utf-8")) if req.content and host == "graph.facebook.com" else {}
        uno = {k: v[0] for k, v in cuerpo.items()}

        if host == "www.wixapis.com":
            if ruta == "/blog/v3/posts/query":
                return httpx.Response(200, json={"posts": [{"slug": self.wix_existe}] if self.wix_existe else []})
            if ruta == "/site-media/v1/files/import":
                if self.wix_foto_falla:
                    return httpx.Response(400, json={"message": "no se pudo bajar"})
                return httpx.Response(200, json={"file": {"id": "FOTO1"}})
            if ruta == "/blog/v3/draft-posts":
                if self.wix_falla == "borrador":
                    return httpx.Response(500, text="error interno")
                self.wix_borradores.append(json.loads(req.content or b"{}"))
                return httpx.Response(200, json={"draftPost": {"id": f"D{len(self.wix_borradores)}"}})
            if ruta.endswith("/publish"):
                self.wix_publicados += 1
                return httpx.Response(200, json={"post": {}})
        if host == "api.github.com" and ruta.endswith("/releases/tags/reels-policiales"):
            return httpx.Response(200, json={"id": 7, "assets": []})
        if host == "uploads.github.com":
            n = req.url.params["name"]
            return httpx.Response(201, json={"browser_download_url":
                f"https://github.com/dlcchivilcoy/policiales-bsas/releases/download/reels-policiales/{n}"})
        if host == "github.com" and m == "HEAD":
            return httpx.Response(200)

        if host == "graph.facebook.com":
            if ruta == "/v26.0/IGUSER/media" and m == "POST":
                self.contenedores.append(uno)
                return httpx.Response(200, json={"id": f"C{len(self.contenedores)}"})
            if ruta == "/v26.0/IGUSER/content_publishing_limit" and self.ig_cupo:
                usados, total = self.ig_cupo
                return httpx.Response(200, json={"data": [{"config": {"quota_total": total,
                    "quota_duration": 86400}, "quota_usage": usados}]})
            if ruta == "/v26.0/IGUSER/media" and m == "GET":
                return httpx.Response(200, json={"data": self.ig_recientes})
            if ruta.startswith("/v26.0/C") and m == "GET":
                cid = ruta.rsplit("/", 1)[1]
                if cid in self.publicado:
                    return httpx.Response(200, json={"status_code": "PUBLISHED"})
                est = self.ig_estados.pop(0) if self.ig_estados else "FINISHED"
                if est == "PUBLICAR_YA":           # el media_publish "fallo" pero salio
                    return httpx.Response(200, json={"status_code": "PUBLISHED"})
                return httpx.Response(200, json={"status_code": est,
                                                 "status": "Error: 2207020 - falso" if est == "ERROR" else ""})
            if ruta == "/v26.0/IGUSER/media_publish":
                self.publicar_llamadas += 1
                if self.ig_tope_prueba is not None and len(self.publicado) >= self.ig_tope_prueba:
                    return httpx.Response(400, json={"error": {"code": 9, "message":
                        "Has alcanzado el número máximo de reels de prueba que se pueden publicar "
                        "mediante la API de publicación de contenido."}})
                resp = self.ig_publicar.pop(0) if self.ig_publicar else (200, {"id": "M1"})
                if resp[0] < 400:
                    self.publicado.add(uno["creation_id"])
                return httpx.Response(resp[0], json=resp[1])
            if ruta == "/v26.0/PAGINA/video_reels":
                if uno.get("upload_phase") == "start":
                    if self.fb_inicio >= 400:
                        return httpx.Response(self.fb_inicio, json={"error": {"message": "permiso", "code": 200}})
                    return httpx.Response(200, json={"video_id": "V1",
                        "upload_url": "https://rupload.facebook.com/video-upload/v26.0/V1"})
                self.fb_finish.append(uno)
                return httpx.Response(200, json={"success": True})
            if ruta == "/v26.0/V1":
                return httpx.Response(200, json={"status": {
                    "video_status": "ready", "publishing_phase": {"status": "complete"}}})
        if host == "rupload.facebook.com":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404, json={"error": {"message": f"ruta no prevista {m} {ruta}"}})


def pieza(orden, pueblo, apta=True, hora="2026-09-26T10:00"):
    return {"orden": orden, "apto_para_publicar": apta, "por_que_no": "" if apta else "por reglas",
            "localidad": pueblo, "url_original": f"https://medio.test/{orden}",
            "publicar_en": hora if apta else None,
            "guion": {"titular": f"Titular {orden}"},
            "descripcion_tiktok": f"Texto del posteo {orden}\n\n#Policiales",
            "web": {"titulo": f"Junín: el hecho número {orden}", "cuerpo": "Párrafo uno.\n\nPárrafo dos."},
            "imagen_url": f"https://medio.test/{orden}.jpg", "medio": "Medio Test",
            "video": {"archivo": f"Z:\\otra\\maquina\\{orden:02d}_reel.mp4", "duracion": 10.4}}


def preparar(meta=None):
    """Una carpeta de tanda nueva, ledger vacio, reloj y red falsos."""
    base = Path(tempfile.mkdtemp(prefix="pub_"))
    carpeta = base / "2026-09-26_1000"
    carpeta.mkdir()
    piezas = [pieza(1, "junin"), pieza(2, "pergamino"), pieza(3, "lobos", apta=False)]
    for p in piezas:
        (carpeta / f"{p['orden']:02d}_reel.mp4").write_bytes(b"\x00" * 4096)
    (carpeta / "_lote.json").write_text(json.dumps({"publicado": False, "piezas": piezas}),
                                        encoding="utf-8")
    reloj = Reloj()
    meta = meta or Meta()
    PUB._http = httpx.Client(transport=httpx.MockTransport(meta))
    PUB._ahora, PUB._dormir = reloj.ahora, reloj.dormir
    PUB._barrer_release = lambda *a, **k: {"borrados": [], "mb": 0}
    PUB.LEDGER = base / "estado" / "publicados.json"
    PUB.RAIZ = base
    return base, carpeta, reloj, meta


def silencio(fn, *a, **k):
    """Corre sin llenar la pantalla con la salida del publicador."""
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


# --- 1. Simular no toca la red ------------------------------------------------
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=False)
chequear("simular: cero pedidos a la red", len(meta.pedidos) == 0)
chequear("simular: no escribe la memoria de publicados", not PUB.LEDGER.exists())
chequear("simular: la pieza no apta queda salteada con motivo",
         [s["orden"] for s in inf["salteadas"]] == [3] and "no apta" in inf["salteadas"][0]["motivo"])
chequear("simular: Instagram se anuncia como reel de prueba automatico",
         inf["piezas"][0]["instagram"]["prueba"] == {"graduation_strategy": "SS_PERFORMANCE"})
shutil.rmtree(base)

# --- 2. Publicar: el camino feliz ---------------------------------------------
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
estados = [(f["instagram"]["estado"], f["facebook"]["estado"]) for f in inf["piezas"]]
chequear("publicar: las dos piezas aptas salen en las dos redes", estados == [("ok", "ok")] * 2)
c = meta.contenedores[0]
chequear("Instagram: es un reel", c.get("media_type") == "REELS")
chequear("Instagram: sale como reel de PRUEBA con graduacion automatica",
         json.loads(c.get("trial_params", "{}")) == {"graduation_strategy": "SS_PERFORMANCE"})
chequear("Instagram: le pasa la URL publica del video en GitHub",
         c.get("video_url", "").startswith("https://github.com/dlcchivilcoy/policiales-bsas/releases/download/"))
chequear("Instagram: el nombre del video lleva la tanda (no se pisan entre pasadas)",
         c.get("video_url", "").endswith("/2026-09-26_1000_01_reel.mp4"))
f = meta.fb_finish[0]
chequear("Facebook: reel publicado normal (video_state PUBLISHED)", f.get("video_state") == "PUBLISHED")
chequear("Facebook: sin nada de reel de prueba", not any("trial" in k for k in f))
chequear("Facebook: lleva el texto del posteo", f.get("description", "").startswith("Texto del posteo 1"))
chequear("ningun token viaja en una URL (Meta, GitHub ni YouTube)",
         not any(t in str(r.url) for r in meta.pedidos for t in TODOS_LOS_SECRETOS))
yt = meta.yt_inicios[0]
chequear("YouTube: las dos piezas suben como Short",
         [f["youtube"]["estado"] for f in inf["piezas"]] == ["ok", "ok"] and len(meta.yt_videos) == 2)
chequear("YouTube: publico, categoria Noticias, no es para chicos",
         yt["status"]["privacyStatus"] == "public" and yt["snippet"]["categoryId"] == "25"
         and yt["status"]["selfDeclaredMadeForKids"] is False)
chequear("YouTube: el titulo lleva el pueblo bien escrito", yt["snippet"]["title"] == "Titular 1 | Junín")
chequear("YouTube: la descripcion lleva #Shorts", "#Shorts" in yt["snippet"]["description"])
chequear("YouTube: se verifico el canal ANTES de subir",
         any(r.url.path == "/youtube/v3/channels" for r in meta.pedidos))
chequear("la pieza no apta no se publico", not any("/3" in str(r.url) for r in meta.pedidos)
         and len(meta.contenedores) == 2)
h1, h2 = (datetime.fromisoformat(f["hora"]) for f in inf["piezas"])
chequear("5 minutos entre posteos aunque las dos vinieran agendadas a la misma hora",
         h2 - h1 >= timedelta(minutes=5))
led = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
chequear("la memoria anota cada red de cada nota",
         led["https://medio.test/1"]["instagram"]["estado"] == "ok"
         and led["https://medio.test/2"]["facebook"]["estado"] == "ok")
chequear("el lote queda marcado como publicado",
         json.loads((carpeta / "_lote.json").read_text(encoding="utf-8"))["publicado"] is True)

# --- 3. Correrlo de nuevo no repite nada --------------------------------------
antes = len(meta.pedidos)
inf2 = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("segunda pasada sobre la misma tanda: cero pedidos a Meta", len(meta.pedidos) == antes)
chequear("segunda pasada: las dos figuran como ya publicadas",
         all(f.get("resultado") == "ya estaba publicada" for f in inf2["piezas"]))
shutil.rmtree(base)

# --- 4. El 500 mentiroso de Instagram -----------------------------------------
m = Meta(ig_publicar=[(500, {"error": {"message": "An unknown error", "is_transient": True, "code": 2}})],
         ig_estados=["FINISHED", "PUBLICAR_YA"])
base, carpeta, reloj, meta = preparar(m)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("500 transitorio pero el contenedor dice PUBLISHED: se da por publicado",
         inf["piezas"][0]["instagram"]["estado"] == "ok")
chequear("...y NO se reintenta el media_publish (no se duplica)", meta.publicar_llamadas == 2)
# (2 = uno por pieza: la primera "fallo" una vez y no se repitio; la segunda salio de una)
shutil.rmtree(base)

# --- 5. Contenedor en ERROR: se crea uno nuevo --------------------------------
m = Meta(ig_estados=["ERROR", "FINISHED"])
base, carpeta, reloj, meta = preparar(m)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("contenedor en ERROR: se crea uno NUEVO y sale",
         inf["piezas"][0]["instagram"]["estado"] == "ok" and len(meta.contenedores) == 3)
shutil.rmtree(base)

# --- 6. Una red que falla no tumba a la otra ----------------------------------
m = Meta(fb_inicio=403)
base, carpeta, reloj, meta = preparar(m)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
p0 = inf["piezas"][0]
chequear("Facebook falla e Instagram y YouTube salen igual",
         p0["instagram"]["estado"] == "ok" and p0["facebook"]["estado"] == "fallo"
         and p0["youtube"]["estado"] == "ok")
aviso = base / "informe_publicacion.md"
chequear("la falla queda escrita para el issue de aviso",
         aviso.exists() and "facebook" in aviso.read_text(encoding="utf-8"))
chequear("el aviso no lleva ningun token",
         not any(t in aviso.read_text(encoding="utf-8") for t in TODOS_LOS_SECRETOS))
antes = len(meta.contenedores)
m.fb_inicio = 200
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("reintento manual: Facebook sale y Instagram NO se repite",
         inf["piezas"][0].get("facebook", {}).get("estado") == "ok" and len(meta.contenedores) == antes
         and "instagram" not in inf["piezas"][0])
shutil.rmtree(base)

# --- 7. Error real de Instagram: fallo, no "sin confirmar" --------------------
m = Meta(ig_publicar=[(400, {"error": {"message": "Invalid parameter", "code": 100}})])
base, carpeta, reloj, meta = preparar(m)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("error 400 de Instagram con el contenedor sin publicar: FALLO y un solo intento",
         inf["piezas"][0]["instagram"]["estado"] == "fallo" and meta.publicar_llamadas == 2)
shutil.rmtree(base)

# --- 8. Credenciales y memoria rota --------------------------------------------
guardado = os.environ.pop("INSTAGRAM_ACCESS_TOKEN")
chequear("sin token de Instagram: se frena ANTES de publicar",
         PUB.faltantes(PUB.REDES, publicar=True) == ["INSTAGRAM_ACCESS_TOKEN"])
chequear("simulando no hacen falta credenciales", PUB.faltantes(PUB.REDES, publicar=False) == [])
os.environ["INSTAGRAM_ACCESS_TOKEN"] = guardado

base, carpeta, reloj, meta = preparar()
PUB.LEDGER.parent.mkdir(parents=True)
PUB.LEDGER.write_text("{roto", encoding="utf-8")
try:
    silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
    chequear("memoria rota: no se publica nada", False)
except SystemExit:
    chequear("memoria rota: no se publica nada", len(meta.pedidos) == 0)
shutil.rmtree(base)

chequear("un token dentro de un mensaje de error se tapa",
         "fb_token_secreto" not in PUB._tapar("https://x?access_token=fb_token_secreto_123456"))
chequear("los secretos de YouTube tambien se tapan",
         "yt_refresco" not in PUB._tapar("refresh_token=yt_refresco_secreto_123456"))

# --- 9. YouTube: tope diario ----------------------------------------------------
chequear("sin racion para policiales: el tope por defecto deja subir un dia enorme (50+)",
         PUB.tope_youtube() >= 50)
chequear("...pero le deja al bot al menos 15 de las 100 subidas del proyecto",
         PUB.tope_youtube() <= 85)
os.environ["YT_SHORTS_POR_DIA"] = "1"
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("tope 1 por dia: la primera sube y la segunda queda por cupo",
         [f["youtube"]["estado"] for f in inf["piezas"]] == ["ok", "cupo"] and len(meta.yt_videos) == 1)
chequear("quedarse sin lugar en YouTube NO es una falla (no abre issue)",
         not (base / "informe_publicacion.md").exists())
chequear("la pieza sin lugar en YouTube sale igual en Instagram y Facebook",
         inf["piezas"][1]["instagram"]["estado"] == "ok" and inf["piezas"][1]["facebook"]["estado"] == "ok")
antes = len(meta.pedidos)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("otra pasada el mismo dia: el tope cuenta lo ya subido y no sube nada",
         len(meta.pedidos) == antes and inf["piezas"][1].get("youtube", {}).get("estado") == "cupo")
reloj.t += timedelta(days=1)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("al dia siguiente el tope se renueva y sube la que habia quedado",
         inf["piezas"][1].get("youtube", {}).get("estado") == "ok" and len(meta.yt_videos) == 2)
os.environ.pop("YT_SHORTS_POR_DIA")
shutil.rmtree(base)

# --- 10. YouTube: cupo agotado ----------------------------------------------------
base, carpeta, reloj, meta = preparar(Meta(yt_sin_cupo=True))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("cupo agotado: la primera falla avisando el cupo",
         inf["piezas"][0]["youtube"]["estado"] == "fallo" and "cupo" in inf["piezas"][0]["youtube"]["detalle"])
chequear("...y no se insiste con la segunda en la misma pasada",
         inf["piezas"][1]["youtube"]["estado"] == "cupo"
         and sum(1 for r in meta.pedidos if r.url.path == "/upload/youtube/v3/videos") == 1)
shutil.rmtree(base)

# --- 11. YouTube: token de otro canal ----------------------------------------------
base, carpeta, reloj, meta = preparar(Meta(yt_canal="UCDIARIO"))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("token de OTRO canal: no se sube nada a YouTube",
         not meta.yt_inicios and all(f["youtube"]["estado"] == "fallo" for f in inf["piezas"]))
chequear("...e Instagram y Facebook salen igual",
         all(f["instagram"]["estado"] == "ok" and f["facebook"]["estado"] == "ok" for f in inf["piezas"]))
shutil.rmtree(base)

# --- 12. YouTube: el archivo llega pero se pierde la respuesta ------------------------
base, carpeta, reloj, meta = preparar(Meta(yt_cortes=1))
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("subida cortada que SI llego: se pregunta, se da por subida y no se duplica",
         inf["piezas"][0]["youtube"]["estado"] == "ok"
         and sum(1 for r in meta.pedidos if r.method == "PUT" and not r.headers.get("content-range")) == 2)
shutil.rmtree(base)

largo = PUB.metadatos_youtube({"localidad": "junin", "descripcion_tiktok": "a <b> c",
                               "guion": {"titular": "x" * 150}})["snippet"]
chequear("titulo de YouTube: nunca mas de 100 caracteres", len(largo["title"]) <= 100)
chequear("sin < ni > (YouTube rechaza el video entero)", "<" not in largo["description"]
         and ">" not in largo["description"])

# --- 14. Instagram: sin tope propio, pero con lugar para el bot -------------------
chequear("Instagram: la reserva para el bot por defecto es de 25 de los 100",
         PUB.reserva_instagram() == 25)
base, carpeta, reloj, meta = preparar(Meta(ig_cupo=(74, 100)))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("Instagram con 74 de 100 usados: todavia hay lugar y sale",
         inf["piezas"][0]["instagram"]["estado"] == "ok")
chequear("se lee el cupo antes de publicar, con el token en el encabezado",
         any(r.url.path.endswith("/content_publishing_limit")
             and r.headers.get("authorization") == "Bearer ig_token_secreto_123456" for r in meta.pedidos))
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(ig_cupo=(75, 100)))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("Instagram con 75 de 100 usados: no se publica ahi (lo que queda es del bot)",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["cupo", "cupo"]
         and not meta.contenedores)
chequear("...y el motivo lo dice",
         "bot" in inf["piezas"][0]["instagram"]["detalle"])
chequear("...Facebook y YouTube salen igual",
         all(f["facebook"]["estado"] == "ok" and f["youtube"]["estado"] == "ok" for f in inf["piezas"]))
chequear("...no es una falla: no abre issue",
         not (base / "informe_publicacion.md").exists())
led = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
chequear("...y no se anota en la memoria como publicado en Instagram",
         "instagram" not in led["https://medio.test/1"])
meta.ig_cupo = (10, 100)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("cuando se libera lugar, otra pasada sobre la misma tanda la sube (solo a Instagram)",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["ok", "ok"]
         and len(meta.fb_finish) == 2 and len(meta.yt_videos) == 2)
shutil.rmtree(base)

os.environ["IG_RESERVA_BOT"] = "0"
base, carpeta, reloj, meta = preparar(Meta(ig_cupo=(99, 100)))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("la reserva se cambia con IG_RESERVA_BOT (0 = hasta el ultimo lugar)",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["ok", "ok"])
os.environ.pop("IG_RESERVA_BOT")
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(ig_cupo=None))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("si el cupo de Instagram no se puede leer, se publica igual",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["ok", "ok"])
shutil.rmtree(base)

# --- 15. Instagram: tope de reels de PRUEBA (no documentado; visto el 27/09) ----------
base, carpeta, reloj, meta = preparar(Meta(ig_tope_prueba=1))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("tope de prueba: la primera sale y la segunda queda por CUPO, no por falla",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["ok", "cupo"])
chequear("...Facebook y YouTube salen igual",
         all(f["facebook"]["estado"] == "ok" and f["youtube"]["estado"] == "ok" for f in inf["piezas"]))
chequear("...no abre issue (no es una falla del sistema)",
         not (base / "informe_publicacion.md").exists())
led = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
chequear("...y no queda anotada en la memoria para Instagram",
         "instagram" not in led["https://medio.test/2"])
chequear("el mensaje en inglés también se reconoce",
         PUB._es_tope_de_prueba("You have reached the maximum number of trial reels"))
chequear("un error cualquiera de Instagram NO se toma por tope",
         not PUB._es_tope_de_prueba("Instagram: publicar: HTTP 400 — Invalid parameter"))
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(ig_tope_prueba=0))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("tope desde la primera: no se insiste con la segunda en la misma pasada",
         meta.publicar_llamadas == 1 and inf["piezas"][1]["instagram"]["estado"] == "cupo")
shutil.rmtree(base)

# --- 16. La NOTA de la web y el link en Facebook (27/09) ------------------------------
os.environ.update({"NOTAS_WEB": "1", "WIX_API_KEY": "wix_clave_secreta_123456",
                   "WIX_SITE_ID": "SITIO", "WIX_MEMBER_ID": "MIEMBRO"})
TODOS_LOS_SECRETOS.append("wix_clave_secreta_123456")
from reels import web as WEBM
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
w = inf["piezas"][0].get("web", {})
chequear("web: cada pieza tiene su nota publicada",
         [f.get("web", {}).get("estado") for f in inf["piezas"]] == ["ok", "ok"] and meta.wix_publicados == 2)
chequear("web: el link es el corto de la web, con la Ñ",
         w.get("url", "").startswith("https://www.diariolacampaña.com.ar/n/junin-el-hecho-numero-1-"))
b1 = meta.wix_borradores[0]["draftPost"]
chequear("web: va SOLO a la sección Región (nunca a Inicio, la portada)", b1["categoryIds"] == [WEBM.REGION_ID])
chequear("web: no se destaca", b1["featured"] is False)
tipos = [n["type"] for n in b1["richContent"]["nodes"]]
chequear("web: foto, el Short de YouTube y el texto",
         tipos[:2] == ["IMAGE", "VIDEO"] and tipos.count("PARAGRAPH") == 3)
chequear("web: el Short va como watch?v= (lo único que muestra la web)",
         b1["richContent"]["nodes"][1]["videoData"]["video"]["src"]["url"] == "https://www.youtube.com/watch?v=YT1")
fuente = b1["richContent"]["nodes"][-1]["nodes"]
chequear("web: cierra con la fuente y el link a la nota original",
         "Medio Test" in fuente[0]["textData"]["text"]
         and fuente[1]["textData"]["decorations"][0]["linkData"]["link"]["url"] == "https://medio.test/1")
chequear("Facebook: el posteo lleva el link a la nota",
         meta.fb_finish[0]["description"].count("📲 Nota completa: https://www.diariolacampaña.com.ar/n/") == 1)
chequear("Instagram y YouTube NO cambian su texto (el link es para Facebook)",
         "Nota completa" not in meta.contenedores[0].get("caption", "")
         and "Nota completa" not in meta.yt_inicios[0]["snippet"]["description"])
orden_pedidos = [r.url.path for r in meta.pedidos]
i_yt = next(i for i, x in enumerate(orden_pedidos) if x == "/upload/youtube/v3/videos")
i_web = orden_pedidos.index("/blog/v3/draft-posts")
i_fb = orden_pedidos.index("/v26.0/PAGINA/video_reels")
chequear("orden: YouTube, después la nota, después Facebook", i_yt < i_web < i_fb)
chequear("la clave de Wix nunca en una URL", not any("wix_clave_secreta" in str(r.url) for r in meta.pedidos))
antes = meta.wix_publicados
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("web: correrlo de nuevo no duplica la nota", meta.wix_publicados == antes)
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(wix_falla="borrador"))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
p0 = inf["piezas"][0]
chequear("web caída: el reel sale igual en Facebook, con el link general",
         p0["web"]["estado"] == "fallo" and p0["facebook"]["estado"] == "ok"
         and "Nota completa" not in meta.fb_finish[0]["description"])
chequear("web caída: queda escrito para el issue",
         "web" in (base / "informe_publicacion.md").read_text(encoding="utf-8"))
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(wix_existe="junin-el-hecho-numero-1-abc123"))
inf = silencio(PUB.publicar_lote, carpeta, ("facebook",), publicar=True)
chequear("web: si la nota ya existía (corte a mitad), se usa esa y no se crea otra",
         not meta.wix_borradores and "junin-el-hecho-numero-1-abc123" in inf["piezas"][0]["web"]["url"])
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(wix_foto_falla=True))
inf = silencio(PUB.publicar_lote, carpeta, ("facebook",), publicar=True)
chequear("web: sin foto importable la nota sale igual, sin portada",
         inf["piezas"][0]["web"]["estado"] == "ok" and "media" not in meta.wix_borradores[0]["draftPost"])
shutil.rmtree(base)

guardada = os.environ.pop("WIX_API_KEY")
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, ("facebook",), publicar=True)
chequear("sin clave de Wix: no frena, Facebook sale con el link general",
         inf["piezas"][0]["facebook"]["estado"] == "ok" and "web" not in inf["piezas"][0])
os.environ["WIX_API_KEY"] = guardada
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar()
silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=False)
chequear("simulando con la web prendida: cero pedidos", len(meta.pedidos) == 0)
shutil.rmtree(base)
os.environ["NOTAS_WEB"] = "0"

chequear("el link reemplaza la línea «📲 Más noticias» si estaba",
         PUB.texto_del_posteo({"descripcion_tiktok": "Texto\n\n📲 Más noticias de Junín en www.x\n\n#A"},
                              "facebook", "https://l") == "Texto\n\n📲 Nota completa: https://l\n\n#A")


# --- 17. Instagram de PRUEBA: los más virales de cada pasada (27/09) --------------------
def preparar_virales(virales, meta=None, titulares=None):
    base, carpeta, reloj, meta = preparar(meta)
    piezas = []
    for i, v in enumerate(virales, 1):
        pz = pieza(i, "junin")
        pz["viral"] = v
        if titulares:
            pz["guion"] = {"titular": titulares[i - 1][0], "bajada": titulares[i - 1][1]}
        piezas.append(pz)
        (carpeta / f"{i:02d}_reel.mp4").write_bytes(b"\x00" * 4096)
    (carpeta / "_lote.json").write_text(json.dumps({"publicado": False, "piezas": piezas}), encoding="utf-8")
    return base, carpeta, reloj, meta


chequear("por defecto van 2 por pasada", PUB.ig_por_pasada() == 2)
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
ig = [f["instagram"]["estado"] for f in inf["piezas"]]
chequear("van las 2 más virales (9 y 7); la de 3 no", ig == ["omitida", "ok", "ok"] and len(meta.contenedores) == 2)
chequear("...con el motivo a la vista", "virales" in inf["piezas"][0]["instagram"]["detalle"])
chequear("...y Facebook y YouTube llevan las tres",
         all(f["facebook"]["estado"] == "ok" and f["youtube"]["estado"] == "ok" for f in inf["piezas"]))
chequear("...no es una falla: no abre issue", not (base / "informe_publicacion.md").exists())
shutil.rmtree(base)

os.environ["IG_PRUEBA_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("IG_PRUEBA_POR_PASADA=1: solo la más viral",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["omitida", "ok", "omitida"])
os.environ.pop("IG_PRUEBA_POR_PASADA")
shutil.rmtree(base)

hechos = [("Detuvieron a dos hombres por el robo de una camioneta en el barrio Centro",
           "La policía recuperó la camioneta sustraída y secuestró herramientas en la vivienda"),
          ("Choque entre un auto y una moto en la Ruta 7 dejó un herido grave",
           "El motociclista fue trasladado al hospital con fracturas tras el impacto"),
          ("Incendio destruyó un galpón de maquinaria agrícola en la zona rural",
           "Los bomberos trabajaron durante horas para controlar las llamas")]
ya_en_ig = [{"caption": "La policía detuvo a dos hombres por el robo de una camioneta en el barrio Centro "
                        "y recuperó la camioneta sustraída tras secuestrar herramientas en la vivienda.\n\n"
                        "📰 Fuente: Otro\n\n#Junin",
             "timestamp": "2026-09-26T08:00:00+0000"}]
base, carpeta, reloj, meta = preparar_virales([9, 8, 7], Meta(ig_recientes=ya_en_ig), hechos)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
ig = inf["piezas"]
chequear("el hecho que YA está en el Instagram de la cuenta no se repite",
         ig[0]["instagram"]["estado"] == "omitida" and "ya está en el Instagram" in ig[0]["instagram"]["detalle"])
chequear("...y en su lugar van las dos siguientes", [f["instagram"]["estado"] for f in ig[1:]] == ["ok", "ok"])
shutil.rmtree(base)

viejo = [dict(ya_en_ig[0], timestamp="2026-09-20T08:00:00+0000")]
base, carpeta, reloj, meta = preparar_virales([9, 8, 7], Meta(ig_recientes=viejo), hechos)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("un posteo de hace más de 3 días no cuenta", inf["piezas"][0]["instagram"]["estado"] == "ok")
shutil.rmtree(base)

# --- 13. TikTok apagado ------------------------------------------------------------
chequear("TikTok no esta entre las redes", "tiktok" not in PUB.REDES and PUB.TIKTOK_ACTIVO is False)
base, carpeta, reloj, meta = preparar()
try:
    silencio(PUB.publicar_lote, carpeta, ("instagram", "tiktok"), publicar=True)
    chequear("pedir TikTok frena TODO, ni borradores", False)
except ValueError:
    chequear("pedir TikTok frena TODO, ni borradores", len(meta.pedidos) == 0)
chequear("ningun pedido va a TikTok en ningun caso",
         not any("tiktok" in r.url.host for r in meta.pedidos))
shutil.rmtree(base)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
