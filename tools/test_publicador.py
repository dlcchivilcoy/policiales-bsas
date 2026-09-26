# -*- coding: utf-8 -*-
"""El publicador contra un Meta, un YouTube y un GitHub FALSOS. No usa la red ni publica nada.

Cubre lo que no se puede probar publicando de a uno: el 500 mentiroso de Instagram,
el contenedor en ERROR, una red que falla sin tumbar a la otra, no repetir lo ya
publicado, los 5 minutos entre posteos, que ningun token termine en una URL, el tope
diario y el cupo agotado de YouTube, el token de otro canal, y que TikTok no salga.
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
                 yt_canal="UCRADIO", yt_sin_cupo=False, yt_cortes=0):
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
            if ruta == "/v26.0/IGUSER/media" and m == "GET":
                return httpx.Response(200, json={"data": []})
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
chequear("YouTube: las dos piezas suben como Short (tope 2 por dia)",
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
