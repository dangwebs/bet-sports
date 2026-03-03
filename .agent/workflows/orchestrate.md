---
description: Explicitly orchestrate a complex task across frontend, backend, and architecture using specialized sub-agent skills
---

# Orchestrate Task Workflow (`/orchestrate`)

> **When to use this**: The orchestrator is already always-on (via `AGENTS.md`). Use `/orchestrate` explicitly only when you want to force the **full decomposition and phased execution** for a complex, multi-skill task — e.g., a full-stack feature that needs a structured plan before any code is written.

## Steps

1. **Read the orchestrator skill**:

   ```
   Read .agent/skills/orchestrator/SKILL.md
   ```

2. **Classify the task** using the orchestrator's classification tree.

3. **Run Discovery** on all relevant parts of the project (check dependency files, folder structure, existing patterns).

4. **Read the relevant specialist skill(s)**:
   - Frontend tasks → `.agent/skills/frontend/SKILL.md`
   - Backend tasks → `.agent/skills/backend/SKILL.md`
   - Non-web tasks → `.agent/skills/general/SKILL.md`
   - Cross-cutting tasks → `.agent/skills/architecture/SKILL.md`
   - All code tasks → `.agent/skills/code-quality/SKILL.md`

5. **Decompose the task** into ordered sub-tasks with explicit dependencies (as per orchestrator Step 3).

6. **Execute each sub-task** following the conventions from the relevant specialist skill.

7. **Apply code-quality rules** to all written or modified code (linting, typing, formatting, imports).

8. **Run integration checks** from the orchestrator's Step 5 checklist.

9. **Generate commit message** following the `code-quality` skill's Conventional Commits section.
