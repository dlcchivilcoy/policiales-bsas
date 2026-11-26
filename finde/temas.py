# -*- coding: utf-8 -*-
"""VERIFICACIÓN Y SELECCIÓN: cada tema arma su FICHA con los datos ya verificados, y la corrida elige cuál sale.

Una ficha es todo lo que el reel necesita, sin inventar nada:
  pregunta + 3 opciones (la correcta entre dos que no se le parecen) → la respuesta (número grande) → el mapa de la
  zona con el MISMO indicador para los 10 partidos → el contexto (2 o 3 cifras) → la pregunta para los comentarios.
Más la narración escena por escena, las fuentes (archivo exacto, año del dato, cálculo), los datos crudos, la
propuesta de historia con encuesta y el texto del posteo.

Reglas (las del pedido del editor):
  - el censo es del PARTIDO de Chivilcoy (no de la ciudad): el texto lo dice así;
  - el año del dato va siempre a la vista (2022 en el censo; la campaña en los rindes);
  - los índices propios se atribuyen a quien los hizo (el de productividad es del INTA, vía ArgenFields);
  - una estimación de rinde se llama estimación, no cosecha;
  - nada de rankings forzados: la comparación es entre partidos de la zona con el mismo indicador y período.
`verificar()` controla lo que se puede controlar con números (rangos, opciones distintas, la correcta entre las
opciones, el mapa con Chivilcoy, fuente con dirección y año). Si algo no cierra, el tema no sale.
"""
from __future__ import annotations

from datetime import date

from finde import datos as DA

DIAS = {5: "sabado", 6: "domingo"}
SEMANAS_SIN_REPETIR = 8
ORDEN_SABADO = ("gas_red", "cloacas", "alquiler", "crecimiento", "internet", "agua", "mayores")
ORDEN_DOMINGO = ("tierra", "soja_peor", "anegamiento", "aptitud", "emergencias")
ARGENFIELDS_URL = "https://www.argenfields.com/zonas/buenos-aires/chivilcoy"


def coma(x: float, dec: int = 1) -> str:
    s = f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def miles(n) -> str:
    return f"{round(n):,}".replace(",", ".")


def pct(parte, total) -> float:
    return 100.0 * parte / total if total else 0.0


def opciones_de(v: float, dec: int = 0, unidad: str = " %", tope: float = 100.0, paso: float = None,
                pos: int = 1) -> tuple:
    """Tres opciones redondas: la verdadera y dos que no se le parecen. `pos` (0, 1, 2) es dónde cae la verdadera
    (abajo, en el medio o arriba) para que no se adivine por el lugar; si no hay lugar (menos de 0 o más del
    `tope`), se corre. Devuelve ([textos], índice de la correcta)."""
    paso = paso or max(10.0, round(abs(v) * 0.3))
    for intento in (pos, 1, 0, 2):
        vals = [v + paso * (k - intento) for k in range(3)]
        if vals[0] >= 0 and vals[-1] <= tope:
            break
    vals = [round(x, dec) if k == intento else round(x) for k, x in enumerate(vals)]
    textos = [(coma(x, dec) if k == intento else coma(x, 0)) + unidad for k, x in enumerate(vals)]
    return textos, intento


def posicion(clave: str) -> int:
    """Dónde cae la respuesta correcta en cada tema (fijo por tema: el reel se puede rehacer igual)."""
    return sum(map(ord, clave)) % 3


def _ranking(valores: dict, nombres: dict) -> list:
    return sorted(((nombres[s], x) for s, x in valores.items() if x is not None), key=lambda f: -f[1])


def _puesto(valores: dict, slug="chivilcoy") -> int:
    orden = sorted((s for s, x in valores.items() if x is not None), key=lambda s: -valores[s])
    return orden.index(slug) + 1


def _fuente_censo(clave: str, calculo: str) -> dict:
    return {"fuente": DA.CENSO, "cuadro": DA.CUADROS[clave][1], "url": DA.url_cuadro(clave),
            "pagina": DA.PAGINA_CENSO, "anio_dato": 2022, "consultado": date.today().isoformat(), "calculo": calculo}


def _base(clave, dia, **k) -> dict:
    f = {"clave": clave, "dia": dia, "territorio": "partido de Chivilcoy"}
    f.update(k)
    return f


# ─────────────────────────────────────────────────────────────────────────────────────────────
# SÁBADO: la ciudad (Censo 2022)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _censo_pct(c: dict, campo: str, total: str) -> dict:
    return {s: pct(x[campo], x[total]) for s, x in c.items() if s != "_fuentes" and x.get(campo) and x.get(total)}


def _nombres(c: dict) -> dict:
    return {s: x.get("nombre") or s for s, x in c.items() if s != "_fuentes"}


