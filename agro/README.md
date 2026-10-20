# Agro: @diarioyradioagro

Vertical de noticias del campo y AgTech. **Publica sola desde el 14/10/2026** (workflow
`.github/workflows/agro.yml`, variable del repo `AGRO_PUBLICAR=1`; en 0 sigue armando y simula).

## Qué sale cada día (desde el 20/10/2026)

6 corridas por día (7, 10, 13, 16, 18 y 21 h). Cada una publica **5 reels, uno cada 20 minutos, cada uno
de un sitio distinto**: antes de cada reel vuelve a leer todas las fuentes y elige la mejor noticia de un
sitio que todavía no salió en esa corrida (las de los sitios ya usados esperan a la corrida siguiente).
= **30 reels por día** + 3 tandas de historias. Sin carruseles (se vuelven con `AGRO_AGENDA`).
La corrida espera dentro de la máquina el horario de cada reel (`agro/agenda.py`, `agro/pasada.py` →
`correr_corrida`; variables del repo `AGRO_POR_CORRIDA` (5), `AGRO_INTERVALO_MIN` (20), `AGRO_CORRIDAS`,
`AGRO_AGENDA` (pisa todo), `AGRO_UN_SITIO_POR_CORRIDA=0` apaga lo del sitio distinto):

| Corrida | Reels | Además |
|---|---|---|
| 07 | 07:00 · 07:20 · 07:40 · 08:00 · 08:20 | 07:00 historias «El campo hoy» |
| 10 | 10:00 · 10:20 · 10:40 · 11:00 · 11:20 | |
| 13 | 13:00 · 13:20 · 13:40 · 14:00 · 14:20 | 14:00 historias: mapa de lluvias, Chicago, la novedad |
| 16 | 16:00 · 16:20 · 16:40 · 17:00 · 17:20 | |
| 18 | 18:00 · 18:20 · 18:40 · 19:00 · 19:20 | 19:00 historias «Así cerró el mercado» |
| 21 | 21:00 · 21:20 · 21:40 · 22:00 · 22:20 | |

Cada reel: IG, FB (9:16 con bandas) y web; el **Short de YouTube, solo el primero de cada corrida** (el
cupo de la API lo comparten policiales y nacionales). Entre dos reels hay siempre 20 minutos: si uno
salió tarde, los siguientes también se corren. Puntaje mínimo 60 (`AGRO_SCORE_MIN`), hasta 36 por día
(`AGRO_MAX_DIA`).

Hasta el 19/10/2026 eran 1 reel + 1 carrusel por corrida (una hora entre los dos).

Sábados y domingos (sin mercados) las historias son clima, mapa, «Los números de la semana» y el resumen.
Una alerta del SMN que toca la zona va primera en la tanda siguiente. Una noticia URGENTE (alerta,
sanidad, norma) pasa primera en la selección.

- **Reel** (`agro/reel.py`, `agro/diseno.py`): 4:5 estilo policiales (imagen arriba, línea naranja,
  bloque blanco o grafito alternado con la marca agro), 22 s: titular → qué pasó → datos → por qué
  importa → cierre.
- **Miniatura** (`agro/portada.py`): imagen + texto SEO corto que arranca con la palabra clave
  («Soja: arranca la siembra con 2% más de área», la clave en naranja), en letra grande. Es la portada
  del reel en Instagram (`cover_url`), la miniatura del Short y de Facebook, el primer cuadro del video y
  la tapa del carrusel. El texto lo escribe la IA en el campo `portada` del guion.
- **Imagen** (`agro/imagen.py`): foto de fuente oficial con crédito; foto de otro medio RECREADA con IA
  (Cloudflare FLUX.2 klein: misma escena, otro encuadre y otra luz, sin letras; la original nunca se
  publica); si no, escena con IA, escena segura o el banco. Video: solo el de fuentes oficiales.
- **Carrusel** (`agro/carrusel.py`): tapa + 3 a 5 diapositivas (una idea cada una) + cierre. Se saca
  la diapositiva que trae una cifra que no está en el material.
- **Historias** (`agro/historias.py`, `agro/mercado.py`): sin IA. Cada placa dice fecha, fuente,
  mercado, moneda y unidad; si el dato no es de hoy, «Último dato disponible».

| Dato | Fuente |
|---|---|
| Granos | Cámara Arbitral de Cereales de Rosario (pizarra) |
| Dólar | BCRA (mayorista Com. A 3500, API) y Banco Nación (billete y divisa) |
| Chicago | CBOT/CME, contrato más cercano (vía Yahoo Finance), convertido a US$/t |
| Clima | SMN: pronóstico por estación (datos abiertos) y alertas CAP |

Probar sin publicar: `venv\Scripts\python.exe -m agro.pasada --tipo reel|carrusel|historias [--bloque cierre]`
→ `salida_agro/<fecha>/informe.html`. Tests: `venv\Scripts\python.exe tools	est_agro.py`.

