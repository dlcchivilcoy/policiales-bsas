# -*- coding: utf-8 -*-
"""La AGENDA del día de @diarioyradioagro: qué sale y a qué hora.

Pedido del editor (17/10/2026): «3 reels + 3 carruseles + 10 historias repartido en 3 corridas; en cada
corrida, margen de 1 h por posteo». Cada corrida tiene tres horarios separados por una hora y en cada
uno sale UNA cosa (la tanda de historias cuenta como una: es una secuencia que se mira seguida):

    corrida 1   07:00 historias «El campo hoy» (4)   08:00 reel   09:00 carrusel
    corrida 2   12:00 reel   13:00 carrusel   14:00 historias (3: mapa de lluvias, Chicago, la novedad)
    corrida 3   19:00 historias «Así cerró el mercado» (3)   20:00 reel   21:00 carrusel

Cada horario es una corrida propia en la nube (cron-job.org a la hora exacta, con un respaldo 20 min
después): así un posteo nunca espera a otro y una falla no arrastra a los siguientes. Se cambia sin
tocar código con la variable del repo AGRO_AGENDA («07:00 historias, 08:00 reel, …»).
"""
import os
from datetime import datetime, timedelta

AGENDA_DEFECTO = ("07:00 historias, 08:00 reel, 09:00 carrusel, "
                  "12:00 reel, 13:00 carrusel, 14:00 historias, "
                  "19:00 historias, 20:00 reel, 21:00 carrusel")
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
