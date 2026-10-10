# Reels de prueba del Archivo Literario + pregunta del día

Pedido del editor (10/10/2026): **2 reels de prueba por día en Instagram**, con la estética, logos e info del
diario. Los reels de prueba los ve primero gente que **no** sigue la cuenta y, si funcionan, Instagram los
pasa solo al feed (graduación automática, `SS_PERFORMANCE`).

| Hora (ARG) | Qué sale | De dónde |
|---|---|---|
| **13:30** | Efeméride de HOY («UN DÍA COMO HOY · 22 DE OCTUBRE»); si hoy no hay, un personaje o una curiosidad | Archivo Literario Municipal (archivoliterariochivilcoy.com) |
| **20:30** | **Pregunta del día** («¿Cuál es el mejor barrio para vivir en Chivilcoy?») | Gemini + imagen de Cloudflare Workers AI |

Los horarios salen de los `online_followers` de @diarioyradio (picos 12-13 y 19-22) y quedan lejos de las
pasadas de policiales (12:05 y 21:05). Decisiones del editor: imagen con **Cloudflare gratis**, **sin nombrar
la fuente**, caption con **exactamente 5 hashtags** (`#chivilcoy #diariolacampaña #radiodelcentro` + 2 del tema).

## Cómo funciona

```
archivo/indice.json ──► elegir.py ──► guion.py (Gemini) ──► foto ──► motor del bot ──► Instagram (reel de PRUEBA)
preguntas_banco.txt ──► preguntas.py (Gemini) ──► imagen.py (Cloudflare | placa) ─┘
```

- **`archivo/fuente.py`**: lee el WordPress del Archivo por su API pública. `archivo/indice.json` (va en el
  repo) tiene los ~1.300 hechos fechados del sitio (338 días del año con alguno), los personajes y las
  curiosidades. En cada pasada se suma lo publicado después de armarlo (1 pedido). Para rearmarlo entero:
  `venv\Scripts\python.exe -m archivo.fuente --indice`. Ver las efemérides de un día: `--dia 22/10`.
  Lee los formatos del sitio: «1 de febrero de 1884: …», «11 y 12 de febrero…», «El domingo 22 de octubre de
  1854, …», «Febrero 1 de 1868 – …», «Los 63 años, el 15 de junio de 1961, …». Sin año no sirve (el «37
  aniversario» está contado desde el año en que se escribió). Crímenes, tragedias, accidentes y muertes de
  chicos quedan afuera.
- **`archivo/elegir.py`**: efeméride de hoy → personaje → curiosidad. Nada se repite en 365 días (ni el mismo
  personaje en 60). La **foto** es la destacada de un post **dedicado** a ese hecho: el post tiene que nombrar
  la fecha exacta y no ser una recopilación (la foto de una lista mensual es de otro tema). Le muestra a la IA
  hasta 5 candidatas, las que tienen foto primero.
- **`archivo/guion.py`**: la IA elige la candidata y escribe volanta/titular/bajada y el posteo, con palabras
  propias (el control de copia de policiales pide otra versión si calca) y el aniversario calculado por el
  código. Si la IA escribe sobre el año de otra candidata, manda el año del texto; si no aparece ninguno, va
  sin foto (placa).
- **`archivo/preguntas.py`**: el banco de 1.000 preguntas del starter son 20 categorías × 10 temas; se usa
  como temario. Una categoría no vuelve en 7 días; dentro de ella, el primer tema que no salió. La IA escribe
  una pregunta concreta y local (sin comercios ni personas, sin política) que no repita las últimas 120.
- **`archivo/imagen.py`**: Cloudflare FLUX.1 schnell (`CF_ACCOUNT_ID`, `CF_API_TOKEN`). Sin clave o si falla,
  la placa propia. Si el motor toma la imagen por un afiche (retratos viejos con fondo liso), la agranda y le
  suma grano: a un afiche el motor no le pone texto.
- **`archivo/pasada.py`**: una por tipo por día (`estado/archivo.json`); sin `--publicar`, simula. Hasta 3
  intentos fallidos por día. «Sin confirmar» cuenta como hecho. Respeta el cupo de Instagram (100/24 h con la
  reserva del bot).

## Correr

```bash
venv\Scripts\python.exe -m archivo.pasada --tipo efemeride             # simula
venv\Scripts\python.exe -m archivo.pasada --tipo pregunta --publicar
venv\Scripts\python.exe tools\test_archivo.py
```

En la nube: `.github/workflows/archivo.yml`. Lo disparan 2 jobs de cron-job.org (13:30 y 20:30) y el
`schedule:` de GitHub es el respaldo (13:50 y 20:50), que no repite lo que ya salió.

**Interruptores** (variables del repo): `PUBLICAR_REDES=1` y `ARCHIVO` distinto de `0` → publica.
`ARCHIVO=0` apaga solo esto (sigue armando y simula).

## Cloudflare (lo hace el editor)

1. Cuenta gratis en <https://dash.cloudflare.com/sign-up>.
2. Workers AI → «Use REST API» → «Create a Workers AI API Token». Copiar el token y el Account ID.
3. Pegarlos en un .txt (`CF_ACCOUNT_ID=…` y `CF_API_TOKEN=…`): se cargan al .env con
   `tools/cargar_credenciales.py` y como secrets del repo `CF_ACCOUNT_ID` y `CF_API_TOKEN`.

Hasta entonces, la pregunta sale con la placa propia.
