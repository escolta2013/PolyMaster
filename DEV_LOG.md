# 📔 PolyMaster Development Log (Bitácora)

Este archivo registra el progreso diario, las decisiones de arquitectura y los cambios clave en el ecosistema PolyMaster.

---

## [2026-02-23] - Council AI Calibration, Filtros CLOB y Paper Trading Mode

### ✅ Hitos Completados

#### 🧠 Corrección de Anchoring Bias en el Council AI (`app/engines/council/orchestrator.py`)
- **Diagnóstico:** Se añadió logging de respuestas crudas del LLM y se detectó que todos los agentes devolvían exactamente `0.60` cuando el precio implícito del mercado era `0.55`. El modelo usaba el precio como ancla y añadía un pequeño incremento en lugar de derivar la probabilidad desde primeros principios (Anchoring Bias en LLMs).
- **Consecuencia:** Con σ = 0, el RiskArbiter operaba siempre en régimen de Cohesión mínima. El sistema de consenso ponderado por dispersión era inoperante.
- **Corrección:** Se añadió instrucción anti-sesgo explícita en el prompt (`AVOID ANCHORING BIAS`), se cambió el output de punto a rango (`FinalConfidenceRange: 0.40-0.60`) con parseo de midpoint, se elevó la temperatura de `0.3` a `0.7`, y se añadió logging de la respuesta cruda de cada agente.
- **Resultado:** Dispersión genuina verificada: `FedWatcher: 0.675, RuleLawyer: 0.500, SentimentSwarm: 0.575, RiskArbiter: 0.525`.

#### 💧 Filtros de Liquidez CLOB (`indexer.py` y `cluster_detector.py`)
- **Discovery Mode (`indexer.py`):** Precio estricto `0.35-0.65` (antes `0.10-0.90`), spread máximo `0.15` (antes `0.20`).
- **Whale Tracker (`cluster_detector.py`):** Añadido chequeo CLOB en tiempo real antes de generar cada `ClusterAlert`. Precio `0.25-0.75`, spread `< 0.15`. Rango de precio más amplio que Discovery porque la señal informacional de ballenas justifica mayor tolerancia.
- **Bugfix:** Corregido `UnboundLocalError: cannot access local variable 'alert'` por error de indentación al refactorizar el bloque de generación de alertas.

#### 📄 Paper Trading Mode para Calibración (`director.py`, `config.py`, `.env`)
- Activado con `PAPER_TRADING_MODE=true` en `.env`.
- Cuando está activo, el Director intercepta la ejecución **después** del cálculo de Edge Neto y loguea `WOULD_EXECUTE` (si `edge_net > 0`) o `PAPER_REJECTED` (si no) en Supabase con todos los scores individuales de agentes, spread, precio y timestamp.
- El filtro de spread se relaja a `PAPER_TRADING_MAX_SPREAD=0.25` en ambos `indexer.py` y `cluster_detector.py`.
- La lógica de producción real **nunca se alcanza** — el bloque hace `return` antes del executor.
- Para ir a producción: cambiar `PAPER_TRADING_MODE=false` en `.env`. Cero cambios de código necesarios.

#### 🐛 Fix UnicodeEncodeError (`cache.py`)
- El emoji `💾` en los logs del `CouncilCache` causaba `UnicodeEncodeError` en consolas Windows. Reemplazado por el prefijo `[CACHE]`.

### 🛠️ Decisiones Técnicas
- **Rango vs Punto:** Pedir `FinalConfidenceRange: 0.35-0.55` en lugar de `FinalConfidence: 0.60` obliga al modelo a razonar explícitamente sobre su incertidumbre, generando dispersión natural entre agentes — exactamente lo que necesita el RiskArbiter.
- **Bifurcación quirúrgica:** El Paper Trading Mode se implementó como una bifurcación con `return` temprano, sin tocar ni reescribir la lógica de producción existente.
- **Filtro CLOB en tiempo real en Whale Tracker:** En lugar de filtrar solo por metadata de Gamma (que puede ser stale), se consulta el orderbook real en vivo antes de emitir la alerta.

### 🚀 Próximos Objetivos
1. Acumular 20-30 entradas `WOULD_EXECUTE` en Supabase y calcular accuracy del Council por agente.
2. Revisar el Whale Grader para descartar wallets sin actividad en los últimos 60 días.
3. Basado en datos de calibración, ajustar threshold del Council Score y decidir si `0.35-0.65` de rango de precio es correcto.

---

## [2026-02-23] - Autonomous Stabilization & Robust Error Handling

