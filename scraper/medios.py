# -*- coding: utf-8 -*-
"""Registro de medios: los 2 de mayor flujo policial por localidad.

GENERADO por tools/generar_registro.py — no editar a mano; cambiar el
padron (data/candidatos.json) o los rellenos del generador y volver a correrlo.

Cada eleccion sale de medir el sitio, no de suponer: tools/sondear_medios.py
cuenta cuantas notas policiales publica cada candidato y tools/rankear.py
ordena. Los campos "medido_*" son lo que devolvio el sondeo.

  seccion   -> URL de la seccion de policiales (via preferida)
  rss       -> feed general, respaldo cuando no hay seccion
  navegador -> el sitio bloquea clientes automaticos: se lee con Playwright
  alcance   -> "local" o "regional" (cubre la localidad desde afuera)

Ultima regeneracion: 2026-09-21
"""

MEDIOS = [

    # --- 25 de Mayo ------------------------------------------------
    {
        'localidad': '25 de Mayo',
        'nombre': 'La Mañana (25 de Mayo)',
        'dominio': 'lamanana.com.ar',
        'base': 'https://www.lamanana.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.lamanana.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 3,
        'medido_policiales': 0,
        # El diario de 25 de Mayo. Su URL /policiales devuelve notas de politica, asi que se usa el feed general + filtro.
    },
    {
        'localidad': '25 de Mayo',
        'nombre': '25 Digital',
        'dominio': '25digital.com.ar',
        'base': 'https://www.25digital.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.25digital.com.ar/index.php/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 20,
        'medido_policiales': 1,
        # Segundo medio local; sin seccion propia, entra por feed general + filtro.
    },

    # --- 9 de Julio ------------------------------------------------
    {
        'localidad': '9 de Julio',
        'nombre': 'El 9 de Julio',
        'dominio': 'diarioel9dejulio.com.ar',
        'base': 'https://www.diarioel9dejulio.com.ar',
        'seccion': 'https://www.diarioel9dejulio.com.ar/seccion/policiales/feed/',
        'seccion_rss': 'https://www.diarioel9dejulio.com.ar/seccion/policiales/feed/',
        'rss': 'https://www.diarioel9dejulio.com.ar/feed',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 8,
    },
    {
        'localidad': '9 de Julio',
        'nombre': 'La Trocha Digital',
        'dominio': 'latrochadigital.com.ar',
        'base': 'https://www.latrochadigital.com.ar',
        'seccion': 'https://www.latrochadigital.com.ar/categoria/policiales/feed/',
        'seccion_rss': 'https://www.latrochadigital.com.ar/categoria/policiales/feed/',
        'rss': 'https://www.latrochadigital.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
    },

    # --- Alberti ---------------------------------------------------
    {
        'localidad': 'Alberti',
        'nombre': 'Noticias Alberti',
        'dominio': 'noticiasalberti.com',
        'base': 'https://noticiasalberti.com',
        'seccion': 'https://noticiasalberti.com/category/policiales/feed/',
        'seccion_rss': 'https://noticiasalberti.com/category/policiales/feed/',
        'rss': 'https://noticiasalberti.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 6,
        'medido_policiales': 5,
        # Unico medio de Alberti con seccion de policiales activa.
    },

    # --- Arrecifes -------------------------------------------------
    {
        'localidad': 'Arrecifes',
        'nombre': 'Diario UNO Arrecifes',
        'dominio': 'unoarrecifes.com',
        'base': 'https://unoarrecifes.com',
        'seccion': 'https://unoarrecifes.com/category/policiales/feed/',
        'seccion_rss': 'https://unoarrecifes.com/category/policiales/feed/',
        'rss': 'https://unoarrecifes.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 12,
        'medido_policiales': 10,
        # Seccion de policiales por RSS, 10 de cada 12 notas del tema.
    },
    {
        'localidad': 'Arrecifes',
        'nombre': 'El Informador (2ª Sección)',
        'dominio': 'diarioelinformador.com',
        'base': 'https://diarioelinformador.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'regional',
        'navegador': True,
        'medido_notas': None,
        'medido_policiales': None,
        # Cubre toda la 2a Seccion (Arrecifes, Areco, Giles, Rojas, Salto). Bloquea clientes automaticos: se lee con navegador.
    },

    # --- Bolivar ---------------------------------------------------
    {
        'localidad': 'Bolivar',
        'nombre': 'Presente Noticias',
        'dominio': 'presentenoticias.com',
        'base': 'https://www.presentenoticias.com',
        'seccion': 'https://www.presentenoticias.com/policiales',
        'seccion_rss': None,
        'rss': 'https://www.presentenoticias.com/rss/noticias',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 25,
    },
    {
        'localidad': 'Bolivar',
        'nombre': 'La Mañana (Bolívar)',
        'dominio': 'diariolamanana.com.ar',
        'base': 'https://www.diariolamanana.com.ar',
        'seccion': 'https://www.diariolamanana.com.ar/policiales.html',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 23,
        'medido_policiales': 11,
    },

    # --- Bragado ---------------------------------------------------
    {
        'localidad': 'Bragado',
        'nombre': 'Bragado es Noticia',
        'dominio': 'bragadoesnoticia.com.ar',
        'base': 'https://bragadoesnoticia.com.ar',
        'seccion': 'https://bragadoesnoticia.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://bragadoesnoticia.com.ar/category/policiales/feed/',
        'rss': 'https://bragadoesnoticia.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 9,
    },
    {
        'localidad': 'Bragado',
        'nombre': 'La Voz de Bragado',
        'dominio': 'lavozdebragado.com.ar',
        'base': 'https://lavozdebragado.com.ar',
        'seccion': 'https://lavozdebragado.com.ar/categoria/policiales/feed/',
        'seccion_rss': 'https://lavozdebragado.com.ar/categoria/policiales/feed/',
        'rss': 'https://lavozdebragado.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 6,
    },

    # --- Canuelas --------------------------------------------------
    {
        'localidad': 'Canuelas',
        'nombre': 'InfoCañuelas',
        'dominio': 'infocanuelas.com',
        'base': 'https://www.infocanuelas.com',
        'seccion': 'https://www.infocanuelas.com/seccion/policiales/',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 24,
        'medido_policiales': 16,
    },
    {
        'localidad': 'Canuelas',
        'nombre': 'Cañuelas Noticias',
        'dominio': 'canuelasnoticias.com',
        'base': 'https://canuelasnoticias.com',
        'seccion': 'https://canuelasnoticias.com/category/policiales/feed/',
        'seccion_rss': 'https://canuelasnoticias.com/category/policiales/feed/',
        'rss': 'https://canuelasnoticias.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 8,
        'medido_policiales': 2,
    },

    # --- Carlos Casares --------------------------------------------
    {
        'localidad': 'Carlos Casares',
        'nombre': 'Casares Online',
        'dominio': 'casaresonline.com.ar',
        'base': 'https://casaresonline.com.ar',
        'seccion': 'https://casaresonline.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://casaresonline.com.ar/category/policiales/feed/',
        'rss': 'https://casaresonline.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
        # Seccion de policiales por RSS, 7 de cada 10 notas del tema.
    },
    {
        'localidad': 'Carlos Casares',
        'nombre': 'Noticias Ruta 5',
        'dominio': 'noticiasruta5.com',
        'base': 'https://noticiasruta5.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 1,
        # Cubre el corredor Bragado-9 de Julio-Casares-Pehuajo-Trenque Lauquen. Sin seccion: feed general + filtro.
    },

    # --- Carmen de Areco -------------------------------------------
    {
        'localidad': 'Carmen de Areco',
        'nombre': 'InfoCiudad',
        'dominio': 'infociudad.com.ar',
        'base': 'https://infociudad.com.ar',
        'seccion': 'https://infociudad.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://infociudad.com.ar/category/policiales/feed/',
        'rss': 'https://infociudad.com.ar/feed/',
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 16,
        'medido_policiales': 12,
        # Seccion de policiales activa sobre la region de Areco.
    },
    {
        'localidad': 'Carmen de Areco',
        'nombre': 'Areco Ciudad',
        'dominio': 'arecociudad.com.ar',
        'base': 'https://arecociudad.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 3,
        # Cubre Carmen de Areco y la zona. Sin seccion: feed general + filtro.
    },

    # --- Chacabuco -------------------------------------------------
    {
        'localidad': 'Chacabuco',
        'nombre': 'Diario Democracia',
        'dominio': 'diariodemocracia.com',
        'base': 'https://www.diariodemocracia.com',
        'seccion': 'https://www.diariodemocracia.com/ciudad/chacabuco/',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 19,
    },
    {
        'localidad': 'Chacabuco',
        'nombre': 'Chacabuco en Red',
        'dominio': 'chacabucoenred.com',
        'base': 'https://chacabucoenred.com',
        'seccion': 'https://chacabucoenred.com/category/policiales/feed/',
        'seccion_rss': 'https://chacabucoenred.com/category/policiales/feed/',
        'rss': 'https://chacabucoenred.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 3,
    },

    # --- Junin -----------------------------------------------------
    {
        'localidad': 'Junin',
        'nombre': 'Junín Digital',
        'dominio': 'junindigital.com',
        'base': 'https://www.junindigital.com',
        'seccion': 'https://www.junindigital.com/policiales',
        'seccion_rss': None,
        'rss': 'https://www.junindigital.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 38,
        'medido_policiales': 27,
    },
    {
        'localidad': 'Junin',
        'nombre': 'Diario Democracia',
        'dominio': 'diariodemocracia.com',
        'base': 'https://www.diariodemocracia.com',
        'seccion': 'https://www.diariodemocracia.com/policiales',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 19,
    },

    # --- Las Flores ------------------------------------------------
    {
        'localidad': 'Las Flores',
        'nombre': 'Noticias Las Flores',
        'dominio': 'noticiaslasflores.com.ar',
        'base': 'https://www.noticiaslasflores.com.ar',
        'seccion': 'https://www.noticiaslasflores.com.ar/categoria/policiales/feed/',
        'seccion_rss': 'https://www.noticiaslasflores.com.ar/categoria/policiales/feed/',
        'rss': 'https://www.noticiaslasflores.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 30,
        'medido_policiales': 26,
    },
    {
        'localidad': 'Las Flores',
        'nombre': 'Las Flores Digital',
        'dominio': 'lasfloresdigital.com.ar',
        'base': 'https://lasfloresdigital.com.ar',
        'seccion': 'https://lasfloresdigital.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://lasfloresdigital.com.ar/category/policiales/feed/',
        'rss': 'https://lasfloresdigital.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 8,
    },

    # --- Lincoln ---------------------------------------------------
    {
        'localidad': 'Lincoln',
        'nombre': 'La Posta del Noroeste',
        'dominio': 'lapostadelnoroeste.com.ar',
        'base': 'https://lapostadelnoroeste.com.ar',
        'seccion': 'https://lapostadelnoroeste.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://lapostadelnoroeste.com.ar/category/policiales/feed/',
        'rss': 'https://lapostadelnoroeste.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 12,
        'medido_policiales': 10,
    },
    {
        'localidad': 'Lincoln',
        'nombre': 'La Marca de Lincoln',
        'dominio': 'lamarcadelincoln.com.ar',
        'base': 'https://lamarcadelincoln.com.ar',
        'seccion': 'https://lamarcadelincoln.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://lamarcadelincoln.com.ar/category/policiales/feed/',
        'rss': 'https://lamarcadelincoln.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
    },

    # --- Lobos -----------------------------------------------------
    {
        'localidad': 'Lobos',
        'nombre': 'Lobos 24',
        'dominio': 'lobos24.com.ar',
        'base': 'https://lobos24.com.ar',
        'seccion': 'https://lobos24.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://lobos24.com.ar/category/policiales/feed/',
        'rss': 'https://lobos24.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 9,
    },
    {
        'localidad': 'Lobos',
        'nombre': 'Lobos Ya',
        'dominio': 'lobosya.com.ar',
        'base': 'https://lobosya.com.ar',
        'seccion': 'https://lobosya.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://lobosya.com.ar/category/policiales/feed/',
        'rss': 'https://lobosya.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 8,
    },

    # --- Lujan -----------------------------------------------------
    {
        'localidad': 'Lujan',
        'nombre': 'Luján en Línea',
        'dominio': 'lujanenlinea.com.ar',
        'base': 'https://www.lujanenlinea.com.ar',
        'seccion': 'https://www.lujanenlinea.com.ar/seccion/policiales/feed/',
        'seccion_rss': 'https://www.lujanenlinea.com.ar/seccion/policiales/feed/',
        'rss': 'https://www.lujanenlinea.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 20,
        'medido_policiales': 13,
    },
    {
        'localidad': 'Lujan',
        'nombre': 'El Diario de Luján',
        'dominio': 'diariodelujan.com',
        'base': 'https://diariodelujan.com',
        'seccion': 'https://diariodelujan.com/tag/policiales/feed/',
        'seccion_rss': 'https://diariodelujan.com/tag/policiales/feed/',
        'rss': 'https://diariodelujan.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 4,
        'medido_policiales': 4,
    },

    # --- Mercedes --------------------------------------------------
    {
        'localidad': 'Mercedes',
        'nombre': 'El Nuevo Cronista',
        'dominio': 'elnuevocronista.com',
        'base': 'https://elnuevocronista.com',
        'seccion': 'https://elnuevocronista.com/category/policiales/feed/',
        'seccion_rss': 'https://elnuevocronista.com/category/policiales/feed/',
        'rss': 'https://elnuevocronista.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 6,
    },
    {
        'localidad': 'Mercedes',
        'nombre': 'Semanario Protagonistas',
        'dominio': 'sprotagonistas.com.ar',
        'base': 'https://sprotagonistas.com.ar',
        'seccion': 'https://sprotagonistas.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://sprotagonistas.com.ar/category/policiales/feed/',
        'rss': 'https://sprotagonistas.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 3,
        'medido_policiales': 2,
    },

    # --- Navarro ---------------------------------------------------
    {
        'localidad': 'Navarro',
        'nombre': 'Navarro en Líneas',
        'dominio': 'navarroenlineas.com.ar',
        'base': 'https://navarroenlineas.com.ar',
        'seccion': 'https://navarroenlineas.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://navarroenlineas.com.ar/category/policiales/feed/',
        'rss': 'https://navarroenlineas.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 4,
        # Seccion de policiales real.
    },
    {
        'localidad': 'Navarro',
        'nombre': 'Navarro Noticias',
        'dominio': 'navarronoticias.com',
        'base': 'https://navarronoticias.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://navarronoticias.com/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 3,
        'medido_policiales': 0,
        # Primer diario digital de Navarro. Su URL /policiales devuelve notas generales: se usa el feed general + filtro.
    },

    # --- Pehuajo ---------------------------------------------------
    {
        'localidad': 'Pehuajo',
        'nombre': 'Rumores de Pehuajó',
        'dominio': 'rumoresdepehuajo.com.ar',
        'base': 'https://rumoresdepehuajo.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': True,
        'medido_notas': 16,
        'medido_policiales': 4,
        # Tiene seccion de policiales propia. Bloquea clientes automaticos (403): se lee con navegador.
    },
    {
        'localidad': 'Pehuajo',
        'nombre': 'Diario Noticias Pehuajó',
        'dominio': 'diarionoticiaspehuajo.com',
        'base': 'https://www.diarionoticiaspehuajo.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.diarionoticiaspehuajo.com/rss',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 1,
        # Diario local con RSS; sin seccion propia, entra por feed general + filtro.
    },

    # --- Pergamino -------------------------------------------------
    {
        'localidad': 'Pergamino',
        'nombre': 'Diario Núcleo',
        'dominio': 'diarionucleo.com',
        'base': 'https://diarionucleo.com',
        'seccion': 'https://diarionucleo.com/policiales',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 18,
    },
    {
        'localidad': 'Pergamino',
        'nombre': 'La Opinión (Pergamino)',
        'dominio': 'laopinionline.ar',
        'base': 'https://laopinionline.ar',
        'seccion': 'https://laopinionline.ar/seccion/policiales/',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 15,
        'medido_policiales': 9,
    },

    # --- Rojas -----------------------------------------------------
    {
        'localidad': 'Rojas',
        'nombre': 'Diario Núcleo',
        'dominio': 'diarionucleo.com',
        'base': 'https://diarionucleo.com',
        'seccion': 'https://diarionucleo.com/ciudad/rojas/',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 18,
    },
    {
        'localidad': 'Rojas',
        'nombre': 'El Nuevo Rojense',
        'dominio': 'elnuevorojense.com.ar',
        'base': 'https://elnuevorojense.com.ar',
        'seccion': 'https://elnuevorojense.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://elnuevorojense.com.ar/category/policiales/feed/',
        'rss': 'https://elnuevorojense.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 5,
    },

    # --- Roque Perez -----------------------------------------------
    {
        'localidad': 'Roque Perez',
        'nombre': 'ABC Saladillo',
        'dominio': 'abcsaladillo.com.ar',
        'base': 'https://www.abcsaladillo.com.ar',
        'seccion': 'https://www.abcsaladillo.com.ar/tema/policiales/feed/',
        'seccion_rss': 'https://www.abcsaladillo.com.ar/tema/policiales/feed/',
        'rss': 'https://www.abcsaladillo.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 8,
    },
    {
        'localidad': 'Roque Perez',
        'nombre': 'Roque Pérez Hoy',
        'dominio': 'roqueperezhoy.com.ar',
        'base': 'https://www.roqueperezhoy.com.ar',
        'seccion': 'https://www.roqueperezhoy.com.ar/policiales',
        'seccion_rss': None,
        'rss': 'https://www.roqueperezhoy.com.ar/rss/noticias',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 6,
        'medido_policiales': 6,
    },

    # --- Saladillo -------------------------------------------------
    {
        'localidad': 'Saladillo',
        'nombre': 'CN Saladillo',
        'dominio': 'cnsaladillo.com.ar',
        'base': 'https://cnsaladillo.com.ar',
        'seccion': 'https://cnsaladillo.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://cnsaladillo.com.ar/category/policiales/feed/',
        'rss': 'https://cnsaladillo.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 9,
    },
    {
        'localidad': 'Saladillo',
        'nombre': 'ABC Saladillo',
        'dominio': 'abcsaladillo.com.ar',
        'base': 'https://www.abcsaladillo.com.ar',
        'seccion': 'https://www.abcsaladillo.com.ar/tema/policiales/feed/',
        'seccion_rss': 'https://www.abcsaladillo.com.ar/tema/policiales/feed/',
        'rss': 'https://www.abcsaladillo.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 8,
    },

    # --- Salto -----------------------------------------------------
    {
        'localidad': 'Salto',
        'nombre': 'Diario Núcleo',
        'dominio': 'diarionucleo.com',
        'base': 'https://diarionucleo.com',
        'seccion': 'https://diarionucleo.com/ciudad/salto/',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 18,
    },
    {
        'localidad': 'Salto',
        'nombre': 'InfoSalto',
        'dominio': 'infosalto.com.ar',
        'base': 'https://www.infosalto.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': 'https://www.infosalto.com.ar/feeds/posts/default',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 25,
        'medido_policiales': 3,
    },

    # --- San Andres de Giles ---------------------------------------
    {
        'localidad': 'San Andres de Giles',
        'nombre': 'InfoCiudad',
        'dominio': 'infociudad.com.ar',
        'base': 'https://infociudad.com.ar',
        'seccion': 'https://infociudad.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://infociudad.com.ar/category/policiales/feed/',
        'rss': 'https://infociudad.com.ar/feed/',
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 16,
        'medido_policiales': 12,
        # Seccion de policiales activa; es el medio que mas nombra a Giles en sus titulares.
    },
    {
        'localidad': 'San Andres de Giles',
        'nombre': 'El Informador (2ª Sección)',
        'dominio': 'diarioelinformador.com',
        'base': 'https://diarioelinformador.com',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'regional',
        'navegador': True,
        'medido_notas': None,
        'medido_policiales': None,
        # 4 menciones a Giles en el muestreo. Se lee con navegador.
    },

    # --- San Antonio de Areco --------------------------------------
    {
        'localidad': 'San Antonio de Areco',
        'nombre': 'Bosco Producciones',
        'dominio': 'boscoproducciones.com.ar',
        'base': 'https://boscoproducciones.com.ar',
        'seccion': 'https://boscoproducciones.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://boscoproducciones.com.ar/category/policiales/feed/',
        'rss': 'https://boscoproducciones.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
        # Seccion de policiales por RSS.
    },
    {
        'localidad': 'San Antonio de Areco',
        'nombre': 'Areco Ciudad',
        'dominio': 'arecociudad.com.ar',
        'base': 'https://arecociudad.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 3,
        # Portal de Areco y la zona. Sin seccion: feed general + filtro.
    },

    # --- San Miguel del Monte --------------------------------------
    {
        'localidad': 'San Miguel del Monte',
        'nombre': 'InfoCañuelas',
        'dominio': 'infocanuelas.com',
        'base': 'https://www.infocanuelas.com',
        'seccion': 'https://www.infocanuelas.com/tags/san-miguel-del-monte',
        'seccion_rss': None,
        'rss': None,
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 24,
        'medido_policiales': 16,
        # No hay medio propio vivo en Monte. InfoCanuelas tiene pagina de la localidad con 24 notas y 6 policiales. OJO: montenoticias.com.ar NO sirve, es de Monte Hermoso (a 500 km).
    },
    {
        'localidad': 'San Miguel del Monte',
        'nombre': 'Presente Noticias',
        'dominio': 'presentenoticias.com',
        'base': 'https://www.presentenoticias.com',
        'seccion': 'https://www.presentenoticias.com/tag/746/san-miguel-del-monte',
        'seccion_rss': None,
        'rss': 'https://www.presentenoticias.com/rss/noticias',
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 40,
        'medido_policiales': 25,
        # Tiene pagina propia de San Miguel del Monte. Cobertura mas fina que la seccion general.
    },

    # --- Suipacha --------------------------------------------------
    {
        'localidad': 'Suipacha',
        'nombre': 'Diario Suipacha',
        'dominio': 'diariosuipacha.com.ar',
        'base': 'https://diariosuipacha.com.ar',
        'seccion': None,
        'seccion_rss': None,
        'rss': None,
        'alcance': 'local',
        'navegador': True,
        'medido_notas': 19,
        'medido_policiales': 2,
        # Unico diario propio de Suipacha. Bloquea clientes automaticos (403): se lee con navegador.
    },
    {
        'localidad': 'Suipacha',
        'nombre': 'El Nuevo Cronista',
        'dominio': 'elnuevocronista.com',
        'base': 'https://elnuevocronista.com',
        'seccion': 'https://elnuevocronista.com/category/policiales/feed/',
        'seccion_rss': 'https://elnuevocronista.com/category/policiales/feed/',
        'rss': 'https://elnuevocronista.com/feed/',
        'alcance': 'regional',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 6,
        # Semanario de Mercedes con seccion de policiales; menciona Suipacha en su cobertura.
    },

    # --- Trenque Lauquen -------------------------------------------
    {
        'localidad': 'Trenque Lauquen',
        'nombre': 'La Trocha Digital',
        'dominio': 'latrochadigital.com.ar',
        'base': 'https://www.latrochadigital.com.ar',
        'seccion': 'https://www.latrochadigital.com.ar/categoria/policiales/feed/',
        'seccion_rss': 'https://www.latrochadigital.com.ar/categoria/policiales/feed/',
        'rss': 'https://www.latrochadigital.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 7,
    },
    {
        'localidad': 'Trenque Lauquen',
        'nombre': 'La Opinión (Trenque Lauquen)',
        'dominio': 'laopinion.com.ar',
        'base': 'https://laopinion.com.ar',
        'seccion': 'https://laopinion.com.ar/category/policiales/feed/',
        'seccion_rss': 'https://laopinion.com.ar/category/policiales/feed/',
        'rss': 'https://laopinion.com.ar/feed/',
        'alcance': 'local',
        'navegador': False,
        'medido_notas': 10,
        'medido_policiales': 2,
    },
]


# Los medios aportados a mano por el editor. Van DESPUES de la lista generada y en
# su propio modulo porque este archivo se reescribe entero cada vez que se corre
# tools/generar_registro.py: si vivieran aca adentro, la proxima regeneracion se
# los llevaria puestos sin que nadie se entere.
from scraper.medios_aportados import APORTADOS as _APORTADOS

_YA = {m['dominio'] for m in MEDIOS}
MEDIOS = MEDIOS + [m for m in _APORTADOS if m['dominio'] not in _YA]


LOCALIDADES = sorted({m['localidad'] for m in MEDIOS})


def por_localidad(localidad):
    return [m for m in MEDIOS if m['localidad'] == localidad]
