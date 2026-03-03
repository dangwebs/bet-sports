# Workspace Agent Rules

## 🔒 Mandatory First Step: Orchestrator Activation

**On EVERY user prompt**, before doing anything else, you MUST:

1. **Read** the orchestrator skill at `.agent/skills/orchestrator/SKILL.md`
2. **Follow** the orchestrator's full workflow (classify → announce → activate → execute)

This applies to ALL prompts — questions, feature requests, bug fixes, refactoring, reviews, etc.

> The orchestrator will determine which specialist skills to activate. Do NOT skip this step. Do NOT guess which skills to use without reading the orchestrator first.

### Specialist Skills Available

| Skill          | Path                                  | Scope                                       |
| -------------- | ------------------------------------- | ------------------------------------------- |
| `frontend`     | `.agent/skills/frontend/SKILL.md`     | Everything in the frontend directory        |
| `backend`      | `.agent/skills/backend/SKILL.md`      | Everything in the backend directory         |
| `general`      | `.agent/skills/general/SKILL.md`      | CLI, libraries, ML, scripts, non-web code   |
| `architecture` | `.agent/skills/architecture/SKILL.md` | Cross-cutting, system design                |
| `code-quality` | `.agent/skills/code-quality/SKILL.md` | Clean code, SOLID, typing, linting, commits |
| `orchestrator` | `.agent/skills/orchestrator/SKILL.md` | Task routing & decomposition (always-on)    |

## Language

Respond in the same language the user writes in.
