---
name: project-memory-context
description: 'Load and maintain project memory/context from /memories for specs, prompts, recall, prior decisions, architecture context, and post-task discoveries. Use when the user asks for contexto del proyecto, recuerda que hicimos, spec drafting, prompt grounding, or reusable repo knowledge.'
argument-hint: 'Tarea, spec o prompt que necesita contexto del proyecto'
---

# Project Memory Context

Use this skill to turn project memory into working context before writing specs or answering context-sensitive prompts, then persist new findings so future agents start from verified knowledge instead of re-discovering the repo.

## When to Use

- Before drafting specs, plans, or task breakdowns for a feature, bug, or refactor
- Before answering a prompt that depends on previous project decisions or prior fixes
- When the user asks to remember, recall, reuse context, or summarize what was done before
- After a bug fix, architectural decision, workflow change, or non-obvious repo discovery

## Core Principle

Project memory is an acceleration layer, not the source of truth. If memory conflicts with code, configuration, or current docs, trust the repo and record a new note that supersedes the stale memory.

## Procedure

1. Inspect memory before broad exploration.
   - View `/memories/` first to identify existing repo and session notes.
   - Avoid creating duplicate notes for the same topic.

2. Classify the request.
   - `spec`: multi-step work that needs structured context for specs, plans, or tasks.
   - `prompt`: a direct prompt, answer, review, or focused edit that still depends on project context.
   - `recall`: the user explicitly asks what happened before, how something was fixed, or which decision was made.

3. Load the smallest useful memory slice.
   - For `spec`, read the most relevant repo memory notes plus the owning docs or architecture files for the touched area.
   - For `prompt`, read only the 1 to 3 most relevant notes. Do not dump broad project history into context.
   - For `recall`, start from memory and verify against the current repo if the note might be stale.

4. Verify memory against ground truth.
   - Check nearby code, config, specs, or architecture docs before relying on a memory note.
   - If memory is missing, do a targeted read of the nearest owning files and continue.
   - If memory conflicts with the repo, treat the repo as correct and capture the updated reality in a new repo memory note.

5. Produce a context packet for the active task.
   - Include goal, prior decisions, hard constraints, relevant commands, and current risks.
   - Keep it task-scoped. The context packet should help execution, not retell the whole repo history.

6. Execute the actual task with that context.
   - For spec work, feed the context packet into the spec, plan, and task generation flow.
   - For direct prompts, answer or implement using only the context that changes the outcome.

7. Persist what was learned.
   - Create a new repo memory note for stable discoveries, bug fixes, architectural decisions, workflow conventions, or important spec outcomes.
   - If the topic already exists in repo memory, create a newer follow-up note instead of rewriting history in place.
   - Use session memory only for short-lived conversation state when that scope is available and appropriate.

8. Close the loop.
   - State which memory notes were used.
   - State what new memory was added.
   - Call out stale notes, unresolved risks, or follow-up gaps.

## Branching Rules

- If the task touches both `backend/` and `frontend/`, load the relevant architecture docs before drafting specs.
- If the task is a small local edit, do not load all repo memory. Stay local.
- If no relevant memory exists, do not invent history. Do the smallest targeted discovery needed, then create a note after the work.
- If the task is read-only and no durable insight was discovered, do not create a new memory note.
- If a memory note is too broad or outdated, create a narrower dated follow-up note with the corrected fact.

## Completion Checks

- Memory was consulted before broad repo exploration.
- Only relevant memory was loaded for the task.
- Any conflict between memory and code was verified and resolved in favor of the repo.
- The context packet includes decisions, constraints, and risks that materially affect the task.
- New memory notes capture what changed, why it mattered, where it applies, and any validation or residual risk.

## Repo Note Naming

- `feature-topic-YYYYMMDD.md`
- `bugfix-topic-YYYYMMDD.md`
- `architecture-topic-YYYYMMDD.md`
- `specs-topic-YYYYMMDD.md`

Use the templates in [memory-note-templates](./references/memory-note-templates.md) when creating new notes.