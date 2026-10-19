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

# Las pruebas de la fila y del cupo usan la grilla completa de pasadas de antes (09:05 a 23:35): prueban
# la mecánica, no los horarios. Los horarios reales viven en reels/cupo.py (19/10/2026: 18:05 y 23:35).
from reels import cupo as _CUPO  # noqa: E402
_CUPO.PASADAS_AR = ((9, 5), (12, 5), (15, 5), (18, 5), (21, 5), (23, 35))
PUB.PASADAS_AR = _CUPO.PASADAS_AR

# La hora argentina fija en una pasada «de 2» (18:05): los reels de prueba por pasada
# dependen del horario, y las pruebas no pueden depender de cuándo se corren.
from datetime import timezone as _tz
_AR = _tz(timedelta(hours=-3))
PUB._hora_ar = lambda: datetime(2026, 9, 26, 18, 10, tzinfo=_AR)
# El relevamiento (12/10/2026) mira estado/publicados.json y le pregunta a la IA: en las pruebas,
# ni lo uno ni lo otro (cada prueba arma su propia memoria).
PUB.RV.cargar_publicados = lambda: {}
# La fila de 15 minutos con nacionales (18/10/2026) se prueba aparte, al final: las pruebas de antes
# son del espaciado propio de policiales (30 minutos), que vuelve con FILA_15=0.
os.environ["FILA_15"] = "0"


def _sin_ia(*a, **k):
    raise RuntimeError("sin IA en las pruebas")


PUB.RV._preguntar_ia = _sin_ia
# El cupo global de 3 hechos por pasada (17/10/2026) tiene su propia sección al final (la 30); las
# pruebas anteriores son de otras reglas y se escribieron con 6 lugares por pasada.
os.environ["MAX_POLICE_REELS_PER_PASS"] = "6"
# Lo mismo el intercalado dentro de cada cuenta (17/10/2026): sección 31.
os.environ["INTERCALADO"] = "0"

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
os.environ["YT_SIN_PLACA"] = "0"       # el corte de la placa se prueba aparte (sección 22)
# Las pruebas de CÓMO se elige ponen más piezas que el tope de Facebook: se fija en 2 (el
# tope de antes) para que siga habiendo que elegir. El valor por defecto (5) se prueba en 18.
os.environ["FB_POR_PASADA"] = "2"
os.environ.pop("IG_PRUEBA_POR_PASADA", None)
# Instagram, igual: el tope de antes (2) para que haya que elegir; el de hoy (5) se prueba aparte.
os.environ["IG_POR_PASADA"] = "2"
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
                 wix_falla=None, wix_existe="", wix_foto_falla=False, fb_recientes=None,
                 fb_lista_falla=False, yt_miniatura=200, yt_recientes=None, fb_link=200):
        self.fb_link = fb_link            # status del POST /feed (el enlace del Short)
        self.fb_links = []                # el cuerpo de cada enlace publicado en la página
        self.yt_recientes = list(yt_recientes or [])   # (publishedAt, título, descripción) del canal
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
        self.fb_recientes = list(fb_recientes or [])   # reels que ya tiene la página
        self.fb_lista_falla = fb_lista_falla
        self.fb_posteos = []              # lo último de la página (intercalado, 17/10/2026)
        self.yt_miniatura = yt_miniatura  # status de thumbnails.set
        self.yt_miniaturas = []           # (videoId, tipo, bytes) de cada miniatura puesta
        self.yt_estado = {}               # id → uploadStatus que contesta videos.list («borrado» = no existe)
        self.yt_cambios = []              # cada videos.update (cambio de descripción)

    def _youtube(self, req, host, ruta, m):
        if host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": YT_ACCESO, "expires_in": 3599})
        if ruta == "/youtube/v3/channels":
            return httpx.Response(200, json={"items": [{"id": self.yt_canal, "contentDetails": {
                "relatedPlaylists": {"uploads": "UUSUBIDOS"}}}]})
        if ruta == "/youtube/v3/playlistItems":
            return httpx.Response(200, json={"items": [
                {"snippet": {"publishedAt": c, "title": t, "description": d}}
                for c, t, d in self.yt_recientes]})
        if ruta == "/youtube/v3/videos" and m == "GET":       # verificar_shorts (17/10/2026)
            ids = req.url.params.get("id", "").split(",")
            return httpx.Response(200, json={"items": [
                {"id": i, "status": {"uploadStatus": self.yt_estado.get(i, "processed"), "privacyStatus": "public",
                                     **({"rejectionReason": "duplicate"} if self.yt_estado.get(i) == "rejected" else {})}}
                for i in ids if i in self.yt_videos.values() and self.yt_estado.get(i) != "borrado"]})
        if ruta == "/youtube/v3/videos" and m == "PUT":
            self.yt_cambios.append(json.loads(req.content))
            return httpx.Response(200, json={"id": "x"})
        if ruta == "/upload/youtube/v3/thumbnails/set" and m == "POST":
            if self.yt_miniatura >= 400:
                return httpx.Response(self.yt_miniatura, json={"error": {"code": self.yt_miniatura,
                    "message": "no", "errors": [{"reason": "forbidden"}]}})
            self.yt_miniaturas.append((req.url.params["videoId"], req.headers.get("content-type"),
                                       len(req.content)))
            return httpx.Response(200, json={"items": [{"default": {"url": "x"}}]})
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
            if ruta == "/v26.0/PAGINA/published_posts" and m == "GET":
                return httpx.Response(200, json={"data": self.fb_posteos})
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
            if ruta == "/v26.0/PAGINA/feed":
                if self.fb_link >= 400:
                    return httpx.Response(self.fb_link, json={"error": {"message": "no se pudo", "code": 1}})
                self.fb_links.append(uno)
                return httpx.Response(200, json={"id": f"PAGINA_{len(self.fb_links)}"})
            if ruta == "/v26.0/PAGINA/video_reels" and m == "GET":
                if self.fb_lista_falla:
                    return httpx.Response(400, json={"error": {"message": "no"}})
                return httpx.Response(200, json={"data": self.fb_recientes})
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
    piezas = [pieza(1, "junin"), pieza(2, "bragado"), pieza(3, "lobos", apta=False)]
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
    PUB.DIST.BUZON = base / "estado" / "buzon_distribuidor.json"   # nunca el buzón real
    PUB.CUPO.ARCHIVO = base / "estado" / "cupo_pasadas.json"      # ni el cupo real de la pasada
    from reels import auditoria as _AU
    _AU.ARCHIVO = base / "estado" / "auditoria.json"              # ni la auditoría real
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
chequear("simular: Instagram ya no se anuncia como reel de prueba (10/10)",
         inf["piezas"][0]["instagram"]["prueba"] is None)
shutil.rmtree(base)

