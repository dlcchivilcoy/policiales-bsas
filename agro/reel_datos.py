# -*- coding: utf-8 -*-
"""El REEL DE DATOS de cada mañana (pedido del editor, 23/10/2026: «hacer un reel con todas las placas de
las historias en 4:5, que vayan pasando cada 5 segundos, y que salga la publicación como colab todos los
días a las 5 am»).

    05:00  lee los datos (clima del SMN, alertas, pizarra de Rosario, dólar, Chicago), arma las placas
           de las historias en 4:5 (agro/historias.py, componer_45) y las une en un reel: 5 segundos
           cada una (SEG_POR_PLACA), sin sonido (una pista muda para que Instagram no lo rechace).
           Instagram: en @diarioyradioagro con @diarioyradio de COLABORADOR (`collaborators`) y la
           invitación aceptada sola con la cuenta del diario (publicar.aceptar_colab): el mismo posteo
           aparece en los dos perfiles. Si la colab no se puede, sale igual en agro.
           Facebook no tiene colab: el reel sale en las DOS páginas (AGRO_REEL_DATOS_FB_DIARIO=0 deja
           solo la de agro).

Las placas son las de datos: alertas del SMN que tocan la zona, clima, granos, dólar y Chicago. Si un
dato no es de hoy, la placa lo dice («Último dato disponible»), como en las historias. AGRO_REEL_DATOS
cambia la hora (o "0" lo apaga: agro/agenda.py).
"""
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

SEG_POR_PLACA = 5
FPS = 30
TIPOS = ("clima", "granos", "dolar", "chicago")
MAX_ALERTAS = 2
HASHTAGS = "#Agro #CampoArgentino #Chivilcoy #Mercados #Clima"


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def placas(datos: dict, mem: dict, carpeta: Path, momento: datetime) -> list:
    """[{tipo, archivo (4:5)}] en el orden del reel: las alertas primero, después clima, granos, dólar y
    Chicago. Lo que no tiene dato no va."""
    from agro import historias as HI
    hoy = momento.date()
    carpeta = Path(carpeta)
    salida = []
    for a in (datos.get("alertas") or [])[:MAX_ALERTAS]:
        r = HI.placa_alerta(a, carpeta / f"dato_{len(salida):02d}_alerta.jpg", hoy)
        salida.append({"tipo": "alerta", "archivo": str(HI.ruta_45(r))})
    for tipo in TIPOS:
        destino = carpeta / f"dato_{len(salida):02d}_{tipo}.jpg"
        r = {"clima": lambda: HI.placa_clima(datos, destino, hoy, "EL CAMPO HOY"),
             "granos": lambda: HI.placa_granos(datos, mem, destino, hoy, "EL CAMPO HOY"),
             "dolar": lambda: HI.placa_dolar(datos, mem, destino, hoy, "EL CAMPO HOY"),
             "chicago": lambda: HI.placa_chicago(datos, destino, hoy, "EL CAMPO HOY")}[tipo]()
        if r:
            salida.append({"tipo": tipo, "archivo": str(HI.ruta_45(r))})
    return salida


