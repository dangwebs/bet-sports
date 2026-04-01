# Spec: Limpieza de ruido ESLint legacy (frontend)

Resumen
-------
Reducir el "ruido" de ESLint en el frontend (`frontend/src/**`) que actualmente provoca fallos en los checks de CI al ejecutar linter sobre el repositorio. El objetivo es dejar las reglas configuradas como `error` sin violaciones en el código productivo y establecer un proceso incremental, revisable y de bajo riesgo para corregir las violaciones existentes.

Alcance
-------
- Carpetas: `frontend/src/**` (primario). Excluir `dev-dist`, `public` y archivos generados.
- Reglas objetivo (ejemplos): `@typescript-eslint/no-unused-vars`, `@typescript-eslint/no-explicit-any`, `react-hooks/exhaustive-deps`, `@typescript-eslint/no-floating-promises`, `@typescript-eslint/await-thenable`, `@typescript-eslint/no-shadow`, `@typescript-eslint/await-thenable`.
- No incluye: cambios de arquitectura, reescrituras funcionales, o backend.

Criterios de aceptación
-----------------------
- Tras completar el plan, ejecutar `npx eslint frontend/src --ext .ts,.tsx` devuelve 0 errores (o solo warnings documentados).
- Nuevos PRs contra `main` no fallan por ESLint en la comprobación `Frontend: Lint + Build` gracias a la detección por archivos cambiados y/o a PRs de limpieza aplicadas.
- Las correcciones se entregan en PRs pequeños, con tests y sin cambios funcionales no revisados.

Tareas (alto nivel)
-------------------
1. Auditoría completa: ejecutar ESLint en `frontend/src` y generar un informe por fichero/regla.
2. Aplicar `eslint --fix` para reglas seguras (formatting, orden de imports, etc.) y abrir PR `chore/lint/auto-fix`.
3. Agrupar errores restantes por regla y carpeta; priorizar por impacto en CI (errores que causan fallos en PRs primero).
4. Implementar PRs pequeños por grupo (ej.: `chore/lint/no-unused-vars/ui`, `chore/lint/react-hooks/hooks`), cada PR < 20 archivos y con CI verde.
5. Validación final: ejecutar auditoría y comprobar reducción de errores a 0 en `frontend/src`.
6. Documentar patrones y añadir guías para evitar regresiones (p.ej. prefijo `_` para parámetros intencionalmente sin usar).

Riesgos
-------
- Algunas correcciones requieren cambios semánticos (p. ej. eliminar `any` requiere tipado), lo que puede introducir bugs si no se prueba adecuadamente.
- Volumen de archivos puede ser grande; revisar en PRs pequeños para reducir riesgo.

Mitigaciones
-----------
- Usar `eslint --fix` solo para reglas seguras y versionar en PRs separados.
- Si una corrección es de alto riesgo, crear un issue y dejar para refactor mayor fuera del alcance inmediato.
- Añadir tests y ejecutar suite en CI antes de mergear.

Responsable
-----------
- Frontend (puedo coordinar e implementar los primeros PRs). Recomendado: dividir trabajo en 2–4 PRs revisables.

Estimación
----------
- Auditoría + auto-fix: 1–2 horas.
- Triage y creación de PRs (por bloque): 1–4 horas por PR (dependiendo del número de archivos y reglas).
- Trabajo total estimado: 1–3 días laborables según tamaño del backlog.

Notas
-----
- Esta spec asume que ya aplicamos la mejora en CI para detectar solo archivos cambiados (ya implementada). Si se desea, podemos priorizar archivos que históricamente bloquean PRs (lista disponible en el informe de auditoría).