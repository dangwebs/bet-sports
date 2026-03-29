---
name: linting
description: "Linting and code formatting. Activate when setting up, fixing, or verifying linting and formatting. Covers ESLint, Prettier, TypeScript strict mode, and the project's specific configurations."
---

# Linting & Formatting Skill

## Discovery (Mandatory First Step)

Before modifying any linting config, check:

```bash
# Backend (mono-ms)
HyperGenIA/mono-ms/.eslintrc.mjs
HyperGenIA/mono-ms/.prettierrc.mjs
HyperGenIA/mono-ms/tsconfig.json

# Frontend
Front/eslint.config.mjs
Front/prettier.config.mjs
Front/tsconfig.json
```

Never assume config — always read it first.

---

## Project Linting Stack

### Backend (`HyperGenIA/mono-ms/`)
- **ESLint** with NestJS-compatible rules
- **Prettier** for formatting
- **TypeScript** strict mode
- **pnpm lint** → runs across all services via Turborepo

### Frontend (`Front/`)
- **ESLint** with Next.js config (`next lint`)
- **Prettier** for formatting
- **TypeScript** strict mode
- `npm run check` → lint + typecheck together

---

## ESLint Rules — Non-Negotiable

These rules must NEVER be disabled:

```javascript
// TypeScript-specific
'@typescript-eslint/no-explicit-any': 'error',       // Zero any
'@typescript-eslint/no-unused-vars': 'error',         // Clean up dead code
'@typescript-eslint/explicit-function-return-type': 'warn',
'@typescript-eslint/no-floating-promises': 'error',   // Unhandled promises
'@typescript-eslint/await-thenable': 'error',

// General
'no-console': 'warn',       // Use the logger, not console.log
'no-debugger': 'error',
'prefer-const': 'error',    // Never use var or unnecessary let
'eqeqeq': ['error', 'always'],
```

Rules that CAN be disabled with a comment (and a required explanation):

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- third-party SDK returns untyped response
const rawResponse: unknown = await sdk.call();
```

## Prettier Configuration

The project uses the following Prettier defaults (verify against `.prettierrc.mjs`):

```javascript
// Expected defaults for this project
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

The project runs TypeScript in strict mode. These compiler flags must remain enabled:

```json
// Required in every tsconfig.json
{
  "compilerOptions": {
    "strict": true,                        // Enables all strict checks
    "noImplicitAny": true,                 // Prevents 'any' from sneaking in
    "strictNullChecks": true,              // Forces null/undefined handling
    "noUncheckedIndexedAccess": true,      // Array access returns T | undefined
    "noImplicitReturns": true,             // All code paths must return
    "noFallthroughCasesInSwitch": true
  }
}
```

**Never add `// @ts-ignore`. Use `// @ts-expect-error` with a comment if unavoidable.**

---

## Import Ordering (ESLint `import/order`)

Imports must follow this order, enforced by ESLint:

```typescript
// 1. Node built-ins
import path from 'path';
import fs from 'fs';

// 2. External packages
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';

// 3. Internal monorepo packages
import { CreateUserDto } from '@repo/api';
import { slugify } from '@repo/common';

// 4. Local imports (relative)
import { UserRepository } from './user.repository';
import { UserMapper } from './user.mapper';
```

Frontend order:

```typescript
// 1. React/Next.js
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. External packages
import { useForm } from 'react-hook-form';
import { useTranslations } from 'next-intl';

// 3. Internal aliases
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';

// 4. Relative imports
import { BotCard } from './bot-card';
import type { BotListProps } from './types';
```

---

## "Perfect Save" Checklist

Before committing any file, verify:

- [ ] `pnpm lint` (backend) or `npm run check` (frontend) passes with 0 errors
- [ ] No unused imports or variables
- [ ] No `any` types
- [ ] No `console.log` left in production code
- [ ] No `TODO` comments without a linked issue / ticket number
- [ ] No `// @ts-ignore` without explanation
- [ ] No commented-out code blocks
- [ ] Import order is correct

---

## Common Fixes

### Unused import
```typescript
// ❌ Left over import
import { BadRequestException } from '@nestjs/common'; // never used

// ✅ Remove it
```

### Floating promise (no-floating-promises)
```typescript
// ❌ Promise not awaited or handled
this.mailer.send(user.email);

// ✅ Await it
await this.mailer.send(user.email);
// or if truly fire-and-forget
void this.mailer.send(user.email);
```

### `any` type violation
```typescript
// ❌ 
function parseConfig(config: any) { ... }

// ✅
function parseConfig(config: Record<string, unknown>) { ... }
```
