# ADR 0001: Restriccion de scope y timeouts en workflow MLOps

## Estado
Aceptado

## Fecha
2026-03-28

## Contexto
El workflow de GitHub Actions `enterprise_daily_mlops.yml` tenia dos desviaciones frente a `RULES.md`:

1. `timeout-minutes` en `train-model` y `finalize-process` configurado en 360, superando el limite de 60 minutos para GitHub Free Tier.
2. Matriz de ligas fuera del scope activo: incluia `UEL` y `UECL`, y no incluia `B1` (Jupiler Pro League), lo cual viola la restriccion operativa de ligas permitidas.

Adicionalmente, el resumen reportaba paralelismo no consistente con la estrategia real (`max-parallel: 1`).

## Decision
Se ajusta el workflow para cumplir reglas operativas:

1. Establecer `timeout-minutes: 60` en `train-model`.
2. Establecer `timeout-minutes: 60` en `finalize-process`.
3. Restringir la matriz de prediccion a las ligas activas de `RULES.md`:
   - `E0`, `D1`, `SP1`, `B1`, `P1`, `I1`, `F1`, `UCL`.
4. Eliminar `UEL` y `UECL` del flujo diario.
5. Corregir el resumen para reflejar ejecucion secuencial segura para rate-limit.

## Consecuencias
Positivas:
- Cumplimiento explicito de politicas de operacion del proyecto.
- Menor riesgo de ejecuciones largas y consumo excesivo en Actions.
- Menor riesgo de errores por rate-limit en proveedores externos.

Trade-offs:
- Cobertura internacional reducida al scope definido.
- Si algun job no termina en 60 minutos, fallara mas rapido y requerira optimizacion incremental.

## Implementacion
Cambios aplicados en:
- `.github/workflows/enterprise_daily_mlops.yml`

## Seguimiento
1. Monitorear durante 3 ejecuciones consecutivas que no haya timeout.
2. Si hay timeout en `train-model`, dividir entrenamiento por bloques de ligas o disminuir ventana de dias.
3. Si se desea ampliar scope de ligas, actualizar primero `RULES.md` y crear nuevo ADR antes de modificar workflow.
