# Plan: API Decomposition

Resumen
-------
Reorganizar el backend HTTP para separar responsabilidades en `schemas/`, `mappers/`, `services/`, `routers/` y `application/use_cases/`. Mejorar mantenibilidad, testabilidad y permitir evolución segura de la API.

Objetivos
---------
- Extraer modelos Pydantic a `backend/src/api/schemas/`.
- Implementar mappers para conversiones DB↔DTO.
- Crear `application/use_cases/` para la lógica con efectos.
- Registrar routers por dominio desde `main.py` manteniendo compatibilidad.

Entregables
-----------
- Código reorganizado en `backend/src/api/{schemas,mappers,routers}`.
- `backend/src/application/use_cases/` con casos de uso.
- Tests unitarios para mappers y use-cases.
- PRs pequeños y verificables.

Hitos y cronograma
------------------
1. Inventario y pruebas base — 1 día.
2. Migración de `schemas/` — 1 día.
3. Implementación de `mappers/` y tests — 1–2 días.
4. Creación de `use_cases/` y refactor de routers — 1–2 días.
5. Ajustes finales, CI y PR — 0.5–1 día.

Dependencias
------------
- Repositorios de persistencia (`backend/src/infrastructure/repositories/`).
- Fixtures y tests de integración existentes.

Riesgos
-------
- Import circulares: usar separación por interfaces/DI.
- Ruptura de contrato: mitigarlo con tests de contrato y PRs pequeños.

Próximos pasos inmediatos
------------------------
1. Ejecutar inventoría (tarea 1 en `tasks.md`).
2. Abrir primer PR moviendo un par de modelos a `schemas/`.
