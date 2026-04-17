---
description: Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
handoffs: 
  - label: Analyze For Consistency
    agent: speckit.analyze
    prompt: Run a project analysis for consistency
    send: true
  - label: Implement Project
    agent: speckit.implement
    prompt: Start the implementation in phases
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before tasks generation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_tasks` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    
    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Project Context Discovery** (MANDATORY — do this BEFORE generating tasks):

   The agent MUST build a mental model of the project to generate tasks with correct file paths, naming conventions, and patterns. Read in this order, skip files that don't exist:

   a. **Project identity** (read ALL that exist):
      - `CLAUDE.md` or `AGENTS.md` at repo root → project overview, structure, conventions, tech stack
      - `.github/copilot-instructions.md` → workspace-level rules and boundaries
      - `README.md` at repo root → project description, setup, and domain context

   b. **Tech stack detection** (read the first match found per category):
      - Package manifests: `package.json`, `pnpm-workspace.yaml`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `composer.json`
      - Framework configs: `tsconfig.json`, `next.config.*`, `vite.config.*`, `angular.json`, `nest-cli.json`
      - Monorepo indicators: `turbo.json`, `lerna.json`, `nx.json`

   c. **Directory structure**: List the top-level directories and up to 2 levels deep for the areas relevant to the feature. This reveals naming conventions, module organization, and existing patterns.

   d. **Existing code in the target area**: If the feature touches an existing domain, read 2-3 existing files in that area to understand current patterns, naming, imports, and file structure.

   **This context is NOT written to a file**. It is held in memory and used to:
   - Generate tasks with CORRECT file paths matching the project's actual structure
   - Use exact import paths, naming conventions, and module patterns from the codebase
   - Include realistic inline Pattern examples that match the project's actual code style
   - Reference existing utilities, types, and services for the Depends on / Input fields
   - Avoid generating tasks for infrastructure that already exists

3. **Load design documents**: Read from FEATURE_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities)
   - **Optional**: data-model.md (entities), contracts/ (interface contracts), research.md (decisions), quickstart.md (test scenarios)
   - Note: Not all projects have all documents. Generate tasks based on what's available.

4. **Execute task generation workflow**:
   - Load plan.md and extract tech stack, libraries, project structure
   - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.)
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map interface contracts to user stories
   - If research.md exists: Extract decisions for setup tasks
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)

5. **Generate tasks.md**: Use `.specify/templates/tasks-template.md` as structure, fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational tasks (blocking prerequisites for all user stories)
   - Phase 3+: One phase per user story (in priority order from spec.md)
   - Each phase includes: story goal, independent test criteria, tests (if requested), implementation tasks
   - Final Phase: Polish & cross-cutting concerns
   - All tasks must follow the strict checklist format (see Task Generation Rules below)
   - Clear file paths for each task
   - Dependencies section showing story completion order
   - Parallel execution examples per story
   - Implementation strategy section (MVP first, incremental delivery)

6. **Report**: Output path to generated tasks.md and summary:
   - Total task count
   - Task count per user story
   - Parallel opportunities identified
   - Independent test criteria for each story
   - Suggested MVP scope (typically just User Story 1)
   - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)

7. **Check for extension hooks**: After tasks.md is generated, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_tasks` key
   - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
   - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
   - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
     - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
     - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
   - For each executable hook, output the following based on its `optional` flag:
     - **Optional hook** (`optional: true`):
       ```
       ## Extension Hooks

       **Optional Hook**: {extension}
       Command: `/{command}`
       Description: {description}

       Prompt: {prompt}
       To execute: `/{command}`
       ```
     - **Mandatory hook** (`optional: false`):
       ```
       ## Extension Hooks

       **Automatic Hook**: {extension}
       Executing: `/{command}`
       EXECUTE_COMMAND: {command}
       ```
   - If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

Context for task generation: $ARGUMENTS

The tasks.md should be immediately executable - each task must be specific enough that the MOST BASIC LLM (e.g., GPT-3.5, Haiku, small local models) can complete it without additional context, without reading other tasks, and without needing to make architectural decisions.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Tests are OPTIONAL**: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach.

### Atomicity Principle (MANDATORY)

