---
name: "speckit.implement"
description: "Execute implementation according to tasks.md and project constraints."
agent: "Orchestrator"
argument-hint: "Optional implementation notes"
---

## MANDATORY: Project Context Discovery

BEFORE any implementation, you MUST read project context to write code that matches existing conventions EXACTLY:

1. **Project identity**: Read `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, and `README.md` at repo root (skip if missing)
2. **Tech stack**: Read `package.json`, `pnpm-workspace.yaml`, `tsconfig.json`, `turbo.json`, or equivalent manifests
3. **Directory structure**: List top-level dirs and 2 levels deep in the feature's target area
4. **Existing code**: Read 2-3 files in the domain being modified to understand import conventions, naming, code style, patterns, error handling, and state management

This context is held in memory (not written to a file) and used to: write code indistinguishable from the rest of the codebase, use exact import paths and naming conventions, follow existing error handling and state management, and reuse shared code.

## Workflow

Follow the exact workflow and constraints defined in
[`../../.claude/commands/speckit.implement.md`](../../.claude/commands/speckit.implement.md).

Apply it to this input:

`$ARGUMENTS`
