---
name: code-quality
description: "Specialist for ensuring maximum code quality. Applies Conventional Commits, Clean Code, SOLID principles, strict typing, import ordering, and guarantees code is perfectly formatted and linter-free."
---

# 💎 Code Quality Skill

This skill is cross-cutting and must be applied to **ALL** code written or modified in the project, both in the frontend and the backend.

Your primary goal with this skill is to ensure code reads as if written by a meticulous Senior Software Engineer.

## 1. SOLID Principles & Clean Code

- **S (Single Responsibility):** Each class, component, or function must have a single responsibility. Keep classes small and functions short (ideally under 20–30 lines).
- **O (Open/Closed):** Code should be open for extension but closed for modification. Prefer interfaces and polymorphism over excessive `if/switch` chains.
- **L (Liskov Substitution):** Derived classes must be substitutable for their base classes without altering correctness.
- **I (Interface Segregation):** Interfaces should be specific and minimal. Don't force implementers to define methods they don't use.
- **D (Dependency Inversion):** Depend on abstractions, not concrete implementations.
- **Meaningful Names:** Use nouns for variables/classes and verbs for functions. Names should reveal intent without needing comments.
- **DRY (Don't Repeat Yourself):** Avoid duplicated logic. Extract common code into utilities, hooks, or shared functions.
- **KISS (Keep It Simple, Stupid):** Favor readability and simplicity over over-engineering.

## 2. Design Patterns (Code-Level)

Apply these patterns when the situation calls for them. Do NOT force a pattern where simple code suffices — KISS takes priority.

### Creational Patterns — _How objects are created_

| Pattern       | When to Use                                                    | Example                                                |
| ------------- | -------------------------------------------------------------- | ------------------------------------------------------ |
| **Factory**   | When object creation logic is complex or varies by type        | `createNotification('email')` returns the right class  |
| **Builder**   | When constructing an object requires many optional parameters  | Building a complex query or config object step-by-step |
| **Singleton** | When exactly one instance must exist globally (use sparingly!) | Database connection pool, logger instance              |

### Structural Patterns — _How objects are composed_

| Pattern       | When to Use                                                                  | Example                                                                       |
| ------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **Adapter**   | When integrating an external library/API whose interface doesn't match yours | Wrapping a third-party payment SDK behind your own interface                  |
| **Decorator** | When adding behavior to an object without modifying it                       | Adding logging, caching, or auth checks to a service                          |
| **Facade**    | When simplifying a complex subsystem into one clean interface                | A single `NotificationService` that internally coordinates email + push + SMS |
| **Composite** | When treating individual objects and groups uniformly                        | A UI component tree, or nested permissions                                    |

### Behavioral Patterns — _How objects communicate_

| Pattern                                  | When to Use                                                  | Example                                                                  |
| ---------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **Strategy**                             | When multiple algorithms can be swapped at runtime           | Different pricing calculations, sorting strategies                       |
| **Observer**                             | When one event needs to trigger reactions in multiple places | Event emitters, real-time UI updates, webhooks                           |
| **Repository**                           | When abstracting data access from business logic             | `UserRepository.findById(id)` hides whether it's SQL, MongoDB, or an API |
| **Middleware / Chain of Responsibility** | When processing goes through a pipeline of steps             | Auth → Validation → Rate Limit → Handler                                 |

### Frontend-Specific Patterns

| Pattern                                    | When to Use                                                                       | Example                                                   |
| ------------------------------------------ | --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **Container / Presentational**             | When separating data-fetching logic from display logic                            | A `UserListContainer` fetches data, `UserList` renders it |
| **Custom Hook (React) / Composable (Vue)** | When reusing stateful logic across components                                     | `useAuth()`, `usePagination()`, `useDebounce()`           |
| **Render Props / Slots**                   | When a component needs to delegate its rendering to the consumer                  | `<DataTable renderRow={(row) => ...}>`                    |
| **Higher-Order Component (HOC)**           | When wrapping components with cross-cutting behavior (prefer hooks when possible) | `withAuth(Component)`, `withTheme(Component)`             |

> **Rule**: When you identify repeated `if/else` or `switch` blocks, a **Strategy** pattern is almost always the right refactor. When you see tight coupling between a producer and consumer, consider **Observer** or **Adapter**.

## 3. Strict Typing

- **Zero `any`:** Using `any` in TypeScript is strictly prohibited. Use `unknown` if absolutely necessary or define generics (`<T>`).
- **Interfaces over Types:** In TypeScript, prefer `interface` for object shapes and `type` for unions or primitive aliases.
- **Type Hints in Python:** Every function must have type annotations for both arguments and return values: `def func(arg: int) -> str:`.
- **Boundary Validation:** Use the project's validation tools (Pydantic, Zod, class-validator, Joi, etc.) to validate data at system boundaries.

## 4. Import Management

Imports must always be organized, clean, and free of circular dependencies. When writing or refactoring files, group imports in the following order, separated by a blank line:

### TypeScript / JavaScript

1. **External libraries** (framework core, NPM packages).
2. **Internal shared libraries/packages** (monorepo shared code, aliases like `@repo/*`).
3. **Local modules** — relative imports from the same project (`@/components/...`, `./utils`, `../dto`).
4. **Assets or styles** (`.css`, `.scss`, images) — only applicable in frontend.

### Python

1. **Standard library** (`os`, `sys`, `typing`, `uuid`).
2. **Third-party libraries** (`fastapi`, `pydantic`, `django`).
3. **Local modules** (`src.common...`, `src.user...`, relative imports).

> Adapt the specific alias patterns (`@/`, `@repo/`, `src/`) to match whatever the project actually uses. Discover this from existing files before imposing any convention.

## 5. Linting & Formatting ("Perfect Save")

When you finish modifying a file, your work is **NOT DONE** until the code complies with all formatting and linter rules. Never leave misaligned code, mixed quotes, or unused variables.

- **Discover the project's formatting config first**: Check for `.prettierrc`, `.eslintrc`, `pyproject.toml`, `.editorconfig`, `biome.json`, or similar config files. Follow whatever the project has configured.
- **If no config exists**, apply these sensible defaults:
  - TypeScript/JavaScript: single quotes, trailing semicolons, 2-space indent.
  - Python: PEP 8, double quotes (Black-style), 4-space indent, max 88 chars per line.
- **Dead code cleanup:** Remove any declared but unused variables, functions, or imports.

## 6. Conventional Commits

When documenting changes or generating commit messages, always use the Conventional Commits standard:

**Format:** `<type>(<optional scope>): <description>`

**Allowed types:**

- `feat`: A new feature.
- `fix`: A bug fix.
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `style`: Changes that don't affect the meaning of the code (whitespace, formatting).
- `docs`: Documentation-only changes.
- `chore`: Build tasks, package upgrades, tooling changes.
- `test`: Adding or fixing tests.
- `perf`: A code change that improves performance.
- `ci`: Changes to CI/CD configuration files and scripts.

**Rules:**

- Description must be lowercase, imperative mood, no trailing period.
- Scope should match the module or domain area (e.g., `auth`, `users`, `workflow`).
- Body (optional) should explain _why_, not _what_.

_Example:_ `refactor(auth): extract validation logic into standalone use case`

---

> ⚠️ **GOLDEN RULE OF THIS SKILL:**
> Do not ask permission to clean up messy code. If you are touching a file and you see a linting issue, disordered imports, or missing types near your work area, **fix it proactively** while ensuring functionality is not broken.
