# Panel editorial — Diario y Radio
Actualizado: 10/11/2026 20:01 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-10)

### 18:30 — 3 de 6 hechos policiales
Notas policiales leídas: 42 · fuera del radio: 15 · ubicación pendiente: 0 · repetidas: 1 · armadas: 4

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Crimen de Mechita: filmaron a los sospechosos con un bulto hacia el ca | Alberti (28.1 km) | ✅ | ✅ | ✅ | ✅ |
| Hallan un cuerpo en el Canal Cafiero en el marco de la búsqueda de un  | Carlos Casares (28.1 km) | ✅ | ✅ | ✅ | ✅ |
| Encontraron un cadáver desmembrado en un canal y hay dos demorados | 9 de Julio (39.8 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Información policial de Chacabuco — no apta: No es del temario de policiales (según la IA): La nota no relata un hecho policial concreto, un siniestro vial ni un delito específico, sino que se trata de un título genérico o institucional que no aporta i

**Fuera del radio de 100 km:**
- Pergamino (122.9 km) ×6 · Cañuelas (115.9 km) ×5 · Pehuajó (198.5 km) ×1 · Las Flores (149.6 km) ×1 · General Pinto (171.5 km) ×1 · Campana (126.8 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 28 | 28 | 28 | 0 | 28 |
| Nacionales | 22 | 322 | 0 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 49 piezas · mediana vistas 206 · mediana likes 1

- **Por categoría:** policiales: 31, vistas 25, likes 0 · virales: 18, vistas 614, likes 6
- **Por franja:** madrugada (0-6): 18, vistas 614, likes 6 · noche (18-24): 31, vistas 25, likes 0
- **Por día:** domingo: 5, vistas 477, likes 1 · jueves: 8, vistas 26.5, likes 0 · lunes: 7, vistas 92, likes 1 · martes: 2, vistas 385.5, likes 2 ⚠️muestra chica · miércoles: 7, vistas 17, likes 0 · sábado: 9, vistas 939, likes 5 · viernes: 11, vistas 85, likes 2
- **Por distancia:** 50 a 100 km: 20, vistas 22, likes 0 · Chivilcoy: 4, vistas 19.5, likes 0.5 ⚠️muestra chica · hasta 50 km: 7, vistas 136, likes 0

### Instagram — 29 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** policiales: 29, likes 5
- **Por franja:** noche (18-24): 29, likes 5
- **Por día:** domingo: 5, likes 6 · jueves: 6, likes 5 · lunes: 2, likes 2 ⚠️muestra chica · martes: 3, likes 4 ⚠️muestra chica · miércoles: 6, likes 6 · sábado: 4, likes 6.5 ⚠️muestra chica · viernes: 3, likes 6 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 20, likes 5 · Chivilcoy: 2, likes 9.5 ⚠️muestra chica · hasta 50 km: 7, likes 5

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 187 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 7

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
