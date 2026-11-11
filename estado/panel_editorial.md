# Panel editorial — Diario y Radio
Actualizado: 11/11/2026 20:02 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-11)

### 18:30 — 3 de 6 hechos policiales
Notas policiales leídas: 34 · fuera del radio: 18 · ubicación pendiente: 0 · repetidas: 0 · armadas: 6

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Apresaron a dos hombres por el homicidio de Ezequiel Caraballo en Brag | Junín (40.8 km) | ✅ | ✅ | ✅ | ✅ |
| Desplegaron 35 policías de 25 de Mayo en Luján por la visita de un Pap | 25 de Mayo (90.1 km) | ✅ | ✅ | ✅ | ✅ |
| Detuvieron a un joven de 21 años tras una persecución y hallaron una m | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Joven lesionado fue hospitalizado tras un incidente en Chacabuco — no apta: No es del temario de policiales (según la IA): Atención médica a un joven por una lesión
- Repudio por un perro atropellado y abandonado en la calle — no apta: No es del temario de policiales (según la IA): Es un episodio de maltrato animal callejero repudiado en redes sociales, que no constituye un delito penal formalmente investigado ni un siniestro vial con vehí
- Debate en el Concejo de San Antonio de Areco por un joven herido — no apta: No es del temario de policiales (según la IA): El hecho central trata sobre el debate político y la presentación de un proyecto en el Concejo Deliberante.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · Pergamino (122.9 km) ×5 · San Carlos de Bolívar (178.3 km) ×2 · Pehuajó (198.5 km) ×2 · Carlos Casares (146.5 km) ×1 · Las Flores (149.6 km) ×1 · Bahía Blanca (469.5 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 25 | 25 | 25 | 0 | 25 | 3 |
| Nacionales | 24 | 320 | 0 | 0 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 50 piezas · mediana vistas 199.5 · mediana likes 1

- **Por categoría:** policiales: 30, vistas 41, likes 0 · virales: 20, vistas 614, likes 7
- **Por franja:** madrugada (0-6): 20, vistas 614, likes 7 · noche (18-24): 30, vistas 41, likes 0
- **Por día:** domingo: 5, vistas 477, likes 1 · jueves: 8, vistas 26.5, likes 0 · lunes: 8, vistas 86.5, likes 0.5 · martes: 7, vistas 221, likes 3 · miércoles: 2, vistas 200, likes 0.5 ⚠️muestra chica · sábado: 9, vistas 939, likes 5 · viernes: 11, vistas 85, likes 2
- **Por distancia:** 50 a 100 km: 19, vistas 19, likes 0 · Chivilcoy: 3, vistas 21, likes 1 ⚠️muestra chica · hasta 50 km: 8, vistas 79, likes 0

### Instagram — 24 piezas · mediana vistas s/d · mediana likes 5.5

- **Por categoría:** policiales: 24, likes 5.5
- **Por franja:** noche (18-24): 24, likes 5.5
- **Por día:** domingo: 5, likes 6 · jueves: 6, likes 5 · lunes: 3, likes 1 ⚠️muestra chica · miércoles: 3, likes 7 ⚠️muestra chica · sábado: 4, likes 6.5 ⚠️muestra chica · viernes: 3, likes 6 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 19, likes 5 · Chivilcoy: 1, likes 12 ⚠️muestra chica · hasta 50 km: 4, likes 5.5 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 188 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 7

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
