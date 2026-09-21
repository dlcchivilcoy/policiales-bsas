# -*- coding: utf-8 -*-
"""Genera scraper/medios.py a partir de lo MEDIDO (data/ranking.json) mas los
rellenos decididos a mano para las localidades que no llegaban a dos medios.

Los rellenos estan aca y no escondidos en el registro final para que se vea de
donde sale cada eleccion y por que. Volver a correr este script regenera el
registro sin perder esas decisiones.

Correr:  venv\\Scripts\\python.exe tools\\generar_registro.py
"""
import sys, os, json
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Nombres lindos para mostrar (el sondeo solo conoce el dominio).
NOMBRES = {
    "diariosuipacha.com.ar": "Diario Suipacha",
    "elnuevocronista.com": "El Nuevo Cronista",
    "sprotagonistas.com.ar": "Semanario Protagonistas",
    "lujanenlinea.com.ar": "Luján en Línea",
    "diariodelujan.com": "El Diario de Luján",
    "lamanana.com.ar": "La Mañana (25 de Mayo)",
    "25digital.com.ar": "25 Digital",
    "cnsaladillo.com.ar": "CN Saladillo",
    "abcsaladillo.com.ar": "ABC Saladillo",
    "noticiasalberti.com": "Noticias Alberti",
    "bragadoesnoticia.com.ar": "Bragado es Noticia",
    "lavozdebragado.com.ar": "La Voz de Bragado",
    "diariodemocracia.com": "Diario Democracia",
    "chacabucoenred.com": "Chacabuco en Red",
    "junindigital.com": "Junín Digital",
    "junin24.com": "Junín 24",
    "lapostadelnoroeste.com.ar": "La Posta del Noroeste",
    "lamarcadelincoln.com.ar": "La Marca de Lincoln",
    "diarioel9dejulio.com.ar": "El 9 de Julio",
    "latrochadigital.com.ar": "La Trocha Digital",
    "casaresonline.com.ar": "Casares Online",
    "noticiasruta5.com": "Noticias Ruta 5",
    "laopinion.com.ar": "La Opinión (Trenque Lauquen)",
    "infoecos.com.ar": "Infoecos",
    "presentenoticias.com": "Presente Noticias",
    "diariolamanana.com.ar": "La Mañana (Bolívar)",
    "rumoresdepehuajo.com.ar": "Rumores de Pehuajó",
    "diarionoticiaspehuajo.com": "Diario Noticias Pehuajó",
    "infociudad.com.ar": "InfoCiudad",
    "arecociudad.com.ar": "Areco Ciudad",
    "diarioelinformador.com": "El Informador (2ª Sección)",
    "boscoproducciones.com.ar": "Bosco Producciones",
    "diarionucleo.com": "Diario Núcleo",
    "infosalto.com.ar": "InfoSalto",
    "unoarrecifes.com": "Diario UNO Arrecifes",
    "laopinionline.ar": "La Opinión (Pergamino)",
    "elnuevorojense.com.ar": "El Nuevo Rojense",
    "lobos24.com.ar": "Lobos 24",
    "lobosya.com.ar": "Lobos Ya",
    "infocanuelas.com": "InfoCañuelas",
    "canuelasnoticias.com": "Cañuelas Noticias",
    "noticiaslasflores.com.ar": "Noticias Las Flores",
    "lasfloresdigital.com.ar": "Las Flores Digital",
    "navarroenlineas.com.ar": "Navarro en Líneas",
    "navarronoticias.com": "Navarro Noticias",
    "roqueperezhoy.com.ar": "Roque Pérez Hoy",
}

