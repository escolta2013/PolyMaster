# Registro de Sesión: 23 de Febrero, 2026

## 🎯 Objetivo de la Sesión
Diagnosticar y corregir la precisión del AI Council, implementar filtros de liquidez reales basados en datos CLOB, y construir un modo de "Paper Trading" para calibración del sistema sin riesgo de capital.

---

## 🧠 1. Diagnóstico y Corrección del Anchoring Bias en el Council AI

### Problema detectado
Al añadir logging de respuestas crudas de los agentes (`Agent FedWatcher raw response: ...`), se detectó que todos los agentes devolvían `0.60` cuando el precio implícito del mercado era `0.55`. El patrón era:
- **FedWatcher:** "suggest a slight lean towards a longer address" → `0.60`
- **RuleLawyer:** "higher probability than the current price" → `0.60`
- **SentimentSwarm:** "increasing the probability" → `0.60`
- **Causa:** El modelo veía el precio de mercado (`Current YES Price: 0.55`) en el prompt y lo usaba como ancla, añadiendo un pequeño incremento para "parecer útil". Esto se conoce como **Anchoring Bias** en LLMs.

### Consecuencia en el sistema
Con `σ = 0` (desviación estándar cero), el RiskArbiter operaba siempre en **régimen de Cohesión** con peso mínimo (`10%`). El sistema de consenso ponderado por dispersión era completamente inoperante en la práctica. El "Edge Bruto" era predeciblemente `~0.05` en todo mercado evaluado — básicamente constante e independiente del mercado real.

### Corrección aplicada (`app/engines/council/orchestrator.py`)

**Cambio 1: Instrucción anti-sesgo explícita en el prompt**
```python
CRITICAL INSTRUCTION - AVOID ANCHORING BIAS:
Derive your probability estimate INDEPENDENTLY from first principles. 
DO NOT anchor your estimate to the 'Current YES Price'. The market 
price is often wrong, and your sole objective is to find the True 
Probability regardless of what the market currently thinks.
```

**Cambio 2: Intervalo de confianza en lugar de punto**
- Antes: `FinalConfidence: 0.60`
- Después: `FinalConfidenceRange: 0.40-0.60` (el midpoint se usa como score)

**Cambio 3: Parseo de rango con regex**
```python
scores = re.findall(r"(\d*\.\d+)", score_str)
if len(scores) >= 2:
    confidence = (float(scores[0]) + float(scores[-1])) / 2.0
```

**Cambio 4: Temperatura de `0.3` → `0.7`** para incentivar respuestas más divergentes entre agentes.

**Cambio 5: Logging de respuesta cruda** añadido justo después de recibir la respuesta del LLM:
```python
logger.info(f"Agent {self.name} raw response: {raw}")
```

### Resultado verificado
Tras la corrección, en el mismo mercado de prueba (`test_live_consensus.py`) los agentes devolvieron rangos genuinamente distintos:
```
FedWatcher:    0.60-0.75  → score: 0.675
RuleLawyer:    0.40-0.60  → score: 0.500
SentimentSwarm: 0.50-0.65 → score: 0.575
RiskArbiter:   0.45-0.60  → score: 0.525
```
Dispersión real, RiskArbiter mediando un conflicto genuino. Sistema funcionando como fue diseñado.

---

## 🔍 2. Implementación de Filtros de Liquidez CLOB

### Fundamento
El Director rechazaba trades no porque el Council no encontrara Edge, sino porque el spread del mercado siempre superaba el Edge Bruto. La única solución correcta es filtrar mercados antes de que lleguen al Council — no después.

**Regla matemática:**
```
Edge Neto = Council_Score - Best_Ask - (Spread × 0.5)
Si Spread > Edge_Bruto × 2 → Edge Neto siempre negativo → trade imposible
```

### Cambio en `app/engines/tracker/indexer.py` (Discovery Mode)

Modificados los umbrales de filtrado en Fase 2 (CLOB Spot-Check):
| Parámetro | Antes | Ahora |
|---|---|---|
| Precio (Layer 1) | `0.10 - 0.90` | `0.35 - 0.65` |
| Spread máximo (Layer 2) | `< 0.20` | `< 0.15` |
| Profundidad (Layer 3) | `> $10` | Sin cambio |

El sorting por `abs(0.5 - precio)` ya existía y se mantiene (prioriza máxima incertidumbre).

### Cambio en `app/engines/tracker/cluster_detector.py` (Whale Tracker)

Se añadió un **chequeo CLOB en tiempo real** antes de generar cada `ClusterAlert`. Para señales de ballenas, el rango de precio es más amplio pues la señal informacional justifica mayor tolerancia:
- **Precio:** `0.25 - 0.75` (más permisivo que Discovery)
- **Spread:** `< 0.15`

```python
# Fetch CLOB orderbook in real time
resp = await client.get(f"https://clob.polymarket.com/book?token_id={token_id}")
# Calcular midpoint y spread, descartar si no cumplen umbrales
```

Se corrigió también un **error de indentación** que causaba `UnboundLocalError: cannot access local variable 'alert'`. El bloque `ClusterAlert(...)` y las llamadas `new_alerts.append(alert)` y `_persist_alert(alert)` debían estar indentados dentro del nuevo `async with httpx.AsyncClient()`.

---

## 📋 3. Corrección de UnicodeEncodeError (cache.py)

El emoji `💾` en los logs de `CouncilCache` causaba `UnicodeEncodeError` en consolas Windows sin soporte UTF-8. Sustituido por el prefijo de texto `[CACHE]` en `app/engines/council/cache.py`.

```python
# Antes
logger.info(f"💾 Cache STORED: ...")

# Después  
logger.info(f"[CACHE] Cache STORED: ...")
```

