# Panel editorial — Diario y Radio
Actualizado: 16/11/2026 21:33 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-16)

### 18:30 — 6 de 6 hechos policiales
Notas policiales leídas: 58 · fuera del radio: 15 · ubicación pendiente: 0 · repetidas: 3 · armadas: 7

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Atraparon a un sospechoso de 45 años con pedido de captura activa | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |
| Motociclista herido tras chocar contra un camión de Absa en Bragado | Bragado (49.3 km) | ✅ | ✅ | ✅ | ✅ |
| Sufrió dos robos en una semana en su local de Junín y evalúa vender el | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |
| Detuvieron a un hombre de Chacabuco tras un robo en la calle 27 de Dic | Chacabuco (50.1 km) | — ese hecho ya está en el canal de YouTube («Detuvieron a un h | ✅ | ✅ | ✅ |
| Murió Jorge Limonta tras ser atropellado por una moto en San Andrés de | San Andrés de Giles (72.7 km) | ✅ | ✅ | ✅ | ✅ |
| Bragado bajo alerta amarilla por tormentas y posibles ráfagas intensas | Bragado (49.3 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Sin datos sobre el hecho — no apta: No es del temario de policiales (según la IA): El texto original está vacío y no contiene información sobre ningún hecho periodístico.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · Pergamino (122.9 km) ×3 · Las Flores (149.6 km) ×2 · San Carlos de Bolívar (178.3 km) ×1 · General Pinto (171.5 km) ×1 · Lincoln (137.8 km) ×1 · Pehuajó (198.5 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 24 | 26 | 26 | 0 | 25 | 3 |
| Nacionales | 20 | 335 | 0 | 0 | 0 | 18 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 42 piezas · mediana vistas 191 · mediana likes 0

- **Por categoría:** policiales: 22, vistas 51, likes 0 · virales: 20, vistas 232.5, likes 2
- **Por franja:** madrugada (0-6): 20, vistas 232.5, likes 2 · noche (18-24): 22, vistas 51, likes 0
- **Por día:** domingo: 5, vistas 487, likes 0 · jueves: 10, vistas 39.5, likes 0 · martes: 7, vistas 221, likes 3 · miércoles: 7, vistas 160, likes 0 · sábado: 4, vistas 343.5, likes 0 ⚠️muestra chica · viernes: 9, vistas 23, likes 0
- **Por distancia:** 50 a 100 km: 13, vistas 23, likes 0 · Chivilcoy: 1, vistas 899, likes 2 ⚠️muestra chica · hasta 50 km: 8, vistas 51, likes 0

### Instagram — 17 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** policiales: 17, likes 5
- **Por franja:** noche (18-24): 17, likes 5
- **Por día:** domingo: 2, likes 4.5 ⚠️muestra chica · jueves: 6, likes 3 · miércoles: 3, likes 8 ⚠️muestra chica · sábado: 2, likes 5.5 ⚠️muestra chica · viernes: 4, likes 7 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 13, likes 4 · hasta 50 km: 4, likes 12 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 201 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 5

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
