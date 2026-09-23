# -*- coding: utf-8 -*-
"""Busca paquetes que el codigo importa y requirements.txt no declara.

Por que existe: faltaban pillow e imageio-ffmpeg. Localmente no se notaba —
estaban en el venv de siempre— pero en la nube `pip install -r requirements.txt`
no las instalaba y el paso de reels moria en el primer import. Dos pasadas
completas trajeron las noticias y no armaron ni una pieza.

Es el tipo de error que no se ve probando en la maquina propia: hay que comparar
lo que el codigo pide contra lo que el archivo promete.

Correr:  venv\\Scripts\\python.exe tools\\verificar_requirements.py
"""
import ast
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paquetes locales del proyecto: no van en requirements.
PROPIOS = {"scraper", "reels", "tools", "entorno", "salud"}

# El nombre con que se importa no siempre es el nombre con que se instala.
ALIAS = {
    "PIL": "pillow",
    "imageio_ffmpeg": "imageio-ffmpeg",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "yaml": "pyyaml",
}


def _importados():
    nombres = set()
    for base, _, archivos in os.walk(RAIZ):
        if any(p in base for p in ("venv", "__pycache__", ".git")):
            continue
        for a in archivos:
            if not a.endswith(".py"):
                continue
            ruta = os.path.join(base, a)
            try:
                arbol = ast.parse(open(ruta, encoding="utf-8").read())
            except Exception:
                continue
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    for n in nodo.names:
                        nombres.add(n.name.split(".")[0])
                elif isinstance(nodo, ast.ImportFrom):
                    if nodo.level == 0 and nodo.module:
                        nombres.add(nodo.module.split(".")[0])
    return nombres


def _declarados():
    ruta = os.path.join(RAIZ, "requirements.txt")
    fuera = set()
    for linea in open(ruta, encoding="utf-8"):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        fuera.add(re.split(r"[<>=!\[ ]", linea)[0].strip().lower())
    return fuera


def main():
    importados = _importados()
    declarados = _declarados()
    stdlib = set(sys.stdlib_module_names)

    faltan = []
    for nombre in sorted(importados):
        if nombre in stdlib or nombre in PROPIOS or nombre.startswith("_"):
            continue
        paquete = ALIAS.get(nombre, nombre).lower()
        if paquete not in declarados:
            faltan.append((nombre, paquete))

    if faltan:
        print("FALTAN en requirements.txt (el codigo las importa):")
        for imp, paq in faltan:
            print(f"   import {imp:<20} -> falta '{paq}'")
        return 1

    print(f"OK — los {len(declarados)} paquetes declarados cubren todo lo que se importa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
