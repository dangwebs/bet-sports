# Plan: Frontend Hardening

Resumen
-------
Mejorar la resiliencia, seguridad y rendimiento del frontend (Vite + React) para producción: type-safety, bundle sizing, errores críticos y políticas de seguridad.

Objetivos
---------
- Aplicar TypeScript strict y corregir errores relevantes.
- Reducir tamaño de bundle y eliminar dependencias no usadas.
- Añadir pruebas E2E básicas y mejorar manejo de errores en UI.
- Revisar configuración de build y headers de seguridad.

Entregables
-----------
- Lista de acciones en `specs/frontend-hardening/tasks.md`.
- PRs para: ajustes de tsconfig, optimización de imports, mejoras de build.
- E2E mínima (Cypress / Playwright) para flujos críticos.

Hitos
------
1. Auditoría de bundle y deps — 0.5 día.
2. TypeScript strict fixes — 1 día.
3. E2E y error-boundaries — 1 día.

Próximos pasos inmediatos
------------------------
1. Ejecutar `npm run build` y generar reporte de bundle.
2. Listar dependencias candidates to remove.