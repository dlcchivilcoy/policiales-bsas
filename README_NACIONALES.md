# Noticias nacionales (Infobae → web, Shorts, Facebook y carrusel)

Pedido del editor del 06/10/2026. Código en `nacionales/`, trabajo `nacionales` de
`.github/workflows/reels.yml` (corre en las mismas pasadas que policiales, en paralelo).

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