def tema_gas_red(c: dict):
    v = _censo_pct(c, "gas_red", "hogares")
    ch = c.get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x, g = v["chivilcoy"], pct(ch["garrafa"], ch["hogares"])
    op, ok = opciones_de(x, 1, pos=posicion("gas_red"))
    p, n, nom = _puesto(v), len(v), _nombres(c)
    rk = _ranking(v, nom)
    return _base(
        "gas_red", "sabado", anio=2022, titulo="¿Cuántos tienen gas natural?",
        pregunta="¿Qué porcentaje de los hogares de Chivilcoy cocina con gas natural de red?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "texto": "de los hogares cocina con gas de red"},
        mapa={"titulo": "Gas de red en la zona", "valores": v, "dec": 1, "unidad": " %",
              "leyenda": "% de hogares que cocinan con gas de red"},
        contexto=[{"numero": f"Puesto {p} de {n}", "texto": "en la zona: " + ("el partido con más gas de red" if p == 1 else "por hogares con gas de red")},
                  {"numero": coma(g) + " %", "texto": f"cocina con garrafa: {miles(ch['garrafa'])} hogares"},
                  {"numero": coma(rk[-1][1]) + " %", "texto": f"en {rk[-1][0]}, el que menos tiene"}],
        cierre="¿Ya llegó el gas natural a tu cuadra?",
        narracion={
            "gancho": "¿Cuántos hogares de Chivilcoy cocinan con gas natural?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el Censo 2022, en el partido de Chivilcoy el {coma(x)} por ciento de los hogares "
                          "cocina con gas de red.",
            "mapa": (f"Es el número más alto de la zona: primero entre {n} partidos. {rk[-1][0]}, el último, tiene "
                     f"el {coma(rk[-1][1], 0)} por ciento." if p == 1
                     else f"En el mapa de la zona, Chivilcoy queda en el puesto {p} de {n}."),
            "contexto": f"Igual, uno de cada {round(100 / g)} hogares todavía cocina con garrafa: más de "
                        f"{miles(round(ch['garrafa'], -2))} familias.",
            "cierre": "Y vos, ¿ya tenés gas natural en tu cuadra? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("gas", "hogares con gas de red ÷ total de hogares, por partido")],
        datos={"porcentajes": v, "chivilcoy": {k: ch[k] for k in ("hogares", "gas_red", "garrafa", "gas_tubo",
                                                                    "cocina_electricidad", "lena", "cocina_otro")}},
        historia={"pregunta": "¿Con qué cocinás en tu casa?", "opciones": ["Gas natural", "Garrafa"],
                  "correcta": None, "dato": f"En el partido: {coma(x)} % gas de red y {coma(g)} % garrafa (Censo 2022)"},
        caption=[f"🔥 ¿Cuántos hogares de Chivilcoy cocinan con gas natural? Según el Censo 2022 del INDEC, en el "
                 f"partido de Chivilcoy el {coma(x)} % de los hogares cocina con gas de red: "
                 + ("el número más alto de la zona." if p == 1 else f"puesto {p} de {n} en la zona."),
                 f"La garrafa sigue siendo clave: la usa el {coma(g)} % de los hogares ({miles(ch['garrafa'])} de "
                 f"{miles(ch['hogares'])}).",
                 "Partido por partido: " + ", ".join(f"{a} {coma(b)} %" for a, b in rk) + ".",
                 "💬 ¿Ya llegó el gas natural a tu cuadra?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#GasNatural", "#Servicios"],
    )


def tema_cloacas(c: dict):
    v = _censo_pct(c, "cloaca", "hogares_cloacas")
    ch = c.get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 1, pos=posicion("cloacas"))
    p, n, nom = _puesto(v), len(v), _nombres(c)
    rk = _ranking(v, nom)
    sin = ch["hogares_cloacas"] - ch["cloaca"]
    return _base(
        "cloacas", "sabado", anio=2022, titulo="¿Cuántos tienen cloacas?",
        pregunta="¿Qué porcentaje de los hogares de Chivilcoy está conectado a la red de cloacas?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "texto": "de los hogares desagota a la red cloacal"},
        mapa={"titulo": "Cloacas en la zona", "valores": v, "dec": 1, "unidad": " %",
              "leyenda": "% de hogares con desagüe a red pública (cloaca)"},
        contexto=[{"numero": f"Puesto {p} de {n}", "texto": "en la zona"},
                  {"numero": miles(sin), "texto": "hogares sin conexión a la red (pozo o cámara séptica)"},
                  {"numero": coma(rk[0][1]) + " %", "texto": f"en {rk[0][0]}, el que más tiene"}],
        cierre="¿Tu barrio ya tiene cloacas?",
        narracion={
            "gancho": "¿Cuántos hogares de Chivilcoy tienen cloacas?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el Censo 2022, en el partido de Chivilcoy el {coma(x)} por ciento de los hogares "
                          "desagota a la red cloacal.",
            "mapa": f"En la zona, Chivilcoy queda en el puesto {p} de {n}. El que más tiene es {rk[0][0]}.",
            "contexto": f"Todavía hay más de {miles(round(sin, -2))} hogares que dependen de un pozo o de una "
                        "cámara séptica.",
            "cierre": "¿Tu barrio ya tiene cloacas? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("cloacas", "hogares con desagüe a red pública (cloaca) ÷ total de hogares, cada "
                                          "partido en su hoja")],
        datos={"porcentajes": v, "chivilcoy": {k: ch[k] for k in ("hogares_cloacas", "cloaca")}},
        historia={"pregunta": "¿Tu casa tiene cloacas?", "opciones": ["Sí", "Todavía no"], "correcta": None,
                  "dato": f"En el partido, {coma(x)} % de los hogares (Censo 2022)"},
        caption=[f"🚽 ¿Cuántos hogares de Chivilcoy tienen cloacas? Según el Censo 2022 del INDEC, en el partido de "
                 f"Chivilcoy el {coma(x)} % de los hogares desagota a la red cloacal: puesto {p} de {n} en la zona.",
                 f"Más de {miles(round(sin, -2))} hogares todavía dependen de un pozo o una cámara séptica.",
                 "Partido por partido: " + ", ".join(f"{a} {coma(b)} %" for a, b in rk) + ".",
                 "💬 ¿Tu barrio ya tiene cloacas?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#Cloacas", "#Servicios"],
    )


