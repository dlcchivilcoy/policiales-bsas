# Noticias nacionales (Infobae → web, Shorts, Facebook y carrusel)

Pedido del editor del 06/10/2026. Código en `nacionales/`, trabajo `nacionales` de
`.github/workflows/reels.yml` (corre en las mismas pasadas que policiales, en paralelo).

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
5. **Placa propia** (`nacionales/placa.py`): la foto de Infobae no se usa nunca. Fondo grafito con
   la sección en letras grandes; el motor del bot le pone marca, volanta y titular.
6. **Publica**, 5 min entre piezas:
   - **YouTube**: Short en Radio del Centro con el link de su nota.
   - **Web**: nota en **Nacionales** y en la **portada** (pedido del 06/10), también en «Lo más
     leído», el archivo y los sitemaps. Lleva además la categoría interna «Nacionales
     automáticas» (b4cdfc99…), por si algún día hay que separarlas (diario_web, `SIN_REGION`).
   - **Facebook**: solo las más virales, **2 por pasada y 8 por día**: posteo con la placa y el
     link a la nota (no reels; el link solo saldría con una foto equivocada).
7. **22:00, Instagram**: carrusel «Noticias nacionales de hoy» (tapa + hasta 9 diapositivas) con
   lo publicado desde el carrusel anterior. La pasada de las 21:05 espera hasta las 22; si no corrió,
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