def armar_video(archivos: list, destino: Path, seg: float = SEG_POR_PLACA) -> Path:
    """Las placas una detrás de otra, `seg` segundos cada una, 1080x1350, con una pista muda."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_ffmpeg(), "-loglevel", "error", "-y"]
    for a in archivos:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{seg}", "-i", str(a)]
    total = seg * len(archivos)
    cmd += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    escalas = "".join(f"[{i}:v]scale=1080:1350,setsar=1,format=yuv420p[v{i}];" for i in range(len(archivos)))
    unir = "".join(f"[v{i}]" for i in range(len(archivos))) + f"concat=n={len(archivos)}:v=1:a=0[v]"
    cmd += ["-filter_complex", escalas + unir, "-map", "[v]", "-map", f"{len(archivos)}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(destino)]
    subprocess.run(cmd, check=True, capture_output=True)
    return destino


def caption(momento: datetime, tipos: list) -> str:
    from agro import historias as HI
    que = {"alerta": "alertas del SMN", "clima": "el clima", "granos": "la soja, el trigo y el maíz en Rosario",
           "dolar": "el dólar", "chicago": "Chicago"}
    lista = []
    for t in tipos:
        if que.get(t) and que[t] not in lista:
            lista.append(que[t])
    cuerpo = ", ".join(lista[:-1]) + (f" y {lista[-1]}" if len(lista) > 1 else (lista[0] if lista else ""))
    return (f"📊 EL CAMPO HOY · {HI.fecha_larga(momento.date()).capitalize()}\n\n"
            f"Arrancá el día con los datos: {cuerpo}.\n\n"
            f"Deslizá y mirá placa por placa. Cada dato dice su fuente y su fecha.\n\n{HASHTAGS}")


def fb_diario() -> bool:
    import os
    return (os.environ.get("AGRO_REEL_DATOS_FB_DIARIO") or "1").strip() != "0"


def publicar(mp4: Path, texto: str, portada: Path, log=print) -> dict:
    """Instagram (agro, con @diarioyradio de colaborador) y Facebook (agro y diario). Nunca lanza por una
    red: {red: {"id"…} | {"error"…}}."""
    from agro import publicar as PUB
    from reels import instagram as IG
    from reels import publicador as PB
    salida = {}
    pp = {"descripcion_tiktok": texto, "video": {"alto": 1350}, "guion": {"titular": "El campo hoy", "bajada": ""}}
    nombre = f"agro_datos_{mp4.parent.name}.mp4"
    with PUB.credenciales_agro():
        import os
        uid, tok = os.environ["INSTAGRAM_USER_ID"], os.environ["INSTAGRAM_ACCESS_TOKEN"]
        try:
            url = PB.subir_a_release(mp4, nombre)
            portada_url = PB.subir_a_release(portada, f"agro_datos_{mp4.parent.name}_portada.jpg") if portada else ""
            params = IG.contenedor_reel(url, texto, prueba=False, portada=portada_url)
            colab = PUB.usuario_diario()
            try:
                cid = PB._contenedor_listo(uid, tok, dict(params, collaborators=json.dumps([colab])))
                con_colab = True
            except PB.FalloRed as e:
                log(f"   Instagram no tomó la colab ({str(e)[:150]}): sale solo en @diarioyradioagro")
                cid, con_colab = PB._contenedor_listo(uid, tok, params), False
            mid = PB._publicar_contenedor(uid, tok, cid, texto) or None
            salida["instagram"] = {"id": mid, "colab": f"@{colab}" if con_colab else "no"}
            log(f"   Instagram: {mid} (colab con @{colab}: {'sí' if con_colab else 'no'})")
        except Exception as e:                             # noqa: BLE001
            salida["instagram"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Instagram FALLÓ: {salida['instagram']['error']}")
        try:
            salida["facebook"] = PB.publicar_facebook(pp, mp4)
            log(f"   Facebook agro: {salida['facebook'].get('id')}")
        except Exception as e:                             # noqa: BLE001
            salida["facebook"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook agro FALLÓ: {salida['facebook']['error']}")
    ig = salida.get("instagram") or {}
    if ig.get("id") and ig.get("colab") != "no":
        try:
            salida["colab"] = PUB.aceptar_colab(ig["id"], log=log)
        except Exception as e:                             # noqa: BLE001
            salida["colab"] = {"estado": "pendiente", "detalle": f"{type(e).__name__}: {str(e)[:200]}"}
    if fb_diario():
        try:
            PUB.credenciales_diario()
            salida["facebook_diario"] = PB.publicar_facebook(pp, mp4)
            log(f"   Facebook @diarioyradio: {salida['facebook_diario'].get('id')}")
        except Exception as e:                             # noqa: BLE001
            salida["facebook_diario"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"   Facebook @diarioyradio FALLÓ: {salida['facebook_diario']['error']}")
    return salida


def pasada(publicar: bool, horario: datetime, log=print, publicador=None, carpeta: Path = None,
           ahora: datetime = None) -> Path:
    """El turno del reel de datos (agro/pasada.py → _un_turno)."""
    from agro import informe as INF
    from agro import mercado as M
    from agro import pasada as PA
    ahora = ahora or datetime.now(PA.TZ_AR)
    carpeta = Path(carpeta or PA.SALIDA / ahora.strftime("%Y-%m-%d_%H%M_reel_datos"))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_mem = PA.MEMORIA_REAL if publicar else PA.MEMORIA
    mem = PA.cargar(ruta_mem)
    log(f"[agro] REEL DE DATOS {'REAL' if publicar else 'SIMULADO'} {ahora:%d/%m %H:%M} → {carpeta}")
    datos = M.leer_todo(mem, momento=ahora, log=log)
    lista = placas(datos, mem, carpeta, ahora)
    log(f"   {len(lista)} placas: {', '.join(p['tipo'] for p in lista)}")
    registro = {"dia": ahora.date().isoformat(), "placas": [p["tipo"] for p in lista]}
    if lista:
        mp4 = armar_video([p["archivo"] for p in lista], carpeta / "reel_datos.mp4")
        texto = caption(ahora, [p["tipo"] for p in lista])
        log(f"   reel: {len(lista) * SEG_POR_PLACA} s")
        if publicar:
            registro["publicado"] = {"estado": "publicando"}
            mem.setdefault("reel_datos", {})[horario.isoformat()] = registro
            PA.guardar(mem, ahora, ruta_mem)
            res = (publicador or publicar_reel)(mp4, texto, Path(lista[0]["archivo"]), log=log)
            registro["publicado"] = res
    mem.setdefault("reel_datos", {})[horario.isoformat()] = registro if publicar else dict(registro, simulado=True)
    lim = (ahora - timedelta(days=PA.DIAS_MEMORIA)).isoformat()
    mem["reel_datos"] = {k: v for k, v in mem["reel_datos"].items() if k >= lim}
    PA.guardar(mem, ahora, ruta_mem)
    inf = {"cuando": f"{ahora:%d/%m/%Y %H:%M}", "formato": "reel de datos",
           "conteos": {"Placas": len(lista), "Segundos": len(lista) * SEG_POR_PLACA},
           "historias": lista, "fuentes": [], "piezas": [], "descartadas": [], "grupos_duplicados": [],
           "config": {"score_min": "—", "max_dia": "—", "horas": 0}, "publicar": publicar,
           "resultado": registro.get("publicado")}
    (carpeta / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return INF.escribir(inf, carpeta)


publicar_reel = publicar
