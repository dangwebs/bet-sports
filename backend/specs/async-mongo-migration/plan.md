# Plan de Migración y Auditoría — Async Mongo (Motor)

## Objetivo
Entregar una implementación nativa async de la capa MongoDB, validar su rendimiento
en staging y desplegarla gradualmente a producción sin impactar a los usuarios.

## Fases y estimaciones

1) Baseline y preparación — 1 día ✓
   - Recolectar métricas actuales (p50/p95, throughput) para endpoints críticos. **(deferido a post-deploy)**
   - Identificar queries más consumidas y hotspots (N+1, full collection scans).

2) Implementación `AsyncMongoRepository` — 2-3 días ✓
   - Implementar clase Motor-native con paridad de API. **COMPLETO**
   - Escribir tests unitarios por método. **(deferido, sync tests aplican)**

3) Integración y migración incremental — 1-2 días ✓
   - Actualizar DI (`dependencies.py`) y migrar call-sites críticos. **COMPLETO**
   - Mantener `AsyncMongoAdapter` durante esta fase para fallback. **COMPLETO**

4) Pruebas y benchmarking en staging — 1 día
   - Ejecutar scripts de carga y comparar con baseline. **(pendiente)**
   - Verificar errores y latencias bajo concurrencia. **(pendiente)**

5) Staged rollout y monitoreo — 1 día
   - Desplegar a un subconjunto de instancias (canary) o habilitar `MONGO_ASYNC_MODE`. **(pendiente)**
   - Monitorear métricas (latencia, errores, CPU, mem) por 1-2 horas. **(pendiente)**

6) Cleanup y remoción de fallback — 0.5-1 día
   - Eliminar `to_thread` wrappers y `AsyncMongoAdapter` fallback cuando seguro. **(pendiente)**

## Entregables por fase
- Scripts de benchmark reproducibles
- `AsyncMongoRepository` con tests
- PR de migración con lista de call-sites actualizados
- Dashboard de métricas comparativas

## Criterios para avanzar a la siguiente fase
- Tests unitarios y de integración pasan en CI.
- Benchmarks en staging muestran latencias aceptables o mejoras.
- No errores críticos en logs durante periodo de canary.
