# Policiales BSAS — scraper de policiales de 28 localidades bonaerenses

Junta noticias de **policiales, siniestros viales, incendios, robos, homicidios y
suicidios** de 55 medios digitales de 28 localidades de la provincia de Buenos Aires.

Reusa el motor de scraping de **NoticIAs Chivilcoy** (RSS + raspado HTML +
`fetch_article_details` + Claude Haiku), pero generalizado: acá no hay un parser por
medio, hay una sola estrategia que se adapta sola. Mantener 55 parsers a mano sería
inviable; descubrir el feed y la sección automáticamente es lo que hace que esto se
sostenga en el tiempo.

---

## Cómo se eligieron los medios

No están elegidos a ojo. El padrón salió de tres fuentes (el directorio de
plusnoticias, búsquedas web y medios conocidos) y después **se midió cada candidato**:

1. `tools/sondear_medios.py` visitó **153 candidatos**: probó `https`/`http`, con y
   sin `www`, buscó el feed RSS, buscó la sección de policiales, listó las notas y
   contó cuántas son policiales según el diccionario.
2. `tools/rankear.py` ordenó por lo medido y eligió los 2 mejores por localidad.
3. `tools/cobertura_regional.py` midió qué localidades cubre de verdad cada medio
   regional, para tapar los huecos con datos y no con intuición.
4. `tools/generar_registro.py` escribe `scraper/medios.py`.

Todo es reproducible: volvés a correr los cuatro scripts y el registro se rehace.

**Lo que la medición corrigió, y que una lista "a ojo" habría dejado pasar:**

| Hallazgo | Consecuencia |
|---|---|
| `montenoticias.com.ar` es de **Monte Hermoso**, no de San Miguel del Monte | Se sacó. Estaba a 500 km de la localidad pedida. |
| La Opinión de Pergamino migró a `laopinionline.ar` | El dominio del directorio estaba muerto. |
| 4 sitios devuelven **403** a clientes automáticos | Se leen con navegador real (Playwright). |
| Varias URLs `/policiales` son **falsas**: devuelven política u horarios de hospital | Se marcan `seccion_falsa` y se usa el feed general + filtro. |
| 56 de los medios vivos tienen **sección propia de policiales** | Entrar por ahí rinde 5× más que filtrar el feed general. |
| `montenoticias`, rótulos de menú y usos figurados se colaban | Se agregaron filtros y un banco de 28 pruebas que hay que mantener en verde. |

---

## Instalación

```bash
cd "D:\CLAUDE PROYECTOS\policiales-bsas"
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.ejemplo .env
```

El scraper **no necesita ninguna clave**: el diccionario de palabras clave filtra gratis y
es el comportamiento por defecto. La IA solo hace falta para los guiones de los reels
(ver [README_REELS.md](README_REELS.md)) y ahí alcanza con el cupo gratis de Gemini.

Playwright usa el **Chrome que ya tenés instalado** (`channel="chrome"`), no baja
Chromium — igual que en NoticIAs, porque el Chromium propio falla por SxS en esta
máquina.

---

## Uso

```bash
venv\Scripts\python.exe -m scraper.run
```

| Opción | Qué hace |
|---|---|
| `--horas 48` | Antigüedad máxima de las notas (por defecto 24). |
| `--localidad Junin,Bragado` | Solo esas localidades. |
| *(nada)* | Por defecto: solo diccionario. Gratis e instantáneo. |
| `--con-ia` | ⛔ Clasifica las ~340 notas con IA. **Cuesta ~US$41/mes** y está frenado por una cláusula — ver abajo. |
| `--sin-navegador` | Saltea los 4 sitios lentos que necesitan Playwright. |
| `--limite-ia 400` | Tope de notas que se mandan a Claude por corrida. |

Salida en `salida/policiales_AAAA-MM-DD_HHMM.csv` y `.json`, con: localidad, medio,
tipo de hecho, gravedad, víctimas, detenidos, titular, resumen, fecha y link.

**Rendimiento medido** (21/09/2026, los 55 medios, ventana de 72 h, sin IA):
399 candidatas → 58 duplicadas descartadas → **333 notas en 68 segundos**, con los
4 sitios que necesitan navegador incluidos.

---

## Cómo funciona el filtro híbrido

```
listar notas  →  diccionario (gratis)  →  bajar detalle  →  Claude confirma  →  CSV/JSON
```

