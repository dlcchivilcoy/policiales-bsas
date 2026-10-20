# -*- coding: utf-8 -*-
"""La fila de 15 minutos entre policiales y nacionales (reels/turnos.py), sin red.

    venv\\Scripts\\python.exe tools\\test_turnos.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from reels import turnos as T

# Las pruebas de la fila y del cupo usan la grilla completa de pasadas de antes (09:05 a 23:35): prueban
# la mecánica, no los horarios. Los horarios reales viven en reels/cupo.py (19/10/2026: 18:05 y 23:35).
from reels import cupo as _CUPO  # noqa: E402
_CUPO.PASADAS_AR = ((9, 5), (12, 5), (15, 5), (18, 5), (21, 5), (23, 35))
_CUPO.PASADAS_FINDE = ()
from reels import turnos as _TUR  # noqa: E402
_TUR.MINUTOS, _TUR.DEMORA_PRIMERO, _TUR.SEPARACION = 15, 15, 2

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


AR = timezone(timedelta(hours=-3))
hm = lambda ts: [f"{t:%H:%M}" for t in ts]   # noqa: E731

g = T.grilla("2026-10-18T12:05")
chequear("grilla: 12 turnos cada 15 minutos, del 12:20 al 15:05", len(g) == 12 and hm(g)[0] == "12:20"
         and hm(g)[-1] == "15:05" and all((b - a) == timedelta(minutes=15) for a, b in zip(g, g[1:])))
g = T.grilla("2026-10-18T09:05")
chequear("grilla: la primera del día arranca 09:20", hm(g)[0] == "09:20" and len(g) == 12)
g = T.grilla("2026-10-18T21:05")
chequear("grilla: la de las 21:05 tiene 10 (21:20 → 23:35, hasta la de las 23:35)",
         len(g) == 10 and hm(g)[-1] == "23:35")
g = T.grilla("2026-10-18T23:35")
chequear("grilla: la de las 23:35 completa sus 12 (hasta las 02:35, pedido del 18/10/2026)",
         len(g) == 12 and hm(g)[-1] == "02:35" and g[-1].date().isoformat() == "2026-10-19")
os.environ["FILA_POR_PASADA"] = "6"
chequear("grilla: FILA_POR_PASADA cambia el tope", len(T.grilla("2026-10-18T12:05")) == 6)
os.environ.pop("FILA_POR_PASADA")
chequear("pasada: 12:10 todavía es la de las 12:05; 14:58 ya cuenta como la de las 15:05",
         T.pasada_actual(datetime(2026, 10, 18, 12, 10, tzinfo=AR)) == "2026-10-18T12:05"
         and T.pasada_actual(datetime(2026, 10, 18, 14, 58, tzinfo=AR)) == "2026-10-18T15:05")

# Policiales: repartidos y nunca dos seguidos.
pid = "2026-10-18T12:05"
inicio = datetime(2026, 10, 18, 12, 12, tzinfo=AR)
f = T.Fila(pid, token="")
plan = T.plan_policiales(f, 3, inicio)
chequear("policiales: 3 hechos → turnos 0, 4 y 8 (12:20, 13:20, 14:20)", [k for k, _ in plan] == [0, 4, 8])
chequear("policiales: 2 hechos → repartidos en la pasada (0 y 6)", [k for k, _ in T.plan_policiales(f, 2, inicio)] == [0, 6])
f.tomar(0, "nacionales", "general")
f.tomar(1, "nacionales", "deportes")
tarde = datetime(2026, 10, 18, 12, 40, tzinfo=AR)
plan = T.plan_policiales(f, 3, tarde)
chequear("policiales tarde: solo turnos libres que no pasaron, y nunca pegados entre sí",
         plan and plan[0][0] == 2 and all(b[0] - a[0] >= 2 for a, b in zip(plan, plan[1:])))
res = T.reservar_policiales(f, 3, tarde, ["A", "B", "C"])
oc = f.ocupados()
chequear("policiales: la reserva toma los turnos con su categoría y su titular",
         len(res) == 3 and all(oc[k]["quien"] == "policiales" and oc[k]["categoria"] == "policial" for k, _ in res)
         and oc[res[0][0]]["titular"] == "A")
chequear("fila: un turno tomado no se puede volver a tomar (el otro trabajo lo pierde)",
         not f.tomar(res[0][0], "nacionales", "general"))
f.soltar(res[-1][0])
chequear("fila: soltar devuelve el turno (lo puede usar nacionales)", f.tomar(res[-1][0], "nacionales", "general"))
lleno = T.Fila(pid, token="")
for k in range(12):
    lleno.tomar(k, "nacionales", "general")
chequear("policiales: sin turnos libres, ninguno", T.reservar_policiales(lleno, 3, inicio) == [])


# La fila en GitHub: crear la referencia es atómico (422 = ya la tomó el otro).
class Resp:
    def __init__(self, status, datos=None):
        self.status_code, self._d = status, datos

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class Cliente:
    def __init__(self):
        self.refs, self.tags, self.pedidos = {}, {}, []

    def post(self, url, json=None):
        self.pedidos.append(("POST", url))
        if url.endswith("/git/tags"):
            sha = f"t{len(self.tags)}"
            self.tags[sha] = json["message"]
            return Resp(201, {"sha": sha})
        if json["ref"] in self.refs:
            return Resp(422, {"message": "Reference already exists"})
        self.refs[json["ref"]] = json["sha"]
        return Resp(201, {})

    def get(self, url):
        self.pedidos.append(("GET", url))
        if "/git/matching-refs/" in url:
            pre = "refs/" + url.split("/git/matching-refs/")[1]
            return Resp(200, [{"ref": r, "object": {"sha": s, "type": "tag"}} for r, s in self.refs.items()
                              if r.startswith(pre)])
        if "/git/tags/" in url:
            return Resp(200, {"message": self.tags[url.rsplit("/", 1)[1]]})
        return Resp(404)

    def delete(self, url):
        self.pedidos.append(("DELETE", url))
        self.refs.pop("refs/" + url.split("/git/refs/")[1] if "/git/refs/" in url else
                      url.split("/git/")[1], None)
        return Resp(204)


os.environ["GITHUB_SHA"] = "abc123"
cli = Cliente()
a = T.Fila(pid, token="x", repo="yo/repo", cliente=cli)
b = T.Fila(pid, token="x", repo="yo/repo", cliente=cli)
chequear("GitHub: el primero que pide el turno lo gana; el segundo recibe 422 y no publica",
         a.tomar(3, "policiales", "policial") and not b.tomar(3, "nacionales", "general"))
chequear("GitHub: la referencia vive en refs/turnos/<pasada>/<turno> (no es una rama)",
         "refs/turnos/20261018-1205/03" in cli.refs)
chequear("GitHub: el otro trabajo lee quién tiene cada turno y su categoría",
         b.ocupados() == {3: a.ocupados()[3]} and b.ocupados()[3]["categoria"] == "policial")
b.soltar(3)
chequear("GitHub: soltar borra la referencia", "refs/turnos/20261018-1205/03" not in cli.refs)
cli.refs["refs/turnos/20261010-0905/00"] = "t0"
a.barrer(datetime(2026, 10, 18, 12, 10, tzinfo=AR))
chequear("GitHub: barrer borra las referencias de hace más de 2 días", "refs/turnos/20261010-0905/00" not in cli.refs)


class Caido(Cliente):
    def post(self, url, json=None):
        raise ConnectionError("sin red")

    def get(self, url):
        raise ConnectionError("sin red")


c = T.Fila(pid, token="x", repo="yo/repo", cliente=Caido())
chequear("GitHub caído: se publica igual (perder la pasada sería peor) y queda el aviso",
         c.tomar(5, "nacionales", "general") and c.ocupados() == {} and c.avisos)
os.environ.pop("GITHUB_SHA")

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
