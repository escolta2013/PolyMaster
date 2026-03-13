**POLYMASTER**

Manual de Continuidad Operativa

*Guia Completa para Transferencia de Contexto a LLM*

Version 4.1.0 \| Febrero 26, 2026

**1. QUE ES POLYMASTER**

PolyMaster es una plataforma de trading algoritmico autonomo para
Polymarket, un mercado de prediccion descentralizado en Polygon
(blockchain) donde los usuarios apuestan sobre eventos del mundo real:
elecciones, deportes, precios de criptomonedas y cualquier evento
verificable.

**1.1 La Tesis Central**

El sistema opera bajo una hipotesis fundamental: los traders mas
rentables de Polymarket (llamados \'ballenas\' o \'whales\') tienen
acceso a informacion o analisis superiores al mercado promedio. Cuando
dos o mas de estas ballenas apuestan al mismo resultado del mismo
mercado, hay una senal de informacion valiosa que puede seguirse con
ventaja estadistica.

**1.2 El Ciclo Autonomo (cada 60 segundos)**

  --------------------------------------------------------------------------
  **Paso**   **Motor**           **Funcion**
  ---------- ------------------- -------------------------------------------
  1          SmartMoneyTracker   Escanea wallets de ballenas en busca de
                                 posiciones recientes

  2          ClusterDetector     Detecta mercados donde \>= 2 ballenas
                                 convergieron en las ultimas 12h

  3          DirectorAgent       Evalua clusters, aplica pre-filtros,
                                 consulta cache o Council AI

  4          CouncilCache        Cache inteligente con TTL dinamico para
                                 evitar llamadas redundantes a OpenAI

  5          Council AI          4 agentes LLM votan sobre el mercado (solo
                                 en cache MISS)

  6          Arbitrage Engine    Escanea 100 mercados buscando YES+NO \<
                                 \$0.985

  7          Rewards Grinder     Mantiene ordenes en rango de scoring para
                                 farming pasivo de USDC

  8          Weather Engine      Compara datos NOAA/Open-Meteo con mercados
                                 climaticos de Polymarket

  9          Supabase Logger     Registra EVERY decision en autonomous_logs
  --------------------------------------------------------------------------

**2. ARQUITECTURA DEL PROYECTO**

**2.1 Stack Tecnologico**

  ------------------------------------------------------------------------
  **Capa**        **Tecnologia**        **Proposito**
  --------------- --------------------- ----------------------------------
  Backend         FastAPI + Python 3.11 Motor de trading, APIs REST, loop
                                        autonomo

  Frontend        Next.js App Router    Dashboard de monitoreo
                                        (http://localhost:3000)

  Base de Datos   Supabase (PostgreSQL) Logs de decisiones, trades,
                                        wallets

  AI Council      OpenRouter / Gemini   Analisis de mercados por LLM
                  Flash Lite            

  Blockchain      Polygon + Gnosis CTF  Ejecucion real de trades en CLOB

  Datos           Polymarket Gamma      Precios y orderbooks en tiempo
                  API + CLOB API        real
  ------------------------------------------------------------------------

**2.2 Estructura de Archivos Criticos**

-   backend/run_autonomous_loop.py --- EL CEREBRO PRINCIPAL. Loop que
    orquesta todos los motores

-   backend/app/engines/tracker/tracker.py --- SmartMoneyTracker, filtra
    farmers vs snipers

-   backend/app/engines/tracker/cluster_detector.py --- Detecta
    convergencia de ballenas en actividad reciente

-   backend/app/engines/tracker/indexer.py --- Discovery Mode, busca
    mercados accionables

-   backend/app/engines/autonomous/director.py --- Director Agent, toma
    la decision final de ejecutar

-   backend/app/engines/council/orchestrator.py --- Orquesta los 4
    agentes AI del Council

-   backend/app/engines/council/cache.py --- CouncilCache con TTL
    dinamico

-   backend/app/engines/ghost/order_manager.py --- Ejecucion de ordenes
    en el CLOB

-   backend/app/engines/arbitrage/manager.py --- Motor de arbitraje
    binario y bundle

-   backend/app/engines/weather/manager.py --- Motor de explotacion de
    mercados climaticos

-   backend/app/core/config.py --- Todas las variables de configuracion
    (Pydantic Settings)

-   backend/.env --- SECRETOS. Nunca commitear. Contiene API keys reales

**2.3 Tablas de Supabase**

  ------------------------------------------------------------------------------------------------
  **Tabla**             **Contenido**          **Campos Clave**
  --------------------- ---------------------- ---------------------------------------------------
  autonomous_logs       Cada decision del      decision
                        Director               (WOULD_EXECUTE/PAPER_REJECTED/EXECUTED/REJECTED),
                                               council_score, edge_net, spread, reasoning (JSON
                                               con scores por agente), cache_hit, detected_at

  wallets               Wallets de Smart Money address, grade (WHALE/SHARK/ORCA), is_smart_money
                        trackeadas             

  cluster_alerts        Eventos de             market_id, whale_count, confidence
                        convergencia           
                        detectados             

  copy_trades           Trades ejecutados      token_id, outcome, size, price, timestamp,
                                               simulated

  council_performance   Predicciones           Para backtesting de accuracy
                        individuales por       
                        agente                 
  ------------------------------------------------------------------------------------------------

**3. EL COUNCIL AI - CORAZON DEL SISTEMA**

El Council AI es el mecanismo de decision mas critico del sistema.
Fueron necesarios varios dias de trabajo para corregir sus sesgos y
hacerlo funcionar correctamente.

**3.1 Los 4 Agentes**

  -------------------------------------------------------------------------
  **Agente**       **Rol**                            **Profundidad**
  ---------------- ---------------------------------- ---------------------
  FedWatcher       Analisis macroeconomico, politica  Media
                   monetaria, tasas base              

  RuleLawyer       Reglas de resolucion,              Media
                   ambiguedades, oracle UMA, gotchas  
                   legales                            

  SentimentSwarm   Hype social, narrativas,           Baja
                   psicologia de masas                

  RiskArbiter      Mediador, penaliza euforia,        Alta
                   pondera conflictos entre agentes   
  -------------------------------------------------------------------------

**3.2 Flujo de Consenso**

-   PASS 1: FedWatcher, RuleLawyer, SentimentSwarm analizan en paralelo
    (3 llamadas OpenAI)

-   PASS 2: RiskArbiter media basado en el regimen de conflicto:

    -   Cohesion (sigma \< 0.12): peso del arbiter = 10%

    -   Divergencia (0.12 \<= sigma \< 0.25): peso del arbiter = 40%

    -   Fragmentacion (sigma \>= 0.25): peso del arbiter = 60%

-   FINAL: weighted_score = specialist_avg x (1 - weight) +
    arbiter_score x weight

**3.3 CORRECCION CRITICA: Anchoring Bias**

+-----------------------------------------------------------------------+
| **🚨 BUG CRITICO CORREGIDO**                                          |
|                                                                       |
| Los agentes originalmente recibían el precio de mercado actual        |
| (Current YES Price) en su prompt, lo que causaba que todos            |
| devolvieran scores idénticos cercanos al precio (ej: precio=0.55,     |
| scores=0.60 todos). Esto se llama Anchoring Bias y eliminaba          |
| completamente la ventaja del análisis independiente.                  |
+-----------------------------------------------------------------------+

La correccion implementada en orchestrator.py incluye tres cambios:

-   Bloque CRITICAL INSTRUCTION - AVOID ANCHORING BIAS en cada prompt

-   Los agentes ya NO reciben el precio actual. Deben estimar
    probabilidad desde primeros principios

-   Formato de respuesta cambiado de FinalConfidence: 0.60 a
    FinalConfidenceRange: 0.45-0.65

-   El score del agente = punto medio del rango (Expected Value)

-   Temperatura del modelo subida de 0.3 a 0.7 para incentivar
    divergencia real

Resultado despues del fix: dispersión genuina entre agentes (ejemplo
real):

> FedWatcher: 0.675 \| RuleLawyer: 0.500 \| SentimentSwarm: 0.575 \|
> RiskArbiter: 0.525
>
> Consenso Final: 0.578 \| vs. Score anterior sesgado: 0.600 (todos
> identicos)

**3.4 CouncilCache - Optimizacion de Costos**

-   TTL dinamico que se acorta a medida que el mercado se acerca a su
    cierre (15min - 4h)

-   Se invalida si entran \>= 2 ballenas nuevas al mercado

-   Presupuesto de seguridad: COUNCIL_MAX_DAILY_CALLS = 300

-   Hit Rate observado en produccion: \~97% (solo 69 llamadas reales en
    15 horas)

-   Ahorro estimado: \$63.78 USD en tokens en un solo dia de operacion

**4. DISCOVERY MODE - FUENTE DE MERCADOS**

El Discovery Mode es el sistema que alimenta al Director con mercados
para analizar cuando no hay señales de ballenas activas. Fue necesario
un diagnostico profundo para hacerlo funcionar.

**4.1 El Bug Critico del Indexer (RESUELTO)**

+-----------------------------------------------------------------------+
| **⚠️ BUG RESUELTO - Contexto Historico Importante**                   |
|                                                                       |
| El sistema original pedía 200 mercados a la API de Gamma sin          |
| especificar closed=false. La API devolvía 197 mercados                |
| cerrados/archivados y solo 3 activos. El bot operaba en un \'desierto |
| de datos\'. Solución: añadir closed=false y aumentar limit a 500.     |
+-----------------------------------------------------------------------+

**4.2 Arquitectura de Filtrado Triple (CLOB Spot-Check)**

El Indexer ahora opera con un sistema de filtrado en dos etapas antes de
pasar mercados al Director:

  ---------------------------------------------------------------------------
  **Etapa**     **Fuente**       **Filtros Aplicados**      **Resultado
                                                            Tipico**
  ------------- ---------------- -------------------------- -----------------
  Etapa 1       Gamma API        500 mercados mas nuevos,   3-20 candidatos
  (Grueso)                       Volumen \> \$3,000, Edad   
                                 \< 72h                     

  Etapa 2       CLOB Real-time   Precio CLOB 0.35-0.65,     0-5 accionables
  (Fino)                         Spread \< 0.15,            
                                 Profundidad \> \$10        

  Etapa 3       CLOB (datos      Edge Neto \>= 0.05         0-2 WOULD_EXECUTE
  (Director)    pre-validados)   (post-spread)              
  ---------------------------------------------------------------------------

**4.3 Hallazgo: Lag de Gamma API**

La API de Gamma tiene un lag de horas o incluso dias en los precios de
metadata. Un mercado que Gamma reporta con precio 0.50 puede tener un
best_ask de 0.999 en el CLOB real. El Director siempre usa datos del
CLOB real, nunca los precios de Gamma como fuente de verdad.

**4.4 Bug de Doble Llamada al CLOB (RESUELTO)**

+-----------------------------------------------------------------------+
| **⚠️ BUG RESUELTO - Liquidity Trap Fantasma**                         |
|                                                                       |
| El Indexer verificaba el spread via CLOB (resultado: 0.03, OK). Luego |
| el loop descartaba esos datos y el Director volvía a consultar el     |
| CLOB. Si esa segunda llamada fallaba (timeout/502), devolvía          |
| spread=1.0 por defecto, activando falsamente la protección de         |
| \'LIQUIDITY TRAP\'. Fix: el loop ahora pasa clob_best_ask,            |
| clob_best_bid y clob_spread directamente en el discovery_alert al     |
| Director. El Director usa los datos pre-validados y omite la segunda  |
| llamada.                                                              |
+-----------------------------------------------------------------------+

**4.5 Configuracion Actual del Indexer**

-   Modo primario: Mercados mas recientes (sort=createdAt) con Volumen
    \> \$3,000 y Edad \< 72h

-   Spread maximo en Paper Mode: 0.25 (relajado para calibracion)

-   Spread maximo en Produccion: 0.15

-   Precio CLOB aceptable: 0.35 - 0.65 (Discovery) \| 0.25 - 0.75 (Whale
    Tracker)

-   Semaphore de 30 conexiones paralelas para el spot-check del CLOB

**5. FORMULA DEL EDGE NETO - LA DECISION FINANCIERA**

Esta formula es el filtro financiero final que determina si el Director
ejecuta un trade. Fue implementada despues de entender que el edge bruto
(score - precio) no refleja el costo real de entrar al mercado.

**Edge Neto = Score del Council - best_ask - (spread × 0.5)**

  ------------------------------------------------------------------------
  **Variable**    **Definicion**                 **Ejemplo**
  --------------- ------------------------------ -------------------------
  Score del       Probabilidad estimada por el   0.63
  Council         AI Council                     
                  (post-antianchoring)           

  best_ask        Precio al que se puede comprar 0.48
                  en el CLOB ahora mismo         

  spread          best_ask - best_bid (costo de  0.12
                  cruzar el mercado)             

  spread x 0.5    Penalizacion por slippage      0.06
                  (mitad del spread)             

  Edge Bruto      Score - best_ask (sin          +0.15
                  considerar spread)             

  Edge Neto       Edge real despues del costo de +0.09
                  liquidez                       
  ------------------------------------------------------------------------

-   Umbral de ejecucion en Paper Mode: Edge Neto \>= 0.05

-   Umbral de ejecucion en Produccion: Edge Neto \>= 0.07 (recomendado
    segun datos de calibracion)

-   Si Edge Neto \< umbral: decision = PAPER_REJECTED (no se llama al
    Council, no hay costo)

**6. PAPER TRADING MODE - ESTADO ACTUAL**

El sistema se encuentra actualmente en Paper Trading Mode, recolectando
datos de calibracion del Council AI antes de activar trading real con
dinero.

**6.1 Como Funciona**

-   PAPER_TRADING_MODE=true en .env activa el modo de calibracion

-   WOULD_EXECUTE: El bot detecto un trade valido pero NO lo ejecuto. Se
    registra en Supabase

-   PAPER_REJECTED: El bot descarto el mercado por edge neto negativo o
    spread excesivo

-   Deduplication Guard: Si el mismo mercado ya fue registrado en el
    ciclo anterior con precio similar, no se vuelve a registrar

**6.2 Resultados de Calibracion (48 horas, 26 Feb 2026)**

  -----------------------------------------------------------------------
  **Metrica**              **Valor**          **Interpretacion**
  ------------------------ ------------------ ---------------------------
  Mercados unicos          75+                Muestra real de trabajo del
  analizados                                  sistema

  Mercados resueltos       66                 Precio final \> 0.97 o \<
  definitivamente                             0.03 (metodologia correcta)

  Accuracy general         54.5% (36W / 30L)  Por debajo del objetivo de
  (WOULD_EXECUTE)                             60%

  Accuracy                 63-84%             Categoria mas fuerte del
  Sports/Baloncesto                           sistema

  Accuracy eSports/Tenis   Variable (33-100%) Inconsistente, categoria
                                              con menos contexto LLM

  EV Real por dolar        +0.267             Positivo pero con intervalo
  apostado                                    de confianza amplio

  ROI Simulado             +9.35%             Rentable pero con margen
                                              estrecho

  Cache Hit Rate           \~97%              Extremadamente eficiente

  Llamadas reales al       69/300 en 15h      Presupuesto de IA bajo
  Council                                     control

  Ahorro en tokens         \~\$63.78 USD/dia  Impacto del sistema de
                                              cache
  -----------------------------------------------------------------------

**6.3 Correlacion Edge Neto vs Accuracy (HALLAZGO CLAVE)**

  -------------------------------------------------------------------------
  **Bucket de Edge       **Wins**    **Losses**   **Accuracy**
  Neto**                                          
  ---------------------- ----------- ------------ -------------------------
  0.03 - 0.07 (Bajo)     8           4            66.7%

  0.07 - 0.12 (Medio)    3           1            75.0%

  \> 0.12 (Alto)         1           0            100% (n=1, insuficiente)
  -------------------------------------------------------------------------

Esta correlacion es la señal mas valiosa de los datos actuales: a mayor
Edge Neto detectado, mayor accuracy real. Esto sugiere que el sistema
está capturando ineficiencias reales y no ruido aleatorio.

**6.4 Metodologia Correcta de Medicion de ROI**

+-----------------------------------------------------------------------+
| **📊 METODOLOGIA CRITICA**                                            |
|                                                                       |
| Solo se consideran mercados con precio final \> 0.97 (resuelto YES) o |
| \< 0.03 (resuelto NO). Los mercados con precios intermedios (en       |
| movimiento pero no resueltos) NO se incluyen en el calculo de         |
| accuracy. Comparar precio de entrada vs precio actual intraday NO es  |
| ROI - es movimiento de precio sin realizacion.                        |
+-----------------------------------------------------------------------+

**7. VARIABLES DE CONFIGURACION CRITICAS (.env)**

  ----------------------------------------------------------------------------------------------------
  **Variable**                      **Valor Actual**                   **Descripcion**
  --------------------------------- ---------------------------------- -------------------------------
  PAPER_TRADING_MODE                true                               Master switch del modo
                                                                       calibracion. false = trading
                                                                       real

  PAPER_TRADING_MAX_SPREAD          0.15                               Spread maximo en paper mode
                                                                       (fue 0.25, bajado para ser mas
                                                                       realista)

  PAPER_MIN_EDGE_NET                0.05                               Edge neto minimo para
                                                                       WOULD_EXECUTE (recomendado
                                                                       subir a 0.07)

  AUTONOMOUS_CONFIDENCE_THRESHOLD   0.68                               Score minimo del Council para
                                                                       ejecutar en modo real

  COUNCIL_MAX_DAILY_CALLS           300                                Presupuesto diario de llamadas
                                                                       al AI Council

  COPY_SIMULATION                   true                               Simula los trades, no envia
                                                                       ordenes reales al CLOB

  AUTONOMOUS_MAX_SIZE               50.0                               Maximo USDC por trade

  COPY_MAX_DAILY                    200.0                              Presupuesto diario total en
                                                                       USDC

  GLOBAL_STOP_LOSS_PCT              0.60                               Stop-loss de emergencia (60% de
                                                                       perdida diaria)

  ENABLE_AUTONOMOUS_TRADING         true                               Switch maestro del trading
                                                                       autonomo

  AUTONOMOUS_MIN_WALLETS            2                                  Minimo de ballenas para
                                                                       disparar un cluster alert

  ENABLE_ARBITRAGE                  true                               Activa el Arbitrage Engine

  ARB_MAX_SUM                       0.985                              Umbral de arbitraje binario
                                                                       (YES+NO \< 0.985)

  ENABLE_NOFOLIO                    true                               Motor de sentimiento contrario
                                                                       (NO en mercados hype)

  ENABLE_WEATHER_EXP                true                               Motor de explotacion de
                                                                       mercados climaticos

  AI_MODEL                          google/gemini-2.0-flash-lite-001   Modelo LLM usado para el
                                                                       Council (via OpenRouter)
  ----------------------------------------------------------------------------------------------------

**8. QUE ESTA PENDIENTE**

**8.1 Prioridad Alta - Antes de Live Trading**

-   **\[INMEDIATO\]** Acumular 150 mercados resueltos definitivamente
    con los filtros estrictos actuales (Spread \< 0.15, Edge \>= 0.05)
    para tener significancia estadistica real. Con n=150 y accuracy de
    58%, p \< 0.05 es alcanzable.

-   **\[INMEDIATO\]** Subir PAPER_MIN_EDGE_NET de 0.05 a 0.07. Los datos
    de calibracion muestran que el bucket de Edge \> 0.07 tiene mejor
    accuracy. Este cambio tiene respaldo empirico directo.

-   **\[INMEDIATO\]** Excluir categorias de eSports del pipeline de
    WOULD_EXECUTE. La accuracy en eSports es inconsistente (33-100% en
    distintas muestras), indicando que el Council AI no tiene suficiente
    contexto informacional en ese dominio.

-   **\[ANTES DE LIVE\]** Verificar el error esporadico \'str object has
    no attribute items\' que aparecio 2 veces en los primeros logs. En
    produccion real ese bug podria dejar una orden abierta sin stop
    loss.

**8.2 Prioridad Media - Mejoras del Sistema**

-   **\[MEJORA\]** VPIN (Volume-Synchronized Probability of Informed
    Trading) como kill switch para el Grinder. Detecta flujo toxico en
    tiempo real. Implementar cuando el Grinder tenga ordenes activas en
    produccion.

-   **\[MEJORA\]** Staged withdrawal near resolution: Retirar ordenes
    del Grinder progresivamente en las ultimas 2-4 horas antes del
    cierre de un mercado. El adverse selection cerca de resolucion es
    extremo.

-   **\[MEJORA\]** Filtro de toxicidad pre-arbitraje: Verificar
    imbalance de order flow antes de entrar a una oportunidad de
    arbitraje. El 73% de las ganancias de arbitraje van a bots
    sub-100ms.

-   **\[MEJORA\]** Real PnL Tracking: Mover el Circuit Breaker de
    \'gasto diario\' a \'perdida realizada neta\'. Actualmente solo mide
    cuanto se ha gastado, no si se ha ganado o perdido.

**8.3 Prioridad Baja - Expansion Futura**

-   **\[FUTURO\]** Semantic Arbitrage: Usar LLM para detectar mercados
    semanticamente equivalentes con precios diferentes (ej: \'Trump
    gana\' vs \'Republicanos ganan\' con 2-4% de diferencia).

-   **\[FUTURO\]** Event Tree Checker: Detectar cuando P(hijo) \>
    P(padre) en arboles de eventos logicamente dependientes.

-   **\[FUTURO\]** Fee-Aware Execution: Integrar el calculo exacto de
    fees de Polymarket (\~0.5% taker) en el calculo de Edge Neto al
    momento de ejecucion.

-   **\[FUTURO\]** Multi-User SaaS: Expansion de single-user a
    multi-tenancy. CRITICO: Nunca almacenar private keys de usuarios en
    el servidor. Cada usuario debe firmar localmente.

-   **\[FUTURO\]** polymarket-cli integration: El CLI oficial de
    Polymarket en Rust (lanzado Feb 24, 2026) ofrece batch queries
    eficientes para CLOB. Evaluar como alternativa al SDK Python para el
    spot-check del Indexer cuando sea mas maduro.

**9. IMPLEMENTACIONES PENDIENTES DEL ARTICULO DE X**

El 26 de febrero de 2026 se analizo un articulo tecnico de X (Twitter)
sobre como Jump Trading, Jane Street y traders institucionales operan en
Polymarket. El articulo describe frameworks matematicos avanzados
(Avellaneda-Stoikov, Glosten-Milgrom, GLFT, VPIN) que los market makers
institucionales usan. Se identificaron tres implementaciones concretas
para PolyMaster, con la condicion de implementarlas DESPUES de que el
sistema base funcione correctamente en produccion.

+-----------------------------------------------------------------------+
| **⏰ CONDICION DE ACTIVACION**                                        |
|                                                                       |
| Estas mejoras NO deben implementarse hasta que el sistema tenga al    |
| menos 150 trades resueltos en paper mode con accuracy \> 60% y haya   |
| ejecutado sus primeros trades reales con micro-posiciones (\$1-\$5)   |
| con resultados positivos.                                             |
+-----------------------------------------------------------------------+

**9.1 VPIN - Kill Switch para el Grinder**

  -----------------------------------------------------------------------
  **Aspecto**        **Detalle**
  ------------------ ----------------------------------------------------
  Que es             Volume-Synchronized Probability of Informed Trading.
                     Mide el porcentaje de flujo \'toxico\' (de traders
                     con informacion privilegiada) en tiempo real.

  Por que importa    Cuando insiders entran al mercado, el imbalance
                     entre buy/sell volume se dispara. Un market maker
                     (el Grinder) con ordenes pasivas en el libro sera
                     adversely selected - llenara posiciones perdedoras
                     porque los insiders saben el resultado.

  Formula            VPIN = \|BuyVolume - SellVolume\| / TotalVolume en
                     cada bucket de volumen. Si VPIN \> 0.7, flujo
                     altamente toxico.

  Implementacion     Monitorear imbalance de order flow del CLOB en cada
                     ciclo. Si VPIN sube abruptamente para un mercado
                     donde el Grinder tiene ordenes, ejecutar cancelAll()
                     para ese mercado especifico.

  Cuando implementar Cuando el Grinder tenga ordenes activas en
                     produccion real. Sin posiciones abiertas, VPIN no
                     tiene nada que proteger.

  Archivo a          backend/app/engines/rewards/grinder.py + nuevo
  modificar          modulo vpin_monitor.py
  -----------------------------------------------------------------------

**9.2 Staged Withdrawal Near Resolution**

  -----------------------------------------------------------------------
  **Aspecto**        **Detalle**
  ------------------ ----------------------------------------------------
  Que es             Retiro progresivo de ordenes del libro de ordenes a
                     medida que un mercado se acerca a su fecha de
                     resolucion.

  Por que importa    Cerca de la resolucion, el modelo de Glosten-Milgrom
                     muestra que el costo de adverse selection domina
                     cualquier otro factor. Los insiders (que conocen el
                     resultado) empiezan a barrer el libro. Un market
                     maker con ordenes a \$0.95/\$0.97 cuando alguien
                     sabe que el resultado es YES enfrenta perdidas
                     catastroficas.

  Logica             4h antes del cierre: reducir tamaño de ordenes al
                     50%. 2h antes: reducir al 25%. 30min antes: cancelar
                     todas las ordenes del Grinder para ese mercado.

  Cuando implementar Cuando el sistema tenga posiciones abiertas que se
                     acerquen a resolucion. Requiere que el Director
                     lleve registro de end_date de cada posicion activa.

  Archivo a          backend/app/engines/autonomous/director.py +
  modificar          backend/app/engines/rewards/grinder.py
  -----------------------------------------------------------------------

**9.3 Filtro de Toxicidad Pre-Arbitraje**

  -----------------------------------------------------------------------
  **Aspecto**        **Detalle**
  ------------------ ----------------------------------------------------
  Que es             Verificar el imbalance de order flow de un mercado
                     ANTES de entrar a una oportunidad de arbitraje.

  Por que importa    Las ventanas de arbitraje se comprimieron de 12.3s
                     (2024) a 2.7s (Q1 2026). El 73% de las ganancias las
                     capturan bots sub-100ms. Si el Arbitrage Engine
                     detecta una oportunidad en su ciclo de 60s,
                     probablemente llega tarde y lo que \'parece\'
                     arbitraje es en realidad una posicion que alguien
                     con informacion ya cerro, dejando al sistema como la
                     contraparte perdedora.

  Formula            Calcular \|BuyFlow - SellFlow\| / TotalFlow en los
                     ultimos 5 minutos de actividad del mercado. Si
                     imbalance \> 0.6, saltar la oportunidad de
                     arbitraje.

  Cuando implementar Cuando el Arbitrage Engine empiece a encontrar
                     oportunidades reales de forma consistente.
                     Actualmente el mercado se reporta como eficiente en
                     la mayoria de ciclos.

  Archivo a          backend/app/engines/arbitrage/manager.py
  modificar          
  -----------------------------------------------------------------------

**9.4 Contexto Adicional: El Articulo de X**

El articulo describe como los market makers institucionales (Jump
Trading, Jane Street, DRW, Susquehanna) han entrado masivamente a
Polymarket en 2025-2026. Los datos clave del articulo:

-   Polymarket proceso mas de \$9 billion en volumen en 2024 (desde
    \$73M en 2023, un aumento de 120x)

-   Bots representando solo el 3.7% de las direcciones generan el 37.4%
    del volumen total

-   El 0.04% de las direcciones capturo el 71% de todas las ganancias
    realizadas

-   Jump Trading tomo participacion accionaria en Polymarket a cambio de
    proveer liquidez

-   Un bot anonimo (@defiance_cr) que inicio con \$10K llego a ganar
    \$700-800/dia antes de que la competencia institucional lo hiciera
    no rentable

La conclusion del articulo es que el edge restante pertenece a
participantes que pueden hacer tres cosas simultaneamente: (1) pricear
eventos mas exactamente que el mercado con modelos probabilisticos
superiores, (2) gestionar el riesgo unico de outcomes binarios, y (3)
ejecutar a calidad institucional (sub-10ms, kill switches robustos).
PolyMaster compite en el frente (1) con su Council AI, y tiene
implementados elementos de (3). El frente (2) es donde VPIN y staged
withdrawal son esenciales.

**10. COMANDOS DE OPERACION**

**10.1 Iniciar el Sistema**

  --------------------------------------------------------------------------
  **Servicio**    **Comando**                        **URL**
  --------------- ---------------------------------- -----------------------
  Backend API     cd backend &&                      http://127.0.0.1:8000
                  .venv\\Scripts\\activate &&        
                  uvicorn main:app \--reload         

  Frontend        cd frontend && npm run dev         http://localhost:3000
  Dashboard                                          

  Loop Autonomo   cd backend &&                      Ver logs en consola
                  .venv\\Scripts\\activate && python 
                  run_autonomous_loop.py             
  --------------------------------------------------------------------------

**10.2 Monitoreo de Salud**

-   Verificar que cada ciclo complete en \< 60 segundos (ahora \~40-50s
    con los filtros actuales)

-   Revisar autonomous_logs en Supabase: debe haber entradas de
    WOULD_EXECUTE y PAPER_REJECTED

-   Cache hit rate debe mantenerse \> 90%

-   Uso de presupuesto del Council debe ser \< 50 llamadas en las
    primeras 3 horas

-   Buscar en logs el patron \'Liquidity Trap\' - si aparece con spread
    \< 0.3, hay regresion del bug

**10.3 Como Verificar Accuracy de Paper Trades**

Script: evaluate_sim_profit.py

-   Filtra solo mercados con precio final \> 0.97 o \< 0.03 (resueltos
    definitivamente)

-   Compara decision del bot (WOULD_EXECUTE) contra resultado real

-   Separa por bucket de Edge Neto y por categoria de mercado

-   Nunca incluir mercados \'en vuelo\' (precio intermedio) en el
    calculo de accuracy

**10.4 Como Activar Trading Real**

+-----------------------------------------------------------------------+
| **🔴 LISTA DE VERIFICACION OBLIGATORIA ANTES DE LIVE**                |
|                                                                       |
| 1\) Minimo 150 mercados resueltos con accuracy \> 60% en filtros      |
| estrictos. 2) Error \'str object has no attribute items\' corregido y |
| verificado. 3) PAPER_TRADING_MAX_SPREAD bajado a 0.15 y datos con esa |
| configuracion. 4) Revisar PRODUCTION_CHECKLIST.md en el repositorio.  |
| 5) Empezar con micro-posiciones de \$1-\$5 por trade durante al menos |
| 1 semana antes de escalar.                                            |
+-----------------------------------------------------------------------+

