# Reels de policiales — criterio, flujo y automatización

Fase 1 del sistema de reels: **genera y muestra, no publica**. Todo lo estético sale de
tu bot de corresponsales (`dlcchivilcoy/social_publisher`), replicado acá para que las
piezas salgan con tu marca y no con un diseño inventado.

---

## ⚠️ Antes que nada: TikTok no publica solo

Lo leí en tu propio `TIKTOK.md`, y cambia el plan que me planteaste:

> **Estado al 2026-09-18: la app está LIVE, pero la auditoría de Direct Post sigue
> RECHAZADA.** Los reels caen en los **borradores** de TikTok y el editor los termina de
> publicar a mano desde el celular. **No es un estado de transición: es el régimen normal
> hasta nuevo aviso.**

Los dos rechazos, en orden:

| Fecha | Motivo | ¿Se arregla tocando algo? |
|---|---|---|
| 16/09 | **Política.** «TikTok for Developers currently does not support personal or internal company use» | No. Es un renglón de las guías: aprueban herramientas para terceros, no para manejar la cuenta propia. |
| 17/09 | **Técnica.** «The media URL submitted does not meet the required technical specifications» | Tampoco: esos cinco requisitos son de `PULL_FROM_URL`, y tu bot usa `FILE_UPLOAD`. Ya lo verificaste. |

Además, un tope duro que condiciona las 3 pasadas por día:

> TikTok admite **5 borradores sin publicar cada 24 h** y al pasarse rechaza TODO.

**Qué significa para lo que pediste.** «Flujo constante sin preocuparme por nada» con
publicación automática en TikTok **hoy no es posible con esa app**. Lo máximo alcanzable
es: el sistema scrapea, arma los reels, los deja en tu bandeja de borradores, y vos abrís
la app y tocás publicar. Y como mucho **5 por día entre las tres pasadas**.

Caminos posibles, por si querés ir por alguno:
1. **Convivir con los borradores** (es lo que ya hacés). 3 pasadas × 1–2 reels = dentro del tope.
2. **Reclamar la auditoría** por escrito: en tu propio doc quedó sin responder si el
   rechazo de política sigue vivo o si quedó resuelto al arreglar la config `reels`.
3. **Publicar a mano** desde el celular con las piezas ya armadas (lo que hace la Fase 1).

Esto no bloquea nada de lo que sigue: la generación es idéntica en los tres casos.

---

## La anatomía de la placa (lo que aprendí de tu sistema)

Salida 1080×1920. De arriba hacia abajo:

```
┌──────────────────────────────────────┐ y=0
│  ZONA MUERTA — acá tapa la app       │
│  (TikTok: «Siguiendo / Para vos»)    │ y=150   SEGURO_ARRIBA
├──────────────────────────────────────┤
│ DIARIO LA CAMPAÑA | RADIO DEL   [C]  │  marca IZQUIERDA (gris #E9ECF0, Montserrat 28)
│ @diarioyradio                        │  isologo DERECHA (150px, margen 72)
│                                      │
│            VOLANTA                   │  NARANJA #F77F00, centrada, 42 → mín. 30
│      TITULAR GRANDE EN HASTA         │  BLANCO, centrado, 88 → mín. 46, 3 renglones
│      TRES RENGLONES                  │  Archivo Narrow SemiBold, interlínea 1.08
│       Bajada en naranja, siempre     │  NARANJA, centrada, 44 → mín. 30, 3 renglones
│       cerrada en punto.              │  Libre Franklin SemiBold, interlínea 1.26
├──────────────────────────────────────┤ y_img (nunca más abajo que 940)
│                                      │
│       FOTO / VIDEO A SANGRE          │  full bleed, mínimo 980px de alto
│                                      │  se funde con el fondo por arriba en 110px
├──────────────────────────────────────┤
│   Pie: primera oración de la nota    │  GRIS, solo si sobra hueco bajo foto apaisada
├──────────────────────────────────────┤ y=1590   (1920 − BANDA_SEGURO)
│  ZONA MUERTA — usuario, caption,     │
│  botones                             │
└──────────────────────────────────────┘ y=1920
```

### Las reglas que no son obvias y que respeté

- **El isologo va a la DERECHA arriba** y la marca a la izquierda, haciendo pareja. La
  derecha está libre ahí porque la columna de botones de la app arranca recién en y=900.
