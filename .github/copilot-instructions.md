# Copilot Instructions — BJJ-BetSports

## Scope

These instructions apply to the whole workspace.

## Language

- Respond in the same language as the user.
- For this repository, default to Spanish (see `RULES.md`).

## Mandatory Orchestration

- Start with task classification (frontend, backend, architecture, or general).
- Use the project specialists in `.github/agents/` for domain execution:
  - `Orchestrator`
  - `Frontend`
  - `Backend`
  - `Architecture`
- Any request that may modify code MUST be routed through `Orchestrator` first.
- Specialists (`Frontend`, `Backend`, `Architecture`) MUST NOT start implementation directly from first contact.

## Specs-First Workflow (required for code changes)

For any feature, bug fix with code edits, or refactor, follow this sequence before implementation:

1. `/speckit.constitution` (when principles are missing/outdated)
2. `/speckit.specify`
3. `/speckit.plan`
4. `/speckit.tasks`
5. implement from generated tasks (`/speckit.implement` or equivalent)

### Hard Gate (Mandatory)

- No code edits are allowed before a feature specification exists for the intervention.
- Minimum required artifact before coding: `spec.md` generated via `/speckit.specify`.
- For any code intervention, the expected path is:
  `Orchestrator` → `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → implementation.
- If a request arrives directly to a specialist with no spec context, the specialist must stop and redirect to `Orchestrator`.

For read-only questions or explanations with no code changes, answer directly.

## Project Boundaries

- Frontend work: `frontend/` (React 19 + Vite + Material UI)
- Backend work: `backend/` (FastAPI + Python + ML worker pipeline)
- Operational scripts: `scripts/`
- Project rules source of truth: `RULES.md`

## Engineering Rules

- Follow `RULES.md` as mandatory policy.
- Keep strict typing; avoid `any` (TypeScript) and keep full type hints in Python.
- Keep changes small, testable, and aligned with existing structure.
- Preserve existing lint/format rules; avoid unrelated refactors.

## Quality Gates Before Finishing

- Validate edits for lint/type errors.
- Frontend: run `cd frontend && npm run lint` and `cd frontend && npm run build` when relevant.
- Backend: run `cd backend && pytest -v` for affected logic when relevant.
- Ensure task status/progress is updated when working from Spec Kit artifacts.

## Sources of Truth

- Agent definitions: `.github/agents/`
- Spec Kit prompts: `.github/prompts/`
- Legacy/extended guidance: `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`