# Localidades que no llegaban a dos medios propios con policiales constantes.
# Cada relleno dice de donde sale la decision. `seccion_falsa` marca los medios
# cuya URL /policiales existe pero devuelve cualquier cosa: para esos se usa el
# feed general y se confia en el filtro.
RELLENOS = {
    "Suipacha": [
        {"dominio": "diariosuipacha.com.ar", "alcance": "local", "navegador": True,
         "por_que": "Unico diario propio de Suipacha. Bloquea clientes automaticos (403): se lee con navegador."},
        {"dominio": "elnuevocronista.com", "alcance": "regional",
         "por_que": "Semanario de Mercedes con seccion de policiales; menciona Suipacha en su cobertura."},
    ],
    "25 de Mayo": [
        {"dominio": "lamanana.com.ar", "alcance": "local", "seccion_falsa": True,
         "por_que": "El diario de 25 de Mayo. Su URL /policiales devuelve notas de politica, asi que se usa el feed general + filtro."},
        {"dominio": "25digital.com.ar", "alcance": "local",
         "por_que": "Segundo medio local; sin seccion propia, entra por feed general + filtro."},
    ],
    "Alberti": [
        {"dominio": "noticiasalberti.com", "alcance": "local",
         "por_que": "Unico medio de Alberti con seccion de policiales activa."},
    ],
    "Carlos Casares": [
        {"dominio": "casaresonline.com.ar", "alcance": "local",
         "por_que": "Seccion de policiales por RSS, 7 de cada 10 notas del tema."},
        {"dominio": "noticiasruta5.com", "alcance": "regional",
         "por_que": "Cubre el corredor Bragado-9 de Julio-Casares-Pehuajo-Trenque Lauquen. Sin seccion: feed general + filtro."},
    ],
    "Pehuajo": [
        {"dominio": "rumoresdepehuajo.com.ar", "alcance": "local", "navegador": True,
         "por_que": "Tiene seccion de policiales propia. Bloquea clientes automaticos (403): se lee con navegador."},
        {"dominio": "diarionoticiaspehuajo.com", "alcance": "local",
         "por_que": "Diario local con RSS; sin seccion propia, entra por feed general + filtro."},
    ],
    "Arrecifes": [
        {"dominio": "unoarrecifes.com", "alcance": "local",
         "por_que": "Seccion de policiales por RSS, 10 de cada 12 notas del tema."},
        {"dominio": "diarioelinformador.com", "alcance": "regional", "navegador": True,
         "por_que": "Cubre toda la 2a Seccion (Arrecifes, Areco, Giles, Rojas, Salto). Bloquea clientes automaticos: se lee con navegador."},
    ],
    "San Andres de Giles": [
        {"dominio": "infociudad.com.ar", "alcance": "regional",
         "por_que": "Seccion de policiales activa; es el medio que mas nombra a Giles en sus titulares."},
        {"dominio": "diarioelinformador.com", "alcance": "regional", "navegador": True,
         "por_que": "4 menciones a Giles en el muestreo. Se lee con navegador."},
    ],
    "Navarro": [
        {"dominio": "navarroenlineas.com.ar", "alcance": "local",
         "por_que": "Seccion de policiales real."},
        {"dominio": "navarronoticias.com", "alcance": "local", "seccion_falsa": True,
         "por_que": "Primer diario digital de Navarro. Su URL /policiales devuelve notas generales: se usa el feed general + filtro."},
    ],
    "Carmen de Areco": [
        {"dominio": "infociudad.com.ar", "alcance": "regional",
         "por_que": "Seccion de policiales activa sobre la region de Areco."},
        {"dominio": "arecociudad.com.ar", "alcance": "regional",
         "por_que": "Cubre Carmen de Areco y la zona. Sin seccion: feed general + filtro."},
    ],
    "San Miguel del Monte": [
        {"dominio": "infocanuelas.com", "alcance": "regional",
         "por_que": "No hay medio propio vivo en Monte. InfoCanuelas tiene pagina de la localidad con 24 notas y 6 policiales. OJO: montenoticias.com.ar NO sirve, es de Monte Hermoso (a 500 km)."},
        {"dominio": "presentenoticias.com", "alcance": "regional",
         "por_que": "Tiene pagina propia de San Miguel del Monte. Cobertura mas fina que la seccion general."},
    ],
    "San Antonio de Areco": [
        {"dominio": "boscoproducciones.com.ar", "alcance": "local",
         "por_que": "Seccion de policiales por RSS."},
        {"dominio": "arecociudad.com.ar", "alcance": "regional",
         "por_que": "Portal de Areco y la zona. Sin seccion: feed general + filtro."},
    ],
}


# Cuando el medio es regional conviene entrar por SU pagina de esa localidad y no
# por su seccion general de policiales, que esta dominada por su propia ciudad.
# Cada URL de aca se verifico a mano: devuelve notas y son de la localidad correcta.
SECCION_LOCALIDAD = {
    ("Rojas", "diarionucleo.com"): "https://diarionucleo.com/ciudad/rojas/",
    ("Salto", "diarionucleo.com"): "https://diarionucleo.com/ciudad/salto/",
    ("Chacabuco", "diariodemocracia.com"): "https://www.diariodemocracia.com/ciudad/chacabuco/",
    ("San Miguel del Monte", "infocanuelas.com"): "https://www.infocanuelas.com/tags/san-miguel-del-monte",
    ("San Miguel del Monte", "presentenoticias.com"): "https://www.presentenoticias.com/tag/746/san-miguel-del-monte",
}


