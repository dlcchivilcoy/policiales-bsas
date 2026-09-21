# -*- coding: utf-8 -*-
"""Medios agregados a mano, aportados por el editor.

Por que existe este archivo y no van adentro de medios.py: medios.py lo ESCRIBE
tools/generar_registro.py a partir del sondeo automatico, asi que cualquier cosa
que se cargue ahi a mano desaparece la proxima vez que se regenera el padron.
Estos medios no salieron del sondeo — los aporto quien conoce la zona — y tienen
que sobrevivir a la regeneracion. Por eso viven aparte y medios.py los suma al
final, casando por dominio para no duplicar si el sondeo los elige por su cuenta.

Aportados no significa a ojo: cada uno se midio con tools/sondear_medios.py antes
de entrar, y se verifico de que partido es mirando a quien nombra en sus titulares
(el padron ya se comio una vez un diario de Monte Hermoso creyendolo de San Miguel
del Monte). Los campos medido_* son lo que devolvio esa sonda, con su fecha.

Los cuatro cierran el agujero de la nube: GitHub Actions corre --sin-navegador, y
estas cuatro localidades dependian de un medio que solo se lee con Playwright, asi
que en la nube se quedaban cortas. Ahora las cuatro tienen dos medios que se leen
por HTTP pelado.
"""

APORTADOS = [

    # --- Alberti ---------------------------------------------------
    {
        'localidad': 'Alberti',
        'nombre': 'Diario El Salado',
        'dominio': 'diarioelsalado.com.ar',
        'base': 'https://diarioelsalado.com.ar',
        'seccion': 'https://diarioelsalado.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://diarioelsalado.com.ar/category/policiales/feed/',
        'rss': 'https://diarioelsalado.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 8,
        'medido_el': '2026-09-21',
        # 80% policial y 0,55 notas/dia: el de mas flujo de Alberti, muy por encima
        # de Noticias Alberti (0,08/dia). Es de Alberti y no de otro pueblo del
        # Salado: nombra Alberti en 7 de 10 titulares, y a Pla y Quintana, que son
        # localidades del partido.
    },

    # --- Arrecifes -------------------------------------------------
    {
        'localidad': 'Arrecifes',
        'nombre': 'Minuto Arrecifes',
        'dominio': 'minutoarrecifes.com.ar',
        'base': 'https://minutoarrecifes.com.ar',
        'seccion': 'https://minutoarrecifes.com.ar/policiales',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 24,
        'medido_policiales': 3,
        'medido_el': '2026-09-21',
        # Reemplaza en la nube a El Informador, que necesita navegador. Seccion de
        # policiales propia pero sin RSS ni fechas: se raspa el HTML de la seccion.
    },

    # --- San Andres de Giles ---------------------------------------
    {
        'localidad': 'San Andres de Giles',
        'nombre': 'Noticias Gilenses',
        'dominio': 'noticiasgilenses.com.ar',
        'base': 'https://noticiasgilenses.com.ar',
        'seccion': 'https://noticiasgilenses.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://noticiasgilenses.com.ar/category/policiales/feed/',
        'rss': 'https://noticiasgilenses.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 20,
        'medido_policiales': 9,
        'medido_el': '2026-09-21',
        # El unico medio de Giles PROPIO del padron: InfoCiudad lo cubre desde
        # afuera. Volumen bajo (0,03 notas/dia) pero la seccion es de verdad: los 20
        # items del feed son del rubro y solo 2 aparecen tambien en el feed general.
        #
        # OJO con la ruta, que tiene trampa. /policiales/feed/ tambien responde 200,
        # pero devuelve item por item el FEED GENERAL: esa categoria no existe y
        # WordPress sirve el de siempre. Es la que habia elegido el descubridor, y
        # con ella entraban como policiales el golf y una presentacion de libro. La
        # buena es la de /category/. fetch.descubrir_seccion_policial ahora compara
        # toda seccion candidata contra el feed general y descarta la que lo repite.
    },

    # --- Suipacha --------------------------------------------------
    {
        'localidad': 'Suipacha',
        'nombre': 'Suipacha Hoy',
        'dominio': 'suipachahoy.com',
        'base': 'https://suipachahoy.com',
        'seccion': 'https://suipachahoy.com/category/policial/',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 14,
        'medido_policiales': 4,
        'medido_el': '2026-09-21',
        # Devuelve a Suipacha un medio propio en la nube: Diario Suipacha bloquea
        # los clientes automaticos y solo se lee con navegador. Ojo con la ruta:
        # la seccion es /category/policial/ en SINGULAR, y por esa "es" que falta
        # el descubridor la daba por inexistente y caia al feed general, donde
        # habia 1 policial cada 36 notas en vez de 4 cada 14.
    },
]
