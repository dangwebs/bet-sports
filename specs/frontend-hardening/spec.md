# Spec: Frontend Hardening

Resumen
-------
Mejorar la robustez del frontend (React + TypeScript) para reducir bugs en producción y mejorar la puntuación de calidad: tipado estricto, manejo de errores, pruebas y optimizaciones de bundle.

Objetivos
--------
- Activar `strict` y eliminar `any` en las áreas críticas.
- Añadir `ErrorBoundary` global y componentes para fallbacks.
- Compartir tipos entre backend y frontend (generación o manual) para evitar desajustes.
- Añadir tests de componente (Jest/Testing Library) para vistas críticas.

Requisitos funcionales
----------------------
1. TypeScript `strict` sin `any` en la capa de presentación principal.
2. Error boundaries que capturen errores y reporten a logging/telemetría.
3. Tipos sincronizados con backend para `Match`, `Prediction`, `Pick`.

Aceptación
----------
- Build de frontend con `npm run build` sin errores de tipado.
- PRs que introduzcan `any` deben fallar en CI.

Desglose de tareas
------------------
1. Auditar `src/` y listar `any` usages (1h).
2. Añadir o generar tipos compartidos (2–4h).
3. Implementar ErrorBoundary y reportes (2h).
4. Añadir tests para componentes críticos (3–6h).
# Spec: Frontend Hardening (Epic 5)

Fecha: 2026-03-31

Resumen
-------
Mejorar la resiliencia y calidad del frontend (Vite + React) mediante tipado estricto, manejo centralizado de errores, pruebas de componentes y reducción de `any` en TypeScript.

Objetivos
---------
- Evitar runtime errors por tipos y respuestas inesperadas.
- Centralizar modelos compartidos (`shared/types`) con sincronización con backend.
- Añadir Error Boundaries y estrategias de fallback en UI crítica.

Requisitos (REQ-5.x)
-------------------
- REQ-5.1: Mover tipos compartidos a `frontend/src/types/shared.ts` y mantener sincronía con `src/api/schemas` (manual o script de generación).
- REQ-5.2: Eliminar `any` en componentes críticos y habilitar `noImplicitAny` más estricto.
- REQ-5.3: Añadir pruebas de componentes con `@testing-library/react` y snapshots donde aplique.

Aceptación
----------
- AC-1: Build limpio (`npm run build`) sin errores de tipo.
- AC-2: PR reviews no introducen `any` sin justificación documentada.

Tareas
------
1. Inventario: localizar usos de `any` y priorizar por criticidad.
2. Crear `frontend/src/types/shared.ts` y mapear campos esenciales.
3. Añadir Error Boundaries y toasts para errores de red genéricos.
4. Escribir tests para componentes de picks y matches.
