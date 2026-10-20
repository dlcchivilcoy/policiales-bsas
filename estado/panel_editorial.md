# Panel editorial — Diario y Radio
Actualizado: 20/10/2026 04:41 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-20)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 57 | 60 | 30 | 26 | 49 |
| Nacionales | 126 | 126 | 56 | 0 | 41 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 124 piezas · mediana vistas 16.5 · mediana likes 0

- **Por categoría:** cine_series: 3, vistas 29, likes 0 ⚠️muestra chica · deportes: 8, vistas 58, likes 0 · espectaculos: 7, vistas 52, likes 0 · general: 49, vistas 7, likes 0 · internacionales: 7, vistas 135, likes 0 · policiales: 49, vistas 36, likes 0 · tecnologia_ia: 1, vistas 3, likes 0 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 11, vistas 52, likes 0 · mañana (6-12): 20, vistas 14.5, likes 0 · noche (18-24): 48, vistas 19, likes 0 · tarde (12-18): 45, vistas 9, likes 0
- **Por día:** domingo: 37, vistas 13, likes 0 · jueves: 36, vistas 18, likes 0 · lunes: 8, vistas 35.5, likes 0 · miércoles: 1, vistas 262, likes 0 ⚠️muestra chica · sábado: 20, vistas 14.5, likes 0 · viernes: 22, vistas 16.5, likes 0
- **Por distancia:** 50 a 100 km: 6, vistas 33, likes 0 · hasta 50 km: 1, vistas 5, likes 0 ⚠️muestra chica

### Facebook — 24 piezas · mediana vistas 471 · mediana likes 1

- **Por categoría:** policiales: 24, vistas 471, likes 1
- **Por franja:** madrugada (0-6): 2, vistas 593.5, likes 1 ⚠️muestra chica · mañana (6-12): 5, vistas 425, likes 1 · noche (18-24): 7, vistas 592, likes 1 · tarde (12-18): 10, vistas 439.5, likes 1
- **Por día:** domingo: 4, vistas 577.5, likes 0.5 ⚠️muestra chica · jueves: 9, vistas 425, likes 1 · miércoles: 1, vistas 286, likes 1 ⚠️muestra chica · sábado: 6, vistas 596, likes 1.5 · viernes: 4, vistas 525.5, likes 2.5 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 4, vistas 588.5, likes 0.5 ⚠️muestra chica · hasta 50 km: 1, vistas 592, likes 2 ⚠️muestra chica

### Instagram — 73 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** cine_series: 4, likes 5 ⚠️muestra chica · deportes: 7, likes 6 · espectaculos: 4, likes 6 ⚠️muestra chica · general: 6, likes 2 · internacionales: 6, likes 20 · policiales: 45, likes 5 · tecnologia_ia: 1, likes 3 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 13, likes 9 · mañana (6-12): 8, likes 6 · noche (18-24): 33, likes 4 · tarde (12-18): 19, likes 4
- **Por día:** domingo: 23, likes 6 · jueves: 22, likes 2 · lunes: 10, likes 6 · miércoles: 1, likes 4 ⚠️muestra chica · sábado: 7, likes 5 · viernes: 10, likes 8.5
- **Por distancia:** 50 a 100 km: 5, likes 7 · hasta 50 km: 1, likes 7 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

anterior al control: 140 · procesado: 120 · subido, se verifica en la pasada siguiente: 7

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
