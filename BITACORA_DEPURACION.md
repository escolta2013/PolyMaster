# Bitácora de Depuración y Cambios (Producción)

Este documento registra los cambios realizados al bot durante su ejecución local en modo producción (Live Trading), para rastrear qué se alteró y qué efecto tuvo en el sistema.

---

### Fecha: 13 de Abril de 2026 (Sesión Local de Depuración)

**1. Relajación de Filtros del Motor de Descubrimiento (Indexer)**
- **Archivo modificado:** `backend/app/engines/tracker/indexer.py`
- **Cambios realizados:** 
  - `age_limit` pasó de `72 horas` a `None` (Sin límite de edad).
  - `min_volume` pasó de `$3000` a `$100`.
  - Filtros de precio (`min_p`, `max_p`) pasaron a `0.15` - `0.85`.
- **Razón:** El bot estaba descartando los 500 mercados obtenidos de la API antes de analizarlos. Se necesitan mercados candidatos para probar el flujo completo.
- **Efecto esperado:** Deberíamos ver mercados "Actionables" en el siguiente ciclo.

**2. Ajuste de Presupuesto (Micro-Testing)**
- **Archivo modificado:** `backend/.env`
- **Cambios realizados:**
  - `AUTONOMOUS_MAX_SIZE` reducido temporalmente de `50.0` a `1.5`.
- **Razón:** El usuario reportó que la wallet real solo tiene un balance de **$5 USD** para pruebas iniciales. Una orden por defecto de $50 causaría de inmediato un error en la cadena de bloques por "Fondos insuficientes".
- **Efecto esperado:** Si el bot decide apostar, lo hará con posiciones máximas de $1.5 USD para permitir hasta 3 intentos diferentes.

---

**3. Corrección de Identidad de Billetera (Proxy Address)**
- **Archivo modificado:** `backend/.env`
- **Cambios realizados:** 
  - `POLY_PROXY_ADDRESS` actualizada de `0x62d3...43eD8` (billetera dueña) a `0xEC812165668F4C339405b8E54C9c6B18432171cE` (billetera Proxy real de Polymarket).
- **Razón:** El dashboard mostraba $0 balance porque consultaba el contrato equivocado. Al poner la dirección Proxy real, el cálculo de balance On-chain ahora es correcto ($5 USDC).
- **Efecto esperado:** Dashboard actualizado con balance real y visibilidad corregida.

**4. Expansión de Memoria del Dashboard (72h Window)**
- **Archivo modificado:** `backend/app/api/status_router.py`
- **Cambios realizados:** 
  - La fecha `today` de consulta a Supabase se cambió de un reset de medianoche (00:00 UTC) a una ventana móvil de 72 horas atrás.
- **Razón:** El reseteo de medianoche UTC dejaba los contadores en 0 justo cuando el usuario en su horario local quería ver los resultados. Ahora el dashboard mantiene viva la memoria de los últimos 3 días.
- **Efecto esperado:** Mayor persistencia de datos visuales y tranquilidad operativa.

**5. Corrección del Motor de Clima — `invalid signature` al Ejecutar (14 de Abril de 2026)**
- **Archivo modificado:** `backend/app/engines/weather/manager.py`
- **Cambios realizados:**
  - Importado `OrderManager` desde `app.engines.ghost.order_manager`.
  - Instanciado como `self.order_mgr = OrderManager()` en `__init__`.
  - Corregida la llamada de `order_mgr.create_and_post_order(...)` (variable indefinida) a `self.order_mgr.create_and_post_order(...)`.
- **Razón:** El Weather Engine usaba `order_mgr` como variable local en el bloque `else` de ejecución live, pero esa variable nunca fue definida en ese scope. Al llegar al bloque de ejecución real, Python lanzaba un `NameError` que internamente caía al cliente CLOB crudo sin credenciales correctas, produciendo el error `PolyApiException[status_code=400, error_message={'error': 'invalid signature'}]`.
- **Efecto esperado:** El Weather Engine ya puede firmar y enviar órdenes correctamente en modo live, usando el mismo `PolyClient` autenticado que el resto del sistema.

**6. Expansión del Horizonte de Mercados (14 de Abril de 2026)**
- **Archivo modificado:** `backend/.env`
- **Cambios realizados:**
  - `AUTONOMOUS_MAX_MARKET_DURATION_HOURS` de `48` → `720` (30 días).
  - `AUTONOMOUS_MAX_SIZE` de `5.0` → `1.5` (confirmado para proteger presupuesto de $5).
