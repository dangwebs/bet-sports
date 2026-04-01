# Tasks: Frontend Hardening

1. Auditoría de bundle y dependencias
   - Ejecutar `npm run build` y analizar reporte (source-map-explorer / rollup-plugin-visualizer).
   - Estimación: 2h

2. Habilitar `strict` en `tsconfig` y corregir errores
   - Ajustar tipos y eliminar `any` donde aplique.
   - Estimación: 4h

3. Eliminar dependencias no usadas y optimizar imports
   - Estimación: 2h

4. Añadir E2E mínimo (Playwright/Cypress)
   - Flujos: login (si aplica), carga de dashboard, fetch de API.
   - Estimación: 4h

5. Añadir error-boundary y manejo global de errores
   - Estimación: 1–2h

6. Revisión de seguridad y headers de build
   - Revisar CSP, X-Frame, políticas de cache.
   - Estimación: 1h
