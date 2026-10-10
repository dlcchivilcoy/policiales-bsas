# -*- coding: utf-8 -*-
"""¿Tiene que correr la pasada de RESPALDO? Solo si la de cron-job.org no corrió o se cortó.

Pedido del editor (10/10/2026): «que el respaldo corra solo si falla la pasada».

Contexto: las pasadas las dispara cron-job.org a horario exacto (workflow_dispatch con
origen=cron). El `schedule:` de GitHub en reels.yml es el RESPALDO de esas mismas horas, pero
GitHub lo larga 20 min a 3 h tarde y casi siempre: hasta el 10/10 contaba como una pasada más
(hasta ~12 por día en vez de 6), y con Instagram a 5 reels por pasada eso duplicaba los posteos.

Qué decide, para cada trabajo por separado (policiales y nacionales):
- Si la corrida NO es del schedule (cron-job.org, a mano): corre siempre.
- Si es del schedule: busca las corridas workflow_dispatch desde el horario de ese respaldo
  (−15 min) hasta ahora. Si en ALGUNA el paso principal del trabajo TERMINÓ —bien o con alguna
  red fallada: ya publicó y anotó, la pasada siguiente reintenta lo que faltó—, el respaldo no
  corre. Si no hubo ninguna, o en todas el paso principal no llegó a terminar (GitHub sin
  máquina, cancelada, colgada, se cortó antes de publicar), corre.
Como el workflow tiene un grupo de concurrencia, el respaldo arranca recién cuando terminó la
pasada que tenía delante: lo que mira ya está cerrado.

Solo biblioteca estándar (corre con el python3 de la máquina, antes de instalar nada).
Escribe `policiales=true|false` y `nacionales=true|false` en $GITHUB_OUTPUT.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# El paso que dice «esta pasada publicó» en cada trabajo: cómo EMPIEZA su nombre en reels.yml
# (por el arranque y no el nombre entero: el 10/10 «Publicar en Instagram (prueba), …» pasó a
# «Publicar en Instagram, …» y las corridas viejas tienen que seguir contando).
PASOS = {
    "policiales": ("generar", ("Publicar en Instagram", "Simular la publicación")),
    "nacionales": ("nacionales", ("Noticias nacionales",)),
}
TERMINADO = ("success", "failure")      # llegó al final (con o sin alguna red fallada)
MARGEN_ANTES = timedelta(minutes=15)


def horario_del_respaldo(cron: str, ahora: datetime) -> datetime:
    """El horario (UTC) al que corresponde este respaldo: «5 12 * * *» → hoy 12:05, o ayer si
    todavía no llegó (un respaldo de las 23:35 que GitHub larga pasada la medianoche)."""
    minuto, hora = (int(x) for x in cron.split()[:2])
    h = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return h if h <= ahora else h - timedelta(days=1)


def paso_terminado(jobs: list, trabajo: str, pasos: tuple) -> bool:
    for j in jobs:
        if j.get("name") != trabajo:
            continue
        for s in j.get("steps") or []:
            if (s.get("name") or "").startswith(pasos) and s.get("conclusion") in TERMINADO:
                return True
    return False


def decidir(evento: str, cron: str, ahora: datetime, corridas, jobs_de) -> tuple:
    """({trabajo: correr}, motivo). `corridas(desde)` lista las workflow_dispatch desde esa
    hora; `jobs_de(id)` da los trabajos de una corrida. Se reemplazan en las pruebas."""
    if evento != "schedule":
        return {t: True for t in PASOS}, f"corrida «{evento}»: no es el respaldo, corre"
    try:
        desde = horario_del_respaldo(cron, ahora) - MARGEN_ANTES
    except (ValueError, AttributeError):
        return {t: True for t in PASOS}, f"no se entiende el horario «{cron}»: corre por las dudas"
    try:
        lista = corridas(desde)
    except Exception as e:                         # noqa: BLE001 — sin datos, mejor correr
        return {t: True for t in PASOS}, f"no se pudo mirar GitHub ({e}): corre por las dudas"
    salida, motivos = {}, []
    for trabajo, (job, pasos) in PASOS.items():
        hecha = None
        for c in lista:
            try:
                if paso_terminado(jobs_de(c["id"]), job, pasos):
                    hecha = c
                    break
            except Exception:                      # noqa: BLE001 — esa corrida no se pudo leer
                continue
        salida[trabajo] = hecha is None
        motivos.append(f"{trabajo}: " + (f"ya la hizo la corrida {hecha['id']} ({hecha.get('created_at')}), "
                                         f"el respaldo NO corre" if hecha else
                                         "ninguna pasada la terminó desde ese horario, el respaldo CORRE"))
    return salida, f"respaldo del horario {desde + MARGEN_ANTES:%H:%M} UTC — " + "; ".join(motivos)


def _api(ruta: str) -> dict:
    req = urllib.request.Request(f"https://api.github.com{ruta}", headers={
        "Authorization": f"Bearer {os.environ.get('GH_TOKEN', '')}",
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    repo = os.environ.get("REPO", "dlcchivilcoy/policiales-bsas")
    ahora = datetime.now(timezone.utc)

    def corridas(desde):
        d = _api(f"/repos/{repo}/actions/workflows/reels.yml/runs?event=workflow_dispatch&per_page=30"
                 f"&created=%3E%3D{desde:%Y-%m-%dT%H:%M:%SZ}")
        return d.get("workflow_runs") or []

    def jobs_de(run_id):
        return _api(f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=50").get("jobs") or []

    flags, motivo = decidir(os.environ.get("EVENTO", ""), os.environ.get("CRON", ""), ahora, corridas, jobs_de)
    print(motivo)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            for t, v in flags.items():
                f.write(f"{t}={'true' if v else 'false'}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"### Respaldo\n\n{motivo}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
