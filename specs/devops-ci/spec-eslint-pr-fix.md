# Spec: Fix ESLint changed-files detection for PRs (frontend)

Resumen
-------
Pequeño ajuste en el workflow de PR para que la detección de archivos frontend cambiados busque rutas bajo `frontend/src/` en lugar de `src/`. Esto evita ejecutar ESLint en todo el repo cuando el PR solo cambia archivos en `frontend/`.

Alcance
-------
- Modificar `.github/workflows/ci-pr.yml` para usar la expresión `^frontend/src/.*\.(ts|tsx)$`.

Criterios de aceptación
-----------------------
- CI ejecuta `npx eslint <archivos>` cuando hay archivos `frontend/src/**` modificados.
- Si no hay archivos frontend cambiados, se ejecuta `npm run lint` de fallback.

Tareas
------
1. Actualizar `.github/workflows/ci-pr.yml` con la expresión correcta.
2. Commit `ci(frontend): fix changed-files detection for ESLint`.
3. Push y verificar que el job `Frontend: Lint + Build` ahora ejecuta lint solo en los archivos cambiados.

Riesgos
-------
- Rutas de frontend fuera de `frontend/src/` no serán detectadas; revisar si existen carpetas alternativas.

Notas
-----
Este es un cambio operacional, de baja complejidad. Está aprobado para aplicarse de forma inmediata.
