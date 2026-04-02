# 🎯 BJJ - BetSports: Intelligent Betting Assistant

> **Sistema Avanzado de Predicción Deportiva con Persistencia SQL y Caché de Alto Rendimiento**

![BJJ BetSports](https://img.shields.io/badge/BJJ-BetSports-6366f1?style=for-the-badge&logo=dependabot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=white)
![Render](https://img.shields.io/badge/Render-Hosted-46E3B7?style=flat-square&logo=render&logoColor=white)

## 📋 Descripción General

**BJJ-BetSports** es una plataforma de análisis y predicción de fútbol diseñada para operar eficientemente en la nube, optimizando el consumo de recursos sin sacrificar la persistencia de datos históricos.

### Nueva Arquitectura Unificada (SSOT)

A diferencia de versiones anteriores, el sistema ahora utiliza una arquitectura de **Fuente Única de Verdad (Single Source of Truth)** centrada en base de datos relacional:

1.  **Persistencia Robusta**: Sustitución de Redis por **PostgreSQL**. Todos los resultados de entrenamiento, estadísticas globales y picks pre-calculados se almacenan de forma permanente en SQL.
2.  **Caché Multi-Capa (Ephemerality-Aware)**:
    - **L1 (Memoria)**: Acceso instantáneo en RAM para peticiones calientes.
    - **L2 (DiskCache)**: Almacenamiento local persistente (basado en archivos) para mitigar reinicios del servidor sin saturar la DB.
3.  **Imagen Unica Portable + Docker Compose**:
    - **Imagen del proyecto**: contiene backend, frontend y utilidades MLOps dentro del mismo artefacto Docker.
    - **Docker Compose (`backend-api`, `frontend`, `mlops-pipeline`)**: reutiliza esa imagen para ejecutar toda la plataforma sin bind mounts de código del host.
    - **API Runtime**: recupera estadísticas y predicciones desde persistencia/caché, evitando cálculos CPU-intensivos por request.

---

## ✨ Características Principales

### 🧠 Inteligencia Artificial

- **Modelo**: Random Forest Classifier (Optimizado para baja latencia).
- **Inferencia Instantánea**: Los picks se pre-calculan y persisten, permitiendo tiempos de respuesta de milisegundos.
- **Continuous Learning**: Ajuste dinámico de pesos basado en el feedback de aciertos/errores de apuestas anteriores.

### 🏗️ Ingeniería de Datos

- **Pipelines de Sincronización**: Sincronización automática entre el entrenamiento en CI/CD y la base de datos de producción.
- **Eficiencia de Memoria**: Arquitectura diseñada para correr en entornos de **512MB RAM**, moviendo cargas pesadas a procesos en segundo plano.

---

## 🛠️ Stack Tecnológico Actualizado

| Área              | Tecnología                  | Rol                                               |
| :---------------- | :-------------------------- | :------------------------------------------------ |
| **Backend**       | **Python 3.11 + FastAPI**   | Motor de API asíncrono.                           |
| **Base de Datos** | **PostgreSQL**              | Persistencia de largo plazo (SSOT).               |
| **Caché**         | **DiskCache (File-based)**  | Capa de aceleración local y persistencia efímera. |
| **ML Engine**     | **Scikit-learn**            | Inferencia y entrenamiento de modelos.            |
| **Frontend**      | **React 19 + Vite**         | Interfaz de usuario PWA de alto rendimiento.      |
| **Diseño**        | **Material UI v5**          | Sistema de componentes limpio y moderno.          |
| **Infra**         | **Docker Compose + Render** | Ejecución local portable, CI informativo y hosting. |

---

## 📂 Estructura Crítica del Proyecto

```bash
backend/src/
├── api/                    # Endpoints y rutas (FastAPI)
├── application/            # Casos de uso y Orquestación (SSOT logic)
├── domain/                 # Entidades y Lógica de Negocio
└── infrastructure/         # Capas de persistencia
    ├── cache/              # CacheService (Memoria + DiskCache)
    ├── data_sources/       # Integración con APIs de Fútbol
    └── repositories/       # PersistenceRepository (PostgreSQL)
```

---

## 🚀 Despliegue en Render (Nueva Configuración)

1.  Crea un **Web Service** para el Backend y una base de datos **PostgreSQL**.
2.  Enlaza la base de datos y configura las variables de entorno:
    - `DATABASE_URL`: URL de conexión a tu instancia de Postgres.
    - `DISABLE_ML_TRAINING`: `true` (Para el servicio de la API).
    - `RENDER`: `true` (Activa salvaguardas de memoria).
3.  El sistema inicializará automáticamente las tablas en el primer arranque.

---

## 🤖 Ciclo de Vida del Modelo (Local Portable)

El entrenamiento se ejecuta fuera de GitHub Actions y dentro de contenedores:

### Arquitectura portable

- `Dockerfile.portable`: imagen única del proyecto.
- `docker-compose.dev.yml`: orquesta MongoDB + backend + frontend + MLOps.
- No se requieren bind mounts del código para ejecutar el stack portable.

1. Levanta dependencias base:
    - `docker compose -f docker-compose.dev.yml up -d mongodb`
2. Ejecuta el pipeline MLOps local:
    - `./run_dev_pipeline.sh`
3. El script dispara `mlops-pipeline` en Compose y ejecuta:
    - `cleanup` -> `train` -> `predict` -> `top-picks`
4. Puedes ajustar recursos sin editar código:
    - `N_JOBS`, `TRAIN_DAYS`, `PREDICT_LEAGUES`
    - El default de `N_JOBS` usa una fracción conservadora del host; si necesitas más paralelismo, sobrescríbelo explícitamente.

### Ejecución full-stack local

Para levantar API + frontend + Mongo:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Para levantar también los jobs periódicos opcionales (`ml-worker`, `labeler`, `updater`):

```bash
docker compose -f docker-compose.dev.yml --profile automation up -d
```

### Rebuild canónico del stack portable

La forma canónica de reconstruir el stack portable es:

```bash
bash scripts/docker-rebuild-portable.sh
```

El script encapsula este comando exacto:

```bash
docker compose -f docker-compose.dev.yml up -d --build --force-recreate
```

Servicios expuestos:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- MongoDB: `localhost:27017`

Para ejecutar solo el pipeline MLOps:

```bash
docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline
```

## 📄 Disclaimer

Este software es para fines **educativos e investigativos**. Las predicciones estadísticas no garantizan resultados financieros. Juega con responsabilidad.

---

Desarrollado con ❤️ por [Jhorman Orozco](https://github.com/jhorman10)
