# Tareas: Optimizacion de recursos Docker

- [x] **T1 / REQ-DRO-3**: Ampliar `.dockerignore` para excluir entornos virtuales, modelos locales, caches y artefactos no necesarios.
- [x] **T2 / REQ-DRO-1**: Mover `ml-worker`, `labeler` y `updater` a un profile opt-in en `docker-compose.dev.yml`.
- [x] **T3 / REQ-DRO-2**: Ajustar `run_dev_pipeline.sh` para que `N_JOBS` use un default de CPU mas conservador.
- [x] **T4 / REQ-DRO-4**: Actualizar `README.md` con el nuevo flujo de stack base y automation.
- [x] **T5 / AC-1..AC-4**: Validar `docker compose config` y sintaxis shell de los archivos modificados.