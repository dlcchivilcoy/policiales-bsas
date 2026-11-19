# Panel editorial — Diario y Radio
Actualizado: 19/11/2026 00:18 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-19)

_Todavía no hay pasadas registradas hoy._

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 23 | 24 | 24 | 0 | 23 | 0 |
| Nacionales | 15 | 346 | 0 | 0 | 0 | 35 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 40 piezas · mediana vistas 160 · mediana likes 0

- **Por categoría:** policiales: 27, vistas 126, likes 0 · virales: 13, vistas 192, likes 1
- **Por franja:** madrugada (0-6): 13, vistas 192, likes 1 · noche (18-24): 27, vistas 126, likes 0
- **Por día:** domingo: 5, vistas 487, likes 0 · jueves: 10, vistas 39.5, likes 0 · lunes: 5, vistas 679, likes 2 · martes: 7, vistas 36, likes 0 · sábado: 4, vistas 343.5, likes 0 ⚠️muestra chica · viernes: 9, vistas 23, likes 0
- **Por distancia:** 50 a 100 km: 19, vistas 126, likes 0 · Chivilcoy: 1, vistas 899, likes 2 ⚠️muestra chica · hasta 50 km: 7, vistas 43, likes 0

### Instagram — 26 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** policiales: 26, likes 5
- **Por franja:** noche (18-24): 26, likes 5
- **Por día:** domingo: 2, likes 4.5 ⚠️muestra chica · jueves: 6, likes 3 · lunes: 6, likes 5.5 · martes: 6, likes 7.5 · sábado: 2, likes 5.5 ⚠️muestra chica · viernes: 4, likes 7 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 20, likes 4 · hasta 50 km: 6, likes 11.5

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 189 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 19

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
