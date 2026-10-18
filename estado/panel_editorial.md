# Panel editorial — Diario y Radio
Actualizado: 17/10/2026 23:39 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-17)

### 23:35 — 0 de 3 hechos policiales
Notas policiales leídas: 41 · fuera del radio: 15 · ubicación pendiente: 1 · repetidas: 0 · armadas: 1

**No salieron en esta pasada:**
- Advierten sobre una nueva modalidad de estafa amorosa en la ciudad — no apta: No es del temario de policiales (según la IA): la nota trata sobre una modalidad general de estafa amorosa y consejos de prevención, sin un hecho policial puntual o denuncia concreta

**Fuera del radio de 100 km:**
- San Carlos de Bolívar (178.3 km) ×5 · Pergamino (122.9 km) ×4 · Cañuelas (115.9 km) ×2 · Carlos Tejedor (225.1 km) ×2 · General Villegas (273.4 km) ×1 · Trenque Lauquen (273.4 km) ×1

**Ubicación sin resolver (no salen solas):**
- MUNICIPIO 16:49 | ¿FAENA CLANDESTINA? Villarino: Hallaron casi 600 kilos de carn — pendiente, ubicación sin resolver: «Villarino» no está en el catálogo de Georef de la provincia

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 77 | 78 | 42 | 37 | 77 |
| Nacionales | 84 | 84 | 56 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 59 piezas · mediana vistas 18 · mediana likes 0

- **Por categoría:** general: 24, vistas 8, likes 0 · policiales: 35, vistas 39, likes 0
- **Por franja:** madrugada (0-6): 1, vistas 295, likes 2 ⚠️muestra chica · mañana (6-12): 11, vistas 5, likes 0 · noche (18-24): 23, vistas 28, likes 0 · tarde (12-18): 24, vistas 13, likes 0
- **Por día:** jueves: 36, vistas 18, likes 0 · miércoles: 1, vistas 262, likes 0 ⚠️muestra chica · viernes: 22, vistas 16.5, likes 0

### Facebook — 14 piezas · mediana vistas 445 · mediana likes 1

- **Por categoría:** policiales: 14, vistas 445, likes 1
- **Por franja:** madrugada (0-6): 1, vistas 465, likes 1 ⚠️muestra chica · mañana (6-12): 4, vistas 448.5, likes 1.5 ⚠️muestra chica · noche (18-24): 4, vistas 443, likes 1 ⚠️muestra chica · tarde (12-18): 5, vistas 388, likes 1
- **Por día:** jueves: 9, vistas 425, likes 1 · miércoles: 1, vistas 286, likes 1 ⚠️muestra chica · viernes: 4, vistas 525.5, likes 2.5 ⚠️muestra chica

### Instagram — 33 piezas · mediana vistas s/d · mediana likes 4

- **Por categoría:** policiales: 33, likes 4
- **Por franja:** madrugada (0-6): 1, likes 13 ⚠️muestra chica · mañana (6-12): 6, likes 6 · noche (18-24): 15, likes 4 · tarde (12-18): 11, likes 4
- **Por día:** jueves: 22, likes 2 · miércoles: 1, likes 4 ⚠️muestra chica · viernes: 10, likes 8.5

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

anterior al control: 174 · procesado: 47

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_VARIEDAD_POR_PASADA`, `NAC_CUPO_<CATEGORIA>` — categorías nuevas.
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
