# 🩺 Protocolo de Revisión del Bot (PolyMaster Health Check)

Este documento define los pasos estandarizados para verificar la salud y el rendimiento del bot PolyMaster. Este protocolo es utilizado por el asistente de IA para garantizar una revisión rápida y evitar análisis redundantes.

## 1. Verificación de Ejecución (Pulso)
- **Objetivo**: Confirmar que el loop autónomo no se ha detenido.
- **Acción**: Revisar las últimas 50 líneas de `backend/logs/autonomous.log` buscando el mensaje "Cycle Complete" o "Analyzing opportunity".

## 2. Detección de Errores
- **Objetivo**: Identificar fallos de API, errores de red o excepciones lógicas.
- **Acción**: 
  - Revisar `backend/logs/error.log`.
  - Buscar "ERROR" o "Exception" en el log principal.

## 3. Auditoría de Filtros
- **Objetivo**: Asegurar que las categorías excluidas no están consumiendo recursos.
- **Acción**: Buscar logs de `excluded_category` o `vpin_toxic_flow`. El bot debe estar rechazando activamente NBA, Tennis y eSports antes de llamar al Council.

## 4. Evaluación de Rentabilidad (PnL)
- **Objetivo**: Medir el ROI real de las operaciones resueltas.
- **Acción**: Ejecutar `python backend/evaluate_sim_profit.py`.
- **Métricas Clave**: Accuracy (Meta: >62%) y ROI Realizado.

## 5. Control de Riesgos
- **Objetivo**: Verificar límites de presupuesto y exposición.
- **Acción**: Revisar el `spent_today` y `remaining_today` reportado por el `Director`.
- **Configuración**: Confirmar si `PAPER_TRADING_MODE` sigue en `true`.

---
*Última actualización: 2026-03-12*
