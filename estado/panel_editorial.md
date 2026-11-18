# Panel editorial — Diario y Radio
Actualizado: 17/11/2026 21:33 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-17)

### 18:30 — 6 de 6 hechos policiales
Notas policiales leídas: 61 · fuera del radio: 24 · ubicación pendiente: 0 · repetidas: 2 · armadas: 7

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Detuvieron al motociclista que atropelló a Marcelo Daniel Tradatti | San Andrés de Giles (72.7 km) | ✅ | ✅ | ✅ | ✅ |
| Investigan robo y destrozos en el cementerio de la localidad de Morea | 9 de Julio (88.2 km) | ✅ | ✅ | ✅ | ✅ |
| Alberti: un menor de 16 años herido tras chocar en moto contra una cam | Alberti (28.1 km) | ✅ | ✅ | ✅ | ✅ |
| Temporal en Chacabuco: 55 milímetros de lluvia, evacuados y cortes de  | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Tres detenidos con armas de fuego en un campo de Bragado | Bragado (56.0 km) | ✅ | ✅ | ✅ | ✅ |
| Recuperan en menos de dos horas una moto robada en Junín tras seguirla | Junín (91.2 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Detuvieron a un hombre con pedido de captura por lesiones graves — no entra en la pasada: como mucho 6 hechos policiales por pasada, un reel cada 30 minutos (6 lugares libres)

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×7 · Pergamino (122.9 km) ×5 · San Carlos de Bolívar (178.3 km) ×3 · Las Flores (149.6 km) ×3 · Carlos Casares (146.5 km) ×2 · Rojas (101.6 km) ×2 · General Villegas (273.4 km) ×1 · Pehuajó (198.5 km) ×1

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram | IG prueba |
|---|---:|---:|---:|---:|---:|---:|
| Policiales | 27 | 29 | 29 | 0 | 28 | 0 |
| Nacionales | 17 | 339 | 0 | 0 | 0 | 26 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 40 piezas · mediana vistas 195.5 · mediana likes 0

- **Por categoría:** policiales: 24, vistas 145, likes 0 · virales: 16, vistas 212.5, likes 1.5
- **Por franja:** madrugada (0-6): 16, vistas 212.5, likes 1.5 · noche (18-24): 24, vistas 145, likes 0
- **Por día:** domingo: 5, vistas 487, likes 0 · jueves: 10, vistas 39.5, likes 0 · lunes: 5, vistas 679, likes 2 · miércoles: 7, vistas 160, likes 0 · sábado: 4, vistas 343.5, likes 0 ⚠️muestra chica · viernes: 9, vistas 23, likes 0
- **Por distancia:** 50 a 100 km: 16, vistas 128, likes 0 · Chivilcoy: 1, vistas 899, likes 2 ⚠️muestra chica · hasta 50 km: 7, vistas 160, likes 0

### Instagram — 23 piezas · mediana vistas s/d · mediana likes 5

- **Por categoría:** policiales: 23, likes 5
- **Por franja:** noche (18-24): 23, likes 5
- **Por día:** domingo: 2, likes 4.5 ⚠️muestra chica · jueves: 6, likes 3 · lunes: 6, likes 5.5 · miércoles: 3, likes 8 ⚠️muestra chica · sábado: 2, likes 5.5 ⚠️muestra chica · viernes: 4, likes 7 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 17, likes 4 · hasta 50 km: 6, likes 11.5

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 201 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 9

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
