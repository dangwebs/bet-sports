---
name: "speckit.specify"
description: "Create a feature specification, plan, and tasks from a natural language description — full pipeline in one flow."
agent: "Orchestrator"
model: "Claude Opus 4.6 (copilot)"
argument-hint: "Describe the feature to specify"
---

## MANDATORY: Project Context Discovery

BEFORE generating any spec content, you MUST read project context to ground the specification in reality:

1. **Project identity**: Read `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, and `README.md` at repo root (skip if missing)
2. **Tech stack**: Read `package.json`, `pnpm-workspace.yaml`, `tsconfig.json`, `turbo.json`, or equivalent manifests
3. **Directory structure**: List top-level dirs and 2 levels deep in the feature's target area
4. **Existing code**: Read 1-2 files in the domain being specified to understand patterns, naming, and what already exists

This context is held in memory (not written to a file) and used to: use correct terminology, avoid specifying what already exists, scope realistically, and leverage existing infrastructure.

## Workflow

Follow the exact workflow and constraints defined in
[`../../.claude/commands/speckit.specify.md`](../../.claude/commands/speckit.specify.md).

This includes the **Automatic Pipeline Continuation** at the end, which mandates generating `plan.md` and `tasks.md` in the **same conversation thread** after the spec is complete. Do NOT stop after spec generation — the full pipeline (spec → plan → tasks) runs as one continuous flow.

For plan generation, follow [`../../.claude/commands/speckit.plan.md`](../../.claude/commands/speckit.plan.md).
For tasks generation, follow [`../../.claude/commands/speckit.tasks.md`](../../.claude/commands/speckit.tasks.md).

Apply it to this input:

`$ARGUMENTS`
