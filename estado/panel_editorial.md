# Panel editorial — Diario y Radio
Actualizado: 28/11/2026 00:18 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-28)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 29 | 29 | 24 | 5 | 27 | 0 |
| Nacionales | 18 | 352 | 0 | 0 | 0 | 46 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 42 piezas · mediana vistas 184 · mediana likes 1

- **Por categoría:** policiales: 29, vistas 189, likes 1 · virales: 13, vistas 178, likes 2
- **Por franja:** madrugada (0-6): 19, vistas 178, likes 2 · noche (18-24): 23, vistas 266, likes 1
- **Por día:** domingo: 6, vistas 236.5, likes 1 · jueves: 8, vistas 387, likes 0.5 · lunes: 6, vistas 261.5, likes 0.5 · martes: 7, vistas 189, likes 1 · miércoles: 9, vistas 131, likes 1 · sábado: 6, vistas 321, likes 1
- **Por distancia:** 50 a 100 km: 26, vistas 227.5, likes 1 · Chivilcoy: 1, vistas 173, likes 1 ⚠️muestra chica · hasta 50 km: 2, vistas 247, likes 0.5 ⚠️muestra chica

### Instagram — 26 piezas · mediana vistas s/d · mediana likes 4.5

- **Por categoría:** policiales: 26, likes 4.5
- **Por franja:** madrugada (0-6): 6, likes 3 · noche (18-24): 20, likes 5
- **Por día:** domingo: 3, likes 1 ⚠️muestra chica · jueves: 4, likes 8.5 ⚠️muestra chica · lunes: 5, likes 12 · martes: 6, likes 2 · miércoles: 4, likes 6.5 ⚠️muestra chica · sábado: 4, likes 11.5 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 24, likes 5 · hasta 50 km: 2, likes 1 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 41 · subido, se verifica en la pasada siguiente: 10

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
