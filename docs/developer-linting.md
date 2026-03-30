# Guía de linting y formateo para desarrolladores

Resumen rápido
--------------
Esta guía recoge los comandos y pasos para mantener el backend en estado "lint‑green" localmente y para entender cómo CI valida el código.

Comandos principales (local)
---------------------------
- Activar entorno virtual:

```bash
source .venv/bin/activate
```

- Ejecutar todos los hooks de `pre-commit` (aplica `black`, `isort` y otras correcciones automáticas):

```bash
.venv/bin/pre-commit run --all-files
```

- Ejecutar ruff para ver todos los errores de lint:

```bash
.venv/bin/ruff check .
```

- Ejecutar `black` en modo verificación (excluir venv):

```bash
.venv/bin/black --check . --exclude '/(backend/venv|venv|\.venv)/'
```

- Ejecutar `isort` en modo verificación (evitar venv/node_modules):

```bash
.venv/bin/isort --check-only . --skip .venv --skip venv --skip backend/venv --skip frontend/node_modules
```

- Ejecutar pruebas unitarias del backend:

```bash
cd backend && .venv/bin/pytest -q
```

Qué hacer si hay fallos
-----------------------
- Para problemas de formato e imports: ejecutar `pre-commit run --all-files` y volver a hacer `git add` + `git commit`.
- Para reglas de `ruff` (p. ej. E402, F821): revisar los imports y las anotaciones de tipos. Las correcciones no triviales (p. ej. C901) requieren un spec y refactor controlado.

CI
--
La acción de GitHub `Lint` está definida en `.github/workflows/lint.yml`. CI ejecuta:
- Instalación de herramientas (`ruff`, `black`, `isort`)
- `ruff check .`
- `black --check .`
- `isort --check-only .`
- Instalación deps y linter frontend (en `frontend/`)

Notas importantes
-----------------
- No deshabilitar reglas globalmente sin criar un `spec.md` justificando la excepción.
- Para C901 (funciones demasiado complejas): crear una tarea de refactor con tests que validen comportamiento antes de cambiar la implementación.
- Si necesitas ayuda para crear tests para una función compleja, pídemelo y puedo generar el esquema de tests y un plan de refactor.

Contacto
-------
- Orquestador (esta repo) documenta el proceso en `specs/manual-lint-fixes/spec.md` y en `specs/remove-c901/spec.md` (si existe).