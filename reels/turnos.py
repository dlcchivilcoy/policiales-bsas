# -*- coding: utf-8 -*-
"""LA FILA DE CADA PASADA: un posteo cada 15 minutos, de una categoría distinta cada vez.

Pedido del editor (18/10/2026): «subí el total de las notas elegidas en cada corrida cada 15 minutos,
estimo que serán máximo 12 por pasada… un posteo de categoría diferente». Entran TODOS en la misma
fila: policiales, nacionales generales y la variedad (deportes, espectáculos, mundo, cine y series, IA,
virales). La pasada de las 23:35 también completa sus 12 (hasta ~02:35).

Cómo se reparte:
- Cada pasada (reels/cupo.py, PASADAS_AR) tiene su GRILLA: el primer turno 15 minutos después del
  horario (le da tiempo a leer los medios y armar la primera pieza) y uno cada 15 minutos, hasta 12 o
  hasta el primer turno de la pasada siguiente (la de las 21:05 tiene 10: 21:20 → 23:35).
- Policiales y nacionales son dos trabajos que corren a la vez en máquinas distintas. Cada turno se
  TOMA creando una referencia de git en el propio repo (refs/turnos/<pasada>/<turno>): crearla es
  atómico, si ya existe GitHub contesta 422 y ese turno es del otro. La referencia apunta a una
  etiqueta con quién lo tomó y su categoría. No son ramas: no disparan workflows ni se ven como ramas.
- Policiales (hasta 3 por pasada) RESERVA sus turnos apenas sabe cuántos hechos salen, repartidos en
  la pasada y nunca dos seguidos. Nacionales toma el turno libre que sigue, de a uno, en el momento.
- Sin GITHUB_TOKEN (simulaciones, pruebas) la fila vive en memoria.

Las referencias de pasadas viejas se borran solas (barrer, 2 días).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from reels import cupo as CUPO

TZ_AR = timezone(timedelta(hours=-3))
MINUTOS = 15                   # entre un posteo y el siguiente
DEMORA_PRIMERO = 15            # el primer turno, a los 15 minutos del horario de la pasada
POR_PASADA = 12                # turnos por pasada, como mucho
TOLERANCIA_ATRASO = timedelta(minutes=3)   # un turno que empezó hace menos que esto todavía se usa
API = "https://api.github.com"
PREFIJO = "turnos"
DIAS_BARRIDO = 2


def activa() -> bool:
    """FILA_15=0 vuelve al reparto viejo (cada trabajo con su espaciado propio)."""
    return (os.environ.get("FILA_15") or "1").strip() != "0"


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(1, int(os.environ.get(nombre) or defecto))
    except ValueError:
        return defecto


def por_pasada() -> int:
    return _entero("FILA_POR_PASADA", POR_PASADA)


def inicio(pid: str) -> datetime:
    """«2026-10-18T12:05» → ese momento en hora argentina."""
    return datetime.strptime(pid, "%Y-%m-%dT%H:%M").replace(tzinfo=TZ_AR)


def _siguiente_pasada(desde: datetime) -> datetime:
    candidatos = [desde.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=d)
                  for d in (0, 1) for h, m in CUPO.PASADAS_AR]
    return min(c for c in candidatos if c > desde)


def grilla(pid: str) -> list:
    """Los horarios de los turnos de la pasada `pid`, en hora argentina."""
    t0 = inicio(pid) + timedelta(minutes=DEMORA_PRIMERO)
    fin = _siguiente_pasada(inicio(pid)) + timedelta(minutes=DEMORA_PRIMERO)
    n = min(por_pasada(), int((fin - t0).total_seconds() // (MINUTOS * 60)))
    return [t0 + timedelta(minutes=MINUTOS * k) for k in range(max(1, n))]


def pasada_actual(ahora: datetime = None) -> str:
    return CUPO.pasada_id(CUPO.PASADAS_AR, ahora or datetime.now(TZ_AR))


def _compacto(pid: str) -> str:
    return pid.replace("-", "").replace("T", "-").replace(":", "")


class Fila:
    """Los turnos de UNA pasada. `ocupados()` → {turno: {quien, categoria, titular}}; `tomar()` es
    atómico: True si el turno quedó para quien lo pidió."""

    def __init__(self, pid: str, token: str = None, repo: str = None, cliente=None):
        self.pid = pid
        self.token = os.environ.get("GITHUB_TOKEN", "") if token is None else token
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
        self.local = not (self.token and self.repo)
        self._memoria = {}           # modo local
        self._etiquetas = {}         # sha de la etiqueta → datos (no cambian nunca)
        self._cliente = cliente
        self.avisos = []

    # ── HTTP ──────────────────────────────────────────────────────────────
    def _http(self):
        if self._cliente is None:
            import httpx
            self._cliente = httpx.Client(timeout=20, headers={
                "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"})
        return self._cliente

    def _ref(self, k: int) -> str:
        return f"{PREFIJO}/{_compacto(self.pid)}/{k:02d}"

    def _aviso(self, texto: str):
        if texto not in self.avisos:
            self.avisos.append(texto)
            print(f"  (fila de turnos: {texto})", flush=True)

    # ── Lo que usan los trabajos ─────────────────────────────────────────
    def ocupados(self) -> dict:
        if self.local:
            return dict(self._memoria)
        try:
            r = self._http().get(f"{API}/repos/{self.repo}/git/matching-refs/{PREFIJO}/{_compacto(self.pid)}/")
            r.raise_for_status()
            salida = {}
            for ref in r.json() or []:
                k = int(ref["ref"].rsplit("/", 1)[-1])
                obj = ref.get("object") or {}
                salida[k] = self._datos(obj.get("sha"), obj.get("type"))
            return salida
        except Exception as e:                        # noqa: BLE001 — sin la fila se sigue igual
            self._aviso(f"no se pudo leer ({type(e).__name__}: {str(e)[:80]})")
            return {}

    def _datos(self, sha: str, tipo: str) -> dict:
        if tipo != "tag" or not sha:
            return {"quien": "?", "categoria": "?"}
        if sha not in self._etiquetas:
            try:
                r = self._http().get(f"{API}/repos/{self.repo}/git/tags/{sha}")
                r.raise_for_status()
                self._etiquetas[sha] = json.loads((r.json() or {}).get("message") or "{}")
            except Exception:                         # noqa: BLE001
                return {"quien": "?", "categoria": "?"}
        return self._etiquetas[sha]

    def tomar(self, k: int, quien: str, categoria: str, titular: str = "") -> bool:
        datos = {"quien": quien, "categoria": categoria, "titular": (titular or "")[:120],
                 "cuando": datetime.now(TZ_AR).isoformat(timespec="seconds")}
        if self.local:
            if k in self._memoria:
                return False
            self._memoria[k] = datos
            return True
        try:
            base = os.environ.get("GITHUB_SHA") or self._punta()
            r = self._http().post(f"{API}/repos/{self.repo}/git/tags", json={
                "tag": "turno", "message": json.dumps(datos, ensure_ascii=False), "object": base,
                "type": "commit"})
            r.raise_for_status()
            sha = r.json()["sha"]
            r = self._http().post(f"{API}/repos/{self.repo}/git/refs",
                                  json={"ref": f"refs/{self._ref(k)}", "sha": sha})
            if r.status_code == 422:                  # ya lo tomó el otro trabajo
                return False
            r.raise_for_status()
            self._etiquetas[sha] = datos
            return True
        except Exception as e:                        # noqa: BLE001
            # GitHub no contesta: se publica igual (perder la pasada sería peor que un choque).
            self._aviso(f"no se pudo anotar el turno {k} ({type(e).__name__}: {str(e)[:80]}); "
                        f"se publica igual")
            return True

    def soltar(self, k: int):
        """Devuelve un turno reservado que al final no se usó (lo toma nacionales)."""
        if self.local:
            self._memoria.pop(k, None)
            return
        try:
            self._http().delete(f"{API}/repos/{self.repo}/git/refs/{self._ref(k)}")
        except Exception:                             # noqa: BLE001
            pass

    def _punta(self) -> str:
        r = self._http().get(f"{API}/repos/{self.repo}/git/ref/heads/main")
        r.raise_for_status()
        return r.json()["object"]["sha"]

    def barrer(self, ahora: datetime = None):
        """Borra las referencias de pasadas de hace más de DIAS_BARRIDO días."""
        if self.local:
            return
        limite = _compacto(((ahora or datetime.now(TZ_AR)) - timedelta(days=DIAS_BARRIDO))
                           .strftime("%Y-%m-%dT%H:%M"))
        try:
            r = self._http().get(f"{API}/repos/{self.repo}/git/matching-refs/{PREFIJO}/")
            r.raise_for_status()
            for ref in r.json() or []:
                partes = ref["ref"].split("/")
                if len(partes) >= 4 and partes[2] < limite:
                    self._http().delete(f"{API}/repos/{self.repo}/git/{ref['ref']}")    # git/refs/turnos/…
        except Exception:                             # noqa: BLE001 — limpiar nunca frena nada
            pass


# =============================================================================
# Policiales: reservar sus turnos repartidos en la pasada
# =============================================================================

def libres(fila: Fila, ahora: datetime) -> list:
    """[(turno, hora)] que todavía no tomó nadie y no pasaron."""
    ocupados = fila.ocupados()
    return [(k, t) for k, t in enumerate(grilla(fila.pid))
            if k not in ocupados and t >= ahora - TOLERANCIA_ATRASO]


def _policiales(ocupados: dict) -> set:
    return {k for k, d in ocupados.items() if (d or {}).get("categoria") == "policial"}


def plan_policiales(fila: Fila, n: int, ahora: datetime) -> list:
    """Hasta `n` turnos libres para policiales, repartidos en lo que queda de la pasada y nunca dos
    seguidos (ni pegados a uno policial que ya estaba). [(turno, hora)], sin tomarlos."""
    if n <= 0:
        return []
    disponibles = libres(fila, ahora)
    if not disponibles:
        return []
    ya = _policiales(fila.ocupados())
    primero, ultimo = disponibles[0][0], len(grilla(fila.pid)) - 1
    paso = max(2, (ultimo - primero + 1) // n)
    elegidos, objetivo = [], primero
    for _ in range(n):
        opcion = next(((k, t) for k, t in disponibles if k >= objetivo
                       and all(abs(k - e) >= 2 for e in [x for x, _t in elegidos] + list(ya))), None)
        if opcion is None:
            break
        elegidos.append(opcion)
        objetivo = opcion[0] + paso
    return elegidos


def reservar_policiales(fila: Fila, n: int, ahora: datetime, titulares: list = None) -> list:
    """Toma los turnos de `plan_policiales`. Si otro trabajo ganó alguno, vuelve a planear. [(turno, hora)]."""
    tomados = []
    for _intento in range(4):
        faltan = n - len(tomados)
        if faltan <= 0:
            break
        plan = [x for x in plan_policiales(fila, faltan, ahora) if x[0] not in {k for k, _t in tomados}]
        if not plan:
            break
        for k, t in plan:
            titular = titulares[len(tomados)] if titulares and len(tomados) < len(titulares) else ""
            if fila.tomar(k, "policiales", "policial", titular):
                tomados.append((k, t))
    return sorted(tomados)