def tema_agua(c: dict):
    v = _censo_pct(c, "agua_red", "hogares_agua")
    ch = c.get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 1, pos=posicion("agua"))
    p, n, nom = _puesto(v), len(v), _nombres(c)
    rk = _ranking(v, nom)
    sin = ch["hogares_agua"] - ch["agua_red"]
    return _base(
        "agua", "sabado", anio=2022, titulo="¿Cuántos tienen agua de red?",
        pregunta="¿Qué porcentaje de los hogares de Chivilcoy tiene agua corriente de red?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "texto": "de los hogares tiene agua corriente de red"},
        mapa={"titulo": "Agua de red en la zona", "valores": v, "dec": 1, "unidad": " %",
              "leyenda": "% de hogares con agua de red pública"},
        contexto=[{"numero": f"Puesto {p} de {n}", "texto": "en la zona"},
                  {"numero": miles(sin), "texto": "hogares con perforación, pozo u otra fuente"},
                  {"numero": coma(rk[0][1]) + " %", "texto": f"en {rk[0][0]}, el que más tiene"}],
        cierre="¿En tu casa tomás agua de red o de pozo?",
        narracion={
            "gancho": "¿Cuántos hogares de Chivilcoy tienen agua corriente?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el Censo 2022, en el partido de Chivilcoy el {coma(x)} por ciento de los hogares "
                          "tiene agua de red.",
            "mapa": f"En la zona, Chivilcoy queda en el puesto {p} de {n}.",
            "contexto": f"El resto, más de {miles(round(sin, -2))} hogares, se arregla con perforaciones o pozos.",
            "cierre": "¿En tu casa tomás agua de red o de pozo? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("agua", "hogares con agua de red pública ÷ total de hogares, cada partido en su "
                                       "hoja")],
        datos={"porcentajes": v, "chivilcoy": {k: ch[k] for k in ("hogares_agua", "agua_red")}},
        historia={"pregunta": "¿Qué agua tomás en tu casa?", "opciones": ["De red", "De pozo"], "correcta": None,
                  "dato": f"En el partido, {coma(x)} % tiene agua de red (Censo 2022)"},
        caption=[f"💧 Según el Censo 2022 del INDEC, en el partido de Chivilcoy el {coma(x)} % de los hogares tiene "
                 f"agua corriente de red: puesto {p} de {n} en la zona.",
                 "Partido por partido: " + ", ".join(f"{a} {coma(b)} %" for a, b in rk) + ".",
                 "💬 ¿En tu casa tomás agua de red o de pozo?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#AguaPotable", "#Servicios"],
    )


def tema_internet(c: dict):
    v = _censo_pct(c, "internet", "hogares_internet")
    ch = c.get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 1, pos=posicion("internet"))
    p, n, nom = _puesto(v), len(v), _nombres(c)
    sin = ch["hogares_internet"] - ch["internet"]
    return _base(
        "internet", "sabado", anio=2022, titulo="¿Cuántos tienen internet en casa?",
        pregunta="¿Qué porcentaje de los hogares de Chivilcoy tiene internet en la vivienda?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "texto": "de los hogares tiene internet en la vivienda"},
        mapa={"titulo": "Internet en casa, en la zona", "valores": v, "dec": 1, "unidad": " %",
              "leyenda": "% de hogares con internet en la vivienda"},
        contexto=[{"numero": f"Puesto {p} de {n}", "texto": "en la zona"},
                  {"numero": miles(sin), "texto": "hogares sin internet en la vivienda"}],
        cierre="¿Cómo te conectás en casa: fibra, cable o los datos del celular?",
        narracion={
            "gancho": "¿Cuántos hogares de Chivilcoy tienen internet en casa?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el Censo 2022, en el partido de Chivilcoy el {coma(x)} por ciento de los hogares "
                          "tenía internet en la vivienda.",
            "mapa": f"En la zona, Chivilcoy queda en el puesto {p} de {n}.",
            "contexto": f"Más de {miles(round(sin, -2))} hogares no tenían conexión en la casa.",
            "cierre": "¿Cómo te conectás en casa? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("internet", "hogares con internet en la vivienda ÷ total de hogares, cada partido en "
                                           "su hoja")],
        datos={"porcentajes": v, "chivilcoy": {k: ch[k] for k in ("hogares_internet", "internet")}},
        historia={"pregunta": "¿Cómo te conectás en casa?", "opciones": ["Wifi", "Datos del celu"], "correcta": None,
                  "dato": f"En el partido, {coma(x)} % de los hogares tenía internet (Censo 2022)"},
        caption=[f"📶 Según el Censo 2022 del INDEC, en el partido de Chivilcoy el {coma(x)} % de los hogares tenía "
                 f"internet en la vivienda: puesto {p} de {n} en la zona.",
                 "💬 ¿Cómo te conectás en casa: fibra, cable o los datos del celular?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#Internet", "#Conectividad"],
    )


