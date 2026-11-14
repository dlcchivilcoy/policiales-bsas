# Panel editorial — Diario y Radio
Actualizado: 13/11/2026 21:03 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-13)

### 18:30 — 5 de 6 hechos policiales
Notas policiales leídas: 70 · fuera del radio: 24 · ubicación pendiente: 0 · repetidas: 1 · armadas: 9

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Seis vehículos secuestrados y un caso de alcoholemia en Roque Pérez | 25 de Mayo (83.7 km) | ✅ | ✅ | ✅ | ✅ |
| Rige alerta naranja por tormentas severas y fuertes ráfagas de viento | Bragado (49.3 km) | ✅ | ✅ | ✅ | ✅ |
| Herido tras una pelea entre vecinos por una moto robada en Chacabuco | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Se prendió fuego una camioneta en el camino real Alberti-Benítez | Alberti (28.1 km) | ✅ | ✅ | ✅ | ✅ |
| Detuvieron en Junín a un hombre de 41 años acusado de abuso sexual | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Allanaron la cárcel de Junín por una estafa millonaria — no apta: No es del temario de policiales (según la IA): Falta el texto de la nota
- Registran una desaceleración en las habilitaciones comerciales de Chacabuco — no apta: No es del temario de policiales (según la IA): Informe sobre la cantidad de habilitaciones comerciales y regularizaciones otorgadas por la municipalidad
- Falleció Ramona Tita Brizuela en Chacabuco — no apta: No es del temario de policiales (según la IA): Es una necrológica o aviso fúnebre, material excluido de la cobertura policial.
- Se complica el tiempo en Chacabuco — no apta: No es del temario de policiales (según la IA): Se trata del pronóstico del tiempo común, sin alerta meteorológica oficial ni temporal con daños

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×7 · General Villegas (273.4 km) ×4 · Las Flores (149.6 km) ×4 · Pehuajó (198.5 km) ×4 · San Carlos de Bolívar (178.3 km) ×3 · Carlos Casares (146.5 km) ×1 · Pergamino (122.9 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 25 | 26 | 26 | 0 | 26 | 3 |
| Nacionales | 26 | 322 | 0 | 0 | 0 | 5 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 47 piezas · mediana vistas 221 · mediana likes 0

- **Por categoría:** policiales: 25, vistas 43, likes 0 · virales: 22, vistas 500, likes 5.5
- **Por franja:** madrugada (0-6): 22, vistas 500, likes 5.5 · noche (18-24): 25, vistas 43, likes 0
- **Por día:** domingo: 5, vistas 477, likes 1 · jueves: 10, vistas 39.5, likes 0 · lunes: 8, vistas 86.5, likes 0.5 · martes: 7, vistas 221, likes 3 · miércoles: 7, vistas 160, likes 0 · sábado: 9, vistas 939, likes 5 · viernes: 1, vistas 747, likes 2 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 18, vistas 20.5, likes 0 · hasta 50 km: 7, vistas 77, likes 0

### Instagram — 20 piezas · mediana vistas s/d · mediana likes 5.5

- **Por categoría:** policiales: 20, likes 5.5
- **Por franja:** noche (18-24): 20, likes 5.5
- **Por día:** domingo: 5, likes 6 · jueves: 5, likes 4 · lunes: 3, likes 1 ⚠️muestra chica · miércoles: 3, likes 8 ⚠️muestra chica · sábado: 4, likes 6.5 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 17, likes 5 · hasta 50 km: 3, likes 9 ⚠️muestra chica

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 195 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 9

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