- **El texto editorial arranca por debajo del isologo.** Tu código calcula la caja real
  del PNG y baja el texto si hace falta: sin eso, un titular largo se le monta encima. Ese
  bug solo aparece con textos largos, por eso costó verlo en su momento.
- **El color de fondo NO es fijo:** sale del color dominante de la propia foto, apagado a
  luz 0.13 y saturación 0.26. Medido sobre 36 matices, en el peor caso el blanco queda en
  14,5:1 de contraste y el naranja en 5,5:1 — los dos por encima del 4,5:1 de la norma.
- **Los cuerpos son TOPES, no medidas fijas.** Si el texto no entra, la tipografía baja
  sola hasta el mínimo. Nunca se corta con «…».
- **La bajada cierra SIEMPRE en punto.** Se arma por oraciones enteras: si la segunda no
  entra, se queda con la primera. Dice menos, pero se lee completa.
- **La volanta larga se achica antes de cortarse,** y recién si ni al cuerpo mínimo entra
  en un renglón, pasa a dos.
- **Tres tipografías, una por trabajo:** Montserrat es la marca y no se toca; Archivo
  Narrow para el titular (angosta = letra más grande en dos renglones); Libre Franklin
  para el resumen (humanista = aguanta mejor el tamaño chico sobre una foto).
- **El alto de renglón se mide con `getmetrics()`**, no con el bbox de una muestra: el
  bbox se olvida de la cola de la «g» y el bloque siguiente arranca pegado. (Me pasó, lo
  corregí mirando tu implementación.)

### Lo que cambié a propósito

| Tu bot | Acá | Por qué |
|---|---|---|
| Regla: NO nombrar la localidad salvo que el contenido la justifique | La localidad SÍ va siempre | Allá la IA metía «Chivilcoy» por costumbre. Acá son 28 localidades y la localidad **es** el producto. Pero sale del scraper, nunca de la IA. |
| Foto apaisada → se respeta la proporción y el hueco lo llena el pie | Si no hay pie, la foto se recorta y llena | Sin pie, ese hueco quedaba como una franja muerta que se comía el tercio inferior. |

---

## El flujo, paso a paso

```
scraper.run                 333 notas policiales de 28 localidades
      ↓
reels.flujo · elegir()      puntúa y elige las mejores, UNA POR LOCALIDAD
      ↓
reels.flujo · material()    vuelve a bajar la nota para tener cuerpo (no se persiste)
      ↓
reels.guion                 volanta · titular · bajada · zócalo · pie · descripción
      ↓
reels.placa                 render 1080×1920 en DOS CAPAS (fondo+foto / texto)
      ↓
reels.video                 .mp4 vertical con zoom lento + placa de cierre
      ↓
salida_reels/<fecha_hora>/  .jpg + .mp4 + .json por pieza  ← FASE 1 TERMINA ACÁ
```

### Cómo elige qué nota merece reel

No todas las 333 notas dan un reel. El puntaje combina:

| Señal | Peso |
|---|---|
| Tipo de hecho | homicidio 100 · siniestro vial 90 · incendio 85 · narco 80 · robo 75 … suicidio 30 |
| Gravedad | fatal +40 · grave +25 · media +10 |
| Intensidad del diccionario | hasta +24 |
| **Tiene foto** | **+30** — sin imagen el reel queda pobre |
| Hay víctimas | +15 |

Y después **reparte por localidad**: primero una de cada una, y recién si faltan completa
con las que sobraron. Tres reels seguidos de Junín dejan sin cobertura a las otras 27.

### La descripción SEO

Misma arquitectura que la tuya: **el cuerpo lo escribe la IA, el cierre lo escribe el
código**. Es la decisión de `utils/branding.py` — cuando el modelo escribía la dirección,
salía sin la Ñ o en punycode.

```
{2 a 4 frases, CADA UNA en su propio párrafo, separadas por renglón en blanco}

📰 Fuente: {medio} ({localidad})

📲 Más noticias de {localidad} en {sitio}        ← cuando definas el dominio

#{Localidad} #{TipoDeHecho} #{Tema} #BuenosAires  ← máx. 6, localidad PRIMERO
```