def tema_alquiler(c: dict):
    v = _censo_pct(c, "alquilada", "hogares_t")
    ch = c.get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x, prop = v["chivilcoy"], pct(ch["propia"], ch["hogares_t"])
    op, ok = opciones_de(x, 1, paso=12, pos=posicion("alquiler"))
    p, n, nom = _puesto(v), len(v), _nombres(c)
    rk = _ranking(v, nom)
    return _base(
        "alquiler", "sabado", anio=2022, titulo="¿Cuántos alquilan?",
        pregunta="¿Qué porcentaje de los hogares de Chivilcoy alquila la casa donde vive?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "texto": "de los hogares alquila su vivienda"},
        mapa={"titulo": "Hogares que alquilan, en la zona", "valores": v, "dec": 1, "unidad": " %",
              "leyenda": "% de hogares en vivienda alquilada"},
        contexto=[{"numero": coma(prop) + " %", "texto": "vive en casa propia"},
                  {"numero": miles(ch["alquilada"]), "texto": "hogares inquilinos"},
                  {"numero": f"Puesto {p} de {n}", "texto": "en la zona, de más a menos inquilinos"}],
        cierre="¿Alquilás o tenés casa propia? ¿Cuánto tardaste en conseguirla?",
        narracion={
            "gancho": "¿Cuántos hogares de Chivilcoy alquilan?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el Censo 2022, en el partido de Chivilcoy el {coma(x)} por ciento de los hogares "
                          "alquilaba la vivienda.",
            "mapa": f"En la zona, Chivilcoy queda en el puesto {p} de {n}: el que más alquila es {rk[0][0]}.",
            "contexto": f"La mayoría, el {coma(prop, 0)} por ciento, vive en casa propia.",
            "cierre": "¿Vos alquilás o tenés casa propia? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("tenencia", "hogares en vivienda alquilada ÷ total de hogares, por partido")],
        datos={"porcentajes": v, "chivilcoy": {k: ch[k] for k in ("hogares_t", "propia", "escritura", "alquilada",
                                                                    "cedida", "prestada", "otra_tenencia")}},
        historia={"pregunta": "¿Alquilás o tenés casa propia?", "opciones": ["Alquilo", "Casa propia"],
                  "correcta": None, "dato": f"En el partido, {coma(x)} % alquila (Censo 2022)"},
        caption=[f"🏠 Según el Censo 2022 del INDEC, en el partido de Chivilcoy el {coma(x)} % de los hogares "
                 f"alquilaba su vivienda ({miles(ch['alquilada'])} hogares) y el {coma(prop)} % vivía en casa propia.",
                 "Partido por partido, hogares inquilinos: " + ", ".join(f"{a} {coma(b)} %" for a, b in rk) + ".",
                 "💬 ¿Alquilás o tenés casa propia?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#Alquileres", "#Vivienda"],
    )


def tema_crecimiento(c: dict):
    v = {s: x["var_pob"] for s, x in c.items() if s != "_fuentes" and x.get("var_pob") is not None}
    ch = c.get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 1, paso=8, tope=60, pos=posicion("crecimiento"))
    op = ["+" + o for o in op]
    p, n, nom = _puesto(v), len(v), _nombres(c)
    rk = _ranking(v, nom)
    mas = ch["pob2022"] - ch["pob2010"]
    return _base(
        "crecimiento", "sabado", anio=2022, titulo="¿Cuánto creció Chivilcoy?",
        pregunta="¿Cuánto creció la población del partido de Chivilcoy entre los censos de 2010 y 2022?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "signo": True, "texto": f"de 2010 a 2022: "
                                                                                 f"{miles(ch['pob2022'])} habitantes"},
        mapa={"titulo": "Cuánto creció cada partido", "valores": v, "dec": 1, "unidad": " %", "signo": True,
              "leyenda": "variación de la población 2010-2022, en %"},
        contexto=[{"numero": "+" + miles(mas), "texto": "vecinos más que en 2010"},
                  {"numero": miles(ch["pob2022"]), "texto": "habitantes en 2022 (censo)"},
                  {"numero": f"Puesto {p} de {n}", "texto": "en la zona, por crecimiento"}],
        cierre="¿En qué notás que Chivilcoy creció?",
        narracion={
            "gancho": "¿Cuánto creció Chivilcoy en los últimos doce años?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace("+", "más ").replace(" %", " por ciento"),
            "revelacion": f"Entre los censos de 2010 y 2022, la población del partido creció un {coma(x)} por "
                          f"ciento: de {miles(ch['pob2010'])} a {miles(ch['pob2022'])} habitantes.",
            "mapa": f"En la zona, quedó en el puesto {p} de {n}. El que más creció fue {rk[0][0]}.",
            "contexto": f"Son {miles(mas)} vecinos más que en 2010.",
            "cierre": "¿En qué notás que Chivilcoy creció? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("poblacion", "variación relativa publicada por el INDEC (población 2022 − 2010) ÷ "
                                            "2010")],
        datos={"variacion": v, "chivilcoy": {k: ch[k] for k in ("pob2010", "pob2022", "var_pob")}},
        historia={"pregunta": "¿Chivilcoy creció mucho o poco?", "opciones": ["Mucho", "Poco"], "correcta": None,
                  "dato": f"+{coma(x)} % entre 2010 y 2022 (Censo)"},
        caption=[f"📈 Entre los censos de 2010 y 2022, la población del partido de Chivilcoy pasó de "
                 f"{miles(ch['pob2010'])} a {miles(ch['pob2022'])} habitantes: creció un {coma(x)} % "
                 f"({miles(mas)} vecinos más). Fuente: INDEC.",
                 "Partido por partido: " + ", ".join(f"{a} +{coma(b)} %" for a, b in rk) + ".",
                 "💬 ¿En qué notás que Chivilcoy creció?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#Poblacion", "#ProvinciaDeBuenosAires"],
    )


