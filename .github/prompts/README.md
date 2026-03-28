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

1. `Orchestrator` handles intake and routing.
2. `/speckit.specify` generates (or updates) the intervention specification.
3. `/speckit.plan` defines technical approach.
4. `/speckit.tasks` creates executable tasks.
5. Implementation starts only after the previous steps are completed.

### Hard Gate

- No code edits without a spec artifact (`spec.md`) for that intervention.
- If a code request reaches a specialist directly without spec context,
  it must be redirected to `Orchestrator` first.

