---
name: devops
description: "DevOps specialist: Docker, Docker Compose, CI/CD pipelines, environment configuration, secrets management, GitHub Actions, and deployment. Activate for infrastructure, containerization, and pipeline tasks."
---

# DevOps Skill

## Discovery (Mandatory First Step)

Before writing any infrastructure code, find and read:

1. All `Dockerfile` files — identify base images, build stages, and patterns.
2. All `docker-compose*.yml` files — understand service topology.
3. `.env.example` files — document the environment variable contract.
4. `.github/workflows/` — review existing CI/CD pipelines.
5. `.dockerignore` files — verify exclusions.

## Docker Conventions

### Dockerfile Best Practices

- **Multi-stage builds**: Always use `builder` and `runner` stages to minimize final image size.
- **Non-root user**: Always run the app as a non-root user in production images.
- **Pinned base images**: Use specific versions, never `latest` (e.g., `node:20.11-alpine3.19`).
- **`.dockerignore`**: Always define it — exclude dependency dirs, `.env`, build output, logs, test files.
- **Layer caching**: Copy dependency manifests and install BEFORE copying source code.
- **Health checks**: Define `HEALTHCHECK` for every service container.

```dockerfile
# ✅ Generic multi-stage pattern
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json lockfile* ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/main"]
```

Adapt the install command (`npm ci`, `pnpm install --frozen-lockfile`, `yarn --frozen-lockfile`) and build output path to match the project.

### Docker Compose Conventions

- **Service isolation**: Each service in its own container, networked via Docker internal DNS.
- **Named volumes**: Always use named volumes for persistent data — never anonymous ones.
- **Resource limits**: Define `mem_limit` and `cpus` for production compose files.
- **Depends_on with condition**: Use `condition: service_healthy` to ensure service ordering.
- **Environment from files**: Use `env_file: .env` — never inline secrets in compose files.

```yaml
# ✅ Service with health check dependency
my-service:
  build: ./path/to/service
  depends_on:
    database:
      condition: service_healthy
  env_file: .env
  restart: unless-stopped
```

## Environment Variables

- **`.env.example`** must exist for every service — it documents required vars.
- **`.env`** is NEVER committed — add to `.gitignore`.
- **Validation at startup**: Use the project's config validation library. The app must crash on startup if required env vars are missing.
- **Naming convention**: `SCREAMING_SNAKE_CASE` — `DATABASE_URL`, `JWT_SECRET`, `PORT`.
- **Secrets**: Never in env vars committed to git. Use a secrets manager (Vault, AWS Secrets Manager, GitHub Secrets) for production.

## CI/CD — GitHub Actions

### Pipeline Structure

Every project should have a CI pipeline with these stages:

```yaml
stages:
  - lint          # Linter + formatter check
  - typecheck     # tsc --noEmit (or equivalent)
  - test          # Unit tests
  - build         # Production build
  - docker-build  # Build and push Docker image (main branch only)
  - deploy        # Deploy to environment (main branch only)
```

### GitHub Actions Best Practices

- **Pinned action versions**: `actions/checkout@v4`, NOT `actions/checkout@main`.
- **Secrets via env**: Never hardcode secrets in workflow files — use `${{ secrets.NAME }}`.
- **Caching**: Cache dependency directories and package manager stores to speed up CI.
- **Fail fast**: Put fastest checks first (lint, typecheck) before expensive ones (tests, build).
- **Matrix builds**: Use matrix strategy for multi-service repos to test all services in parallel.

## Logging & Observability

- **Structured JSON logs**: All logs must be structured (JSON preferred).
- **Log levels**: `error` for failures, `warn` for degraded states, `info` for lifecycle events, `debug` for development only.
- **Request correlation**: Propagate a `requestId` / `correlationId` through all log entries.
- **Never log secrets**: Sanitize incoming request bodies before logging — remove `password`, `token`, `secret`.

## Security in Infrastructure

- **Network isolation**: Services in Docker should NOT expose ports to the host unless required.
- **Read-only filesystems**: Mount app containers with `read_only: true` in production.
- **Image scanning**: Scan Docker images for vulnerabilities before deployment (`trivy`, `snyk`).
- **Least-privilege service accounts**: Each service account should only have access to its own resources.
