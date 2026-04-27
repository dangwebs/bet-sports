---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description` + Detail Block

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- **Every task MUST include an indented detail block** with: What, File, Why, Input, Output, Pattern, Acceptance, Depends on
- Each task must be executable by the most basic AI without reading any other task or document

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
  - **What**: Initialize folder structure with all directories needed by subsequent tasks
  - **File**: Project root (create directories only)
  - **Why**: All subsequent tasks expect these directories to exist
  - **Input**: None
  - **Output**: Directory tree matching the plan.md structure section
  - **Pattern**: `mkdir -p src/{models,services,routes,middleware} tests/{unit,integration,contract}`
  - **Acceptance**: All directories exist, no files created yet
  - **Depends on**: none

- [ ] T002 Initialize [language] project with [framework] dependencies
  - **What**: Create package manifest and install all dependencies listed in plan.md
  - **File**: `package.json` (or equivalent)
  - **Why**: Runtime and dev dependencies must be available before any code task
  - **Input**: Dependency list from plan.md (enumerate here: dep1@version, dep2@version, ...)
  - **Output**: Lock file generated, node_modules (or equivalent) populated
  - **Pattern**: `npm init -y && npm install dep1 dep2 && npm install -D devdep1 devdep2`
  - **Acceptance**: `npm ls` shows all deps installed, no peer dependency warnings
  - **Depends on**: T001

- [ ] T003 [P] Configure linting and formatting tools
  - **What**: Create ESLint and Prettier config files with project-standard rules
  - **File**: `.eslintrc.js` and `.prettierrc` (or equivalents)
  - **Why**: All subsequent code must pass lint/format checks
  - **Input**: Framework-specific recommended configs (enumerate here)
  - **Output**: Config files that enforce project coding standards
  - **Pattern**: (paste actual config content here, e.g. `{ "semi": true, "singleQuote": true }`)
  - **Acceptance**: Running `npx eslint .` and `npx prettier --check .` produces zero errors on an empty project
  - **Depends on**: T002

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
  - **What**: Configure ORM/migration tool with connection to database
  - **File**: `src/config/database.ts` (or equivalent)
  - **Why**: Models in subsequent tasks need a database connection and migration runner
  - **Input**: Database URL from environment variable `DATABASE_URL`
  - **Output**: Exported `db` instance and migration runner config
  - **Pattern**: (paste actual setup code here — 5-10 lines)
  - **Acceptance**: Running migrations command succeeds with empty database, connection test passes
  - **Depends on**: T002

- [ ] T005 [P] Implement authentication/authorization framework
  - **What**: Create auth middleware that validates JWT tokens and attaches user to request
  - **File**: `src/middleware/auth.ts`
  - **Why**: Protected routes in user story phases require authenticated requests
  - **Input**: JWT secret from env, `Authorization: Bearer <token>` header
  - **Output**: Export `authMiddleware` function that sets `req.user = { id, role, permissions }` or returns 401
  - **Pattern**: (paste actual middleware skeleton here)
  - **Acceptance**: Middleware rejects requests without valid token (401), passes valid token requests with user object attached
  - **Depends on**: T002

- [ ] T006 [P] Setup API routing and middleware structure
  - **What**: Create the router/app entry point that mounts route groups
  - **File**: `src/app.ts` or `src/routes/index.ts`
  - **Why**: All endpoint tasks mount routes here
  - **Input**: Framework (e.g., Express, Fastify, NestJS) app instance
  - **Output**: Exported app instance with middleware chain (cors, json parsing, error handler)
  - **Pattern**: (paste actual app setup here)
  - **Acceptance**: App starts on specified port, health endpoint returns 200
  - **Depends on**: T002

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
  - **What**: Write a failing contract test that defines the expected request/response shape
  - **File**: `tests/contract/test_[name].py`
  - **Why**: Defines the contract before implementation — TDD anchor
  - **Input**: Endpoint `POST /api/[resource]` with body `{ field1: string, field2: number }`
  - **Output**: Test file that asserts: status 201, response shape `{ id: string, field1: string, createdAt: string }`
  - **Pattern**: (paste test skeleton with exact assertions)
  - **Acceptance**: Test exists and FAILS (no implementation yet). Running `pytest tests/contract/test_[name].py` fails with expected error.
  - **Depends on**: T006 (routing structure)

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create [Entity1] model in src/models/[entity1].py
  - **What**: Define the [Entity1] database model/schema with all fields
  - **File**: `src/models/[entity1].py`
  - **Why**: Data layer for [Entity1] CRUD operations in this user story
  - **Input**: Database connection from `src/config/database.ts`
  - **Output**: Export `Entity1Model` with fields: `id (PK, auto)`, `name (string, required, max 100)`, `description (string, optional)`, `createdAt (datetime, auto)`, `updatedAt (datetime, auto)`
  - **Pattern**:
    ```python
    class Entity1(Base):
        __tablename__ = "entity1"
        id = Column(Integer, primary_key=True)
        name = Column(String(100), nullable=False)
        # ... all fields here
    ```
  - **Acceptance**: Model can be imported without errors, migration generates correct table schema
  - **Depends on**: T004 (database setup)

- [ ] T014 [US1] Implement [Service] in src/services/[service].py
  - **What**: Business logic service with CRUD methods for [Entity1]
  - **File**: `src/services/[service].py`
  - **Why**: Encapsulates business rules, called by route handlers
  - **Input**: `Entity1Model` from `src/models/[entity1].py`, receives `{ name: string, description?: string }` for create
  - **Output**: Export `Entity1Service` class/object with methods: `create(data) → Entity1`, `findById(id) → Entity1 | null`, `findAll() → Entity1[]`, `delete(id) → boolean`
  - **Pattern**: (paste service skeleton showing method signatures and error handling)
  - **Acceptance**: Service methods work with in-memory or test database, create returns entity with id, findById returns null for non-existent id
  - **Depends on**: T012 (Entity1 model)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
  - **What**: (describe exactly what the test validates)
  - **File**: `tests/contract/test_[name].py`
  - **Why**: (one sentence)
  - **Input**: (request shape)
  - **Output**: (expected assertions)
  - **Pattern**: (inline test code)
  - **Acceptance**: Test fails before implementation
  - **Depends on**: (task IDs)

### Implementation for User Story 2

- [ ] T020 [P] [US2] Create [Entity] model in src/models/[entity].py
  - **What**: (exactly what model/fields)
  - **File**: `src/models/[entity].py`
  - **Why**: (purpose)
  - **Input**: (imports/dependencies)
  - **Output**: (exported symbol with fields listed)
  - **Pattern**: (inline code)
  - **Acceptance**: (how to verify)
  - **Depends on**: T004

- [ ] T021 [US2] Implement [Service] in src/services/[service].py
  - **What**: (exactly what methods)
  - **File**: `src/services/[service].py`
  - **Why**: (purpose)
  - **Input**: (model imports, method params with types)
  - **Output**: (exported class/object with method signatures)
  - **Pattern**: (inline code)
  - **Acceptance**: (verifiable criteria)
  - **Depends on**: T020

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T024 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
  - **(same detail block structure as above — What, File, Why, Input, Output, Pattern, Acceptance, Depends on)**

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create [Entity] model in src/models/[entity].py
  - **(same detail block structure as above)**

- [ ] T027 [US3] Implement [Service] in src/services/[service].py
  - **(same detail block structure as above)**

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
  - **What**: (exact doc file to create/update, what content)
  - **File**: `docs/[file].md`
  - **Why**: (purpose of documentation)
  - **Input**: (what to document — API endpoints, setup steps, etc.)
  - **Output**: (markdown file with specific sections)
  - **Pattern**: (template/structure to follow)
  - **Acceptance**: (doc is accurate, all endpoints documented, etc.)
  - **Depends on**: (all implementation tasks)

- [ ] TXXX Code cleanup and refactoring
  - **(same detail block structure)**

- [ ] TXXX [P] Run quickstart.md validation
  - **(same detail block structure)**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- **EVERY task MUST have the detail block** (What, File, Why, Input, Output, Pattern, Acceptance, Depends on)
- The detail block must contain ALL info needed — a basic AI should execute the task reading ONLY that block
- Never reference "see spec.md" or "follow the pattern in X file" — paste the relevant info inline
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
