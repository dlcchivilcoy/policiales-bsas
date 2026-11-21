# Panel editorial — Diario y Radio
Actualizado: 21/11/2026 00:18 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-21)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 29 | 30 | 30 | 0 | 30 | 0 |
| Nacionales | 13 | 352 | 0 | 0 | 0 | 44 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 38 piezas · mediana vistas 294.5 · mediana likes 1

- **Por categoría:** policiales: 29, vistas 310, likes 0 · virales: 9, vistas 220, likes 1
- **Por franja:** madrugada (0-6): 8, vistas 339.5, likes 1.5 · mañana (6-12): 5, vistas 531, likes 1 · noche (18-24): 25, vistas 279, likes 0
- **Por día:** domingo: 5, vistas 487, likes 0 · jueves: 9, vistas 531, likes 1 · lunes: 5, vistas 679, likes 2 · martes: 7, vistas 36, likes 0 · miércoles: 6, vistas 182, likes 0.5 · sábado: 4, vistas 343.5, likes 0 ⚠️muestra chica · viernes: 2, vistas 560, likes 4 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 23, vistas 279, likes 0 · Chivilcoy: 1, vistas 899, likes 2 ⚠️muestra chica · hasta 50 km: 5, vistas 678, likes 0

### Instagram — 28 piezas · mediana vistas s/d · mediana likes 6

- **Por categoría:** policiales: 28, likes 6
- **Por franja:** madrugada (0-6): 4, likes 8.5 ⚠️muestra chica · noche (18-24): 24, likes 6
- **Por día:** domingo: 2, likes 4.5 ⚠️muestra chica · jueves: 6, likes 6.5 · lunes: 6, likes 5.5 · martes: 6, likes 7.5 · miércoles: 4, likes 4.5 ⚠️muestra chica · sábado: 2, likes 5.5 ⚠️muestra chica · viernes: 2, likes 11 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 24, likes 5 · hasta 50 km: 4, likes 9 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 206 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 15

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
