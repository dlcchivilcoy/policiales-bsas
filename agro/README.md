# Agro: @diarioyradioagro

Vertical de noticias del campo y AgTech. **Publica sola desde el 14/10/2026** (workflow
`.github/workflows/agro.yml`, variable del repo `AGRO_PUBLICAR=1`; en 0 sigue armando y simula).

## Qué sale cada día (desde el 17/10/2026)

3 reels + 3 carruseles + 10 historias, en 3 corridas, una cosa por horario y una hora entre una y otra
(`agro/agenda.py`; se cambia sin tocar código con la variable del repo `AGRO_AGENDA`):

| Corrida | Horario | Qué | Dónde |
|---|---|---|---|
| 1 | 07:00 | Historias «El campo hoy»: clima de la zona, granos, dólar, lo que tenés que saber | IG + FB |
| 1 | 08:00 | Reel 4:5 de una noticia | IG, FB (9:16 con bandas), Short, web |
| 1 | 09:00 | Carrusel «deslizá e informate» (sábados: «Los números de la semana») | IG, FB (fotos + link), web |
| 2 | 12:00 | Reel | ídem |
| 2 | 13:00 | Carrusel | ídem |
| 2 | 14:00 | Historias: «Tu zona en el mapa» (lluvias), Chicago, la novedad del día | IG + FB |
| 3 | 19:00 | Historias «Así cerró el mercado»: pizarra de Rosario, dólar, Chicago | IG + FB |
| 3 | 20:00 | Reel | ídem |
| 3 | 21:00 | Carrusel | ídem |

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

## Costos (17/10/2026)

**US$ 0 por mes en servicios.** Todo corre en planes gratis:

| Pieza | Uso por día | Límite gratis |
|---|---|---|
| GitHub Actions (repo público) | 9 corridas, ~35 min | sin tope para repos públicos |
| Gemini (clave gratis) | ~60-80 llamadas (puntaje, textos, carrusel, control de letras) | cupo gratis de la clave |
| Cloudflare Workers AI | ~800-1.600 neuronas (recreación ~130 c/u) | 10.000 por día, compartido con el Archivo |
| YouTube Data API | 3 Shorts (~4.900 unidades) | 10.000 por día |
| Instagram | 16 publicaciones (3 reels, 3 carruseles, 10 historias) | 100 cada 24 h |
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
