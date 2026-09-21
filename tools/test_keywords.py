# -*- coding: utf-8 -*-
"""Banco de pruebas del diccionario policial. Corrolo cada vez que toques keywords.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.keywords import puntuar

CASOS = [
    # --- deben entrar ---
    ("Chocaron dos autos en la Ruta 5 y hay un herido grave", True),
    ("Detuvieron a un hombre por el robo a una vivienda", True),
    ("Incendio consumió una casa en el barrio Norte", True),
    ("Violento asalto a una familia en zona rural", True),
    ("Hallaron muerto a un hombre en su domicilio", True),
    ("Un motociclista murió en el acto tras chocar con un camión", True),
    ("Allanamiento en el barrio: secuestraron marihuana y detuvieron a dos", True),
    ("Femicidio: detuvieron a la pareja de la víctima", True),
    ("Vuelco en la Ruta 7: trasladaron a dos personas al hospital", True),
    ("Denunció una entradera y se llevaron dinero y joyas", True),
    ("Tragedia vial: cuatro muertos en un choque frontal", True),
    ("Robaron en un comercio del centro durante la madrugada", True),
    # Casos reales que se escapaban del diccionario (vistos en el sondeo)
    ("Recuperaron siete terneros Aberdeen Angus robados de un campo", True),
    ("Buscaban a un hombre de 87 años y lo encontraron sin vida en un descampado", True),
    ("Ruta 5 accidentada: dos camiones volcaron con pocas horas de diferencia", True),
    ("Operativo cerrojo: tres hombres fueron aprehendidos", True),
    # Un hecho policial puede pasar en un contexto deportivo y sigue siendo policial
    ("Un joven fue apuñalado tras un partido de fútbol en Lincoln", True),
    ("Incidentes en el clásico: detuvieron a cuatro hinchas", True),
    # --- no deben entrar ---
    ("El equipo local se robó el show en la final", False),
    ("Se realizó una charla sobre seguridad vial en la escuela", False),
    ("Homenaje a los bomberos voluntarios en su aniversario", False),
    ("Nuevo asfalto para el barrio San Juan", False),
    ("El intendente inauguró la obra del polideportivo", False),
    ("Colecta anual de los bomberos: cómo colaborar", False),
    ("Comenzó el torneo de fútbol infantil", False),
    ("Capacitación para comerciantes sobre prevención de estafas", False),
    ("Aumentó la venta de vehículos usados en la región", False),
    ("Simulacro de evacuación en la escuela primaria", False),
]

if __name__ == "__main__":
    ok = 0
    for titulo, esperado in CASOS:
        r = puntuar(titulo)
        bien = r["probable"] == esperado
        ok += bien
        marca = "OK " if bien else "MAL"
        print(f"{marca} score={r['score']:>4} esp={str(esperado):<5} | {titulo[:60]}")
        if not bien:
            print(f"      aciertos={r['aciertos'][:6]} apagadores={r['apagadores']}")
    print(f"\n--- {ok}/{len(CASOS)} correctos ---")
    sys.exit(0 if ok == len(CASOS) else 1)
