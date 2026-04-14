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
*(Nuevos cambios se agregarán aquí abajo a medida que avancemos)*

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
