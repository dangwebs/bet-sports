# Copilot Agents for HyperGenIA

This folder recreates the specialized agent setup from `.claude/agents` for GitHub Copilot custom agents.

## Available Agents

- `hypergenia-orchestrator.agent.md`
  - Intake, classification, delegation, and Spec Kit enforcement.
- `hypergenia-frontend.agent.md`
  - Next.js work in `Front/`.
- `hypergenia-backend.agent.md`
  - NestJS microservices work in `HyperGenIA/mono-ms/`.
- `hypergenia-architecture.agent.md`
  - Cross-domain/cross-service architecture and contracts.

## Default Tone

All agents default to caveman full: terse, direct, and compact. Keep this as the baseline unless a user asks for more detail.

## Spec Kit Compatibility

These agents are designed to work with Spec Kit prompts under `.github/prompts/`:

1. `/speckit.constitution`
2. `/speckit.specify` — generates `spec.md`, `plan.md`, and `tasks.md` in one continuous flow
3. implementation delegated to specialist agent
4. `/speckit.implement`

## Mapping to Existing Claude Setup

| Claude source | Copilot equivalent |
|---|---|
| `.claude/agents/orchestrator.md` | `orchestrator.agent.md` |
| `.claude/agents/frontend.md` | `frontend.agent.md` |
| `.claude/agents/backend.md` | `backend.agent.md` |
| `.claude/agents/architecture.md` | `architecture.agent.md` |
