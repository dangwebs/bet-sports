# Copilot Agents for BJJ-BetSports

This folder defines the specialized agent setup for this repository and keeps Copilot aligned with `RULES.md`.

## Available Agents

- `hypergenia-orchestrator.agent.md`
  - Intake, classification, delegation, and Spec Kit enforcement.
- `hypergenia-frontend.agent.md`
  - React + Vite + MUI work in `frontend/`.
- `hypergenia-backend.agent.md`
  - FastAPI + Python + ML/worker work in `backend/`.
- `hypergenia-architecture.agent.md`
  - Cross-domain architecture, data flow, and infrastructure decisions.

## Spec Kit Compatibility

These agents are designed to work with Spec Kit prompts under `.github/prompts/`:

1. `/speckit.constitution`
2. `/speckit.specify`
3. `/speckit.plan`
4. `/speckit.tasks`
5. implementation delegated to specialist agent
6. `/speckit.implement`

## Mandatory Rules Alignment

- `RULES.md` is mandatory for all specialists.
- All responses must be in Spanish.
- Any code-changing task must go through the orchestrator and specs-first flow.

## Shared Skills Baseline

To keep a consistent experience across all agents, every agent uses the same base skills from `.github/skills/`:

- `orchestrator`
- `architecture`
- `frontend`
- `backend`
- `general`
- `code-quality`
- `clean-code`
- `best-practices`
- `linting`
- `design-patterns`
- `software-architecture`
- `devops`
- `conventional-commits`

## Mapping to Existing Claude Setup

| Claude source | Copilot equivalent |
|---|---|
| `.claude/agents/orchestrator.md` | `hypergenia-orchestrator.agent.md` |
| `.claude/agents/frontend.md` | `hypergenia-frontend.agent.md` |
| `.claude/agents/backend.md` | `hypergenia-backend.agent.md` |
| `.claude/agents/architecture.md` | `hypergenia-architecture.agent.md` |
