# 🚀 Optimización MLOps Pipeline para GitHub Actions

## 📋 Resumen de Optimizaciones

### Antes vs Después

| Métrica                   | Antes                | Después            | Mejora      |
| ------------------------- | -------------------- | ------------------ | ----------- |
| **Jobs paralelos**        | 4 grupos             | 17 grupos          | **+325%**   |
| **CPUs por job**          | 1 core (por defecto) | 2 cores            | **+100%**   |
| **Procesamiento interno** | Secuencial           | Paralelo (asyncio) | **~40-60%** |
| **Tiempo estimado**       | ~40-60 min           | ~15-25 min         | **~50-60%** |

### ✨ Características

1. **17 jobs paralelos** en lugar de 4 (máximo permitido: 20 en tier gratuito)
2. **Uso de ambos cores** disponibles (2 CPUs en GitHub Actions)
3. **Procesamiento paralelo** dentro de cada job con `asyncio.gather()`
4. **Variables de entorno** optimizadas para NumPy, OpenBLAS, MKL
5. **Compresión mejorada** de artifacts (nivel 9)
6. **Logging detallado** con emojis para mejor visualización

---

## 📁 Archivos Incluidos

### 1. `enterprise_daily_mlops.yml`

**Ubicación:** `.github/workflows/enterprise_daily_mlops.yml`

Workflow de GitHub Actions optimizado con:

- 17 grupos de ligas para máximo paralelismo
- Variables de entorno para multi-threading
- Compresión máxima de artifacts
- Summary reports automáticos

### 2. `orchestrator_cli.py`

**Ubicación:** `backend/scripts/orchestrator_cli.py`

Script CLI optimizado con:

- Auto-detección de CPUs disponibles
- Procesamiento paralelo de múltiples ligas
- Parámetro `--n-jobs` para control manual
- Logging mejorado con emojis y contadores

---

## 🔧 Instalación

### Paso 1: Reemplazar el workflow de GitHub Actions

```bash
# Desde la raíz de tu repositorio
cp enterprise_daily_mlops.yml .github/workflows/enterprise_daily_mlops.yml
```

### Paso 2: Reemplazar el script orchestrator

```bash
# Desde la raíz de tu repositorio
cp orchestrator_cli.py backend/scripts/orchestrator_cli.py
```

### Paso 3: Commit y push

```bash
git add .github/workflows/enterprise_daily_mlops.yml
git add backend/scripts/orchestrator_cli.py
git commit -m "⚡ Optimize MLOps pipeline for maximum parallelism"
git push
```

---

## 🎯 Uso

### Ejecución Automática

El workflow se ejecuta automáticamente cada 6 horas según el cron configurado.

### Ejecución Manual

1. Ve a **Actions** en tu repositorio de GitHub
2. Selecciona **"Enterprise Daily MLOps"**
3. Click en **"Run workflow"**
4. Opcionalmente marca **"Force Retraining"**

### Uso Local (Desarrollo)

```bash
# Training con 2 cores
python backend/scripts/orchestrator_cli.py train --days 400 --n-jobs 2

# Predicciones en paralelo
python backend/scripts/orchestrator_cli.py predict --leagues "E0,E1,E2" --parallel

# Predicciones secuenciales (fallback)
python backend/scripts/orchestrator_cli.py predict --leagues "E0,E1" --sequential

# Generar top picks
python backend/scripts/orchestrator_cli.py top-picks
```

---

## ⚙️ Configuración Avanzada

### Variables de Entorno

El workflow configura automáticamente:

```yaml
OMP_NUM_THREADS: 2 # OpenMP threads
OPENBLAS_NUM_THREADS: 2 # OpenBLAS threads
MKL_NUM_THREADS: 2 # Intel MKL threads
NUMEXPR_NUM_THREADS: 2 # NumExpr threads
N_JOBS: 2 # Scikit-learn / XGBoost jobs
```

### Modificar Paralelismo del Matrix

Si quieres ajustar los grupos de ligas:

```yaml
matrix:
  include:
    - group: "Custom_Group_1"
      leagues: "E0,E1"
    - group: "Custom_Group_2"
      leagues: "D1,D2"
    # ... hasta 20 grupos máximo
```

### Modificar Timeout

```yaml
timeout-minutes: 45 # Ajusta según tus necesidades
```

---

## 📊 Monitoreo

### En GitHub Actions

Cada ejecución muestra:

- ✅ Jobs completados exitosamente
- ❌ Jobs fallidos (no bloquean otros jobs)
- 📊 Summary report al final
- 📧 Issue automático si falla el pipeline completo

### Logs Mejorados

```
🚀 Running with 2 CPU cores
🔄 Processing League: E0
✅ Saved 15 predictions for E0
📊 Results: ✅ 3 succeeded, ❌ 0 failed
```

---

## 🔍 Troubleshooting

### Error: "n_jobs parameter not supported"

Si tu `orchestrator.run_training_pipeline()` no soporta `n_jobs`:

**Opción 1:** Modifica tu orchestrator para aceptar el parámetro:

```python
async def run_training_pipeline(self, league_ids, days_back, n_jobs=1):
    # Pasa n_jobs a tus modelos ML
    self.model = RandomForestClassifier(n_jobs=n_jobs)
```

**Opción 2:** Usa variables de entorno (ya configuradas en el workflow):

```python
import os
n_jobs = int(os.getenv('N_JOBS', 1))
self.model = RandomForestClassifier(n_jobs=n_jobs)
```

### Jobs Fallando por Rate Limits

Si las APIs externas tienen rate limits, considera:

```yaml
strategy:
  max-parallel: 10 # Reducir de 20 a 10
```

### Memoria Insuficiente

GitHub Actions tiene 7GB RAM. Si te quedas sin memoria:

- Reduce `--days` en training (400 → 200)
- Procesa menos ligas por grupo
- Usa `--sequential` en lugar de `--parallel`

---

## 📈 Métricas de Rendimiento

### Recursos Utilizados (GitHub Actions Free Tier)

- **CPUs:** 2 cores por job
- **RAM:** 7 GB por job
- **Storage:** 14 GB SSD por job
- **Jobs concurrentes:** 20 máximo
- **Tiempo límite:** 6 horas por job

### Benchmark Esperado

Con las optimizaciones:

- Training: ~10-15 min (depende de days_back)
- Predicciones: ~3-5 min por grupo
- Total pipeline: ~20-30 min (vs ~45-60 min anterior)

---

## 🤝 Soporte

Si encuentras problemas:

1. Revisa los logs en GitHub Actions
2. Verifica que los secrets estén configurados
3. Confirma que las dependencias están actualizadas
4. Abre un issue con los logs relevantes

---

## 📝 Notas Adicionales

### Compatibilidad con tu Código Existente

Estos cambios son **retrocompatibles**:

- ✅ Funciona con código legacy sin modificaciones
- ✅ Parámetros nuevos son opcionales
- ✅ Fallback a modo secuencial si falla el paralelo

### Próximas Optimizaciones Posibles

1. **Caché de dependencias mejorado** con hash del requirements
2. **Predicciones incrementales** (solo nuevos partidos)
3. **Matrix dinámico** basado en fixtures disponibles
4. **Warm-up de la base de datos** antes de predicciones

---

## 📄 Licencia

Estos archivos son parte de tu proyecto existente. Mantienen la misma licencia.

---
