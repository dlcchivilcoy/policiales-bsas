# Panel editorial — Diario y Radio
Actualizado: 15/11/2026 20:34 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-15)

### 18:30 — 4 de 6 hechos policiales
Notas policiales leídas: 46 · fuera del radio: 11 · ubicación pendiente: 1 · repetidas: 1 · armadas: 7

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Detuvieron a un hombre de 42 años tras allanar una vivienda en Chacabu | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Murió un conductor de 30 años en un choque frontal en la Ruta 5 | Alberti (28.1 km) | ✅ | ✅ | ✅ | — ese hecho ya está en el Instagram de la cuenta |
| Chivilcoy: un motociclista de 22 años falleció tras impactar contra ot | Junín (0.0 km) | ✅ | ✅ | ✅ | ✅ |
| Junín: un repartidor se defendió a golpes de motochorros y frustró el  | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Queja de vecina por una situación insostenible en Chacabuco — no apta: No es del temario de policiales (según la IA): El hecho central es el reclamo o queja de una vecina sobre una situación cotidiana, no constituyendo un delito, siniestro, operativo ni causa penal.
- Salvan sus autos del secuestro tras dar positivo de alcoholemia en Chacabuco — no apta: No es del temario de policiales (según la IA): La nota habla de una nueva medida sobre controles de alcoholemia, no de un delito, accidente o hecho policial grave.
- Despegó un vuelo sanitario nocturno desde la pista del Aeroclub local — no apta: No es del temario de policiales (según la IA): Traslado sanitario nocturno sin detalles de gravedad ni delito

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · Carlos Casares (146.5 km) ×1 · Lincoln (137.8 km) ×1 · Las Flores (149.6 km) ×1 · Pergamino (122.9 km) ×1 · Colón (148.9 km) ×1

**Ubicación sin resolver (no salen solas):**
- Choque y despiste en la Ruta 5 a la altura de French — pendiente, ubicación sin resolver: «French» no está en el catálogo de Georef de la provincia

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 22 | 23 | 23 | 0 | 22 | 3 |
| Nacionales | 24 | 329 | 0 | 0 | 0 | 8 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 46 piezas · mediana vistas 111 · mediana likes 0

- **Por categoría:** policiales: 23, vistas 39, likes 0 · virales: 23, vistas 247, likes 2
- **Por franja:** madrugada (0-6): 23, vistas 247, likes 2 · noche (18-24): 23, vistas 39, likes 0
- **Por día:** domingo: 1, vistas 1315, likes 2 ⚠️muestra chica · jueves: 10, vistas 39.5, likes 0 · lunes: 8, vistas 86.5, likes 0.5 · martes: 7, vistas 221, likes 3 · miércoles: 7, vistas 160, likes 0 · sábado: 4, vistas 343.5, likes 0 ⚠️muestra chica · viernes: 9, vistas 23, likes 0
- **Por distancia:** 50 a 100 km: 15, vistas 18, likes 0 · hasta 50 km: 8, vistas 51, likes 0

### Instagram — 19 piezas · mediana vistas s/d · mediana likes 4

- **Por categoría:** policiales: 19, likes 4
- **Por franja:** noche (18-24): 19, likes 4
- **Por día:** domingo: 1, likes 2 ⚠️muestra chica · jueves: 6, likes 3 · lunes: 3, likes 1 ⚠️muestra chica · miércoles: 3, likes 8 ⚠️muestra chica · sábado: 2, likes 5.5 ⚠️muestra chica · viernes: 4, likes 7 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 15, likes 2 · hasta 50 km: 4, likes 12 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 199 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 5

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