def tema_mayores(c: dict):
    v = {s: x["mayores65"].get(2022) or x["mayores65"].get("2022") for s, x in c.items()
         if s != "_fuentes" and x.get("mayores65")}
    ch = c.get("chivilcoy") or {}
    serie = {int(k): float(x) for k, x in (ch.get("mayores65") or {}).items()}
    if len(v) < 5 or "chivilcoy" not in v or len(serie) < 3:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 1, paso=7, tope=50, pos=posicion("mayores"))
    p, n, nom = _puesto(v), len(v), _nombres(c)
    primero = min(serie)
    return _base(
        "mayores", "sabado", anio=2022, titulo="¿Cuántos tienen 65 o más?",
        pregunta="¿Qué porcentaje de los vecinos del partido de Chivilcoy tiene 65 años o más?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 1, "unidad": "%", "texto": "de la población tiene 65 años o más"},
        mapa={"titulo": "Mayores de 65 en la zona", "valores": v, "dec": 1, "unidad": " %",
              "leyenda": "% de la población con 65 años o más"},
        contexto=[{"numero": f"{coma(serie[primero])} %", "texto": f"en el censo de {primero}"},
                  {"numero": f"{coma(x)} %", "texto": "en el censo de 2022"},
                  {"numero": f"Puesto {p} de {n}", "texto": "en la zona, de más a menos mayores"}],
        cierre="¿Qué le falta a Chivilcoy para los adultos mayores?",
        narracion={
            "gancho": "¿Cuántos vecinos de Chivilcoy tienen 65 años o más?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el Censo 2022, en el partido de Chivilcoy el {coma(x)} por ciento de la población "
                          "tiene 65 años o más.",
            "mapa": f"En la zona, Chivilcoy queda en el puesto {p} de {n}.",
            "contexto": f"En el censo de {primero} eran el {coma(serie[primero])} por ciento.",
            "cierre": "¿Qué le falta a Chivilcoy para los adultos mayores? Contanos en los comentarios.",
        },
        fuentes=[_fuente_censo("mayores", "porcentaje publicado por el INDEC; la serie es la de los censos "
                                          "1970-2022 del mismo cuadro")],
        datos={"porcentajes": v, "serie_chivilcoy": serie},
        historia={"pregunta": "¿Chivilcoy es una ciudad para adultos mayores?", "opciones": ["Sí", "Le falta"],
                  "correcta": None, "dato": f"{coma(x)} % tiene 65 o más (Censo 2022)"},
        caption=[f"👵 Según el Censo 2022 del INDEC, el {coma(x)} % de la población del partido de Chivilcoy tiene "
                 f"65 años o más. En el censo de {primero} era el {coma(serie[primero])} %.",
                 "💬 ¿Qué le falta a Chivilcoy para los adultos mayores?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Censo2022", "#AdultosMayores", "#Poblacion"],
    )


# ─────────────────────────────────────────────────────────────────────────────────────────────
# DOMINGO: el territorio y el campo (ArgenFields)
# ─────────────────────────────────────────────────────────────────────────────────────────────
def leer_campana(c: str) -> str:
    """«2022/23» → «2022-2023» (así lo lee bien la voz)."""
    a, _, b = c.partition("/")
    return f"{a}-{a[:2]}{b}" if len(b) == 2 and a.isdigit() else c


def _fuente_af(dato: str, anio, calculo: str, af: dict) -> dict:
    return {"fuente": f"ArgenFields ({af.get('fuente') or 'www.argenfields.com'})", "url": ARGENFIELDS_URL,
            "pagina": "https://www.argenfields.com/", "anio_dato": anio, "consultado": af.get("traido") or "",
            "dato": dato, "calculo": calculo}


def _af_vals(af: dict, fn) -> dict:
    salida = {}
    for s, p in (af.get("partidos") or {}).items():
        try:
            x = fn(p)
        except (KeyError, TypeError, IndexError):
            x = None
        if x is not None:
            salida[s] = x
    return salida


def _af_nombres(af: dict) -> dict:
    return {s: p.get("partido") or s for s, p in (af.get("partidos") or {}).items()}


def tema_tierra(af: dict):
    v = _af_vals(af, lambda p: p.get("productividad"))
    ch = (af.get("partidos") or {}).get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v or not ch.get("puesto"):
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 0, unidad="", paso=15, pos=posicion("tierra"))
    p, n = _puesto(v), len(v)
    rk = _ranking(v, _af_nombres(af))
    return _base(
        "tierra", "domingo", anio="carta de suelos del INTA", titulo="¿Qué tan buena es nuestra tierra?",
        pregunta="Del 0 al 100, ¿qué nota le pone el INTA a la tierra de Chivilcoy?",
        opciones=[o + " / 100" for o in op], correcta=ok,
        respuesta={"numero": x, "dec": 0, "unidad": "/100", "texto": "índice de productividad del suelo (INTA)"},
        mapa={"titulo": "La nota del suelo en la zona", "valores": v, "dec": 0, "unidad": "",
              "leyenda": "índice de productividad del INTA, sobre 100"},
        contexto=[{"numero": f"Puesto {ch['puesto']} de {ch['de']}", "texto": "entre los partidos bonaerenses"},
                  {"numero": str(ch.get("productividad_provincia")), "texto": "promedio de la provincia"},
                  {"numero": f"{ch['clase_1_3']} %" if ch.get("clase_1_3") else f"Puesto {p} de {n}",
                   "texto": "del partido es apto para agricultura (clases I a III)" if ch.get("clase_1_3")
                   else "en la zona"}],
        cierre="¿Qué se siembra en tu campo o en el de tu familia?",
        narracion={
            "gancho": "Del cero al cien, ¿qué nota tiene la tierra de Chivilcoy?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?",
            "revelacion": f"Según el índice de productividad del INTA, Chivilcoy tiene {x} puntos sobre cien.",
            "mapa": f"En la zona queda en el puesto {p} de {n}; en toda la provincia, en el {ch['puesto']} de "
                    f"{ch['de']}.",
            "contexto": f"El promedio bonaerense es {ch.get('productividad_provincia')}"
                        + (f", y el {ch['clase_1_3']} por ciento del partido es apto para agricultura."
                           if ch.get("clase_1_3") else "."),
            "cierre": "¿Qué se siembra en tu campo? Contanos en los comentarios.",
        },
        fuentes=[_fuente_af("índice de productividad del suelo (INTA, cartas de suelos) por partido",
                            "cartas de suelos del INTA", "el índice es del INTA; ArgenFields lo promedia por partido",
                            af)],
        datos={"productividad": v, "chivilcoy": {k: ch.get(k) for k in ("productividad", "puesto", "de",
                                                                          "productividad_provincia", "clase_1_3")}},
        historia={"pregunta": "¿La tierra de Chivilcoy es de las mejores?", "opciones": ["Sí", "No"],
                  "correcta": 0 if x > (ch.get("productividad_provincia") or 0) else 1,
                  "dato": f"{x}/100, sobre un promedio provincial de {ch.get('productividad_provincia')}"},
        caption=[f"🌱 Del 0 al 100, la tierra del partido de Chivilcoy tiene {x} puntos en el índice de "
                 f"productividad del INTA: puesto {ch['puesto']} de {ch['de']} partidos bonaerenses (el promedio de "
                 f"la provincia es {ch.get('productividad_provincia')}).",
                 "En la zona: " + ", ".join(f"{a} {b:.0f}" for a, b in rk) + ".",
                 "💬 ¿Qué se siembra en tu campo?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Campo", "#Suelo", "#INTA"],
    )


