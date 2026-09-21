# Dónde vive el sistema y cuánto cuesta

Números **medidos** en este proyecto el 21/09/2026, no estimados de manual.

> ## 💸 La versión de US$ 0,00
>
> **Se puede llegar a gratis, y las dos piezas ya existen en tu ecosistema.**
>
> | | En vez de | Usar | Sale |
> |---|---|---|---|
> | Ejecución | Railway Hobby (US$5/mes) | **GitHub Actions** — donde ya corre tu bot | **$0** |
> | Redacción | Claude Haiku (US$1,25/mes) | **Gemini**, tu pool de claves gratis | **$0** |
> | Borrado diario | código propio | `retention-days: 1` de Actions | **$0** |
>
> Ya está implementado: el workflow es `.github/workflows/reels.yml` y el selector de
> proveedor es `reels/ia.py`. Los detalles, las dos advertencias y los pasos para
> encenderlo están en la sección **«Cómo llegar a US$ 0»**, al final.

---

## Dónde vive cada cosa

| Pieza | Dónde | Cuesta |
|---|---|---|
| **El código** | GitHub, repo privado | **$0** — los repos privados son gratis |
| **La ejecución** (3 pasadas/día) | Railway, servicio **cron** | se mide por segundo; ver abajo |
| **Los .mp4 y las placas** | **En ningún lado por defecto** | **$0** |
| **Lo que sí querés conservar** | GitHub Release, purgado a diario | **$0** |
| **El ledger anti-duplicados** | un JSON de pocos KB en ese mismo Release | **$0** |

### Por qué los videos no se guardan en Railway

El contenedor de un cron de Railway es **efímero**: se levanta, corre, y todo lo que
escribió en disco desaparece cuando termina. Eso, que suena a limitación, acá es
exactamente lo que querés — **saturación cero y almacenamiento cero, sin hacer nada**.

Lo único que sobrevive es lo que se sube a propósito. Por eso los reels que valga la pena
guardar van como assets de un **GitHub Release**, que es el mismo patrón que ya usa tu bot
en `utils/video_host.py` (el tag `reel-latest` que se sobrescribe cada día). Gratis, y no
infla el repo porque los assets de un Release no son parte del árbol de git.

**Lo que descarté, y por qué:**

- **Volumen de Railway** — $0.15/GB/mes y hay que dimensionarlo a mano. Con el contenedor
  efímero + el Release no hace falta ninguno. Un volumen además obliga a que el servicio
  sea *always-on*, que es lo caro (ver más abajo).
- **Supabase Storage** — 1 GB gratis, alcanzaría. Pero es una pieza más para mantener y
  tu ecosistema ya tiene el patrón del Release andando.

---

## Lo que consume una pasada (medido)

| | Tiempo | CPU | Pico de RAM |
|---|---|---|---|
| Scrapeo de los 55 medios **sin navegador** | 67 s | 24,6 s | 82 MB |
| Scrapeo **con navegador** (Playwright) | 148 s | 24,7 s | **1698 MB** |
| Armado de 5 reels con video | 40 s | 17,3 s | 761 MB |
| **Total sin navegador** | **107 s** | **41,9 s** | **761 MB** |
| **Total con navegador** | **188 s** | **42,6 s** | **1698 MB** |

El navegador cuesta 80 segundos y **casi 1 GB extra de RAM**, y compra 4 medios: Diario
Suipacha, Rumores de Pehuajó y El Informador (que cubre Arrecifes y Giles). Es la palanca
de costo más grande que tenés.

---

## La cuenta

Tarifas de Railway (verificadas en su página de precios):

```
CPU     $0,00000772 por vCPU-segundo   (≈ $20 por vCPU/mes)
RAM     $0,00000386 por GB-segundo     (≈ $10 por GB/mes)
Volumen $0,00000006 por GB-segundo     (≈ $0,15 por GB/mes)
Egress  $0,05 por GB
Hobby   $5/mes, con $5/mes de crédito de uso incluido
```

