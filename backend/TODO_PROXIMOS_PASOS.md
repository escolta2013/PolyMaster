# 📋 Plan de Trabajo: Post-Calibración — 24/25 de Febrero, 2026

## Estado Actual
El bot ya supera los filtros críticos de fecha y precio. El modo **Paper Trading** está configurado con un spread generoso (0.50) para maximizar la recolección de datos.

### ✅ Logros Recientes
- [x] Fix de regex de fecha (ya no confunde "Feb 28" con "Feb 2").
- [x] Filtro de precios extremas usa `midpoint` (evita falsos positivos por spreads anchos).
- [x] Sincronización de `.env` y `config.py` para spreads de calibración.
- [x] Activación de protección contra trampas de liquidez (spread > 0.50).

---

## 🎯 Próximos Pasos (Marzo 1, 2026)

### 1. Monitoreo de `RuleLawyer` y Formato
Observar en `autonomous.log` si el agente `RuleLawyer` respeta el formato sin headers de Markdown. Si persiste en usar `1.`, `2.`, `#`, etc., se procederá a:
- Cambiar el modelo de `RuleLawyer` a `mistral-7b-instruct` vía OpenRouter.
- Verificar que el `FinalConfidenceRange` aparezca en la **última línea**.

### 2. Análisis de Divergencia Geopolítica
El mercado de **Arabia Saudita vs Irán** mostró una divergencia de 16 puntos (Council 0.35 vs Market 0.51).
- Revisar si el Council está subestimando riesgos geopolíticos por falta de "noticias de última hora" (Breaking News).
- Evaluar si el `news_fetcher` necesita integración con fuentes geopolíticas fuera del ecosistema cripto.

### 3. Validación de `Council Score` vs `Current Price`
Confirmar que el Council está operando sin sesgo de anclaje (ignora el precio actual para su cálculo). Las corridas recientes sugieren que esto está funcionando perfectamente.

---

## ⚠️ Notas de Seguridad y Configuración
- Mantener `PAPER_TRADING_MODE=true` hasta que el Council demuestre un ROI positivo.
- **Modelo Actual**: `gemini-2.0-flash-lite` para el resto del Council (por costo/eficiencia).
- Reiniciar el bot (`python run_autonomous_loop.py`) tras cualquier cambio en el `orchestrator.py`.
