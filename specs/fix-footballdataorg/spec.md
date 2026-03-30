# Spec: Corregir redefiniciones y errores de lint en football_data_org.py

## Contexto
- Archivo afectado: `backend/src/infrastructure/data_sources/football_data_org.py`
- Problemas detectados: redefinición de funciones (flake8 F811), errores de indentación (E114/E116), y ruido del linter (E501, F401) derivado de duplicados y pequeñas inconsistencias.

## Objetivo
Corregir las redefiniciones y problemas de estilo en `football_data_org.py` para:

- Eliminar definiciones duplicadas que provocan F811.
- Unificar e identificar la implementación canónica de cada función (equipos, partidos, matches por rango, etc.).
- Asegurar retornos consistentes (por ejemplo, funciones que devuelven listas nunca retornan `None`).
- Aplicar formato y pasar linter (`flake8`/`black`) sin cambiar la lógica observable ni la semántica de la API.

## Alcance
- Cambios limitados a `backend/src/infrastructure/data_sources/football_data_org.py`.
- No se tocarán otras capas (repositorios, use_cases) en esta intervención atómica.

## Criterios de aceptación
1. `flake8` en el archivo no reporta F811, E114, E116 ni errores sintácticos.
2. `python -m py_compile backend/src/infrastructure/data_sources/football_data_org.py` no produce errores.
3. `pytest -q` (suite del backend) no introduce fallos nuevos por estos cambios.
4. Cambios hechos en commits atómicos con mensaje siguiendo Conventional Commits.

## Riesgos y mitigaciones
- Riesgo: eliminación accidental de lógica válida al consolidar duplicados.
  - Mitigación: revisar manualmente cada función duplicada y conservar la versión que respete mejor el contrato y las llamadas existentes.
- Riesgo: introducir regresiones en parsing de partidos.
  - Mitigación: correr tests relevantes y compilar antes de commitear.

## Stakeholders
- Implementador: Backend specialist (orquestado por Orchestrator)
- QA: revisar linter y tests locales