Each task MUST be **self-contained and atomic** — executable by the most basic AI without access to any other task, spec, or design document. This means:

1. **Zero ambiguity**: The task description alone must contain ALL information needed to execute it. No "see spec" or "as described in plan.md".
2. **Exact inputs/outputs**: Specify the exact interface (props, params, return types) inline in the task.
3. **Explicit patterns**: If the task must follow an existing pattern, PASTE the pattern example in the task — don't reference another file to "follow".
4. **One file, one concern**: Each task creates or modifies exactly ONE file (exceptions only for tightly coupled pairs like component + test).
5. **No decision-making**: The task tells the AI WHAT to do, not what to "figure out". Architecture decisions are resolved in the task description, not delegated.
6. **Copy-pasteable verification**: Each task includes HOW to verify it's done correctly (e.g., "the component renders a table with 4 columns", "the function returns `{ success: boolean }`").

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

Followed by an **indented detail block** with:

```text
  - **What**: One-sentence summary of what to create/modify
  - **File**: Exact absolute or relative file path
  - **Why**: One sentence on the purpose (so AI understands intent, not just mechanics)
  - **Input**: What this file receives (props, params, imports from specific files)
  - **Output**: What this file exports/renders/returns
  - **Pattern**: Inline code snippet showing the structure to follow (3-10 lines max)
  - **Acceptance**: How to verify correctness (renders X, exports Y, passes Z)
  - **Depends on**: Task IDs that must be complete first (or "none")
```

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: Sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: Include ONLY if task is parallelizable (different files, no dependencies on incomplete tasks)
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from spec.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: Clear action verb + what + exact file path
6. **Detail block**: REQUIRED for every task (see format above)

**Examples**:

- ✅ CORRECT:
  ```
  - [ ] T012 [P] [US1] Create Product type interface in src/types/product.ts
    - **What**: Define the TypeScript interface for product data
    - **File**: `src/types/product.ts`
    - **Why**: Typed contract for product data used by list views and forms
    - **Input**: None (standalone type file)
    - **Output**: Export `Product` interface with fields: `id: string`, `name: string`, `price: number`, `category: string`, `createdAt: string`
    - **Pattern**:
      ```ts
      export interface Product {
        id: string;
        name: string;
        price: number;
        category: string;
        createdAt: string;
      }
      ```
    - **Acceptance**: File exports the interface, no `any` types, compiles without errors
    - **Depends on**: none
  ```

- ✅ CORRECT:
  ```
  - [ ] T014 [US1] Create product list service in src/services/product.service.ts
    - **What**: Service class with CRUD methods for Product entity
    - **File**: `src/services/product.service.ts`
    - **Why**: Encapsulates business logic for product operations, called by controllers/handlers
    - **Input**: Imports `Product` from `src/types/product.ts`, receives `{ name: string, price: number, category: string }` for create
    - **Output**: Export `ProductService` with methods: `create(data) → Product`, `findAll() → Product[]`, `findById(id) → Product | null`, `delete(id) → boolean`
    - **Pattern**:
      ```ts
      export class ProductService {
        async create(data: CreateProductInput): Promise<Product> { /* ... */ }
        async findAll(): Promise<Product[]> { /* ... */ }
        async findById(id: string): Promise<Product | null> { /* ... */ }
        async delete(id: string): Promise<boolean> { /* ... */ }
      }
      ```
    - **Acceptance**: All 4 methods exist, types match, no `any`, service is importable without errors
    - **Depends on**: T012 (Product type)
  ```

- ❌ WRONG: `- [ ] T001 Create project structure per implementation plan` (no detail block, vague)
- ❌ WRONG: `- [ ] T012 [P] [US1] Create User model in src/models/user.py` (no detail block)
- ❌ WRONG: `- [ ] Create User model` (missing ID, Story label, AND detail block)
- ❌ WRONG: Any task with "follow the pattern in X file" without inlining the pattern
- ❌ WRONG: Any task that requires reading another task to understand what to do

### Task Organization

1. **From User Stories (spec.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Interfaces/UI needed for that story
     - If tests requested: Tests specific to that story
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each interface contract → to the user story it serves
   - If tests requested: Each interface contract → contract test task [P] before implementation in that story's phase

3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase

4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns
