# Noticias nacionales (Infobae → web, Shorts, Facebook y carrusel)

Pedido del editor del 06/10/2026. Código en `nacionales/`, trabajo `nacionales` de
`.github/workflows/reels.yml` (corre en las mismas pasadas que policiales, en paralelo).

> **18/10/2026 (noche) — VIDEOS VIRALES DEL MUNDO** (pedido del editor: identificar los videos internacionales que se viralizan en los reels de La Nación e Infobae y sacarlos de sus webs). Los reels de Instagram de otros medios no se leen (la API de Meta lo niega sin revisión de la app; raspar Instagram va contra sus reglas): la señal sale de los canales de YouTube de La Nación, Infobae, TN y Clarín, que suben los mismos videos (`senales.videos_medios`: últimas 50 subidas, vistas por hora, 72 h; 8 unidades de cupo por pasada). Un tema que coincide con un video que explota suma hasta 25 puntos (`impacto`, componente «video»; sin vivos ni coincidencias por «muertos/heridos»). TN Internacional es fuente de Mundo (después de La Nación) y las secciones Mundo de La Nación, TN, Clarín e Infobae ya no exigen «gran tema». En Mundo va primero el tema que trae su video (en su nota o en la de otro portal del mismo tema) si está a 10 puntos o menos del primero. El video se elige con la API pública de JW (el de la nota, no los «loops» de cabecera; 720 del lado corto) y en TN, el de la portada de la nota (reproductor vodgc).
>
> **18/10/2026 (noche) — NOTAS DE LISTA** (pedido del editor tras el posteo de Netflix: «no aclaró cuáles eran las 5 películas… no podés obviar información fundamental de las notas»). El guion trae el campo `lista` (cada elemento con su dato clave); si el titular original promete N («las cinco películas», «los 10 estrenos», o «qué ver / las mejores…» = al menos 3) y la pieza nombra menos, pide otra versión y, si sigue incompleta, NO sale. La lista va completa y numerada en el texto de Instagram, YouTube y la web, y la pieza sale como carrusel con una lámina por elemento aunque la nota traiga video. El material que lee la IA pasó de 3.500 a 6.000 caracteres.
>
> **18/10/2026 (noche) — LA FILA DE 15 MINUTOS** (pedido del editor: «subí el total de las notas elegidas en
> cada corrida cada 15 minutos… máximo 12 por pasada… un posteo de categoría diferente»; «sacá el link a la
> nota en Instagram y poné el link de mi página web»; «cada una a Instagram y desactivá el carrusel de las
> 22»; la de las 23:35 completa sus 12). `reels/turnos.py`: cada pasada tiene una GRILLA, el primer turno a
> los 15 minutos del horario y uno cada 15 hasta 12 (09:20 → 12:05, 12:20 → 15:05, …, 21:20 → 23:35 son 10,
> 23:50 → 02:35). Policiales y nacionales comparten la fila: policiales reserva sus hechos (hasta 3)
> repartidos y nunca seguidos; nacionales toma, de a uno y en el momento, los turnos libres. Los dos
> trabajos siguen en paralelo y se reparten los turnos con referencias de git (`refs/turnos/<pasada>/<turno>`,
> crearla es atómico; se barren a los 2 días). En cada turno de nacionales va la categoría con el tema más
> fuerte (impacto en la variedad, puntos en las generales; −12 por pieza ya salida en la pasada), NUNCA la
> misma que el turno anterior: si solo queda una categoría, espera un turno. Topes por pasada: generales 3,
> deportes 2, espectáculos 2, mundo 2, virales 1, cine y series 1, IA 1 (`NAC_POR_PASADA`,
> `NAC_PASADA_<CATEGORIA>`); por día, de seguridad: generales 18, deportes/espectáculos/mundo 10, virales y cine
> 4, IA 3 (`NAC_POR_DIA`, `NAC_CUPO_<CATEGORIA>`). Las GENERALES también van a Instagram (reel con el video de
> la nota o carrusel explicativo con láminas). El texto de Instagram lleva «📲 Más noticias en
> www.diariolacampaña.com.ar» y nunca el link de la nota. Facebook: potencial viral 7 o más, 2 por pasada y
> 8 por día. YouTube: tope `YT_SHORTS_POR_DIA` sumando policiales; Instagram: deja la reserva del bot. El
> carrusel «Noticias nacionales de hoy» de las 22 quedó APAGADO (`--sin-carrusel`; a mano sigue
> `--solo-carrusel`). `FILA_15=0` apaga la fila (policiales vuelve a sus 30 minutos).
>
> **18/10/2026 (tarde) — TODOS los portales del PDF y PUNTAJE DE IMPACTO** (pedido del editor: «scrapeá
> todos los portales… y hacé un sistema de scoring para poner las notas que tengan más impacto viral… en el
> orden del ranking de sitios por categoría»). `nacionales/portales.py` lee 17 portales (~1.800 notas en
> ~20 s, en paralelo) con el ORDEN del PDF por categoría: deportes TyC → ESPN → Olé → AFA → Liga
> Profesional → Infobae/La Nación/Clarín/Ámbito; mundo BBC Mundo → Infobae → La Nación → Clarín → Ámbito
> (EFE, Reuters y AP no dejan leer); IA Zapier → Google Workspace → Microsoft → HubSpot → n8n → Shopify →
> diarios (Make no deja leer); espectáculos, cine y virales Infobae → La Nación → Clarín → El Cronista →
> Ámbito. Sin RSS se lee el listado y la página (TyC, AFA, Workspace, Shopify); ESPN por su API en JSON.
> `nacionales/senales.py` junta señales REALES: «más leídas» de Cronista, La Nación, Ámbito y Clarín,
> búsquedas en tendencia de Google, Google News (puesto y medios del tema) y YouTube en tendencia (vistas,
> me gusta, comentarios). `nacionales/impacto.py` da 0-100 por TEMA: fuente según el PDF 20, cobertura 20,
> lectores 20, búsquedas 15, Google News 10, YouTube 10, actualidad 5, editorial 10, con sus razones
> (quedan en la pieza y en el resumen de la corrida). Va primero la categoría con el tema más fuerte (−12
> por pieza ya salida hoy); `NAC_IMPACTO_MINIMO` (15) deja afuera lo que nadie cubre ni lee. Las nacionales
> generales siguen saliendo de Infobae, pero Ámbito, Cronista, La Nación y Clarín y las señales les suman
> hasta 35 puntos. Si la nota elegida no trae video, se busca en los otros portales del mismo tema; si su
> RSS trae solo el titular, el texto sale de la página. Facebook ya no informa compartidos de notas
> ajenas (da 0): no se usa. Registro con el estado y el puesto de cada portal: `data/registro_fuentes.json`.
>
> **18/10/2026 — VARIEDAD rehecha a pedido del editor** (`nacionales/categorias.py`): deportes, espectáculos,
> cine y series, **mundo** (internacionales), **virales** e IA para comercios, de Infobae, **La Nación**, **El
> Cronista** y los blogs de **Zapier, HubSpot y n8n**. **Cupo propio** (~10 por día, hasta 2 por corrida,
> aparte de las 12 nacionales; topes: deportes 2, espectáculos 2, mundo 2, virales 2, cine y series 1, IA 1),
> intercaladas en la tanda (segunda y cuarta). **Foto y video ORIGINALES de la nota** (el MP4 del reproductor
> propio del portal; nada generado con IA). **Instagram**: con video → **reel**; sin video → **carrusel
> explicativo** (portada + 4-6 láminas con la foto original, `placa.lamina_texto`); un **viral sin su video no
> sale**. Además: Short, nota en su sección (Mundo y Virales creadas el 18/10, diario_web 9314c3e), Facebook si
> está entre las 2 más virales y TikTok/X por Buffer. `NAC_INSTAGRAM=0` apaga el Instagram de la variedad. El
> carrusel de las 22 sale a su hora aunque la tanda de las 21:05 siga.
>
> **17/10/2026 — categorías nuevas (PDF «Prompt integral», etapa 4)** en `nacionales/categorias.py`:
> deportes (Infobae `deportes`, solo con protagonista argentino, sin «en vivo»), espectáculos
> (`teleshow`, sin galerías ni chicanas), cine y series (`que-puedo-ver`, 72 h) e IA aplicada a
> comercios (`tecno`, con el uso práctico en el TÍTULO; casi nunca hay). **Dentro del mismo cupo**
> (3 por pasada, 12 por día): como mucho `NAC_VARIEDAD_POR_PASADA` (1) por pasada, va SEGUNDA en la
> tanda, rotando la categoría que hace más que no sale; tope por día `NAC_CUPO_<CATEGORIA>`
> (deportes 2, espectáculos 2, cine y series 1, tecnologia_ia 1). La IA recibe reglas por categoría
> (resultado final o en juego, muerte confirmada y atribuida, plataforma/país/fecha del estreno,
> qué tarea resuelve la IA y lo que dice la empresa atribuido). Web: cada una en su sección
> (Deportes, y Espectáculos, Cine y series y Tecnología, creadas el 17/10 en Wix y en diario_web;
> `WIX_CAT_<CATEGORIA>` la pisa). NO van al carrusel «Noticias nacionales de hoy». Las efemérides las
> cubre el Archivo Literario (README_ARCHIVO). Registro de fuentes con estado real:
> `data/registro_fuentes.json`.

## Qué hace cada pasada (09:05, 12:05, 15:05, 18:05, 21:05, 23:35)

1. **Lee Infobae** por sus feeds RSS de sección (política, economía, sociedad, policiales,
   judiciales, salud). robots.txt lo permite (solo prohíbe el buscador). `nacionales/infobae.py`.
2. **Filtra y ordena** (`nacionales/filtro.py`, sin IA):
   - Lo que nombra a **Chivilcoy** (en cualquier parte de la nota, no la calle porteña de
     Floresta), la Ruta 5, la Zona Fría y la zona → primero.
   - Lo que toca el **bolsillo** o un trámite (ANSES, PAMI, IOMA, tarifas, paros, feriados,
     salario mínimo, dengue…) y las medidas de la Provincia.
   - **Política** (internas incluidas), **juicios**, salud y sociedad → entran con menos puntaje.
   - **Popularidad**: cuántas notas le dedica Infobae al mismo tema (+8 por nota, hasta +32).
   - Afuera: deportes, espectáculos, el exterior (salvo que hable de la Argentina), lo local de
     otras provincias, la Ciudad de Buenos Aires sola, la salud «de revista», policiales de otros
     lados salvo casos grandes (3+ notas).
3. **Hasta 3 piezas por pasada y 12 por día**, sin repetir un tema de las últimas 24 h.
4. **Guion** con Gemini (`nacionales/guion.py`): reescrito de cero, sin nombrar a Infobae,
   neutral en política, con el control de copia de policiales.