**Costo por pasada** (calculado con el PICO de RAM durante toda la corrida, o sea el peor
caso — Railway cobra el uso real, que es menor):

| | Sin navegador | Con navegador |
|---|---|---|
| CPU | $0,000323 | $0,000329 |
| RAM | $0,000314 | $0,001232 |
| **Por pasada** | **$0,00064** | **$0,00156** |

**Al mes** (3 pasadas/día × 30 días = 90 corridas):

| Concepto | Sin navegador | Con navegador |
|---|---|---|
| Cómputo | $0,06 | $0,14 |
| Egress (subir ~4 MB de reels por pasada) | $0,02 | $0,02 |
| Almacenamiento | $0,00 | $0,00 |
| **Uso total** | **≈ $0,08** | **≈ $0,16** |

### Entonces, ¿cuánto pagás?

**El uso de este sistema son 8 a 16 centavos de dólar por mes.** Es ruido.

Lo que pagás de verdad es **el mínimo del plan Hobby: US$ 5/mes**, que viene con US$ 5 de
crédito de uso incluido. O sea:

- Si ya tenés Hobby y tu consumo total queda **por debajo de US$ 5**, este proyecto te sale
  **$0 extra**. Entra holgado en el crédito.
- Si te pasás del crédito, se factura la diferencia — y la parte de este sistema serían
  esos 16 centavos.

### ⚠️ El que te puede romper la cuenta es el otro proyecto

Un servicio **always-on** de apenas 0,5 GB consume:

```
0,5 GB × 2.592.000 s/mes × $0,00000386 = $5,00/mes
```

**Un solo servicio prendido todo el tiempo con medio giga se come el crédito entero.** En
la memoria del circuito del diario está anotado que el panel «siempre encendido» sale
~US$5/mes: es exactamente esta cuenta.

Este sistema de reels **no necesita estar prendido**: son 3 corridas de menos de 2 minutos
por día, o sea que el servicio está apagado el **99,6% del tiempo**. Esa es toda la
diferencia entre $0,16 y $5.

---

## El otro costo: la API de Claude

**Esto faltaba en la primera versión de este documento.** Railway es el hosting; Claude es
lo que redacta. Son dos facturas distintas.

Tarifa de **Claude Haiku 4.5**: $1,00 por millón de tokens de entrada, $5,00 por millón de
salida.

### Lo que sí hay que pagar: el guion de cada reel

| | Tokens | Costo |
|---|---|---|
| Entrada (system prompt 634 + la nota ~400) | ~1.034 | $0,00103 |
| Salida (el JSON con volanta/titular/bajada/…) | ~350 | $0,00175 |
| **Por reel** | | **$0,0028** |

5 reels × 3 pasadas × 30 días = 450 reels/mes → **≈ US$ 1,25/mes**.

### ⚠️ La trampa: NO prendas el clasificador del scraper

El scraper tiene su propio paso de IA (`scraper/clasificador.py`), que manda **las ~340
notas del día** a Claude en lotes de 8 para confirmar cuáles son policiales:

```
$0,0106 por lote × 42 lotes = $0,45 por pasada
× 90 pasadas = US$ 41/mes
```

**Treinta y tres veces más caro que los guiones, y no hace falta.** Solo 5 de esas 340
notas terminan en un reel: gastar IA clasificando las otras 335 es tirar plata.

La regla quedó **grabada en el código**, no en la buena memoria: el clasificador está
apagado por defecto y encenderlo pide el flag `--con-ia` **más** la variable de entorno
`CLASIFICADOR_IA_AUTORIZADO=1`. Sin las dos cosas, el proceso imprime la advertencia con
esta cuenta y sale sin gastar un token. La IA se usa **solo en los 5 guiones**.

### El total, entonces

