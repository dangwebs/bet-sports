---
name: linting
description: "Linting and code formatting. Activate when setting up, fixing, or verifying linting and formatting. Covers ESLint, Prettier, TypeScript strict mode, and import ordering."
---

# Linting & Formatting Skill

## Discovery (Mandatory First Step)

Before modifying any linting config, find and read the project's actual files:

1. Search for ESLint configs: `.eslintrc.*`, `eslint.config.*`, `eslint` key in `package.json`.
2. Search for Prettier configs: `.prettierrc.*`, `prettier.config.*`, `prettier` key in `package.json`.
3. Read `tsconfig.json` files to understand strictness level.
4. Identify the lint/format commands in `package.json` scripts.

Never assume config — always read it first.

---

## ESLint Rules — Non-Negotiable

These rules must NEVER be disabled:

```javascript
// TypeScript-specific
'@typescript-eslint/no-explicit-any': 'error',
'@typescript-eslint/no-unused-vars': 'error',
'@typescript-eslint/explicit-function-return-type': 'warn',
'@typescript-eslint/no-floating-promises': 'error',
'@typescript-eslint/await-thenable': 'error',

// General
'no-console': 'warn',
'no-debugger': 'error',
'prefer-const': 'error',
'eqeqeq': ['error', 'always'],
```

Rules that CAN be disabled with a comment (and a required explanation):

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- third-party SDK returns untyped response
const rawResponse: unknown = await sdk.call();
```

## Prettier Configuration

Expected defaults — verify against the project's actual Prettier config:

```javascript
{
  semi: true,
  singleQuote: true,
  trailingComma: 'all',
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
  bracketSpacing: true,
  arrowParens: 'always',
}
```

**Never mix tabs and spaces. Never change indent width per-file.**

---

## TypeScript Strict Mode

These compiler flags must remain enabled:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

**Never add `// @ts-ignore`. Use `// @ts-expect-error` with a comment if unavoidable.**

---

## Import Ordering

Imports must follow this order (adapt alias patterns from the project's config):

```typescript
// 1. Node built-ins
import path from 'path';

// 2. External packages
import { SomeLib } from 'some-library';

// 3. Internal monorepo / alias packages
import { SharedDto } from '@alias/shared';

// 4. Local imports (relative)
import { MyService } from './my.service';
```

---

## "Perfect Save" Checklist

Before committing any file, verify:

- [ ] Lint command passes with 0 errors
- [ ] No unused imports or variables
- [ ] No `any` types
- [ ] No `console.log` left in production code
- [ ] No `TODO` comments without a linked issue / ticket number
- [ ] No `// @ts-ignore` without explanation
- [ ] No commented-out code blocks
- [ ] Import order is correct

---

## Common Fixes

### Floating promise
```typescript
// ❌ Promise not awaited or handled
this.mailer.send(user.email);

// ✅ Await it or mark fire-and-forget
await this.mailer.send(user.email);
void this.mailer.send(user.email);
```

### `any` type violation
```typescript
// ❌
function parseConfig(config: any) { ... }

// ✅
function parseConfig(config: Record<string, unknown>) { ... }
```
