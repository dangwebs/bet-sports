# Tareas: Hardening del Rebuild Docker

- [x] **T1 / REQ-DR-2**: Corregir `frontend/src/presentation/components/ErrorBoundary/ErrorBoundary.tsx` para eliminar errores de props y parametros no usados.
- [x] **T2 / REQ-DR-2**: Corregir `frontend/src/utils/matchMatching.ts` para construir un `Prediction` valido sin cast parcial inseguro.
- [x] **T3 / REQ-DR-2**: Corregir `frontend/src/utils/predictionUtils.ts` y/o `frontend/src/types/index.ts` para alinear los campos de corners y tarjetas usados por la UI.
- [x] **T4 / REQ-DR-3**: Ajustar `docker-compose.dev.yml` para que `labeler` use un entrypoint estable y existente dentro de la imagen.
- [x] **T5 / REQ-DR-1**: Guardar la configuracion canonica de rebuild Docker en el repositorio.
- [x] **T6 / AC-1..AC-3**: Validar que los archivos modificados no tengan errores y que el wiring del stack quede coherente.
