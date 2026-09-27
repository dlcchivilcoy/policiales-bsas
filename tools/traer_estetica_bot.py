# -*- coding: utf-8 -*-
"""Trae el motor de reels del BOT DEL DIARIO a estetica_bot/, tal cual, sin tocarlo.

    venv\\Scripts\\python.exe tools\\traer_estetica_bot.py
    venv\\Scripts\\python.exe tools\\traer_estetica_bot.py --bot C:\\otra\\ruta\\social_publisher

Por que COPIA y no reescribe: los reels de policiales tienen que salir con la MISMA
estetica que los del bot (pedido del editor, 26/09/2026). Antes se habia reimplementado
a mano el estilo del 18/09, y a la semana el bot ya lo habia cambiado dos veces: una
copia hecha a mano se separa sola. Con el archivo del bot tal cual, ponerse al dia es
correr esto de nuevo.

Que NO se copia: utils/ (el bot lee su .env; aca hay un reemplazo chico en
estetica_bot/utils que lee las variables de entorno) y nada con credenciales.

⚠️ Este repo es PUBLICO y el del bot es PRIVADO. Antes de copiar se revisa que los
archivos no traigan nada que parezca una clave, un mail o un telefono: si aparece, se
frena y no se copia nada.
"""
import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "estetica_bot"
BOT_DEFAULT = Path(r"C:\Users\Diario\social_publisher")

# Lo que usa el motor de reels. video.py es el motor; story_image.py pone las caras
# (el encuadre que no corta cabezas); el resto son la marca y las letras.
CODIGO = ["video.py", "story_image.py"]
ASSETS = ["logo_reel.png", "placa_final.png", "fondo_reel.png", "overlay_reel.png", "logo.png"]
FUENTES = "fonts"

# Cosas que NO pueden terminar en un repo publico.
SOSPECHOSO = [
    (r"EAA[A-Za-z0-9]{40,}", "token de Meta"),
    (r"ya29\.[0-9A-Za-z_-]{20,}", "token de Google"),
    (r"AIza[0-9A-Za-z_-]{30,}", "clave de Google"),
    (r"gh[pousr]_[0-9A-Za-z]{30,}", "token de GitHub"),
    (r"sk-ant-[0-9A-Za-z_-]{20,}", "clave de Anthropic"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "clave privada"),
    (r"[\w.+-]+@(gmail|hotmail|yahoo|outlook)\.com", "mail"),
    (r"\+?54\s?9?\s?\d{2,4}[\s-]?\d{2,4}[\s-]?\d{4}", "telefono"),
]


def _git(bot: Path, *args) -> str:
    try:
        r = subprocess.run(["git", "-C", str(bot), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def revisar(bot: Path) -> list:
    """Lo que parezca un dato privado en el codigo a copiar. Vacio = se puede copiar."""
    hallazgos = []
    for nombre in CODIGO:
        texto = (bot / nombre).read_text(encoding="utf-8", errors="replace")
        for patron, que in SOSPECHOSO:
            for m in re.finditer(patron, texto):
                linea = texto.count("\n", 0, m.start()) + 1
                hallazgos.append(f"{nombre}:{linea} parece {que}")
    return hallazgos


def traer(bot: Path) -> dict:
    faltan = [n for n in CODIGO + ASSETS + [FUENTES] if not (bot / n).exists()]
    if faltan:
        raise SystemExit(f"En {bot} faltan: {', '.join(faltan)}. ¿Es la carpeta del bot?")

    hallazgos = revisar(bot)
    if hallazgos:
        print("NO se copia nada: el codigo del bot trae algo que no puede ir a un repo publico:")
        for h in hallazgos:
            print("  - " + h)
        raise SystemExit(1)

    DESTINO.mkdir(exist_ok=True)
    for nombre in CODIGO + ASSETS:
        shutil.copy2(bot / nombre, DESTINO / nombre)
    fuentes = DESTINO / FUENTES
    if fuentes.exists():
        shutil.rmtree(fuentes)
    shutil.copytree(bot / FUENTES, fuentes)

    commit = _git(bot, "rev-parse", "--short", "HEAD") or "(sin git)"
    fecha = _git(bot, "log", "-1", "--format=%cd", "--date=format:%d/%m/%Y %H:%M") or "?"
    sin_commitear = _git(bot, "status", "--porcelain", "--", *CODIGO, *ASSETS, FUENTES)
    (DESTINO / "ORIGEN.txt").write_text(
        "Copia del motor de reels del bot del diario (dlcchivilcoy/social_publisher).\n"
        "NO EDITAR A MANO: se pisa con  venv\\Scripts\\python.exe tools\\traer_estetica_bot.py\n"
        "Lo propio de policiales va en reels/reel_bot.py; utils/ es un reemplazo chico.\n\n"
        f"commit del bot: {commit} ({fecha})\n"
        f"traido: {datetime.now():%d/%m/%Y %H:%M}\n"
        + (f"OJO: habia cambios SIN COMMITEAR en el bot:\n{sin_commitear}\n" if sin_commitear else ""),
        encoding="utf-8")
    return {"commit": commit, "fecha": fecha, "sin_commitear": bool(sin_commitear)}


def main():
    ap = argparse.ArgumentParser(description="Trae la estetica de reels del bot del diario.")
    ap.add_argument("--bot", default=str(BOT_DEFAULT), help="carpeta del bot (social_publisher)")
    args = ap.parse_args()
    info = traer(Path(args.bot))
    print(f"Motor de reels traido del bot: commit {info['commit']} ({info['fecha']}).")
    if info["sin_commitear"]:
        print("OJO: se copiaron cambios que el bot todavia no commiteo.")
    print("Ahora:  venv\\Scripts\\python.exe tools\\test_estetica.py")


if __name__ == "__main__":
    sys.exit(main())
