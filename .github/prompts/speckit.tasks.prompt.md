---
name: "speckit.tasks"
description: "Generate dependency-ordered executable tasks from the feature design artifacts."
agent: "Orchestrator"
argument-hint: "Optional task generation preferences"
---

## MANDATORY: Project Context Discovery

BEFORE generating tasks, you MUST read project context to generate tasks with correct file paths, naming, and patterns:

1. **Project identity**: Read `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, and `README.md` at repo root (skip if missing)
2. **Tech stack**: Read `package.json`, `pnpm-workspace.yaml`, `tsconfig.json`, `turbo.json`, or equivalent manifests
3. **Directory structure**: List top-level dirs and 2 levels deep in the feature's target area
4. **Existing code**: Read 2-3 files in the target domain to understand patterns, imports, naming, and file structure

This context is held in memory (not written to a file) and used to: generate tasks with CORRECT file paths, use exact import conventions, include realistic inline Pattern examples, reference existing utilities/types/services, and avoid tasks for existing infrastructure.

## Workflow

Follow the exact workflow and constraints defined in
[`../../.claude/commands/speckit.tasks.md`](../../.claude/commands/speckit.tasks.md).

Apply it to this input:

`$ARGUMENTS`
