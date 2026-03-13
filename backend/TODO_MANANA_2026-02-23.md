# 📋 Plan de Trabajo: 23 de Febrero, 2026

## Contexto del Problema (Sesión de Anoche)

A pesar de múltiples parches, el bot sigue generando cientos de errores 404 por ciclo y no ejecuta ninguna compra simulada. Se determinó que el problema es **arquitectónico**, no superficial.

### Causa Raíz Identificada

Hay **DOS fuentes independientes** de 404s:

#### 1. Arbitrage Engine (Causa #1 — la más prolífica)
El `arb_manager.scan_all()` itera sobre tokens de mercados para buscar spreads entre pares. Busca orderbooks de tokens que pertenecen a mercados ya expirados/cerrados. 
- **Archivo:** `backend/app/engines/arbitrage/manager.py`
- **Fix necesario:** Agregar un filtro de `endDate` para descartar tokens de mercados cuya fecha ya pasó antes de intentar consultar el libro de órdenes.

#### 2. Cluster Detector — Ballenas con posiciones históricas (Causa #2)
Las 66 ballenas en Supabase tienen posiciones principalmente de largo plazo y apuestas ya implícitamente resueltas (Trump en el poder, Real Madrid ganando un partido pasado, etc.) con `curPrice = 0.99`. El Cluster Detector detecta que muchas ballenas coinciden en esas posiciones y las convierte en alertas para el Director, que las rechaza de inmediato con Edge negativo.
- **Archivo:** `backend/app/engines/tracker/cluster_detector.py`
- **Status:** Se aplicó un filtro de `curPrice >= 0.90` que filtra PARTE del problema, pero el campo `curPrice` a veces viene como `0` (para posiciones redeemable). El filtro `redeemable = True` ya está aplicado.
- **Fix pendiente:** El cluster detector necesita filtrar también por `endDate` ISO directamente de la posición.

---

## Plan de Acción para Mañana (2 Cambios Limpios)

### Cambio #1: Silenciar el Arbitrage Engine
**Archivo:** `backend/app/engines/arbitrage/manager.py`

Antes de llamar `get_orderbook()` para cualquier token, verificar la fecha del mercado:
```python
# Pseudocódigo
if market.get('endDate') and datetime.fromisoformat(market['endDate']) < datetime.now(utc):
    continue  # Skip expired markets
```

### Cambio #2: Migrar el Director a Discovery Mode exclusivo
**Archivo:** `backend/run_autonomous_loop.py`

El código actual tiene dos fuentes de trabajo para el Director:
1. `detector.scan_for_clusters()` → Ballenas con posiciones históricas → Precios 0.99 siempre
2. `tracker.indexer.get_top_markets()` → Mercados frescos de Gamma con incertidumbre real → **ESTA ES LA CORRECTA**

El `get_top_markets()` YA filtra precios entre 0.01-0.99. Esta noche encontró **1 mercado válido** de 200 analizados — eso es una señal de vida real.

**Fix:** Deshabilitar temporalmente el Cluster Detector como fuente para el Director o al menos hacer que el Director solo procese las alertas del Cluster si `confidence >= 0.7` (alta convergencia de ballenas) para reducir el ruido.

**O alternativamente:** Cambiar `scan_for_clusters()` para que además de posiciones, también analice trades recientes (últimas 24h) en lugar de posiciones históricas.

---

## Estado Actual de los Filtros (Lo que SÍ funciona)

| Filtro | Archivo | Estado |
|--------|---------|--------|
| Mercados cerrados (`closed`/`active`) | `director.py:189` | ✅ Funciona |
| Mercados expirados por fecha (`time_to_end < 0`) | `director.py:215` | ✅ Funciona |
| Posiciones redeemable de ballenas | `cluster_detector.py:107` | ✅ Funciona |
| Precio extremo en posiciones (`curPrice >= 0.90`) | `cluster_detector.py:124` | ✅ Funciona |
| Precio extremo en Director (`best_ask >= 0.90`) | `director.py:265` | ✅ Funciona (nuevo) |
| Precios válidos en Discovery Mode (0.01-0.99) | `indexer.py:54` | ✅ Funciona |

## Lo que NO está resuelto

- ❌ Arbitrage Engine continúa generando rafagas de 404 (50+ por ciclo)
- ❌ Cluster Detector sigue alimentando alertas de mercados con precio 0.99 (las ballenas tienen posiciones históricas)
- ❌ Ninguna compra simulada ejecutada en Supabase `autonomous_logs`

---

## Señal de Esperanza

El `Discovery Mode` con `get_top_markets()` encontró **1 mercado válido con incertidumbre real** esta noche. El bot tiene todo el motor necesario para ejecutar una compra — solo necesita alimentarse con datos limpios.

**Si mañana silenciamos el Arb Engine y hacemos que el Director dependa más del Discovery Mode, el bot debería ejecutar su primera compra simulada en el primer ciclo limpio.**
