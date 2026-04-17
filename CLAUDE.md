# SpiderSecurity — Claude Code Memory

## Project Overview

Full-stack RPA/automation platform called **HyperGenIA**. Consists of a Next.js frontend and a NestJS microservices backend connected via gRPC, exposed through a GraphQL API Gateway.

## Default Tone

Use caveman by default: terse, direct, and compact. Keep replies short unless the user explicitly asks for more detail.

## Repository Structure

```
SpiderSecurity/
├── Front/                        # Next.js 15 frontend (React 19)
└── HyperGenIA/
    └── mono-ms/                  # Turborepo + pnpm workspaces (backend)
        ├── apps/
        │   ├── api-gateway/      # NestJS — GraphQL entry point (Apollo)
        │   ├── auth-svc/         # NestJS — JWT + MongoDB + Redis
        │   ├── user-svc/
        │   ├── tenant-svc/
        │   ├── billing-svc/
        │   ├── bot-svc/
        │   ├── bot-schedule-svc/
        │   ├── orchestrator-svc/
        │   ├── player-svc/
        │   ├── modeler-svc/
        │   ├── file-svc/
        │   ├── notify-svc/
        │   ├── signer-svc/
        │   ├── signerfile-svc/
        │   ├── transaction-svc/
        │   ├── license-svc/
        │   ├── password-vault-svc/
        │   ├── work-flow-svc/
        │   ├── audit-svc/
        │   ├── bill-gateway-svc/
        │   ├── chat-svc/
        │   └── manager/          # Internal management app
        └── packages/
            ├── api/              # Shared types / DTOs
            ├── common/           # Shared utilities
            ├── eslint-config/
            ├── jest-config/
            └── typescript-config/
```

## Tech Stack

### Frontend (`Front/`)
- **Framework**: Next.js 15 (App Router), React 19
- **Styling**: TailwindCSS, Flowbite React
- **API**: Apollo Client (GraphQL)
- **Auth**: next-auth v5 (beta)
- **i18n**: next-intl (en/es)
- **Forms**: React Hook Form + Zod
- **ORM**: Prisma (client only)
- **Package manager**: npm

### Backend (`HyperGenIA/mono-ms/`)
- **Framework**: NestJS 11 (TypeScript)
- **Monorepo**: Turborepo + pnpm workspaces
- **API style**: GraphQL (API Gateway → frontend), gRPC (inter-service)
- **Proto files**: `HyperGenIA/_proto/**/*.proto`
- **Database**: MongoDB (Mongoose)
- **Cache**: Redis (`@liaoliaots/nestjs-redis`)
- **Auth**: JWT (`@nestjs/jwt`), Passport
- **Testing**: Jest
- **Package manager**: pnpm 8

## Key Commands

### Frontend
```bash
cd Front
npm run dev          # Start dev server on :3000
npm run build        # Production build
npm run check        # Lint + typecheck
npm run format:write # Format code
```

### Backend (mono-ms)
```bash
cd HyperGenIA/mono-ms
pnpm dev             # Start all services (Turborepo)
pnpm build           # Build all services
pnpm test            # Run all tests
pnpm lint            # Lint all packages
pnpm format          # Format all files
```

### Individual service
```bash
cd HyperGenIA/mono-ms/apps/<service-name>
pnpm dev             # Watch mode
pnpm test            # Jest
pnpm build           # Compile
```

## Architecture & Conventions

### Backend (NestJS microservices)
- **API Gateway** is the ONLY service exposed to the frontend — it speaks GraphQL
- **All other services** communicate exclusively via gRPC
- gRPC contracts are in `HyperGenIA/_proto/<domain>/*.proto`
- Each service has its own MongoDB database (no shared DB)
- Module structure follows NestJS standard: `module → controller → service → repository`
- Shared code goes in `packages/api` (DTOs/types) or `packages/common` (utilities)
- Environment variables are validated per-service via `@nestjs/config`

### Frontend (Next.js)
- App Router with `[locale]` dynamic segment for i18n
- Apollo Client for all data fetching (no REST)
- Server Components for layout/data fetching, Client Components for interactivity
- Translation keys must be added to both `messages/en.json` and `messages/es.json`
- Global error handling via `error-boundary-wrapper.tsx`

### Code Quality
- TypeScript strict mode everywhere
- ESLint + Prettier configured at monorepo root
- No `any` types — use proper interfaces/types
- Zod schemas for all user input validation (frontend)
- Class-validator decorators for DTOs (backend)

## Agent Skills

Claude-specific skills live in `.claude/skills/`. The orchestrator (`.claude/skills/orchestrator/SKILL.md`) MUST be read first on every task. Available specialists: `frontend`, `backend`, `general`, `architecture`, `code-quality`, `clean-code`, `best-practices`, `devops`, `conventional-commits`, `design-patterns`, `software-architecture`, `linting`.

Sub-agents are in `.claude/agents/` (orchestrator entrypoint). Domain specialization is applied via `.claude/skills/`.
Workflows are in `.claude/workflows/`.

Copilot workspace agents live in `.github/agents/` and are documented in `.github/agents/README.md`.

Current files:
- `hypergenia-backend.agent.md`
- `hypergenia-frontend.agent.md`
- `hypergenia-architecture.agent.md`

## Security Notes
- Never commit `.env` files — use `.env.example` as templates
- JWT secrets are per-service environment variables
- All GraphQL mutations require authentication via `GqlAuthGuard`
- Input validation is mandatory at every service boundary
