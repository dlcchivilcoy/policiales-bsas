# Panel editorial — Diario y Radio
Actualizado: 26/11/2026 23:47 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-26)

### 22:30 — 4 de 6 hechos policiales
Notas policiales leídas: 71 · fuera del radio: 25 · ubicación pendiente: 0 · repetidas: 3 · armadas: 6

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Nueve de Julio: automovilista de 30 años murió en un violento choque e | Junín (99.4 km) | ✅ | ✅ | ✅ | ✅ |
| Detuvieron a un sospechoso por robar una cartera tras un forcejeo | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Dos aprehendidos por tenencia de marihuana y una moto incautada a las  | Chacabuco (91.2 km) | ✅ | ✅ | ✅ | ✅ |
| Fuego destruyó tres contenedores y un vallado cerca del Parque Borchex | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Sin datos sobre un choque en Chacabuco — no apta: No es del temario de policiales (según la IA): La nota provista no contiene información sobre un hecho real, ya que el texto se encuentra vacío.
- Luján figura entre los partidos con mayor cantidad de muertes viales — no apta: No es del temario de policiales (según la IA): la nota trata sobre estadísticas generales de víctimas fatales en siniestros viales por distrito, no sobre un hecho policial o accidente específico

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · Trenque Lauquen (273.4 km) ×6 · Pergamino (122.9 km) ×6 · Las Flores (149.6 km) ×3 · General Villegas (273.4 km) ×2 · Carlos Casares (146.5 km) ×1 · Lincoln (137.8 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 29 | 30 | 30 | 0 | 27 | 0 |
| Nacionales | 17 | 350 | 0 | 0 | 0 | 45 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 46 piezas · mediana vistas 283 · mediana likes 1

- **Por categoría:** policiales: 33, vistas 339, likes 1 · virales: 13, vistas 178, likes 3
- **Por franja:** madrugada (0-6): 20, vistas 191.5, likes 2 · mañana (6-12): 3, vistas 657, likes 3 ⚠️muestra chica · noche (18-24): 23, vistas 300, likes 1
- **Por día:** domingo: 6, vistas 236.5, likes 1 · lunes: 6, vistas 261.5, likes 0.5 · martes: 7, vistas 189, likes 1 · miércoles: 9, vistas 131, likes 1 · sábado: 8, vistas 534.5, likes 1 · viernes: 10, vistas 455, likes 2
- **Por distancia:** 50 a 100 km: 28, vistas 323.5, likes 1 · Chivilcoy: 1, vistas 173, likes 1 ⚠️muestra chica · hasta 50 km: 4, vistas 373.5, likes 0.5 ⚠️muestra chica

### Instagram — 30 piezas · mediana vistas s/d · mediana likes 4

- **Por categoría:** policiales: 30, likes 4
- **Por franja:** madrugada (0-6): 10, likes 4 · noche (18-24): 20, likes 4.5
- **Por día:** domingo: 3, likes 1 ⚠️muestra chica · lunes: 5, likes 12 · martes: 6, likes 2 · miércoles: 4, likes 6.5 ⚠️muestra chica · sábado: 6, likes 11.5 · viernes: 6, likes 4.5
- **Por distancia:** 50 a 100 km: 26, likes 4.5 · hasta 50 km: 4, likes 3 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 41 · subido, se verifica en la pasada siguiente: 8

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
