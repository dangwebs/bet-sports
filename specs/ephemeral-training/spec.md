# Spec: Entrenamiento Efímero (sin persistencia de modelos en disco)

Fecha: 2026-04-01

## Resumen

El pipeline de entrenamiento debe dejar de persistir modelos ML como archivos `.joblib` en disco. El entrenamiento seguirá ocurriendo, pero los modelos solo vivirán en memoria durante el ciclo de entrenamiento e inferencia. El resultado persistente del proceso será exclusivamente la data guardada en MongoDB: predicciones, métricas y resultados de entrenamiento.

## Contexto

Actualmente el pipeline entrena modelos ML (`RandomForest`) y los persiste como archivos `.joblib` en disco (`ml_models/`, `ml_picks_classifier.joblib`). Después, distintos servicios intentan recargar esos archivos desde el filesystem para enriquecer predicciones.

Este comportamiento genera tres problemas:

1. Los modelos en disco quedan obsoletos con rapidez frente a nuevas corridas.
2. Se introduce acoplamiento innecesario al filesystem local.
3. El sistema ya persiste el verdadero artefacto de negocio en MongoDB: predicciones, resultados y métricas.

## Objetivo

Cambiar el flujo para que funcione así:

1. Entrenar modelos en memoria.
2. Generar predicciones con esos modelos en memoria.
3. Guardar predicciones y resultados del entrenamiento en la base de datos.
4. Eliminar cualquier `.joblib` existente al finalizar la corrida.
5. Permitir que el resto del sistema degrade con lógica estadística cuando no existan modelos en disco.

## Requisitos Funcionales

### REQ-ET-1: Entrenamiento sin persistencia local

- `backend/src/application/services/ml_training_orchestrator.py` no debe escribir `ml_picks_classifier.joblib`.
- `backend/scripts/train_model_optimized.py` no debe escribir archivos `ml_models/*.joblib`.
- Los modelos entrenados deben seguir disponibles en memoria durante la misma ejecución para generar inferencia inmediata.

### REQ-ET-2: Limpieza explícita de artefactos previos

- Al finalizar una corrida exitosa o parcialmente exitosa, el sistema debe eliminar archivos `.joblib` previamente existentes en:
	- `backend/ml_models/`
	- la raíz del backend para `ml_picks_classifier.joblib`
- La limpieza debe registrar logs con el resultado por archivo o por lote.
- La limpieza no debe romper la corrida si un archivo no existe o no puede eliminarse; debe loguearse el incidente.

### REQ-ET-3: Persistencia canónica en base de datos

- Las predicciones generadas por el entrenamiento deben seguir guardándose en MongoDB mediante `bulk_save_predictions`.
- Los resultados agregados del entrenamiento deben seguir guardándose en MongoDB mediante `save_training_result` o el mecanismo actual equivalente.
- La base de datos debe ser la fuente de verdad para consultar resultados ya generados.

### REQ-ET-4: Fallback operativo sin modelos locales

- `PredictionService._get_model()` debe continuar retornando `None` cuando no exista un archivo local.
- `PicksService` debe tratar la ausencia del modelo en disco como una condición esperada, no como una anomalía operativa severa.
- El sistema debe seguir funcionando con lógica estadística base cuando no haya modelos cargables desde disco.

### REQ-ET-5: Compatibilidad con scheduler y flujo diario

- El `scheduler` diario no debe requerir cambios de comportamiento externos para seguir:
	- entrenando,
	- generando predicciones,
	- guardando resultados en caché y MongoDB.
- La eliminación de persistencia local no debe impedir que la corrida diaria termine con predicciones disponibles en BD.

## Escenarios de Aceptación

### Escenario 1: Corrida completa de entrenamiento

- Dado un ciclo de entrenamiento con data suficiente,
- cuando el pipeline entrena y genera predicciones,
- entonces las predicciones deben quedar persistidas en MongoDB,
- y no debe quedar ningún archivo `.joblib` generado por esa corrida en disco.

### Escenario 2: Existen modelos viejos en disco

- Dado que existen archivos `.joblib` de corridas previas,
- cuando finaliza una nueva corrida,
- entonces esos archivos deben ser eliminados,
- y la limpieza debe quedar registrada en logs.

### Escenario 3: No hay modelos en disco al momento de predecir

- Dado que no existen archivos `.joblib` en el filesystem,
- cuando un servicio intenta resolver modelos locales,
- entonces debe continuar operando con fallback estadístico,
- y no debe fallar toda la predicción por ausencia del archivo.

### Escenario 4: Falla parcial en la limpieza

- Dado que uno o más archivos `.joblib` no pueden eliminarse,
- cuando corre la etapa de cleanup,
- entonces el sistema debe registrar el error,
- y no debe perder las predicciones ya guardadas en MongoDB.

## Criterios de Aceptación

- AC-1: No quedan llamadas activas a `joblib.dump(...)` en el flujo de entrenamiento operativo.
- AC-2: `ml_training_orchestrator.py` ya no persiste `ml_picks_classifier.joblib`.
- AC-3: `train_model_optimized.py` ya no persiste modelos por liga en `ml_models/`.
- AC-4: Existe una limpieza explícita de archivos `.joblib` al finalizar el entrenamiento.
- AC-5: La ausencia de modelos en disco no rompe el fallback actual de predicción.

## Impacto Técnico

| Archivo | Cambio esperado |
|---------|-----------------|
| `backend/src/application/services/ml_training_orchestrator.py` | Eliminar persistencia a disco y agregar cleanup |
| `backend/scripts/train_model_optimized.py` | Mantener modelos en memoria, quitar `joblib.dump`, agregar cleanup |
| `backend/src/domain/services/prediction_service.py` | Mantener fallback sin archivo local |
| `backend/src/domain/services/picks_service.py` | Tratar la ausencia de modelo en disco como comportamiento esperado |

## Restricciones

- **Graceful Degradation** (`RULES.md` §7): si no existe modelo en disco, el sistema debe continuar con lógica estadística base.
- **Trazabilidad** (`RULES.md` §12): las predicciones guardadas deben conservar metadatos del modelo y de la corrida.
- **No romper el scheduler**: el flujo diario debe seguir publicando resultados a caché y MongoDB.
- **Sin migración de almacenamiento de modelos**: este cambio no serializa modelos en MongoDB ni en otro backend.

## Riesgos

- Si algún punto del sistema dependía implícitamente del filesystem, ese punto quedará expuesto una vez desaparezcan los `.joblib`.
- Si el entrenamiento falla antes de generar predicciones, no habrá artefactos locales que reutilizar. La mitigación es el fallback estadístico ya existente.

## Fuera de Alcance

- Migrar modelos entrenados a MongoDB.
- Rediseñar el algoritmo de entrenamiento o la arquitectura de inferencia.
- Cambiar el formato de los documentos de predicción ya guardados en base de datos.
