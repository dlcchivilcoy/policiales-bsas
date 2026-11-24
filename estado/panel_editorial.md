# Panel editorial — Diario y Radio
Actualizado: 24/11/2026 00:18 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-24)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 35 | 36 | 36 | 0 | 33 | 0 |
| Nacionales | 13 | 349 | 0 | 0 | 0 | 39 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 48 piezas · mediana vistas 289.5 · mediana likes 1

- **Por categoría:** policiales: 35, vistas 279, likes 1 · virales: 13, vistas 531, likes 1
- **Por franja:** madrugada (0-6): 14, vistas 529.5, likes 1.5 · mañana (6-12): 8, vistas 594, likes 2 · noche (18-24): 26, vistas 235, likes 0
- **Por día:** domingo: 6, vistas 236.5, likes 1 · jueves: 9, vistas 531, likes 1 · lunes: 2, vistas 483, likes 2.5 ⚠️muestra chica · martes: 7, vistas 36, likes 0 · miércoles: 6, vistas 182, likes 0.5 · sábado: 8, vistas 534.5, likes 1 · viernes: 10, vistas 455, likes 2
- **Por distancia:** 50 a 100 km: 29, vistas 300, likes 1 · Chivilcoy: 1, vistas 173, likes 1 ⚠️muestra chica · hasta 50 km: 5, vistas 86, likes 0

### Instagram — 32 piezas · mediana vistas s/d · mediana likes 5.5

- **Por categoría:** policiales: 32, likes 5.5
- **Por franja:** madrugada (0-6): 9, likes 4 · noche (18-24): 23, likes 6
- **Por día:** domingo: 3, likes 1 ⚠️muestra chica · jueves: 6, likes 6.5 · lunes: 1, likes 12 ⚠️muestra chica · martes: 6, likes 7.5 · miércoles: 4, likes 4.5 ⚠️muestra chica · sábado: 6, likes 11.5 · viernes: 6, likes 4.5
- **Por distancia:** 50 a 100 km: 27, likes 6 · hasta 50 km: 5, likes 5

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 224 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 6

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