### ✅ Hitos Completados
- **Estabilización del Bucle**: Corregidos dos errores críticos que causaban reinicios infinitos:
    - `AttributeError`: Reemplazado `.get()` por acceso directo a atributos en objetos `ClusterAlert`.
    - `UnboundLocalError`: Eliminada importación redundante de `director` dentro del bucle que sombreaba la variable global.
- **Orquestación Centralizada**: Se eliminó el disparo directo del Director desde `ClusterDetector`. Ahora toda la lógica de filtrado y decisión reside en `run_autonomous_loop.py`, mejorando el control y evitando análisis duplicados.
- **Robustez de API (404 Handling)**:
    - Modificado `PolyClient` para tratar errores `404: No orderbook exists` como **WARNING** en lugar de **ERROR**. Esto evita falsas alarmas por mercados liquidados o inactivos.
    - Implementado filtrado estricto en el motor de Arbitraje (`ArbManager`) para ignorar mercados/eventos marcados como `closed`, `archived` o `active: false` antes de consultar el CLOB.
- **Deduplicación de Alertas**: Reforzado el filtro de clusters de ballenas para procesar solo alertas con **confianza ≥ 70%**, eliminando ruido de posiciones históricas irrelevantes.

### 🛠️ Decisiones Técnicas
- **Logging Diferenciado**: Decidimos que la falta de un orderbook no es un fallo del cliente sino un estado del mercado. El cambio a `WARNING` mantiene los logs limpios de errores "falsos positivos".
- **Filtro de Estado Prematuro**: Al filtrar por `active=true` y fechas de cierre antes de llamar a la API de CLOB, reducimos la latencia de cada ciclo y evitamos hitting de rate-limits innecesarios.

### 🚀 Próximos Objetivos
- **Semantic Arbitrage**: Iniciar el desarrollo del scanner basado en NLP para detectar mercados espejo.
- **PnL Analytics**: Integrar el reporte diario de ganancias/pérdidas en el Dashboard de Supabase.

---


### 🛰️ Hitos Completados
- **Skill Deployment**: Instaladas 15 habilidades de nivel senior en `.agent/skills/` (Arquitectura, Seguridad, FastAPI, Next.js).
- **AGENTS.md Standard**: Implementado manual de operaciones para agentes de IA siguiendo el estándar `agents.md`.
- **Auditoría de Sistemas**: Identificados puntos críticos de mejora: sincronismo en el backend y falta de Server Components en el frontend.

### 🛠️ Decisiones Técnicas
- **Adopción de `httpx`**: Se decidió migrar todas las llamadas REST a modo asíncrono para evitar el bloqueo del event loop durante el escaneo de mercados.
- **Pydantic Settings**: Centralización de la configuración para mejorar la trazabilidad de secretos y variables de entorno.

### 🚀 Próximos Objetivos
- **Refactorización Asíncrona**: Comenzar con el `PolymarketIndexer` para optimizar la recolección de datos de ballenas.
- **Logging Pro**: Sustituir el logging estándar por `loguru` con formato JSON.


## [2026-02-12] - Cierre de Fase 1: Inteligencia de "Smart Money"

### ✅ Hitos Completados
- **Cluster Detector**: Implementado sistema de detección de convergencia. Ahora el backend identifica automáticamente cuándo ≥3 ballenas entran en el mismo mercado.
- **Copy Executor**: Motor de copiado de trading listo con límites de seguridad (per-trade/daily) y modo simulación activado por defecto.
- **Sistema de Notificaciones UI**:
    - Agregado `NotificationBell` en el Navbar con polling en tiempo real.
    - Nuevo panel de `Cluster Alerts` en el Dashboard con tarjetas dinámicas.
- **Sincronización de Base de Datos**: Migradas tablas `cluster_alerts` y `copy_trades` a Supabase.
- **Background Worker**: Refactorizado para manejar dos ciclos (Detección de Clusters cada 5 min / Sincronización Total cada 1 hora).

### 🛠️ Decisiones Técnicas
- **Modo Simulación**: Decidimos que todas las copias de trading sean simuladas (`COPY_SIMULATION=true`) hasta que se configure una Private Key válida, para proteger el capital del usuario durante el desarrollo.
- **Estructura de Worker**: Se optó por un modelo de `asyncio.create_task` para permitir que el escáner de clusters sea más frecuente que la sincronización pesada de wallets sin bloquear el proceso.

### 🐛 Problemas Resueltos (Troubleshooting)
- **Supabase Auth Error**: Se corrigió el error de inicialización agregando las variables `SUPABASE_URL` y `SUPABASE_KEY` al archivo `.env`.
- **Import Errors**: Se normalizaron las rutas de importación en el worker para evitar el conflicto entre ejecutar como módulo vs. script directo.
- **Estabilidad de Frontend**: Se instalaron dependencias de `lucide-react` y se verificó que el build de Next.js sea exitoso tras las integraciones de la Phase 1.