5. **La foto** (desde el 07/10): la de la nota de Infobae, en todas las redes y la web, SALVO que
   el epígrafe diga que es de una **agencia** (AP, AFP, Reuters, EFE, Getty, NA…): esas agencias
   facturan cada foto usada en un sitio. Esas notas, las que no traen foto y las que no dejan leer
   el epígrafe van con la **placa propia** (`nacionales/placa.py`: grafito con la sección en
   letras grandes). En los dos casos el motor del bot pone marca, volanta y titular.
6. **Publica**, 5 min entre piezas:
   - **YouTube**: Short en Radio del Centro con el link de su nota.
   - **Web**: nota en **Nacionales** y en la **portada** (pedido del 06/10), también en «Lo más
     leído», el archivo y los sitemaps. Lleva además la categoría interna «Nacionales
     automáticas» (b4cdfc99…), por si algún día hay que separarlas (diario_web, `SIN_REGION`).
   - **Facebook**: solo las más virales, **2 por pasada y 8 por día**: posteo con la placa (la misma del
     carrusel, estilo portal en grafito, desde el 12/10) y el link a la nota (no reels; el link solo saldría con una foto equivocada).
7. **22:00, Instagram**: carrusel «Noticias nacionales de hoy» (hasta 10 diapositivas, una por
   nota; la primera es la portada) con lo publicado desde el carrusel anterior. Desde el 12/10 va
   con el estilo portal en **grafito** (`placa.slide_carrusel`, motor del bot
   `story_image.compose_carrusel_slide`): logo arriba a la izquierda e isologo a la derecha; las
   fotos horizontales alternan uno y uno dos estilos con la foto arriba y el texto abajo, y las
   cuadradas o verticales, y las notas sin foto, van a sangre con el titular en una caja
   semitransparente que no tapa caras. Ya no hay tapa con la lista de titulares. La pasada de las 21:05 espera hasta las 22; si no corrió,
   lo saca la de las 23:35. Es un posteo normal del feed (los «reels de prueba» son solo reels).

