# -*- coding: utf-8 -*-
"""Reemplazo de utils/logger.py del bot: avisos y errores del motor de reels a la consola.

Solo WARNING para arriba: los INFO del bot ("Foto-reel: 1 foto compuesta...") son ruido en
una tanda de policiales, pero un aviso de que algo se degrado tiene que verse.
"""
import logging
import sys


def get_logger(nombre: str) -> logging.Logger:
    log = logging.getLogger(f"estetica_bot.{nombre}")
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("      [reel] %(levelname)s %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.WARNING)
        log.propagate = False
    return log
