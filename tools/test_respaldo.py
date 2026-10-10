# -*- coding: utf-8 -*-
"""El respaldo corre solo si la pasada de cron-job.org no corrió o se cortó (10/10/2026). Sin red."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from tools import respaldo as R  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


AHORA = datetime(2026, 10, 10, 15, 40, tzinfo=timezone.utc)      # el respaldo de las 15:05 UTC, tarde


def job(nombre, paso, conclusion):
    return {"name": nombre, "steps": [{"name": "Set up job", "conclusion": "success"},
                                      {"name": paso, "conclusion": conclusion}]}


PUBLICAR = "Publicar en Instagram, Facebook y YouTube"
pedidas = []


def corridas_con(lista):
    def f(desde):
        pedidas.append(desde)
        return [{"id": i, "created_at": "x"} for i in range(len(lista))]
    return f


def jobs_con(lista):
    return lambda run_id: lista[run_id]


flags, motivo = R.decidir("workflow_dispatch", "", AHORA, None, None)
chequear("la pasada de cron-job.org (workflow_dispatch) corre siempre", all(flags.values()))

pasada_ok = [job("generar", PUBLICAR, "success"), job("nacionales", "Noticias nacionales", "success")]
flags, motivo = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([pasada_ok]), jobs_con([pasada_ok]))
chequear("respaldo: si la pasada de ese horario publicó, NO corre ninguno de los dos", not any(flags.values()))
chequear("...y busca desde 15 minutos antes del horario", pedidas[-1] == datetime(2026, 10, 10, 14, 50, tzinfo=timezone.utc))

con_falla = [job("generar", PUBLICAR, "failure"), job("nacionales", "Noticias nacionales", "failure")]
flags, _ = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([con_falla]), jobs_con([con_falla]))
chequear("una pasada que publicó con alguna red fallada cuenta como hecha (la siguiente reintenta)",
         not any(flags.values()))

flags, motivo = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([]), jobs_con([]))
chequear("si cron-job.org no disparó, el respaldo CORRE los dos", all(flags.values()) and "CORRE" in motivo)

sin_maquina = [{"name": "generar", "steps": []}, {"name": "nacionales", "steps": []}]
flags, _ = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([sin_maquina]), jobs_con([sin_maquina]))
chequear("si GitHub la cortó sin pasos (sin máquina), el respaldo CORRE", all(flags.values()))

media = [job("generar", PUBLICAR, "skipped"), job("nacionales", "Noticias nacionales", "success")]
flags, _ = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([media]), jobs_con([media]))
chequear("se decide por trabajo: policiales no llegó a publicar (corre), nacionales sí (no corre)",
         flags == {"policiales": True, "nacionales": False})

cancelada = [job("generar", PUBLICAR, "cancelled"), job("nacionales", "Noticias nacionales", "cancelled")]
flags, _ = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([cancelada, pasada_ok]),
                     jobs_con([cancelada, pasada_ok]))
chequear("una cancelada y otra completa en la ventana (la siguiente pasada): no corre", not any(flags.values()))

simulada = [job("generar", "Simular la publicación (no se publica nada)", "success")]
flags, _ = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([simulada]), jobs_con([simulada]))
chequear("una pasada que simuló (publicación apagada) también cuenta para policiales", flags["policiales"] is False)

chequear("horario: el de las 23:35 ARG (2:35 UTC) largado a las 3:10 es de hoy",
         R.horario_del_respaldo("35 2 * * *", datetime(2026, 10, 10, 3, 10, tzinfo=timezone.utc))
         == datetime(2026, 10, 10, 2, 35, tzinfo=timezone.utc))
chequear("horario: si todavía no llegó la hora, es el de ayer",
         R.horario_del_respaldo("5 21 * * *", datetime(2026, 10, 10, 0, 30, tzinfo=timezone.utc))
         == datetime(2026, 10, 9, 21, 5, tzinfo=timezone.utc))


def explota(desde):
    raise OSError("sin red")


vieja = [job("generar", "Publicar en Instagram (prueba), Facebook y YouTube", "success")]
flags, _ = R.decidir("schedule", "5 15 * * *", AHORA, corridas_con([vieja]), jobs_con([vieja]))
chequear("una corrida con el nombre VIEJO del paso («… (prueba) …») también cuenta", flags["policiales"] is False)

flags, motivo = R.decidir("schedule", "5 15 * * *", AHORA, explota, None)
chequear("si no puede mirar GitHub, corre por las dudas (mejor repetir nada que perder la pasada)",
         all(flags.values()) and "por las dudas" in motivo)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
