"""Pruebas de los arreglos del 30/10/2026 (corridas en rojo por una sola nota o un guardado). Sin red."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reels import ia  # noqa: E402
from reels import web as W  # noqa: E402
import guardar_estado as GE  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# 1. El JSON de Gemini: saltos de línea crudos dentro de una cadena y coma colgada (29/10, paro docente).
chequear("JSON con salto de línea crudo dentro de una cadena", ia._parsear('{"a": "uno\ndos"}') == {"a": "uno\ndos"})
chequear("JSON con coma colgada", ia._parsear('{"a": [1, 2,], "b": 3,}') == {"a": [1, 2], "b": 3})
chequear("JSON entre ```json", ia._parsear('```json\n{"a": 1}\n```') == {"a": 1})
try:
    ia._parsear('{"titular": "Paro", "lista": [\n    ]\n    "x": }')
    _msg = ""
except json.JSONDecodeError as e:
    _msg = str(e)
chequear("si igual no parsea, el error muestra dónde se rompió", "cerca de «" in _msg)

# 2. Nacionales: la nota que la IA no puede escribir es un descarte, no una falla de la corrida.
from nacionales import pasada as PA  # noqa: E402
_e = RuntimeError("gemini: intento 1: JSON cortado: Expecting value | gemini: intento 2: JSON cortado: x")
chequear("«JSON cortado» en todos los intentos cuenta como descarte", PA.bloqueada_por_ia(_e) and PA.ia_no_pudo(_e))
chequear("un error cualquiera sigue siendo falla", not PA.bloqueada_por_ia(RuntimeError("timeout de Wix")))
_mem, _inf = {"descartadas": {}}, {"descartadas": []}
PA._descartar_bloqueada({"titulo": "Influencer", "url": "u1"}, _mem, True, PA._ahora(), _inf, _e)
chequear("queda anotada en descartadas (no se reintenta mañana) con el motivo claro",
         "u1" in _mem["descartadas"] and "no devolvió la nota completa" in _mem["descartadas"]["u1"]["motivo"])


# 3. Wix: «Media image … id not found» (la foto recién importada todavía no está) → espera y reintenta;
# si nunca aparece, la nota sale sin foto.
class R:
    def __init__(self, codigo, datos=None, texto=""):
        self.status_code, self._d, self.text = codigo, datos or {}, texto or json.dumps(datos or {})

    def json(self):
        return self._d


def wix_falso(veces_sin_foto):
    estado = {"borradores": [], "n": 0}

    def pedir(metodo, url, **kw):
        if url == W.POSTS_QUERY_URL:
            return R(200, {"posts": []})
        if url == W.MEDIA_IMPORT_URL:
            return R(200, {"file": {"id": "foto1"}})
        if url == W.DRAFT_POSTS_URL:
            cuerpo = (kw.get("json") or {}).get("draftPost") or kw.get("json") or {}
            con_foto = any(n.get("type") == "IMAGE" for n in cuerpo.get("richContent", {}).get("nodes", []))
            estado["borradores"].append(con_foto)
            if con_foto and estado["n"] < veces_sin_foto:
                estado["n"] += 1
                return R(400, texto='{"message":"INVALID_ARGUMENT: Media image with provided foto1 id not found"}')
            return R(200, {"draftPost": {"id": "d1"}})
        return R(200, {})
    return pedir, estado


_pieza = {"web": {"titulo": "Alfalfa: el INTA presenta avances", "cuerpo": "Uno.\n\nDos."},
          "imagen_url": "https://x/f.jpg", "guion": {"bajada": "b"}}
_dormidas = []
_orig_dormir = W.dormir_wix
W.dormir_wix = _dormidas.append
try:
    pedir, est = wix_falso(1)
    res = W.publicar(pedir, dict(_pieza))
    chequear("Wix: la foto aparece al reintentar → la nota sale CON foto",
             res.get("foto") and est["borradores"] == [True, True] and _dormidas == [10])
    _dormidas.clear()
    pedir, est = wix_falso(99)
    res = W.publicar(pedir, dict(_pieza))
    chequear("Wix: la foto nunca aparece → la nota sale igual, sin foto (no se pierde)",
             res.get("id") == "d1" and not res.get("foto") and est["borradores"][-1] is False and _dormidas == [10, 30])
finally:
    W.dormir_wix = _orig_dormir

# 4. Guardar la memoria: el motivo del rechazo se muestra sin credenciales.
_r = subprocess.CompletedProcess([], 1, "", "remote: error: GH013 rejected\nfatal: unable to access "
                                            "'https://x-access-token:ghs_abc@github.com/a/b.git/'")
_m = GE._motivo(_r)
chequear("el motivo del push se muestra en una línea", "GH013 rejected" in _m)
chequear("…y sin el token", "ghs_abc" not in _m and "x-access-token" not in _m)
chequear("espera cada vez más entre intentos", list(GE.ESPERAS) == sorted(GE.ESPERAS) and GE.INTENTOS >= 6)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
