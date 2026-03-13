# CHANGELOG - 01 de Marzo, 2026: Refuerzo de Formato del Council

## Contexto de la Modificación
Se detectó que el agente `RuleLawyer` persistía en generar análisis con headers de Markdown (`#`, `##`, `1.`, `2.`), lo cual ensuciaba el log y dificultaba el parsing correcto del `FinalConfidenceRange`. Aunque el parser extraía un valor (posiblemente fallback de 0.500), el comportamiento no era el diseñado.

## Cambios Realizados en `app/engines/council/orchestrator.py`

### 1. Refuerzo de Instrucciones en LLMAgent (Base Prompt)
- **Prohibición de Markdown**: Se añadieron instrucciones explícitas prohibiendo `#`, `##`, `###`, bold (`**`), e italics (`_`).
- **Instrucción de "Thinking Process" Interno**: Se movieron los pasos de superforecasting a un bloque de "Internal Thinking Process" para indicar al modelo que debe ejecutarlos mentalmente pero no incluirlos como headers en la salida.
- **Formato de Salida Agresivo**: Se especificó que la respuesta **DEBE** terminar con el formato `Reasoning: ... | FinalConfidenceRange: X.XX-X.XX` en la **ÚLTIMA LÍNEA**.
- **Restricción de Palabras**: Se redujo el límite del reasoning a **15 palabras** (antes 30) para maximizar la concisión y evitar truncamientos.

### 2. Aumento de Recursos (Tokens)
- Se incrementó `max_tokens` de **250** a **350** para permitir que modelos con razonamiento extenso (CoT) terminen su conclusión y el delimitador `|` sin ser cortados prematuramente.

### 3. Fix Quirúrgico para RuleLawyer
- Se inyectaron ejemplos de **CORRECT vs WRONG** directamente en la personalidad del agente `RuleLawyer`.
- Se enfatizó la necesidad de seguir el formato "SIN EXCEPCIONES" dentro de su mindset específico.

## Observaciones Técnicas
- El modelo base utilizado es `gemini-2.0-flash-lite`. 
- **Hipótesis**: Si el modelo persiste en usar headers jerárquicos a pesar de estas instrucciones "negativas", se confirmará un sesgo estructural del modelo base hacia el formato instructivo estándar.
- **Plan de Contingencia**: Si el formato falla de nuevo, se migrará `RuleLawyer` a `mistral-7b-instruct` vía OpenRouter para evaluar una mejor adherencia a instrucciones de formato técnico.

## Estado del Sistema
- **Anti-anchoring**: Operativo (el Council ignora el precio del mercado en su estimación).
- **Caché**: Operativo (HITs detectados correctamente reduciendo latencia y costos).
- **Consenso**: Funcionando con régimen de "Divergencia" detectado en mercados geopolíticos complejos (ej. Arabia Saudita vs Irán).
