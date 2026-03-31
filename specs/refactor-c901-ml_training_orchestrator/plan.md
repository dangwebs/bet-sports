# Plan: Refactor ML Training Orchestrator

Resumen
-------
Reorganizar el orquestador de entrenamiento para mejorar trazabilidad, paralelismo y posibilidad de testing aislado.

Objetivos
---------
- Separar pipeline de preparación de datos, entrenamiento y evaluación.
- Introducir módulos de retry y observabilidad.
