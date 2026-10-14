# -*- coding: utf-8 -*-
"""Guarda estado/ en el repo SIN choques: combina la memoria de esta pasada con la que
haya subido otra mientras tanto, en vez de pelearse con git.

Nació el 27/09/2026: la pasada de las 15:05 publicó bien 16 posteos, pero su commit de
la memoria chocó en estado/salud.json con el de la pasada cancelada de las 12 y
`git pull --rebase` abortó. La memoria se perdió, y la pasada siguiente iba a volver a
subir los mismos 10 videos a YouTube (se recuperó a mano desde el artefacto).

Cómo combina (siempre gana lo más completo, nunca se pierde nada anotado):
- publicados.json: unión por nota; en una misma nota, por red gana el resultado más
  nuevo ("cuando"), y un "ok" nunca se pisa con algo que no sea "ok".
- reels_hechos.json: unión por nota; gana el registro más nuevo.
- salud.json y ultima_corrida.json: los de esta pasada (son su diagnóstico).
- tema_reels.json (12/10/2026): el tema del último reel 4:5 (bloque blanco o grafito); gana el
  más nuevo. Lo escriben policiales, nacionales y el Archivo.

Uso (en el workflow, después de que la pasada escribió estado/):
    python tools/guardar_estado.py
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RAMA = "main"
INTENTOS = 4
EXITO = ("ok", "sin_confirmar")


def combinar_publicados(nuestro: dict, remoto: dict) -> dict:
    out = {k: dict(v) for k, v in remoto.items()}
    for clave, mio in nuestro.items():
        e = out.setdefault(clave, {})
        for campo, valor in mio.items():
            if isinstance(valor, dict) and "estado" in valor:          # una red
                otro = e.get(campo)
                if not isinstance(otro, dict):
                    e[campo] = valor
                    continue
                ok_mio, ok_otro = valor.get("estado") in EXITO, otro.get("estado") in EXITO
                if ok_otro and not ok_mio:
                    continue                                            # un ok no se pisa
                if ok_mio and not ok_otro:
                    e[campo] = valor
                elif (valor.get("cuando") or "") >= (otro.get("cuando") or ""):
                    e[campo] = valor
            elif campo == "ultimo":
                e["ultimo"] = max(valor or "", e.get("ultimo") or "")
            else:
                e.setdefault(campo, valor)
    return out


def combinar_hechos(nuestro: dict, remoto: dict) -> dict:
    out = dict(remoto)
    out["hechos"] = dict(remoto.get("hechos") or {})
    for clave, v in (nuestro.get("hechos") or {}).items():
        otro = out["hechos"].get(clave)
        if not otro or (v.get("cuando") or 0) >= (otro.get("cuando") or 0):
            out["hechos"][clave] = v
    for campo in ("actualizado", "dias_memoria"):
        if campo in nuestro:
            out[campo] = nuestro[campo]
    return out


def combinar_nacionales(nuestro: dict, remoto: dict) -> dict:
    """estado/nacionales.json (nacionales/pasada.py, 06/10/2026): unión por clave en piezas,
    descartadas y carruseles; en una misma clave gana el registro más nuevo ("cuando").

    Hace falta aunque cada trabajo escriba lo suyo: el trabajo de POLICIALES guarda TODO
    estado/, y su copia de nacionales.json es la del arranque de la pasada. Sin combinar, la
    pisaría con una vieja y la pasada siguiente repetiría las nacionales."""
    out = dict(remoto)
    for seccion in ("piezas", "descartadas", "carruseles"):
        union = dict(remoto.get(seccion) or {})
        for clave, v in (nuestro.get(seccion) or {}).items():
            otro = union.get(clave)
            if not isinstance(otro, dict) or (v.get("cuando") or "") >= (otro.get("cuando") or ""):
                union[clave] = v
        out[seccion] = union
    out["actualizado"] = max(nuestro.get("actualizado") or "", remoto.get("actualizado") or "")
    return out


def combinar_archivo(nuestro: dict, remoto: dict) -> dict:
    """estado/archivo.json (archivo/pasada.py, 10/10/2026: reels de prueba del Archivo Literario y
    la pregunta del día). Igual que nacionales, la copia que guarda el trabajo de policiales es la
    vieja del arranque: sin esto, pisaría lo publicado y se repetiría la pieza del día.
    - usados: unión; por clave, la fecha más nueva.
    - publicaciones: unión por «día:tipo»; un ok nunca se pisa con algo que no sea ok.
    - preguntas: unión por (día, pregunta), en orden, las últimas 200."""
    out = dict(remoto)
    usados = dict(remoto.get("usados") or {})
    for clave, dia in (nuestro.get("usados") or {}).items():
        usados[clave] = max(dia or "", usados.get(clave) or "")
    out["usados"] = usados
    pubs = dict(remoto.get("publicaciones") or {})
    for clave, mio in (nuestro.get("publicaciones") or {}).items():
        otro = pubs.get(clave)
        if not isinstance(otro, dict):
            pubs[clave] = mio
            continue
        ok_mio, ok_otro = mio.get("estado") in EXITO, otro.get("estado") in EXITO
        if ok_otro and not ok_mio:
            continue
        if (ok_mio and not ok_otro) or (mio.get("cuando") or "") >= (otro.get("cuando") or ""):
            pubs[clave] = mio
    out["publicaciones"] = pubs
    vistas, preguntas = set(), []
    for p in (remoto.get("preguntas") or []) + (nuestro.get("preguntas") or []):
        clave = (p.get("dia"), p.get("pregunta"))
        if clave not in vistas:
            vistas.add(clave)
            preguntas.append(p)
    out["preguntas"] = sorted(preguntas, key=lambda p: p.get("dia") or "")[-200:]
    out["actualizado"] = max(nuestro.get("actualizado") or "", remoto.get("actualizado") or "")
    return out


def combinar_buzon(nuestro: dict, remoto: dict) -> dict:
    """estado/buzon_distribuidor.json (reels/distribuidor.py, 11/10/2026): unión por id."""
    sys.path.insert(0, str(RAIZ))
    from reels.distribuidor import combinar
    return combinar(nuestro, remoto)


def combinar_tema(nuestro: dict, remoto: dict) -> dict:
    """estado/tema_reels.json: el más nuevo («cuando»), así la alternancia sigue al último reel."""
    return nuestro if (nuestro.get("cuando") or 0) >= (remoto.get("cuando") or 0) else remoto


def combinar_agro(nuestro: dict, remoto: dict) -> dict:
    """estado/agro.json (agro/pasada.py --publicar, 14/10/2026). El trabajo de policiales guarda TODO
    estado/ con la copia vieja del arranque: sin esto pisaría lo que publicó agro y se repetiría.
    - indice y scores: unión (son «ya visto», nunca se des-ven).
    - elegidas: unión por id; una con resultado de publicación le gana a una sin él o «publicando».
    - pendientes: los de la copia más nueva («actualizado»)."""
    out = dict(remoto)
    idx = {k: dict(v) for k, v in (remoto.get("indice") or {}).items()}
    for k, v in (nuestro.get("indice") or {}).items():
        idx.setdefault(k, {}).update(v)
    out["indice"] = idx
    out["scores"] = {**(remoto.get("scores") or {}), **(nuestro.get("scores") or {})}

    def peso(e):
        pub = e.get("publicado")
        if not isinstance(pub, dict):
            return 0
        return 1 if pub.get("estado") == "publicando" else 2
    por_id = {e["id"]: e for e in remoto.get("elegidas") or []}
    for e in nuestro.get("elegidas") or []:
        otro = por_id.get(e["id"])
        if otro is None or peso(e) >= peso(otro):
            por_id[e["id"]] = e
    out["elegidas"] = sorted(por_id.values(), key=lambda e: e.get("cuando") or "")
    mas_nuevo = nuestro if (nuestro.get("actualizado") or "") >= (remoto.get("actualizado") or "") else remoto
    out["pendientes"] = mas_nuevo.get("pendientes") or []
    out["actualizado"] = max(nuestro.get("actualizado") or "", remoto.get("actualizado") or "")
    return out


COMBINAR = {"publicados.json": combinar_publicados, "reels_hechos.json": combinar_hechos,
            "agro.json": combinar_agro,
            "tema_reels.json": combinar_tema,
            "nacionales.json": combinar_nacionales, "archivo.json": combinar_archivo,
            "buzon_distribuidor.json": combinar_buzon}


def _git(*args, chequear=True, raiz=RAIZ) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True)
    if chequear and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r


def _leer(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _remoto(nombre: str, raiz=RAIZ):
    r = _git("show", f"origin/{RAMA}:estado/{nombre}", chequear=False, raiz=raiz)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def guardar(mensaje: str, raiz: Path = RAIZ, solo=None) -> str:
    """`solo`: los archivos de estado/ que escribió este trabajo (el de nacionales guarda solo
    nacionales.json: el resto de su copia es la vieja del arranque)."""
    estado = raiz / "estado"
    g = lambda *a, **k: _git(*a, raiz=raiz, **k)
    # Lo que escribió ESTA pasada, en memoria, antes de tocar nada en git.
    nuestros = {p.name: _leer(p) for p in sorted(estado.glob("*.json"))
                if not solo or p.name in solo}
    nuestros = {k: v for k, v in nuestros.items() if v is not None}
    if not nuestros:
        return "estado/ vacío: nada que guardar."

    for intento in range(1, INTENTOS + 1):
        g("fetch", "--quiet", "origin", RAMA)
        g("reset", "--quiet", "--hard", f"origin/{RAMA}")     # la punta actual de la rama
        for nombre, mio in nuestros.items():
            remoto = _remoto(nombre, raiz)
            final = COMBINAR[nombre](mio, remoto) if (nombre in COMBINAR and remoto) else mio
            (estado / nombre).write_text(json.dumps(final, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        g("add", *[f"estado/{n}" for n in nuestros])
        if not g("status", "--porcelain", "estado/").stdout.strip():
            return "La memoria ya estaba al día: nada que commitear."
        g("commit", "--quiet", "-m", mensaje)
        if g("push", "--quiet", "origin", f"HEAD:{RAMA}", chequear=False).returncode == 0:
            return f"Memoria guardada (intento {intento})."
        print(f"El push no entró (otra pasada subió algo); intento {intento} de {INTENTOS}...")
    raise RuntimeError("No se pudo guardar la memoria después de varios intentos.")


if __name__ == "__main__":
    from datetime import datetime, timezone
    solo = sys.argv[sys.argv.index("--solo") + 1:] if "--solo" in sys.argv else None
    que = {"nacionales.json": "Nacionales", "archivo.json": "Archivo", "agro.json": "Agro"}.get((solo or [""])[0], "Reels")
    msg = f"{que} de {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC [skip ci]"
    try:
        print(guardar(msg, solo=solo))
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
