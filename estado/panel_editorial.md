# Panel editorial — Diario y Radio
Actualizado: 28/10/2026 20:03 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-10-28)

### 18:30 — 3 de 5 hechos policiales
Notas policiales leídas: 54 · fuera del radio: 21 · ubicación pendiente: 0 · repetidas: 3 · armadas: 5

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Detuvieron en Lomas de Zamora a un hombre de 41 años por robar techos  | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |
| Choque entre camioneta y moto: dos jóvenes al hospital | 9 de Julio (99.4 km) | ✅ | ✅ | ✅ | ✅ |
| Aprehenden a un joven de 24 años por intento de robo de cables en el e | Bragado (49.3 km) | ✅ | ✅ | — no está entre las 2 más virales de la pasada (esta: viral 5/ | ✅ |

**No salieron en esta pasada:**
- Dos jóvenes de 18 y 20 años fueron aprehendidos por robar herramientas de una ca — no apta: El nota_web copia 20 palabras seguidas de la nota original («semanas atras con las pruebas reunidas la unidad funcional de instruccion y juicio ufij n »), aun después de pedir que lo reescriba.
- Al menos 30 muertos tras el choque de dos trenes de alta velocidad en Toledo — no apta: No es del temario de policiales (según la IA): El accidente ferroviario ocurrió en Toledo, España, por lo que no es de interés local ni pertenece al partido de Roque Pérez en la provincia de Buenos Aires.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×4 · Pergamino (122.9 km) ×4 · Carlos Casares (146.5 km) ×3 · Pehuajó (198.5 km) ×3 · Trenque Lauquen (273.4 km) ×3 · General Pinto (171.5 km) ×2 · Las Flores (149.6 km) ×2

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 27 | 27 | 13 | 8 | 22 |
| Nacionales | 25 | 201 | 9 | 0 | 15 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 58 piezas · mediana vistas 68.5 · mediana likes 0

- **Por categoría:** general: 15, vistas 40, likes 0 · policiales: 35, vistas 69, likes 0 · virales: 8, vistas 297, likes 3
- **Por franja:** madrugada (0-6): 3, vistas 68, likes 2 ⚠️muestra chica · mañana (6-12): 5, vistas 526, likes 4 · noche (18-24): 50, vistas 63.5, likes 0
- **Por día:** domingo: 5, vistas 298, likes 2 · jueves: 10, vistas 86, likes 1 · lunes: 10, vistas 38, likes 0 · martes: 6, vistas 39.5, likes 0.5 · miércoles: 9, vistas 83, likes 0 · sábado: 5, vistas 21, likes 0 · viernes: 13, vistas 148, likes 0
- **Por distancia:** 50 a 100 km: 28, vistas 63.5, likes 0 · Chivilcoy: 2, vistas 655.5, likes 3 ⚠️muestra chica · hasta 50 km: 5, vistas 35, likes 0

### Facebook — 6 piezas · mediana vistas 501 · mediana likes 1

- **Por categoría:** policiales: 6, vistas 501, likes 1
- **Por franja:** noche (18-24): 6, vistas 501, likes 1
- **Por día:** jueves: 1, vistas 3511, likes 3 ⚠️muestra chica · miércoles: 2, vistas 501, likes 2 ⚠️muestra chica · viernes: 3, vistas 293, likes 1 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 5, vistas 494, likes 1 · hasta 50 km: 1, vistas 3511, likes 3 ⚠️muestra chica

### Instagram — 31 piezas · mediana vistas s/d · mediana likes 7

- **Por categoría:** general: 5, likes 2 · policiales: 26, likes 8
- **Por franja:** noche (18-24): 31, likes 7
- **Por día:** domingo: 4, likes 21.5 ⚠️muestra chica · jueves: 5, likes 9 · lunes: 4, likes 6.5 ⚠️muestra chica · martes: 3, likes 3 ⚠️muestra chica · miércoles: 6, likes 2.5 · sábado: 4, likes 13 ⚠️muestra chica · viernes: 5, likes 10
- **Por distancia:** 50 a 100 km: 19, likes 8 · Chivilcoy: 2, likes 55.5 ⚠️muestra chica · hasta 50 km: 5, likes 7

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 145 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 5

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