def tema_soja_peor(af: dict):
    ch = (af.get("partidos") or {}).get("chivilcoy") or {}
    r = (ch.get("rindes") or {}).get("soja") or {}
    serie = [(c, x) for c, x, *_ in r.get("serie") or [] if x]
    if len(serie) < 8 or not r.get("peor") or not r.get("mejor"):
        return None
    peor, mejor = r["peor"], r["mejor"]
    candidatas = [c for c, _ in serie if c != peor[0]]
    otras = [candidatas[len(candidatas) // 3], candidatas[-1] if candidatas[-1] != mejor[0] else candidatas[-2]]
    op = sorted({peor[0], *otras})
    v = _af_vals(af, lambda p: (p.get("rindes") or {}).get("soja", {}).get("peor", [None, None])[1])
    return _base(
        "soja_peor", "domingo", anio=f"campañas {serie[0][0]} a {serie[-1][0]}", titulo="La peor cosecha de soja",
        pregunta="¿En qué campaña la soja rindió menos en Chivilcoy?",
        opciones=op, correcta=op.index(peor[0]),
        respuesta={"numero": peor[1], "dec": 1, "unidad": " qq/ha", "texto": f"rinde estimado en la {peor[0]}"},
        mapa={"titulo": f"El rinde de la soja en la {peor[0]}", "valores": v, "dec": 1, "unidad": "",
              "leyenda": f"rinde estimado de soja en la peor campaña, qq/ha"},
        contexto=[{"numero": f"{coma(mejor[1])} qq/ha", "texto": f"la mejor: {mejor[0]}"},
                  {"numero": f"{coma(r['promedio'])} qq/ha", "texto": "el promedio de la serie"},
                  {"numero": f"{round(100 - pct(peor[1], r['promedio']))} %", "texto": "menos que el promedio"}],
        cierre="¿Cómo viene la siembra de soja este año en tu campo?",
        narracion={
            "gancho": "¿En qué campaña la soja de Chivilcoy rindió menos?",
            "opciones": "¿" + ", ".join(leer_campana(o) for o in op[:-1]) + " o " + leer_campana(op[-1]) + "?",
            "revelacion": f"Fue la campaña {leer_campana(peor[0])}, la de la sequía: el rinde estimado cayó a "
                          f"{coma(peor[1])} quintales por hectárea.",
            "mapa": "Y le pasó a toda la zona: fue la peor campaña de soja en casi todos los partidos vecinos.",
            "contexto": f"En la {leer_campana(mejor[0])}, la mejor, se habían estimado "
                        f"{coma(mejor[1])} quintales.",
            "cierre": "¿Cómo viene la soja este año? Contanos en los comentarios.",
        },
        fuentes=[_fuente_af("rinde de soja por partido y campaña (Estimaciones Agrícolas del Ministerio de "
                            "Agricultura)", f"{serie[0][0]} a {serie[-1][0]}",
                            "rinde = producción ÷ superficie cosechada, según la estimación oficial; no es una "
                            "cosecha medida en cada campo", af)],
        datos={"serie_chivilcoy": serie, "peor_por_partido": v, "peor": peor, "mejor": mejor,
               "promedio": r.get("promedio")},
        historia={"pregunta": "¿Cuál fue la peor campaña de soja?", "opciones": op[:2] if peor[0] in op[:2]
                  else [peor[0], op[0]], "correcta": None, "dato": f"{peor[0]}: {coma(peor[1])} qq/ha"},
        caption=[f"🌾 ¿En qué campaña la soja rindió menos en Chivilcoy? Fue la {peor[0]}, la de la sequía: "
                 f"{coma(peor[1])} quintales por hectárea según las estimaciones oficiales, contra "
                 f"{coma(mejor[1])} en la {mejor[0]}, la mejor.",
                 f"El promedio de la serie {serie[0][0]} a {serie[-1][0]} es {coma(r['promedio'])} qq/ha.",
                 "💬 ¿Cómo viene la soja este año en tu campo?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Soja", "#Campo", "#Agro"],
    )


def tema_anegamiento(af: dict):
    def agua(p):
        return next((x for nnn, x in p.get("limitantes") or [] if DA.plano(nnn).startswith("exceso de agua")),
                    None)
    v = _af_vals(af, agua)
    ch = (af.get("partidos") or {}).get("chivilcoy") or {}
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 0, paso=20, pos=posicion("anegamiento"))
    p, n = _puesto(v), len(v)
    return _base(
        "anegamiento", "domingo", anio="carta de suelos del INTA", titulo="El problema del agua",
        pregunta="¿Qué parte del campo de Chivilcoy tiene problemas por exceso de agua?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 0, "unidad": "%", "texto": "del partido tiene como limitante el anegamiento"},
        mapa={"titulo": "Exceso de agua en la zona", "valores": v, "dec": 0, "unidad": " %",
              "leyenda": "% del partido con limitante por exceso de agua o anegamiento"},
        contexto=[{"numero": f"Puesto {p} de {n}", "texto": "en la zona"},
                  {"numero": f"{coma(ch['franco_limosa'])} %" if ch.get("franco_limosa") else "—",
                   "texto": "es franco limoso en superficie"}],
        cierre="¿Se te anega el campo cuando llueve fuerte?",
        narracion={
            "gancho": "¿Cuánto campo de Chivilcoy sufre cuando llueve de más?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según las cartas de suelos del INTA, el {x:.0f} por ciento del partido tiene como "
                          "limitante el exceso de agua o el anegamiento.",
            "mapa": f"En la zona queda en el puesto {p} de {n}.",
            "contexto": "Es un riesgo del suelo, no una inundación que haya pasado: marca dónde el agua tarda en irse.",
            "cierre": "¿Se te anega el campo cuando llueve fuerte? Contanos en los comentarios.",
        },
        fuentes=[_fuente_af("limitantes de uso del suelo por partido (cartas de suelos del INTA)",
                            "cartas de suelos del INTA", "% de la superficie del partido con esa limitante", af)],
        datos={"exceso_agua": v},
        historia={"pregunta": "¿Se te anega el campo?", "opciones": ["Sí", "No"], "correcta": None,
                  "dato": f"{x:.0f} % del partido con limitante por exceso de agua"},
        caption=[f"💧 Según las cartas de suelos del INTA (vía ArgenFields), el {x:.0f} % del partido de Chivilcoy "
                 "tiene como limitante el exceso de agua o el anegamiento. Es un riesgo del suelo, no una "
                 "inundación ocurrida.",
                 "💬 ¿Se te anega el campo cuando llueve fuerte?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Campo", "#Suelo", "#Lluvias"],
    )


def tema_aptitud(af: dict):
    v = _af_vals(af, lambda p: p.get("clase_1_3"))
    if len(v) < 5 or "chivilcoy" not in v:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 0, paso=20, pos=posicion("aptitud"))
    p, n = _puesto(v), len(v)
    rk = _ranking(v, _af_nombres(af))
    return _base(
        "aptitud", "domingo", anio="carta de suelos del INTA", titulo="¿Cuánta tierra es agrícola?",
        pregunta="¿Qué parte del partido de Chivilcoy es tierra apta para agricultura?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 0, "unidad": "%", "texto": "es clase I a III: apta para agricultura"},
        mapa={"titulo": "Tierra agrícola en la zona", "valores": v, "dec": 0, "unidad": " %",
              "leyenda": "% del partido en clases de uso I a III (INTA)"},
        contexto=[{"numero": f"Puesto {p} de {n}", "texto": "en la zona"},
                  {"numero": f"{rk[0][1]:.0f} %", "texto": f"en {rk[0][0]}, el que más tiene"}],
        cierre="¿Tu familia trabaja en el campo?",
        narracion={
            "gancho": "¿Cuánta tierra de Chivilcoy sirve para la agricultura?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?".replace(" %", " por ciento"),
            "revelacion": f"Según el INTA, el {x:.0f} por ciento del partido tiene clase de uso uno a tres: apta para "
                          "agricultura, con limitaciones de leves a moderadas.",
            "mapa": f"En la zona queda en el puesto {p} de {n}. El que más tiene es {rk[0][0]}.",
            "contexto": "El resto sirve sobre todo para ganadería o tiene limitaciones fuertes.",
            "cierre": "¿Tu familia trabaja en el campo? Contanos en los comentarios.",
        },
        fuentes=[_fuente_af("clases de capacidad de uso de las tierras por partido (INTA)",
                            "cartas de suelos del INTA", "% de la superficie en clases I, II y III", af)],
        datos={"clase_1_3": v},
        historia={"pregunta": "¿Chivilcoy es más agrícola o ganadero?", "opciones": ["Agrícola", "Ganadero"],
                  "correcta": 0 if x >= 50 else None, "dato": f"{x:.0f} % es clase I a III"},
        caption=[f"🚜 Según el INTA (vía ArgenFields), el {x:.0f} % del partido de Chivilcoy es tierra de clase I a "
                 f"III, apta para agricultura: puesto {p} de {n} en la zona.",
                 "💬 ¿Tu familia trabaja en el campo?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Campo", "#Agricultura", "#INTA"],
    )


