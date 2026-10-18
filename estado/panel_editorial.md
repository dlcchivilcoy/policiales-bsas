# Panel editorial — Diario y Radio
Actualizado: 18/10/2026 11:50 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-18)

### 09:05 — 3 de 3 hechos policiales
Notas policiales leídas: 13 · fuera del radio: 5 · ubicación pendiente: 0 · repetidas: 0 · armadas: 5

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Detuvieron al papá de la abogada acusada de racismo en Brasil | 9 de Julio (99.4 km) | ✅ | ✅ | ✅ | ✅ |
| Un motociclista fue hospitalizado tras chocar contra una camioneta est | Chacabuco (50.1 km) | — ese hecho ya está en el canal de YouTube («Le chocaron la ca | ✅ | — intercalado: no salió otra temática en Facebook antes de la | — intercalado: no salió otra temática en Instagram antes de la |
| Demoraron a un joven de 18 años tras disturbios en el barrio de los Bo | Chacabuco (50.1 km) | ✅ | ✅ | — no está entre las 2 más virales de la pasada (esta: viral 6/ | — intercalado: no salió otra temática en Instagram antes de la |

**No salieron en esta pasada:**
- Falleció Martín Rubén Montoya a los 42 años en Chacabuco — no apta: No es del temario de policiales (según la IA): Es un aviso fúnebre o necrológica, que pertenece a la categoría de servicios y necrológicas, excluida del temario policial.
- Un joven de 21 años fue internado tras una pelea cerca del paso a nivel de la ca — no entra en la pasada: como mucho 3 hechos policiales por pasada, un reel cada 30 minutos (3 lugares libres)

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×2 · San Carlos de Bolívar (178.3 km) ×1 · Pehuajó (198.5 km) ×1 · Pergamino (122.9 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 79 | 81 | 43 | 38 | 78 |
| Nacionales | 81 | 81 | 54 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 65 piezas · mediana vistas 18 · mediana likes 0

- **Por categoría:** general: 27, vistas 9, likes 0 · policiales: 38, vistas 43.5, likes 0
- **Por franja:** madrugada (0-6): 3, vistas 295, likes 2 ⚠️muestra chica · mañana (6-12): 15, vistas 10, likes 0 · noche (18-24): 23, vistas 28, likes 0 · tarde (12-18): 24, vistas 13, likes 0
- **Por día:** jueves: 36, vistas 18, likes 0 · miércoles: 1, vistas 262, likes 0 ⚠️muestra chica · sábado: 6, vistas 18, likes 0 · viernes: 22, vistas 16.5, likes 0

### Facebook — 15 piezas · mediana vistas 465 · mediana likes 1

- **Por categoría:** policiales: 15, vistas 465, likes 1
- **Por franja:** madrugada (0-6): 2, vistas 593.5, likes 1 ⚠️muestra chica · mañana (6-12): 4, vistas 448.5, likes 1.5 ⚠️muestra chica · noche (18-24): 4, vistas 443, likes 1 ⚠️muestra chica · tarde (12-18): 5, vistas 388, likes 1
- **Por día:** jueves: 9, vistas 425, likes 1 · miércoles: 1, vistas 286, likes 1 ⚠️muestra chica · sábado: 1, vistas 722, likes 1 ⚠️muestra chica · viernes: 4, vistas 525.5, likes 2.5 ⚠️muestra chica

### Instagram — 36 piezas · mediana vistas s/d · mediana likes 4.5

- **Por categoría:** policiales: 36, likes 4.5
- **Por franja:** madrugada (0-6): 3, likes 13 ⚠️muestra chica · mañana (6-12): 7, likes 5 · noche (18-24): 15, likes 4 · tarde (12-18): 11, likes 4
- **Por día:** jueves: 22, likes 2 · miércoles: 1, likes 4 ⚠️muestra chica · sábado: 3, likes 12 ⚠️muestra chica · viernes: 10, likes 8.5

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

anterior al control: 174 · procesado: 47 · subido, se verifica en la pasada siguiente: 2

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_VARIEDAD_POR_PASADA`, `NAC_CUPO_<CATEGORIA>` — categorías nuevas.
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
