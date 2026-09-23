# Corrida manual: cómo se arma una tanda y qué mirar

Este archivo es la receta de una pasada hecha a mano, y el registro de todo lo que
se aprendió armándolas. La automatización está **apagada** (los crons de
`.github/workflows/reels.yml` están comentados) porque la clave de Gemini es paga:
hoy el sistema corre solo cuando alguien lo dispara.

---

## Los tres comandos

```bat
venv\Scripts\python.exe -m scraper.run
venv\Scripts\python.exe -m reels.flujo --con-ia --cuantos 14 --sin-ledger
venv\Scripts\python.exe tools\galeria.py
```

El último deja una página en la carpeta de la corrida para revisar todo junto:
placa, video, texto del posteo y el link a la nota original.

**`--sin-ledger` es solo para las vistas previas.** Apaga la memoria de pasadas
anteriores, no el control de repetidos dentro de la tanda (son dos cosas
distintas, y confundirlas hizo salir el mismo femicidio dos veces). En una pasada
de verdad va sin ese flag, para que no se repita nada de los últimos 5 días.

**Pedir más de lo que hay no da más.** Si se piden 14 y hay 12 notas buenas, salen
12: el sistema no rellena con material flojo. Ver *El relleno* más abajo.

---

## Qué mira el scraper

**Solo las notas de HOY**, día calendario argentino (UTC-3 fijo, el país no tiene
horario de verano). Es el default; `--ventana 48` existe solo para probar.

> **Consecuencia que hay que tener presente:** a las 10 de la mañana, un hecho de
> anoche a las 23:30 queda afuera, porque calendariamente es de ayer. Si se quiere
> que la primera pasada del día levante la madrugada, es una línea en
> `_en_ventana()`.

**Tres fuentes por medio**, no una:

| Fuente | Qué aporta |
|---|---|
| Sección de policiales | Viene acotada al rubro. Es la mejor cuando existe y se lee por RSS. |
| Feed general | Las últimas noticias que publica el medio. |
| Portada (HTML) | Se raspa aparte del feed. |

Lo medido el 22/09: de 31 notas, **14 entraron por el feed y 12 de ellas no estaban
en la sección de su propio medio**. En estos diarios la nota sale primero en
portada y la categorizan después, si se acuerdan. Por eso se miran las tres.

La portada, en cambio, **no aportó ni una nota única** y costó 80% más de tiempo
(60 s → 108 s). El motivo es estructural: la portada trae bloques de "lo más leído"
y destacados, que son notas viejas — sumó 38 candidatas y las 38 se cayeron por
fecha. El feed y la sección son cronológicos; la portada es curada. Está activa
igual, pero si algún día molesta la demora, es lo primero que se puede sacar.

---

## Qué llega a ser reel y qué no

**Sin foto ni video, no hay reel.** La placa queda con media pantalla vacía y el
.mp4 pesa 330 KB contra 800 de una con foto, porque es casi todo fondo liso. Se
descartan antes de elegir, así no ocupan un lugar de la tanda ni gastan una llamada
a la IA. El 22/09 fueron 13 de 34.

**Se reparte por la localidad del HECHO, no la del medio.** Un medio de Chacabuco
republica un femicidio de Pergamino: eso es una nota de Pergamino. Resolverlo antes
de redactar arregla tres cosas de una — la volanta de la placa, el hashtag del
posteo, y que dos medios distintos cubriendo el mismo hecho no ocupen dos lugares.
El 22/09, **7 de 35 notas estaban mal atribuidas**, y salía impreso en la placa
("NARCOTRÁFICO EN 9 DE JULIO" para un hecho de Bragado).

### El relleno
La primera vuelta reparte una nota por localidad. La segunda completa con una
segunda nota de alguna localidad ya usada, y ahí es **más** exigente, no menos,
porque lo que entra es lo que quedó abajo en el orden:

