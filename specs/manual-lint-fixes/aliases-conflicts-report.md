# Reporte de conflictos en `aliases` — statistics_service.py

Fecha: 29 de marzo de 2026
Autor: Orchestrator / Backend specialist

Resumen
-------
Se detectaron claves duplicadas en el diccionario `aliases` de `backend/src/domain/services/statistics_service.py` donde la misma clave aparece más de una vez con valores distintos. Quitar una de las entradas puede cambiar comportamiento (mapeos canónicos distintos), por lo que se requiere revisión manual.

Conflictos detectados
---------------------
1) `sc braga`
- Valores encontrados: `"braga"`, `"sp braga"`
- Apariciones:
  - Línea ~247: `"sc braga": "braga",`
  - Línea ~266: `"sc braga": "sp braga",`

2) `sporting clube de braga`
- Valores encontrados: `"braga"`, `"sp braga"`
- Apariciones:
  - Línea ~246: `"sporting clube de braga": "braga",`
  - Línea ~264: `"sporting clube de braga": "sp braga",  # CSV is Sp Braga`

3) `vitoria guimaraes`
- Valores encontrados: `"guimaraes"`, `"vitoriaguimaraes"`
- Apariciones:
  - Línea ~255: `"vitoria guimaraes": "guimaraes",`
  - Línea ~272: `"vitoria guimaraes": "vitoriaguimaraes",`

4) `vitoria sc`
- Valores encontrados: `"guimaraes"`, `"vitoriaguimaraes"`
- Apariciones:
  - Línea ~254: `"vitoria sc": "guimaraes",`
  - Línea ~271: `"vitoria sc": "vitoriaguimaraes",`

5) `vitória sc` (con acento)
- Valores encontrados: `"guimaraes"`, `"vitoriaguimaraes"`
- Apariciones:
  - Línea ~253: `"vitória sc": "guimaraes",`
  - Línea ~273: `"vitória sc": "vitoriaguimaraes",`

Notas y análisis
-----------------
- Estos conflictos ocurren principalmente en la sección de Portugal (Primeira Liga) y parecen deberse a mezcla de dos convenciones en fuentes de datos (CSV vs API). Algunos valores canonizan a `sp braga` / `sp lisbon` / `vitoriaguimaraes` y otros a formas abreviadas (`braga`, `guimaraes`).
- Eliminar la línea que mapea a `braga` y dejar `sp braga` (o viceversa) cambiará el resultado de `StatisticsService._resolve_alias` para entradas afectadas si hay entradas que dependen de la forma concreta.

Recomendación (segura y mínima)
-------------------------------
1. No aplicar eliminaciones automáticas para estas claves; requieren decisión de dominio.
2. Proponer canonicalizaciones por origen de datos:
   - Si la fuente principal de truth es el CSV (se usan claves `sp braga`, `sp lisbon`, `vitoriaguimaraes`), unificar a esas formas.
   - Si la fuente preferida es la API (formas cortas: `braga`, `guimaraes`), unificar a las formas cortas.
3. Para avanzar sin riesgo, yo propongo crear una PR que:
   - Liste los conflictos (este reporte).
   - Proponga la canonicalización recomendada (ej.: preferir `sp braga` y `vitoriaguimaraes`).
   - Aplique los cambios en una rama separada y ejecute `ruff` + `pytest` como verificación.

Acción propuesta ahora
---------------------
- He generado este reporte en `specs/manual-lint-fixes/aliases-conflicts-report.md`.
- Opciones siguientes (elige una):
  A) Yo aplico la canonicalización recomendada (`sp braga`, `vitoriaguimaraes`, etc.) y pruebo/commit/PR.
  B) Genero la PR con este reporte y dejo la decisión para revisión humana antes de aplicar cambios.
  C) Prefieres otra convención (indícala) y la aplico.

Comandos útiles para ver/validar localmente
------------------------------------------
```bash
# Ejecutar ruff localmente
.venv/bin/ruff check backend/src/domain/services/statistics_service.py
# Ejecutar pruebas
cd backend && .venv/bin/pytest -q
```

---

Si quieres que continúe, dime si escogemos A, B o C (y en C indícame la convención a usar).