## Costos (19/10/2026)

**US$ 0 por mes en servicios.** Todo corre en planes gratis:

| Pieza | Uso por día | Límite gratis |
|---|---|---|
| GitHub Actions (repo público) | 6 corridas, ~90 min c/u (casi todo espera) | sin tope para repos públicos |
| Gemini (clave gratis) | ~100-140 llamadas (puntaje, textos, carrusel, control de letras) | cupo gratis de la clave |
| Cloudflare Workers AI | ~1.600-3.200 neuronas (recreación ~130 c/u) | 10.000 por día, compartido con el Archivo |
| YouTube Data API | 6 Shorts (~9.800 unidades) | 10.000 por día, compartido con policiales y nacionales: sin cupo, el reel sale igual en las otras redes |
| Instagram | 40 publicaciones (30 reels, 10 historias) | 100 cada 24 h (cuenta propia, no la del diario) |
| Datos (CAC, BCRA, BNA, SMN, Yahoo) | ~10 pedidos por tanda | públicos |

Las historias no usan IA. Si Gemini o Cloudflare se quedan sin cupo, la pieza sale igual con el banco
de imágenes o el guion del reel; nunca se pasa a un servicio pago.

| Red | Cuenta | Antes |
|---|---|---|
| Instagram | @diarioyradioagro | @radiodelcentro |
| Facebook | Diario y Radio Agro (@diarioyradioagro) | facebook.com/delcentro919 |
| YouTube | canal Radio del Centro (Shorts), el mismo token que ya usa policiales | — |

## Marca

En `agro/marca/` están:

- `logo_original.png`: el logo sobre fondo grafito.
- `perfil_1080.png`: la foto de perfil de IG y FB. El dibujo entra entero en el círculo.
- `portada_facebook_1640x624.png`: la portada de la página. El texto va centrado para que
  se vea en el celular.

Se regeneran con `venv\Scripts\python.exe tools\marca_agro.py`.

## Pasos en Meta (a mano, una sola vez)

1. **Página delcentro919** (Configuración → Información de la página):
   - Nombre: «Diario y Radio Agro».
   - Usuario: `diarioyradioagro`.
   - Foto: `perfil_1080.png`.
   - Portada: `portada_facebook_1640x624.png`.

   Meta revisa el cambio de nombre (puede tardar hasta 3 días). **Hacerlo una sola vez.**
2. **Instagram @radiodelcentro**:
   - Usuario: `diarioyradioagro`.
   - Nombre y foto nuevos.
   - Bio.
   - Tiene que ser cuenta **profesional** (empresa o creador).
3. **Vincular** el IG a la página, desde Configuración de la página → Cuentas vinculadas → Instagram.
4. **business.facebook.com**, en el negocio «Diario La Campaña»:
   - Cuentas → Páginas → Agregar → la página agro.
   - Cuentas de Instagram → Agregar → @diarioyradioagro.
   - Tu usuario tiene que quedar con acceso total.
5. **Token**:
   1. En developers.facebook.com/tools/explorer, elegir la app **diario**.
   2. Agregar estos permisos: `pages_show_list`, `pages_read_engagement`,
      `pages_manage_posts`, `instagram_basic`, `instagram_content_publish` y
      `business_management`.
   3. «Generate Access Token».
   4. ⚠️ En la ventana de páginas e Instagram, dejar tildadas **las del diario Y las agro**.
      Si se destilda la del diario, se le puede cortar el token al diario.
   5. Copiar ese token y abrirlo en el Access Token Debugger
      (developers.facebook.com/tools/debug/accesstoken). Tocar «Extend Access Token» y
      copiar el token largo.
   6. Volver al Explorer, pegar el token largo y consultar
      `me/accounts?fields=name,id,access_token,instagram_business_account`.
   7. Copiar el `access_token` **de la página agro**. Sale de un token largo, así que no vence.
   8. Pegarlo en un archivo suelto, por ejemplo `agro.txt`, con esta línea:
      `AGRO_FACEBOOK_PAGE_ACCESS_TOKEN=...`

## Cargar y verificar (no imprime ningún token)

```
venv\Scripts\python.exe tools\cargar_credenciales.py agro.txt --borrar-origen
venv\Scripts\python.exe tools\verificar_cuenta_agro.py --guardar-ids
```

El verificador **solo lee**. Revisa:

- el token: que sea válido, de la app «diario», de tipo PAGE y con los 6 permisos;
- hasta cuándo dura el acceso a los datos;
- cuál es la página de verdad y cuál es su Instagram vinculado;
- que Instagram deje publicar por API;
- la **salvaguarda**: si algo es @diarioyradio, falla.

Hasta que Meta apruebe el cambio de usuario, sale como aviso (no como falla).

Para probar la salvaguarda: `tools\verificar_cuenta_agro.py --principal`, que revisa la
cuenta del diario y **tiene que fallar**. Tests sin red: `tools\test_cuenta_agro.py`.