Para activar: cambiar en .env:

> PAPER_TRADING_MODE=false
>
> COPY_SIMULATION=true (mantener en true hasta verificar el CLOB con
> micro-trades)

**11. ALERTAS DE SEGURIDAD CRITICAS**

+-----------------------------------------------------------------------+
| **🚨 PRIVATE KEYS - RIESGO MAXIMO**                                   |
|                                                                       |
| El archivo backend/.env contiene credenciales REALES de Polymarket y  |
| una API key real de OpenAI/OpenRouter. NUNCA commitear este archivo.  |
| NUNCA logear su contenido. NUNCA exponerlo en ninguna interfaz.       |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
| **🚨 ALMACENAMIENTO DE KEYS DE USUARIOS**                             |
|                                                                       |
| Si el proyecto escala a multi-usuario (SaaS), JAMAS almacenar las     |
| private keys de los usuarios en el servidor. Bots como Polygun y      |
| Polycule fueron hackeados exactamente por este error, drenando los    |
| fondos de todos sus usuarios simultaneamente. Cada usuario debe       |
| firmar transacciones localmente; el servidor nunca debe tocar las     |
| keys.                                                                 |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
| **⚠️ PROYECTO HOLYPOLY**                                              |
|                                                                       |
| Existe una carpeta llamada HolyPoly/ en el directorio padre de        |
| polymaster/. Es un proyecto de REFERENCIA SOLAMENTE. NO leer, NO      |
| modificar, NO referenciar ese codigo en PolyMaster bajo ninguna       |
| circunstancia.                                                        |
+-----------------------------------------------------------------------+

