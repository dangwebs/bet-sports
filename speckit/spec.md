<!--
spec.md — Especificación para aplicar linter a todo el repo
Generado: 29 de marzo de 2026
Estado: borrador
-->

# Spec: Linter global para BJJ-BetSports

## Resumen ejecutivo

Este documento especifica el alcance, objetivos, criterios de éxito y el plan de implementación
para integrar un conjunto de linters y formateadores coherentes en todo el repositorio
BJJ-BetSports (backend, frontend y scripts). El objetivo es homologar estilo, detectar
errores sintácticos y estilísticos de forma automatizada y asegurar que nuevos PRs cumplan
las reglas establecidas.

## Motivación

- Mejorar la legibilidad y mantenibilidad del código.
- Detectar errores estáticos y anti-patrones temprano.
- Evitar debates de estilo en PRs mediante formateo automático.
- Integrar comprobaciones en hooks locales y en CI.

## Objetivos

- Definir una configuración reproducible para cada lenguaje del repo.
- Proveer herramientas (pre-commit, CI) que garanticen que el código nuevo pasa linters.
- Aplicar formateo automático cuando sea seguro (Black/Prettier/ruff/eslint --fix).
- Mantener la lógica del dominio intacta: NO hacer cambios algorítmicos.

## Alcance

- Incluir: todo el código fuente del repo en `backend/`, `frontend/`, `scripts/` y archivos de
  configuración relevantes (`*.py`, `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.css`, `*.scss`, `*.json`, `*.yaml`, `*.yml`).
- Excluir (no lint automático): binarios, artefactos entrenados y pesos (`backend/ml_models/*`, archivos `.joblib`), datos de entrenamiento grandes y directorios `dev-dist/` generados.

Si se detectan archivos que deban incluirse/excluir, se documentará en el apartado "Excepciones" y se actualizará la spec.

## Criterios de éxito (aceptación)

- Repositorio con configuración en el árbol (`pyproject.toml` / `.ruff.toml` / `.eslintrc.*` / `.prettierrc` / `.pre-commit-config.yaml`).
- Job de CI `lint` que pasa en la rama principal (green).
- Hooks `pre-commit` configurados para formateo y chequeo local.
- Todos los archivos de código aplicables pasan los checks o quedan en un estado con issues explícitos documentados y con plan de corrección.

## Toolchain recomendada (propuesta)

- Python (backend + scripts):
  - Formateo: `black` (line-length 88)
  - Import sorting: `isort`
  - Linter principal: `ruff` (reemplaza flake8 donde sea posible, admite --fix)
  - Configuración centralizada en `pyproject.toml` o `.ruff.toml`.

- Frontend (TypeScript / React):
  - Linter: `eslint` con `@typescript-eslint` y reglas recomendadas.
  - Formateo: `prettier` (integrado con eslint via `eslint-plugin-prettier` o `eslint-config-prettier`).

- Otros: `stylelint` para CSS/SCSS si hay estilos complejos.

- Integración local/CI:
  - `pre-commit` para hooks locales.
  - GitHub Actions workflow `.github/workflows/lint.yml` para comprobaciones en PRs.

## Reglas clave y configuración inicial propuesta

- Longitud máxima de línea: 88 caracteres (coherente con Black en Python).
- No permitir warnings como errores en CI: `eslint --max-warnings=0` y `ruff check --exit-zero` configurado para fallar según política.
- Mantener reglas que no alteren semántica: evitar reglas de reescritura peligrosa sin revisión humana.

Ejemplo de comandos iniciales que documentaremos en README:

```bash
# Python
pip install ruff black isort pre-commit
black --check .
ruff check .

# Frontend (desde frontend/)
npm ci
npx eslint "src/**/*.{ts,tsx,js,jsx}" --fix
npx prettier --check "**/*.{ts,tsx,js,jsx,json,css,md}"

# Hooks
pre-commit install
pre-commit run --all-files
```

## Plan de despliegue (fases)

1. Descubrimiento (1 día): inventario automático y manual de lenguajes, paquetes y excepciones.
2. Especificación y configuración (1 día): crear `pyproject.toml` / `.ruff.toml`, `.pre-commit-config.yaml`, `.eslintrc.cjs`, `.prettierrc` y plantilla de workflow CI.
3. Formateo automático inicial (1-2 días): ejecutar `black`, `isort`, `ruff --fix` y `prettier --write` por módulos; crear commits atómicos por paquete/submódulo.
4. Correcciones manuales (varía): resolver lints no autoarreglables, priorizando backend crítico.
5. Integración CI y hooks (1 día): añadir GitHub Actions y requerir `lint` como check obligatorio en PRs.
6. Monitor y cierre (1 día): validar PRs, actualizar documentación y cerrar la spec.

Recomendación práctica: aplicar cambios por carpetas (ej. `backend/` primero), con commits atómicos y PRs pequeños para facilitar review.

## Riesgos y mitigaciones

- Cambios voluminosos (Black/Prettier) que dificulten revisión: mitigar con commits por módulo y pruebas automatizadas.
- Reglas incompatibles con código legacy (p.ej. imports, f-strings vacías): documentar excepciones y añadir suppressions específicas.
- Posible cambio involuntario en semántica si se aplica transformaciones agresivas: no ejecutar refactors automáticos sin revisión humana.

## Excepciones y reglas especiales

- Archivos de modelos (`backend/ml_models/*.joblib`) y datos de entrenamiento no serán modificados ni evaluados por los linters binarios.
- Scripts de generación o herramientas internas que deben conservar estilo específico se documentarán y evaluarán caso a caso.

## Criterios de verificación (checks de aceptación)

- `python -m py_compile` no debe producir errores en archivos Python aplicables.
- `black --check .` => OK
- `ruff check .` => OK (o lista de issues aceptados documentados)
- `npx eslint --max-warnings=0` en `frontend/` => OK
- Pre-commit hooks instalados y `pre-commit run --all-files` pasa.

## Tareas (mapeo a la lista de trabajo)

- Ver `speckit/tasks` o el TODO maestro. Mapeo mínimo:
  1. Eliminar espacios finales (ya completado)
  2. Corregir E701 (ya completado)
  3. Ajustar líneas largas E501 (en progreso)
  9. Generar spec de linting (completado)
  11. Definir toolchain y reglas (próximo paso)
  12. Añadir archivos de configuración (implementación)
  13. Añadir hooks pre-commit (implementación)
  14. Añadir workflow CI de linting (implementación)
  15-17. Formateo, correcciones manuales y validación en CI

## Propietarios y responsabilidades

- Responsable técnico (owner): equipo backend / orquestador (designado por el repo).
- Revisión de cambios grandes: al menos 1 revisor del dominio (backend) y 1 del código frontend cuando aplique.

## Timeline estimado (orientativo)

- Fase de Discovery + Spec: 1–2 días (hecho).
- Implementación inicial backend: 1–3 días.
- Implementación frontend + CI: 2–4 días.

## Próximos pasos inmediatos (acción inmediata)

1. Validar y aprobar esta `spec.md` con el equipo.
2. Decidir toolchain final (ruff vs flake8; eslint config exacta).
3. Implementar la fase 2: añadir configuraciones y hooks.

---

Si quieres, procedo ahora a generar los archivos de configuración iniciales (`pyproject.toml`/`.ruff.toml`, `.pre-commit-config.yaml`, `.github/workflows/lint.yml`) y aplicar el formateo automático por módulos. ¿Procedo con la implementación ahora o prefieres revisar/ajustar la spec primero?
