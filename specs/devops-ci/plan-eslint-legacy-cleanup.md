# Plan: Limpieza ESLint legacy (frontend)

Objetivo
--------
Ejecutar la limpieza incremental del ruido ESLint en `frontend/src/**`, entregando cambios en PRs pequeños y seguros, hasta que `npx eslint frontend/src --ext .ts,.tsx` no devuelva errores.

Fases y pasos
------------
1) Auditoría (1-2 h)
   - Comando: `cd frontend && npx eslint . --ext .ts,.tsx -f json -o ../eslint-legacy-report.json`
   - Generar un CSV/tabla con conteo por fichero y por regla.
   - Entregar reporte como `specs/devops-ci/reports/eslint-legacy-report-YYYYMMDD.json`.

2) Auto-fix seguro (0.5-1 h)
   - Ejecutar: `npx eslint frontend/src --ext .ts,.tsx --fix`
   - Revisar cambios, correr `npm run build` y `npm test`.
   - PR: `chore/lint/auto-fix` (máximo 1 PR para auto-fixes).

3) Triage y agrupado (1-2 h)
   - Clasificar errores restantes por regla y carpeta.
   - Priorizar grupos que más afectan CI (p.ej. `no-unused-vars`, `react-hooks`).
   - Planificar PRs por grupo (target 10–20 archivos por PR).

4) Implementación por PR (variable)
   - Para cada PR:
     - Aplicar cambios mínimos seguros (renombrar parámetros no usados a `_foo`, eliminar imports no usados, arreglar dependencias de hooks).
     - Evitar cambios lógicos; si necesario, abrir issue separado.
     - Incluir tests y screenshots si aplica.
     - Esperar revisión y merge.

5) Validación final (0.5 h)
   - Ejecutar auditoría completa y confirmar 0 errores de nivel `error` en `frontend/src`.
   - Actualizar la spec con métricas finales.

Reglas de seguridad / convenciones
---------------------------------
- No usar `/* eslint-disable */` global salvo casos documentados con link a issue.
- Prefijo `_` para parámetros intencionalmente sin usar.
- Reemplazar `any` por `unknown` + validación o por tipos concretos cuando sea sencillo.

Entregables
-----------
- `specs/devops-ci/spec-eslint-legacy-cleanup.md` (ya creado).
- `specs/devops-ci/plan-eslint-legacy-cleanup.md` (este archivo).
- Reportes de auditoría (`specs/devops-ci/reports/`).
- PRs `chore/lint/*` en la organización de PRs pequeñas.

Decisión requerida
------------------
- ¿Procedo a desglosar las tareas en el TODO y empezar a generar el primer PR (auto-fix + triage)?
  - Modo por defecto: `interactive` — te muestro cada PR antes de crearla.
  - Si prefieres, puedo ejecutar en `auto` y crear PRs pequeños directamente.

Estimación total
----------------
- 1–3 jornadas, dependiendo del backlog.

Contacto
-------
- Puedo comenzar ahora si das luz verde; priorizo archivos que históricamente bloquean PRs.
