# Panel editorial — Diario y Radio
Actualizado: 31/10/2026 21:02 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-31)

### 18:30 — 5 de 5 hechos policiales
Notas policiales leídas: 49 · fuera del radio: 17 · ubicación pendiente: 0 · repetidas: 1 · armadas: 7

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Aprehendieron a un hombre de 54 años por robos con inhibidores de seña | Bragado (49.3 km) | ✅ | ✅ | ✅ | ✅ |
| Una camioneta se prendió fuego de madrugada en la vía pública | Bragado (49.3 km) | ✅ | ✅ | ✅ | ✅ |
| Menor herido tras impactar en moto contra un auto en Bragado | Bragado (49.3 km) | ✅ | ✅ | — no está entre las 2 más virales de la pasada (esta: viral 5/ | ✅ |
| Allanaron dos viviendas y secuestraron ropa y calzado deportivo trucho | 9 de Julio (99.4 km) | ✅ | ✅ | — no está entre las 2 más virales de la pasada (esta: viral 6/ | ✅ |
| Una mujer sufrió una fractura grave tras chocar con su moto en Bragado | Bragado (49.3 km) | ✅ | ✅ | — no está entre las 2 más virales de la pasada (esta: viral 6/ | ✅ |

**No salieron en esta pasada:**
- Allanaron una casa y secuestraron armas y 149 municiones por amenazas — no apta: El nota_web copia 15 palabras seguidas de la nota original («un rifle de aire comprimido marca mahely calibre 4 5 una pistola bersa calibre 22»), aun después de pedir que lo reescriba.
- Un motociclista herido tras un choque con una camioneta — no entra en la pasada: como mucho 5 hechos policiales por pasada, un reel cada 30 minutos (5 lugares libres)

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×6 · General Villegas (273.4 km) ×3 · Carlos Casares (146.5 km) ×2 · Pergamino (122.9 km) ×2 · San Carlos de Bolívar (178.3 km) ×1 · General Arenales (135.1 km) ×1 · Las Flores (149.6 km) ×1 · Pehuajó (198.5 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 25 | 25 | 12 | 13 | 24 |
| Nacionales | 23 | 350 | 0 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 43 piezas · mediana vistas 35 · mediana likes 0

- **Por categoría:** policiales: 25, vistas 16, likes 0 · virales: 18, vistas 65, likes 1
- **Por franja:** madrugada (0-6): 13, vistas 62, likes 1 · mañana (6-12): 5, vistas 526, likes 4 · noche (18-24): 25, vistas 16, likes 0
- **Por día:** domingo: 5, vistas 298, likes 2 · jueves: 7, vistas 32, likes 0 · lunes: 10, vistas 38, likes 0 · martes: 6, vistas 39.5, likes 0.5 · miércoles: 5, vistas 56, likes 1 · viernes: 10, vistas 13.5, likes 0
- **Por distancia:** 50 a 100 km: 16, vistas 12.5, likes 0 · Chivilcoy: 2, vistas 655.5, likes 3 ⚠️muestra chica · hasta 50 km: 7, vistas 16, likes 0

### Instagram — 22 piezas · mediana vistas s/d · mediana likes 4

- **Por categoría:** policiales: 22, likes 4
- **Por franja:** noche (18-24): 22, likes 4
- **Por día:** domingo: 4, likes 21.5 ⚠️muestra chica · jueves: 4, likes 3.5 ⚠️muestra chica · lunes: 4, likes 6.5 ⚠️muestra chica · martes: 3, likes 3 ⚠️muestra chica · miércoles: 3, likes 8 ⚠️muestra chica · viernes: 4, likes 2.5 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 14, likes 3.5 · Chivilcoy: 2, likes 55.5 ⚠️muestra chica · hasta 50 km: 6, likes 6

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 151 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 10

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