---

## [2026-02-12] - Cierre de Fase 2: Ghost Engine & Tactical Arbitrage

### ✅ Hitos Completados
- **Scanner Estratégico**: El motor de escaneo ahora clasifica oportunidades en dos categorías: **Hype Spikes** (momentum) y **Nothing Ever Happens (NEH)** (decay de probabilidad).
- **Risk Manager**: Implementado sistema de Stop-loss (15%) y Take-profit (25%) monitoreable y límites de exposición por mercado ($100 USDC).
- **Shadow Merger**: Implementada lógica para consolidar posiciones YES/NO y liberar capital atrapado.
- **Frontend v2.5 Tactical**:
    - Dashboard de Ghost actualizado con insignias de estrategia.
    - Controles tácticos interactivos para spread, tamaño de posición y gestión de riesgo.
    - Botón de Merger funcional (simulado) con feedback visual de escaneo.
- **API Ghost**: Endpoints expandidos para `/strategy/start` (con soporte NEH), `/merge/scan`, y `/risk/configure`.

### 🛠️ Decisiones Técnicas
- **Heurística de NEH**: Se definió un puntaje de "Grind" basado en precios de YES inflados (>0.6) y volumen moderado, permitiendo al bot apostar sistemáticamente contra el optimismo irracional del mercado retail.
- **Panic Kill-Switch**: Se integró un botón de emergencia unificado que cancela todas las órdenes activas en el CLOB a través del `OrderManager`.

### 🚀 Próximos Objetivos
- **Fase 3: Council Engine (AI Swarm)**: Implementar el orquestador multi-agente y el consenso del 66%.
- **RuleLawyer**: Agente especializado en detectar ambigüedades en las reglas de resolución de mercados.

---

## [2026-02-12] - Cierre de Fase 3: Council Engine & Neural Consensus

### ✅ Hitos Completados
- **Orquestador LLM**: Migración completa de mockups a agentes reales (`LLMAgent`) usando OpenAI/OpenRouter.
- **Swarm Intelligence**: Implementados tres perfiles especializados:
    - **FedWatcher**: Análisis macro y política monetaria.
    - **RuleLawyer**: Verificación de ambigüedad en reglas de resolución.
    - **SentimentSwarm**: Análisis de narrativa y psicología de masas.
- **Detección de Bloqueo Regional**: El sistema ahora detecta y reporta errores de región de OpenAI, sugiriendo el uso de VPN o OpenRouter.
- **Frontend v3.0 Governance**:
    - **Consensus Feed**: Visualización en tiempo real del consenso del enjambre.
    - **Detailed Brief Modal**: Implementada la funcionalidad de "descomposición de consenso" que permite ver el razonamiento individual de cada agente.
    - **Neural Link Status**: Indicador de conectividad con los modelos de IA.

### 🛠️ Decisiones Técnicas
- **Formato de Salida Estricto**: Se forzó a los agentes a responder en formato `[Razonamiento] | [Score]` para permitir un parsing eficiente en el backend y visualización modular en el frontend.
- **Uso de GPT-4o-Mini**: Se optó por modelos "mini" para el enjambre para reducir latencia y costos, manteniendo la calidad del análisis para sentencias cortas.

### 🚀 Próximos Objetivos
- **Infraestructura de Billeteras (Wallet Manager)**: Crear el sistema de Proxy/Burner Wallets para permitir el uso multi-usuario de forma segura.
- **Bot de Telegram**: Implementar el puente de notificaciones y "1-tap trading" para las alertas de Smart Money.

---

## [2026-02-19] - Estabilización de Costos y Documentación Maestra

### ✅ Hitos Completados
- **Council Cache Implementation**: Se detectó una fuga masiva de tokens OpenAI (~800k tokens/5 min) debido a re-análisis infinitos de mercados rechazados.
- **Caché Inteligente (Dynamic TTL)**: Implementado `CouncilCache` que reutiliza scores de IA. Ahora un mercado solo se analiza una vez cada 45m-4h, recalculando el edge con el precio fresco (gratis).
- **Invalidación por Convergencia**: El caché se invalida automáticamente si entra una ráfaga nueva de ballenas (≥2 nuevas), forzando un re-análisis.
- **Presupuesto de Seguridad**: Agregado `COUNCIL_MAX_DAILY_CALLS` (300) para evitar colapsos financieros ante bugs de bucle.
- **Deduplicación de Supabase**: Actualizada la tabla `autonomous_logs` con `cache_hit` y migración ejecutada.
- **Limpieza de Documentación**: Reescritura total de `AGENTS.md` para evitar confusiones con proyectos de referencia (`HolyPoly`).