def tema_emergencias(af: dict):
    v = _af_vals(af, lambda p: (p.get("emergencias") or {}).get("total"))
    ch = (af.get("partidos") or {}).get("chivilcoy") or {}
    lista = (ch.get("emergencias") or {}).get("lista") or []
    if len(v) < 5 or "chivilcoy" not in v or len(lista) < 3:
        return None
    x = v["chivilcoy"]
    op, ok = opciones_de(x, 0, unidad="", paso=4, tope=40, pos=posicion("emergencias"))
    secas = [e for e in lista if "sequ" in DA.plano(e.get("motivo"))]
    p, n = _puesto(v), len(v)
    return _base(
        "emergencias", "domingo", anio=f"{lista[0]['desde'][-4:]} a {lista[-1]['hasta'][-4:]}",
        titulo="Las emergencias del campo",
        pregunta="¿Cuántas emergencias agropecuarias alcanzaron al partido de Chivilcoy?",
        opciones=op, correcta=ok,
        respuesta={"numero": x, "dec": 0, "unidad": "", "texto": "emergencias agropecuarias declaradas"},
        mapa={"titulo": "Emergencias del campo en la zona", "valores": v, "dec": 0, "unidad": "",
              "leyenda": "emergencias agropecuarias declaradas que alcanzaron a cada partido"},
        contexto=[{"numero": str(len(secas)), "texto": "fueron por sequía"},
                  {"numero": f"{lista[-1]['desde']}", "texto": "la última: " + lista[-1]["motivo"]}],
        cierre="¿Cuál fue el peor año que te tocó en el campo?",
        narracion={
            "gancho": "¿Cuántas emergencias agropecuarias tuvo Chivilcoy?",
            "opciones": f"¿{op[0]}, {op[1]} o {op[2]}?",
            "revelacion": f"Fueron {x}: emergencias declaradas que alcanzaron al partido.",
            "mapa": f"En la zona, Chivilcoy queda en el puesto {p} de {n}.",
            "contexto": f"{len(secas)} de ellas fueron por sequía." if secas else "",
            "cierre": "¿Cuál fue el peor año que te tocó en el campo? Contanos en los comentarios.",
        },
        fuentes=[_fuente_af("emergencias agropecuarias declaradas (normas en InfoLEG)",
                            f"{lista[0]['desde']} a {lista[-1]['hasta']}", "cantidad de declaraciones que incluyen "
                            "al partido", af)],
        datos={"emergencias": v, "lista_chivilcoy": lista},
        historia={"pregunta": "¿Cuál fue el peor año para el campo?", "opciones": ["La sequía", "Las inundaciones"],
                  "correcta": None, "dato": f"{x} emergencias, {len(secas)} por sequía"},
        caption=[f"☀️ {x} emergencias agropecuarias declaradas alcanzaron al partido de Chivilcoy"
                 + (f"; {len(secas)} fueron por sequía." if secas else "."),
                 "💬 ¿Cuál fue el peor año que te tocó en el campo?"],
        hashtags=["#Chivilcoy", "#ChivilcoyEnDatos", "#Campo", "#Sequia", "#Agro"],
    )