- **Razón:** El Director analizaba los 15 mercados del Indexer en cada ciclo pero los rechazaba a TODOS porque ninguno cierra dentro de 48h. El mercado de Polymarket con buena liquidez y precio equilibrado (0.15-0.85) tiende a tener horizontes de semanas o meses. Con 48h el bot es un francotirador mirando por la mirilla con la lente tapada. Ahora con 30 días (720h), mercados como "West Ham relegado" (42d), "Czechia Eurovision" (31d) e "Israel-Líbano normalize" serán analizados por el Concilio de IA.
- **Efecto esperado:** En el próximo ciclo el Director debería pasar de "15 markets analyzed → 0 proceeded" a "N markets sent to Council AI". El primer trade vivo debería ocurrir en las próximas horas.

**7. Eliminación del Límite de Spread Hardcodeado — Liquidity Trap (14 de Abril de 2026)**
- **Archivo modificado:** `backend/app/engines/autonomous/director.py` (línea 365)
- **Cambios realizados:**
  - Eliminado límite de spread en modo live hardcodeado a `0.05`.
  - Ahora usa `settings.PAPER_TRADING_MAX_SPREAD` (`0.15` en el `.env`) en ambos modos.
- **Razón:** El Director usaba un spread máximo de `0.05` en modo live que era más estricto que el Indexer (`spread < 0.15`). Esta contradicción hacía que mercados pre-validados como "Belgium advance Eurovision" (spread 0.06) fueran rechazados después de haber pasado todos los demás filtros. Era el último cuello de botella.
- **Efecto esperado:** En el próximo ciclo, el bot enviará mercados al Concilio de IA y se producirá el primer `EXECUTED` o `REJECTED (Council score insuficiente)`.

**8. Migración Crítica de Paginación API Gamma (Keyset/Cursor) (14 de Abril de 2026)**
- **Archivos modificados:**
  - `backend/app/engines/tracker/indexer.py`
  - `backend/app/engines/autonomous/director.py`
  - `backend/app/engines/ghost/scanner.py`
  - `backend/app/engines/arbitrage/manager.py`
- **Cambios realizados:**
  - Actualizados todos los endpoints `/markets` con query params a `/markets/keyset`.
  - Ajustada la lógica de respuesta para parsear el nuevo objeto `{"markets": [...]}`.
  - Corregidos parámetros booleanos (`ascending`: `false` → `False`).
- **Razón:** Polymarket activó una migración obligatoria con fecha límite 1 de mayo de 2026. La API antigua basada en `offset` será desactivada. Al migrar hoy, garantizamos que el bot no se quede "ciego" cuando cierren los endpoints viejos.
- **Efecto esperado:** Funcionamiento fluido y estabilidad a largo plazo. El Indexer y los motores de escaneo ya están listos para la nueva infraestructura de Polymarket.

---

**9. Limpieza Final y Verificación Keyset API (14 de Abril de 2026)**
- **Archivos modificados:**
  - `backend/app/engines/weather/manager.py`
  - `backend/app/engines/arbitrage/manager.py`
  - `backend/run_autonomous_loop.py` (OutcomeResolver)
  - `backend/.env` (OpenRouter Key)
- **Cambios realizados:**
  - Migración completa de los motores restantes (`weather_manager.py`, `arbitrage/manager.py`) para usar `/markets/keyset` y `/events/keyset`.
  - Corrección de tipos: Se eliminaron los parámetros booleanos en formato string (`"true"`/`"false"`) y se reemplazaron por tipos nativos de Python (`True`/`False`) en todas las llamadas a la API Gamma.
  - Actualización del `OutcomeResolver` en `run_autonomous_loop.py` para buscar mercados vía `/markets/keyset`, asegurando la compatibilidad post-1 de mayo.
  - Configuración de la nueva OpenRouter API Key y verificación del modelo `google/gemma-4-31b-it:free`.
- **Razón:** Completar la migración obligatoria de Polymarket y asegurar que todos los componentes del sistema utilicen los estándares de la nueva API.
- **Efecto esperado:** Estabilidad total ante el cambio del 1 de mayo y capacidad de análisis de IA restaurada en EC2.