| Concepto | Por mes |
|---|---|
| Railway — plan Hobby (mínimo, con US$5 de crédito) | **US$ 5,00** |
| Railway — uso real de este sistema | $0,08 – $0,16 *(sale del crédito)* |
| Claude — 450 guiones con Haiku | **US$ 1,25** |
| GitHub — repo privado + Release | $0,00 |
| Almacenamiento | $0,00 |
| **A pagar** | **≈ US$ 6,25/mes** |

Y si te tienta prender el clasificador del scraper, serían **US$ 46/mes**. Esa sola
decisión es casi todo el costo del sistema.

---

## La limpieza automática

Sin barrer nada, cada pasada deja **~9 MB**. Con 3 por día son **~810 MB/mes**.

Hay dos clases de basura y se tratan distinto:

### 1. Intermedios — se borran apenas el video está armado

Las capas que consume ffmpeg (`_texto.png`, `_foto.jpg` a 2160 px, `_fondo.png`) son
**~2 MB por pasada** y dejan de servir en el instante en que el .mp4 quedó listo. No
esperan al otro día: se borran ahí mismo, al terminar la corrida.

Una salvedad: **si el video falló, las capas se conservan**. Son lo único que queda para
diagnosticar por qué, y tirarlas sería quedarse sin evidencia.

### 2. Piezas viejas — por antigüedad

Las carpetas de corridas anteriores y los `.json`/`.csv` del scrapeo se borran a los
**`--conservar-dias` días** (por defecto **1**: el reel de hoy y nada más).

El barrido también levanta los intermedios de corridas **cortadas por la mitad** (Railway
mató el proceso, se cayó la red), que si no quedaban ahí para siempre.

### Cómo se usa

Corre **solo**, al final de cada pasada. Y se puede llamar a mano:

```bash
venv\Scripts\python.exe -m reels.limpieza --simular      # dice qué borraría, sin borrar
venv\Scripts\python.exe -m reels.limpieza --dias 1       # borrado real
venv\Scripts\python.exe -m reels.limpieza --con-release  # barre también el Release
```

Probado: liberó 9,69 MB de intermedios y 9,66 MB de corridas envejecidas a 3 días.

Para desactivarla en una corrida puntual: `--conservar-dias 0`.

---

## Las 3 pasadas en Railway

Railway usa **UTC** y Argentina es UTC−3:

| Hora AR | Cron (UTC) |
|---|---|
| 10:00 | `0 13 * * *` |
| 17:00 | `0 20 * * *` |
| 20:00 | `0 23 * * *` |

Un **solo servicio** con los tres crons, no tres servicios: cada servicio suma su propio
overhead de arranque y no hay ninguna razón para separarlos.

### Cómo bajar el costo todavía más, si hiciera falta

1. **`--sin-navegador`** → de $0,16 a $0,08/mes. Perdés 4 medios de 55.
2. **Dos pasadas en vez de tres** → un tercio menos.
3. **Menos reels por pasada.** Igual el tope real no es el costo sino TikTok: 5 borradores
   cada 24 h, así que más de 5 por día no te sirven de nada.

---

## Resumen en una línea

**≈ US$ 6,25/mes:** los US$ 5 del plan Hobby de Railway (que ya pagás y absorbe el uso de
este sistema) más US$ 1,25 de Claude por los 450 guiones. Código en GitHub gratis, videos
en ningún lado permanente, limpieza automática.

Las dos cosas que pueden hacer explotar ese número, y las dos son decisiones tuyas:

1. **Un servicio always-on** en Railway → se come los US$5 de crédito él solo.
2. **Prender el clasificador de IA del scraper** → US$ 41/mes de más, para clasificar 335
   notas por día que nunca van a ser un reel.


---

## Cómo llegar a US$ 0

### 1. La ejecución: GitHub Actions en vez de Railway — ahorra US$ 5/mes

Tu bot de corresponsales **ya corre entero en GitHub Actions**, sin Railway: `publicador.yml`
tiene sus crones y `chequeo.yml` valida el código en cada push. No hace falta una segunda
plataforma para esto.