**12. LOG DE DECISIONES ARQUITECTONICAS**

Este registro captura las decisiones mas importantes tomadas durante el
desarrollo, con su razonamiento, para que un agente nuevo entienda POR
QUE el sistema es como es.

  -----------------------------------------------------------------------
  **Decision**       **Razonamiento**               **Alternativa
                                                    Descartada**
  ------------------ ------------------------------ ---------------------
  Whale-first como   Un trade reciente de una       Indexer-first:
  fuente primaria de ballena es una senal           buscaba mercados
  discovery          informacional activa. Buscar   genericos sin señal
                     primero mercados con actividad de informacion
                     de ballenas y usar el Indexer  privilegiada
                     solo como red de seguridad     
                     maximiza la calidad de la      
                     senal.                         

  Separar score del  El score del Council es una    Re-llamar al Council
  Council vs precio  estimacion de probabilidad     en cada ciclo: costo
  del CLOB           fundamental (estatica). El     de tokens prohibitivo
                     precio del CLOB es precio      (\~800k tokens/5min
                     tactico (dinamico). El edge se sin cache)
                     calcula en cada ciclo con      
                     precio fresco sin re-llamar al 
                     Council.                       

  TTL dinamico en    Un mercado que cierra en 1h    TTL fijo: demasiado
  CouncilCache       necesita re-analisis mas       rigido, no captura la
                     frecuente que uno que cierra   urgencia de mercados
                     en 48h. El TTL escala con el   proximos a cierre
                     horizonte temporal del         
                     mercado.                       

  Anti-anchoring     Los LLMs tienden a anclar sus  Prompts con precio
  bias en prompts    estimaciones al precio de      visible: generaban
  del Council        mercado mostrado en el prompt, scores identicos
                     eliminando su valor como       (todos 0.60), sin
                     analista independiente. La     valor analitico real
                     correccion mejoro la           
                     dispersion de scores de 0.00 a 
                     \>0.10.                        

  Edge Neto con      El edge bruto (score - precio) Edge bruto sin
  penalizacion por   no refleja el costo real de    ajuste: aprobaria
  spread             cruzar el spread. Un edge      trades donde el
                     bruto de 5% con spread de 10%  spread devora toda la
                     es un trade perdedor en        ventaja
                     esperanza matematica.          

  Excluir eSports    La accuracy en eSports es      Incluir eSports:
  del pipeline       inconsistente (33-100% en      contamina las
                     distintas muestras) porque los metricas generales
                     LLMs tienen menos contexto     con trades de calidad
                     informacional sobre torneos    impredecible
                     especificos. La volatilidad    
                     del accuracy indica ruido, no  
                     señal.                         

  Datos CLOB         El Indexer ya consulto el CLOB Segunda consulta
  pre-validados del  con exito. Hacer una segunda   independiente en el
  Indexer al         llamada en el Director duplica Director: causaba el
  Director           la carga sobre una API         bug de Liquidity Trap
                     inestable (muchos              Fantasma
                     timeouts/502). La segunda      
                     llamada fallaba y activaba     
                     falsamente la Liquidity Trap.  
  -----------------------------------------------------------------------

