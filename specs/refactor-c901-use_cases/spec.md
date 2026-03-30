# Especificación: Refactor C901 — `use_cases.py`

## Objetivo
Reducir la complejidad cognitiva (C901) en `backend/src/application/use_cases/use_cases.py` extrayendo bloques lógicos en helpers privados y/o módulos auxiliares, con cobertura por tests unitarios, para eliminar los `# noqa: C901` temporales.

## Alcance
- Archivo objetivo: `backend/src/application/use_cases/use_cases.py`.
- Extraer funciones/ciertos bloques dentro de las funciones de mayor complejidad (`execute`, `get_predictions`, etc.) en helpers privados del mismo módulo o métodos auxiliares de la clase.
- Mantener la misma interfaz pública del `UseCase`.
- Añadir tests unitarios para cubrir la lógica extraída.

## Restricciones
- No cambiar la lógica de negocio ni los contratos públicos.
- No cargar modelos/performance-heavy ops en tests reales; usar mocks para dependencias externas (modelos, servicios HTTP, DB).
- Seguir las reglas del proyecto: tipado estricto, PEP8, y pasar `ruff`/`pre-commit`.

## Criterios de Aceptación
- `ruff` ya no reporta C901 en `use_cases.py`.
- Tests unitarios nuevos que cubran >70% de las líneas extraídas.
- El código no introduce cambios funcionales; todos los tests existentes siguen pasando.

## Plan de implementación (alto nivel)
1. Identificar las funciones con C901 en el archivo.
2. Extraer bloques lógicos en helpers privados con nombres descriptivos.
3. Añadir tests unitarios para cada helper.
4. Ejecutar linter y tests; iterar hasta verde.
5. Eliminar `# noqa: C901` y limpiar comentarios temporales.
6. Commit, push y abrir PR desde `refactor/c901/use_cases`.

## Notas
- Trabajar incrementalmente: extraer y testear por cada helper antes de proceder al siguiente.
- Mantener commits atómicos y descriptivos.