# --- 2. Publicar: el camino feliz ---------------------------------------------
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
estados = [(f["instagram"]["estado"], f["facebook"]["estado"]) for f in inf["piezas"]]
chequear("publicar: las dos piezas aptas salen en las dos redes", estados == [("ok", "ok")] * 2)
c = meta.contenedores[0]
chequear("Instagram: es un reel", c.get("media_type") == "REELS")
chequear("Instagram: sale como reel NORMAL al feed (sin trial_params, con share_to_feed)",
         "trial_params" not in c and c.get("share_to_feed") == "true")
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
chequear("segunda pasada sobre la misma tanda: cero pedidos a Meta (a YouTube, solo la consulta de "
         "si terminó de procesar los Shorts)",
         [r.url.path for r in meta.pedidos[antes:] if r.url.host.endswith("googleapis.com")
          and r.url.path not in ("/token", "/youtube/v3/channels")] == ["/youtube/v3/videos"]
         and not [r for r in meta.pedidos[antes:] if not r.url.host.endswith("googleapis.com")])
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
chequear("otra pasada el mismo dia: el tope cuenta lo ya subido y no sube nada (solo consulta si el "
         "Short anterior terminó de procesarse)",
         {r.url.path for r in meta.pedidos[antes:]} <= {"/token", "/youtube/v3/channels", "/youtube/v3/videos"}
         and not any(r.method != "GET" and r.url.path != "/token" for r in meta.pedidos[antes:])
         and inf["piezas"][1].get("youtube", {}).get("estado") == "cupo")
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
cruzado = PUB.metadatos_youtube({"localidad": "9 de julio", "localidad_hecho": "Bragado",
                                 "descripcion_tiktok": "t", "guion": {"titular": "Granizo en la ciudad"}})
chequear("titulo de YouTube con el pueblo del HECHO, no el del medio",
         cruzado["snippet"]["title"] == "Granizo en la ciudad | Bragado"
         and "9 de Julio" not in cruzado["snippet"]["tags"])

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
         tipos[:2] == ["IMAGE", "VIDEO"] and tipos.count("PARAGRAPH") == 2)
chequear("web: la foto lleva texto alternativo (el titular, 17/10/2026)",
         b1["richContent"]["nodes"][0]["type"] == "IMAGE"
         and b1["richContent"]["nodes"][0]["imageData"]["altText"] == b1["title"][:125])
chequear("web: el Short va como watch?v= (lo único que muestra la web)",
         b1["richContent"]["nodes"][1]["videoData"]["video"]["src"]["url"] == "https://www.youtube.com/watch?v=YT1")
cuerpo_web = json.dumps(b1["richContent"], ensure_ascii=False)
chequear("web: SIN la fuente ni el link a la nota original (pedido del editor, 03/10)",
         "Medio Test" not in cuerpo_web and "Fuente" not in cuerpo_web
         and "medio.test" not in cuerpo_web)
chequear("Facebook: el posteo lleva el link a la nota",
         meta.fb_finish[0]["description"].count("📲 Nota completa: https://www.diariolacampaña.com.ar/n/") == 1)
chequear("Instagram NO cambia su texto (no hay links en Instagram)",
         "Nota completa" not in meta.contenedores[0].get("caption", ""))
chequear("el Short lleva el link a SU nota (17/10/2026, PDF §29)",
         meta.yt_inicios[0]["snippet"]["description"].count("📲 Nota completa: https://www.diariolacampaña.com.ar/n/") == 1
         and meta.yt_inicios[0]["snippet"]["description"].split("📲 Nota completa: ")[1].split()[0]
         in meta.fb_finish[0]["description"])
orden_pedidos = [r.url.path for r in meta.pedidos]
i_yt = next(i for i, x in enumerate(orden_pedidos) if x == "/upload/youtube/v3/videos")
i_web = orden_pedidos.index("/blog/v3/draft-posts")
i_fb = next(i for i, r in enumerate(meta.pedidos) if r.url.path == "/v26.0/PAGINA/video_reels" and r.method == "POST")
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