---

## 📄 4. Paper Trading Mode para Calibración del Council

### Diseño general
El Paper Trading Mode permite recolectar entre 20-30 entradas reales en Supabase con los datos del Council (scores individuales por agente, spread, edge) y sus outcomes futuros, para calibrar estadísticamente la precisión del sistema **sin ejecutar ningún trade real**.

### Archivos modificados

#### `app/core/config.py`
Añadidas dos nuevas variables al modelo Pydantic:
```python
PAPER_TRADING_MODE: bool = False
PAPER_TRADING_MAX_SPREAD: float = 0.25  # Relajado para calibración
```

#### `.env`
Activado Paper Trading Mode:
```env
PAPER_TRADING_MODE=true
PAPER_TRADING_MAX_SPREAD=0.25
```

#### `app/engines/tracker/indexer.py`
El spread máximo ahora es dinámico:
```python
max_spread = settings.PAPER_TRADING_MAX_SPREAD if settings.PAPER_TRADING_MODE else 0.15
```
El rango de precio `0.35-0.65` **no cambia** en Paper Mode — solo el spread se relaja.
El log incluye el tag `[PAPER]` cuando el modo está activo.

**Bugfix:** `max_spread` fue movido fuera del `for` loop (antes se definía dentro, provocando `UnboundLocalError` cuando `verified_results` era una lista vacía de `None`).

#### `app/engines/tracker/cluster_detector.py`
El spread del Whale Tracker también respeta Paper Mode:
```python
whale_max_spread = settings.PAPER_TRADING_MAX_SPREAD if settings.PAPER_TRADING_MODE else 0.15
```

#### `app/engines/autonomous/director.py` (cambio más crítico)
Se añadió un bloque `PAPER TRADING MODE` **después** del cálculo del Edge Neto y **antes** del bloque de ejecución real. El bloque intercepta con `return` temprano, garantizando que nunca se llegue al executor.

Lógica:
- Si `edge_net > 0` → status = `WOULD_EXECUTE`
- Si `edge_net ≤ 0` → status = `PAPER_REJECTED`

Datos guardados en `autonomous_logs` por cada entrada:
```python
{
    "market_id": ...,
    "market_question": ...,
    "outcome": ...,
    "council_score": ...,         # Score ponderado final del Council
    "decision": "WOULD_EXECUTE",  # o PAPER_REJECTED
    "reasoning": json.dumps(agent_scores_dict),  # {"FedWatcher": 0.675, "RuleLawyer": 0.500, ...}
    "best_ask": ...,
    "best_bid": ...,
    "spread": ...,
    "detected_at": ...
}
```

Log en consola:
```
[PAPER] WOULD_EXECUTE | Market: ... | Council: 0.578 | Ask: 0.55 | 
        Spread: 0.15 | Edge Bruto: +0.028 | Edge Net: +0.003 | 
        Agents: {"FedWatcher": 0.675, "RuleLawyer": 0.500, ...}
```

### Cómo desactivar Paper Mode para producción
En `.env`, solo cambiar:
```env
PAPER_TRADING_MODE=false
```
No hay que modificar ni una línea de código. Los filtros estrictos de producción (`spread < 0.15`) retoman el control automáticamente.

---

## 📂 Resumen de Archivos Modificados

| Archivo | Tipo de cambio |
|---|---|
| `app/engines/council/orchestrator.py` | Anti-anchoring bias en prompt, rango de confianza, temperatura 0.7, log de raw response |
| `app/engines/council/cache.py` | Reemplazo de emoji `💾` por `[CACHE]` (fix UnicodeEncodeError Windows) |
| `app/engines/tracker/indexer.py` | Filtros de precio/spread más estrictos, spread dinámico para Paper Mode, bugfix de scope de `max_spread` |
| `app/engines/tracker/cluster_detector.py` | Filtro CLOB en tiempo real para alertas de ballenas, spread dinámico para Paper Mode, bugfix de indentación |
| `app/engines/autonomous/director.py` | Bloque `PAPER TRADING MODE` con lógica `WOULD_EXECUTE`/`PAPER_REJECTED` y logging a Supabase |
| `app/core/config.py` | Nuevos settings `PAPER_TRADING_MODE` y `PAPER_TRADING_MAX_SPREAD` |
| `.env` | Activación de `PAPER_TRADING_MODE=true` y `PAPER_TRADING_MAX_SPREAD=0.25` |

---

## 🚦 Estado al Cierre de Sesión

- **Bucle autónomo:** Corriendo en Paper Trading Mode
- **Council:** Generando dispersión genuina entre agentes (no anchoring)
- **Filtros de liquidez:** Activos en Discovery (`0.35-0.65`, `spread<0.25 [paper]`) y Whale Tracker (`0.25-0.75`, `spread<0.25 [paper]`)
- **Datos de calibración:** Pendientes de acumulación (el Indexer aún no encuentra mercados que pasen el filtro coarse de `Age<72h + Vol>$3k`)

## 🔜 Próximos Pasos
1. **Revisión del Whale Grader:** Verificar que las carteras en la lista de "smart money" tienen actividad y ROI positivo en los últimos 60 días.
2. **Ajuste del filtro coarse del Indexer** si en 24h no se generan entradas `WOULD_EXECUTE` (posiblemente relajar el mínimo de volumen de `$3k` a `$1k`).
3. **Análisis de calibración:** Con 20-30 entradas de `WOULD_EXECUTE`, calcular la tasa de acierto del Council por agente y decidir si el threshold de `0.65` de Council Score necesita ajuste.
4. **Activar producción:** Una vez validada la calibración, establecer `PAPER_TRADING_MODE=false` en `.env`.
