# Panel editorial — Diario y Radio
Actualizado: 19/10/2026 04:41 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-19)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 68 | 69 | 36 | 32 | 66 |
| Nacionales | 105 | 105 | 56 | 0 | 24 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 79 piezas · mediana vistas 17 · mediana likes 0

- **Por categoría:** deportes: 1, vistas 18, likes 0 ⚠️muestra chica · general: 35, vistas 7, likes 0 · policiales: 43, vistas 39, likes 0
- **Por franja:** madrugada (0-6): 3, vistas 295, likes 2 ⚠️muestra chica · mañana (6-12): 15, vistas 10, likes 0 · noche (18-24): 27, vistas 27, likes 0 · tarde (12-18): 34, vistas 8.5, likes 0
- **Por día:** jueves: 36, vistas 18, likes 0 · miércoles: 1, vistas 262, likes 0 ⚠️muestra chica · sábado: 20, vistas 14.5, likes 0 · viernes: 22, vistas 16.5, likes 0
- **Por distancia:** 50 a 100 km: 1, vistas 243, likes 0 ⚠️muestra chica

### Facebook — 20 piezas · mediana vistas 467.5 · mediana likes 1

- **Por categoría:** policiales: 20, vistas 467.5, likes 1
- **Por franja:** madrugada (0-6): 2, vistas 593.5, likes 1 ⚠️muestra chica · mañana (6-12): 4, vistas 448.5, likes 1.5 ⚠️muestra chica · noche (18-24): 5, vistas 512, likes 1 · tarde (12-18): 9, vistas 409, likes 1
- **Por día:** jueves: 9, vistas 425, likes 1 · miércoles: 1, vistas 286, likes 1 ⚠️muestra chica · sábado: 6, vistas 596, likes 1.5 · viernes: 4, vistas 525.5, likes 2.5 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 1, vistas 752, likes 3 ⚠️muestra chica

### Instagram — 40 piezas · mediana vistas s/d · mediana likes 4.5

- **Por categoría:** policiales: 40, likes 4.5
- **Por franja:** madrugada (0-6): 3, likes 13 ⚠️muestra chica · mañana (6-12): 7, likes 5 · noche (18-24): 16, likes 4 · tarde (12-18): 14, likes 3
- **Por día:** jueves: 22, likes 2 · miércoles: 1, likes 4 ⚠️muestra chica · sábado: 7, likes 5 · viernes: 10, likes 8.5
- **Por distancia:** 50 a 100 km: 1, likes 41 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

anterior al control: 159 · procesado: 75 · subido, se verifica en la pasada siguiente: 11

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