TEMAS_SABADO = {"gas_red": tema_gas_red, "cloacas": tema_cloacas, "agua": tema_agua, "internet": tema_internet,
                "alquiler": tema_alquiler, "crecimiento": tema_crecimiento, "mayores": tema_mayores}
TEMAS_DOMINGO = {"tierra": tema_tierra, "soja_peor": tema_soja_peor, "anegamiento": tema_anegamiento,
                 "aptitud": tema_aptitud, "emergencias": tema_emergencias}


def verificar(f: dict) -> list:
    """Los problemas de la ficha (lista vacía = sale)."""
    mal = []
    r = f.get("respuesta") or {}
    num = r.get("numero")
    if not isinstance(num, (int, float)):
        mal.append("la respuesta no es un número")
    elif r.get("unidad", "").strip() == "%" and not r.get("signo") and not 0 <= num <= 100:
        mal.append(f"porcentaje fuera de rango: {num}")
    op = f.get("opciones") or []
    if len(op) != 3 or len(set(op)) != 3:
        mal.append(f"las opciones no son tres distintas: {op}")
    if not isinstance(f.get("correcta"), int) or not 0 <= f["correcta"] < len(op):
        mal.append("la opción correcta no está entre las opciones")
    m = f.get("mapa") or {}
    vals = {k: x for k, x in (m.get("valores") or {}).items() if x is not None}
    if len(vals) < 5 or "chivilcoy" not in vals:
        mal.append("el mapa no tiene a Chivilcoy o tiene menos de 5 partidos")
    if isinstance(num, (int, float)) and "chivilcoy" in vals and f["clave"] not in ("soja_peor",):
        if abs(vals["chivilcoy"] - num) > 0.051:
            mal.append(f"la respuesta ({num}) no coincide con el mapa ({vals['chivilcoy']})")
    for fu in f.get("fuentes") or [{}]:
        if not fu.get("url") or not fu.get("anio_dato"):
            mal.append("falta la dirección o el año de una fuente")
    narr = f.get("narracion") or {}
    for k in ("gancho", "opciones", "revelacion", "cierre"):
        if not (narr.get(k) or "").strip():
            mal.append(f"falta la narración de «{k}»")
    if f.get("dia") == "sabado" and "partido" not in (narr.get("revelacion") or "") + (narr.get("mapa") or ""):
        mal.append("el dato del censo es del partido y la narración no lo dice")
    if len(f.get("hashtags") or []) != 5:
        mal.append("tienen que ser cinco hashtags")
    return mal


def disponibles(dia: str, censo: dict = None, af: dict = None, log=print) -> dict:
    temas = TEMAS_SABADO if dia == "sabado" else TEMAS_DOMINGO
    base = censo if dia == "sabado" else af
    salida = {}
    for k, fn in temas.items():
        try:
            f = fn(base or {})
        except Exception as e:                       # noqa: BLE001 — un tema roto no tumba los demás
            log(f"   tema {k}: {type(e).__name__}: {e}")
            continue
        if not f:
            continue
        problemas = verificar(f)
        if problemas:
            log(f"   tema {k} descartado: {'; '.join(problemas)}")
            continue
        salida[k] = f
    return salida


def elegir(dia: str, fichas: dict, historial: list, hoy: date) -> str | None:
    """El primero del orden que no salió en las últimas SEMANAS_SIN_REPETIR semanas; si todos salieron, el más
    viejo."""
    orden = [k for k in (ORDEN_SABADO if dia == "sabado" else ORDEN_DOMINGO) if k in fichas]
    if not orden:
        return None
    ultimo = {}
    for h in historial:
        if h.get("estado") in ("publicado", "generado", "listo"):
            ultimo[h["clave"]] = max(ultimo.get(h["clave"], ""), h.get("fecha") or "")
    limite = date.fromordinal(hoy.toordinal() - 7 * SEMANAS_SIN_REPETIR).isoformat()
    libres = [k for k in orden if ultimo.get(k, "") < limite]
    if libres:
        return libres[0]
    return min(orden, key=lambda k: ultimo.get(k, ""))