El hashtag de localidad va primero porque es el que trae a la gente del lugar. Se
normaliza sin tildes ni eñes (`#Canuelas`, no `#Cañuelas`): los hashtags con caracteres
no ASCII se rompen en varias plataformas. Tope duro de 2200 caracteres, que es el máximo
del caption de TikTok contando los hashtags.

---

## El video

La pieza tiene **dos tramos** y un fundido de 0,6 s entre ellos:

| Tramo | Dura | Qué se ve |
|---|---|---|
| La nota | 8 s | Fondo de color + foto con **zoom lento** (1.00 → 1.12) + texto **quieto** encima |
| El cierre | 3 s | `placa_final.png`, la misma que usa tu bot |

Total **10,4 s**, entre 550 KB y 1 MB por reel.

### Por qué la placa se compone en dos capas

Si se animara la placa entera, el titular escalaría junto con la foto y se leería mal.
Así que `placa.componer()` dibuja en dos capas separadas y recién al final las junta:

- **base** — el fondo de color y la foto;
- **capa** — el isologo y todo el texto, sobre transparente.

Con `capas=True` se guardan las dos por separado (`_texto.png`, `_foto.jpg`, `_fondo.png`)
y ffmpeg anima la de abajo con `zoompan` mientras superpone la de arriba quieta. **El JPG
fijo sale de juntar exactamente esas mismas dos capas**, así no puede haber diferencia
entre lo que se ve en la imagen y lo que se ve en el video.

La foto se guarda al **doble de resolución** (2160 px de ancho): el zoom se come píxeles y
si se parte de 1080 la imagen llega blanda al final del recorrido.

### Codificación

Mismos valores que tu `video.py`, y por la misma razón que anotaste ahí: sin control de
tasa, libx264 deja un reel de 1080×1920 en más de 20 MB, que tarda una eternidad en
abrirse desde el celular para revisarlo — y es lo mismo que después sube a la red, donde
igual lo vuelven a comprimir.

```
libx264 · preset veryfast · CRF 26 · maxrate 3500k · bufsize 7000k
yuv420p · 30 fps · +faststart · sin audio
```

El ffmpeg sale de `imageio-ffmpeg==0.6.0`, **con la versión fijada**. Acá pasó lo que
predice tu comentario: en este Windows trae `ffmpeg 7.1-essentials (gyan.dev)` y en el
Linux de la nube trae `7.0.2-static (johnvansickle)`. O sea que probar un reel en la PC
NO prueba el ffmpeg que va a correr en producción.

### El zócalo queda sin usar (a propósito)

El guion genera el campo `zocalo` porque tu prompt lo genera, pero **esta composición no
lo dibuja**. El zócalo pertenece a la OTRA estética tuya: la del `overlay_reel.png` con la
caja negra en (175, 1481), que se usa cuando la fuente es un video de corresponsal que
llena el cuadro. El estilo «placa» —el de 2026-09-18, que es el que repliqué— pone el
texto arriba y la imagen abajo, y ahí el zócalo no tiene lugar. Queda generado por si
alguna vez querés la otra variante.

---

## Uso

```bash
venv\Scripts\python.exe -m scraper.run --horas 12              # traer noticias (sin IA, gratis)
venv\Scripts\python.exe -m reels.flujo --cuantos 5             # armar los reels
```

| Opción | Qué hace |
|---|---|
| `--cuantos 3` | Cuántos reels generar (default 5). |
| `--localidad Junin,Bragado` | Solo esas localidades. |
| `--con-ia` | El guion lo redacta Claude. **Necesario para material publicable.** |
| `--entrada archivo.json` | Usar otro scrapeo en vez del último. |
| `--sin-video` | Solo la placa fija, sin armar el .mp4 (más rápido para revisar). |
| `--conservar-dias 1` | Cuántos días de corridas guardar. `0` desactiva la limpieza. |
| `--proveedor gemini` | Forzar proveedor de IA. Vacío = Gemini si hay claves (gratis). |
| `--sin-ledger` | Ignorar la memoria y permitir repetir notas ya usadas. |

### ⚠️ El camino sin IA NO es publicable

Sin `--con-ia` la bajada **reproduce oraciones del medio de origen** tal cual, y el zócalo
es un recorte del titular en vez de un hecho de 5 palabras. Sirve para ver la estética y
el flujo — que es lo que pediste para esta fase — pero publicar texto copiado del medio no
es lo mismo que resumirlo con palabras propias.