**Paso 1 — diccionario** (`scraper/keywords.py`). Tres listas: términos FUERTES
(robo, homicidio, choque, incendio, allanamiento…), DÉBILES que suman pero solos no
alcanzan (herido, ruta, moto, bomberos…) y APAGADORES que restan (torneo, homenaje,
colecta, simulacro, "se robó el show"). El **título pesa el triple** que el cuerpo,
porque en el medio local el titular describe el hecho mientras el cuerpo arrastra
menús y "notas relacionadas".

Es generoso a propósito: es barato dejar pasar de más porque después Claude confirma,
y es caro descartar una nota buena porque de ahí no vuelve.

Banco de pruebas: `venv\Scripts\python.exe tools\test_keywords.py` (28 casos, 28 OK).
Corrélo cada vez que toques el diccionario.

**Paso 2 — Claude** (`scraper/clasificador.py`, `claude-haiku-4-5`). Confirma si es
policial y estructura el hecho: tipo, gravedad, localidad, víctimas, detenidos y un
resumen propio. Va **de a lotes de 8**: mandar las notas de a una multiplica por 8 el
costo fijo del prompt.

Si la credencial falla, el proceso **corta y no escribe nada**. Una salida sin
confirmar tiene la misma pinta que una confirmada, y después no hay cómo
distinguirlas.

---

## Los 55 medios

`local` = de la localidad · `regional` = la cubre desde afuera · 🌐 = necesita navegador
Los números son lo que midió el sondeo: *notas policiales / notas listadas*.

| Localidad | Medio 1 | Medio 2 |
|---|---|---|
| 25 de Mayo | La Mañana `lamanana.com.ar` 0/3 ⚠ | 25 Digital `25digital.com.ar` 1/20 |
| 9 de Julio | El 9 de Julio 8/10 | La Trocha Digital 7/10 |
| Alberti | Noticias Alberti 5/6 | **— no hay segundo medio —** |
| Arrecifes | Diario UNO Arrecifes 10/12 | El Informador 2ª Sec. · regional 🌐 |
| Bolívar | Presente Noticias 25/40 | La Mañana de Bolívar 11/23 |
| Bragado | Bragado es Noticia 9/10 | La Voz de Bragado 6/10 |
| Cañuelas | InfoCañuelas 16/24 | Cañuelas Noticias 2/8 |
| Carlos Casares | Casares Online 7/10 | Noticias Ruta 5 · regional |
| Carmen de Areco | InfoCiudad · regional 12/16 | Areco Ciudad · regional 3/40 |
| Chacabuco | Diario Democracia 19/40 | Chacabuco en Red 3/10 |
| Junín | **Junín Digital 27/38** | Diario Democracia 19/40 |
| Las Flores | **Noticias Las Flores 26/30** | Las Flores Digital 8/10 |
| Lincoln | La Posta del Noroeste 10/12 | La Marca de Lincoln 7/10 |
| Lobos | Lobos 24 9/10 | Lobos Ya 8/10 |
| Luján | Luján en Línea 13/20 | El Diario de Luján 4/4 |
| Mercedes | El Nuevo Cronista 6/10 | Semanario Protagonistas 2/3 |
| Navarro | Navarro en Líneas 4/10 | Navarro Noticias 0/3 ⚠ |
| Pehuajó | Rumores de Pehuajó 4/16 🌐 | Diario Noticias Pehuajó 1/40 |
| Pergamino | Diario Núcleo 18/25 | La Opinión de Pergamino 9/15 |
| Rojas | Diario Núcleo 18/25 | El Nuevo Rojense 5/10 |
| Roque Pérez | ABC Saladillo · regional 8/10 | Roque Pérez Hoy 6/6 |
| Saladillo | CN Saladillo 9/10 | ABC Saladillo 8/10 |
| Salto | Diario Núcleo · regional 18/25 | InfoSalto 3/25 |
| San Andrés de Giles | InfoCiudad · regional 12/16 | El Informador 2ª Sec. · regional 🌐 |
| San Antonio de Areco | Bosco Producciones 7/10 | Areco Ciudad · regional 3/40 |
| San Miguel del Monte | InfoCañuelas · regional 16/24 | Presente Noticias · regional |
| Suipacha | Diario Suipacha 2/19 🌐 | El Nuevo Cronista · regional |
| Trenque Lauquen | La Trocha Digital 7/10 | La Opinión de T. Lauquen 2/10 |

