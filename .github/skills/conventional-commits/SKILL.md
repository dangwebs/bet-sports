---
name: conventional-commits
description: "Conventional Commits v1.0.0 specification. Activate when writing commit messages, PR descriptions, changelogs, or reviewing git history. Ensures git history is readable, parseable, and release-automation-compatible."
---

# Conventional Commits Skill

All commit messages in this project **must** follow [Conventional Commits v1.0.0](https://www.conventionalcommits.org/).

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | When to Use | Triggers version bump |
|---|---|---|
| `feat` | A new user-visible feature | Minor (`1.x.0`) |
| `fix` | A bug fix | Patch (`1.0.x`) |
| `refactor` | Code change that neither fixes a bug nor adds a feature | None |
| `perf` | Code change that improves performance | None (patch if significant) |
| `docs` | Documentation-only changes | None |
| `style` | Whitespace, formatting, missing semicolons (no logic change) | None |
| `test` | Adding or correcting tests | None |
| `chore` | Build tasks, dependency updates, tooling configuration | None |
| `ci` | Changes to CI/CD configuration files (.github/workflows) | None |
| `build` | Changes affecting the build system (turbo, webpack, nest-cli) | None |
| `revert` | Reverts a previous commit | Depends on reverted commit |

> `feat` and `fix` MUST align with the actual change. Never use `chore` for a feature or `refactor` for a fix.

## Scope

Scope identifies which part of the codebase was changed. Use the service or module name:

| Area | Scope Examples |
|---|---|
| Backend services | `auth`, `user`, `tenant`, `bot`, `billing`, `notify`, `player` |
| API Gateway modules | `api-gateway`, `graphql`, `gql-auth` |
| Frontend | `frontend`, `auth-ui`, `dashboard`, `bot-ui` |
| Infrastructure | `docker`, `ci`, `proto`, `k8s` |
| Monorepo packages | `api-pkg`, `common-pkg` |
| Documentation | `docs`, `readme` |

## Description Rules

- **Imperative mood**: `add feature`, not `added feature` or `adds feature`.
- **Lowercase**: No capital letters in the description.
- **No period**: Don't end with `.`
- **Max 72 characters**: Keep it concise.
- **What changed, not how**: Describe the change, not the implementation detail.

## Body (Optional but Recommended for Complex Changes)

- Separate from description with a blank line.
- Explain the **why**, not the **what** (the diff shows the what).
- Wrap at 72 characters.

## Footer

Used for breaking changes and issue references:

```
BREAKING CHANGE: <description of what breaks and how to migrate>
Closes #123
Refs #456
```

> A `BREAKING CHANGE` footer triggers a Major version bump (`x.0.0`).

## Examples

```
# ✅ Simple feature
feat(auth): add refresh token rotation

# ✅ Bug fix with scope
fix(bot): prevent duplicate execution when schedule overlaps

# ✅ Refactor with body
refactor(user-svc): extract password hashing into dedicated service

Password hashing logic was duplicated between the create and update
flows. Centralizing it ensures consistent bcrypt rounds configuration
from the environment.

# ✅ Breaking change
feat(api-gateway)!: remove deprecated listBots_v1 query

BREAKING CHANGE: listBots_v1 has been removed. Migrate to listBots
which now supports cursor-based pagination via the 'cursor' argument.

Closes #234

# ✅ Chore
chore(deps): upgrade nestjs to 11.1.0

# ✅ CI change
ci: add docker image vulnerability scan step to pipeline

# ✅ Docs
docs(auth-svc): document JWT refresh token flow in README
```

## Anti-patterns to Avoid

```
# ❌ Vague
git commit -m "fix stuff"
git commit -m "update"
git commit -m "wip"

# ❌ Wrong type
git commit -m "chore: add user export feature"   # should be feat
git commit -m "feat: fix typo in button"         # should be fix/style

# ❌ Past tense
git commit -m "feat(auth): added OAuth2 login"   # should be "add"

# ❌ Too long description
git commit -m "feat(bot): add a new feature that allows users to schedule bots to run automatically at specific times"
# → feat(bot): add time-based bot scheduling
```

## Commit Atomicity

- **One logical change per commit**: If you're tempted to use `and` in the description, split into two commits.
- **Don't bundle unrelated changes**: A refactor and a feature fix in the same commit makes rollback impossible.
- **Never commit broken code to main**: All commits on `main` must be in a working state.

## Branch Naming (Related Convention)

Branches should mirror commit types:

```
feat/bot-scheduling
fix/auth-token-refresh
refactor/user-service-extraction
chore/upgrade-nestjs-11
docs/api-gateway-graphql-schema
```
