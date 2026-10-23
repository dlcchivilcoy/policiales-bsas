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

20/10/2026 (pedido del editor: «en cada corrida necesito 5 reels publicados cada 20 minutos, y cada reel
tiene que provenir de una web distinta; en total deberían ser 30 reels por día»): cada corrida publica
POR_CORRIDA reels (5), uno cada INTERVALO_MIN (20), sin carruseles; las historias, igual que antes:

    corrida 07   07:00 historias + reel · 07:20 · 07:40 · 08:00 · 08:20
    corrida 10   10:00 · 10:20 · 10:40 · 11:00 · 11:20
    corrida 13   13:00 · 13:20 · 13:40 · 14:00 (+ historias del mediodía) · 14:20
    corrida 16   16:00 · 16:20 · 16:40 · 17:00 · 17:20
    corrida 18   18:00 · 18:20 · 18:40 · 19:00 (+ historias «Así cerró el mercado») · 19:20
    corrida 21   21:00 · 21:20 · 21:40 · 22:00 · 22:20

= 30 reels + 3 tandas de historias. Cada reel de la corrida viene de un sitio distinto (agro/pasada.py).
AGRO_POR_CORRIDA y AGRO_INTERVALO_MIN los cambian; AGRO_AGENDA sigue pisando todo.

Cada corrida es UNA corrida en la nube (cron-job.org a la hora exacta, con un respaldo 20 min después)
que publica lo suyo y espera hasta el horario siguiente (agro/pasada.py, correr_corrida). Entre dos
posteos del feed de la misma corrida hay siempre intervalo_min(): si el primero salió tarde, el segundo
también se corre. La memoria (estado/agro.json) frena al respaldo: lo que ya salió no se repite.

Se cambia sin tocar código con las variables del repo AGRO_AGENDA («07:00 historias, 07:00 reel, …») y
AGRO_CORRIDAS («07:00,10:00,…»).
"""
import os
from datetime import datetime, timedelta

HISTORIAS_DEFECTO = ((7, 0), (14, 0), (19, 0))
CORRIDAS_DEFECTO = "07:00,10:00,13:00,16:00,18:00,21:00"
POR_CORRIDA = 5              # reels por corrida (20/10/2026)
INTERVALO_MIN = 20           # entre un reel y el siguiente de la misma corrida
TIPOS = ("reel", "carrusel", "historias", "reel_datos")
# 23/10/2026: el REEL DE DATOS de cada mañana (agro/reel_datos.py), con su propia corrida. AGRO_REEL_DATOS
# cambia la hora; "0" lo apaga.
REEL_DATOS_DEFECTO = "05:00"
TOLERANCIA_MIN = 40          # una corrida que arranca hasta 40 min tarde es la de ese horario
ANTES_MIN = 5                # y hasta 5 min antes (el reloj de cron-job.org y el de GitHub)
BLOQUES = ("manana", "mediodia", "cierre")


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(1, int((os.environ.get(nombre) or "").strip()))
    except ValueError:
        return defecto


def por_corrida() -> int:
    return _entero("AGRO_POR_CORRIDA", POR_CORRIDA)


def intervalo_min() -> int:
    """Entre dos posteos del feed de la misma corrida (si el primero salió tarde, el segundo también se corre)."""
    return _entero("AGRO_INTERVALO_MIN", INTERVALO_MIN)


def agenda_texto_defecto() -> str:
    """Por cada corrida, por_corrida() reels cada intervalo_min(), sin pasarse de la corrida siguiente;
    más las historias de siempre."""
    inicios = [h * 60 + m for h, m in corridas_noticias()]
    partes = [f"{h:02d}:{m:02d} historias" for h, m in HISTORIAS_DEFECTO]
    datos = hora_reel_datos()
    if datos:
        partes.append(f"{datos[0]:02d}:{datos[1]:02d} reel_datos")
    for i, ini in enumerate(inicios):
        fin = inicios[i + 1] if i + 1 < len(inicios) else 24 * 60
        partes += [f"{t // 60:02d}:{t % 60:02d} reel"
                   for t in (ini + k * intervalo_min() for k in range(por_corrida())) if t < fin]
    return ", ".join(partes)


def agenda() -> list:
    """[(hora, minuto, tipo), …] ordenada. Lo que no se entiende se saltea."""
    salida = []
    for parte in (os.environ.get("AGRO_AGENDA") or agenda_texto_defecto()).split(","):
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


def hora_reel_datos():
    """(hora, minuto) del reel de datos, o None si está apagado (AGRO_REEL_DATOS="0")."""
    crudo = (os.environ.get("AGRO_REEL_DATOS") or REEL_DATOS_DEFECTO).strip()
    if crudo.lower() in ("0", "no", "off"):
        return None
    h, _, m = crudo.partition(":")
    try:
        if 0 <= int(h) < 24 and 0 <= int(m or 0) < 60:
            return int(h), int(m or 0)
    except ValueError:
        pass
    return 5, 0


def corridas() -> list:
    """Las corridas del día: las de noticias y, si está prendido, la del reel de datos."""
    datos = hora_reel_datos()
    return sorted(set(corridas_noticias() + ([datos] if datos else [])))


def corridas_noticias() -> list:
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


def inicio_corrida(horario: datetime):
    """El inicio de la corrida a la que pertenece `horario` (la última que arrancó ese día), o None."""
    previos = [horario.replace(hour=h, minute=m, second=0, microsecond=0) for h, m in corridas()]
    previos = [t for t in previos if t <= horario]
    return previos[-1] if previos else None


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
