# Plan de Acción: Depuración Local en Entorno de Producción

## Contexto del Proyecto
El bot **PolyMaster** operó en modo simulación (sin conectar una wallet real y sin firmas de transacciones) durante más de un mes. Al ser desplegado en AWS EC2 para "trading en vivo", el sistema falló. Específicamente, el sistema arroja errores de conexión, errores de validación de firma y problemas visuales en el balance del dashboard. 

Además, se actualizó el modelo de IA a la versión de límite de razonamiento más alto gratuita en OpenRouter (`google/gemini-2.0-pro-exp-02-05:free`) porque el modelo viejo fue depreciado.

## Obejtivo Actual
Detener los intentos de operar a ciegas en EC2. Vamos a **ejecutar el bot en esta máquina local (Windows)** usando la configuración exacta de producción (llaves reales, fondos reales). Así podremos ver los errores en tiempo real, corregir la lógica de firmas/creación de órdenes en los scripts y, cuando el bot logre su primer trade exitoso, actualizar el código en EC2.

---

## Fases de Ejecución

### Fase 1: Sincronización del Entorno (Estamos aquí)
1. **Detener servicios en EC2:** Asegurar que el bot en AWS está detenido (`sudo systemctl stop polymaster-bot`) para evitar colisiones de llaves o consumo de créditos.
2. **Sincronizar el `.env`:** El archivo `backend/.env` en esta máquina local DEBE tener exactamente las mismas credenciales que el de EC2:
   - Llave privada real (`PK`) del proxy wallet.
   - `POLY_PROXY_ADDRESS` correcta.
   - `AI_MODEL=google/gemini-2.0-pro-exp-02-05:free`
   - `COPY_SIMULATION=false` (Para intentar ejecutar la orden de verdad).
   - `ENABLE_AUTONOMOUS_TRADING=true`

### Fase 2: Depuración del Ciclo Autónomo (Testing Local)
1. Ejecutar el loop principal localmente: `python run_autonomous_loop.py`
2. **Hito A (Discovery):** Verificar que el `Indexer` encuentra mercados activos. (Vamos a relajar los filtros de precio a 0.15 - 0.85).
3. **Hito B (Council):** Verificar que se llama al modelo de IA y no hay errores de token/timeout con OpenRouter.
4. **Hito C (Execution - EL GRAN CUELLO DE BOTELLA):** Cuando el bot decida hacer un trade, observar el error que lanza el SDK de Polymarket. Repararemos la lógica en `app/core/client.py` y `order_manager.py` (Problemas de `sig_type` y fondos de proxy).

### Fase 3: Solución de Balance Front-End
Una vez que el backend funcione:
1. Detectar por qué `manager.py` no consigue el balance de USDC.
2. Comprobar los Endpoints de RPC gratuitos o la inyección de `user_id` en Supabase.

### Fase 4: Despliegue Final
1. Cometer y subir cambios al repositorio (`git add .`, `git commit`, `git push`).
2. En EC2 hacer `git pull` y reiniciar servicios.