def main():
    with open(os.path.join(RAIZ, "data", "ranking.json"), encoding="utf-8") as f:
        ranking = json.load(f)
    with open(os.path.join(RAIZ, "data", "sondeo.json"), encoding="utf-8") as f:
        crudos = json.load(f)["resultados"]
    sondeo = {(r["localidad"], r["dominio"]): r for r in crudos}
    # Un medio regional se midio bajo UNA localidad, pero lo usamos en varias.
    # Sin este indice por dominio, esas entradas quedaban sin la seccion de
    # policiales detectada y terminaban raspando la home (paso con El Nuevo
    # Cronista en Suipacha y con El Informador en Arrecifes y Giles).
    por_dominio = {}
    for r in crudos:
        prev = por_dominio.get(r["dominio"])
        if prev is None or (r.get("n_policiales") or 0) > (prev.get("n_policiales") or 0):
            por_dominio[r["dominio"]] = r

    filas, sin_par = [], []
    for loc in sorted(ranking):
        if loc in RELLENOS:
            elegidos = []
            for relleno in RELLENOS[loc]:
                med = dict(sondeo.get((loc, relleno["dominio"]))
                           or por_dominio.get(relleno["dominio"], {}))
                med.update(relleno)
                elegidos.append(med)
        else:
            elegidos = [dict(r, alcance="local") for r in ranking[loc]]

        for m in elegidos:
            dom = m["dominio"]
            usa_seccion = bool(m.get("seccion_policial")) and not m.get("seccion_falsa")
            override = SECCION_LOCALIDAD.get((loc, dom))
            filas.append({
                "localidad": loc,
                "nombre": NOMBRES.get(dom, dom),
                "dominio": dom,
                "base": m.get("base") or f"https://{dom}",
                "seccion": override or (m.get("seccion_policial") if usa_seccion else None),
                "seccion_rss": None if override else (m.get("seccion_rss") if usa_seccion else None),
                "rss": m.get("rss"),
                "alcance": m.get("alcance", "local"),
                "navegador": bool(m.get("navegador")),
                "nota": m.get("por_que", ""),
                # metricas del sondeo, para saber que esperar de cada fuente
                "medido_notas": m.get("n_notas"),
                "medido_policiales": m.get("n_policiales"),
            })
        if len(elegidos) < 2:
            sin_par.append(loc)

    ruta = os.path.join(RAIZ, "scraper", "medios.py")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""Registro de medios: los 2 de mayor flujo policial por localidad.\n\n')
        f.write('GENERADO por tools/generar_registro.py — no editar a mano; cambiar el\n')
        f.write('padron (data/candidatos.json) o los rellenos del generador y volver a correrlo.\n\n')
        f.write('Cada eleccion sale de medir el sitio, no de suponer: tools/sondear_medios.py\n')
        f.write('cuenta cuantas notas policiales publica cada candidato y tools/rankear.py\n')
        f.write('ordena. Los campos "medido_*" son lo que devolvio el sondeo.\n\n')
        f.write('  seccion   -> URL de la seccion de policiales (via preferida)\n')
        f.write('  rss       -> feed general, respaldo cuando no hay seccion\n')
        f.write('  navegador -> el sitio bloquea clientes automaticos: se lee con Playwright\n')
        f.write('  alcance   -> "local" o "regional" (cubre la localidad desde afuera)\n')
        f.write(f'\nUltima regeneracion: {date.today().isoformat()}\n"""\n\n')
        f.write("MEDIOS = [\n")
        actual = None
        for fila in filas:
            if fila["localidad"] != actual:
                actual = fila["localidad"]
                f.write(f"\n    # --- {actual} " + "-" * (58 - len(actual)) + "\n")
            f.write("    {\n")
            for k in ("localidad", "nombre", "dominio", "base", "seccion", "seccion_rss",
                      "rss", "alcance", "navegador", "medido_notas", "medido_policiales"):
                f.write(f"        {k!r}: {fila[k]!r},\n")
            if fila["nota"]:
                f.write(f"        # {fila['nota']}\n")
            f.write("    },\n")
        f.write("]\n\n\n")
        f.write("LOCALIDADES = sorted({m['localidad'] for m in MEDIOS})\n\n\n")
        f.write("def por_localidad(localidad):\n")
        f.write("    return [m for m in MEDIOS if m['localidad'] == localidad]\n")

    print(f"{len(filas)} medios en {len(ranking)} localidades -> {ruta}")
    con_seccion = sum(1 for f_ in filas if f_["seccion"])
    con_nav = sum(1 for f_ in filas if f_["navegador"])
    regionales = sum(1 for f_ in filas if f_["alcance"] == "regional")
    print(f"  {con_seccion} con seccion de policiales | {regionales} regionales | "
          f"{con_nav} requieren navegador")
    if sin_par:
        print(f"  Localidades con un solo medio: {', '.join(sin_par)}")


if __name__ == "__main__":
    main()