## Interruptores (Settings → Secrets and variables → Actions → Variables)

| Variable | Qué hace |
|---|---|
| `NACIONALES=0` | Deja nacionales solo simulando (policiales sigue igual). |
| `PUBLICAR_REDES` | El de siempre: sin él, nada publica. |
| `NAC_POR_PASADA` / `NAC_POR_DIA` | Piezas por pasada (3) y por día (12). |
| `NAC_FB_POR_PASADA` / `NAC_FB_POR_DIA` | Posteos de Facebook por pasada (2) y por día (8). |

## A mano

```
venv\Scripts\python.exe -m nacionales.pasada                      # simula
venv\Scripts\python.exe -m nacionales.pasada --publicar --cuantos 1 --sin-carrusel
venv\Scripts\python.exe -m nacionales.pasada --publicar --solo-carrusel
venv\Scripts\python.exe tools\test_nacionales.py
```

Memoria: `estado/nacionales.json` (piezas, descartadas por la IA y carruseles, 7 días).

## Agenda v8 (24/10/2026): 04 solo web, 22 el carrusel del día

Todos los días, también sábado y domingo (`nacionales/agenda.py`):

| hora | qué hace |
|---|---|
| 04:00 | SOLO WEB: 5 notas de cada categoría (política, economía y sociedad —también lo provincial—, espectáculos, cine y series, tecnología/IA, mundo y virales). Ni Short, ni Facebook, ni Instagram, ni TikTok/X. `NAC_WEB_<CATEGORIA>` cambia cuántas. |
| 22:00 | UN CARRUSEL en Instagram (y el mismo álbum en Facebook, con el link a la sección) con las 10 generales más importantes del día para Chivilcoy (los puntos de `filtro.py`): las de la web de las 4 y las nuevas de la noche, que también quedan como nota en la web. `NAC_CARRUSEL_NOTAS`, `NAC_CARRUSEL_FB=0`. |

Deportes ya no sale. Sin foto real que se pueda usar, una nota no sale (tampoco en la web). Las corridas no
usan fila ni turnos: la de las 4 publica una detrás de otra.

## Agenda propia (20/10/2026, reemplazada por la v8)

Las nacionales tienen su workflow (`.github/workflows/nacionales.yml`, `python -m nacionales.pasada --agenda`) y su
agenda (`nacionales/agenda.py`). TODO sale como **reel con el video original de la nota**: sin video, no sale
(`NAC_TODO_REEL=0` vuelve a permitir el carrusel). Un posteo cada 30 minutos; las corridas van de a una.

| días | corridas | qué sale en cada corrida |
|---|---|---|
| lunes a viernes | 18 · 21 | 2 de política y 2 de economía nacional (sin Chivilcoy, región ni provincia), reel armado SOLO con la foto; ni viral, ni sociedad, ni mundo |
| sábado y domingo | 10 · 14 · 18 · 21 | 6 de las 7: viral, mundo, IA, general, deporte, cine/serie, espectáculo (1 de cada una, las más virales) |

«Mundo» = internacionales con algo policial o de violencia/conflicto (`agenda.es_mundo`).

YouTube: un reel de más de 3 minutos (sin la placa) no se sube (`YT_SHORT_MAX_SEG`); sale en Instagram y Facebook.