**13. RESUMEN DEL ESTADO ACTUAL (26 FEB 2026)**

  -----------------------------------------------------------------------
  **Componente**     **Estado**       **Notas**
  ------------------ ---------------- -----------------------------------
  Loop Autonomo      ✅ ACTIVO Y      Ciclos de \~40-50s, sin crashes en
                     ESTABLE          15+ horas

  Indexer /          ✅ FUNCIONAL     376 candidatos por ciclo, filtro
  Discovery Mode                      triple CLOB activo

  Whale Tracker      ✅ FUNCIONAL     Escanea actividad de ultimas 12h,
                                      es fuente primaria

  Council AI         ✅ CORREGIDO     Anti-anchoring bias activo,
                                      dispersion real entre agentes

  CouncilCache       ✅ OPTIMO        97% hit rate, 69/300 llamadas
                                      usadas en 15h

  Director Agent     ✅ FUNCIONAL     Edge Neto \>= 0.05, usa datos CLOB
                                      pre-validados

  Paper Trading Mode ✅ ACTIVO        WOULD_EXECUTE y PAPER_REJECTED en
                                      Supabase

  Arbitrage Engine   🟡 ACTIVO SIN    Mercado eficiente actualmente
                     OPORTUNIDADES    

  Rewards Grinder    🟡 ACTIVO        Sin implementar VPIN todavia
                                      (pendiente)

  Weather Engine     🟡 ACTIVO        Operando en background

  Live Trading       🔴 DESACTIVADO   COPY_SIMULATION=true, esperando 150
                                      trades calibrados

  VPIN / Staged      ⏳ PENDIENTE     A implementar despues de primeros
  Withdrawal                          trades reales
  -----------------------------------------------------------------------

