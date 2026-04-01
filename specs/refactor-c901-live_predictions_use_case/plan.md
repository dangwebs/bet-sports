# Plan: Refactor Live Predictions Use Case

Resumen
-------
Refactorizar el caso de uso de predicciones en vivo para separar responsabilidades: entrada, validación, lógica de inferencia y persistencia.

Objetivos
---------
- Extraer lógica a `application/use_cases/live_predictions`.
- Asegurar tests unitarios e integración para el flujo en vivo.
- Reducir acoplamiento con infraestructuras específicas.
