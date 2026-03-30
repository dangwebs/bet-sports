---
title: "Spec: Limpieza y corrección de data_sources (flake8/pytest)"
date: 2026-03-28
author: Orquestador (Copilot)
---

## Resumen

Esta especificación describe la intervención para limpiar y corregir problemas de estilo y lint en los módulos de `backend/src/infrastructure/data_sources/`, empezando por
`football_data_org.py`, y continuando con los archivos con más violaciones detectadas por `flake8`.

## Objetivo

- Eliminar trailing/blank whitespace (W291/W293), imports/vars no usados (F401/F841), y corregir indentación simple y saltos de línea (E111/E117, E302/E305).
- Ejecutar `flake8 backend/` y `cd backend && pytest -q` tras cada archivo modificado.
- Revertir la edición de un archivo si `pytest` falla; documentar la razón y seguir con el siguiente archivo.
- Realizar commits atómicos por archivo con mensajes en español siguiendo Conventional Commits.

## Alcance

- Carpeta objetivo: `backend/src/infrastructure/data_sources/` (hasta 40 archivos máximos)
- Archivo de inicio: `backend/src/infrastructure/data_sources/football_data_org.py`

## Criterios de aceptación

- `flake8 backend/` devuelve 0 errores tras completar la lista de archivos procesados (o indica sólo problemas fuera del alcance).
- `cd backend && pytest -q` pasa sin fallos después de cada commit.
- Cada archivo modificado tiene un commit atómico con mensaje en español y tipo apropiado (`fix`, `style`, `refactor`).

## Restricciones

- No se harán cambios funcionales que alteren la lógica de negocio salvo cuando sean necesarios para arreglar errores sintácticos que impidan pasar linters/tests.
- Si un cambio provoca fallos en `pytest`, se revierte inmediatamente el archivo y se documenta el motivo.

## Entregables

- `specs/cleanup-data-sources/spec.md` (este archivo)
- `specs/cleanup-data-sources/plan.md`
- `specs/cleanup-data-sources/tasks.md`
