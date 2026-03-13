---
description: Protocolo de Revisión del Bot (Health Check)
---

Este protocolo debe ejecutarse cada vez que se solicite una revisión del estado del bot. Sigue estos pasos estrictamente para dar una respuesta rápida y precisa.

// turbo
1. **Pulso de Ejecución**: Verifica si el bot está activamente analizando mercados.
   ```powershell
   Get-Content -Path "backend\logs\autonomous.log" -Tail 50 | Select-String -Pattern "Cycle Complete|Analyzing opportunity"
   ```

// turbo
2. **Escaneo de Errores**: Busca excepciones recientes o errores críticos.
   ```powershell
   Get-Content -Path "backend\logs\error.log" -Tail 20
   Get-Content -Path "backend\logs\autonomous.log" -Tail 100 | Select-String -Pattern "ERROR|Exception|FAILED"
   ```

// turbo
3. **Validación de Filtros**: Confirma que los filtros de categoría (NBA, Tennis, etc.) y VPIN están funcionando.
   ```powershell
   Get-Content -Path "backend\logs\autonomous.log" -Tail 500 | Select-String -Pattern "excluded_category|vpin_toxic_flow|specific_price_target" | Select-Object -Last 5
   ```

// turbo
4. **Auditoría de Performance**: Ejecuta el script de evaluación de ganancias simuladas.
   ```powershell
   cd backend; python evaluate_sim_profit.py
   ```

// turbo
5. **Estado del Presupuesto**: Verifica el gasto diario y el modo actual (Simulación/Live).
   ```powershell
   Get-Content -Path "backend\logs\autonomous.log" -Tail 200 | Select-String -Pattern "spent_today|remaining_today|PAPER_TRADING_MODE" | Select-Object -Last 3
   ```

6. **Resumen Final**: Proporciona un resumen con:
   - Estado: (OPERATIVO / ERROR / DETENIDO)
   - Última actividad: (Hora del último ciclo)
   - ROI Realizado: (% del audit)
   - Accuracy: (W/L ratio)
   - Bloqueos: (Si existen errores recurrentes)
