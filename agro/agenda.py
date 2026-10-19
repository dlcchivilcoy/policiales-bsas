# -*- coding: utf-8 -*-
"""La AGENDA del día de @diarioyradioagro: qué sale y a qué hora.

Pedido del editor (19/10/2026): «6 corridas por día (7, 10, 13, 16, 18 y 21 h); en cada una se scrapean
todas las fuentes, se arma y se publica: 1 reel y 1 carrusel intercalados, con 1 h entre posteo y
posteo». Las historias siguen en sus horarios de siempre (07:00, 14:00 y 19:00), dentro de la corrida que
las contiene:

    corrida 07   07:00 historias «El campo hoy» + reel     08:00 carrusel
    corrida 10   10:00 reel                                 11:00 carrusel
    corrida 13   13:00 reel                                 14:00 carrusel + historias del mediodía
    corrida 16   16:00 reel                                 17:00 carrusel
    corrida 18   18:00 reel                                 19:00 carrusel + historias «Así cerró el mercado»
    corrida 21   21:00 reel                                 22:00 carrusel

= 6 reels + 6 carruseles + 3 tandas de historias por día, reel y carrusel alternados todo el día.

Cada corrida es UNA corrida en la nube (cron-job.org a la hora exacta, con un respaldo 20 min después)
que publica lo suyo y espera hasta el horario siguiente (agro/pasada.py, correr_corrida). Entre dos
posteos del feed de la misma corrida hay siempre MARGEN_MIN: si el primero salió tarde, el segundo
también se corre. La memoria (estado/agro.json) frena al respaldo: lo que ya salió no se repite.

Se cambia sin tocar código con las variables del repo AGRO_AGENDA («07:00 historias, 07:00 reel, …») y
AGRO_CORRIDAS («07:00,10:00,…»).
"""
import os
from datetime import datetime, timedelta

AGENDA_DEFECTO = ("07:00 historias, 07:00 reel, 08:00 carrusel, "
                  "10:00 reel, 11:00 carrusel, "
                  "13:00 reel, 14:00 carrusel, 14:00 historias, "
                  "16:00 reel, 17:00 carrusel, "
                  "18:00 reel, 19:00 carrusel, 19:00 historias, "
                  "21:00 reel, 22:00 carrusel")
CORRIDAS_DEFECTO = "07:00,10:00,13:00,16:00,18:00,21:00"
MARGEN_MIN = 60              # entre dos posteos del feed (reel o carrusel) de la misma corrida
TIPOS = ("reel", "carrusel", "historias")
TOLERANCIA_MIN = 40          # una corrida que arranca hasta 40 min tarde es la de ese horario
ANTES_MIN = 5                # y hasta 5 min antes (el reloj de cron-job.org y el de GitHub)
BLOQUES = ("manana", "mediodia", "cierre")


def agenda() -> list:
    """[(hora, minuto, tipo), …] ordenada. Lo que no se entiende se saltea."""
    salida = []
    for parte in (os.environ.get("AGRO_AGENDA") or AGENDA_DEFECTO).split(","):
        bits = parte.split()
        if len(bits) != 2 or bits[1].lower() not in TIPOS:
            continue
        h, _, m = bits[0].partition(":")
        try:
            if 0 <= int(h) < 24 and 0 <= int(m or 0) < 60:
                salida.append((int(h), int(m or 0), bits[1].lower()))
        except ValueError:
            continue
    return sorted(set(salida)) or agenda_defecto()


def agenda_defecto() -> list:
    viejo = os.environ.pop("AGRO_AGENDA", None)
    try:
        return agenda()
    finally:
        if viejo is not None:
            os.environ["AGRO_AGENDA"] = viejo


def corridas() -> list:
    """[(hora, minuto), …] de AGRO_CORRIDAS, ordenadas. Lo que no se entiende se saltea."""
    salida = []
    for parte in (os.environ.get("AGRO_CORRIDAS") or CORRIDAS_DEFECTO).split(","):
        h, _, m = parte.strip().partition(":")
        try:
            if 0 <= int(h) < 24 and 0 <= int(m or 0) < 60:
                salida.append((int(h), int(m or 0)))
        except ValueError:
            continue
    return sorted(set(salida)) or [(7, 0), (10, 0), (13, 0), (16, 0), (18, 0), (21, 0)]


def _orden(item):
    """Mismo horario: primero las historias (no son del feed), después el reel o el carrusel."""
    t, tipo = item
    return t, tipo != "historias"


def corrida(ahora: datetime):
    """(inicio, en_horario, turnos): la corrida que corresponde a `ahora` y lo que publica, en orden:
    [(horario, tipo), …] = los horarios de la agenda desde su inicio hasta el de la corrida siguiente.
    Fuera de horario: la próxima corrida, con en_horario False."""
    inicios = [ahora.replace(hour=h, minute=m, second=0, microsecond=0) for h, m in corridas()]
    elegido, en_horario = None, False
    for t in inicios:
        if t - timedelta(minutes=ANTES_MIN) <= ahora <= t + timedelta(minutes=TOLERANCIA_MIN):
            elegido, en_horario = t, True
            break
    if elegido is None:
        futuros = [t for t in inicios if t > ahora]
        elegido = futuros[0] if futuros else inicios[0] + timedelta(days=1)
    dia = elegido.replace(hour=0, minute=0)
    del_dia = [dia.replace(hour=h, minute=m) for h, m in corridas()]
    siguiente = next((t for t in del_dia if t > elegido), dia + timedelta(days=1))
    turnos = sorted(((dia.replace(hour=h, minute=m), tipo) for h, m, tipo in agenda()
                     if elegido <= dia.replace(hour=h, minute=m) < siguiente), key=_orden)
    return elegido, en_horario, turnos


def turno(ahora: datetime):
    """(horario, tipo) de la corrida que corresponde a `ahora`, o (próximo horario, tipo, ) con
    `en_horario` False. Devuelve (datetime, tipo, en_horario)."""
    hoy = [(ahora.replace(hour=h, minute=m, second=0, microsecond=0), t) for h, m, t in agenda()]
    for t, tipo in hoy:
        if t - timedelta(minutes=ANTES_MIN) <= ahora <= t + timedelta(minutes=TOLERANCIA_MIN):
            return t, tipo, True
    futuros = [(t, tipo) for t, tipo in hoy if t > ahora]
    t, tipo = futuros[0] if futuros else (hoy[0][0] + timedelta(days=1), hoy[0][1])
    return t, tipo, False


def bloque(horario: datetime) -> str:
    """«manana», «mediodia» o «cierre»: cuál de las tandas de historias del día es la de `horario`."""
    horas = sorted((h, m) for h, m, t in agenda() if t == "historias")
    try:
        i = horas.index((horario.hour, horario.minute))
    except ValueError:
        i = 0 if horario.hour < 11 else 1 if horario.hour < 17 else 2
    return BLOQUES[min(i, len(BLOQUES) - 1)]


def cuantos(tipo: str) -> int:
    return sum(1 for *_, t in agenda() if t == tipo)


def es_primer_carrusel_del_sabado(horario: datetime) -> bool:
    """El carrusel de datos «Los números de la semana» sale en el primer horario de carrusel del sábado."""
    if horario.weekday() != 5:
        return False
    carr = sorted((h, m) for h, m, t in agenda() if t == "carrusel")
    return bool(carr) and (horario.hour, horario.minute) == carr[0]
