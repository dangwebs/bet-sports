# Tasks: DevOps / CI

1. Crear workflow `ci.yml` (PR validation)
   - Jobs: `lint` (backend/frontend), `test:backend` (pytest), `test:frontend` (npm test/build).
   - Añadir caching para pip/npm.
   - Estimación: 3h

2. Job `build` (imagen Docker)
   - Construir imagen reproducible usando `Dockerfile.portable` o `backend/Dockerfile` y almacenar como artefacto.
   - Estimación: 1–2h

3. Security scans
   - Integrar `bandit` o `safety` para Python y `npm audit` para frontend; fallar el job en vulnerabilidades críticas.
   - Estimación: 1–2h

4. Workflow `release.yml`
   - Automatizar build/tag y push a registry (opcional, protegido por secrets y manual approval para producción).
   - Estimación: 1–2h

5. Documentación y reproducibilidad local
   - `docs/ci.md` con pasos para ejecutar pipelines localmente (`tox`, `docker-compose --file docker-compose.dev.yml up --build`).
   - Estimación: 1h

6. Optimización y caching
   - Añadir cache de dependencias y split de jobs para reducir tiempo total de CI.
   - Estimación: 1–2h