⚠ = tiene una URL `/policiales` que **no filtra**: se usa el feed general + diccionario.

### Lo que hay que saber antes de confiar en la tabla

- **Alberti tiene un solo medio.** Probé los cuatro vecinos con sección de policiales
  (Bragado ×2, Chacabuco, Ruta 5) y ninguno lo menciona. No lo rellené para no
  inventar cobertura.
- **7 localidades dependen de medios regionales** porque no tienen dos medios propios
  con policiales constantes: Carmen de Areco, San Andrés de Giles, San Miguel del
  Monte, Suipacha, Roque Pérez, Salto y Carlos Casares.
- **El volumen varía muchísimo.** Junín, Bolívar, Las Flores y Pergamino publican
  policiales todos los días. Saladillo, 25 de Mayo y Navarro publican por mes: en una
  ventana de 48 h te van a dar cero, y eso es correcto, no un error del scraper.
- Los números son una **foto del día del sondeo**. Volvé a correr
  `tools/sondear_medios.py` cada tanto: estos sitios cambian de CMS y se caen seguido.

---

## Estructura

```
policiales-bsas/
├── scraper/
│   ├── fetch.py          Motor: RSS, descubrimiento de feed y de sección, detalle
│   ├── keywords.py       Diccionario policial + puntaje
│   ├── navegador.py      Respaldo Playwright para sitios con 403 o JS
│   ├── clasificador.py   Claude Haiku por lotes
│   ├── medios.py         Registro de los 55 medios (GENERADO)
│   └── run.py            Orquestador
├── tools/
│   ├── harvest_directorio.py   Semilla de candidatos
│   ├── sondear_medios.py       Mide el flujo policial real
│   ├── rankear.py              Elige los 2 por localidad
│   ├── cobertura_regional.py   Qué cubre cada regional
│   ├── generar_registro.py     Escribe medios.py
│   └── test_keywords.py        Banco de pruebas del diccionario
├── data/     Padrón y mediciones
└── salida/   CSV/JSON de cada corrida
```

## Mantenimiento

Cuando un medio se caiga o cambie de CMS:

```bash
venv\Scripts\python.exe tools\sondear_medios.py          # remide todo
venv\Scripts\python.exe tools\sondear_medios.py --navegador --solo "Suipacha,Pehuajo"
venv\Scripts\python.exe tools\rankear.py
venv\Scripts\python.exe tools\generar_registro.py
```

Para agregar una localidad: sumala a `data/candidatos.json` con sus dominios y corré
los cuatro scripts.

## ⛔ La cláusula de costo del clasificador

El scraper tiene un paso de IA que manda **todas** las notas del día al modelo para
confirmar cuáles son policiales. Medido el 21/09/2026:

```
US$ 0,0106 por lote × 42 lotes = US$ 0,45 por pasada
× 90 pasadas al mes            = US$ 41 POR MES
```

**Y no hace falta:** de esas ~340 notas solo 5 terminan en un reel. Gastar IA clasificando
las otras 335 es tirar plata. El diccionario filtra gratis y da 28/28 en su banco de
pruebas; la IA que sí se usa es la de los guiones, que sale US$1,25/mes — o **$0** con el
cupo gratis de Gemini.

Por eso está **apagado por defecto** y encenderlo pide **dos gestos deliberados**: el flag
`--con-ia` **y** la variable de entorno `CLASIFICADOR_IA_AUTORIZADO=1`. Un flag suelto se
copia y se pega sin pensar; una variable con ese nombre, no. Sin las dos cosas el proceso
imprime la advertencia y sale sin gastar un token.

**No pongas esa variable en el `.env` ni en los secrets del repo.** La idea es que sea una
decisión por corrida y no un default que después nadie recuerda haber activado.

---

## Nota legal

Mismo criterio que NoticIAs Chivilcoy: **el cuerpo de la nota se usa solo para
clasificar y no se persiste**. La salida lleva titular, link, fecha y un resumen
original generado por la IA, con instrucción explícita de no copiar frases del
texto fuente (Ley 11.723). El link siempre apunta al medio original.

El respaldo con navegador no saltea ningún login ni muro de pago: son páginas
públicas que cualquiera abre en su navegador. Si vas a correr esto seguido, conviene
revisar el `robots.txt` de cada medio y espaciar las corridas — con una por hora
alcanza de sobra para el ritmo de publicación que tienen.