Cada pieza se marca con `apto_para_publicar: false` y el proceso lo avisa al terminar, para
que ningún paso posterior lo tome por publicable por error.

La clave de Claude que hay en el `.env` local de `noticias-chivilcoy` está **vencida**
(devuelve 401): la viva está en Railway. Con una clave válida en el `.env` de este proyecto,
`--con-ia` redacta con las reglas editoriales de tu bot, adaptadas a policiales:
presunción de inocencia, sin morbo, sin inventar nombres, sin mayúsculas sostenidas.

---

## Dónde vive y cuánto cuesta

Está todo medido en **[COSTOS.md](COSTOS.md)**. El resumen:

- **Código** en GitHub privado (gratis), **ejecución** en Railway como cron, **videos** en
  ningún lado permanente (el contenedor es efímero).
- Una pasada consume 107 s y 761 MB de pico → **$0,0006**. Las 90 del mes: **~$0,08**.
  Con el navegador prendido, ~$0,16.
- Lo que pagás es el mínimo del plan **Hobby: US$5/mes, con US$5 de crédito incluido**.
  Este sistema entra holgado adentro de ese crédito.
- ⚠️ Un solo servicio *always-on* de 0,5 GB se come los US$5 enteros. Este no lo necesita:
  está apagado el 99,6% del tiempo.
- La **limpieza corre sola** al final de cada pasada: borra los intermedios de ffmpeg
  (~2 MB) y las corridas de más de 1 día. Sin eso serían ~810 MB/mes.

---

## Lo que falta para el automatismo en Railway

Diseñado, **no desplegado** (pediste ver el flujo primero).

### Las 3 pasadas

Railway usa **UTC** y Argentina es UTC−3:

| Hora AR | Cron (UTC) | Qué hace |
|---|---|---|
| 10:00 | `0 13 * * *` | Scrapea las últimas 14 h y arma los reels de la mañana |
| 17:00 | `0 20 * * *` | Scrapea desde las 10 y arma los del mediodía |
| 20:00 | `0 23 * * *` | Scrapea desde las 17 y arma el cierre del día |

Ventanas sin solapamiento, para que no se repita la misma nota en dos pasadas. El dedup
por URL ya está en el scraper; falta un **ledger persistente** entre corridas, que en
Railway necesita volumen — misma lección del proyecto del diario: los volúmenes **no se
comparten entre servicios**, así que todo va en UN servicio.

### Respetar el tope de TikTok

5 borradores por 24 h. Con 3 pasadas eso es **1 o 2 reels por pasada, nunca más**. El
generador ya acepta `--cuantos`; falta el contador que lleve la cuenta del día y frene
antes de gastar un pedido que TikTok va a rechazar igual (tu `TikTokFrenado` hace
exactamente eso, se puede portar).

### Lo que hay que resolver antes de encender

1. **Clave de Claude válida** en el `.env` del proyecto. Sin eso no hay material publicable.
2. **Decidir el dominio** del producto, para la línea «Más noticias de X en …».
3. **Costo del always-on** en Railway (~US$5/mes), igual que en el circuito del diario.
   Ojo que ahora hay ffmpeg en la ecuación: armar 5 reels por corrida es CPU, no red.
4. **Quién revisa.** Con `--con-ia` el texto es propio, pero son notas policiales: conviene
   una pantalla de aprobación antes de que salga, como la que ya tenés para los videos.
5. **Música.** El reel sale SIN audio, igual que los tuyos. En TikTok la canción se le pone
   desde la app al publicar, que es justamente lo que hoy hacés a mano.

---

## Archivos

```
reels/
├── marca.py    Constantes de identidad, copiadas de video.py con sus comentarios
├── placa.py    Render 1080×1920 con Pillow (port de placa_layout)
├── guion.py    Nota → volanta/titular/bajada/zócalo + descripción SEO
├── video.py    Armado del .mp4 con ffmpeg (zoom lento + fundido + cierre)
├── limpieza.py Borrado de intermedios y retención por antigüedad
└── flujo.py    Orquestador de la Fase 1. NO importa platforms.tiktok a propósito.
marca/          Tus assets: logo_reel, overlay, fondo, placa_final + las 3 tipografías
salida_reels/   Una carpeta por corrida, con .jpg y .json por pieza
```
