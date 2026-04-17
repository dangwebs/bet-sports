# Spec Kit Prompts for Copilot

This folder exposes Spec Kit workflows as Copilot slash prompts.

## Available Prompts

- `/speckit.constitution`
- `/speckit.specify`
- `/speckit.clarify`
- `/speckit.plan`
- `/speckit.tasks`
- `/speckit.analyze`
- `/speckit.checklist`
- `/speckit.implement`
- `/speckit.taskstoissues`

## Compatibility Strategy

Each `.prompt.md` delegates to the corresponding command definition in
`.claude/commands/` to avoid behavior drift and keep a single source of truth.

## Mandatory Policy for Code Interventions

Any activity that implies code modification must follow this mandatory path:

1. The **Orchestrator** handles intake and routing.
2. `/speckit.specify` generates the intervention specification, plan, and tasks in one continuous flow.
3. Implementation starts only after the previous steps are completed.

### Hard Gate

- No code edits without the full pipeline artifacts (`spec.md`, `plan.md`, `tasks.md`) for that intervention.
- If a code request reaches a specialist directly without spec context,
  it must be redirected to the **Orchestrator** first.
