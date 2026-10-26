# Panel editorial — Diario y Radio
Actualizado: 25/10/2026 21:08 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-25)

### 18:30 — 0 de 5 hechos policiales
Notas policiales leídas: 41 · fuera del radio: 4 · ubicación pendiente: 0 · repetidas: 1 · armadas: 7

**Fuera del radio de 100 km:**
- Carlos Casares (146.5 km) ×1 · Cañuelas (115.9 km) ×1 · General Villegas (273.4 km) ×1 · Trenque Lauquen (273.4 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 31 | 32 | 11 | 7 | 19 |
| Nacionales | 65 | 109 | 23 | 0 | 51 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 96 piezas · mediana vistas 46 · mediana likes 0

- **Por categoría:** cine_series: 2, vistas 75.5, likes 0.5 ⚠️muestra chica · deportes: 5, vistas 49, likes 0 · espectaculos: 6, vistas 50.5, likes 0 · general: 32, vistas 37.5, likes 0 · internacionales: 12, vistas 27, likes 0 · policiales: 35, vistas 82, likes 0 · tecnologia_ia: 1, vistas 7, likes 0 ⚠️muestra chica · virales: 3, vistas 12, likes 0 ⚠️muestra chica
- **Por franja:** madrugada (0-6): 10, vistas 48.5, likes 0 · mañana (6-12): 11, vistas 28, likes 0 · noche (18-24): 69, vistas 57, likes 0 · tarde (12-18): 6, vistas 9.5, likes 0
- **Por día:** domingo: 9, vistas 165, likes 1 · jueves: 10, vistas 86, likes 1 · lunes: 36, vistas 17.5, likes 0 · martes: 10, vistas 110, likes 0 · miércoles: 13, vistas 49, likes 0 · sábado: 5, vistas 21, likes 0 · viernes: 13, vistas 148, likes 0
- **Por distancia:** 50 a 100 km: 28, vistas 76, likes 0 · hasta 50 km: 7, vistas 82, likes 0

### Facebook — 15 piezas · mediana vistas 388 · mediana likes 1

- **Por categoría:** policiales: 15, vistas 388, likes 1
- **Por franja:** noche (18-24): 12, vistas 432.5, likes 1 · tarde (12-18): 3, vistas 366, likes 1 ⚠️muestra chica
- **Por día:** domingo: 1, vistas 592, likes 2 ⚠️muestra chica · jueves: 1, vistas 3511, likes 3 ⚠️muestra chica · lunes: 5, vistas 366, likes 1 · martes: 3, vistas 350, likes 1 ⚠️muestra chica · miércoles: 2, vistas 501, likes 2 ⚠️muestra chica · viernes: 3, vistas 293, likes 1 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 10, vistas 332.5, likes 1 · hasta 50 km: 5, vistas 592, likes 2

### Instagram — 52 piezas · mediana vistas s/d · mediana likes 7

- **Por categoría:** cine_series: 2, likes 5 ⚠️muestra chica · deportes: 4, likes 11.5 ⚠️muestra chica · espectaculos: 3, likes 9 ⚠️muestra chica · general: 15, likes 3 · internacionales: 6, likes 20 · policiales: 22, likes 8.5
- **Por franja:** madrugada (0-6): 10, likes 6 · mañana (6-12): 1, likes 0 ⚠️muestra chica · noche (18-24): 41, likes 8
- **Por día:** domingo: 9, likes 11 · jueves: 5, likes 9 · lunes: 15, likes 5 · martes: 6, likes 11 · miércoles: 8, likes 2.5 · sábado: 4, likes 13 ⚠️muestra chica · viernes: 5, likes 10
- **Por distancia:** 50 a 100 km: 18, likes 9.5 · hasta 50 km: 4, likes 7 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 139 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 5

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
