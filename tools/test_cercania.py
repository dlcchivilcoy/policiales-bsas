# -*- coding: utf-8 -*-
"""Cercanía a Chivilcoy: las localidades prioritarias van primero. Sin red.

Nació el 27/09/2026, pedido del editor: priorizar Junín, Chacabuco, Bragado, Mercedes,
Suipacha, Alberti y 25 de Mayo (las más cercanas y con más movimiento en las redes), y
los accidentes de la Ruta 5.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")      # la consola de Windows es cp1252
from reels import cercania as C, flujo as F

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


# --- 1. El bono ------------------------------------------------------------------------
chequear("las 7 prioritarias suman, con o sin tildes y mayúsculas",
         all(C.bono(x) == C.BONO_LOCALIDAD for x in
             ("Junín", "junin", "CHACABUCO", "Bragado", "Mercedes", "Suipacha", "Alberti", "25 de Mayo")))
chequear("una lejana no suma", C.bono("Trenque Lauquen", "Robaron una moto") == 0)
chequear("vacía no suma (ni rompe)", C.bono("", "") == 0 and C.bono(None, None) == 0)
chequear("Ruta 5 suma aunque sea lejana", C.bono("9 de Julio", "Vuelco en la Ruta 5") == C.BONO_RUTA_5)
chequear("…escrita de varias formas",
         all(C.bono("Lobos", t) == 1 for t in ("Ruta Nacional Nº 5", "ruta nacional n° 5", "RN5",
                                               "cruce de las rutas 5 y 7", "Ruta Nacional 5")))
chequear("Ruta 51, 50 o el kilómetro 5 no son la Ruta 5",
         all(C.bono("Lobos", t) == 0 for t in ("Ruta 51", "ruta 50", "kilómetro 5", "a 5 cuadras")))
chequear("nombrar a Chivilcoy o a un chivilcoyano suma",
         C.bono("Pergamino", "Un chivilcoyano detenido") == C.BONO_CHIVILCOY
         and C.bono("Chacabuco", "Pelea en una escuela de Chivilcoy") == C.BONO_MAXIMO)
chequear("tope: Suipacha + Ruta 5 + Chivilcoy no pasa de BONO_MAXIMO",
         C.bono("Suipacha", "Vecino de Chivilcoy murió en la Ruta 5") == C.BONO_MAXIMO)
chequear("la pieza usa la localidad del HECHO, no la del medio",
         C.bono_pieza({"localidad": "pergamino", "localidad_hecho": "Chacabuco"}) == 2
         and C.bono_pieza({"localidad": "junin", "localidad_hecho": "Pergamino"}) == 0)
chequear("la pieza mira volanta, titular, bajada y la nota web",
         C.bono_pieza({"localidad": "lobos", "guion": {"bajada": "sobre la Ruta 5"}}) == 1
         and C.bono_pieza({"localidad": "lobos", "web": {"cuerpo": "un joven de Chivilcoy"}}) == 2)


# --- 2. El flujo: van primero y entra una segunda nota con menos exigencia -----------------
def nota(loc, titulo, kw, tipo="robo"):
    return {"localidad": loc, "localidad_medio": loc, "titulo": titulo, "score_keywords": kw,
            "tipo": tipo, "gravedad": "media", "imagen": "https://medio.test/x.jpg",
            "url": "https://medio.test/" + titulo[:10]}


a = nota("Pergamino", "Robaron una camioneta estacionada frente a una escuela del centro", 12)
b = nota("Chacabuco", "Robaron una bicicleta del patio de una vivienda del barrio norte", 12)
orden = F.elegir([a, b], 2)
chequear("a igual hecho, la de Chacabuco va antes que la de Pergamino", orden == [b, a])

primera = nota("Junín", "Detuvieron a dos jóvenes por vender droga en el barrio Villa Belgrano", 20)
cercana = nota("Junín", "Amenazó de muerte a su hijo adolescente y le allanaron la vivienda", 6)
lejana = nota("Bolívar", "Amenazó a un vecino con un cuchillo y fue aprehendido por la policía", 6)
lejana_1 = nota("Bolívar", "Secuestraron cocaína y dinero en un allanamiento del barrio Colón", 20)
elegidas = F.elegir([primera, cercana, lejana, lejana_1], 10)
chequear("segunda nota de Junín con puntaje 6: ENTRA (vara de las cercanas)", cercana in elegidas)
chequear("segunda nota de Bolívar con puntaje 6: queda afuera (vara de siempre)", lejana not in elegidas)

corta = nota("Bragado", "PRISIÓN PREVENTIVA PARA DÍAZ", 6, "judicial")
larga = nota("Bragado", "La Justicia dictó la prisión preventiva del concejal Germán Díaz de LLA", 14, "judicial")
chequear("con la vara baja, un titular demasiado corto para compararlo no entra",
         corta not in F.elegir([larga, corta], 10))
otra = nota("Bragado", "Un incendio destruyó un galpón del parque industrial durante la madrugada", 14, "incendio")
chequear("…pero con puntaje de sobra, un titular corto entra como siempre",
         dict(corta, score_keywords=9) in F.elegir([otra, dict(corta, score_keywords=9)], 10))

chequear("el puntaje suma 10 por punto de cercanía",
         F._puntaje(nota("Alberti", "Choque en la Ruta 5", 10)) - F._puntaje(nota("Lobos", "Choque", 10)) == 30)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