### 🛠️ Decisiones Técnicas
- **Score vs Precio**: Se separó la probabilidad fundamental (estática, Council) de la rentabilidad táctica (dinámica, CLOB Price). Esto permite operar 24/7 con costo de IA mínimo.
- **Escalado de TTL**: Se implementó un TTL dinámico que se acorta a medida que el mercado se acerca a su cierre, permitiendo un "Sniping" más preciso en la última hora.

### 🚀 Próximos Objetivos
- **Validación de ROI**: Monitorear las estadísticas del caché (`hit_rate`) y comparar contra el consumo de tokens real.
- **Refactorización de PnL**: Implementar cálculo de PnL neto en tiempo real en el Circuit Breaker.

---

## [2026-02-21] - Optimización de Sensibilidad y Periodo de Prueba

### ✅ Hitos Completados
- **Escalado de Smart Money**: Reducido el umbral de `ClusterDetector` de 3 a **2 billeteras** para capturar más señales de Sharks y Orcas.
- **Suavizado de Director**:
    - Ajustado el umbral de confianza para eventos <48h de 0.55 a **0.45**.
    - Reducido el **Edge mínimo** de 2% a **1%** para incentivar la toma de posiciones en fase de testeo.
    - Implementada tolerancia a mercados sin `end_date_iso` (Gamma fallback).
- **Estabilización de IA Gratis**: Configurado `gemini-2.0-flash-lite` vía OpenRouter para análisis rápidos y gratuitos.
- **Hotfix de Syntax**: Corregido `SyntaxWarning` en el regex de detección de fechas en `director.py`.
- **Corrección de Indexer**: Reparado `NameError: url` que impedía el funcionamiento del modo Discovery.
- **Hotfix de Configuración**: Añadida la variable `AUTONOMOUS_MIN_WALLETS` (default: 2) al modelo de Pydantic y al archivo `.env` para evitar errores de atributo.
- **Estabilización de Cerebro (AI)**: Migración a `google/gemini-2.0-flash-lite-001` tras detectar que el ID anterior era inválido. Verificación mediante script de depuración `debug_ai.py`.
- **Ajuste de Filtros**: Elevado el umbral de precio extremo de 0.99 a **0.995** y añadido filtro `active=true` en la API de Gamma para reducir el ruido.
- **Optimización de Discovery**: Ampliado el rango de incertidumbre a **0.01 - 0.99** en `indexer.py` para capturar más oportunidades en mercados con tendencia clara.
- **Visibilidad de Logs**: Desactivado el filtro restrictivo en `autonomous.log` para permitir una auditoría completa durante la fase de estabilización.

### 🛠️ Decisiones Técnicas
- **Raw f-strings**: Se adoptó el uso de `fr""` para evitar advertencias de secuencias de escape en expresiones regulares complejas.
- **Detección Dual**: Al bajar a 2 billeteras, se prioriza la velocidad de entrada sobre la confirmación masiva, confiando en el filtro posterior del Council AI.
- **Descubrimiento Activo**: Se priorizó el modo Discovery (top 20 mercados) sobre el escaneo masivo de ballenas para encontrar "Alpha" real en el rango de precio 0.1-0.9.

### 🚀 Próximos Objetivos
- **Evaluación de ROI (30 min)**: Primer control de calidad de las apuestas simuladas.
- **Ajuste de Council Cache**: Monitorear si la invalidación por ballenas nuevas funciona con el nuevo umbral de 2 billeteras.
- **Backlog: Builder Program**: Analizar la integración oficial tras confirmar rentabilidad del bot.

---

## [2026-02-21] - Phase 4: Alpha Expansion (Arbitrage & NoFolio)

### ✅ Hitos Completados

#### 🆕 Motor de Arbitraje (`app/engines/arbitrage/manager.py`)
Implementado desde cero. 280 líneas. Incluye:
- **`ArbOpportunity` dataclass:** Representa una oportunidad con tipo, coste total, payout garantizado y edge %.
- **`ArbManager.scan_all()`:** Orquesta los dos scanners y devuelve oportunidades ordenadas por edge (mayor primero).
- **`_scan_binary_markets()`:** Descarga 100 mercados activos vía Gamma API. Para cada uno obtiene el orderbook del YES y NO token. Si `YES_ask + NO_ask < ARB_MAX_SUM (0.985)`, crea una oportunidad.
- **`_scan_bundle_markets()`:** Descarga los 50 eventos más grandes. Para cada evento con ≥3 mercados comprueba si la suma de los asks de YES es < 0.985.
- **`execute(opp)`:** En modo SIMULATION registra la oportunidad sin ejecutar. En modo LIVE llama al `OrderManager` para cada outcome del bundle. Registra todo en Supabase.
- **Singleton `arb_manager`** exportado para uso en el loop.

