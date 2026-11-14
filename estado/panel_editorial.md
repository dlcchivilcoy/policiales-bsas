# Panel editorial — Diario y Radio
Actualizado: 14/11/2026 19:34 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-14)

### 18:30 — 2 de 6 hechos policiales
Notas policiales leídas: 42 · fuera del radio: 21 · ubicación pendiente: 1 · repetidas: 0 · armadas: 6

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Demoraron a un hombre que rompió los vidrios de un kiosco en el centro | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Múltiples operativos en Junín: cuatro aprehensiones, un prófugo y drog | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Vecino cuestiona el estado de una avenida en Chacabuco — no apta: No es del temario de policiales (según la IA): Queja de un vecino por el estado de una avenida de la ciudad
- Bragado acaparó la atención nacional por un crimen y una venta empresaria — no apta: No es del temario de policiales (según la IA): La nota habla de la repercusión mediática nacional de dos hechos ocurridos en Bragado y no constituye un hecho policial o delito en sí mismo.
- Incidente en un barrio de Chacabuco — no apta: No es del temario de policiales (según la IA): La nota trata sobre un incidente genérico en un barrio sin especificar gravedad, delitos, heridos ni intervención policial o judicial clara.
- Falleció Marta del Carmen González en Chacabuco — no apta: No es del temario de policiales (según la IA): La nota corresponde a una necrológica o aviso fúnebre institucional, temática excluida de los hechos policiales.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · Las Flores (149.6 km) ×3 · Pergamino (122.9 km) ×3 · General Villegas (273.4 km) ×2 · Pehuajó (198.5 km) ×2 · Carlos Casares (146.5 km) ×1 · Rojas (101.6 km) ×1 · Remedios de Escalada (132.9 km) ×1 · Germania (188.8 km) ×1 · Embarcación (None km) ×1

**Ubicación sin resolver (no salen solas):**
- Volcó una camioneta en Ruta 5: no hubo lesionados — pendiente, ubicación sin resolver: «French» no está en el catálogo de Georef de la provincia

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 22 | 23 | 23 | 0 | 23 | 3 |
| Nacionales | 23 | 321 | 0 | 0 | 0 | 7 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 45 piezas · mediana vistas 160 · mediana likes 0

- **Por categoría:** policiales: 24, vistas 41, likes 0 · virales: 21, vistas 247, likes 3
- **Por franja:** madrugada (0-6): 21, vistas 247, likes 3 · noche (18-24): 24, vistas 41, likes 0
- **Por día:** domingo: 5, vistas 477, likes 1 · jueves: 10, vistas 39.5, likes 0 · lunes: 8, vistas 86.5, likes 0.5 · martes: 7, vistas 221, likes 3 · miércoles: 7, vistas 160, likes 0 · sábado: 2, vistas 12.5, likes 0 ⚠️muestra chica · viernes: 6, vistas 106.5, likes 0
- **Por distancia:** 50 a 100 km: 16, vistas 17.5, likes 0 · hasta 50 km: 8, vistas 68, likes 0

### Instagram — 21 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** policiales: 21, likes 5
- **Por franja:** noche (18-24): 21, likes 5
- **Por día:** domingo: 5, likes 6 · jueves: 6, likes 3 · lunes: 3, likes 1 ⚠️muestra chica · miércoles: 3, likes 8 ⚠️muestra chica · sábado: 2, likes 6.5 ⚠️muestra chica · viernes: 2, likes 7 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 17, likes 4 · hasta 50 km: 4, likes 10.5 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 199 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 4

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