- **Repos públicos: ilimitado y gratis.**
- **Repos privados (plan Free): 2.000 minutos/mes.** Cada pasada tarda ~3 minutos, así que
  las 90 del mes son **~270 minutos**. Entra cómodo… en teoría.

**⚠️ La advertencia que importa:** esos 2.000 minutos son **de la cuenta, no del repo**. Tu
`publicador.yml` tiene un cron `*/15 * * * *` — cada 15 minutos, o sea **2.880 corridas por
mes**. Aunque cada una dure 1 minuto, eso solo ya supera los 2.000 gratis. O sea que es muy
posible que **ya estés pagando minutos de Actions**, o estés al límite.

Antes de encender esto, mirá **Settings → Billing → Actions** y fijate cuánto te queda. Si
estás justo, hay dos salidas:

1. **Hacer PÚBLICO el repo de policiales.** Los minutos pasan a ser ilimitados y no tocan el
   cupo compartido. Las claves siguen seguras: los *secrets* de GitHub están cifrados y no se
   exponen ni en un repo público. Lo que sí queda a la vista es qué medios scrapeás.
2. **Bajar a 2 pasadas** en vez de 3, o correr la tercera en tu PC.

### 2. La redacción: Gemini en vez de Claude — ahorra US$ 1,25/mes

Ya tenés armado exactamente esto en `utils/gemini.py`: **un pool de 9 claves**, cada una de
un proyecto distinto de Google AI Studio, **cada proyecto con su propio cupo gratis**, con
rotación automática ante un 429 y caída a un modelo de respaldo que tiene su propio cupo.

`reels/ia.py` replica esa estrategia y lee **los mismos nombres de variable**, así que el
`.env` que ya tenés sirve tal cual. El guion necesita **15 pedidos por día** — nada al lado
de esos cupos.

Dos detalles:

- Usa los alias `gemini-flash-latest` y `gemini-flash-lite-latest`, que **sí tienen cupo
  gratis**. NO usa `gemini-3.8-flash`, que es el modelo PAGO de tu bot (US$0,75/1M).
- El cupo gratis de Google implica que **los datos pueden usarse para mejorar sus modelos**.
  Para notas policiales ya publicadas por otro medio el riesgo es bajo, pero es tu decisión.

Claude queda como respaldo automático: si se agotan las claves gratis, `reels/ia.py` cae a
Haiku sin que nadie intervenga. Si no querés ni eso, dejá `ANTHROPIC_API_KEY` vacío.

### 3. El borrado diario: gratis y sin código

El workflow sube los reels como artefacto con **`retention-days: 1`**: GitHub los borra solo
al día siguiente. Sin eso quedarían 90 días y el cupo de 500 MB de artefactos de un repo
privado se llenaría en una semana.

La limpieza de `reels/limpieza.py` sigue corriendo igual — es la que mantiene ordenado el
disco cuando lo corrés en tu PC.

### El total, entonces

| Concepto | Con Railway + Claude | Todo gratis |
|---|---|---|
| Ejecución | US$ 5,00 | **$0** (Actions) |
| Redacción de 450 guiones | US$ 1,25 | **$0** (Gemini) |
| Almacenamiento y borrado | $0 | **$0** |
| **Total** | **US$ 6,25/mes** | **US$ 0,00/mes** |

### Los pasos para encenderlo

1. Crear el repo en GitHub y subir el proyecto.
2. Cargar los secrets en **Settings → Secrets → Actions**: `GEMINI_API_KEY`,
   `GEMINI_API_KEY_2`, `_3`, `_4` (las mismas del bot).
3. Revisar el consumo de minutos en **Settings → Billing**.
4. Probar a mano desde la pestaña **Actions → Reels de policiales → Run workflow**, antes de
   esperar a que salte un cron.

### Lo que NO se puede hacer gratis

Para ser claro: el dominio propio, si lo querés, son **US$ 10–15 al año** y no hay versión
gratuita que sirva. Pero el sistema funciona perfectamente sin él — esa línea de la
descripción simplemente no se imprime.
