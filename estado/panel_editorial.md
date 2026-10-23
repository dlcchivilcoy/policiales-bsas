# Panel editorial — Diario y Radio
Actualizado: 23/10/2026 03:06 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-23)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 29 | 32 | 15 | 7 | 17 |
| Nacionales | 103 | 105 | 41 | 0 | 56 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 138 piezas · mediana vistas 18 · mediana likes 0

- **Por categoría:** cine_series: 4, vistas 50.5, likes 0 ⚠️muestra chica · deportes: 10, vistas 33.5, likes 0 · espectaculos: 9, vistas 49, likes 0 · general: 54, vistas 7.5, likes 0 · internacionales: 15, vistas 28, likes 0 · policiales: 41, vistas 44, likes 0 · tecnologia_ia: 2, vistas 5, likes 0 ⚠️muestra chica · virales: 3, vistas 12, likes 0 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 12, vistas 56.5, likes 0 · mañana (6-12): 25, vistas 21, likes 0 · noche (18-24): 65, vistas 37, likes 0 · tarde (12-18): 36, vistas 8.5, likes 0
- **Por día:** domingo: 37, vistas 13, likes 0 · lunes: 36, vistas 17.5, likes 0 · martes: 10, vistas 110, likes 0 · miércoles: 13, vistas 49, likes 0 · sábado: 20, vistas 14.5, likes 0 · viernes: 22, vistas 16.5, likes 0
- **Por distancia:** 50 a 100 km: 18, vistas 49.5, likes 0 · hasta 50 km: 6, vistas 50, likes 0

### Facebook — 24 piezas · mediana vistas 474.5 · mediana likes 1

- **Por categoría:** policiales: 24, vistas 474.5, likes 1
- **Por franja:** madrugada (0-6): 1, vistas 722, likes 1 ⚠️muestra chica · mañana (6-12): 3, vistas 472, likes 2 ⚠️muestra chica · noche (18-24): 10, vistas 485.5, likes 1.5 · tarde (12-18): 10, vistas 439.5, likes 1
- **Por día:** domingo: 4, vistas 577.5, likes 0.5 ⚠️muestra chica · lunes: 5, vistas 366, likes 1 · martes: 3, vistas 350, likes 1 ⚠️muestra chica · miércoles: 2, vistas 501, likes 2 ⚠️muestra chica · sábado: 6, vistas 596, likes 1.5 · viernes: 4, vistas 525.5, likes 2.5 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 11, vistas 477, likes 1 · hasta 50 km: 4, vistas 490, likes 1.5 ⚠️muestra chica

### Instagram — 69 piezas · mediana vistas s/d · mediana likes 6

- **Por categoría:** cine_series: 4, likes 5 ⚠️muestra chica · deportes: 7, likes 6 · espectaculos: 4, likes 6 ⚠️muestra chica · general: 15, likes 2 · internacionales: 8, likes 13 · policiales: 30, likes 7 · tecnologia_ia: 1, likes 3 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 12, likes 8 · mañana (6-12): 5, likes 7 · noche (18-24): 41, likes 5 · tarde (12-18): 11, likes 6
- **Por día:** domingo: 23, likes 6 · lunes: 15, likes 5 · martes: 6, likes 11 · miércoles: 8, likes 2.5 · sábado: 7, likes 5 · viernes: 10, likes 8.5
- **Por distancia:** 50 a 100 km: 11, likes 7 · hasta 50 km: 3, likes 7 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 128 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 4

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
