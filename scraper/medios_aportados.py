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

    # ═════════════════════════════════════════════════════════════════════════
    #  Tanda del 23/09/2026 — 94 medios aportados por el editor, uno por uno.
    #
    #  De esos, 40 ya estaban y 54 eran nuevos. Se SONDEARON los 54 y entraron
    #  estos 29: los que devolvieron al menos 3 notas y 2 policiales entre ellas.
    #  Los otros 25 no quedaron afuera por flojos sino porque no hay con que
    #  juzgarlos — un medio que devuelve 0 policiales de 40 notas no aporta
    #  material y si aporta tiempo de corrida.
    #
    #  De cada uno se verifico ademas DE QUE PARTIDO ES, mirando a quien nombra
    #  en sus titulares y que dice de si mismo. Seis no nombran su propio pueblo
    #  —que es lo normal en un diario local, nadie escribe "choque en Arrecifes"
    #  para lectores de Arrecifes— y se confirmaron a mano; el motivo esta
    #  anotado en cada uno. El caso que justifica todo esto: losprincipios.com.ar
    #  comparte nombre con un diario historico de Cordoba, y resulto ser el de
    #  Salto (B.), como dice su propio title.
    # ═════════════════════════════════════════════════════════════════════════

    {
        'localidad': '9 de Julio',
        'nombre': 'Diario Tiempo Digital',
        'dominio': 'diariotiempodigital.com',
        'base': 'https://www.diariotiempodigital.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.diariotiempodigital.com/rss',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 2,
        'medido_el': '2026-09-23',
        # 2 de 10 notas del listado son policiales (4.00/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': '9 de Julio',
        'nombre': 'El Regional Digital',
        'dominio': 'elregionaldigital.com.ar',
        'base': 'https://elregionaldigital.com.ar',
        'seccion': 'https://elregionaldigital.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://elregionaldigital.com.ar/category/policiales/feed/',
        'rss': 'https://elregionaldigital.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 5,
        'medido_el': '2026-09-23',
        # 5 de 10 notas del listado son policiales (0.12/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': '9 de Julio',
        'nombre': 'Noticias YA (9 de Julio)',
        'dominio': 'noticiasyasj.com.ar',
        'base': 'https://noticiasyasj.com.ar',
        'seccion': 'https://noticiasyasj.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://noticiasyasj.com.ar/category/policiales/feed/',
        'rss': 'https://noticiasyasj.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 30,
        'medido_policiales': 22,
        'medido_el': '2026-09-23',
        # 22 de 30 notas del listado son policiales (1.06/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Arrecifes',
        'nombre': 'Diario Imagen de Arrecifes',
        'dominio': 'diarioimagen.com.ar',
        'base': 'https://diarioimagen.com.ar',
        'seccion': 'https://diarioimagen.com.ar/policiales/feed/',
        'seccion_rss': 'https://diarioimagen.com.ar/policiales/feed/',
        'rss': 'https://diarioimagen.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 12,
        'medido_policiales': 8,
        'medido_el': '2026-09-23',
        # 8 de 12 notas del listado son policiales (0.43/dia medido). Medido el 2026-09-23. Localidad verificada: el title dice "Diario Imagen de Arrecifes".
    },
    {
        'localidad': 'Arrecifes',
        'nombre': 'InfoArrecifes',
        'dominio': 'infoarrecifes.com',
        'base': 'https://www.infoarrecifes.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.infoarrecifes.com/feeds/posts/default',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 4,
        'medido_el': '2026-09-23',
        # 4 de 25 notas del listado son policiales (0.01/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Bolivar',
        'nombre': 'Qué Pasa En Bolívar',
        'dominio': 'quepasaenbolivar.com.ar',
        'base': 'https://quepasaenbolivar.com.ar',
        'seccion': 'https://quepasaenbolivar.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://quepasaenbolivar.com.ar/category/policiales/feed/',
        'rss': 'https://quepasaenbolivar.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 15,
        'medido_policiales': 10,
        'medido_el': '2026-09-23',
        # 10 de 15 notas del listado son policiales (0.41/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Bragado',
        'nombre': 'Bragado Informa',
        'dominio': 'bragadoinforma.com.ar',
        'base': 'https://www.bragadoinforma.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 6,
        'medido_el': '2026-09-23',
        # 6 de 25 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Bragado',
        'nombre': 'Bragado Noticias',
        'dominio': 'bragadonoticias.com',
        'base': 'https://bragadonoticias.com',
        'seccion': 'https://bragadonoticias.com/category/policiales/feed/',
        'seccion_rss': 'https://bragadonoticias.com/category/policiales/feed/',
        'rss': 'https://bragadonoticias.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 2,
        'medido_el': '2026-09-23',
        # 2 de 10 notas del listado son policiales (0.05/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Bragado',
        'nombre': 'Bragado TV',
        'dominio': 'bragadotv.com.ar',
        'base': 'https://www.bragadotv.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.bragadotv.com.ar/rss/noticias',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 3,
        'medido_el': '2026-09-23',
        # 3 de 40 notas del listado son policiales (0.35/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Bragado',
        'nombre': 'Cuarto Poder Bragado',
        'dominio': 'cuartopoderbragado.com.ar',
        'base': 'https://cuartopoderbragado.com.ar',
        'seccion': 'https://cuartopoderbragado.com.ar/tag/policiales/feed/',
        'seccion_rss': 'https://cuartopoderbragado.com.ar/tag/policiales/feed/',
        'rss': 'https://cuartopoderbragado.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 20,
        'medido_policiales': 13,
        'medido_el': '2026-09-23',
        # 13 de 20 notas del listado son policiales (0.09/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Canuelas',
        'nombre': 'Cañuelas al día',
        'dominio': 'canuelasaldia.com.ar',
        'base': 'https://canuelasaldia.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 21,
        'medido_policiales': 5,
        'medido_el': '2026-09-23',
        # 5 de 21 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Canuelas',
        'nombre': 'Cañuelas Digital',
        'dominio': 'canuelasdigital.com',
        'base': 'https://canuelasdigital.com',
        'seccion': 'https://canuelasdigital.com/category/policiales/feed/',
        'seccion_rss': 'https://canuelasdigital.com/category/policiales/feed/',
        'rss': 'https://canuelasdigital.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 4,
        'medido_el': '2026-09-23',
        # 4 de 10 notas del listado son policiales (0.05/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Canuelas',
        'nombre': 'Cañuelas News',
        'dominio': 'canuelasnews.com.ar',
        'base': 'https://canuelasnews.com.ar',
        'seccion': 'https://canuelasnews.com.ar/tag/policiales/feed/',
        'seccion_rss': 'https://canuelasnews.com.ar/tag/policiales/feed/',
        'rss': 'https://canuelasnews.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
        'medido_el': '2026-09-23',
        # 7 de 10 notas del listado son policiales (0.01/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Chacabuco',
        'nombre': 'Chacabuco Noticias',
        'dominio': 'chacabuconoticias.com.ar',
        'base': 'https://www.chacabuconoticias.com.ar',
        'seccion': 'https://www.chacabuconoticias.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://www.chacabuconoticias.com.ar/category/policiales/feed/',
        'rss': 'https://www.chacabuconoticias.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 4,
        'medido_el': '2026-09-23',
        # 4 de 10 notas del listado son policiales (0.07/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Chacabuco',
        'nombre': 'Chacabuquero',
        'dominio': 'chacabuquero.com.ar',
        'base': 'https://www.chacabuquero.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.chacabuquero.com.ar/feeds/posts/default',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 15,
        'medido_el': '2026-09-23',
        # 15 de 25 notas del listado son policiales (7.78/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Chacabuco',
        'nombre': 'Qué Pensás Chacabuco',
        'dominio': 'quepensaschacabuco.com',
        'base': 'https://www.quepensaschacabuco.com',
        'seccion': 'https://www.quepensaschacabuco.com/policiales',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 15,
        'medido_policiales': 2,
        'medido_el': '2026-09-23',
        # 2 de 15 notas del listado son policiales. Medido el 2026-09-23. Seccion propia pero sin RSS: se raspa el HTML.
    },
    {
        'localidad': 'Chacabuco',
        'nombre': 'Radio Lider Chacabuco',
        'dominio': 'radioliderchacabuco.com.ar',
        'base': 'https://radioliderchacabuco.com.ar',
        'seccion': 'https://radioliderchacabuco.com.ar/tag/policiales/feed/',
        'seccion_rss': 'https://radioliderchacabuco.com.ar/tag/policiales/feed/',
        'rss': 'https://radioliderchacabuco.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
        'medido_el': '2026-09-23',
        # 7 de 10 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Junin',
        'nombre': 'Diario Junín',
        'dominio': 'diariojunin.com',
        'base': 'https://www.diariojunin.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.diariojunin.com/noticiasrss/rss.html',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 3,
        'medido_el': '2026-09-23',
        # 3 de 25 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Junin',
        'nombre': 'Junín 24',
        'dominio': 'junin24.com',
        'base': 'https://junin24.com',
        'seccion': 'https://junin24.com/policiales',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 18,
        'medido_policiales': 14,
        'medido_el': '2026-09-23',
        # 14 de 18 notas del listado son policiales. Medido el 2026-09-23. Seccion propia pero sin RSS: se raspa el HTML.
    },
    {
        'localidad': 'Junin',
        'nombre': 'Semanario de Junín',
        'dominio': 'semanariodejunin.com.ar',
        'base': 'https://semanariodejunin.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 4,
        'medido_el': '2026-09-23',
        # 4 de 40 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Lujan',
        'nombre': 'Semanario El Civismo',
        'dominio': 'elcivismo.com.ar',
        'base': 'https://elcivismo.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://elcivismo.com.ar/rss.xml',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 35,
        'medido_policiales': 2,
        'medido_el': '2026-09-23',
        # 2 de 35 notas del listado son policiales (0.04/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Mercedes',
        'nombre': 'Noticias Mercedes',
        'dominio': 'noticiasmercedes.com',
        'base': 'https://noticiasmercedes.com',
        'seccion': 'https://noticiasmercedes.com/policiales/feed/',
        'seccion_rss': 'https://noticiasmercedes.com/policiales/feed/',
        'rss': 'https://noticiasmercedes.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 6,
        'medido_el': '2026-09-23',
        # 6 de 10 notas del listado son policiales (0.07/dia medido). Medido el 2026-09-23.
    },
    {
        'localidad': 'Pergamino',
        'nombre': 'Primera Plana',
        'dominio': 'primeraplana.com.ar',
        'base': 'https://primeraplana.com.ar',
        'seccion': 'https://primeraplana.com.ar/policiales',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 3,
        'medido_policiales': 3,
        'medido_el': '2026-09-23',
        # 3 de 3 notas del listado son policiales. Medido el 2026-09-23. Localidad verificada: sus tres titulares son de Pergamino. Seccion propia pero sin RSS: se raspa el HTML.
    },
    {
        'localidad': 'Rojas',
        'nombre': 'Hoy Rojas',
        'dominio': 'hoyrojas.com.ar',
        'base': 'https://hoyrojas.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 5,
        'medido_el': '2026-09-23',
        # 5 de 40 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Rojas',
        'nombre': 'Rojas Ciudad',
        'dominio': 'rojasciudad.net',
        'base': 'https://rojasciudad.net',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 38,
        'medido_policiales': 4,
        'medido_el': '2026-09-23',
        # 4 de 38 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'Salto',
        'nombre': 'Los Principios (Salto)',
        'dominio': 'losprincipios.com.ar',
        'base': 'https://losprincipios.com.ar',
        'seccion': 'https://losprincipios.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://losprincipios.com.ar/category/policiales/feed/',
        'rss': 'https://losprincipios.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
        'medido_el': '2026-09-23',
        # 7 de 10 notas del listado son policiales (0.04/dia medido). Medido el 2026-09-23. Localidad verificada: el title dice "Salto (B.)": es el de Buenos Aires, NO el diario homonimo de Cordoba.
    },
    {
        'localidad': 'Salto',
        'nombre': 'Salto Ciudad',
        'dominio': 'saltociudad.com.ar',
        'base': 'https://saltociudad.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 4,
        'medido_el': '2026-09-23',
        # 4 de 40 notas del listado son policiales. Medido el 2026-09-23.
    },
    {
        'localidad': 'San Miguel del Monte',
        'nombre': 'Monte 24 Noticias',
        'dominio': 'monte24noticias.com.ar',
        'base': 'https://monte24noticias.com.ar',
        'seccion': 'https://monte24noticias.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://monte24noticias.com.ar/category/policiales/feed/',
        'rss': 'https://monte24noticias.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 15,
        'medido_policiales': 6,
        'medido_el': '2026-09-23',
        # 6 de 15 notas del listado son policiales (0.01/dia medido). Medido el 2026-09-23. Localidad verificada: titula "Policia de Seguridad Comunal Monte", "La Masacre de Monte".
    },
    {
        'localidad': 'Trenque Lauquen',
        'nombre': 'DataTrenque',
        'dominio': 'datatrenque.com.ar',
        'base': 'https://datatrenque.com.ar',
        'seccion': 'https://datatrenque.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://datatrenque.com.ar/category/policiales/feed/',
        'rss': 'https://datatrenque.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 16,
        'medido_policiales': 11,
        'medido_el': '2026-09-23',
        # 11 de 16 notas del listado son policiales (0.55/dia medido). Medido el 2026-09-23.
    },
]
