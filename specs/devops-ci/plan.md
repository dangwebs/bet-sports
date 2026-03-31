# Plan: DevOps / CI

Resumen
-------
Establecer pipelines de CI reproducibles que ejecuten linting, type-check, tests (backend/frontend), builds y artefactos, con caching y seguridad básica (scans). Habilitar pipelines para PRs y releases (staging).

Objetivos
---------
- Tener un flujo CI en GitHub Actions que valide cada PR: lint, tests unitarios, build frontend y backend.
- Construir imágenes Docker reproducibles para pruebas de integración y despliegue en staging.
- Integrar escaneos básicos de seguridad y dependencias (bandit, safety, npm audit).

Entregables
-----------
- `.github/workflows/ci.yml` con jobs: `lint`, `test:backend`, `test:frontend`, `build`.
- `.github/workflows/release.yml` para builds de release y push opcional a registry.
- Documentación en `docs/ci.md` con instrucciones locales y variables de entorno necesarias.

Hitos y cronograma
------------------
1. Job `ci.yml` básico (lint + tests) — 0.5 día.
2. Job `build` que crea imagen Docker — 0.5 día.
3. Integración de cache y artefactos (pip/npm cache) — 0.5 día.
4. Añadir security scans y workflow de release — 0.5–1 día.

Dependencias
------------
- Secrets para registry (si se publica imágenes).
- Acceso a runners que soporten Docker (para build de imágenes).

Riesgos
-------
- Secrets expuestos en logs → Mitigación: usar secrets de GitHub y no imprimir variables sensibles.
- Tiempo de CI excesivo → Mitigación: cache, split jobs y paralelismo.

Próximos pasos inmediatos
------------------------
1. Crear `.github/workflows/ci.yml` con jobs mínimos.
2. Documentar `docs/ci.md` con comandos locales para reproducir CI.