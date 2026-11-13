# Panel editorial — Diario y Radio
Actualizado: 12/11/2026 21:32 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-12)

### 18:30 — 6 de 6 hechos policiales
Notas policiales leídas: 46 · fuera del radio: 15 · ubicación pendiente: 0 · repetidas: 1 · armadas: 9

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| La autopsia reveló que Ezequiel Caraballo murió de un golpe en la cabe | Alberti (39.8 km) | ✅ | ✅ | ✅ | ✅ |
| Un joven de 25 años grave tras ser apuñalado en el Parque Borchex | Chacabuco (91.2 km) | ✅ | ✅ | ✅ | ✅ |
| Dos motos chocaron en el centro y un conductor terminó en el hospital | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Le robaron la moto a un vecino de Chacabuco en la madrugada | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Delincuentes abandonaron una bicicleta y una amoladora al huir de la P | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Robaron una moto Guerrero 110 negra en la zona de la quinta 1010 | Chacabuco (50.1 km) | — ese hecho ya está en el canal de YouTube («Le robaron la mot | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Aviso fúnebre de Chacabuco — no apta: No es del temario de policiales (según la IA): La nota corresponde a una necrológica o aviso fúnebre
- Llegan millones para reparar caminos rurales — no apta: No es del temario de policiales (según la IA): Gestión de fondos públicos municipales para caminos rurales y subsidio
- Aviso fúnebre de Chacabuco — no apta: No es del temario de policiales (según la IA): Es una necrológica o aviso fúnebre institucional, temática excluida de los hechos policiales cubiertos.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · Las Flores (149.6 km) ×3 · Rojas (101.6 km) ×3 · Pehuajó (198.5 km) ×1 · Pergamino (122.9 km) ×1 · Trenque Lauquen (273.4 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 24 | 25 | 25 | 0 | 25 | 3 |
| Nacionales | 27 | 317 | 0 | 0 | 0 | 4 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 47 piezas · mediana vistas 221 · mediana likes 1

- **Por categoría:** policiales: 25, vistas 43, likes 0 · virales: 22, vistas 614, likes 6.5
- **Por franja:** madrugada (0-6): 22, vistas 614, likes 6.5 · noche (18-24): 25, vistas 43, likes 0
- **Por día:** domingo: 5, vistas 477, likes 1 · lunes: 8, vistas 86.5, likes 0.5 · martes: 7, vistas 221, likes 3 · miércoles: 7, vistas 160, likes 0 · sábado: 9, vistas 939, likes 5 · viernes: 11, vistas 85, likes 2
- **Por distancia:** 50 a 100 km: 16, vistas 21, likes 0 · Chivilcoy: 3, vistas 21, likes 1 ⚠️muestra chica · hasta 50 km: 6, vistas 79, likes 0

### Instagram — 18 piezas · mediana vistas s/d · mediana likes 6

- **Por categoría:** policiales: 18, likes 6
- **Por franja:** noche (18-24): 18, likes 6
- **Por día:** domingo: 5, likes 6 · lunes: 3, likes 1 ⚠️muestra chica · miércoles: 3, likes 8 ⚠️muestra chica · sábado: 4, likes 6.5 ⚠️muestra chica · viernes: 3, likes 6 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 15, likes 6 · Chivilcoy: 1, likes 12 ⚠️muestra chica · hasta 50 km: 2, likes 10.5 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 189 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 10

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
