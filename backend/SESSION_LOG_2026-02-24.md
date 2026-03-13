📊 Reporte de Comportamiento del Bot — 24 Feb 2026
Período analizado: 2026-02-23 18:34 → 2026-02-24 10:26 (~15h 52min) Estado actual: 🔴 BOT DETENIDO — No hay proceso Python activo en este momento.

🕐 Cronología de Actividad
Período	Estado
2026-02-22 19:00 → 2026-02-23 11:00	Corriendo (sesiones previas)
2026-02-23 11:00	Loop caído (CRITICAL LOOP ERROR)
2026-02-23 11:00 → 18:34	7.5h SIN ACTIVIDAD
2026-02-23 18:34	Reinicio manual (última sesión registrada)
2026-02-23 18:34:45	Última línea del 

autonomous.log
2026-02-24 10:26	Sin proceso activo — Bot caído de nuevo
La última entrada del log es:

2026-02-23 18:34:45 | SUCCESS | app.core.client:__init__:55 - Authenticated SDK Client Ready
El bot se autenticó el 23 a las 6:34pm y no hay ningún registro posterior. El proceso Python aparentemente murió al poco de iniciarse, dejando el loop sin correr durante las últimas ~16 horas.

🎯 Resultado Clave: 0 Trades Simulados Ejecutados (Paper Trading Mode)
No se encontró ni una sola entrada con tag [PAPER] ni WOULD_EXECUTE en los logs. El bot nunca llegó a ejecutar un trade simulado en ninguna sesión. Los motivos se identificaron claramente en los datos:

🔍 ¿Qué hizo el bot mientras estuvo corriendo?
✅ Lo que funcionó bien
Filtros de mercados caducados — El Director rechazó correctamente cientos de mercados expirados:

Skipping expired market 'Trail Blazers vs. Suns' (Ended 1 days ago)
Skipping expired market '...Vietnam...' (Ended 30 days ago)
Filtros de precios extremos — Rechazó correctamente mercados a 0.999:

Skipping settled or extreme market 'Will Kansas City Chiefs win...' (Price: 0.999)
Literalmente cientos de mercados NBA, F1, elecciones 2028, etc. descartados con precio 0.999.
Council Cache funcionando — Hits exitosos del caché:

Cache HIT: 'Will Real Madrid CF win on 2026-02-25?...' (score=0.982, TTL left=3.7h)
Cache HIT: 'Trump out as President before 2027?...' (score=0.963, TTL left=3.7h)
Cluster Detector activo — Procesando ballenas:

Cluster scan complete. Generated 234 new alerts. por ciclo
Director evaluando y calculando Edge — Ejemplos reales de mercados que casi pasaron:

Council Score: 0.96 | Ask: 0.99 | Edge: -0.03 → REJECTED
Council Score: 0.92 | Ask: 0.99 | Edge: -0.07 → REJECTED  
Council Score: 0.63 | Ask: 0.99 | Edge: -0.36 → REJECTED
❌ Los 3 Problemas que Impiden el Primer Trade
Problema #1: El Cluster Detector alimenta posiciones históricas en 0.99
Las 66 ballenas en Supabase tienen posiciones históricas en mercados que ya tienen precio 0.999 (Trump ganó, Real Madrid ganó el partido pasado, etc.). El bot genera 234 alertas de ballenas por ciclo pero todas con precio extremo → el Director las rechaza inmediatamente. El Council Score correcto no importa si el mercado ya está resuelto.

Problema #2: El Arbitrage Engine inunda los logs con 404s
El Arbitrage Engine escanea 100 mercados por ciclo intentando obtener orderbooks de tokens en mercados ya cerrados/expirados. En el log se ven ráfagas de 20-50 errores 404 consecutivos por ciclo:

ERROR | Error fetching orderbook for token 38703...: 
       PolyApiException[status_code=404, 'No orderbook exists for the requested token id']
Esto no tira el loop pero genera ruido masivo en 

error.log
 (5.5MB acumulados).

Problema #3: Discovery Mode encuentra muy pocos mercados válidos
El Indexer (get_top_markets) encontró 0-2 mercados válidos por ciclo de los 200 que analiza. El filtro de precio 0.35-0.65 es correcto, pero el mercado de Polymarket en este momento está dominado por mercados con precios extremos. El único mercado viable encontrado fue 'China coup attempt before 2027?' — que pasó los filtros de precio pero el Director lo rechazó por precio 0.999.

📉 Error Crítico que Mató el Loop
La última sesión antes del cierre final fue crasheada por este error (visible en 

error.log
):

2026-02-23 11:00:34 | ERROR | CRITICAL LOOP ERROR: 
'ClusterAlert' object has no attribute 'get'
Este error ocurre en 

run_autonomous_loop.py
 donde el código intenta tratar un objeto ClusterAlert como si fuera un diccionario (.get("market_id")). Las alertas del Cluster Detector son objetos Python, pero el loop las pasa directamente al Director esperando un dict. El try/except global captura el error y espera 60s... pero el loop se reinicia con el mismo problema y vuelve a caer.

