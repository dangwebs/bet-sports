---
name: devops
description: "DevOps specialist: Docker, Docker Compose, CI/CD pipelines, environment configuration, secrets management, GitHub Actions, and deployment. Activate for infrastructure, containerization, and pipeline tasks."
---

# DevOps Skill

## Discovery (Mandatory First Step)

Before writing any infrastructure code, check:
- `Dockerfile` files per service — identify base images and build stages.
- `docker-compose.dev.yml` / `docker-compose.test.yml` at `HyperGenIA/mono-ms/`.
- `.env.example` files for environment variable contracts.
- `.github/workflows/` for existing CI/CD pipelines.

## Docker Conventions

### Dockerfile Best Practices

- **Multi-stage builds**: Always use `builder` and `runner` stages to minimize final image size.
- **Non-root user**: Always run the app as a non-root user in production images.
- **Pinned base images**: Use specific versions, never `latest` (e.g., `node:20.11-alpine3.19`).
- **`.dockerignore`**: Always define it — exclude `node_modules`, `.env`, `dist`, `logs`, `*.spec.ts`.
- **Layer caching**: Copy `package.json`/`pnpm-lock.yaml` and run install BEFORE copying source code.
- **Health checks**: Define `HEALTHCHECK` for every service container.

```dockerfile
# ✅ Correct multi-stage pattern for NestJS services
FROM node:20.11-alpine3.19 AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:20.11-alpine3.19 AS runner
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/main"]
```

### Docker Compose Conventions

- **Service isolation**: Each service in its own container, networked via Docker internal DNS.
- **Named volumes**: Always use named volumes for persistent data (MongoDB, Redis) — never anonymous ones.
- **Resource limits**: Define `mem_limit` and `cpus` for production compose files.
- **Depends_on with condition**: Use `condition: service_healthy` to ensure service ordering.
- **Environment from files**: Use `env_file: .env` — never inline secrets in compose files.

```yaml
# ✅ Service with health check dependency
auth-svc:
  build: ./apps/auth-svc
  depends_on:
    mongo:
      condition: service_healthy
    redis:
      condition: service_healthy
  env_file: .env
  restart: unless-stopped
```

## Environment Variables

- **`.env.example`** must exist for every service — it is the documentation for required vars.
- **`.env`** is NEVER committed — add to `.gitignore`.
- **Validation at startup**: Use `@nestjs/config` with a Joi/Zod validation schema. The app must crash on startup if required env vars are missing.
- **Naming convention**: `SCREAMING_SNAKE_CASE` — `DATABASE_URL`, `JWT_SECRET`, `GRPC_PORT`.
- **Secrets**: Never in env vars committed to git. Use a secrets manager (Vault, AWS Secrets Manager, GitHub Secrets) for production.

```typescript
// ✅ Config validation with Joi at service startup
export const configValidationSchema = Joi.object({
  NODE_ENV: Joi.string().valid('development', 'production', 'test').required(),
  PORT: Joi.number().default(3000),
  MONGODB_URI: Joi.string().required(),
  JWT_SECRET: Joi.string().min(32).required(),
  REDIS_HOST: Joi.string().required(),
  REDIS_PORT: Joi.number().default(6379),
});
```

## CI/CD — GitHub Actions

### Pipeline Structure

Every service should have a CI pipeline with these stages:

```yaml
# .github/workflows/ci.yml
stages:
  - lint          # ESLint + Prettier check
  - typecheck     # tsc --noEmit
  - test          # Jest unit tests
  - build         # nest build / next build
  - docker-build  # Build and push Docker image (main branch only)
  - deploy        # Deploy to environment (main branch only)
```

### GitHub Actions Best Practices

- **Pinned action versions**: `actions/checkout@v4`, NOT `actions/checkout@main`.
- **Secrets via env**: Never hardcode secrets in workflow files — use `${{ secrets.NAME }}`.
- **Caching**: Cache `node_modules` and the pnpm store to speed up CI.
- **Fail fast**: Put fastest checks first (lint, typecheck) before expensive ones (tests, build).
- **Matrix builds**: Use matrix strategy for multi-service repos to test all services in parallel.

```yaml
# ✅ pnpm caching in GitHub Actions
- name: Setup pnpm
  uses: pnpm/action-setup@v3
  with:
    version: 8

- name: Cache pnpm store
  uses: actions/cache@v4
  with:
    path: ~/.pnpm-store
    key: ${{ runner.os }}-pnpm-${{ hashFiles('**/pnpm-lock.yaml') }}
    restore-keys: ${{ runner.os }}-pnpm-
```

## Logging & Observability

- **Structured JSON logs**: All logs must be JSON (Winston is already configured in each service).
- **Log levels**: `error` for failures, `warn` for degraded states, `info` for lifecycle events, `debug` for development only.
- **Request correlation**: Propagate a `requestId` / `correlationId` through all log entries for a transaction.
- **Never log secrets**: Sanitize incoming request bodies before logging — remove `password`, `token`, `secret`.

## Security in Infrastructure

- **Network isolation**: Services in Docker should NOT expose ports to the host unless required.
- **Read-only filesystems**: Mount app containers with `read_only: true` in production.
- **Image scanning**: Scan Docker images for vulnerabilities before deployment (`trivy`, `snyk`).
- **Least-privilege service accounts**: Each service account should only have access to its own database and Redis namespace.
