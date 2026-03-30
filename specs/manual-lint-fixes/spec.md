---
title: "Spec: Revisión y corrección manual de issues de lint en backend"
status: draft
owner: Orchestrator
---

Objetivo
--------
Realizar una revisión manual focalizada en el paquete `backend/` para corregir problemas detectados por linters y limpiar comentarios/`TODO` menores. Esta tarea NO incluye refactors complejos (C901) que tendrán su propio ticket.

Alcance
-------
- Ejecutar `ruff check backend` y priorizar violaciones por archivo.
- Corregir issues seguros y no disruptivos (E501, E111/E117 si aparecen, F401/F841 restantes, F541, docstrings mal formados, comments/TODOs simples).
- Mantener pruebas existentes estables: ejecutar `cd backend && pytest -q` después de cada cambio.
- No eliminar supresiones `C901` ni realizar refactors masivos aquí — eso queda en la tarea dedicada `Remover supresiones temporales y refactor C901`.

No objetivos
------------
- Refactorizar funciones grandes para eliminar C901.
- Cambiar comportamiento de negocio.

Criterios de aceptación
-----------------------
- `ruff check backend` devuelve 0 errores para las reglas abordadas en este spec (se documentarán las excepciones aprobadas).
- `cd backend && pytest -q` pasa sin fallos.
- Todos los cambios tienen commits atómicos con mensajes en español y convencionales (ej.: `fix(lint): ...`).

Plan de trabajo (tareas)
------------------------
1. Ejecutar `ruff check backend` y generar lista priorizada de archivos.
2. Para cada archivo en orden de prioridad:
   - Aplicar corrección mínima y segura.
   - Ejecutar `cd backend && pytest -q`.
   - Si pasa, commitear; si falla, revertir y documentar.
3. Reportar resultados y abrir PR si procede.

Comandos de verificación
------------------------
```bash
source .venv/bin/activate
.venv/bin/ruff check backend
cd backend && pytest -q
```

Notas
-----
- Para supresiones C901 (ej.: `backend/src/domain/services/picks_service.py`) se creará una tarea separada con alcance de refactor.
