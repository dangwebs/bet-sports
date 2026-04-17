---
name: "speckit.plan"
description: "Generate the implementation planning artifacts from the approved spec."
agent: "Orchestrator"
model: "Claude Opus 4.6 (copilot)"
argument-hint: "Optional planning constraints or context"
---

## MANDATORY: Project Context Discovery

BEFORE generating the plan, you MUST read project context to produce a plan grounded in the real codebase:

1. **Project identity**: Read `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, and `README.md` at repo root (skip if missing)
2. **Tech stack**: Read `package.json`, `pnpm-workspace.yaml`, `tsconfig.json`, `turbo.json`, or equivalent manifests
3. **Directory structure**: List top-level dirs and 2 levels deep in the feature's target area
4. **Existing code**: Read 1-2 files in the domain being planned to understand current architecture and patterns

This context is held in memory (not written to a file) and used to: select appropriate technical approaches, propose consistent data models, design contracts following established patterns, and avoid recommending foreign technologies.

## Workflow

Follow the exact workflow and constraints defined in
[`../../.claude/commands/speckit.plan.md`](../../.claude/commands/speckit.plan.md).

Apply it to this input:

`$ARGUMENTS`
