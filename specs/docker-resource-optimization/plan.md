# Plan: Optimizacion de recursos Docker

Fecha: 2026-04-02

## Enfoque

Atacar primero el desperdicio claro del contexto Docker, luego reducir el costo del stack por defecto y finalmente ajustar la documentacion para que el flujo optimizado quede utilizable.

## Pasos

1. Endurecer `.dockerignore` con exclusiones de `venv`, `.venv`, `ml_models`, caches y artefactos locales.
2. Mover `ml-worker`, `labeler` y `updater` a un profile opcional de automatizacion.
3. Ajustar `run_dev_pipeline.sh` para que el default de `N_JOBS` use menos CPU del host.
4. Actualizar `README.md` con comandos diferenciados para stack base, automation y MLOps.
5. Validar sintaxis de compose y shell sin ejecutar builds completos.

## Resultado esperado

- Menor consumo por defecto al levantar el stack.
- Menor peso potencial de imagen y menor build context.
- Uso mas controlado de CPU al correr el pipeline MLOps.