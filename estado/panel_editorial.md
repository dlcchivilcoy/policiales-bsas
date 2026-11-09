# Panel editorial — Diario y Radio
Actualizado: 09/11/2026 20:31 (hora AR). Se rehace al final de cada pasada.

Íconos: ✅ salió · ⏳ esperando otra temática · 🚫 cupo · — no le tocaba · ❌ falló · ⛔ rechazado · ❔ sin confirmar

## Hoy (2026-11-09)

### 18:30 — 4 de 6 hechos policiales
Notas policiales leídas: 54 · fuera del radio: 16 · ubicación pendiente: 1 · repetidas: 2 · armadas: 5

| Hecho | Lugar | YouTube | Web | Facebook | Instagram |
|---|---|---|---|---|---|
| Buscan a un joven de 27 años por un presunto homicidio en Mechita | 25 de Mayo (39.8 km) | ✅ | ✅ | ✅ | ✅ |
| Murió un joven de 24 años en un choque de moto en Lobos | Lobos (89.8 km) | ✅ | ✅ | ✅ | ✅ |
| Secuestraron una camioneta y frenaron una fiesta clandestina con 90 pe | Pergamino (70.7 km) | ✅ | ✅ | ✅ | ✅ |
| Choque, operativos viales y pedido de auxilio por acoso en la madrugad | Chacabuco (50.1 km) | ✅ | ✅ | ✅ | ✅ |

**No salieron en esta pasada:**
- Aprehendieron a un joven tras amenazar de muerte a policías en Comodoro Py — no apta: El nota_web copia 19 palabras seguidas de la nota original («luego de presentarse en el lugar en estado euforico y proferir amenazas de muerte contra e»), aun después de pedir que lo reescriba.

**Fuera del radio de 100 km:**
- Cañuelas (115.9 km) ×7 · General Villegas (273.4 km) ×2 · Las Flores (149.6 km) ×2 · General Pinto (171.5 km) ×1 · Pehuajó (198.5 km) ×1 · Trenque Lauquen (273.4 km) ×1 · Concepción del Uruguay (149.6 km) ×1 · Dudignac (104.6 km) ×1

**Ubicación sin resolver (no salen solas):**
- Cinco monjas volcaron en la Ruta 188 cuando viajaban a Luján para ver al Papa — pendiente, ubicación sin resolver: «Coronel Granada» no está en el catálogo de Georef de la provincia

## Últimos 7 días: volumen por destino

| Origen | YouTube | Web | Facebook (reel/posteo) | FB enlace | Instagram |
|---|---:|---:|---:|---:|---:|
| Policiales | 30 | 31 | 31 | 0 | 31 |
| Nacionales | 22 | 327 | 0 | 0 | 0 |

Topes vigentes: policiales 3 hechos por pasada (6 pasadas); nacionales 3 por pasada y 12 por día (1 de las categorías nuevas); X y TikTok en el [panel del distribuidor](https://github.com/dlcchivilcoy/social_publisher/blob/main/state/distribuidor_panel.md).
Ajuste semanal: con esto y las métricas de abajo se decide a mano; nada sube solo.

## Métricas a 24-72 h de publicadas (últimos 7 días)

### YouTube — 50 piezas · mediana vistas 159 · mediana likes 1

- **Por categoría:** policiales: 32, vistas 20, likes 0 · virales: 18, vistas 336, likes 5
- **Por franja:** madrugada (0-6): 18, vistas 336, likes 5 · noche (18-24): 32, vistas 20, likes 0
- **Por día:** domingo: 4, vistas 398, likes 0.5 ⚠️muestra chica · jueves: 8, vistas 26.5, likes 0 · lunes: 2, vistas 942.5, likes 4 ⚠️muestra chica · martes: 9, vistas 9, likes 0 · miércoles: 7, vistas 17, likes 0 · sábado: 9, vistas 939, likes 5 · viernes: 11, vistas 85, likes 2
- **Por distancia:** 50 a 100 km: 19, vistas 25, likes 0 · Chivilcoy: 4, vistas 19.5, likes 0.5 ⚠️muestra chica · hasta 50 km: 9, vistas 17, likes 0

### Instagram — 29 piezas · mediana vistas s/d · mediana likes 6

- **Por categoría:** policiales: 29, likes 6
- **Por franja:** noche (18-24): 29, likes 6
- **Por día:** domingo: 4, likes 6 ⚠️muestra chica · jueves: 6, likes 5 · lunes: 1, likes 2 ⚠️muestra chica · martes: 5, likes 11 · miércoles: 6, likes 6 · sábado: 4, likes 6.5 ⚠️muestra chica · viernes: 3, likes 6 ⚠️muestra chica
- **Por distancia:** 50 a 100 km: 18, likes 5.5 · Chivilcoy: 2, likes 9.5 ⚠️muestra chica · hasta 50 km: 9, likes 6

_No disponible: Instagram: alcance, reproducciones, guardados, compartidos y retención — falta el permiso instagram_manage_insights en el token. Facebook: alcance (falta read_insights) y los posteos con placa de nacionales (falta pages_read_user_content). Web: vistas por nota — sin integración en este sistema._
_Con menos de 5 piezas por grupo no se saca conclusión (franja, día o categoría)._

## Shorts en Radio del Centro (memoria de 5-7 días)

procesado: 184 · anterior al control: 120 · subido, se verifica en la pasada siguiente: 8

## Controles (sin tocar código)

Variables del repo policiales-bsas (Settings → Secrets and variables → Actions → Variables):
- `PUBLICAR_REDES` — sin él, todo simula. `MAX_POLICE_REELS_PER_PASS` — hechos por pasada (3; 0 pausa
  policiales). `POLICE_RADIUS_KM` — radio (100). `INTERCALADO=0` — apaga el intercalado de IG/FB.
- `NACIONALES=0` — nacionales solo simula. `NAC_PASADA_<CATEGORIA>` / `NAC_CUPO_<CATEGORIA>` — variedad por
  pasada / por día. `NAC_INSTAGRAM=0` — nacionales sin Instagram.
- `FILA_15=0` — apaga la fila de 15 minutos compartida (policiales vuelve a 30 min). `FILA_POR_PASADA` (12).
- `IG_POR_PASADA`, `FB_POR_PASADA`, `YT_SHORTS_POR_DIA` — topes por red.
X y TikTok: `DISTRIBUIDOR_ACTIVO`, `CUPO_<ORIGEN>_<RED>`, `INTERCALADO` en el ENV_FILE de social_publisher.
