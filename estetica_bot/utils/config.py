# -*- coding: utf-8 -*-
"""Reemplazo de utils/config.py del bot: la configuracion sale de las variables de entorno.

El bot lee su .env (con todas sus credenciales). Aca no hace falta nada de eso: el motor
de reels solo lee perillas REEL_*, y las que usa policiales las pone reels/reel_bot.py.
"""
import os


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)