#### 🎯 NoFolio Sentiment Engine (`app/engines/autonomous/director.py`)
Integrado dentro de `evaluate_and_execute()` después de la consulta al Council AI:
- **Condición:** `Council score < NOFOLIO_MAX_AI_SCORE (0.40)` + `precio YES en mercado > NOFOLIO_MIN_MARKET_PRICE (0.70)` = burbuja de optimismo detectada.
- **Acción:** Obtiene el NO token (index 1 en `clobTokenIds`), verifica que el ask del NO sea < $0.40, y redirige la ejecución hacia el NO con score = 0.90 y threshold = 0.60.
- Se preservan todas las salvaguardas existentes (circuit breaker, budget, daily limit).

#### ⚙️ Configuración (`app/core/config.py`)
7 nuevas variables añadidas en dos grupos:
```
# Arbitrage
ENABLE_ARBITRAGE, ARB_MAX_SUM, ARB_MIN_EDGE_PCT, ARB_MAX_BUDGET_PER_BUNDLE

# NoFolio
ENABLE_NOFOLIO, NOFOLIO_MAX_AI_SCORE, NOFOLIO_MIN_MARKET_PRICE
```

#### 🔁 Loop Principal (`run_autonomous_loop.py`)
- Import de `arb_manager` añadido al header.
- Nuevo **Step 4** (Arbitrage Engine) insertado entre Discovery Mode y Rewards Farming.
- Rewards renombrado a **Step 5** con indentación corregida.

### 🛠️ Decisiones Técnicas

- **Dos tipos de arbitraje separados:** Binary (intra-mercado) y Bundle (inter-mercado en eventos categóricos), porque el origen del dato es distinto (CLOB directamente vs Gamma Events API).
- **Deduplicación por 1 hora:** Evita re-ejecutar la misma oportunidad si el precio no ha cambiado significativamente entre ciclos.
- **`ARB_MIN_EDGE_PCT = 0.01`**: Margen mínimo del 1% después de fees. Polymarket cobra ~0.5% de taker, por lo que el edge neto real es ~0.5% mínimo.
- **NoFolio threshold conservador (YES > 0.70):** Se eligió un umbral alto para evitar falsos positivos en mercados legítimamente caros.
- **Ejecución atómica del bundle:** Si algún outcome no tiene liquidez (ask = None), se descarta el bundle completo para evitar una posición incompleta que no pague $1 fijo.

### 🐛 Problemas resueltos
- **Indentación del Rewards block:** Tras insertar el Step 4, el Step 3 (Rewards) quedó dentro del `else` accidentalmente. Corregido con replace limpio.
- **NoFolio usa `self.executor.client`:** Verificado que `CopyExecutor.__init__` asigna `self.client = PolyClient.get_instance()`, haciendo el acceso válido.
- **Stability Hotfix (DateTime Conflict):** Corregido error de resta entre datetimes `naive` y `aware` en `ClusterDetector` y `Director`. Normalización forzada a UTC tras `fromisoformat`.
- **Supabase Logging:** Todas las ejecuciones de arbitraje se guardan ahora en `autonomous_logs`.
- **Weather Exploit Engine (`app/engines/weather/manager.py`):**
  - Implementación de motor de arbitraje físico basado en NOAA (vía Open-Meteo).
  - Mapeo automático de ciudades a coordenadas GPS.
  - Extracción de umbrales de temperatura mediante Regex.
  - Ejemplo: Si Dallas ya está a 62°F y el mercado paga < 0.90 por el YES, el bot barre la liquidez.

### 🚀 Próximos Objetivos (Pendientes)
1. **Semantic Arbitrage (Fase 4.2):** Usar LLM para detectar mercados semánticamente equivalentes y explotar diferencias de precio.
2. **Event Tree Checker (Fase 4.3):** Detectar cuando `P(child) > P(parent)` en árboles de eventos (e.g., ganar la final sin ganar la semi).
3. **Fee-Aware Execution:** Integrar el cálculo exacto de fees de Polymarket en `edge_pct` al momento de ejecución.
4. **Real PnL Circuit Breaker:** Reemplazar el límite de gasto diario por un stop-loss sobre P&L realizado real.
5. **Backtesting del Arbitrageur:** Correr el scanner sobre datos históricos para cuantificar la frecuencia real de oportunidades.
