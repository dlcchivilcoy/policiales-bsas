# -*- coding: utf-8 -*-
"""El relevamiento de lo publicado (reels/relevamiento.py, 12/10/2026): el mismo hecho contado por
otro medio no sale dos veces. Casos REALES que salieron repetidos, y hechos distintos que no se
tienen que frenar. Sin red: la IA se reemplaza por una respuesta fija."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from reels import publicador as PUB  # noqa: E402
from reels import relevamiento as RV  # noqa: E402

fallas, total = [], 0


def chequear(nombre, condicion):
    global total
    total += 1
    print(("OK " if condicion else "MAL") + " " + nombre)
    if not condicion:
        fallas.append(nombre)


def F(titular, lugar, cuando, url="", bajada="", medio=""):
    return RV.ficha(titular, bajada, lugar, medio, url or f"https://x.test/{abs(hash(titular))}", cuando)


PUBLICADAS = [
    F("Robaron más de 100 placas de bronce del Cementerio Judío en Carlos Casares", "Carlos Casares",
      "2026-10-11T12:21:00", "https://www.latrochadigital.com.ar/2026/10/11/robaron-placas-cementerio-judio"),
    F("Una camioneta de bomberos protagonizó un choque en la Ruta 205", "Cañuelas", "2026-09-28T15:36:00"),
    F("Se prendió fuego una camioneta en la Ruta 5 por una falla eléctrica", "Bragado", "2026-10-04T21:15:00"),
    F("Dos detenidos tras allanamientos por presunta venta de cocaína", "Bragado", "2026-10-01T12:36:00"),
    F("Choque entre una camioneta y una moto en Chacabuco", "Chacabuco", "2026-10-01T23:02:00"),
    F("Emiten alerta amarilla por tormentas fuertes y posible granizo", "Junín", "2026-10-06T18:13:00"),
]

# 1) Sin IA: lo que se decide solo con las palabras
RV._preguntar_ia = lambda nueva, cands: (_ for _ in ()).throw(RuntimeError("sin IA"))
rep = RV.repetida(F("Robaron más de un centenar de placas de bronce en el Cementerio Judío", "Junín",
                    "2026-10-12T15:31:00", medio="Robo de más de un centenar de placas de bronce"),
                  PUBLICADAS)
chequear("cementerio judío: «centenar» = 100, otro medio y otro pueblo de referencia → repetida",
         rep is not None and "Cementerio" in rep["titular"])
rep = RV.repetida(F("Una camioneta de bomberos protagonizó un choque en la Ruta 205", "Cañuelas",
                    "2026-09-28T18:15:00"), PUBLICADAS)
chequear("bomberos de Cañuelas: el mismo titular 3 horas después → repetida", rep is not None)
rep = RV.repetida(F("Una camioneta se prendió fuego en plena Ruta 5", "9 de Julio", "2026-10-05T00:27:00"),
                  PUBLICADAS)
chequear("fuego en la Ruta 5 (Bragado / 9 de Julio) → repetida por la ruta en común", rep is not None)
rep = RV.repetida(F("Dos detenidos tras allanamientos por venta de estupefacientes", "Bragado",
                    "2026-10-01T15:16:00"), PUBLICADAS)
chequear("dos detenidos en Bragado el mismo día, otra palabra para la droga → repetida (sin IA, mismo día)",
         rep is not None)
rep = RV.repetida(F("Choque entre una moto y una camioneta estacionada", "Chacabuco", "2026-10-04T12:11:00"),
                  PUBLICADAS)
chequear("otro choque de moto y camioneta en Chacabuco 3 días después: sin IA NO se frena", rep is None)
rep = RV.repetida(F("Detuvieron a un hombre por robar una bicicleta en el centro", "Lobos",
                    "2026-10-06T10:00:00"), PUBLICADAS)
chequear("un hecho que no se parece a nada → sale", rep is None)
rep = RV.repetida(F("Otro título cualquiera", "Carlos Casares", "2026-10-12T10:00:00",
                    url="https://latrochadigital.com.ar/2026/10/11/robaron-placas-cementerio-judio/"), PUBLICADAS)
chequear("la misma nota con otra forma de escribir la dirección → repetida", rep is not None and rep["como"] == "url")

# 2) Con IA: lo dudoso lo decide ella
preguntas = []


def ia_dice(indice):
    def f(nueva, cands):
        preguntas.append((nueva, cands))
        return indice, "mismo hecho"
    return f


RV._preguntar_ia = ia_dice(0)
rep = RV.repetida(F("Encontraron muerto a un ex policía en un monte", "Bolívar", "2026-10-04T18:39:00"),
                  [F("Encontraron muerto a un ex policía en una zona rural", "Bolívar", "2026-10-03T21:10:00")])
chequear("dudoso (pocas palabras): se le pregunta a la IA y, si dice que es el mismo, se frena",
         rep is not None and rep["como"] == "ia" and len(preguntas) == 1)
RV._preguntar_ia = ia_dice(-1)
rep = RV.repetida(F("Choque entre una moto y una camioneta estacionada", "Chacabuco", "2026-10-04T12:11:00"),
                  PUBLICADAS)
chequear("si la IA dice que es otro hecho, sale", rep is None)
preguntas.clear()
RV._preguntar_ia = ia_dice(0)
RV.repetida(F("Detuvieron a un hombre por robar una bicicleta en el centro", "Lobos", "2026-10-06T10:00:00"),
            PUBLICADAS)
chequear("lo que no se parece a nada ni siquiera gasta una consulta a la IA", not preguntas)

# 3) En el publicador: antes de repartir cupos, contra lo publicado y entre las piezas del lote
RV._preguntar_ia = lambda nueva, cands: (_ for _ in ()).throw(RuntimeError("sin IA"))


def pieza(n, titular, lugar, url):
    return {"orden": n, "url_original": url, "localidad_hecho": lugar, "guion": {"titular": titular}}


listas = [(pieza(1, "Robaron más de un centenar de placas de bronce en el Cementerio Judío", "Carlos Casares",
                 "https://diariojunin.test/1"), "a.mp4"),
          (pieza(2, "Un auto volcó en la Ruta 30 y el conductor resultó ileso", "Chivilcoy",
                 "https://otro.test/2"), "b.mp4"),
          (pieza(3, "Volcó un auto en la Ruta 30: el conductor salió ileso", "Chivilcoy",
                 "https://tercero.test/3"), "c.mp4")]
quedan, salteadas = PUB.sin_repetir(listas, {}, usar_ia=False, previas=list(PUBLICADAS))
chequear("publicador: la repetida de lo publicado y la repetida dentro del lote no salen",
         [p["orden"] for p, _ in quedan] == [2] and len(salteadas) == 2
         and all("repite un hecho" in s["motivo"] for s in salteadas))
ledger = {"https://diariojunin.test/1": {"instagram": {"estado": "ok"}}}
quedan, _ = PUB.sin_repetir(listas[:1], ledger, usar_ia=False, previas=list(PUBLICADAS))
chequear("una pieza que YA salió en alguna red es nuestra: sigue (para completar las otras redes)",
         len(quedan) == 1)

print(f"\n--- {total - len(fallas)}/{total} correctos ---")
sys.exit(1 if fallas else 0)
