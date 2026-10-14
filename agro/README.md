# Agro: @diarioyradioagro

Esta es la vertical de noticias del campo y AgTech. **Hoy NO publica nada.** Por ahora solo
se engancharon las cuentas a la API de Meta y se verificó que funcionen. Ningún código de
policiales lee las variables `AGRO_*`.

| Red | Cuenta | Antes |
|---|---|---|
| Instagram | @diarioyradioagro | @radiodelcentro |
| Facebook | Diario y Radio Agro (@diarioyradioagro) | facebook.com/delcentro919 |
| YouTube (más adelante) | canal Radio del Centro, el mismo token que ya usa policiales | — |

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