os.environ.pop("IG_POR_PASADA")
chequear("Instagram: 5 reels por pasada por defecto (10/10)", PUB.ig_por_pasada() == 5)
PUB._hora_ar = lambda: datetime(2026, 9, 26, 9, 10, tzinfo=_AR)
chequear("...a cualquier hora (ya no depende del horario)", PUB.ig_por_pasada() == 5)
os.environ["IG_PRUEBA_POR_PASADA"] = "3"
chequear("la variable vieja IG_PRUEBA_POR_PASADA sigue pisando el tope", PUB.ig_por_pasada() == 3)
del os.environ["IG_PRUEBA_POR_PASADA"]
os.environ["IG_POR_PASADA"] = "4"
chequear("la variable IG_POR_PASADA pisa el tope", PUB.ig_por_pasada() == 4)
os.environ.pop("IG_POR_PASADA")
base, carpeta, reloj, meta = preparar_virales([3, 1, 2, 8, 5, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
ig = [f["instagram"]["estado"] for f in inf["piezas"]]
chequear("con 7 piezas salen las 5 MÁS VIRALES (9, 8, 7, 5, 3); la de 2 no va a Instagram y la de 1 "
         "no entra en la pasada (a las 9:10 hay 6 lugares de 30 minutos hasta las 12:05)",
         ig == ["ok", "omitida", "ok", "ok", "ok", "ok"] and len(meta.contenedores) == 5
         and any("no entra en la pasada" in s_["motivo"] for s_ in inf["salteadas"]))
horas = [f["hora"] for f in inf["piezas"] if f.get("hora")]
chequear("un reel cada 30 minutos (13/10/2026)",
         all((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() >= 30 * 60
             for a, b in zip(horas, horas[1:])))
shutil.rmtree(base)
chequear("lugares por pasada: 12:20 → 6 (hasta las 14:55), 21:20 → 5 (hasta las 23:25), 23:50 → 6 (tope)",
         PUB.lugares_en_la_pasada(datetime(2026, 10, 13, 12, 20, tzinfo=_AR)) == 6
         and PUB.lugares_en_la_pasada(datetime(2026, 10, 13, 21, 20, tzinfo=_AR)) == 5
         and PUB.lugares_en_la_pasada(datetime(2026, 10, 13, 23, 50, tzinfo=_AR)) == 6)
os.environ["IG_POR_PASADA"] = "2"
PUB._hora_ar = lambda: datetime(2026, 9, 26, 18, 10, tzinfo=_AR)
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
ig = [f["instagram"]["estado"] for f in inf["piezas"]]
chequear("van las 2 más virales (9 y 7); la de 3 no", ig == ["omitida", "ok", "ok"] and len(meta.contenedores) == 2)
chequear("...con el motivo a la vista", "más virales" in inf["piezas"][0]["instagram"]["detalle"])
chequear("...YouTube lleva las tres; Facebook, las mismas 2 más virales",
         all(f["youtube"]["estado"] == "ok" for f in inf["piezas"])
         and [f["facebook"]["estado"] for f in inf["piezas"]] == ["omitida", "ok", "ok"])
chequear("...no es una falla: no abre issue", not (base / "informe_publicacion.md").exists())
shutil.rmtree(base)

os.environ["IG_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("IG_POR_PASADA=1: solo la más viral",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["omitida", "ok", "omitida"])
os.environ["IG_POR_PASADA"] = "2"
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


# --- 18. Facebook: 30 reels por día POR PÁGINA, compartidos con el bot (27/09) ----------
os.environ.pop("FB_POR_PASADA")
chequear("Facebook: 2 por pasada por defecto (03/10: se probó 5 y se volvió a 2)", PUB.fb_por_pasada() == 2)
base, carpeta, reloj, meta = preparar_virales([3, 9, 7, 5, 6, 8])
inf = silencio(PUB.publicar_lote, carpeta, ("facebook", "youtube"), publicar=True)
fb = [f["facebook"]["estado"] for f in inf["piezas"]]
chequear("...de 6 piezas, como reel van las 2 MÁS VIRALES (9 y 8)",
         fb == ["omitida", "ok", "omitida", "omitida", "omitida", "ok"] and len(meta.fb_finish) == 2)
chequear("...y el motivo de las otras lo dice", "más virales" in inf["piezas"][0]["facebook"]["detalle"])
links = [(f.get("fb_youtube") or {}).get("estado") for f in inf["piezas"]]
chequear("...las otras 4 van a la página como ENLACE del Short; las 2 del reel no se repiten",
         links == ["ok", None, "ok", "ok", "ok", None] and len(meta.fb_links) == 4)
chequear("...el enlace es el Short, y el texto: el título en una oración y el link a la nota",
         all(x["link"].startswith("https://youtube.com/shorts/") for x in meta.fb_links)
         and meta.fb_links[0]["message"].split("\n\n")[0].endswith(".")
         and meta.fb_links[0]["message"].count("\n\n") == 1)
shutil.rmtree(base)

os.environ.update({"NOTAS_WEB": "1"})
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, ("facebook", "youtube"), publicar=True)
chequear("enlace del Short: con la nota de la web, la segunda oración es su link",
         "📲 Leé la nota completa: https://www.diariolacampaña.com.ar/n/" in meta.fb_links[0]["message"])
shutil.rmtree(base)
os.environ["NOTAS_WEB"] = "0"

base, carpeta, reloj, meta = preparar_virales([3, 9, 7], Meta(fb_link=500))
inf = silencio(PUB.publicar_lote, carpeta, ("facebook", "youtube"), publicar=True)
chequear("enlace del Short que falla: queda anotado y no frena el resto",
         inf["piezas"][0]["fb_youtube"]["estado"] == "fallo"
         and all(f["youtube"]["estado"] == "ok" for f in inf["piezas"]))
shutil.rmtree(base)

os.environ["FB_YOUTUBE"] = "0"
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, ("facebook", "youtube"), publicar=True)
chequear("FB_YOUTUBE=0 lo apaga", not meta.fb_links and all("fb_youtube" not in f for f in inf["piezas"]))
os.environ.pop("FB_YOUTUBE")
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, ("facebook", "youtube"), publicar=False)
chequear("simulando: el enlace sale simulado y no se toca la página",
         [(f.get("fb_youtube") or {}).get("estado") for f in inf["piezas"]].count("simulado") == 1
         and not meta.fb_links)
shutil.rmtree(base)
os.environ["FB_POR_PASADA"] = "2"
os.environ["FB_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("FB_POR_PASADA=1: a Facebook solo la más viral",
         [f["facebook"]["estado"] for f in inf["piezas"]] == ["omitida", "ok", "omitida"] and len(meta.fb_finish) == 1)
os.environ["FB_POR_PASADA"] = "2"
shutil.rmtree(base)

llena = [{"created_time": "2026-09-26T0%d:%02d:00+0000" % (1 + i // 60, i % 60), "description": f"Reel del bot {i}"}
         for i in range(26)]
base, carpeta, reloj, meta = preparar(Meta(fb_recientes=llena))
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("página con 26 reels en 24 h: policiales NO publica en Facebook (lugar del bot)",
         [f["facebook"]["estado"] for f in inf["piezas"]] == ["cupo", "cupo"] and not meta.fb_finish)
chequear("...Instagram y YouTube salen igual, y no es una falla",
         all(f["instagram"]["estado"] == "ok" and f["youtube"]["estado"] == "ok" for f in inf["piezas"])
         and not (base / "informe_publicacion.md").exists())
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(fb_recientes=llena[:25]))
inf = silencio(PUB.publicar_lote, carpeta, ("facebook",), publicar=True)
chequear("con 25 todavía hay lugar para una", inf["piezas"][0]["facebook"]["estado"] == "ok")
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(fb_lista_falla=True))
inf = silencio(PUB.publicar_lote, carpeta, ("facebook",), publicar=True)
chequear("si no se puede leer la página, Facebook sale igual",
         [f["facebook"]["estado"] for f in inf["piezas"]] == ["ok", "ok"])
shutil.rmtree(base)

ya_en_fb = [{"created_time": "2026-09-26T08:00:00+0000",
             "description": ya_en_ig[0]["caption"]}]
base, carpeta, reloj, meta = preparar_virales([9, 8, 7], Meta(fb_recientes=ya_en_fb), hechos)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("el hecho que YA está en la página de Facebook no se repite ahí",
         inf["piezas"][0]["facebook"]["estado"] == "omitida"
         and "Facebook" in inf["piezas"][0]["facebook"]["detalle"]
         and [f["facebook"]["estado"] for f in inf["piezas"][1:]] == ["ok", "ok"])
shutil.rmtree(base)


# --- 19. Cercanía a Chivilcoy: a igual interés, las localidades cercanas primero (27/09) ---
def preparar_pueblos(pueblos_virales):
    base, carpeta, reloj, meta = preparar()
    piezas = []
    for i, (pueblo, v) in enumerate(pueblos_virales, 1):
        pz = pieza(i, pueblo)
        pz["viral"] = v
        piezas.append(pz)
        (carpeta / f"{i:02d}_reel.mp4").write_bytes(b"\x00" * 4096)
    (carpeta / "_lote.json").write_text(json.dumps({"publicado": False, "piezas": piezas}), encoding="utf-8")
    return base, carpeta, reloj, meta


base, carpeta, reloj, meta = preparar_pueblos([("junin", 9), ("lobos", 8), ("chivilcoy", 7), ("alberti", 5)])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("Chivilcoy (viral 7, +3) le gana el lugar a Lobos (viral 8, +1) en Instagram y Facebook",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["ok", "omitida", "ok", "omitida"]
         and [f["facebook"]["estado"] for f in inf["piezas"]] == ["ok", "omitida", "ok", "omitida"])
chequear("...el motivo de la cercana que no entró lo dice",
         "+2 por cercanía" in inf["piezas"][3]["instagram"]["detalle"]
         and "+1 por cercanía" in inf["piezas"][1]["instagram"]["detalle"])
chequear("...y YouTube sigue llevando todas", all(f["youtube"]["estado"] == "ok" for f in inf["piezas"]))
shutil.rmtree(base)

os.environ["IG_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_pueblos([("bragado", 6), ("junin", 9)])
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("un hecho lejano mucho más viral (9) le sigue ganando a uno cercano de 6",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["omitida", "ok"])
os.environ["IG_POR_PASADA"] = "2"
shutil.rmtree(base)


# --- 20. La noticia DEL MOMENTO, sea cual sea el tema (27/09) ---------------------------
def preparar_horas(filas):
    """filas: (pueblo, viral, hora de publicación en el medio, UTC)"""
    base, carpeta, reloj, meta = preparar()
    piezas = []
    for i, (pueblo, v, hora) in enumerate(filas, 1):
        pz = pieza(i, pueblo)
        pz["viral"] = v
        pz["publicado"] = f"2026-09-26T{hora}+00:00" if hora else ""
        piezas.append(pz)
        (carpeta / f"{i:02d}_reel.mp4").write_bytes(b"\x00" * 4096)
    (carpeta / "_lote.json").write_text(json.dumps({"publicado": False, "piezas": piezas}), encoding="utf-8")
    return base, carpeta, reloj, meta


# El caso del 27/09: el temporal de horas antes (muy viral y cercano) se llevaba el lugar.
base, carpeta, reloj, meta = preparar_horas([("bragado", 9, "13:00"), ("junin", 5, "15:00"),
                                             ("lobos", 6, "15:10")])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("Instagram (10/10): las 2 MÁS VIRALES, como Facebook, aunque sean de horas antes",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["ok", "omitida", "ok"])
chequear("...y el motivo dice que no está entre las más virales",
         "más virales" in inf["piezas"][1]["instagram"]["detalle"])
chequear("Facebook, en cambio (03/10): las 2 MÁS VIRALES, aunque sean de horas antes",
         [f["facebook"]["estado"] for f in inf["piezas"]] == ["ok", "omitida", "ok"])
shutil.rmtree(base)

os.environ["IG_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_horas([("lobos", 6, "15:10"), ("bragado", 6, "15:00")])
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("con minutos de diferencia, desempata la cercanía (Bragado, 49 km, 10 min antes le gana)",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["omitida", "ok"])
base2, carpeta2, _, _ = preparar_horas([("lobos", 6, "15:10"), ("bragado", 6, "13:30")])
inf2 = silencio(PUB.publicar_lote, carpeta2, ("instagram",), publicar=True)
chequear("...y desde el 10/10 la hora ya no manda: gana la cercana aunque sea de 1,5 h antes",
         [f["instagram"]["estado"] for f in inf2["piezas"]] == ["omitida", "ok"])
base3, carpeta3, _, _ = preparar_horas([("lobos", 9, ""), ("lobos", 5, "15:10")])
inf3 = silencio(PUB.publicar_lote, carpeta3, ("instagram",), publicar=True)
chequear("la más viral gana aunque no se sepa su hora (9 contra 5)",
         [f["instagram"]["estado"] for f in inf3["piezas"]] == ["ok", "omitida"])
os.environ["IG_POR_PASADA"] = "2"
for b in (base, base2, base3):
    shutil.rmtree(b)


# --- 21. Miniatura del Short = PORTADA del reel, no la placa final (27/09) ----------------
base, carpeta, reloj, meta = preparar()
(carpeta / "01_reel.jpg").write_bytes(b"JPGportada")
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
yt1 = inf["piezas"][0]["youtube"]
chequear("YouTube: se le pone la portada del reel (.jpg al lado del .mp4) como miniatura",
         meta.yt_miniaturas == [("YT1", "image/jpeg", 10)] and yt1.get("miniatura") == "portada del reel")
chequear("...la pieza sin portada .jpg no llama y lo anota",
         len(meta.yt_miniaturas) == 1 and "sin portada" in inf["piezas"][1]["youtube"].get("miniatura", ""))
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar(Meta(yt_miniatura=403))
(carpeta / "01_reel.jpg").write_bytes(b"JPGportada")
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("si YouTube rechaza la miniatura, el Short queda publicado igual (con el aviso)",
         inf["piezas"][0]["youtube"]["estado"] == "ok"
         and "no aceptó la portada" in inf["piezas"][0]["youtube"].get("miniatura", "")
         and not (base / "informe_publicacion.md").exists())
shutil.rmtree(base)

os.environ["YT_MINIATURA"] = "0"
base, carpeta, reloj, meta = preparar()
(carpeta / "01_reel.jpg").write_bytes(b"JPGportada")
silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("YT_MINIATURA=0 la apaga", meta.yt_miniaturas == [])
os.environ.pop("YT_MINIATURA")
shutil.rmtree(base)


# --- 22. YouTube va SIN la placa final (27/09) ---------------------------------------------
from reels import reel_bot as RB
_original_sin_placa = RB.sin_placa_final
cortes = []


def _corte_falso(mp4, destino):
    cortes.append(Path(mp4).name)
    Path(destino).write_bytes(b"CORTO" * 100)            # 500 bytes: distinto del original
    return Path(destino)


os.environ["YT_SIN_PLACA"] = "1"
try:
    RB.sin_placa_final = _corte_falso
    base, carpeta, reloj, meta = preparar()
    inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
    subidas = [len(r.content) for r in meta.pedidos
               if r.url.path == "/upload/youtube/v3/videos" and r.method == "PUT" and r.content]
    chequear("a YouTube sube el reel CORTADO (sin la placa final)",
             subidas and all(n == 500 for n in subidas) and inf["piezas"][0]["youtube"].get("sin_placa"))
    fb = [r for r in meta.pedidos if r.url.host == "rupload.facebook.com"]
    chequear("...Facebook sigue recibiendo el reel entero, con la placa",
             fb and all(len(r.content) == 4096 for r in fb if r.content))
    shutil.rmtree(base)

    def _corte_roto(mp4, destino):
        raise RuntimeError("ffmpeg no está")
    RB.sin_placa_final = _corte_roto
    base, carpeta, reloj, meta = preparar()
    inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
    chequear("si el corte falla, sube el reel entero y no es una falla",
             inf["piezas"][0]["youtube"]["estado"] == "ok" and not inf["piezas"][0]["youtube"].get("sin_placa"))
    shutil.rmtree(base)

    RB.sin_placa_final = _corte_falso
    os.environ["YT_SIN_PLACA"] = "0"
    cortes.clear()
    base, carpeta, reloj, meta = preparar()
    silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
    chequear("YT_SIN_PLACA=0 sube el reel entero", cortes == [])
    shutil.rmtree(base)
finally:
    RB.sin_placa_final = _original_sin_placa
    os.environ["YT_SIN_PLACA"] = "0"


# --- 23. El VIDEO del medio por sobre la foto (27/09) --------------------------------------
def preparar_video(filas):
    """filas: (pueblo, viral, hora UTC, tenia_video)"""
    base, carpeta, reloj, meta = preparar_horas([(pu, v, h) for pu, v, h, _ in filas])
    lote = json.loads((carpeta / "_lote.json").read_text(encoding="utf-8"))
    for pz, (_, _, _, vid) in zip(lote["piezas"], filas):
        pz["tenia_video"] = vid
    (carpeta / "_lote.json").write_text(json.dumps(lote), encoding="utf-8")
    return base, carpeta, reloj, meta


os.environ["IG_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_video([("junin", 7, "15:10", False), ("lobos", 5, "15:00", True)])
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("de la misma hora, la que tiene VIDEO le gana a la de foto aunque sea menos viral",
         [f["instagram"]["estado"] for f in inf["piezas"]] == ["omitida", "ok"])
chequear("...y el motivo de la de foto no dice «por video»", "por video" not in inf["piezas"][0]["instagram"]["detalle"])
base2, carpeta2, _, _ = preparar_video([("junin", 7, "15:10", False), ("lobos", 5, "13:00", True)])
inf2 = silencio(PUB.publicar_lote, carpeta2, ("instagram",), publicar=True)
chequear("...y el video suma aunque sea de 2 horas antes (desde el 10/10 la hora solo desempata)",
         [f["instagram"]["estado"] for f in inf2["piezas"]] == ["omitida", "ok"]
         and "más virales" in inf2["piezas"][0]["instagram"]["detalle"])
os.environ["IG_POR_PASADA"] = "2"
for b in (base, base2):
    shutil.rmtree(b)


# --- 24. YouTube: no repetir un hecho que YA está en el canal (28/09) ------------------------
def preparar_yt(filas, recientes):
    """filas: (titular, bajada, tipo, pueblo); recientes: Shorts del canal."""
    base, carpeta, reloj, meta = preparar(Meta(yt_recientes=recientes))
    piezas = []
    for i, (tit, baj, tipo, pueblo) in enumerate(filas, 1):
        pz = pieza(i, pueblo.lower())
        pz.update({"guion": {"titular": tit, "bajada": baj}, "tipo": tipo, "localidad_hecho": pueblo})
        piezas.append(pz)
        (carpeta / f"{i:02d}_reel.mp4").write_bytes(b"\x00" * 4096)
    (carpeta / "_lote.json").write_text(json.dumps({"publicado": False, "piezas": piezas}), encoding="utf-8")
    return base, carpeta, reloj, meta


ROBO = ("Detuvieron a dos hombres por el robo de una camioneta en el barrio Centro",
        "La policía recuperó la camioneta sustraída y secuestró herramientas en la vivienda")
base, carpeta, reloj, meta = preparar_yt(
    [ROBO + ("robo", "Junín"), ("Choque entre un auto y una moto en la Ruta 7 dejó un herido grave",
                               "El motociclista fue trasladado al hospital con fracturas", "accidente_vial", "Junín")],
    [("2026-09-26T08:00:00Z", "Detuvieron a dos hombres por el robo de una camioneta | Junín",
      "La policía detuvo a dos hombres, recuperó la camioneta sustraída y secuestró herramientas en la vivienda.")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
yts = [f["youtube"] for f in inf["piezas"]]
chequear("YouTube: el hecho que YA está en el canal no se sube de nuevo",
         yts[0]["estado"] == "omitida" and "ya está en el canal" in yts[0]["detalle"])
chequear("...el otro hecho sí", yts[1]["estado"] == "ok" and len(meta.yt_videos) == 1)
shutil.rmtree(base)

BRAGADO_1 = ("Fuertes tormentas y caída de granizo afectaron a Bragado | Bragado",
             "Un temporal de gran intensidad azotó a la localidad.\n\n#Bragado #AlertaMeteorologica")
TEMPORAL = ("Temporal en Bragado: intensas tormentas, granizo y calles anegadas",
            "Un fuerte temporal de lluvia azotó la ciudad cabecera y las zonas rurales del distrito",
            "alerta_meteorologica", "Bragado")
base, carpeta, reloj, meta = preparar_yt([TEMPORAL], [("2026-09-26T02:00:00Z",) + BRAGADO_1])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("temporal: si ya hay un Short del temporal de ese pueblo en 24 h, no va otro (el caso de Bragado)",
         inf["piezas"][0]["youtube"]["estado"] == "omitida"
         and "temporal o la alerta de Bragado" in inf["piezas"][0]["youtube"]["detalle"])
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_yt([TEMPORAL], [("2026-09-25T04:00:00Z",) + BRAGADO_1])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("...pero el de hace más de 24 h no frena uno nuevo", inf["piezas"][0]["youtube"]["estado"] == "ok")
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_yt(
    [("Emiten alerta amarilla por tormentas en Junín", "Rige desde la tarde para el distrito y la zona",
      "alerta_meteorologica", "Junín")], [("2026-09-26T02:00:00Z",) + BRAGADO_1])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("...ni el temporal de OTRO pueblo", inf["piezas"][0]["youtube"]["estado"] == "ok")
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_yt(
    [("Alerta amarilla por tormentas en Salto", "Rige desde la tarde para el distrito y la zona",
      "alerta_meteorologica", "Salto")],
    [("2026-09-26T02:00:00Z", "Asalto a mano armada durante la tormenta | Chacabuco", "Robo en un comercio")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("«Salto» no se confunde con «asalto»", inf["piezas"][0]["youtube"]["estado"] == "ok")
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_yt([TEMPORAL, TEMPORAL[:2] + ("alerta_meteorologica", "Bragado")],
                                         [("2026-09-20T02:00:00Z", "Otra cosa vieja | Lobos", "nada")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("dentro de la misma pasada tampoco se repite (la primera cuenta para la segunda)",
         [f["youtube"]["estado"] for f in inf["piezas"]] == ["ok"]
         and any("repite un hecho" in s_["motivo"] for s_ in inf["salteadas"]))
shutil.rmtree(base)

chequear("el token de YouTube se renueva antes de la hora (vence a los 60 min)", PUB.YT_ACCESO_MINUTOS < 60)

# Títulos casi iguales con bajadas distintas: el caso real del operativo de Lobos (27/09).
base, carpeta, reloj, meta = preparar_yt(
    [("Despliegue de seguridad en Lobos dejó cinco vehículos secuestrados",
      "Personal policial identificó 143 rodados y labró 28 infracciones en distintos puntos", "operativo_policial", "Lobos")],
    [("2026-09-26T08:00:00Z", "Despliegue de seguridad en Lobos deja cinco vehículos secuestrados | Lobos",
      "Un amplio operativo de control vial terminó con varias actas.\n\n#Lobos #Policiales")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("título casi igual (deja/dejó) aunque cambie la bajada: no se repite",
         inf["piezas"][0]["youtube"]["estado"] == "omitida" and "Despliegue" in inf["piezas"][0]["youtube"]["detalle"])
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_yt(
    [("Dos detenidos tras una amenaza en la vía pública de Chacabuco",
      "La policía detuvo a dos personas luego de un llamado al 911", "operativo_policial", "Chacabuco")],
    [("2026-09-26T08:00:00Z", "Dos jóvenes fueron detenidos tras un operativo antidrogas | Chacabuco",
      "Secuestraron cocaína y marihuana en un allanamiento.")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("...pero dos hechos distintos del mismo pueblo con títulos parecidos NO se frenan",
         inf["piezas"][0]["youtube"]["estado"] == "ok")
shutil.rmtree(base)

# Otro pueblo: hace falta un título MUY parecido (la ruta 191 salió como de Salto y de Chacabuco).
base, carpeta, reloj, meta = preparar_yt(
    [("Encontraron un auto volcado y sin ocupantes en la Ruta 191",
      "Un Peugeot 208 protagonizó un vuelco en una curva del tramo", "accidente_vial", "Chacabuco")],
    [("2026-09-26T08:00:00Z", "Hallan un auto volcado a la vera de la ruta 191 sin sus ocupantes | Salto",
      "Un vehículo fue hallado volcado al costado de la ruta.")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("otro pueblo pero el mismo título (ruta 191, Salto/Chacabuco): no se repite",
         inf["piezas"][0]["youtube"]["estado"] == "omitida")
shutil.rmtree(base)
base, carpeta, reloj, meta = preparar_yt(
    [("Robaron una moto estacionada en el centro de Junín",
      "El propietario radicó la denuncia en la comisaría", "robo", "Junín")],
    [("2026-09-26T08:00:00Z", "Robaron una moto estacionada en el centro | Chacabuco",
      "La víctima denunció el hecho en la comisaría local.")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("...y dos robos de moto en pueblos distintos NO son el mismo hecho",
         inf["piezas"][0]["youtube"]["estado"] == "ok")
shutil.rmtree(base)
base, carpeta, reloj, meta = preparar_yt(
    [("Choque en la Ruta 65 entre una moto y un camión en el acceso sur",
      "El motociclista fue trasladado al hospital municipal", "accidente_vial", "9 de Julio")],
    [("2026-09-26T08:00:00Z", "Choque en la Ruta 65 cerca del acceso norte: dos autos involucrados | Junín",
      "No hubo heridos de gravedad.")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("...ni dos choques distintos en la misma ruta y en pueblos distintos",
         inf["piezas"][0]["youtube"]["estado"] == "ok")
shutil.rmtree(base)

# El poste de luz «durante el temporal» es un incendio: no frena el Short del temporal.
base, carpeta, reloj, meta = preparar_yt(
    [TEMPORAL], [("2026-09-26T02:00:00Z", "Bomberos apagaron el fuego en un poste de luz durante el temporal | Bragado",
                  "El personal intervino con rapidez.\n\n#Bragado #Bomberos #Temporal #Incendio")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("temporal: solo cuentan Shorts de CLIMA (#Clima/#AlertaMeteorologica), no un incendio que dice «temporal»",
         inf["piezas"][0]["youtube"]["estado"] == "ok")
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


# --- 25. La nota de la web va con cada reel de YOUTUBE (pedido del editor, 03/10) ---------
os.environ["NOTAS_WEB"] = "1"
os.environ["FB_POR_PASADA"] = "1"
base, carpeta, reloj, meta = preparar_virales([3, 9, 7])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube", "facebook"), publicar=True)
chequear("web: una nota por cada reel de YouTube, aunque a Facebook vaya uno solo",
         [f["facebook"]["estado"] for f in inf["piezas"]].count("ok") == 1
         and [(f.get("web") or {}).get("estado") for f in inf["piezas"]] == ["ok", "ok", "ok"]
         and meta.wix_publicados == 3)
shutil.rmtree(base)
os.environ["FB_POR_PASADA"] = "2"

base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("web: también en una pasada que solo publica YouTube",
         [(f.get("web") or {}).get("estado") for f in inf["piezas"]] == ["ok", "ok"])
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_yt(
    [ROBO + ("robo", "Junín")],
    [("2026-09-26T08:00:00Z", "Detuvieron a dos hombres por el robo de una camioneta | Junín",
      "La policía detuvo a dos hombres, recuperó la camioneta sustraída y secuestró herramientas en la vivienda.")])
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
chequear("web: el hecho que YouTube no repite (ya está en el canal) tampoco se repite en la web",
         inf["piezas"][0]["youtube"]["estado"] == "omitida" and "web" not in inf["piezas"][0]
         and meta.wix_publicados == 0)
shutil.rmtree(base)
os.environ["NOTAS_WEB"] = "0"


# --- 30. Cupo GLOBAL de 3 hechos por pasada y radio de 100 km (17/10/2026) -----------------
os.environ["MAX_POLICE_REELS_PER_PASS"] = "3"
os.environ.pop("IG_POR_PASADA", None)
PUB._hora_ar = lambda: datetime(2026, 10, 17, 12, 10, tzinfo=_AR)   # 6 lugares de 30 min hasta 15:05
chequear("lugares por pasada: nunca más de 3 aunque entren 6 de 30 minutos",
         PUB.lugares_en_la_pasada(datetime(2026, 10, 17, 12, 10, tzinfo=_AR)) == 3)
base, carpeta, reloj, meta = preparar_virales([3, 1, 2, 8, 5, 9, 7, 4, 6, 6])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
salieron = [f for f in inf["piezas"] if any((f.get(r) or {}).get("estado") == "ok" for r in PUB.REDES)]
chequear("10 piezas elegibles → como mucho 3 hechos en TODAS las redes (YouTube incluido)",
         len(salieron) == 3 and sum(1 for f in inf["piezas"] if (f.get("youtube") or {}).get("estado") == "ok") == 3)
chequear("...las 3 más virales (9, 8, 7)", sorted(int(f["titular"].split()[-1]) for f in salieron) == [4, 6, 7])
chequear("...las demás, salteadas con el motivo del cupo",
         sum(1 for s_ in inf["salteadas"] if "como mucho 3 hechos" in s_["motivo"]) == 7)
chequear("...y la pasada queda anotada con sus 3 reservas",
         inf["pasada"]["id"] == "2026-10-17T12:05" and len(PUB.CUPO.reservadas("2026-10-17T12:05")) == 3)
# La misma pasada otra vez (el respaldo o una corrida a mano): no hay 3 lugares nuevos.
lote2 = carpeta.parent / "2026-10-17_0930"
lote2.mkdir()
piezas2 = [dict(pieza(20 + i, "chivilcoy"), viral=10) for i in range(3)]
for p_ in piezas2:
    (lote2 / f"{p_['orden']:02d}_reel.mp4").write_bytes(b"\x00" * 4096)
(lote2 / "_lote.json").write_text(json.dumps({"publicado": False, "piezas": piezas2}), encoding="utf-8")
inf2 = silencio(PUB.publicar_lote, lote2, PUB.REDES, publicar=True)
chequear("un reintento de la MISMA pasada no habilita otros 3 (ni con viral 10 de Chivilcoy)",
         not any((f.get(r) or {}).get("estado") == "ok" for f in inf2["piezas"] for r in PUB.REDES)
         and len(PUB.CUPO.reservadas("2026-10-17T12:05")) == 3)
# La pasada siguiente sí tiene sus 3.
PUB._hora_ar = lambda: datetime(2026, 10, 17, 15, 10, tzinfo=_AR)
inf3 = silencio(PUB.publicar_lote, lote2, PUB.REDES, publicar=True)
chequear("la pasada siguiente (15:05) tiene sus propios 3 lugares",
         inf3["pasada"]["id"] == "2026-10-17T15:05"
         and sum(1 for f in inf3["piezas"] if (f.get("youtube") or {}).get("estado") == "ok") == 3)
shutil.rmtree(base)

# Radio: lo lejano no sale en ninguna red, ni va al buzón de X/TikTok, aunque sea lo más viral.
PUB._hora_ar = lambda: datetime(2026, 10, 17, 15, 10, tzinfo=_AR)
base, carpeta, reloj, meta = preparar_pueblos([("pergamino", 10), ("rojas", 10), ("9 de julio", 5),
                                               ("bolivar", 9)])
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("Pergamino (123 km), Rojas (101,6 km) y Bolívar quedan afuera con el motivo; 9 de Julio (99,4) sale",
         [f["orden"] for f in inf["piezas"]] == [3]
         and sum(1 for s_ in inf["salteadas"] if "fuera del radio" in s_["motivo"]) == 3)
buzon = json.loads(PUB.DIST.BUZON.read_text(encoding="utf-8")) if PUB.DIST.BUZON.exists() else {}
chequear("...y al buzón de X/TikTok no llega ninguna lejana",
         all("medio.test/3" in json.dumps(e) for e in (buzon.get("eventos") or [])))
ledger = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
chequear("...la memoria guarda distancia, precisión y pasada de lo publicado",
         ledger["https://medio.test/3"].get("distancia_km") == 99.4
         and ledger["https://medio.test/3"].get("pasada") == "2026-10-17T15:05")
shutil.rmtree(base)


# --- 31. Intercalado: nunca dos policiales seguidos en la misma cuenta (17/10/2026) ---------
os.environ["INTERCALADO"] = "1"
os.environ["IG_POR_PASADA"] = "5"
PUB._hora_ar = lambda: datetime(2026, 10, 17, 12, 10, tzinfo=_AR)      # cierre de la pasada: 14:55
_cuando_real = PUB.INT.cuando_local
PUB.INT.cuando_local = lambda ts: datetime.fromisoformat(ts[:19]) if ts else None   # el reloj falso no tiene zona


def bot_publica(meta, reloj, texto, cuando_dormir=None):
    """El bot del diario publica `texto` en Instagram cuando el publicador espera su turno."""
    dormir = reloj.dormir
    llamadas = []

    def _dormir(s):
        dormir(s)
        if s >= 600:                                  # las esperas de turno, no los sondeos
            llamadas.append(s)
            if cuando_dormir is None or len(llamadas) in cuando_dormir:
                meta.ig_recientes.insert(0, {"id": f"BOT{len(llamadas)}", "caption": texto,
                                             "timestamp": reloj.t.isoformat() + "+0000"})
    PUB._dormir = _dormir


def hora_ar_del_reloj(reloj):
    """La hora argentina avanza con el reloj falso: la pasada arranca a las 9:10."""
    PUB._hora_ar = lambda: datetime(2026, 10, 17, 12, 10, tzinfo=_AR) + (reloj.t - datetime(2026, 9, 26, 10, 0))


def estados(inf, red="instagram"):
    return [(f.get(red) or {}).get("estado") for f in inf["piezas"]]


base, carpeta, reloj, meta = preparar_virales([9, 8, 7])
hora_ar_del_reloj(reloj)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram", "youtube"), publicar=True)
chequear("sin otra temática en la cuenta: el 1.º reel sale y los otros 2 NO van pegados en Instagram",
         estados(inf) == ["ok", "omitida", "omitida"]
         and all("intercalado" in (f["instagram"].get("detalle") or "") for f in inf["piezas"][1:]))
chequear("...pero salen igual en YouTube (el intercalado es por cuenta)", estados(inf, "youtube") == ["ok"] * 3)
chequear("...y esperó hasta el cierre de la pasada, no más (11:55, 10 min antes de la de 12:05)",
         datetime(2026, 9, 26, 10, 0) + timedelta(hours=2, minutes=30) <= reloj.t
         <= datetime(2026, 9, 26, 10, 0) + timedelta(hours=2, minutes=45))
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_virales([9, 8, 7])
hora_ar_del_reloj(reloj)
bot_publica(meta, reloj, "El intendente inauguró la nueva plaza del barrio Villa Sarmiento")
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("con un posteo del bot de otra temática entre medio, salen los 3", estados(inf) == ["ok", "ok", "ok"])
shutil.rmtree(base)

base, carpeta, reloj, meta = preparar_virales([9, 8, 7])
hora_ar_del_reloj(reloj)
bot_publica(meta, reloj, "Detuvieron a dos jóvenes tras un robo en un comercio de Chivilcoy")
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("si lo que publicó el bot TAMBIÉN es policial, no cuenta como intercalado",
         estados(inf) == ["ok", "omitida", "omitida"])
posteo_bot = [{"id": "B", "cuando": datetime(2026, 9, 26, 12, 0), "texto": "Choque en la Ruta 5: un herido"}]
chequear("...y el motivo dice que es un policial de otro origen",
         "de otro origen" in PUB.INT.libre("instagram", posteo_bot, {})[1])
chequear("un posteo ajeno de otra temática deja el hueco libre",
         PUB.INT.libre("instagram", [dict(posteo_bot[0], texto="Abre la muestra de pintura en el museo")], {})[0])
chequear("nuestro reel que todavía no aparece en el listado cuenta como el último",
         not PUB.INT.libre("instagram", [dict(posteo_bot[0], texto="Abre la muestra de pintura")],
                           {"u": {"instagram": {"estado": "ok", "id": "X", "cuando": "2026-09-26T12:01:00"}}})[0])
shutil.rmtree(base)

# El que espera con más interés toma el primer hueco: 5 sale, 9 espera, el bot publica, 9 sale
# en el turno de 6, y 6 se queda sin hueco.
base, carpeta, reloj, meta = preparar_virales([5, 9, 6])
hora_ar_del_reloj(reloj)
bot_publica(meta, reloj, "Se viene la Fiesta del Inmigrante en el Parque", cuando_dormir={2})
inf = silencio(PUB.publicar_lote, carpeta, ("instagram",), publicar=True)
chequear("el reel de más interés que esperaba (9) toma el hueco antes que el del turno (6)",
         estados(inf) == ["ok", "ok", "omitida"]
         and inf["piezas"][1]["instagram"].get("intercalado") == "esperó otra temática")
ledger = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
chequear("...y la memoria lo anota como publicado en Instagram",
         (ledger["https://medio.test/2"].get("instagram") or {}).get("estado") == "ok")
shutil.rmtree(base)

# Facebook: el reel y también el enlace del Short son posteos policiales de la página.
os.environ["FB_POR_PASADA"] = "2"
base, carpeta, reloj, meta = preparar_virales([9, 8, 3])
hora_ar_del_reloj(reloj)
inf = silencio(PUB.publicar_lote, carpeta, PUB.REDES, publicar=True)
chequear("Facebook: el 2.º reel no va pegado al 1.º", estados(inf, "facebook")[:2] == ["ok", "omitida"])
chequear("...y el enlace del Short del 3.º tampoco (también es un policial en la página)",
         (inf["piezas"][2].get("fb_youtube") or {}).get("estado") in ("omitida", None)
         and not meta.fb_links)
shutil.rmtree(base)

os.environ["INTERCALADO"] = "0"

# --- 32. Shorts: estado real y link a la nota (17/10/2026, PDF «Prompt integral» §29) -------------
base, carpeta, reloj, meta = preparar()
inf = silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
ledger = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
yt1 = ledger["https://medio.test/1"]["youtube"]
chequear("recién subido: queda «uploaded», sin verificar todavía",
         yt1.get("subida") == "uploaded" and not yt1.get("verificado"))
meta.yt_estado = {"YT1": "processed", "YT2": "rejected"}
reloj.t += timedelta(minutes=30)
silencio(PUB.publicar_lote, carpeta, ("youtube",), publicar=True)
ledger = json.loads(PUB.LEDGER.read_text(encoding="utf-8"))
chequear("en la pasada siguiente: el procesado queda verificado",
         ledger["https://medio.test/1"]["youtube"].get("verificado") == "procesado")
chequear("...y el rechazado deja de contar como publicado, con el motivo, y no se resube solo",
         ledger["https://medio.test/2"]["youtube"]["estado"] == "rechazado"
         and "rejected (duplicate)" in ledger["https://medio.test/2"]["youtube"]["detalle"]
         and len(meta.yt_videos) == 2)
regs = {"a": {"youtube": {"estado": "ok", "id": "YT1"}}, "b": {"youtube": {"estado": "ok", "id": "NOESTA"}}}
PUB.verificar_shorts(regs)
chequear("un Short que ya no existe en el canal también se marca", regs["b"]["youtube"]["verificado"] == "no_existe")
shutil.rmtree(base)

os.environ["NOTAS_WEB"] = "1"
base, carpeta, reloj, meta = preparar(Meta(wix_falla="borrador"))
inf = silencio(PUB.publicar_lote, carpeta, ("youtube", "facebook"), publicar=True)
chequear("si la nota de la web no sale, al Short se le saca el link (no queda roto)",
         meta.yt_cambios and "Nota completa" not in meta.yt_cambios[0]["snippet"]["description"]
         and inf["piezas"][0]["youtube"].get("descripcion") == "sin link: la nota no salió")
shutil.rmtree(base)
os.environ["NOTAS_WEB"] = "0"
chequear("INTERCALADO=0 lo apaga", PUB.intercalado_libre("instagram", {}) == (True, ""))
PUB.INT.cuando_local = _cuando_real
os.environ["MAX_POLICE_REELS_PER_PASS"] = "6"


# --- 32. La fila de 15 minutos con nacionales (18/10/2026, reels/turnos.py) ------------------------
os.environ["FILA_15"] = "1"
os.environ["INTERCALADO"] = "0"
os.environ["MAX_POLICE_REELS_PER_PASS"] = "3"
base, carpeta, reloj, meta = preparar_virales([9, 8, 7])
hora_ar_del_reloj(reloj)                              # la pasada de las 12:05, arranca 12:10 (la de las 09:05 ya no existe)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram", "youtube"), publicar=True)
horas = [f.get("hora") for f in inf["piezas"]]
# El reloj falso arranca 10:00 cuando en la Argentina son las 12:10: 12:20 AR = 10:10 del reloj.
chequear("fila: los 3 policiales toman turnos repartidos (12:20, 13:20 y 14:20), nunca dos seguidos",
         inf["fila"]["turnos"] == ["12:20", "13:20", "14:20"]
         and horas == ["2026-09-26T10:10", "2026-09-26T11:10", "2026-09-26T12:10"])
chequear("fila: y salen en todas sus redes", estados(inf) == ["ok"] * 3)
shutil.rmtree(base)

# Si nacionales ya tomó turnos, policiales usa los libres que siguen, sin pegarse entre sí.
from reels import turnos as TURNOS
_Fila = TURNOS.Fila
compartida = _Fila("2026-10-17T12:05", token="")
for k in (0, 1, 2):
    compartida.tomar(k, "nacionales", "general")
TURNOS.Fila = lambda pid, token=None, **k: compartida
base, carpeta, reloj, meta = preparar_virales([9, 8])
hora_ar_del_reloj(reloj)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram", "youtube"), publicar=True)
oc = compartida.ocupados()
pol = sorted(k for k, d in oc.items() if d["quien"] == "policiales")
chequear("fila: con los primeros turnos tomados por nacionales, policiales sigue desde el libre (13:05)",
         inf["fila"]["turnos"][0] == "13:05" and pol[0] == 3 and all(b - a >= 2 for a, b in zip(pol, pol[1:])))
shutil.rmtree(base)
# Simulando no se reserva nada (la fila es de verdad solo publicando).
compartida2 = _Fila("2026-10-17T12:05", token="")
TURNOS.Fila = lambda pid, token=None, **k: compartida2
base, carpeta, reloj, meta = preparar_virales([9, 8])
hora_ar_del_reloj(reloj)
inf = silencio(PUB.publicar_lote, carpeta, ("instagram", "youtube"), publicar=False)
chequear("fila: la simulación muestra los turnos pero no reserva ninguno",
         inf["fila"]["turnos"] == ["12:20", "13:50"] and compartida2.ocupados() == {})
TURNOS.Fila = _Fila
shutil.rmtree(base)
os.environ["FILA_15"] = "0"
os.environ["MAX_POLICE_REELS_PER_PASS"] = "6"

# --- 33. Instagram SIN links, para todo lo que sale de este repo (18/10/2026) -------------------------------
cap_racing = ("La tribuna de Racing atraviesa una disputa.\n\n📲 Leé la nota completa: "
              "https://www.diariolacampaña.com.ar/n/racing-quien-es-el-nuevo-jefe-78b5fd\n\n#Racing #Deportes")
limpio = PUB.caption_sin_links(cap_racing)
chequear("IG sin links: el renglón de la nota pasa a ser el sitio, antes de los hashtags",
         "/n/" not in limpio and "http" not in limpio
         and limpio.endswith("📲 Más noticias en www.diariolacampaña.com.ar\n\n#Racing #Deportes"))
pol = "Detuvieron a un joven.\n\n📲 Más noticias de Chacabuco en www.diariolacampaña.com.ar\n\n#Chacabuco"
chequear("IG sin links: el sitio pelado se respeta (el texto de policiales queda igual)", PUB.caption_sin_links(pol) == pol)
chequear("IG sin links: un renglón con otro link (YouTube) se saca entero",
         PUB.caption_sin_links("Texto.\n📺 El canal 👉 https://youtube.com/@x\n\n#Tag")
         == "Texto.\n\n📲 Más noticias en www.diariolacampaña.com.ar\n\n#Tag")
mandados = []
_pedir_real, _estado_real = PUB._pedir, PUB._estado_contenedor
PUB._pedir = lambda m, u, tok, **k: mandados.append(k.get("data") or {}) or type(
    "R", (), {"status_code": 200, "json": lambda s: {"id": "c1"}})()
PUB._estado_contenedor = lambda cid, tok: ("FINISHED", "")
PUB._contenedor_listo("u", "t", {"media_type": "REELS", "video_url": "https://gh/v.mp4", "caption": cap_racing})
PUB._pedir, PUB._estado_contenedor = _pedir_real, _estado_real
chequear("IG sin links: la última barrera (el contenedor) limpia el texto venga de donde venga",
         mandados and "/n/" not in mandados[0]["caption"] and "www.diariolacampaña.com.ar" in mandados[0]["caption"])

# --- 34. Portada del reel y videos largos (18/10/2026) -------------------------------------------------
import tempfile as _tf
_d34 = Path(_tf.mkdtemp())
_mp4 = _d34 / "reel_1.mp4"
_mp4.write_bytes(b"mp4")
(_d34 / "reel_1_portada.jpg").write_bytes(b"jpg")
chequear("portada: se encuentra al lado del .mp4 aunque la ruta del lote sea de otra máquina",
         PUB.portada_del_reel({"video": {"portada": "C:\\otra\\maquina\\reel_1_portada.jpg"}}, _mp4)
         == str(_d34 / "reel_1_portada.jpg"))
_pedidos = []
_listo_real, _subir_real = PUB._contenedor_listo, PUB.subir_a_release
PUB.subir_a_release = lambda ruta, nombre: f"https://gh/{nombre}"
PUB._contenedor_listo = lambda uid, tok, params: _pedidos.append(dict(params)) or "c1"
cid, como = PUB.contenedor_con_portada("u", "t", {"media_type": "REELS"}, str(_d34 / "reel_1_portada.jpg"), "x.jpg")
chequear("portada: el contenedor del reel lleva cover_url con la portada subida",
         como == "propia" and _pedidos[-1].get("cover_url") == "https://gh/x.jpg")


def _rechaza_portada(uid, tok, params):
    _pedidos.append(dict(params))
    if params.get("cover_url"):
        raise PUB.FalloRed("Instagram: cover_url inválida")
    return "c2"


PUB._contenedor_listo = _rechaza_portada
_pedidos.clear()
cid, como = PUB.contenedor_con_portada("u", "t", {"media_type": "REELS"}, str(_d34 / "reel_1_portada.jpg"), "x.jpg")
chequear("portada: si Instagram la rechaza, el reel sale igual con la suya",
         cid == "c2" and como == "de Instagram" and "cover_url" not in _pedidos[-1])
PUB._contenedor_listo, PUB.subir_a_release = _listo_real, _subir_real
_fb = []
_pedir_real, _subir_real = PUB._pedir, PUB.subir_a_release
PUB.subir_a_release = lambda ruta, nombre: f"https://gh/{nombre}"
PUB._pedir = lambda m, u, tok="", **k: _fb.append((u, k.get("data") or {})) or type(
    "R", (), {"status_code": 200, "json": lambda s: {"id": "v9"}})()
_res = PUB.publicar_facebook({"video": {"duracion": 140.0}, "guion": {"titular": "Un video largo"}}, _mp4)
PUB._pedir, PUB.subir_a_release = _pedir_real, _subir_real
chequear("Facebook: un reel de más de 90 s sale como video de la página (los reels por API llegan a 90)",
         _res == {"id": "v9", "formato": "video"} and _fb and _fb[0][0].endswith("/videos")
         and _fb[0][1].get("file_url", "").startswith("https://gh/fb_"))

# --- 35. Solo Shorts en YouTube: nada de más de 3 minutos (19/10/2026) -----------------------------------
os.environ["YT_SIN_PLACA"] = "1"            # como en producción: a YouTube va sin la placa de 5 s
chequear("Shorts: 3 min o menos (sin la placa de 5 s) va; más largo no",
         not PUB.largo_para_short({"video": {"duracion": 185.0}})
         and "no va a YouTube" in PUB.largo_para_short({"video": {"duracion": 200.0}}))
_r = PUB._intentar(PUB.publicar_youtube, {"video": {"duracion": 400.0}}, Path("no-existe.mp4"))
chequear("Shorts: el largo queda «omitida» (no es una falla ni manda mail)",
         _r["estado"] == "omitida" and "Short" in _r["detalle"])

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
