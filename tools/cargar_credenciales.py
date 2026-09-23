# -*- coding: utf-8 -*-
"""Vuelca las credenciales de otro archivo dentro del .env del proyecto.

Para que existe: al rotar un token o al sumar una red hay que copiar media docena
de valores largos de un lado a otro, y hacerlo a mano termina en una linea pegada a
la anterior o en un valor cortado por la mitad.

Lo que NO hace, y es el punto: **nunca imprime un valor**. Informa que variables
cargo, cuantos caracteres tenia cada una y nada mas. Asi se puede correr con la
salida a la vista —una terminal compartida, un log, una conversacion— sin que las
credenciales queden dando vueltas en ningun lado.

Uso:
    venv\\Scripts\\python.exe tools\\cargar_credenciales.py <archivo>
    venv\\Scripts\\python.exe tools\\cargar_credenciales.py <archivo> --borrar-origen

`--borrar-origen` borra el archivo de donde vinieron una vez cargadas. Conviene: un
archivo suelto con todas las claves es justo lo que no hay que dejar tirado.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, ".env")


def _leer(ruta):
    """{NOMBRE: valor} de un archivo tipo .env. Ignora comentarios y huecos."""
    datos = {}
    with open(ruta, encoding="utf-8-sig") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            k = k.strip()
            # "export FOO=bar" tambien vale: es como los copia y pega mucha gente.
            k = re.sub(r"^export\s+", "", k)
            v = v.strip().strip('"').strip("'")
            if k and v:
                datos[k] = v
    return datos


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    borrar = "--borrar-origen" in sys.argv
    if not args:
        print(__doc__)
        return 1

    origen = args[0]
    if not os.path.exists(origen):
        print(f"No existe: {origen}")
        return 1
    if os.path.abspath(origen) == os.path.abspath(DESTINO):
        print("El origen y el destino son el mismo archivo.")
        return 1

    nuevos = _leer(origen)
    if not nuevos:
        print("El archivo no tiene ninguna variable con valor.")
        return 1

    # El .env se reescribe conservando sus comentarios: son las instrucciones de
    # donde sale cada credencial, y perderlas convierte el archivo en una lista de
    # nombres sin contexto.
    lineas = []
    if os.path.exists(DESTINO):
        with open(DESTINO, encoding="utf-8") as f:
            lineas = f.read().split("\n")

    puestas, cambiadas, vistas = [], [], set()
    for i, linea in enumerate(lineas):
        desnuda = linea.strip()
        if not desnuda or desnuda.startswith("#") or "=" not in desnuda:
            continue
        k, _, v = desnuda.partition("=")
        k = k.strip()
        if k in nuevos:
            vistas.add(k)
            (cambiadas if v.strip() else puestas).append(k)
            lineas[i] = f"{k}={nuevos[k]}"

    # Las que el .env no tenia previstas se agregan al final, marcadas.
    sobrantes = [k for k in nuevos if k not in vistas]
    if sobrantes:
        lineas += ["", "# Agregadas por tools/cargar_credenciales.py "
                       "(no estaban en la plantilla):"]
        lineas += [f"{k}={nuevos[k]}" for k in sobrantes]

    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    print(f"{len(nuevos)} variable(s) cargadas en .env\n")
    for grupo, titulo in ((puestas, "completadas"), (cambiadas, "REEMPLAZADAS"),
                          (sobrantes, "agregadas al final")):
        for k in grupo:
            print(f"   {titulo:<20} {k:<26} ({len(nuevos[k])} caracteres)")

    if borrar:
        os.remove(origen)
        print(f"\nBorrado el archivo de origen: {origen}")
    else:
        print(f"\nOJO: {origen} sigue teniendo las credenciales en texto plano. "
              f"Borralo, o volve a correr esto con --borrar-origen.")

    # Lo ultimo y lo mas importante: que el .env no se suba. El repo es PUBLICO.
    import subprocess
    r = subprocess.run(["git", "check-ignore", ".env"], cwd=RAIZ,
                       capture_output=True, text=True)
    print("\n.env ignorado por git: " + ("SI" if r.returncode == 0 else
                                         "NO  <-- FRENAR, el repo es publico"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