📊 Resumen Cuantitativo (Última Sesión Activa)
Métrica	Valor
Ciclos ejecutados	~10 (entre sesiones)
Alertas de ballenas generadas/ciclo	~234
Mercados evaluados por Director	~240/ciclo
Mercados con precio 0.999	~230+/ciclo (>95%)
Mercados rechazados por expirados	~15-20/ciclo
Mercados que llegaron al Council	~2-5/ciclo
Trades [PAPER] WOULD_EXECUTE	0 en total
Errores 404 Arbitrage Engine/ciclo	~50
Errores críticos de loop	2 crashes documentados
🔜 Diagnóstico Final y Próximos Pasos
El bot está correctamente arquitecturado — los filtros funcionan, el Council genera scores genuinos, el Director calcula el Edge correctamente. El problema es la fuente de datos:

El Cluster Detector está alimentando señales de posiciones históricas que el mercado ya tiene a 0.99, y el Arbitrage Engine está consultando tokens de mercados expirados. El Discovery Mode (la única fuente válida) encuentra muy poco porque Polymarket en este momento tiene pocos mercados en el rango de incertidumbre real.

Fix crítico — 
run_autonomous_loop.py
: El ClusterAlert object necesita ser convertido a dict antes de pasarlo al Director (es el crash actual)
Fix urgente — arbitrage/manager.py: Filtrar mercados expirados antes de consultar orderbooks (silencia los 404s)
Fix de fondo — cluster_detector.py: Añadir filtro por endDate en las posiciones de ballenas para descartar mercados que ya cerraron

---

## ✅ Fixes Aplicados — 2026-02-24 (Sesión de Reparación)

### Fix #1 — `director.py`: Guards contra crashes por None  
**Causa raíz:** `question.lower()` en las líneas 124 y 132 crasheaba con `AttributeError` cuando el ClusterAlert llegaba con `market_question=None` o vacío (común en alertas de whale).  
**Fix aplicado:**
- `question` y `outcome` se inicializan con `or ""` / `or "YES"` como fallback seguros.
- `q_lower = question.lower()` se extrae a una sola definición en el tope de la función (elimina duplicado y el bug).
- Guard temprano: si `token_id` es None o vacío, retorna `"no_token_id"` inmediatamente.

### Fix #2 — `arbitrage/manager.py`: Filtrar mercados expirados  
**Status:** Ya estaba corregido en sesiones anteriores. Los filtros de `endDate` y `active/closed/archived` estaban presentes en `_check_binary_arb` y `_check_bundle_arb`.  
**Confirmado:** No requirió cambios adicionales.

### Fix #3 — `cluster_detector.py`: market_id placeholder → market_id real  
**Causa raíz:** El Cluster Detector generaba alertas con `market_id=f"m_{token_id[:8]}"` (placeholder) y `market_question="Whale Movement Detected"`. El Director recibía este market_id inútil, lo buscaba en Gamma API, no lo encontraba, y retornaba `"market_not_found"`. **Nunca llegaban al Council.**  
**Fix aplicado:**
- Antes de crear el `ClusterAlert`, se hace un lookup a `https://clob.polymarket.com/markets/{token_id}`.
- El endpoint CLOB devuelve el `condition_id` real del mercado, la `question` real y el `end_date_iso`.
- El alert ahora lleva datos reales: `market_id=condition_id`, `market_question=pregunta_real`, `end_date=end_date_iso`.
- Si el lookup falla, se usa `token_id` como fallback (que el Director ya sabe manejar buscando por `clob_token_ids`).

---

## 🔧 Calibración y Refinamiento del Director (Fase 2) — 2026-02-24

### 1. Corrección del Filtro de Fecha (Regex)
**Problema:** El bot saltaba mercados como *"Bitcoin above $64k on February 28"* porque el bucle de fechas encontraba el "2" dentro de "28" y asumía que era una fecha pasada (2 de febrero).
**Solución:** Se implementaron **límites de palabra (`\b`)** en la regex del Director para que "February 2" solo coincida con el día exacto y no como parte de otros números.

### 2. Sincronización de Spread en `.env`
**Problema:** Aunque `config.py` tenía `0.50` para Paper Trading, el archivo `.env` tenía `0.25` hardcodeado, lo que filtraba demasiados mercados en modo calibración.
**Solución:** Se actualizó el `.env` a `PAPER_TRADING_MAX_SPREAD=0.50`.

### 3. Cambio a Midpoint para Filtro de Precios Extremos
**Problema:** El Director usaba el `best_ask` para validar si un mercado era "extremo" (>0.90). En mercados de baja liquidez, el midpoint podía ser `0.50` pero el Ask `0.99`, causando un rechazo erróneo.
**Solución:** Se modificó `director.py` para usar el **midpoint** en el chequeo de seguridad de precios extremos, manteniendo el **best_ask** solo para el cálculo de Edge (coste real de ejecución).

### 4. Reactivación de Protección de Spread
**Problema:** La protección contra spreads anchos estaba comentada.
**Solución:** Se reactivó con un umbral dinámico: `0.05` en producción y `PAPER_TRADING_MAX_SPREAD` (0.50) en modo calibración.