**14. PROXIMOS PASOS EN ORDEN DE PRIORIDAD**

1.  Acumular 150 mercados resueltos definitivamente con filtros
    estrictos (Spread \< 0.15, Edge \>= 0.05, excluyendo eSports). Plazo
    estimado: 3-5 dias adicionales de paper trading.

2.  Subir PAPER_MIN_EDGE_NET de 0.05 a 0.07 en .env. Cambio de una linea
    con respaldo empirico directo en los datos de calibracion.

3.  Verificar y corregir el error \'str object has no attribute items\'
    antes de activar live trading. Revisar los primeros logs del sistema
    para encontrar el stack trace completo.

4.  Con 150 trades calibrados y accuracy \> 60%, activar
    micro-posiciones live de \$1-\$5 por trade. Mantener
    COPY_SIMULATION=false pero con AUTONOMOUS_MAX_SIZE=5.0 durante 1
    semana.

5.  Cuando el Grinder tenga ordenes activas en produccion: implementar
    VPIN como kill switch (ver Seccion 9.1).

6.  Cuando haya posiciones abiertas proximas a resolucion: implementar
    staged withdrawal (ver Seccion 9.2).

7.  Cuando el Arbitrage Engine encuentre oportunidades consistentes:
    implementar filtro de toxicidad pre-arbitraje (ver Seccion 9.3).

*PolyMaster \| Manual de Continuidad Operativa \| Version 4.1.0 \| 26
Feb 2026*

*Este documento fue generado automaticamente como transferencia de
contexto entre sesiones de desarrollo.*
