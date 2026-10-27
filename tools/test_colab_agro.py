"""Pruebas de la colaboración con @diarioyradioagro (reels/colab_agro.py, 27/10/2026). Sin red."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reels import colab_agro as CA  # noqa: E402
from reels import publicador as PB  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK  " if condicion else "MAL ") + nombre)
    if not condicion:
        fallas.append(nombre)


DIARIO = CA.DIARIO_IG
os.environ.pop("COLAB_AGRO", None)

# 1. ¿Qué es del campo?
for texto in ("Récord de cosecha de soja en el partido", "Senasa controló un tambo de la zona",
              "Detuvieron a dos hombres por abigeato en un campo de Moquehuá",
              "La Sociedad Rural presentó la Expo Rural 2026", "Suben las retenciones al maíz y al trigo",
              "MAÍZ: la siembra avanza con buena humedad"):
    chequear(f"del campo: «{texto}»", CA.es_del_campo(texto))
for texto in ("La productora del festival anunció la grilla", "Mejoró el rendimiento escolar en Chivilcoy",
              "Secuestraron un cultivo de marihuana en una casa", "Inauguraron la nueva chacra deportiva",
              "Diario La Campaña cumple años", "Choque en la ruta 5: dos heridos", "El Gobierno subió las jubilaciones"):
    chequear(f"NO es del campo: «{texto}»", not CA.es_del_campo(texto))

# 2. Solo invita la cuenta del diario, y el interruptor la apaga.
chequear("cuenta del diario + campo → @diarioyradioagro",
         CA.colaborador_para("Cosecha de trigo", DIARIO) == "diarioyradioagro")
chequear("otra cuenta (agro, la radio) → sin colab", CA.colaborador_para("Cosecha de trigo", "999") == "")
os.environ["COLAB_AGRO"] = "0"
chequear("COLAB_AGRO=0 → sin colab", CA.colaborador_para("Cosecha de trigo", DIARIO) == "")
os.environ.pop("COLAB_AGRO")

# 3. El contenedor lleva la colab y, si Instagram la rechaza, sale igual sin ella.
vistos = []


def crear_ok(p):
    vistos.append(dict(p))
    return "C1"


cid, colab = CA.contenedor(crear_ok, {"caption": "x"}, "diarioyradioagro")
chequear("el contenedor lleva collaborators=[\"diarioyradioagro\"]",
         cid == "C1" and colab == "diarioyradioagro" and vistos[-1].get("collaborators") == '["diarioyradioagro"]')
vistos.clear()


def crear_rechaza_colab(p):
    vistos.append(dict(p))
    if "collaborators" in p:
        raise PB.FalloRed("Instagram: crear el contenedor: HTTP 400 — collaborators no válido")
    return "C2"


cid, colab = CA.contenedor(crear_rechaza_colab, {"caption": "x"}, "diarioyradioagro", log=lambda *_: None)
chequear("si Instagram no toma la colab, el posteo sale igual (sin colab)",
         cid == "C2" and colab == "" and len(vistos) == 2 and "collaborators" not in vistos[1])
vistos.clear()
cid, colab = CA.contenedor(crear_ok, {"caption": "x"}, "")
chequear("sin colaborador: el contenedor de siempre", cid == "C1" and "collaborators" not in vistos[-1])

# 4. Aceptar con la cuenta de agro; el barrido solo acepta lo de @diarioyradio.
pedidos = []


class R:
    def __init__(self, codigo, datos):
        self.status_code, self._d = codigo, datos

    def json(self):
        return self._d


INVITACIONES = [{"media_id": "M1", "media_owner_username": "diarioyradio", "caption": "Cosecha"},
                {"media_id": "M9", "media_owner_username": "puntodequiebreradio", "caption": "Tenis"}]


def pedir(metodo, url, tok, **kw):
    pedidos.append((metodo, url, kw.get("data")))
    return R(200, {"data": INVITACIONES} if metodo == "GET" else {"success": True})


orig = (PB._pedir, PB._dormir, CA._agro)
PB._pedir, PB._dormir = pedir, (lambda s: None)
CA._agro = lambda: ("AGRO_UID", "AGRO_TOK")
try:
    chequear("aceptar: la cuenta de agro acepta la invitación del posteo",
             CA.aceptar("M1", log=lambda *_: None) == "aceptada"
             and ("POST", f"{PB.GRAPH}/AGRO_UID/collaboration_invites", {"media_id": "M1", "accept": "true"})
             in pedidos)
    pedidos.clear()
    n = CA.aceptar_pendientes(log=lambda *_: None)
    aceptadas = [d["media_id"] for m, _u, d in pedidos if m == "POST"]
    chequear("barrido: acepta la de @diarioyradio y NO la de otras cuentas", n == 1 and aceptadas == ["M1"])
    CA._agro = lambda: ("", "")
    chequear("sin claves de agro: no rompe, queda para el barrido",
             CA.aceptar("M1", log=lambda *_: None) == "sin credenciales")
finally:
    PB._pedir, PB._dormir, CA._agro = orig

print(f"\n{total - len(fallas)}/{total} bien")
sys.exit(1 if fallas else 0)