- puntaje del diccionario ≥ 8 (el umbral general es 5, que sirve para "revisá
  esto", no para ocupar un lugar);
- y que no sea un hecho que ya está en la tanda.

Para lo segundo, el parecido de titulares no alcanza: dos medios titulan el mismo
hecho muy distinto. «Dictan prisión preventiva al edil libertario Díaz» y «Prisión
preventiva para el concejal de Bragado acusado de vender drogas» comparten tres
palabras de trece — jaccard 0,19. Pero esas tres son las distintivas, así que entre
notas de la **misma localidad** se mide cuánto del titular más corto está contenido
en el otro: ese par da 0,43 y dos hechos distintos rara vez pasan de 0,25.

---

## Video

El reel usa el **video de la nota** si el medio publicó uno propio, y la foto si
no. El clip se recorta a la caja de la imagen, se loopea si es más corto que el
tramo, y el texto queda fijo encima. Sale sin audio, porque el cierre es una placa
muda y pegar un tramo con sonido a uno sin sonido deja el reel con audio a la
mitad.

Solo cuenta el video **alojado por el medio** (`og:video`, `<video>`, `<source>`).
Un iframe de YouTube o un embed de Facebook no: no se bajan así, y además son de
otro.

> **Lo medido el 22/09: 0 de 35 notas tenían video propio.** De los iframes
> encontrados, 29 eran publicidades y 6 eran el widget de playlist de YouTube del
> propio sitio, no el video de la noticia. Estos diarios publican fotos, no video.
> La capacidad está hecha y probada; el material todavía no existe.

---

## Peso de los archivos

Bajado el 23/09 a pedido del editor, porque con más flujo de posteo lo que pesa la
cuenta importa. **−37% por pieza** (1304 KB → 819 KB). Una tanda de 12 pasa de 15,3 a
9,6 MB.

El número de CRF **no se eligió a ojo**: se codificó la misma pieza a 26, 30 y 32 y
se comparó recorte a recorte, texto y foto por separado.

| | tamaño |
|---|---|
| CRF 26 / veryfast (antes) | 672 KB |
| CRF 30 / medium | 624 KB |
| **CRF 32 / slow (ahora)** | **519 KB** |

A 32 no se degrada nada visible, por dos razones propias de estas piezas: el texto es
color plano sobre fondo plano, que se comprime casi gratis, y **la foto de origen ya
viene blanda** —son imágenes chicas de web estiradas a 1080— así que el límite de
nitidez lo pone la foto, no el codificador. Encima TikTok recomprime todo al subir.

> Ojo con el atajo de pensar que un preset más lento siempre achica: a CRF fijo,
> `medium` dio un archivo **más grande** que `veryfast` (767 contra 672 KB), porque
> gasta bits en preservar detalle. Lo que achica es el CRF; `slow` aporta recién
> combinado con él. Cuesta 4 segundos más por pieza.

La placa bajó de calidad 95 a 85 (430 → 259 KB). Si alguna vez entran fotos de calidad
de verdad, revisar los dos números: ahí sí se va a ver.

---

## La localidad, siempre visible

La volanta tiene que decir de dónde es la noticia: es lo primero que busca el lector
de un pueblo. Se pide en el prompt **y** se garantiza en código, porque pedir no es
garantizar — el modelo escribía «Justicia bonaerense» y «Operativo policial en la
región», y así el lector no tiene cómo saber si la noticia es de su ciudad o de una
que queda a 200 km.

El código no toca la volanta en dos casos, los dos a propósito:

- **Si el titular ya nombra la localidad.** Repetirla arriba y abajo queda como un
  error de armado.
- **Si la volanta ya dice un lugar** (tiene un « en »). «Accidente en Sunchales» es un
  piloto de Pehuajó que volcó en Santa Fe: agregarle « en Pehuajó» no solo daba
  «Accidente en Sunchales en Pehuajó», afirmaba que el hecho pasó en Pehuajó. Que
  falte la localidad es una molestia; que diga la equivocada es un error publicado.

---

## Aire entre la foto y el pie

El pie es el texto gris bajo una foto apaisada. Estaba pegado al filo de la foto y se
leían como un solo bloque.

El aire sale de la **foto**, no del texto, y eso costó dos intentos fallidos que
conviene no repetir:

1. Recortar la zona del pie → el pie **desapareció entero**: el hueco bajo una
   apaisada es de unos 95 px y dos renglones lo llenan justo.
2. Empujar el texto hacia abajo → no tenía a dónde, por lo mismo.

Lo que funciona: dibujar la foto 28 px más corta. Sobre una foto de ~600 px es un 4%
que no se ve; perder el pie sí se ve.

---

## Cadencia de publicación: 5 minutos entre posteo y posteo

Decidido por el editor. **No es estético**: subir cinco videos seguidos en el mismo
minuto es el patrón más fácil de reconocer que tiene una cuenta automatizada, y las
redes lo tratan como spam antes de mirar el contenido. Espaciarlos hace que la tanda
parezca una redacción trabajando y no un script vaciando una cola.

**En las corridas manuales está apagado**, que es como corre esto hoy: una vista
previa se mira toda junta, y ponerle horarios a algo que se revisa a mano solo
confunde. Se enciende con `--cadencia`, y eso es lo que va a pasar el día que exista
el paso que publica solo.

Con el flag puesto, cada tanda deja escrito **a qué hora sale cada pieza**, en
`_lote.json` y en el `.json` de cada una.

```
apto=True  sale=13:47  Pergamino   Adolescente herido tras chocar con un auto...
apto=False sale=—      9 de Julio  (no se publica: no ocupa lugar en la cola)
apto=True  sale=13:52  9 de Julio  Prisión preventiva para el concejal...
apto=True  sale=13:57  Alberti     Cayó un hombre buscado por homicidio...
```

Las piezas con objeciones **no reciben horario**. Si se les diera uno igual, el
publicador tendría que acordarse de saltearlas, y eso es justo lo que se olvida.

El intervalo vive en una sola constante, `MINUTOS_ENTRE_POSTEOS` en
`reels/flujo.py`. La galería muestra el horario en el badge de cada tarjeta.

> **Para el día que se construya el posteo, dos cosas que hay que resolver ahí:**
>
> 1. **El job no puede simplemente dormir.** Cinco piezas a 5 minutos son 20
>    minutos de espera, y el workflow tiene `timeout-minutes: 20` — lo mataría
>    justo antes de la última. O se sube ese tope, o el que publica lee
>    `publicar_en` y sale a postear lo que esté vencido, en corridas separadas.
> 2. **El tope de TikTok manda igual.** Son 5 borradores sin publicar cada 24 h;
>    con 3 pasadas por día eso es 1 o 2 piezas por pasada, no 5. La cadencia de 5
>    minutos recién se nota el día que haya Direct Post y varias piezas seguidas.

---

## Criterio editorial (decidido por el editor)

- **Los nombres propios se publican**, zócalo incluido, incluso de acusados y
  víctimas. Se planteó el riesgo y se reafirmó: es criterio del editor.
- **Excepción: menores de 18**, ni víctimas ni acusados, aunque el medio de origen
  los nombre. La edad y el parentesco sí van.
- **No hay revisión humana previa a publicar.** Por eso `apto_para_publicar` no
  mira solo quién escribió el guion sino también que los campos tengan contenido:
  una pieza salió con la bajada en blanco y el sistema la dio por lista.

---

## Trampas que ya costaron una corrida y no hay que repetir

- **Probar en esta máquina no prueba nada.** `reels/flujo.py` no leía el `.env`, y
  `requirements.txt` no declaraba `pillow` ni `imageio-ffmpeg` — las dos cosas
  andaban acá porque estaban en el venv de siempre. En la nube, dos pasadas
  enteras trajeron las noticias y armaron 0 reels. Verificar con
  `tools\verificar_requirements.py`, o mejor, en un venv nuevo con solo el archivo.
- **Un título de obra puede ser un titular policial.** «Infancias Robadas» disparó
  "robadas" y entró como policial. Los verbos de presentación ("fue presentado en",
  "presentaron la obra") están entre los apagadores FUERTES, que se aplican aunque
  haya una palabra policial en el título. «Casa de la Cultura» no: un robo *en* la
  Casa de la Cultura sí es policial.
- **WordPress sirve el feed general cuando le pedís una categoría que no existe.**
  Responde 200, trae notas de verdad, y queda anotado como "sección de policiales"
  un feed con golf adentro. `descubrir_seccion_policial` compara toda sección
  candidata contra el feed general y descarta la que lo repite.
- **La consola de Windows es cp1252.** Imprimir un `⚠` tumbaba la corrida entera:
  el sistema de avisos se rompía justo cuando había algo para avisar.

---

## Antes de dar una tanda por buena

1. Abrir `galeria.html` y mirar las placas, no solo los títulos.
2. Que ninguna tenga media pantalla vacía.
3. Que la volanta y el titular no se contradigan en la localidad.
4. Mirar las fotos: son las que puso el medio de origen. El 22/09 una era una
   captura de Facebook con posteos de terceros a la vista.
5. Leer la descripción del posteo entera, que es lo que se copia a TikTok.
