# -*- coding: utf-8 -*-
"""La noticia DEL MOMENTO primero, sea cual sea el tema (pedido del editor, 27/09/2026).

«Lo que necesito es que, sea cual sea la temática, sea la última del día, del momento.»
Había salido una pasada con los dos lugares de Facebook e Instagram para el clima, y uno
de ellos era un temporal de horas antes.

Cómo se decide, en una sola cuenta:

    puntos = viral de la IA (1-10) + cercanía a Chivilcoy (0-3) - PUNTOS_POR_HORA × horas

donde «horas» es cuánto más vieja es la nota que la más nueva de la pasada. Con 4 por
hora, una nota una hora más vieja necesita 4 puntos más para ganar: en la práctica gana
la más nueva, y la viralidad y la cercanía solo desempatan entre notas de minutos de
diferencia. La hora es la de publicación en el medio de origen.
"""
from datetime import datetime, timezone

PUNTOS_POR_HORA = 4
# Una nota sin hora conocida cuenta como de hace 6 horas: sin poder probar que es del
# momento, no le gana el lugar a una que sí.
HORAS_SIN_FECHA = 6


def momento(publicado):
    """datetime con zona, o None. Sin zona = UTC, como las entrega feedparser (igual que
    scraper/run.py: _momento)."""
    if not publicado:
        return None
    try:
        d = datetime.fromisoformat(str(publicado).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d


def publicado_utc(nota: dict) -> str:
    """La hora de publicación de la nota en UTC ISO, o "" si no se sabe."""
    d = momento(nota.get("publicado"))
    return d.astimezone(timezone.utc).isoformat(timespec="minutes") if d else ""


def edades(piezas: list) -> list:
    """Horas de atraso de cada pieza respecto de la MÁS NUEVA de la lista (0 = la más
    nueva). Relativo y no contra el reloj: así no depende de la zona horaria de la
    máquina. Si ninguna tiene hora, todas 0 (lotes de antes del 27/09)."""
    ms = [momento(p.get("publicado")) for p in piezas]
    conocidas = [m for m in ms if m]
    if not conocidas:
        return [0.0] * len(piezas)
    tope = max(conocidas)
    return [((tope - m).total_seconds() / 3600) if m else float(HORAS_SIN_FECHA) for m in ms]


def ordenar(notas: list) -> list:
    """Las más nuevas primero; las sin hora, al final (en su orden)."""
    minimo = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(notas, key=lambda n: momento(n.get("publicado")) or minimo, reverse=True)


def hace(horas: float) -> str:
    if horas < 1:
        return f"{round(horas * 60)} min más vieja que la más nueva"
    return f"{horas:.1f} h más vieja que la más nueva".replace(".", ",")
