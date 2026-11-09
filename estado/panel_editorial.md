# Panel editorial — Diario y Radio
Actualizado: 08/11/2026 21:02 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-08)

### 18:30 — 5 de 6 hechos policiales
Notas policiales leídas: 42 · fuera del radio: 19 · ubicación pendiente: 0 · repetidas: 0 · armadas: 8

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Atacaron en patota a una alumna de 16 años a la salida de una escuela  | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |
| Motociclista ebrio chocó contra un auto frente al teatro Constantino | Bragado (49.3 km) | ✅ | ✅ | ✅ | ✅ |
| Estafa virtual de $11,7 millones llegó a presos alojados en una cárcel | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |
| Incendio total de un vehículo en la autopista Chacabuco-Junín | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Choque y caída en avenida San Martín por hacer willy con la moto | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Ampliaron detalles sobre un choque con heridos en Chacabuco — no apta: No es del temario de policiales (según la IA): El texto está vacío y no aporta información sobre un hecho policial o accidente concreto.
- Destituyeron y detuvieron a Santiago Peña, ex presidente de Paraguay — no apta: No es del temario de policiales (según la IA): La nota relata la destitución y detención del expresidente de Paraguay Santiago Peña en el marco de una crisis financiera internacional, tratándose de un hecho 
- Accidente en la madrugada de Chacabuco — no apta: No es del temario de policiales (según la IA): El texto original no contiene información sobre un hecho policial o siniestro vial, ya que está vacío.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×8 · Pergamino (122.9 km) ×4 · General Arenales (135.1 km) ×2 · General Villegas (273.4 km) ×2 · Pehuajó (198.5 km) ×2 · Las Flores (149.6 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 31 | 33 | 33 | 0 | 33 |
| Nacionales | 20 | 335 | 0 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 52 piezas · mediana vistas 33 · mediana likes 0.5

- **Por categoría:** policiales: 32, vistas 16.5, likes 0 · virales: 20, vistas 273, likes 3.5
- **Por franja:** madrugada (0-6): 20, vistas 273, likes 3.5 · noche (18-24): 32, vistas 16.5, likes 0
- **Por día:** jueves: 8, vistas 26.5, likes 0 · lunes: 8, vistas 39, likes 0.5 · martes: 9, vistas 9, likes 0 · miércoles: 7, vistas 17, likes 0 · sábado: 9, vistas 939, likes 5 · viernes: 11, vistas 85, likes 2
- **Por distancia:** 50 a 100 km: 20, vistas 15.5, likes 0 · Chivilcoy: 4, vistas 19.5, likes 0.5 ⚠️muestra chica · hasta 50 km: 8, vistas 13, likes 0

### Instagram — 29 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** policiales: 29, likes 5
- **Por franja:** noche (18-24): 29, likes 5
- **Por día:** jueves: 6, likes 5 · lunes: 5, likes 2 · martes: 5, likes 11 · miércoles: 6, likes 6 · sábado: 4, likes 6.5 ⚠️muestra chica · viernes: 3, likes 6 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 19, likes 4 · Chivilcoy: 2, likes 9.5 ⚠️muestra chica · hasta 50 km: 8, likes 6

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 184 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 5

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
