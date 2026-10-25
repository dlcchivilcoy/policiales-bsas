# Panel editorial — Diario y Radio
Actualizado: 24/10/2026 23:36 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-24)

### 18:30 — 0 de 5 hechos policiales
Notas policiales leídas: 37 · fuera del radio: 10 · ubicación pendiente: 0 · repetidas: 1 · armadas: 7

**Fuera del radio de 100 km:**
- Trenque Lauquen (273.4 km) ×3 · Pergamino (122.9 km) ×3 · Las Flores (149.6 km) ×2 · Cañuelas (115.9 km) ×1 · Pehuajó (198.5 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 30 | 31 | 12 | 8 | 20 |
| Nacionales | 89 | 91 | 31 | 0 | 66 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 119 piezas · mediana vistas 29 · mediana likes 0

- **Por categoría:** cine_series: 4, vistas 50.5, likes 0 ⚠️muestra chica · deportes: 9, vistas 49, likes 0 · espectaculos: 9, vistas 49, likes 0 · general: 43, vistas 10, likes 0 · internacionales: 15, vistas 28, likes 0 · policiales: 34, vistas 82.5, likes 0 · tecnologia_ia: 2, vistas 5, likes 0 ⚠️muestra chica · virales: 3, vistas 12, likes 0 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 10, vistas 48.5, likes 0 · mañana (6-12): 16, vistas 33, likes 0 · noche (18-24): 76, vistas 48, likes 0 · tarde (12-18): 17, vistas 11, likes 0
- **Por día:** domingo: 37, vistas 13, likes 0 · jueves: 10, vistas 86, likes 1 · lunes: 36, vistas 17.5, likes 0 · martes: 10, vistas 110, likes 0 · miércoles: 13, vistas 49, likes 0 · viernes: 13, vistas 148, likes 0
- **Por distancia:** 50 a 100 km: 27, vistas 83, likes 0 · hasta 50 km: 7, vistas 82, likes 0

### Facebook — 18 piezas · mediana vistas 432.5 · mediana likes 1

- **Por categoría:** policiales: 18, vistas 432.5, likes 1
- **Por franja:** mañana (6-12): 1, vistas 337, likes 0 ⚠️muestra chica · noche (18-24): 13, vistas 477, likes 1 · tarde (12-18): 4, vistas 464.5, likes 1 ⚠️muestra chica
- **Por día:** domingo: 4, vistas 577.5, likes 0.5 ⚠️muestra chica · jueves: 1, vistas 3511, likes 3 ⚠️muestra chica · lunes: 5, vistas 366, likes 1 · martes: 3, vistas 350, likes 1 ⚠️muestra chica · miércoles: 2, vistas 501, likes 2 ⚠️muestra chica · viernes: 3, vistas 293, likes 1 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 13, vistas 366, likes 1 · hasta 50 km: 5, vistas 592, likes 2

### Instagram — 62 piezas · mediana vistas s/d · mediana likes 6

- **Por categoría:** cine_series: 4, likes 5 ⚠️muestra chica · deportes: 7, likes 6 · espectaculos: 4, likes 6 ⚠️muestra chica · general: 17, likes 3 · internacionales: 8, likes 13 · policiales: 21, likes 7 · tecnologia_ia: 1, likes 3 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 10, likes 6 · mañana (6-12): 2, likes 3.5 ⚠️muestra chica · noche (18-24): 45, likes 6 · tarde (12-18): 5, likes 6
- **Por día:** domingo: 23, likes 6 · jueves: 5, likes 9 · lunes: 15, likes 5 · martes: 6, likes 11 · miércoles: 8, likes 2.5 · viernes: 5, likes 10
- **Por distancia:** 50 a 100 km: 17, likes 8 · hasta 50 km: 4, likes 7 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 131 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 12

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
